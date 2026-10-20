# ZCode 3.16.2 Compatibility: Development and Release Plan

- Date: 2026-10-20
- Status: Stable release; agreed acceptance scope complete, host reboot excluded by the user
- Current tool version: `0.2.0`
- Source Server release line: `0.2.x`

This document records the Windows ZCode 3.16.2 connection failure on CentOS 7,
describes the implemented remote-only compatibility workflow, and establishes
how releases declare ZCode compatibility. Automated remote tests pass. The user
confirmed a real Windows ZCode 3.16.2 connection on 2026-10-20 after applying
the SSH command-wrapper fix, followed by desktop project and disconnect/task
checks. Isolated live rollback and crash recovery also passed. Host reboot
was explicitly excluded by the user and was not performed.

## 1. Problems Encountered

### 1.1 The desktop client rejects the system before starting Node

The Windows 3.16.2 client reports:

```text
Remote glibc 2.17 is older than glibc 2.28 required by ZCode Source Server.
Use a Linux system with glibc 2.28 or later, such as RHEL 8+,
Ubuntu 20.04+ or Debian 10+.
```

Inspection of the official Windows installation package located this check in
`resources/app.asar`, at `out/host/index.js`. The retained function names show
the following sequence:

1. `buildSourceServerProbeCommand` adds
   `getconf GNU_LIBC_VERSION 2>/dev/null` to the SSH probe.
2. `readSourceServerProbeSections` reads its `LIBC` output section.
3. `assertSupportedGlibc` compares the Linux glibc version with a hardcoded
   `[2, 28]` minimum and throws `SourceServerProbeEnvironmentError` if lower.
4. `probeSourceServer` performs this check before deciding whether Source
   Server is already installed.

The affected host returns `glibc 2.17`. The probe does not test the patched
Node executable or inspect its private ELF interpreter. Consequently,
preinstalling a working Node does not satisfy the desktop check, and rerunning
the current `repair` command cannot resolve this error.

The corresponding public source module is
`packages/server/src/source-server/sourceServerProbe.ts`. The public source
snapshot inspected during diagnosis did not contain this added glibc check;
the behavior above was confirmed from the actual 3.16.2 Windows package.

### 1.2 Source Server uses a different installation and startup layout

The existing tool has one fixed patch target:

```text
~/.zcode/server/node
```

That matches the legacy startup chain:

```text
Windows ZCode -> SSH -> server/node -> server/zcode-server.cjs
```

The 3.16.2 distribution instead contains:

```text
zcode-server-linux-x64/
  bin/zcode
  manifest.json
  runtime/node
  runtime/server-cli.js
  runtime/server-core.js
  runtime/zcode.cjs
  runtime/node_modules/
  runtime/tools/
```

Its archive launcher runs `runtime/node` to start the Server CLI. During first
installation, the desktop extracts a bootstrap directory and invokes that
launcher to apply the archive. After installation, the stable launcher at
`~/.zcode/server/bin/zcode` reads `current.json` and starts Node from
`~/.zcode/server/releases/<releaseId>/runtime/node`.

Both bootstrap execution and execution from an installed release require
compatibility handling. Updating only the old `server/node` path leaves both
new paths uncovered.

### 1.3 Release contents are checked for integrity

The shipped `runtime/server-cli.js` implements
`assertExistingReleaseMatches`. When an existing release directory is reused
during installation or promotion, it hashes the release tree and compares it
with `.release-integrity.json` and the expected release identity.

Patching an already installed immutable release in place can therefore cause
`Existing immutable release conflict` during a later reinstall or update.
This is a reuse/install check; the analysis did not establish that every
server startup hashes the entire release.

### 1.4 Native dependencies changed, but the ABI baseline did not increase

Static ELF inspection compared the 3.16.2 Linux x64 archive with the existing
3.15.3 installation. The relevant results are:

| Component | Highest GLIBC requirement | Highest GLIBCXX requirement | Comparison with the old installation |
|---|---|---|---|
| Node v22.16.0 | 2.28 | 3.4.21 | Byte-identical to the old unpatched backup |
| `node-pty` / `pty.node` | 2.28 | 3.4.22 | Same binary, different package location |
| `koffi` 2.15.6, Linux x64/glibc module | 2.28 | 3.4.22 | Newly packaged relative to the old installation |
| `unsafe-pointer` 0.2.0, Linux x64/glibc module | 2.14 | None | Newly packaged |
| OpenTUI 0.2.15 / `libopentui.so` | 2.17 | None | Newly packaged |
| `bfs` | 2.28 | None | Same binary |
| `ugrep` | 2.28 | None | Same binary |
| `ripgrep` / `rg` | No versioned glibc requirement | None | Same binary; no `DT_NEEDED` entries |

