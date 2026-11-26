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
- One narrow exception: skills that ship inside an npm package this repo installs (Modern Web Guidance, Chrome DevTools MCP) are copied from `/opt/mcp` into the yadm plugin `workstation-web/skills/` (ignored by yadm) after each update, so skill and tool keep one version; the plugin manifest and MCP template stay in yadm.
- Secrets come from the environment or `~/.config/ai/env` (rendered by `ai_workstation`, mode `0600`); `~/.config/ai/env.local` holds yadm-only secrets and is never written by a role.
- `ai_workstation` must not restart Claude Code remote-control role servers that are running (it would kill the session running the playbook); it reports roles that need `rc restart <role>`.
- `mcp-shared.service` (`127.0.0.1:8790`) runs the stateless MCP servers; the role restarts it after launcher, config, unit or tool updates.
- `tasks/ws_sync.yml` only schedules `ws-sync sync --auto` (user timer, on where the lease is on). The script `ws-sync`, its greeting and tests belong to yadm, its config and state to `~/sync/ai/ws-sync/` (private); intended per-machine differences go into that config, never into this repo.

## Conventions
- Latest stable release everywhere, no version pins: zypper `state: present` plus `zypper dup` in `system_update`, npm prefixes and uv tools updated on every run, GitHub downloads via `github_release` (sha256 from release metadata). A cap only where a newer major is known to break, with a comment.
- 24-hour supply-chain cooldown: `ai_workstation` sets `min-release-age=1` in the system npmrc, `github_release` skips releases younger than `github_release_cooldown_hours` (24); the user-level npm, uv and pnpm settings live in yadm.
- Claude Code (Peter, 2026-11-20: "latest + 24 h everywhere"): `ai_desktop` installs only through `claude-code-update` (`files/claude-code-update.sh`: `claude install <v>` with the version from `files/release-past-cooldown`, an unchanged copy of the VPS nightly helper; never downgrades). Never `claude update`. The built-in autoupdater stays off via `env.DISABLE_AUTOUPDATER` in the yadm-tracked `~/.claude/settings.json`. Once a workstation runs nightly-routine in active mode with `CLAUDE_USERS`, its unit becomes prune-only.
- `~/.claude/settings.json` belongs to yadm: role tasks may only remove the named legacy keys (`ai_workstation_claude_legacy_env_keys`) and write it back with `ensure_ascii=False`; never delete the `env` block (that wiped Code Mode nightly until 2026-11-20).
- `npm audit` gates each Node prefix; findings without a fixed release need Peter's acceptance recorded in the repo.
- Exception to the no-pin rule: `garmin-mcp` stays on a reviewed commit and is bumped only on purpose (it holds the Garmin login and upload rights; Peter, 2026-11-15, D52).
- PEP 668: system pip tasks use `--break-system-packages`; prefer `uv tool` for Python CLIs.
- Dropped apps (Peter's keep/delete lists): remove them from every role list and add leaf apps to `workstation_packages_absent` (removed through a guarded dry run, then zypper-locked); libraries are removed once and never locked. Never `zypper rm -u` on the workstations: it cascades through pattern recommends (2026-11-18 dry run: 434 packages on m11x). Apps dropped on one host only go into that host's `workstation_packages_absent_host` (hosts file), never the shared list.
- zypper's `--unneeded` list only means nothing requires or recommends a package. Drain it in guarded passes (`pkg-policy.py remove`, refused on any extra) and hold back for review every package that ships units, udev rules, PAM/NSS modules, boot (GRUB), network or sysconfig files: on m11x a pass took `sysconfig-netconfig` (it writes `/etc/resolv.conf` there) and DNS was gone until it was restored from an rpm fetched on schulpc (2026-11-18). Run `zypper clean -a` only after the last package step, or offline installs find no metadata.
- FQCN modules (`ansible.builtin.*`, `community.general.*`), idempotent tasks, `changed_when`/`failed_when` on commands, `no_log: true` on anything touching secrets.
- Update hooks: `topgrade_nightly` runs the executables in `/etc/topgrade/pre.d` before topgrade (a failure skips the update) and in `post.d` after it; roles drop their own hooks there (`virtualbox`: kernel hold, Extension Pack sync) instead of editing the wrapper.
- VirtualBox host modules only from the openSUSE KMP (Peter, 2026-11-26: the distribution's way over `vboxconfig`); a new kernel waits for its KMP through `vbox-kernel-guard`, never a local module build. Accepting a changed Extension Pack license (`virtualbox_extpack_license_sha256`) is Peter's decision.
- Git: work on a feature branch off `master`, Conventional Commits, `git merge --no-ff` into `master`, push. No force-push.

## Takeover lease (D33 B, decided 2026-11-14)
- `ai_workstation` `tasks/lease.yml` (flag `ai_workstation_lease`, host vars `ai_workstation_lease_remote` and `ai_workstation_lease_host` in the hosts file) installs `/usr/local/libexec/workstation-lease` (`files/workstation-lease.py`): branch `lease` of a private arbiter repo, compare-and-swap pushes, TTL 10 min, watch every 2 min, fence margin 4 min, takeover grace 2 min.
- The two workstations only. Never enable it on a laptop that is not one of the pair or on a VPS; never edit the arbiter branch by hand (use `rc lease release|take|force`).
- Gates: `ExecCondition` on `claude-remote-control@.service` plus `rc up` (yadm `rc`). Timer gates only for services that run on both machines (`ai_workstation_lease_gated_*_units`); schulpc-only jobs stay ungated so backups keep running while the standby holds the lease.
- Tests: `python3 -I tests/test_workstation_lease.py` after every change to the tool; changes to timings need the margin rule (`ttl >= fence_margin + 120`) and a fence that finishes before expiry (`rc down --wait`, hard stop after twice that).
- Rollout on a standby laptop needs a role run with sudo while it is awake; no unattended root changes there.
