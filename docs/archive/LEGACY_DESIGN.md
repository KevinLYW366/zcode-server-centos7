# zcode-server-centos7 Legacy Development Design

> Historical scope: this document preserves the design for the legacy `0.1.x`
> fixed `~/.zcode/server/node` layout. It does not apply to the `0.2.0` Source
> Server workflow. See the [legacy guide](../LEGACY.md) for legacy usage.
> The current 0.2.1 stable release supports ZCode 3.16.3; see the
> [README](../../README.md) for usage and the
> [3.16.3 compatibility record](../ZCODE_3_16_3_COMPATIBILITY.md) for validation.
> The 0.2.0 stable design and acceptance boundaries are documented in the
> [3.16.2 Source Server compatibility document](ZCODE_3_16_2_COMPATIBILITY_PLAN.md).
> For future adaptation, release gates, and user upgrade and recovery procedures,
> see the [upgrade and compatibility policy](../UPGRADE_POLICY.md). This
> historical design is not the current update procedure.

## 1. Purpose

This document defines the development scope, technical design, safety boundaries,
test strategy, and acceptance criteria for `zcode-server-centos7`.

The tool addresses one problem: allowing `~/.zcode/server/node`, launched directly
by the Windows Zcode client on CentOS 7, to start using compatible runtime
libraries under the user's directory, resolving missing `GLIBC_*`, `GLIBCXX_*`,
and `CXXABI_*` versions.

The tool must not change the execution environment of other tasks, other users,
or system programs.

## 2. Background and Problem

CentOS 7 typically provides:

- glibc 2.17;
- an older `libstdc++.so.6` associated with GCC 4.8;
- a Linux kernel from the 3.10 series.

Zcode deploys Node.js on the remote server at:

```text
~/.zcode/server/node
```

The Node.js binary considered here requires at least:

```text
GLIBC_2.25
GLIBC_2.27
GLIBC_2.28
GLIBCXX_3.4.20
GLIBCXX_3.4.21
CXXABI_1.3.9
```

CentOS 7's system dynamic loader and libraries therefore cannot start this
binary. Zcode exits before emitting its handshake message.

## 3. Core Principles

### 3.1 Affect Only Zcode

The compatibility layer must be strictly limited to:

```text
~/.zcode/server/node
```

Runtime files may be modified or created only at:

```text
~/.zcode/server/node
~/.zcode/centos7-runtime/
~/.zcode/centos7-runtime/backups/
~/.zcode/centos7-runtime/state.json
```

Unless the user explicitly specifies a test directory, the tool must not scan,
modify, or wrap other Node.js, Python, Git, shell, editor server, or user tasks.

### 3.2 Do Not Modify the System Environment

The following actions are prohibited:

- Replacing or modifying any file in `/lib64`, `/usr/lib64`, `/lib`, or `/usr/lib`.
- Upgrading system glibc through RPM/YUM.
- Modifying `/etc/ld.so.conf` or running `ldconfig` to install private libraries.
- Modifying `.bashrc`, `.bash_profile`, `.profile`, SSH configuration, or system
  environment variables.
- Setting `LD_LIBRARY_PATH` or `LD_PRELOAD` globally or persistently.
- Placing files in `$PATH` that impersonate system commands such as `node`,
  `bash`, or `git`.
- Recursively patching ELF files under `~/.zcode/server`.
- Modifying Zcode's JavaScript/CJS application code.

### 3.3 Do Not Propagate the Compatibility Environment to Child Tasks

Private glibc and libstdc++ must take effect only through the target Node ELF's
private interpreter, not through environment variables. The verified loader must
resolve its companion GNU libraries from its own directory. The tool must not
add or modify RPATH/RUNPATH on the target Node.

Programs launched from Zcode, including `/bin/bash`, `git`, `ls`, build tasks,
and user scripts, must continue using the native system dynamic loader and their
respective libraries.

### 3.4 Recoverable, Repeatable, and Auditable

Every installation operation must:

- Save the original files and their SHA256 hashes before making changes.
- Create and verify temporary files before atomically replacing targets.
- Remain idempotent on repeated execution.
- Refuse to overwrite files when state is ambiguous.
- Support restoration of the byte-identical original Node.
- Record the tool's own state in a separate manifest.

## 4. Scope and Non-Goals

### 4.1 First-Release Scope