The applicable new ELF files introduce no additional system-library names
beyond the old Node/pty dependency set. The package also contains musl and
other-architecture alternatives; these are not requirements for this x64
glibc host. Packaged optional modules are not necessarily loaded on every
Source Server startup.

The following limited runtime checks passed without installing the new server:

- The new Node printed `v22.16.0` when invoked through the existing private
  loader with its library directory explicitly supplied.
- The currently patched Node loaded the new package's `pty.node`, Linux
  x64/glibc `koffi.node`, and Linux x64/glibc `unsafe-pointer` module.

The new unpatched Node failed against the system libraries. The unchanged
`bfs` and `ugrep` executables also failed with missing `GLIBC_2.28`. These
search-tool failures are an existing coverage gap, not a new ABI increase.
Module loading alone does not verify terminal creation, FFI operations,
OpenTUI behavior, or a complete remote connection.

## 2. Implemented Remote-Only Solution

### 2.1 Execution environment and isolation

The supported target is Windows x64 ZCode **3.16.2**, connecting over SSH to
CentOS 7 x86-64 using Bash. The Windows application and its ASAR are unchanged.
Python 3.6+, Bash, timeout, GNU tar, readelf, and checksum utilities are required
on the remote host. The included private runtime is documented in
[USING_VSCODE_RUNTIME.md](USING_VSCODE_RUNTIME.md).

The legacy commands and their `state.json` remain separate. Source Server
artifacts, installation records, hook code, and profile backups live under
`~/.zcode/centos7-runtime/source-server/`.

New bundles require the canonical runtime checksum manifest. An explicitly
listed legacy manifest is also accepted for existing installations: its
executables and libraries were compared byte-for-byte with the canonical
runtime; only the license notice text differs. Every listed file is still
verified, and the selected manifest fingerprint is pinned in local state.
Unlisted runtime manifests are refused.

The previous proposal treated a Windows adapter as necessary. Further
inspection established that the production desktop uses the installed server
version for this reconnect path; archive identity comparison is enabled for
the development content-addressed policy. Preinstallation plus the remote
probe hook therefore provides the supported route without changing the client.
The development policy is not supported by this release.

### 2.2 Exact SSH probe matching

Installation adds a marked block at the top of the SSH user's `.bashrc` so it
runs before possible non-interactive early returns. The sourced hook produces
no startup output. It defines a shell-local `getconf` function only when:

- The shell is non-interactive and has `SSH_CONNECTION`, without `SSH_TTY`.
- `BASH_EXECUTION_STRING` exactly matches `src/probe-3.16.2.sh` or the official
  SSH backend's `/bin/sh -c` wrapper around it. The wrapper uses the exact
  `quotePosixShellArg` single-quote spelling. Marker substrings alone are
  insufficient.

The original candidate tested only the inner probe. A real desktop attempt
still returned glibc 2.17 because `buildPosixShellExecCommand` wraps that probe
before `SSHBackend.exec` sends it. Replaying the official wrapper reproduced
the failure, including with the real user's profile. The corrected hook
recognizes both exact forms. For the wrapped form only, it exports the
function from the SSH parent Bash to CentOS 7's Bash-based `/bin/sh`. The child
function rechecks the exact inner probe and SSH conditions, then removes its
export attribute before spawning diagnostics. It is not exported during
ordinary SSH sessions, and diagnostic child processes do not inherit it.

For exactly one argument, `GNU_LIBC_VERSION`, the function runs the installed
read-only helper with an eight-second timeout. The helper verifies the current
release identity, full release-tree integrity, private runtime checksums,
three ELF interpreters, and short program checks. It then invokes the system
`/usr/bin/getconf` through the private loader and prints that program's actual
result. This is not a hardcoded replacement version.

Failure, missing Python/timeout, damaged state, or other arguments fall back
to `/usr/bin/getconf`. Ordinary SSH, PTY sessions, and user programs retain the
system environment. No global PATH, LD_LIBRARY_PATH, or LD_PRELOAD is set.

The probe has no client-version field. A later client sending identical bytes
cannot be distinguished; users must keep ZCode pinned to 3.16.2.

### 2.3 Verified derived archives

`source-server prepare --archive PATH` performs the following steps:

1. Verify the pinned official size, SHA-256, Linux x64 target, and application
   version. Reject unknown inputs before executing extracted programs.
