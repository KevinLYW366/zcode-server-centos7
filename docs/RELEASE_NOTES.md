# v0.2.2 - ZCode 3.17.1

Supports **Windows x64 ZCode 3.17.1** connecting over SSH to **CentOS 7 x86-64**
with the bundled private runtime. This is a routine adaptation of the existing
Source Server workflow, with no new public commands or state format.

Download `zcode-server-centos7-0.2.2-zcode-3.17.1-x86_64.tar.gz` and its
matching `.sha256` file, then follow the
[installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.2/README.md#quick-start).

- Pins the official 3.17.1 archive and validates the server version from the
  compatibility metadata. A file-by-file comparison found all 12 ELF files,
  the bootstrap script, and the Node version identical to 3.16.3, so the
  private runtime, patch targets, and exact SSH probe are retained unchanged.
- Keeps the README focused on the current release, with links to older guides.
- Uses patch releases for routine ZCode adaptations under the same installation
  model, command contract, and state format. Each tool release declares its
  exact supported ZCode version independently.

For an existing **0.2.1 / ZCode 3.16.3** installation, finish remote tasks and
disconnect the desktop, then run the new tool's
`source-server repair --archive PATH` with the official **3.17.1** archive.
Run `source-server verify` and `source-server status --json`; reconnect from
Windows 3.17.1 only after verification succeeds and status reports
`"ready": true`. Do not update the Windows client before the server side is
repaired: the client raises its minimum compatible server version.
Replacing tool files alone is insufficient.

Windows desktop acceptance for 3.17.1 was confirmed by the user on
**2026-11-02**; it is manual evidence, separate from automated release
checks. The Windows Host bundle has not been independently inspected. Host
reboot remains untested. Desktop-managed server installation and updates
remain unsupported. Local, unpublished **0.2.2-rc.1** users also need repair
with the stable tool to refresh the versioned state and support files.
See the
[validation record](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.2/docs/ZCODE_3_17_1_COMPATIBILITY.md)
and [upgrade guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.2/docs/UPGRADE_POLICY.md).

For ZCode **3.16.3**, retain [v0.2.1](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.1)
and its [installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.1/README.md).
For ZCode **3.16.2**, retain [v0.2.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.0)
and its [installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.0/README.md).
For the legacy fixed `server/node` layout, use
[v0.1.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.1.0)
and the [legacy guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.1.0/README.md).
Historical release notes remain available in the
[v0.2.1 documentation](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.1/docs/RELEASE_NOTES.md).
