#!/usr/bin/env bash
# Restart the OpenCode background server when it runs an older version than the installed binary.
# OpenCode updates (`opencode upgrade`, config `update: auto`) never restart a running server.
set -euo pipefail

bin="${HOME}/.opencode/bin/opencode"
state="${XDG_STATE_HOME:-${HOME}/.local/state}/opencode/service.json"

[[ -x "${bin}" && -r "${state}" ]] || exit 0

installed="$("${bin}" --version | sed -n 's/^opencode v\{0,1\}\([0-9][^ ]*\).*/\1/p')"
running="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${state}")"

if [[ -n "${installed}" && -n "${running}" && "${installed}" != "${running}" ]]; then
    systemctl --user try-restart opencode-server.service
    echo "CHANGED: restarted OpenCode server ${running} -> ${installed}"
fi
