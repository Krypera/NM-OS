# 06 Update Release Architecture

## Purpose
Define update, channel, signing, and release lifecycle architecture starting from current version/artifact behavior.

## Current State
- Version source is `config/version` (`0.1.0-alpha.1` currently).
- Build emits multiple artifacts and a build manifest.
- CI publishes `dist/` artifact in `build-smoke`.
- No first-party package repository, channel policy, or rollback protocol yet.

## Evidence From Repo
- `config/version`
- `build/build.sh` (build manifest content, artifact naming)
- `build/verify-artifacts.sh`
- `.github/workflows/smoke.yml`
- `docs/build.md`

## Target State
- NM-OS package repository with signed metadata.
- Release channels:
  - nightly
  - beta
  - stable
- Signed release artifacts:
  - package metadata
  - ISO checksums/signatures
  - release manifest
- Upgrade and migration policy with rollback/recovery strategy.

## Recommended Channel Model
- `nightly`:
  - frequent integration, lower stability guarantees.
- `beta`:
  - release candidates and migration rehearsal.
- `stable`:
  - gated, support-backed releases only.

## Versioning Policy
- Keep SemVer-like format already enforced by `validate_version_format`.
- Extend manifest with:
  - channel
  - minimum upgrade source version
  - migration bundle ID
  - signing key ID

## Artifact and Metadata Model
For each release:
- signed package repository metadata
- signed image checksums
- signed release manifest with:
  - package set lock
  - image IDs and hashes
  - migration rules
  - recovery image link/hash

## Rollback and Recovery Policy
- Supported rollback scopes:
  - package set rollback within same major track
  - boot to recovery image for failed upgrade
- Mandatory:
  - preserve settings and vault state unless user opts to reset

## Alternatives Considered
1. ISO-only releases, no channelized updates:
   - poor lifecycle and security response agility.
2. Immediate full OTA system:
   - too large for current alpha stage.
3. Channelized repository + staged updater evolution:
   - recommended.

## Risks
- Key management mistakes can undermine trust chain.
- Upgrade path complexity can outpace support tooling.

## Open Questions
- UI location for update controls in Control Center.
- Migration policy for incompatible profile/setting schema changes.

## Exit Criteria
- Nightly/beta/stable channel metadata is generated and signed in CI.
- Stable release requires passing QA gates and migration tests.

## Fact / Inference / Assumption
- FACT: version format is already validated in build scripts and smoke checks.
- FACT: build manifest already carries installer and feature metadata fields.
- INFERENCE: existing manifest mechanism can evolve into release metadata.
- ASSUMPTION: APT-compatible repository path is likely first transition step before deeper package ecosystem changes.

