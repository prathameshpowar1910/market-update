"""
Logging configuration for the market digest pipeline.
Produces structured, coloured console output suitable for GitHub Actions logs.
"""

from __future__ import annotations

import logging
import sys


# ── ANSI colour codes (GitHub Actions supports ANSI) ─────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"

COLOURS = {
    logging.DEBUG:    "\033[36m",   # cyan
    logging.INFO:     "\033[32m",   # green
    logging.WARNING:  "\033[33m",   # yellow
    logging.ERROR:    "\033[31m",   # red
    logging.CRITICAL: "\033[35m",   # magenta
}


class _ColouredFormatter(logging.Formatter):
    """Formatter that adds ANSI colour to the levelname."""

    def format(self, record: logging.LogRecord) -> str:
        record.colour = COLOURS.get(record.levelno, "")
        record.reset = RESET
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  Call once per module:

        log = get_logger(__name__)
    """
    return logging.getLogger(name)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger.  Call once from main.py before anything else.

    Args:
        level: Log level string — 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _ColouredFormatter(
            fmt="%(asctime)s  %(colour)s%(levelname)-8s%(reset)s  %(name)-30s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="%",
        )
    )

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)
