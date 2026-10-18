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
- yadm auto-alt re-renders templates on ordinary yadm commands with the caller's environment; `~/.config/ai/env` must therefore export every templated secret (now includes `NOWCODING_API_KEY`, `NEXTCLOUD_*`).

## Immediate Next Steps
- Supply Nextcloud app password and re-run: `NEXTCLOUD_HOST=… NEXTCLOUD_USERNAME=… NEXTCLOUD_PASSWORD=… ansible-playbook main.yml -e enable_ai_workstation=true`.
- NowCoding API key in `~/.config/opencode/opencode.json` was blanked by a `yadm alt` run without the variable; re-supply via `NOWCODING_API_KEY=… ansible-playbook …` if the key is still in use.
- On Docker hosts: run `docker` + `ai_workstation` roles to get the read-only proxy.
- Open decision: `laptops` and `master` have diverged (54 vs 15 commits). The new auto-merge rule deliberately does not merge `laptops` into `master`; do that only on explicit approval.
- `roles/ai_workstation/templates/AGENTS.md.j2` mirrors the new auto-merge rule from the yadm-owned `~/.config/ai/AGENTS.md`.
