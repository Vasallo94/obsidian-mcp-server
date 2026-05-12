"""Tests for MCP server security utilities."""

from obsidian_mcp.utils.security import (
    check_path_access,
    is_path_forbidden,
    load_forbidden_patterns,
)


class TestLoadForbiddenPatterns:
    """Tests for forbidden pattern loading."""

    def test_load_patterns_returns_list(self):
        """load_forbidden_patterns returns a list."""
        patterns = load_forbidden_patterns()
        assert isinstance(patterns, list)

    def test_load_patterns_includes_private_folder(self):
        """The default private folder is included."""
        patterns = load_forbidden_patterns()
        private_patterns = [p for p in patterns if "Privado" in p]
        assert len(private_patterns) > 0

    def test_load_patterns_caches_result(self):
        """Forbidden patterns are cached."""
        patterns1 = load_forbidden_patterns()
        patterns2 = load_forbidden_patterns()
        assert patterns1 is patterns2  # Mismo objeto (cacheado)

    def test_force_reload_clears_cache(self):
        """force_reload refreshes the pattern list."""
        patterns1 = load_forbidden_patterns()
        patterns2 = load_forbidden_patterns(force_reload=True)
        assert patterns1 == patterns2


class TestIsPathForbidden:
    """Tests for forbidden path checks."""

    def test_private_folder_is_forbidden(self):
        """Private folders are forbidden."""
        is_forbidden, pattern = is_path_forbidden("04_Recursos/Privado/Códigos.md")
        assert is_forbidden is True
        assert pattern != ""

    def test_private_folder_any_file_forbidden(self):
        """Any file in Privado is forbidden."""
        is_forbidden, _ = is_path_forbidden("04_Recursos/Privado/cualquier_archivo.md")
        assert is_forbidden is True

    def test_normal_path_is_allowed(self):
        """Normal note paths are allowed."""
        is_forbidden, pattern = is_path_forbidden("01_Inbox/nota_normal.md")
        assert is_forbidden is False
        assert pattern == ""

    def test_codigos_file_anywhere_forbidden(self):
        """Códigos.md is forbidden anywhere."""
        is_forbidden, _ = is_path_forbidden("cualquier/ruta/Códigos.md")
        assert is_forbidden is True

    def test_secrets_file_anywhere_forbidden(self):
        """secrets.md is forbidden anywhere."""
        is_forbidden, _ = is_path_forbidden("otra/carpeta/secrets.md")
        assert is_forbidden is True


class TestCheckPathAccess:
    """Tests for centralized access checks."""

    def test_forbidden_path_returns_error(self):
        """Forbidden paths return an error."""
        is_allowed, error = check_path_access(
            "04_Recursos/Privado/Códigos.md", operation="read"
        )
        assert is_allowed is False
        assert "Access denied" in error

    def test_allowed_path_returns_success(self):
        """Allowed paths pass."""
        is_allowed, error = check_path_access(
            "01_Inbox/nota_normal.md", operation="read"
        )
        assert is_allowed is True
        assert error == ""

    def test_operation_included_in_error(self):
        """The requested operation appears in the denial message."""
        _, error = check_path_access("04_Recursos/Privado/test.md", operation="modify")
        assert "modify" in error
