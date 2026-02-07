# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Essential Commands

### Development Workflow
```bash
# Install dependencies (uses uv, NEVER pip)
make install
# Alternative: uv sync

# Run the MCP server locally
make dev
# Alternative: uv run obsidian-mcp-server

# Run all tests
make test
# Alternative: uv run pytest tests/

# Run linting (Ruff + Pyright)
make lint
# Alternative: uv run ruff check . && uv run pyright .

# Auto-format code
make format
# Alternative: uv run ruff check --fix . && uv run ruff format .

# Run verification scripts
make verify
# Alternative: uv run python scripts/verify_agents.py && uv run python scripts/verify_youtube.py
```

### Package Management - CRITICAL
- **ONLY use `uv`**, NEVER `pip`
- Add dependencies: `uv add package`
- Add dev dependencies: `uv add --dev package`
- Run tools: `uv run tool`
- Upgrade: `uv add --dev package --upgrade-package package`
- **FORBIDDEN**: `uv pip install`, `@latest` syntax

### Testing
- Framework: `pytest` with `anyio` for async tests (NOT asyncio)
- Run single test: `uv run pytest tests/test_basic.py::TestClassName::test_name -v`
- Run with coverage: `uv run pytest tests/ --cov=obsidian_mcp`
- All async tests must use `anyio` fixtures, not `asyncio`

## High-Level Architecture

### Core Concept
This is an **MCP (Model Context Protocol) server** built with FastMCP that exposes Obsidian vault operations as tools, resources, and prompts. The server acts as a bridge between AI assistants (Claude Desktop, Cursor, etc.) and a user's Obsidian knowledge base.

### Key Architectural Principles

1. **Vault-Agnostic Design**: The server auto-detects vault structure rather than assuming specific folder names. Configuration lives in the user's vault at `.agent/vault.yaml`, not in this repo.

2. **Skills System**: AI personas/roles are loaded dynamically from the **user's vault** at `{vault}/.agent/skills/`, NOT from this repository. Each skill has a `SKILL.md` file with YAML frontmatter defining its capabilities.

3. **Separation of Concerns**:
   - Tools (`tools/*.py`): MCP tool registration and parameter validation
   - Logic (`tools/*_logic.py`): Core business logic, testable independently
   - Utils (`utils/*.py`): Shared utilities for file operations, logging, security

4. **Security Model**: Path validation via `.forbidden_paths` and vault config to prevent access to sensitive folders. All file operations go through security checks in `utils/security.py`.

5. **Optional RAG**: Semantic search is an optional feature requiring extra dependencies (`pip install "obsidian-mcp-server[rag]"`). ChromaDB-based vector indexing lives in `semantic/`.

### Module Organization

```
obsidian_mcp/
├── server.py              # FastMCP instance creation and module registration
├── config.py              # Pydantic Settings (env vars: OBSIDIAN_VAULT_PATH, LOG_LEVEL)
├── vault_config.py        # Loads optional .agent/vault.yaml from user's vault
├── tools/                 # MCP Tools (30+ tools organized by domain)
│   ├── navigation.py      # Read notes, list files, search
│   ├── creation.py        # Create/edit/delete notes, template usage
│   ├── analysis.py        # Vault stats, tag management, quality checks
│   ├── graph.py           # Backlinks, orphan detection, connection analysis
│   ├── agents.py          # Skills loader (reads from user's vault/.agent/skills/)
│   ├── semantic.py        # RAG/vector search integration
│   ├── context.py         # Vault structure and metadata
│   └── youtube.py         # Transcript extraction for knowledge ingestion
├── semantic/              # Optional RAG module (ChromaDB + sentence-transformers)
│   ├── indexer.py         # Embedding generation
│   ├── retriever.py       # Similarity search
│   └── service.py         # High-level RAG API
├── utils/                 # Shared utilities
│   ├── logging.py         # Centralized logging (stderr only, stdout is MCP protocol)
│   ├── security.py        # Path validation and access control
│   └── vault.py           # Vault file operations
├── resources/             # MCP Resources (read-only data endpoints)
├── prompts/               # MCP Prompts (system prompts for AI)
└── models/                # Pydantic models for data validation
```

