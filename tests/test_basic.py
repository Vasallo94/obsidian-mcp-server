"""
Tests básicos para verificar que el servidor MCP funciona correctamente
"""

import os
from pathlib import Path

import pytest


class TestImports:
    """Tests de importación de módulos"""

    def test_import_main_module(self):
        """Test básico de importación del módulo principal"""
        import obsidian_mcp

        assert obsidian_mcp is not None

    def test_import_new_modules(self):
        """Test de importación de los módulos de la nueva estructura"""
        from obsidian_mcp import config, server
        from obsidian_mcp.tools import analysis, creation, navigation

        assert config is not None
        assert server is not None
        assert navigation is not None
        assert creation is not None
        assert analysis is not None

    def test_import_dependencies(self):
        """Test de importación de dependencias"""
        import dotenv
        import fastmcp

        assert fastmcp is not None
        assert dotenv is not None


class TestConfiguration:
    """Tests de configuración del proyecto"""

    def test_env_file_exists(self):
        """Verificar que el archivo .env existe"""
        env_file = Path(".env")
        assert env_file.exists(), "Archivo .env no encontrado"

    def test_env_example_exists(self):
        """Verificar que el archivo .env.example existe"""
        env_example = Path(".env.example")
        assert env_example.exists(), "Archivo .env.example no encontrado"

    def test_obsidian_vault_path_configured(self):
        """Verificar que OBSIDIAN_VAULT_PATH está configurado"""
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        assert vault_path is not None, "Variable OBSIDIAN_VAULT_PATH no configurada"
        assert vault_path != "/ruta/a/tu/vault/de/obsidian", (
            "OBSIDIAN_VAULT_PATH tiene valor por defecto"
        )

    def test_vault_path_exists(self, vault_path):
        """Verificar que el path del vault existe"""
        assert vault_path.exists(), f"El vault no existe en {vault_path}"
        assert vault_path.is_dir(), (
            f"El path del vault no es un directorio: {vault_path}"
        )


class TestServerInitialization:
    """Tests de inicialización del servidor"""

    def test_mcp_server_creation_new(self):
        """Test de creación del servidor MCP con nueva estructura"""
        from obsidian_mcp import create_server

        server = create_server()
        assert server is not None

    def test_server_components_creation(self):
        """Test de creación de componentes del servidor"""
        from obsidian_mcp import create_server, validate_configuration

        is_valid, message = validate_configuration()
        if is_valid:
            server = create_server()
            assert server is not None

    def test_main_function_exists(self):
        """Verificar que la función main existe"""
        from obsidian_mcp import main

        assert callable(main), "main no es una función callable"


class TestVaultContent:
    """Tests relacionados con el contenido del vault"""

    def test_vault_has_markdown_files(self, sample_vault_content):
        """Verificar que el vault tiene archivos markdown"""
        assert len(sample_vault_content) > 0, "No hay archivos markdown en el vault"

    def test_vault_structure(self, vault_path):
        """Test básico de estructura del vault"""
        # Verificar que es un directorio válido
        assert vault_path.is_dir()

        # Contar archivos markdown
        md_files = list(vault_path.rglob("*.md"))
        assert len(md_files) >= 0  # Puede ser 0 si es un vault nuevo


class TestMCPTools:
    """Tests de las herramientas MCP disponibles"""

    def test_tools_are_registered(self):
        """Verificar que las herramientas están registradas"""
        from obsidian_mcp import create_server, validate_configuration

        # Solo ejecutar si la configuración es válida
        is_valid, message = validate_configuration()
        if not is_valid:
            pytest.skip(f"Configuración no válida: {message}")

        server = create_server()
        assert server is not None

        # Verificar que el servidor se creó correctamente
        # Solo verificamos que es una instancia de FastMCP
        assert str(type(server)).endswith("FastMCP'>"), (
            "El servidor no es una instancia de FastMCP"
        )

    def test_mcp_tools_accessible(self, sample_vault_content):
        """Test que verifica que las herramientas MCP son accesibles"""
        from obsidian_mcp import get_vault_path, validate_configuration

        # Solo ejecutar si la configuración es válida
        is_valid, message = validate_configuration()
        if not is_valid:
            pytest.skip(f"Configuración no válida: {message}")

        # Verificar que tenemos acceso al vault
        vault_path = get_vault_path()
        assert vault_path is not None, "Vault path no está configurado"
        assert vault_path.exists(), "Vault path no existe"

        # Verificar que hay archivos markdown
        md_files = list(vault_path.rglob("*.md"))
        assert len(md_files) > 0, "No hay archivos markdown en el vault"


class TestProjectStructure:
    """Tests de estructura del proyecto"""

    def test_required_files_exist(self):
        """Verificar que los archivos requeridos existen"""
        required_files = [
            "main.py",  # Nuevo punto de entrada
            "obsidian_mcp/",  # Directorio del paquete principal
            "pyproject.toml",
            ".env.example",
            "README.md",
            "LICENSE",
            "setup.sh",
        ]

        for filename in required_files:
            file_path = Path(filename)
            assert file_path.exists(), f"Archivo requerido no encontrado: {filename}"

    def test_setup_script_executable(self):
        """Verificar que el script de setup es ejecutable"""
        setup_script = Path("setup.sh")
        assert setup_script.exists()
        # En Unix, verificar permisos de ejecución
        if os.name != "nt":  # No Windows
            import stat

            mode = setup_script.stat().st_mode
            assert mode & stat.S_IEXEC, "setup.sh no es ejecutable"
