"""Public package distribution contracts."""

from __future__ import annotations

import re
import subprocess
import tarfile
import tomllib
from pathlib import Path

PUBLIC_GUIDANCE_PATHS = [
    Path("README.md"),
    Path("docs/configuration.md"),
    Path("docs/troubleshooting.md"),
    Path("docs/installation.md"),
    Path("CONTRIBUTING.md"),
    Path("SECURITY.md"),
    Path("docs/release-checklist.md"),
    Path("scripts/diagnose.py"),
]


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
        r"/\.agents/",
        r"/AGENTS\.md$",
    ]
    leaked = [
        name
        for name in names
        if any(re.search(pattern, name) for pattern in forbidden_patterns)
    ]
    assert leaked == []


def test_public_docs_do_not_recommend_pip_or_missing_start_script() -> None:
    docs = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_GUIDANCE_PATHS)

    assert "pip install" not in docs
    assert "uv run main.py" not in docs
    assert "scripts/start-mcp.sh" not in docs


def test_public_docs_do_not_reference_missing_python_scripts() -> None:
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            Path("README.md"),
            Path("docs/configuration.md"),
            Path("docs/troubleshooting.md"),
            Path("docs/installation.md"),
        ]
    )

    script_paths = set(re.findall(r"scripts/[A-Za-z0-9_./-]+\.py", docs))
    missing_scripts = sorted(
        script_path for script_path in script_paths if not Path(script_path).exists()
    )
    assert missing_scripts == []


def test_mcpb_docs_describe_release_artifacts_and_prerelease_git_install() -> None:
    text = Path("docs/installation.md").read_text(encoding="utf-8")
    mcpb_section = text.split("## MCPB", maxsplit=1)[1]

    assert "MCPB bundles are release artifacts" in mcpb_section
    assert (
        "uvx --from git+https://github.com/Vasallo94/obsidian-mcp-server.git "
        "obsidian-mcp-server"
    ) in mcpb_section
    assert "scripts/build_mcpb.py" not in mcpb_section


def test_readme_configures_vault_path_before_local_run() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    configure_index = text.index("Set OBSIDIAN_VAULT_PATH")
    run_index = text.index("uv run obsidian-mcp-server")

    assert configure_index < run_index


def test_installation_docs_cover_target_harnesses() -> None:
    text = Path("docs/installation.md").read_text(encoding="utf-8")

    for required in [
        "Claude Code",
        "Codex",
        "Hermes",
        "Claude Desktop",
        "uvx",
        "OBSIDIAN_VAULT_PATH",
    ]:
        assert required in text

    assert (
        "uvx --from git+https://github.com/Vasallo94/obsidian-mcp-server.git "
        "obsidian-mcp-server"
    ) in text
    assert (
        '"--from", "git+https://github.com/Vasallo94/obsidian-mcp-server.git"' in text
    )
    assert (
        '"--from",\n  "git+https://github.com/Vasallo94/obsidian-mcp-server.git",'
    ) in text
    assert (
        '- "--from"\n      - "git+https://github.com/Vasallo94/obsidian-mcp-server.git"'
    ) in text
    assert (
        '"--from",\n        "git+https://github.com/Vasallo94/obsidian-mcp-server.git",'
    ) in text


def test_public_governance_docs_exist() -> None:
    required = [
        Path("SECURITY.md"),
        Path("CONTRIBUTING.md"),
        Path("docs/release-checklist.md"),
        Path("LICENSE"),
    ]

    assert [path for path in required if not path.is_file()] == []


def test_public_source_tree_has_no_private_local_artifacts() -> None:
    forbidden_paths = [
        Path("docs/superpowers"),
        Path("scripts/batch_integrate_journal.py"),
        Path("scripts/diagnose_backup.py"),
        Path("scripts/vault_analytics.py"),
    ]

    assert [path for path in forbidden_paths if path.exists()] == []
