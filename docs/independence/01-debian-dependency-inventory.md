# 01 Debian Dependency Inventory

## Purpose
Enumerate Debian-specific assumptions in the current NM-OS alpha and score replacement difficulty and risk.

## Current State
Current pipeline and runtime are Debian-family-oriented in build, install, package names, service identity, and desktop/session assumptions.

## Evidence From Repo
- `build/lib/common.sh`
- `build/build.sh`
- `config/installer/debian-installer/preseed/*`
- `config/system-packages/base.txt`
- `config/installer-packages/base.txt`
- `config/system-overlay/usr/lib/systemd/system/*`
- `config/system-overlay/etc/dbus-1/system.d/*`
- `docs/installation.md`

## Dependency Inventory

## Boot
- Dependency: Debian netinst ISO layout (`isolinux`, `grub`, `install.amd` paths)
- Where: `build/lib/common.sh` in `patch_debian_installer_menu`
- Role: injects `Install NM-OS` menu entries and kernel args
- Difficulty to replace: High
- Risk: High
- Migration note: move to NM-OS-owned image definitions and boot config generation

## Installer
- Dependency: Debian-installer preseed mechanism and tasksel behavior
- Where: `config/installer/debian-installer/preseed/nmos.cfg.in`
- Role: install GNOME task and package set, run late overlay application
- Difficulty: High
- Risk: High
- Migration note: move to installer flow where partition/encryption/profile logic is NM-OS first-class, not late-command hooks

- Dependency: Debian target assumptions inside late script (`in-target`, file paths)
- Where: `config/installer/debian-installer/preseed/install-overlay.sh.in`
- Role: unpack overlay and initialize runtime files
- Difficulty: Medium
- Risk: High
- Migration note: replace with package post-install actions or installer modules

## Runtime
- Dependency: Debian user/group naming (`Debian-gdm`, `debian-tor`)
- Where:
  - `config/system-overlay/usr/lib/tmpfiles.d/nmos.conf`
  - `config/system-overlay/etc/dbus-1/system.d/org.nmos.Settings1.conf`
  - `config/system-overlay/etc/dbus-1/system.d/org.nmos.PersistentStorage.conf`
  - `config/system-overlay/usr/local/lib/nmos/network_bootstrap.py`
- Role: ownership, permissions, and nftables UID logic
- Difficulty: Medium
- Risk: Medium
- Migration note: centralize identity mapping in platform adapter and avoid hardcoded names

- Dependency: Debian-style package names and availability
- Where: `config/system-packages/base.txt`
- Role: runtime package resolution
- Difficulty: Medium
- Risk: Medium
- Migration note: create package abstraction manifests with per-platform mapping

## Desktop / Session
- Dependency: GNOME/GDM stack conventions from Debian packaging
- Where:
  - `config/system-packages/base.txt`
  - `config/system-overlay/usr/share/gdm/greeter/applications/*`
  - `config/system-overlay/etc/gdm3/PostLogin/Default`
- Role: greeter/session launch and post-login policy application
- Difficulty: Medium
- Risk: Medium
- Migration note: keep GNOME target initially, but isolate distro assumptions in adapter scripts

## Network
- Dependency: `tor` and `nftables` tool/runtime behavior expected by Debian packages
- Where:
  - `config/system-packages/base.txt`
  - `config/system-overlay/usr/local/lib/nmos/network_bootstrap.py`
- Role: Tor-first gate and offline policy
- Difficulty: Medium
- Risk: Medium
- Migration note: define NM-OS network policy contract independent of distro package naming

## Crypto / Storage
- Dependency: `cryptsetup`, `fsck`, mount stack from Debian userspace
- Where:
  - `config/system-packages/base.txt`
  - `apps/nmos_persistent_storage/nmos_persistent_storage/storage.py`
  - `apps/nmos_persistent_storage/nmos_persistent_storage/mount_crypto_ops.py`
- Role: encrypted vault create/unlock/repair
- Difficulty: Medium
- Risk: Medium
- Migration note: keep operation interface stable, swap command provider via platform adapter

## Packaging / Distribution
- Dependency: apt-oriented package list artifacts and netinst base
- Where:
  - `build/build.sh`
  - `build/lib/common.sh`
  - `docs/build.md`
- Role: runtime package manifest and installer package include list
- Difficulty: High
- Risk: High
- Migration note: shift from package list text files to NM-OS repo metadata and image manifests

## QA / Build / Release
- Dependency: Ubuntu runners with Debian tools (`xorriso`, shell scripts), Debian installer assumptions in tests
- Where:
  - `.github/workflows/smoke.yml`
  - `tests/smoke/verify-installer-media.sh`
  - `tests/smoke/verify-artifacts.sh`
- Role: CI validation for current pipeline
- Difficulty: Medium
- Risk: Medium
- Migration note: add new release gates while preserving current smoke path during migration

## Dependency Heat Map
- High risk/high effort:
  - Debian-installer preseed flow
  - netinst remix and boot path patching
  - apt-list-driven assembly model
- Medium:
  - user/group identity assumptions
  - package naming assumptions
  - command path/tool assumptions
- Low:
  - first-party Python product logic and D-Bus interface semantics

## Recommended Direction
1. Treat Debian bindings as adapter layer, not product core.
2. Move packaging and image logic to declarative manifests.
3. Preserve public D-Bus contracts while replacing distro substrate.

## Alternatives Considered
1. Keep hard Debian coupling and optimize around it:
   - low migration effort, low independence.
2. Immediate substrate swap:
   - high risk and likely break current alpha.
3. Phased decoupling with adapter layer:
   - recommended.

## Exit Criteria
- Every Debian-specific dependency above has an owner, migration ticket, and replacement status.
- New image/install path can run without `resolve_base_installer_iso`.

## Fact / Inference / Assumption
- FACT: netinst dependency is explicit in `build/lib/common.sh`.
- FACT: preseed late-command drives current overlay application.
- INFERENCE: package list format is currently apt-oriented and not distro-neutral.
- ASSUMPTION: early NM-OS independent releases will keep GNOME/GDM UX target.

