@echo off
echo Starting VUES Orchestrator...
cd /d "%~dp0.."
uv run python tools/orchestrator.py
pause
