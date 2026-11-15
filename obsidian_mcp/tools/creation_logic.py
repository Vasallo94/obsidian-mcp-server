"""
Core business logic for creation tools.

This module contains the actual implementation of note creation operations,
separated from the MCP tool registration to improve testability and
maintain single responsibility.

All functions return Result[str] for consistent error handling.
"""

# pylint: disable=too-many-lines

import difflib
import json
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from ..config import get_vault_path
from ..middleware import blocking_violations, load_vault_rules
from ..result import Result
from ..utils import (
    atomic_write_text,
    check_path_access,
    find_note_by_name,
    get_logger,
    iter_safe_vault_files,
    resolve_vault_path,
    sanitize_filename,
)
from ..vault_config import get_vault_config, nfc, resolve_role


def _json_serial(obj: Any) -> str:
    """JSON serializer for objects not handled by default json module."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


logger = get_logger(__name__)

# "Plantillas", "_templates", "99 Templates": not "Contemplates".
_TEMPLATE_WORD_RE = re.compile(r"(?<![^\W\d_])(?:plantilla|template)[sr]?(?![^\W\d_])")
# Group 2 is optional so an empty block ("---\n---\n") ends at its own close.
_FRONTMATTER_BLOCK_RE = re.compile(r"^(---\s*\n)((?:.*?\n)??)(---\s*\n)", re.DOTALL)


def _normalize_frontmatter(content: str) -> str:
    """Re-parse frontmatter through yaml round-trip to eliminate duplicate keys.

    LLM clients sometimes generate YAML with repeated keys (e.g. two
    ``created:`` lines).  ``yaml.safe_load`` silently keeps the last
    value for each key; ``yaml.dump`` serialises the clean dict back.
    """
    match = _FRONTMATTER_BLOCK_RE.match(content)
    if not match:
        return content

    raw_yaml = match.group(2)
    try:
        parsed = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return content

    if not isinstance(parsed, dict):
        return content

    clean_yaml = yaml.dump(
        parsed,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    return f"---\n{clean_yaml}---\n{content[match.end() :]}"


def _process_date_placeholders(content: str, date_obj: datetime | None = None) -> str:
    """
    Process date placeholders in content.

    Supports formats:
    - {{date}} or {{fecha}} -> YYYY-MM-DD
    - {{date:FORMAT}} -> Custom Moment.js-style format
    """
    if date_obj is None:
        date_obj = datetime.now()

    format_map = [
        ("YYYY", "%Y"),
        ("YY", "%y"),
        ("MMMM", "%B"),
        ("MMM", "%b"),
        ("MM", "%m"),
        ("M", "%-m" if hasattr(datetime, "strftime") else "%m"),
        ("dddd", "%A"),
        ("ddd", "%a"),
        ("DD", "%d"),
        ("D", "%-d" if hasattr(datetime, "strftime") else "%d"),
        ("HH", "%H"),
        ("mm", "%M"),
        ("ss", "%S"),
    ]

    meses_es = {
        "January": "Enero",
        "February": "Febrero",
        "March": "Marzo",
        "April": "Abril",
        "May": "Mayo",
        "June": "Junio",
        "July": "Julio",
        "August": "Agosto",
        "September": "Septiembre",
        "October": "Octubre",
        "November": "Noviembre",
        "December": "Diciembre",
        "Jan": "Ene",
        "Feb": "Feb",
        "Mar": "Mar",
        "Apr": "Abr",
        "Jun": "Jun",
        "Jul": "Jul",
        "Aug": "Ago",
        "Sep": "Sep",
        "Oct": "Oct",
        "Nov": "Nov",
        "Dec": "Dic",
    }
    dias_es = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
        "Mon": "Lun",
        "Tue": "Mar",
        "Wed": "Mié",
        "Thu": "Jue",
        "Fri": "Vie",
        "Sat": "Sáb",
        "Sun": "Dom",
    }

    def convert_format(moment_format: str) -> str:
        result = moment_format
        for moment, strftime in format_map:
            result = result.replace(moment, strftime)
        try:
            formatted = date_obj.strftime(result)
            for en, es in meses_es.items():
                formatted = formatted.replace(en, es)
            for en, es in dias_es.items():
                formatted = formatted.replace(en, es)
            return formatted
        except ValueError:
            return moment_format

    pattern_with_format = re.compile(r"\{\{(?:date|fecha):([^}]+)\}\}")

    def replace_with_format(match: re.Match) -> str:
        formato = match.group(1)
        return convert_format(formato)

    content = pattern_with_format.sub(replace_with_format, content)
    simple_date = date_obj.strftime("%Y-%m-%d")
    content = re.sub(r"\{\{(?:date|fecha)\}\}", simple_date, content)

    content = re.sub(
        r'(created:\s*["\']?)YYYY-MM-DD(["\']?)',
        rf"\g<1>{simple_date}\g<2>",
        content,
    )
    content = re.sub(
        r'(updated:\s*["\']?)YYYY-MM-DD(["\']?)',
        rf"\g<1>{simple_date}\g<2>",
        content,
    )

    return content


def _suggest_close_matches(
    needle: str, haystack: str, max_suggestions: int = 3, cutoff: float = 0.6
) -> list[str]:
    """Find lines or line-windows in ``haystack`` that look like ``needle``.

    Used by ``edit_note`` when an exact-match ``old`` text isn't found, so
    the agent gets actionable suggestions instead of guessing emoji
    codepoints or whitespace variants (Issue #8).

    Returns up to ``max_suggestions`` candidate strings, ordered by
    similarity. Empty list if nothing crosses the ``cutoff`` ratio.
    """
    if not needle.strip() or not haystack:
        return []

    needle_lines = needle.splitlines() or [needle]
    haystack_lines = haystack.splitlines()
    window = len(needle_lines)

    if window == 1:
        candidates = haystack_lines
    else:
        candidates = [
            "\n".join(haystack_lines[i : i + window])
            for i in range(len(haystack_lines) - window + 1)
        ]

    matcher = difflib.SequenceMatcher(autojunk=False)
    matcher.set_seq2(needle)
    scored: list[tuple[float, str]] = []
    for cand in candidates:
        if not cand.strip() or cand == needle:
            continue
        matcher.set_seq1(cand)
        ratio = matcher.ratio()
        if ratio >= cutoff:
            scored.append((ratio, cand))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [cand for _, cand in scored[:max_suggestions]]


def _extract_frontmatter_from_content(contenido: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter from content if it exists.

    A leading ``---`` block that parses as a mapping is frontmatter, even
    with blank lines inside: the Kanban and Excalidraw plugins write
    ``---``, a blank line, then the keys. A horizontal rule that happens to
    wrap ``key: value`` text is indistinguishable and is read the same way.
    """
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
    match = frontmatter_pattern.match(contenido)
    if not match:
        return {}, contenido

    try:
        yaml_content = match.group(1)
        metadata = yaml.safe_load(yaml_content) or {}
        if not isinstance(metadata, dict):
            return {}, contenido
        contenido_limpio = contenido[match.end() :]
        return metadata, contenido_limpio.lstrip()
    except yaml.YAMLError:
        return {}, contenido


_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(\S(?:.*\S)?)[ \t]*$")
# Fence run plus the rest of the line; `.*` always matches, so no backtracking.
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)")
# Markers that can hide what follows them (Obsidian comments, HTML).
_OPAQUE_MARKERS = ("<!--", "%%", "<details")


def _strip_inline_code(line: str) -> str:
    """Drop `code spans` from one line (a run closes at the next run of equal length).

    Linear: a regex with a backreference backtracks quadratically on long
    backtick runs. A span crossing lines is left as prose, the safe side.
    """
    if "`" not in line or "\\`" in line:
        return line  # an escaped backtick: keep it all as prose, the safe side
    runs = list(re.finditer(r"`+", line))
    closer: dict[int, int] = {}  # run index -> next run index of equal length
    last: dict[int, int] = {}
    for k in range(len(runs) - 1, -1, -1):
        size = len(runs[k].group())
        if size in last:
            closer[k] = last[size]
        last[size] = k
    out, pos, k = [], 0, 0
    while k < len(runs):
        if k in closer:
            out.append(line[pos : runs[k].start()])
            pos, k = runs[closer[k]].end(), closer[k] + 1
        else:
            k += 1
    return "".join(out) + line[pos:]


