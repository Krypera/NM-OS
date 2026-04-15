#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess

from nmos_common.platform_adapter import get_runtime_dir
from nmos_common.runtime_state import write_runtime_json
from nmos_common.system_settings import load_effective_system_settings

STATUS_FILE = get_runtime_dir() / "app-isolation-status.json"

POLICY_ARGS = {
    "standard": ["--filesystem=home"],
    "focused": ["--nofilesystem=host"],
    "strict": ["--nofilesystem=home", "--nofilesystem=host"],
}

APP_FILESYSTEM_ARGS = {
    "inherit": [],
    "home": ["--filesystem=home"],
    "documents": ["--filesystem=xdg-documents"],
    "host": ["--filesystem=host"],
    "none": ["--nofilesystem=home", "--nofilesystem=host", "--nofilesystem=xdg-documents"],
}
APP_NETWORK_ARGS = {
    "inherit": [],
    "shared": ["--share=network"],
    "isolated": ["--unshare=network"],
}
APP_DEVICE_ARGS = {
    "inherit": [],
    "all": ["--device=all"],
    "none": ["--nodevice=all"],
}


def policy_name(settings: dict) -> str:
    value = str(settings.get("sandbox_default", "focused")).strip().lower()
    if value in POLICY_ARGS:
        return value
    return "focused"


def app_overrides(settings: dict) -> dict[str, dict[str, str]]:
    raw = settings.get("app_overrides", {})
    if isinstance(raw, dict):
        return {
            str(app_id): config
            for app_id, config in raw.items()
            if isinstance(config, dict) and str(app_id).strip()
        }
    return {}


def policy_commands(profile: str, overrides: dict[str, dict[str, str]]) -> list[list[str]]:
    commands: list[list[str]] = [["flatpak", "override", "--system", "--reset"]]
    args = POLICY_ARGS.get(profile, POLICY_ARGS["focused"])
    if args:
        commands.append(["flatpak", "override", "--system", *args])
    for app_id, config in sorted(overrides.items()):
        filesystem_profile = str(config.get("filesystem", "inherit")).strip().lower()
        network_profile = str(config.get("network", "inherit")).strip().lower()
        device_profile = str(config.get("devices", "inherit")).strip().lower()
        commands.append(["flatpak", "override", "--system", "--reset", app_id])
        app_args = [
            *APP_FILESYSTEM_ARGS.get(filesystem_profile, APP_FILESYSTEM_ARGS["inherit"]),
            *APP_NETWORK_ARGS.get(network_profile, APP_NETWORK_ARGS["inherit"]),
            *APP_DEVICE_ARGS.get(device_profile, APP_DEVICE_ARGS["inherit"]),
        ]
        if app_args:
            commands.append(["flatpak", "override", "--system", *app_args, app_id])
    return commands


def run_command(command: list[str], timeout: int = 15) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    detail = completed.stderr.strip() or completed.stdout.strip()
    return completed.returncode == 0, detail


def main() -> None:
    settings = load_effective_system_settings()
    profile = policy_name(settings)
    overrides = app_overrides(settings)
    commands = policy_commands(profile, overrides)

    if shutil.which("flatpak") is None:
        status = {
            "sandbox_default": profile,
            "app_overrides": overrides,
            "apply_ok": False,
            "error": "flatpak binary not found",
            "commands": commands,
        }
        write_runtime_json(STATUS_FILE, status, mode=0o644)
        print("NMOS_APP_ISOLATION apply_ok=False reason=flatpak_missing", flush=True)
        return

    command_results: list[dict[str, object]] = []
    apply_ok = True
    for command in commands:
        ok, detail = run_command(command)
        command_results.append({"command": command, "ok": ok, "detail": detail})
        if not ok:
            apply_ok = False
            break

    status = {
        "sandbox_default": profile,
        "app_overrides": overrides,
        "apply_ok": apply_ok,
        "results": command_results,
    }
    write_runtime_json(STATUS_FILE, status, mode=0o644)
    print(f"NMOS_APP_ISOLATION profile={profile} apply_ok={apply_ok}", flush=True)


if __name__ == "__main__":
    main()
