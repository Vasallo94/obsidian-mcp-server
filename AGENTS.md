# AGENTS.md

Context file for AI coding agents working on this repository.

## Essential Commands

```bash
# Install dependencies (ALWAYS uv, NEVER pip)
make install          # uv sync

# Run MCP server locally
make dev              # uv run obsidian-mcp-server

# Testing
make test             # uv run pytest tests/
make coverage         # uv run pytest --cov=obsidian_mcp --cov-report=term-missing tests/

# Linting & formatting
make lint             # uv run ruff check . && uv run pyright .
make format           # uv run ruff check --fix . && uv run ruff format .

# Pre-commit hooks (ruff, pyright, pylint, bandit + general checks)
make hooks            # uv run pre-commit install
make check            # uv run pre-commit run --all-files

# Verification scripts
make verify           # uv run python scripts/verify_agents.py && scripts/verify_youtube.py
```

### Package Management — CRITICAL

- **ONLY use `uv`**, NEVER `pip` or `uv pip install`
- Add dependencies: `uv add package`
- Add dev dependencies: `uv add --dev package`
- Add optional RAG deps: `uv sync --extra rag`
- Run tools: `uv run tool`
- **FORBIDDEN**: `pip install`, `uv pip install`, `@latest` syntax

### Testing

- Framework: `pytest` with `anyio` for async tests (NOT asyncio)
- Single test: `uv run pytest tests/test_basic.py::TestClassName::test_name -v`
- Coverage: `uv run pytest tests/ --cov=obsidian_mcp`
- CI minimum coverage: **25%**
- All async tests must use `anyio` fixtures, not `asyncio`

## Architecture

### Core Concept

MCP (Model Context Protocol) server built with **FastMCP** that exposes Obsidian vault operations as tools, resources, and prompts. Acts as a bridge between AI assistants (Claude Desktop, Cursor, Claude Code, Cline, etc.) and a user's Obsidian knowledge base.

### Key Principles

1. **Vault-Agnostic**: Auto-detects vault structure. User config lives in `{vault}/.agent/vault.yaml`, not here.
2. **Skills System**: AI personas loaded from the **user's vault** at `{vault}/.agent/skills/`. Each skill has `SKILL.md` with YAML frontmatter.
3. **Separation of Concerns**: Tool registration (`tools/*.py`) → Business logic (`tools/*_logic.py`) → Utilities (`utils/*.py`).
4. **Security Model**: Path validation via `.forbidden_paths` and vault config. All file ops go through `utils/security.py`.
5. **Optional RAG**: Semantic search requires extra deps (`uv sync --extra rag`). ChromaDB-based vector indexing in `semantic/`.

### Module Organization

```
obsidian_mcp/
├── server.py              # FastMCP instance, module registration, transport config
├── config.py              # Pydantic Settings (env: OBSIDIAN_VAULT_PATH, LOG_LEVEL, etc.)
├── vault_config.py        # Loads optional .agent/vault.yaml from user's vault
├── constants.py           # Centralized magic numbers (SemanticDefaults, SearchLimits, etc.)
├── messages.py            # User-facing message templates
├── result.py              # Generic Result[T] type for consistent return values
├── tools/                 # MCP Tools organized by domain
│   ├── navigation.py      # Read, list, search notes
│   ├── navigation_logic.py
│   ├── creation.py        # Create, edit, delete, template usage
│   ├── creation_logic.py
│   ├── analysis.py        # Vault stats, tag sync, quality checks
│   ├── analysis_logic.py
│   ├── graph.py           # Backlinks, orphans, connection analysis
│   ├── graph_logic.py
│   ├── agents.py          # Skills loader (from user vault/.agent/skills/)
│   ├── agents_logic.py
│   ├── agents_generator.py # Skill generation, suggestion, and sync tools
│   ├── context.py         # Vault structure and metadata
│   ├── context_logic.py
│   ├── semantic.py        # RAG/vector search integration
│   ├── semantic_logic.py
│   ├── youtube.py         # Transcript extraction
│   └── youtube_logic.py
├── semantic/              # Optional RAG module (ChromaDB + sentence-transformers)
│   ├── indexer.py         # Embedding generation
│   ├── retriever.py       # Similarity search
│   └── service.py         # High-level RAG API
├── utils/
│   ├── logging.py         # Centralized logging (stderr only, stdout = MCP protocol)
│   ├── security.py        # Path validation, access control, directory traversal prevention
│   ├── vault.py           # Vault file operations
│   ├── mcp_ignore.py      # .mcpignore file handling
│   └── timeout.py         # Timeout utilities for long operations
├── resources/             # MCP Resources (read-only data endpoints)
├── prompts/               # MCP Prompts (system prompts for AI)
└── models/                # Pydantic models for data validation
```

### Tool Registration Pattern

