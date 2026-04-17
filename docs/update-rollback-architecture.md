# Update And Rollback Architecture

This document defines the NM-OS update and rollback model as a release-gated architecture.

## Scope

- update channel selection (`stable`, `beta`, `nightly`)
- update metadata verification (`release-manifest.json`, `update-catalog.json`)
- rollback expectations and operator workflow
- failure handling policy for interrupted or invalid updates

## Atomic Strategy Decision

NM-OS currently uses a **metadata-first staged apply** strategy:

1. Control Center validates update metadata for the selected channel.
2. The new target version is recorded in runtime update state.
3. Package rollout and reboot validation happen as explicit follow-up steps.

This is not full image-level A/B swapping yet. The release gate requires that the strategy is explicit and test-covered.

## Signed Artifact And Manifest Requirements

Release metadata must provide:

- installer artifact identity
- checksum/signature mode
- build/channel/version metadata
- rollback capability signal

Minimum required files:

- `dist/release-manifest.json`
- `dist/update-catalog.json`

Verification rules:

- metadata format and required keys must pass CI checks
- checksum/signature mode must be present and readable
- trust-chain status must be user-visible from Control Center

## Rollback UX And State

Rollback is modeled as an explicit user action:

1. Update history tracks `from` and `to` versions.
2. Rollback action restores previous version metadata intent.
3. Operator reboots and validates actual package/image state.

Control Center must surface:

- active channel and installed version
- last action (check/apply/rollback)
- rollback availability based on history

## Failure Recovery UX

If update apply fails or metadata is invalid:

- keep current installed version as authoritative
- preserve rollback history without destructive rewrites
- surface failure guidance in Control Center status text
- require explicit operator retry instead of silent background mutation

If rollback cannot proceed:

- keep existing update state unchanged
- show actionable diagnostics guidance

## Release Gate Checklist

Every release must satisfy all of the following:

1. Architecture doc exists and stays aligned with implementation.
2. Update metadata files are generated and verified in CI.
3. Control Center exposes update + rollback state and actions.
4. Rollback path is test-covered.
5. Trust-chain metadata and verification status are visible.
