from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_i18n_contribution_docs_and_smoke_hooks_exist(repo_root: Path) -> None:
    translations_doc = (repo_root / "docs" / "translations.md").read_text(encoding="utf-8")
    greeter_i18n_smoke = (repo_root / "tests" / "smoke" / "verify-greeter-i18n.sh").read_text(encoding="utf-8")
    quality_script = (repo_root / "scripts" / "check_i18n_quality.py").read_text(encoding="utf-8")

    assert "Contribution Workflow" in translations_doc
    assert "scripts/check_i18n_quality.py" in translations_doc
    assert "placeholder" in translations_doc.lower()
    assert "scripts/check_i18n_quality.py" in greeter_i18n_smoke
    assert "CRITICAL_KEYS" in quality_script
    assert "PLACEHOLDER_PATTERN" in quality_script


def test_i18n_quality_script_passes_on_current_tree(repo_root: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "check_i18n_quality.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
