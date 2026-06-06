"""
Middleware for vault rule enforcement.

Loads machine-readable validations from .agents/REGLAS_GLOBALES.md,
runs checks against content on write operations, and enriches tool
responses with warnings and rule prose.

This is agent-agnostic: any MCP client receives the same enforcement.
"""

import re
from typing import Any

import yaml

from .config import get_vault_path
from .utils import get_logger

logger = get_logger(__name__)

# --- Cache ---

_rules_cache: list[dict[str, Any]] | None = None  # pylint: disable=invalid-name
_prose_cache: str | None = None  # pylint: disable=invalid-name

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def _read_rules_file() -> tuple[dict[str, Any], str]:
    """Read and parse REGLAS_GLOBALES.md, returning (frontmatter_dict, prose_body)."""
    vault_path = get_vault_path()
    if not vault_path:
        return {}, ""

    rules_path = vault_path / ".agents" / "REGLAS_GLOBALES.md"
    if not rules_path.exists():
        return {}, ""

    try:
        content = rules_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Could not read rules file: %s", e)
        return {}, ""

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return {}, match.group(2).strip()
        return frontmatter, match.group(2).strip()
    except yaml.YAMLError as e:
        logger.warning("Malformed YAML in REGLAS_GLOBALES.md: %s", e)
        return {}, ""


def load_vault_rules(force_reload: bool = False) -> list[dict[str, Any]]:
    """Load validations from vault rules frontmatter. Cached in memory."""
    global _rules_cache  # pylint: disable=global-statement
    if _rules_cache is not None and not force_reload:
        return _rules_cache

    frontmatter, _ = _read_rules_file()
    validations = frontmatter.get("validations", [])
    _rules_cache = validations if isinstance(validations, list) else []
    return _rules_cache


def load_vault_rules_prose(force_reload: bool = False) -> str:
    """Load the prose body of REGLAS_GLOBALES.md (without frontmatter). Cached."""
    global _prose_cache  # pylint: disable=global-statement
    if _prose_cache is not None and not force_reload:
        return _prose_cache

    _, prose = _read_rules_file()
    _prose_cache = prose
    return _prose_cache


def invalidate_rules_cache() -> None:
    """Invalidate both caches. Called when REGLAS_GLOBALES.md is edited."""
    global _rules_cache, _prose_cache  # pylint: disable=global-statement
    _rules_cache = None
    _prose_cache = None


# --- Validation Engine ---


def run_validations(
    rules: list[dict[str, Any]],
    mode: str,
    title: str = "",
    content: str = "",
    frontmatter: dict[str, Any] | None = None,
) -> list[str]:
    """Run applicable validations and return list of warning strings."""
    return [
        warning
        for _, warning in iter_violations(
            rules, mode, title=title, content=content, frontmatter=frontmatter
        )
    ]


def iter_violations(
    rules: list[dict[str, Any]],
    mode: str | None,
    *,
    title: str = "",
    content: str = "",
    frontmatter: dict[str, Any] | None = None,
) -> list[tuple[dict[str, Any], str]]:
    """Like ``run_validations`` but also returns the rule that fired.

    Public surface used by ``vault.lint`` (Issue #9) to decide which
    violations are auto-fixable per-rule.

    Pass ``mode=None`` to ignore each rule's ``applies_to`` filter --
    useful for whole-vault lint sweeps where every rule should be
    enforced regardless of write mode.
    """
    pairs: list[tuple[dict[str, Any], str]] = []
    for rule in rules:
        if mode is not None and mode not in rule.get("applies_to", []):
            continue
        warning = _check_rule(rule, title, content, frontmatter or {})
        if warning:
            pairs.append((rule, warning))
    return pairs


def _check_rule(
    rule: dict[str, Any], title: str, content: str, fm: dict[str, Any]
) -> str | None:
    """Execute a single rule. Returns warning string or None."""
    scope = rule.get("scope", "")

    if scope in ("headings", "title", "body") and "pattern" in rule:
        return _check_pattern(rule, title, content)

    if scope == "frontmatter":
        if "required_fields" in rule:
            return _check_required_fields(rule, fm)
        if "field" in rule and "allowed_values" in rule:
            return _check_allowed_values(rule, fm)

    return None


