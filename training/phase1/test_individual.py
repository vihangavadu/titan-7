#!/usr/bin/env python3
"""Test each model individually with 300s timeout."""
import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

tests = [
    ("titan-strategist", "Perform decline autopsy: code=card_declined, category=fraud_block, target=stockx.com, psp=stripe, amount=220, bin=414720 (Chase Visa), session=95s, profile_age=45d. Output JSON."),
    ("titan-fast", "My checkout was declined on Eneba with code card_declined. BIN 421783, amount 85 USD. What happened and what should I do?"),
]

for model, prompt in tests:
    print(f"\n=== Testing {model} ===")
    t0 = time.time()
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        }, timeout=300)
        data = r.json()
        resp = data.get("response", "")
        elapsed = time.time() - t0
        print(f"Time: {elapsed:.1f}s | Length: {len(resp)} chars")
        print(resp[:1200])
    except Exception as e:
        print(f"ERROR after {time.time()-t0:.1f}s: {e}")
