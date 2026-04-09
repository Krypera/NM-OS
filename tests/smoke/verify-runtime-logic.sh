#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 NMOS_ROOT="${ROOT_DIR}" python3 - <<'PY'
import importlib.util
import os
import tempfile
import ast
import sys
from pathlib import Path

root = Path(os.environ["NMOS_ROOT"])
sys.path.insert(0, str(root / "apps" / "nmos_common"))
sys.path.insert(0, str(root / "apps" / "nmos_greeter"))

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

network_bootstrap = load_module(
    "network_bootstrap",
    root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "network_bootstrap.py",
)
tor_status = load_module(
    "tor_bootstrap_status",
    root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py",
)
storage = load_module(
    "nmos_storage",
    root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage" / "storage.py",
)
gdmclient_source = (root / "apps" / "nmos_greeter" / "nmos_greeter" / "gdmclient.py").read_text(encoding="utf-8")
main_source = (root / "apps" / "nmos_greeter" / "nmos_greeter" / "main.py").read_text(encoding="utf-8")
client_source = (root / "apps" / "nmos_greeter" / "nmos_greeter" / "client.py").read_text(encoding="utf-8")
network_bootstrap_source = (
    root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "network_bootstrap.py"
).read_text(encoding="utf-8")
tor_status_source = (
    root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos" / "tor_bootstrap_status.py"
).read_text(encoding="utf-8")
install_hook_source = (
    root / "hooks" / "live" / "010-install-nmos-apps.hook.chroot"
).read_text(encoding="utf-8")


