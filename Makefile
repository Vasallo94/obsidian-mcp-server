.PHONY: install dev test lint clean verify hooks check

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

format:
	uv run ruff check --fix .
	uv run ruff format .

verify:
	uv run python scripts/verify_agents.py
	uv run python scripts/verify_youtube.py
