# ZCode Upgrade and Compatibility Policy

This guide covers manual adaptation of new ZCode versions by maintainers and
user deployment of verified tool releases. The main development line follows
new ZCode versions: each tool release pins one verified client/server/runtime
combination, while users of older versions retain the corresponding historical
release. Discovering a new version does not establish support or trigger an
automatic production update.

## 1. Current Baseline and Boundaries

The **0.2.1** release supports Windows x64 ZCode
**3.16.3** connecting to CentOS 7 x86-64 / kernel 3.10 / Bash SSH, using Source
Server **3.16.3**. Tool **0.2.0** corresponds to ZCode **3.16.2**; the historical
fixed `server/node` layout uses **0.1.x**. Supported identities and evidence are
recorded in each release's [compatibility.json](../compatibility.json) and
[version-specific validation record](ZCODE_3_16_3_COMPATIBILITY.md). Do not claim
support for an arbitrary version range.

Keep installation under an ordinary user account, with a private runtime and a
managed `.bashrc` SSH hook. Do not replace system libraries, globally set
`LD_LIBRARY_PATH` / `LD_PRELOAD`, or modify the Windows client. Host reboot
remains outside the default acceptance scope; reboot recovery is not guaranteed.

Review these assumptions in the current implementation:

- Node version validation in `src/source_server.py` is fixed at `v22.16.0`,
  and native module paths also follow specific assumptions.
- The exact patch targets are Node, bfs, and ugrep. Inspect all ELF files and
  actual startup dependencies in a new release; do not recursively patch the
  entire directory.
- `src/probe-3.16.2.sh` and its `/bin/sh -c` wrapper require exact matching of
  the complete command. The probe contains no client version.
- The Windows 3.16.3 Host bundle has not been independently inspected. Desktop
  acceptance and byte-identical Host bundles are separate kinds of evidence.
- Current CI runs syntax checks, ShellCheck, and unit tests. It does not run
  real CentOS 7 integration, cross-version upgrades, or Windows acceptance.

## 2. Collect Inputs and Classify Changes

First establish which server version the new client actually requires. A client
version alone does not prove that a server with the same version is required or
compatible. Save the official release descriptor, original archive, and
comparison results in a temporary directory; record sources, dates, sizes, and
SHA256 hashes. Mark missing evidence as "not obtained" or "unverified", never
as passed.

| Required input | Information to record |
|---|---|
| Client | Version, OS/architecture, available build identifiers, installer and Windows Host hashes |
| Official server | Release descriptor, download URL, version, target, size, archive SHA256 |
| Archive layout and execution dependencies | Manifest, installation and startup entry points, added/removed/changed ELF files, Node and native module versions |
| ABI and platform | ELF architecture, interpreter, DT_NEEDED, RPATH/RUNPATH, GLIBC/GLIBCXX/CXXABI and kernel requirements |
| SSH startup chain | Actual probe text, complete wrapped command, environment checks, server version selection, startup protocol |
| Private runtime | Runtime ID, source archive hash, checksum manifest hash, suitability for reuse |
| Upgrade source | Previous stable tool, client, official server archive, state format, data migration requirements |

Apply the following rules based on the comparison. When several categories
change, perform every applicable check:

| Change | Required action |
|---|---|
| Layout, native programs, and probe unchanged | Reuse the runtime and adaptation logic, update the necessary pinned identities, and still complete acceptance |
| Node, native modules, or search tools changed | Inspect ABI and dependencies; adjust version checks, exact targets, and tests as needed; reuse the runtime only after validation |
| Probe or command wrapper changed | Retain evidence of the new commands, adjust exact matching and fixtures, and focus on ordinary SSH, PTY, and child-process isolation |
| Installation protocol, state format, data migration, or kernel requirements changed | Pause routine adaptation and separately review feasibility, migration, and recovery; retain "unsupported" status until that review passes |

The historical 3.16.2 to 3.16.3 comparison found all 12 ELF files identical,
allowing reuse of the existing runtime. Do not extrapolate this result to the
next patch version. If client and server versions diverge, first review the
version relationship assumed by the compatibility metadata, packaging checks,
and tests. Do not enter false versions to bypass validation.

## 3. Make the Minimum Necessary Adaptation

- Use a separate working directory and temporary HOME. Keep the original
  official archive unchanged; derived archives belong only to the corresponding
  installation root on that host.
- Update candidate identities, official archive size and hash, exact executable
  hashes, and applicable limitations in `compatibility.json`. Start the new
  version with acceptance pending. Do not copy previous dates, user confirmations,
  or passing results.
- Change checks, patch targets, probes, and related tests only where evidence
  requires it. Continue rejecting unknown archives, preserving original
  RPATH/RUNPATH, and isolating ordinary command environments. Do not use probe
  substring matching.
- Review the CLI version, the release script's document copy list, and the pinned
  runtime source in the workflow. If the runtime changes, update build sources,
  hashes, licenses, and recovery tests together.