def _check_pattern(rule: dict[str, Any], title: str, content: str) -> str | None:
    """Validate regex against the indicated scope."""
    try:
        pattern = re.compile(rule["pattern"])
    except re.error as e:
        logger.warning("Invalid regex in rule '%s': %s", rule.get("id", "?"), e)
        return None

    scope = rule["scope"]

    if scope == "title":
        if pattern.search(title):
            return rule["warning"]
    elif scope == "headings":
        for line in content.splitlines():
            if line.startswith("#") and pattern.search(line):
                return rule["warning"]
    elif scope == "body":
        if pattern.search(content):
            return rule["warning"]

    return None


def _check_required_fields(rule: dict[str, Any], fm: dict[str, Any]) -> str | None:
    """Check that required frontmatter fields are present and non-empty."""
    missing = [f for f in rule["required_fields"] if f not in fm or not fm[f]]
    if missing:
        return rule["warning"].format(missing_fields=", ".join(missing))
    return None


def _check_allowed_values(rule: dict[str, Any], fm: dict[str, Any]) -> str | None:
    """Check that a frontmatter field value is in the allowed list."""
    field = rule["field"]
    value = fm.get(field, "")
    if value and value not in rule["allowed_values"]:
        return rule["warning"].format(value=value)
    return None


# --- Auto-fix Engine (Issue #9) ---


def is_rule_autofixable(rule: dict[str, Any]) -> bool:
    """Return True iff ``rule`` is one of the kinds ``apply_autofix`` handles.

    Currently: regex-based ``scope=headings`` or ``scope=body`` rules with a
    ``pattern``. These map cleanly to ``re.sub(pattern, "", ...)``.

    Frontmatter rules (``required_fields``, ``allowed_values``) need
    semantic user input and are intentionally NOT auto-fixed.
    """
    if "pattern" not in rule:
        return False
    return rule.get("scope") in {"headings", "body"}


def apply_autofix(rule: dict[str, Any], content: str) -> tuple[str, int]:
    """Apply ``rule`` as an in-place rewrite of ``content``.

    For ``scope=headings``: strip every match of ``rule['pattern']`` from
    lines that start with ``#`` (after lstrip). For ``scope=body``: strip
    every match anywhere. Whitespace collapse is applied to keep
    headings readable after emoji removal.

    Returns ``(new_content, replacement_count)``. Counts pattern hits,
    not lines touched.
    """
    if not is_rule_autofixable(rule):
        return content, 0

    try:
        pattern = re.compile(rule["pattern"])
    except re.error:
        return content, 0

    scope = rule["scope"]
    count = 0

    if scope == "headings":
        new_lines: list[str] = []
        for line in content.splitlines(keepends=True):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                new_line, n = pattern.subn("", line)
                if n:
                    count += n
                    # Collapse "## " + emoji + " title" -> "## title"
                    new_line = re.sub(r"^(#+)\s+\s+", r"\1 ", new_line)
                    new_line = re.sub(r"^(#+)\s+$", r"\1", new_line)
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        return "".join(new_lines), count

    # scope == "body"
    new_content, count = pattern.subn("", content)
    return new_content, count


# --- Response Enrichment ---

CONTENT_CREATION_TOOLS = frozenset({"notes.create", "notes.append"})

TOOL_MODE_MAP: dict[str, str] = {
    "notes.create": "create",
    "inbox.capture": "create",
    "notes.append": "append",
    "notes.patch": "edit",
    "notes.replace": "edit",
    "notes.update_frontmatter": "edit",
    # Canvas card text is markdown too — enforce the same heading/body rules
    # (AFP issue #50). Cards aren't notes, so prose isn't injected.
    "canvas.add_card": "create",
    "canvas.update_card": "edit",
}


def enrich_response(
    tool_name: str,
    result: str,
    title: str = "",
    content: str = "",
    frontmatter: dict[str, Any] | None = None,
) -> str:
    """Main entry point. Run validations and inject rules prose into tool response."""
    mode = TOOL_MODE_MAP.get(tool_name)
    if not mode:
        return result

    rules = load_vault_rules()
    warnings = run_validations(rules, mode, title, content, frontmatter)

    parts = [result]

    if warnings:
        parts.append("---")
        parts.append(f"[WARNINGS: {len(warnings)} violacion(es) detectada(s)]")
        for w in warnings:
            parts.append(f"- {w}")

        if tool_name in CONTENT_CREATION_TOOLS:
            prose = load_vault_rules_prose()
            if prose:
                parts.append("---")
                parts.append("[REGLAS ACTIVAS DEL VAULT]")
                parts.append(prose)
    elif tool_name in CONTENT_CREATION_TOOLS:
        parts.append("---")
        parts.append(
            "[Reglas del vault activas. Llama a get_global_rules() si necesitas el texto completo.]"
        )

    return "\n".join(parts)
