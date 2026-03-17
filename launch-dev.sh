#!/usr/bin/env bash
# launch-dev.sh — Start backend + frontend and open Chrome.
# Designed to be called from the .app bundle on Desktop.

set -euo pipefail

ROOT="/Users/byunjungwon/Dev/my-project-01/my_chart"
LOG="$ROOT/.dev-server.log"

cd "$ROOT"

# Stop any previously running dev servers on ports 8000 and 5173
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5173 2>/dev/null | xargs kill -9 2>/dev/null || true

# Start backend
echo "[$(date)] Starting backend..." >> "$LOG"
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 >> "$LOG" 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready (max 30 seconds)
echo "[$(date)] Waiting for backend..." >> "$LOG"
for i in $(seq 1 60); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "[$(date)] Backend ready." >> "$LOG"
        break
    fi
    sleep 0.5
done

# Start frontend
echo "[$(date)] Starting frontend..." >> "$LOG"
cd "$ROOT/frontend"
pnpm dev >> "$LOG" 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready (max 15 seconds)
for i in $(seq 1 30); do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Open Chrome
open -a "Google Chrome" "http://localhost:5173"

# Show notification
osascript -e 'display notification "Backend :8000 / Frontend :5173" with title "My Chart Dev Server" subtitle "Servers started successfully"'

# Cleanup: kill backend when this script exits (frontend dies or Ctrl+C)
cleanup() {
    echo "[$(date)] Stopping all servers..." >> "$LOG"
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    lsof -ti:8000 2>/dev/null | xargs kill 2>/dev/null || true
    lsof -ti:5173 2>/dev/null | xargs kill 2>/dev/null || true
    osascript -e 'display notification "All servers stopped" with title "My Chart Dev Server"'
}
trap cleanup EXIT INT TERM

# Monitor frontend — if it dies, exit (triggers cleanup)
wait "$FRONTEND_PID" 2>/dev/null
cleanup
