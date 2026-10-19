# Ansible openSUSE Tumbleweed Server & Laptop Provisioning

Modular, production-ready Ansible playbook designed for automated provisioning, software deployment, power management, and desktop environment configuration on **openSUSE Tumbleweed**.

---

## 🛠 Features & Architecture

* **Modular Feature-Flag Architecture**: Every subsystem is decoupled into a compact, single-responsibility role controlled via booleans in `group_vars/all.yml` or runtime CLI flags (`-e "enable_<role>=true"`).
* **Idempotent Playbook Execution**: Follows strict Ansible best practices with TDD verification, check-mode support (`--check`), and full idempotency.
* **openSUSE Tumbleweed Ready**: Optimized for Tumbleweed's rolling release model, featuring PEP 668 pip isolation handling, PipeWire audio integration, and vendor-priority codec alignment via Packman.

---

## 📦 Role Catalog

### ⚙️ System & Core Infrastructure
* **`system_update`**: Installs `topgrade` upgrade utility via zypper, refreshes package repositories, and executes system-wide updates (`zypper dup`).
* **`ssh_setup`**: Secures `.ssh` directory permissions and provisions `authorized_keys`.
* **`luks_boot_setup`**: Manages root LUKS keyfiles, LVM discards/TRIM, Dracut initramfs modules, and GRUB kernel parameters.
* **`power_management`**: Configures `powertop` and manages `tlp.service` for laptop battery optimization.
* **`bluetooth_setup`**: Installs `bluez`, firmware packages, and enables system Bluetooth services.
* **`printing_setup`**: Installs CUPS printing stack, PDF backends, deploys `printers.conf`, and manages `cups.service`.

### 🐚 Base Software & Command-Line Tools
* **`base_software`**: Baseline system utilities and filesystem tools (`zellij`, `neovim`, `htop`, `mosh`, `git`, NTFS/exFAT drivers).
* **`python_environment`**: Provisions Python 3 alternatives, `pip`, and installs CLI packages (`manly`) with PEP 668 compliance.
* **`shell_environment`**: Interactive shell setup including Zsh, Yadm dotfile manager, Topgrade updater, FZF, Ripgrep, and NCDU.
* **`cli_tools`**: Specialized CLI applications (`tldr` via global npm, `tmuxp` via pip, `tintin++` source compilation toolchain).
* **`ai_workstation`**: Provisions the unified AI environment across Antigravity, Claude Code, and OpenCode: MCP server runtimes (`uv tool` servers with a daily `ai-mcp-tools-update.timer`, global npm servers, zypper `chromium` for Playwright), the 0600 secrets file `~/.config/ai/env`, a read-only `docker-socket-proxy` on `127.0.0.1:2375` where Docker is installed, skills, and shell environment. Harness configs are owned by yadm (`~/.config/ai/claude-plugins`, `mcp_config.json##template`, `opencode.json##template`); the role renders the templates with the secrets and registers the `workstation-mcp` Claude Code plugin. `DRAGTOKENS_API_KEY` feeds the DragTokens provider in OpenCode (plan agent `gpt-6-astra`, build agent `gpt-6.1-sol`). Supply new secrets via environment, e.g. `NEXTCLOUD_HOST=… NEXTCLOUD_USERNAME=… NEXTCLOUD_PASSWORD=… ansible-playbook main.yml -e enable_ai_workstation=true`; existing values are kept from `~/.config/ai/env`.
* **`ai_desktop`**: Installs Claude Desktop (from Anthropic's signed apt repository, signature and checksums verified), Claude Code (official native installer), Google Antigravity Desktop (from Google's official release repository, size and CRC32C verified), Google Antigravity CLI (`agy`, official native installer), and OpenCode CLI (official V2 native installer into `~/.opencode/bin`; migrates V1 installs and replaces the former npm global `opencode-ai`; `opencode-restart-stale-server` restarts the background server after an update), with daily systemd timers keeping all five up to date and only the newest version of each installed.


### 🎨 Desktop & Graphical Applications
* **`desktop_fonts`**: Installs Adobe Source Code Pro, Source Sans Pro, and Source Serif Pro typography packages.
* **`graphical_environment`**: Core desktop software suite (`MozillaFirefox`, `MozillaThunderbird`, `partitionmanager`, `gwenview`, `ark`, `tigervnc` VNC viewer).
* **`desktop_messaging`**: Removes legacy zypper repository/packages and installs Signal Desktop client via Flatpak (`org.signal.Signal`).
* **`multimedia_codecs`**: Configures high-priority Packman repository and installs unrestricted audio/video codecs (`ffmpeg`, `vlc`, `mpv`, `gstreamer-plugins-*`, `x264`, `x265`, `faac`, `faad2`).
* **`office_suite`**: Installs full LibreOffice productivity suite, Okular PDF viewer, and FileZilla FTP client.
* **`graphics_tools`**: Image manipulation and editing tools (GIMP, Gwenview).
* **`gaming_environment`**: Installs Linux gaming platforms and emulators (`steam`, `lutris`, `dosbox`, `doomsday`).

### 📦 Containers & Application Packaging
* **`docker`**: Installs Docker engine, container utilities, and manages `docker.service`.
* **`flatpak_setup`**: Installs Flatpak daemon and configures the Flathub remote repository.
* **`obsidian`**: Installs Obsidian knowledge management app via Flatpak (automatically includes `flatpak_setup`).

### 🖥️ Services & Daemons
* **`syncthing_daemon`**: Configures Syncthing continuous file synchronization daemon.
* **`docker_pi_hole`**: Containerized Pi-hole DNS ad-blocker deployment.
* **`plex_server`**: Media server deployment (`plexmediaserver`).
* **`rdp_server`**: Remote desktop environment configuration (`xrdp`).
* **`irc_bouncer`**: ZNC IRC bouncer deployment.
* **`rclone_backup`**: Cloud storage sync and backup tooling.
* **`transmission_daemon`**: BitTorrent client service (`transmission-daemon`).

---

## 🚀 Usage Guide

### Syntax Verification
```bash
ansible-playbook main.yml --syntax-check
```

### Dry-Run Check Mode
```bash
ansible-playbook main.yml --check -e "enable_base_software=true enable_shell_environment=true"
```

### Provision Local Host
Run selected roles directly on `localhost`:
```bash
sudo ansible-playbook main.yml -e "enable_multimedia_codecs=true enable_office_suite=true enable_gaming_environment=true"
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.