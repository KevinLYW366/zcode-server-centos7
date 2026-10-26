# zcode-server-centos7

Run ZCode remote components on CentOS 7 with private runtime libraries.
Tool **0.3.0** supports **Windows x64 ZCode 3.16.3** connecting over SSH to
**CentOS 7 x86-64**. Desktop acceptance was confirmed on 2026-10-26.
The Windows client remains unchanged.

## ZCode 3.16.3

The desktop requires Server 3.16.3 and cannot reuse Server 3.16.2. Its built-in
updater extracts an unpatched bootstrap Node, which cannot start against
CentOS 7's system libraries. Repeating the desktop update does not apply this
tool's private runtime. Use the remote helper to prepare and install the new
archive first.

For an existing **0.2.0** or **0.3.0-rc.1** compatible installation, run from this checkout as
the same SSH user after remote tasks have completed:

```bash
curl -fL https://cdn-zcode.z.ai/zcode/electron/releases/3.16.3/zcode-server-linux-x64.tar.gz \
  -o /tmp/zcode-server-3.16.3-linux-x64.tar.gz
bin/zcode-centos7 source-server repair --archive /tmp/zcode-server-3.16.3-linux-x64.tar.gz
bin/zcode-centos7 source-server verify
```

Repair verifies the pinned official archive and reuses the installed private
runtime. It invokes the vendor updater without `--force`; finish running tasks
before updating. Then reconnect from Windows 3.16.3. Desktop connection,
project operations, and task persistence have passed user acceptance.
Existing 0.3.0-rc.1 users must also run repair to refresh the versioned state
and installed hook. See the [3.16.3 validation record](docs/ZCODE_3_16_3_COMPATIBILITY.md).

## Verified ZCode 3.16.2 release

Tool **0.2.0** remains the verified release for **Windows x64 ZCode 3.16.2**.
The following download and maintenance instructions apply to that release.

For the historical `~/.zcode/server/node` layout, use the **0.1.x** release
line and the [legacy guide](docs/LEGACY.md).

## Requirements

Run the installation on the remote host as the user used for SSH connections:

- CentOS 7 x86-64, Linux kernel 3.10 or newer, with Bash as the SSH login shell.
- Python 3.6+, Bash 4+, GNU `tar`, `timeout`, `readelf`, `sha256sum`,
  `readlink`, `awk`, `sed`, `grep`, `sort`, and `mktemp`.
- `curl` for the download commands below, or transfer the files to the host.
- The default server root, `$HOME/.zcode`, for desktop connections.

No root access is required. The tool bundle includes the private runtime;
release users do not need to build glibc, libstdc++, or patchelf.

## Quick start

Complete these steps on the remote host before connecting from Windows.

1. Download the tool archive and its checksum from the
   [v0.2.0 release](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.0):

   ```bash
   curl -fLO https://github.com/KevinLYW366/zcode-server-centos7/releases/download/v0.2.0/zcode-server-centos7-0.2.0-zcode-3.16.2-x86_64.tar.gz
   curl -fLO https://github.com/KevinLYW366/zcode-server-centos7/releases/download/v0.2.0/zcode-server-centos7-0.2.0-zcode-3.16.2-x86_64.tar.gz.sha256
   sha256sum -c zcode-server-centos7-0.2.0-zcode-3.16.2-x86_64.tar.gz.sha256
   tar -xzf zcode-server-centos7-0.2.0-zcode-3.16.2-x86_64.tar.gz
   cd zcode-server-centos7-0.2.0
   ```

2. Download the official Source Server archive, then install and verify:

   ```bash
   curl -fLO https://cdn-zcode.z.ai/zcode/electron/releases/3.16.2/zcode-server-linux-x64.tar.gz
   bin/zcode-centos7 source-server install --archive "$PWD/zcode-server-linux-x64.tar.gz"
   bin/zcode-centos7 source-server verify
   ```

   Installation checks the official archive against the pinned size and SHA256
   in [compatibility.json](compatibility.json), prepares a compatible archive,
   installs the server, and enables the SSH hook. A separate `prepare` command
   is unnecessary for normal installation.

3. Open **ZCode 3.16.2** on Windows and connect over SSH with the same user.
   If ZCode is already connected, disconnect and reconnect.

## Maintenance

Run these commands from the unpacked tool directory as the same SSH user.

### Check status

```bash
bin/zcode-centos7 source-server status --json
```

Check the `ready` field and any reported error. To repeat short diagnostics,
run `bin/zcode-centos7 source-server verify`; it starts no persistent daemon.

### Repair or refresh an installation

Keep the supported official archive available and run:

```bash
bin/zcode-centos7 source-server repair --archive "$PWD/zcode-server-linux-x64.tar.gz"
```

Use this command for explicit reinstallation and supported server updates.
Existing **0.2.0-rc.1** installations must run it with the **0.2.0** tool to
refresh installed state and hook files; replacing the tool alone is insufficient.

### Check daemon readiness (optional)

```bash
bin/zcode-centos7 source-server verify --handshake
```

This starts or reuses a persistent daemon and checks its ready status. It
leaves the daemon running.

### Disable compatibility

```bash
bin/zcode-centos7 source-server uninstall
```

This removes the managed SSH hook from `.bashrc` while preserving other
content and later user edits. It retains the server, private runtime, derived
archives, and backups, and does not stop server processes.

## Limits and installation changes

- Keep the desktop pinned to **ZCode 3.16.2**. Other client versions are
  unverified, and the SSH probe cannot identify the client version.
- Install and maintain the server with this remote helper. Desktop-managed
  server installation and updates are unsupported; unknown archives are refused.
- Installation adds a marked block to the SSH user's `.bashrc`. It enables
  private-runtime `getconf` only for the exact known SSH probe after integrity
  checks. Ordinary commands retain the system environment; no global
  `LD_LIBRARY_PATH` or `LD_PRELOAD` is added.
- Prepared archives contain host-specific absolute runtime paths; do not copy
  them to another installation root.
- Host reboot recovery has not been tested. This release makes no reboot
  recovery guarantee.

## Further reading and license

- [Legacy 0.1.x guide and historical compatibility](docs/LEGACY.md)
- [Compatibility identities and validation status](compatibility.json)
- [Source Server design and acceptance details](docs/ZCODE_3_16_2_COMPATIBILITY_PLAN.md)
- [Release notes](docs/RELEASE_NOTES.md)
- [Runtime source, build instructions, and layout](docs/USING_VSCODE_RUNTIME.md)

Inspired by [vscode-server-centos7](https://github.com/MikeWang000000/vscode-server-centos7).
Project management code uses the [MIT License](LICENSE). Runtime components
retain their upstream licenses; see [third-party notices](THIRD_PARTY_NOTICES.md)
and the bundled `runtime/licenses/` directory.
