# Public Packaging Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Obsidian MCP Server ready for public installation through standard MCP harnesses, with a clean Python package path, accurate docs for Claude Code/Codex/Hermes/Claude Desktop, and a real MCPB release path.

**Architecture:** Treat `uvx`/PyPI as the primary cross-harness distribution path for stdio MCP clients, and MCPB as the secondary one-click Claude Desktop path. Keep public core vault-agnostic by default, move personal or vault-specific behavior behind explicit profile gates, and verify packaging with automated contract tests.

**Tech Stack:** Python 3.11+, FastMCP, uv, Hatch, pytest, Ruff, Pyright, Bandit, pip-audit, PyInstaller for platform-specific MCPB binaries, `@anthropic-ai/mcpb` for bundle validation/packing.

---

## File Map

- Modify `Makefile`: repair `make verify` so it calls scripts that exist.
- Modify `tests/test_normalize_frontmatter.py`: let Ruff sort imports/format the file.
- Create `tests/test_dev_commands_contract.py`: guard Makefile script references.
- Modify `pyproject.toml`: public metadata, beta classifier, sdist excludes, packaging dev dependency.
- Create `tests/test_public_distribution_contract.py`: enforce public package/docs contracts.
- Modify `README.md`: shorter public quickstart with links to full install docs.
- Create `docs/installation.md`: canonical install guide for Claude Code, Codex, Hermes, Claude Desktop, and MCPB.
- Modify `docs/configuration.md`: point client setup to `docs/installation.md`; keep environment/tool-set reference here.
- Modify `docs/troubleshooting.md`: remove missing `scripts/start-mcp.sh` recommendation or add a real script in a separate task.
- Modify `obsidian_mcp/tools/context_logic.py`: avoid routing generic media requests to personal Secundo workflow unless the vault declares the media standard/profile.
- Modify `obsidian_mcp/prompts/profiles.py`: make prompt prose profile-neutral or explicitly local-profile-only.
- Modify `tests/test_profile_prompts_resources.py`: verify generic vaults do not expose personal media routing.
- Move or exclude `scripts/batch_integrate_journal.py` and `scripts/vault_analytics.py`: keep them out of public sdist.
- Create `packaging/mcpb/manifest.template.json`: source manifest for platform-specific MCPB builds.
- Create `scripts/build_mcpb.py`: build a PyInstaller binary, stage manifest/assets, validate, and pack MCPB.
- Modify `tests/test_tool_registry_contract.py`: validate the template/source manifest contract rather than the current placeholder bundle.
- Create `SECURITY.md`: supported versions and vulnerability reporting.
- Create `CONTRIBUTING.md`: public development flow using uv.
- Create `docs/release-checklist.md`: release commands and required checks.
- Modify `CHANGELOG.md`: document packaging/docs changes under `[Unreleased]`.

---

### Task 1: Repair Baseline Quality Gates

**Files:**
- Modify: `Makefile:32-34`
- Modify: `tests/test_normalize_frontmatter.py:8-14`
- Create: `tests/test_dev_commands_contract.py`

- [ ] **Step 1: Write the failing Makefile contract test**

Create `tests/test_dev_commands_contract.py`:

```python
"""Contracts for developer-facing commands."""

from __future__ import annotations

import re
from pathlib import Path


def test_make_verify_references_existing_python_scripts() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    scripts = re.findall(r"uv run python (scripts/[^\s]+\.py)", makefile)

    assert scripts, "Makefile should expose at least one Python verification script"
    missing = [script for script in scripts if not Path(script).is_file()]
    assert missing == []
```

- [ ] **Step 2: Run the targeted test and confirm it fails**

Run:

```bash
uv run pytest tests/test_dev_commands_contract.py -v
```

Expected: FAIL because `scripts/verify_agents.py` is referenced by `make verify` but does not exist.

- [ ] **Step 3: Fix `make verify`**

Replace the missing script in `Makefile`:

```makefile
verify:
	uv run python scripts/verify_ignore.py
	uv run python scripts/verify_youtube.py
```

- [ ] **Step 4: Let Ruff format the existing frontmatter test**

Run:

