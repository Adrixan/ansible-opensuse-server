#!/usr/bin/env bash
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)/roles/ai_workstation/files/code-sync.py"  # run: bash tests/test_code_sync.sh
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; cd "$T"
g() { git -c user.email=t@t -c user.name=t "$@"; }
cs() { python3 -I "$SRC" --code "$1" --list list.tsv --exclude none; echo "  (exit $?)"; }
git init -q --bare --initial-branch=main remote.git
git init -q -b main A/code/proj && git -C A/code/proj remote add origin "$T/remote.git"
(cd A/code/proj && g commit -q --allow-empty -m one && git push -q -u origin main 2>/dev/null)
mkdir -p B/code
echo "-- A registers"; cs A/code; tail -1 list.tsv | cut -f1
echo "-- B clones"; cs B/code; ls B/code
echo "-- A pushes, B fast-forwards"; (cd A/code/proj && g commit -q --allow-empty -m two && git push -q)
cs B/code; echo "  B commits: $(git -C B/code/proj log --oneline | wc -l) (want 2)"
echo "-- B dirty, A pushes: no update"; echo x > B/code/proj/f
(cd A/code/proj && g commit -q --allow-empty -m three && git push -q)
cs B/code; echo "  B commits: $(git -C B/code/proj log --oneline | wc -l) (want 2)"
echo "-- clean again: updates"; rm B/code/proj/f; cs B/code; echo "  B commits: $(git -C B/code/proj log --oneline | wc -l) (want 3)"
echo "-- unpushed and no-remote reported"
(cd B/code/proj && g commit -q --allow-empty -m local && git switch -q -c topic && g commit -q --allow-empty -m topic && git switch -q main)
cs B/code
echo "-- exclude"; printf 'proj\n' > excl; rm -rf C; mkdir -p C/code
python3 -I "$SRC" --code C/code --list list.tsv --exclude excl; ls C/code | wc -l
