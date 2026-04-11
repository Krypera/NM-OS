# NM-OS Independence Program

## Purpose
This program defines how NM-OS moves from a Debian-netinst-plus-overlay alpha into an independent Linux distribution with its own build, installer, packaging, update, trust, and release lifecycle.

## NM-OS Today (short)
- Build outputs are an installed-system overlay, installer assets, and a bootable installer ISO.
- The ISO is currently produced by remixing Debian netinst media and injecting NM-OS preseed plus overlay payload.
- Core product logic exists in first-party Python components and system-overlay integration scripts.

Repo evidence:
- `build/build.sh`
- `build/lib/common.sh`
- `config/installer/debian-installer/preseed/nmos.cfg.in`
- `config/installer/debian-installer/preseed/install-overlay.sh.in`
- `config/installer/calamares/settings.conf`
- `apps/`

## Target State (short)
- NM-OS owns a package-first distro pipeline:
  - first-party package repository and metadata
  - image definitions and reproducible rootfs/image assembly
  - installer owned by NM-OS product requirements
  - signed update channels and recovery strategy
- Product logic is cleanly separated from distro infrastructure so platform changes do not require app rewrites.

## Recommended Reading Order
1. [00-goal-and-adr.md](./00-goal-and-adr.md)
2. [01-debian-dependency-inventory.md](./01-debian-dependency-inventory.md)
3. [02-modular-architecture.md](./02-modular-architecture.md)
4. [03-packaging-strategy.md](./03-packaging-strategy.md)
5. [04-image-build-architecture.md](./04-image-build-architecture.md)
6. [10-qa-release-gates.md](./10-qa-release-gates.md)
7. [11-roadmap-12-months.md](./11-roadmap-12-months.md)
8. [12-first-sprint.md](./12-first-sprint.md)
9. [05-installer-redesign.md](./05-installer-redesign.md)
10. [06-update-release-architecture.md](./06-update-release-architecture.md)
11. [07-security-trust-chain.md](./07-security-trust-chain.md)
12. [08-hardware-validation-roadmap.md](./08-hardware-validation-roadmap.md)
13. [09-recovery-supportability.md](./09-recovery-supportability.md)

## Critical Path
1. Freeze boundaries between portable product core and distro adapter layer.
2. Convert overlay staging assumptions into package boundaries.
3. Add package repository and signing baseline.
4. Build image pipeline from package manifests, not injected tar overlays.
5. Replace Debian-installer preseed path with NM-OS controlled installer flow.
6. Introduce release channels with upgrade and recovery gates.

## Scope Guardrails
- Not in scope: writing a kernel, replacing Linux, giant immediate refactor.
- In scope: incremental architecture and tooling evolution from current repository state.

## Fact / Inference / Assumption
- FACT: Current build path resolves Debian netinst and patches installer menus in `build/lib/common.sh`.
- FACT: Current CI includes `smoke`, `build-smoke`, and `windows-smoke` jobs in `.github/workflows/smoke.yml`.
- INFERENCE: Current Calamares files are scaffolding, while active installation path is Debian-installer preseed.
- ASSUMPTION: NM-OS intends long-term independent branding and release ownership rather than remaining a remix forever.

