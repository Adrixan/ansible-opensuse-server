# Sprint Backlog & To-Do

## Sprint Goal
Replace archived MCP servers, add MarkItDown/Serena/Nextcloud/Context7/Docker (read-only), and make yadm the single owner of harness configs while `ai_workstation` provisions runtimes and secrets.

## Active Sprint Story (Sprint 14)
None (Sprint 14 Complete)

## Completed Sprint Stories (Sprint 14)
- **US-14.1**: Overhaul MCP stack per free-MCP report review: yadm owns harness configs, `ai_workstation` installs runtimes only (8 SP) - **Done**
  - [x] Replace archived `server-github` (remote `api.githubcopilot.com/mcp/`) and `server-puppeteer` (`@playwright/mcp` + zypper `chromium`); drop unused `sqlite`
  - [x] Persist memory graph in `~/sync/ai/mcp-memory.jsonl` (Syncthing)
  - [x] Install uv tools (`serena-agent`, `markitdown-mcp`, `nextcloud-mcp-server`, `mcp-server-docker`, `arxiv-mcp-server`, `zotero-mcp-server`, `mcp-server-fetch`, `mcp-server-git`) with daily `ai-mcp-tools-update.timer`
  - [x] Remove Ansible-written harness configs (`gemini_mcp.json.j2`, `opencode.json.j2`, `update_claude_mcp.py`); purge legacy user-scope servers and plaintext PAT from `~/.claude.json`
  - [x] Render yadm templates from `~/.config/ai/env` (export `NOWCODING_API_KEY`, `NEXTCLOUD_*`), 0600 outputs, drift-detecting checksum
  - [x] Register yadm-tracked `workstation-mcp@workstation` Claude Code plugin
  - [x] Read-only `docker-socket-proxy` (POST=0) on `127.0.0.1:2375` where Docker is installed
  - [x] `instructions.yml` no longer overwrites yadm-owned `~/.config/ai/AGENTS.md`; relative symlinks match yadm
  - [x] Deploy live on localhost and verify idempotency (`ok=55, changed=0, failed=0`); `claude mcp list` all plugin servers connected except `docker` (no Docker on this host)

## Completed Sprint Stories (Sprint 13)
- **US-13.1**: Add Antigravity Desktop and Antigravity CLI (`agy`) with daily systemd auto-update timers and single-version pruning to `ai_desktop` role (5 SP) - **Done**
  - [x] Create `roles/ai_desktop/files/antigravity-desktop-update.py` verifying GCS object size and CRC32C (`libcrc32c1`), managing `/opt/antigravity-<version>` with atomic symlink switch and single-version pruning
  - [x] Restore `antigravity.desktop` launcher and 512x512 `antigravity.png` icon in `roles/ai_desktop/files/`
  - [x] Create `roles/ai_desktop/tasks/antigravity_desktop.yml` and `antigravity-desktop-update.{service,timer}.j2`
  - [x] Create `roles/ai_desktop/tasks/antigravity_cli.yml` and `antigravity-cli-update.{service,timer}.j2`
  - [x] Verify playbook syntax (`--syntax-check`) and dry-run (`--check`)
  - [x] Deploy live on localhost (`ok=40, changed=10, failed=0`) and verify idempotency (`ok=40, changed=0, failed=0`)
  - [x] Update state files, `README.md`, and session handoff

## Completed Sprint Stories (Sprint 12)
- **US-12.1**: Enable Default Remote Control across Claude Code, Antigravity, and OpenCode (3 SP) - **Done**

## Completed Sprint Stories (Sprint 11)
- **US-11.1**: Create `ai_desktop` role for Claude Desktop and Antigravity GUI application deployment (5 SP) - **Done**


