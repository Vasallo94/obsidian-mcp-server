"""
Core business logic for YouTube tools.

This module handles video ID extraction and fetching using the Result pattern.
"""

import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from ..result import Result


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from various URL formats.

    Returns:
        Video ID string or empty string if not found.
    """
    # Common YouTube URL patterns
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
    ]

    # Try standard URL parsing first
    parsed_url = urlparse(url)
    if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
        if parsed_url.path == "/watch":
            params = parse_qs(parsed_url.query)
            if "v" in params:
                return params["v"][0]
        if parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/shorts/")[1]

    # Try regex for other cases (youtu.be, embeds, etc)
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If input looks like an ID (11 chars)
    if len(url) == 11 and re.match(r"^[0-9A-Za-z_-]{11}$", url):
        return url

    return ""


def get_transcript_text(url: str, language: Optional[str] = None) -> Result[str]:
    """
    Get the transcript of a YouTube video.

    Args:
        url: YouTube video URL or ID.
        language: Preferred language code. If None, attemps to detect original logic.

    Returns:
        Result with full transcript text or error message.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return Result.fail(
            "No se pudo extraer un ID de video válido de la URL proporcionada."
        )

    try:
        # Instantiate API
        api = YouTubeTranscriptApi()

        # Get available transcripts list
        transcript_list = api.list(video_id)

        target_transcript = None

        if language:
            # If language specified, try to find it
            try:
                target_transcript = transcript_list.find_transcript([language])
            except Exception:
                # If fails, could try translation logic here (omitted for now)
                pass
        else:
            # Auto logic: Prioritize manual, then generated
            # 1. Search for manuals (is_generated=False)
            for t in transcript_list:
                if not t.is_generated:
                    target_transcript = t
                    break

            # 2. If no manual, use first available (likely generated)
            if not target_transcript:
                for t in transcript_list:
                    target_transcript = t
                    break

        if not target_transcript:
            # Fallback logic
            languages = ["es", "en"] if not language else [language]
            target_transcript = transcript_list.find_transcript(languages)

        # Fetch transcript
        transcript_data = target_transcript.fetch()

        # Format to plain text
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript_data)

        metadata = (
            f"Idioma: {target_transcript.language} ({target_transcript.language_code})"
        )
        if target_transcript.is_generated:
            metadata += " [Autogenerado]"
        else:
            metadata += " [Manual]"

        return Result.ok(
            f"✅ Transcripción obtenida para video {video_id}\n"
            f"ℹ️ {metadata}:\n\n{text_formatted}"
        )

    except Exception as e:
        return Result.fail(f"Error al obtener transcripción para {video_id}: {e}")
