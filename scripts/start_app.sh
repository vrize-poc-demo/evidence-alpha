#!/usr/bin/env sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

cleanup() {
  echo ""
  echo "Stopping Evidence Alpha..."
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup INT TERM EXIT

echo "Starting Evidence Alpha..."

cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
  echo "Creating backend virtual environment..."
  python3 -m venv .venv
fi

. .venv/bin/activate
if ! python -c "import fastapi, openai, bs4" >/dev/null 2>&1; then
  echo "Installing backend dependencies..."
  pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created backend/.env. Add OPENAI_API_KEY for OpenAI answers."
fi

uvicorn app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID="$!"

cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" &
FRONTEND_PID="$!"

echo ""
echo "Evidence Alpha is starting."
echo "Frontend app: http://127.0.0.1:$FRONTEND_PORT"
echo "Backend API:  http://127.0.0.1:$BACKEND_PORT/api"
echo "API docs:     http://127.0.0.1:$BACKEND_PORT/docs"
echo ""
echo "Note: http://127.0.0.1:$BACKEND_PORT also serves the frontend for Render-style single-service deployment."
echo ""
echo "Keep this terminal open. Press Ctrl-C to stop both servers."

wait