```bash
uv run ruff check tests/test_normalize_frontmatter.py --fix
uv run ruff format tests/test_normalize_frontmatter.py
```

Expected: the import block in `tests/test_normalize_frontmatter.py` is sorted and `ruff format --check .` no longer reports that file.

- [ ] **Step 5: Verify baseline checks**

Run:

```bash
make verify
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/test_dev_commands_contract.py tests/test_normalize_frontmatter.py -v
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```bash
git add Makefile tests/test_dev_commands_contract.py tests/test_normalize_frontmatter.py
git commit -m "chore: repair developer verification commands"
```

---

### Task 2: Clean Public Package Metadata and Source Distribution

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_public_distribution_contract.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write public distribution contract tests**

Create `tests/test_public_distribution_contract.py`:

```python
"""Public package distribution contracts."""

from __future__ import annotations

import re
import tarfile
from pathlib import Path

import tomllib


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


def test_sdist_excludes_internal_agent_plans_and_personal_scripts() -> None:
    sdist = next(Path("dist").glob("obsidian_mcp_server-*.tar.gz"))

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
```

- [ ] **Step 2: Run the metadata test and confirm it fails**

Run:

```bash
uv build --sdist
uv run pytest tests/test_public_distribution_contract.py -v
```

Expected: FAIL because metadata lacks `authors`/`license`/URLs/beta classifier and the current sdist includes internal files.

- [ ] **Step 3: Update `pyproject.toml` public metadata**

Apply these changes under `[project]`:

```toml
authors = [{ name = "Enrique Book" }]
license = "MIT"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Text Processing :: Markup :: Markdown",
    "Topic :: Office/Business :: Groupware",
]

[project.urls]
Homepage = "https://github.com/Vasallo94/obsidian-mcp-server"
Repository = "https://github.com/Vasallo94/obsidian-mcp-server"
Documentation = "https://github.com/Vasallo94/obsidian-mcp-server/tree/main/docs"
Issues = "https://github.com/Vasallo94/obsidian-mcp-server/issues"
```

Add this sdist configuration:

```toml
[tool.hatch.build.targets.sdist]
exclude = [
    "/.agents",
    "/docs/superpowers",
    "/scripts/batch_integrate_journal.py",
    "/scripts/vault_analytics.py",
    "/AGENTS.md",
]
```

- [ ] **Step 4: Add packaging dependency**

Run:

```bash
uv add --dev pyinstaller
```

Expected: `pyproject.toml` and `uv.lock` are updated without using `pip`.

- [ ] **Step 5: Update changelog**

Add under `CHANGELOG.md` > `[Unreleased]` > `### Changed`:

```markdown
- Preparada la metadata pública del paquete y limpiado el sdist para excluir planes internos, scripts personales y configuración de agentes local.
```

- [ ] **Step 6: Verify distribution**

Run:

```bash
rm -rf dist
uv build --sdist --wheel
uv run pytest tests/test_public_distribution_contract.py -v
```

Expected: PASS. The wheel should still contain only `obsidian_mcp/` and `.dist-info`; the sdist should not contain internal plans or personal scripts.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock tests/test_public_distribution_contract.py CHANGELOG.md
git commit -m "chore(packaging): clean public distribution metadata"
```

---

### Task 3: Remove Personal Workflow Leakage from Generic Routing

**Files:**
- Modify: `obsidian_mcp/tools/context_logic.py`
- Modify: `obsidian_mcp/prompts/profiles.py`
- Modify: `tests/test_profile_prompts_resources.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write the failing generic routing test**

Append to `tests/test_profile_prompts_resources.py`:

```python
def test_generic_media_request_does_not_route_to_personal_profile(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()

    from obsidian_mcp.tools.context_logic import route_task_request

    result = route_task_request("actualiza una película en mi vault")

    assert result.success
    assert result.data is not None
    assert "Secundo Selebro" not in result.data
    assert "update_media_item" not in result.data
    assert "assistant_overview" in result.data
```

Use the existing imports in the file; if `reset_settings`, `invalidate_vault_config_cache`, or `invalidate_skills_cache` are not already imported there, add them from the same modules used by nearby tests.

