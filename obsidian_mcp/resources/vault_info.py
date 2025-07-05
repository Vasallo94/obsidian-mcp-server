"""
Recurso de información del vault para el servidor MCP de Obsidian
"""

import json
from datetime import datetime

from fastmcp import FastMCP

from ..utils import get_vault_stats


def register_vault_resources(mcp: FastMCP) -> None:
    """
    Registra recursos relacionados con información del vault
    
    Args:
        mcp: Instancia del servidor FastMCP
    """
    
    @mcp.resource("obsidian://vault_info")
    async def info_vault() -> str:
        """Información general del vault de Obsidian"""
        try:
            info = get_vault_stats()
            return json.dumps(info, indent=2, ensure_ascii=False)
        except Exception as e:
            error_info = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(error_info, indent=2, ensure_ascii=False)
