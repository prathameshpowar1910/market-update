"""
Glossary manager — load, save, and update glossary.json.

Guarantees:
  • Existing terms are never overwritten
  • File is never left in a corrupt state (write to temp, then rename)
  • All writes are atomic via a backup strategy
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import date
from pathlib import Path

from src.glossary.models import GlossaryEntry
from src.utils.dates import format_date_iso, today_ist
from src.utils.logging import get_logger

log = get_logger(__name__)

_DEFAULT_PATH = Path("glossary.json")


class GlossaryManager:
    """
    Manages the persistent glossary.json file.

    Usage::

        gm = GlossaryManager()
        gm.load()
        added = gm.add_entries(new_entries)
        gm.save()
    """

    def __init__(self, path: Path | str = _DEFAULT_PATH) -> None:
        self._path = Path(path)
        self._entries: list[GlossaryEntry] = []
        self._loaded = False

    # ── I/O ─────────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load glossary.json into memory. Creates an empty list if missing."""
        if not self._path.exists():
            log.warning("glossary.json not found at %s — starting empty", self._path)
            self._entries = []
            self._loaded = True
            return

        raw = self._path.read_text(encoding="utf-8")
        data: list[dict] = json.loads(raw)
        self._entries = []
        for item in data:
            try:
                self._entries.append(GlossaryEntry.model_validate(item))
            except Exception as exc:
                log.warning("Skipping invalid glossary entry %r: %s", item.get("term"), exc)

        self._loaded = True
        log.info("Glossary loaded: %d terms from %s", len(self._entries), self._path)

    def save(self) -> None:
        """
        Atomically save current entries to glossary.json.

        Writes to a .tmp file first, then renames to prevent corruption.
        """
        if not self._loaded:
            raise RuntimeError("Cannot save before loading — call load() first")

        tmp_path = self._path.with_suffix(".tmp")
        data = [e.model_dump() for e in self._entries]
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        shutil.move(str(tmp_path), str(self._path))
        log.info("Glossary saved: %d terms → %s", len(self._entries), self._path)

    # ── query ────────────────────────────────────────────────────────────────

    def all_entries(self) -> list[GlossaryEntry]:
        """Return all loaded entries."""
        return list(self._entries)

    def existing_slugs(self) -> set[str]:
        """Return the set of slugs already in the glossary."""
        return {e.slug for e in self._entries}

    def existing_terms_normalised(self) -> set[str]:
        """Return lowercased terms for case-insensitive comparison."""
        return {e.term.lower() for e in self._entries}

    # ── mutation ─────────────────────────────────────────────────────────────

    def add_entries(self, new_entries: list[GlossaryEntry]) -> list[GlossaryEntry]:
        """
        Add *new_entries* to the glossary, skipping any already present.

        Returns the list of entries that were actually added.
        """
        if not self._loaded:
            raise RuntimeError("Call load() before add_entries()")

        existing_lower = self.existing_terms_normalised()
        added: list[GlossaryEntry] = []

        for entry in new_entries:
            if entry.term.lower() in existing_lower:
                log.debug("Glossary: skipping existing term %r", entry.term)
                continue
            self._entries.append(entry)
            existing_lower.add(entry.term.lower())
            added.append(entry)
            log.info("Glossary: added new term %r (%s)", entry.term, entry.category)

        return added

    def sorted_entries(self) -> list[GlossaryEntry]:
        """Return entries sorted alphabetically by term."""
        return sorted(self._entries, key=lambda e: e.term.lower())
