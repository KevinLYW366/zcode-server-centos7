#!/usr/bin/env python3
"""Opt-in vendor-archive integration; all installations use a disposable HOME."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import tarfile
import time

from ssh_harness import client_exec_command, ssh_session
from lifecycle_acceptance import check_lifecycle

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--cli", default=str(ROOT / "bin/zcode-centos7"))
    args = parser.parse_args()
    temporary = Path(tempfile.mkdtemp(prefix="zcode-source-e2e."))
    home = temporary / "home"
    home.mkdir()
    zroot = home / ".zcode"
    cli = [str(Path(args.cli).resolve()), "--zcode-root", str(zroot),
           "--runtime-dir", str(Path(args.runtime_dir).resolve()), "source-server"]
    archive = str(Path(args.archive).resolve())

    def call(*arguments):
        env = dict(os.environ, ZCODE_SERVER_SKIP_SERVICE_REGISTRATION="1")
        p = subprocess.run(cli + list(arguments), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=env, timeout=240)
        if p.returncode:
            raise RuntimeError(p.stderr.decode("utf-8", "replace"))
        return p.stdout.decode("utf-8", "replace").strip()

    def stop():
        launcher = zroot / "server/bin/zcode"
        if launcher.exists():
            env = dict(os.environ, HOME=str(home), ZCODE_DATA_BASE_DIR=str(zroot))
            subprocess.run([str(launcher), "stop", "--server-root", str(zroot), "--json"],
                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)

    def owned_processes():
        result = []
        for cmdline in Path("/proc").glob("[0-9]*/cmdline"):
            try:
                if cmdline.stat().st_uid == os.getuid() and str(temporary).encode() in cmdline.read_bytes():
                    result.append(int(cmdline.parent.name))
            except OSError:
                pass
        return result

    try:
        # Existing legacy state and user profile content must survive.
        (home / ".bashrc").write_text("# existing user configuration\n")
        (zroot / "centos7-runtime").mkdir(parents=True)
        legacy = zroot / "centos7-runtime/state.json"
        legacy.write_text('{"legacy":true}\n')
        prepared = json.loads(call("prepare", "--archive", archive))
        print("Prepared verified compatible archive", flush=True)
        again = json.loads(call("prepare", "--archive", archive))
        assert prepared == again
        assert not (zroot / "server/current.json").exists()
        installed = json.loads(call("install", "--archive", archive))
        print("Installed and verified Source Server", flush=True)
        current = json.loads((zroot / "server/current.json").read_text())
        actual_manifest = json.loads((Path(current["releaseDir"]) / "manifest.json").read_text())
        with tarfile.open(archive, "r:gz") as original:
            original_manifest = json.load(original.extractfile("zcode-server-linux-x64/manifest.json"))
        changed = [a["id"] for a, b in zip(original_manifest["components"], actual_manifest["components"]) if a != b]
        assert changed == ["node-runtime", "native-search-tools"], changed
        assert installed["derived_sha256"] == prepared["derived_sha256"]
        call("verify")
        assert json.loads(call("status", "--json"))["ready"]
        probe = (ROOT / "src/probe-3.16.2.sh").read_text().rstrip("\n")
        wrapped_probe = client_exec_command(probe)
        system_version = subprocess.check_output(["/usr/bin/getconf", "GNU_LIBC_VERSION"]).decode().strip()
        with ssh_session(home) as ssh:
            for command in (probe, wrapped_probe):
                started = time.monotonic()
                output = ssh(command)
                assert "__ZCODE_PROBE_LIBC__\nglibc 2.44\n" in output, output
                assert "__ZCODE_PROBE_INSTALLED__\n1\n" in output
                assert time.monotonic() - started < 10, "Probe exceeded client startup budget"
            assert ssh("getconf GNU_LIBC_VERSION") == system_version
            assert ssh(client_exec_command("getconf GNU_LIBC_VERSION")) == system_version
            assert system_version in ssh(probe + "; printf changed")
            assert system_version in ssh(client_exec_command(probe + "; printf changed"))
            assert system_version in ssh(wrapped_probe + "; printf changed")
            assert ssh("getconf LONG_BIT") == "64"
            assert ssh(client_exec_command("getconf LONG_BIT")) == "64"
            assert ssh("getconf GNU_LIBC_VERSION", tty=True) == system_version
            assert system_version in ssh(wrapped_probe, tty=True)
            assert ssh("bash --noprofile --rcfile \"$HOME/.bashrc\" -ic 'getconf GNU_LIBC_VERSION'") == system_version
            current_path = zroot / "server/current.json"
            original_current = current_path.read_bytes()
            try:
                stale = json.loads(original_current.decode("utf-8"))
                stale["archiveSha256"] = "0" * 64
                current_path.write_text(json.dumps(stale))
                assert system_version in ssh(probe), "Stale installation state was accepted"
                assert system_version in ssh(wrapped_probe), "Wrapped probe accepted stale state"
            finally:
                current_path.write_bytes(original_current)
            release = Path(json.loads((zroot / "server/current.json").read_text())["releaseDir"])
            target = release / "runtime/tools/bfs/bfs"
            mode = target.stat().st_mode & 0o777
            target.chmod(0o600)
            assert system_version in ssh(probe), "Corrupt release was accepted"
            assert system_version in ssh(wrapped_probe), "Wrapped probe accepted corrupt release"
            target.chmod(mode)
            runtime_lib = Path(installed["runtime_dir"]) / "lib/libutil.so.1"
            original = runtime_lib.read_bytes()
            try:
                runtime_lib.write_bytes(b"corrupt")
                assert system_version in ssh(probe), "Corrupt runtime was accepted"
                assert system_version in ssh(wrapped_probe), "Wrapped probe accepted corrupt runtime"
            finally:
                runtime_lib.write_bytes(original)
        print("Direct and official wrapped SSH probes and corruption fallback verified", flush=True)
        call("install", "--archive", archive)  # Exercise immutable release reuse.
        call("verify", "--handshake")
        call("verify", "--handshake")  # Existing daemon/reconnect path.
        print("Repeated install and daemon handshake verified", flush=True)
        check_lifecycle(home, zroot, args, archive, installed, call, owned_processes)
        stop()
        (home / ".bashrc").write_text((home / ".bashrc").read_text() + "# later user edit\n")
        call("uninstall")
        assert (home / ".bashrc").read_text() == "# existing user configuration\n# later user edit\n"
        assert legacy.read_text() == '{"legacy":true}\n'
        with ssh_session(home) as ssh:
            assert system_version in ssh(probe)
            assert system_version in ssh(wrapped_probe)
    finally:
        try:
            stop()
        finally:
            # The vendor stop can leave provider workers; these are exclusively ours.
            for sig in (signal.SIGTERM, signal.SIGKILL):
                for pid in owned_processes():
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        pass
                for _ in range(50):
                    if not owned_processes():
                        break
                    time.sleep(.1)
            shutil.rmtree(str(temporary))
    print("Source Server archive, SSH probe, fallback, integrity, daemon, and uninstall checks passed")
    print("Automated checks do not validate Windows desktop or host reboot acceptance; see compatibility.json")


if __name__ == "__main__":
    main()