- [ ] **Step 2: Run the targeted test and confirm it fails**

Run:

```bash
uv run pytest tests/test_profile_prompts_resources.py::test_generic_media_request_does_not_route_to_personal_profile -v
```

Expected: FAIL because generic media requests currently route to personal media workflow text.

- [ ] **Step 3: Gate media routing by declared standard or profile prompt**

In `obsidian_mcp/tools/context_logic.py`, update the media branch inside `_infer_route`:

```python
    has_media_workflow = "media" in standards or "update_media_item" in prompt_sets
    if has_media_workflow and _has_any(
        text, ["película", "pelicula", "serie", "libro", "kindle", "media"]
    ):
```

Change the notes string in the Kindle route from:

```python
"Uses the Secundo Selebro media workflow when the media standard is declared."
```

to:

```python
"Uses the declared media workflow from the active vault profile."
```

- [ ] **Step 4: Make profile prompt prose profile-neutral**

In `obsidian_mcp/prompts/profiles.py`, change user-facing docstrings:

```python
"""Update a movie, series, or book in the active vault media library."""
```

and:

```python
"""Import Kindle highlights into the active vault media notes."""
```

Keep `SECUNDO_PROFILE = "secundo_selebro"` as an internal compatibility gate for existing vaults.

- [ ] **Step 5: Verify routing behavior**

Run:

```bash
uv run pytest tests/test_profile_prompts_resources.py -v
```

Expected: PASS. Existing Secundo/profile tests should still pass when they explicitly configure that profile.

- [ ] **Step 6: Update changelog**

Add under `CHANGELOG.md` > `[Unreleased]` > `### Fixed`:

```markdown
- Evitado que `route.task` recomiende workflows personales de media en vaults genéricos sin estándar `media` declarado.
```

- [ ] **Step 7: Commit**

```bash
git add obsidian_mcp/tools/context_logic.py obsidian_mcp/prompts/profiles.py tests/test_profile_prompts_resources.py CHANGELOG.md
git commit -m "fix(context): keep profile media routing vault scoped"
```

---

### Task 4: Create Standard Installation Documentation

**Files:**
- Create: `docs/installation.md`
- Modify: `README.md`
- Modify: `docs/configuration.md`
- Modify: `docs/troubleshooting.md`
- Modify: `tests/test_public_distribution_contract.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add documentation contract tests**

Append to `tests/test_public_distribution_contract.py`:

```python
def test_public_docs_do_not_recommend_pip_or_missing_start_script() -> None:
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            Path("README.md"),
            Path("docs/configuration.md"),
            Path("docs/troubleshooting.md"),
            Path("docs/installation.md"),
        ]
    )

    assert "pip install" not in docs
    assert "scripts/start-mcp.sh" not in docs


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
```

- [ ] **Step 2: Run docs tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_public_distribution_contract.py::test_public_docs_do_not_recommend_pip_or_missing_start_script tests/test_public_distribution_contract.py::test_installation_docs_cover_target_harnesses -v
```

Expected: FAIL because `docs/installation.md` does not exist and current docs mention `pip install` and `scripts/start-mcp.sh`.

- [ ] **Step 3: Create `docs/installation.md`**

Create the file with this structure:

```markdown
# Installation

Obsidian MCP Server runs as a local stdio MCP server. The only required
configuration is `OBSIDIAN_VAULT_PATH`, an absolute path to the Obsidian vault.

## Recommended command

After the package is published, use:

```bash
uvx obsidian-mcp-server
```

Before the package is published to PyPI, use the Git source:

```bash
uvx --from git+https://github.com/Vasallo94/obsidian-mcp-server.git obsidian-mcp-server
```

For local development:

```bash
uv run --directory /path/to/obsidian-mcp-server obsidian-mcp-server
```

## Claude Code

```bash
claude mcp add-json --scope user obsidian '{
  "type": "stdio",
  "command": "uvx",
  "args": ["obsidian-mcp-server"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
  }
}'
```

For a Git install before PyPI publication:

```bash
claude mcp add-json --scope user obsidian '{
  "type": "stdio",
  "command": "uvx",
  "args": ["--from", "git+https://github.com/Vasallo94/obsidian-mcp-server.git", "obsidian-mcp-server"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
  }
}'
```

## Codex

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.obsidian]
command = "uvx"
args = ["obsidian-mcp-server"]
startup_timeout_sec = 30
tool_timeout_sec = 120

[mcp_servers.obsidian.env]
OBSIDIAN_VAULT_PATH = "/absolute/path/to/your/vault"
```