### Tool Registration Pattern
Every tool module follows this pattern:

```python
from fastmcp import FastMCP
from ..config import get_vault_path

def register_xxx_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def my_tool(param: str) -> str:
        """Docstring becomes tool description in MCP."""
        vault_path = get_vault_path()
        # Parameter validation
        # Call logic function (testable)
        return result
```

### Configuration Hierarchy
1. **Environment Variables** (`.env`):
   - `OBSIDIAN_VAULT_PATH`: Absolute path to vault (required)
   - `LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR (default: INFO)
   - Performance settings: `SEARCH_TIMEOUT_SECONDS`, `MAX_SEARCH_RESULTS`, etc.

2. **Vault Config** (`{vault}/.agent/vault.yaml`):
   - `templates_folder`: Where templates live (auto-detected if not specified)
   - `excluded_folders`: Folders to skip in semantic search
   - `excluded_patterns`: Regex patterns for files to exclude
   - `private_paths`: Glob patterns for restricted paths

3. **Skills & Rules** (in user's vault, NOT this repo):
   - Skills: `{vault}/.agent/skills/{skill_name}/SKILL.md`
   - Global rules: `{vault}/.agent/REGLAS_GLOBALES.md`

## Code Quality Standards

### Type Hints & Documentation
- Type hints are **required** for all functions
- Public APIs must have docstrings (private helpers may skip them)
- Use Pydantic models for complex data structures
- Line length: 88 characters maximum (enforced by Ruff)

### Code Style
- PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Use f-strings for formatting, not `.format()` or `%`
- Prefer early returns over nested conditionals
- Use descriptive names (prefix handlers with "handle_")
- Keep functions small and focused

### Testing Requirements
- New features require tests
- Bug fixes require regression tests
- Use `anyio` for async tests, NOT `asyncio`
- Test edge cases and error conditions
- Tests should be isolated (use fixtures for vault setup)

### Logging
- All logs go to `stderr` (stdout is reserved for MCP protocol JSON)
- Use: `from ..utils import get_logger; logger = get_logger(__name__)`
- Never use `print()` - it breaks MCP communication

### Linting & Formatting
- Ruff handles both linting and formatting
- Type checking via Pyright (Mypy also installed but Pyright is primary)
- Run before committing: `make format && make lint`
- CI will fail on:
  - Line length violations
  - Unused imports
  - Type errors
  - Missing docstrings on public APIs

## Git Workflow

### Commits
- Use conventional commit format: `type(scope): description`
- For bug fixes from user reports: `git commit --trailer "Reported-by:<name>"`
- For GitHub issues: `git commit --trailer "Github-Issue:#<number>"`
- **NEVER mention co-authors, AI tools, or Copilot in commits**

### Pull Requests
- Focus PR description on **what** changed and **why**, not implementation details
- Always add `ArthurClune` as reviewer
- **NEVER mention co-authors, AI tools, or Copilot in PR descriptions**

## Development Philosophy

- **Simplicity over cleverness**: Write straightforward code
- **Readability first**: Code is read more than written
- **Less code = less debt**: Minimize footprint
- **Build iteratively**: Start minimal, verify it works, then add complexity
- **Test frequently**: Run tests with realistic inputs
- **Functional when clear**: Prefer functional/stateless approaches when they improve clarity
- **Push details to edges**: Keep core logic clean, implementation details at boundaries

## Common Gotchas

1. **Skills are NOT in this repo**: They're in the user's vault at `.agent/skills/`. Don't create skills here.

2. **stdout is sacred**: Only MCP protocol JSON goes to stdout. All other output (logs, debug info) must go to stderr.

3. **Path validation is critical**: Always validate paths through `utils/security.py` to prevent directory traversal attacks.

4. **RAG is optional**: Code must handle missing `langchain` dependencies gracefully. Check imports and skip RAG features if not available.

5. **vault_config.yaml vs .env**: Operational settings (folder names, exclusions) come from vault config. Server-level settings (vault path, log level) come from .env.

6. **Type narrowing**: Pyright is strict about Optional types. Always check for None before using values from Optional types.
