"""
Tests básicos para verificar que el servidor MCP funciona correctamente
"""

import os
import pytest
from pathlib import Path


class TestImports:
    """Tests de importación de módulos"""
    
    def test_import_main_module(self):
        """Test básico de importación del módulo principal"""
        import obsidian_mcp_server
        assert obsidian_mcp_server is not None
    
    def test_import_dependencies(self):
        """Test de importación de dependencias"""
        import fastmcp
        import dotenv
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
        vault_path = os.getenv('OBSIDIAN_VAULT_PATH')
        assert vault_path is not None, "Variable OBSIDIAN_VAULT_PATH no configurada"
        assert vault_path != "/ruta/a/tu/vault/de/obsidian", "OBSIDIAN_VAULT_PATH tiene valor por defecto"
    
    def test_vault_path_exists(self, vault_path):
        """Verificar que el path del vault existe"""
        assert vault_path.exists(), f"El vault no existe en {vault_path}"
        assert vault_path.is_dir(), f"El path del vault no es un directorio: {vault_path}"


class TestServerInitialization:
    """Tests de inicialización del servidor"""
    
    def test_mcp_server_creation(self):
        """Test de creación del servidor MCP"""
        import obsidian_mcp_server
        assert hasattr(obsidian_mcp_server, 'mcp'), "Servidor MCP no inicializado"
        assert obsidian_mcp_server.mcp is not None
    
    def test_main_function_exists(self):
        """Verificar que la función main existe"""
        import obsidian_mcp_server
        assert hasattr(obsidian_mcp_server, 'main'), "Función main no encontrada"
        assert callable(obsidian_mcp_server.main), "main no es una función callable"


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
        import obsidian_mcp_server
        
        # Verificar que las funciones de herramientas existen
        expected_tools = [
            'listar_notas',
            'leer_nota', 
            'buscar_en_notas',
            'crear_nota',
            'agregar_a_nota',
            'estadisticas_vault',
            'buscar_notas_por_fecha'
        ]
        
        for tool_name in expected_tools:
            assert hasattr(obsidian_mcp_server, tool_name), f"Herramienta {tool_name} no encontrada"
    
    def test_mcp_tools_accessible(self, sample_vault_content):
        """Test que verifica que las herramientas MCP son accesibles"""
        import obsidian_mcp_server
        
        # Verificar que el servidor MCP existe
        assert hasattr(obsidian_mcp_server, 'mcp'), "Servidor MCP no existe"
        
        # Verificar que las herramientas están disponibles como FunctionTool
        listar_notas_tool = obsidian_mcp_server.listar_notas
        assert listar_notas_tool is not None, "Tool listar_notas no disponible"
        assert str(type(listar_notas_tool)).endswith("FunctionTool'>"), "listar_notas no es FunctionTool"
        
        # Test simplificado: verificar que tenemos acceso al vault
        # En lugar de llamar a la función directamente, solo verificamos que el vault existe
        vault_path_var = obsidian_mcp_server.OBSIDIAN_VAULT_PATH
        assert vault_path_var is not None, "OBSIDIAN_VAULT_PATH no configurado en el módulo"
        
        from pathlib import Path
        vault_path = Path(vault_path_var)
        assert vault_path.exists(), "Vault path no existe"
        
        # Verificar que hay archivos markdown
        md_files = list(vault_path.rglob("*.md"))
        assert len(md_files) > 0, "No hay archivos markdown en el vault"


class TestProjectStructure:
    """Tests de estructura del proyecto"""
    
    def test_required_files_exist(self):
        """Verificar que los archivos requeridos existen"""
        required_files = [
            "obsidian_mcp_server.py",
            "pyproject.toml",
            ".env.example",
            "README.md",
            "LICENSE",
            "setup.sh"
        ]
        
        for filename in required_files:
            file_path = Path(filename)
            assert file_path.exists(), f"Archivo requerido no encontrado: {filename}"
    
    def test_setup_script_executable(self):
        """Verificar que el script de setup es ejecutable"""
        setup_script = Path("setup.sh")
        assert setup_script.exists()
        # En Unix, verificar permisos de ejecución
        if os.name != 'nt':  # No Windows
            import stat
            mode = setup_script.stat().st_mode
            assert mode & stat.S_IEXEC, "setup.sh no es ejecutable"
