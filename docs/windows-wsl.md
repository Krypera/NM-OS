# Windows + WSL2 Workflow

NM-OS is developed on Windows, but built inside WSL2.

## What runs where

- Edit code on Windows
- Run build commands from PowerShell
- Let WSL2 execute the Linux build
- Write the generated `.img` to a USB stick from Windows
- Boot the computer from that USB stick to run NM-OS
- Complete the GDM welcome flow before entering the live desktop

## First setup

1. Install WSL2 and a Debian or Ubuntu distribution.
2. Open PowerShell in the repository root.
3. Run:

```powershell
.\build\install-deps.ps1
```

If you want a specific distro:

```powershell
.\build\install-deps.ps1 -Distro Ubuntu
```

## Build

From PowerShell:

```powershell
.\build\build.ps1
```

The primary output for Windows testing is:

- `dist\nmos-amd64-<version>.img`

## USB testing

1. Open Rufus on Windows.
2. Select the generated `.img` file.
3. Write it to a USB stick.
4. Reboot the computer and choose the USB device from the boot menu.
5. NM-OS should start from the USB stick instead of Windows.

When you shut down NM-OS and boot normally from your internal drive, Windows
should continue as usual.
