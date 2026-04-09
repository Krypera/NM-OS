# Runtime Notes

## Boot flow

1. USB boot menu sets `nmos.mode=<profile>` in kernel parameters
2. `nmos-boot-profile.service` normalizes the mode and writes `/run/nmos/boot-mode.json`
3. `nmos-live-user-password.service` assigns the live-session password before GDM starts the user login
4. `nmos-network-bootstrap.service` enforces mode-aware network policy
5. `nmos-persistent-storage.service` exposes the persistence D-Bus backend
6. the GDM welcome session starts `nmos-greeter` before the live desktop login
7. GDM `PostLogin` applies the chosen locale and keyboard settings from `/run/nmos/greeter-state.json`

The live-user password is generated per boot unless `LIVE_PASSWORD` is
explicitly configured. The generated password is written to
`/run/nmos/live-user-password` so the `Debian-gdm` greeter session can start
the live desktop login flow without a hardcoded repository secret.

## Disk safety defaults

The alpha image is configured to avoid mounting internal disks automatically.

- GNOME media automount is disabled
- internal non-USB block devices are hidden from UDisks by default
- persistence is created on the boot USB device only
- automatic persistence creation is only allowed on writable GPT USB layouts

This is meant to reduce accidental writes to the internal Windows disk during a
live session.

## Network gate

The alpha network policy is intentionally strict:

- loopback traffic is allowed
- established traffic is allowed
- DHCP, DNS, and NTP are allowed for bootstrap
- traffic from the `debian-tor` user is allowed
- all other outbound traffic is blocked until Tor bootstrap completes

When Tor reaches bootstrap readiness, NM-OS removes the temporary nftables
bootstrap table and marks the runtime as ready.

When Tor reaches 100% bootstrap, the runtime marks the session as ready by
creating `/run/nmos/network-ready` and starting `nmos-network-ready.target`.

The runtime also records status in:

- `/run/nmos/network-status.json`
- `/run/nmos/boot-mode.json`

The greeter "continue without network" option only bypasses UI readiness. It
still keeps user network traffic blocked until Tor reaches readiness and the
temporary firewall gate is removed.

This gives the greeter and smoke tests a stable place to read progress, timeout,
and failure information.

### Mode-aware behavior

- `strict`, `flexible`, `compat` run Tor bootstrap and keep the outbound gate until readiness.
- `offline` and `recovery` skip Tor bootstrap, keep networking disabled, and publish a
  disabled status phase in `/run/nmos/network-status.json`.
- invalid or missing `nmos.mode` values fail closed to `strict`.

## Persistence

The persistence backend is exposed on the system bus as:

- service: `org.nmos.PersistentStorage`
- path: `/org/nmos/PersistentStorage`
- interface: `org.nmos.PersistentStorage`

Methods:

- `Create(passphrase)`
- `Unlock(passphrase)`
- `Lock()`
- `Repair()`
- `GetState()`

`GetState()` also reports:

- `boot_device_supported`
- `can_create`
- `reason`
- `device`

The storage backend is designed for a single LUKS2 volume mounted at:

- `/live/persistence/nmos-data`

## Optional Brave support

NM-OS can optionally include Brave Browser at build time.

- this is disabled by default
- this is intended as a privacy-focused browser option
- this is not equivalent to Tor Browser anonymity guarantees
- when Brave is included, the launcher is only shown in `flexible` mode
