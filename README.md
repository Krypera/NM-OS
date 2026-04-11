# NM-OS

NM-OS is a privacy-first installed operating system profile for Debian-based systems.

The current direction is simple:

- security presets instead of one hard-coded mode
- a pre-login setup assistant inside GDM
- a desktop control center for everyday tuning
- Tor-first, direct, or offline networking as system settings
- an encrypted vault for sensitive files
- a retro-futuristic but user-friendly visual language

## What Exists Today

The repo currently builds an installed-system overlay plus installer scaffolding assets.

The first product slice now includes:

- preset-aware system settings with schema versioning
- `org.nmos.Settings1` for settings management
- the existing encrypted vault backend on `org.nmos.PersistentStorage`
- a richer greeter onboarding flow with profile and appearance choices
- an `NM-OS Control Center` desktop app skeleton
- shared theme CSS and branding assets
- Calamares installer configuration scaffolding

## Product Direction

NM-OS is not trying to be a Qubes clone.

The goal is a normal desktop OS that can start from cautious defaults, then let the user move toward:

- more comfort
- more privacy
- more restriction
- or a custom balance

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

## Useful Docs

- [Build notes](docs/build.md)
- [Installation notes](docs/installation.md)
- [Runtime notes](docs/runtime.md)
- [Security settings](docs/security-profiles.md)
- [Translation guide](docs/translations.md)
- [Windows + WSL2 workflow](docs/windows-wsl.md)

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
