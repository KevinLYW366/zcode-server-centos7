# zcode-server-centos7

`zcode-server-centos7` runs the Zcode remote server Node.js on CentOS 7
without upgrading the system glibc and without changing the runtime environment
of unrelated commands.

The tool has one deliberately narrow target:

```text
~/.zcode/server/node
```

It does not patch other Node.js installations, recursively patch the Zcode
server tree, change shell startup files, or export a compatibility
`LD_LIBRARY_PATH`.

## Quick start

Download these two files from the
[latest GitHub release](../../releases/latest):

- `zcode-server-centos7-<version>-x86_64.tar.gz`
- `zcode-server-centos7-<version>-x86_64.tar.gz.sha256`

Copy them to the CentOS 7 host where Zcode Remote Server is installed, then
run:

```bash
sha256sum -c zcode-server-centos7-<version>-x86_64.tar.gz.sha256
tar -xzf zcode-server-centos7-<version>-x86_64.tar.gz
cd zcode-server-centos7-<version>

bin/zcode-centos7 inspect
bin/zcode-centos7 install
bin/zcode-centos7 verify
```

The release archive includes the compatibility runtime, so release users do
not need to build or download glibc, libstdc++, or patchelf separately. Root
access is not required. Reconnect Zcode after installation.

## Tested compatibility

The following combinations have been verified with a manual end-to-end
remote connection test:

| Zcode client | Client OS | Remote OS | Architecture | Result |
|---|---|---|---|---|
| 3.11.2 | Windows | CentOS 7 | x86-64 | Remote connection successful |

Other Zcode versions may also work, but have not yet been verified.

## Problem

CentOS 7 normally provides glibc 2.17 and the GCC 4.8 C++ runtime. Recent Zcode
Node.js builds require newer ABI versions, such as:

```text
GLIBC_2.25
GLIBC_2.27
GLIBC_2.28
GLIBCXX_3.4.20
GLIBCXX_3.4.21
CXXABI_1.3.9
```

The Node.js process therefore exits before it can complete the Zcode remote
handshake.

## Isolation model

The installer creates a verified backup of the original Zcode Node.js, patches
a temporary copy, tests that copy, and then atomically replaces only
`~/.zcode/server/node`.

The patched ELF contains an interpreter pointing to a private Zcode-only
dynamic loader. The verified loader imported from `vscode-server-centos7`
resolves its matching GNU libraries from its own directory. The installer does
not add or change the Node.js RPATH/RUNPATH.

The resulting process chain is:

```text
Windows Zcode
  -> SSH
  -> ~/.zcode/server/node
  -> ~/.zcode/centos7-runtime/releases/<id>/lib/ld-linux-x86-64.so.2
  -> private glibc, libstdc++, and libgcc
  -> zcode-server.cjs
```

No loader environment variable is added. When Zcode launches `/bin/sh`, Git,
tests, or another system program, that program uses its own ELF interpreter and
the normal CentOS 7 libraries.

The tool never modifies:

- `/lib`, `/lib64`, `/usr/lib`, or `/usr/lib64`;
- `/etc/ld.so.conf` or the system loader cache;
- `.bashrc`, `.bash_profile`, `.profile`, or SSH configuration;
- global `PATH`, `LD_LIBRARY_PATH`, or `LD_PRELOAD` values; or
- Zcode JavaScript files and unrelated executables.

## Inspiration and differences

