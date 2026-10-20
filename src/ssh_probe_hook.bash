# Sourced only by the managed .bashrc block. Never print during initialization.
[[ $- != *i* && -n ${SSH_CONNECTION-} && -z ${SSH_TTY-} ]] || return 0
[[ -n ${BASH_EXECUTION_STRING-} ]] || return 0
[[ -r ${HOME}/.zcode/centos7-runtime/source-server/support/probe-3.16.2.sh ]] || return 0
_zcode_probe=$(<"${HOME}/.zcode/centos7-runtime/source-server/support/probe-3.16.2.sh")
# The official SSH backend applies quotePosixShellArg, then /bin/sh -c.
_zcode_quoted=${_zcode_probe//\'/\'\"\'\"\'}
if [[ ${BASH_EXECUTION_STRING} != "${_zcode_probe}" &&
      ${BASH_EXECUTION_STRING} != "/bin/sh -c '${_zcode_quoted}'" ]]; then
    unset _zcode_probe _zcode_quoted
    return 0
fi

getconf() {
    # CentOS 7 /bin/sh imports this function from its parent Bash. Stop its
    # propagation before running diagnostics or any later probe subprocesses.
    export -n -f getconf
    if [[ $# == 1 && $1 == GNU_LIBC_VERSION && $- != *i* &&
          -n ${SSH_CONNECTION-} && -z ${SSH_TTY-} &&
          -r ${HOME}/.zcode/centos7-runtime/source-server/support/probe-3.16.2.sh &&
          ${BASH_EXECUTION_STRING-} == "$(<"${HOME}/.zcode/centos7-runtime/source-server/support/probe-3.16.2.sh")" ]]; then
        if command timeout 8s python3 "${HOME}/.zcode/centos7-runtime/source-server/support/source_server.py" \
            --zcode-root "${HOME}/.zcode" status --probe-getconf 2>/dev/null; then
            return 0
        fi
    fi
    command /usr/bin/getconf "$@"
}

if [[ ${BASH_EXECUTION_STRING} != "${_zcode_probe}" ]]; then
    export -f getconf
fi
unset _zcode_probe _zcode_quoted
