"""
Pydantic schemas for Gemini's structured output.

These schemas define EXACTLY what Gemini must return.
The pipeline validates all AI output against these models before use.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


# ── Sub-models ───────────────────────────────────────────────────────────────

class SectorInsight(BaseModel):
    """AI interpretation of a market sector's performance."""

    name: str = Field(..., description="Sector name, e.g. 'Nifty Bank'")
    performance: str = Field(
        ...,
        description="One-sentence human interpretation of today's sector performance.",
    )
    outlook: Literal["positive", "neutral", "negative"]


class MarketEvent(BaseModel):
    """A notable market event or catalyst from today."""

    headline: str = Field(..., description="Short headline (max 12 words)")
    detail: str = Field(..., description="1-2 sentence explanation of the event's significance")
    impact: Literal["high", "medium", "low"]


class GlossaryCandidate(BaseModel):
    """
    A financial term Gemini identified in its own report.
    The glossary engine will validate and add new ones to glossary.json.
    """

    term: str = Field(..., description="The financial term (title case)")
    definition: str = Field(
        ...,
        description="Plain-English definition, 1-3 sentences. No jargon.",
    )
    category: Literal[
        "basics",
        "valuation",
        "technical-analysis",
        "fundamentals",
        "derivatives",
        "macro",
        "fixed-income",
        "commodities",
        "market-structure",
    ]

    @field_validator("term")
    @classmethod
    def validate_term(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 60:
            raise ValueError("Term must be 2-60 characters")
        return v

    @field_validator("definition")
    @classmethod
    def validate_definition(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError("Definition too short")
        return v


# ── Root report model ─────────────────────────────────────────────────────────

class DailyReport(BaseModel):
    """
    The complete structured daily market report produced by Gemini.

    Every field is required — Gemini must populate all of them.
    The pipeline validates this model before generating HTML or sending email.
    """

    date: str = Field(..., description="Report date in ISO 8601 format: YYYY-MM-DD")

    overall_sentiment: Literal["bullish", "neutral", "bearish"] = Field(
        ...,
        description=(
            "Overall market sentiment for the day. "
            "'bullish' = broadly positive, 'bearish' = broadly negative, "
            "'neutral' = mixed or sideways."
        ),
    )

    tldr: list[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description=(
            "3-5 bullet points summarising the most important market events of the day. "
            "Each bullet should be ≤20 words."
        ),
    )

    india_summary: str = Field(
        ...,
        description=(
            "2-3 paragraph narrative analysis of Indian market performance. "
            "Reference specific indices and sector movements."
        ),
    )

    international_summary: str = Field(
        ...,
        description=(
            "1-2 paragraph narrative analysis of international market performance "
            "and its potential impact on Indian markets."
        ),
    )

    sectors: list[SectorInsight] = Field(
        ...,
        min_length=1,
        description="AI interpretation of each sector's performance.",
    )

    key_events: list[MarketEvent] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1-5 notable market events or catalysts from today.",
    )

    glossary_terms: list[GlossaryCandidate] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Financial terms used in this report that belong in the glossary. "
            "Include terms that readers might not know. Do NOT include obvious terms "
            "already in common usage."
        ),
    )

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        from datetime import date
        try:
            date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"date must be YYYY-MM-DD, got: {v!r}") from exc
        return v

    @field_validator("india_summary", "international_summary")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError("Summary too short — must be at least 50 characters")
        return v.strip()
