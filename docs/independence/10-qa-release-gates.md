# 10 QA Release Gates

## Purpose
Define release-grade QA gates by mapping current repository tests and adding missing layers required for an independent distro lifecycle.

## Current State
Current QA already includes:
- static quality checks (`ruff`, `mypy`, `shellcheck`)
- Python tests (`tests/python`)
- broad smoke suite (`tests/smoke`)
- CI jobs for Linux smoke/build and Windows wrapper checks

## Evidence From Repo
- `.github/workflows/smoke.yml`
- `tests/python/test_compile_sources.py`
- `tests/python/test_runtime_logic.py`
- `tests/smoke/verify-*.sh`
- `pyproject.toml`

## Existing Coverage Map
- Static checks:
  - `tests/smoke/verify-quality-tooling.sh`
- Structure and policy checks:
  - `verify-structure.sh`, `verify-version-policy.sh`, `verify-build-hygiene.sh`
- Product/runtime smoke:
  - `verify-settings-model.sh`
  - `verify-control-center.sh`
  - `verify-greeter-state.sh`
  - `verify-greeter-i18n.sh`
  - `verify-network-policy.sh`
  - `verify-prelogin-wiring.sh`
  - `verify-vault-storage.sh`
  - `verify-runtime-logic.sh`
  - `verify-systemd-hardening.sh`
- Build/install media checks:
  - `verify-installer-media.sh`
  - `verify-artifacts.sh`
  - `build/smoke-overlay.sh`
- Platform wrapper checks:
  - `verify-windows-wsl-bridge.ps1`

## Missing Layers
- Package build tests (per package install/upgrade/remove behavior)
- Image boot tests in virtualized matrix (BIOS/UEFI, secure settings)
- Installer end-to-end tests with assertion checkpoints
- Upgrade tests (n-1 to n, channel migrations)
- Recovery tests (safe mode, rollback, diagnostics)
- Hardware smoke tests (official support matrix)

## Gate Model
## Per Commit (required)
- lint/type/unit/smoke gates (current + incremental additions)
- installer media structure checks
- artifact integrity checks
- no regression in D-Bus/service contracts

## Nightly (required)
- full image build and boot in VM matrix
- installer unattended flow smoke
- update simulation within nightly channel
- recovery smoke scenarios

## Release Candidate (required)
- full installer E2E with profile/vault/network assertions
- upgrade path tests from previous stable and previous beta
- recovery drills and rollback tests
- hardware matrix smoke pass threshold
- signed artifact verification checks

## Release Gate Checklist
- Code Quality
  - `ruff`, `mypy`, `shellcheck`, python tests pass
- Build Integrity
  - overlay/assets/ISO artifacts present and verified
- Installer Integrity
  - boot menu entries and payload embedding verified
- Runtime Contracts
  - `org.nmos.Settings1` and `org.nmos.PersistentStorage` smoke checks pass
- Security Baseline
  - systemd hardening and runtime write-safety checks pass
- i18n Baseline
  - supported locale checks pass
- Channel/Update Integrity (future gate)
  - signed metadata verified
- Recovery Integrity (future gate)
  - rollback/recovery scenarios pass
- Hardware Baseline (future gate)
  - official matrix pass threshold met

## Recommended CI Evolution
1. Keep current `smoke` workflow stable as base gate.
2. Add `nightly-image-validation.yml` for heavier VM scenarios.
3. Add `release-candidate.yml` with upgrade/recovery/hardware gate aggregation.
4. Add artifact-signature verification job once signing is introduced.

## Alternatives Considered
1. Keep only current smoke:
   - insufficient for release lifecycle.
2. Add all gates immediately:
   - high implementation load and noisy CI.
3. staged gate expansion by risk:
   - recommended.

## Risks
- CI runtime growth without prioritization.
- False confidence if gate definitions are broad but assertions are weak.

## Open Questions
- Which emulator stack to standardize for nightly installer tests.
- How to source and schedule hardware matrix runs.

## Exit Criteria
- Per-commit, nightly, and RC workflows are separated with explicit pass criteria.
- Stable release requires RC gate approval checklist completion.

## Fact / Inference / Assumption
- FACT: current CI already runs broad smoke and build validation.
- FACT: quality and typing checks are enforced in repo scripts.
- INFERENCE: release robustness now depends more on missing upgrade/recovery/hardware gates than on static checks.
- ASSUMPTION: team can support longer nightly/RC jobs while keeping per-commit fast.

