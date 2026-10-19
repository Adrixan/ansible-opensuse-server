# Session Handoff State

## Active Intent
US-15.1 & US-15.2: System-wide RethinkDNS DoH (`dns_setup`) matching Firefox TRR, `localhost` cloaking for `cloudflared`, and a local TLS 1.3 ECH reverse proxy (`dragtokens-ech-proxy.service` in `ai_workstation`) so OpenCode reaches `dragtokens.com` over ECH.

## Task & Story Status
- Current Stories: US-15.1 (`dns_setup`) and US-15.2 (`dragtokens-ech-proxy`), complete and verified live on localhost (2026-10-19), idempotent (`dns_setup`: `ok=10, changed=0`; `ai_workstation`: `ok=65, changed=0`).

## Key Decisions & Architecture
- Server set (all harnesses): github (remote `https://api.githubcopilot.com/mcp/`, PAT header), playwright (`/usr/local/bin/playwright-mcp`, system chromium, headless, isolated), memory (`MEMORY_FILE_PATH=~/sync/ai/mcp-memory.jsonl`), fetch, git, arxiv, zotero, markitdown, serena (`--project-from-cwd --open-web-dashboard False`), nextcloud, docker (`DOCKER_HOST=tcp://127.0.0.1:2375`). context7 only in Antigravity/OpenCode (Claude uses the claude.ai connector). sqlite and puppeteer removed.
- Antigravity/OpenCode: serena, nextcloud, docker disabled by default (those harnesses load all schemas up front; Nextcloud alone has 181 tools).
- Claude Code: yadm-tracked plugin marketplace `~/.config/ai/claude-plugins` (`workstation-mcp@workstation`), `${VAR}` secrets expanded at runtime; `permissions.ask` rules for Nextcloud send/share/delete/trash and GitHub merge/delete.
- `instructions.yml` only bootstraps `~/.config/ai/AGENTS.md` when missing (previous behaviour overwrote the yadm-owned file).
- yadm auto-alt re-renders templates on ordinary yadm commands with the caller's environment; `~/.config/ai/env` must therefore export every templated secret (now includes `NEXTCLOUD_*`).

## Immediate Next Steps
- Supply Nextcloud app password and re-run: `NEXTCLOUD_HOST=… NEXTCLOUD_USERNAME=… NEXTCLOUD_PASSWORD=… ansible-playbook main.yml -e enable_ai_workstation=true`.
- NowCoding provider and `NOWCODING_API_KEY` removed entirely (2026-10-18).
- On Docker hosts: run `docker` + `ai_workstation` roles to get the read-only proxy.
- Open decision: `laptops` and `master` have diverged (54 vs 15 commits). The new auto-merge rule deliberately does not merge `laptops` into `master`; do that only on explicit approval.
- `roles/ai_workstation/templates/AGENTS.md.j2` mirrors the new auto-merge rule from the yadm-owned `~/.config/ai/AGENTS.md`.

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



