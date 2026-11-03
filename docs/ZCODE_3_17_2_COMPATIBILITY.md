# ZCode 3.17.2 compatibility

Investigation date: 2026-11-03. Candidate tool version: 0.2.3-rc.1.
This is a routine adaptation of the 0.2.2 workflow for the new ZCode
3.17.2 release under the
[versioning policy](UPGRADE_POLICY.md#6-versioning-and-release).

## Failure and scope

The Windows desktop reports that ZCode 3.17.2 is available. As with the
3.16.3 to 3.17.1 history, a client update raises the minimum compatible
server version, so the desktop must not be updated until the CentOS 7
server side is adapted and repaired. The existing installed 3.17.1
compatible release keeps working with the pinned 3.17.1 client.

The official 3.17.2 Source Server archive keeps the same bootstrap
structure as 3.17.1: `bin/zcode` is a POSIX shell script that executes
`runtime/node` with `runtime/server-cli.js`. The 3.17.2 server CLI and
server core declare `ZCODE_MIN_COMPATIBLE_VERSION = "3.17.2"`, where
3.17.1 declared `"3.17.1"`; a mixed client/server pair is therefore not
a supported end state and both sides must move together.

## Pinned inputs

- [Official release descriptor](https://cdn-zcode.z.ai/zcode/electron/releases/3.17.2/source-server-release.json).
- [Official Linux x64 archive](https://cdn-zcode.z.ai/zcode/electron/releases/3.17.2/zcode-server-linux-x64.tar.gz).
- Size: 91,085,918 bytes.
- SHA-256: `88a41b337faa3f578a1fd68c1f28025fa0385a391eacfbac34b819653b8938e3`.
- Runtime identity: `vscode-1.137.0-glibc-2.44-libstdcxx-6.0.36-x86_64`.

The downloaded size and SHA-256 match the official descriptor. A full
file-by-file comparison with the verified 3.17.1 archive found:

- All 12 ELF files are byte-identical to their 3.17.1 counterparts,
  including Node, bfs, ugrep, ripgrep, and every native module
  (`koffi`, `node-pty`, `unsafe-pointer`, `opentui-core`). No ELF file
  was added or removed.
- `bin/zcode` is byte-identical; the startup chain is unchanged.
- The new manifest reports appVersion 3.17.2, nodeVersion 22.16.0, and
  target linux-x64. Entrypoints, native modules, tools, and the plugin
  list keep the 3.17.1 shape.
- Remaining differences are JavaScript/TypeScript sources under
  `runtime/node_modules` (`@zcode/contracts`, `@zcode/shared`), the
  bundled `zcode-guide-plugin` skill text, `server-cli.js`,
  `server-core.js`, and `zcode.cjs`, plus updated component archive
  entries (server-runtime, agent-runtime, official-plugins) used by the
  desktop-managed installer, which this tool does not use.

The existing private runtime and the exact patch targets therefore remain
suitable without modification. Node, bfs, and ugrep keep receiving private
interpreters in a derived archive; JavaScript and other binaries remain
unchanged. The pinned executable hashes in
[compatibility.json](../compatibility.json) are unchanged because the
files are unchanged.

The retained probe fixture is still `src/probe-3.16.2.sh`. The Windows
3.17.2 Host bundle has not been independently inspected, and the probe
template is not embedded in the server archive (confirmed for 3.16.3,
3.17.1, and 3.17.2), so the 3.17.2 client probe text cannot be verified
from the server side before connection. The unchanged bootstrap and ELF
layer make a probe change unlikely; if the 3.17.2 client sends a
different command, the managed hook safely falls back to system behavior
and the connection fails without environment overrides, requiring a new
captured fixture.

## Adaptation

One source change beyond pinned identities was required. The 3.17.1
server CLI introduced a downgrade guard that the 3.17.2 archive keeps:
`update --from-archive` exits with the structured error
`source-server-downgrade-unconfirmed` when the active release is newer
than the archive and `--allow-downgrade` is absent. The helper's live
activation-failure rollback runs the retained older release's own CLI
against its known-good archive, which is exactly a deliberate downgrade.
`src/source_server.py` now appends `--allow-downgrade` to that rollback
command when the retained record's `zcode_version` is 3.17.1 or newer;
older CLIs without the guard keep the plain invocation. The forward
install path is unaffected because it always targets the same or a newer
version. The plain-command branch that served the 0.2.2-era 3.16.3
rollback is unchanged.

## Validation

The following automated checks passed on CentOS 7, kernel
`3.10.0-1160.el7.x86_64`, on 2026-11-03:

- Syntax checks, CLI regressions, all 14 Python unit tests, and ShellCheck
  0.11.0. CLI, compatibility metadata, and candidate versions agree.
- Fresh-install integration with the official 3.17.2 archive: preparation
  without activation, repeat installation, native modules and PTY, search
  tools, immutable release integrity, exact retained SSH probe and wrapper,
  corruption fallback, daemon handshake, activation-fault rollback,
  incomplete recovery followed by explicit repair, crash/stale-state
  recovery, daemon survival after SSH disconnect, and profile-preserving
  uninstall.
- Cross-version upgrade using the unmodified packaged public 0.2.2 helper
  and official 3.17.1 archive as the upgrade source: a disposable 3.17.1
  daemon was started, 3.17.2 was prepared without changing the active
  pointer, an injected failure after real 3.17.2 activation first failed
  recovery because of the new downgrade guard, then restored the old
  archive identity, compatibility state, and hook after the helper
  confirmed the deliberate downgrade, and the old helper verified daemon
  readiness in the rolled-back state. The subsequent real upgrade
  succeeded.
- The complete suite was rerun with the built local 0.2.3-rc.1 bundle as
  the new helper, including the cross-version upgrade path.
- The release bundle's archive and standalone compatibility metadata
  passed SHA256 verification.

All installations and loopback SSH sessions used temporary HOME directories
under `/tmp`. The production `.bashrc`, server current pointer, and
compatibility state were not touched; no production upgrade or host reboot
was performed.

## Desktop acceptance and stable promotion (2026-11-03)

The user repaired the real default `~/.zcode` installation with the local
0.2.3-rc.1 helper and the official 3.17.2 archive from a plain SSH session
with the desktop disconnected. The compatibility state was refreshed to
tool 0.2.3-rc.1 / ZCode 3.17.2, the 3.17.2 release became active,
`verify` passed, and status reported `"ready": true`. The user then updated
the Windows desktop to ZCode 3.17.2, reconnected, and confirmed completion
of the agreed desktop acceptance scope: SSH connection and reconnection,
remote project access, file creation, reading, and editing, terminal
commands, filename and content searches, Git status, and a short
observable task with disconnect/reconnect persistence. The managed hook
therefore still receives an acceptable probe command from the 3.17.2
client; the probe fixture remains the retained exact 3.16.2 text. The
production derived archive SHA-256 for this host/root is
`eaa4f8fd3cf850305b1625c57bc35252212ecbcebdd5902dc166cf07609c2b7a`;
it is specific to that installation, not a distributable identity.
Host reboot was not performed or claimed.

After desktop acceptance, the candidate was promoted to stable
**0.2.3**: `end_to_end_verified_zcode_versions` now includes 3.17.2, the
desktop validation entries record the user confirmation, and the pending
list is empty. Local 0.2.3-rc.1 installations require one `repair` with
the stable 0.2.3 helper to refresh the versioned state and support files;
this keeps Server 3.17.2 and is not a downgrade. Automated suites do not
rerun desktop acceptance; that evidence remains the user-confirmed
2026-11-03 result above.
