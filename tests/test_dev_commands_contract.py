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
