# Session Handoff State

## Active Intent
Transition AI workstation tools (Claude Code and OpenCode) from legacy Alibaba Cloud Model Studio (Bailian) custom gateway to official Anthropic access, separating flat-rate Claude subscription (for Claude Code) from API key access (for OpenCode).

## Task & Story Status
- Current Story: US-10.6 (Transition Claude Code and OpenCode from Bailian gateway to official Anthropic access and clean up configurations)
- State: Complete & Verified

## Key Decisions & Architecture
- Claude Code CLI uses native first-party OAuth authentication for the user's flat-rate Claude subscription. `ANTHROPIC_API_KEY` is not exported in shell environments to avoid overriding the OAuth session with per-token billing.
- OpenCode uses the official Anthropic API with credentials in `~/.local/share/opencode/auth.json`.
- All legacy Alibaba Bailian gateway URLs, Qwen model aliases, and `modelOverrides` have been purged from `roles/ai_workstation/`, `~/.config/ai/env`, `~/.claude/settings.json`, and `~/.claude.json`.
- Workspace scoping for OpenCode is active: `ANTHROPIC_WORKSPACE_ID="wrkspc_017CGfYfmKQbqyxBeQp14Czy"` is stored in `~/.config/ai/env` and automatically mapped into `~/.config/opencode/opencode.json` via Ansible.
- Live test confirmed: Anthropic API accepted the workspace ID header and returned the credit balance requirement.

## Immediate Next Steps
- For Claude Code CLI: Run `claude auth login` in a local terminal window to authorize your Claude subscription via browser OAuth.
- For OpenCode: Add prepaid API usage credits in the Anthropic Console under Plans & Billing if you wish to run Anthropic models via OpenCode.
