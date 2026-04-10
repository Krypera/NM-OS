# Security Profiles

NM-OS boot modes are security profiles selected at boot time. They are not
simple UI toggles after login.

## Profile summary

- `Strict`:
  - default profile
  - Tor-first network gate
  - highest privacy baseline in the current alpha
- `Flexible`:
  - still Tor-first
  - allows a more relaxed greeter flow
  - optional Brave support can run only in this mode
- `Offline`:
  - network intentionally disabled
  - no Tor bootstrap
- `Recovery`:
  - persistence/recovery-first flow
  - network intentionally disabled
- `Hardware Compatibility`:
  - strict runtime network posture
  - compatibility-oriented boot parameters (`nomodeset`)

## Runtime contract

- Bootloader writes `nmos.mode=<profile>` in kernel parameters.
- `nmos-boot-profile.service` normalizes this into `/run/nmos/boot-mode.json`.
- Runtime services and greeter behavior must read that file as the canonical
  mode source.
- Invalid or missing mode values fail closed to `strict`.

## Browser policy in alpha

- Tor-first profiles (`strict`, `flexible`, `compat`) keep user traffic blocked
  until Tor readiness.
- Brave is optional at build time.
- If Brave is included, launcher visibility and runtime binary policy both
  restrict use to `flexible` mode.
- This does not make Brave equivalent to Tor Browser anonymity guarantees.

## Current limits

- The alpha does not claim full amnesic guarantees.
- Internal-disk installer and updater are out of scope.
- Profile behavior is enforced through runtime policy and service wiring; final
  release-level guarantees still require hardware validation.
