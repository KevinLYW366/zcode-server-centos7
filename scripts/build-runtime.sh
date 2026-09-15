#!/usr/bin/env bash

# Import the verified private runtime from a vscode-server-centos7 archive.

set -euo pipefail

if (($# != 1)); then
    printf 'Usage: %s <vscode-server-centos7.tar.gz>\n' "$0" >&2
    exit 2
fi

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
exec "${ROOT_DIR}/scripts/import-vscode-runtime.sh" "$1" "${ROOT_DIR}/dist"