def _fence_open(line: str) -> str:
    """Return the fence a line opens, or "" (CommonMark rules)."""
    opened = _FENCE_OPEN_RE.match(line)
    if not opened:
        return ""
    fence, info = opened.groups()
    # A backtick fence's info string can't contain backticks (```npm i``` is code).
    return "" if fence[0] == "`" and "`" in info else fence


def _split_markdown(
    text: str,
) -> tuple[str | None, str, list[tuple[tuple[int, str], str]], bool]:
    """Split Markdown into (title, intro, sections, unsafe_to_merge).

    ``title`` is a leading H1 (nothing but blank lines before it). Sections
    are cut at the shallowest heading level left, so each one carries its
    subsections; the key is (level, heading text in NFC, casefolded).
    Headings inside code fences don't count (CommonMark closing rules).
    ``unsafe_to_merge`` is true when the text ends inside a fence or has a
    comment or ``<details>`` outside code, which could swallow what follows.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    heads: list[tuple[int, int, str]] = []
    fence = ""
    opaque = False
    for i, line in enumerate(lines):
        if fence:
            if re.match(rf"^ {{0,3}}{fence[0]}{{{len(fence)},}}[ \t]*$", line):
                fence = ""
            continue
        prose = _strip_inline_code(line)
        opaque = opaque or any(m in prose for m in _OPAQUE_MARKERS)
        if opened := _fence_open(line):
            fence = opened
        elif heading := _HEADING_RE.match(line):
            words = heading.group(2)
            closing = words.rstrip("#")  # `## X ##`; rstrip, a regex is quadratic
            if closing != words and closing[-1:] in (" ", "\t"):
                words = closing.rstrip(" \t")
            words = words.strip("*_ ").rstrip(":").strip("*_ ")
            heads.append((i, len(heading.group(1)), words))
    title, start = None, 0
    if heads and heads[0][1] == 1 and not "".join(lines[: heads[0][0]]).strip():
        title, start = lines[heads[0][0]].strip(), heads[0][0] + 1
        heads = heads[1:]
    unsafe = bool(fence) or opaque
    if not heads:
        return title, "\n".join(lines[start:]), [], unsafe
    top = min(level for _, level, _ in heads)
    cuts = [(i, words) for i, level, words in heads if level == top]
    sections = [
        (
            (top, nfc(words).casefold()),
            "\n".join(lines[i : cuts[n + 1][0] if n + 1 < len(cuts) else None]),
        )
        for n, (i, words) in enumerate(cuts)
    ]
    return title, "\n".join(lines[start : cuts[0][0]]), sections, unsafe


def _shift_headings(block: str, delta: int) -> str:
    """Move every heading of ``block`` (outside code fences) by ``delta`` levels."""
    out, fence = [], ""
    for line in block.split("\n"):
        if fence:
            if re.match(rf"^ {{0,3}}{fence[0]}{{{len(fence)},}}[ \t]*$", line):
                fence = ""
        elif opened := _fence_open(line):
            fence = opened
        elif heading := _HEADING_RE.match(line):
            level = min(6, max(1, len(heading.group(1)) + delta))
            line = "#" * level + line[heading.end(1) :]
        out.append(line)
    return "\n".join(out)


def _place_content(template_body: str, content: str) -> str:
    """Return the note body merging the caller's content into the template.

    Nothing of the template is dropped except what the content replaces: a
    leading H1 in the content replaces the template's; a content section
    (with its subsections) replaces, in place, the template section with the
    same heading, even if the content wrote it one level off (it takes the
    template's level); a new section goes right after the matched section
    that precedes it in the content, or under the title and the template's
    intro.
    """
    if not content.strip():
        return template_body
    c_title, c_intro, c_sections, unsafe = _split_markdown(content)
    if unsafe:
        # ponytail: a comment or an unclosed fence could swallow the template
        # sections placed after it; such content is appended as is instead.
        blocks = [template_body, content]
    else:
        t_title, t_intro, t_sections, _ = _split_markdown(template_body)
        # Match by heading text; a content section at another level is
        # re-levelled to the template's ("### Notas" fills "## Notas").
        template_levels = {words: level for (level, words), _ in t_sections}
        replacements: dict[tuple[int, str], list[str]] = {}
        # New sections follow the last matched section before them in the
        # content (None: none yet, so they go under the intro).
        after: dict[tuple[int, str] | None, list[str]] = {}
        anchor: tuple[int, str] | None = None
        for (level, words), text in c_sections:
            if words in template_levels:
                key = (template_levels[words], words)
                if key[0] != level:
                    text = _shift_headings(text, key[0] - level)
                replacements.setdefault(key, []).append(text)
                anchor = key
            else:
                after.setdefault(anchor, []).append(text)
        blocks = [c_title or t_title or "", t_intro, c_intro, *after.pop(None, [])]
        for key, text in t_sections:
            blocks.extend(replacements.pop(key, [text]))
            blocks.extend(after.pop(key, []))
    return "\n\n".join(b.strip("\n") for b in blocks if b.strip()) + "\n"


_INDEX_NAMES = ("índice.md", "indice.md", "index.md")
_INDEX_SECTION = "Por clasificar"


def _is_index_note(path: Path) -> bool:
    """An index is `Índice.md`/`index.md` or a note whose name ends in "MOC"."""
    name = nfc(path.name).casefold()
    return name in _INDEX_NAMES or name.removesuffix(".md").endswith("moc")


def link_from_index(  # pylint: disable=too-many-locals,too-many-branches,too-many-return-statements
    note_path: Path, vault_path: Path, description: str = ""
) -> str:
    """Link a new note from the index of its folder; return the index's path.

    The index is the nearest one going up from the note's folder (never the
    vault root). The link goes to a "## Por clasificar" section, created
    right before the index's first H2 so it stays above any footer. Returns
    "" when there is no index, the note is an index itself, the index is
    protected or already links the note, the note's name can't be a wikilink
    target, or either lives in the templates folder or a hidden one (a
    template "MOC.md" is not an index: linking would bake the link into
    every note made from it).
    """
    vault_root = vault_path.resolve()
    stem = nfc(note_path.stem)
    if _is_index_note(note_path) or any(c in stem for c in "#|[]^"):
        return ""
    templates = find_templates_folder(vault_path, get_vault_config(vault_path))
    templates_root = (vault_root / templates).resolve() if templates else None
    # Judged on the configured text, not the resolved path: a templates
    # folder symlinked to a shared folder outside the vault is still valid.
    configured = Path(os.path.normpath(vault_root / templates)) if templates else None
    if configured and vault_root not in configured.parents:
        # "." or a path outside the vault would turn the exclusion off: refuse
        # to link rather than bake a link into every template.
        logger.warning("templates_folder %r no es una subcarpeta del vault", templates)
        return ""
    # Compared as NFC casefolded parts: APFS ignores case, resolve() keeps it.
    templates_parts = (
        [nfc(part).casefold() for part in templates_root.relative_to(vault_root).parts]
        if templates_root and vault_root in templates_root.parents
        else []
    )

    def excluded(path: Path) -> bool:
        path = path.resolve()  # an index may be a symlink into the templates
        if vault_root not in path.parents:
            return True
        folders = [
            nfc(part).casefold() for part in path.relative_to(vault_root).parts[:-1]
        ]
        # Hidden folders, the configured templates folder and any folder named
        # like one (a nested "Sistema/Plantillas" isn't auto-detected).
        return any(
            f.startswith(".") or _TEMPLATE_WORD_RE.search(f) for f in folders
        ) or bool(
            templates_parts and folders[: len(templates_parts)] == templates_parts
        )

    if excluded(note_path):
        return ""
    folder, index = note_path.parent, None
    while folder != vault_root and vault_root in folder.parents:
        index = next(
            (
                p
                for p in sorted(folder.glob("*.md"))
                if p.is_file() and _is_index_note(p)
            ),
            None,
        )
        if index:
            break
        folder = folder.parent
    if (
        index is None
        or excluded(index)
        or not check_path_access(index, vault_path, "modificar")[0]
    ):
        return ""
    with open(index, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")  # written back with its own line endings
    # "[" in the class keeps the search linear on many unclosed "[[".
    if re.search(
        rf"\[\[(?:[^\]\[|#\n]*/)?{re.escape(stem)}(?:\.md)?[|#\]]",
        nfc(text),
        re.IGNORECASE,
    ):
        return ""
    entry = f"- [[{stem}]]" + (
        f": {' '.join(description.split())}" if description else ""
    )
    frontmatter = _FRONTMATTER_BLOCK_RE.match(text)
    head = frontmatter.group(0) if frontmatter else ""
    lines = text[len(head) :].split("\n")
    heads, fence, comment = [], "", False
    for i, line in enumerate(lines):
        if fence:
            if re.match(rf"^ {{0,3}}{fence[0]}{{{len(fence)},}}[ \t]*$", line):
                fence = ""
            continue
        prose = _strip_inline_code(line)  # `%%` in code is not a comment
        if not comment and (opened := _fence_open(line)):
            fence = opened
        elif comment or "%%" in prose:  # headings inside %% comments are hidden
            if prose.count("%%") % 2:
                comment = not comment
        elif heading := _HEADING_RE.match(line):
            heads.append((i, len(heading.group(1)), heading.group(2).strip()))
    section = next(
        (h for h in heads if nfc(h[2]).casefold() == _INDEX_SECTION.casefold()), None
    )
    if section:
        end = next(
            (i for i, lvl, _ in heads if i > section[0] and lvl <= section[1]),
            len(lines),
        )
        while end > section[0] + 1 and not lines[end - 1].strip():
            end -= 1
        lines[end:end] = [entry]
    else:
        h2 = next((i for i, lvl, _ in heads if lvl == 2), None)
        block = [f"## {_INDEX_SECTION}", "", entry, ""]
        if h2 is not None:
            lines[h2:h2] = ["", *block] if h2 and lines[h2 - 1].strip() else block
        elif not "".join(lines).strip():
            lines = block
        else:
            lines += block if lines[-1] == "" else ["", *block]
    # The date only inside the frontmatter: the body may hold an inline
    # `updated::` field or a ```yaml block that must stay as written.
    # A "---" block that isn't a YAML mapping is a rule around prose: no date.
    if head and _extract_frontmatter_from_content(head)[0]:
        head = _update_frontmatter_date(head)
    new_text = head + "\n".join(lines)
    atomic_write_text(index, new_text.replace("\n", newline), newline="")
    return index.relative_to(vault_root).as_posix()


# Canonical `agente_creador` per known client, keyed by the name lowercased
# with "-"/"_" as spaces. Covers MCP clientInfo names (claude-code, claude-ai,
# codex-mcp-client) and the spellings found in the vault. Unknown names are
# kept as given, trimmed.
_AGENT_ALIASES = {
    "claude code": "Claude Code",
    "claude ai": "Claude",
    "claude": "Claude",
    "codex": "Codex",
    "codex mcp client": "Codex",
    "codex cli": "Codex",
    "hermes": "Hermes",
    "hermes agent": "Hermes",
    "pi": "Pi",
    "pi agent": "Pi",
    "antigravity": "Antigravity",
}


# Printable but blank: joiner, Hangul fillers, Braille blank.
_INVISIBLE = dict.fromkeys(map(ord, "\u200d\u115f\u1160\u3164\uffa0\u2800"))


def normalize_agent_name(name: str) -> str:
    """Return the canonical agent name for ``agente_creador``.

    Non-printable characters are dropped and the result is capped at 64
    characters: the client's name reaches the note without the agent typing it.
    """
    # Split first so tabs and Unicode spaces become spaces; keep ZWJ emoji.
    name = "".join(
        c for c in " ".join(name.split()) if c.isprintable() or c == "\u200d"
    )
    name = nfc(name)[:64].rstrip()
    if all(
        c.isspace() or unicodedata.category(c) in ("Mn", "Me")
        for c in name.translate(_INVISIBLE)
    ):
        return ""  # only invisible characters: no signature at all
    key = " ".join(re.sub(r"[-_]", " ", name).casefold().split())
    return _AGENT_ALIASES.get(key, name)


def find_templates_folder(vault_path: Path, config: Any) -> str | None:
    """Return the vault's templates folder: configured, else auto-detected.

    Auto-detection looks at visible top-level folders: an exact "Templates"
    or "Plantillas" wins; otherwise the first (sorted, so the choice is
    stable) whose name contains "plantilla" or "template", preferring any
    other folder to the Templater plugin's one.
    """
    if config and config.templates_folder:
        return config.templates_folder
    folders = [
        item.name
        for item in sorted(vault_path.iterdir())
        if item.is_dir() and not item.name.startswith(".")
    ]
    for name in folders:
        if name.casefold() in ("templates", "plantillas", "_templates"):
            return name
    for name in folders:
        lowered = name.casefold()
        if "templater" not in lowered and (
            "plantilla" in lowered or "template" in lowered
        ):
            return name
    for name in folders:  # a Templater folder only when it is the only one
        if "template" in name.casefold():
            return name
    return None


def _build_frontmatter(
    titulo: str,
    ahora: str,
    tags_list: list[str],
    agente_creador: str = "",
    extra_metadata: dict[str, Any] | None = None,
    agente_por_defecto: str = "",
) -> str:
    """Build YAML frontmatter block combining metadata.

    Issue #2: when ``extra_metadata`` carries an embedded frontmatter block
    extracted from ``content``, its fields take precedence over the
    parameter-derived defaults. Filename identity is still the caller's
    ``titulo`` argument; the frontmatter ``title`` reflects what the
    author wrote.
    """
    metadata: dict[str, Any] = {}

    if extra_metadata:
        metadata.update(extra_metadata)

    # Notes following the Spanish media schema (``titulo``/``fecha_creacion``)
    # must not get the generic ``title``/``created`` too: mixing both schemas
    # is exactly what the media validation rules reject.
    if "titulo" not in metadata:
        metadata.setdefault("title", titulo)
    if "fecha_creacion" not in metadata:
        metadata.setdefault("created", ahora)

    existing_tags = metadata.get("tags", [])
    if isinstance(existing_tags, str):
        existing_tags = [t.strip() for t in existing_tags.split(",") if t.strip()]
    elif not isinstance(existing_tags, list):
        existing_tags = []

    all_tags = list(existing_tags)
    for tag in tags_list:
        if tag not in all_tags:
            all_tags.append(tag)

    if all_tags:
        metadata["tags"] = all_tags

    if agente_creador:
        metadata["agente_creador"] = agente_creador
    elif agente_por_defecto and not metadata.get("agente_creador"):
        # Default only: a signature from the template or content is kept.
        metadata["agente_creador"] = agente_por_defecto

    yaml_content = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    return f"---\n{yaml_content}---\n\n"


def append_to_note(
    nombre_archivo: str,
    contenido: str,
    al_final: bool = True,
) -> Result[str]:
    """Append content to an existing note.

    Args:
        nombre_archivo: Name of the file to modify.
        contenido: Content to append.
        al_final: If True, append at end; if False, prepend.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido_actual = f.read()

    if al_final:
        sep = "\n\n" if not contenido_actual.endswith("\n\n") else ""
        nuevo_contenido = contenido_actual + sep + contenido
    else:
        nuevo_contenido = contenido + "\n\n" + contenido_actual

    atomic_write_text(nota_path, nuevo_contenido)

    ruta_relativa = nota_path.relative_to(vault_path)
    posicion = "final" if al_final else "inicio"
    return Result.ok(f"Contenido agregado al {posicion} de {ruta_relativa}")


