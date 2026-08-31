#!/usr/bin/env sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/backend"

if [ ! -f ".env" ]; then
  echo "Missing backend/.env. Run ./scripts/setup.sh first."
  exit 1
fi

. .venv/bin/activate
uvicorn app.main:app --reload --port 8000
