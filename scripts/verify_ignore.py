import shutil
from pathlib import Path

from obsidian_mcp.utils.mcp_ignore import McpIgnore


def test_mcp_ignore():
    print("Testing McpIgnore...")

    # Setup dummy vault
    base_path = Path("./test_vault_ignores")
    base_path.mkdir(exist_ok=True)

    (base_path / "private").mkdir(exist_ok=True)
    (base_path / "public").mkdir(exist_ok=True)

    with open(base_path / "private" / "secret.md", "w") as f:
        f.write("secret")

    with open(base_path / "public" / "hello.md", "w") as f:
        f.write("hello")

    with open(base_path / "finance.md", "w") as f:
        f.write("money")

    # Create .mcpignore
    with open(base_path / ".mcpignore", "w") as f:
        f.write("private/\nfinance.md\n*.secret")

    # Initialize
    ignore = McpIgnore(vault_path=base_path)

    # Test cases
    cases = [
        ("public/hello.md", False),
        ("private/secret.md", True),
        ("finance.md", True),
        ("notes.secret", True),
        ("public/notes.md", False),
        (".git/config", True),  # Default ignore
    ]

    failures = 0
    for path_str, expected in cases:
        p = base_path / path_str
        ignored = ignore.is_ignored(p)
        status = "PASSED" if ignored == expected else "FAILED"
        print(f"[{status}] {path_str}: Ignored={ignored} (Expected={expected})")
        if ignored != expected:
            failures += 1

    # Cleanup
    shutil.rmtree(base_path)

    if failures == 0:
        print("\nALL TESTS PASSED")
    else:
        print(f"\n{failures} TESTS FAILED")
        exit(1)


if __name__ == "__main__":
    test_mcp_ignore()
