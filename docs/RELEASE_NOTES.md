# 0.3.0 - ZCode 3.16.3 on CentOS 7

This release pins the official Linux x64 Server 3.16.3 archive and uses its
version throughout preparation, CLI validation, installation state, and release
packaging. It retains the private runtime and exact SSH probe hook. The existing
3.16.2 probe fixture keeps its filename; no broader probe matching is enabled.

Desktop-managed updates remain unsupported: their extracted bootstrap Node
has not received the private ELF interpreter and fails before installation on
CentOS 7. Existing 0.2.0 or 0.3.0-rc.1 users must run this release's `source-server repair
--archive PATH` with the official **3.16.3** archive after finishing remote
tasks, then reconnect from Windows 3.16.3. The vendor updater is invoked without
`--force`. Replacing helper files alone does not update the installed server.

The user confirmed completion of Windows ZCode 3.16.3 desktop acceptance on
**2026-10-26**, covering the agreed connection, project operations, and task
persistence scope. This promotes the candidate to **0.3.0**.
The Windows 3.16.3 Host bundle has not been independently inspected.
The user's update log passes environment checks;
automated SSH replay uses the retained exact 3.16.2 probe. Host reboot remains
excluded and untested. See [the validation record](ZCODE_3_16_3_COMPATIBILITY.md).

Use **0.2.0** for the verified 3.16.2 workflow and **0.1.x** for the legacy
fixed `server/node` layout. This release accepts only its pinned 3.16.3
archive; it does not broaden support to an arbitrary version range.

# Previous release: 0.2.0 - ZCode 3.16.2 on CentOS 7

This release adds a remote-only Source Server compatibility workflow.
The Windows ZCode application is unchanged. A managed Bash startup hook uses
the private runtime for `getconf` only when the complete known SSH probe
matches and the installed compatible release passes integrity checks.
The hook matches the official SSH backend's exact `/bin/sh -c` wrapper as well
as the inner probe.
The scoped function is passed to CentOS 7's child shell only for the recognized
wrapper, then stops being exported before diagnostic subprocesses run.

The remote helper verifies the official archive, derives a host-specific
archive with private interpreters for Node, bfs, and ugrep, and installs it
through the original Server CLI. The legacy commands and state remain separate.

Supported target: Windows x64 ZCode **3.16.2**, CentOS 7 x86-64, Bash SSH.
Keep the client pinned to this version and use the remote helper for server
installation and updates. Identical probes do not identify a client version.

A real Windows ZCode 3.16.2 connection was confirmed by the user on
**2026-10-20** after the SSH wrapper correction. The user also confirmed project
opening, file creation/editing, terminal creation, file/content searches, Git
status, and short-task completion after disconnect/reconnect.

Isolated live-update fault injection passed: post-activation verification
failure restored the previous release and running identity; a damaged recovery
archive produced a visible failure, and explicit repair restored readiness.
The second archive changes only gzip metadata around the same verified payload;
this does not test an unknown ZCode release. Recovery from killed temporary
server processes and stale run files passed, as did daemon survival after the
test SSH connection closed.

Host reboot was **not performed** and was explicitly excluded by the user from
the acceptance scope on 2026-10-20. The agreed scope is complete; this does not
claim reboot recovery coverage. See the development document for the
acceptance record and limits.
The inspected vendor `stop` can leave provider helpers alive; isolated tests
clean up their own descendants explicitly. The tool does not force-kill tasks.

When upgrading an existing `0.2.0-rc.1` installation, run the new tool's
`source-server repair --archive PATH` with the supported official 3.16.2
archive. This refreshes the versioned compatibility state and installed hook;
upgrading the tool files alone does not migrate that state. No automatic
production reinstall is performed by publishing this release.

The `0.1.x` line targets the legacy `server/node` layout; its historical
Windows connection results cover 3.11.2, 3.14.3, 3.14.4, 3.14.5, 3.15.1, and
3.15.3. This is an exact list, not a supported version range. Users retaining
that layout should select the legacy release explicitly instead of following
the latest-release link.
