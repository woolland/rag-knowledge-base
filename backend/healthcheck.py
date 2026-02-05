import urllib.request, json, sys
try:
    r = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)
    data = json.loads(r.read().decode())
    assert data.get("status") == "ok"
except Exception:
    sys.exit(1)
