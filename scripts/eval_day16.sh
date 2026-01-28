#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=backend
python backend/app/eval/run_eval.py

echo ""
echo "=== Summary ==="
python - <<'PY'
import json
p="storage/eval_results/day16_eval.json"
d=json.load(open(p))
print(json.dumps(d.get("summary", {}), indent=2, ensure_ascii=False))
PY
