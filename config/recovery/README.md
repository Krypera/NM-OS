# NM-OS Recovery Payload

This directory is packaged as the recovery image payload for NM-OS A/B update flows.

Current v1 contents:

- recovery diagnostics metadata
- rollback helper entrypoint
- update-engine state inspection notes
- diagnostics bundle generator
- detached manifest verification helper

Useful entrypoints:

- `./rollback-helper.sh`
- `./collect-diagnostics.py /tmp/nmos-recovery.json`
- `./verify-manifest.py /usr/share/nmos/release-manifest.json /usr/share/nmos/release-manifest.json.sig /usr/share/nmos/update-signing.gpg`

The real bootable recovery rootfs is still planned to evolve from this payload in later milestones, but this bundle is now directly usable from a recovery shell.
