# Build Notes

## Host requirements

- Linux build host
- `live-build`
- `debootstrap`
- `rsync`
- `xorriso`
- `sha256sum`
- `qemu-system-x86_64`

## Windows entry point

From PowerShell:

```powershell
.\build\install-deps.ps1
.\build\build.ps1
```

## Linux / WSL2 entry point

Use:

```bash
./build/build.sh
```

This script:

1. verifies repo hygiene
2. stages a temporary live-build tree under `.build/live-build`
3. copies first-party applications into the image source tree
4. rejects staged `__pycache__`, `.pyc`, and `.pyo` artifacts
5. runs `lb config` and `lb build`
6. publishes both `.img` and `.iso` images, plus package manifest, checksum,
   and build manifest into `dist/`

The published `.img` is the same `iso-hybrid` payload as the `.iso`. NM-OS
only advertises automatic persistence creation when the running USB exposes a
supported writable GPT or DOS layout with safe trailing free space.

## Staged sources

The build script copies:

- `config/live-build/` into the working live-build tree
- `hooks/live/` into `config/hooks/live/`
- `apps/` into `config/includes.chroot/usr/src/nmos/apps/`

The chroot hooks then install the runtime pieces into their final locations.

## Published artifacts

- `nmos-amd64-<version>.img`
- `nmos-amd64-<version>.iso`
- `nmos-amd64-<version>.sha256`
- `nmos-amd64-<version>.packages`
- `nmos-amd64-<version>.build-manifest`

## Verification

Before a build:

```bash
./tests/smoke/verify-structure.sh
./tests/smoke/verify-python.sh
./tests/smoke/verify-build-hygiene.sh
./tests/smoke/verify-greeter-state.sh
./tests/smoke/verify-live-login-config.sh
./tests/smoke/verify-network-gate-transition.sh
./tests/smoke/verify-prelogin-wiring.sh
./tests/smoke/verify-persistence-state-machine.sh
./tests/smoke/verify-runtime-logic.sh
./tests/smoke/verify-disk-safety.sh
./tests/smoke/verify-leaks.sh
```

After a build:

```bash
./tests/smoke/verify-artifacts.sh
./build/smoke-qemu.sh
```
