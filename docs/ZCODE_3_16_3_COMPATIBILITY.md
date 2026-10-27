# ZCode 3.16.3 compatibility

Investigation date: 2026-10-26. Release tool version: 0.2.1.
The original investigation and desktop acceptance used local, unpublished
0.3.0 candidate/stable builds. The public release is numbered 0.2.1 under the
[versioning policy](UPGRADE_POLICY.md#6-versioning-and-release).

## Failure and scope

The Windows update log reports current Server 3.16.2, minimum compatible
3.16.3, successful prerequisite checks and upload, followed by seven dynamic
library errors after extraction. The supplied log redacts the symbol names
and executable paths, so it does not identify the failing executable directly.
The existing installed 3.16.2 compatible release still passes the read-only
helper status checks.

The original Source Server archive uses a bootstrap Node with the system ELF
interpreter. Desktop-managed installation executes this bootstrap before the
private-runtime derivation workflow can run. Running the verified original
3.16.3 Node with `--version` on this CentOS 7 host reproduces exactly seven
errors: GLIBCXX_3.4.21, GLIBCXX_3.4.20, CXXABI_1.3.9, GLIBC_2.27 from libm,
and GLIBC_2.27/2.28/2.25 from libc. Invoking it through the existing private
loader succeeds and reports v22.16.0. This matches the reported failure stage
and error count; the redacted log cannot independently confirm its paths.

## Pinned inputs

- [Official release descriptor](https://cdn-zcode.z.ai/zcode/electron/releases/3.16.3/source-server-release.json).
- [Official Linux x64 archive](https://cdn-zcode.z.ai/zcode/electron/releases/3.16.3/zcode-server-linux-x64.tar.gz).
- Size: 91,199,722 bytes.
- SHA-256: `5062d871bd2ad2ddd1b44d6463bd9159af5b493be93845ffc7163dd5b5d45375`.
- Runtime identity: `vscode-1.137.0-glibc-2.44-libstdcxx-6.0.36-x86_64`.

The downloaded size and SHA-256 match the official descriptor. All 12 ELF
files are byte-identical to their 3.16.2 counterparts, including Node, bfs,
ugrep, and native modules. The existing private runtime remains suitable.
The new manifest reports appVersion 3.16.3, nodeVersion 22.16.0, and target
linux-x64.

The release accepts this archive only. Server version comparisons now read
the pinned compatibility record rather than hardcoding 3.16.2. The upstream
installer still owns activation and immutable release integrity. Node, bfs,
and ugrep receive private interpreters in a derived archive; JavaScript and
other binaries remain unchanged.

The retained probe fixture is `src/probe-3.16.2.sh`. The Windows 3.16.3 Host
bundle has not been independently inspected. The reported update reached
upload/extraction, providing evidence that this user's environment checks
passed; this does not prove byte identity of all 3.16.3 probe implementations.
No substring matching or global environment override is added.

## Validation

The following checks passed on CentOS 7 / Linux 3.10:

- Syntax checks, CLI regressions, and 14 Python unit tests.
- Legacy runtime installation, repair, restoration, and child-shell isolation
  using the official 3.16.3 Node.
- Fresh 3.16.3 archive preparation and installation, repeat installation,
  native module loading, actual PTY creation, search tools, immutable release
  integrity, exact retained SSH probe and wrapper, corruption fallback,
  daemon handshake, and profile-preserving uninstall.
- Live activation fault rollback, incomplete recovery followed by explicit
  repair, and recovery from crashed temporary processes with stale run files.

Cross-version validation additionally uses the unmodified packaged 0.2.0
helper and official 3.16.2 archive. It starts a disposable 3.16.2 daemon,
prepares 3.16.3 without changing the active pointer, injects verification
failure after real 3.16.3 activation, checks rollback of the old archive,
compatibility state and hook, and then performs the real upgrade successfully.
The integration test accepts `--previous-cli` and `--previous-archive` to
reproduce this route. Current results are recorded in `compatibility.json`.
Temporary downloads and test installations live under `/tmp`.

On 2026-10-26 the user confirmed completion of the agreed Windows 3.16.3
desktop acceptance scope, covering connection, project/file/terminal/search/Git
operations and task persistence after disconnect/reconnect. These are recorded
as user-confirmed results, separately from automated checks. The end-to-end
verified version list now includes 3.16.3. At that time the local candidate was
promoted from 0.3.0-rc.1 to a local stable 0.3.0 build; neither version was
published as a Git tag or release.
Host reboot remains explicitly excluded by the user's earlier instruction.

The existing production 3.16.2 installation is not changed by building or
testing the tool. To deploy, use the explicit remote `repair` command
in the README after running tasks have completed. Keep the 0.2.0 helper and
original 3.16.2 archive for recovery; their compatibility metadata remains
available in the v0.2.0 release.

On 2026-10-26, after the user confirmed no running tasks needed preservation,
the remote helper upgraded the real default `~/.zcode` installation from
3.16.2 to 3.16.3 without `--force`. `verify --handshake` passed, compatibility
status reported `ready: true`, and the daemon's runtime-identity response
confirmed that Supervisor and Core both matched the current 3.16.3 release.
The production derived archive SHA-256 is
`ef4c25698baeef955e45068df11604c169d114c48ad2dbb61e4bc95bf631b699`.
This is specific to that host/root, not a distributable vendor archive identity.
Windows desktop acceptance was subsequently confirmed by the user on the same
date. No host reboot was performed or claimed.

Existing local 0.3.0 and 0.3.0-rc.1 installations must run the 0.2.1 helper's
`source-server repair --archive PATH` to refresh versioned state and installed
support files.
Changing the helper version alone does not migrate installed state.

## 0.2.1 release validation (2026-10-27)

The following automated checks passed on CentOS 7, kernel
`3.10.0-1160.el7.x86_64`, with system glibc 2.17. The release was built from a
clean staged source snapshot with an explicitly selected, verified runtime.

- Syntax checks, CLI regressions, all 14 Python unit tests, and ShellCheck
  0.11.0 passed. CLI, compatibility metadata, and artifact versions agree.
- The actual 0.2.1 bundle passed the existing fresh-install integration suite:
  preparation without activation, repeat installation, native modules and PTY,
  exact SSH probes and corruption fallback, daemon handshake, activation-fault
  rollback, incomplete recovery and repair, crash/stale-state recovery, daemon
  survival after SSH disconnect, and profile-preserving uninstall.
- The same suite passed with the original packaged 0.2.0 helper and official
  3.16.2 archive as the upgrade source. An injected failure after 3.16.3
  activation restored the old archive identity, running service, compatibility
  state, and hook; the subsequent real upgrade to 3.16.3 succeeded.
- Separate temporary installations of the original local 0.3.0 and 0.3.0-rc.1
  bundles passed state-refresh checks. Before repair, 0.2.1 rejected the old
  tool-versioned state. Repair refreshed state and installed metadata to 0.2.1
  while retaining Server 3.16.3. Daemon readiness, repeated repair, a single
  managed hook, and preservation of unrelated profile content all passed.
- README instructions cover only the current combination; historical guides
  use fixed tags. Bundled documents match the staged source, and the archive
  and standalone compatibility metadata passed SHA256 verification.

All installations and loopback SSH sessions used temporary HOME directories.
The production `.bashrc`, server current pointer, and compatibility state
retained their pre-test hashes. No production upgrade or host reboot was
performed. Windows desktop acceptance remains the separate user-confirmed
2026-10-26 result above; it was not rerun by these automated checks.