def delete_note(nombre_archivo: str, confirmar: bool = False) -> Result[str]:
    """Delete a note from the vault (requires confirmation).

    Args:
        nombre_archivo: Name of the file to delete.
        confirmar: Must be True to confirm deletion.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    if not confirmar:
        return Result.fail("Para eliminar una nota, debes confirmar con confirmar=True")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "eliminar")
    if not is_allowed:
        return Result.fail(error)

    ruta_relativa = nota_path.relative_to(vault_path)
    nota_path.unlink()

    return Result.ok(f"Nota eliminada: {ruta_relativa}")


def _update_frontmatter_date(content: str, user_set_updated: bool = False) -> str:
    """Update the 'updated' field in frontmatter to today's date.

    Args:
        content: The full note content.
        user_set_updated: If True, skip auto-update (user set it explicitly).

    Returns:
        Content with updated date in frontmatter.
    """
    if user_set_updated:
        return content

    if not content.startswith("---"):
        return content

    ahora = datetime.now().strftime("%Y-%m-%d")

    if re.search(r"^updated:", content, re.MULTILINE):
        return re.sub(
            r'^(updated:\s*["\']?)[^"\'\n]+(["\']?)$',
            rf"\g<1>{ahora}\g<2>",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    if re.search(r"^created:", content, re.MULTILINE):
        return re.sub(
            r"^(created:\s*.+)$",
            rf"\1\nupdated: {ahora}",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    return content.replace("\n---\n", f"\nupdated: {ahora}\n---\n", 1)


def _operation_to_dict(operation: Any) -> dict[str, Any] | None:
    """Convert dict-like or Pydantic edit operation inputs to a plain dict."""
    if isinstance(operation, dict):
        return operation
    if hasattr(operation, "model_dump"):
        return operation.model_dump()
    return None


def _edit_operation_value(
    operation: dict[str, Any], aliases: tuple[str, ...]
) -> str | None:
    """Read an edit operation field, accepting common client aliases."""
    for alias in aliases:
        if alias in operation:
            value = operation[alias]
            return value if isinstance(value, str) else None
    return None


def normalize_edit_operations(operaciones: list[Any]) -> Result[list[dict[str, str]]]:
    """Normalize exact-match edit operations from MCP clients.

    The public tool contract is {"old": "...", "new": "..."}, but some clients
    synthesize camelCase field names from prose. Accepting these aliases keeps
    patch_note portable while preserving the same exact-match semantics.
    """
    normalized: list[dict[str, str]] = []
    for index, operation in enumerate(operaciones, start=1):
        operation_dict = _operation_to_dict(operation)
        if operation_dict is None:
            return Result.fail(
                f"Operation {index} must be an object with old/new text fields."
            )

        old_text = _edit_operation_value(operation_dict, ("old", "oldText", "old_text"))
        new_text = _edit_operation_value(operation_dict, ("new", "newText", "new_text"))
        if old_text is None or new_text is None:
            return Result.fail(
                f"Operation {index} must include string fields 'old' and 'new'. "
                "Aliases 'oldText'/'newText' and 'old_text'/'new_text' are also accepted."
            )

        normalized.append({"old": old_text, "new": new_text})

    return Result.ok(normalized)


def edit_note(  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
    nombre_archivo: str,
    operaciones: list[Any],
) -> Result[str]:
    """Edit an existing note by applying a list of old->new operations.

    All operations are validated before any writes (atomic).

    Args:
        nombre_archivo: Name or path of the note to edit.
        operaciones: List of {"old": "...", "new": "..."} dicts.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "editar")
    if not is_allowed:
        return Result.fail(error)

    if not operaciones:
        return Result.fail("Debe incluir al menos una operación.")

    if len(operaciones) > 50:
        return Result.fail("Maximo 50 operaciones por llamada.")

    normalized_result = normalize_edit_operations(operaciones)
    if not normalized_result.success:
        return Result.fail(normalized_result.error or "Invalid edit operations.")
    operaciones = normalized_result.data or []

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido_actual = f.read()

    ruta_relativa = nota_path.relative_to(vault_path)

    # --- Full-replace mode ---
    if any(op["old"] == "" for op in operaciones):
        if len(operaciones) != 1:
            return Result.fail(
                "El reemplazo total (old vacío) debe ser la única operación en la lista."
            )
        op = operaciones[0]
        if op["new"] == "":
            return Result.fail(
                "No se puede vaciar la nota completa. Usa eliminar_nota para borrar."
            )
        contenido_final = _process_date_placeholders(op["new"])
        has_updated = bool(re.search(r"^updated:", op["new"], re.MULTILINE))
        contenido_final = _update_frontmatter_date(
            contenido_final, user_set_updated=has_updated
        )
        contenido_final = _normalize_frontmatter(contenido_final)
        atomic_write_text(nota_path, contenido_final)
        return Result.ok(f"Nota editada: {ruta_relativa} (reemplazo total)")

    # --- Partial edit mode: validate all operations ---
    matches: list[tuple[int, int, str]] = []  # (start, end, new_text)

    for op in operaciones:
        old_text = op["old"]
        new_text = op["new"]

        count = contenido_actual.count(old_text)
        if count == 0:
            preview = old_text[:80] + ("..." if len(old_text) > 80 else "")
            suggestions = _suggest_close_matches(old_text, contenido_actual)
            base_msg = (
                f"No se encontró el texto: '{preview}' en la nota {ruta_relativa}"
            )
            if suggestions:
                hint_lines = "\n".join(f"  - {s!r}" for s in suggestions)
                base_msg += "\nQuiza quisiste decir:\n" + hint_lines
            return Result.fail(base_msg)
        if count > 1:
            preview = old_text[:80] + ("..." if len(old_text) > 80 else "")
            return Result.fail(
                f"El texto '{preview}' aparece {count} veces en la nota. "
                "Incluye mas contexto para que sea unico."
            )

        start = contenido_actual.index(old_text)
        end = start + len(old_text)
        matches.append((start, end, new_text))

    # Check for overlaps
    for i, (start_a, end_a, _) in enumerate(matches):
        for j, (start_b, end_b, _) in enumerate(matches):
            if i >= j:
                continue
            if start_a < end_b and start_b < end_a:
                return Result.fail(
                    f"Las operaciones {i + 1} y {j + 1} afectan el mismo fragmento de texto."
                )

    # Check if user explicitly modifies the "updated" field
    user_set_updated = any("updated:" in op["new"] for op in operaciones)

    # Apply in reverse order so offsets remain valid
    matches.sort(key=lambda m: m[0], reverse=True)
    resultado = contenido_actual
    for start, end, new_text in matches:
        resultado = resultado[:start] + new_text + resultado[end:]

    resultado = _process_date_placeholders(resultado)
    resultado = _update_frontmatter_date(resultado, user_set_updated=user_set_updated)
    resultado = _normalize_frontmatter(resultado)

    atomic_write_text(nota_path, resultado)

    n = len(operaciones)
    return Result.ok(f"Nota editada: {ruta_relativa} ({n} operaciones aplicadas)")


