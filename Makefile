.PHONY: install dev test lint clean verify

install:
	uv sync

dev:
	uv run obsidian-mcp-server

test:
	uv run pytest tests/

lint:
	uv run ruff check .
	uv run pyright .

format:
	uv run ruff check --fix .
	uv run ruff format .

verify:
	uv run python scripts/verify_agents.py
	uv run python scripts/verify_youtube.py