- OS: CentOS 7 / RHEL 7-compatible systems.
- CPU architecture: `x86_64`.
- Target: `~/.zcode/server/node`.
- Private libraries: glibc 2.28 and libstdc++/libgcc satisfying the target Node ABI.
- Functions: inspection, installation, status, verification, repair, and uninstall.
- Installation privileges: ordinary user, without root access.
- Zcode connection: a Windows client launches remote Node over SSH.

### 4.2 First-Release Non-Goals

- Providing a general CentOS 7 compatibility layer for arbitrary Node.js binaries
  or applications.
- Patching Zcode extensions, user plugins, or other ELF files.
- Taking over the Zcode updater.
- Preventing Zcode from overwriting or updating Node.
- Monitoring files with a persistent daemon.
- Locking Zcode files with `chattr +i`.
- Supporting ARM, ARM64, or 32-bit platforms.
- Redistributing Zcode Server, Zcode Node.js, or other proprietary Zcode files.

## 5. Recommended Architecture

### 5.1 Execution Chain

Before installation:

```text
Windows Zcode
    -> SSH
    -> ~/.zcode/server/node
    -> CentOS 7 system loader
    -> Insufficient ABI versions; exits before handshake
```

After installation:

```text
Windows Zcode
    -> SSH
    -> ~/.zcode/server/node (only this ELF is redirected)
    -> ~/.zcode/centos7-runtime/lib/ld-linux-x86-64.so.2
    -> Private glibc/libstdc++ in ~/.zcode/centos7-runtime/lib
    -> ~/.zcode/server/zcode-server.cjs
    -> zcode-hello
```

When Zcode launches an external task:

```text
Zcode Node
    -> exec /bin/bash, git, or another user command
    -> The external program's own system ELF interpreter
    -> CentOS 7 system libraries
```

Because no private glibc `LD_LIBRARY_PATH` is exported, external tasks do not
inherit Zcode's compatibility library paths.

### 5.2 Patch Node Directly Instead of Using a Global Wrapper

The first release sets ELF `PT_INTERP` only on the installed copy of
`~/.zcode/server/node`, pointing it to the absolute path of the private
`ld-linux-x86-64.so.2`.

The following conceptual command illustrates the design; it is not a manual
procedure for users:

```text
patchelf --set-interpreter <absolute-private-loader> <temporary-node>
```

Writing RPATH on the Zcode Node v22.16.0 examined here causes SIGSEGV, so the
implementation must preserve the original RPATH/RUNPATH. The loader from
`vscode-server-centos7` 1.137.0 already locates its companion GNU libraries in
its own directory; changing the target Node's RPATH is unnecessary.

Apply the patch to a temporary copy. Replace `~/.zcode/server/node` atomically
only after that copy passes verification.

Benefits of this design:

- Only Zcode's bundled Node uses the private loader.
- `process.execPath` still points to `~/.zcode/server/node`.
- Node can still start itself or use `child_process.fork()` correctly.
- No shell wrapper is required, and arguments and standard I/O protocols remain
  unchanged.
- No environment variables need to be set for other processes.
- System commands launched by Zcode continue using their own ELF configuration.

### 5.3 Avoid Whole-Directory ELF Scanning

The reference project `vscode-server-centos7` scans VS Code Server and extension
directories to handle VS Code's multiple-binary layout.

This tool's first release must not copy that behavior. The failure occurs before
the top-level Zcode Node starts, so patching only that Node is the minimum change
that meets the requirement.

If Zcode is later found to require direct execution of another incompatible
native binary, collect clear failure evidence first. Add an exact target to the
allowlist through a separate requirement; do not switch to unconditional recursive
scanning.

## 6. Private Runtime Libraries

### 6.1 Runtime Contents

The release should contain only the minimum runtime files needed to start the
target Node, for example:

- `ld-linux-x86-64.so.2`;
- `libc.so.6`;
- `libm.so.6`;
- `libdl.so.2`;
- `libpthread.so.0`;
- `librt.so.1`;
- `libresolv.so.2`;
- necessary NSS/DNS modules;
- `libstdc++.so.6`;
- `libgcc_s.so.1`;
- corresponding licenses and build metadata.

Determine the actual list from the target Node's `DT_NEEDED`, execution tests,
and DNS/TLS tests together. Do not infer it from filenames alone.

### 6.2 Build Constraints

