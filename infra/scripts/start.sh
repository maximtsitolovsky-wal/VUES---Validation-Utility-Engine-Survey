#!/bin/bash
# SiteOwlQA container entrypoint
set -euo pipefail

echo "[start] SiteOwlQA pipeline starting in container..."
echo "[start] Python: $(python --version)"
echo "[start] Working dir: $(pwd)"

# Ensure volume-mounted dirs exist (fresh volumes are empty)
mkdir -p /app/output /app/logs /app/temp /app/archive /app/corrections

# Validate required env vars before starting
: "${AIRTABLE_TOKEN:?AIRTABLE_TOKEN is required}"
: "${AIRTABLE_BASE_ID:?AIRTABLE_BASE_ID is required}"
: "${SQL_SERVER:?SQL_SERVER is required}"
: "${SQL_DATABASE:?SQL_DATABASE is required}"

echo "[start] Config validated. Launching pipeline..."
exec python -u main.py
