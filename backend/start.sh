#!/usr/bin/env bash
# start.sh — Render start command for the FastAPI backend
# Render sets the PORT env var automatically; default to 8000 for local use.

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2 --log-level info
