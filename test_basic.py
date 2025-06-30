#!/usr/bin/env python3
"""
Tests básicos para verificar que el servidor MCP funciona correctamente
"""

import os
import sys
from pathlib import Path

# Agregar el directorio actual al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent))

def test_import():
    """Test básico de importación"""
    try:
        import obsidian_mcp_server
        print("✅ Import del módulo exitoso")
        return True
    except Exception as e:
        print(f"❌ Error al importar módulo: {e}")
        return False

def test_env_config():
    """Test de configuración de variables de entorno"""
    # Cargar .env si existe
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
        
        vault_path = os.getenv('OBSIDIAN_VAULT_PATH')
        if vault_path:
            print(f"✅ Variable OBSIDIAN_VAULT_PATH configurada: {vault_path}")
            
            # Verificar que el path existe
            if Path(vault_path).exists():
                print("✅ Path del vault existe")
                return True
            else:
                print(f"⚠️  Path del vault no existe: {vault_path}")
                return False
        else:
            print("❌ Variable OBSIDIAN_VAULT_PATH no configurada")
            return False
    else:
        print("⚠️  Archivo .env no encontrado")
        return False

def test_dependencies():
    """Test de dependencias"""
    try:
        import fastmcp
        import dotenv
        print("✅ Todas las dependencias están disponibles")
        return True
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🧪 Ejecutando tests básicos del Obsidian MCP Server")
    print("=" * 50)
    
    tests = [
        ("Importación del módulo", test_import),
        ("Configuración de entorno", test_env_config),
        ("Verificación de dependencias", test_dependencies)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n🔍 Test: {name}")
        if test_func():
            passed += 1
    
    print(f"\n{'=' * 50}")
    print(f"📊 Resultados: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("🎉 ¡Todos los tests pasaron! El servidor está listo para usar.")
        return True
    else:
        print("⚠️  Algunos tests fallaron. Revisa la configuración.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
