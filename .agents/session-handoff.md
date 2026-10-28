# Session Handoff State

## Active Intent
US-15.1 & US-15.2: System-wide RethinkDNS DoH (`dns_setup`) matching Firefox TRR, `localhost` cloaking for `cloudflared`, and a local TLS 1.3 ECH reverse proxy (`dragtokens-ech-proxy.service` in `ai_workstation`) so OpenCode reaches `dragtokens.com` over ECH.

## Task & Story Status
- Current Stories: US-15.1 (`dns_setup`) and US-15.2 (`dragtokens-ech-proxy`), complete and verified live on localhost (2026-10-19), idempotent (`dns_setup`: `ok=10, changed=0`; `ai_workstation`: `ok=65, changed=0`).

## Key Decisions & Architecture
- Server set (all harnesses): github (remote `https://api.githubcopilot.com/mcp/`, PAT header), playwright (`/usr/local/bin/playwright-mcp`, system chromium, headless, isolated), memory (`MEMORY_FILE_PATH=~/sync/ai/mcp-memory.jsonl`), fetch, git, arxiv, zotero, markitdown, serena (`--project-from-cwd --open-web-dashboard False`), nextcloud, docker (`DOCKER_HOST=tcp://127.0.0.1:2375`). context7 only in Antigravity/OpenCode (Claude uses the claude.ai connector). sqlite and puppeteer removed.
- Antigravity/OpenCode: serena, nextcloud, docker disabled by default (those harnesses load all schemas up front; Nextcloud alone has 181 tools).
- Claude Code: yadm-tracked plugin marketplace `~/.config/ai/claude-plugins` (`workstation-mcp@workstation`), `${VAR}` secrets expanded at runtime; `permissions.ask` rules for Nextcloud send/share/delete/trash and GitHub merge/delete.
- 2026-10-20: `instructions.yml`, `skills.yml` and `templates/AGENTS.md.j2` removed. Agent instructions, their symlinks and skills are tracked only in yadm; this repo covers technical setup only.
- yadm auto-alt re-renders templates on ordinary yadm commands with the caller's environment; `~/.config/ai/env` must therefore export every templated secret (now includes `NEXTCLOUD_*`).

## Immediate Next Steps
- Supply Nextcloud app password and re-run: `NEXTCLOUD_HOST=… NEXTCLOUD_USERNAME=… NEXTCLOUD_PASSWORD=… ansible-playbook main.yml -e enable_ai_workstation=true`.
- NowCoding provider and `NOWCODING_API_KEY` removed entirely (2026-10-18).
- On Docker hosts: run `docker` + `ai_workstation` roles to get the read-only proxy.
- Open decision: `laptops` and `master` have diverged (54 vs 15 commits). The new auto-merge rule deliberately does not merge `laptops` into `master`; do that only on explicit approval.

## 2026-10-19: US-14.2 OpenCode on DragTokens
- OpenCode CLI v1 now comes from `ai_desktop` (`tasks/opencode_cli.yml`, native installer into `~/.opencode/bin`, daily `opencode-cli-update.timer`); `roles/opencode` and the npm global install are gone.
- `ai_workstation` handles `DRAGTOKENS_API_KEY` like the Nextcloud secrets (env var or existing `~/.config/ai/env`). New machine: `DRAGTOKENS_API_KEY=… ansible-playbook main.yml -e enable_ai_workstation=true -e enable_ai_desktop=true`.
- yadm `opencode.json##template` defines provider `dragtokens`; plan agent `dragtokens/gpt-6-astra`, build agent `dragtokens/gpt-6.1-sol`. Top-level `model` stays `anthropic/claude-sonnet-4-5`.
- Open: no live API call verified because the current network's FortiGuard DNS blocks dragtokens.com. Test on another network: `opencode run -m dragtokens/gpt-6-astra "ping"`. Pool binding (codex-pro vs enterprise) is set on the DragTokens dashboard and cannot be checked from here.

