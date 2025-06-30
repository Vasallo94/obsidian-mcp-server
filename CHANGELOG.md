# Changelog

Todos los cambios importantes de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-06-30

### ✨ Añadido
- Servidor MCP completo para interactuar con vaults de Obsidian
- Herramientas de navegación: `listar_notas`, `leer_nota`, `buscar_en_notas`, `buscar_notas_por_fecha`
- Herramientas de creación: `crear_nota`, `agregar_a_nota`
- Herramientas de análisis: `estadisticas_vault`
- Configuración de variables de entorno con archivo `.env`
- Documentación completa con ejemplos
- Script de instalación automática (`setup.sh`)
- Tests básicos de verificación
- Soporte para Python 3.8+
- Gestión de dependencias con UV

### 🔧 Configuración
- Configuración de Claude Desktop mediante JSON
- Variables de entorno para path del vault
- Archivos de ejemplo y plantillas

### 📚 Documentación
- README completo con instrucciones de instalación
- Ejemplos de uso y configuración
- Licencia MIT incluida
- Changelog para seguimiento de versiones

### 🛡️ Seguridad
- Path del vault protegido en variables de entorno
- Archivo `.env` excluido del control de versiones
- Manejo de errores robusto

## [Unreleased]

### 🔄 En desarrollo
- Mejoras en la búsqueda de contenido
- Soporte para más tipos de archivos
- Integración con plugins de Obsidian
