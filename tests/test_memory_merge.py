"""Tests for roles/ai_workstation/files/memory-merge.py (run: python3 -I tests/test_memory_merge.py)."""
import importlib.util
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "roles/ai_workstation/files/memory-merge.py"
spec = importlib.util.spec_from_file_location("mm", SRC)
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)


def ent(name, typ, obs):
    return json.dumps({"type": "entity", "name": name, "entityType": typ, "observations": obs},
                      ensure_ascii=False, separators=(",", ":"))


def rel(f, t, r):
    return json.dumps({"type": "relation", "from": f, "to": t, "relationType": r}, separators=(",", ":"))


def lines(*items):
    return "\n".join(items) + "\n"


fails = 0


def check(cond, msg):
    global fails
    if not cond:
        fails += 1
        print("FAIL", msg)
    else:
        print("ok  ", msg)


main = lines(ent("Peter", "person", ["runs ultras", "vegan"]), ent("Travel planning", "rules", ["a"]),
             rel("Peter", "Travel planning", "owns"))
other = lines(ent("Peter", "person", ["vegan", "wakes 04:30"]), ent("Prague", "trip", ["Nov"]),
              rel("Peter", "Prague", "plans"), "not json at all")

# 1. merge semantics
out = mm.merge(main, [other])
e, r, bad = mm.parse(out)
names = [x["name"] for x in e]
check(names == ["Peter", "Travel planning", "Prague"], "entities in main order, new appended")
check(e[0]["observations"] == ["runs ultras", "vegan", "wakes 04:30"], "observations united in order")
check([mm.rel_key(x) for x in r] == [("Peter", "Travel planning", "owns"), ("Peter", "Prague", "plans")],
      "relations united")
check(bad == ["not json at all"], "unreadable lines kept")
check(out.splitlines()[0] == ent("Peter", "person", ["runs ultras", "vegan", "wakes 04:30"]),
      "line format equals the server's JSON.stringify output")
check(mm.merge(out, [other]) == out, "idempotent")
check(mm.merge(main, []) == main, "no conflicts, no change")
check("Österreich" in mm.merge(lines(ent("Graz", "city", ["Österreich"])), []), "non-ASCII kept unescaped")

with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "sync"
    st = Path(tmp) / "state"
    d.mkdir()
    live = d / "mcp-memory.jsonl"
    live.write_text(main)
    live.chmod(0o640)
    c = d / "mcp-memory.sync-conflict-20261104-101010-YPIVZ5E.jsonl"
    c.write_text(other)
    unrelated = d / "WORKSTATION.sync-conflict-20261104-101010-YPIVZ5E.md"
    unrelated.write_text("x")

    # 2. standby waits for min age
    rc = mm.run(d, "mcp-memory.jsonl", st, min_age_min=15, settle_sec=0, now=1000.0)
    check(rc == 0 and c.exists() and live.read_text() == main, "standby: first sighting only recorded")
    rc = mm.run(d, "mcp-memory.jsonl", st, min_age_min=15, settle_sec=0, now=1000.0 + 14 * 60)
    check(c.exists(), "standby: still waiting after 14 min")
    rc = mm.run(d, "mcp-memory.jsonl", st, min_age_min=15, settle_sec=0, now=1000.0 + 15 * 60)
    check(rc == 0 and not c.exists(), "standby: merges after 15 min")
    check((st / "archive" / c.name).exists(), "conflict copy archived")
    check("Prague" in live.read_text(), "live file holds the merge")
    check(oct(live.stat().st_mode & 0o777) == "0o640", "file mode kept")
    check(unrelated.exists(), "other conflict files untouched")
    check(not list(d.glob(".syncthing.*")), "no temp file left")

    # 3. primary merges at once
    c2 = d / "mcp-memory.sync-conflict-20261104-111111-HX3GERA.jsonl"
    c2.write_text(lines(ent("Solveig", "person", ["x"])))
    rc = mm.run(d, "mcp-memory.jsonl", st, min_age_min=0, settle_sec=0)
    check(rc == 0 and not c2.exists() and "Solveig" in live.read_text(), "primary merges at once")

    # 4. a concurrent writer drops the merge: merged again
    c3 = d / "mcp-memory.sync-conflict-20261104-121212-HX3GERA.jsonl"
    c3.write_text(lines(ent("Julia", "person", ["y"])))
    before = live.read_text()

    def racer():
        time.sleep(0.3)
        live.write_text(before)  # like a server that loaded before the merge and saved after it

    t = threading.Thread(target=racer)
    t.start()
    rc = mm.run(d, "mcp-memory.jsonl", st, min_age_min=0, settle_sec=0.6)
    t.join()
    check(rc == 0 and "Julia" in live.read_text() and not c3.exists(), "race: merge repeated after a lost write")

    # 5. missing live file: conflict copies stay
    c4 = d / "mcp-memory.sync-conflict-20261104-131313-HX3GERA.jsonl"
    c4.write_text(lines(ent("X", "t", [])))
    live.unlink()
    rc = mm.run(d, "mcp-memory.jsonl", st, min_age_min=0, settle_sec=0)
    check(rc == 1 and c4.exists(), "missing live file: nothing merged, copy kept")

print("FAILED" if fails else "ALL PASSED", fails)
sys.exit(1 if fails else 0)
