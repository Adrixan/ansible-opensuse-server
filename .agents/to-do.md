# Sprint Backlog & To-Do

## Sprint Goal
Replace archived MCP servers, add MarkItDown/Serena/Nextcloud/Context7/Docker (read-only), and make yadm the single owner of harness configs while `ai_workstation` provisions runtimes and secrets.

## Active Sprint Story (Sprint 14)
None (Sprint 14 Complete)

## Completed Sprint Stories (Sprint 14)
- **US-14.4**: Native V2 OpenCode config and update activation (2 SP) - **Done**
  - [x] yadm `opencode.json##template` in native V2 shape (`providers`, `agents`, `mcp.servers`, `disabled`, `update: auto`); DragTokens via `@opencode/ai/providers/openai/responses` with `canonical: openai`
  - [x] `/usr/local/bin/opencode-restart-stale-server`: `systemctl --user try-restart opencode-server.service` when `~/.local/state/opencode/service.json` reports an older version than the binary; runs after the daily upgrade and in the role
  - [x] No config diagnostics; `opencode mcp list` 9 connected, 3 disabled; plan `dragtokens/gpt-6-astra`, build `dragtokens/gpt-6.1-sol`; rerun `ok=101, changed=0`
  - [ ] DragTokens API unreachable on the school network: FortiGuard DNS sinkhole plus TLS reset on SNI `dragtokens.com`
- **US-14.3**: Track the newest OpenCode release (V2) (3 SP) - **Done**
  - [x] `ai_desktop` uses the V2 installer (`https://opencode.ai/v2/install`); reinstalls when the binary is missing or older than `opencode_cli_major_version` (V1 installer refuses 2.x)
  - [x] `opencode-server.service` is a oneshot `opencode service start`/`stop` (running `serve --service` under systemd raced `opencode service restart`); listen address persisted via `opencode service set hostname/port`
  - [x] Aliases: `opencode-remote` = `opencode --server http://127.0.0.1:4096`, `opencode-web` = `opencode pair` (V2 removed `attach` and `web`)
  - [x] `main.yml` runs `ai_desktop` before `ai_workstation` (binaries before config)
  - [x] Live 2.0.32 on localhost; idempotent rerun `ok=99, changed=0, failed=0`; one server process on `127.0.0.1:4096`; V1 credentials (`auth list`) and DragTokens models carried over
- **US-14.2**: OpenCode on DragTokens: native CLI in `ai_desktop`, `DRAGTOKENS_API_KEY` secret in `ai_workstation` (3 SP) - **Done**
  - [x] `ai_desktop/tasks/opencode_cli.yml`: official installer (`--no-modify-path`, `~/.opencode/bin/opencode`), npm global `opencode-ai` removed, daily `opencode-cli-update.timer` (`opencode upgrade --method curl`)
  - [x] Standalone `roles/opencode` and `enable_opencode` removed
  - [x] `DRAGTOKENS_API_KEY` read from env or `~/.config/ai/env`, exported there and passed to `yadm alt`; `opencode-server.service` uses the native binary and restarts on unit or rendered-config changes
  - [x] yadm `opencode.json##template`: provider `dragtokens` (`@ai-sdk/openai`, `https://dragtokens.com/v1`), agents plan `gpt-6-astra`, build `gpt-6.1-sol`
  - [x] Live run `ok=100, changed=9`; idempotent rerun `ok=98, changed=0, failed=0`; `opencode models dragtokens` lists all three models
  - [ ] Live API call untested: FortiGuard DNS on the current network (10.106.81.0/24) blocks dragtokens.com by category
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



