# Sprint Backlog & To-Do

## Sprint Goal
Enable default remote control across all supporting AI harnesses (Claude Code CLI, Google Antigravity CLI, and OpenCode AI CLI) via `ai_workstation` role, verify syntax, and deploy live on localhost.

## Active Sprint Story (Sprint 12)
None (Sprint 12 Complete)

## Completed Sprint Stories (Sprint 12)
- **US-12.1**: Enable Default Remote Control across Claude Code, Antigravity, and OpenCode (3 SP) - **Done**
  - [x] Configure `"remoteControlAtStartup": true` in `~/.claude/settings.json` via Ansible task
  - [x] Configure `antigravity-cli-daemon.service` under user systemd and add `alias agy="agy --remote-control"` to `~/.config/ai/env`
  - [x] Configure `"server"` object in `~/.config/opencode/opencode.json` (port 4096, localhost bound)
  - [x] Provision and enable `opencode-server.service` under user systemd
  - [x] Verify playbook syntax (`--syntax-check`)
  - [x] Deploy live on localhost (`ansible-playbook -i hosts main.yml -e "enable_ai_workstation=true"`)
  - [x] Verify service states, daemon status, and idempotency (`changed=0`)
  - [x] Update state files and session handoff

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
- Live localhost execution (`ai_workstation` Sprint 12 deployment): **PASS (ok=46, changed=10, failed=0)**
- Live localhost execution (`ai_workstation` Sprint 12 idempotency run): **PASS (ok=44, changed=0, failed=0)**
- Harness Remote Control Verifications:
  - Claude Code CLI: **`"remoteControlAtStartup": true` set in `~/.claude/settings.json`**
  - Antigravity CLI: **`antigravity-cli-daemon.service` active under user systemd, connected to cloud relay, interactive alias `alias agy="agy --remote-control"` in `~/.config/ai/env`**
  - OpenCode AI CLI: **`opencode-server.service` active under user systemd, listening on `127.0.0.1:4096`, `"server"` config configured in `~/.config/opencode/opencode.json`, helper aliases `opencode-remote` and `opencode-web` in `~/.config/ai/env`**
- Live localhost execution (`ai_desktop` initial run): **PASS (ok=34, changed=21, failed=0)**
- Live localhost execution (`ai_desktop` idempotency run): **PASS (ok=15, changed=0, failed=0)**

- Application Verifications:
  - Claude Desktop (`claude-desktop`): **Installed in `/opt/claude-desktop/`, verified (`/usr/local/bin/claude-desktop` v2.7032.0)**
  - Claude Desktop Launcher: **`/usr/share/applications/com.anthropic.Claude.desktop` deployed with hicolor icons**
  - Google Antigravity GUI (`antigravity`): **Installed in `/opt/antigravity/`, verified (`/usr/local/bin/antigravity` v2.17.0-5217732355031040)**
  - Google Antigravity Launcher: **`/usr/share/applications/antigravity.desktop` deployed with pixmap and 512x512 hicolor icon**
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