def _has_word(text: str, keywords: list[str]) -> bool:
    """Whole-word (plural allowed) match: "ia" must not fire on "media",
    nor "red" on "receta de pared"."""
    alternatives = "|".join(re.escape(k) for k in keywords)
    return re.search(rf"(?<!\w)(?:{alternatives})(?:e?s)?(?!\w)", text) is not None


def suggest_folder_location(titulo: str, contenido: str, etiquetas: str = "") -> str:
    # pylint: disable=too-many-return-statements,too-many-branches,too-many-locals
    """Helper to suggest location from keywords and the vault's declared taxonomy.

    This used to try the in-process semantic index first and fall back here when
    the optional RAG extra was missing. That stack is gone, so the keyword
    heuristic is now the only path.
    """

    texto = (titulo + " " + contenido + " " + etiquetas).lower()

    # Parent folders come from the vault's declared taxonomy so suggestions
    # survive layout renames; fall back to this vault's current names.
    vp = get_vault_path()
    know_role = resolve_role(vp, "knowledge") if vp else None
    crea_role = resolve_role(vp, "creations") if vp else None
    know = know_role.name if know_role else "02_Conocimiento"
    crea = crea_role.name if crea_role else "03_Creaciones"

    # IA / Machine Learning
    if _has_word(
        texto,
        [
            "ia",
            "inteligencia artificial",
            "mcp",
            "llm",
            "gpt",
            "claude",
            "agente",
            "embedding",
            "rag",
            "machine learning",
            "ml",
            "modelo",
        ],
    ):
        return f"📂 Sugerencia: `{know}/IA`"

    # Lógica simple de categorización basada en la estructura del vault
    if _has_word(texto, ["poema", "poesía", "verso", "rima"]):
        return f"📂 Sugerencia: `{crea}/Poemas`"
    if _has_word(
        texto, ["reflexión", "reflexiones", "pienso", "creo", "opinión", "opiniones"]
    ):
        return f"📂 Sugerencia: `{crea}/Reflexiones`"
    if _has_word(
        texto,
        [
            "código",
            "github",
            "gitlab",
            "dockerfile",
            "python",
            "sql",
            "config",
            "bash",
            "script",
            "git",
            "docker",
        ],
    ):
        return f"📂 Sugerencia: `{know}/Programación`"
    if _has_word(
        texto,
        [
            "sistema",
            "linux",
            "ssh",
            "nas",
            "red",
            "networking",
            "homelab",
        ],
    ):
        return f"📂 Sugerencia: `{know}/Sistemas`"
    if _has_word(texto, ["filosofía", "ética", "aristóteles", "dualismo"]):
        return f"📂 Sugerencia: `{know}/Filosofía`"
    if _has_word(texto, ["psicología", "cognitivo", "mente", "ego"]):
        return f"📂 Sugerencia: `{know}/Psicología`"

    # Default fallback - scan for inbox-like folders or use root
    try:
        vault_path = get_vault_path()
        if vault_path:
            for item in Path(vault_path).iterdir():
                if item.is_dir() and any(
                    t in item.name.lower() for t in ["inbox", "bandeja", "entrada"]
                ):
                    return f"📂 Sugerencia: `{item.name}` (Categoría general)"
    except OSError as e:
        logger.debug("Error al buscar carpeta inbox en vault: %s", e)

    return "📂 Sugerencia: Ubicación a confirmar con el usuario"


