"""
Pydantic models for structured tool responses.

These models provide type-safe structures for data returned by MCP tools.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class NoteMetadata(BaseModel):
    """Metadata for a vault note."""

    name: str = Field(..., description="Full filename including extension")
    stem: str = Field(..., description="Filename without extension")
    relative_path: str = Field(..., description="Path relative to vault root")
    size_kb: float = Field(..., ge=0, description="File size in kilobytes")
    modified: str = Field(..., description="Last modified timestamp")
    created: str = Field(..., description="Creation timestamp")


class SearchResult(BaseModel):
    """A single search result from text search."""

    archivo: str = Field(..., description="File path relative to vault")
    linea: Optional[str] = Field(None, description="Line number of match")
    tipo: Optional[str] = Field(None, description="Match type (title/content)")
    coincidencia: str = Field(..., description="Matched text snippet")


class VaultStats(BaseModel):
    """Statistics for an Obsidian vault."""

    vault_name: str = Field(..., description="Name of the vault")
    vault_path: str = Field(..., description="Absolute path to vault")
    total_files: int = Field(..., ge=0, description="Total number of files")
    markdown_files: int = Field(..., ge=0, description="Number of markdown files")
    folders: int = Field(..., ge=0, description="Number of folders")
    last_scan: str = Field(..., description="ISO timestamp of last scan")
    error: Optional[str] = Field(None, description="Error message if scan failed")


class TagAnalysis(BaseModel):
    """Analysis of tags in the vault."""

    tag: str = Field(..., description="Tag name")
    count: int = Field(..., ge=0, description="Number of occurrences")
    files: List[str] = Field(
        default_factory=list,
        description="Files containing this tag",
    )


class BacklinkResult(BaseModel):
    """Result of backlink analysis."""

    source_note: str = Field(..., description="Note being linked to")
    linking_notes: List[str] = Field(
        default_factory=list,
        description="Notes that link to source",
    )
    count: int = Field(..., ge=0, description="Number of backlinks")
