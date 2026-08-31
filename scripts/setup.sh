#!/usr/bin/env sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up Evidence Alpha..."

cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "Created backend/.env"
  echo "Open backend/.env and paste your API key before running the app."
fi

cd "$ROOT_DIR/frontend"
npm install

echo ""
echo "Setup complete."
echo "Next:"
echo "1. Edit backend/.env and add your API key."
echo "2. Run ./scripts/run_backend.sh"
echo "3. In another terminal, run ./scripts/run_frontend.sh"
