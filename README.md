# NM-OS

NM-OS is a configurable desktop operating system experience for Debian-based systems.

The project is built around one idea: the system should start clear, calm, and accessible, then become stricter only when the user asks for stronger boundaries.

This is not meant to be a themed Linux install with security branding on top. NM-OS aims to grow into a platform with its own policy model, installer flow, security posture, and user experience.

## What NM-OS Tries To Do

- stay understandable for new users
- let advanced users harden the same system without switching products
- make security choices visible instead of magical
- explain the tradeoff behind each stronger restriction
- give the user real control over comfort versus containment

## Current Product Shape

Today the repository builds:

- an installed-system overlay archive
- installer assets
- a bootable installer ISO

Today the product slice includes:

- security profiles with explainable tradeoffs
- a pre-login setup assistant
- a desktop control center
- Tor-first, direct, or offline networking modes
- an encrypted vault backend for sensitive files
- shared NM-OS theme and branding assets
- Debian-installer-based media for VM and hardware testing

The default profile is `Balanced`.

## Design Principles

### Explainable Security

Users should be able to see:

- what a profile changes
- which restrictions come with it
- what convenience is lost or preserved
- which changes apply now and which wait until reboot

### Choice Without Chaos

NM-OS should not force one correct workflow.

It should offer:

- clear defaults
- a small number of readable profiles
- stronger overrides for advanced users
- language that describes consequences plainly

### Progressive Hardening

The same platform should be able to serve:

- someone who wants a comfortable daily desktop
- someone who wants tighter network and device policy
- someone who wants stronger isolation with less convenience

## What Exists In The Repo

- `apps/` Python applications and services
- `build/` build entry points and artifact verification helpers
- `config/system-overlay/` runtime overlay content for the installed system
- `config/installer/` installer scaffolding
- `config/system-packages/` target runtime package manifests
- `config/installer-packages/` installer-side package manifests
- `tests/` smoke and Python validation

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

The safest way to evaluate NM-OS is inside a virtual machine.

Recommended flow:

1. Build the installer ISO from this repo.
2. Boot the ISO in VirtualBox, QEMU, VMware, or another VM.
3. Choose `Install NM-OS`.
4. Finish the Debian-based install flow.
5. Reboot into the installed system and test the setup assistant, profiles, vault, and control center.

Install details live in [docs/installation.md](docs/installation.md).

## Useful Docs

- [Product direction](docs/vision.md)
- [Security model](docs/security-model.md)
- [Security settings](docs/security-profiles.md)
- [Runtime notes](docs/runtime.md)
- [Build notes](docs/build.md)
- [Installation notes](docs/installation.md)
- [Translation guide](docs/translations.md)
- [Windows + WSL2 workflow](docs/windows-wsl.md)
- [Independence program](docs/independence/README.md)

## Current Limits

This is still alpha software.

Not finished yet:

- a release-grade update flow
- full per-app permission editing
- release-grade hardware validation
- a fully independent base platform beyond the current Debian-backed layer

## License

NM-OS is licensed under `GPL-3.0-or-later`.

See [LICENSE](LICENSE) and [COPYING](COPYING).
