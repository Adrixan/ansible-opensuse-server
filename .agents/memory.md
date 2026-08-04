# Project Memory: ansible-opensuse-server

This memory file captures the essential logic, design goals, architectural patterns, and known issues of the `ansible-opensuse-server` repository.

## Repository Intention
The primary goal of this repository is to automate the installation, configuration, and provisioning of a local personal workstation/server running **openSUSE Tumbleweed**.
It is configured to run pull-style deployments (`ansible_connection=local`) targeting `localhost`.

## Compact Semantic Role Architecture
- **[roles/system_update](file:///home/Adrixan/code/ansible-opensuse-server/roles/system_update)**: System package upgrade.
- **[roles/ssh_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/ssh_setup)**: User SSH access (`authorized_keys`).
- **[roles/luks_boot_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/luks_boot_setup)**: LUKS keyfile, Dracut, initramfs.
- **[roles/power_management](file:///home/Adrixan/code/ansible-opensuse-server/roles/power_management)**: Power management (`powertop`).
- **[roles/bluetooth_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/bluetooth_setup)**: Bluetooth stack (`bluez`).
- **[roles/printing_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/printing_setup)**: CUPS printing subsystem.
- **[roles/python_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/python_environment)**: Python system alternatives & pip packages (`manly`).
- **[roles/base_software](file:///home/Adrixan/code/ansible-opensuse-server/roles/base_software)**: Essential system utilities & drivers.
- **[roles/shell_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/shell_environment)**: Interactive shell tools & Packman repo.
- **[roles/cli_tools](file:///home/Adrixan/code/ansible-opensuse-server/roles/cli_tools)**: Specialized CLI applications (`tldr` npm, `tmuxp` pip, `tintin++` build).
- **[roles/opencode](file:///home/Adrixan/code/ansible-opensuse-server/roles/opencode)**: OpenCode AI CLI tool (`opencode-ai` via global npm).
- **[roles/desktop_fonts](file:///home/Adrixan/code/ansible-opensuse-server/roles/desktop_fonts)**: Desktop typography.
- **[roles/graphical_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/graphical_environment)**: Core desktop software.
- **[roles/desktop_messaging](file:///home/Adrixan/code/ansible-opensuse-server/roles/desktop_messaging)**: Signal Desktop Flatpak client (`org.signal.Signal`).
- **[roles/multimedia_codecs](file:///home/Adrixan/code/ansible-opensuse-server/roles/multimedia_codecs)**: Packman players and codecs with Packman vendor preference.
- **[roles/office_suite](file:///home/Adrixan/code/ansible-opensuse-server/roles/office_suite)**: LibreOffice suite & utilities.
- **[roles/graphics_tools](file:///home/Adrixan/code/ansible-opensuse-server/roles/graphics_tools)**: GIMP & Gwenview image software.
- **[roles/gaming_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/gaming_environment)**: Steam, Lutris, DOSBox, Doomsday.
- **[roles/docker](file:///home/Adrixan/code/ansible-opensuse-server/roles/docker)**: Containerization daemon & systemd template.
- **[roles/flatpak_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/flatpak_setup)**: Flatpak system package & Flathub remote.
- **[roles/obsidian](file:///home/Adrixan/code/ansible-opensuse-server/roles/obsidian)**: Obsidian Flatpak app.
- Other server/daemon roles: `docker_pi_hole`, `irc_bouncer`, `plex_server`, `rclone_backup`, `rdp_server`, `syncthing_daemon`, `transmission_daemon`.

## Key Implementation Patterns & Decisions
- **Packman Codec Vendor Alignment**: Configured `roles/multimedia_codecs` with Packman priority (50) and `allow_vendor_change: yes` to pull unrestricted media libraries (`libavcodec`, `libavformat`, `libavfilter`, `vlc-codecs`, `ffmpeg`) from Packman.
- **PEP 668 Pip Compliance**: System-wide pip tasks use `extra_args: "--break-system-packages"` for openSUSE Tumbleweed compatibility.
- **PipeWire Audio Integration**: Replaced legacy `pulseaudio-module-bluetooth` and `pulseaudio-module-x11` with openSUSE standard PipeWire audio stack.
- **Dynamic Role Evaluation**: [main.yml](file:///home/Adrixan/code/ansible-opensuse-server/main.yml) uses `ansible.builtin.include_role` with `when: enable_<role> | default(false) | bool`.

## Deferred / Technical Debt Log
- **Plaintext Host Password**: `ansible_ssh_pass=aufner02` is in [hosts](file:///home/Adrixan/code/ansible-opensuse-server/hosts). Retained per explicit user directive.
