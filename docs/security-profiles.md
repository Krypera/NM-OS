# Security Settings

NM-OS no longer relies on boot-time profile selection.

The installed system keeps its privacy posture in a persistent settings file and exposes those choices through the setup assistant.

## Current settings

- `network_policy=tor`
  - default setting
  - Tor-first network gate
  - strongest privacy baseline in the current alpha
- `network_policy=direct`
  - allows normal outbound networking
  - still keeps the same setup assistant and vault model
- `network_policy=offline`
  - disables networking intentionally
  - skips Tor bootstrap
- `allow_brave_browser=true|false`
  - only relevant when the build enables Brave support
  - hidden by default

## Runtime contract

- `/var/lib/nmos/system-settings.json` is the persistent source of truth
- `/run/nmos/system-settings.json` is the runtime mirror
- runtime services must read the settings file, not kernel boot parameters
- missing or invalid settings fail closed to the default Tor-first policy

## Browser policy in alpha

- Tor-first keeps the temporary network gate until Tor readiness
- Direct mode removes the gate immediately
- Offline mode keeps networking disabled
- Brave is optional at build time and optional again at runtime
- This does not make Brave equivalent to Tor Browser anonymity guarantees

## Current limits

- the alpha does not claim full amnesic guarantees
- the repo does not yet ship a full installer image
- release-level guarantees still require hardware and deployment validation
