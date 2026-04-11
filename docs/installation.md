# Installation Notes

NM-OS currently ships as an installed-system overlay bundle.

The expected target is a Debian-based system with GNOME and GDM already available, or a base image you control in CI or VM automation.

## Artifact Output

The build produces:

- `dist/nmos-system-overlay-<version>.tar.gz`
- `dist/nmos-system-overlay-<version>.sha256`
- `dist/nmos-system-overlay-<version>.packages`
- `dist/nmos-system-overlay-<version>.build-manifest`

## High-Level Install Flow

1. Prepare a Debian-based target system.
2. Install the packages listed in `*.packages`.
3. Extract the overlay archive on top of `/`.
4. Run `systemd-tmpfiles --create /usr/lib/tmpfiles.d/nmos.conf`.
5. Run `systemctl daemon-reload`.
6. Ensure GDM is the active display manager.
7. Reboot.

## What The Overlay Enables

- a pre-login setup assistant in the greeter
- runtime settings bootstrap under `/var/lib/nmos/system-settings.json`
- Tor-first, direct, or offline network policy
- an encrypted vault backend at `/var/lib/nmos/storage/vault.img`

## Current Limitation

The repo does not yet build a complete installer ISO or disk image.

That is an intentional scope cut for this stage of the transition away from the live-image model.
