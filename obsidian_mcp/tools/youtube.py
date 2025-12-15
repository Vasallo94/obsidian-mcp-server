"""
Herramientas para interactuar con YouTube (obtención de transcripciones).
"""

import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


def extract_video_id(url: str) -> str:
    """
    Extrae el ID de un video de YouTube desde diferentes formatos de URL.
    """
    # Patrones comunes de URL de YouTube
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
    ]

    # Intentar parsear URL estándar primero
    parsed_url = urlparse(url)
    if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
        if parsed_url.path == "/watch":
            params = parse_qs(parsed_url.query)
            if "v" in params:
                return params["v"][0]
        if parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/shorts/")[1]

    # Intentar con regex para otros casos (youtu.be, embeds, etc)
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Si la entrada ya parece un ID (11 chars)
    if len(url) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", url):
        return url

    return ""


def get_transcript_text(url: str, language: Optional[str] = None) -> str:
    """
    Obtiene la transcripción de un video de YouTube.

    Args:
        url: URL del video de YouTube o ID del video.
        language: Código del idioma preferido. Si es None, intenta detectar
                  el idioma original o usa el generadado automáticamente.

    Returns:
        El texto completo de la transcripción o un mensaje de error.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return (
            "❌ Error: No se pudo extraer un ID de video válido "
            "de la URL proporcionada."
        )

    try:
        # Instanciar la API
        api = YouTubeTranscriptApi()

        # Obtener lista de transcripciones disponibles
        transcript_list = api.list(video_id)

        target_transcript = None

        if language:
            # Si se especificó un idioma, intentar encontrarlo (manual o generado)
            try:
                target_transcript = transcript_list.find_transcript([language])
            except Exception:
                # Si falla, intentar traducirlo
                try:
                    # Buscar cualquiera y traducir
                    # (Esto es simplificado, idealmente buscaríamos el mejor origen)
                    # Por ahora fallamos al catch general si no existe el idioma directo
                    pass
                except Exception:
                    pass
        else:
            # Lógica "Auto": Priorizar manual en idioma cualquiera, o generado.
            # Normalmente la lista viene con manuales primero o podemos iterar.

            # 1. Buscar manuales (is_generated=False)
            for t in transcript_list:
                if not t.is_generated:
                    target_transcript = t
                    break

            # 2. Si no hay manual, usar el primero (que será generado)
            if not target_transcript:
                # Iterar para tomar el primero disponible.
                # transcript_list es iterable
                for t in transcript_list:
                    target_transcript = t
                    break

        if not target_transcript:
            # Fallback a lógica antigua de "fetch" con defaults si algo falló arriba
            # aunque transcript_list debería lanzar error si está vacío.
            languages = ["es", "en"] if not language else [language]
            target_transcript = transcript_list.find_transcript(languages)

        # Hacer fetch de la transcripción seleccionada
        transcript_data = target_transcript.fetch()

        # Formatear a texto plano
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript_data)

        metadata = (
            f"Idioma: {target_transcript.language} ({target_transcript.language_code})"
        )
        if target_transcript.is_generated:
            metadata += " [Autogenerado]"
        else:
            metadata += " [Manual]"

        return (
            f"✅ Transcripción obtenida para video {video_id}\n"
            f"ℹ️ {metadata}:\n\n{text_formatted}"
        )

    except Exception as e:
        return f"❌ Error al obtener transcripción para {video_id}: {e}"


def register_youtube_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de YouTube en el servidor MCP.
    """

    @mcp.tool()
    def get_youtube_transcript(url: str, language: Optional[str] = None) -> str:
        """
        Obtiene la transcripción de un video de YouTube.

        Args:
            url: URL del video de YouTube o ID del video.
            language: Código del idioma opcional (ej: 'es', 'en').
                      Si se omite, busca subtítulos manuales en el idioma original,
                      o falla al autogenerado del video.

        Returns:
            El texto completo de la transcripción o un mensaje de error.
        """
        return get_transcript_text(url, language)
