# Session Handoff State

## Active Intent
Transition AI workstation tools (Claude Code and OpenCode) from legacy Alibaba Cloud Model Studio (Bailian) custom gateway to official Anthropic access, separating flat-rate Claude subscription (for Claude Code) from API key access (for OpenCode).

## Task & Story Status
- Current Story: US-10.6 (Transition Claude Code and OpenCode from Bailian gateway to official Anthropic access and clean up configurations)
- State: Implementation Complete; Awaiting Workspace Scope Input for OpenCode

## Key Decisions & Architecture
- Claude Code CLI uses native first-party OAuth authentication for the user's flat-rate Claude subscription. `ANTHROPIC_API_KEY` is not exported in shell environments to avoid overriding the OAuth session with per-token billing.
- OpenCode uses the official Anthropic API with credentials in `~/.local/share/opencode/auth.json`.
- All legacy Alibaba Bailian gateway URLs, Qwen model aliases, and `modelOverrides` have been purged from `roles/ai_workstation/`, `~/.config/ai/env`, `~/.claude/settings.json`, and `~/.claude.json`.
- OpenCode template supports passing `anthropic-workspace-id` header when `ai_workstation_anthropic_workspace_id` is defined.

## Immediate Next Steps
- Awaiting user input on Anthropic Workspace scoping:
  - Option A: Generate a workspace-scoped API key in Anthropic Console (Workspaces -> select Workspace -> API Keys -> Create Key) and supply it.
  - Option B: Provide the Anthropic Workspace ID (`wrkspc_...`) to pass via `anthropic-workspace-id` header with the existing key.
- For Claude Code CLI: user runs `claude auth login` in their terminal to authorize their Claude subscription via browser OAuth.
- Push clean git commits to `origin/laptops`.
