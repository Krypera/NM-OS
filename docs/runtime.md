# Runtime Notes

## Main services

1. `nmos-settings.service`
   exposes `org.nmos.Settings1`
2. `nmos-settings-bootstrap.service`
   mirrors current settings into `/run/nmos/system-settings.json`
   and snapshots boot-applied values into `/run/nmos/applied-system-settings.json`
3. `nmos-network-bootstrap.service`
   enforces the selected network policy
4. `nmos-persistent-storage.service`
   exposes the encrypted vault backend
5. the GDM greeter session launches `nmos-greeter`
6. after login, the desktop can use `nmos-control-center`
7. the desktop autostart helper applies the selected wallpaper, color scheme, motion, density, and Brave visibility policy

## Settings model

Persistent source of truth:

- `/var/lib/nmos/system-settings.json`

Runtime mirror:

- `/run/nmos/system-settings.json`

Boot-applied snapshot:

- `/run/nmos/applied-system-settings.json`

Important top-level fields:

- `schema_version`
- `active_profile`
- `overrides`
- `network_policy`
- `allow_brave_browser`
- `sandbox_default`
- `vault`
- `device_policy`
- `logging_policy`
- `ui_theme_profile`
- `ui_accent`
- `ui_density`
- `ui_motion`
- `pending_reboot`

## D-Bus services

### Settings

- service: `org.nmos.Settings1`
- path: `/org/nmos/Settings1`
- interface: `org.nmos.Settings1`

Methods:

- `GetSettings()`
- `GetEffectiveSettings()`
- `ApplyPreset(profile)`
- `SetOverrides(map)`
- `ResetToPreset()`
- `GetPendingRebootChanges()`
- `Commit()`

Signal:

- `SettingsChanged`

### Encrypted vault

- service: `org.nmos.PersistentStorage`
- path: `/org/nmos/PersistentStorage`
- interface: `org.nmos.PersistentStorage`

Methods:

- `Create(passphrase)`
- `Unlock(passphrase)`
- `Lock()`
- `Repair()`
- `GetState()`

## Network policy

### `tor`

- keeps the nftables gate until Tor is ready
- writes runtime status to `/run/nmos/network-status.json`

### `direct`

- removes the temporary gate
- marks networking ready immediately

### `offline`

- applies an offline-only nftables policy
- skips Tor bootstrap

## Desktop surfaces

Greeter:

- onboarding for language, keyboard, profile, network, appearance, and vault

Control Center:

- profiles
- privacy and network
- apps and permissions
- vault preferences
- system and recovery
- language and region
- appearance

Desktop session sync:

- `config/system-overlay/etc/xdg/autostart/nmos-desktop-mode.desktop` launches the post-login policy helper
- the helper reads effective settings and mirrors the active look into `~/.config/nmos/session-appearance.json`
- theme profile selects a curated wallpaper and GNOME color scheme
- motion and density preferences are applied through `gsettings`
- Brave visibility stays aligned with the selected network and browser policy
