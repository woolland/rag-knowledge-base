#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8000"

echo "== health =="
# Wait for server to be ready
retries=0
while ! curl -s "$BASE/health" | grep -q "ok"; do
  sleep 1
  retries=$((retries+1))
  if [ $retries -gt 30 ]; then
    echo "Server failed to start in 30s"
    exit 1
  fi
  echo -n "."
done
echo ""
curl -s "$BASE/health" | python -m json.tool

echo "== ask-kb =="
RESP="$(curl -s -X POST "$BASE/ask-kb" \
  -H "Content-Type: application/json" \
  -d '{"kb_id":"demo","query":"What is the plan for?"}')"

echo "$RESP" | python -m json.tool > /tmp/ask_kb.json

echo "== check quality gate =="

python - <<'PY'
import json, sys
d=json.load(open("/tmp/ask_kb.json"))
qg=d.get("quality_gate", {})
if qg.get("decision") != "accept":
    print("Quality gate rejected:", qg)
    sys.exit(1)
print("Quality gate: ACCEPT ✅")
PY

echo "== extract first chunk_id from source_map.S1 =="
CHUNK_ID="$(python - <<'PY'
import json
d=json.load(open("/tmp/ask_kb.json"))
print(d["source_map"]["S1"])
PY
)"

echo "chunk_id=$CHUNK_ID"

echo "== fetch chunk evidence =="
curl -s "$BASE/kb/chunk?kb_id=demo&chunk_id=$CHUNK_ID&include_content=true" | python -m json.tool

echo "== ask-kb (negative test) =="
RESP_NEG="$(curl -s -X POST "$BASE/ask-kb" \
  -H "Content-Type: application/json" \
  -d '{"kb_id":"demo","query":"What is the CEO of Apple favorite food?"}')"

echo "$RESP_NEG" | python -m json.tool > /tmp/ask_kb_neg.json

echo "== check fallback behavior =="
python - <<'PY'
import json, sys
d=json.load(open("/tmp/ask_kb_neg.json"))
qg=d.get("quality_gate", {})
fallback=d.get("fallback_used")

if qg.get("decision") != "fallback":
    print("Expected decision='fallback', got:", qg.get("decision"))
    sys.exit(1)

if not fallback:
    print("Expected fallback_used=True, got:", fallback)
    sys.exit(1)

print("Fallback behavior: OPTIMAL ✅")
PY

echo "== smoke ok ✅ =="