def class_function(module: ast.Module, class_name: str, function_name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == function_name:
                    return child
    raise AssertionError(f"missing {class_name}.{function_name}")

sample = 'NOTICE BOOTSTRAP PROGRESS=67 TAG=conn_done SUMMARY="Connected to a relay"'
progress, summary = network_bootstrap.parse_bootstrap_status(sample)
assert progress == 67, progress
assert summary == "Connected to a relay", summary

progress2, summary2 = tor_status.parse_bootstrap_status(sample)
assert progress2 == 67, progress2
assert summary2 == "Connected to a relay", summary2

with tempfile.TemporaryDirectory() as tmp:
    temp_root = Path(tmp)
    tor_status.READY_FILE = temp_root / "network-ready"
    tor_status.STATUS_FILE = temp_root / "network-status.json"

    tor_status.READY_FILE.write_text("ready\n", encoding="utf-8")
    ready_state = tor_status.read_status()
    assert ready_state["ready"] is True
    assert ready_state["last_error"] == ""

    tor_status.READY_FILE.unlink()
    tor_status.STATUS_FILE.write_text('{"ready": false, "progress": 13, "summary": "Testing"}', encoding="utf-8")
    file_state = tor_status.read_status()
    assert file_state["ready"] is False
    assert file_state["progress"] == 13
    assert file_state["summary"] == "Testing"
    assert file_state["last_error"] == ""

assert storage.boot_disk_is_supported("usb", False, False) is True
assert storage.boot_disk_is_supported(None, True, False) is True
assert storage.boot_disk_is_supported(None, False, True) is False
assert storage.boot_disk_is_supported("sata", False, False) is False
assert storage.partition_table_label_is_supported("gpt") is True
assert storage.partition_table_label_is_supported("dos") is False
assert storage.partition_table_label_is_supported("bsd") is False
assert hasattr(network_bootstrap, "remove_firewall_gate")

gib = 1024 * 1024 * 1024
mib = 1024 * 1024

single_partition_plan = storage.plan_trailing_partition(
    device_size_bytes=8 * gib,
    partitions=[
        {
            "number": 1,
            "start_bytes": 1 * mib,
            "size_bytes": 2 * gib,
        }
    ],
)
assert single_partition_plan["can_create"] is True
assert single_partition_plan["partition_number"] == 2
assert single_partition_plan["reason"] == "ready"

multi_partition_plan = storage.plan_trailing_partition(
    device_size_bytes=16 * gib,
    partitions=[
        {"number": 1, "start_bytes": 1 * mib, "size_bytes": 2 * gib},
        {"number": 2, "start_bytes": 3 * gib, "size_bytes": 4 * gib},
    ],
)
assert multi_partition_plan["can_create"] is True
assert multi_partition_plan["partition_number"] == 3
assert multi_partition_plan["free_bytes"] >= gib

full_disk_plan = storage.plan_trailing_partition(
    device_size_bytes=4 * gib,
    partitions=[
        {"number": 1, "start_bytes": 1 * mib, "size_bytes": (4 * gib) - (2 * mib)},
    ],
)
assert full_disk_plan["can_create"] is False
assert full_disk_plan["reason"] == "no_free_space"

gdm_ast = ast.parse(gdmclient_source)
on_session_opened = class_function(gdm_ast, "GdmLoginClient", "_on_session_opened")
has_report_problem = any(
    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "_report_problem"
    for node in ast.walk(on_session_opened)
)
assert has_report_problem, "gdmclient _on_session_opened does not report call_start_session_when_ready failures"

main_ast = ast.parse(main_source)
refresh_persistence = class_function(main_ast, "GreeterWindow", "refresh_persistence")
has_update_navigation = any(
    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "update_navigation"
    for node in ast.walk(refresh_persistence)
)
assert has_update_navigation, "GreeterWindow.refresh_persistence does not refresh navigation state"

current_string = class_function(main_ast, "GreeterWindow", "current_string")
uses_invalid_position_guard = any(
    isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "Gtk" and node.attr == "INVALID_LIST_POSITION"
    for node in ast.walk(current_string)
)
assert uses_invalid_position_guard, "GreeterWindow.current_string does not guard Gtk.INVALID_LIST_POSITION"

poll_runtime = class_function(main_ast, "GreeterWindow", "poll_runtime")
uses_session_handoff_guard = any(
    isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self" and node.attr == "session_start_in_progress"
    for node in ast.walk(poll_runtime)
)
assert uses_session_handoff_guard, "GreeterWindow.poll_runtime does not guard the in-progress GDM handoff state"

refresh_network = class_function(main_ast, "GreeterWindow", "refresh_network")
uses_network_status_force = any(
    isinstance(node, ast.arg) and node.arg == "force_status"
    for node in refresh_network.args.kwonlyargs
)
assert uses_network_status_force, "GreeterWindow.refresh_network does not support non-clobbering status updates"

on_create_persistence = class_function(main_ast, "GreeterWindow", "on_create_persistence")
create_uses_async_dispatch = any(
    isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and node.func.attr == "start_persistence_action"
    for node in ast.walk(on_create_persistence)
)
assert create_uses_async_dispatch, "GreeterWindow.on_create_persistence does not dispatch through async persistence action handling"

start_persistence_action = class_function(main_ast, "GreeterWindow", "start_persistence_action")
spawns_worker_thread = any(
    isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and isinstance(node.func.value, ast.Name)
    and node.func.value.id == "threading"
    and node.func.attr == "Thread"
    for node in ast.walk(start_persistence_action)
)
assert spawns_worker_thread, "GreeterWindow.start_persistence_action does not spawn a background worker thread"

setup_network_watchers = class_function(main_ast, "GreeterWindow", "setup_network_watchers")
uses_file_monitor = any(
    isinstance(node, ast.Attribute)
    and isinstance(node.value, ast.Name)
    and node.value.id == "Gio"
    and node.attr == "FileMonitorFlags"
    for node in ast.walk(setup_network_watchers)
)
assert uses_file_monitor, "GreeterWindow.setup_network_watchers does not wire Gio file monitoring"

on_allow_offline_toggled = class_function(main_ast, "GreeterWindow", "on_allow_offline_toggled")
offline_message_matches_gate = any(
    isinstance(node, ast.Constant)
    and isinstance(node.value, str)
    and "network traffic stays blocked until Tor is ready" in node.value
    for node in ast.walk(on_allow_offline_toggled)
)
assert offline_message_matches_gate, "Greeter offline bypass message does not describe that network stays blocked until Tor readiness"

assert "subprocess.run" not in client_source, "Greeter network status reader still shells out synchronously instead of using runtime files"
assert "discover_repo_greeter_path" not in network_bootstrap_source, "network bootstrap still uses repo path discovery fallback"
assert "discover_repo_greeter_path" not in tor_status_source, "tor status helper still uses repo path discovery fallback"
assert "sys.path.insert" not in network_bootstrap_source, "network bootstrap still mutates sys.path at runtime"
assert "sys.path.insert" not in tor_status_source, "tor status helper still mutates sys.path at runtime"
assert 'cp -a /opt/nmos/apps/nmos_common/nmos_common "${PYTHON_PURELIB}/"' in install_hook_source, (
    "live-build install hook does not install nmos_common into Python purelib"
)
assert "self.bus" not in client_source, "PersistenceClient still stores a long-lived D-Bus bus handle"
assert 'return self._call("Create", passphrase)' in client_source
assert 'return self._call("Unlock", passphrase)' in client_source
assert 'return self._call("Lock")' in client_source
assert 'return self._call("Repair")' in client_source

print("runtime logic checks passed")
PY
