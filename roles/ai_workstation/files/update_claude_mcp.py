#!/usr/bin/env python3
import json
import os
import sys

if len(sys.argv) < 3:
    print("Usage: update_claude_mcp.py <claude_json_path> <github_token>")
    sys.exit(1)

path = sys.argv[1]
github_token = sys.argv[2]
home = os.path.dirname(path)

try:
    with open(path, "r") as f:
        data = json.load(f)
except Exception:
    data = {}

data["mcpServers"] = {
    "github": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": github_token}
    },
    "puppeteer": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": {}
    },
    "sqlite": {
        "type": "stdio",
        "command": "uvx",
        "args": ["--with", "mcp<=1.1.2", "mcp-server-sqlite", "--db-path", os.path.join(home, "code/workspace.db")],
        "env": {}
    },
    "memory": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {}
    },
    "fetch": {
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {}
    },
    "git": {
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git"],
        "env": {}
    },
    "arxiv": {
        "type": "stdio",
        "command": "uvx",
        "args": ["arxiv-mcp-server", "--storage-path", os.path.join(home, "Obsidian/Ph.D./Papers/arxiv")],
        "env": {}
    },
    "zotero": {
        "type": "stdio",
        "command": "uvx",
        "args": ["zotero-mcp-server"],
        "env": {"ZOTERO_LOCAL": "true"}
    }
}

with open(path, "w") as f:
    json.dump(data, f, indent=2)

print("Updated Claude MCP servers successfully.")
