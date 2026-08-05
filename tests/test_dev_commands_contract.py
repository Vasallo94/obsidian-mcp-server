"""Contracts for developer-facing commands."""

from __future__ import annotations

import re
from pathlib import Path


def test_makefile_python_script_references_exist() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    scripts = re.findall(r"uv run python (scripts/[^\s]+\.py)", makefile)

    missing = [script for script in scripts if not Path(script).is_file()]
    assert missing == []
