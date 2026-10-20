"""Live lifecycle checks restricted to an integration test's disposable root."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import time
import uuid
from unittest import mock

from ssh_harness import client_exec_command, ssh_session


def control(zroot, command):
    request_id = str(uuid.uuid4())
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(15)
        connection.connect(str(zroot / "server/run/control.sock"))
        connection.sendall((json.dumps({"id": request_id, "command": command}) + "\n").encode())
        with connection.makefile("rb") as stream:
            response = json.loads(stream.readline())
    assert response["id"] == request_id and response["ok"], response
    return response["result"]


def assert_active(zroot):
    current = json.loads((zroot / "server/current.json").read_text())
    identity = control(zroot, "runtime-identity")
    for key in ("supervisorReleaseId", "activeReleaseId", "coreReleaseId"):
        assert identity[key] == current["releaseId"], (key, identity, current["releaseId"])
    assert control(zroot, "status")["state"] == "ready"
    return current


def check_lifecycle(home, zroot, args, archive, installed, call, owned_processes):
    # This is test-only fault injection, never a production CLI option. Changing
    # gzip MTIME yields a new archive identity with byte-identical tar payload.
    helper_path = Path(args.cli).resolve().parent.parent / "src/source_server.py"
    spec = importlib.util.spec_from_file_location("lifecycle_source_server", str(helper_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    helper = module.SourceServer(argparse.Namespace(
        zcode_root=str(zroot), runtime_dir=args.runtime_dir, cli=args.cli, archive=archive))
    helper.env["ZCODE_SERVER_SKIP_SERVICE_REGISTRATION"] = "1"
    original_current = assert_active(zroot)
    original_state = helper.state_path.read_bytes()
    original_profile = (home / ".bashrc").read_bytes()
    original_archive = Path(installed["artifact_dir"]) / "compatible.tar.gz"
    original_bytes = original_archive.read_bytes()
    candidate_dir = helper.work / "artifacts/acceptance-next"
    candidate_dir.mkdir()
    candidate_bytes = bytearray(original_bytes)
    assert candidate_bytes[:2] == b"\x1f\x8b"
    candidate_bytes[4:8] = b"\x01\x00\x00\x00"
    (candidate_dir / "compatible.tar.gz").write_bytes(candidate_bytes)
    candidate = dict(installed, artifact_dir=str(candidate_dir),
                     derived_sha256=hashlib.sha256(candidate_bytes).hexdigest())
    assert candidate["derived_sha256"] != installed["derived_sha256"]

    def fail_after_activation(record, *unused_args, **unused_kwargs):
        activated = assert_active(zroot)
        assert activated["archiveSha256"] == candidate["derived_sha256"]
        raise ValueError("Acceptance fault after live activation")

    with helper.lock(), mock.patch.object(helper, "prepare", return_value=candidate), \
            mock.patch.object(helper, "verify_record", side_effect=fail_after_activation):
        try:
            helper.install()
        except ValueError as error:
            assert str(error) == "Acceptance fault after live activation", str(error)
        else:
            raise AssertionError("Injected live update failure was not reported")
    assert assert_active(zroot)["archiveSha256"] == original_current["archiveSha256"]
    assert helper.state_path.read_bytes() == original_state
    assert (home / ".bashrc").read_bytes() == original_profile
    helper.verify_record(json.loads(original_state.decode()))
    print("Live activation failure restored previous release, running identity, state, and hook", flush=True)

    # A missing/corrupt recovery archive must produce a visible incomplete
    # recovery, followed by a real, explicit CLI repair after restoring it.
    original_archive.write_bytes(b"acceptance-corrupt-recovery-archive")
    try:
        with helper.lock(), mock.patch.object(helper, "prepare", return_value=candidate), \
                mock.patch.object(helper, "verify_record", side_effect=fail_after_activation):
            try:
                helper.install()
            except ValueError as error:
                assert "recovery could not complete" in str(error), str(error)
                assert "Rollback archive changed" in str(error), str(error)
            else:
                raise AssertionError("Broken recovery archive was not reported")
        assert assert_active(zroot)["archiveSha256"] == candidate["derived_sha256"]
        report = json.loads(call("status", "--json"))
        assert not report["ready"], report
        assert json.loads((helper.work / "previous-current.json").read_text())["archiveSha256"] == original_current["archiveSha256"]
    finally:
        original_archive.write_bytes(original_bytes)
    call("repair", "--archive", archive)
    assert assert_active(zroot)["archiveSha256"] == original_current["archiveSha256"]
    assert json.loads(call("status", "--json"))["ready"]
    print("Incomplete live recovery was reported; explicit repair restored readiness", flush=True)

    # Crash only processes identified by this test's unique root and UID. Keep
    # run files to exercise recovery from stale PID/lock/socket state.
    before = control(zroot, "status")["pid"]
    processes = owned_processes()
    assert before in processes
    for pid in processes:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    for _ in range(50):
        if not owned_processes():
            break
        time.sleep(.1)
    assert not owned_processes(), "Temporary server processes survived crash injection"
    probe_path = helper_path.parent / "probe-3.16.2.sh"
    with ssh_session(home) as ssh:
        assert "__ZCODE_PROBE_LIBC__\nglibc 2.44\n" in ssh(client_exec_command(probe_path.read_text().rstrip("\n")))
        launcher = zroot / "server/bin/zcode"
        command = 'ZCODE_SERVER_SKIP_SERVICE_REGISTRATION=1 "{}" serve --daemon --server-root "{}" --json'.format(launcher, zroot / "server")
        assert json.loads(ssh(client_exec_command(command)))["state"] == "ready"
    after = control(zroot, "status")["pid"]
    assert after != before
    assert assert_active(zroot)["archiveSha256"] == original_current["archiveSha256"]
    assert json.loads(call("status", "--json"))["ready"]
    print("Crash/stale-state recovery and daemon survival after SSH disconnect verified (not a host reboot)", flush=True)
