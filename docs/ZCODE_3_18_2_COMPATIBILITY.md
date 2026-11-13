# ZCode 3.18.2 compatibility

Investigation date: 2026-11-13. Candidate tool version: 0.2.4-rc.1.
This is a routine adaptation of the 0.2.3 workflow for the new ZCode
3.18.2 release under the
[versioning policy](UPGRADE_POLICY.md#6-versioning-and-release).

## Failure and scope

The Windows desktop reports that ZCode 3.18.2 is available. As with the
earlier 3.16.3 to 3.17.1 and 3.17.1 to 3.17.2 history, a client update
raises the minimum compatible server version, so the desktop must not be
updated until the CentOS 7 server side is adapted and repaired. The
existing installed 3.17.2 compatible release keeps working with the
pinned 3.17.2 client.

The official 3.18.2 Source Server archive keeps the same bootstrap
structure as 3.17.2: `bin/zcode` is a POSIX shell script that executes
`runtime/node` with `runtime/server-cli.js`. The 3.18.2 server CLI
declares `ZCODE_MIN_COMPATIBLE_VERSION = "3.18.2"`, where 3.17.2
declared `"3.17.2"`; a mixed client/server pair is therefore not
a supported end state and both sides must move together.

## Pinned inputs

- [Official release descriptor](https://cdn-zcode.z.ai/zcode/electron/releases/3.18.2/source-server-release.json).
- [Official Linux x64 archive](https://cdn-zcode.z.ai/zcode/electron/releases/3.18.2/zcode-server-linux-x64.tar.gz).
- Size: 94,268,667 bytes.
- SHA-256: `c4ea27fffb927d076419edfdfa2ccadee1c3176e0ded72a874b6b28f4390d4ff`.
- Runtime identity: `vscode-1.137.0-glibc-2.44-libstdcxx-6.0.36-x86_64`.

The downloaded size and SHA-256 match the official descriptor. A full
file-by-file comparison with the verified 3.17.2 archive found:

- All 12 ELF files of 3.17.2 are byte-identical to their 3.18.2
  counterparts, including Node, bfs, ugrep, ripgrep, and every previous
  native module (`koffi`, `node-pty`, `unsafe-pointer`,
  `opentui-core`). No ELF file was removed.
- One ELF file was added:
  `runtime/node_modules/@napi-rs/keyring-linux-x64-gnu/keyring.linux-x64-gnu.node`.
  Its maximum symbol-version requirement is GLIBC_2.15, below the
  CentOS 7 system glibc 2.17; it is dlopen'd by the patched Node like
  the other prebuilds and stays an unpatched ELF. It is not added to
  the exact patch targets.
- `bin/zcode` is byte-identical; the startup chain is unchanged.
- The new manifest reports appVersion 3.18.2, nodeVersion 22.16.0, and
  target linux-x64. Entrypoints, native modules, and the component
  list keep the 3.17.2 shape. The official-plugins component gains a
  `design-plugin` directory, and the native-search-tools component
  splits its `runtime/tools` path into the three per-tool paths;
  both are handled generically by the component identity logic.
- 516 files were added and 4 removed in total. The additions are the
  `@napi-rs/keyring` packages plus updated JavaScript sources and
  plugin content under `runtime/packages`; the removals are the four
  `read-session-context` files of `@zcode/contracts`. Remaining
  differences are JavaScript/TypeScript sources (`@zcode/contracts`,
  `@zcode/shared`, `@zcode/session-control`, `@zcode/tui`), skill
  text, `server-cli.js`, `server-core.js`, and `zcode.cjs`, plus
  updated component archive entries used by the desktop-managed
  installer, which this tool does not use.

The existing private runtime and the exact patch targets therefore
remain suitable without modification. Node, bfs, and ugrep keep
receiving private interpreters in a derived archive; JavaScript and
other binaries remain unchanged. The pinned executable hashes in
[compatibility.json](../compatibility.json) are unchanged because the
files are unchanged.

The retained probe fixture is still `src/probe-3.16.2.sh`. The Windows
3.18.2 Host bundle has not been independently inspected, and the probe
template is not embedded in the server archive (confirmed for 3.16.3,
3.17.1, 3.17.2, and 3.18.2), so the 3.18.2 client probe text cannot be
verified from the server side before connection. The unchanged
bootstrap and ELF layer make a probe change unlikely; if the 3.18.2
client sends a different command, the managed hook safely falls back to
system behavior and the connection fails without environment
overrides, requiring a new captured fixture.

## Adaptation

Two server-side behavior changes were adapted in `src/source_server.py`,
beyond pinned identities.

First, 3.18.2 introduces remote credential storage for the server data
root (documented in the archive under
`runtime/node_modules/@zcode/shared/src/credential-security/`). The
core refuses to become ready until a private (0600), 32–4096 byte
`credential-secret` file exists under `<ZCode root>/v2`, or an explicit
`ZCODE_CREDENTIAL_SECRET_FILE`/`ZCODE_CREDENTIAL_SECRET` is configured;
headless hosts have no Secret Service, so the file is required. The
official client flow publishes this file: the server CLI accepts
`--prepare-credentials` on `serve` and `update` and then atomically
publishes a 0600 random 32-byte secret under a file lock, never
overwriting an existing secret, an explicit environment configuration,
a pinned `credential-source` marker, or existing `v2` encrypted data.
The helper now passes `--prepare-credentials` on its forward
`update --from-archive` activation — required because a live-upgrade
core restart on 3.18.2 needs the secret before it can become ready —
and on the opt-in `verify --handshake` daemon start, which then matches
the client's remote start command form. The activation-failure rollback
is unchanged: it runs the retained older release's own CLI, whose core
predates the credential requirement.

Second, `src/source_server.py` adds the new
`@napi-rs/keyring-linux-x64-gnu/keyring.linux-x64-gnu.node` prebuild to
the native-module load checks so the fresh-install and verify suites
prove that the one new ELF loads under the private runtime. It stays
unpatched, like the other prebuilds.

The 3.17.1 downgrade guard is kept by the 3.18.2 archive
(`source-server-downgrade-unconfirmed` with `--allow-downgrade`), and
the helper's rollback already appends `--allow-downgrade` for retained
releases of 3.17.1 or newer, so the existing rollback path covers the
3.18.2 to 3.17.2 direction without modification. The node-pty entry
file `runtime/node_modules/node-pty/lib/index.js` still exists with the
same `exports`-without-`main` package shape, and the Node version stays
`v22.16.0`, so the previous version checks remain exact.

## Validation

The following automated checks passed on CentOS 7, kernel
`3.10.0-1160.el7.x86_64`, on 2026-11-13:

- Syntax checks, CLI regressions, all 14 Python unit tests, and ShellCheck
  0.11.0. CLI, compatibility metadata, and candidate versions agree.
- Fresh-install integration with the official 3.18.2 archive: preparation
  without activation, repeat installation, native modules and PTY (including
  the new keyring prebuild), search tools, immutable release integrity,
  exact retained SSH probe and wrapper, corruption fallback, daemon
  handshake with prepared credential storage, activation-fault rollback,
  incomplete recovery followed by explicit repair, crash/stale-state
  recovery, daemon survival after SSH disconnect, and profile-preserving
  uninstall.
- Cross-version upgrade using the unmodified packaged public 0.2.3 helper
  and official 3.17.2 archive as the upgrade source: a disposable 3.17.2
  daemon was started, 3.18.2 was prepared without changing the active
  pointer, an injected failure after real 3.18.2 activation restored the
  old archive identity, compatibility state, and hook, and the old helper
  verified daemon readiness in the rolled-back state. The subsequent real
  upgrade succeeded, including the first 3.18.2 credential-secret
  publication.
- The complete suite was rerun with the built local 0.2.4-rc.1 bundle as
  the new helper, including the cross-version upgrade path.
- The release bundle's archive and standalone compatibility metadata
  passed SHA256 verification.

All installations and loopback SSH sessions used temporary HOME directories
under `/tmp`. The production `.bashrc`, server current pointer, and
compatibility state were not touched; no production upgrade or host reboot
was performed.

## Desktop acceptance and stable promotion (2026-11-13)

The user repaired the real default `~/.zcode` installation with the local
0.2.4-rc.1 helper and the official 3.18.2 archive from a plain SSH session
with the desktop disconnected. The compatibility state was refreshed to
tool 0.2.4-rc.1 / ZCode 3.18.2, the 3.18.2 release became active,
`verify` passed, and status reported `"ready": true`. The user then updated
the Windows desktop to ZCode 3.18.2, reconnected, and confirmed completion
of the agreed desktop acceptance scope: SSH connection and reconnection,
remote project access, file creation, reading, and editing, terminal
commands, filename and content searches, Git status, and a short
observable task with disconnect/reconnect persistence. The managed hook
therefore still receives an acceptable probe command from the 3.18.2
client; the probe fixture remains the retained exact 3.16.2 text. The
production derived archive SHA-256 for this host/root is
`d04d837826124823c8f326de4ca33beeb49a6da2d9a3ffb19be967678815dbdf`;
it is specific to that installation, not a distributable identity.
Host reboot was not performed or claimed.

After desktop acceptance, the candidate was promoted to stable
**0.2.4**: `end_to_end_verified_zcode_versions` now includes 3.18.2, the
desktop validation entries record the user confirmation, and the pending
list is empty. Local 0.2.4-rc.1 installations require one `repair` with
the stable 0.2.4 helper to refresh the versioned state and support files;
this keeps Server 3.18.2 and is not a downgrade. Automated suites do not
rerun desktop acceptance; that evidence remains the user-confirmed
2026-11-13 result above.