## Hermes

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  obsidian:
    command: "uvx"
    args: ["obsidian-mcp-server"]
    env:
      OBSIDIAN_VAULT_PATH: "/absolute/path/to/your/vault"
```

## Claude Desktop

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": ["obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
      }
    }
  }
}
```

## Optional tool sets

Core read tools are enabled by default. Enable write/analysis integrations with
`OBSIDIAN_MCP_TOOL_SETS`:

```json
{
  "OBSIDIAN_MCP_TOOL_SETS": "notes_write,vault_analysis"
}
```

Common tool sets: `notes_write`, `vault_analysis`, `agents_admin`, `youtube`,
`obsidianrag`, `canvas`, `kanvas`, and `legacy_semantic`.

## MCPB

MCPB bundles are intended for one-click local installation in apps that support
the `.mcpb` format. Use the release artifact for your operating system rather
than the source tree. Development builds are produced with:

```bash
uv run python scripts/build_mcpb.py
```
```

- [ ] **Step 4: Update README**

Replace the install section around `README.md:62-68` with:

```markdown
2. **Run locally**:

   ```bash
   make install
   uv run obsidian-mcp-server
   ```

   For end-user installation in MCP clients, prefer `uvx` once the package is
   published:

   ```bash
   uvx obsidian-mcp-server
   ```
```

Add a short link near the Usage heading:

```markdown
For Claude Code, Codex, Hermes, Claude Desktop, and MCPB setup, see
[Installation](docs/installation.md).
```

- [ ] **Step 5: Simplify client examples in `docs/configuration.md`**

Replace the long per-client setup block with:

```markdown
## MCP client integration

Client-specific setup lives in [Installation](installation.md). This page is
kept focused on environment variables, vault configuration, tool sets, and
profile behavior.
```

Keep the tool sets and vault config sections below it.

- [ ] **Step 6: Fix troubleshooting**

In `docs/troubleshooting.md`, replace the missing `scripts/start-mcp.sh` advice with:

```markdown
**Permanent fix**: pre-warm dependencies before reconnecting:

```bash
cd /path/to/obsidian-mcp-server
uv sync
```

For MCP clients, prefer the `uvx` install path in `docs/installation.md`, or
use `uv run --directory /path/to/obsidian-mcp-server obsidian-mcp-server` for a
local checkout.
```

- [ ] **Step 7: Update changelog**

Add under `CHANGELOG.md` > `[Unreleased]` > `### Docs`:

```markdown
- Añadida guía estándar de instalación para Claude Code, Codex, Hermes, Claude Desktop y MCPB.
```

- [ ] **Step 8: Verify docs**

Run:

```bash
uv run pytest tests/test_public_distribution_contract.py -v
uv run ruff format docs/installation.md README.md docs/configuration.md docs/troubleshooting.md
```

Expected: docs tests pass and Markdown remains readable.

- [ ] **Step 9: Commit**

```bash
git add docs/installation.md README.md docs/configuration.md docs/troubleshooting.md tests/test_public_distribution_contract.py CHANGELOG.md
git commit -m "docs: add standard MCP installation guide"
```

---

### Task 5: Replace Placeholder MCPB with a Real Build Pipeline

