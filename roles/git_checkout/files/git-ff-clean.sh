#!/usr/bin/env bash
# Fast-forward a checkout to origin/<branch>, but only while it sits on <branch> with no local changes,
# so a session's feature branch or uncommitted work is never touched. Prints CHANGED when HEAD moved.
set -euo pipefail
dir=$1 branch=$2
cd "$dir"
if [ "$(git branch --show-current)" != "$branch" ]; then echo "SKIP: not on $branch"; exit 0; fi
if ! git diff --quiet || ! git diff --cached --quiet; then echo "SKIP: local changes"; exit 0; fi
before=$(git rev-parse HEAD)
git pull --ff-only --quiet origin "$branch"
if [ "$(git rev-parse HEAD)" != "$before" ]; then echo CHANGED; fi