```python
from fastmcp import FastMCP
from ..config import get_vault_path

def register_xxx_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def my_tool(param: str) -> str:
        """Docstring becomes tool description in MCP."""
        vault_path = get_vault_path()
        result = my_tool_logic(param, vault_path)
        return result.to_display()
```

### Result Pattern

All `*_logic.py` functions return `Result[T]` (from `result.py`):

```python
from obsidian_mcp.result import Result

def my_logic(param: str) -> Result[str]:
    if error_condition:
        return Result.fail("Error description")
    return Result.ok("Success data")

# In tool: result.to_display() for MCP output
# In tests: result.success, result.data, result.error
```

### Configuration Hierarchy

1. **Environment Variables** (`.env`):
   - `OBSIDIAN_VAULT_PATH`: Absolute path to vault (required)
   - `LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR (default: INFO)
   - `OBSIDIAN_SEARCH_TIMEOUT_SECONDS`, `OBSIDIAN_MAX_SEARCH_RESULTS`, `OBSIDIAN_CACHE_TTL_SECONDS`

2. **Vault Config** (`{vault}/.agent/vault.yaml`):
   - `templates_folder`, `excluded_folders`, `excluded_patterns`, `private_paths`

3. **Constants** (`constants.py`):
   - `SemanticDefaults`, `SearchLimits`, `FolderSuggestion`, `FileConstants`

4. **Skills & Rules** (in user's vault, NOT this repo):
   - Skills: `{vault}/.agent/skills/{name}/SKILL.md`
   - Global rules: `{vault}/.agent/REGLAS_GLOBALES.md`

## Quality & CI

### Pre-commit Hooks

Installed via `make hooks`. Runs on every commit:
- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`, `check-merge-conflict`, `debug-statements`
- **Ruff** lint + format
- **Pyright** type checking
- **Pylint** code quality (excludes `semantic/`)
- **Bandit** security analysis

### CI Pipeline (GitHub Actions)

4 parallel jobs on push/PR to `main`:

| Job | What it checks |
|---|---|
| **Lint & Format** | `ruff check .` + `ruff format --check .` |
| **Type Check** | `pyright` |
| **Security** | `bandit -c pyproject.toml -r obsidian_mcp/` |
| **Tests** | `pytest --cov --cov-fail-under=25` |

### Code Style

- Type hints **required** for all functions
- Public APIs must have docstrings
- Line length: 88 chars (Ruff enforced)
- PEP 8 naming: `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- Use f-strings, early returns, descriptive names
- Pylint config in `pyproject.toml`: max 8 args, 20 locals, 15 branches, 60 statements

### Logging

- All logs → `stderr` (stdout is MCP protocol JSON)
- Use: `from ..utils import get_logger; logger = get_logger(__name__)`
- **Never** use `print()` — it breaks MCP communication

## Dev Environment

### `.agent/` in This Repo

This repo has its own `.agent/` directory with **development-specific** guidance (separate from the user's vault `.agent/`):

- **Skills** (`.agent/skills/`): `code-quality`, `docs-updater`, `git-workflow`, `mcp-developer`, `python-patterns`, `refactoring`, `test-runner`
- **Workflows** (`.agent/workflows/`): `debug-tests`, `dev-server`, `new-tool`, `quality-check`, `quick-push`

Read these before performing related tasks. Workflows can be invoked via `/slash-command` syntax.

### Docs

Detailed documentation in `docs/`:
- `architecture.md`, `tool-reference.md`, `configuration.md`, `agent-folder-setup.md`, `semantic-search.md`, `FUTURE.md`

## Git Workflow

- Conventional commits: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`
- For bug fixes: `git commit --trailer "Reported-by:<name>"`
- For issues: `git commit --trailer "Github-Issue:#<number>"`
- **NEVER mention co-authors, AI tools, or Copilot in commits or PRs**

## Common Gotchas

1. **Skills are in the user's vault**, not this repo. The `.agent/skills/` here are for **development guidance**, not runtime skills.
2. **stdout is sacred**: Only MCP protocol JSON goes to stdout. Everything else → stderr.
3. **Path validation is critical**: Always validate through `utils/security.py` to prevent directory traversal.
4. **RAG is optional**: Handle missing `langchain` deps gracefully. Check imports and skip RAG if unavailable.
5. **`vault_config.yaml` vs `.env`**: Vault-specific settings (folders, exclusions) from vault config. Server settings (path, log level) from `.env`.
6. **Type narrowing**: Pyright is strict about `Optional`. Always check for `None` before using Optional values.
7. **Pylint pre-commit**: May block commits on pre-existing warnings. Use `--no-verify` only if warnings are not from your changes.
8. **Duplicate `torch`**: `pyproject.toml` has a duplicated `torch` entry in `[project.optional-dependencies].rag` — known issue, harmless.
