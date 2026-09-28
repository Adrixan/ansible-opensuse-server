# Sprint Backlog & To-Do

## Sprint Goal
Create `ai_desktop` role to provision official GUI editions of Claude Desktop (`2.7032.0`) and Google Antigravity (`2.17.0`) on openSUSE Tumbleweed, integrate with `group_vars/all.yml` and `main.yml`, verify syntax, and deploy live on localhost.

## Active Sprint Story (Sprint 11)
- **US-11.1**: Create `ai_desktop` role for Claude Desktop and Antigravity GUI application deployment (5 SP) - **Done**
  - [x] Role directory structure and defaults created (`roles/ai_desktop/defaults/main.yml`)
  - [x] Desktop and icon assets created in `roles/ai_desktop/files/`
  - [x] Tasks implemented (`tasks/main.yml`, `tasks/claude_desktop.yml`, `tasks/antigravity.yml`)
  - [x] Variable and playbook integration (`group_vars/all.yml`, `main.yml`)
  - [x] Playbook syntax verification (`--syntax-check`)
  - [x] Live localhost deployment verification (`ansible-playbook -i hosts main.yml -e "enable_ai_desktop=true"`)
  - [x] Idempotency test verified (`ok=15, changed=0, failed=0`)
  - [x] Binary execution and desktop file validation
  - [x] State files and session handoff updated

## Completed Sprint Stories (Sprint 10)
- **US-10.1**: Create `opencode` role (`roles/opencode`), configure feature flag in `group_vars/all.yml` & `main.yml`, and execute live on localhost (2 SP) - **Done**
- **US-10.2**: Ensure `topgrade` upgrade utility is installed via zypper in `system_update` and `shell_environment`, verified live on localhost (2 SP) - **Done**
- **US-10.3**: Create `ai_workstation` role for unified MCP parity, lean core instructions, skills consolidation, and shell env (5 SP) - **Done**
- **US-10.4**: Integrate personal branding and visual styleguide into `ai_workstation` default configuration (2 SP) - **Done**
- **US-10.5**: Implement workspace locality mandate, session handoff protocol, and global gitignore in `ai_workstation` role (3 SP) - **Done**
- **US-10.6**: Transition Claude Code and OpenCode from Bailian gateway to official Anthropic access and clean up configurations (3 SP) - **Done**

## Verification Summary
- Playbook `--syntax-check`: **PASS (100%)**
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



