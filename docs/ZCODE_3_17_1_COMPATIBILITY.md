# ZCode 3.17.1 compatibility

Investigation date: 2026-10-30. Candidate tool version: 0.2.2-rc.1.
This is a routine adaptation of the 0.2.1 workflow for the new ZCode
3.17.1 release under the
[versioning policy](UPGRADE_POLICY.md#6-versioning-and-release).

## Failure and scope

The Windows desktop reports that ZCode 3.17.1 is available. Based on the
3.16.2 to 3.16.3 history, a client update raises the minimum compatible
server version, so the desktop must not be updated until the CentOS 7
server side is adapted and repaired. The existing installed 3.16.3
compatible release keeps working with the pinned 3.16.3 client.

The official 3.17.1 Source Server archive keeps the same bootstrap
structure as 3.16.3: `bin/zcode` is a POSIX shell script that executes
`runtime/node` with `runtime/server-cli.js`. Running the 3.17.1 Node with
the system loader on CentOS 7 reproduces the historical dynamic library
failures; the private-runtime derivation workflow remains required.

## Pinned inputs

- [Official release descriptor](https://cdn-zcode.z.ai/zcode/electron/releases/3.17.1/source-server-release.json).
- [Official Linux x64 archive](https://cdn-zcode.z.ai/zcode/electron/releases/3.17.1/zcode-server-linux-x64.tar.gz).
- Size: 91,071,879 bytes.
- SHA-256: `ec11bd918516d9468a0d746d00ff792a9521f345304190877d5e9d43131ca38d`.
- Runtime identity: `vscode-1.137.0-glibc-2.44-libstdcxx-6.0.36-x86_64`.

The downloaded size and SHA-256 match the official descriptor. A full
file-by-file comparison with the verified 3.16.3 archive found:

- All 12 ELF files are byte-identical to their 3.16.3 counterparts,
  including Node, bfs, ugrep, ripgrep, and every native module
  (`koffi`, `node-pty`, `unsafe-pointer`, `opentui-core`). No ELF file
  was added or removed.
- `bin/zcode` is byte-identical; the startup chain is unchanged.
- The new manifest reports appVersion 3.17.1, nodeVersion 22.16.0, and
  target linux-x64. Entrypoints, native modules, and tool lists keep the
  3.16.3 shape; the plugin list adds `zcode-site`.
- Remaining differences are JavaScript/TypeScript sources under
  `runtime/node_modules` and updated component archive entries
  (server-runtime, agent-runtime, official-plugins, native-search-tools)
  used by the desktop-managed installer, which this tool does not use.

The existing private runtime and the exact patch targets therefore remain
suitable without modification. Node, bfs, and ugrep keep receiving private
interpreters in a derived archive; JavaScript and other binaries remain
unchanged. The pinned executable hashes in
[compatibility.json](../compatibility.json) are unchanged because the
files are unchanged.

The retained probe fixture is still `src/probe-3.16.2.sh`. The Windows
3.17.1 Host bundle has not been independently inspected, and the probe
template is not embedded in the server archive (confirmed for both 3.16.3
and 3.17.1), so the 3.17.1 client probe text cannot be verified from the
server side before connection. The unchanged bootstrap and ELF layer make
a probe change unlikely; if the 3.17.1 client sends a different command,
the managed hook safely falls back to system behavior and the connection
fails without environment overrides, requiring a new captured fixture.

## Adaptation

One source change beyond pinned identities was required. The 3.17.1 archive
replaces `node-pty` 1.1.0 with `@lydell/node-pty-linux-x64` 1.2.0-beta.10,
whose `package.json` declares `"exports"` but no `"main"`. Absolute-path
`require()` of the package directory therefore no longer resolves under
CommonJS directory rules, while the server's own bare-specifier
`require("node-pty")` still resolves through `"exports"`. The PTY acceptance
check in `src/source_server.py` now requires
`runtime/node_modules/node-pty/lib/index.js` directly. The `pty.node`
prebuild is byte-identical to 3.16.3, so no ABI change is involved.

## Validation

The following automated checks passed on CentOS 7, kernel
`3.10.0-1160.el7.x86_64`, on 2026-10-30:

- Syntax checks, CLI regressions, all 14 Python unit tests, and ShellCheck
  0.11.0. CLI, compatibility metadata, and candidate versions agree.
- Fresh-install integration with the official 3.17.1 archive: preparation
  without activation, repeat installation, native modules and PTY, search
  tools, immutable release integrity, exact retained SSH probe and wrapper,
  corruption fallback, daemon handshake, activation-fault rollback,
  incomplete recovery followed by explicit repair, crash/stale-state
  recovery, daemon survival after SSH disconnect, and profile-preserving
  uninstall.
- Cross-version upgrade using the unmodified packaged public 0.2.1 helper
  and official 3.16.3 archive as the upgrade source: a disposable 3.16.3
  daemon was started, 3.17.1 was prepared without changing the active
  pointer, an injected failure after real 3.17.1 activation restored the
  old archive identity, compatibility state, and hook, and the subsequent
  real upgrade succeeded. The old helper verified daemon readiness in the
  rolled-back state.
- The complete suite was rerun with the built local 0.2.2-rc.1 bundle as
  the new helper, including the cross-version upgrade path.
- The release bundle's archive and standalone compatibility metadata
  passed SHA256 verification.

All installations and loopback SSH sessions used temporary HOME directories
under `/tmp`. The production `.bashrc`, server current pointer, and
compatibility state were not touched; no production upgrade or host reboot
was performed.

Windows ZCode 3.17.1 desktop acceptance is pending. Until the user confirms
it, 0.2.2 remains a candidate (`0.2.2-rc.1`) and 3.17.1 must not be added to
`end_to_end_verified_zcode_versions`. Host reboot remains explicitly excluded
by the user's earlier instruction.
