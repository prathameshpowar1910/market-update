"""
Static HTML generator using Jinja2.

Generates:
  • site/generated/index.html     — homepage / archive
  • site/generated/YYYY-MM-DD.html — daily report page
  • site/generated/glossary.html   — A-Z glossary page
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.ai.schemas import DailyReport
from src.glossary.linker import link_glossary_terms
from src.glossary.manager import GlossaryManager
from src.glossary.models import GlossaryEntry
from src.market.models import IndiaMarketData, InternationalMarketData
from src.news.models import NewsItem
from src.utils.dates import format_date_display, format_date_iso
from src.utils.logging import get_logger

log = get_logger(__name__)

_TEMPLATES_DIR = Path("site/templates")
_STATIC_DIR = Path("site/static")
_OUTPUT_DIR = Path("site/generated")


class HTMLGenerator:
    """Generates all static HTML pages from a DailyReport."""

    def __init__(
        self,
        templates_dir: Path = _TEMPLATES_DIR,
        output_dir: Path = _OUTPUT_DIR,
        static_dir: Path = _STATIC_DIR,
    ) -> None:
        self._output_dir = output_dir
        self._static_dir = static_dir
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._env.globals["format_date_display"] = format_date_display

    def _render(self, template_name: str, context: dict) -> str:
        """Render a Jinja2 template with the given context."""
        tmpl = self._env.get_template(template_name)
        return tmpl.render(**context)

    def _write(self, filename: str, content: str) -> Path:
        """Write content to the output directory."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        out = self._output_dir / filename
        out.write_text(content, encoding="utf-8")
        log.info("Generated: %s", out)
        return out

    def _copy_static(self) -> None:
        """Copy CSS/JS static assets into the generated directory."""
        dest = self._output_dir / "static"
        if self._static_dir.exists():
            shutil.copytree(str(self._static_dir), str(dest), dirs_exist_ok=True)
            log.info("Static assets copied to %s", dest)

    # ── public API ───────────────────────────────────────────────────────────

    def generate_daily(
        self,
        report: DailyReport,
        india: IndiaMarketData,
        intl: InternationalMarketData,
        news: list[NewsItem],
        glossary_entries: list[GlossaryEntry],
        report_date: date,
    ) -> Path:
        """Generate the daily report page and return its path."""
        date_str = format_date_iso(report_date)
        context = {
            "report": report,
            "india": india,
            "intl": intl,
            "news": news,
            "glossary_entries": glossary_entries,
            "report_date": report_date,
            "date_str": date_str,
            "date_display": format_date_display(report_date),
        }
        html = self._render("daily.html", context)
        # Post-process: wrap glossary terms with links
        html = link_glossary_terms(html, glossary_entries)
        return self._write(f"{date_str}.html", html)

    def generate_index(
        self,
        latest_report: DailyReport,
        archive_dates: list[str],
        report_date: date,
    ) -> Path:
        """Generate the homepage with latest report summary + archive."""
        context = {
            "report": latest_report,
            "archive_dates": archive_dates,
            "report_date": report_date,
            "date_str": format_date_iso(report_date),
            "date_display": format_date_display(report_date),
        }
        html = self._render("index.html", context)
        return self._write("index.html", html)

    def generate_glossary(self, manager: GlossaryManager) -> Path:
        """Generate the A-Z glossary page."""
        sorted_entries = manager.sorted_entries()

        # Group by first letter
        grouped: dict[str, list[GlossaryEntry]] = {}
        for entry in sorted_entries:
            first = entry.term[0].upper()
            grouped.setdefault(first, []).append(entry)

        context = {
            "grouped": grouped,
            "total": len(sorted_entries),
            "letters": sorted(grouped.keys()),
            "categories": sorted({entry.category for entry in sorted_entries}),
        }
        html = self._render("glossary.html", context)
        return self._write("glossary.html", html)

    def generate_all(
        self,
        report: DailyReport,
        india: IndiaMarketData,
        intl: InternationalMarketData,
        news: list[NewsItem],
        manager: GlossaryManager,
        archive_dates: list[str],
        report_date: date,
    ) -> dict[str, Path]:
        """Generate all pages and copy static assets. Returns paths dict."""
        self._copy_static()
        entries = manager.all_entries()
        paths = {
            "daily":    self.generate_daily(report, india, intl, news, entries, report_date),
            "index":    self.generate_index(report, archive_dates, report_date),
            "glossary": self.generate_glossary(manager),
        }
        log.info("HTML generation complete: %d pages", len(paths))
        return paths
