# 📊 Market Digest

> AI-powered daily Indian & global market digest — generated automatically by GitHub Actions, deployed to GitHub Pages, delivered via Resend.

## Architecture

```
GitHub Actions (daily cron)
        │
        ▼
Python Pipeline
        │
   ┌────┴─────┐
   ▼          ▼
Alpha Vantage  Tiingo News
   │          │
   └────┬─────┘
        ▼
  Normalize & Validate
        │
        ▼
  Gemini AI (structured JSON)
        │
   ┌────┴──────────────┐
   ▼                   ▼
DailyReport        GlossaryCandidate list
   │                   │
   │             Validate & dedupe
   │                   │
   │             glossary.json
   │
   ├── Jinja2 → site/generated/*.html
   └── Email HTML → Resend
```

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/yourusername/market-update
cd market-update
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys:
- `GEMINI_API_KEY` — [Google AI Studio](https://aistudio.google.com/)
- `ALPHA_VANTAGE_API_KEY` — [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
- `TIINGO_API_KEY` — [Tiingo](https://api.tiingo.com/)
- `RESEND_API_KEY` — [Resend](https://resend.com/)
- `TO_EMAIL` — recipient email address
- `FROM_EMAIL` — verified sender address in Resend

### 3. Run locally

```bash
# Full run (generates site, sends email)
python src/main.py

# Dry run (generates site, skips email)
python src/main.py --dry-run

# Specific date
python src/main.py --date 2026-09-07 --dry-run

# Debug logging
python src/main.py --dry-run --log-level DEBUG
```

### 4. Run tests

```bash
pytest tests/ -v
ruff check src/ tests/
```

## GitHub Setup

### Secrets

Set these in your repository **Settings → Secrets → Actions**:

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key |
| `TIINGO_API_KEY` | Tiingo API key |
| `RESEND_API_KEY` | Resend API key |
| `TO_EMAIL` | Newsletter recipient(s), comma-separated |
| `FROM_EMAIL` | Verified sender address in Resend |

### GitHub Pages

1. Go to **Settings → Pages**
2. Set **Source** to **Deploy from a branch**
3. Set **Branch** to `gh-pages`, folder `/` (root)
4. Save — your site will be at `https://yourusername.github.io/market-update/`

### Manual trigger

Go to **Actions → Daily Market Digest → Run workflow** to test on demand.

## Project Structure

```
market-update/
├── .github/workflows/
│   ├── daily.yml          # Scheduled pipeline + deploy
│   └── tests.yml          # Lint + test on push
├── config/
│   └── config.yaml        # Central configuration
├── site/
│   ├── templates/         # Jinja2 HTML templates
│   └── static/            # CSS + JS assets
├── src/
│   ├── main.py            # Pipeline orchestrator
│   ├── ai/                # Gemini client + schemas + prompts
│   ├── market/            # Alpha Vantage clients
│   ├── news/              # Tiingo + RSS clients
│   ├── glossary/          # Auto-glossary engine
│   ├── generator/         # HTML + email generators
│   └── utils/             # Dates, logging, validation
├── tests/                 # pytest test suite
├── glossary.json          # Auto-growing financial glossary
├── requirements.txt
└── .env.example
```

## Glossary

The `glossary.json` file grows automatically:

1. Gemini identifies financial terms it uses in each report
2. The glossary detector filters out existing terms
3. New terms are validated and appended
4. Every term is hyperlinked inline in the HTML reports
5. The `glossary.html` page shows all terms A-Z with search

## Schedule

The pipeline runs **weekdays at 18:30 UTC (midnight IST)**, covering the India market close session.

## License

MIT