def resolve_create_folder(
    titulo: str, contenido: str, etiquetas: str, carpeta: str = ""
) -> str:
    """Return ``carpeta`` or, when empty, the auto-suggested folder ('' = root)."""
    if carpeta:
        return carpeta
    res_sug = suggest_folder_location(titulo, contenido, etiquetas)
    # Extrae el path de vuelta entre backticks: 📂 Sugerencia: `path`
    match = re.search(r"`([^`]+)`", res_sug)
    return match.group(1) if match else ""


def note_relative_path(carpeta: str, titulo: str) -> Path:
    """Vault-relative path where ``create_note`` writes ``titulo`` in ``carpeta``."""
    nota_path = Path(carpeta) / sanitize_filename(titulo)
    if nota_path.suffix != ".md":
        nota_path = nota_path.with_suffix(".md")
    return nota_path


def _resolve_type_defaults(
    vault_path: Path, config: Any, tipo: str, plantilla: str, carpeta: str
) -> tuple[str, str, str | None]:
    """Fill template and folder for ``tipo`` from taxonomy.templates.

    ``taxonomy.types`` is the vocabulary (as in the middleware type rule).
    Explicit ``plantilla`` wins; an explicit ``carpeta`` must sit inside the
    type's base folder when the type is filed by topic (choose_subfolder).
    Returns (plantilla, carpeta, error message or None).
    """
    tipo = nfc(tipo)
    taxonomy = config.taxonomy if config else None
    types = taxonomy.types if taxonomy else []
    if types and tipo not in types:
        return (
            plantilla,
            carpeta,
            f"El tipo '{tipo}' no existe en taxonomy.types de .agents/vault.yaml. "
            f"Tipos válidos: {', '.join(sorted(types))}",
        )
    spec = taxonomy.templates.get(tipo) if taxonomy else None
    if spec is None:
        return plantilla, carpeta, None

    plantilla = plantilla or spec.template
    if not spec.choose_subfolder:
        return plantilla, carpeta or spec.folder, None

    base = PurePosixPath(spec.folder)
    if carpeta:
        target = PurePosixPath(carpeta.strip("/"))
        # PurePosixPath does not resolve "..": reject it instead of letting
        # "Base/../Otra" pass the containment check.
        if ".." not in target.parts and target != base and base in target.parents:
            return plantilla, carpeta, None
    return (
        plantilla,
        carpeta,
        f"Las notas de tipo '{tipo}' van en una subcarpeta de {spec.folder}. "
        f"Pasa folder con una de estas o una nueva dentro de {spec.folder}: "
        f"{_list_subfolders(vault_path, spec.folder)}",
    )


def _list_subfolders(vault_path: Path, folder: str) -> str:
    """Comma-separated visible subfolders of ``folder``, hiding private ones."""
    base, _ = resolve_vault_path(folder, vault_path, "list folders in")
    if base is None or not base.is_dir():
        return "(ninguna)"
    names = sorted(
        p.name
        for p in base.iterdir()
        if p.is_dir()
        and not p.is_symlink()
        and not p.name.startswith(".")
        and check_path_access(p, vault_path, "list")[0]
        # private_paths patterns such as "**/Privado/*" match the contents,
        # not the folder itself: probe a child path as well.
        and check_path_access(p / "_.md", vault_path, "list")[0]
    )
    return ", ".join(f"{folder}/{n}" for n in names) or "(ninguna)"


def create_note(
    titulo: str,
    contenido: str,
    carpeta: str = "",
    etiquetas: str = "",
    plantilla: str = "",
    agente_creador: str = "",
    descripcion: str = "",
) -> Result[str]:
    # pylint: disable=too-many-positional-arguments
    """Create a new note in the vault. See ``create_note_with_content``."""
    return create_note_with_content(
        titulo, contenido, carpeta, etiquetas, plantilla, agente_creador, descripcion
    )[0]


