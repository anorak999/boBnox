#!/bin/bash
# Run boBnox with Vue.js frontend
# Starts the Python backend API server + Vite dev server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting boBnox v5.0.0..."
echo ""

# Start Python backend
echo "[1/2] Starting API server on :8420..."
python3 -m backend.server &
BACKEND_PID=$!
sleep 2

# Start Vue frontend dev server
echo "[2/2] Starting frontend dev server on :5173..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== boBnox is running ==="
echo "  Frontend: http://localhost:5173"
echo "  API:      http://localhost:8420/docs"
echo "  WebSocket: ws://localhost:8420/ws/events"
echo ""
echo "Press Ctrl+C to stop."

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait 2>/dev/null
    echo "Done."
}

trap cleanup EXIT INT TERM
wait
