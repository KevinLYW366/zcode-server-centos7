SHELL := /bin/bash

.PHONY: test test-runtime test-source-server lint runtime release clean

test:
	bash tests/test_cli.sh
	python3 tests/test_source_server.py

test-source-server:
	test -n "$(RUNTIME_DIR)" && test -n "$(SOURCE_SERVER_ARCHIVE)"
	python3 tests/integration_source_server.py --runtime-dir "$(RUNTIME_DIR)" --archive "$(SOURCE_SERVER_ARCHIVE)"

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
	bash -n src/ssh_probe_hook.bash
	python3 -c 'import ast,pathlib; [ast.parse(p.read_text(encoding="utf-8")) for p in list(pathlib.Path("src").glob("*.py")) + list(pathlib.Path("tests").glob("*.py"))]'

runtime:
	test -n "$(VSCODE_ARCHIVE)" || { echo "VSCODE_ARCHIVE is required" >&2; exit 2; }
	bash scripts/build-runtime.sh "$(VSCODE_ARCHIVE)"

release:
	bash scripts/build-release.sh

clean:
	rm -rf build dist

