# Product Backlog & Plan

## Product Backlog (MoSCoW)

### Completed Stories (Sprints 1-8)
- **US-1**: Repository Analysis & State Scaffolding (3 SP) - **Done**
- **US-2**: Intention Explanation & Memory File Creation (2 SP) - **Done**
- **US-2.1**: Parameterize User and Home Directory Variables (5 SP) - **Done**
- **US-2.2**: Disable Roles by Default & Refactor Playbook Execution (2 SP) - **Done**
- **US-2.3**: Standardize Inventory, Configuration, `group_vars/all.yml`, and `roles/` Layout (2 SP) - **Done**
- **US-2.4**: Refactor Tasks for Native Modules, Idempotency, and Quality (5 SP) - **Done**
- **US-3.1**: Rename Hyphenated Roles to `snake_case` Conventions (2 SP) - **Done**
- **US-3.2**: Upgrade Ansible Module Invocations to FQCN Syntax (3 SP) - **Done**
- **US-4.1**: Refine `base_software` & `shell_environment`, purge `cheat`/`hstr`, migrate `topgrade` to `zypper` (3 SP) - **Done**
- **US-4.2**: Extract Docker Containerization into Standalone `docker` Role (3 SP) - **Done**
- **US-4.3**: Local Verification & Playbook Testing (2 SP) - **Done**
- **US-5.1**: Decompose System Maintenance & SSH Access (`system_update`, `ssh_setup`) (2 SP) - **Done**
- **US-5.2**: Decompose Python Environment (`python_environment`) (2 SP) - **Done**
- **US-5.3**: Decompose Compiled & Global CLI Tools (`cli_tools`) (2 SP) - **Done**
- **US-5.4**: Refine `base_software` & `shell_environment` Roles (3 SP) - **Done**
- **US-5.5**: Local Host Execution Verification (2 SP) - **Done**
- **US-6.1**: Create `flatpak_setup` Role (2 SP) - **Done**
- **US-6.2**: Create `obsidian` Role (2 SP) - **Done**
- **US-6.3**: Register Roles in `group_vars/all.yml` & `main.yml` (1 SP) - **Done**
- **US-6.4**: Local Verification & Playbook Testing (2 SP) - **Done**
- **US-7.1**: Decompose `laptop_setup` into `power_management`, `printing_setup`, `luks_boot_setup` (3 SP) - **Done**
- **US-7.2**: Decompose `graphical_environment` into `desktop_fonts`, `multimedia_codecs`, `gaming_environment`, `office_suite`, `graphics_tools`, `desktop_messaging`, `bluetooth_setup` (5 SP) - **Done**
- **US-7.3**: Update `group_vars/all.yml` & `main.yml` (2 SP) - **Done**
- **US-7.4**: Ansible `--syntax-check` & `--check` Dry-Run Verification (2 SP) - **Done**
- **US-7.5**: Live Localhost Execution of Base Setup & Shell Environment (3 SP) - **Done**
- **US-7.6**: State File Updates & Git Commit / Push (2 SP) - **Done**
- **US-8.1**: Configure Packman vendor-priority alignment for unrestricted codecs in `multimedia_codecs` (3 SP) - **Done**
- **US-8.2**: Live Localhost Execution of `desktop_*`, `gaming`, `graphical`, `graphics`, `multimedia`, and `office` roles (5 SP) - **Done**
- **US-8.3**: Comprehensive `README.md` documentation explaining all 26 playbook roles (3 SP) - **Done**
- **US-8.4**: State File Updates & Git Commit / Push to `origin/laptops` (2 SP) - **Done**

### Deferred / Backlog
- **US-1.1**: Encrypt Plaintext Password in `hosts` File (Deferred per user instruction, retained in state/memory log).
- **US-5.6**: Modernize Source Code Compilation Roles (PulseAudio 11.1 version parameterization).
