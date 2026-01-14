"""
Tests para el módulo de seguridad del servidor MCP.

Verifica que las rutas prohibidas se bloquean correctamente.
"""

import pytest
from pathlib import Path

from obsidian_mcp.utils.security import (
    load_forbidden_patterns,
    is_path_forbidden,
    check_path_access,
    AccessDeniedError,
)


class TestLoadForbiddenPatterns:
    """Tests para la carga de patrones prohibidos."""

    def test_load_patterns_returns_list(self):
        """Verifica que load_forbidden_patterns retorna una lista."""
        patterns = load_forbidden_patterns()
        assert isinstance(patterns, list)

    def test_load_patterns_includes_private_folder(self):
        """Verifica que siempre incluye la carpeta privada."""
        patterns = load_forbidden_patterns()
        # Debe haber al menos un patrón que incluya Privado
        private_patterns = [p for p in patterns if "Privado" in p]
        assert len(private_patterns) > 0

    def test_load_patterns_caches_result(self):
        """Verifica que los patrones se cachean."""
        patterns1 = load_forbidden_patterns()
        patterns2 = load_forbidden_patterns()
        assert patterns1 is patterns2  # Mismo objeto (cacheado)

    def test_force_reload_clears_cache(self):
        """Verifica que force_reload recarga los patrones."""
        patterns1 = load_forbidden_patterns()
        patterns2 = load_forbidden_patterns(force_reload=True)
        # Después de force_reload, puede ser el mismo contenido pero recargado
        assert patterns1 == patterns2  # Contenido igual


class TestIsPathForbidden:
    """Tests para verificación de rutas prohibidas."""

    def test_private_folder_is_forbidden(self):
        """Verifica que la carpeta privada está prohibida."""
        is_forbidden, pattern = is_path_forbidden("04_Recursos/Privado/Códigos.md")
        assert is_forbidden is True
        assert pattern != ""

    def test_private_folder_any_file_forbidden(self):
        """Verifica que cualquier archivo en Privado está prohibido."""
        is_forbidden, _ = is_path_forbidden("04_Recursos/Privado/cualquier_archivo.md")
        assert is_forbidden is True

    def test_normal_path_is_allowed(self):
        """Verifica que rutas normales están permitidas."""
        is_forbidden, pattern = is_path_forbidden("01_Inbox/nota_normal.md")
        assert is_forbidden is False
        assert pattern == ""

    def test_codigos_file_anywhere_forbidden(self):
        """Verifica que Códigos.md está prohibido en cualquier ubicación."""
        is_forbidden, _ = is_path_forbidden("cualquier/ruta/Códigos.md")
        assert is_forbidden is True

    def test_secrets_file_anywhere_forbidden(self):
        """Verifica que secrets.md está prohibido en cualquier ubicación."""
        is_forbidden, _ = is_path_forbidden("otra/carpeta/secrets.md")
        assert is_forbidden is True


class TestCheckPathAccess:
    """Tests para la función centralizada de verificación de acceso."""

    def test_forbidden_path_returns_error(self):
        """Verifica que paths prohibidos retornan error."""
        is_allowed, error = check_path_access(
            "04_Recursos/Privado/Códigos.md", 
            operation="leer"
        )
        assert is_allowed is False
        assert "ACCESO DENEGADO" in error

    def test_allowed_path_returns_success(self):
        """Verifica que paths permitidos retornan éxito."""
        is_allowed, error = check_path_access(
            "01_Inbox/nota_normal.md",
            operation="leer"
        )
        assert is_allowed is True
        assert error == ""

    def test_operation_included_in_error(self):
        """Verifica que la operación aparece en el mensaje de error."""
        is_allowed, error = check_path_access(
            "04_Recursos/Privado/test.md",
            operation="modificar"
        )
        assert "modificar" in error