def create_note_with_content(
    titulo: str,
    contenido: str,
    carpeta: str = "",
    etiquetas: str = "",
    plantilla: str = "",
    agente_creador: str = "",
    descripcion: str = "",
    tipo: str = "",
    agente_por_defecto: str = "",
    enlazar_indice: bool = False,
) -> tuple[Result[str], tuple[str, str] | None]:
    # pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-positional-arguments,too-many-arguments,too-many-return-statements
    """Create a new note in the vault and return the text written to disk.

    Args:
        titulo: Title of the note.
        contenido: Content of the note.
        carpeta: Target folder (empty = root or auto-suggested).
        etiquetas: Comma-separated tags.
        plantilla: Name of the template file to use.
        agente_creador: Name of the creating agent.
        descripcion: Brief description for placeholders.
        agente_por_defecto: ``agente_creador`` used only when neither
            ``agente_creador`` nor the template or content set one.
        tipo: Note type. Picks the default template and folder from
            ``taxonomy.templates`` in vault.yaml and sets ``type``.
        enlazar_indice: Link the new note from the index of its folder
            (see ``link_from_index``).

    Returns:
        (Result with success message or error, (final note text, vault-relative
        path) or None on
        failure). The text lets callers validate the note as written without
        re-reading the file or parsing paths out of the display message.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada."), None

    config = get_vault_config(vault_path)

    if tipo:
        tipo = nfc(tipo)  # canonical form, also for the frontmatter written below
        plantilla, carpeta, error = _resolve_type_defaults(
            vault_path, config, tipo, plantilla, carpeta
        )
        if error:
            return Result.fail(error), None

    carpeta = resolve_create_folder(titulo, contenido, etiquetas, carpeta)
    nombre_archivo = sanitize_filename(titulo)
    # normpath: "05_Media/../Notas" must not match rules for 05_Media.
    ruta_pedida = Path(os.path.normpath(note_relative_path(carpeta, titulo))).as_posix()
    nota_path = vault_path / ruta_pedida

    # Validate before mkdir so rejected paths cannot mutate the filesystem.
    resolved_note, error = resolve_vault_path(nota_path, vault_path, "crear nota en")
    if resolved_note is None:
        return Result.fail(error), None
    nota_path = resolved_note

    # Verificar si ya existe
    if nota_path.exists():
        return Result.fail(f"Ya existe una nota con el nombre '{nombre_archivo}'"), None

    # Preparar contenido final
    contenido_final = ""
    ahora = datetime.now().strftime("%Y-%m-%d")
    tags_list = [t.strip() for t in etiquetas.split(",") if t.strip()]

    # Si se usa plantilla
    if plantilla:
        templates_folder = find_templates_folder(vault_path, config)

        if not templates_folder:
            return Result.fail(
                "No se detectó carpeta de plantillas.\n\n"
                "💡 Crea `.agents/vault.yaml` con:\n"
                "```yaml\n"
                'templates_folder: "TuCarpetaDePlantillas"\n'
                "```"
            ), None

        plantilla_path = vault_path / templates_folder / plantilla
        if not plantilla.endswith(".md"):
            plantilla_path = plantilla_path.with_suffix(".md")
        resolved_template, error = resolve_vault_path(
            plantilla_path, vault_path, "read template from"
        )
        if resolved_template is None:
            return Result.fail(error), None
        plantilla_path = resolved_template

        if plantilla_path.exists():
            with open(plantilla_path, "r", encoding="utf-8") as f:
                plantilla_content = f.read()
            plantilla_raw = plantilla_content

            # Reemplazos de título
            plantilla_content = plantilla_content.replace("{{title}}", titulo)
            plantilla_content = plantilla_content.replace("{{titulo}}", titulo)

            # Reemplazos de descripción
            plantilla_content = plantilla_content.replace(
                "{{description}}", descripcion
            )
            plantilla_content = plantilla_content.replace(
                "{{descripcion}}", descripcion
            )

            # Reemplazos de hora (HH:mm)
            hora_actual = datetime.now().strftime("%H:%M")
            plantilla_content = plantilla_content.replace("{{time}}", hora_actual)
            plantilla_content = plantilla_content.replace("{{hora}}", hora_actual)

            # Reemplazos de carpeta
            carpeta_final = carpeta if carpeta else ""
            plantilla_content = plantilla_content.replace("{{folder}}", carpeta_final)
            plantilla_content = plantilla_content.replace("{{carpeta}}", carpeta_final)

            # Reemplazos de etiquetas
            plantilla_content = plantilla_content.replace("{{tags}}", etiquetas)
            plantilla_content = plantilla_content.replace("{{etiquetas}}", etiquetas)

            # Procesar todas las fechas con formatos
            plantilla_content = _process_date_placeholders(plantilla_content)

            template_metadata, template_body = _extract_frontmatter_from_content(
                plantilla_content
            )
            extra_metadata, contenido_limpio = _extract_frontmatter_from_content(
                contenido
            )
            combined_metadata = dict(template_metadata)
            # La plantilla aporta estructura, no identidad: un título o una
            # fecha escritos a fuego en la plantilla se sustituyen por los
            # reales. Si el campo venía de un marcador ({{title}} MOC,
            # {{date:...}}) se respeta lo que produjo. Si la plantilla no trae
            # `updated`, no se añade; `title` y `created` los rellena siempre
            # _build_frontmatter. El frontmatter del contenido sigue mandando.
            # Los marcadores se buscan solo en el frontmatter de la plantilla.
            # ponytail: solo reconoce `clave: valor` en una línea; una clave
            # entre comillas o un valor plegado (`title: >-`) cuenta como fijo.
            raw_fm = _FRONTMATTER_BLOCK_RE.match(
                plantilla_raw + "\n"
            )  # plantilla sin salto final
            raw_fm_text = raw_fm.group(2) if raw_fm else ""
            for key, real in (
                ("title", titulo),
                ("created", ahora),
                ("updated", ahora),
            ):
                if key in template_metadata and not re.search(
                    rf"^{key}:.*\{{\{{", raw_fm_text, re.MULTILINE
                ):
                    combined_metadata[key] = real
            combined_metadata.update(extra_metadata)
            # Notes with their own schema (media: `tipo`/`estado`) don't get
            # the generic `type`: their rules may forbid it.
            if tipo and not combined_metadata.get("tipo"):
                combined_metadata["type"] = tipo

            contenido_final = _build_frontmatter(
                titulo=titulo,
                ahora=ahora,
                tags_list=tags_list,
                agente_creador=agente_creador,
                extra_metadata=combined_metadata if combined_metadata else None,
                agente_por_defecto=agente_por_defecto,
            )
            contenido_final += _place_content(template_body, contenido_limpio)
        else:
            return Result.fail(f"No se encontró la plantilla '{plantilla}'"), None
    else:
        # Sin plantilla: detectar si el contenido ya tiene frontmatter
        # Extraer frontmatter del contenido si existe
        extra_metadata, contenido_limpio = _extract_frontmatter_from_content(contenido)
        if tipo and not extra_metadata.get("tipo"):
            extra_metadata["type"] = tipo

        # Construir frontmatter unificado
        frontmatter = _build_frontmatter(
            titulo=titulo,
            ahora=ahora,
            tags_list=tags_list,
            agente_creador=agente_creador,
            extra_metadata=extra_metadata if extra_metadata else None,
            agente_por_defecto=agente_por_defecto,
        )

        contenido_final = frontmatter

        # Añadir título si el contenido limpio no empieza con un heading
        if not contenido_limpio.lstrip().startswith("#"):
            contenido_final += f"# {titulo}\n\n"

        contenido_final += contenido_limpio

    # Procesar cualquier placeholder de fecha restante en el contenido
    contenido_final = _process_date_placeholders(contenido_final)
    contenido_final = _normalize_frontmatter(contenido_final)

    ruta_relativa = nota_path.relative_to(vault_path)

    # Vault rules marked ``block: true`` refuse the write (validated against
    # the final note, template included, and its real path).
    final_fm, final_body = _extract_frontmatter_from_content(contenido_final)
    bloqueantes_rotas: set[str] = set()
    bloqueos: list[str] = []
    # Both the requested and the resolved path: a symlinked folder
    # ("05_Media" -> elsewhere in the vault) must not dodge path rules.
    for ruta in dict.fromkeys((ruta_pedida, ruta_relativa.as_posix())):
        bloqueos += [
            b
            for b in blocking_violations(
                load_vault_rules(),
                title=titulo,
                content=final_body,
                frontmatter=final_fm,
                path=ruta,
                broken=bloqueantes_rotas,
            )
            if b not in bloqueos
        ]
    if bloqueos:
        return Result.fail(
            f"Nota NO creada ({ruta_relativa}): incumple reglas bloqueantes "
            "del vault.\n"
            + "\n".join(f"- {b}" for b in bloqueos)
            + "\nCorrige el frontmatter (usa la plantilla del tipo con "
            "`template` y rellena los campos en `content`) y vuelve a intentarlo."
        ), None

    # The folder is created only once the template and content are ready, so a
    # failed creation (missing template, rejected path) leaves no empty folders.
    nota_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(nota_path, contenido_final)

    resultado = f"Nota creada: **{titulo}**\n"
    resultado += f"📍 Ubicación: {ruta_relativa}\n"
    if bloqueantes_rotas:
        resultado += (
            "⚠️ Reglas bloqueantes mal formadas, no comprobadas: "
            + ", ".join(sorted(bloqueantes_rotas))
            + " (corrígelas en .agents/REGLAS_GLOBALES.md)\n"
        )
    if plantilla:
        resultado += f"📝 Plantilla usada: {plantilla}\n"
    if agente_creador:
        resultado += f"🤖 Agente: {agente_creador}\n"
    if enlazar_indice:
        try:
            indice = link_from_index(nota_path, vault_path, descripcion)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # The note is already written: report, never fail the creation.
            logger.exception("No se pudo enlazar %s desde su índice", nota_path)
            resultado += f"⚠️ No se pudo enlazar desde el índice: {e}\n"
        else:
            if indice:
                resultado += f"🔗 Enlazada desde: {indice}\n"

    return Result.ok(resultado), (contenido_final, ruta_relativa.as_posix())


def list_templates() -> Result[str]:
    """List available templates in the vault.

    Returns:
        Result with formatted list of templates.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    config = get_vault_config(vault_path)

    templates_folder = find_templates_folder(vault_path, config)

    if not templates_folder:
        return Result.fail(
            "No se detectó carpeta de plantillas en el vault.\n\n"
            "💡 **Solución**: Crea `.agents/vault.yaml` con:\n"
            "```yaml\n"
            'templates_folder: "NombreDeTuCarpetaDePlantillas"\n'
            "```"
        )

    templates_path, error = resolve_vault_path(
        templates_folder, vault_path, "list templates in"
    )
    if templates_path is None:
        return Result.fail(error)
    if not templates_path.is_dir():
        return Result.fail(f"No se encontró la carpeta '{templates_folder}'")

    plantillas = []
    for item in sorted(iter_safe_vault_files(vault_path, root=templates_path)):
        plantillas.append(item.name)

    if not plantillas:
        return Result.ok(f"ℹ️ No hay plantillas disponibles en {templates_folder}")

    mapping = ""
    if config and config.taxonomy.templates:
        mapping = "\n\n**Por tipo** (usa `notes.create(note_type=...)`):\n" + "\n".join(
            f"- `{t}`: {spec.template} → {spec.folder}"
            + ("/<subcarpeta>" if spec.choose_subfolder else "")
            for t, spec in config.taxonomy.templates.items()
        )
    return Result.ok(
        "📝 **Plantillas disponibles:**\n"
        + "\n".join([f"- {p}" for p in plantillas])
        + mapping
    )


