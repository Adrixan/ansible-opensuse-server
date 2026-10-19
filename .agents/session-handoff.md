# Session Handoff State

## Active Intent
US-14.1: MCP stack overhaul after reviewing `~/Free Claude MCP Servers.md`. yadm owns every harness config; the `ai_workstation` role only installs runtimes, keeps secrets in `~/.config/ai/env` and renders the yadm templates.

## Task & Story Status
- Current Story: US-14.1, complete and verified live on localhost (2026-10-18), idempotent (`ok=55, changed=0, failed=0`).

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

