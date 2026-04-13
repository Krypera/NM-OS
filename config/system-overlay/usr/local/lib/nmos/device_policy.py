#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from nmos_common.platform_adapter import get_runtime_dir
from nmos_common.runtime_state import write_runtime_json
from nmos_common.system_settings import load_effective_system_settings

UDEV_RULE_DIR = Path("/etc/udev/rules.d")
UDEV_RULE_FILE = UDEV_RULE_DIR / "90-nmos-device-policy.rules"
STATUS_FILE = get_runtime_dir() / "device-policy-status.json"

RULES = {
    "shared": "",
    "prompt": (
        '# Managed by NM-OS device policy service\n'
        '# "prompt" keeps devices visible while requiring explicit user authorization flows.\n'
        'SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{UDISKS_AUTO}="0"\n'
        'SUBSYSTEM=="net", ENV{ID_BUS}=="usb", ENV{NM_UNMANAGED}="1"\n'
        'SUBSYSTEM=="thunderbolt", ENV{NMOS_PROMPT_REQUIRED}="1"\n'
    ),
    "locked": (
        "# Managed by NM-OS device policy service\n"
        '# "locked" blocks USB storage, USB networking, and all non-HID USB device authorization.\n'
        'SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{UDISKS_IGNORE}="1"\n'
        'SUBSYSTEM=="net", ENV{ID_BUS}=="usb", ENV{NM_UNMANAGED}="1"\n'
        'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ENV{ID_USB_INTERFACES}=="*:03*", GOTO="nmos_device_allow_hid"\n'
        'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{authorized}="0"\n'
        'LABEL="nmos_device_allow_hid"\n'
        'SUBSYSTEM=="thunderbolt", ATTR{authorized}="0"\n'
    ),
}


def policy_name(settings: dict) -> str:
    value = str(settings.get("device_policy", "prompt")).strip().lower()
    if value in RULES:
        return value
    return "prompt"


def apply_rule(profile: str) -> tuple[bool, str]:
    try:
        UDEV_RULE_DIR.mkdir(parents=True, exist_ok=True)
        content = RULES[profile]
        if content:
            UDEV_RULE_FILE.write_text(content, encoding="utf-8")
        elif UDEV_RULE_FILE.exists():
            UDEV_RULE_FILE.unlink()
    except OSError as exc:
        return False, str(exc)
    return True, ""


def run_best_effort(*args: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    detail = completed.stderr.strip() or completed.stdout.strip()
    return completed.returncode == 0, detail


def thunderbolt_commands(profile: str) -> list[list[str]]:
    if profile == "shared":
        return [["boltctl", "config", "--set", "auth-mode=enabled"]]
    if profile == "locked":
        return [
            ["boltctl", "config", "--set", "auth-mode=manual"],
            ["boltctl", "forget", "--all"],
        ]
    return [["boltctl", "config", "--set", "auth-mode=manual"]]


def apply_thunderbolt_policy(profile: str) -> tuple[bool, str]:
    if shutil.which("boltctl") is None:
        return False, "boltctl not installed"

    errors: list[str] = []
    for command in thunderbolt_commands(profile):
        ok, detail = run_best_effort(*command, timeout=20)
        if not ok:
            errors.append(" ".join(command) + (f": {detail}" if detail else ""))
    if errors:
        return False, "; ".join(errors)
    return True, ""


def prompt_authorization_state(profile: str) -> tuple[bool, str]:
    if profile != "prompt":
        return False, ""
    prompt_stack = []
    if shutil.which("pkexec"):
        prompt_stack.append("pkexec")
    if shutil.which("zenity"):
        prompt_stack.append("zenity")
    if shutil.which("kdialog"):
        prompt_stack.append("kdialog")
    if prompt_stack:
        return True, f"prompt helper candidates: {', '.join(prompt_stack)}"
    return False, "no graphical authorization helper available"


def main() -> None:
    settings = load_effective_system_settings()
    profile = policy_name(settings)
    write_ok, write_detail = apply_rule(profile)

    reload_ok = False
    reload_detail = ""
    trigger_ok = False
    trigger_detail = ""
    thunderbolt_ok = False
    thunderbolt_detail = ""
    prompt_supported, prompt_detail = prompt_authorization_state(profile)
    if write_ok:
        reload_ok, reload_detail = run_best_effort("udevadm", "control", "--reload-rules", timeout=10)
        trigger_ok, trigger_detail = run_best_effort("udevadm", "trigger", "--subsystem-match=block", timeout=20)
        run_best_effort("udevadm", "trigger", "--subsystem-match=net", timeout=20)
        run_best_effort("udevadm", "trigger", "--subsystem-match=usb", timeout=20)
        run_best_effort("udevadm", "trigger", "--subsystem-match=thunderbolt", timeout=20)
        thunderbolt_ok, thunderbolt_detail = apply_thunderbolt_policy(profile)

    status = {
        "device_policy": profile,
        "write_ok": write_ok,
        "write_detail": write_detail,
        "reload_ok": reload_ok,
        "reload_detail": reload_detail,
        "trigger_ok": trigger_ok,
        "trigger_detail": trigger_detail,
        "thunderbolt_ok": thunderbolt_ok,
        "thunderbolt_detail": thunderbolt_detail,
        "prompt_authorization_supported": prompt_supported,
        "prompt_authorization_detail": prompt_detail,
        "rule_path": str(UDEV_RULE_FILE),
        "rule_present": UDEV_RULE_FILE.exists(),
    }
    write_runtime_json(STATUS_FILE, status, mode=0o644)
    print(
        "NMOS_DEVICE_POLICY "
        f"policy={profile} write_ok={write_ok} reload_ok={reload_ok} trigger_ok={trigger_ok}",
        flush=True,
    )


if __name__ == "__main__":
    main()
