#!/bin/bash
curl -s http://localhost:8000/openapi.json > /tmp/api_routes.json 2>/dev/null
python3 << 'PYEOF'
import json
try:
    d = json.load(open("/tmp/api_routes.json"))
    info = d.get("info", {})
    print(f"API: {info.get('title','?')} v{info.get('version','?')}")
    paths = list(d.get("paths", {}).keys())
    print(f"Routes ({len(paths)} total):")
    for p in paths[:25]:
        print(f"  {p}")
except Exception as e:
    print(f"Error: {e}")
    print(open("/tmp/api_routes.json").read()[:300])
PYEOF
