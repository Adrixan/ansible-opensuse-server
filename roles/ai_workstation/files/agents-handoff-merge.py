#!/usr/bin/python3
"""Merge Syncthing conflict copies of the home-level agent handoff note back into the live file.

`~/.agents/session-handoff.md` is a Markdown note that agent sessions on several workstations append
to. The Syncthing folder "agents-home" (ai_workstation agents_handoff.yml) syncs only this note.
When two machines edit it while apart, Syncthing keeps the newer file and renames the other to
`session-handoff.sync-conflict-<date>-<time>-<device>.md`. This tool folds each such copy back in.

Semantics: a line-based union of the live file and the copy. Lines both sides share stay once;
lines only one side has are kept, the live file's first where both changed the same place. Nothing
written on either side is lost; a line one side deleted while the other kept it comes back. Merged
copies are moved to the state directory's archive (kept 90 days), never deleted.

Several machines may run this. `--min-age-min` makes a standby machine wait until a conflict copy
has been visible that long (first sighting recorded in the state dir), so the primary merges first.
"""
from __future__ import annotations

import argparse
import difflib
import fcntl
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ARCHIVE_DAYS = 90


def union(live: list[str], other: list[str]) -> list[str]:
    out: list[str] = []
    matcher = difflib.SequenceMatcher(a=live, b=other, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out.extend(live[i1:i2])
        elif tag == "delete":
            out.extend(live[i1:i2])
        elif tag == "insert":
            out.extend(other[j1:j2])
        else:  # replace: keep both sides, live first
            out.extend(live[i1:i2])
            # Markdown: a heading that now follows the live text needs a blank line before it.
            if out and out[-1].strip() and other[j1].lstrip().startswith("#"):
                out.append("\n")
            out.extend(other[j1:j2])
    return out


def read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def write_atomic(path: Path, lines: list[str], mode: int) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".agents-handoff-merge.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.writelines(lines)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, type=Path, help="folder that holds the live note")
    ap.add_argument("--file", default="session-handoff.md", help="name of the live note")
    ap.add_argument("--state-dir", type=Path,
                    default=Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
                    / "agents-handoff-merge")
    ap.add_argument("--min-age-min", type=int, default=0,
                    help="merge a conflict copy only after it was seen this long (standby machines)")
    args = ap.parse_args()

    folder: Path = args.dir.expanduser()
    live = folder / args.file
    stem, ext = os.path.splitext(args.file)
    if live.is_symlink():
        print(f"{live} is a symlink; refusing to merge into it", file=sys.stderr)
        return 1

    state: Path = args.state_dir
    archive = state / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    seen_path = state / "seen.json"

    with open(state / "lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            seen: dict[str, float] = json.loads(seen_path.read_text())
        except (OSError, ValueError):
            seen = {}
        now = time.time()
        copies = sorted(p for p in folder.glob(f"{stem}.sync-conflict-*{ext}") if p.is_file())
        merged_any = False
        for copy in copies:
            first = seen.setdefault(copy.name, now)
            if now - first < args.min_age_min * 60:
                continue
            other = read_lines(copy)
            if live.exists():
                current = read_lines(live)
                mode = live.stat().st_mode & 0o777
            else:
                current, mode = [], 0o644
            result = union(current, other)
            if result != current:
                write_atomic(live, result, mode)
                merged_any = True
                print(f"merged {copy.name} into {live.name}")
            else:
                print(f"{copy.name} adds nothing to {live.name}")
            dest = archive / f"{int(now)}-{copy.name}"
            shutil.move(str(copy), dest)
            seen.pop(copy.name, None)
        # Forget sightings of copies that vanished (merged elsewhere) and prune the archive.
        names = {p.name for p in copies if p.exists()}
        seen = {k: v for k, v in seen.items() if k in names}
        seen_path.write_text(json.dumps(seen))
        cutoff = now - ARCHIVE_DAYS * 86400
        for old in archive.iterdir():
            if old.is_file() and old.stat().st_mtime < cutoff:
                old.unlink()
        if merged_any:
            print(f"{live} updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
