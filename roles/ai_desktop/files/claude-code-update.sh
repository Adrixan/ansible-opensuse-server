#!/usr/bin/env bash
# Install the newest Claude Code release of the npm `latest` channel that is at least <hours> old
# (supply-chain cooldown; Peter, 2026-11-20: "latest + 24 h everywhere"). Never downgrades: a newer
# release that is already installed stays until the cooldown catches up with it.
# Usage: claude-code-update <claude binary> <hours> [--check]
# Prints UP_TO_DATE or CHANGED; exits 1 when the version cannot be determined (the unit retries).
set -euo pipefail

readonly HELPER=/usr/local/libexec/release-past-cooldown
readonly SEMVER='^[0-9]+\.[0-9]+\.[0-9]+$'

[[ $# -ge 2 && $# -le 3 && $2 =~ ^[0-9]+$ && ${3:---check} == --check ]] || {
    echo "usage: claude-code-update <claude binary> <hours> [--check]" >&2
    exit 2
}
bin=$1 hours=$2 check=${3:-}

version_of() { "$bin" --version 2>/dev/null | awk 'NR == 1 { print $1 }'; }

installed=$(version_of)
[[ $installed =~ $SEMVER ]] || { echo "ERROR: cannot read the version of $bin" >&2; exit 1; }
target=$(python3 -I "$HELPER" npm @anthropic-ai/claude-code "$hours") \
    || { echo "ERROR: no release past the ${hours} h cooldown found (registry unreachable?), $installed kept" >&2; exit 1; }
[[ $target =~ $SEMVER ]] || { echo "ERROR: unexpected version '$target' from the registry" >&2; exit 1; }

if [[ $(printf '%s\n%s\n' "$target" "$installed" | sort -V | tail -n 1) == "$installed" ]]; then
    echo "UP_TO_DATE: $installed (newest past the ${hours} h cooldown: $target)"
    exit 0
fi
if [[ $check == --check ]]; then
    echo "CHANGED: would install $target over $installed"
    exit 0
fi
"$bin" install "$target"
now=$(version_of)
[[ $now == "$target" ]] || { echo "ERROR: $bin reports '$now' after installing $target" >&2; exit 1; }
echo "CHANGED: $installed -> $target"
