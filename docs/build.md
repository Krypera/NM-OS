# Build Notes

## Host requirements

- Linux build host
- `rsync`
- `tar`
- `gzip`
- `sha256sum`

## Line endings

The repository uses `.gitattributes` to keep Linux runtime scripts (`.sh`, `.py`) as LF and PowerShell scripts (`.ps1`) as CRLF.

This avoids WSL shebang failures and keeps overlay files deterministic.

## Windows entry point

From PowerShell:

```powershell
.\build\install-deps.ps1
.\build\build.ps1
```

To build an overlay that enables the optional Brave runtime flag:

```powershell
.\build\build.ps1 -EnableBrave
```

## Linux / WSL2 entry point

Use:

```bash
./build/build.sh
```

This script:

1. verifies repo hygiene
2. validates `config/version` format
3. stages a temporary system overlay tree under `.build/system-overlay/rootfs`
4. copies first-party Python applications into `/usr/lib/python3/dist-packages`
5. rejects staged `__pycache__`, `.pyc`, and `.pyo` artifacts
6. writes build metadata into `/usr/share/nmos/build-info`
7. enables NM-OS systemd units in the staged tree
8. publishes a compressed overlay archive plus checksum, package list, and build manifest into `dist/`

When `NMOS_ENABLE_BRAVE=1` is used, the build also stages `/etc/nmos/features/brave` and records `features=brave` in the build manifest.

## Staged sources

The build stages:

- `config/system-overlay/` into the target rootfs
- `apps/nmos_common/nmos_common` into `/usr/lib/python3/dist-packages`
- `apps/nmos_greeter/nmos_greeter` into `/usr/lib/python3/dist-packages`
- `apps/nmos_persistent_storage/nmos_persistent_storage` into `/usr/lib/python3/dist-packages`

## Published artifacts

- `nmos-system-overlay-<version>.tar.gz`
- `nmos-system-overlay-<version>.sha256`
- `nmos-system-overlay-<version>.packages`
- `nmos-system-overlay-<version>.build-manifest`

## Verification

Before a build:

```bash
./tests/smoke/verify-structure.sh
./tests/smoke/verify-python.sh
./tests/smoke/verify-quality-tooling.sh
./tests/smoke/verify-build-hygiene.sh
./tests/smoke/verify-version-policy.sh
./tests/smoke/verify-settings-model.sh
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
