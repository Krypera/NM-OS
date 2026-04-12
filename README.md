# NM-OS

NM-OS is a privacy-focused desktop system profile for Debian-based systems.

The goal is simple: start with careful defaults, stay easy to understand, and let people shape the system around their own comfort level.

Today NM-OS includes:

- security profiles with room for custom tuning
- a setup assistant before login
- a desktop control center for everyday changes
- Tor-first, direct, or offline networking choices
- an encrypted vault for sensitive files
- a clean visual style with a few intentional theme options

## What Exists Today

The repo currently builds:

- an installed-system overlay archive
- installer assets
- a ready-to-boot installer ISO

The current slice includes:

- preset-aware system settings with schema versioning
- `org.nmos.Settings1` for settings management
- the existing encrypted vault backend on `org.nmos.PersistentStorage`
- a richer greeter onboarding flow with profile and appearance choices
- an `NM-OS Control Center` desktop app skeleton
- shared theme CSS and branding assets
- a Debian-installer-based NM-OS ISO
- Calamares installer configuration scaffolding for the desktop installer path

The default profile is `Balanced`.

## Quick Start

### Windows + WSL2

```powershell
.\build\install-deps.ps1
.\build\build.ps1
```

Optional Brave-aware overlay:

```powershell
.\build\build.ps1 -EnableBrave
```

### Linux / WSL2 Direct

```bash
./build/build.sh
```

Optional Brave-aware overlay:

```bash
NMOS_ENABLE_BRAVE=1 ./build/build.sh
```

## Testing

The safest way to test NM-OS is inside a virtual machine.

The easiest flow now is:

1. build the installer ISO from this repo
2. boot that ISO in VirtualBox or another VM
3. choose `Install NM-OS`
4. finish the Debian-based install flow
5. reboot into the installed NM-OS system

The current install details are in [docs/installation.md](docs/installation.md).

## Useful Docs

- [Product direction](docs/vision.md)
- [Build notes](docs/build.md)
- [Installation notes](docs/installation.md)
- [Runtime notes](docs/runtime.md)
- [Security model](docs/security-model.md)
- [Security settings](docs/security-profiles.md)
- [Translation guide](docs/translations.md)
- [Windows + WSL2 workflow](docs/windows-wsl.md)
- [Independence program](docs/independence/README.md)

## Repository Layout

- `apps/` Python applications and services
- `build/` build entry points and artifact verification helpers
- `config/system-overlay/` runtime overlay content for the installed system
- `config/installer/` Calamares installer scaffolding
- `config/system-packages/` target runtime package manifests
- `config/installer-packages/` installer-side package manifests
- `tests/` smoke and Python validation

## Current Limits

Still not finished in this alpha:

- a release-grade installer ISO
- a full update UI
- full per-app permission editing
- release-grade hardware validation

## Translations

English is the source language for NM-OS, and Spanish is the first additional UI translation.

Translation help is welcome. The current workflow is documented in [docs/translations.md](docs/translations.md).

## License

NM-OS is licensed under `GPL-3.0-or-later`.
See [LICENSE](LICENSE) and [COPYING](COPYING).
