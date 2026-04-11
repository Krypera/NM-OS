# Windows + WSL2 Workflow

NM-OS is developed on Windows, but the overlay build runs inside WSL2.

## What runs where

- Edit code on Windows
- Run build commands from PowerShell
- Let WSL2 execute the Linux overlay build
- Review the generated `.tar.gz` overlay and package manifest from Windows
- Apply that overlay to a Debian-based test VM, image, or staging system

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

- `dist\nmos-system-overlay-<version>.tar.gz`

If you want the optional Brave-aware overlay:

```powershell
.\build\build.ps1 -EnableBrave
```

## Apply Or Inspect

Typical next steps are:

1. open the generated `*.packages` file
2. prepare a Debian-based VM or disk image
3. install the listed packages
4. extract the overlay onto the target root filesystem
5. reload systemd and reboot
