# Runtime Notes

## Service flow

1. `nmos-settings-bootstrap.service` mirrors `/var/lib/nmos/system-settings.json` into `/run/nmos/system-settings.json`
2. `nmos-network-bootstrap.service` enforces the selected network policy
3. `nmos-persistent-storage.service` exposes the encrypted vault D-Bus backend
4. the GDM greeter session starts `nmos-greeter` as the setup assistant
5. GDM `PostLogin` applies the chosen locale and keyboard settings from `/run/nmos/greeter-state.json`

## Settings model

The canonical settings file is:

- `/var/lib/nmos/system-settings.json`

The runtime mirror is:

- `/run/nmos/system-settings.json`

The current alpha supports:

- `network_policy=tor`
- `network_policy=direct`
- `network_policy=offline`
- `allow_brave_browser=true|false`

## Network policy

### `tor`

- starts Tor bootstrap
- keeps the temporary nftables gate until Tor is ready
- writes status to `/run/nmos/network-status.json`

### `direct`

- removes the temporary gate
- marks networking ready immediately
- still publishes runtime status for the setup assistant

### `offline`

- applies an offline-only nftables policy
- does not start Tor bootstrap
- reports a disabled network phase in `/run/nmos/network-status.json`

## Encrypted vault

The storage backend is exposed on the system bus as:

- service: `org.nmos.PersistentStorage`
- path: `/org/nmos/PersistentStorage`
- interface: `org.nmos.PersistentStorage`

Methods:

- `Create(passphrase)`
- `Unlock(passphrase)`
- `Lock()`
- `Repair()`
- `GetState()`

The backend manages:

- image file: `/var/lib/nmos/storage/vault.img`
- mapper: `/dev/mapper/nmos-vault`
- mount point: `/var/lib/nmos/storage/mnt`

## Optional Brave support

NM-OS can optionally enable Brave-aware runtime policy at build time.

- this is disabled by default
- launcher visibility still depends on the user setting
- Brave is blocked when networking is set to `offline`
- Brave is privacy-focused but not equivalent to Tor Browser anonymity
