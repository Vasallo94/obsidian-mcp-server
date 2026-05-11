"""ObsidianRAG integration tools."""

from __future__ import annotations

import json
import shlex
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from shutil import which
from typing import Any

from fastmcp import FastMCP

from ..config import get_vault_path
from ..result import Result
from ..vault_config import get_vault_config
from .registry import enabled_tool_sets, register_tool

DEFAULT_API_URL = "http://127.0.0.1:8000"


def register_obsidianrag_tools(mcp: FastMCP) -> None:
    """Register ObsidianRAG tools when the optional pack is enabled."""
    if not _is_obsidianrag_enabled():
        return

    @register_tool(mcp, "rag_setup_status")
    def rag_setup_status() -> str:
        """
        Inspect local ObsidianRAG setup status.

        Checks profile config, project path, CLI availability, Ollama availability,
        and whether the ObsidianRAG API is reachable.
        """
        return get_rag_setup_status().to_display()

    @register_tool(mcp, "rag_health")
    def rag_health() -> str:
        """
        Check whether the ObsidianRAG backend is reachable and ready.
        """
        return check_rag_health().to_display()

    @register_tool(mcp, "ask_vault")
    def ask_vault(question: str, session_id: str | None = None) -> str:
        """
        Ask a natural-language question against the Obsidian vault via ObsidianRAG.

        Args:
            question: User question to answer from vault context.
            session_id: Optional ObsidianRAG conversation session ID.
        """
        return ask_rag(question, session_id).to_display()

    @register_tool(mcp, "rebuild_rag_index")
    def rebuild_rag_index() -> str:
        """
        Rebuild the ObsidianRAG index after large vault changes.
        """
        return rebuild_rag_database().to_display()


def get_rag_setup_status() -> Result[str]:
    """Build a setup status report for the active ObsidianRAG integration."""
    config = _get_integration_config()
    if not config.success:
        return Result.fail(config.error or "ObsidianRAG integration is not configured.")

    data = config.data or {}
    project_path = Path(str(data.get("project_path") or ""))
    backend_path = project_path / "backend"
    checks = [
        ("pack_enabled", _is_obsidianrag_enabled(), "tool_sets includes obsidianrag"),
        (
            "integration_declared",
            bool(data),
            ".agents/vault.yaml profile.integrations.obsidianrag",
        ),
        ("project_path_exists", project_path.exists(), str(project_path)),
        (
            "backend_project_available",
            (backend_path / "pyproject.toml").is_file(),
            str(backend_path),
        ),
        ("uv_available", bool(which("uv")), which("uv") or "not found"),
        (
            "global_obsidianrag_cli_available",
            bool(which("obsidianrag")),
            which("obsidianrag") or "optional; local `uv run obsidianrag` is enough",
        ),
        ("ollama_cli_available", bool(which("ollama")), which("ollama") or "not found"),
    ]

    health = _request_json("GET", f"{data['api_url'].rstrip('/')}/health")
    checks.append(("api_reachable", health.success, str(data["api_url"])))

    output = "# ObsidianRAG Setup Status\n\n"
    output += "\n".join(
        f"- {'✅' if ok else '❌'} `{name}`: {detail}" for name, ok, detail in checks
    )
    output += "\n\n## Next Actions\n"
    if health.success:
        output += "- ObsidianRAG is reachable. Use `ask_vault` for semantic vault questions.\n"
        output += "- Run `rebuild_rag_index` after big vault reorganizations.\n"
    else:
        output += "- Read `obsidian://integrations/obsidianrag/setup`.\n"
        output += "- Start Ollama or another supported LLM provider.\n"
        output += "- Start ObsidianRAG with the command shown in the setup resource.\n"
    return Result.ok(output.rstrip())


def check_rag_health() -> Result[str]:
    """Call ObsidianRAG health endpoint."""
    config = _get_integration_config()
    if not config.success:
        return Result.fail(config.error or "ObsidianRAG integration is not configured.")
    data = config.data or {}
    result = _request_json("GET", f"{data['api_url'].rstrip('/')}/health")
    if not result.success:
        return Result.fail(
            "ObsidianRAG is not reachable. Read "
            "`obsidian://integrations/obsidianrag/setup` and start the backend."
        )
    return Result.ok(json.dumps(result.data, ensure_ascii=False, indent=2))


def ask_rag(question: str, session_id: str | None = None) -> Result[str]:
    """Ask ObsidianRAG through its HTTP API."""
    if not question.strip():
        return Result.fail("Question cannot be empty.")

    config = _get_integration_config()
    if not config.success:
        return Result.fail(config.error or "ObsidianRAG integration is not configured.")
    data = config.data or {}
    payload: dict[str, Any] = {"text": question}
    if session_id:
        payload["session_id"] = session_id

    result = _request_json(
        "POST", f"{data['api_url'].rstrip('/')}/ask", payload, timeout=120
    )
    if not result.success:
        return Result.fail(
            "ObsidianRAG query failed. Check `rag_health` and "
            "`obsidian://integrations/obsidianrag/setup`."
        )

    response = result.data or {}
    output = "# Vault Answer\n\n"
    output += str(response.get("result", "")).strip() or "No answer returned."
    sources = response.get("sources") or []
    if sources:
        output += "\n\n## Sources\n"
        for source in sources[:8]:
            output += (
                f"- {source.get('source', 'Unknown')} ({source.get('score', 0)})\n"
            )
    if response.get("session_id"):
        output += f"\nSession: `{response['session_id']}`"
    return Result.ok(output.rstrip())


