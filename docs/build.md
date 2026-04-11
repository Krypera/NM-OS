# Build Notes

## Host requirements

- Linux build host or WSL2
- `rsync`
- `tar`
- `gzip`
- `sha256sum`

## What the build publishes

The current build is still overlay-first, but it now emits installer scaffolding too.

Artifacts in `dist/`:

- `nmos-system-overlay-<version>.tar.gz`
- `nmos-system-overlay-<version>.sha256`
- `nmos-system-overlay-<version>.packages`
- `nmos-system-overlay-<version>.build-manifest`
- `nmos-installer-assets-<version>.tar.gz`
- `nmos-installer-assets-<version>.sha256`
- `nmos-installer-assets-<version>.packages`

## What gets staged

Runtime overlay:

- `config/system-overlay/`
- first-party Python packages in `apps/`
- shared theme assets under `/usr/share/nmos/theme`
- systemd units for settings, network bootstrap, vault, and boot marker flows

Installer assets:

- `config/installer/calamares/`
- `config/installer-packages/`

## Entry points

### Windows + WSL2

```powershell
.\build\install-deps.ps1
.\build\build.ps1
```

Optional Brave-aware overlay:

```powershell
.\build\build.ps1 -EnableBrave
```

### Linux / WSL2 direct

```bash
./build/build.sh
```

Optional Brave-aware overlay:

```bash
NMOS_ENABLE_BRAVE=1 ./build/build.sh
```

## Verification

Before a build:

```bash
./tests/smoke/verify-structure.sh
./tests/smoke/verify-python.sh
./tests/smoke/verify-quality-tooling.sh
./tests/smoke/verify-build-hygiene.sh
./tests/smoke/verify-version-policy.sh
./tests/smoke/verify-settings-model.sh
./tests/smoke/verify-control-center.sh
./tests/smoke/verify-network-policy.sh
./tests/smoke/verify-prelogin-wiring.sh
./tests/smoke/verify-vault-storage.sh
./tests/smoke/verify-runtime-logic.sh
./tests/smoke/verify-leaks.sh
```

After a build:

```bash
./tests/smoke/verify-artifacts.sh
./build/smoke-overlay.sh
```
