# NM-OS

NM-OS is a privacy-focused installed operating system profile for Debian-based systems.

The goal is simple: ship cautious defaults, keep privacy features understandable, and let the user tune them from a setup assistant instead of juggling boot-time modes.

NM-OS is still in alpha, but the current direction is already clear:

- a pre-login setup assistant inside GDM
- Tor-first, direct, or offline network policy as normal system settings
- an encrypted vault for sensitive files
- optional Brave support gated by both build-time and runtime settings
- a reproducible system overlay build for Linux and WSL2

## What It Builds Today

The repository now produces an installed-system overlay bundle, not a live USB image.

The overlay contains:

- systemd units and runtime helpers
- GDM greeter session wiring
- NM-OS Python applications installed into the target Python path
- package manifests for the expected Debian base system

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

- `apps/` application code for the setup assistant and backend services
- `build/` build entry points and artifact verification helpers
- `config/system-overlay/` filesystem overlay content for the installed system
- `config/system-packages/` expected Debian package manifests
- `tests/` smoke checks for repo and runtime safety
- `docs/` project notes and setup guides

## Current Scope

Already in progress:

- overlay assembly for an installed base system
- pre-login setup assistant flow
- settings-driven network policy
- encrypted vault management

Not part of the current alpha yet:

- a full graphical installer
- an updater
- large application bundles
- release-grade hardware validation

## Translations

English is the source language for NM-OS, and Spanish is the first additional UI translation.

Translation help is welcome. If you want to add or improve another language, feel free to open a PR.

The current translation workflow is documented in [docs/translations.md](docs/translations.md).

## License

NM-OS is licensed under `GPL-3.0-or-later`.
See [LICENSE](LICENSE) and [COPYING](COPYING).
