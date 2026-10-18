#!/usr/bin/env python3
"""Remove legacy user-scope MCP servers and gateway overrides from ~/.claude.json.

MCP servers are now provided by the yadm-tracked workstation-mcp plugin, so the
user-scope copies (which also stored the GitHub token in plaintext) must go.
"""
import json
import os
import sys
import tempfile

LEGACY_MODELS = {"qwen3.7-plus", "qwen3.8-max", "qwen3.8-flash", "deepseek-v4-pro", "glm-5.2"}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: purge_claude_mcp.py <claude_json_path> [server_name ...]", file=sys.stderr)
        return 1
    path, names = sys.argv[1], set(sys.argv[2:])
    if not os.path.exists(path):
        print("ALREADY_SET")
        return 0
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False
    for key in ("env", "modelOverrides", "customApiKeyResponses"):
        if key in data:
            del data[key]
            changed = True
    if data.get("model") in LEGACY_MODELS:
        del data["model"]
        changed = True
    servers = data.get("mcpServers", {})
    for name in names & servers.keys():
        del servers[name]
        changed = True

    if not changed:
        print("ALREADY_SET")
        return 0
    # Atomic replace that keeps the 0600 mode of the original file
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".claude.json.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.chmod(tmp, os.stat(path).st_mode & 0o777)
    os.replace(tmp, path)
    print("CONFIGURED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
