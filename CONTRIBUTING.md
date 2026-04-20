# Contributing to VUES (SiteOwlQA)

Thank you for your interest in contributing! This document provides guidelines for contributing to the VUES - Validation Utility Engine Survey project.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd SiteOwlQA_App

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run smoke test
python scripts/smoke_test.py

# Run the application
python main.py
```

## 📋 Development Workflow

### Branch Naming

- `feature/<description>` — New features
- `bugfix/<description>` — Bug fixes
- `refactor/<description>` — Code refactoring
- `docs/<description>` — Documentation updates

### Commit Messages

Follow conventional commits:

```
type: short description

Longer description if needed.

- Bullet points for details
- Keep lines under 72 chars
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

### Code Style

- **Python**: Follow PEP 8, use type hints
- **Max file length**: 600 lines (split on cohesion, not line count)
- **Principles**: DRY, YAGNI, SOLID, Zen of Python
- **Config**: All `os.getenv()` calls must be in `config.py`
- **Types**: All domain types live in `models.py`

### Before Submitting

1. Run smoke test: `python scripts/smoke_test.py`
2. Test your changes manually
3. Update documentation if needed
4. Commit with clear message

## 🏗️ Architecture Overview

```
src/siteowlqa/
├── main.py              # Entry point, polling loop
├── config.py            # All configuration (env vars, user config)
├── models.py            # Domain types (AirtableRecord, etc.)
├── airtable_client.py   # Airtable REST API
├── bigquery_provider.py # BigQuery reference data
├── python_grader.py     # Grading engine
├── queue_worker.py      # Parallel submission processing
├── metrics_worker.py    # Dashboard/CSV generation
└── ...
```

### Key Principles

1. **Single instance**: Only one pipeline should poll a given Airtable base
2. **Idempotent processing**: Re-processing a record produces the same result
3. **Crash recovery**: Stuck records are auto-recovered on startup
4. **Append-only archive**: Never delete execution records or lessons

## 🔒 Security

### Never Commit

- `.env` files with real credentials
- `~/.siteowlqa/config.json`
- GCP service account JSON files
- Any file containing tokens, passwords, or PII

### Sensitive Data

- Store tokens in `~/.siteowlqa/config.json` (not in repo)
- Use `.env` only for non-sensitive configuration
- Never log sensitive values

## 🧪 Testing

```bash
# Smoke test (verifies all dependencies)
python scripts/smoke_test.py

# Manual grading test
python scripts/test_bq_grade.py
```

## 📚 Documentation

- **README.md** — Project overview and quick start
- **docs/configuration.md** — Detailed configuration guide
- **docs/clone-and-run.md** — Onboarding guide
- **CLAUDE.md** — AI assistant context
- **MEMORY.md** — Project decisions and history

## 🐛 Reporting Issues

When reporting issues, include:

1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Relevant log output (sanitize sensitive data)
5. Environment (Python version, OS)

## 📞 Contact

- **Teams Channel**: [VUES Support](https://teams.microsoft.com/...)
- **Slack**: #vues-support
- **Email**: vues-support@walmart.com

## 📜 License

See [LICENSE](LICENSE) file.
