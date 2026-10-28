#!/bin/bash
# Managed by Ansible (ai_workstation): update the Phở Research Tools lockfile to the newest versions the
# workspace ranges allow, then install the production tree from it without install scripts.
# `pnpm update` refuses a production-only node_modules, so the lockfile is updated in a copy of the
# workspace manifests. Optional overrides (name=spec, e.g. zod=latest) are written to
# pnpm-workspace.yaml in both places. Prints "lockfile changed" when the dependency tree moved.
# Usage: pho-update-deps.sh <checkout> <pnpm package spec, e.g. pnpm@latest> [name=spec ...]
set -euo pipefail

src=$1
pnpm_spec=$2
shift 2
pnpm() { npm exec --yes --package="$pnpm_spec" -- pnpm "$@"; }
# Upstream's packageManager field would otherwise switch pnpm to the version it names
export npm_config_manage_package_manager_versions=false

add_overrides() {
  local file=$1/pnpm-workspace.yaml pair
  [ "$#" -gt 1 ] || return 0
  if grep -q '^overrides:' "$file"; then
    echo "pnpm-workspace.yaml already has overrides; refusing to merge" >&2
    exit 1
  fi
  echo "overrides:" >> "$file"
  shift
  for pair in "$@"; do
    printf '  "%s": "%s"\n' "${pair%%=*}" "${pair#*=}" >> "$file"
  done
}

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

git -C "$src" ls-files -z -- package.json '*/package.json' pnpm-lock.yaml pnpm-workspace.yaml .npmrc \
  | tar -C "$src" -c --null -T - | tar -C "$work" -x
add_overrides "$work" "$@"
add_overrides "$src" "$@"
(cd "$work" && pnpm update --recursive --lockfile-only --no-save)

cp -- "$work/pnpm-lock.yaml" "$src/pnpm-lock.yaml"
(cd "$src" && pnpm install --prod --frozen-lockfile --ignore-scripts)

# Compare with the lockfile applied last time (kept in node_modules, outside git), not with upstream's
applied=$src/node_modules/.pho-applied-pnpm-lock.yaml
if ! cmp -s "$src/pnpm-lock.yaml" "$applied"; then
  cp -- "$src/pnpm-lock.yaml" "$applied"
  echo "lockfile changed"
fi
