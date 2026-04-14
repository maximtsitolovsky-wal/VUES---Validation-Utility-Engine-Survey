# 🏗️ SiteOwlQA — System & Build Infrastructure

> Auto-generated: 2026-04-14 | Code Puppy `code-puppy-e05be7`

---

## 🖥️ Host Machine

| Property         | Value                                      |
|------------------|--------------------------------------------|
| OS               | Microsoft Windows 11 Enterprise            |
| OS Build         | 10.0.26100 (Build 26100)                   |
| Architecture     | x64-based PC                               |
| RAM              | ~32 GB                                     |
| BIOS             | Lenovo N48ET31W (1.18), Oct 29 2025        |
| Working Dir      | `C:\SiteOwlQA_App`                         |

---

## ⚙️ Runtime Toolchain

| Tool       | Version         | Notes                                      |
|------------|-----------------|--------------------------------------------|
| Python     | 3.14.0          | System Python; project requires `>=3.11`   |
| pip        | 26.0.1          | System pip                                 |
| uv         | 0.8.0           | Preferred package manager                  |
| Node.js    | v24.11.1        | Used for front-end tooling / UI            |
| npm        | 11.6.2          | Node package manager                       |
| Git        | 2.47.1.windows.2| Source control                             |
| Docker     | ❌ Not installed | Not in use                                 |

---

## 📦 Python Project Metadata

| Property         | Value                                      |
|------------------|--------------------------------------------|
| Package Name     | `siteowlqa`                                |
| Version          | `0.1.0`                                    |
| Description      | SiteOwlQA automation pipeline              |
| Python Req.      | `>=3.11`                                   |
| Build System     | `setuptools >= 69` + `wheel`               |
| Build Backend    | `setuptools.build_meta`                    |
| Source Layout    | `src/` layout (`src/siteowlqa/`)           |
| Entry Point      | `main.py` → `siteowlqa.main.run_forever()` |
| Compiled Binary  | `SiteOwlQA.exe` (17.4 MB)                  |

---

## 📚 Python Dependencies (`pyproject.toml` / `requirements.txt`)

| Package           | Version Pin  | Purpose                        |
|-------------------|--------------|--------------------------------|
| `pyairtable`      | `>=2.3.3`    | Airtable API integration       |
| `pandas`          | `>=2.2.0`    | Data processing & transforms   |
| `openpyxl`        | `>=3.1.2`    | XLSX read/write                |
| `pyodbc`          | `>=5.1.0`    | SQL Server connectivity        |
| `requests`        | `>=2.31.0`   | HTTP client                    |
| `httpx`           | `>=0.27.0`   | Async HTTP client              |
| `pydantic-ai`     | `>=0.0.24`   | LLM / AI integration           |
| `openai`          | `>=1.51.0`   | OpenAI API client              |
| `python-dotenv`   | `>=1.0.1`    | `.env` config loading          |

**Stdlib used (no install):** `smtplib`, `csv`, `json`, `logging`, `pathlib`, `dataclasses`, `typing`, `shutil`

---

## 🗂️ Project Directory Structure

```
C:\SiteOwlQA_App\
├── main.py                   # Root entry point (sys.path shim → src/)
├── SiteOwlQA.exe             # Compiled Windows binary (17.4 MB)
├── pyproject.toml            # Build config & dependency declarations
├── requirements.txt          # Pip-compat dependency list
├── .env                      # Secrets/config (gitignored)
├── .env.example              # Documented env template (committed)
├── .gitignore                # Excludes: .env, logs/, output/, temp/, DBs
├── CLAUDE.md                 # AI agent instructions
├── MEMORY.md                 # Persistent session memory
├── README.md                 # Project documentation (24 KB)
├── development.md            # Developer notes
├── orchestration_map.html    # Live 59-node architecture map (47 KB)
│
├── src/siteowlqa/            # Main Python package (src layout)
├── tests/                    # Test suite (pytest)
├── docs/                     # Extended documentation
├── scripts/                  # Utility & automation scripts
├── ui/                       # Front-end assets
├── ops/                      # Ops / deployment scripts
│   └── windows/
│       └── run_siteowlqa.bat # Task Scheduler launch script
├── tools/                    # Developer tooling
├── prompts/                  # LLM prompt templates
├── skills/                   # Agent skill definitions
├── sql_migrations/           # DB schema migrations
├── legacy_db_tools/          # Archived DB utilities
│
├── logs/                     # Runtime logs (gitignored)
├── output/                   # Pipeline output files (gitignored)
├── temp/                     # Scratch space (gitignored)
├── archive/                  # Old artifacts (gitignored)
├── served_dashboard/         # Dashboard build output (gitignored)
└── share/                    # Shared exports (gitignored)
```