2. Reject traversal, links, duplicate entries, special files, and set-ID files.
3. Install and verify the private runtime using the existing runtime installer.
4. Extract to temporary tool-owned storage; verify the original hashes of
   Node, bfs, and ugrep; change only their ELF interpreters. Preserve RPATH and
   RUNPATH. Leave JavaScript, native modules, and other executables unchanged.
5. Recompute component hashes and sizes using the upstream sorted path plus
   NUL plus file-content algorithm; update content-derived archive names.
6. Verify Node, CLI version, native modules, actual PTY creation, search tools,
   and child-shell library isolation. Build a reproducible derived archive.
7. Record official and derived hashes, runtime identity, checksum-manifest
   fingerprint, tool version, and canonical installation root.

The output is host- and path-specific because the private interpreter is an
absolute path. It must not be copied to a different installation root. The
original vendor archive and existing immutable releases are not patched.
Preparation is cached by verified input, runtime, root, and tool identity.

### 2.4 Installation, state, and recovery

`source-server install --archive PATH` prepares the archive, uses its patched
bootstrap to invoke the original `update --from-archive` installer without
`--force`, and verifies the installed release. The upstream installer creates
its own release identity and integrity metadata from the derived bytes. The
helper does not falsify an official checksum or rewrite an installed release's
integrity record.

After successful verification, installation saves independent Source Server
state and enables the SSH hook. Windows connects only after this preinstallation.
Use a `.zcode` root under the SSH user's HOME; alternative temporary HOME roots
are supported for integration tests. The helper refuses symbolic-link target
directories and ambiguous managed profile blocks.

The legacy Node and its backup/state are preserved. Preparation failures leave
the active release unchanged. The upstream transaction remains responsible for
active-daemon update handoff. If post-install verification fails, the helper
restores its own offline activation only when no daemon owns the pointer. For
a live installation, it attempts the previous compatible archive through the
vendor updater without forcing running tasks to stop. The prior current
manifest is retained as recovery evidence; incomplete recovery is reported.
Fault-injected live rollback and explicit recovery passed in a disposable
installation; the acceptance scope and archive fixture are described below.

`source-server repair --archive PATH` explicitly repeats preparation and
installation. Updates from the desktop or directly from the vendor's online
catalog are outside this workflow. There is no updater watcher. Unknown
artifacts are rejected; running tasks are never forcibly interrupted.

`source-server uninstall` removes only the marked profile block, preserves
other profile content and later user edits, and marks compatibility disabled.
It retains the server, private runtime, derived artifacts, and backups. Removing
these retained files or stopping unrelated sessions is not part of uninstall.

### 2.5 CLI and verification behavior

The existing Bash entrypoint accepts `source-server` followed by:

| Command | Behavior |
|---|---|
| `prepare --archive PATH` | Derive a verified archive without activating it |
| `install --archive PATH` | Install and verify, then enable the SSH hook |
| `repair --archive PATH` | Explicitly prepare/install the supported release again |
| `status --json` | Read-only readiness and error report |
| `verify` | Short diagnostics; no persistent daemon started |
| `verify --handshake` | Start or reuse a daemon and require ready status |
| `uninstall` | Remove the hook and disable its state; retain recovery material |

Global `--zcode-root` and `--runtime-dir` remain available. Source Server does
not silently migrate or reinterpret legacy state. Explicit handshake checking
can leave a persistent daemon running; it does not stop a preexisting daemon.

## 3. Validation and Acceptance

The following automated checks passed on the CentOS 7 / Linux 3.10 host,
using temporary installation roots and an isolated loopback sshd:

- Existing CLI regression checks and the legacy runtime install/repair/restore
  integration test remain required.
- Archive traversal, link, duplicate-entry, checksum, and profile-edit tests.
- Official-archive preparation, repeated preparation, installation, and
  repeated installation through the vendor integrity checks.
- Real SSH replay of both the inner probe and the official wrapped command
  within the startup budget;
  ordinary SSH, PTY sessions, different arguments, and altered probes remain
  on system getconf.
- A focused function-inheritance regression verifies that the official wrapper
  reaches private getconf but the diagnostic process receives no exported
  getconf function. Altered inner and outer commands retain system behavior.
- Corrupt runtime and installed-release tests return to the system version.
- PTY creation, native module loading, search execution, private Node library
  loading, and system child-shell isolation.
- Daemon readiness, repeated handshake checks, explicit stop, legacy-state
  preservation, and uninstall preserving later profile edits.
- A real live update followed by injected post-activation verification failure
  restored the previous archive identity, Supervisor/Core release identities,
  compatibility state, and managed profile content.
