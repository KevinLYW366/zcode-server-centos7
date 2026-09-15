SHELL := /bin/bash

.PHONY: test test-runtime lint runtime release clean

test:
	bash tests/test_cli.sh

test-runtime:
	test -n "$(RUNTIME_DIR)" || { echo "RUNTIME_DIR is required" >&2; exit 2; }
	test -n "$(NODE_BINARY)" || { echo "NODE_BINARY is required" >&2; exit 2; }
	bash tests/test_runtime_integration.sh "$(RUNTIME_DIR)" "$(NODE_BINARY)"

lint:
	bash -n bin/zcode-centos7
	bash -n scripts/build-runtime.sh
	bash -n scripts/import-vscode-runtime.sh
	bash -n scripts/build-release.sh
	bash -n tests/test_cli.sh
	bash -n tests/test_runtime_integration.sh

runtime:
	test -n "$(VSCODE_ARCHIVE)" || { echo "VSCODE_ARCHIVE is required" >&2; exit 2; }
	bash scripts/build-runtime.sh "$(VSCODE_ARCHIVE)"

release:
	bash scripts/build-release.sh

clean:
	rm -rf build dist

