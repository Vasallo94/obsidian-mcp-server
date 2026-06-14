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