- A corrupt rollback archive caused a visible incomplete-recovery error and
  readiness failure. Restoring the recovery archive and invoking the real
  `repair` CLI restored the original release and readiness.
- Killing only the disposable server's processes while retaining run files
  exercised stale PID/lock/socket recovery. A fresh SSH session started a new
  daemon, which remained ready after that SSH session closed.

`tests/lifecycle_acceptance.py` creates the second archive identity by changing
gzip MTIME only; the tar payload is byte-identical to the already verified
3.16.2 derivation. Test-only injection selects this fixture and forces a
post-activation validation error; the vendor updater, daemon handoff, runtime
identity checks, and rollback are real. This proves recovery for the supported
payload, not compatibility with a future unrecognized release. Test daemons
disable service registration and only their unique temporary root is cleaned.

Run the checks with:

```bash
make lint
make test
make test-runtime RUNTIME_DIR=/absolute/runtime NODE_BINARY=/absolute/original-node
make test-source-server RUNTIME_DIR=/absolute/runtime SOURCE_SERVER_ARCHIVE=/absolute/zcode-server-linux-x64.tar.gz
```

The function-inheritance unit test checks whether `/bin/sh` is Bash before
running. It runs on the CentOS 7 target and reports an explicit skip on Ubuntu
CI, where `/bin/sh` is dash. Other unit tests still run on that runner; skipping
this platform-specific test does not claim Ubuntu remote-hook support.

The full source integration test requires `/usr/sbin/sshd`, ssh, ssh-keygen,
and a Bash login shell. It uses temporary keys and an authorized-key-scoped
HOME, binds only to loopback, and removes its daemon and temporary files.
It does not modify the real SSH configuration, `.bashrc`, or ZCode installation.

In the inspected vendor build, `stop` can leave provider helper processes
alive after reporting success. The integration harness terminates only
processes owned by its temporary installation before deleting that directory.
The production helper does not force-kill user sessions or provider tasks.

On 2026-10-20, the user confirmed that the original Windows ZCode 3.16.2 client
connected successfully after the SSH wrapper correction. This records a real
desktop connection separately from automated SSH replay and module loading.
The user subsequently confirmed all requested desktop checks: opening a test
project, creating/editing files, creating a terminal, file and content search,
Git status, and short-task completion after desktop disconnect/reconnect.

| Acceptance item | Result | Evidence |
|---|---|---|
| Original Windows 3.16.2 connection | Passed | User confirmation, 2026-10-20 |
| Desktop project/files/terminal/search/Git | Passed | User confirmation, 2026-10-20 |
| Short task after desktop disconnect/reconnect | Passed | User confirmation, 2026-10-20 |
| Live activation failure and rollback | Passed | Disposable real-daemon integration test |
| Incomplete recovery and explicit repair | Passed | Disposable real-daemon integration test |
| Process crash, stale state, restart over SSH | Passed | Disposable integration test; not a reboot |
| Host reboot/service recovery | Not performed | Explicitly excluded by the user, 2026-10-20 |

The user instructed that the server must not be rebooted and that reboot
acceptance is not required. This is a scope exclusion, not a passing test.
The agreed scope is complete, so compatibility metadata records 3.16.2 in its
end-to-end verified list together with this explicit exclusion. No host reboot
recovery guarantee or automatic boot-time service installation is claimed.
The accepted implementation is promoted to `0.2.0`. Existing `0.2.0-rc.1`
installations must explicitly run the new tool's `source-server repair` with
the pinned official archive to refresh versioned state and support files;
publishing or replacing tool files does not modify a running installation.

## 4. Tool Versioning and ZCode Compatibility

### 4.1 Separate tool versions from ZCode versions

Keep the tool's own version sequence. Do not rename this tool to version
`3.16.2`, which would confuse its lifecycle with ZCode's lifecycle.

Use the following release lines:

| Tool release line | Installation model | ZCode versions | Status |
|---|---|---|---|
| `0.1.x` | Legacy fixed `server/node` | Windows 3.11.2, 3.14.3, 3.14.4, 3.14.5, 3.15.1, 3.15.3 | Historical manual connection results recorded in the [legacy guide](LEGACY.md); original implementation was `0.1.0` |
| `0.2.0-rc.N` | Remote-only Source Server workflow | 3.16.2 | Development candidates superseded by 0.2.0 |
| `0.2.x` stable | Verified remote-only workflow | Initially Windows 3.16.2 only | 0.2.0 accepted; host reboot excluded and untested |

