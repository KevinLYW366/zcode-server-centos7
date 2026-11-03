<!-- Release notes are published verbatim by the release workflow. GitHub
     renders release bodies in comment mode, where each source newline becomes
     a visible line break. Keep every paragraph on a single long line so links
     and sentences do not break mid-paragraph. -->

Windows x64 ZCode 3.17.2 over SSH to CentOS 7 x86-64, with the bundled private runtime. No root access is required; the Windows client stays unchanged.

Download `zcode-server-centos7-0.2.3-zcode-3.17.2-x86_64.tar.gz` (+ `.sha256`) and follow the [installation guide](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.3/README.md#quick-start).

Upgrading from 0.2.2 / ZCode 3.17.1: finish remote tasks, disconnect the desktop, then run `source-server repair --archive <official 3.17.2 archive>`, `verify`, and `status --json` with this tool. Reconnect from Windows 3.17.2 only after status reports `"ready": true`.

Desktop acceptance was confirmed by the user on 2026-11-03. Details: [validation record](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.3/docs/ZCODE_3_17_2_COMPATIBILITY.md) · [upgrade policy](https://github.com/KevinLYW366/zcode-server-centos7/blob/v0.2.3/docs/UPGRADE_POLICY.md).

Other clients: ZCode 3.17.1 → [v0.2.2](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.2), ZCode 3.16.3 → [v0.2.1](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.1), ZCode 3.16.2 → [v0.2.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.2.0), legacy fixed layout → [v0.1.0](https://github.com/KevinLYW366/zcode-server-centos7/releases/tag/v0.1.0).
