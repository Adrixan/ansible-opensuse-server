#!/usr/bin/python3
"""Tests for roles/ai_workstation/files/workstation-lease.py.

Run: python3 -I tests/test_workstation_lease.py
A local bare repository stands in for the GitHub repo; the clock and the role controller are fakes.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "roles" / "ai_workstation" / "files" / "workstation-lease.py"
spec = importlib.util.spec_from_file_location("workstation_lease", SRC)
wl = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["workstation_lease"] = wl
spec.loader.exec_module(wl)


class Clock:
    def __init__(self, t: float = 1_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeRoles:
    def __init__(self) -> None:
        self.running: set[str] = set()
        self.stopped: list[tuple[str, int]] = []
        self.started: list[str] = []

    def list_running(self) -> list[str]:
        return sorted(self.running)

    def stop(self, roles: list[str], wait_min: int) -> None:
        for r in roles:
            self.stopped.append((r, wait_min))
            self.running.discard(r)

    def start(self, roles: list[str]) -> None:
        for r in roles:
            self.started.append(r)
            self.running.add(r)


class LeaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="wl-test-", dir=os.environ.get("XDG_RUNTIME_DIR") or None))
        self.remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        self.clock = Clock()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, host: str, remote: str | None = None, **over) -> tuple[object, FakeRoles]:
        cfg = wl.Config(
            remote=remote or str(self.remote),
            host=host,
            state_dir=self.tmp / f"state-{host}",
            **over,
        )
        roles = FakeRoles()
        return wl.Lease(cfg, clock=self.clock, roles=roles), roles

    def remote_state(self) -> dict:
        out = subprocess.run(["git", "--git-dir", str(self.remote), "show", "lease:lease.json"],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    # --- acquire / check ---------------------------------------------------------------------------
    def test_first_acquire_creates_the_lease(self) -> None:
        a, _ = self.make("schulpc")
        self.assertTrue(a.acquire())
        st = self.remote_state()
        self.assertEqual((st["holder"], st["epoch"]), ("schulpc", 1))
        self.assertEqual(st["expires"], self.clock.t + 600)
        self.assertTrue(a.check())

    def test_second_host_cannot_take_a_valid_lease(self) -> None:
        a, _ = self.make("schulpc")
        b, _ = self.make("xps")
        self.assertTrue(a.acquire())
        self.assertFalse(b.acquire())
        self.assertFalse(b.check())
        self.assertEqual(self.remote_state()["holder"], "schulpc")

    def test_compare_and_swap_rejects_a_stale_writer(self) -> None:
        a, _ = self.make("schulpc")
        b, _ = self.make("xps")
        sha, st = b.remote.read()  # xps reads the empty state ...
        self.assertIsNone(sha)
        self.assertTrue(a.acquire())  # ... schulpc wins meanwhile ...
        won = b.remote.write(sha, {"holder": "xps", "epoch": 1, "expires": self.clock.t + 600})
        self.assertFalse(won)  # ... so the stale create is refused
        self.assertEqual(self.remote_state()["holder"], "schulpc")

    def test_history_does_not_grow(self) -> None:
        a, _ = self.make("schulpc")
        a.acquire()
        for _ in range(5):
            self.clock.t += 120
            a.watch()
        count = subprocess.run(["git", "--git-dir", str(self.remote), "rev-list", "--count", "lease"],
                               capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(count, "1")

    def test_check_closes_inside_the_fence_margin(self) -> None:
        a, _ = self.make("schulpc")
        a.acquire()
        self.clock.t += 600 - 240 - 1
        self.assertTrue(a.check())
        self.clock.t += 2
        self.assertFalse(a.check())

    def test_check_needs_no_network(self) -> None:
        a, _ = self.make("schulpc")
        a.acquire()
        shutil.rmtree(self.remote)
        self.assertTrue(a.check())

    def test_ensure_acquires_a_free_lease_and_refuses_a_held_one(self) -> None:
        a, _ = self.make("schulpc")
        b, _ = self.make("xps")
        self.assertTrue(b.ensure())
        self.assertFalse(a.ensure())

    # --- watch: renew, takeover, fencing -----------------------------------------------------------
    def test_watch_renews_and_keeps_the_epoch(self) -> None:
        a, _ = self.make("schulpc")
        a.acquire()
        self.clock.t += 120
        a.watch()
        st = self.remote_state()
        self.assertEqual((st["holder"], st["epoch"], st["expires"]), ("schulpc", 1, self.clock.t + 600))

    def test_standby_takes_over_after_expiry_plus_grace_and_starts_the_greeter(self) -> None:
        a, _ = self.make("schulpc")
        b, broles = self.make("xps")
        a.acquire()  # schulpc then loses power: no more renewals
        self.clock.t += 600 + 119
        b.watch()
        self.assertEqual(self.remote_state()["holder"], "schulpc")  # still inside the grace period
        self.assertEqual(broles.started, [])
        self.clock.t += 2
        b.watch()
        st = self.remote_state()
        self.assertEqual((st["holder"], st["epoch"]), ("xps", 2))
        self.assertEqual(broles.started, ["greeter"])
        self.assertTrue(b.check())

    def test_no_takeover_when_auto_takeover_is_off(self) -> None:
        a, _ = self.make("schulpc")
        b, broles = self.make("xps", auto_takeover=False)
        a.acquire()
        self.clock.t += 2000
        b.watch()
        self.assertEqual(self.remote_state()["holder"], "schulpc")
        self.assertEqual(broles.started, [])

    def test_returning_holder_stays_passive_and_stops_its_roles(self) -> None:
        a, aroles = self.make("schulpc")
        b, _ = self.make("xps")
        a.acquire()
        self.clock.t += 800
        b.watch()  # xps took over
        aroles.running = {"greeter"}  # schulpc comes back; its boot started the Greeter anyway
        a.watch()
        self.assertEqual(self.remote_state()["holder"], "xps")
        self.assertIn(("greeter", 1), aroles.stopped)
        self.assertFalse(a.check())
        self.assertFalse(a.ensure())

    def test_holder_fences_itself_when_it_cannot_renew(self) -> None:
        a, aroles = self.make("schulpc", remote=str(self.tmp / "missing.git"))
        # hand-write a cached lease, as if the last renew had succeeded before the network went away
        a.save_cache({"holder": "schulpc", "epoch": 1, "expires": self.clock.t + 600})
        aroles.running = {"greeter", "code"}
        self.clock.t += 300
        a.watch()  # 300 s left: outside the fence margin, nothing happens
        self.assertEqual(aroles.stopped, [])
        self.clock.t += 61
        a.watch()  # 239 s left: inside the margin, roles stop
        self.assertEqual(sorted(r for r, _ in aroles.stopped), ["code", "greeter"])
        self.assertFalse(a.check())

    def test_fenced_roles_come_back_when_the_lease_is_still_ours(self) -> None:
        a, aroles = self.make("schulpc")
        a.acquire()
        aroles.running = {"greeter", "code"}
        a.remote.url = str(self.tmp / "missing.git")  # outage
        self.clock.t += 400
        a.watch()
        self.assertEqual(aroles.running, set())
        a.remote.url = str(self.remote)  # back, and nobody took the lease
        self.clock.t += 120
        a.watch()
        self.assertEqual(sorted(aroles.started), ["code", "greeter"])
        self.assertEqual(self.remote_state()["epoch"], 1)

    def test_role_gated_while_offline_starts_once_the_lease_is_back(self) -> None:
        a, aroles = self.make("schulpc", remote=str(self.tmp / "missing.git"))
        with self.assertRaises(wl.NetError):  # boot, network not up yet: the Greeter is skipped
            a.ensure(role="greeter")
        a.remote.url = str(self.remote)
        self.clock.t += 120
        a.watch()  # free lease: taken, the Greeter starts once (not twice)
        self.assertEqual(aroles.started, ["greeter"])

    def test_role_refused_by_a_foreign_lease_is_not_queued(self) -> None:
        a, _ = self.make("schulpc")
        b, broles = self.make("xps")
        a.acquire()
        self.assertFalse(b.ensure(role="code"))
        self.clock.t += 1000
        b.watch()  # takeover starts the takeover roles only
        self.assertEqual(broles.started, ["greeter"])

    # --- release, force ----------------------------------------------------------------------------
    def test_release_stops_roles_and_the_other_host_takes_the_free_lease(self) -> None:
        a, aroles = self.make("schulpc")
        b, broles = self.make("xps")
        a.acquire()
        aroles.running = {"greeter"}
        self.assertTrue(a.release())
        self.assertEqual(aroles.running, set())
        st = self.remote_state()
        self.assertEqual((st["holder"], st["released_by"]), ("", "schulpc"))
        a.watch()  # the releasing host does not take it straight back
        self.assertEqual(self.remote_state()["holder"], "")
        b.watch()
        self.assertEqual(self.remote_state()["holder"], "xps")
        self.assertEqual(self.remote_state()["epoch"], 2)
        self.assertEqual(broles.started, ["greeter"])

    def test_release_by_a_non_holder_changes_nothing(self) -> None:
        a, _ = self.make("schulpc")
        b, _ = self.make("xps")
        a.acquire()
        self.assertFalse(b.release())
        self.assertEqual(self.remote_state()["holder"], "schulpc")

    def test_force_takes_a_valid_lease_with_a_new_epoch(self) -> None:
        a, _ = self.make("schulpc")
        b, _ = self.make("xps")
        a.acquire()
        self.assertTrue(b.acquire(force=True))
        st = self.remote_state()
        self.assertEqual((st["holder"], st["epoch"]), ("xps", 2))

    def test_renew_with_a_longer_ttl_for_a_reboot(self) -> None:
        a, _ = self.make("schulpc")
        a.acquire()
        self.assertTrue(a.renew(ttl=2700))
        self.assertEqual(self.remote_state()["expires"], self.clock.t + 2700)

    def test_renew_refuses_a_lease_someone_else_holds(self) -> None:
        a, _ = self.make("schulpc")
        b, _ = self.make("xps")
        a.acquire()
        b.acquire(force=True)
        self.assertFalse(a.renew())
        self.assertEqual(self.remote_state()["holder"], "xps")
        self.assertFalse(a.check())

    def test_unreadable_remote_state_counts_as_free_only_with_force(self) -> None:
        a, _ = self.make("schulpc")
        a.acquire()
        sha, _ = a.remote.read()
        a.remote.write_raw(sha, "not json")
        b, _ = self.make("xps")
        self.assertFalse(b.acquire())
        self.assertTrue(b.acquire(force=True))

    # --- config ------------------------------------------------------------------------------------
    def test_config_file_is_validated(self) -> None:
        p = self.tmp / "config.json"
        p.write_text(json.dumps({"remote": "git@github.com:o/r.git", "host": "schulpc",
                                 "state_dir": str(self.tmp / "s"), "ttl": 600}))
        cfg = wl.load_config(p)
        self.assertEqual((cfg.host, cfg.ttl, cfg.grace), ("schulpc", 600, 120))
        p.write_text(json.dumps({"remote": "x", "host": "bad host;", "state_dir": "/s"}))
        with self.assertRaises(ValueError):
            wl.load_config(p)
        p.write_text(json.dumps({"remote": "x", "host": "schulpc", "state_dir": "/s", "ttl": 100,
                                 "fence_margin": 240}))
        with self.assertRaises(ValueError):  # the fence margin must fit inside the TTL
            wl.load_config(p)

    def test_cli_check_is_open_on_an_unconfigured_host(self) -> None:
        rc = subprocess.run([sys.executable, "-I", str(SRC), "--config", str(self.tmp / "none.json"), "check"],
                            capture_output=True, text=True).returncode
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
