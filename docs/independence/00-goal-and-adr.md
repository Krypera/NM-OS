# 00 Goal And ADR

## Purpose
Define the exact independence target for NM-OS and lock the architectural decision record (ADR) that guides all follow-up work.

## Current State
The repository currently builds three artifacts:
- installed-system overlay archive
- installer assets archive
- bootable installer ISO

The installer ISO is assembled by taking Debian netinst media, injecting NM-OS preseed/templates and overlay payload, and replaying boot metadata.

## Evidence From Repo
- Build output and manifest generation:
  - `build/build.sh`
  - `build/verify-artifacts.sh`
- Debian netinst resolution and ISO remix:
  - `build/lib/common.sh` (`resolve_base_installer_iso`, `build_installer_iso_image`)
- Debian-installer late-command overlay install:
  - `config/installer/debian-installer/preseed/nmos.cfg.in`
  - `config/installer/debian-installer/preseed/install-overlay.sh.in`
- Calamares branding/config currently present as scaffolding:
  - `config/installer/calamares/settings.conf`
  - `config/installer/calamares/branding/nmos/branding.desc`
- Runtime and product layers:
  - `apps/nmos_common`
  - `apps/nmos_settings`
  - `apps/nmos_greeter`
  - `apps/nmos_control_center`
  - `apps/nmos_persistent_storage`

## Clarification: Independent Distro vs From-Scratch OS
- Independent Linux distribution:
  - uses Linux kernel and standard ecosystem toolchain
  - owns package repository, build pipeline, installer, release lifecycle
  - controls compatibility/support matrix and trust chain
- From-scratch OS:
  - would replace most platform layers and is a different mission class

NM-OS should target the first, not the second.

## ADR-0001
### Title
Adopt package-first independent Linux distribution strategy while preserving current overlay alpha as transition path.

### Status
Accepted (program baseline).

### Decision
NM-OS will evolve from Debian netinst remix to an NM-OS-owned distribution pipeline:
- package-first assembly for first-party components
- NM-OS-controlled image definitions (base, desktop, installer, recovery)
- NM-OS release channels, signing, update policy, and recovery model
- explicit separation between portable product core and replaceable distro infrastructure

### Rationale
- Current repo already has modular first-party product code and CI signals.
- Current Debian coupling is concentrated in known scripts/manifests and is replaceable in phases.
- Immediate rewrite would create high breakage risk and stall product velocity.

### Consequences
- Short term: dual operation (current overlay path + new package/image scaffolding).
- Medium term: packaging and installer ownership work becomes critical-path engineering.
- Long term: NM-OS controls release and trust lifecycle end-to-end.

### Tradeoffs
- Pro: controlled migration with less runtime breakage.
- Con: temporary complexity while both old and new assembly paths coexist.

### Alternatives Considered
1. Stay permanent Debian remix:
   - rejected because lifecycle ownership stays external.
2. Full from-scratch OS rewrite:
   - rejected as scope-incompatible and high-risk.
3. Recommended phased independence path:
   - accepted for feasibility and continuity.

## Migration Steps (high-level)
1. Freeze module boundaries and define package map.
2. Build first-party package artifacts and local package repo metadata.
3. Shift image assembly to package manifests.
4. Replace preseed-driven install with NM-OS installer workflow.
5. Add signed channels and recovery-tested release gates.

## Risks
- Packaging drift between current overlay and future packages.
- Installer transition delays due to partition/encryption UX complexity.
- Update/recovery immaturity causing support burden.

## Open Questions
- Initial package format and build backend choice for first-party components.
- First release cadence (nightly/beta/stable timing) and channel policy.
- Secure Boot enrollment strategy for early public releases.

## Exit Criteria
- Overlay is no longer primary assembly primitive.
- Release image is produced from NM-OS package repository and image definitions.
- Installer, updates, and recovery pass release gates defined in this program.

## Fact / Inference / Assumption
- FACT: build scripts currently produce and verify overlay plus installer artifacts and an ISO.
- FACT: installer logic currently depends on Debian netinst and preseed.
- INFERENCE: Calamares path is prepared but not yet the active install path.
- ASSUMPTION: team wants to keep Python/GTK product stack while changing distro infrastructure.

