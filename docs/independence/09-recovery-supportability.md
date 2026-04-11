# 09 Recovery Supportability

## Purpose
Define how NM-OS recovers from failures across boot, settings, network, vault, install, and update flows.

## Current State
- Current repo has runtime state files, settings bootstrap, network bootstrap, and vault service flows.
- Recovery behavior is mostly implicit; no dedicated end-user recovery mode spec exists yet.

## Evidence From Repo
- `config/system-overlay/usr/local/lib/nmos/settings_bootstrap.py`
- `config/system-overlay/usr/local/lib/nmos/network_bootstrap.py`
- `apps/nmos_persistent_storage/nmos_persistent_storage/storage.py`
- `config/system-overlay/usr/lib/systemd/system/*`
- `docs/runtime.md`

## Failure Classes and Required Recovery
- Boot failures:
  - provide recovery boot entry and safe defaults boot path.
- Settings failures:
  - reset to active preset and optional full settings reset.
- Network failures:
  - emergency direct/offline fallback with clear status.
- Vault failures:
  - explicit lock/unlock/repair flow with diagnostics.
- Install/update failures:
  - rollback boot path and recovery image handoff.

## Recommended Recovery Features
- Safe mode:
  - starts minimal services and bypasses non-critical customizations.
- Recovery boot:
  - dedicated image/entry with repair tools and logs access.
- Config reset:
  - reset only problematic settings domains first, then full reset option.
- Vault repair:
  - guided repair sequence wrapping existing backend operations.
- Network recovery:
  - quick switch among `tor/direct/offline` with persistent status feedback.
- Diagnostic bundle:
  - package relevant logs/status snapshots for support triage.
- Support workflow:
  - issue template requiring bundle ID, version, and hardware profile.

## Migration Steps
1. Define recovery metadata schema and locations.
2. Add system service for collecting minimal diagnostics.
3. Add Control Center "Recovery" actions mapped to safe operations.
4. Add installer option for creating/repairing recovery boot entry.

## Alternatives Considered
1. Manual support only:
   - slow and error-prone.
2. full auto-recovery immediately:
   - too risky without mature gates.
3. staged explicit recovery tooling:
   - recommended.

## Risks
- Incorrect reset behavior can hide root cause or break user setup.
- Vault repair misuse can risk data loss without clear warnings.

## Open Questions
- How recovery image is versioned against installed system.
- What minimum tooling is shipped in recovery environment.

## Exit Criteria
- Recovery procedures are documented, tested, and reachable from installer and installed system.
- Support diagnostics are standardized and reproducible.

## Fact / Inference / Assumption
- FACT: settings and network bootstrap scripts already maintain runtime status artifacts.
- FACT: persistent storage service already exposes `Repair`.
- INFERENCE: recovery UX can be layered on existing service capabilities.
- ASSUMPTION: a dedicated recovery image is acceptable within release artifact budget.

