#!/usr/bin/env python3
"""Remove superseded Claude Code versions from a versions directory.

Keeps the newest version, the target of --keep-target (if given) and any
version a running process was started from. Entries are only touched when
their name is a plain dotted version number, so unrelated files are safe.

Prints CHANGED: <what> for every removal, KEEP: <what> for protected old
versions and UP_TO_DATE when nothing needed to be done.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")


def version_key(name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in name.split("."))


def in_use(path: Path) -> bool:
    target = str(path)
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            exe = os.readlink(proc / "exe")
        except OSError:
            continue
        if exe == target or exe.startswith(target + "/"):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", required=True, type=Path, help="directory containing one entry per version")
    parser.add_argument("--keep-target", type=Path, help="symlink whose resolved target must be kept")
    parser.add_argument("--keep", default=1, type=int, help="number of newest versions to keep")
    parser.add_argument("--check", action="store_true", help="report what would be removed without removing")
    args = parser.parse_args()

    if not args.dir.is_dir():
        print(f"UP_TO_DATE {args.dir} does not exist")
        return 0

    protected: set[Path] = set()
    if args.keep_target:
        if not args.keep_target.exists():
            raise RuntimeError(f"--keep-target {args.keep_target} does not resolve; refusing to prune")
        protected.add(args.keep_target.resolve())

    entries = sorted(
        (e for e in args.dir.iterdir() if VERSION_RE.match(e.name) and not e.is_symlink()),
        key=lambda e: version_key(e.name),
        reverse=True,
    )
    protected.update(e.resolve() for e in entries[: max(args.keep, 1)])

    changed = False
    for entry in entries:
        if entry.resolve() in protected:
            continue
        if in_use(entry):
            print(f"KEEP {entry} (in use)")
            continue
        if args.check:
            print(f"CHANGED: would prune {entry}")
        else:
            shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
            print(f"CHANGED: pruned {entry}")
        changed = True

    if not changed:
        print(f"UP_TO_DATE {args.dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - surface any failure as a non-zero exit for systemd/Ansible
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
