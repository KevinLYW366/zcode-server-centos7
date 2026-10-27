#!/usr/bin/env bash

# Assemble the CLI and a previously built runtime into one release archive.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
VERSION=$(sed -n 's/^readonly PROGRAM_VERSION="\([^"]*\)"/\1/p' \
    "${ROOT_DIR}/bin/zcode-centos7")
python3 - "${ROOT_DIR}/compatibility.json" "${VERSION}" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    metadata = json.load(f)
assert metadata['tool_version'] == sys.argv[2], 'Compatibility metadata version mismatch'
assert metadata['candidate_zcode_versions'] == [metadata['source_server']['version']], 'Unexpected supported-version set'
if '-' not in sys.argv[2]:
    assert metadata['source_server']['version'] in metadata['end_to_end_verified_zcode_versions'], 'Stable release requires end-to-end evidence'
PY
ZCODE_VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_server"]["version"])' "${ROOT_DIR}/compatibility.json")
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
mkdir -p "${BUILD_DIR}/bin" "${BUILD_DIR}/runtime" "${BUILD_DIR}/docs" "${BUILD_DIR}/src"
cp -- "${ROOT_DIR}/bin/zcode-centos7" "${BUILD_DIR}/bin/"
cp -- "${ROOT_DIR}/README.md" "${ROOT_DIR}/LICENSE" \
    "${ROOT_DIR}/THIRD_PARTY_NOTICES.md" "${BUILD_DIR}/"
cp -- "${ROOT_DIR}/compatibility.json" "${BUILD_DIR}/"
cp -- "${ROOT_DIR}/src/source_server.py" "${ROOT_DIR}/src/ssh_probe_hook.bash" \
    "${ROOT_DIR}/src/probe-3.16.2.sh" "${BUILD_DIR}/src/"
cp -- "${ROOT_DIR}/docs/USING_VSCODE_RUNTIME.md" \
    "${ROOT_DIR}/docs/LEGACY.md" \
    "${ROOT_DIR}/docs/LEGACY_DESIGN.md" \
    "${ROOT_DIR}/docs/ZCODE_3_16_2_COMPATIBILITY_PLAN.md" \
    "${ROOT_DIR}/docs/ZCODE_3_16_3_COMPATIBILITY.md" \
    "${ROOT_DIR}/docs/UPGRADE_POLICY.md" \
    "${ROOT_DIR}/docs/RELEASE_NOTES.md" "${BUILD_DIR}/docs/"
tar -xzf "${RUNTIME_ARCHIVE}" -C "${BUILD_DIR}/runtime" --strip-components=1
python3 - "${BUILD_DIR}" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
metadata = json.loads((root / 'compatibility.json').read_text())
actual = hashlib.sha256((root / 'runtime/SHA256SUMS').read_bytes()).hexdigest()
assert actual == metadata['runtime']['checksum_manifest_sha256'], 'Release requires the canonical runtime manifest'
PY
(cd "${BUILD_DIR}/runtime" && sha256sum -c SHA256SUMS >/dev/null)

TAR_REPRODUCIBLE_ARGS=(--mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner)
if tar --help 2>&1 | grep -q -- '--sort'; then
    TAR_REPRODUCIBLE_ARGS+=(--sort=name)
fi
ARCHIVE_NAME="zcode-server-centos7-${VERSION}-zcode-${ZCODE_VERSION}-x86_64.tar.gz"
tar "${TAR_REPRODUCIBLE_ARGS[@]}" \
    -czf "${ROOT_DIR}/dist/${ARCHIVE_NAME}" \
    -C "${ROOT_DIR}/build/release" "zcode-server-centos7-${VERSION}"
(
    cd "${ROOT_DIR}/dist"
    cp -- "${ROOT_DIR}/compatibility.json" "zcode-server-centos7-${VERSION}-compatibility.json"
    sha256sum "${ARCHIVE_NAME}" >"${ARCHIVE_NAME}.sha256"
    sha256sum "zcode-server-centos7-${VERSION}-compatibility.json" \
        >"zcode-server-centos7-${VERSION}-compatibility.json.sha256"
)