- The imported runtime currently verified here contains glibc 2.44 and
  libstdc++ 6.0.36.
- The reference runtime was built with a minimum kernel of `3.10.0`.
- Builds must be reproducible, with all source URLs and SHA256 hashes pinned.
- Artifacts must be validated with real CentOS 7 userspace and kernel 3.10.
- Release bundles must not include Zcode's own files.
- Every file in the release bundle should be covered by a SHA256 manifest.

### 6.3 Path Constraints

The private loader's ELF `PT_INTERP` must be an absolute path. Generate the patch
at installation time using the target user's home directory and the specific
runtime release directory.

Preserve the target Node's original RPATH/RUNPATH. Do not add private runtime,
Conda, globally customized system library, or other tasks' library directories.

## 7. Management Command Design

A single entry point is recommended:

```text
zcode-centos7 inspect
zcode-centos7 install
zcode-centos7 status
zcode-centos7 verify
zcode-centos7 repair
zcode-centos7 uninstall
```

Every command that writes must explicitly specify or confirm the target Zcode
root, defaulting to `$HOME/.zcode`.

### 7.1 `inspect`

Inspect without writing:

- OS, CPU architecture, and kernel.
- System glibc version.
- Whether `~/.zcode/server/node` exists and is a regular ELF file.
- Node architecture, `PT_INTERP`, and RPATH/RUNPATH.
- Required GLIBC, GLIBCXX, and CXXABI versions.
- Zcode Node Runtime metadata.
- Whether this tool has already processed the current file.
- Private runtime integrity.

`inspect` must not write files, automatically download dependencies, or start or
terminate existing Zcode processes.

### 7.2 `install`

Proposed procedure:

1. Resolve and normalize `$HOME/.zcode`; reject empty paths, the filesystem root,
   and symlink traversal beyond the allowed boundary.
2. Confirm that the target is exactly `<zcode-root>/server/node`.
3. Perform a read-only ABI inspection of the original Node.
4. Verify the runtime release archive's SHA256.
5. Install the runtime into a temporary directory.
6. Copy the original Node to the backup directory and record its SHA256.
7. Copy the original Node to a temporary path on the same filesystem.
8. Set only the temporary Node's interpreter, preserving original RPATH/RUNPATH.
9. Run `--version`, dependency checks, and child-process isolation tests on the
   temporary Node.
10. Write a temporary state manifest.
11. Commit the runtime, Node, and state manifest using atomic renames.
12. Perform full verification again.

Any failed step must preserve the original Node and must not leave a partial
installation.

### 7.3 `status`

Report at least:

- Installation state.
- Current Node SHA256.
- Corresponding original Node SHA256.
- Current ELF interpreter.
- Current RPATH.
- Private runtime version.
- Zcode Node Runtime version.
- Whether a Zcode update appears to have overwritten Node.
- Most recent installation or repair time.

`status` must be read-only.

### 7.4 `verify`

Verify that:

1. The private loader can start the target Node.
2. `node --version` exits successfully.
3. The Node process loads private libc, libstdc++, and libgcc.
4. Simple JavaScript executes successfully.
5. Node can launch `/bin/bash -c` successfully.
6. `/bin/bash` uses the system interpreter, with no tool-injected glibc
   `LD_LIBRARY_PATH` in its environment.
7. Node DNS resolution succeeds.
8. When the user explicitly allows starting a test service, `zcode-server.cjs`
   runs and emits a recognizable `zcode-hello`.

By default, `verify` must not terminate a running Zcode service. Handshake tests
must have timeouts and terminate only processes created by that verification.

### 7.5 `repair`

Handle cases where a Zcode update overwrites Node:

- If Node is already correctly patched, exit successfully.
- If Node uses the system interpreter again and its SHA256 differs from the
  record, treat it as a new Zcode Node.
- Create a new versioned backup of the new Node before running installation.
- Never silently overwrite old backups.
- If the target is neither a known patched file nor a valid new Node ELF,
  refuse to process it and report the reason.

The first release does not install watchers, cron jobs, or persistent services.
Repair occurs only when the user explicitly runs `repair`.

### 7.6 `uninstall`

Uninstall procedure:

1. Verify that the current Node matches the state manifest.
2. Locate the original backup corresponding to the current Zcode Node version.
3. Verify the backup's SHA256.
4. Restore atomically through a temporary file.
5. Verify that the restored file uses the original system interpreter.
6. Mark the state as uninstalled.

