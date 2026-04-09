# NM-OS

NM-OS is a Tor-first, Debian-based live operating system focused on private
sessions, controlled persistence, and a small, auditable runtime.

## Alpha scope

- Debian Trixie `amd64` live image
- GNOME + GDM welcome session before the live desktop
- Tor-gated network bootstrap
- pre-login greeter for locale, keyboard, network, and persistence
- LUKS2-backed persistence service

## Repository layout

- `build/` build, packaging, and verification entry points
- `config/` live-build project files and static image content
- `hooks/` live-build hook scripts
- `apps/` first-party Python applications and services
- `tests/` smoke checks for repo hygiene and image scaffolding
- `docs/` operator and implementation notes

## Build host

NM-OS is built on Linux. A Debian or Ubuntu host with `live-build`,
`debootstrap`, `rsync`, `xorriso`, `qemu-system-x86`, `sha256sum`, and root
access is expected.

For Windows development, use WSL2 and the PowerShell wrappers in `build/`.

## Quick start

```powershell
.\build\build.ps1
```

Optional Brave build (privacy-focused, not equivalent to Tor Browser
anonymity):

```powershell
.\build\build.ps1 -EnableBrave
```

The build produces:

- `dist/nmos-amd64-<version>.img`
- `dist/nmos-amd64-<version>.iso`
- `dist/nmos-amd64-<version>.sha256`
- `dist/nmos-amd64-<version>.packages`
- `dist/nmos-amd64-<version>.build-manifest`

The `.img` file is the primary artifact for writing a USB stick from Windows.
It is published as an `iso-hybrid` raw image, so the persistence backend fails
closed unless the boot USB exposes a writable GPT partition table with safe
trailing free space.

## Smoke checks

```bash
./tests/smoke/verify-structure.sh
./tests/smoke/verify-python.sh
./tests/smoke/verify-build-hygiene.sh
./tests/smoke/verify-brave-optional.sh
./tests/smoke/verify-greeter-state.sh
./tests/smoke/verify-live-login-config.sh
./tests/smoke/verify-network-gate-transition.sh
./tests/smoke/verify-network-status-normalization.sh
./tests/smoke/verify-prelogin-wiring.sh
./tests/smoke/verify-persistence-state-machine.sh
./tests/smoke/verify-runtime-logic.sh
./tests/smoke/verify-disk-safety.sh
./tests/smoke/verify-leaks.sh
```

After a build completes:

```bash
./tests/smoke/verify-artifacts.sh
```

## Current status

This repository contains the alpha platform scaffold: build system, GDM welcome
flow, runtime services, persistence backend, and smoke checks. It is intended
to be iterated on from a Windows editor + WSL2 build environment.
