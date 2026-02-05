#!/usr/bin/env bash
set -euo pipefail

export KB_STORAGE_DIR="$(pwd)/storage"
export PYTHONPATH="$(pwd)/backend"

# Activate venv if exists (for local dev)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start uvicorn in background
# We bind to 127.0.0.1 for CI/local testing
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!

echo "Starting server with PID: $SERVER_PID"

# Wait for healthy
echo "Waiting for health check..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health | grep -q "ok"; then
    echo "Server is ready!"
    # Write PID to file for cleanup
    echo $SERVER_PID > /tmp/rag_server.pid
    exit 0
  fi
  sleep 1
  echo -n "."
done

echo ""
echo "Server failed to start in 30s"
kill $SERVER_PID || true
exit 1
