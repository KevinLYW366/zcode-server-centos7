<!-- Release notes are published verbatim by the release workflow. GitHub
     renders release bodies in comment mode, where each source newline becomes
     a visible line break. Keep every paragraph on a single long line so links
     and sentences do not break mid-paragraph. -->

Windows x64 ZCode 4.0.0 over SSH to CentOS 7 x86-64, with the bundled private runtime. No root access is required; the Windows client stays unchanged.

Download `zcode-server-centos7-0.2.6-zcode-4.0.0-x86_64.tar.gz` (+ `.sha256`) and follow the [installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.6/README.md#quick-start).

Upgrading from 0.2.5 / ZCode 3.19.1: finish remote tasks, disconnect the desktop, then run `source-server repair --archive <official 4.0.0 archive>`, `verify`, and `status --json` with this tool. Reconnect from Windows 4.0.0 only after status reports `"ready": true`.

Desktop acceptance was confirmed by the user on 2026-11-24. Details: [validation record](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.6/docs/ZCODE_4_0_0_COMPATIBILITY.md) · [upgrade policy](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.6/docs/UPGRADE_POLICY.md).

Other clients: find your ZCode version under [previous releases](https://github.com/KevinLYW366/zcode-server-centos7/releases), where each release is titled with the ZCode version it supports. The legacy fixed layout (`0.1.x`) uses [v0.1.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.1.0).
