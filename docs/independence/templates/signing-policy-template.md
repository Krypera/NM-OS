# Signing Policy Template

## Scope
- package repository metadata
- ISO artifacts
- release manifests

## Key Types
- repository metadata key
- image/release signing key
- revocation/emergency key

## Operations
- key generation procedure:
- key storage location:
- rotation frequency:
- compromise response:

## Verification Requirements
- CI must verify signatures before promotion to beta/stable.
- release notes must include key ID and verification steps.

