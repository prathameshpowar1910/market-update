"""
Market Digest — Main Pipeline Orchestrator

Usage:
    python src/main.py                  # full run
    python src/main.py --dry-run        # skip email and git push
    python src/main.py --skip-email     # generate site but no email
    python src/main.py --date 2026-09-07  # override date (for testing)
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from datetime import date
from pathlib import Path

# Add project root to sys.path so 'python src/main.py' works cleanly from root
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

# ── load .env before importing anything that reads env vars ──────────────────
load_dotenv()

from src.ai.gemini import GeminiClient
from src.generator.email import EmailGenerator
from src.generator.html import HTMLGenerator
from src.glossary.detector import detect_new_terms
from src.glossary.manager import GlossaryManager
from src.market.india import AlphaVantageIndiaClient
from src.market.international import AlphaVantageInternationalClient
from src.news.provider import NewsProvider
from src.utils.dates import format_date_iso, today_ist, parse_iso_date
from src.utils.logging import get_logger, setup_logging

log = get_logger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _collect_archive_dates(generated_dir: Path, limit: int = 30) -> list[str]:
    """
    Scan generated/ for YYYY-MM-DD.html files and return the most recent
    *limit* date strings, newest first (excluding today to avoid self-reference).
    """
    pattern = str(generated_dir / "????-??-??.html")
    files = sorted(glob.glob(pattern), reverse=True)
    dates: list[str] = []
    for f in files:
        stem = Path(f).stem
        try:
            parse_iso_date(stem)   # validate it really is a date
            dates.append(stem)
        except ValueError:
            pass
    return dates[:limit]


# ── pipeline ─────────────────────────────────────────────────────────────────

def run(report_date: date, dry_run: bool = False, skip_email: bool = False) -> bool:
    """
    Execute the full daily market digest pipeline.

    Returns True on success, False on failure.
    """
    date_str = format_date_iso(report_date)
    log.info("=" * 60)
    log.info("Starting daily market digest  [%s]", date_str)
    if dry_run:
        log.info("DRY RUN MODE — email will not be sent")
    log.info("=" * 60)

    generated_dir = Path("site/generated")

    # ── Phase 1: Market Data ─────────────────────────────────────────────────
    try:
        log.info("Phase 1: Fetching Indian market data")
        india_client = AlphaVantageIndiaClient()
        india = india_client.fetch_all()
        log.info("Phase 1: Indian market data OK")
    except Exception as exc:
        log.error("Phase 1: Indian market data FAILED: %s", exc)
        return False

    try:
        log.info("Phase 1: Fetching international market data")
        intl_client = AlphaVantageInternationalClient()
        intl = intl_client.fetch_all()
        log.info("Phase 1: International market data OK")
    except Exception as exc:
        log.error("Phase 1: International market data FAILED: %s", exc)
        return False

    # ── Phase 2: News ────────────────────────────────────────────────────────
    log.info("Phase 2: Fetching market news")
    try:
        news_provider = NewsProvider()
        news = news_provider.fetch(limit=15)
        log.info("Phase 2: News OK — %d articles", len(news))
    except Exception as exc:
        log.warning("Phase 2: News fetch failed (continuing without news): %s", exc)
        news = []

    # ── Phase 3: Gemini AI ───────────────────────────────────────────────────
    try:
        log.info("Phase 3: Sending data to Gemini")
        ai_client = GeminiClient()
        report = ai_client.generate_report(india, intl, news, report_date)
        log.info("Phase 3: Gemini report generated — sentiment: %s", report.overall_sentiment)
    except Exception as exc:
        log.error("Phase 3: Gemini generation FAILED: %s", exc)
        log.error("Aborting — will not publish incomplete report")
        return False

    # ── Phase 4: Glossary ────────────────────────────────────────────────────
    log.info("Phase 4: Processing glossary")
    glossary_path = Path("glossary.json")
    gm = GlossaryManager(glossary_path)
    try:
        gm.load()
        report_text = " ".join([
            report.india_summary,
            report.international_summary,
            " ".join(e.detail for e in report.key_events),
        ])
        new_terms = detect_new_terms(
            candidates=report.glossary_terms,
            manager=gm,
            report_text=report_text,
        )
        if new_terms:
            added = gm.add_entries(new_terms)
            gm.save()
            log.info("Phase 4: Added %d new glossary terms", len(added))
        else:
            log.info("Phase 4: No new glossary terms")
    except Exception as exc:
        log.warning("Phase 4: Glossary update failed (existing glossary preserved): %s", exc)

    # ── Phase 5: Generate HTML ───────────────────────────────────────────────
    log.info("Phase 5: Generating HTML")
    try:
        html_gen = HTMLGenerator()
        archive_dates = _collect_archive_dates(generated_dir)
        paths = html_gen.generate_all(
            report=report,
            india=india,
            intl=intl,
            news=news,
            manager=gm,
            archive_dates=archive_dates,
            report_date=report_date,
        )
        log.info("Phase 5: HTML generated — %s", ", ".join(str(p) for p in paths.values()))
    except Exception as exc:
        log.error("Phase 5: HTML generation FAILED: %s", exc)
        return False

    # ── Phase 6: Email ───────────────────────────────────────────────────────
    if skip_email or dry_run:
        log.info("Phase 6: Email skipped (%s)", "dry_run" if dry_run else "skip_email flag")
    else:
        log.info("Phase 6: Sending newsletter via Resend")
        try:
            email_gen = EmailGenerator()
            success = email_gen.send(
                report=report,
                india=india,
                intl=intl,
                news=news,
                report_date=report_date,
                dry_run=dry_run,
            )
            if success:
                log.info("Phase 6: Newsletter sent")
            else:
                log.warning("Phase 6: Newsletter send failed (site still deployed)")
        except Exception as exc:
            log.warning("Phase 6: Email error (site still deployed): %s", exc)

    log.info("=" * 60)
    log.info("Daily digest completed successfully  [%s]", date_str)
    log.info("=" * 60)
    return True


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Market Digest daily pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline but skip email sending",
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Generate site but do not send email",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override report date (YYYY-MM-DD). Defaults to today IST.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    report_date: date
    if args.date:
        try:
            report_date = parse_iso_date(args.date)
        except ValueError as exc:
            print(f"Invalid date format: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        report_date = today_ist()

    ok = run(
        report_date=report_date,
        dry_run=args.dry_run,
        skip_email=args.skip_email,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
