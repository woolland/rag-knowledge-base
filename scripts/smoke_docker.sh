#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8000"

echo "[1/2] health..."
curl -s "$BASE/health" | python -m json.tool

echo "[2/2] ask-kb..."
curl -s -X POST "$BASE/ask-kb" \
  -H "Content-Type: application/json" \
  -d '{"kb_id":"demo","query":"What is the plan for?"}' \
| python -m json.tool
