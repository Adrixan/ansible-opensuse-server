#!/usr/bin/python3
"""Takeover lease between the two workstations: one machine at a time serves the rc roles.

The arbiter is branch `lease` of a private GitHub repository. Each lease state is one parentless commit
holding `lease.json` (holder, epoch, expires, renewed, released_by); every write is a compare-and-swap
push (`--force-with-lease=refs/heads/lease:<sha seen>`), so of two machines writing at once exactly one
wins, and the branch never grows a history. Times are epoch seconds of the writer's clock (NTP).

- The holder renews every 2 min (`watch`, user timer) with a TTL of 10 min. When it cannot renew and its
  last good renew expires within the fence margin (4 min), it stops its roles itself (self-fencing by its
  own clock) and restarts them when a later renew succeeds while the lease is still its own.
- A standby takes an expired lease once the grace period after expiry (2 min) has passed, or a lease the
  other machine released, then starts the takeover roles (the Greeter). A valid lease of the other machine
  stops the local roles: a machine that comes back after a takeover stays passive.
- `check` answers from the local cache only (no network): this host holds the lease and its last good
  renew is outside the fence margin. Gates: ExecCondition of claude-remote-control@.service (`ensure`),
  `rc up`, and optional ExecCondition drop-ins on timers' services (`check`).
- `acquire --force` takes a valid lease (new epoch) when the other machine cannot be asked: it may still
  be writing, so conflict copies can follow. The epoch rises with every change of holder.
Design: vault report Research/Reports/2026-11-03-schulpc-xps-mirror (section 4); Peter's decision D33 B.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

REF = "refs/heads/lease"
SEEN = "refs/lease/seen"
FILE = "lease.json"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
ROLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
DEFAULT_CONFIG = Path.home() / ".config" / "workstation-lease" / "config.json"
DEFAULT_STATE = Path.home() / ".local" / "state" / "workstation-lease"
UNIT_PREFIX = "claude-remote-control@"


class NetError(Exception):
    """The arbiter could not be reached (network, GitHub, authentication)."""


@dataclass
class Config:
    remote: str
    host: str
    state_dir: Path = DEFAULT_STATE
    ttl: int = 600
    grace: int = 120
    fence_margin: int = 240
    auto_takeover: bool = True
    takeover_roles: list[str] = field(default_factory=lambda: ["greeter"])
    rc_bin: str = str(Path.home() / ".local" / "bin" / "rc")
    git_timeout: int = 30
    stop_wait_min: int = 2

    def __post_init__(self) -> None:
        self.state_dir = Path(os.path.expanduser(str(self.state_dir)))
        self.rc_bin = os.path.expanduser(self.rc_bin)
        if not self.remote or not isinstance(self.remote, str):
            raise ValueError("remote missing")
        if not NAME_RE.match(self.host):
            raise ValueError(f"invalid host name {self.host!r}")
        for name in ("ttl", "grace", "fence_margin", "git_timeout", "stop_wait_min"):
            v = getattr(self, name)
            if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.ttl < self.fence_margin + 120:
            raise ValueError("ttl must exceed fence_margin by at least 120 s")
        if not all(isinstance(r, str) and ROLE_RE.match(r) for r in self.takeover_roles):
            raise ValueError("invalid takeover role name")


def load_config(path: Path, state_dir: str | None = None) -> Config:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    known = set(Config.__dataclass_fields__)
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown config keys: {', '.join(sorted(unknown))}")
    if state_dir:
        data["state_dir"] = state_dir
    return Config(**data)


class Roles(Protocol):
    def list_running(self) -> list[str]: ...
    def stop(self, roles: list[str], wait_min: int) -> None: ...
    def start(self, roles: list[str]) -> None: ...


class SystemdRoles:
    """The rc roles of this user: claude-remote-control@<role>.service units, stopped and started by rc."""

    def __init__(self, rc_bin: str) -> None:
        self.rc_bin = rc_bin

    def list_running(self) -> list[str]:
        out = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service", "--state=active,activating",
             "--plain", "--no-legend", f"{UNIT_PREFIX}*"],
            capture_output=True, text=True, timeout=30).stdout
        roles = []
        for line in out.splitlines():
            unit = line.split(" ", 1)[0]
            if unit.startswith(UNIT_PREFIX) and unit.endswith(".service"):
                roles.append(unit[len(UNIT_PREFIX):-len(".service")])
        return sorted(roles)

    def stop(self, roles: list[str], wait_min: int) -> None:
        """rc down with handoff (bounded wait); blocks until stopped, then stops stragglers at once."""
        for role in roles:
            subprocess.run([self.rc_bin, "down", role, "--wait", str(wait_min)], timeout=120)
        deadline = time.time() + (2 * wait_min + 1) * 60
        while time.time() < deadline and set(roles) & set(self.list_running()):
            time.sleep(10)
        for role in sorted(set(roles) & set(self.list_running())):
            subprocess.run([self.rc_bin, "down", role, "--now"], timeout=120)

    def start(self, roles: list[str]) -> None:
        for role in roles:
            subprocess.run([self.rc_bin, "up", role], timeout=300)


class Remote:
    """Compare-and-swap on branch `lease` of the arbiter repository, through a private bare repo."""

    def __init__(self, url: str, repo: Path, host: str, timeout: int) -> None:
        self.url = url
        self.repo = repo
        self.host = host
        self.timeout = timeout

    def _git(self, *args: str, stdin: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update({
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10",
            "GIT_AUTHOR_NAME": f"workstation-lease {self.host}",
            "GIT_AUTHOR_EMAIL": f"workstation-lease@{self.host}.invalid",
            "GIT_COMMITTER_NAME": f"workstation-lease {self.host}",
            "GIT_COMMITTER_EMAIL": f"workstation-lease@{self.host}.invalid",
        })
        try:
            p = subprocess.run(["git", "--git-dir", str(self.repo), *args], input=stdin, capture_output=True,
                               text=True, env=env, timeout=self.timeout)
        except subprocess.TimeoutExpired as e:
            raise NetError(f"git {args[0]} timed out") from e
        if check and p.returncode != 0:
            raise NetError(f"git {args[0]} failed: {(p.stderr or p.stdout).strip()[:300]}")
        return p

    def _init(self) -> None:
        if not (self.repo / "HEAD").exists():
            self.repo.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init", "-q", "--bare", str(self.repo)], check=True, capture_output=True)

    def read(self) -> tuple[str | None, dict | None]:
        """(sha, state) of the branch; (None, None) when it does not exist; state {"_invalid": True} when
        lease.json is unreadable. Raises NetError when the arbiter cannot be reached."""
        self._init()
        p = self._git("fetch", "--no-tags", "-q", self.url, f"+{REF}:{SEEN}", check=False)
        if p.returncode != 0:
            if "couldn't find remote ref" in p.stderr:
                self._git("update-ref", "-d", SEEN, check=False)
                return None, None
            raise NetError(f"fetch failed: {p.stderr.strip()[:300]}")
        sha = self._git("rev-parse", SEEN).stdout.strip()
        blob = self._git("cat-file", "-p", f"{sha}:{FILE}", check=False)
        try:
            state = json.loads(blob.stdout) if blob.returncode == 0 else None
        except json.JSONDecodeError:
            state = None
        if not isinstance(state, dict):
            return sha, {"_invalid": True}
        return sha, state

    def write(self, expected: str | None, state: dict) -> bool:
        return self.write_raw(expected, json.dumps(state, sort_keys=True) + "\n")

    def write_raw(self, expected: str | None, text: str) -> bool:
        """True when the branch moved from `expected` (None: absent) to the new state; False when another
        writer changed it first. Raises NetError when the arbiter cannot be reached."""
        self._init()
        blob = self._git("hash-object", "-w", "--stdin", stdin=text).stdout.strip()
        tree = self._git("mktree", stdin=f"100644 blob {blob}\t{FILE}\n").stdout.strip()
        commit = self._git("commit-tree", tree, "-m", f"lease: {self.host}").stdout.strip()
        p = self._git("push", "-q", "--porcelain", f"--force-with-lease={REF}:{expected or ''}", self.url,
                      f"{commit}:{REF}", check=False)
        if p.returncode == 0:
            return True
        if "rejected" in p.stdout or "stale info" in p.stdout or "rejected" in p.stderr:
            return False
        raise NetError(f"push failed: {(p.stderr or p.stdout).strip()[:300]}")


class Lease:
    def __init__(self, cfg: Config, clock: Callable[[], float] = time.time, roles: Roles | None = None) -> None:
        self.cfg = cfg
        self.clock = clock
        self.roles = roles or SystemdRoles(cfg.rc_bin)
        self.remote = Remote(cfg.remote, cfg.state_dir / "repo.git", cfg.host, cfg.git_timeout)

    # --- local files -------------------------------------------------------------------------------
    def _path(self, name: str) -> Path:
        return self.cfg.state_dir / name

    def _write_json(self, name: str, data: object) -> None:
        self.cfg.state_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._path(name + ".tmp")
        tmp.write_text(json.dumps(data, sort_keys=True) + "\n")
        os.replace(tmp, self._path(name))

    def _read_json(self, name: str, default: object) -> object:
        try:
            return json.loads(self._path(name).read_text())
        except (OSError, json.JSONDecodeError):
            return default

    def load_cache(self) -> dict:
        c = self._read_json("state.json", {})
        return c if isinstance(c, dict) else {}

    def save_cache(self, state: dict) -> None:
        self._write_json("state.json", {**state, "seen": int(self.clock())})

    def _fenced(self) -> list[str]:
        f = self._read_json("fenced.json", [])
        return [r for r in f if isinstance(r, str) and ROLE_RE.match(r)] if isinstance(f, list) else []

    def _lock(self):
        self.cfg.state_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path("lock"), os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    @staticmethod
    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    # --- state logic -------------------------------------------------------------------------------
    def _valid_for_other(self, st: dict | None) -> bool:
        """The state is a lease of another holder that has not yet passed expiry plus grace."""
        if st is None:
            return False
        if st.get("_invalid"):
            return True  # unknown content: never taken without --force
        holder = st.get("holder") or ""
        return bool(holder) and holder != self.cfg.host and float(st.get("expires", 0)) + self.cfg.grace > self.clock()

    def _new_state(self, st: dict | None, ttl: int | None = None) -> dict:
        now = int(self.clock())
        epoch = int(st.get("epoch", 0)) if st and not st.get("_invalid") else 0
        if not (st and st.get("holder") == self.cfg.host):
            epoch += 1
        return {"holder": self.cfg.host, "epoch": epoch, "expires": now + (ttl or self.cfg.ttl),
                "renewed": now, "released_by": ""}

    def check(self) -> bool:
        c = self.load_cache()
        return c.get("holder") == self.cfg.host and self.clock() < float(c.get("expires", 0)) - self.cfg.fence_margin

    def acquire(self, force: bool = False, ttl: int | None = None) -> bool:
        fd = self._lock()
        try:
            for _ in range(3):
                sha, st = self.remote.read()
                if self._valid_for_other(st) and not force:
                    if st and not st.get("_invalid"):
                        self.save_cache(st)
                    return False
                new = self._new_state(st, ttl)
                if self.remote.write(sha, new):
                    self.save_cache(new)
                    return True
            return False
        finally:
            self._unlock(fd)

    def ensure(self, role: str | None = None) -> bool:
        """check, else acquire. With `role` (the ExecCondition of a role unit): when the arbiter cannot be
        reached, the role is queued and the next tick that holds the lease starts it (boot before the
        network is up). A role refused because the other host holds the lease is not queued."""
        if self.check():
            return True
        try:
            return self.acquire()
        except NetError:
            if role and ROLE_RE.match(role):
                self._write_json("fenced.json", sorted(set(self._fenced()) | {role}))
            raise

    def renew(self, ttl: int | None = None) -> bool:
        fd = self._lock()
        try:
            sha, st = self.remote.read()
            if not st or st.get("holder") != self.cfg.host:
                if st and not st.get("_invalid"):
                    self.save_cache(st)
                return False
            new = self._new_state(st, ttl)
            if self.remote.write(sha, new):
                self.save_cache(new)
                return True
            return False
        finally:
            self._unlock(fd)

    def release(self) -> bool:
        """Stop the local roles (with handoff), then free the lease. False when this host does not hold it."""
        sha, st = self.remote.read()
        if not st or st.get("holder") != self.cfg.host:
            return False
        running = self.roles.list_running()
        if running:
            self.roles.stop(running, self.cfg.stop_wait_min)
        fd = self._lock()
        try:
            sha, st = self.remote.read()
            if not st or st.get("holder") != self.cfg.host:
                return False
            free = {"holder": "", "epoch": int(st.get("epoch", 0)), "expires": 0, "renewed": int(self.clock()),
                    "released_by": self.cfg.host}
            if not self.remote.write(sha, free):
                return False
            self.save_cache(free)
            self._write_json("fenced.json", [])
            return True
        finally:
            self._unlock(fd)

    def watch(self) -> str:
        """One timer tick; returns what happened (for the journal)."""
        to_stop: list[str] = []
        to_start: list[str] = []
        wait = self.cfg.stop_wait_min
        fd = self._lock()
        try:
            try:
                sha, st = self.remote.read()
            except NetError as e:
                return self._fence_if_due(f"arbiter unreachable ({e})")
            holder = (st or {}).get("holder") or ""
            if st and not st.get("_invalid") and holder == self.cfg.host:
                new = self._new_state(st)
                try:
                    won = self.remote.write(sha, new)
                except NetError as e:
                    return self._fence_if_due(f"renew failed ({e})")
                if not won:
                    return "renew lost a race; next tick decides"
                self.save_cache(new)
                to_start = [r for r in self._fenced() if r not in self.roles.list_running()]
                self._write_json("fenced.json", [])
                result = f"renewed (epoch {new['epoch']})"
            elif self._valid_for_other(st):
                if st and not st.get("_invalid"):
                    self.save_cache(st)
                to_stop = self.roles.list_running()
                wait = 1
                result = f"held by {holder or 'unknown'}"
            else:
                mine_released = st is not None and not holder and st.get("released_by") == self.cfg.host
                if not self.cfg.auto_takeover or mine_released:
                    if st:
                        self.save_cache(st)
                    return "lease free; not taking it" if mine_released else "lease free; auto takeover off"
                new = self._new_state(st)
                if not self.remote.write(sha, new):
                    return "takeover lost a race"
                self.save_cache(new)
                running = self.roles.list_running()
                wanted = list(dict.fromkeys(self.cfg.takeover_roles + self._fenced()))
                to_start = [r for r in wanted if r not in running]
                self._write_json("fenced.json", [])
                result = f"took over from {holder or 'nobody'} (epoch {new['epoch']})"
        finally:
            self._unlock(fd)
        if to_stop:
            self.roles.stop(to_stop, wait)
            result += f"; stopped {', '.join(to_stop)}"
        if to_start:
            self.roles.start(to_start)
            result += f"; started {', '.join(to_start)}"
        return result

    def _fence_if_due(self, why: str) -> str:
        c = self.load_cache()
        if c.get("holder") != self.cfg.host:
            return f"{why}; not the holder"
        left = float(c.get("expires", 0)) - self.clock()
        if left > self.cfg.fence_margin:
            return f"{why}; {int(left)} s left on the lease"
        running = self.roles.list_running()
        if running:
            self._write_json("fenced.json", sorted(set(self._fenced()) | set(running)))
            self.roles.stop(running, self.cfg.stop_wait_min)
            return f"{why}; fenced: stopped {', '.join(running)}"
        return f"{why}; fenced (no roles running)"

    def describe(self, st: dict | None) -> str:
        if st is None:
            return "no lease yet"
        if st.get("_invalid"):
            return "unreadable lease state (acquire --force to reset)"
        holder = st.get("holder") or ""
        if not holder:
            by = st.get("released_by") or "?"
            return f"free (released by {by}, epoch {st.get('epoch', 0)})"
        left = int(float(st.get("expires", 0)) - self.clock())
        when = "expired" if left <= 0 else f"{left // 60} min {left % 60} s left"
        return f"{holder}, epoch {st.get('epoch', 0)}, {when}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="workstation-lease", description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--state-dir", help="state directory (for gates run by root for the user)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="show the lease")
    s.add_argument("--cached", action="store_true", help="from the local cache, no network")
    sub.add_parser("check", help="exit 0 when this host holds the lease (local cache only)")
    e = sub.add_parser("ensure", help="check, else acquire a free or expired lease")
    e.add_argument("--role", help="role unit instance; queued for the next tick when the arbiter is unreachable")
    a = sub.add_parser("acquire", help="take a free or expired lease")
    a.add_argument("--force", action="store_true", help="take it even while the other host holds it")
    r = sub.add_parser("renew", help="renew the lease this host holds")
    r.add_argument("--ttl", type=int, help="seconds (for example 2700 before a reboot)")
    sub.add_parser("release", help="stop the local roles, then free the lease")
    sub.add_parser("watch", help="one timer tick: renew, take over or fence")
    args = ap.parse_args(argv)

    if not args.config.exists():
        if args.cmd in ("check", "ensure"):
            return 0  # the lease is not configured on this host: gates stay open
        print("lease not configured on this host", file=sys.stderr if args.cmd != "status" else sys.stdout)
        return 0 if args.cmd == "status" else 3
    try:
        cfg = load_config(args.config, args.state_dir)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"workstation-lease: bad config {args.config}: {e}", file=sys.stderr)
        return 3
    lease = Lease(cfg)
    try:
        if args.cmd == "check":
            return 0 if lease.check() else 1
        if args.cmd == "status":
            if args.cached:
                c = lease.load_cache()
                print(lease.describe(c or None) + (" (cached)" if c else ""))
            else:
                _, st = lease.remote.read()
                print(lease.describe(st))
            return 0
        if args.cmd == "ensure":
            if lease.ensure(role=args.role):
                return 0
            print(f"workstation-lease: lease held by {lease.describe(lease.load_cache() or None)}", file=sys.stderr)
            return 1
        if args.cmd == "acquire":
            ok = lease.acquire(force=args.force)
            print(("acquired: " if ok else "not acquired: ") + lease.describe(lease.load_cache() or None))
            return 0 if ok else 1
        if args.cmd == "renew":
            ok = lease.renew(ttl=args.ttl)
            print(("renewed: " if ok else "not renewed: ") + lease.describe(lease.load_cache() or None))
            return 0 if ok else 1
        if args.cmd == "release":
            ok = lease.release()
            print("released" if ok else "not released: this host does not hold the lease")
            return 0 if ok else 1
        if args.cmd == "watch":
            print(lease.watch())
            return 0
    except NetError as e:
        print(f"workstation-lease: {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