def rebuild_rag_database() -> Result[str]:
    """Trigger ObsidianRAG index rebuild."""
    config = _get_integration_config()
    if not config.success:
        return Result.fail(config.error or "ObsidianRAG integration is not configured.")
    data = config.data or {}
    result = _request_json(
        "POST", f"{data['api_url'].rstrip('/')}/rebuild_db", timeout=1800
    )
    if not result.success:
        return Result.fail(
            "Could not rebuild ObsidianRAG index. Check `rag_health` first."
        )
    return Result.ok(json.dumps(result.data, ensure_ascii=False, indent=2))


def build_obsidianrag_config_resource() -> str:
    """Return safe ObsidianRAG integration config."""
    config = _get_integration_config()
    if not config.success:
        return json.dumps(
            {"enabled": False, "error": config.error}, ensure_ascii=False, indent=2
        )
    payload = {"enabled": True, **(config.data or {})}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_obsidianrag_setup_resource() -> str:
    """Return a guided setup playbook for ObsidianRAG."""
    config = _get_integration_config()
    if not config.success:
        return f"# ObsidianRAG Setup\n\n{config.error}"
    data = config.data or {}
    project_path = Path(str(data["project_path"]))
    backend_path = project_path / "backend"
    vault_path = str(data["vault_path"])
    api_url = str(data["api_url"])
    quoted_backend_path = shlex.quote(str(backend_path))
    quoted_vault_path = shlex.quote(vault_path)

    return f"""# ObsidianRAG Setup

This resource is for agents configuring semantic vault search.

## Goal

Use ObsidianRAG as the only advanced RAG engine. The MCP stays lightweight and
calls ObsidianRAG through HTTP tools.

## User Consent

Agents must show the exact commands before running installs, starting local
services, pulling models, or rebuilding the index. Do not run setup commands
silently.

## Expected Local Paths

- Vault: `{vault_path}`
- ObsidianRAG project: `{project_path}`
- Backend folder: `{backend_path}`
- API URL: `{api_url}`

## Agent Checklist

1. Run `rag_setup_status`.
2. If Ollama is missing, help the user install/start Ollama and pull a local model.
3. Install backend dependencies from the ObsidianRAG backend folder.
4. Start the backend.
5. Run `rag_health`.
6. Run `rebuild_rag_index` for the first index. Large vaults can take several minutes.
7. Ask the user to restart or reconnect the MCP client if new tools were just enabled.

## Suggested Commands

```bash
cd {quoted_backend_path}
uv sync
uv run obsidianrag serve --vault {quoted_vault_path} --host 127.0.0.1 --port 8000
```

If using Ollama:

```bash
ollama serve
ollama pull llama3.2
```

First index through MCP:

```text
Call tool: rebuild_rag_index
```

Semantic question through MCP:

```text
Call tool: ask_vault(question="...")
```

## Troubleshooting

- If `rag_health` fails, confirm the server is listening at `{api_url}`.
- If the server starts but is not ready, check the LLM provider and embedding model.
- If results are stale, run `rebuild_rag_index`.
- Keep the old MCP in-process semantic tools disabled unless testing legacy behavior.
"""


def _get_integration_config() -> Result[dict[str, Any]]:
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    config = get_vault_config(vault_path)
    if not config or "obsidianrag" not in enabled_tool_sets():
        return Result.fail(
            "ObsidianRAG tool set is not enabled in `.agents/vault.yaml`."
        )

    integration = config.profile.integrations.get("obsidianrag")
    if not integration:
        return Result.fail(
            "Missing `profile.integrations.obsidianrag` in `.agents/vault.yaml`."
        )

    raw_project_path = str(integration.get("project_path") or "")
    if not raw_project_path:
        return Result.fail("Missing ObsidianRAG `project_path`.")
    project_path = Path(raw_project_path)
    if not project_path.is_absolute():
        project_path = vault_path / project_path

    api_url = str(integration.get("api_url") or DEFAULT_API_URL)
    if not _is_loopback_http_url(api_url):
        return Result.fail(
            "ObsidianRAG `api_url` must be an HTTP loopback URL "
            "(127.0.0.1, localhost, or ::1)."
        )
    return Result.ok(
        {
            "vault_path": str(vault_path),
            "project_path": str(project_path),
            "api_url": api_url,
            "docs": integration.get("docs"),
        }
    )


def _is_obsidianrag_enabled() -> bool:
    return "obsidianrag" in enabled_tool_sets()


def _is_loopback_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http":
        return False
    if not parsed.hostname:
        return False
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 5,
) -> Result[dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            body = response.read().decode("utf-8")
            return Result.ok(json.loads(body) if body else {})
    except (
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
        json.JSONDecodeError,
    ) as e:
        return Result.fail(str(e))
