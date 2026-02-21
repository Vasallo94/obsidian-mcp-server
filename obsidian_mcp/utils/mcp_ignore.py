"""
Utilidad para manejar archivos ignorados (.mcpignore).
"""

from pathlib import Path
from typing import Optional

import pathspec

from ..config import get_vault_path


class McpIgnore:
    def __init__(self, vault_path: Optional[Path] = None):
        """
        Inicializa el manejador de ignore.

        Args:
            vault_path: Ruta al vault. Si es None, busca en config.
        """
        self.vault_path = vault_path or get_vault_path()
        self.spec: Optional[pathspec.PathSpec] = None
        self._load_ignore_file()

    def _load_ignore_file(self) -> None:
        """Carga el archivo .mcpignore si existe."""
        if not self.vault_path:
            return

        ignore_file = self.vault_path / ".mcpignore"
        if ignore_file.exists():
            try:
                with open(ignore_file, "r", encoding="utf-8") as f:
                    patterns = f.read().splitlines()

                # Siempre añadir archivos de sistema/ocultos comunes
                patterns.append(".git/")
                patterns.append(".DS_Store")
                patterns.append(".mcpignore")

                self.spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            except OSError as e:
                print(f"Error al cargar .mcpignore: {e}")
        else:
            # Default ignores
            self.spec = pathspec.PathSpec.from_lines(
                "gitwildmatch", [".git/", ".DS_Store", ".mcpignore"]
            )

    def is_ignored(self, path: Path) -> bool:
        """
        Verifica si un path debe ser ignorado.

        Args:
            path: Ruta absoluta o relativa al archivo/directorio.

        Returns:
            True si debe ser ignorado.
        """
        if not self.vault_path or not self.spec:
            return False

        try:
            # Asegurar path relativo para el chequeo
            if path.is_absolute():
                if str(path).startswith(str(self.vault_path)):
                    rel_path = path.relative_to(self.vault_path)
                else:
                    # Si está fuera del vault, técnicamente debería ser ignorado/
                    # prohibido pero eso es validación de seguridad aparte.
                    return False
            else:
                rel_path = path

            return self.spec.match_file(str(rel_path))
        except (ValueError, TypeError):
            return False
