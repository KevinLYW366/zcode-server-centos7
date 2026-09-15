#!/usr/bin/env bash

# Run an install/verify/uninstall cycle entirely inside a temporary Zcode root.

set -euo pipefail

if (($# < 2 || $# > 3)); then
    printf 'Usage: %s <runtime-dir> <node-binary> [cli]\n' "$0" >&2
    exit 2
fi

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
CLI=${3:-"${ROOT_DIR}/bin/zcode-centos7"}
RUNTIME_DIR=$(readlink -f -- "$1")
NODE_SOURCE=$(readlink -f -- "$2")
TEST_DIR=$(mktemp -d /tmp/zcode-centos7-integration.XXXXXX)

cleanup() {
    rm -rf -- "${TEST_DIR}"
}
trap cleanup EXIT

mkdir -p "${TEST_DIR}/.zcode/server"
cp -p -- "${NODE_SOURCE}" "${TEST_DIR}/.zcode/server/node"
printf 'must-not-change\n' >"${TEST_DIR}/unrelated-task-data"
NODE_SHA=$(sha256sum "${TEST_DIR}/.zcode/server/node" | awk '{print $1}')
UNRELATED_SHA=$(sha256sum "${TEST_DIR}/unrelated-task-data" | awk '{print $1}')
ORIGINAL_RPATH=$(readelf -d "${TEST_DIR}/.zcode/server/node" 2>/dev/null | \
    sed -n 's/.*\(RPATH\|RUNPATH\).*Library rpath: \[\(.*\)\]/\2/p' | head -n 1)

DEFAULT_RUNTIME=$(readlink -m -- "$(dirname -- "${CLI}")/../runtime")
if [[ "${DEFAULT_RUNTIME}" == "${RUNTIME_DIR}" ]]; then
    "${CLI}" --zcode-root "${TEST_DIR}/.zcode" install
else
    "${CLI}" --zcode-root "${TEST_DIR}/.zcode" --runtime-dir "${RUNTIME_DIR}" install
fi
PATCHED_INTERPRETER=$(readelf -l "${TEST_DIR}/.zcode/server/node" | \
    sed -n 's/.*Requesting program interpreter: \(.*\)]/\1/p' | head -n 1)
PATCHED_RPATH=$(readelf -d "${TEST_DIR}/.zcode/server/node" 2>/dev/null | \
    sed -n 's/.*\(RPATH\|RUNPATH\).*Library rpath: \[\(.*\)\]/\2/p' | head -n 1)
[[ "${PATCHED_INTERPRETER}" == "${TEST_DIR}/.zcode/centos7-runtime/"* ]]
[[ "${PATCHED_RPATH}" == "${ORIGINAL_RPATH}" ]]
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" verify
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" status | grep -q 'State drift: no'

# Simulate an updater replacing Node.js, then require an explicit repair.
cp -p -- "${NODE_SOURCE}" "${TEST_DIR}/.zcode/server/node"
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" status | grep -q 'State drift: yes'
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" repair
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" verify
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" status | grep -q 'State drift: no'
"${CLI}" --zcode-root "${TEST_DIR}/.zcode" uninstall

[[ "$(sha256sum "${TEST_DIR}/.zcode/server/node" | awk '{print $1}')" == "${NODE_SHA}" ]]
[[ "$(sha256sum "${TEST_DIR}/unrelated-task-data" | awk '{print $1}')" == "${UNRELATED_SHA}" ]]
printf 'Runtime integration test passed.\n'

