# USB Boot Checklist

## Before writing the USB stick

- build completed in WSL2
- `dist\nmos-amd64-<version>.img` exists
- checksum file exists
- target USB stick does not contain data you need

## First boot checks

- system boots from USB, not from the internal Windows drive
- boot menu shows `Strict`, `Flexible`, `Offline`, `Recovery`, and `Hardware Compatibility` entries
- selected boot mode appears in the greeter header
- GDM welcome screen appears before the desktop session starts
- greeter window appears in that welcome session
- network page shows Tor bootstrap progress in `strict/flexible/compat`
- `offline/recovery` show an intentional offline state instead of a Tor error
- internal Windows partitions do not auto-mount in the desktop
- persistence page can create or unlock the USB persistence volume

## After shutdown

- remove the USB stick
- boot the computer normally
- Windows starts from the internal disk
- normal Windows files are still present

## If the system boots into Windows instead

- re-open the motherboard or laptop boot menu
- explicitly pick the USB device
- if needed, disable Fast Startup in Windows and retry