## 2026-10-19: US-14.3 OpenCode 2
- OpenCode 2.0.32 installed via the V2 installer; `ai_desktop` migrates any V1 binary and the daily `opencode-cli-update.timer` runs `opencode upgrade --method curl`.
- V2 owns its background server: `opencode-server.service` only runs `opencode service start` at login. Do not change it back to `serve --service`. Listen address lives in `~/.config/opencode/service.json` (also holds the server password; git-ignored).
- The V1 config format in the yadm template stays (V2 reads it). Converting to the native V2 shape is optional; don't do it while any machine still runs V1.
- Dropped: `@frankhommers/opencode-yolo` plugin and `/yolo` command (V1 plugin API, fails to load in V2). Closest built-in replacement: `opencode --auto` (auto-approves permissions that aren't explicitly denied).

## 2026-10-19: US-14.4 native V2 config
- yadm template now uses the native V2 shape; machines still on OpenCode V1 cannot read it, so run the playbook (`ai_desktop` migrates to V2) right after `yadm pull`.
- DragTokens is blocked on the `schule.intern` network: system DNS answers with the Fortinet block page (208.91.112.55), and connecting to the real Cloudflare IP gets a TLS reset on SNI `dragtokens.com`. Firefox only reaches it through DoH (`network.trr.mode=3`, RethinkDNS), probably plus ECH (unverified). Making OpenCode work there would mean evading the school's filter: the user decides, ideally via school IT. Test on another network instead.

## 2026-10-19: US-15.1 System-wide RethinkDNS DoH (`dns_setup`)
- Added `roles/dns_setup` (`enable_dns_setup` in `group_vars/all.yml` and `main.yml`) to deploy `dnscrypt-proxy` on `127.0.0.1:53` via `dnscrypt-proxy.socket`, configured with Firefox's RethinkDNS DoH endpoint (`https://sky.rethinkdns.com/1-5apwaaejaebrciqbftqiaacugaqaaaai`, strict DoH with `ignore_system_dns = true`).
- Only `.intern` and `.local` domains are excluded from DoH and forwarded via `/etc/dnscrypt-proxy/forwarding-rules.txt` to `/run/dnscrypt-proxy-dhcp-resolv.conf` (maintained by `/etc/NetworkManager/dispatcher.d/10-dnscrypt-dhcp-dns.sh`), with bootstrap fallback.
- Enabled `/etc/dnscrypt-proxy/cloaking-rules.txt` (`localhost` -> `127.0.0.1` / `::1`, `cloak_ptr = true`) so pure-DNS clients that bypass `/etc/hosts` when `127.0.0.1:53` is in `/etc/resolv.conf` (such as Go's `cloudflared` daemon dialing `ssh://localhost:22`) resolve `localhost` instead of getting `NXDOMAIN` from `block_unqualified = true`.
- NetworkManager uses `/etc/NetworkManager/conf.d/90-dnscrypt-proxy.conf` (`[global-dns-domain-*] servers=127.0.0.1`) so `/etc/resolv.conf` points to `127.0.0.1`. Live-verified and idempotent (`ok=10, changed=0, failed=0`).

## 2026-10-19: US-15.2 DragTokens TLS 1.3 ECH Proxy for OpenCode (`ai_workstation`)
- Root cause for OpenCode failing to reach `dragtokens.com`: OpenCode's bundled Bun v1.4.2 runtime does not query DNS `HTTPS` (`TYPE65`) records or negotiate TLS 1.3 Encrypted Client Hello (ECH), so it sends `dragtokens.com` in plaintext SNI and gets reset (`RST`) by the network's FortiGate (`FG200FT921914884`), whereas Firefox uses ECH (`cloudflare-ech.com` outer SNI from the `HTTPS` record).
- Added `roles/ai_workstation/files/dragtokens-ech-proxy.go` and `tasks/dragtokens_ech_proxy.yml` (`dragtokens-ech-proxy.service` on `127.0.0.1:4097`, built with Go 1.27 `crypto/tls.Config.EncryptedClientHelloConfigList` using the `TYPE65` record from `127.0.0.1:53`).
- Pointed yadm `~/.config/opencode/opencode.json##template` `providers.dragtokens.settings.baseURL` to `http://127.0.0.1:4097/v1`. OpenCode now reaches DragTokens cleanly (`GET /v1/models` returns 200; `opencode run -m dragtokens/gpt-6-astra` receives API response from DragTokens: `Insufficient user quota, remaining quota: ¥0.000000`). Top up or check pool binding on the DragTokens dashboard.

## 2026-10-20: Document tooling, Zotero, linger, login shell
- `office_suite`: pinned Marp CLI 4.5.1 in `/opt/marp-cli` (npm overrides, audit gate) and pandoc 3.12.1 (checksum-pinned).
- New role `zotero` (`enable_zotero`): flatpak, default profile when missing, Better BibTeX 9.0.71 (checksum-pinned), `user.js` with local API, UTF-8 export, citekey format and `extensions.autoDisableScopes` 14 so the sideloaded add-on starts enabled (verified with an isolated Zotero instance on a fresh profile).
- Lingering: `ai_workstation_linger` (default true) and in `edu_publisher`. Zsh login shell in `shell_environment`.
- Verified: two consecutive runs of zotero, shell_environment, ai_workstation, edu_publisher; second run changed=0.

## 2026-10-21: Docker on schulpc
- `docker` role updated: Compose v2 from zypper (`docker-compose` 5.6.0, `docker compose` CLI plugin) replaces the EOL pip Compose v1 (`--break-system-packages`); `docker-compose@.service` now calls `/usr/bin/docker compose` (used by `docker_pi_hole` and the `ai_workstation` socket proxy).
- Applied on schulpc with `-e enable_docker=true` only: Docker 29.7.2-ce active and enabled, second run `changed=0`, test container pulled and resolved DNS, then removed. No compose units, no containers, user not in the `docker` group.
- Later the same day (user request): docker MCP enabled on schulpc by running `ai_workstation` with Docker present (`-e enable_docker=true -e enable_ai_workstation=true`; dry run showed only the proxy tasks change). The socket proxy got 503 because SELinux (Tumbleweed default, `selinux-enabled: true` in daemon.json) denies `container_t` write access to `docker.sock`; fixed with `label:disable` for that container only (no policy module, which would open the socket to every container). Verified: GET /version and /containers/json 200, POST create and DELETE 403; docker MCP connected in OpenCode, Antigravity listed containers through it. Second run `changed=0`.
- New `docker_users` (role default `[]`, `group_vars/all.yml` sets `target_user`): schulpc user Adrixan is in the `docker` group. Other machines join on their next docker role run. Takes effect after a new login.

## 2026-10-21: research, security and diagram MCP servers
- `ai_workstation` adds: uv tools package-version-check-mcp and semgrep (uv override `mcp==1.30.0`, CVE-2026-59951, kept in the uv receipt); zypper osv-scanner; pinned npm prefixes `/opt/mcp/{openalex,excalidraw,drawio,obsidian-hybrid-search}` with overrides, `allowScripts` allowlist and npm audit gate (`tasks/mcp_node.yml`); Phở Research Tools from commit 42e4ea5 with pnpm audit and loopback user service (`tasks/pho.yml`, `files/pho-mcp-local.ts`); Obsidian Hybrid Search user service per vault (`tasks/obsidian_search.yml`, default only Ph.D. on 3939).
- Plugin refresh task: Claude Code caches plugins by version, the role now updates `workstation-mcp` when the yadm `plugin.json` version is newer.
- Verified on schulpc: check mode clean, live run ok, second run changed=0, all eight servers connected in `claude mcp list`.
- Open decisions (asked the user): Adrixan vault index (RAM), semgrep metrics, OpenAlex/Crossref contact mail, laptops rollout.
- Replacements vs. the original proposal: Google `osv-scanner experimental-mcp` instead of StacklokLabs/osv-mcp (stdio, no 0.0.0.0 listener); official `@drawio/mcp` instead of lgazo/drawio-mcp-server (unfixable node-forge advisory).

## 2026-10-21: Tier 2 MCP servers and Adrixan vault index
- Adrixan vault index service on 3940 (user chose all machines; first index 22 min, 2154 of 2159 notes, ~530 MB RSS).
- Tier 2 (user picks): lighthouse, accessibility-scanner (axe-core; replaces a11y-mcp-server, which pins puppeteer 13), Grounded Docs (user service 6280), NASA, Open-Meteo, mcp-searxng (ihor-sokoliuk, replaces SecretiveShell), wikipedia-mcp, openroute-mcp (mcp override). Security group (Ghidra, Wireshark, RSigma, Burp) not chosen.
- Chromium wrapper strips `--no-sandbox`; SearXNG container uid 977, caps dropped, certifi patched (PYSEC-2026-4320), osv-scanner image scan clean.
- Verified: idempotent (changed=0), all Tier 2 servers connected in Claude except openroute (no key yet).
- Pending from the user: NASA and OpenRouteService API keys (`NASA_API_KEY=… OPENROUTESERVICE_API_KEY=… ansible-playbook main.yml -e enable_ai_workstation=true`), laptop rollout.
- 2026-10-21 (later): schulpc ran out of memory; Adrixan vault index now skipped there via `skip_hosts: [schulpc]` (stopped and disabled by the role), laptops only.

## 2026-10-23: SearXNG retired, DuckDuckGo MCP added
- Peter: SearXNG is too resource-intensive. `tasks/searxng.yml` now only removes it (container, local and upstream images, `/etc/docker-compose/searxng` with the secret key, `/opt/mcp/searxng`, `/usr/local/bin/mcp-searxng`); drop the file once m11x and xps13 have run the role. Templates, certifi fix and `ai_workstation_searxng*` vars deleted.
- New uv tool `duckduckgo-mcp-server` (0.7.0, without the `[browser]` extra, so no curl TLS impersonation); OSV and pip-audit clean (43 packages). yadm templates for all three harnesses switched from searxng to duckduckgo (plugin 1.4.0).
- Verified on schulpc: check mode clean, live run changed=8, second run changed=0; headless probes returned results in Claude Code, OpenCode (`-m dragtokens/gpt-6.1-sol`) and Antigravity.
- Laptops: `yadm pull`, then `ansible-playbook main.yml -e enable_ai_workstation=true`.

## 2026-10-23: Law, YouTube, ÖBB and Thunderbird MCP servers
- Node (pinned, npm audit gate): `@cyanheads/ris-austria-mcp-server` 0.5.2, `@cyanheads/eur-lex-mcp-server` 0.19.1. uv tools: `oebb-mcp-server` 0.2.8 (PyPI), `mcp-youtube-transcript` from the v0.8.1 commit (PyPI stops at 0.3.5; uv tool entries accept an optional `spec`). pip-audit clean for both.
- `tasks/thunderbird_mcp.yml`: thunderbird-mcp 0.9.3 bridge (no dependencies) and the .xpi, checksum-pinned to the release commit, wrapper `/usr/local/bin/thunderbird-mcp`. The add-on is installed by hand in Thunderbird (153.4 ESR supported).
- Verified on schulpc: headless probes in Claude Code (all four), OpenCode and Antigravity (RIS, EUR-Lex).

## 2026-10-27: Research and Code remote-control servers
- `ai_workstation_claude_rc_servers` gained `research` (`~/Obsidian/Adrixan/Research`, rules in its `AGENTS.md`) and `code` (`~/code`). On schulpc both configs are deployed by hand to match the role output; both run and are enabled (Research trust accepted by Peter 2026-10-27; a new directory needs `cd <dir> && claude` once to accept trust).
- The five servers were restarted 2026-10-27 so they load `TRIP_PLANNER_TOKEN`; servers read `~/.config/ai/env` only at start, so restart them after changing it.

## 2026-10-28: Remote-control servers (relabel, restart scope, no home server)
- `research` server relabelled "Deep Research" (fresh standby session after a bridge-pointer reset). A home-directory server was requested and dropped: Claude Code never saves trust for `$HOME`, so `claude remote-control` there exits "Workspace not trusted" (verified on schulpc).
- Restart task now restarts only servers whose `.conf` changed (all on a unit change). The old condition restarted all five, which also killed the session running the playbook.
- Resolved 2026-10-28 (next section): the npm audit gate failures.

## 2026-10-28: Latest releases everywhere, no version pins (Peter's order)
- Node MCP servers and Marp: manifests depend on `latest`, every run `npm update`s the whole tree,
  overrides force affected transitive deps to `latest` (excalidraw: zod, mermaid, dompurify, katex,
  lodash-es, nanoid, uuid, chevrotain, langium, MCP SDK, sass; Marp: puppeteer-core, katex, xmldom,
  basic-ftp, zod), `allowScripts` keyed by name. Runtime checked: excalidraw tools/list and
  create_element on zod 4, Marp HTML and PDF, docs native modules, Phở tools and a live tool call.
- uv: `mcp<2` caps for semgrep (still pins vulnerable mcp==1.29.0) and openroute-mcp (breaks on 2.x);
  youtube-transcript from its latest GitHub release tag; `uv tool upgrade --all` every run.
- GitHub downloads (pandoc, Better BibTeX, Thunderbird MCP add-on and bridge, docker-socket-proxy tag)
  resolve the latest stable release via the new `github_release` role; files verified against the
  sha256 digest in the release metadata.
- Phở follows upstream HEAD with pnpm@latest (`manage-package-manager-versions=false`, upstream names
  pnpm 9.15.4), `files/pho-update-deps.sh` updates the lockfile in a manifest copy, override zod=latest;
  the old lockfile had 7 advisories.
- Flatpaks (Zotero, Obsidian, Signal) updated via `flatpak_setup` `tasks_from: update`. ECH proxy is
  rebuilt when the Go toolchain is newer than the binary's.
- zypper: per-package `state: latest` failed (new chromium needs Qt 6.12 while KDE is on 6.11; only
  "solution" was removing the X11 session). Tumbleweed supports only `zypper dup`, so roles keep
  `state: present` and `system_update` now uses `state: dist-upgrade` (not run by me). Pending
  Tumbleweed snapshot on schulpc: run `system_update` or `sudo zypper dup`.
- Verified: ai_workstation, office_suite, zotero run clean twice (second run 0 changed); all Node
  servers on the registry's latest; docs and obsidian-hybrid-search restarted onto the new code (now
  restarted automatically when `npm update` changes their tree).

## 2026-10-28: Shared MCP services and Claude plugin split
- Peter approved (from the Research session): stateless stdio MCP servers now run once in `mcp-shared.service` (user unit, `tasks/mcp_shared.yml`): `mcp-proxy` (uv tool, latest 0.13.0, pip-audit clean) behind `/usr/local/libexec/mcp-shared-proxy.py` on `127.0.0.1:8790`, URL `/servers/<name>/mcp`, `--stateless` (clients survive restarts), `--pass-environment` (secrets from `~/.config/ai/env`, none in `~/.config/mcp-shared/servers.json`). 25 servers in `ai_workstation_mcp_shared_servers`; playwright, serena, git, osv and semgrep stay stdio (per-session state or cwd-relative paths).
- Launcher safeguards: TrustedHostMiddleware (loopback Host only; verified 400 for a foreign Host, mcp-proxy has no DNS rebinding protection); skips an entry whose command is missing, `requires_env` empty or `requires_path` missing, because mcp-proxy stops all servers when one exits (reproduced with openroute without a key); `default_env` for fallbacks (NASA DEMO_KEY).
- Measured on schulpc: one idle Claude Code session had 33 to 35 processes, about 2.3 GB (RSS plus swap); a fresh session now has 6 processes and 222 MB in a vault folder (dev plugin off), 14 processes and 657 MB in a code repo; the shared service is about 2.2 GB RSS once, right after start.
- Restart rules: on launcher/config/unit change, after `uv tool upgrade` or Node server updates in the role, and nightly via `ExecStartPost` in `ai-mcp-tools-update.service`.
- `TRIP_PLANNER_TOKEN` is now kept in `ai_env.j2` (the 2026-10-27 22:29 run had dropped it; the token must be supplied again: `TRIP_PLANNER_TOKEN=… ansible-playbook main.yml -e enable_ai_workstation=true`). Until then trip-planner (and openroute without a key) are skipped by the shared service.
- yadm side (same day): plugin split `workstation-mcp` 2.0.0 (core) plus `workstation-dev`, `workstation-research`, `workstation-travel` 1.0.0; OpenCode and Antigravity templates point the same 25 servers at the shared URLs (Termux keeps stdio). The role task now registers all four plugins.
- Laptops: run this role BEFORE `yadm pull`, otherwise the new templates point at a service that is not there yet.
- Verified: full `ai_workstation` run changed=0 on the second run; `claude mcp list` in Research (no dev servers) and in a code repo (all dev servers); headless probes called memory and RIS through the plugin tool names.

## 2026-10-28: Greeter and on-demand remote-control roles
- Peter's choices: only the greeter starts at boot; custom roles live in `~/Obsidian/Adrixan/AI/Roles`; no auto-stop by default (`rc up --ttl` optional); `rc up` refuses below 1 GB MemAvailable without `--force`.
- `ai_workstation_claude_rc_servers` gained `autostart` (greeter only), `description`, `args` (rendered as `RC_ARGS`, appended to `claude remote-control`, e.g. `--spawn worktree`), plus roles `greeter` (`~/Obsidian/Adrixan/AI/Greeter`, all plugins off) and `travel` (`~/Obsidian/Adrixan/Travel`, dev off).
- `remote_control.yml`: enables only autostart roles, disables (never stops) the others, and no longer restarts anything; it reports running roles with old settings (`rc restart <role>`). The trust warning covers autostart roles only; `rc up` checks trust for the rest (parent trust for non-git folders, own trust for a git repo).
- yadm: `~/.local/bin/rc` (ls, up, down, restart, new, rm, logs; busy guard 15 min, RAM guard, ttl via systemd-run timer `rc-ttl-<role>`), global skill `rc-roles`. An `rc trust` command (writing `hasTrustDialogAccepted` into `~/.claude.json`) and a `permissions.allow` rule for `rc` in the Greeter were refused by the auto-mode classifier and dropped: trust stays a manual `cd <dir> && claude`.
- Open: Peter must trust Greeter, Travel and the Roles root once interactively, then `rc up greeter` (or rerun the role, which enables it). phd, teaching, educator, research and code still run from before and are disabled for boot; they keep running until `rc down`.
