#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# NZ Gym Guide — Daily Post Generator
# Runs every day via cron to generate 3 posts:
#   1. Exercise tip    2. Gym deal    3. Health information
#
# Cron entry (6am NZST = 6pm UTC prev day):
#   0 18 * * * /home/ben/nz-gym-guide/scripts/run_daily.sh >> /home/ben/nz-gym-guide/logs/daily.log 2>&1
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
LOGDIR="$ROOT/logs"
LOGFILE="$LOGDIR/daily.log"
VENV_PYTHON="$ROOT/venv/bin/python"

mkdir -p "$LOGDIR"

echo ""
echo "════════════════════════════════════════════"
echo "  NZ Gym Guide Daily Post Generator"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "════════════════════════════════════════════"

# Check venv exists
if [ ! -f "$VENV_PYTHON" ]; then
  echo "❌ ERROR: venv not found at $VENV_PYTHON"
  echo "   Run: cd $ROOT && python3 -m venv venv && venv/bin/pip install groq jinja2"
  exit 1
fi

# Check GROQ_API_KEY
if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | grep GROQ_API_KEY | xargs)
fi

if [ -z "${GROQ_API_KEY:-}" ]; then
  echo "❌ ERROR: GROQ_API_KEY not set — add it to $ROOT/.env"
  exit 1
fi

# Run generator
echo ""
echo "▶ Running auto_generate.py..."
cd "$ROOT"
"$VENV_PYTHON" scripts/auto_generate.py

echo ""
echo "✅ Daily post generation complete at $(date '+%H:%M:%S')"
echo ""
