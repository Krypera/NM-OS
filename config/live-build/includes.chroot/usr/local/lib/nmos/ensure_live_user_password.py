#!/usr/bin/env python3
from __future__ import annotations

import pwd
import subprocess
from pathlib import Path


LIVE_RUNTIME_USERNAME_CONFIG = Path("/etc/live/config.d/username.conf")
LIVE_DEFAULTS_CONFIG = Path("/etc/nmos/live-user.conf")


def read_assignment_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def resolve_live_username() -> str:
    defaults = read_assignment_file(LIVE_DEFAULTS_CONFIG)
    runtime_values = read_assignment_file(LIVE_RUNTIME_USERNAME_CONFIG)
    return runtime_values.get("LIVE_USERNAME") or defaults.get("LIVE_USERNAME") or "nmos"


def resolve_live_password() -> str:
    defaults = read_assignment_file(LIVE_DEFAULTS_CONFIG)
    return defaults.get("LIVE_PASSWORD") or "live"


def validate_credential_field(name: str, value: str) -> str:
    cleaned = str(value or "")
    if not cleaned:
        raise ValueError(f"{name} is empty")
    if ":" in cleaned or "\n" in cleaned or "\r" in cleaned:
        raise ValueError(f"{name} contains unsupported characters")
    return cleaned


def main() -> None:
    username = validate_credential_field("LIVE_USERNAME", resolve_live_username())
    password = validate_credential_field("LIVE_PASSWORD", resolve_live_password())
    try:
        pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(f"live user '{username}' does not exist") from exc
    subprocess.run(
        ["chpasswd"],
        input=f"{username}:{password}\n",
        text=True,
        check=True,
    )


if __name__ == "__main__":
    main()
