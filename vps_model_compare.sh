#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN — EXTENDED MODEL COMPARISON                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "VPS specs: 8 CPU cores | 32GB RAM | No GPU | CPU inference only"
echo ""

echo "=== CURRENTLY INSTALLED MODELS ==="
ollama list 2>/dev/null
echo ""

echo "=== SYSTEM RAM AVAILABLE FOR MODELS ==="
free -h | grep Mem
echo ""
echo "Rule of thumb for CPU inference (Q4 quantization):"
echo "  7B  model → ~4-5GB RAM  → fits easily"
echo "  13B model → ~8-9GB RAM  → fits easily"
echo "  30B model → ~18-20GB RAM → fits on this VPS"
echo "  70B model → ~40-45GB RAM → TOO BIG (only 32GB)"
echo ""

python3 - <<'PYEOF'
import json, time, urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def query(model, prompt, max_tokens=200, temperature=0.1, timeout=90):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            r = json.loads(resp.read().decode())
            elapsed = time.time() - t0
            tokens = r.get("eval_count", 0)
            return {
                "text": r.get("response", ""),
                "tokens": tokens,
                "elapsed": elapsed,
                "tps": tokens / max(elapsed, 0.1),
                "load_s": r.get("load_duration", 0) / 1e9,
                "ok": True
            }
    except Exception as e:
        return {"text": f"ERROR: {e}", "tokens": 0, "elapsed": 0, "tps": 0, "load_s": 0, "ok": False}

# Get installed models
try:
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        installed = [m["name"] for m in data.get("models", [])]
except:
    installed = ["qwen2.5:7b", "mistral:7b-instruct-v0.2-q4_0"]

print(f"Installed models: {installed}")
print()

# Benchmark prompts — real TITAN tasks
PROMPTS = [
    ("JSON output", 'Respond ONLY with JSON: {"bank":"Chase","country":"US","risk":45,"card":"credit"}'),
    ("Fraud engine ID", "What fraud system does nike.com use? One word: Forter, Riskified, Sift, or Kount."),
    ("3DS advice", "Best 3DS bypass for $200 on amazon.com? One sentence."),
    ("Speed test", "What is a BIN number? One sentence only."),
]

results = {}
for model in installed:
    print(f"\n{'─'*60}")
    print(f"  Testing: {model}")
    print(f"{'─'*60}")
    scores = []
    total_tps = 0
    passes = 0
    
    for name, prompt in PROMPTS:
        r = query(model, prompt, max_tokens=150)
        passed = r["ok"] and len(r["text"]) > 5
        if passed:
            passes += 1
            total_tps += r["tps"]
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name:<20} | {r['tps']:>5.1f} tok/s | {r['elapsed']:>5.1f}s | {r['text'][:60].strip()}")
    
    avg_tps = total_tps / max(passes, 1)
    results[model] = {"passes": passes, "avg_tps": avg_tps, "total": len(PROMPTS)}
    print(f"  → Avg: {avg_tps:.1f} tok/s | {passes}/{len(PROMPTS)} passed")

# Recommend additional models to pull
print(f"\n\n{'═'*60}")
print("  WHAT ELSE CAN THIS VPS RUN?")
print(f"{'═'*60}\n")

candidates = [
    ("llama3.2:3b",      "3B",  "~2GB",  "Fastest, good for simple tasks"),
    ("llama3.1:8b",      "8B",  "~5GB",  "Meta's best 8B, strong reasoning"),
    ("qwen2.5-coder:7b", "7B",  "~5GB",  "Best for JSON/code structured output"),
    ("deepseek-r1:8b",   "8B",  "~5GB",  "Strong reasoning, chain-of-thought"),
    ("phi4:14b",         "14B", "~9GB",  "Microsoft, excellent instruction following"),
    ("gemma2:9b",        "9B",  "~6GB",  "Google, very fast inference"),
    ("llama3.1:70b",     "70B", "~40GB", "TOO BIG — exceeds 32GB RAM"),
]

print(f"  {'Model':<25} {'Size':<6} {'RAM':<8} {'Notes'}")
print(f"  {'─'*65}")
for model, size, ram, notes in candidates:
    already = "✅ INSTALLED" if any(model.split(":")[0] in m for m in installed) else ""
    too_big = "❌ TOO BIG" if "TOO BIG" in notes else ""
    flag = already or too_big or "⬇️  pullable"
    print(f"  {model:<25} {size:<6} {ram:<8} {flag} — {notes}")

# Final verdict
print(f"\n{'═'*60}")
print("  VERDICT — CURRENT INSTALLED MODELS")
print(f"{'═'*60}\n")

best_model = max(results, key=lambda m: results[m]["avg_tps"] * results[m]["passes"])
for model, r in results.items():
    crown = "🏆" if model == best_model else "  "
    print(f"  {crown} {model}")
    print(f"       Speed: {r['avg_tps']:.1f} tok/s | Quality: {r['passes']}/{r['total']} tasks passed")

print(f"\n  Best for TITAN tasks: {best_model}")
print(f"\n  RECOMMENDATION:")
print(f"  Pull 'qwen2.5-coder:7b' for better JSON structured output")
print(f"  Pull 'gemma2:9b' for faster inference speed")
print(f"  Keep mistral as primary — it's the best balance currently installed")
PYEOF