def search_and_replace_global(
    buscar: str,
    reemplazar: str,
    carpeta: str = "",
    solo_preview: bool = True,
    limite: int = 100,
) -> Result[str]:
    # pylint: disable=too-many-branches,too-many-locals,too-many-statements
    """Search and replace text in all notes.

    Args:
        buscar: Text/Pattern to search (literal).
        reemplazar: Replacement text.
        carpeta: Specific folder to search (empty = whole vault).
        solo_preview: If True, only show preview of changes.
        limite: Max files to process.

    Returns:
        Result with summary of changes.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    if not buscar:
        return Result.fail("Debes especificar un texto a buscar.")
    if limite < 1:
        return Result.fail("El límite debe ser al menos 1.")

    # Determinar carpeta de búsqueda
    search_path, error = resolve_vault_path(
        carpeta or vault_path, vault_path, "search and replace in"
    )
    if search_path is None:
        return Result.fail(error)
    if not search_path.is_dir():
        return Result.fail(f"La carpeta '{carpeta}' no existe.")

    # Carpetas excluidas por seguridad
    config = get_vault_config(vault_path)
    excluded = [".git", ".obsidian", ".trash", "node_modules"]
    if config and config.excluded_folders:
        excluded.extend(config.excluded_folders)

    # Buscar archivos .md
    archivos_afectados: list[dict[str, Any]] = []
    limite_alcanzado = False
    archivos_omitidos = 0

    for md_file in iter_safe_vault_files(vault_path, root=search_path):
        # Saltar carpetas excluidas
        if any(excl in md_file.parts for excl in excluded):
            continue

        # Verificar acceso usando función centralizada
        is_allowed, _ = check_path_access(md_file, vault_path, "buscar en")
        if not is_allowed:
            continue

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                contenido = f.read()

            if buscar in contenido:
                if len(archivos_afectados) >= limite:
                    limite_alcanzado = True
                    break
                ocurrencias = contenido.count(buscar)
                ruta_rel = md_file.relative_to(vault_path)
                archivos_afectados.append(
                    {
                        "path": md_file,
                        "ruta_rel": str(ruta_rel),
                        "ocurrencias": ocurrencias,
                    }
                )

        except (OSError, UnicodeDecodeError) as e:
            archivos_omitidos += 1
            logger.debug("No se pudo leer '%s' para busqueda: %s", md_file, e)
            continue

    if not archivos_afectados:
        resultado = f"ℹ️ No se encontró '{buscar}' en ninguna nota."
        if archivos_omitidos:
            resultado += f"\n⚠️ Archivos ilegibles omitidos: {archivos_omitidos}."
        return Result.ok(resultado)

    # Modo preview
    if solo_preview:
        resultado = f"🔍 **Preview de búsqueda**: `{buscar}`\n"
        resultado += f"📊 Se encontraron **{len(archivos_afectados)}** "
        total_ocurrencias = sum(a["ocurrencias"] for a in archivos_afectados)
        resultado += f"archivos con {total_ocurrencias} ocurrencias totales.\n\n"
        resultado += "**Archivos afectados:**\n"
        for arch in archivos_afectados[:20]:  # Limitar output
            resultado += f"- `{arch['ruta_rel']}` ({arch['ocurrencias']} ocurrencias)\n"
        if len(archivos_afectados) > 20:
            resultado += f"- ... y {len(archivos_afectados) - 20} archivos más\n"
        if limite_alcanzado:
            resultado += (
                f"\n⚠️ Límite de {limite} archivos alcanzado; "
                "puede haber más coincidencias.\n"
            )
        if archivos_omitidos:
            resultado += f"\n⚠️ Archivos ilegibles omitidos: {archivos_omitidos}.\n"
        resultado += "\n⚠️ Usa `notes.apply_replace` para aplicar los cambios."
        return Result.ok(resultado)

    # Modo ejecución
    archivos_modificados = 0
    archivos_sin_coincidencia = 0
    total_reemplazos = 0

    for arch in archivos_afectados:
        try:
            contenido_actual = arch["path"].read_text(encoding="utf-8")
            ocurrencias = contenido_actual.count(buscar)
            if not ocurrencias:
                archivos_sin_coincidencia += 1
                continue
            nuevo_contenido = contenido_actual.replace(buscar, reemplazar)
            atomic_write_text(arch["path"], nuevo_contenido)
            archivos_modificados += 1
            total_reemplazos += ocurrencias
        except (OSError, UnicodeDecodeError) as e:
            archivos_omitidos += 1
            logger.warning("No se pudo reemplazar en '%s': %s", arch["path"], e)
            continue

    resultado = "✅ **Reemplazo completado**\n"
    resultado += f"- Archivos modificados: {archivos_modificados}\n"
    resultado += f"- Reemplazos realizados: {total_reemplazos}\n"
    resultado += f"- `{buscar}` → `{reemplazar}`"
    if archivos_sin_coincidencia:
        resultado += f"\n- Archivos ya sin coincidencias: {archivos_sin_coincidencia}"
    if archivos_omitidos:
        resultado += f"\n⚠️ Archivos ilegibles o no escritos: {archivos_omitidos}."
    if limite_alcanzado:
        resultado += (
            f"\n⚠️ Límite de {limite} archivos alcanzado; puede haber más coincidencias."
        )
    return Result.ok(resultado)


def inbox_capture_frontmatter(etiquetas: str = "") -> dict[str, Any]:
    """Return the frontmatter that ``quick_capture`` writes for an inbox note.

    Single source of truth for the inbox semantics (``type``/``status``/
    ``created``/``updated`` plus parsed ``tags``). Exposed so the tool layer
    can hand the real metadata to the rule middleware: otherwise a
    ``required_fields`` vault rule fires a false "missing type/status/tags"
    warning even though the note on disk has those fields.
    """
    ahora_fecha = datetime.now().strftime("%Y-%m-%d")
    metadata: dict[str, Any] = {
        "type": "inbox",
        "status": "captura",
        "created": ahora_fecha,
        "updated": ahora_fecha,
    }
    tags = [t.strip() for t in etiquetas.split(",") if t.strip()]
    if tags:
        metadata["tags"] = tags
    return metadata


def quick_capture(texto: str, etiquetas: str = "") -> Result[str]:
    """Capture an idea quickly to Inbox with minimal friction.

    Args:
        texto: The content to capture.
        etiquetas: Optional comma-separated tags.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # 1. Find Inbox folder by auto-detection
    inbox_folder = None
    inbox_candidates = ["00_Bandeja", "Inbox", "01_Inbox", "Bandeja", "inbox"]

    for candidate in inbox_candidates:
        candidate_path = vault_path / candidate
        if candidate_path.exists() and candidate_path.is_dir():
            inbox_folder = candidate
            break

    if not inbox_folder:
        # Fallback: create in root
        inbox_folder = ""

    # 2. Generate title with timestamp
    ahora = datetime.now()
    titulo = ahora.strftime("Captura %Y-%m-%d %H:%M")

    # 3. Try to use "Idea" template if exists
    plantilla = ""
    templates_folder = None
    config = get_vault_config(vault_path)
    if config and config.templates_folder:
        templates_folder = config.templates_folder
    else:
        for item in vault_path.iterdir():
            if item.is_dir() and any(
                t in item.name.lower() for t in ["plantilla", "template"]
            ):
                templates_folder = item.name
                break

    if templates_folder:
        idea_template = vault_path / templates_folder / "Idea.md"
        if idea_template.exists():
            plantilla = "Idea.md"

    # 4. Create the note with inbox semantics preserved in frontmatter.
    metadata = inbox_capture_frontmatter()
    contenido = (
        "---\n"
        f"type: {metadata['type']}\n"
        f"status: {metadata['status']}\n"
        f"created: {metadata['created']}\n"
        f"updated: {metadata['updated']}\n"
        "---\n\n"
        f"{texto}"
    )

    return create_note(
        titulo=titulo,
        contenido=contenido,
        carpeta=inbox_folder,
        etiquetas=etiquetas,
        plantilla=plantilla,
    )


