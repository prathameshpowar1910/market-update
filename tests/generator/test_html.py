"""Tests for HTML generation."""

import json
import tempfile
from pathlib import Path
from datetime import date

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


# ── Helper: render a template string directly ─────────────────────────────────

def _render_template(template_str: str, **ctx) -> str:
    env = Environment(autoescape=select_autoescape(["html"]))
    tmpl = env.from_string(template_str)
    return tmpl.render(**ctx)


# ── HTMLGenerator integration tests ──────────────────────────────────────────

class TestHTMLGenerator:
    @pytest.fixture
    def generator(self, tmp_path):
        from src.generator.html import HTMLGenerator
        templates_dir = Path("site/templates")
        output_dir = tmp_path / "generated"
        static_dir = Path("site/static")
        return HTMLGenerator(
            templates_dir=templates_dir,
            output_dir=output_dir,
            static_dir=static_dir,
        )

    @pytest.fixture
    def india_data(self):
        from src.market.models import IndiaMarketData, IndexData, MarketDirection
        return IndiaMarketData(
            date="2026-09-07",
            indices=[
                IndexData(
                    symbol="NIFTY_50", name="Nifty 50", display_name="NIFTY 50",
                    price=25000, change=300, change_pct=1.2,
                    direction=MarketDirection.UP,
                )
            ],
        )

    @pytest.fixture
    def intl_data(self):
        from src.market.models import InternationalMarketData, IndexData, MarketDirection
        return InternationalMarketData(
            date="2026-09-07",
            indices=[
                IndexData(
                    symbol="SPY", name="S&P 500", display_name="S&P 500",
                    price=5500, change=15, change_pct=0.27,
                    direction=MarketDirection.UP,
                )
            ],
        )

    def test_daily_page_generated(self, generator, sample_report, india_data, intl_data, sample_glossary_entries, sample_date):
        path = generator.generate_daily(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            glossary_entries=sample_glossary_entries,
            report_date=sample_date,
        )
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "Daily Market Report" in html
        assert "NIFTY 50" in html
        assert "Market pulse" in html
        assert "Sector breadth" in html

    def test_daily_page_includes_optional_market_details(self, generator, sample_report, india_data, intl_data, sample_glossary_entries, sample_date):
        india_data.indices[0].previous_close = 24700
        india_data.indices[0].volume = 1234567
        path = generator.generate_daily(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            glossary_entries=sample_glossary_entries,
            report_date=sample_date,
        )
        html = path.read_text(encoding="utf-8")
        assert "Prev close" in html
        assert "Vol 1,234,567" in html

    def test_daily_page_contains_tldr(self, generator, sample_report, india_data, intl_data, sample_glossary_entries, sample_date):
        path = generator.generate_daily(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            glossary_entries=sample_glossary_entries,
            report_date=sample_date,
        )
        html = path.read_text(encoding="utf-8")
        assert sample_report.tldr[0] in html

    def test_index_page_generated(self, generator, sample_report, india_data, intl_data, sample_date):
        path = generator.generate_index(
            latest_report=sample_report,
            india=india_data,
            intl=intl_data,
            archive_dates=["2026-09-06", "2026-09-05"],
            report_date=sample_date,
        )
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "Market Digest" in html
        assert "2026-09-06" in html
        assert f'href="{sample_date.isoformat()}.html"' in html
        assert "Today in numbers" in html
        assert "NIFTY 50" in html

    def test_glossary_page_generated(self, generator, tmp_path):
        from src.glossary.manager import GlossaryManager
        data = [
            {"term": "P/E Ratio", "slug": "p-e-ratio", "definition": "Price-to-Earnings.", "category": "valuation", "added_date": "2026-09-01"},
            {"term": "Bull Market", "slug": "bull-market", "definition": "Rising trend.", "category": "basics", "added_date": "2026-09-01"},
        ]
        gf = tmp_path / "glossary.json"
        gf.write_text(json.dumps(data), encoding="utf-8")
        gm = GlossaryManager(gf)
        gm.load()

        path = generator.generate_glossary(gm)
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "P/E Ratio" in html
        assert "Bull Market" in html
        assert 'id="p-e-ratio"' in html

    def test_glossary_links_injected(self, generator, sample_report, india_data, intl_data, sample_date):
        from src.glossary.models import GlossaryEntry
        entries = [
            GlossaryEntry(
                term="Banking", slug="banking",
                definition="Related to banks and financial institutions.",
                category="basics", added_date="2026-09-07",
            )
        ]
        path = generator.generate_daily(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            glossary_entries=entries,
            report_date=sample_date,
        )
        html = path.read_text(encoding="utf-8")
        assert 'href="glossary.html#banking"' in html
