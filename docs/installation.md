# Installation Notes

NM-OS is moving toward a `Calamares` installer-first model, but the current repo still publishes:

- a runtime overlay archive
- installer scaffolding assets

## Current artifact output

- `dist/nmos-system-overlay-<version>.tar.gz`
- `dist/nmos-system-overlay-<version>.sha256`
- `dist/nmos-system-overlay-<version>.packages`
- `dist/nmos-system-overlay-<version>.build-manifest`
- `dist/nmos-installer-assets-<version>.tar.gz`
- `dist/nmos-installer-assets-<version>.sha256`
- `dist/nmos-installer-assets-<version>.packages`

## Overlay install flow today

1. Prepare a Debian-based target with GNOME and GDM.
2. Install the packages listed in `nmos-system-overlay-<version>.packages`.
3. Extract the overlay archive on top of `/`.
4. Run `systemd-tmpfiles --create /usr/lib/tmpfiles.d/nmos.conf`.
5. Run `systemctl daemon-reload`.
6. Reboot.

## What the overlay enables

- the GDM setup assistant
- `org.nmos.Settings1`
- `org.nmos.PersistentStorage`
- Tor-first, direct, or offline networking
- the NM-OS Control Center
- shared theme assets for first-party surfaces

## Installer status

The repo now includes:

- Calamares base configuration
- NM-OS installer branding assets
- installer-side package manifests

It does **not** yet publish a finished installer ISO.
