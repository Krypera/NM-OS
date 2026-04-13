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
5. `nmos-app-isolation-policy.service`
   enforces the selected `sandbox_default` as a global Flatpak baseline override
6. `nmos-device-policy.service`
   enforces the selected `device_policy` baseline for removable USB storage trust
7. the GDM greeter session launches `nmos-greeter`
8. after login, the desktop can use `nmos-control-center`
9. the desktop autostart helper applies the selected wallpaper, color scheme, motion, density, and Brave visibility policy
10. optional platform adapter overrides can be declared in `/etc/nmos/platform-adapter.env`
11. runtime values are resolved from process env first (`NMOS_TOR_USER`, `NMOS_GDM_USER`, `NMOS_SETTINGS_ADMIN_GROUP`, `NMOS_RUNTIME_DIR`, `NMOS_STATE_DIR`) and then from `/etc/nmos/platform-adapter.env`
12. static D-Bus, tmpfiles, and systemd write-path entries are rendered during build from platform adapter values

## Settings model

Persistent source of truth:

- `<state_dir>/system-settings.json` (default `/var/lib/nmos/system-settings.json`)

Runtime mirror:

- `<runtime_dir>/system-settings.json` (default `/run/nmos/system-settings.json`)

Boot-applied snapshot:

- `<runtime_dir>/applied-system-settings.json` (default `/run/nmos/applied-system-settings.json`)

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
- `default_browser`
- `pending_reboot`

## D-Bus services

### Settings

- service: `org.nmos.Settings1`
- path: `/org/nmos/Settings1`
- interfaces:
- `org.nmos.Settings1.Read`
- `org.nmos.Settings1.Write`

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

Client behavior:

- `SettingsClient` is D-Bus first by default and does not silently downgrade to local writes
- emergency local fallback requires `NMOS_ALLOW_LOCAL_SETTINGS_FALLBACK=1` and only applies to retriable transport failures

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
- resolves the Tor service user through platform adapter values (`NMOS_TOR_USER`) before applying uid-bound rules

### `direct`

- removes the temporary gate
- marks networking ready immediately

### `offline`

- applies an offline-only nftables policy
- skips Tor bootstrap

## Desktop surfaces

Greeter:

- onboarding for language, keyboard, profile, network, browser, and appearance
- greeter state and network watcher paths resolve from platform adapter runtime directory

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
- default browser preference is applied through desktop defaults/`xdg-settings`
- Brave visibility stays aligned with the selected network and browser policy
