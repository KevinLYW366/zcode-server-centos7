# ZCode 4.0.0 compatibility

Investigation date: 2026-11-24. Candidate tool version: 0.2.6-rc.1.
This is a routine adaptation of the 0.2.5 workflow for the new ZCode
4.0.0 release under the
[versioning policy](UPGRADE_POLICY.md#6-versioning-and-release).

## Failure and scope

The Windows desktop reports that ZCode 4.0.0 is available. As with the
earlier 3.x update history, a client update raises the minimum compatible
server version, so the desktop must not be updated until the CentOS 7
server side is adapted and repaired. The existing installed 3.19.1
compatible release keeps working with the pinned 3.19.1 client.

The official 4.0.0 Source Server archive keeps the same bootstrap
structure as 3.19.1: `bin/zcode` is a POSIX shell script that executes
`runtime/node` with `runtime/server-cli.js`, and it is byte-identical to
3.19.1. The 4.0.0 server CLI declares
`ZCODE_MIN_COMPATIBLE_VERSION = "4.0.0"`, where 3.19.1 declared
`"3.19.1"`; a mixed client/server pair is therefore not a supported end
state and both sides must move together. This is the first 4.x release,
but it does not change the installation model, state format, or command
contract.

## Pinned inputs

- [Official release descriptor](https://cdn-zcode.z.ai/zcode/electron/releases/4.0.0/source-server-release.json).
- [Official Linux x64 archive](https://cdn-zcode.z.ai/zcode/electron/releases/4.0.0/zcode-server-linux-x64.tar.gz).
- Size: 97,544,737 bytes.
- SHA-256: `e68f1d7b94536b95308348b9f98102d792059e3c9fe45a592660f07afd5eb31a`.
- Runtime identity: `vscode-1.137.0-glibc-2.44-libstdcxx-6.0.36-x86_64`.

The downloaded size and SHA-256 match the official descriptor. A full
file-by-file comparison with the verified 3.19.1 archive found:

- All 13 ELF files of 3.19.1 are byte-identical to their 4.0.0
  counterparts, including Node, bfs, ugrep, ripgrep, and every native
  module (`koffi`, `node-pty`, `unsafe-pointer`, `opentui-core`,
  `@napi-rs/keyring-linux-x64-gnu`). No ELF file was added or removed.
- The three exact patch targets (`runtime/node`,
  `runtime/tools/bfs/bfs`, `runtime/tools/ugrep/ugrep`) are
  byte-identical, so the pinned executable hashes in
  [compatibility.json](../compatibility.json) are unchanged.
- `bin/zcode` is byte-identical; the startup chain is unchanged.
- The new manifest reports appVersion 4.0.0, nodeVersion 22.16.0, and
  target linux-x64. Entrypoints, the native module list (`node-pty`),
  the search tool list, the plugin list, and the component identifiers
  and paths keep the 3.19.1 shape; only component hashes and sizes
  changed, which the component identity logic recomputes anyway.
- No files were added and 4 were removed in total: the
  `agents/visual-judge.md` descriptions of the documents, pdf,
  presentations, and spreadsheets plugins. 42 tracked files changed in
  place: TypeScript sources and declarations under `@zcode/contracts`
  and `@zcode/shared`, bundled plugin dist/UI assets and manifests,
  `server-cli.js`, `server-core.js`, and `zcode.cjs`, plus the manifest.
  None of it affects the ELF layer, the patch targets, or the startup
  chain.

The existing private runtime and the exact patch targets therefore
remain suitable without modification. Node, bfs, and ugrep keep
receiving private interpreters in a derived archive; JavaScript and
other binaries remain unchanged.

Behavioral checks against the extracted 4.0.0 tree confirm the 3.19.1
mechanisms carry over unchanged: `--prepare-credentials` exists on the
server CLI update/serve forms, the core still requires the private
`credential-secret` state, the downgrade guard
(`source-server-downgrade-unconfirmed` with `--allow-downgrade`) is
present, the node-pty entry file
`runtime/node_modules/node-pty/lib/index.js` still has the same
`exports`-without-`main` package shape, and the Node version stays
`v22.16.0`. The option markers used by the helper (`--from-archive`,
`--prepare-credentials`, `--server-root`, `--allow-downgrade`,
`--daemon`, `--json`) occur with identical counts in the 3.19.1 and
4.0.0 server CLI.

The retained probe fixture is still `src/probe-3.16.2.sh`. The Windows
4.0.0 Host bundle has not been independently inspected, and the probe
template is not embedded in the server archive (confirmed for 3.16.3,
3.17.1, 3.17.2, 3.18.2, 3.19.1, and 4.0.0), so the 4.0.0 client probe
text cannot be verified from the server side before connection. The
unchanged bootstrap and ELF layer make a probe change unlikely; if the
4.0.0 client sends a different command, the managed hook safely falls
back to system behavior and the connection fails without environment
overrides, requiring a new captured fixture.

## Adaptation

No server-side behavior change required adaptation in
`src/source_server.py`. The 3.18.2 adaptations — `--prepare-credentials`
on the forward update activation and the opt-in verify daemon start, the
keyring prebuild in the native-module load checks, and the rollback that
appends `--allow-downgrade` for retained releases of 3.17.1 or newer —
apply unchanged to 4.0.0. The adaptation is limited to pinned
identities in `compatibility.json`, the tool version, tests, and
documentation. The README quick start also stopped telling users to
open the previous client version, a leftover from the 0.2.4 cycle that
the 0.2.5 cycle missed.

## Validation

The following automated checks passed on CentOS 7, kernel
`3.10.0-1160.el7.x86_64`, on 2026-11-24:

- Syntax checks, CLI regressions, all 14 Python unit tests, and ShellCheck
  0.11.0. CLI, compatibility metadata, and candidate versions agree.
- Fresh-install integration with the official 4.0.0 archive: preparation
  without activation, repeat installation, native modules and PTY (including
  the keyring prebuild), search tools, immutable release integrity,
  exact retained SSH probe and wrapper, corruption fallback, daemon
  handshake with prepared credential storage, activation-fault rollback,
  incomplete recovery followed by explicit repair, crash/stale-state
  recovery, daemon survival after SSH disconnect, and profile-preserving
  uninstall.
- Cross-version upgrade using the unmodified packaged public 0.2.5 helper
  and official 3.19.1 archive as the upgrade source: a disposable 3.19.1
  daemon was started, 4.0.0 was prepared without changing the active
  pointer, an injected failure after real 4.0.0 activation restored the
  old archive identity, compatibility state, and hook, and the old helper
  verified daemon readiness in the rolled-back state. The subsequent real
  upgrade succeeded.
- The complete suite was rerun with the built local 0.2.6-rc.1 bundle as
  the new helper, including the cross-version upgrade path.
- The release bundle's archive and standalone compatibility metadata
  passed SHA256 verification.

All installations and loopback SSH sessions used temporary HOME directories
under `/tmp`. The production `.bashrc`, server current pointer, and
compatibility state were not touched; no production upgrade or host reboot
was performed.

## Desktop acceptance and stable promotion (2026-11-24)

The user repaired the real default `~/.zcode` installation with the local
0.2.6-rc.1 helper and the official 4.0.0 archive from a plain SSH session
with the desktop disconnected. The compatibility state was refreshed to
tool 0.2.6-rc.1 / ZCode 4.0.0, the 4.0.0 release became active,
`verify` passed, and status reported `"ready": true`. The user then updated
the Windows desktop to ZCode 4.0.0, reconnected, and confirmed completion
of the agreed desktop acceptance scope: SSH connection and reconnection,
remote project access, file creation, reading, and editing, terminal
commands, filename and content searches, Git status, and a short
observable task with disconnect/reconnect persistence. The managed hook
therefore still receives an acceptable probe command from the 4.0.0
client; the probe fixture remains the retained exact 3.16.2 text. The
production derived archive SHA-256 for this host/root is
`63d4899a09fac1d170269114292d962a8b90467d9b7bd27d4d85bf676070f23b`;
it is specific to that installation, not a distributable identity.
Host reboot was not performed or claimed.

After desktop acceptance, the candidate was promoted to stable
**0.2.6**: `end_to_end_verified_zcode_versions` now includes 4.0.0, the
desktop validation entries record the user confirmation, and the pending
list is empty. Local 0.2.6-rc.1 installations require one `repair` with
the stable 0.2.6 helper to refresh the versioned state and support files;
this keeps Server 4.0.0 and is not a downgrade. Automated suites do not
rerun desktop acceptance; that evidence remains the user-confirmed
2026-11-24 result above.
