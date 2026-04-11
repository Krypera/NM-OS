# Security Settings

NM-OS now treats security as a spectrum instead of a boot-only mode switch.

The current alpha ships four presets:

## `Relaxed`

- direct networking by default
- broadest comfort profile
- lighter sandbox expectations
- best when ease of use matters more than stricter defaults

## `Balanced`

- default NM-OS profile
- Tor-first networking by default
- moderate friction
- recommended starting point for most users

## `Hardened`

- tighter sandbox and device defaults
- reduced motion and denser UI defaults
- stronger posture for daily use with less convenience

## `Maximum`

- offline by default
- strict device and logging posture
- strongest practical baseline in the current product slice

## Overrides

Every preset can be customized with per-setting overrides.

Current override surfaces include:

- language and keyboard
- network policy
- Brave visibility
- sandbox default
- vault preferences
- device policy
- logging policy
- theme profile, accent, density, and motion

## Pending reboot behavior

Some changes can apply immediately.

Some changes are tracked in `pending_reboot`, especially:

- `network_policy`
- `sandbox_default`
- `device_policy`
- `logging_policy`

This is why both the greeter summary and the control center show reboot hints.

## Current limits

- presets do not yet map to full per-app permission editing
- the current alpha does not claim amnesic guarantees
- the visual theme is curated and intentionally limited, not a full theme editor
