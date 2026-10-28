"""Run mcp-proxy for the shared loopback MCP services, with two safeguards.

1. Host header validation: mcp-proxy has no DNS rebinding protection, so a web page that rebinds its
   own hostname to 127.0.0.1 could call these servers (mail, Nextcloud, tokens) from the browser.
   Every Starlette app mcp-proxy builds gets a TrustedHostMiddleware that accepts only loopback hosts.
2. Startup filter: mcp-proxy stops all servers when one exits, so an entry is skipped when its command
   is not installed, a `requiresEnv` variable is empty or a `requiresPath` is missing.
3. `defaultEnv`: values used only where the service environment leaves the variable unset (config
   `env` always overrides the environment, so it cannot express a fallback).

Usage: mcp-shared-proxy.py <servers.json> [mcp-proxy options]
"""

import json
import logging
import os
import shutil
import sys
import tempfile

from starlette import applications
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
_starlette_init = applications.Starlette.__init__


def _init_with_host_check(self, *args, middleware=None, **kwargs):
    host_check = Middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    _starlette_init(self, *args, middleware=[host_check, *(middleware or [])], **kwargs)


def _unmet(server: dict) -> list[str]:
    """Return the reasons a server cannot start; empty when it can."""
    reasons = [] if shutil.which(server["command"]) else [f"{server['command']} not installed"]
    reasons += [f"{var} not set" for var in server.pop("requiresEnv", []) if not os.environ.get(var)]
    reasons += [f"{path} missing" for path in server.pop("requiresPath", []) if not os.path.exists(path)]
    return reasons


def _runnable_config(path: str) -> str:
    """Write a copy of the config to the runtime dir without the servers that cannot start."""
    with open(path) as f:
        config = json.load(f)
    servers = config["mcpServers"]
    for name in list(servers):
        defaults = servers[name].pop("defaultEnv", {})
        servers[name].setdefault("env", {}).update(
            {var: value for var, value in defaults.items() if not os.environ.get(var)}
        )
        reasons = _unmet(servers[name])
        if reasons:
            logging.warning("Skipping '%s': %s", name, "; ".join(reasons))
            del servers[name]
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    fd, out = tempfile.mkstemp(dir=runtime_dir, prefix="mcp-shared.", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(config, f)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    config = _runnable_config(sys.argv[1])
    sys.argv = [sys.argv[0], *sys.argv[2:], "--named-server-config", config]
    applications.Starlette.__init__ = _init_with_host_check
    from mcp_proxy.__main__ import main as proxy_main

    try:
        proxy_main()
    finally:
        os.unlink(config)


if __name__ == "__main__":
    main()
