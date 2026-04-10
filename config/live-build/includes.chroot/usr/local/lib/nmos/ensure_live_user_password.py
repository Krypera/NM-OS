#!/usr/bin/env python3
from __future__ import annotations

import grp
import pwd
import secrets
import string
import subprocess
from pathlib import Path

from nmos_common.config_helpers import read_assignment_file
from nmos_common.runtime_state import write_runtime_text

LIVE_RUNTIME_USERNAME_CONFIG = Path("/etc/live/config.d/username.conf")
LIVE_RUNTIME_PASSWORD_CONFIG = Path("/etc/live/config.d/password.conf")
LIVE_DEFAULTS_CONFIG = Path("/etc/nmos/live-user.conf")
RUNTIME_PASSWORD_FILE = Path("/run/nmos/live-user-password")
RUNTIME_PASSWORD_GROUP = "Debian-gdm"
PASSWORD_ALPHABET = string.ascii_letters + string.digits
PASSWORD_LENGTH = 24


def resolve_live_username() -> str:
    defaults = read_assignment_file(LIVE_DEFAULTS_CONFIG)
    runtime_values = read_assignment_file(LIVE_RUNTIME_USERNAME_CONFIG)
    return runtime_values.get("LIVE_USERNAME") or defaults.get("LIVE_USERNAME") or "nmos"


def generate_live_password() -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_LENGTH))


def resolve_configured_password() -> str:
    defaults = read_assignment_file(LIVE_DEFAULTS_CONFIG)
    runtime_values = read_assignment_file(LIVE_RUNTIME_PASSWORD_CONFIG)
    return runtime_values.get("LIVE_PASSWORD") or defaults.get("LIVE_PASSWORD") or ""


def validate_credential_field(name: str, value: str) -> str:
    cleaned = str(value or "")
    if not cleaned:
        raise ValueError(f"{name} is empty")
    if ":" in cleaned or "\n" in cleaned or "\r" in cleaned:
        raise ValueError(f"{name} contains unsupported characters")
    return cleaned


def store_runtime_password(password: str) -> None:
    gid: int | None = None
    mode = 0o600
    try:
        getgrnam = getattr(grp, "getgrnam", None)
        if getgrnam is None:
            raise KeyError(RUNTIME_PASSWORD_GROUP)
        gid = getgrnam(RUNTIME_PASSWORD_GROUP).gr_gid
        mode = 0o640
    except KeyError:
        gid = None
    write_runtime_text(
        RUNTIME_PASSWORD_FILE,
        f"{password}\n",
        mode=mode,
        owner_uid=0,
        owner_gid=gid,
    )


def main() -> None:
    username = validate_credential_field("LIVE_USERNAME", resolve_live_username())
    configured_password = resolve_configured_password()
    if configured_password:
        password = validate_credential_field("LIVE_PASSWORD", configured_password)
    else:
        password = validate_credential_field("LIVE_PASSWORD", generate_live_password())
    try:
        getpwnam = getattr(pwd, "getpwnam", None)
        if getpwnam is None:
            raise RuntimeError("pwd.getpwnam is unavailable on this platform")
        getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(f"live user '{username}' does not exist") from exc
    subprocess.run(
        ["chpasswd"],
        input=f"{username}:{password}\n",
        text=True,
        check=True,
    )
    store_runtime_password(password)


if __name__ == "__main__":
    main()
