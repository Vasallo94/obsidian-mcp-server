"""Pydantic input models for MCP tool schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SuggestNoteLocationInput(BaseModel):
    title: str = Field(description="Note title.")
    content: str = Field(description="Note content or representative excerpt.")
    tags: str = Field(default="", description="Comma-separated tags.")


class CreateNoteInput(BaseModel):
    title: str = Field(description="Note title.")
    content: str = Field(description="Note content.")
    folder: str = Field(default="", description="Target folder relative to the vault.")
    tags: str = Field(default="", description="Comma-separated tags.")
    template: str = Field(default="", description="Template filename.")
    creator: str = Field(default="", description="Optional creating agent name.")
    description: str = Field(default="", description="Short note description.")


class AppendToNoteInput(BaseModel):
    note_path: str = Field(description="Note path or filename.")
    content: str = Field(description="Content to insert.")
    position: str = Field(default="end", description="'end', 'start', or 'section'.")
    section: str = Field(default="", description="Section heading for section inserts.")
    create_section: bool = Field(
        default=True,
        description="Create the target section when it does not exist.",
    )


class DeleteNoteInput(BaseModel):
    note_path: str = Field(description="Note path or filename to delete.")


class EditOperation(BaseModel):
    old: str = Field(description="Exact text to replace. Must be unique.")
    new: str = Field(description="Replacement text.")


class PatchNoteInput(BaseModel):
    note_path: str = Field(description="Note path or filename to edit.")
    operations: list[EditOperation] = Field(
        min_length=1,
        description="Atomic list of exact old/new replacements.",
    )


class ReplaceNoteInput(BaseModel):
    note_path: str = Field(description="Note path or filename to replace.")
    content: str = Field(description="Full replacement content.")


class ReplaceInNotesInput(BaseModel):
    search: str = Field(description="Literal text to search for.")
    replacement: str = Field(description="Replacement text.")
    folder: str = Field(default="", description="Optional folder scope.")
    limit: int = Field(default=100, description="Maximum number of files to process.")


class QuickCaptureInput(BaseModel):
    text: str = Field(description="Content to capture.")
    tags: str = Field(default="", description="Comma-separated tags.")


class FrontmatterInput(BaseModel):
    note_path: str = Field(description="Note path or filename.")


class UpdateFrontmatterInput(BaseModel):
    note_path: str = Field(description="Note path or filename.")
    frontmatter_updates: str = Field(description="JSON object with metadata updates.")
    merge: bool = Field(default=True, description="Merge with existing frontmatter.")


class UpdateNoteTagsInput(BaseModel):
    note_path: str = Field(description="Note path or filename.")
    operation: str = Field(description="'add', 'remove', or 'set'.")
    tags: str = Field(default="", description="Comma-separated tags.")


class ReadSkillInput(BaseModel):
    name: str = Field(description="Skill folder name.")


class CreateSkillInput(BaseModel):
    name: str = Field(description="Skill identifier.")
    description: str = Field(description="Short skill description.")
    instructions: str = Field(description="Main Markdown instructions.")
    tools: str = Field(default="", description="Comma-separated tool names.")
    default_location: str = Field(default="", description="Default note folder.")


class SyncSkillsInput(BaseModel):
    update: bool = Field(default=False, description="Apply automatic fixes.")


class ListNotesInput(BaseModel):
    folder: str = Field(default="", description="Folder to list.")
    include_subfolders: bool = Field(default=True, description="Include subfolders.")


class ReadNoteInput(BaseModel):
    note_path: str = Field(description="Note path or filename.")


class SearchNotesInput(BaseModel):
    query: str = Field(description="Text to search for.")
    folder: str = Field(default="", description="Optional folder scope.")
    titles_only: bool = Field(default=False, description="Search note titles only.")


class SearchNotesByDateInput(BaseModel):
    start_date: str = Field(description="Start date in YYYY-MM-DD format.")
    end_date: str = Field(default="", description="End date in YYYY-MM-DD format.")


class MoveNoteInput(BaseModel):
    source: str = Field(description="Current note path.")
    destination: str = Field(description="New note path.")
    create_folders: bool = Field(
        default=True, description="Create destination folders."
    )


class RandomConceptInput(BaseModel):
    folder: str = Field(default="", description="Optional folder scope.")


class ReadNotesInput(BaseModel):
    paths: list[str] = Field(description="List of note paths or filenames.")


class GetNoteInfoInput(BaseModel):
    paths: list[str] = Field(description="List of note paths or filenames.")


class SyncTagRegistryInput(BaseModel):
    update: bool = Field(default=False, description="Update registry statistics.")


class SummarizeRecentActivityInput(BaseModel):
    days: int = Field(default=7, description="Number of days to inspect.")


class GetBacklinksInput(BaseModel):
    note_path: str = Field(description="Central note path or filename.")


class GetNotesByTagInput(BaseModel):
    tag: str = Field(description="Tag to search for.")


class GetLocalGraphInput(BaseModel):
    note_path: str = Field(description="Central note path or filename.")
    depth: int = Field(default=1, description="Traversal depth.")


class GetYoutubeTranscriptInput(BaseModel):
    url: str = Field(description="YouTube URL or video ID.")
    language: Optional[str] = Field(default=None, description="Optional language code.")


class SemanticSearchInput(BaseModel):
    query: str = Field(description="Question or topic to search for.")
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filter.",
    )


class IndexVaultSemanticInput(BaseModel):
    force: bool = Field(default=False, description="Rebuild the index from scratch.")


class SuggestSemanticConnectionsInput(BaseModel):
    threshold: float = Field(default=0.70, description="Minimum similarity threshold.")
    limit: int = Field(default=5, description="Maximum suggestions.")
    include_folders: Optional[list[str]] = Field(default=None, description="Folders.")
    exclude_mocs: bool = Field(default=True, description="Exclude MOC/system notes.")
    min_words: int = Field(default=150, description="Minimum note word count.")
