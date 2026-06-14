"""Public package distribution contracts."""

from __future__ import annotations

import re
import subprocess
import tarfile
import tomllib
from pathlib import Path


def _pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def test_project_metadata_has_public_urls_and_beta_classifier() -> None:
    project = _pyproject()["project"]

    assert {"name": "Enrique Book"} in project["authors"]
    assert project["license"] == "MIT"
    assert project["urls"]["Repository"].startswith("https://github.com/")
    assert project["urls"]["Documentation"].endswith("/docs")
    assert "Development Status :: 4 - Beta" in project["classifiers"]
    assert "Development Status :: 5 - Production/Stable" not in project["classifiers"]


def test_sdist_excludes_internal_agent_plans_and_personal_scripts(
    tmp_path: Path,
) -> None:
    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(tmp_path)],
        check=True,
    )
    sdist = next(tmp_path.glob("obsidian_mcp_server-*.tar.gz"))

    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()

    forbidden_patterns = [
        r"/docs/superpowers/",
        r"/\.agents/",
        r"/scripts/batch_integrate_journal\.py$",
        r"/scripts/vault_analytics\.py$",
        r"/AGENTS\.md$",
    ]
    leaked = [
        name
        for name in names
        if any(re.search(pattern, name) for pattern in forbidden_patterns)
    ]
    assert leaked == []
