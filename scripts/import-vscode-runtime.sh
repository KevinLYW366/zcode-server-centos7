#!/usr/bin/env bash

# Import only the private GNU runtime from a vscode-server-centos7 archive.
# Zcode and VS Code binaries are never copied into the resulting artifact.

set -euo pipefail

if (($# < 1 || $# > 2)); then
    printf 'Usage: %s <vscode-server-centos7.tar.gz> [output-directory]\n' "$0" >&2
    exit 2
fi

SOURCE_ARCHIVE=$(readlink -f -- "$1")
OUTPUT_DIR=$(readlink -m -- "${2:-dist}")
EXPECTED_SOURCE_SHA256="${VSCODE_ARCHIVE_SHA256:-1ee04fef60c35af3aa981ecba7d44b631a45b2ee611394edcdaa68d7abe2ed8a}"
PATCHELF_VERSION=0.18.0
PATCHELF_SHA256=ce84f2447fb7a8679e58bc54a20dc2b01b37b5802e12c57eece772a6f14bf3f0
PATCHELF_URL="https://github.com/NixOS/patchelf/releases/download/${PATCHELF_VERSION}/patchelf-${PATCHELF_VERSION}-x86_64.tar.gz"
RUNTIME_ID="vscode-1.137.0-glibc-2.44-libstdcxx-6.0.36-x86_64"
WORK_DIR=$(mktemp -d /tmp/zcode-vscode-runtime.XXXXXX)
EXTRACT_DIR="${WORK_DIR}/extract"
RUNTIME_DIR="${WORK_DIR}/${RUNTIME_ID}"
PATCHELF_ARCHIVE="${PATCHELF_ARCHIVE:-${WORK_DIR}/patchelf.tar.gz}"

cleanup() { rm -rf -- "${WORK_DIR}"; }
trap cleanup EXIT

[[ -f "${SOURCE_ARCHIVE}" ]] || {
    printf 'source archive not found: %s\n' "${SOURCE_ARCHIVE}" >&2
    exit 1
}
SOURCE_SHA256=$(sha256sum "${SOURCE_ARCHIVE}" | awk '{print $1}')
[[ "${SOURCE_SHA256}" == "${EXPECTED_SOURCE_SHA256}" ]] || {
    printf 'source archive checksum mismatch\nexpected: %s\nactual:   %s\n' \
        "${EXPECTED_SOURCE_SHA256}" "${SOURCE_SHA256}" >&2
    exit 1
}

if [[ ! -f "${PATCHELF_ARCHIVE}" ]]; then
    command -v curl >/dev/null 2>&1 || {
        printf 'curl is required unless PATCHELF_ARCHIVE is provided\n' >&2
        exit 1
    }
    curl -fL "${PATCHELF_URL}" -o "${PATCHELF_ARCHIVE}"
fi
ACTUAL_PATCHELF_SHA256=$(sha256sum "${PATCHELF_ARCHIVE}" | awk '{print $1}')
[[ "${ACTUAL_PATCHELF_SHA256}" == "${PATCHELF_SHA256}" ]] || {
    printf 'patchelf archive checksum mismatch\n' >&2
    exit 1
}

mkdir -p "${EXTRACT_DIR}" "${RUNTIME_DIR}/bin" "${RUNTIME_DIR}/lib" \
    "${RUNTIME_DIR}/licenses" "${OUTPUT_DIR}"
tar -xzf "${SOURCE_ARCHIVE}" -C "${EXTRACT_DIR}" vscode-server/gnu
tar -xzf "${PATCHELF_ARCHIVE}" -C "${EXTRACT_DIR}" ./bin/patchelf

GNU_DIR="${EXTRACT_DIR}/vscode-server/gnu"
for library in \
    ld-linux-x86-64.so.2 libc.so.6 libm.so.6 libdl.so.2 libpthread.so.0 \
    librt.so.1 libresolv.so.2 libstdc++.so.6 libgcc_s.so.1 libanl.so.1 \
    libatomic.so.1 libnsl.so.1 libnss_compat.so.2 libnss_dns.so.2 \
    libnss_files.so.2 libutil.so.1; do
    [[ -e "${GNU_DIR}/${library}" ]] || {
        printf 'required runtime file is missing: %s\n' "${library}" >&2
        exit 1
    }
    cp -L -- "${GNU_DIR}/${library}" "${RUNTIME_DIR}/lib/${library}"
done

cp -- "${EXTRACT_DIR}/bin/patchelf" "${RUNTIME_DIR}/bin/patchelf"
chmod 0755 "${RUNTIME_DIR}/bin/patchelf" "${RUNTIME_DIR}/lib/ld-linux-x86-64.so.2"

cat >"${RUNTIME_DIR}/manifest.env" <<EOF
RUNTIME_ID=${RUNTIME_ID}
ARCH=x86_64
LOADER=lib/ld-linux-x86-64.so.2
LIB_DIR=lib
PATCHELF=bin/patchelf
EOF

cat >"${RUNTIME_DIR}/licenses/SOURCES.md" <<EOF
# Runtime Sources

- GNU runtime: MikeWang000000/vscode-server-centos7 release 1.137.0 x64
- GNU runtime archive SHA256: ${SOURCE_SHA256}
- Runtime versions: glibc 2.44, libstdc++ 6.0.36
- PatchELF version: ${PATCHELF_VERSION}
- PatchELF archive SHA256: ${PATCHELF_SHA256}

See https://github.com/MikeWang000000/vscode-server-centos7 and
https://github.com/NixOS/patchelf for source code and license information.
EOF

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cp -- "${ROOT_DIR}/THIRD_PARTY_NOTICES.md" "${RUNTIME_DIR}/licenses/THIRD_PARTY_NOTICES.md"
(
    cd "${RUNTIME_DIR}"
    find bin lib licenses -type f -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS
    sha256sum manifest.env >>SHA256SUMS
)

ARCHIVE_PATH="${OUTPUT_DIR}/zcode-centos7-runtime-${RUNTIME_ID}.tar.gz"
ARCHIVE_NAME=$(basename -- "${ARCHIVE_PATH}")
TAR_REPRODUCIBLE_ARGS=(--mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner)
if tar --help 2>&1 | grep -q -- '--sort'; then
    TAR_REPRODUCIBLE_ARGS+=(--sort=name)
fi
tar "${TAR_REPRODUCIBLE_ARGS[@]}" -czf "${ARCHIVE_PATH}" \
    -C "${WORK_DIR}" "${RUNTIME_ID}"
(
    cd "${OUTPUT_DIR}"
    sha256sum "${ARCHIVE_NAME}" >"${ARCHIVE_NAME}.sha256"
)
printf '%s\n' "${ARCHIVE_PATH}"
