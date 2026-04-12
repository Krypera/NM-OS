from __future__ import annotations

from pathlib import Path


def test_security_model_maps_settings_to_enforcement(repo_root: Path) -> None:
    security_model_source = (repo_root / "docs" / "security-model.md").read_text(encoding="utf-8")
    assert "## Setting To Enforcement Matrix" in security_model_source
    assert "`network_policy`" in security_model_source
    assert "network_bootstrap.py" in security_model_source
    assert "`sandbox_default`" in security_model_source
    assert "`device_policy`" in security_model_source
    assert "`logging_policy`" in security_model_source
    assert "`allow_brave_browser`" in security_model_source
    assert "desktop_mode.py" in security_model_source
    assert "brave_policy.py" in security_model_source
    assert "`vault`" in security_model_source
    assert "release gate aid" in security_model_source