If Zcode has updated and the current file no longer matches the manifest,
`uninstall` must not guess which version to restore.

Keep runtimes and backups by default to avoid irreversible deletion. Historical
file cleanup should be a separate, explicit future feature.

## 8. State Manifest

JSON is recommended, with an illustrative structure as follows:

```json
{
  "schema_version": 1,
  "tool_version": "0.1.0",
  "zcode_root": "/home/example/.zcode",
  "node_path": "/home/example/.zcode/server/node",
  "node_original_sha256": "...",
  "node_patched_sha256": "...",
  "backup_path": "/home/example/.zcode/centos7-runtime/backups/node.<sha256>",
  "original_interpreter": "/lib64/ld-linux-x86-64.so.2",
  "patched_interpreter": "/home/example/.zcode/centos7-runtime/lib/ld-linux-x86-64.so.2",
  "runtime_version": "glibc-2.28-gcc-9",
  "zcode_node_version": "...",
  "installed_at": "..."
}
```

The state manifest must not record tokens, SSH keys, environment variable
contents, or Zcode session data.

## 9. Update and Compatibility Strategy

Zcode may use the following metadata to decide whether to redeploy Node:

```text
~/.zcode/server/.asset-components/node-runtime.json
```

The tool may read and record this file's contents or hash, but must not forge,
freeze, or modify version metadata to prevent updates.

Expected behavior after an update:

1. Zcode's update overwrites Node.
2. The next connection may fail with ABI errors again.
3. The user runs `zcode-centos7 repair`.
4. The tool identifies the new Node, creates a new backup, and patches it again.
5. The user reconnects after verification.

Consider automatic repair only after establishing an official Zcode deployment
hook or stable protocol. Do not implement it through global login scripts or
mechanisms that affect other SSH tasks.

## 10. Failure Safety

### 10.1 File Safety

- Accept only regular files as Node targets.
- Resolve symlinks and check path boundaries.
- Temporary file permissions must not be broader than those of the original Node.
- Do not follow untrusted symlinks in backup directories.
- Use temporary files on the same filesystem to ensure atomic renames.
- Run `fsync` after writing manifests and before committing critical renames.
- On exit, clean up only temporary files created by the tool whose paths have
  been verified.

### 10.2 Process Safety

- Do not use `pkill node`, `killall node`, or ambiguous process matching.
- Do not terminate existing Zcode processes by default.
- Tests manage only child processes they started and whose PIDs they recorded.
- If the target Node is running before installation, notify the user and allow
  file replacement without disrupting existing processes.
- Do not monitor or modify other users' processes.

### 10.3 Output Protocol Safety

Zcode uses standard input/output for its startup handshake. Patched Node must
not emit additional output during normal startup.

The management tool may emit diagnostics, but normal stdout/stderr behavior of
the target `~/.zcode/server/node` itself must match the original Node.

## 11. Test Plan

### 11.1 Static Tests

- Verify runtime SHA256 hashes.
- Inspect original and patched Node ELF headers.
- Inspect `PT_INTERP`.
- Confirm that RPATH/RUNPATH matches the original file.
- Extract and compare GLIBC/GLIBCXX/CXXABI requirements.
- Confirm that only intended targets and tool state directories change.

### 11.2 Unit Tests

- Path normalization and boundary checks.
- State manifest reading and writing.
- SHA256 and version identification.
- State transitions for original, installed, updated, and unknown files.
- Repeated-installation idempotency.
- Backup rotation during repair.
- Conflict refusal during uninstall.
- Argument and exit-code forwarding.

### 11.3 CentOS 7 Container Tests

In a clean CentOS 7 environment, verify:

- System glibc remains at 2.17.
- The original test Node fails because of ABI incompatibility.
- Node starts normally after installation.
- Node loads private glibc/libstdc++.
- Bash still loads system glibc when Node launches `/bin/bash`.
- DNS, HTTPS, file I/O, and Git child processes work normally.
- The complete installation, repeated installation, simulated update, repair,
  and uninstall cycle works.
- After uninstall, the original Node SHA256 exactly matches its pre-installation
  value.

### 11.4 Real Zcode End-to-End Tests

