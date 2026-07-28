# Sprint Backlog & To-Do

## Sprint Goal
Migrate `desktop_messaging` role to remove legacy OBS zypper repository and native Signal RPM packages, install Signal Desktop via Flatpak (`org.signal.Signal`), verify live execution, update documentation, and commit/push changes.

## Completed Sprint Stories (Sprint 9)
- **US-9.1**: Refactor `desktop_messaging` to purge legacy `signal` zypper repo and packages, and install `org.signal.Signal` Flatpak (3 SP) - **Done**

## Verification Summary
- Playbook `--syntax-check`: **PASS (100%)**
- Live localhost execution (`desktop_messaging`): **PASS (ok=8, changed=3, failed=0)**
  - Legacy RPM packages (`signal-desktop`, `signal-sqlcipher`, `libsignal`, `signal-libringrtc`): **Uninstalled**
  - Legacy Zypper repo (`signal`): **Removed**
  - Flatpak app (`org.signal.Signal`): **Installed & Verified (v8.20.0)**
- Remote Push: **Pushed to `origin/laptops`**

