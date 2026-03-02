#!/usr/bin/env bash
# dev.sh — Start backend + frontend together.
# Ctrl+C stops both.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Kill entire process group on exit (covers Ctrl+C and unexpected exits)
cleanup() {
    echo ""
    echo "Stopping all processes..."
    kill 0
}
trap cleanup EXIT INT TERM

# Backend
echo "[backend]  starting on http://localhost:8000"
cd "$ROOT"
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 &

# Frontend
echo "[frontend] starting on http://localhost:5173"
cd "$ROOT/frontend"
pnpm dev &

echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop all"
echo ""

wait
