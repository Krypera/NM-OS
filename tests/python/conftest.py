from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def configure_python_path(repo_root: Path) -> None:
    sys.path.insert(0, str(repo_root / "apps" / "nmos_common"))
    sys.path.insert(0, str(repo_root / "apps" / "nmos_control_center"))
    sys.path.insert(0, str(repo_root / "apps" / "nmos_greeter"))
    sys.path.insert(0, str(repo_root / "apps" / "nmos_persistent_storage"))
    sys.path.insert(0, str(repo_root / "apps" / "nmos_settings"))
    sys.path.insert(0, str(repo_root / "apps" / "nmos_update"))


@pytest.fixture
def workspace_tmp_path(repo_root: Path):
    tmp_root = repo_root / ".tmp-tests" / "pytest"
    tmp_root.mkdir(parents=True, exist_ok=True)
    case_dir = tmp_root / f"case-{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield case_dir
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
