"""Shared pytest fixtures for all test modules."""

import pytest
from datetime import date


@pytest.fixture
def sample_date() -> date:
    return date(2026, 9, 7)


@pytest.fixture
def sample_glossary_entries():
    from src.glossary.models import GlossaryEntry
    return [
        GlossaryEntry(term="P/E Ratio",   slug="p-e-ratio",   definition="Price-to-Earnings ratio.", category="valuation",   added_date="2026-09-01"),
        GlossaryEntry(term="Market Cap",  slug="market-cap",  definition="Total market value.",      category="basics",      added_date="2026-09-01"),
        GlossaryEntry(term="Bull Market", slug="bull-market", definition="Rising market condition.", category="basics",      added_date="2026-09-01"),
    ]


@pytest.fixture
def sample_report():
    from src.ai.schemas import DailyReport, SectorInsight, MarketEvent, GlossaryCandidate
    return DailyReport(
        date="2026-09-07",
        overall_sentiment="bullish",
        tldr=["Nifty 50 rose 1.2%", "Banking sector outperformed", "FIIs turned net buyers"],
        india_summary="Indian markets rallied today as banking stocks led gains. The NIFTY 50 index closed above the 25,000 mark for the first time this month. FII inflows supported the broader market breadth.",
        international_summary="Global markets were mixed as the S&P 500 edged higher. US economic data remained resilient, supporting risk appetite across emerging markets including India.",
        sectors=[
            SectorInsight(name="Nifty Bank", performance="Banking stocks outperformed on RBI policy optimism.", outlook="positive"),
            SectorInsight(name="Nifty IT",   performance="IT sector was flat amid global tech weakness.",      outlook="neutral"),
        ],
        key_events=[
            MarketEvent(headline="RBI holds repo rate steady", detail="The Reserve Bank of India kept rates unchanged.", impact="high"),
        ],
        glossary_terms=[
            GlossaryCandidate(term="Market Breadth", definition="A measure comparing the number of advancing stocks to declining stocks.", category="technical-analysis"),
            GlossaryCandidate(term="Yield Curve",    definition="A graph showing the relationship between bond yields and maturities.", category="macro"),
        ],
    )
