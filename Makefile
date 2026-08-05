.PHONY: install dev test lint clean hooks check audit

install:
	uv sync

hooks:
	uv run pre-commit install

check:
	uv run pre-commit run --all-files

dev:
	uv run obsidian-mcp-server

test:
	uv run pytest tests/

coverage:
	uv run pytest --cov=obsidian_mcp --cov-report=term-missing tests/

lint:
	uv run ruff check .
	uv run pyright .

audit:
	uv run pip-audit

format:
	uv run ruff check --fix .
	uv run ruff format .
