#!/usr/bin/env bash

# Exercise read-only CLI behavior without touching a real Zcode installation.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
CLI="${ROOT_DIR}/bin/zcode-centos7"
TEST_DIR=$(mktemp -d /tmp/zcode-centos7-cli-test.XXXXXX)

cleanup() {
    rm -rf -- "${TEST_DIR}"
}
trap cleanup EXIT

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

assert_contains() {
    local output=$1 expected=$2
    [[ "${output}" == *"${expected}"* ]] || fail "output does not contain: ${expected}"
}

mkdir -p "${TEST_DIR}/.zcode/server"
cp -- /bin/true "${TEST_DIR}/.zcode/server/node"
chmod 0755 "${TEST_DIR}/.zcode/server/node"
printf 'outside-data\n' >"${TEST_DIR}/outside"
OUTSIDE_SHA=$(sha256sum "${TEST_DIR}/outside" | awk '{print $1}')

OUTPUT=$("${CLI}" --version)
assert_contains "${OUTPUT}" "zcode-centos7 0.1.0"

OUTPUT=$("${CLI}" --help)
assert_contains "${OUTPUT}" "inspect"
assert_contains "${OUTPUT}" "uninstall"

OUTPUT=$("${CLI}" --zcode-root "${TEST_DIR}/.zcode" inspect)
assert_contains "${OUTPUT}" "Node SHA256"
assert_contains "${OUTPUT}" "/lib64/ld-linux-x86-64.so.2"

OUTPUT=$("${CLI}" --zcode-root "${TEST_DIR}/.zcode" status)
assert_contains "${OUTPUT}" "Status: not-installed"
[[ ! -e "${TEST_DIR}/.zcode/centos7-runtime" ]] || fail "status created runtime files"

if "${CLI}" --zcode-root / inspect >/dev/null 2>&1; then
    fail "filesystem root was accepted"
fi

mv "${TEST_DIR}/.zcode/server/node" "${TEST_DIR}/real-node"
ln -s "${TEST_DIR}/real-node" "${TEST_DIR}/.zcode/server/node"
if "${CLI}" --zcode-root "${TEST_DIR}/.zcode" inspect >/dev/null 2>&1; then
    fail "symbolic-link target was accepted"
fi

[[ "$(sha256sum "${TEST_DIR}/outside" | awk '{print $1}')" == "${OUTSIDE_SHA}" ]] || \
    fail "unrelated file changed"

printf 'All CLI tests passed.\n'

