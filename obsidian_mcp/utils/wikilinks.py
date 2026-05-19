"""
Wikilink scanning, resolution, and rewriting.

Shared engine for issues #6 (find_broken_wikilinks), #7 (rename_note with
link updates), and #11 (move_note unresolved-reference reporting).

Naming: a "wikilink" follows Obsidian syntax — ``[[Target]]``,
``[[Target|alias]]``, ``[[Target#Section]]``. Image/file embeds
``![[file.png]]`` are intentionally excluded; they aren't note-to-note
edges and aren't covered by ``notes.rename``.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Match [[...]] but NOT ![[...]] (embeds). The negative lookbehind keeps
# the regex simple while filtering image/file transclusions.
WIKILINK_RE = re.compile(r"(?<!\!)\[\[([^\]\n]+?)\]\]")


@dataclass(frozen=True)
class WikilinkOccurrence:
    """A single ``[[...]]`` occurrence in a vault file."""

    source: Path
    line_no: int
    raw: str  # full bracket contents, e.g. "Note Name|alias"
    target: str  # the resolution target, e.g. "Note Name"
    alias: str | None
    section: str | None

    def reconstruct(self, new_target: str) -> str:
        """Build the replacement bracket contents preserving alias/section."""
        out = new_target
        if self.section:
            out += f"#{self.section}"
        if self.alias is not None:
            out += f"|{self.alias}"
        return out


@dataclass(frozen=True)
class BrokenWikilink:
    """A wikilink whose target stem doesn't exist in the vault."""

    occurrence: WikilinkOccurrence
    suggestions: tuple[str, ...]  # candidate existing stems, by similarity desc


def parse_wikilink(raw: str) -> tuple[str, str | None, str | None]:
    """Split ``raw`` (contents between ``[[`` and ``]]``) into target/section/alias."""
    alias: str | None = None
    section: str | None = None
    body = raw.strip()
    if "|" in body:
        body, alias_part = body.split("|", 1)
        alias = alias_part.strip()
        body = body.strip()
    if "#" in body:
        body, section_part = body.split("#", 1)
        section = section_part.strip()
        body = body.strip()
    return body, section, alias


def iter_wikilinks(content: str, source: Path) -> Iterable[WikilinkOccurrence]:
    """Yield every wikilink in ``content`` with its line number."""
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in WIKILINK_RE.finditer(line):
            raw = match.group(1)
            target, section, alias = parse_wikilink(raw)
            if not target:
                continue
            yield WikilinkOccurrence(
                source=source,
                line_no=line_no,
                raw=raw,
                target=target,
                alias=alias,
                section=section,
            )


def build_stem_index(vault_path: Path) -> dict[str, list[Path]]:
    """Map note stems (basename without ``.md``) to one or more vault paths.

    A stem can map to multiple paths when the vault has duplicate
    filenames in different folders; Obsidian itself disambiguates by
    full path, but for broken-link detection any match counts as
    resolution.
    """
    index: dict[str, list[Path]] = {}
    for md_file in vault_path.rglob("*.md"):
        stem = md_file.stem
        index.setdefault(stem, []).append(md_file)
    return index


def target_resolves(
    target: str, stem_index: dict[str, list[Path]], vault_path: Path
) -> bool:
    """Return True iff ``target`` matches an existing note.

    Resolution rules (in order):
    1. ``target`` is a full vault-relative path with ``.md`` -> file must exist.
    2. ``target`` is a bare stem -> stem index hit.
    3. ``target`` contains ``/`` (folder/Stem) -> resolve as ``<vault>/<target>.md``.
    """
    if target.endswith(".md"):
        candidate = vault_path / target
        return candidate.exists()
    if "/" in target:
        candidate = vault_path / f"{target}.md"
        return candidate.exists()
    return target in stem_index


def suggest_targets(
    target: str, stem_index: dict[str, list[Path]], limit: int = 3, cutoff: float = 0.6
) -> tuple[str, ...]:
    """Use difflib to find existing stems that are close to ``target``."""
    needle = target.split("/")[-1]
    stems = list(stem_index.keys())
    matches = difflib.get_close_matches(needle, stems, n=limit, cutoff=cutoff)
    return tuple(matches)


def scan_broken_wikilinks(vault_path: Path) -> list[BrokenWikilink]:
    """Walk the vault and return every wikilink that can't be resolved."""
    stem_index = build_stem_index(vault_path)
    broken: list[BrokenWikilink] = []
    for md_file in vault_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for occ in iter_wikilinks(content, md_file):
            if target_resolves(occ.target, stem_index, vault_path):
                continue
            broken.append(
                BrokenWikilink(
                    occurrence=occ,
                    suggestions=suggest_targets(occ.target, stem_index),
                )
            )
    return broken


def rewrite_wikilinks_in_content(
    content: str,
    *,
    old_target: str,
    new_target: str,
) -> tuple[str, int]:
    """Replace every ``[[old_target...]]`` with ``[[new_target...]]``.

    Aliases and sections are preserved (``[[X|alias]]`` -> ``[[Y|alias]]``,
    ``[[X#Section]]`` -> ``[[Y#Section]]``). Comparison is case-sensitive
    because Obsidian filenames are case-sensitive on Linux/macOS.

    Returns ``(new_content, replacement_count)``.
    """
    if old_target == new_target:
        return content, 0

    count = 0

    def _replace(match: re.Match) -> str:
        nonlocal count
        raw = match.group(1)
        target, section, alias = parse_wikilink(raw)
        if target != old_target:
            return match.group(0)
        count += 1
        replacement = new_target
        if section:
            replacement += f"#{section}"
        if alias is not None:
            replacement += f"|{alias}"
        return f"[[{replacement}]]"

    new_content = WIKILINK_RE.sub(_replace, content)
    return new_content, count


def rewrite_wikilinks_in_vault(
    vault_path: Path,
    *,
    old_target: str,
    new_target: str,
    dry_run: bool = False,
) -> tuple[int, list[Path]]:
    """Update every wikilink across the vault that points to ``old_target``.

    Returns ``(total_replacements, list_of_touched_files)``. When
    ``dry_run`` is True, no files are written; the return values still
    reflect what would change.
    """
    total = 0
    touched: list[Path] = []
    for md_file in vault_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        new_content, count = rewrite_wikilinks_in_content(
            content, old_target=old_target, new_target=new_target
        )
        if count == 0:
            continue
        total += count
        touched.append(md_file)
        if not dry_run:
            md_file.write_text(new_content, encoding="utf-8")
    return total, touched
