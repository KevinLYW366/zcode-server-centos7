# 0.2.0 - ZCode 3.16.2 on CentOS 7

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
