#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"
KB_ID="${KB_ID:-demo}"

OK_QUERY="${OK_QUERY:-What is the plan for?}"
BAD_QUERY="${BAD_QUERY:-What is the CEO of Apple favorite food?}"

TMP_DIR="${TMP_DIR:-/tmp}"
OK_JSON="$TMP_DIR/gate_ok.json"
BAD_JSON="$TMP_DIR/gate_bad.json"

MOCK_FILE="${MOCK_FILE:-/tmp/rag_mock_response.txt}"

cleanup() {
  rm -f "$MOCK_FILE"
}
trap cleanup EXIT

echo "== Gate Regression =="
echo "BASE=$BASE"
echo "KB_ID=$KB_ID"
echo "TMP_DIR=$TMP_DIR"
echo ""

# ---------- helpers ----------
req() {
  local query="$1"
  curl -s -X POST "$BASE/ask-kb" \
    -H "Content-Type: application/json" \
    -d "{\"kb_id\":\"$KB_ID\",\"query\":\"$query\"}"
}

py_assert_ok_case() {
  python3 -c "
import json, sys
path=\"$OK_JSON\"
d=json.load(open(path, 'r', encoding='utf-8'))

gate=d.get('quality_gate', {}) or {}
decision=gate.get('decision')
reason=gate.get('reason')

evaluation=d.get('evaluation', {}) or {}
ok=evaluation.get('ok')

if decision != 'accept':
  print(f'[FAIL] OK case: quality_gate.decision expected accept, got {decision!r} (reason={reason!r})')
  sys.exit(1)

if ok is not True:
  print(f'[FAIL] OK case: evaluation.ok expected true, got {ok!r}')
  sys.exit(1)

ans=(d.get('answer') or '').strip()
if not ans:
  print('[FAIL] OK case: answer is empty')
  sys.exit(1)

print('[PASS] OK case: accept + evaluation.ok=true + non-empty answer')
"
}

py_assert_bad_case_allow_reject_or_fallback() {
  python3 -c "
import json, sys
path=\"$BAD_JSON\"
d=json.load(open(path, 'r', encoding='utf-8'))

gate=d.get('quality_gate', {}) or {}
decision=gate.get('decision')
reason=gate.get('reason')

if decision not in ('fallback', 'reject'):
  print(f'[FAIL] BAD case: quality_gate.decision expected fallback or reject, got {decision!r} (reason={reason!r})')
  sys.exit(1)

ans=(d.get('answer') or '').strip()
if not ans:
  print('[FAIL] BAD case: answer is empty')
  sys.exit(1)

fallback_prefix='I couldn\\'t produce a fully grounded answer.'
if fallback_prefix not in ans and '- [S' not in ans:
  print('[FAIL] BAD case: expected grounded fallback format (prefix or - [S bullets), but not found')
  sys.exit(1)

final_eval=d.get('final_evaluation', None)
evaluation=d.get('evaluation', {}) or {}

# If final_evaluation exists (your Day19+ pattern), it MUST be ok=True
if isinstance(final_eval, dict):
  fe_ok=final_eval.get('ok')
  if fe_ok is not True:
    print(f'[FAIL] BAD case: final_evaluation.ok expected true, got {fe_ok!r}')
    sys.exit(1)
else:
  # If not present, original evaluation should have failed
  if evaluation.get('ok') is not False:
    print(f'[FAIL] BAD case: evaluation.ok expected false when no final_evaluation, got {evaluation.get('ok')!r}')
    sys.exit(1)

print(f'[PASS] BAD case: decision={decision!r} reason={reason!r} + fallback answer + eval semantics OK')
"
}

py_assert_must_fallback_case() {
  python3 -c "
import json, sys
path=\"$BAD_JSON\"
d=json.load(open(path, 'r', encoding='utf-8'))

gate=d.get('quality_gate', {}) or {}
decision=gate.get('decision')
reason=gate.get('reason')

if decision != 'fallback':
  print(f'[FAIL] MUST-FALLBACK case: expected decision=fallback, got {decision!r} (reason={reason!r})')
  sys.exit(1)

if d.get('fallback_used') is not True:
  print('[FAIL] MUST-FALLBACK case: expected fallback_used=true')
  sys.exit(1)

final_eval=d.get('final_evaluation', {}) or {}
if final_eval.get('ok') is not True:
  print(f\"[FAIL] MUST-FALLBACK case: expected final_evaluation.ok=true, got {final_eval.get('ok')!r}\")
  sys.exit(1)

ans=(d.get('answer') or '').strip()
if '- [S' not in ans:
  print('[FAIL] MUST-FALLBACK case: expected - [S bullets in fallback answer')
  sys.exit(1)

print(f'[PASS] MUST-FALLBACK case: decision=fallback reason={reason!r} + fallback_used + final_evaluation.ok')
"
}

# ---------- run ----------
echo "== health =="
retries=0
while ! curl -s "$BASE/health" | grep -q "ok"; do
  sleep 1
  retries=$((retries+1))
  if [ "$retries" -gt 30 ]; then
    echo "[FAIL] Server failed to become ready within 30s"
    exit 1
  fi
  echo -n "."
done
echo ""
curl -s "$BASE/health" | python -m json.tool
echo ""

echo "== Case A: OK query should ACCEPT =="
echo "This is a verified plan [S1] and [S2]." > "$MOCK_FILE"
req "$OK_QUERY" > "$OK_JSON"
cat "$OK_JSON" | python -m json.tool
py_assert_ok_case
echo ""

echo "== Case B: BAD query should FALLBACK (or reject+fallback answer) =="
echo "I like apples." > "$MOCK_FILE"
req "$BAD_QUERY" > "$BAD_JSON"
cat "$BAD_JSON" | python -m json.tool
py_assert_bad_case_allow_reject_or_fallback
echo ""

echo "== Case C: Hallucination (no citations) MUST FALLBACK =="
# 用 OK_QUERY 保证 retrieval 稳定，但 mock answer 故意不带 [S#]
echo "Apple CEO likes sushi." > "$MOCK_FILE"
req "$OK_QUERY" > "$BAD_JSON"
cat "$BAD_JSON" | python -m json.tool
py_assert_must_fallback_case
echo ""

echo "== Gate regression ok ✅ =="
