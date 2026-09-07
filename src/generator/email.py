"""
Email generator + Resend integration.

Generates the email HTML from the same DailyReport used for the website
(Gemini is called only once), then sends via Resend with an idempotency key.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.ai.schemas import DailyReport
from src.market.models import IndiaMarketData, InternationalMarketData
from src.news.models import NewsItem
from src.utils.dates import format_date_display, format_date_iso, idempotency_key
from src.utils.logging import get_logger

log = get_logger(__name__)

_TEMPLATES_DIR = Path("site/templates")
_DISCLAIMER = (
    "This newsletter is for informational purposes only and does not constitute "
    "financial advice. Always do your own research before making investment decisions. "
    "Past market performance is not indicative of future results."
)


class EmailGenerator:
    """Renders the email HTML and sends it via Resend."""

    def __init__(
        self,
        resend_api_key: str | None = None,
        from_name: str = "Market Digest",
        from_address: str | None = None,
        templates_dir: Path = _TEMPLATES_DIR,
    ) -> None:
        resend.api_key = resend_api_key or os.environ["RESEND_API_KEY"]
        self._from_name = from_name
        self._from_address = from_address or os.getenv(
            "FROM_EMAIL", "digest@yourdomain.com"
        )
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html"]),
        )
        self._env.globals["format_date_display"] = format_date_display

    # ── rendering ────────────────────────────────────────────────────────────

    def render_email(
        self,
        report: DailyReport,
        india: IndiaMarketData,
        intl: InternationalMarketData,
        news: list[NewsItem],
        report_date: date,
    ) -> str:
        """Render the email HTML from the shared email.html template."""
        tmpl = self._env.get_template("email.html")
        return tmpl.render(
            report=report,
            india=india,
            intl=intl,
            news=news,
            report_date=report_date,
            date_display=format_date_display(report_date),
            disclaimer=_DISCLAIMER,
        )

    # ── sending ──────────────────────────────────────────────────────────────

    def send(
        self,
        report: DailyReport,
        india: IndiaMarketData,
        intl: InternationalMarketData,
        news: list[NewsItem],
        report_date: date,
        to_emails: list[str] | None = None,
        subject_template: str = "📊 Market Digest — {date}",
        dry_run: bool = False,
    ) -> bool:
        """
        Render and send the daily email.

        Args:
            report:           The validated DailyReport.
            india/intl/news:  Data contexts for the template.
            report_date:      Date this email covers.
            to_emails:        Recipient list. Falls back to TO_EMAIL env var.
            subject_template: Format string accepting {date}.
            dry_run:          If True, render but do not send.

        Returns:
            True on success, False on failure (does not raise).
        """
        recipients = to_emails or [
            e.strip()
            for e in os.getenv("TO_EMAIL", "").split(",")
            if e.strip()
        ]
        if not recipients:
            log.warning("No recipients configured — skipping email")
            return False

        html = self.render_email(report, india, intl, news, report_date)
        date_display = format_date_display(report_date)
        subject = subject_template.format(date=date_display)
        idem_key = idempotency_key("daily-digest", report_date)

        log.info(
            "Email: subject=%r, recipients=%d, idempotency_key=%r",
            subject, len(recipients), idem_key,
        )

        if dry_run:
            log.info("DRY RUN — email not sent")
            return True

        try:
            resp = resend.Emails.send({
                "from": f"{self._from_name} <{self._from_address}>",
                "to": recipients,
                "subject": subject,
                "html": html,
                "headers": {"X-Idempotency-Key": idem_key},
            })
            log.info("Email sent: id=%s", getattr(resp, "id", resp))
            return True
        except Exception as exc:
            log.error("Email send failed: %s", exc)
            return False