This project is inspired by
[MikeWang000000/vscode-server-centos7](https://github.com/MikeWang000000/vscode-server-centos7).
That project builds a private glibc and GCC runtime, uses a compatible ELF
patching implementation, redirects VS Code Server executables to the private
loader, and validates the result on CentOS 7.

The reusable implementation ideas are:

1. keep the compatibility runtime in a user-owned directory;
2. redirect an incompatible ELF to a private dynamic loader;
3. include a matching `libstdc++.so.6` and `libgcc_s.so.1` as well as glibc;
4. build for the CentOS 7 kernel baseline; and
5. test the complete remote-server startup path on CentOS 7.

The Zcode implementation is intentionally smaller. The reference project
discovers VS Code commit directories, patches multiple server and extension
executables, monitors extension metadata, and creates a VS Code-specific
requirements-check marker. Zcode starts through a fixed
`~/.zcode/server/node` path, so this project patches that single ELF only. It
does not copy the reference project's VS Code directory discovery, extension
watching, or server packaging code.

The management code in this repository is an original implementation under
the MIT license. The separately packaged glibc, libstdc++, libgcc, and patchelf
components retain their upstream licenses.

## Requirements

- CentOS 7 or a compatible RHEL 7 user space;
- x86-64 CPU architecture;
- Bash 4 or newer;
- GNU `readelf`, `sha256sum`, `readlink`, `awk`, `sed`, and `grep`;
- an installed Zcode remote server at `~/.zcode/server`;
- a runtime directory built by this project or unpacked from a release bundle.

Root access is not required.

## Usage

```text
zcode-centos7 inspect
zcode-centos7 install
zcode-centos7 status
zcode-centos7 verify
zcode-centos7 repair
zcode-centos7 uninstall
```

Common options:

```text
--zcode-root PATH
--runtime-dir PATH
--handshake
```

### Inspect without changing anything

```bash
bin/zcode-centos7 inspect
```

This reports the Node.js checksum, ELF interpreter, RPATH, required ABI
versions, and Zcode runtime metadata location. It does not write files or start
the Zcode server.

### Install from a release bundle

The release bundle contains a `runtime/` directory. When the command is run
from the extracted bundle, no `--runtime-dir` option is needed:

```bash
bin/zcode-centos7 install
```

The installer performs all patching on a temporary Node.js copy. It installs
the runtime and replaces the live Node.js only after checksum, ELF, Node.js,
private-library, and child-shell checks pass.

### Build a runtime from source

The tested runtime source is release 1.137.0 x64 from the reference project.
Download the verified upstream archive, then run:

```bash
curl -fLO https://github.com/MikeWang000000/vscode-server-centos7/releases/download/1.137.0/vscode-server_1.137.0_x64.tar.gz
make runtime VSCODE_ARCHIVE="$PWD/vscode-server_1.137.0_x64.tar.gz"
```

The importer downloads the pinned official static patchelf archive. To build
fully offline, set `PATCHELF_ARCHIVE` to a previously downloaded patchelf
archive. Both inputs are checked against fixed SHA256 values. The output is
written below `dist/`; no VS Code or Zcode executable is copied into it. See
[`docs/USING_VSCODE_RUNTIME.md`](docs/USING_VSCODE_RUNTIME.md) for provenance
and version details.

Unpack the generated archive before passing it to the installer:

```bash
mkdir -p build/runtime
tar -xzf dist/zcode-centos7-runtime-*.tar.gz -C build/runtime --strip-components=1
```

Install a locally built runtime explicitly:

```bash
bin/zcode-centos7 --runtime-dir build/runtime install
```

### Verify

```bash
bin/zcode-centos7 verify
```

The default verification starts only short-lived Node.js and `/bin/sh` test
processes owned by the command. It does not stop an existing Zcode server.

The full Zcode handshake test is opt-in because it starts
`zcode-server.cjs`:

```bash
bin/zcode-centos7 --handshake verify
```

### Repair after a Zcode update

Zcode may replace its Node.js runtime during an update. The tool does not block
or modify the updater. Reapply the compatibility patch explicitly:

```bash
bin/zcode-centos7 repair
```

The new Node.js is backed up under its own SHA256 before it is patched.

### Uninstall

```bash
bin/zcode-centos7 uninstall
```

Uninstall restores the byte-identical original Node.js only when the current
file and saved state agree. Runtime files and backups are retained by default
to avoid destructive cleanup.

## Custom Zcode root

For testing or a non-default installation:

```bash
bin/zcode-centos7 --zcode-root /absolute/path/to/.zcode inspect
```

All modifications remain below that root, and the only server executable that
may be replaced is `<zcode-root>/server/node`.

## Runtime layout

An unpacked runtime has the following interface:

```text
runtime/
├── manifest.env
├── SHA256SUMS
├── bin/
│   └── patchelf
├── lib/
│   ├── ld-linux-x86-64.so.2
│   ├── libc.so.6
│   ├── libstdc++.so.6
│   ├── libgcc_s.so.1
│   └── ...
└── licenses/
```

The installer validates every file listed in `SHA256SUMS` before using the
runtime.

## Development

Run syntax checks and unit tests with:

```bash
make lint
make test
```

## Publishing a release

Set `PROGRAM_VERSION` in `bin/zcode-centos7`, commit the change, then push a
matching tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The release workflow checks the version, runs the test suite, downloads and
verifies the pinned runtime source, builds the self-contained x86-64 archive,
and publishes the archive and its SHA256 file to GitHub Releases.

## Security and failure behavior

- The installer refuses symbolic-link Node.js targets.
- Unknown ELF interpreters are not overwritten.
- Original files are addressed by SHA256 and never silently replaced.
- Changes are made through temporary files on the same filesystem.
- No broad process-killing command is used.
- No daemon, login hook, cron job, or immutable file flag is installed.
- Ambiguous update or uninstall state causes a safe failure.

## License

Project management code is licensed under the MIT License. Runtime artifacts
contain separately licensed upstream components. A distributed runtime must
include the corresponding license notices, exact source versions, patches,
checksums, and reproducible build instructions.

