# 05 Installer Redesign

## Purpose
Define the phased path from Debian-installer preseed remix to an NM-OS-controlled installer experience.

## Current State
- Active install path: Debian-installer preseed injected into remixed netinst ISO.
- Calamares configuration/branding exists, but is not the active installation flow.
- NM-OS product settings are currently applied post-install via overlay script.

## Evidence From Repo
- `build/lib/common.sh` (`render_installer_preseed_files`, `patch_debian_installer_menu`)
- `config/installer/debian-installer/preseed/nmos.cfg.in`
- `config/installer/debian-installer/preseed/install-overlay.sh.in`
- `config/installer/calamares/settings.conf`
- `config/installer/calamares/branding/nmos/branding.desc`
- `docs/installation.md`

## Target State
Installer that is owned by NM-OS product requirements:
- partitioning and encryption policies
- user creation and identity setup
- profile selection at install time
- post-install service bootstrap and recovery hooks

## Responsibility Matrix
- Live environment:
  - minimal bootable installer runtime with hardware/network basics
- Disk selection/partitioning:
  - guided and advanced paths, safe defaults
- Encryption:
  - explicit encrypted-system and encrypted-vault options
- User creation:
  - account, locale, keyboard, host naming
- Profile selection:
  - `Relaxed/Balanced/Hardened/Maximum` and reboot-impact notice
- Post-install:
  - enable units, seed settings, register recovery metadata
- Recovery hooks:
  - recovery boot entry and diagnostic bundle entry point

## Phased Plan
Phase A (now):
- Stabilize current preseed path and continue CI coverage.

Phase B:
- Expand Calamares scaffolding from branding-only to module-level install flow while still using Debian base packages.

Phase C:
- Move installer logic to NM-OS package/image definitions and remove preseed late-command overlay dependency.

Phase D:
- Add installer recovery integration and upgrade-safe migration flow.

## Alternatives Considered
1. Keep preseed forever:
   - low effort, weak product control.
2. Immediate installer rewrite:
   - high risk while distro pipeline is still evolving.
3. Controlled phased redesign:
   - recommended.

## Risks
- Partitioning/encryption edge cases can become support bottlenecks.
- Migration from old installs must preserve user data and settings.

## Open Questions
- Final installer engine and module strategy.
- Minimum hardware and firmware requirements for installer environment.

## Exit Criteria
- Installer no longer depends on Debian preseed injection.
- NM-OS profile and policy setup is first-class during install.
- Recovery boot path is install-time configurable.

## Fact / Inference / Assumption
- FACT: preseed `late_command` currently copies and extracts NM-OS overlay.
- FACT: Calamares config exists as scaffolding.
- INFERENCE: installer ownership can evolve without immediate runtime refactor.
- ASSUMPTION: future installer should preserve current NM-OS UX tone (profile-driven, user-friendly).

