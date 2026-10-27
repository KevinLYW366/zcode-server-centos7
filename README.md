# zcode-server-centos7

Run ZCode remote components on CentOS 7 with private runtime libraries.
Release **0.2.1** supports **Windows x64 ZCode 3.16.3** connecting over SSH to
**CentOS 7 x86-64**. No root access is required; the Windows client remains
unchanged. The tool bundle includes the private runtime.

## Requirements

- CentOS 7 x86-64, Linux kernel 3.10 or newer, with Bash as the SSH login shell.
- Python 3.6+, Bash 4+, GNU `tar`, `timeout`, `readelf`, `sha256sum`,
  `readlink`, `awk`, `sed`, `grep`, `sort`, and `mktemp`.
- `curl` for the downloads below, or transfer the files to the host.
- The default server root, `$HOME/.zcode`, for desktop connections.

Run the commands on the remote host as the user used for SSH connections.
Continue to the next command only after the previous one succeeds.

## Quick start

Complete the remote installation before connecting from Windows.

1. Download and verify the tool from the
   [v0.2.1 release](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.1):

   ```bash
   curl -fLO https://github.com/KevinLYW366/zcode-server-centos7/releases/download/v0.2.1/zcode-server-centos7-0.2.1-zcode-3.16.3-x86_64.tar.gz
   curl -fLO https://github.com/KevinLYW366/zcode-server-centos7/releases/download/v0.2.1/zcode-server-centos7-0.2.1-zcode-3.16.3-x86_64.tar.gz.sha256
   sha256sum -c zcode-server-centos7-0.2.1-zcode-3.16.3-x86_64.tar.gz.sha256
   tar -xzf zcode-server-centos7-0.2.1-zcode-3.16.3-x86_64.tar.gz
   cd zcode-server-centos7-0.2.1
   ```

2. Download the official Source Server archive, then install and verify:

   ```bash
   curl -fLO https://cdn-zcode.z.ai/zcode/electron/releases/3.16.3/zcode-server-linux-x64.tar.gz
   bin/zcode-centos7 source-server install --archive "$PWD/zcode-server-linux-x64.tar.gz"
   bin/zcode-centos7 source-server verify
   bin/zcode-centos7 source-server status --json
   ```

   Installation verifies the official size and SHA256 in
   [compatibility.json](compatibility.json), prepares a compatible archive,
   installs the server, and enables the SSH hook. A separate `prepare` command
   is unnecessary. Connect only after verification succeeds and status reports
   `"ready": true`.

3. Open **ZCode 3.16.3** on Windows and connect over SSH with the same user.

## Upgrade and maintenance

Run these commands from the unpacked **0.2.1** tool directory.

### Upgrade or repair

Finish remote tasks and disconnect the desktop. Retain the previous tool,
official archive, and installed recovery material, then download and unpack
the current tool and official archive as shown above. Run:

```bash
bin/zcode-centos7 source-server repair --archive "$PWD/zcode-server-linux-x64.tar.gz"
bin/zcode-centos7 source-server verify
bin/zcode-centos7 source-server status --json
```

Reconnect from Windows **3.16.3** only after verification succeeds and status
reports `"ready": true`. Repair refreshes the server, versioned state, and
installed support files; replacing the tool files alone is insufficient.
Stop on any failure and check recovery before retrying. Supported upgrade
sources and recovery procedures are in the
[upgrade guide](docs/UPGRADE_POLICY.md#7-user-deployment-and-recovery).

### Check status

```bash
bin/zcode-centos7 source-server status --json
bin/zcode-centos7 source-server verify
```

To check daemon readiness, run
`bin/zcode-centos7 source-server verify --handshake`. This starts or reuses a
persistent daemon and leaves it running; ordinary `verify` starts none.

### Disable compatibility

```bash
bin/zcode-centos7 source-server uninstall
```

This removes the managed SSH hook from `.bashrc`, preserving unrelated content
and later edits. It retains the server, runtime, archives, and backups, and
does not stop server processes or roll back the server version.

## Limits

- Keep the desktop pinned to **ZCode 3.16.3**. Other versions require separate
  validation; the SSH probe cannot identify the client version.
- Install and update through the remote helper. Desktop-managed updates run
  an unpatched bootstrap Node that cannot start with CentOS 7's system libraries.
- The managed `.bashrc` hook enables the private runtime only for the exact
  known SSH probe after integrity checks. Ordinary commands use the system
  environment; no global `LD_LIBRARY_PATH` or `LD_PRELOAD` is added.
- Prepared archives contain host-specific absolute paths. Do not copy them to
  another installation root.
- Host reboot recovery has not been tested or guaranteed.

## Documentation and previous versions

- [Release notes](docs/RELEASE_NOTES.md)
- [Upgrade policy and recovery guide](docs/UPGRADE_POLICY.md)
- [ZCode 3.16.3 validation record](docs/ZCODE_3_16_3_COMPATIBILITY.md)
- [Runtime source and build instructions](docs/USING_VSCODE_RUNTIME.md)
- [ZCode 3.16.2 installation guide (v0.2.0)](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.0/README.md)
- [Legacy 0.1.x guide](docs/LEGACY.md)

Inspired by [vscode-server-centos7](https://github.com/MikeWang000000/vscode-server-centos7).
Project management code uses the [MIT License](LICENSE). Runtime components
retain their upstream licenses; see [third-party notices](THIRD_PARTY_NOTICES.md)
and the bundled `runtime/licenses/` directory.
