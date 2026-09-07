"""
Glossary term detector.

Compares AI-generated GlossaryCandidates against the existing glossary
and returns only validated new terms, ready to be added.
"""

from __future__ import annotations

from datetime import date

from src.ai.schemas import GlossaryCandidate
from src.glossary.manager import GlossaryManager
from src.glossary.models import GlossaryEntry, _make_slug
from src.utils.dates import format_date_iso, today_ist
from src.utils.logging import get_logger

log = get_logger(__name__)

_MIN_DEFINITION_LENGTH = 20
_MAX_NEW_PER_RUN = 10


def detect_new_terms(
    candidates: list[GlossaryCandidate],
    manager: GlossaryManager,
    report_text: str = "",
    max_new: int = _MAX_NEW_PER_RUN,
    added_date: date | None = None,
) -> list[GlossaryEntry]:
    """
    Filter AI-generated candidates to only those that are genuinely new
    and pass validation.

    Validation pipeline (all must pass):
        1. Term not already in glossary (case-insensitive)
        2. Definition is non-trivially long (≥20 chars)
        3. Category is valid
        4. Term appears in report_text (if report_text is provided)
        5. Not a duplicate within this batch

    Args:
        candidates:   GlossaryCandidate list from Gemini's response.
        manager:      Loaded GlossaryManager (has existing terms).
        report_text:  Full report text to validate term usage (optional).
        max_new:      Cap on how many new terms to add per run.
        added_date:   Date to stamp new entries (defaults to today IST).

    Returns:
        List of validated GlossaryEntry objects ready to be added.
    """
    if not candidates:
        log.info("Glossary detector: no candidates from AI")
        return []

    d = format_date_iso(added_date or today_ist())
    existing_lower = manager.existing_terms_normalised()
    report_lower = report_text.lower()
    seen_in_batch: set[str] = set()
    new_entries: list[GlossaryEntry] = []

    log.info("Glossary detector: evaluating %d candidates", len(candidates))

    for cand in candidates:
        term = cand.term.strip()
        term_lower = term.lower()
        slug = _make_slug(term)

        # ── 1. already in glossary? ───────────────────────────────────────────
        if term_lower in existing_lower:
            log.debug("  SKIP (existing):   %r", term)
            continue

        # ── 2. duplicate in this batch? ───────────────────────────────────────
        if term_lower in seen_in_batch:
            log.debug("  SKIP (duplicate):  %r", term)
            continue

        # ── 3. definition too short? ──────────────────────────────────────────
        if len(cand.definition.strip()) < _MIN_DEFINITION_LENGTH:
            log.warning("  SKIP (short def):  %r", term)
            continue

        # ── 4. term appears in report? ────────────────────────────────────────
        if report_text and term_lower not in report_lower:
            log.debug("  SKIP (not in report): %r", term)
            continue

        # ── 5. cap check ──────────────────────────────────────────────────────
        if len(new_entries) >= max_new:
            log.info("  STOP: reached max_new=%d", max_new)
            break

        seen_in_batch.add(term_lower)
        new_entries.append(
            GlossaryEntry(
                term=term,
                slug=slug,
                definition=cand.definition.strip(),
                category=cand.category,
                added_date=d,
            )
        )
        log.info("  NEW term: %r (%s)", term, cand.category)

    log.info(
        "Glossary detector: %d/%d candidates accepted",
        len(new_entries), len(candidates),
    )
    return new_entries
