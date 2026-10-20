"""Loopback sshd with ephemeral keys and an authorized-key-scoped temporary HOME."""
import contextlib
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import tempfile
import time


def client_exec_command(command):
    """Match official buildPosixShellExecCommand, including its quote spelling."""
    return "/bin/sh -c '" + command.replace("'", "'\"'\"'") + "'"


@contextlib.contextmanager
def ssh_session(home):
    directory = Path(tempfile.mkdtemp(prefix="zcode-sshd."))
    daemon = None
    try:
        subprocess.check_call(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(directory / "key")])
        (directory / "authorized_keys").write_text('environment="HOME=' + str(home) + '" ' +
                                                  (directory / "key.pub").read_text())
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        config = ["ListenAddress 127.0.0.1", "Port " + str(port), "HostKey " + str(directory / "key"),
                  "PidFile " + str(directory / "pid"), "AuthorizedKeysFile " + str(directory / "authorized_keys"),
                  "UsePAM no", "UsePrivilegeSeparation no", "StrictModes no", "PasswordAuthentication no",
                  "ChallengeResponseAuthentication no", "PermitUserEnvironment yes", "LogLevel ERROR"]
        (directory / "config").write_text("\n".join(config) + "\n")
        with (directory / "log").open("wb") as log:
            daemon = subprocess.Popen(["/usr/sbin/sshd", "-D", "-e", "-f", str(directory / "config")],
                                      stdout=log, stderr=log)
            for _ in range(50):
                if daemon.poll() is not None:
                    raise RuntimeError((directory / "log").read_text())
                try:
                    with socket.create_connection(("127.0.0.1", port), .1):
                        break
                except OSError:
                    time.sleep(.05)
            else:
                raise RuntimeError("Temporary sshd did not listen")

            def execute(command, tty=False):
                args = ["ssh", "-tt" if tty else "-T", "-p", str(port), "-i", str(directory / "key"),
                        "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                        pwd.getpwuid(os.getuid()).pw_name + "@127.0.0.1", command]
                p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
                if p.returncode:
                    raise RuntimeError(p.stderr.decode("utf-8", "replace"))
                return p.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
            yield execute
    finally:
        if daemon is not None and daemon.poll() is None:
            daemon.terminate()
            daemon.wait(timeout=5)
        shutil.rmtree(str(directory))
