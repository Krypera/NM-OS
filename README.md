# NM-OS

NM-OS is a privacy-focused live operating system project designed to boot from a USB drive.

The goal is simple: start clean, stay cautious by default, and keep the user in control.

NM-OS is still in alpha, but the core direction is already here:

- USB boot with multiple boot modes
- a real welcome screen before the desktop session
- Tor-first network gating
- encrypted persistence on the same USB drive

## What It Includes Today

- GNOME + GDM based live session flow
- `nmos-greeter` for pre-login setup and status
- a persistence backend for encrypted USB storage
- smoke checks for build and runtime wiring
- Windows-friendly build wrappers with WSL2 support

Brave support is optional. If enabled, it is only intended for `Flexible` mode.

## Quick Start

### Windows + WSL2

```powershell
.\build\install-deps.ps1
.\build\build.ps1
```

Optional Brave build:

```powershell
.\build\build.ps1 -EnableBrave
```

### Linux / WSL2 Direct

```bash
./build/build.sh
```

Optional Brave build:

```bash
NMOS_ENABLE_BRAVE=1 ./build/build.sh
```

## Useful Docs

- [Build notes](docs/build.md)
- [Runtime notes](docs/runtime.md)
- [Translation guide](docs/translations.md)
- [Windows + WSL2 workflow](docs/windows-wsl.md)
- [Security profiles](docs/security-profiles.md)
- [USB boot checklist](docs/usb-boot-checklist.md)

## Repository Layout

- `apps/` application code for the greeter and backend services
- `build/` build entry points and verification helpers
- `config/` live-build project files and runtime image content
- `hooks/` build hooks used while assembling the image
- `tests/` smoke checks for repo and runtime safety
- `docs/` project notes and setup guides

## Current Scope

Already in progress:

- image assembly
- pre-login greeter flow
- network readiness gating
- encrypted persistence

Not part of the current alpha yet:

- internal disk installer
- updater
- large application bundle
- release-grade hardware validation

## Translations

English is the source language for NM-OS, and Spanish is the first additional UI translation.

Translation help is welcome. If you want to add or improve another language, feel free to open a PR.

The current translation workflow is documented in [docs/translations.md](docs/translations.md).

## License

NM-OS is licensed under `GPL-3.0-or-later`.
See [LICENSE](LICENSE) and [COPYING](COPYING).