## Completed Sprint Stories (Sprint 10)
- **US-10.1**: Create `opencode` role (`roles/opencode`), configure feature flag in `group_vars/all.yml` & `main.yml`, and execute live on localhost (2 SP) - **Done**
- **US-10.2**: Ensure `topgrade` upgrade utility is installed via zypper in `system_update` and `shell_environment`, verified live on localhost (2 SP) - **Done**
- **US-10.3**: Create `ai_workstation` role for unified MCP parity, lean core instructions, skills consolidation, and shell env (5 SP) - **Done**
- **US-10.4**: Integrate personal branding and visual styleguide into `ai_workstation` default configuration (2 SP) - **Done**
- **US-10.5**: Implement workspace locality mandate, session handoff protocol, and global gitignore in `ai_workstation` role (3 SP) - **Done**
- **US-10.6**: Transition Claude Code and OpenCode from Bailian gateway to official Anthropic access and clean up configurations (3 SP) - **Done**

## Verification Summary
- Playbook `--syntax-check`: **PASS (100%)**
- Playbook `--check` (`ai_desktop` dry-run): **PASS (ok=36, changed=6, failed=0)**
- Live localhost execution (`ai_desktop` Sprint 13 deployment): **PASS (ok=40, changed=10, failed=0)**
- Live localhost execution (`ai_desktop` Sprint 13 idempotency run): **PASS (ok=40, changed=0, failed=0)**
- Application & Timer Verifications:
  - Google Antigravity Desktop (`antigravity`): **Installed in `/opt/antigravity` -> `antigravity-2.24.0`, symlinked at `/usr/local/bin/antigravity`, launcher and icons deployed**
  - Antigravity Desktop Auto-Update Timer: **`antigravity-desktop-update.timer` active (system), sandboxed service verified**
  - Google Antigravity CLI (`agy`): **Installed at `~/.local/bin/agy` (v1.4.0)**
  - Antigravity CLI Auto-Update Timer: **`antigravity-cli-update.timer` active (user), service verified**
  - Claude Desktop (`claude-desktop`): **Installed in `/opt/claude-desktop` -> `claude-desktop-2.42304.0`, `claude-desktop-update.timer` active (system)**
  - Claude Code CLI (`claude`): **Installed at `~/.local/bin/claude`, `claude-code-update.timer` active (user)**

- Live localhost execution (`opencode`): **PASS (ok=4, changed=1, failed=0)**
  - OpenCode CLI (`opencode-ai` via npm): **Installed & Verified (`/usr/local/bin/opencode` v1.18.12)**
- Live localhost execution (`shell_environment` & `system_update` check): **PASS (ok=4, changed=0, failed=0)**
  - Package `topgrade`: **Installed & Verified via Zypper (`/usr/bin/topgrade` v17.8.0)**
- Live localhost execution (`ai_workstation`): **PASS (ok=32, changed=5, failed=0)**
  - Unified core instructions: **`~/.config/ai/AGENTS.md` deployed with workspace locality & session handoff rules**
  - Global gitignore: **`~/.config/git/ignore` configured with `.scratch/` entry**
  - Session handoff reference: **`.agents/session-handoff.md` created in repository**
  - Canonical styleguide link: **`~/.config/ai/BRANDING.md` created pointing to `~/Obsidian/Adrixan/Freelancing/Branding.md`**
  - MCP servers parity: **8 servers (`github`, `puppeteer`, `sqlite`, `memory`, `fetch`, `git`, `arxiv`, `zotero`) across Gemini, OpenCode, Claude Code**
  - Skills consolidation: **`~/.local/share/skills` centralized and symlinked to `~/.claude/skills`, `~/.gemini/antigravity-cli/skills`, `~/.config/opencode/skills`**
  - Environment centralization: **`~/.config/ai/env` purged of legacy gateway tokens and Qwen variables**
  - Claude settings cleanup: **Legacy Bailian `env`, `modelOverrides`, and custom models purged from `~/.claude/settings.json` and `~/.claude.json`**
  - OpenCode configuration: **Bailian provider removed; Anthropic model set to `anthropic/claude-sonnet-4-5`; optional `anthropic-workspace-id` header support integrated**
- Remote Push: **Pending push to `origin/laptops`**



