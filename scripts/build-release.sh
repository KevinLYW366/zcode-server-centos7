#!/usr/bin/env bash

# Assemble the CLI and a previously built runtime into one release archive.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
VERSION=$(sed -n 's/^readonly PROGRAM_VERSION="\([^"]*\)"/\1/p' \
    "${ROOT_DIR}/bin/zcode-centos7")
RUNTIME_ARCHIVE=${RUNTIME_ARCHIVE:-}

if [[ -z "${RUNTIME_ARCHIVE}" ]]; then
    RUNTIME_ARCHIVE=$(find "${ROOT_DIR}/dist" -maxdepth 1 -type f \
        -name 'zcode-centos7-runtime-*.tar.gz' | sort | tail -n 1)
fi
[[ -f "${RUNTIME_ARCHIVE}" ]] || {
    printf 'runtime archive not found; run make runtime first\n' >&2
    exit 1
}

BUILD_DIR="${ROOT_DIR}/build/release/zcode-server-centos7-${VERSION}"
rm -rf -- "${ROOT_DIR}/build/release"
mkdir -p "${BUILD_DIR}/bin" "${BUILD_DIR}/runtime" "${BUILD_DIR}/docs"
cp -- "${ROOT_DIR}/bin/zcode-centos7" "${BUILD_DIR}/bin/"
cp -- "${ROOT_DIR}/README.md" "${ROOT_DIR}/LICENSE" \
    "${ROOT_DIR}/THIRD_PARTY_NOTICES.md" "${BUILD_DIR}/"
cp -- "${ROOT_DIR}/docs/USING_VSCODE_RUNTIME.md" "${BUILD_DIR}/docs/"
tar -xzf "${RUNTIME_ARCHIVE}" -C "${BUILD_DIR}/runtime" --strip-components=1

TAR_REPRODUCIBLE_ARGS=(--mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner)
if tar --help 2>&1 | grep -q -- '--sort'; then
    TAR_REPRODUCIBLE_ARGS+=(--sort=name)
fi
ARCHIVE_NAME="zcode-server-centos7-${VERSION}-x86_64.tar.gz"
tar "${TAR_REPRODUCIBLE_ARGS[@]}" \
    -czf "${ROOT_DIR}/dist/${ARCHIVE_NAME}" \
    -C "${ROOT_DIR}/build/release" "zcode-server-centos7-${VERSION}"
(
    cd "${ROOT_DIR}/dist"
    sha256sum "${ARCHIVE_NAME}" >"${ARCHIVE_NAME}.sha256"
)



