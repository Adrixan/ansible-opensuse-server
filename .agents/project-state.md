# Project State: ansible-opensuse-server

## User Profile
- **Development Experience**: Senior (Full control, detailed trade-offs)
- **Role**: System Administrator / Power User

## Environment & Tech Stack
- **Target OS**: openSUSE Tumbleweed
- **Control Node OS**: Linux (Localhost target)
- **Package Manager**: `zypper` (system), `pip3` (Python), `npm` (Node.js), `flatpak` (Flathub)
- **Primary Shell**: `zsh`
- **Configuration Management**: Ansible 2.9+
- **Containerization**: Docker & Docker Compose
- **Service Manager**: `systemd`

## Compact Semantic Role Architecture (26 Roles)
1. **[system_update](file:///home/Adrixan/code/ansible-opensuse-server/roles/system_update)**: System package upgrade.
2. **[ssh_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/ssh_setup)**: User SSH access & `authorized_keys`.
3. **[luks_boot_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/luks_boot_setup)**: Root LUKS keyfile, Dracut, GRUB parameters, initramfs.
4. **[power_management](file:///home/Adrixan/code/ansible-opensuse-server/roles/power_management)**: Power management tools (`powertop`, `tlp.service`).
5. **[bluetooth_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/bluetooth_setup)**: Bluetooth stack (`bluez`, `bluez-firmware`, `bluetooth.service`).
6. **[printing_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/printing_setup)**: Printing subsystem (`cups`, `cups-backends`, `cups-pdf`, `printers.conf`).
7. **[python_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/python_environment)**: Python system alternatives (`python`/`pip`) & `manly` (PEP 668 compliant).
8. **[base_software](file:///home/Adrixan/code/ansible-opensuse-server/roles/base_software)**: Essential system utilities & drivers.
9. **[shell_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/shell_environment)**: Interactive shell packages (`zsh`, `yadm`, `topgrade` via zypper, `fzf`, `ripgrep`, etc.) and Packman repo.
10. **[cli_tools](file:///home/Adrixan/code/ansible-opensuse-server/roles/cli_tools)**: Specialized CLI applications (`tldr` via npm, `tmuxp` via pip, `tintin++` compilation).
11. **[desktop_fonts](file:///home/Adrixan/code/ansible-opensuse-server/roles/desktop_fonts)**: Adobe Source Code/Sans/Serif Pro fonts.
12. **[graphical_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/graphical_environment)**: Desktop tools (Firefox, Partition Manager, Gwenview, Ark).
13. **[desktop_messaging](file:///home/Adrixan/code/ansible-opensuse-server/roles/desktop_messaging)**: Signal desktop messaging client.
14. **[multimedia_codecs](file:///home/Adrixan/code/ansible-opensuse-server/roles/multimedia_codecs)**: Packman media players & codecs (`vlc`, `ffmpeg`, `mpv`, `gstreamer`, `x264`, `x265`, `faac`, `faad2`) with Packman vendor priority alignment.
15. **[office_suite](file:///home/Adrixan/code/ansible-opensuse-server/roles/office_suite)**: LibreOffice suite, Okular, FileZilla.
16. **[graphics_tools](file:///home/Adrixan/code/ansible-opensuse-server/roles/graphics_tools)**: GIMP & Gwenview image applications.
17. **[gaming_environment](file:///home/Adrixan/code/ansible-opensuse-server/roles/gaming_environment)**: Steam, Lutris, DOSBox, Doomsday.
18. **[docker](file:///home/Adrixan/code/ansible-opensuse-server/roles/docker)**: Docker daemon, `docker-compose`, systemd service template.
19. **[flatpak_setup](file:///home/Adrixan/code/ansible-opensuse-server/roles/flatpak_setup)**: Flatpak package installation & Flathub remote setup.
20. **[obsidian](file:///home/Adrixan/code/ansible-opensuse-server/roles/obsidian)**: Obsidian Flatpak application installation (`md.obsidian.Obsidian`).
21. Other server/daemon roles: `docker_pi_hole`, `irc_bouncer`, `plex_server`, `rclone_backup`, `rdp_server`, `syncthing_daemon`, `transmission_daemon`.

## Technical Debt & Deferred Items
1. **Plaintext Password in Host File**: Password `ansible_ssh_pass=aufner02` in [hosts](file:///home/Adrixan/code/ansible-opensuse-server/hosts) retained per user directive.