---

## 🚀 Deployment — Windows Task Scheduler

The pipeline runs as a **persistent Windows Scheduled Task**, auto-starting at user logon.

| Property             | Value                                                |
|----------------------|------------------------------------------------------|
| Task Name            | `SiteOwlQA Pipeline`                                 |
| Run As               | `HOMEOFFICE\vn59j7j`                                 |
| Trigger              | At logon + **90s delay** (OneDrive sync time)        |
| Executable           | `C:\Windows\System32\cmd.exe /c run_siteowlqa.bat`   |
| Working Dir          | `C:\SiteOwlQA_App`                                   |
| Multiple Instances   | `IgnoreNew` (no double-runs)                         |
| Restart on Fail      | Up to **10 times**, every **1 minute**               |
| Execution Time Limit | **None** (runs indefinitely)                         |
| Battery / Idle       | Runs regardless                                      |
| Privilege Level      | **Highest** (admin)                                  |

**Setup:** Double-click `INSTALL_TASK.bat` → UAC prompt → auto-calls `register_task.ps1`

---

## 🌿 Git & Source Control

| Property         | Value                                                                      |
|------------------|----------------------------------------------------------------------------|
| Active Branch    | `main`                                                                     |
| Remote: `origin` | `https://github.com/maximtsitolovsky-wal/VUES---Validation-Utility-Engine-Survey.git` |
| Remote: `walmart-origin` | `https://gecgithub01.walmart.com/vn59j7j/siteowlqa_app`         |

### Recent Commits (last 10)

| Hash      | Message                                                                            |
|-----------|------------------------------------------------------------------------------------|
| `dfdaefc` | feat: remove SMTP/emailer — Airtable automation owns all vendor email              |
| `83174f1` | fix: architecture tab link, config hot-reload, arch map auto-publish               |
| `f298c82` | feat: add Desktop Launcher node to architecture map (root realm)                   |
| `b5cb980` | chore: remove stale root-level audit/check scripts                                 |
| `3b84ea0` | fix: simplify start_pipeline.bat - reads port file, opens browser, no frills      |
| `ee350c4` | docs: session log — deep arch map 59 nodes, dashboard sync fix, Scout confirmed    |
| `b0e15da` | feat: deep architecture map — 59 real nodes across 8 drill-down realms             |
| `3909679` | fix: skip self-copy in _copy_raw_file when source is already in RAW dir            |
| `cb2dba0` | fix: dynamic port selection so shortcut works on any machine                       |
| `0ec9c62` | fix: restore Name to correctable fields with similarity guard                      |

---

## 🧪 Testing

| Property    | Value                              |
|-------------|------------------------------------|
| Framework   | `pytest`                           |
| Test Dir    | `tests/`                           |
| Python Path | `src/` (configured in `pyproject.toml`) |

---

## 🔐 Secrets & Configuration

| File           | Status              | Notes                                       |
|----------------|---------------------|---------------------------------------------|
| `.env`         | ✅ Gitignored       | Runtime secrets (API keys, DB strings)      |
| `.env.example` | ✅ Committed        | Documented template — safe to share         |

---

## 🚫 Gitignored Patterns (notable)

```
.env / .env.*          # Secrets
__pycache__/ *.pyc     # Python bytecode
.venv/ venv/           # Virtual environments
logs/ output/ temp/    # Runtime artifacts
archive/ share/        # Export/archive dirs
*.sqlite *.db          # SQLite databases
*.csv *.xlsx *.xls     # Data files (PII risk)
*.log                  # Log files
build/ dist/ *.egg-info # Build artifacts
```
