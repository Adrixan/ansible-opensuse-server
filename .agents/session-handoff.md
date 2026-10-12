# Session Handoff State

## Active Intent
Switch to `laptops` branch and apply the unified AI roles (`ai_workstation` and `ai_desktop`) on this host.

## Task & Story Status
- Current Task: Apply `ai_workstation` and `ai_desktop` roles on localhost (`laptops` branch)
- State: Complete, verified live on localhost (2026-10-12), playbook execution 100% idempotent (`ok=64, changed=0, failed=0`).

## Key Decisions & Architecture
- User Group Provisioning: Created group `Adrixan` (gid 1000) on openSUSE Tumbleweed host; openSUSE defaults users to `users` (gid 100), but tasks across roles standardly target `group: "{{ target_user }}"`.
- Claude MCP Updater Hardening: Made GitHub token optional with default empty string in `roles/ai_workstation/files/update_claude_mcp.py` and changed `roles/ai_workstation/tasks/mcp.yml` to pass arguments via `argv` list.
- OpenCode Config Schema: Aligned `roles/ai_workstation/templates/opencode.json.j2` with OpenCode 1.2+ provider schema by replacing `"package"` with `"npm"`, allowing `opencode-server.service` to start successfully.
- Live Verifications:
  - `claude-desktop-update.timer`: active (system)
  - `claude-code-update.timer`: active (user)
  - `opencode-server.service`: active (user, listening on 127.0.0.1:4096)
  - `antigravity-cli-daemon.service`: active (user)
  - `~/.config/ai/AGENTS.md`: deployed with "Auto Commit & Push" rule and symlinked to `~/.claude/CLAUDE.md`, `~/.gemini/GEMINI.md`, and `~/.config/opencode/AGENTS.md`
  - Claude Desktop v2.31226.1 & Claude Code v2.1.296 confirmed functional

## Immediate Next Steps
- Restart Claude Desktop to load 2.31226.1, then run `sudo systemctl start claude-desktop-update.service` and `systemctl --user start claude-code-update.service` (or wait for the timers) to drop the old Desktop and bundled CLI versions.
- New global rule "Auto Commit & Push" added to `roles/ai_workstation/templates/AGENTS.md.j2` and copied to `~/.config/ai/AGENTS.md` (symlinked as `~/.claude/CLAUDE.md`, `~/.gemini/GEMINI.md`, OpenCode `AGENTS.md`).
- Single-version policy (2026-10-12): `claude_desktop_keep_versions: 1`; new helper `/usr/local/bin/claude-prune-versions` (from `files/claude-prune-versions.py`) prunes `~/.local/share/claude/versions` (keeps newest and the `~/.local/bin/claude` target) and `~/.config/Claude/claude-code` (Desktop-bundled CLI), and runs as `ExecStartPost` of `claude-code-update.service`. Versions a running process was started from are never removed (verified under the root service sandbox).
- Pruned now: native CLI 2.1.291 and 2.1.292, empty `/usr/local/lib/node_modules/@anthropic-ai`. Still present because in use by the running Desktop session: `/opt/claude-desktop-2.7032.0` and `~/.config/Claude/claude-code/2.1.280`; both are removed on the next role run or timer after Claude Desktop is restarted.
- `/usr/local/bin/claude-zai` (outside the repo) exec'd the removed npm `/usr/local/bin/claude`; repointed to `~/.local/bin/claude`. It contains a plaintext API token and is world-readable (mode 755); consider mode 700 or loading the token from an env file.
- Open question: `hosts` holds a plaintext `ansible_ssh_pass`; consider moving it to Ansible Vault or removing it (unused with `ansible_connection=local`).

