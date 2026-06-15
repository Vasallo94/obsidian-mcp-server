#!/usr/bin/env python3
"""
Script de diagnóstico para el servidor MCP de Obsidian
Valida la configuración y la conectividad antes de ejecutar el servidor
"""

import os
import sys
from importlib.util import find_spec
from pathlib import Path

from dotenv import load_dotenv


def diagnose_setup():
    """Diagnostica la configuración del servidor MCP"""
    print("🔍 Diagnóstico del servidor MCP para Obsidian")
    print("=" * 50)

    # Cargar variables de entorno
    load_dotenv()

    # Verificar variable de entorno
    vault_path_env = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_env:
        print("❌ ERROR: Variable OBSIDIAN_VAULT_PATH no configurada")
        print(
            "💡 Solución: Crea un archivo .env con "
            "OBSIDIAN_VAULT_PATH='/ruta/a/tu/vault'"
        )
        return False

    print(f"✅ Variable de entorno configurada: {vault_path_env}")

    # Verificar que el vault existe
    vault_path = Path(vault_path_env)
    if not vault_path.exists():
        print(f"❌ ERROR: El vault no existe en {vault_path_env}")
        print("💡 Solución: Verifica que la ruta sea correcta")
        return False

    print(f"✅ Vault encontrado: {vault_path}")

    # Verificar que es un directorio
    if not vault_path.is_dir():
        print(f"❌ ERROR: {vault_path_env} no es un directorio")
        return False

    print("✅ Es un directorio válido")

    # Contar archivos markdown
    md_files = list(vault_path.glob("**/*.md"))
    print(f"📄 Archivos markdown encontrados: {len(md_files)}")

    if len(md_files) == 0:
        print("⚠️  ADVERTENCIA: No se encontraron archivos .md en el vault")
        print("💡 Asegúrate de que esta sea la ruta correcta a tu vault de Obsidian")

    # Verificar permisos de lectura
    try:
        list(vault_path.iterdir())
        print("✅ Permisos de lectura: OK")
    except PermissionError:
        print("❌ ERROR: Sin permisos de lectura en el vault")
        return False

    # Verificar dependencias
    if find_spec("fastmcp"):
        print("✅ FastMCP instalado")
    else:
        print("❌ ERROR: FastMCP no instalado")
        print("💡 Instala las dependencias con: uv sync")
        return False

    if find_spec("dotenv"):
        print("✅ python-dotenv instalado")
    else:
        print("❌ ERROR: python-dotenv no instalado")
        print("💡 Instala las dependencias con: uv sync")
        return False

    print("\n🎉 ¡Configuración válida! El servidor debería funcionar correctamente.")
    print("\n🚀 Para ejecutar el servidor:")
    print("   uv run obsidian-mcp-server")
    print("\n💡 Nuevas funcionalidades disponibles:")
    print("   - Guardar prompts refinados en tu vault")
    print("   - Gestionar biblioteca de prompts")
    print("   - Todas las herramientas de navegación y análisis")

    return True


def main() -> int:
    """Run diagnostics and return a process exit code."""
    setup_ok = diagnose_setup()
    return 0 if setup_ok else 1


if __name__ == "__main__":
    sys.exit(main())
