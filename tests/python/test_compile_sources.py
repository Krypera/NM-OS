from __future__ import annotations

import py_compile
from pathlib import Path


def test_python_sources_compile(repo_root: Path, workspace_tmp_path: Path) -> None:
    targets = [
        *sorted((repo_root / "apps" / "nmos_common" / "nmos_common").glob("*.py")),
        *sorted((repo_root / "apps" / "nmos_control_center" / "nmos_control_center").glob("*.py")),
        *sorted((repo_root / "apps" / "nmos_greeter" / "nmos_greeter").glob("*.py")),
        *sorted((repo_root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage").glob("*.py")),
        *sorted((repo_root / "apps" / "nmos_settings" / "nmos_settings").glob("*.py")),
        *sorted((repo_root / "config" / "system-overlay" / "usr" / "local" / "lib" / "nmos").glob("*.py")),
    ]
    assert targets, "no Python sources were discovered"
    for path in targets:
        relative = path.relative_to(repo_root)
        cfile = workspace_tmp_path / "pyc" / relative.with_suffix(".pyc")
        cfile.parent.mkdir(parents=True, exist_ok=True)
        py_compile.compile(str(path), cfile=str(cfile), doraise=True)
