# 07 Security Trust Chain

## Purpose
Map current security posture and define future trust chain for independent NM-OS distribution lifecycle.

## Current State
Current repository already includes strong baseline controls:
- hardened runtime state writes (temp file, fsync, replace, no symlink-follow)
- systemd hardening options on core services
- artifact verification for generated outputs and ISO embedding correctness
- settings and storage D-Bus service boundaries
- Tor-first/offline network gate control

## Evidence From Repo
- `apps/nmos_common/nmos_common/runtime_state.py`
- `config/system-overlay/usr/lib/systemd/system/nmos-settings.service`
- `config/system-overlay/usr/lib/systemd/system/nmos-network-bootstrap.service`
- `config/system-overlay/usr/lib/systemd/system/nmos-persistent-storage.service`
- `build/verify-artifacts.sh`
- `config/system-overlay/etc/dbus-1/system.d/org.nmos.Settings1.conf`
- `config/system-overlay/etc/dbus-1/system.d/org.nmos.PersistentStorage.conf`
- `config/system-overlay/usr/local/lib/nmos/network_bootstrap.py`

## Trust Boundaries (current)
- Settings boundary:
  - `org.nmos.Settings1` controls system settings writes.
- Storage boundary:
  - `org.nmos.PersistentStorage` controls vault operations.
- Runtime state boundary:
  - `/run/nmos` and `/var/lib/nmos` with controlled ownership/permissions.
- Network policy boundary:
  - nftables gate and Tor bootstrap status.

## Threat Model Draft (high-level)
- Threats:
  - malicious local user/session tampering with runtime state
  - unauthorized D-Bus calls altering policy
  - artifact tampering in build/release pipeline
  - installer media substitution
  - update channel compromise
- Mitigations today:
  - state write hardening
  - D-Bus policy restrictions
  - service hardening and capability bounding
  - build artifact verification
- Missing future mitigations:
  - signed package repository metadata
  - signed ISO and release attestations
  - key rotation/compromise response playbook
  - Secure Boot ownership roadmap

## Future Trust Chain Design
1. Source and CI trust:
   - protected release workflow and signed tags.
2. Package trust:
   - repository metadata signing and verification.
3. Image trust:
   - detached signatures for ISO/checksum/release manifest.
4. Boot trust:
   - Secure Boot roadmap and signed boot artifacts.
5. Update trust:
   - channel-specific keys and anti-rollback policy.

## Key Handling Principles
- separate keys by function:
  - package metadata key
  - image/release signing key
  - emergency revocation key
- define rotation cadence and compromise drill procedures.

## Alternatives Considered
1. Keep checksum-only trust:
   - insufficient against metadata substitution.
2. Over-complex PKI immediately:
   - heavy operational burden for current stage.
3. staged signing and key governance:
   - recommended.

## Risks
- Operational key handling errors are more likely than cryptographic failures.
- Incomplete upgrade signature checks can create false confidence.

## Open Questions
- Key custody model (single maintainer vs threshold/team).
- Secure Boot enrollment strategy and hardware compatibility impact.

## Exit Criteria
- Every release artifact and package metadata set is signed and verifiable by documented workflow.
- Security gate in CI validates signature integrity before promotion to stable.

## Fact / Inference / Assumption
- FACT: runtime-state and service hardening controls are present in repository.
- FACT: artifact verification checks ISO payload consistency.
- INFERENCE: current trust model is strong for alpha internals but incomplete for public release lifecycle.
- ASSUMPTION: Secure Boot enablement is targeted after package/release signing baseline is stable.