The legacy list is an exact tested-version list, not a claim that every ZCode
version below 3.16.2 works. ZCode 3.16.1 and future releases remain unverified
unless separately tested. Do not advertise `>= 3.16.2` support.

Proposed version rules while the tool remains below 1.0:

- **Patch release**, such as `0.2.1`: fixes within the same installation model,
  command contract, state format, and supported ZCode-version set. A new
  vendor build hash still requires validation and a published metadata update.
- **Minor release**, such as `0.3.0`: changes the installation model or state
  contract, or adds a newly verified ZCode version to the supported set.
- **Prerelease**, such as `0.2.0-rc.1`: distributes reviewable work before all
  stable acceptance criteria have passed. Prerelease status does not imply
  production support.

### 4.2 Make compatibility visible in every release

For the first stable implementation, the proposed presentation is:

```text
Tool version: 0.2.0
Git tag: v0.2.0
Release title: v0.2.0 - ZCode 3.16.2 / Windows x64 to CentOS 7 x86-64
Archive: zcode-server-centos7-0.2.0-zcode-3.16.2-x86_64.tar.gz
Checksum: zcode-server-centos7-0.2.0-zcode-3.16.2-x86_64.tar.gz.sha256
Compatibility record: zcode-server-centos7-0.2.0-compatibility.json
```

The archive contains the remote Linux helper, private runtime, probe fixture,
compatibility record, and instructions. No Windows component or modified vendor
archive is distributed.

For a future release supporting several ZCode versions, use a model-specific
asset suffix such as `source-server` and list every exact supported version
in the compatibility record and release title/body. Avoid a misleading single
ZCode-version suffix on a multi-version bundle.

The compatibility record should contain at least:

- Tool version, installation model, and support status.
- Exact tested ZCode versions and recognized Windows client build hashes.
- Client OS/architecture and remote OS, architecture, shell, and kernel baseline.
- Official Source Server archive hashes for supported targets.
- Private runtime identity and checksum-manifest identity.
- Required remote preinstallation, release limitations, and validation status.

Derived archive hashes belong in per-installation state, because the private
loader path makes them installation-specific. They must not be published as
one universal release checksum.

The README, bundled compatibility record, and GitHub release notes must agree.
Release notes must state whether legacy versions remain supported and must
name the last suitable legacy release when they do not. Do not rely on the
GitHub `latest` link alone to guide users of the legacy deployment model.

### 4.3 Integrate the policy with the existing release workflow

The current source of the CLI version is `PROGRAM_VERSION` in
`bin/zcode-centos7`. `scripts/build-release.sh` uses it for the artifact name,
and `.github/workflows/release.yml` requires the Git tag to match it.

The packaging workflow now:

1. Checks the CLI version against compatibility metadata and the Git tag.
2. Includes the Python helper, exact SSH fixture, hook, development document,
   release notes, and private runtime.
3. Names the archive with both tool and ZCode versions, and emits a separate
   compatibility record and checksum files.
4. Publishes suffix-bearing versions as GitHub prereleases with curated notes.
5. Refuses a stable build unless the compatibility record includes an
   end-to-end verified 3.16.2 result.

No tag or release is created by development or tests. The runtime identity and
local derived-archive identity remain separate from the tool release number.

## 5. Investigation References

- [Official Windows 3.16.2 installer](https://cdn-zcode.z.ai/zcode/electron/releases/3.16.2/windows-x64/ZCode-3.16.2-win-x64.exe),
  whose version resource reports `3.16.2.8769`.
- [Official Source Server release descriptor](https://cdn-zcode.z.ai/zcode/electron/releases/3.16.2/source-server-release.json).
- [Official Linux x64 Source Server archive](https://cdn-zcode.z.ai/zcode/electron/releases/3.16.2/zcode-server-linux-x64.tar.gz),
  verified against that descriptor: 91,189,880 bytes; SHA-256
  `947eb91d3dd7d8a539d9df8d0e46c52a796e076c46b14feb004558337ab3bf3d`.
- Windows Host bundle SHA-256:
  `0018ac1f40c1b72f6b59ff31ac1ab7f1be7d82614c7aba94bde64df319a92c30`.
  The Windows and Linux 3.16.2 Host bundles inspected were identical.
- Original Node SHA-256, matching both the new archive and the old backup:
  `8142d37c6f2f372ef040419e7a111a6baf17df89f8078d02447d6c639ae20c1d`.

Temporary investigation files were saved under `/tmp/zcode-3162-analysis/`.
They are not durable repository dependencies; the artifact references,
identities, findings, and validation limits needed for development are
recorded above.
