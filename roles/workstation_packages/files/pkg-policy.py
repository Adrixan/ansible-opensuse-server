#!/usr/bin/python3 -I
"""Package policy for the workstations: keep dropped apps out, align a host to schulpc's package set.

Subcommands (run as root; print one JSON object; exit 0 ok, 2 refused, 1 error):
  remove --names N... [--allow REGEX] [--apply]
      Remove the installed subset of N. A zypper dry run comes first; if the transaction would remove
      anything outside N (and outside --allow), nothing is removed and the command is refused.
  lock --names N... --comment TEXT [--apply]
      Add a zypper lock (`zypper al -m TEXT`) for each name without one, so no pattern recommends,
      role run or sync installs it again.
  align --state-dir DIR --source HOST [--exclude GLOB...] [--apply]
      Install on this host what the ws-sync state of HOST says was installed on purpose there
      (installed minus zypper's AutoInstalled list), minus ws-sync's ignore and host-specific lists,
      minus --exclude and locked names; plus every Flatpak app of every host state.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

LOCKS = Path("/etc/zypp/locks")
ZYPPER = ["zypper", "--non-interactive", "--no-refresh"]


def run(cmd: list[str], timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def installed() -> set[str]:
    out = run(["rpm", "-qa", "--qf", "%{NAME}\n"]).stdout.split()
    return set(out) - {"gpg-pubkey"}


def locked() -> set[str]:
    if not LOCKS.exists():
        return set()
    return {m.group(1).strip() for m in re.finditer(r"^solvable_name:\s*(\S+)", LOCKS.read_text(), re.M)}


def zypper_removals(names: list[str]) -> tuple[set[str], str]:
    p = run(["zypper", "-x", *ZYPPER[1:], "rm", "--dry-run", "--", *names])
    try:
        root = ET.fromstring(p.stdout[p.stdout.find("<?xml"):] if "<?xml" in p.stdout else p.stdout)
    except ET.ParseError:
        return set(), p.stdout[-2000:] + p.stderr[-2000:]
    errors = [m.text or "" for m in root.iter("message") if m.get("type") == "error"]
    gone = {s.get("name", "") for blk in root.iter("to-remove") for s in blk.iter("solvable")}
    return gone, "; ".join(errors)


def cmd_remove(a: argparse.Namespace) -> int:
    want = sorted(set(a.names) & installed())
    res: dict = {"changed": False, "removed": [], "extra": []}
    if not want:
        print(json.dumps(res))
        return 0
    gone, err = zypper_removals(want)
    if err and not gone:
        res["error"] = err
        print(json.dumps(res))
        return 1
    allow = re.compile(a.allow) if a.allow else None
    extra = sorted(n for n in gone - set(want) if not (allow and allow.search(n)))
    res["extra"] = extra
    if extra:
        res["refused"] = "the removal would take packages outside the list"
        print(json.dumps(res))
        return 2
    res["removed"] = sorted(gone)
    if a.apply:
        p = run([*ZYPPER, "rm", "--", *want])
        if p.returncode != 0:
            res["error"] = (p.stdout + p.stderr)[-2000:]
            print(json.dumps(res))
            return 1
    res["changed"] = True
    print(json.dumps(res))
    return 0


def cmd_lock(a: argparse.Namespace) -> int:
    have = locked()
    new = [n for n in dict.fromkeys(a.names) if n not in have]
    res = {"changed": bool(new), "locked": new}
    if new and a.apply:
        for n in new:
            p = run([*ZYPPER, "al", "-m", a.comment, n], timeout=300)
            if p.returncode != 0:
                res["error"] = f"{n}: {(p.stdout + p.stderr)[-500:]}"
                print(json.dumps(res))
                return 1
    print(json.dumps(res))
    return 0


def match_any(name: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, g) for g in globs)


def cmd_align(a: argparse.Namespace) -> int:
    sdir = Path(a.state_dir)
    cfg = tomllib.loads((sdir / "config.toml").read_text())
    states = {p.stem: json.loads(p.read_text()) for p in sorted((sdir / "state").glob("*.json"))
              if "sync-conflict" not in p.name and p.stem != "baseline"}
    if a.source not in states:
        print(json.dumps({"error": f"no state for {a.source} in {sdir}/state"}))
        return 1
    pk = states[a.source]["packages"]
    pcfg = cfg.get("packages", {})
    skip = list(pcfg.get("ignore", [])) + list((pcfg.get("host_specific") or {}).get(a.source, [])) + a.exclude
    have, locks = installed(), locked()
    wanted = {n for n in set(pk["installed"]) - set(pk["auto"]) if not match_any(n, skip)}
    missing = sorted(wanted - have - locks)
    fcfg = cfg.get("flatpak", {})
    fskip = list(fcfg.get("ignore", [])) + a.exclude
    apps: dict[str, dict] = {}
    for host, st in states.items():
        for app, meta in (st.get("flatpak") or {}).items():
            if not match_any(app, fskip) and not match_any(app, (fcfg.get("host_specific") or {}).get(host, [])):
                apps.setdefault(app, meta)
    flist = run(["flatpak", "list", "--app", "--columns=application"]).stdout.split()
    fmissing = sorted(set(apps) - set(flist))
    # Names no enabled repository offers (an orphaned package on the source host) are reported, not retried.
    unavailable = [n for n in missing
                   if run(["zypper", "-x", *ZYPPER[1:], "se", "-x", "-t", "package", "--", n]).returncode != 0]
    missing = [n for n in missing if n not in unavailable]
    res: dict = {"changed": bool(missing or fmissing), "packages": missing, "flatpaks": fmissing,
                 "unavailable": unavailable, "failed": [], "source": a.source}
    if a.apply:
        if missing:
            p = run([*ZYPPER, "install", "--auto-agree-with-licenses", "--no-recommends", "--", *missing])
            if p.returncode != 0:  # one by one, so one conflicting package blocks nothing else
                for n in missing:
                    q = run([*ZYPPER, "install", "--auto-agree-with-licenses", "--no-recommends", "--", n])
                    if q.returncode != 0:
                        res["failed"].append(n)
        for app in fmissing:
            origin = apps[app].get("origin") or "flathub"
            q = run(["flatpak", "install", "--system", "-y", "--noninteractive", origin, app])
            if q.returncode != 0:
                res["failed"].append(app)
    print(json.dumps(res))
    return 1 if res["failed"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("remove")
    r.add_argument("--names", nargs="+", required=True)
    r.add_argument("--allow", default="")
    r.add_argument("--apply", action="store_true")
    lk = sub.add_parser("lock")
    lk.add_argument("--names", nargs="+", required=True)
    lk.add_argument("--comment", required=True)
    lk.add_argument("--apply", action="store_true")
    al = sub.add_parser("align")
    al.add_argument("--state-dir", required=True)
    al.add_argument("--source", required=True)
    al.add_argument("--exclude", nargs="*", default=[])
    al.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    return {"remove": cmd_remove, "lock": cmd_lock, "align": cmd_align}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
