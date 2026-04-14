from __future__ import annotations

from pathlib import Path


def test_security_model_maps_settings_to_enforcement(repo_root: Path) -> None:
    security_model_source = (repo_root / "docs" / "security-model.md").read_text(encoding="utf-8")
    assert "## Setting To Enforcement Matrix" in security_model_source
    assert "`network_policy`" in security_model_source
    assert "network_bootstrap.py" in security_model_source
    assert "`sandbox_default`" in security_model_source
    assert "app_isolation_policy.py" in security_model_source
    assert "`app_overrides`" in security_model_source
    assert "`device_policy`" in security_model_source
    assert "device_policy.py" in security_model_source
    assert "`logging_policy`" in security_model_source
    assert "logging_policy.py" in security_model_source
    assert "journald.conf.d/90-nmos-logging-policy.conf" in security_model_source
    assert "`allow_brave_browser`" in security_model_source
    assert "desktop_mode.py" in security_model_source
    assert "brave_policy.py" in security_model_source
    assert "`vault`" in security_model_source
    assert "release gate aid" in security_model_source


def test_markdown_docs_do_not_contain_common_mojibake_sequences(repo_root: Path) -> None:
    bad_sequences = [
        "\u00e2\u20ac\u201d",  # mojibake em dash
        "\u00e2\u20ac\u201c",  # mojibake en dash
        "\u00e2\u2020\u2019",  # mojibake right arrow
        "\u00c3",  # common UTF-8 decode artifact prefix
        "\u00c2",  # common UTF-8 decode artifact prefix
    ]
    markdown_paths = [repo_root / "README.md", *sorted((repo_root / "docs").rglob("*.md"))]
    offenders: list[str] = []
    for path in markdown_paths:
        source = path.read_text(encoding="utf-8")
        for marker in bad_sequences:
            if marker in source:
                offenders.append(f"{path}: {repr(marker)}")
                break
    assert not offenders, "Found mojibake markers in markdown files:\n" + "\n".join(offenders)
