"""MCPB entry point for the packaged Obsidian MCP server."""

from __future__ import annotations

import sys
from pathlib import Path


def _add_vendor_paths() -> None:
    bundle_root = Path(__file__).resolve().parents[1]
    vendor_path = bundle_root / "server" / "vendor"
    package_path = bundle_root / "server" / "package"
    for path in (vendor_path, package_path):
        if path.exists():
            sys.path.insert(0, str(path))


def main() -> None:
    """Load bundled dependencies and run the stdio MCP server."""
    _add_vendor_paths()
    from obsidian_mcp.server import main as run_main

    run_main()


if __name__ == "__main__":
    main()