- Keep the existing `source-server` commands; do not add public CLI commands for
  this manual update workflow.

## 4. Acceptance in an Isolated Environment

Run the following commands from the source root of the proposed release. Replace
example absolute paths before running them. The previous tool must be an original
release bundle with all support files, rather than a copied CLI alone.
`--runtime-dir` points to an unpacked runtime containing `manifest.env` and
`SHA256SUMS`.

Run the same basic checks as CI:

```bash
make lint
make test
shellcheck bin/zcode-centos7 src/ssh_probe_hook.bash scripts/*.sh tests/*.sh
```

Run fresh-install integration on real CentOS 7 / kernel 3.10:

```bash
make test-source-server \
  RUNTIME_DIR=/absolute/path/to/runtime \
  SOURCE_SERVER_ARCHIVE=/absolute/path/to/new-official-server.tar.gz
```

Run a real upgrade from the previous stable release, including recovery from a
failure after activation:

```bash
python3 tests/integration_source_server.py \
  --runtime-dir /absolute/path/to/runtime \
  --archive /absolute/path/to/new-official-server.tar.gz \
  --previous-cli /absolute/path/to/previous-tool/bin/zcode-centos7 \
  --previous-archive /absolute/path/to/previous-official-server.tar.gz
```

The integration script creates a temporary HOME and separate `.zcode`, uses
loopback SSH, and cleans up its own test processes. Restrict fault injection to
these temporary objects; never substitute a production directory. The original
previous tool must accept the runtime used in the test. If the runtime identity
changes, add upgrade and recovery validation using the old and new runtimes
separately; do not weaken the previous tool's checks.

Verify and record:

- Fresh installation, repeated installation, prepare without activation, repair,
  `status --json`, verify, daemon handshake, and uninstall.
- Node, self-spawning/child processes, native modules, real PTY creation, search
  tools, and immutable release content integrity.
- Successful original and officially wrapped probes. Altered probes, ordinary
  SSH, PTY sessions, interactive shells, and different arguments must not trigger
  the compatibility override. Damaged state or files must fall back to system
  behavior.
- A real upgrade from the previous stable release. Failure after activation must
  restore the old service's running identity, compatibility state, and hook.
  Damaged recovery material must produce an explicit incomplete-recovery error;
  repair must restore readiness.
- Recovery from crashes and stale PID/socket state, and daemon survival after a
  short-lived connection closes. These checks do not establish reboot recovery.
- Isolation of unrelated `.bashrc` content, existing user tasks, and system
  command environments.

Existing scripts do not replace tests for newly introduced changes. If the
probe, runtime, or state format changes, additionally verify its failure recovery
paths. Historical rollback between identical probes and runtimes does not cover
these scenarios. The default upgrade source is the previous stable release;
upgrades that skip versions or cross installation models require separate
validation and documented paths.

## 5. Windows Acceptance and Stable Release Gate

After server checks pass, use the candidate tool and specified Windows build in
a test environment to verify:

- SSH connection and reconnection, and opening a remote project.
- Creating, reading, and editing files; creating a terminal and running shell
  commands.
- Filename and content searches, Git status, and short project tasks.
- Starting an observable short task, disconnecting and reconnecting, and checking
  its result and persistence.

Record operator confirmation, date, client identity, and results. Distinguish
automated output from manual confirmation. A release with passing server checks
but no desktop acceptance remains a candidate and must not enter the end-to-end
verified list. Update `validation`,
`end_to_end_verified_zcode_versions`, and stable status only after evidence covers
all agreed acceptance requirements.

The packaging script checks stable eligibility through compatibility metadata;
it does not independently perform or prove manual acceptance. Promoting a
candidate to stable changes the tool version, which affects installed state.
Run repair with the stable tool to refresh state and support files, then recheck
verify, readiness, and desktop connectivity.

## 6. Versioning and Release

- Tool versions are independent of ZCode. While below 1.0, routine ZCode
  adaptations, fixes, and metadata updates increment the patch version when
  the installation model, command contract, and state format remain unchanged.
  For example, `0.2.0` supports ZCode 3.16.2 and `0.2.1` supports ZCode 3.16.3.
  Each release pins its own verified combination; a shared `0.2.x` prefix does
  not imply support for the same client versions.
- Increment the minor version for new tool capabilities or changes to the
  installation model, command contract, state format, or migration requirements.
  Code complexity alone does not determine the version. Use `-rc.N` while
  acceptance is incomplete.
- A changed archive hash under the same official version also requires
  reassessment. Retain the old identity and source, and publish a new tool and
  compatibility record. Do not silently relax hash checks or overwrite published
  artifacts.
- Keep the CLI version, compatibility metadata, README, release notes, and
  version-specific validation record synchronized. Validation records preserve
  historical facts. Rewrite the README's existing quick start and maintenance
  instructions for the latest release instead of appending version-specific
  tutorials. Link historical instructions through fixed tags or separate guides.
