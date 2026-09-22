# Sprint Backlog & To-Do

## Sprint Goal
Create `opencode` role to install OpenCode AI CLI tool via global npm (`opencode-ai`), integrate with playbook, execute live on localhost, verify installation, and commit/push changes.

## Completed Sprint Stories (Sprint 10)
- **US-10.1**: Create `opencode` role (`roles/opencode`), configure feature flag in `group_vars/all.yml` & `main.yml`, and execute live on localhost (2 SP) - **Done**
- **US-10.2**: Ensure `topgrade` upgrade utility is installed via zypper in `system_update` and `shell_environment`, verified live on localhost (2 SP) - **Done**
- **US-10.3**: Create `ai_workstation` role for unified MCP parity, lean core instructions, skills consolidation, and shell env (5 SP) - **Done**
- **US-10.4**: Integrate personal branding and visual styleguide into `ai_workstation` default configuration (2 SP) - **Done**

## Verification Summary
- Playbook `--syntax-check`: **PASS (100%)**
- Live localhost execution (`opencode`): **PASS (ok=4, changed=1, failed=0)**
  - OpenCode CLI (`opencode-ai` via npm): **Installed & Verified (`/usr/local/bin/opencode` v1.18.12)**
- Live localhost execution (`shell_environment` & `system_update` check): **PASS (ok=4, changed=0, failed=0)**
  - Package `topgrade`: **Installed & Verified via Zypper (`/usr/bin/topgrade` v17.8.0)**
- Live localhost execution (`ai_workstation`): **PASS (ok=26, changed=5, failed=0)**
  - Unified core instructions: **`~/.config/ai/AGENTS.md` deployed with personal branding section and symlinked to Claude, Gemini, OpenCode**
  - Canonical styleguide link: **`~/.config/ai/BRANDING.md` created pointing to `~/Obsidian/Adrixan/Freelancing/Branding.md`**
  - MCP servers parity: **8 servers (`github`, `puppeteer`, `sqlite`, `memory`, `fetch`, `git`, `arxiv`, `zotero`) across Gemini, OpenCode, Claude Code**
  - Skills consolidation: **`~/.local/share/skills` centralized and symlinked to `~/.claude/skills`, `~/.gemini/antigravity-cli/skills`, `~/.config/opencode/skills`**
  - Environment centralization: **`~/.config/ai/env` created (0600) and sourced in `~/.zshrc` and `~/.bashrc`**
  - Cleanup: **Legacy code skills directory and inline exports removed**
- Remote Push: **Pending push to `origin/laptops`**



