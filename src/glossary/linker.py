"""
Glossary linker — post-processes HTML to hyperlink glossary terms.

Example:
  Input:  "Today's market breadth improved."
  Output: 'Today's <a href="/glossary.html#market-breadth">market breadth</a> improved.'

Rules:
  • Only links the FIRST occurrence of each term per HTML block
  • Case-insensitive matching, preserves original capitalisation
  • Does not modify text inside existing <a>, <code>, <pre> tags
  • Longest-match-first to avoid partial replacements
"""

from __future__ import annotations

import re

from src.glossary.models import GlossaryEntry
from src.utils.logging import get_logger

log = get_logger(__name__)

# Tags whose content should never be modified
_PROTECTED_TAGS = re.compile(
    r"<(a|code|pre|script|style)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)


def _protect_regions(html: str) -> tuple[str, dict[str, str]]:
    """
    Replace protected tag content with unique tokens to avoid modifying them.

    Returns:
        (modified_html, token_map) where token_map maps token → original text.
    """
    token_map: dict[str, str] = {}
    counter = 0

    def replacer(m: re.Match) -> str:
        nonlocal counter
        token = f"\x00PROTECT{counter}\x00"
        token_map[token] = m.group(0)
        counter += 1
        return token

    return _PROTECTED_TAGS.sub(replacer, html), token_map


def _restore_regions(html: str, token_map: dict[str, str]) -> str:
    """Restore protected regions from their tokens."""
    for token, original in token_map.items():
        html = html.replace(token, original)
    return html


def link_glossary_terms(
    html: str,
    entries: list[GlossaryEntry],
    glossary_path: str = "/glossary.html",
    first_only: bool = True,
) -> str:
    """
    Wrap glossary terms in the HTML with anchor links.

    Args:
        html:           HTML string to post-process.
        entries:        List of all glossary entries.
        glossary_path:  URL path to the glossary page.
        first_only:     If True, only link the first occurrence of each term.

    Returns:
        HTML with glossary terms hyperlinked.
    """
    if not entries or not html:
        return html

    # Sort longest-match-first to avoid "Market Cap" being partially
    # replaced before "Market Capitalisation"
    sorted_entries = sorted(entries, key=lambda e: len(e.term), reverse=True)

    # Protect regions we must not touch
    html, token_map = _protect_regions(html)

    linked: set[str] = set()

    for entry in sorted_entries:
        term_lower = entry.term.lower()

        if first_only and term_lower in linked:
            continue

        pattern = re.compile(
            r"(?<![a-zA-Z])" + re.escape(entry.term) + r"(?![a-zA-Z])",
            re.IGNORECASE,
        )

        def _replace(m: re.Match, _entry: GlossaryEntry = entry) -> str:
            return (
                f'<a href="{glossary_path}#{_entry.slug}" '
                f'class="glossary-link" '
                f'title="{_entry.definition[:80]}...">'
                f"{m.group(0)}"
                f"</a>"
            )

        if first_only:
            new_html, count = pattern.subn(_replace, html, count=1)
        else:
            new_html, count = pattern.subn(_replace, html)

        if count:
            html = new_html
            linked.add(term_lower)
            log.debug("Glossary linker: linked %r (%d occurrence(s))", entry.term, count)

    html = _restore_regions(html, token_map)
    log.info("Glossary linker: linked %d unique terms", len(linked))
    return html
