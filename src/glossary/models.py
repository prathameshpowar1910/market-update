"""Pydantic models for the glossary."""

from __future__ import annotations

import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_CATEGORIES = frozenset({
    "basics",
    "valuation",
    "technical-analysis",
    "fundamentals",
    "derivatives",
    "macro",
    "fixed-income",
    "commodities",
    "market-structure",
})


def _make_slug(term: str) -> str:
    """
    Convert a term to a URL-safe slug.
    e.g. 'P/E Ratio' → 'p-e-ratio'
    """
    slug = term.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class GlossaryEntry(BaseModel):
    """A single glossary term stored in glossary.json."""

    term: str
    slug: str = ""
    definition: str
    category: str
    added_date: str

    @field_validator("term")
    @classmethod
    def validate_term(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 60:
            raise ValueError(f"Term length out of range: {v!r}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category {v!r}. "
                f"Allowed: {sorted(VALID_CATEGORIES)}"
            )
        return v

    @model_validator(mode="after")
    def ensure_slug(self) -> "GlossaryEntry":
        if not self.slug:
            self.slug = _make_slug(self.term)
        return self
