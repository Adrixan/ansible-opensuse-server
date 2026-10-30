# ansible-opensuse-server

Ansible playbook that provisions openSUSE Tumbleweed workstations and laptops against `localhost` (`ansible_connection=local`). This repository is PUBLIC: no secrets, credentials, private hostnames or personal data in tracked files, commit messages or `.agents/` notes (reference secrets by variable name only).

## Layout
- `main.yml`: one `ansible.builtin.include_role` per role, gated by `when: enable_<role> | default(false) | bool` and tagged with the role name.
- `group_vars/all.yml`: `enable_<role>` defaults; every new role gets a flag here and an include in `main.yml`.
- `roles/<role>/`: compact single-responsibility roles (`tasks/`, `defaults/`, `templates/`, `files/`, `handlers/`); `github_release` is a helper role for upstream downloads.
- `hosts`: local inventory, gitignored; copy `hosts.example`. Never put passwords in it.
- `.agents/`: state files (`session-handoff.md`, `project-state.md`, `plan.md`, `to-do.md`, `memory.md`). Read them first; update the handoff after non-trivial work.

## Running
- One role: `ansible-playbook main.yml -e enable_<role>=true`.
- Single task file: an `import_role` playbook with `tasks_from` in `.scratch/` (gitignored globally).
- Verify every change: `ansible-playbook main.yml --syntax-check`, then `--check` where the role supports it, a live run, and a second live run that must report `changed=0`.

## Scope and ownership
- This repo installs software and services and renders yadm templates with secrets. Agent instructions, skills and harness configs (Claude plugins, OpenCode and Antigravity configs) belong to yadm (dotfiles), never to this repo.
- Secrets come from the environment or `~/.config/ai/env` (rendered by `ai_workstation`, mode `0600`); `~/.config/ai/env.local` holds yadm-only secrets and is never written by a role.
- `ai_workstation` must not restart Claude Code remote-control role servers that are running (it would kill the session running the playbook); it reports roles that need `rc restart <role>`.
- `mcp-shared.service` (`127.0.0.1:8790`) runs the stateless MCP servers; the role restarts it after launcher, config, unit or tool updates.

## Conventions
- Latest stable release everywhere, no version pins: zypper `state: present` plus `zypper dup` in `system_update`, npm prefixes and uv tools updated on every run, GitHub downloads via `github_release` (sha256 from release metadata). A cap only where a newer major is known to break, with a comment.
- 24-hour supply-chain cooldown: `ai_workstation` sets `min-release-age=1` in the system npmrc, `github_release` skips releases younger than `github_release_cooldown_hours` (24); the user-level npm, uv and pnpm settings live in yadm.
- `npm audit` gates each Node prefix; findings without a fixed release need Peter's acceptance recorded in the repo.
- PEP 668: system pip tasks use `--break-system-packages`; prefer `uv tool` for Python CLIs.
- FQCN modules (`ansible.builtin.*`, `community.general.*`), idempotent tasks, `changed_when`/`failed_when` on commands, `no_log: true` on anything touching secrets.
- Git: work on a feature branch off `master`, Conventional Commits, `git merge --no-ff` into `master`, push. No force-push.
