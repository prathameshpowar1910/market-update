"""Tests for email generation."""

from datetime import date
from pathlib import Path

import pytest
from src.generator.email import EmailGenerator, _DISCLAIMER


class TestEmailGenerator:
    @pytest.fixture
    def generator(self):
        return EmailGenerator(
            resend_api_key="test-key-not-real",
            from_name="Test Digest",
            from_address="test@example.com",
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
        from src.market.models import InternationalMarketData
        return InternationalMarketData(date="2026-09-07")

    def test_email_html_generated(self, generator, sample_report, india_data, intl_data, sample_date):
        html = generator.render_email(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
        )
        assert isinstance(html, str)
        assert len(html) > 100

    def test_disclaimer_present(self, generator, sample_report, india_data, intl_data, sample_date):
        html = generator.render_email(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
        )
        # At least the word "financial advice" should appear
        assert "financial advice" in html.lower()

    def test_date_display_present(self, generator, sample_report, india_data, intl_data, sample_date):
        html = generator.render_email(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
        )
        # "September" should appear (from the date display)
        assert "September" in html

    def test_sentiment_badge_present(self, generator, sample_report, india_data, intl_data, sample_date):
        html = generator.render_email(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
        )
        assert "Bullish" in html

    def test_tldr_present(self, generator, sample_report, india_data, intl_data, sample_date):
        html = generator.render_email(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
        )
        assert sample_report.tldr[0] in html

    def test_sector_watch_present(self, generator, sample_report, india_data, intl_data, sample_date):
        html = generator.render_email(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
        )
        assert "Sector Watch" in html
        assert sample_report.sectors[0].name in html

    def test_correct_subject_format(self):
        from src.utils.dates import format_date_display
        d = date(2026, 9, 7)
        template = "📊 Market Digest — {date}"
        subject = template.format(date=format_date_display(d))
        assert "September" in subject
        assert "📊" in subject

    def test_dry_run_returns_true(self, generator, sample_report, india_data, intl_data, sample_date, monkeypatch):
        import os
        monkeypatch.setenv("TO_EMAIL", "test@example.com")
        result = generator.send(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
            dry_run=True,
        )
        assert result is True

    def test_no_recipients_returns_false(self, generator, sample_report, india_data, intl_data, sample_date, monkeypatch):
        monkeypatch.delenv("TO_EMAIL", raising=False)
        result = generator.send(
            report=sample_report,
            india=india_data,
            intl=intl_data,
            news=[],
            report_date=sample_date,
            to_emails=[],
        )
        assert result is False
