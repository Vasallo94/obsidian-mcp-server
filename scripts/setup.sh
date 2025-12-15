#!/bin/bash
# Script de configuración para Obsidian MCP Server

echo "🧠 Configuración de Obsidian MCP Server"
echo "======================================"

# Verificar UV
if ! command -v uv &> /dev/null; then
    echo "❌ UV no está instalado. Instálalo desde: https://docs.astral.sh/uv/"
    exit 1
fi

echo "✅ UV encontrado"

# Instalar dependencias
echo "📦 Instalando dependencias..."
uv sync

# Configurar archivo .env si no existe
if [ ! -f .env ]; then
    echo "🔧 Configurando archivo de entorno..."
    cp .env.example .env
    echo ""
    echo "⚙️  Edita el archivo .env y configura la ruta de tu vault de Obsidian:"
    echo "   OBSIDIAN_VAULT_PATH=\"/ruta/a/tu/vault\""
    echo ""
else
    echo "✅ Archivo .env ya existe"
fi

# Verificar configuración
echo "🔍 Verificando configuración..."
if ! grep -q "OBSIDIAN_VAULT_PATH=" .env || grep -q "/ruta/a/tu/vault" .env; then
    echo "⚠️  Configura la ruta de tu vault en el archivo .env antes de continuar"
else
    echo "✅ Configuración completada"
    
    # Ejecutar tests básicos
    echo ""
    echo "🧪 Ejecutando tests de verificación..."
    if uv run pytest tests/ -v; then
        echo ""
        echo "🚀 Para iniciar el servidor:"
        echo "   uv run python obsidian_mcp_server.py"
        echo ""
        echo "📖 Consulta el README.md para configurar Claude Desktop"
    else
        echo "⚠️  Algunos tests fallaron. Revisa la configuración antes de continuar."
    fi
fi
