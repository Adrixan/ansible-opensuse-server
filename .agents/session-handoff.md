# Session Handoff State

## Active Intent
Remove Google Antigravity Desktop from the `ai_desktop` role and keep Claude Desktop and Claude Code updated automatically on openSUSE Tumbleweed.

## Task & Story Status
- Current Story: `ai_desktop` Antigravity removal + Claude auto-update
- State: Complete, verified live on localhost (2026-10-12), committed and pushed to `origin/laptops`

## Key Decisions & Architecture
- Antigravity Desktop: install tasks, launcher and icon assets removed from the role; `tasks/antigravity_cleanup.yml` deletes leftover files (`/opt/antigravity`, launcher, icons, `/usr/local/bin/antigravity`). The Antigravity CLI (`agy`) setup in `ai_workstation` was intentionally left untouched.
- Claude Desktop: `/usr/local/sbin/claude-desktop-update` (from `roles/ai_desktop/files/claude-desktop-update.py`) tracks Anthropic's apt repo. Trust chain: InRelease verified with gpgv against the role-shipped key `files/claude-desktop-signing-key.asc` with pinned fingerprint `31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE`, Valid-Until enforced, Packages and .deb verified by SHA256.
- Install layout: versioned dirs `/opt/claude-desktop-<version>`, `/opt/claude-desktop` is a symlink swapped atomically; keeps 2 versions and never prunes a version a running process uses. `claude_desktop_version: latest` (set an exact version to pin or roll back).
- Root timer `claude-desktop-update.timer` (daily, sandboxed service with ProtectSystem=strict).
- Claude Code: native installer (`~/.local/bin/claude`) plus user timer `claude-code-update.timer` running `claude update` daily. The stale root-owned npm global (2.1.278) and the `/usr/bin/claude` symlink were removed.
- Live run: Claude Desktop 2.7032.0 -> 2.31226.1 (`ok=23, changed=11, failed=0`); idempotency rerun `changed=0`. Both timers active; both services tested manually.

## Immediate Next Steps
- Restart Claude Desktop to load 2.31226.1 (the running instance still uses `/opt/claude-desktop-2.7032.0`, which will be pruned after a later update).
- New global rule "Auto Commit & Push" added to `roles/ai_workstation/templates/AGENTS.md.j2` and copied to `~/.config/ai/AGENTS.md` (symlinked as `~/.claude/CLAUDE.md`, `~/.gemini/GEMINI.md`, OpenCode `AGENTS.md`).
- Open question: `hosts` holds a plaintext `ansible_ssh_pass`; consider moving it to Ansible Vault or removing it (unused with `ansible_connection=local`).