- Record the supported combination, previous stable upgrade source, recovery
  conditions, missing evidence, and unverified items. Follow existing script
  checks for artifact names, Git tags, and tool versions. Include this guide and
  validation documents in the bundle.
- Build with an explicit runtime archive and verify the artifacts, for example:

  ```bash
  RUNTIME_ARCHIVE=/absolute/path/to/verified-runtime.tar.gz make release
  ```

  Check bundled documents, runtime and compatibility metadata, archive SHA256,
  and the standalone compatibility metadata SHA256. A derived archive's hash
  belongs to local installation state, not a universal official archive identity.
  Do not redistribute proprietary ZCode archives.
- Retain historical releases and direct older users to explicit version links.
  Do not rely solely on `latest` for users with different installation layouts.
  Review CI, integration, and desktop evidence before publishing. Pushing a `v*`
  tag triggers the release workflow; document checks do not require pushing tags.

## 7. User Deployment and Recovery

The verified stable upgrade source for `0.2.1` is tool `0.2.0` with ZCode
3.16.2. Local, unpublished `0.3.0` and `0.3.0-rc.1` builds for ZCode 3.16.3
also require repair with `0.2.1` to refresh the tool-versioned state and support
files. This keeps the same server version; it is not a server downgrade.
See the [3.16.3 validation record](ZCODE_3_16_3_COMPATIBILITY.md) for results.
The `0.1.x` installation model requires its separate
[legacy guide](LEGACY.md); this release does not claim a direct legacy upgrade.

Deploy only a release that explicitly supports the current client. Before
upgrading, finish remote tasks, disconnect the desktop, and retain the complete
previous tool directory, old official archive, compatibility metadata, installed
state, and local derived archives/runtime/backups. Do not clean up this recovery
material during an upgrade. Derived archives embed their original absolute paths
and cannot be moved to another home directory or installation root.

Verify and unpack the new tool and obtain its explicitly supported official
archive. Then run the following from the new tool directory as the same SSH user.
This is a procedure template: replace
`/absolute/path/to/supported-official-server.tar.gz` with the verified actual path.

```bash
bin/zcode-centos7 source-server repair \
  --archive /absolute/path/to/supported-official-server.tar.gz
bin/zcode-centos7 source-server verify
bin/zcode-centos7 source-server status --json
```

Check each exit status and stop subsequent steps if any command fails. Connect
the matching new client only after verify succeeds and status reports `ready`
as `true`. To explicitly check daemon readiness, run
`bin/zcode-centos7 source-server verify --handshake`; it starts or reuses a daemon
and leaves it running. The updater does not use `--force`. Replacing tool files
alone does not migrate the server or its state.

After failure, retain redacted logs and check the active server version, running
state, and recovery outcome using a tool that matches the restored state. If
recovery is incomplete, follow that release's verified recovery procedure. Do not
repeat desktop installation or manually edit pointers or state. Automatic rollback
of failed activation does not guarantee downgrade at any time. Publish manual
downgrade commands only after verifying server downgrade and data compatibility;
repair with an older tool is not a general downgrade guarantee.

If the client has already been upgraded while the server has reverted, use the
previous matching client or wait for adaptation. Do not let the new client force
another unsupported installation. `uninstall` only removes the compatibility hook;
it is not a version rollback command.

## 8. Per-Release Maintainer Checklist

Copy this checklist into the version-specific validation record and fill in each
result and evidence location. Distinguish passed, failed, pending, and excluded
items. Give reasons for exclusions; exclusions do not establish verification of
the corresponding feature.

- [ ] Record the new client identity, official server requirements, upgrade source, and official archive size/SHA256.
- [ ] Compare Windows Host, probe and wrapper, manifest, ELF files, ABI, installation protocol, and migration requirements; identify missing evidence.
- [ ] Classify changes, complete required separate reviews, and justify runtime reuse or replacement.
- [ ] Update necessary identities, exact adaptation, and related tests; do not inherit previous passing results into candidate status.
- [ ] Pass syntax checks, unit tests, and ShellCheck.
- [ ] Pass CentOS 7 / kernel 3.10 fresh-install, idempotency, runtime functionality, and SSH/child-process isolation checks.
- [ ] Pass a real upgrade from the previous stable release, post-activation failure recovery, damaged recovery material checks, and explicit repair.
- [ ] Pass additional recovery tests for runtime/probe/state changes; explicitly state when upgrades that skip versions are unverified.
- [ ] Retain confirmation of Windows connection, project/file/terminal/search/Git operations, and short-task disconnect/reconnect acceptance.
- [ ] Separate automated and manual evidence, disclose Host identity gaps and unverified areas such as reboot, and confirm stable eligibility.
- [ ] Synchronize README, versions, compatibility metadata, release notes, validation records, and bundle contents; verify hashes.
- [ ] Document upgrade and recovery procedures, retain historical releases and local recovery material, and check state and connectivity after deployment.
