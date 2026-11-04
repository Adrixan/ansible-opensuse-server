#!/usr/bin/python3
"""Merge Syncthing conflict copies of the MCP memory graph back into the live file.

The memory MCP server (@modelcontextprotocol/server-memory) runs on several machines against one
JSONL file in a Syncthing folder. Each machine writes while it is cut off from the others; when they
meet again, Syncthing keeps the newer file and renames the older one to
`<stem>.sync-conflict-<date>-<time>-<device>.<ext>`. This tool folds every such copy back in:
entities by name (observations united in order), relations by (from, to, relationType), unreadable
lines kept verbatim. Output uses the server's own line format, written by atomic rename.

Semantics: a union. Additions from every side survive; something deleted on one side while the other
side also wrote comes back. Merged copies are moved to an archive (kept 90 days), never deleted.

Several machines may run this. `--min-age-min` makes a standby machine wait until a conflict copy
has been visible that long (first sighting recorded in the state dir), so the primary merges first.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import sys
import time
from pathlib import Path

ARCHIVE_DAYS = 90


def parse(text: str) -> tuple[list[dict], list[dict], list[str]]:
    entities: list[dict] = []
    relations: list[dict] = []
    unreadable: list[str] = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            unreadable.append(line)
            continue
        if not isinstance(item, dict):
            unreadable.append(line)
        elif item.get("type") == "entity" and _is_entity(item):
            entities.append(item)
        elif item.get("type") == "relation" and _is_relation(item):
            relations.append(item)
        else:
            unreadable.append(line)
    return entities, relations, unreadable


def _is_entity(item: dict) -> bool:
    obs = item.get("observations")
    return (isinstance(item.get("name"), str) and isinstance(item.get("entityType"), str)
            and isinstance(obs, list) and all(isinstance(o, str) for o in obs))


def _is_relation(item: dict) -> bool:
    return all(isinstance(item.get(k), str) for k in ("from", "to", "relationType"))


def rel_key(r: dict) -> tuple[str, str, str]:
    return (r["from"], r["to"], r["relationType"])


def merge(main: str, others: list[str]) -> str:
    """Union of the main file and the conflict copies, in main's order, new items appended."""
    ents, rels, bad = parse(main)
    by_name = {e["name"]: {"name": e["name"], "entityType": e["entityType"],
                           "observations": list(dict.fromkeys(e["observations"]))} for e in ents}
    order = [e["name"] for e in ents]
    order = list(dict.fromkeys(order))
    rel_order = list(dict.fromkeys(rel_key(r) for r in rels))
    bad_seen = list(dict.fromkeys(bad))
    for text in others:
        o_ents, o_rels, o_bad = parse(text)
        for e in o_ents:
            cur = by_name.get(e["name"])
            if cur is None:
                by_name[e["name"]] = {"name": e["name"], "entityType": e["entityType"],
                                      "observations": list(dict.fromkeys(e["observations"]))}
                order.append(e["name"])
            else:
                for obs in e["observations"]:
                    if obs not in cur["observations"]:
                        cur["observations"].append(obs)
        for r in o_rels:
            k = rel_key(r)
            if k not in rel_order:
                rel_order.append(k)
        for line in o_bad:
            if line not in bad_seen:
                bad_seen.append(line)
    lines = [_dump({"type": "entity", **by_name[n]}) for n in order]
    lines += [_dump({"type": "relation", "from": f, "to": t, "relationType": rt}) for f, t, rt in rel_order]
    lines += bad_seen
    return "\n".join(lines) + ("\n" if lines else "")


def _dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def missing(merged: str, current: str) -> bool:
    """True when the current file lacks something the merge added (a concurrent writer raced us)."""
    m_ents, m_rels, _ = parse(merged)
    c_ents, c_rels, _ = parse(current)
    c_obs = {e["name"]: set(e["observations"]) for e in c_ents}
    for e in m_ents:
        if e["name"] not in c_obs or not set(e["observations"]) <= c_obs[e["name"]]:
            return True
    return not {rel_key(r) for r in m_rels} <= {rel_key(r) for r in c_rels}


def write_atomic(path: Path, text: str) -> None:
    # Syncthing ignores `.syncthing.*.tmp`, so the temporary file never travels
    tmp = path.with_name(f".syncthing.{path.name}.merge.tmp")
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def run(folder: Path, name: str, state: Path, min_age_min: float, settle_sec: float, now: float | None = None) -> int:
    live = folder / name
    stem, dot, ext = name.rpartition(".")
    pattern = f"{stem}.sync-conflict-*.{ext}" if dot else f"{name}.sync-conflict-*"
    state.mkdir(parents=True, exist_ok=True)
    seen_file = state / "first-seen.json"
    try:
        seen = json.loads(seen_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        seen = {}
    now = time.time() if now is None else now
    conflicts = sorted(folder.glob(pattern))
    seen = {k: v for k, v in seen.items() if (folder / k).exists()}
    ready = []
    for c in conflicts:
        seen.setdefault(c.name, now)
        if now - seen[c.name] >= min_age_min * 60:
            ready.append(c)
    seen_file.write_text(json.dumps(seen))
    if not ready:
        return 0
    if not live.exists():
        print(f"{live} is missing; leaving {len(ready)} conflict copies alone", file=sys.stderr)
        return 1
    others = [c.read_text(encoding="utf-8") for c in ready]
    for attempt in range(3):
        current = live.read_text(encoding="utf-8")
        merged = merge(current, others)
        if merged != current:
            write_atomic(live, merged)
        if settle_sec:
            time.sleep(settle_sec)
        if not missing(merged, live.read_text(encoding="utf-8")):
            break
        print(f"a concurrent write dropped merged items; merging again (attempt {attempt + 2})")
    else:
        print("merged items still missing after 3 attempts; conflict copies kept", file=sys.stderr)
        return 1
    archive = state / "archive"
    archive.mkdir(exist_ok=True)
    for c in ready:
        shutil.move(c, archive / c.name)  # works across filesystems too
        seen.pop(c.name, None)
        print(f"merged {c.name}")
    seen_file.write_text(json.dumps(seen))
    for old in archive.iterdir():
        if now - old.stat().st_mtime > ARCHIVE_DAYS * 86400:
            old.unlink()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", required=True, type=Path, help="Syncthing folder that holds the memory file")
    ap.add_argument("--file", default="mcp-memory.jsonl")
    ap.add_argument("--state", type=Path,
                    default=Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "memory-merge")
    ap.add_argument("--min-age-min", type=float, default=0.0,
                    help="merge only conflict copies seen at least this long (standby machines)")
    ap.add_argument("--settle-sec", type=float, default=20.0,
                    help="wait this long after writing, then check that no concurrent write dropped the merge")
    args = ap.parse_args()
    args.state.mkdir(parents=True, exist_ok=True)
    with open(args.state / "lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return run(args.dir, args.file, args.state, args.min_age_min, args.settle_sec)


if __name__ == "__main__":
    sys.exit(main())
