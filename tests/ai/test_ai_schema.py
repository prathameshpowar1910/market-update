"""Tests for AI schema validation."""

import pytest
from pydantic import ValidationError
from src.ai.schemas import DailyReport, GlossaryCandidate, SectorInsight, MarketEvent


class TestDailyReportSchema:
    def _base(self, **overrides):
        defaults = dict(
            date="2026-09-07",
            overall_sentiment="bullish",
            tldr=["Point one", "Point two", "Point three"],
            india_summary="A sufficiently long India summary that describes market events clearly.",
            international_summary="A sufficiently long international summary describing global markets.",
            sectors=[SectorInsight(name="Nifty Bank", performance="Banks rose on rate optimism.", outlook="positive")],
            key_events=[MarketEvent(headline="RBI holds rates steady", detail="The RBI kept rates unchanged.", impact="high")],
            glossary_terms=[],
        )
        defaults.update(overrides)
        return defaults

    def test_valid_report(self):
        r = DailyReport(**self._base())
        assert r.overall_sentiment == "bullish"

    def test_invalid_sentiment(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(overall_sentiment="very_bullish"))

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(date="07-09-2026"))

    def test_too_few_tldr(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(tldr=["Just one"]))

    def test_too_many_tldr(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(tldr=["a", "b", "c", "d", "e", "f"]))

    def test_india_summary_too_short(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(india_summary="Too short."))

    def test_international_summary_too_short(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(international_summary="Too short."))

    def test_empty_key_events(self):
        with pytest.raises(ValidationError):
            DailyReport(**self._base(key_events=[]))

    def test_glossary_terms_optional(self):
        r = DailyReport(**self._base(glossary_terms=[]))
        assert r.glossary_terms == []

    def test_all_sentiments_valid(self):
        for s in ("bullish", "neutral", "bearish"):
            r = DailyReport(**self._base(overall_sentiment=s))
            assert r.overall_sentiment == s


class TestGlossaryCandidate:
    def test_valid_candidate(self):
        c = GlossaryCandidate(
            term="Market Breadth",
            definition="A measure of advancing vs declining stocks.",
            category="technical-analysis",
        )
        assert c.term == "Market Breadth"

    def test_term_too_short(self):
        with pytest.raises(ValidationError):
            GlossaryCandidate(term="X", definition="A valid definition here.", category="basics")

    def test_term_too_long(self):
        with pytest.raises(ValidationError):
            GlossaryCandidate(term="X" * 61, definition="Valid definition.", category="basics")

    def test_definition_too_short(self):
        with pytest.raises(ValidationError):
            GlossaryCandidate(term="EPS", definition="Short.", category="fundamentals")

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            GlossaryCandidate(term="EPS", definition="Earnings per share.", category="made-up-category")

    def test_all_valid_categories(self):
        valid = ["basics", "valuation", "technical-analysis", "fundamentals",
                 "derivatives", "macro", "fixed-income", "commodities", "market-structure"]
        for cat in valid:
            c = GlossaryCandidate(term="Test Term", definition="A valid definition here.", category=cat)
            assert c.category == cat


class TestSectorInsight:
    def test_valid_outlooks(self):
        for o in ("positive", "neutral", "negative"):
            s = SectorInsight(name="Nifty Bank", performance="Banks performed well.", outlook=o)
            assert s.outlook == o

    def test_invalid_outlook(self):
        with pytest.raises(ValidationError):
            SectorInsight(name="Nifty Bank", performance="Performed.", outlook="great")


class TestMarketEvent:
    def test_valid_impacts(self):
        for i in ("high", "medium", "low"):
            e = MarketEvent(headline="Test event happened today", detail="Detail about the event.", impact=i)
            assert e.impact == i

    def test_invalid_impact(self):
        with pytest.raises(ValidationError):
            MarketEvent(headline="Test", detail="Detail.", impact="critical")
