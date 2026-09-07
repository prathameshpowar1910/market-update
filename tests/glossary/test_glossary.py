"""Tests for the automatic glossary engine."""

import json
import tempfile
from pathlib import Path

import pytest
from src.ai.schemas import GlossaryCandidate
from src.glossary.detector import detect_new_terms
from src.glossary.linker import link_glossary_terms
from src.glossary.manager import GlossaryManager
from src.glossary.models import GlossaryEntry, _make_slug


# ── Slug generation ──────────────────────────────────────────────────────────

class TestSlugGeneration:
    def test_simple_term(self):
        assert _make_slug("Market Cap") == "market-cap"

    def test_special_chars(self):
        assert _make_slug("P/E Ratio") == "pe-ratio"

    def test_multiple_spaces(self):
        assert _make_slug("Bull  Market") == "bull-market"

    def test_lowercase(self):
        assert _make_slug("NIFTY 50") == "nifty-50"

    def test_leading_trailing_spaces(self):
        assert _make_slug("  Yield Curve  ") == "yield-curve"


# ── GlossaryManager ──────────────────────────────────────────────────────────

class TestGlossaryManager:
    @pytest.fixture
    def tmp_glossary(self, tmp_path):
        data = [
            {"term": "P/E Ratio", "slug": "p-e-ratio", "definition": "Price-to-Earnings.", "category": "valuation", "added_date": "2026-09-01"},
            {"term": "Market Cap", "slug": "market-cap", "definition": "Total market value.", "category": "basics", "added_date": "2026-09-01"},
        ]
        f = tmp_path / "glossary.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        return f

    def test_load(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        assert len(gm.all_entries()) == 2

    def test_legacy_entries_are_preserved_when_adding(self, tmp_path):
        f = tmp_path / "glossary.json"
        f.write_text(json.dumps([
            {
                "term": "Legacy Term",
                "slug": "legacy-term",
                "definition": "An entry from the original glossary format.",
                "category": "basics",
            }
        ]), encoding="utf-8")
        gm = GlossaryManager(f)
        gm.load()
        gm.add_entries([
            GlossaryEntry(
                term="New Term",
                slug="new-term",
                definition="An entry added by the current pipeline.",
                category="basics",
                added_date="2026-09-07",
            )
        ])
        gm.save()

        saved_terms = {entry["term"] for entry in json.loads(f.read_text(encoding="utf-8"))}
        assert saved_terms == {"Legacy Term", "New Term"}

    def test_existing_terms_normalised(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        assert "p/e ratio" in gm.existing_terms_normalised()
        assert "market cap" in gm.existing_terms_normalised()

    def test_add_new_entry(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        new = GlossaryEntry(term="Bull Market", slug="bull-market", definition="Rising trend.", category="basics", added_date="2026-09-07")
        added = gm.add_entries([new])
        assert len(added) == 1
        assert len(gm.all_entries()) == 3

    def test_skip_existing_entry(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        dup = GlossaryEntry(term="P/E Ratio", slug="p-e-ratio", definition="Duplicate.", category="valuation", added_date="2026-09-07")
        added = gm.add_entries([dup])
        assert len(added) == 0
        assert len(gm.all_entries()) == 2

    def test_case_insensitive_dedup(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        dup = GlossaryEntry(term="p/e ratio", slug="p-e-ratio", definition="Lowercase version.", category="valuation", added_date="2026-09-07")
        added = gm.add_entries([dup])
        assert len(added) == 0

    def test_atomic_save(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        new = GlossaryEntry(term="EPS", slug="eps", definition="Earnings Per Share.", category="fundamentals", added_date="2026-09-07")
        gm.add_entries([new])
        gm.save()
        gm2 = GlossaryManager(tmp_glossary)
        gm2.load()
        assert len(gm2.all_entries()) == 3

    def test_sorted_entries(self, tmp_glossary):
        gm = GlossaryManager(tmp_glossary)
        gm.load()
        s = gm.sorted_entries()
        assert s[0].term.lower() <= s[1].term.lower()


# ── Detector ─────────────────────────────────────────────────────────────────

class TestDetector:
    @pytest.fixture
    def loaded_manager(self, tmp_path):
        data = [{"term": "P/E Ratio", "slug": "p-e-ratio", "definition": "Price-to-Earnings.", "category": "valuation", "added_date": "2026-09-01"}]
        f = tmp_path / "glossary.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        gm = GlossaryManager(f)
        gm.load()
        return gm

    def _cand(self, term, definition="A detailed definition here.", category="basics"):
        return GlossaryCandidate(term=term, definition=definition, category=category)

    def test_new_term_accepted(self, loaded_manager):
        cands = [self._cand("Market Breadth", "Number of advancing vs declining stocks.", "technical-analysis")]
        new = detect_new_terms(cands, loaded_manager, report_text="market breadth improved today")
        assert len(new) == 1
        assert new[0].term == "Market Breadth"

    def test_existing_term_rejected(self, loaded_manager):
        cands = [self._cand("P/E Ratio")]
        new = detect_new_terms(cands, loaded_manager, report_text="p/e ratio was discussed")
        assert len(new) == 0

    def test_case_insensitive_existing(self, loaded_manager):
        cands = [self._cand("p/e ratio")]
        new = detect_new_terms(cands, loaded_manager, report_text="p/e ratio analysis")
        assert len(new) == 0

    def test_not_in_report_rejected(self, loaded_manager):
        cands = [self._cand("Yield Curve", "A graph of bond yields.", "macro")]
        new = detect_new_terms(cands, loaded_manager, report_text="banking sector performed well")
        assert len(new) == 0

    def test_short_definition_rejected(self, loaded_manager):
        cand = GlossaryCandidate.model_construct(term="EPS", definition="Short.", category="fundamentals")
        cands = [cand]
        new = detect_new_terms(cands, loaded_manager, report_text="eps improved")
        assert len(new) == 0

    def test_duplicate_in_batch_rejected(self, loaded_manager):
        cands = [
            self._cand("Market Breadth", "Number of advancing stocks.", "technical-analysis"),
            self._cand("Market Breadth", "Duplicate definition.", "technical-analysis"),
        ]
        new = detect_new_terms(cands, loaded_manager, report_text="market breadth today")
        assert len(new) == 1

    def test_max_per_run_cap(self, loaded_manager):
        cands = [self._cand(f"Term{i}", f"A sufficiently long definition for term {i} in the glossary.", "basics") for i in range(20)]
        report = " ".join(f"term{i}" for i in range(20))
        new = detect_new_terms(cands, loaded_manager, report_text=report, max_new=5)
        assert len(new) <= 5


# ── Linker ────────────────────────────────────────────────────────────────────

class TestLinker:
    @pytest.fixture
    def entries(self):
        return [
            GlossaryEntry(term="Market Breadth", slug="market-breadth", definition="Advancing vs declining.", category="technical-analysis", added_date="2026-09-07"),
            GlossaryEntry(term="Bull Market",    slug="bull-market",    definition="Rising trend.",            category="basics",            added_date="2026-09-07"),
        ]

    def test_term_is_linked(self, entries):
        html = "<p>Today's market breadth improved significantly.</p>"
        out = link_glossary_terms(html, entries)
        assert 'href="glossary.html#market-breadth"' in out

    def test_only_first_occurrence(self, entries):
        html = "<p>Market breadth is good. Market breadth was high.</p>"
        out = link_glossary_terms(html, entries, first_only=True)
        assert out.count('href="glossary.html#market-breadth"') == 1

    def test_existing_link_not_double_linked(self, entries):
        html = '<a href="/foo">Market Breadth</a> is the market breadth measure.'
        out = link_glossary_terms(html, entries)
        # The one inside <a> should NOT get re-linked
        assert out.count('href="glossary.html#market-breadth"') <= 1

    def test_case_insensitive_match(self, entries):
        html = "<p>MARKET BREADTH was positive.</p>"
        out = link_glossary_terms(html, entries)
        assert 'href="glossary.html#market-breadth"' in out

    def test_no_entries_returns_unchanged(self):
        html = "<p>Some text here.</p>"
        out = link_glossary_terms(html, [])
        assert out == html

    def test_link_has_title_attribute(self, entries):
        html = "<p>The bull market continues.</p>"
        out = link_glossary_terms(html, entries)
        assert 'title=' in out
