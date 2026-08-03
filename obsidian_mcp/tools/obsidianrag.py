"""ObsidianRAG integration tools."""

from __future__ import annotations

import json
import shlex
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
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

    @register_tool(mcp, "rag.setup_status")
    def rag_setup_status() -> str:
        """
        Inspect local ObsidianRAG setup status.

        Checks profile config, project path, CLI availability, Ollama availability,
        and whether the ObsidianRAG API is reachable.
        """
        return get_rag_setup_status().to_display()

    @register_tool(mcp, "rag.health")
    def rag_health() -> str:
        """
        Check whether the ObsidianRAG backend is reachable and ready.
        """
        return check_rag_health().to_display()

    @register_tool(mcp, "rag.ask")
    def ask_vault(question: str, session_id: str | None = None) -> str:
        """
        Ask a natural-language question against the Obsidian vault via ObsidianRAG.

        Args:
            question: User question to answer from vault context.
            session_id: Optional ObsidianRAG conversation session ID.
        """
        return ask_rag(question, session_id).to_display()

    @register_tool(mcp, "rag.rebuild_index")
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

    ollama_tags = _request_json("GET", "http://127.0.0.1:11434/api/tags")
    checks.append(
        ("ollama_api_reachable", ollama_tags.success, "http://127.0.0.1:11434")
    )
    health = _request_json("GET", f"{data['api_url'].rstrip('/')}/health")
    checks.append(("api_reachable", health.success, str(data["api_url"])))

    output = "# ObsidianRAG Setup Status\n\n"
    output += "\n".join(
        f"- {'✅' if ok else '❌'} `{name}`: {detail}" for name, ok, detail in checks
    )
    output += "\n\n## Next Actions\n"
    if health.success:
        output += (
            "- ObsidianRAG is reachable. Use `rag.ask` for semantic vault questions.\n"
        )
        output += "- Run `rag.rebuild_index` after big vault reorganizations.\n"
    else:
        output += "- Read `obsidian://integrations/obsidianrag/setup`.\n"
        output += "- Start Ollama or another supported LLM provider.\n"
        output += "- Start ObsidianRAG with the command shown in the setup resource.\n"
        output += (
            "- Reconnect the MCP client after enabling the `obsidianrag` tool set.\n"
        )
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

    api_url = str(data["api_url"]).rstrip("/")
    result = _request_json("POST", f"{api_url}/ask", payload, timeout=120)
    if not result.success:
        return Result.fail(
            f"ObsidianRAG query failed: the backend at {api_url} is unreachable. "
            "Start it (see `obsidian://integrations/obsidianrag/setup`) and "
            "verify with `rag.health`."
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
    api_url = str(data["api_url"]).rstrip("/")
    result = _request_json("POST", f"{api_url}/rebuild_db", timeout=1800)
    if not result.success:
        return Result.fail(
            f"Could not rebuild ObsidianRAG index: the backend at {api_url} is "
            "unreachable. Start it (see "
            "`obsidian://integrations/obsidianrag/setup`) and verify with "
            "`rag.health` first."
        )
    return Result.ok(json.dumps(result.data, ensure_ascii=False, indent=2))


def build_obsidianrag_config_resource() -> str:
    """Return safe ObsidianRAG integration config."""
    config = _get_integration_config()
    if not config.success:
        return json.dumps(
            {"enabled": False, "error": config.error}, ensure_ascii=False, indent=2
        )
    data = dict(config.data or {})
    data.pop("env", None)
    return json.dumps({"enabled": True, **data}, ensure_ascii=False, indent=2)


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
    raw_env = data.get("env")
    env_vars = _safe_env_vars(raw_env)
    sensitive_env_names = _sensitive_env_names(raw_env)
    omitted_env_notice = (
        "Sensitive variables configured but omitted: "
        + ", ".join(f"`{name}`" for name in sensitive_env_names)
        + ". Set them securely in the parent shell before running these commands."
        if sensitive_env_names
        else "No secret-like integration variables are configured."
    )
    quoted_backend_path = shlex.quote(str(backend_path))
    quoted_vault_path = shlex.quote(vault_path)
    env_prefix = " ".join(
        f"{name}={shlex.quote(value)}" for name, value in sorted(env_vars.items())
    )
    uv_run_prefix = f"{env_prefix} uv run" if env_prefix else "uv run"
    uv_sync_prefix = f"{env_prefix} uv sync" if env_prefix else "uv sync"

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

1. Run `rag.setup_status`.
2. Run `client.roots` to confirm the client exposes the expected workspace roots.
3. If Ollama is missing, help the user install/start Ollama and pull a local model.
4. Install backend dependencies from the ObsidianRAG backend folder.
5. Start the backend.
6. Run `rag.health`.
7. Run `rag.rebuild_index` for the first index. Large vaults can take several minutes.
8. Ask the user to restart or reconnect the MCP client if new tools were just enabled.

## Environment

The vault profile may declare integration environment variables under
`profile.integrations.obsidianrag.env`. Secret-like values are never surfaced.
{omitted_env_notice}

```bash
{_format_env_export(env_vars)}
```

## Suggested Commands

```bash
cd {quoted_backend_path}
{uv_sync_prefix}
{uv_run_prefix} obsidianrag serve --vault {quoted_vault_path} --host 127.0.0.1 --port 8000
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

- If `rag.health` fails, confirm the server is listening at `{api_url}`.
- If the server starts but is not ready, check the LLM provider and embedding model.
- If results are stale, run `rag.rebuild_index`.
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
            "env": integration.get("env") or {},
        }
    )


def _is_obsidianrag_enabled() -> bool:
    return "obsidianrag" in enabled_tool_sets()


def _is_loopback_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http":
        return False
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
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


def _valid_env_name(name: str) -> bool:
    return name.replace("_", "").isalnum() and name.upper() == name


def _is_sensitive_env(name: str, value: str) -> bool:
    sensitive_parts = {
        "APIKEY",
        "AUTH",
        "AUTHORIZATION",
        "BEARER",
        "COOKIE",
        "CRED",
        "CREDENTIAL",
        "DSN",
        "KEY",
        "PASSWD",
        "PASSWORD",
        "PWD",
        "SALT",
        "SECRET",
        "SESSION",
        "SIGNATURE",
        "TOKEN",
    }
    name_parts = {part.rstrip("S") for part in name.split("_")}
    if sensitive_parts.intersection(name_parts):
        return True
    if name in {"DATABASE_URL", "MONGO_URL", "REDIS_URL"}:
        return True
    parsed = urllib.parse.urlparse(value)
    return parsed.username is not None or parsed.password is not None


def _safe_env_vars(raw_env: Any) -> dict[str, str]:
    """Return non-secret shell-safe environment values from integration config."""
    if not isinstance(raw_env, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, value in raw_env.items():
        name = str(key)
        if value is None or not _valid_env_name(name):
            continue
        text = str(value)
        if not _is_sensitive_env(name, text):
            result[name] = text
    return result


def _sensitive_env_names(raw_env: Any) -> list[str]:
    """Return safe variable names whose values were omitted from resources."""
    if not isinstance(raw_env, Mapping):
        return []
    names = []
    for key, value in raw_env.items():
        name = str(key)
        if (
            value is not None
            and _valid_env_name(name)
            and _is_sensitive_env(name, str(value))
        ):
            names.append(name)
    return sorted(names)


def _format_env_export(env_vars: dict[str, str]) -> str:
    if not env_vars:
        return "# No integration-specific environment variables declared."
    return "\n".join(
        f"export {name}={shlex.quote(value)}"
        for name, value in sorted(env_vars.items())
    )
