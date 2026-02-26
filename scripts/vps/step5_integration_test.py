#!/usr/bin/env python3
"""Full integration test: ONNX engine + Ollama fallback + task routing."""
import os
import sys
import json
import time

sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan/apps")
os.environ["TITAN_ROOT"] = "/opt/titan"

print("=" * 60)
print("TITAN OS — Full AI Integration Test")
print("=" * 60)

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  OK: {name}" + (f" ({detail})" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL: {name}" + (f" ({detail})" if detail else ""))

# --- 1. ONNX Engine Import ---
print("\n[1] ONNX Engine Import")
try:
    from titan_onnx_engine import get_engine, get_status, generate, generate_json
    check("titan_onnx_engine imports", True)
except Exception as e:
    check("titan_onnx_engine imports", False, str(e))
    sys.exit(1)

# --- 2. Engine Status ---
print("\n[2] Engine Status")
status = get_status()
print(f"  Backend: {status.get('backend')}")
print(f"  Model loaded: {status.get('model_loaded')}")
print(f"  ONNX files: {status.get('onnx_files')}")
print(f"  Tasks mapped: {status.get('tasks_mapped')}")
check("engine initialized", status.get("initialized"))
check("model directory exists", status.get("model_dir_exists"))
check("tasks mapped > 20", status.get("tasks_mapped", 0) > 20)

# --- 3. Generation Test (ONNX or Ollama fallback) ---
print("\n[3] Generation Test")
backend = status.get("backend", "unknown")
print(f"  Using backend: {backend}")

start = time.time()
result = generate("What is BIN 421783?", task="bin_analysis")
elapsed = time.time() - start

check("generation succeeds", result.ok, f"{elapsed:.1f}s")
check("response not empty", len(result.text) > 10, f"{len(result.text)} chars")
check("tokens generated > 0", result.tokens_generated > 0, f"{result.tokens_generated} tokens")
print(f"  Speed: {result.tokens_per_second:.1f} tok/s")
print(f"  Backend used: {result.backend}")
print(f"  Preview: {result.text[:150]}...")

# --- 4. JSON Generation Test ---
print("\n[4] JSON Generation Test")
start = time.time()
json_result = generate_json("Score target eneba.com for BIN 421783", task="target_recon")
elapsed = time.time() - start

check("json generation succeeds", json_result.get("ok"), f"{elapsed:.1f}s")
if json_result.get("data"):
    print(f"  JSON keys: {list(json_result['data'].keys())[:5]}")
elif json_result.get("raw_text"):
    print(f"  Raw text preview: {json_result['raw_text'][:100]}...")

# --- 5. Multiple Task Routing ---
print("\n[5] Task Routing (5 different tasks)")
tasks_to_test = [
    ("situation_assessment", "Profile is 3 days old. Should I proceed on amazon.com?"),
    ("decline_diagnosis", "Got decline code card_declined on Stripe. BIN 479226."),
    ("3ds_strategy", "Expecting 3DS on farfetch.com. BIN has VBV. No phone access."),
    ("copilot_guidance", "Quick: best time to run operations EST?"),
    ("fingerprint_check", "Check: Windows 10, Chrome 128, timezone America/Chicago, WebGL ANGLE NVIDIA RTX 3060"),
]

for task, prompt in tasks_to_test:
    start = time.time()
    r = generate(prompt, task=task, max_tokens=100)
    elapsed = time.time() - start
    check(f"task:{task}", r.ok, f"{elapsed:.1f}s, {r.tokens_per_second:.0f}t/s, persona={r.persona}")

# --- 6. Training Data Check ---
print("\n[6] Training Data")
import glob
training_files = glob.glob("/opt/titan/training/data_v10_operator/*.jsonl")
if training_files:
    total_lines = 0
    for f in training_files:
        with open(f) as fh:
            lines = sum(1 for _ in fh)
            total_lines += lines
    check("operator training data exists", True, f"{total_lines} examples in {len(training_files)} files")
    
    # Validate format
    with open(training_files[0]) as fh:
        sample = json.loads(fh.readline())
        has_messages = "messages" in sample
        has_3_roles = len(sample.get("messages", [])) == 3
        roles = [m["role"] for m in sample.get("messages", [])]
        check("ChatML format valid", has_messages and has_3_roles, f"roles={roles}")
else:
    check("operator training data exists", False, "no .jsonl files")

# --- 7. llm_config.json ---
print("\n[7] LLM Config")
config_path = "/opt/titan/config/llm_config.json"
if os.path.exists(config_path):
    with open(config_path) as f:
        cfg = json.load(f)
    routes = cfg.get("task_routing", {})
    check("llm_config.json exists", True, f"{len(routes)} task routes")
else:
    check("llm_config.json exists", False)

# --- 8. Ollama Models Still Working ---
print("\n[8] Ollama Models (backup)")
import urllib.request
try:
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    models = [m["name"] for m in data.get("models", [])]
    titan_models = [m for m in models if "titan" in m]
    check("ollama running", True, f"{len(models)} models")
    check("titan models present", len(titan_models) >= 3, str(titan_models))
except Exception as e:
    check("ollama running", False, str(e))

# --- 9. ONNX Model Files ---
print("\n[9] ONNX Model Files")
onnx_files = glob.glob("/opt/titan/models/phi4-mini-onnx/**/*.onnx", recursive=True)
check("phi4-mini ONNX files", len(onnx_files) > 0, f"{len(onnx_files)} files")
total_size = sum(os.path.getsize(f) for f in onnx_files) / 1024 / 1024
data_files = glob.glob("/opt/titan/models/phi4-mini-onnx/**/*.onnx.data", recursive=True)
if data_files:
    total_size += sum(os.path.getsize(f) for f in data_files) / 1024 / 1024
print(f"  Total model size: {total_size:.0f} MB")

# --- Summary ---
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed")
print(f"ONNX Backend: {backend}")
print(f"Model: Phi-4-mini INT4 ({total_size:.0f} MB)")
print(f"Training data: {total_lines if training_files else 0} examples")
print("=" * 60)
