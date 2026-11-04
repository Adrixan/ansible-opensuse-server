#!/usr/bin/python3
"""Declare Claude Code user-scope MCP servers: add or fix the listed ones through the claude CLI.

Input: argv[1] a JSON list of {"name", "config", "requires_path"?}, argv[2] the claude binary. A server
whose required path is missing on this machine is skipped; servers not in the list are never touched.
Prints CHANGED when anything was written.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    spec = json.loads(sys.argv[1])
    claude = sys.argv[2]
    state = json.loads((Path.home() / ".claude.json").read_text())
    current = state.get("mcpServers", {})
    changed = False
    for entry in spec:
        need = [os.path.expanduser(p) for p in entry.get("requires_path", [])]
        if not all(os.path.exists(p) for p in need):
            continue
        want = entry["config"]
        have = current.get(entry["name"])
        if have is not None and all(have.get(k) == v for k, v in want.items()):
            continue
        if have is not None:
            subprocess.run([claude, "mcp", "remove", "--scope", "user", entry["name"]],
                           capture_output=True, text=True, check=True)
        subprocess.run([claude, "mcp", "add-json", "--scope", "user", entry["name"], json.dumps(want)],
                       capture_output=True, text=True, check=True)
        changed = True
    if changed:
        print("CHANGED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
