#!/usr/bin/env python3
"""Fast archive/state/profile tests; no vendor downloads or live installation."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from ssh_harness import client_exec_command

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_server", str(ROOT / "src/source_server.py"))
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)


class SourceServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zcode-source-unit.")
        self.root = Path(self.temp.name)
        self.helper = ss.SourceServer(argparse.Namespace(zcode_root=str(self.root / ".zcode"),
                                                        runtime_dir=None, cli=str(ROOT / "bin/zcode-centos7")))

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, names):
        archive = self.root / "input.tar.gz"
        with tarfile.open(str(archive), "w:gz") as t:
            for name, kind in names:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = "/etc/passwd" if kind == tarfile.SYMTYPE else ""
                t.addfile(member, io.BytesIO())
        return archive

    def test_unsafe_archive_entries(self):
        for entries in [ [("zcode-server-linux-x64/../outside", tarfile.REGTYPE)],
                         [("/absolute", tarfile.REGTYPE)],
                         [("zcode-server-linux-x64/link", tarfile.SYMTYPE)],
                         [("zcode-server-linux-x64/hard", tarfile.LNKTYPE)],
                         [("zcode-server-linux-x64/file", tarfile.REGTYPE)] * 2 ]:
            with self.subTest(entries=entries):
                destination = self.root / "extract"
                with self.assertRaises(ValueError):
                    ss.extract_archive(self.archive(entries), destination)
                self.assertFalse(destination.exists())

    def test_wrong_vendor_archive_rejected_before_runtime_install(self):
        self.helper.args.archive = str(self.archive([("zcode-server-linux-x64/file", tarfile.REGTYPE)]))
        with self.assertRaisesRegex(ValueError, "official archive"):
            self.helper.prepare()
        self.assertFalse(self.helper.runtime_root.exists())

    def test_component_hash_fixture(self):
        files = self.root / "runtime"
        files.mkdir()
        (files / "b").write_bytes(b"second")
        (files / "a").write_bytes(b"first")
        (files / "folder").mkdir()
        (files / "folder/child").write_bytes(b"nested")
        (files / "folder.txt").write_bytes(b"flat")
        identity, size = ss.component_identity(self.root, ["runtime"])
        self.assertEqual(identity, hashlib.sha256(
            b"runtime/a\0firstruntime/b\0secondruntime/folder.txt\0flatruntime/folder/child\0nested").hexdigest())
        self.assertEqual(size, 21)

    def test_release_hash_detects_file_and_mode_changes(self):
        target = self.root / "file"
        target.write_bytes(b"original")
        before = ss.tree_hash(self.root)
        target.chmod(0o700)
        self.assertNotEqual(before, ss.tree_hash(self.root))
        target.write_bytes(b"replacement")
        changed = ss.tree_hash(self.root)
        (self.root / ".release-integrity.json").write_text("ignored")
        self.assertEqual(changed, ss.tree_hash(self.root))

    def test_uninstall_removes_only_managed_block(self):
        rc = self.root / ".bashrc"
        rc.write_bytes(("before\n" + ss.BEGIN + ". /managed/hook\n" + ss.END + "after\n").encode())
        self.helper.work.mkdir(parents=True)
        self.helper.uninstall()
        self.assertEqual(rc.read_bytes(), b"before\nafter\n")

    def test_profile_symlink_and_ambiguous_markers_refused(self):
        rc = self.root / ".bashrc"
        rc.symlink_to(self.root / "outside")
        with self.assertRaises(ValueError):
            self.helper.bashrc_without_block()
        rc.unlink()
        rc.write_text(ss.BEGIN)
        with self.assertRaises(ValueError):
            self.helper.bashrc_without_block()

    def test_status_does_not_create_state(self):
        self.assertFalse(self.helper.status(probe=True))
        self.assertFalse(self.helper.root.exists())

    def test_wrapped_probe_function_stops_at_diagnostic_process(self):
        if subprocess.call(["/bin/sh", "-c", 'test -n "${BASH_VERSION-}"']) != 0:
            self.skipTest("Function inheritance requires Bash-based /bin/sh (CentOS 7 target)")
        support = self.helper.work / "support"
        support.mkdir(parents=True)
        probe = "getconf GNU_LIBC_VERSION"
        (support / "probe-3.16.2.sh").write_text(probe + "\n")
        (support / "source_server.py").write_text(
            'import os\nassert "BASH_FUNC_getconf%%" not in os.environ\nprint("glibc 2.44")\n')
        env = dict(os.environ, HOME=str(self.root), SSH_CONNECTION="127.0.0.1 1 127.0.0.1 2")
        env.pop("SSH_TTY", None)
        script = 'BASH_EXECUTION_STRING=$1; . "$2"; eval "$1"'

        def execute(command):
            return subprocess.check_output(
                ["bash", "--noprofile", "--norc", "-c", script, "hook-test", command,
                 str(ROOT / "src/ssh_probe_hook.bash")], env=env).decode().strip()

        self.assertEqual(execute(probe), "glibc 2.44")
        self.assertEqual(execute(client_exec_command(probe)), "glibc 2.44")
        system = subprocess.check_output(["/usr/bin/getconf", "GNU_LIBC_VERSION"]).decode().strip()
        self.assertEqual(execute(client_exec_command(probe + "; true")), system)
        self.assertEqual(execute(client_exec_command(probe) + "; true"), system)
        self.assertEqual(execute(client_exec_command("getconf LONG_BIT")), "64")

    def test_mutating_commands_refuse_symlink_directories(self):
        self.helper.runtime_root.mkdir(parents=True)
        (self.helper.runtime_root / "releases").symlink_to(self.root / "outside")
        with self.assertRaises(ValueError):
            with self.helper.lock():
                self.fail("Symlink directory accepted")

    def test_failed_offline_activation_restores_previous_pointer(self):
        self.helper.work.mkdir(parents=True)
        self.helper.server.mkdir()
        current = self.helper.server / "current.json"
        original = b'{"version":"3.16.2","archiveSha256":"previous"}\n'
        current.write_bytes(original)
        artifact = self.root / "artifact"
        artifact.mkdir()
        archive = self.archive([("zcode-server-linux-x64/bin/zcode", tarfile.REGTYPE)])
        (artifact / "compatible.tar.gz").write_bytes(archive.read_bytes())
        record = {"artifact_dir": str(artifact), "derived_sha256": "new"}

        def activate(*args, **kwargs):
            current.write_text(json.dumps({"archiveSha256": "new"}))

        with mock.patch.object(self.helper, "prepare", return_value=record), \
                mock.patch.object(self.helper, "verify_record", side_effect=ValueError("post-install failure")), \
                mock.patch.object(ss, "run", side_effect=activate):
            with self.assertRaisesRegex(ValueError, "post-install failure"):
                self.helper.install()
        self.assertEqual(current.read_bytes(), original)
        self.assertFalse(self.helper.state_path.exists())

    def test_task_guard_does_not_trigger_unnecessary_live_rollback(self):
        self.helper.work.mkdir(parents=True)
        self.helper.server.mkdir()
        current = self.helper.server / "current.json"
        original = b'{"version":"3.16.2","archiveSha256":"same"}\n'
        current.write_bytes(original)
        previous_state = b'{"status":"installed"}\n'
        self.helper.state_path.write_bytes(previous_state)
        artifact = self.root / "artifact"
        artifact.mkdir()
        (artifact / "compatible.tar.gz").write_bytes(self.archive([
            ("zcode-server-linux-x64/bin/zcode", tarfile.REGTYPE)]).read_bytes())
        record = {"artifact_dir": str(artifact), "derived_sha256": "same"}
        with mock.patch.object(self.helper, "prepare", return_value=record), \
                mock.patch.object(self.helper, "daemon_live", return_value=True), \
                mock.patch.object(ss, "run", side_effect=ValueError("Running tasks require --force")):
            with self.assertRaisesRegex(ValueError, "^Running tasks require --force$"):
                self.helper.install()
        self.assertEqual(current.read_bytes(), original)
        self.assertEqual(self.helper.state_path.read_bytes(), previous_state)

    def test_release_version_and_explicit_compatibility(self):
        actual = subprocess.check_output([str(ROOT / "bin/zcode-centos7"), "--version"]).decode().split()[1]
        self.assertEqual(actual, self.helper.meta["tool_version"])
        self.assertEqual(self.helper.meta["candidate_zcode_versions"], ["3.16.2"])
        self.assertEqual(self.helper.meta["end_to_end_verified_zcode_versions"], ["3.16.2"])
        self.assertEqual(self.helper.meta["validation"]["windows_desktop_connection"]["status"],
                         "user-confirmed")
        self.assertEqual(self.helper.meta["validation"]["host_reboot"]["status"], "excluded-by-user")
        self.assertEqual(ss.digest(ROOT / "src/probe-3.16.2.sh"), self.helper.meta["probe_sha256"])


if __name__ == "__main__":
    unittest.main()
