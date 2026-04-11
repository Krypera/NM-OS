# 08 Hardware Validation Roadmap

## Purpose
Define realistic hardware validation strategy for early independent NM-OS releases.

## Current State
- CI currently validates static checks, smoke logic, build artifacts, and Windows wrapper checks.
- No repository evidence of full hardware lab automation yet.
- VM-focused install/test flow is documented.

## Evidence From Repo
- `.github/workflows/smoke.yml`
- `tests/smoke/*`
- `docs/installation.md`
- `docs/windows-wsl.md`

## Target State
Credible staged support matrix:
- transparent "officially supported" baseline
- broader "best effort" compatibility tier
- reproducible hardware smoke and issue triage workflow

## Early Official Support Matrix (recommended)
Release 0.x official baseline:
- x86_64 UEFI systems
- Intel/AMD integrated graphics (non-proprietary baseline path)
- wired Ethernet
- common Intel Wi-Fi chipsets
- standard laptop keyboard/touchpad
- single-monitor and dual-monitor mainstream setups

Best effort tier:
- NVIDIA proprietary stack
- uncommon Wi-Fi/Bluetooth chipsets
- advanced docking station paths
- unusual firmware edge cases

## Validation Domains and Tests
- Wi-Fi:
  - scan/connect/reconnect, suspend/resume network recovery
- Ethernet:
  - DHCP and static route behavior
- Bluetooth:
  - adapter enable/pair/connect basic audio/input devices
- GPU:
  - boot/display integrity, session stability, external monitor handling
- Audio:
  - output and microphone baseline checks
- Input:
  - touchpad gestures, keyboard layout switching
- Multi-monitor:
  - hotplug, resolution switching, session persistence
- Suspend/resume:
  - network and session restoration
- Firmware/UEFI:
  - installer boot, installed boot, recovery entry visibility

## Execution Plan
1. Virtualized nightly smoke remains mandatory.
2. Weekly physical-hardware smoke on small matrix.
3. Release-candidate sweep on expanded matrix.
4. Publish support matrix and known limitations per release.

## Alternatives Considered
1. Claim broad hardware support early:
   - high support risk.
2. Overly narrow single-device support:
   - limits adoption and feedback quality.
3. narrow-credible matrix with growth policy:
   - recommended.

## Risks
- Driver regressions across kernel updates.
- Support load spikes if matrix communication is unclear.

## Open Questions
- Budget and ownership for hardware pool.
- Community hardware reporting format and triage SLA.

## Exit Criteria
- Support matrix document exists and is versioned per release.
- RC gate includes pass rate threshold across official matrix.

## Fact / Inference / Assumption
- FACT: current CI does not yet include physical hardware jobs.
- FACT: current docs prioritize VM install flow.
- INFERENCE: early hardware strategy should be explicit to avoid overpromising.
- ASSUMPTION: first independent releases remain x86_64-focused.

