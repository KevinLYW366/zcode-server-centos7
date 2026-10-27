# v0.2.1 - ZCode 3.16.3

Supports **Windows x64 ZCode 3.16.3** connecting over SSH to **CentOS 7 x86-64**
with the bundled private runtime. This is a routine adaptation of the existing
Source Server workflow, with no new public commands or state format.

Download `zcode-server-centos7-0.2.1-zcode-3.16.3-x86_64.tar.gz` and its matching
`.sha256` file, then follow the
[installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.1/README.md#quick-start).

- Pins the official 3.16.3 archive and validates the server version from the
  compatibility metadata. The private runtime and exact SSH probe are retained.
- Keeps the README focused on the current release, with links to older guides.
- Uses patch releases for routine ZCode adaptations under the same installation
  model, command contract, and state format. Each tool release declares its
  exact supported ZCode version independently.

For an existing **0.2.0 / ZCode 3.16.2** installation, finish remote tasks and
disconnect the desktop, then run the new tool's
`source-server repair --archive PATH` with the official **3.16.3** archive.
Run `source-server verify` and `source-server status --json`; reconnect from
Windows 3.16.3 only after verification succeeds and status reports `"ready": true`.
Local, unpublished **0.3.0** and **0.3.0-rc.1** users also need repair to refresh
the versioned state and support files. Replacing tool files alone is insufficient.

Windows desktop acceptance was confirmed by the user on **2026-10-26**; it is
historical evidence, separate from automated release checks. The Windows Host
bundle has not been independently inspected. Host reboot remains untested.
Desktop-managed server installation and updates remain unsupported.
See the [validation record](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.1/docs/ZCODE_3_16_3_COMPATIBILITY.md)
and [upgrade guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.1/docs/UPGRADE_POLICY.md).

For ZCode **3.16.2**, retain [v0.2.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.0)
and its [installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.0/README.md).
For the legacy fixed `server/node` layout, use
[v0.1.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.1.0)
and the [legacy guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.1.0/README.md).
Historical release notes remain available in the
[v0.2.0 documentation](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.0/docs/RELEASE_NOTES.md).
