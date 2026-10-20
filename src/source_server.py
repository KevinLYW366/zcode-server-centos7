#!/usr/bin/env python3
"""Prepare immutable Source Server releases and a narrowly scoped SSH probe hook."""

import argparse
import contextlib
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
METADATA = HERE / "compatibility.json" if (HERE / "compatibility.json").exists() else HERE.parent / "compatibility.json"
BEGIN = "# BEGIN zcode-centos7 Source Server probe\n"
END = "# END zcode-centos7 Source Server probe\n"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    require(not path.is_symlink(), "Refusing symbolic-link metadata: " + str(path))
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    require(isinstance(value, dict), "Expected a metadata object: " + str(path))
    return value


def atomic_write(path, data, mode=0o600):
    require(not path.is_symlink(), "Refusing symbolic-link target: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, data):
    atomic_write(path, (json.dumps(data, indent=2, sort_keys=True) + "\n").encode())


def run(args, env=None, timeout=30):
    p = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=env, timeout=timeout)
    require(p.returncode == 0, "Command failed: {}\n{}".format(
        args[0], (p.stderr or p.stdout).decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace").strip()


def tree_hash(root):
    """Match Source Server hashReleaseTree, including file modes and directories."""
    h = hashlib.sha256()

    def visit(directory):
        for path in sorted(directory.iterdir()):
            rel = path.relative_to(root).as_posix()
            if rel == ".release-integrity.json":
                continue
            require(not path.is_symlink(), "Release contains a symbolic link")
            if path.is_dir():
                h.update(("directory\0" + rel + "\0").encode())
                visit(path)
            else:
                require(path.is_file(), "Unsupported release entry")
                h.update(("file\0{}\0{}\0".format(rel, path.stat().st_mode & 0o777)).encode())
                with path.open("rb") as f:
                    for block in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(block)
    visit(root)
    return h.hexdigest()


def component_identity(root, paths):
    """Match upstream hashPaths; size is the sum of component file sizes."""
    h = hashlib.sha256()
    size = 0
    for raw in sorted(paths):
        relative = PurePosixPath(raw)
        require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in raw,
                "Unsafe component path")
        path = root / raw
        files = sorted((p for p in path.rglob("*") if p.is_file()),
                       key=lambda p: p.relative_to(root).as_posix().encode("utf-16-be")) if path.is_dir() else [path]
        for item in files:
            require(not item.is_symlink(), "Component contains a symbolic link")
            h.update((item.relative_to(root).as_posix() + "\0").encode())
            size += item.stat().st_size
            with item.open("rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
    return h.hexdigest(), size


def extract_archive(archive, destination):
    with tarfile.open(str(archive), "r:gz") as t:
        members = t.getmembers()
        seen = set()
        for m in members:
            parts = PurePosixPath(m.name).parts
            require(parts and parts[0] == "zcode-server-linux-x64" and ".." not in parts
                    and not m.name.startswith("/") and "\\" not in m.name
                    and not any(ord(c) < 32 for c in m.name), "Unsafe archive path")
            require(m.isfile() or m.isdir(), "Archive links and special files are not supported")
            normalized = str(PurePosixPath(m.name))
            require(normalized not in seen, "Duplicate archive entry")
            seen.add(normalized)
            require(not m.mode & 0o6000, "Set-ID archive member")
        t.extractall(str(destination), members=members)
    return destination / "zcode-server-linux-x64"


def pack_archive(root, destination):
    # Fixed timestamps and owners make repeated preparation reproducible.
    with destination.open("wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0, compresslevel=6) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as t:
            for p in [root] + sorted(root.rglob("*")):
                info = t.gettarinfo(str(p), arcname="zcode-server-linux-x64" +
                                    ("/" + p.relative_to(root).as_posix() if p != root else ""))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                info.pax_headers = {}
                if p.is_file():
                    with p.open("rb") as source:
                        t.addfile(info, source)
                else:
                    t.addfile(info)


class SourceServer:
    def __init__(self, args):
        self.args = args
        raw = Path(args.zcode_root).absolute()
        require(str(raw) != "/" and not any(c in str(raw) for c in '\n\r"\\'), "Unsafe ZCode root")
        require(not raw.is_symlink(), "Symbolic-link ZCode root is not supported")
        self.root = raw.resolve()
        self.home = self.root.parent
        self.server = self.root / "server"
        self.runtime_root = self.root / "centos7-runtime"
        self.work = self.runtime_root / "source-server"
        self.state_path = self.work / "state.json"
        self.meta = read_json(METADATA)
        self.release = self.meta["source_server"]
        self.env = dict(os.environ, HOME=str(self.home), ZCODE_DATA_BASE_DIR=str(self.root),
                        ZCODE_SERVER_ROOT=str(self.server))

    @contextlib.contextmanager
    def lock(self):
        for path in (self.runtime_root, self.runtime_root / "releases", self.runtime_root / "backups",
                     self.work, self.work / "artifacts", self.work / "support", self.server,
                     self.server / "releases"):
            require(not path.is_symlink(), "Refusing symbolic-link installation directory: " + str(path))
        self.work.mkdir(parents=True, exist_ok=True)
        lock = self.work / ".lock"
        lock.mkdir()  # Never steal a lock from another process.
        try:
            yield
        finally:
            lock.rmdir()

    def runtime(self, directory, expected=None):
        directory = Path(directory)
        require(directory.resolve() == directory and not directory.is_symlink(), "Unsafe runtime path")
        require(str(directory).startswith(str(self.runtime_root / "releases") + "/"), "Runtime is outside private releases")
        manifest = {}
        for line in (directory / "manifest.env").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                manifest[k] = v
        require(manifest["ARCH"] == "x86_64", "Unsupported runtime architecture")
        fingerprint = digest(directory / "SHA256SUMS")
        accepted = [self.meta["runtime"]["checksum_manifest_sha256"]] + self.meta["runtime"].get("legacy_checksum_manifest_sha256", [])
        require(manifest["RUNTIME_ID"] == self.meta["runtime"]["id"] and
                fingerprint in accepted, "Unrecognized private runtime")
        if expected:
            require(fingerprint == expected, "Runtime checksum manifest changed")
        for line in (directory / "SHA256SUMS").read_text().splitlines():
            sha, name = line.split(None, 1)
            name = name.lstrip(" *")
            p = directory / name
            require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
                    and p.resolve() == p and p.is_file(), "Unsafe runtime checksum entry")
            require(digest(p) == sha, "Runtime checksum failure: " + name)
        for key in ("LOADER", "LIB_DIR", "PATCHELF"):
            p = directory / manifest[key]
            require(p.resolve() == p and directory in p.parents, "Unsafe runtime manifest path")
        return manifest, fingerprint

    def install_runtime(self):
        source = self.args.runtime_dir
        if not source:
            state = read_json(self.state_path) if self.state_path.exists() else {}
            source = state.get("runtime_dir") or str(HERE.parent / "runtime")
        cli = str(Path(self.args.cli).resolve())
        command = 'source "$1"; ZCODE_ROOT=$2; initialize_paths; acquire_lock; install_runtime "$3"'
        fields = run(["bash", "-c", command, "zcode-runtime", cli, self.root, source]).split("\t")
        require(len(fields) == 4, "Unexpected runtime installer output")
        directory, loader, lib, patcher = map(Path, fields)
        manifest, fingerprint = self.runtime(directory)
        return directory, loader, lib, patcher, manifest, fingerprint

    def check_programs(self, release_dir, runtime_dir, native=False):
        node = release_dir / "runtime/node"
        require(run([node, "--version"], self.env) == "v22.16.0", "Unexpected Node version")
        script = 'const fs=require("fs"),c=require("child_process");' \
                 'if(!fs.readFileSync("/proc/self/maps","utf8").includes(process.argv[1]))process.exit(70);' \
                 'if(c.execFileSync("/bin/sh",["-c","printf ok"],{encoding:"utf8"})!=="ok")process.exit(71);' \
                 'if(c.execFileSync("/bin/sh",["-c","cat /proc/$$/maps"],{encoding:"utf8"}).includes(process.argv[1]))process.exit(72);'
        run([node, "-e", script, runtime_dir], self.env)
        for relative in ("runtime/tools/bfs/bfs", "runtime/tools/ugrep/ugrep", "runtime/tools/ripgrep/rg"):
            run([release_dir / relative, "--version"], self.env)
        if native:
            for module in ("node-pty/prebuilds/linux-x64/pty.node", "koffi/build/koffi/linux_x64/koffi.node",
                           "unsafe-pointer/prebuilds/linux-x64/unsafe-pointer.glibc.node"):
                run([node, "-e", "require(process.argv[1])", release_dir / "runtime/node_modules" / module], self.env)
            terminal = ('const p=require(process.argv[1]).spawn("/bin/sh",["-c","printf pty-ok"],{env:process.env});'
                        'let text="";p.onData(x=>text+=x);p.onExit(e=>process.exit(e.exitCode===0&&text.includes("pty-ok")?0:1));'
                        'setTimeout(()=>{p.kill();process.exit(2)},5000).unref();')
            run([node, "-e", terminal, release_dir / "runtime/node_modules/node-pty"], self.env)
        require(run([release_dir / "bin/zcode", "--version"], self.env) == "3.16.2", "Unexpected Server CLI version")

    def prepare(self):
        require(platform.system() == "Linux" and platform.machine() == "x86_64", "Only Linux x86-64 is supported")
        archive = Path(self.args.archive).resolve()
        require(archive.is_file() and archive.stat().st_size == self.release["size_bytes"]
                and digest(archive) == self.release["sha256"], "Unsupported official archive size or SHA-256")
        directory, loader, lib, patcher, manifest, fingerprint = self.install_runtime()
        identity = hashlib.sha256((self.release["sha256"] + str(directory) + fingerprint +
                                   str(self.root) + self.meta["tool_version"] +
                                   digest(HERE / "source_server.py")).encode()).hexdigest()
        destination = self.work / "artifacts" / identity
        if destination.exists():
            record = read_json(destination / "derivation.json")
            require(digest(destination / "compatible.tar.gz") == record["derived_sha256"], "Derived archive changed")
            return record
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".prepare-", dir=str(destination.parent)))
        try:
            extracted = temporary / "extract"
            extracted.mkdir()
            root = extract_archive(archive, extracted)
            runtime_manifest = read_json(root / "manifest.json")
            require(runtime_manifest["appVersion"] == "3.16.2" and runtime_manifest["target"] == "linux-x64", "Manifest target mismatch")
            for relative, sha in self.release["executables"].items():
                p = root / relative
                require(digest(p) == sha, "Unknown executable: " + relative)
                before = [line for line in run(["readelf", "-d", p]).splitlines()
                          if "(RPATH)" in line or "(RUNPATH)" in line]
                run([loader, "--library-path", lib, patcher, "--set-interpreter", loader, p])
                after = [line for line in run(["readelf", "-d", p]).splitlines()
                         if "(RPATH)" in line or "(RUNPATH)" in line]
                require(before == after, "Patching changed ELF RPATH/RUNPATH")
            for component in runtime_manifest["components"]:
                component["sha256"], component["sizeBytes"] = component_identity(root, component["paths"])
                component["archivePath"] = "components/linux-x64/{}-{}.tar.gz".format(component["id"], component["sha256"])
            write_json(root / "manifest.json", runtime_manifest)
            # Manifest permissions are included in the installer's release-tree hash.
            os.chmod(str(root / "manifest.json"), 0o644)
            self.check_programs(root, directory, native=True)
            pack_archive(root, temporary / "compatible.tar.gz")
            record = {"schema_version": 1, "tool_version": self.meta["tool_version"], "zcode_version": "3.16.2",
                      "official_sha256": self.release["sha256"], "derived_sha256": digest(temporary / "compatible.tar.gz"),
                      "artifact_dir": str(destination), "runtime_dir": str(directory), "runtime_id": manifest["RUNTIME_ID"],
                      "runtime_checksums_sha256": fingerprint, "loader": str(loader), "zcode_root": str(self.root)}
            shutil.rmtree(str(extracted))
            write_json(temporary / "derivation.json", record)
            os.rename(str(temporary), str(destination))
            return record
        finally:
            if temporary.exists():
                shutil.rmtree(str(temporary))

    def verify_record(self, record, programs=True):
        require(digest(HERE / "probe-3.16.2.sh") == self.meta["probe_sha256"], "Probe fixture checksum mismatch")
        require(record["schema_version"] == 1 and record["zcode_root"] == str(self.root)
                and record["official_sha256"] == self.release["sha256"]
                and record["tool_version"] == self.meta["tool_version"], "Unrecognized compatibility state")
        directory = Path(record["runtime_dir"])
        manifest, _ = self.runtime(directory, record["runtime_checksums_sha256"])
        require(record["loader"] == str(directory / manifest["LOADER"]), "Runtime loader changed")
        current = read_json(self.server / "current.json")
        require(current["version"] == "3.16.2" and current["archiveSha256"] == record["derived_sha256"], "Current release differs from compatibility state")
        release_dir = Path(current["releaseDir"])
        require(release_dir.resolve() == release_dir and self.server / "releases" in release_dir.parents, "Unsafe current release directory")
        integrity = read_json(release_dir / ".release-integrity.json")
        require(integrity["archiveSha256"] == record["derived_sha256"]
                and integrity["contentSha256"] == tree_hash(release_dir), "Installed release integrity failure")
        for relative in self.release["executables"]:
            require("Requesting program interpreter: " + record["loader"] + "]" in
                    run(["readelf", "-l", release_dir / relative]), "Executable no longer uses private loader")
        if programs:
            self.check_programs(release_dir, directory)
        return release_dir

    def bashrc_without_block(self):
        bashrc = self.home / ".bashrc"
        require(not bashrc.is_symlink(), "Refusing symbolic-link .bashrc")
        data = bashrc.read_bytes() if bashrc.exists() else b""
        begin, end = BEGIN.encode(), END.encode()
        require(data.count(begin) == data.count(end) and data.count(begin) <= 1, "Ambiguous managed .bashrc block")
        if begin in data:
            start, finish = data.index(begin), data.index(end)
            require(finish > start, "Malformed managed .bashrc block")
            data = data[:start] + data[finish + len(end):]
        return bashrc, data

    def enable_hook(self):
        require(self.root.name == ".zcode", "SSH probe requires a .zcode root under the SSH HOME")
        support = self.work / "support"
        support.mkdir(exist_ok=True)
        for source in (HERE / "source_server.py", HERE / "probe-3.16.2.sh", METADATA):
            if source.name == "probe-3.16.2.sh":
                require(digest(source) == self.meta["probe_sha256"], "Probe fixture checksum mismatch")
            atomic_write(support / source.name, source.read_bytes())
        hook = self.work / "ssh-probe-hook.bash"
        atomic_write(hook, (HERE / "ssh_probe_hook.bash").read_bytes())
        bashrc, clean = self.bashrc_without_block()
        backup = self.work / "backups" / ("bashrc." + hashlib.sha256(clean).hexdigest())
        if not backup.exists():
            atomic_write(backup, clean)
        block = (BEGIN + "if [ -n \"${BASH_VERSION-}\" ] && [ -r " + shlex.quote(str(hook)) + " ]; then\n" +
                 "    . " + shlex.quote(str(hook)) + "\nfi\n" + END).encode()
        mode = stat.S_IMODE(bashrc.stat().st_mode) if bashrc.exists() else 0o644
        atomic_write(bashrc, block + clean, mode)

    def install(self):
        require(self.root.name == ".zcode", "Install into <SSH HOME>/.zcode; use prepare for other roots")
        # Check profile editability before invoking the upstream installer.
        self.bashrc_without_block()
        record = self.prepare()
        artifact = Path(record["artifact_dir"]) / "compatible.tar.gz"
        bootstrap = Path(tempfile.mkdtemp(prefix=".bootstrap-", dir=str(self.work)))
        previous = (self.server / "current.json").read_bytes() if (self.server / "current.json").exists() else None
        previous_state = self.state_path.read_bytes() if self.state_path.exists() else None
        was_live = self.daemon_live()
        try:
            root = extract_archive(artifact, bootstrap)
            run([root / "bin/zcode", "update", "--from-archive", artifact,
                 "--server-root", self.server, "--json"], self.env, timeout=180)
            self.verify_record(record)
            record["status"] = "installed"
            write_json(self.state_path, record)
            self.enable_hook()
            return record
        except Exception as failure:
            if previous is not None:
                atomic_write(self.work / "previous-current.json", previous)
            try:
                current_path = self.server / "current.json"
                current = read_json(current_path) if current_path.exists() else None
                old_current = json.loads(previous.decode("utf-8")) if previous is not None else None
                changed = current and (old_current is None or any(
                    current.get(key) != old_current.get(key) for key in ("archiveSha256", "releaseDir")))
                if changed and current.get("archiveSha256") == record["derived_sha256"]:
                    if not was_live and not self.daemon_live():
                        # No running process owns this pointer; undo our offline activation.
                        if previous is None:
                            current_path.unlink()
                        else:
                            atomic_write(current_path, previous)
                    elif previous_state is not None:
                        old = json.loads(previous_state.decode("utf-8"))
                        old_artifact = Path(old["artifact_dir"]) / "compatible.tar.gz"
                        require(digest(old_artifact) == old["derived_sha256"], "Rollback archive changed")
                        old_bootstrap = bootstrap / "rollback"
                        old_bootstrap.mkdir()
                        old_root = extract_archive(old_artifact, old_bootstrap)
                        run([old_root / "bin/zcode", "update", "--from-archive", old_artifact,
                             "--server-root", self.server, "--json"], self.env, timeout=180)
                    else:
                        raise ValueError("Live rollback needs a previously prepared compatible archive")
                if previous_state is not None:
                    atomic_write(self.state_path, previous_state)
                elif self.state_path.exists():
                    self.state_path.unlink()
            except (ValueError, OSError, KeyError, subprocess.SubprocessError) as rollback:
                raise ValueError("{}; recovery could not complete: {}. Prior manifest: {}".format(
                    failure, rollback, self.work / "previous-current.json")) from failure
            raise
        finally:
            shutil.rmtree(str(bootstrap))

    def daemon_live(self):
        path = self.server / "run/status.json"
        if not path.exists():
            return False
        try:
            status = read_json(path)
            pid = status.get("pid")
            if not isinstance(pid, int) or pid <= 0:
                return status.get("state") not in ("stopped", "stop-failed")
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except (ValueError, OSError):
            return True  # Uncertain ownership must not permit pointer-only rollback.

    def status(self, probe=False):
        try:
            record = read_json(self.state_path)
            require(record.get("status") == "installed", "Compatibility is not enabled")
            self.verify_record(record)
            if probe:
                output = run([record["loader"], "--library-path", str(Path(record["loader"]).parent),
                              "/usr/bin/getconf", "GNU_LIBC_VERSION"])
                parts = output.split()
                require(len(parts) == 2 and parts[0] == "glibc" and
                        tuple(map(int, parts[1].split("."))) >= (2, 28), "Private glibc does not satisfy probe")
                print(output)
            else:
                print(json.dumps({"ready": True, "state": record}, sort_keys=True))
            return True
        except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
            if not probe:
                print(json.dumps({"ready": False, "error": str(error)}, sort_keys=True))
            return False

    def verify(self):
        record = read_json(self.state_path)
        require(record.get("status") == "installed", "Compatibility is not installed")
        self.verify_record(record)
        if self.args.handshake:
            # A caller must opt in because this can start a persistent daemon.
            run([self.server / "bin/zcode", "serve", "--daemon", "--server-root", self.server, "--json"], self.env, timeout=60)
            status = json.loads(run([self.server / "bin/zcode", "status", "--server-root", self.server, "--json"], self.env))
            require(status.get("state") == "ready", "Source Server did not become ready")
        print("Source Server compatibility verified" + ("; daemon ready" if self.args.handshake else " (no daemon started)"))

    def uninstall(self):
        bashrc, clean = self.bashrc_without_block()
        if bashrc.exists() and clean != bashrc.read_bytes():
            atomic_write(bashrc, clean, stat.S_IMODE(bashrc.stat().st_mode))
        if self.state_path.exists():
            record = read_json(self.state_path)
            record["status"] = "disabled"
            write_json(self.state_path, record)
        print("SSH probe hook disabled; server, private runtime, and backups retained")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default=str(HERE.parent / "bin/zcode-centos7"))
    parser.add_argument("--zcode-root", default=str(Path.home() / ".zcode"))
    parser.add_argument("--runtime-dir")
    parser.add_argument("--handshake", action="store_true")
    parser.add_argument("command", choices=["prepare", "install", "repair", "verify", "status", "uninstall"])
    parser.add_argument("--archive")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--probe-getconf", action="store_true", help=argparse.SUPPRESS)
    # Accept --handshake on either side of the subcommand.
    args = parser.parse_args()
    try:
        helper = SourceServer(args)
        if args.command == "status":
            ok = helper.status(args.probe_getconf)
            return 0 if ok or not args.probe_getconf else 1
        if args.command == "verify":
            helper.verify()
        else:
            require(args.command == "uninstall" or args.archive, "--archive is required")
            with helper.lock():
                if args.command == "prepare":
                    print(json.dumps(helper.prepare(), sort_keys=True))
                elif args.command in ("install", "repair"):
                    print(json.dumps(helper.install(), sort_keys=True))
                else:
                    helper.uninstall()
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        if not args.probe_getconf:
            print("zcode-centos7 source-server: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
