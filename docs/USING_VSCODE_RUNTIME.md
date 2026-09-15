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

After unpacking the resulting runtime archive, use it with the normal
`zcode-centos7 --runtime-dir ... install` flow. Always run the integration test
against a temporary Zcode root before modifying a real installation.

The importer does not install anything below `~/.zcode`. Importing, unpacking,
and integration testing are separate from modifying the real Zcode Node.js.

