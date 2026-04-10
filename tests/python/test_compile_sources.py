from __future__ import annotations

import py_compile
from pathlib import Path


def test_python_sources_compile(repo_root: Path) -> None:
    targets = [
        *sorted((repo_root / "apps" / "nmos_common" / "nmos_common").glob("*.py")),
        *sorted((repo_root / "apps" / "nmos_greeter" / "nmos_greeter").glob("*.py")),
        *sorted((repo_root / "apps" / "nmos_persistent_storage" / "nmos_persistent_storage").glob("*.py")),
        *sorted((repo_root / "config" / "live-build" / "includes.chroot" / "usr" / "local" / "lib" / "nmos").glob("*.py")),
    ]
    assert targets, "no Python sources were discovered"
    for path in targets:
        py_compile.compile(str(path), doraise=True)
