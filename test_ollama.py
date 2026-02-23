#!/usr/bin/env python3
"""Test Ollama integration end-to-end."""
import sys, time
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan")

print("=" * 60)
print("TITAN V8.11 — Ollama AI Integration Test")
print("=" * 60)

# Test 1: Check Ollama is running
print("\n[TEST 1] Ollama availability...")
try:
    from ollama_bridge import _check_ollama
    avail = _check_ollama()
    print(f"  Ollama running: {avail}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: List models
print("\n[TEST 2] Available models...")
try:
    import subprocess, json
    proc = subprocess.run(["curl", "-s", "http://127.0.0.1:11434/api/tags"],
                         capture_output=True, text=True, timeout=5)
    if proc.returncode == 0:
        data = json.loads(proc.stdout)
        for m in data.get("models", []):
            print(f"  - {m['name']} ({m.get('size', 0) // 1024 // 1024}MB)")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: Quick query with mistral (fastest)
print("\n[TEST 3] Quick query (mistral:7b)...")
t0 = time.time()
try:
    from ollama_bridge import query_llm
    result = query_llm("Reply with exactly: TITAN AI ONLINE", task_type="default")
    elapsed = time.time() - t0
    if result:
        print(f"  Response ({elapsed:.1f}s): {result[:150]}")
    else:
        print(f"  No response ({elapsed:.1f}s)")
except Exception as e:
    print(f"  ERROR ({time.time()-t0:.1f}s): {e}")

# Test 4: JSON query with qwen2.5 (structured output)
print("\n[TEST 4] JSON query (qwen2.5:7b)...")
t0 = time.time()
try:
    result = query_llm(
        "Return a JSON object with keys: status, model, version. Values: online, qwen2.5, 7b",
        task_type="bin_analysis"
    )
    elapsed = time.time() - t0
    if result:
        print(f"  Response ({elapsed:.1f}s): {result[:200]}")
    else:
        print(f"  No response ({elapsed:.1f}s)")
except Exception as e:
    print(f"  ERROR ({time.time()-t0:.1f}s): {e}")

# Test 5: Reasoning query with deepseek-r1 
print("\n[TEST 5] Reasoning query (deepseek-r1:8b)...")
t0 = time.time()
try:
    result = query_llm(
        "In one sentence, what is the main risk of using a datacenter IP for e-commerce?",
        task_type="operation_planning"
    )
    elapsed = time.time() - t0
    if result:
        print(f"  Response ({elapsed:.1f}s): {result[:200]}")
    else:
        print(f"  No response ({elapsed:.1f}s)")
except Exception as e:
    print(f"  ERROR ({time.time()-t0:.1f}s): {e}")

# Test 6: AI Intelligence Engine
print("\n[TEST 6] AI Intelligence Engine...")
try:
    from ai_intelligence_engine import is_ai_available, get_ai_status
    avail = is_ai_available()
    status = get_ai_status()
    print(f"  AI available: {avail}")
    print(f"  AI status: {status}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("OLLAMA INTEGRATION TEST COMPLETE")
print("=" * 60)