def append_to_section(
    nombre_archivo: str,
    seccion: str,
    contenido: str,
    crear_si_no_existe: bool = True,
) -> Result[str]:
    # pylint: disable=too-many-locals
    """Append content to a specific section of a note.

    Args:
        nombre_archivo: Name of the file to modify.
        seccion: Section heading to find (e.g., "Recursos", "## Ideas").
        contenido: Content to insert.
        crear_si_no_existe: If True, create the section if not found.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido_actual = f.read()

    # Normalize section name (remove leading # if present)
    seccion_limpia = seccion.lstrip("#").strip()

    # Find section heading at any level (##, ###, ####, etc.)
    # Pattern matches: ## Section, ### Section, etc.
    pattern = rf"^(#{{1,6}})\s+{re.escape(seccion_limpia)}\s*$"
    match = re.search(pattern, contenido_actual, re.MULTILINE | re.IGNORECASE)

    if match:
        # Found the section
        section_start = match.end()
        section_level = len(match.group(1))  # Number of # characters

        # Find the next heading of equal or higher level (fewer or equal #)
        next_heading_pattern = rf"^#{{{1},{section_level}}}\s+\S"
        remaining_content = contenido_actual[section_start:]
        next_match = re.search(next_heading_pattern, remaining_content, re.MULTILINE)

        if next_match:
            # Insert before next heading
            insert_pos = section_start + next_match.start()
            # Ensure proper spacing
            nuevo_contenido = (
                contenido_actual[:insert_pos].rstrip()
                + "\n\n"
                + contenido
                + "\n\n"
                + contenido_actual[insert_pos:].lstrip()
            )
        else:
            # No next heading, append at end of file
            nuevo_contenido = contenido_actual.rstrip() + "\n\n" + contenido + "\n"

    elif crear_si_no_existe:
        # Section not found, create it at end
        nuevo_contenido = (
            contenido_actual.rstrip() + f"\n\n## {seccion_limpia}\n\n{contenido}\n"
        )
    else:
        return Result.fail(
            f"No se encontró la sección '{seccion}' en la nota. "
            "Usa crear_si_no_existe=True para crearla."
        )

    atomic_write_text(nota_path, nuevo_contenido)

    ruta_relativa = nota_path.relative_to(vault_path)
    return Result.ok(
        f"Contenido añadido a sección '{seccion_limpia}' de {ruta_relativa}"
    )


def get_frontmatter_logic(nombre_archivo: str) -> Result[str]:
    """Retrieve only the frontmatter of a note as JSON.

    Args:
        nombre_archivo: Name of the file.

    Returns:
        Result containing the frontmatter as a JSON string.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "leer")
    if not is_allowed:
        return Result.fail(error)

    try:
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        metadata, _ = _extract_frontmatter_from_content(contenido)
        return Result.ok(
            json.dumps(metadata, indent=2, ensure_ascii=False, default=_json_serial)
        )
    except OSError as e:
        return Result.fail(f"Error al leer frontmatter: {e}")


def update_frontmatter_logic(
    nombre_archivo: str,
    frontmatter_updates: str,
    merge: bool = True,
) -> Result[str]:
    """Update the frontmatter of a note without altering the body.

    Args:
        nombre_archivo: Name of the file.
        frontmatter_updates: JSON string containing the dictionary of updates.
        merge: If True, merges with existing frontmatter. If False, replaces it.

    Returns:
        Result with success message.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    try:
        updates_dict = json.loads(frontmatter_updates)
    except json.JSONDecodeError:
        return Result.fail("frontmatter_updates debe ser un JSON string válido.")

    if not isinstance(updates_dict, dict):
        return Result.fail(
            "frontmatter_updates debe ser un objeto JSON codificado como string."
        )

    try:
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        metadata, cuerpo = _extract_frontmatter_from_content(contenido)

        if merge:
            metadata.update(updates_dict)
        else:
            metadata = updates_dict

        yaml_content = yaml.dump(
            metadata,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        nuevo_contenido = f"---\n{yaml_content}---\n{cuerpo}"

        atomic_write_text(nota_path, nuevo_contenido)

        ruta_rel = nota_path.relative_to(vault_path)
        return Result.ok(f"Frontmatter actualizado exitosamente en {ruta_rel}")
    except OSError as e:
        return Result.fail(f"Error al actualizar frontmatter: {e}")


def manage_tags_logic(
    nombre_archivo: str,
    operation: str,
    tags: str,
) -> Result[str]:
    """Add, remove, or list tags in a note's frontmatter.

    Args:
        nombre_archivo: Name of the file.
        operation: 'add', 'remove', or 'list'.
        tags: Comma-separated tags to add/remove (empty for list).

    Returns:
        Result with success message or tag list.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    try:
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        metadata, cuerpo = _extract_frontmatter_from_content(contenido)
        existing_tags = metadata.get("tags", [])

        # Normalize existing tags to a list of strings
        if isinstance(existing_tags, str):
            tags_list = [t.strip() for t in existing_tags.split(",") if t.strip()]
        elif isinstance(existing_tags, list):
            tags_list = [str(t).strip() for t in existing_tags if str(t).strip()]
        else:
            tags_list = []

        if operation == "list":
            tags_str = ", ".join(tags_list) if tags_list else "(sin etiquetas)"
            return Result.ok(f"Etiquetas en {nombre_archivo}: {tags_str}")

        input_tags = [t.strip() for t in tags.split(",") if t.strip()]

        if operation == "add":
            for t in input_tags:
                if t not in tags_list:
                    tags_list.append(t)
        elif operation == "remove":
            tags_list = [t for t in tags_list if t not in input_tags]
        else:
            return Result.fail("Operación no válida. Usa 'add', 'remove', o 'list'.")

        metadata["tags"] = tags_list

        yaml_content = yaml.dump(
            metadata,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        nuevo_contenido = f"---\n{yaml_content}---\n{cuerpo}"

        atomic_write_text(nota_path, nuevo_contenido)

        ruta_rel = nota_path.relative_to(vault_path)
        return Result.ok(
            f"Etiquetas ({operation}) actualizadas exitosamente en {ruta_rel}"
        )
    except OSError as e:
        return Result.fail(f"Error al gestionar etiquetas: {e}")
