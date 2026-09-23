# Session Handoff State

## Active Intent
Standardize workspace locality for scratch scripts (`.scratch/`) and establish cross-device session continuity across AI harnesses (Antigravity, Claude Code, OpenCode).

## Task & Story Status
- Current Story: US-10.5 (Workspace locality mandate, session handoff protocol, and global gitignore in `ai_workstation` role)
- State: Complete

## Key Decisions & Architecture
- Scratch scripts, temporary tests, and debug data are directed to `.scratch/` in the active working directory.
- `~/.config/git/ignore` globally excludes `.scratch/` from git tracking.
- Universal core instructions (`~/.config/ai/AGENTS.md`) enforce workspace locality and `.agents/session-handoff.md` generation before session exit.
- Cross-device resumption is achieved via workspace state synchronization rather than incompatible binary/JSON chat transcript conversion.

## Immediate Next Steps
- Maintain `.agents/session-handoff.md` as context handoff artifact between sessions and devices.
- Commit and push changes to `origin/laptops`.