- Windows Zcode establishes an SSH connection.
- The server emits a valid `zcode-hello`.
- A remote workspace opens successfully.
- Zcode Agent can read and modify workspace files.
- Zcode Agent can execute shell commands, Git, and project tests.
- Concurrent ordinary SSH sessions and non-Zcode tasks behave identically.
- No compatibility-layer environment variables or daemons remain after Zcode
  disconnects.

### 11.5 Isolation Regression Tests

Isolation failures block release. Test at least:

```text
/bin/bash
/usr/bin/git
/usr/bin/ssh
/usr/bin/python (if present)
System node (if present and distinct from Zcode Node)
Programs in a Conda environment (if available in the test environment)
```

Their interpreters, library resolution, and basic behavior must remain identical
before and after installation.

The following user shell values must remain unchanged before and after running
the tool:

```text
PATH
LD_LIBRARY_PATH
LD_PRELOAD
LIBRARY_PATH
CPATH
```

## 12. Acceptance Criteria

The first release may ship only when all of the following hold:

1. The target Node no longer reports missing GLIBC, GLIBCXX, or CXXABI versions
   on CentOS 7.
2. Windows Zcode completes the remote handshake and remains usable.
3. Only `~/.zcode/server/node` and `~/.zcode/centos7-runtime` are modified.
4. System libraries, shell configuration, SSH configuration, and the global
   environment are unchanged.
5. System tasks launched by Zcode continue using system libraries.
6. Non-Zcode tasks behave identically before and after installation.
7. Installation and repair are idempotent.
8. Uninstall restores the byte-identical original Node.
9. No failure path leaves an unstartable Node without a backup.
10. Runtime sources, build parameters, SHA256 hashes, and licenses are fully
    auditable.

## 13. Development Phases

### Phase One: Read-Only Environment Inventory

- Inspect the current `~/.zcode/server` layout.
- Record Node version, SHA256, interpreter, and ABI requirements.
- Inspect Zcode Runtime metadata.
- Confirm startup commands and handshake behavior.
- Produce an inventory report without modifying files.

### Phase Two: Minimum Technical Validation

- Prepare private glibc/libstdc++ libraries.
- Patch only the interpreter on a temporary Node copy.
- Verify Node, self-spawning, shell child processes, DNS, and handshake.
- Do not replace the production `~/.zcode/server/node` until all temporary
  validation passes.

### Phase Three: Management Tool

- Implement `inspect/install/status/verify/repair/uninstall`.
- Implement the state machine, atomic replacement, and backup restoration.
- Add unit and fault-injection tests.

### Phase Four: Reproducible Builds and Release

- Pin glibc, GCC, binutils, and kernel header versions.
- Pin download URLs and SHA256 hashes.
- Build a minimal runtime release bundle.
- Add CentOS 7 container tests.
- Generate an SBOM, license inventory, and release checksums.

### Phase Five: Real Client Acceptance

- Test remote connections from Windows Zcode.
- Run isolation regression tests.
- Simulate a Zcode Node update and verify `repair`.
- Verify restoration during uninstall.

## 14. Licensing and Distribution

The project may refer to the build approach of `vscode-server-centos7`, but
copying or adapting its GPLv3 code requires compliance with GPLv3.

glibc, libstdc++, libgcc, and build tools have their own licenses and exceptions.
When distributing binary runtime libraries:

- Preserve licenses and copyright notices.
- Publish the corresponding source versions and patches.
- Provide complete, reproducible build scripts.
- Meet LGPL requirements for relinking, modification, and source availability.
- Do not include proprietary Zcode binaries in this project's release bundles.

If the project itself is to use a more permissive license, implement management
and startup adaptation code independently, borrowing only architectural ideas
without copying GPLv3 source code.

## 15. Information to Confirm Before Development

Before coding, phase one must establish:

- The server's exact CPU architecture and kernel version.
- The Node version and SHA256 of `~/.zcode/server/node`.
- Node's current `PT_INTERP`, RPATH/RUNPATH, and `DT_NEEDED`.
- Whether `~/.zcode/server` contains other native binaries executed directly.
- The actual format of `.asset-components/node-runtime.json`.
- All arguments passed to Node by the Windows Zcode client.
- Whether file hash checks or automatic overwrites occur.
- Whether placing private libraries in `~/.zcode/centos7-runtime` matches the
  user's expectations.

Until these facts are confirmed, do not expand the patch scope or assume that
all VS Code Server handling logic also applies to Zcode.
