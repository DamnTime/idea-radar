# IdeaRadar

> Daily AI-powered startup idea aggregator. Fetches from Reddit, Zhihu, and RSS — deduplicates, filters spam, scores with LLM, and pushes the best ideas via email.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Pipeline

```
Scrape (Reddit + Zhihu + RSS)
    ↓
Semantic Dedup (SimHash, threshold 0.85)
    ↓
Spam Filter (keywords + content features)
    ↓
LLM Feasibility Score (0-10, 5 dimensions weighted)
    ↓
Sort → Top N → Email Push (HTML)
```

## Data Sources

| Source | Method | Auth |
|---|---|---|
| Reddit | `old.reddit.com` JSON API | None |
| Zhihu (知乎) | Hot list + search API | None |
| RSS | Any Atom/RSS feed | None |

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI-compatible API Key (works with DeepSeek, GLM-4, etc.)
- SMTP email account

### Setup

```bash
# 1. Enter project directory
cd idea-radar

# 2. Install dependencies
pip install -r requirements.txt
# or with uv: uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your keys:
#   OPENAI_API_KEY=sk-xxx
#   SMTP_HOST=smtp.gmail.com
#   SMTP_PORT=587
#   SMTP_USER=your@gmail.com
#   SMTP_PASS=your-app-password
#   EMAIL_FROM=your@gmail.com
#   EMAIL_RECIPIENTS=user@example.com

# 4. Run
python -m src.main --hours 24 --top-n 5
```

### Docker

```bash
docker compose up --build
```

### GitHub Actions (Scheduled)

Fork this repo, add the environment variables in Settings → Secrets. The `daily-push.yml` workflow runs at UTC 00:00 / 08:00 / 16:00 automatically.

## Project Structure

```
idea-radar/
├── src/
│   ├── main.py                   # CLI entry point
│   ├── orchestrator.py           # Pipeline orchestrator
│   ├── models.py                 # Data models
│   ├── scrapers/                 # Data source scrapers
│   │   ├── reddit.py
│   │   ├── rss.py
│   │   └── zhihu.py
│   ├── processors/               # Data processors
│   │   ├── deduplicator.py       # SimHash dedup
│   │   ├── spam_filter.py        # Spam detection
│   │   └── scorer.py             # LLM scoring
│   └── notifiers/
│       └── email_notifier.py     # SMTP email
├── data/config.json              # User config
├── config/spam_keywords.txt      # Spam keyword list
├── prompts/scorer.txt            # LLM prompt template
├── templates/email.html          # Email HTML template
├── Dockerfile / docker-compose.yml
└── docs/                         # Design documents
    ├── 01-requirements.md
    ├── 02-technical-plan.md
    └── 03-skill.md
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Scraping | httpx (async) |
| Dedup | SimHash + jieba |
| Scoring | OpenAI-compatible API |
| Push | SMTP (HTML email) |
| Deploy | Docker / GitHub Actions |

## License

MIT
