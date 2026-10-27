# Importing the vscode-server-centos7 Runtime

The x64 release archive produced by
[MikeWang000000/vscode-server-centos7](https://github.com/MikeWang000000/vscode-server-centos7)
can be used as the GNU runtime source for this project.

The verified release 1.137.0 archive has this SHA256:

```text
1ee04fef60c35af3aa981ecba7d44b631a45b2ee611394edcdaa68d7abe2ed8a
```

It contains a glibc 2.44 loader built for a Linux 3.10 minimum kernel and
libstdc++ 6.0.36. These versions satisfy the current Zcode Node.js requirements
of GLIBC 2.28, GLIBCXX 3.4.21, and CXXABI 1.3.9.

The reference loader is specifically built to locate the matching GNU runtime
next to itself. This matters because changing the current Zcode Node.js RPATH
causes that binary to crash. `zcode-centos7` therefore changes only `PT_INTERP`
and leaves the original RPATH/RUNPATH untouched.

The reference archive does not contain a standalone patchelf executable. Its
VS Code launcher embeds libpatchelf and has VS Code-specific path logic. The
importer therefore adds the official statically linked patchelf 0.18.0 x86-64
release after verifying this SHA256:

```text
ce84f2447fb7a8679e58bc54a20dc2b01b37b5802e12c57eece772a6f14bf3f0
```

## Import or build from a source checkout

Release bundles already include the runtime. The commands in this section
are for a repository checkout and run from its root directory.

Import the runtime with:

```bash
curl -fLO https://github.com/MikeWang000000/vscode-server-centos7/releases/download/1.137.0/vscode-server_1.137.0_x64.tar.gz
scripts/import-vscode-runtime.sh \
  ./vscode-server_1.137.0_x64.tar.gz \
  dist
```

To avoid a network request, download patchelf separately and provide it through
the environment:

```bash
PATCHELF_ARCHIVE=/path/to/patchelf-0.18.0-x86_64.tar.gz \
  scripts/import-vscode-runtime.sh \
  ./vscode-server_1.137.0_x64.tar.gz \
  dist
```

The importer extracts only the private GNU runtime libraries. It does not copy
or redistribute the VS Code CLI, VS Code Server, Zcode Server, or Zcode Node.js.

The equivalent Make target is:

```bash
make runtime VSCODE_ARCHIVE="$PWD/vscode-server_1.137.0_x64.tar.gz"
```

Both input archives are checked against fixed SHA256 values. To use the Make
target offline, also set `PATCHELF_ARCHIVE` to the downloaded patchelf archive.
The generated runtime archive is written below `dist/`. Unpack it before
passing it to an installer:

```bash
mkdir -p build/runtime
tar -xzf dist/zcode-centos7-runtime-*.tar.gz -C build/runtime --strip-components=1
```

For the current Source Server workflow:

```bash
bin/zcode-centos7 --runtime-dir build/runtime source-server install --archive "$PWD/zcode-server-linux-x64.tar.gz"
```

For the [legacy workflow](LEGACY.md):

```bash
bin/zcode-centos7 --runtime-dir build/runtime install
```

Always run the relevant integration test against a temporary Zcode root
before modifying a real installation. See the
[Source Server validation instructions](ZCODE_3_16_2_COMPATIBILITY_PLAN.md#3-validation-and-acceptance)
or the [historical development design](LEGACY_DESIGN.md).

The importer does not install anything below `~/.zcode`. Importing, unpacking,
and integration testing are separate from modifying a real Zcode installation.

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
runtime. Redistributed runtimes must retain the upstream license notices,
exact source versions, patches, checksums, and reproducible build instructions.

