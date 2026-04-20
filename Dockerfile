# =============================================================================
# VUES — Dockerfile
#
# Stages:
#   base  — system deps + Python packages (cached; busts only on pyproject.toml)
#   dev   — hot-reload via watchmedo (used by Docker Compose Watch)
#
# Hot-reload flow:
#   1. You save a .py file on your host
#   2. Compose Watch syncs it into /app/src inside the container
#   3. watchmedo detects the change and kills + restarts 'python main.py'
#   4. New process picks up your changes — no rebuild needed
# =============================================================================

# ── Stage 1: base ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System dependencies
#   gcc / g++       → build C-extension wheels
#   unixodbc-dev    → required by pyodbc at build time
#   curl / gnupg2   → needed to add Microsoft's APT repo
#   msodbcsql18     → Microsoft ODBC Driver 18 for SQL Server (runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ curl gnupg2 unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy ONLY the dep manifest first — Docker caches this layer until
# pyproject.toml changes, so re-installs only happen when deps actually change.
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . --no-build-isolation

# ── Stage 2: dev (hot-reload) ─────────────────────────────────────────────────
FROM base AS dev

# watchdog ships the 'watchmedo' CLI we use for hot-reload.
# Kept separate from base so production images never carry dev tooling.
RUN pip install --no-cache-dir "watchdog[watchmedo]"

# Copy the full project.
# Compose Watch will sync individual file changes on top of this snapshot,
# so this layer is only the baseline — deltas happen at runtime, not build time.
COPY . .

# Dashboard server port
EXPOSE 8765

# watchmedo auto-restart:
#   --directory  : watch /app/src for any .py changes (synced by Compose Watch)
#   --pattern    : only trigger on Python files
#   --recursive  : include all sub-packages
#   --           : separator before the command to run
#   python main.py : your actual app
#
# When a .py file changes → watchmedo sends SIGTERM and re-executes python main.py
CMD ["watchmedo", "auto-restart", \
     "--directory=/app/src", \
     "--pattern=*.py", \
     "--recursive", \
     "--", \
     "python", "main.py"]
