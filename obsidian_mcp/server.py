"""
Servidor MCP principal para Obsidian
Configura y ejecuta el servidor con todas las herramientas, recursos y prompts
"""

import sys
from typing import Optional

from fastmcp import FastMCP

from .config import APP_NAME, validate_configuration
from .prompts import register_assistant_prompts
from .resources import register_vault_resources
from .tools import (
    register_agent_tools,
    register_analysis_tools,
    register_context_tools,
    register_creation_tools,
    register_navigation_tools,
    register_youtube_tools,
)
from .utils import get_logger

# Configurar logging
logger = get_logger(__name__)


def create_server() -> FastMCP:
    """
    Crea y configura el servidor MCP de Obsidian

    Returns:
        Instancia configurada del servidor FastMCP

    Raises:
        ValueError: Si la configuración no es válida
    """
    # Validar configuración antes de crear el servidor
    is_valid, error_message = validate_configuration()
    if not is_valid:
        logger.error(error_message)
        raise ValueError(error_message)

    # Crear servidor
    mcp = FastMCP(APP_NAME)

    # Registrar herramientas
    logger.info("Registrando herramientas de navegación...")
    register_navigation_tools(mcp)

    logger.info("Registrando herramientas de creación...")
    register_creation_tools(mcp)

    logger.info("Registrando herramientas de análisis...")
    register_analysis_tools(mcp)

    logger.info("Registrando herramientas de YouTube...")
    register_youtube_tools(mcp)

    logger.info("Registrando herramientas de contexto...")
    register_context_tools(mcp)

    logger.info("Registrando herramientas de agentes...")
    register_agent_tools(mcp)

    # Registrar recursos
    logger.info("Registrando recursos del vault...")
    register_vault_resources(mcp)

    # Registrar prompts
    logger.info("Registrando prompts del asistente...")
    register_assistant_prompts(mcp)

    logger.info("✅ Servidor MCP configurado correctamente")
    return mcp


def run_server(
    transport: str = "stdio",
    host: Optional[str] = None,
    port: Optional[int] = None,
    path: Optional[str] = None,
) -> None:
    """
    Ejecuta el servidor MCP

    Args:
        transport: Tipo de transporte ("stdio", "http", "sse")
        host: Host para transportes HTTP/SSE
        port: Puerto para transportes HTTP/SSE
        path: Path para transporte HTTP
    """
    try:
        logger.info(f"🚀 Iniciando servidor MCP con transporte: {transport}")

        # Crear servidor
        mcp = create_server()

        # Ejecutar servidor según el transporte
        if transport == "stdio":
            mcp.run()
        elif transport == "http":
            kwargs = {}
            if host:
                kwargs["host"] = host
            if port:
                kwargs["port"] = port
            if path:
                kwargs["path"] = path
            mcp.run(transport="http", **kwargs)
        elif transport == "sse":
            kwargs = {}
            if host:
                kwargs["host"] = host
            if port:
                kwargs["port"] = port
            mcp.run(transport="sse", **kwargs)
        else:
            raise ValueError(f"Transporte no soportado: {transport}")

        logger.info("🎯 Servidor listo. Esperando conexiones...")

    except KeyboardInterrupt:
        logger.info("🛑 Servidor detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error fatal del servidor: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Función principal del servidor MCP"""
    run_server()


if __name__ == "__main__":
    main()