**Files:**
- Create: `packaging/mcpb/manifest.template.json`
- Create: `scripts/build_mcpb.py`
- Modify: `mcpb/manifest.json` or remove it after migrating tests to `packaging/mcpb/manifest.template.json`
- Modify: `tests/test_tool_registry_contract.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write MCPB source manifest contract test**

Modify `tests/test_tool_registry_contract.py::test_mcpb_manifest_contract` to read `packaging/mcpb/manifest.template.json`:

```python
def test_mcpb_manifest_contract():
    manifest_path = Path("packaging/mcpb/manifest.template.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == "0.4"
    assert manifest["server"]["type"] == "binary"
    config = manifest["server"]["mcp_config"]
    assert config["command"].startswith("${__dirname}/server/obsidian-mcp-server")
    assert config["env"]["OBSIDIAN_VAULT_PATH"] == "${user_config.vaultPath}"
    assert config["env"]["OBSIDIAN_MCP_TOOL_SETS"] == "${user_config.toolSets}"
    assert manifest["user_config"]["vaultPath"]["type"] == "directory"
    assert manifest["user_config"]["toolSets"]["default"] == "core"
    assert "runtimes" not in manifest.get("compatibility", {})
```

- [ ] **Step 2: Run the MCPB test and confirm it fails**

Run:

```bash
uv run pytest tests/test_tool_registry_contract.py::test_mcpb_manifest_contract -v
```

Expected: FAIL because the template does not exist and the current manifest still describes a system-Python runtime.

- [ ] **Step 3: Create `packaging/mcpb/manifest.template.json`**

```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/mcpb/main/schemas/mcpb-manifest-v0.4.schema.json",
  "manifest_version": "0.4",
  "name": "obsidian-mcp-server",
  "display_name": "Obsidian MCP Server",
  "version": "1.0.0",
  "description": "Local MCP server for reading, searching, and maintaining Obsidian vaults.",
  "author": {
    "name": "Enrique Book"
  },
  "server": {
    "type": "binary",
    "entry_point": "server/obsidian-mcp-server",
    "mcp_config": {
      "command": "${__dirname}/server/obsidian-mcp-server",
      "args": [],
      "env": {
        "OBSIDIAN_VAULT_PATH": "${user_config.vaultPath}",
        "OBSIDIAN_MCP_TOOL_SETS": "${user_config.toolSets}",
        "OBSIDIAN_MCP_PROFILE_NAME": "${user_config.profileName}",
        "OBSIDIANRAG_API_URL": "${user_config.obsidianRagApiUrl}"
      }
    }
  },
  "user_config": {
    "vaultPath": {
      "type": "directory",
      "title": "Obsidian vault",
      "description": "Folder containing the Obsidian vault to expose.",
      "required": true
    },
    "toolSets": {
      "type": "string",
      "title": "Tool sets",
      "description": "Comma-separated optional tool sets such as notes_write,vault_analysis,obsidianrag.",
      "default": "core"
    },
    "profileName": {
      "type": "string",
      "title": "Profile name",
      "description": "Optional vault profile name.",
      "default": ""
    },
    "obsidianRagApiUrl": {
      "type": "string",
      "title": "ObsidianRAG API URL",
      "description": "Loopback HTTP URL for the optional ObsidianRAG backend.",
      "default": "http://127.0.0.1:8000"
    }
  },
  "compatibility": {
    "claude_desktop": ">=1.0.0",
    "platforms": ["darwin", "linux", "win32"]
  },
  "keywords": ["obsidian", "mcp", "notes", "knowledge-management"]
}
```

- [ ] **Step 4: Create `scripts/build_mcpb.py`**

```python
"""Build a platform-specific MCPB bundle."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "build" / "mcpb"
DIST_ROOT = ROOT / "dist" / "mcpb"
TEMPLATE = ROOT / "packaging" / "mcpb" / "manifest.template.json"


def _platform_name() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    if system == "linux":
        return "linux"
    if system == "windows":
        return "win32"
    raise SystemExit(f"Unsupported platform for MCPB build: {system}")


def _binary_name() -> str:
    return "obsidian-mcp-server.exe" if _platform_name() == "win32" else "obsidian-mcp-server"


def _run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def _build_binary() -> Path:
    _run(
        [
            "uv",
            "run",
            "pyinstaller",
            "--clean",
            "--onefile",
            "--name",
            "obsidian-mcp-server",
            "mcpb/server/obsidian_mcp_server.py",
        ]
    )
    return ROOT / "dist" / _binary_name()


def _stage_bundle(binary: Path) -> Path:
    platform_id = _platform_name()
    stage = BUILD_ROOT / platform_id
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "server").mkdir(parents=True)

    shutil.copy2(binary, stage / "server" / _binary_name())

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest["version"] = _read_project_version()
    manifest["compatibility"]["platforms"] = [platform_id]
    if platform_id == "win32":
        manifest["server"]["entry_point"] = "server/obsidian-mcp-server.exe"
        manifest["server"]["mcp_config"]["command"] = (
            "${__dirname}/server/obsidian-mcp-server.exe"
        )

    (stage / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return stage


def _read_project_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in pyproject.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("Could not read project version from pyproject.toml")


def main() -> None:
    binary = _build_binary()
    stage = _stage_bundle(binary)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)

    _run(["npx", "--yes", "@anthropic-ai/mcpb", "validate", str(stage)])
    _run(["npx", "--yes", "@anthropic-ai/mcpb", "pack", str(stage)], cwd=ROOT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the manifest test**

Run:

```bash
uv run pytest tests/test_tool_registry_contract.py::test_mcpb_manifest_contract -v
```

Expected: PASS.

- [ ] **Step 6: Build and validate a local MCPB**

Run:

```bash
uv run python scripts/build_mcpb.py
```

Expected: PyInstaller produces a platform binary, `npx @anthropic-ai/mcpb validate` passes, and a `.mcpb` artifact appears under the build or dist output produced by the CLI.

- [ ] **Step 7: Update changelog**

Add under `CHANGELOG.md` > `[Unreleased]` > `### Added`:

```markdown
- Pipeline de MCPB con binario local para generar bundles instalables por plataforma sin depender del Python del usuario.
```

- [ ] **Step 8: Commit**

```bash
git add packaging/mcpb/manifest.template.json scripts/build_mcpb.py tests/test_tool_registry_contract.py CHANGELOG.md
git commit -m "build(mcpb): add platform bundle pipeline"
```

---

### Task 6: Add Public Project Governance Files

**Files:**
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `docs/release-checklist.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write governance docs contract**

Append to `tests/test_public_distribution_contract.py`:

```python
def test_public_governance_docs_exist() -> None:
    required = [
        Path("SECURITY.md"),
        Path("CONTRIBUTING.md"),
        Path("docs/release-checklist.md"),
        Path("LICENSE"),
    ]

    assert [path for path in required if not path.is_file()] == []
```

- [ ] **Step 2: Run the governance test and confirm it fails**

Run:

```bash
uv run pytest tests/test_public_distribution_contract.py::test_public_governance_docs_exist -v
```

Expected: FAIL because the governance docs do not exist yet.

- [ ] **Step 3: Create `SECURITY.md`**

```markdown
# Security Policy

## Supported versions

Security fixes are prepared against the current `main` branch and the latest
published release.

## Reporting a vulnerability

Please report security issues privately through GitHub Security Advisories when
available. If that is unavailable, open a minimal issue asking for a private
security contact without including exploit details.

## Local MCP security model

This server runs locally with the user's permissions. Do not point
`OBSIDIAN_VAULT_PATH` at directories that contain unrelated secrets. The server
validates vault-relative paths and blocks configured private paths, but MCP hosts
do not sandbox local processes for you.
```

- [ ] **Step 4: Create `CONTRIBUTING.md`**

```markdown
# Contributing

Thanks for helping improve Obsidian MCP Server.

## Development setup

```bash
uv sync
uv run pytest tests/
uv run ruff check .
uv run pyright
```

Use `uv` for all Python dependency management. Do not use `pip install` or
`uv pip install` in this repository.

## Pull request checklist

- Tests pass with `uv run pytest tests/`.
- Ruff passes with `uv run ruff check .`.
- Pyright passes with `uv run pyright`.
- User-facing changes are documented in `README.md` or `docs/`.
- `CHANGELOG.md` has an `[Unreleased]` entry.

## Commit style

Use Conventional Commits, for example:

```bash
git commit -m "fix(navigation): validate paths before reading notes"
```
```

- [ ] **Step 5: Create `docs/release-checklist.md`**

```markdown
# Release Checklist

## Pre-release

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run bandit -c pyproject.toml -r obsidian_mcp/
uv run pip-audit
uv run pytest tests/
rm -rf dist build
uv build --sdist --wheel
uv run python scripts/build_mcpb.py
```

## Versioning

1. Move relevant `CHANGELOG.md` entries from `[Unreleased]` to the release
   version.
2. Update `pyproject.toml` version.
3. Ensure `packaging/mcpb/manifest.template.json` picks up the same version via
   `scripts/build_mcpb.py`.
4. Tag the release as `vX.Y.Z`.

## Publish

Publish the Python package to PyPI and attach platform-specific `.mcpb`
artifacts to the GitHub release.
```

- [ ] **Step 6: Link governance docs from README**

Add near the Technical Documentation section:

```markdown
For contribution, release, and security process, see
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[Release Checklist](docs/release-checklist.md).
```

- [ ] **Step 7: Update changelog**

Add under `CHANGELOG.md` > `[Unreleased]` > `### Docs`:

```markdown
- Añadidos documentos públicos de contribución, seguridad y checklist de release.
```

- [ ] **Step 8: Verify**

Run:

```bash
uv run pytest tests/test_public_distribution_contract.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add SECURITY.md CONTRIBUTING.md docs/release-checklist.md README.md tests/test_public_distribution_contract.py CHANGELOG.md
git commit -m "docs: add public project governance"
```

---

### Task 7: Final End-to-End Verification

**Files:**
- No code changes expected unless a verification step exposes a defect.

- [ ] **Step 1: Run full local quality suite**

Run:

```bash
make verify
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run bandit -c pyproject.toml -r obsidian_mcp/
uv run pip-audit
uv run pytest tests/
```

Expected:
- `pytest`: all non-optional tests pass.
- `pyright`: 0 errors. Warnings from optional legacy semantic imports are acceptable only if unchanged and documented.
- `pip-audit`: no known vulnerabilities.

- [ ] **Step 2: Run packaging checks**

Run:

```bash
rm -rf build dist
uv build --sdist --wheel
tar -tzf dist/obsidian_mcp_server-*.tar.gz | rg "docs/superpowers|batch_integrate_journal|vault_analytics|AGENTS.md" && exit 1 || true
uv run python scripts/build_mcpb.py
```

Expected:
- Wheel and sdist build.
- Internal docs/scripts are absent from sdist.
- MCPB manifest validation passes.
- One platform-specific MCPB artifact is produced locally.

- [ ] **Step 3: Smoke test stdio startup from wheel/git path**

Run:

```bash
tmp_vault="$(mktemp -d)"
printf '# Smoke\n' > "$tmp_vault/smoke.md"
OBSIDIAN_VAULT_PATH="$tmp_vault" uvx --from dist/obsidian_mcp_server-*.whl obsidian-mcp-server
```

Expected: server starts and waits for stdio. Stop with Ctrl-C after confirming startup logs go to stderr and stdout is reserved for MCP protocol.

- [ ] **Step 4: Review public docs with grep**

Run:

```bash
rg -n "pip install|scripts/start-mcp.sh|/Users/enriquebook|Secundo Selebro|C:/Users/ldaevf1" README.md docs pyproject.toml scripts packaging obsidian_mcp
```

Expected:
- No `pip install` in public docs.
- No missing `scripts/start-mcp.sh`.
- No private absolute paths in public docs/package scripts.
- `Secundo Selebro` appears only in explicitly local-profile compatibility code or tests, not generic install docs.

- [ ] **Step 5: Commit any verification fixes**

If verification required fixes:

```bash
git add <fixed-files>
git commit -m "chore: finalize public packaging readiness"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

**Spec coverage:** The plan covers remote sync status, CI repair, public metadata, generic behavior, docs for Claude Code/Codex/Hermes/Claude Desktop, MCPB packaging, and release governance.

**Placeholder scan:** There are no `TBD`, `TODO`, or undefined "handle later" steps. Each implementation step names files, commands, and expected results.

**Type consistency:** New tests use standard library `Path`, `re`, `tarfile`, and `tomllib`; build script uses `Path`, `json`, `platform`, `shutil`, and `subprocess`. Function names referenced in tasks are defined in their snippets or already exist in the repository.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-14-public-packaging-standardization.md`.

Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
