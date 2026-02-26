#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"

echo "=== APPS IN LIVE BUT NOT SRC ==="
for f in /opt/titan/apps/*.py; do
  name=$(basename "$f")
  if [ ! -f "/opt/titan/src/apps/$name" ]; then
    lines=$(wc -l < "$f")
    echo "  MISSING from src: $name ($lines lines)"
  fi
done

echo ""
echo "=== titan.env status ==="
ls -la /opt/titan/config/titan.env 2>/dev/null || echo "  MISSING"

echo ""
echo "=== DIRECTORY CHECK ==="
for d in core apps src config scripts docs training tests bin branding modelfiles; do
  if [ -d "/opt/titan/$d" ]; then
    count=$(find "/opt/titan/$d" -type f 2>/dev/null | wc -l)
    echo "  /opt/titan/$d: $count files"
  else
    echo "  MISSING: /opt/titan/$d"
  fi
done

echo ""
echo "=== LLM CONFIG TASK ROUTING ==="
python3 -c "
import json
cfg = json.load(open('/opt/titan/config/llm_config.json'))
routing = {k:v for k,v in cfg.items() if not k.startswith('_')}
print(f'  Total routing entries: {len(routing)}')
for k,v in sorted(routing.items())[:35]:
    if isinstance(v, str):
        print(f'  {k:45s} -> {v}')
    elif isinstance(v, dict):
        model = v.get('model', v.get('name', str(v)[:60]))
        print(f'  {k:45s} -> {model}')
" 2>/dev/null || echo "  Parse error"

echo ""
echo "=== AI MODEL QUICK CHECK (5s timeout, 10 token limit) ==="
for model in titan-analyst titan-strategist titan-fast; do
  echo -n "  $model: "
  resp=$(curl -s --max-time 8 http://127.0.0.1:11434/api/generate \
    -d "{\"model\":\"$model\",\"prompt\":\"Reply OK\",\"stream\":false,\"options\":{\"num_predict\":5,\"temperature\":0}}" 2>/dev/null)
  if [ -z "$resp" ]; then
    echo "TIMEOUT"
  else
    answer=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','NO_RESP')[:60])" 2>/dev/null || echo "PARSE_ERR")
    echo "$answer"
  fi
done

echo ""
echo "=== MODELFILE CHECK ==="
for model in titan-analyst titan-strategist titan-fast; do
  echo "-- $model --"
  curl -s http://127.0.0.1:11434/api/show -d "{\"name\":\"$model\"}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
det=d.get('details',{})
print(f'  family={det.get(\"family\",\"?\")} params={det.get(\"parameter_size\",\"?\")} quant={det.get(\"quantization_level\",\"?\")}')
# Show SYSTEM prompt first 200 chars
mf=d.get('modelfile','')
for line in mf.split('\n'):
    if line.startswith('SYSTEM'):
        print(f'  SYSTEM: {line[7:200]}')
        break
" 2>/dev/null
done

echo ""
echo "=== DONE ==="
