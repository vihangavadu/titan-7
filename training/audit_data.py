#!/usr/bin/env python3
"""Audit V9 training data quality on Vast.ai instance."""
import json, os, sys

data_dir = "/workspace/training/data_v9"
tasks = sorted([f for f in os.listdir(data_dir) if f.endswith(".jsonl") and not f.startswith("combined")])
print("Task files:", len(tasks))

gaps = []
quality = {}
for tf in tasks:
    name = tf.replace(".jsonl", "")
    lines = open(os.path.join(data_dir, tf)).readlines()
    valid = 0
    has_cot = 0
    avg_resp_len = 0
    short_resp = 0
    empty = 0
    has_json_resp = 0
    for line in lines:
        try:
            d = json.loads(line)
            valid += 1
            resp = d.get("response", "")
            avg_resp_len += len(resp)
            if len(resp) < 50:
                short_resp += 1
            if len(resp) == 0:
                empty += 1
            if "reasoning" in resp.lower() or "because" in resp.lower() or "therefore" in resp.lower():
                has_cot += 1
            # Check if response contains valid JSON
            try:
                json.loads(resp)
                has_json_resp += 1
            except:
                pass
        except:
            pass
    avg_resp_len = avg_resp_len // max(valid, 1)
    issues = []
    if valid < 300:
        issues.append("only %d/300 valid" % valid)
    if has_cot < 100:
        issues.append("low CoT: %d/300" % has_cot)
    if short_resp > 30:
        issues.append("%d short responses" % short_resp)
    if empty > 0:
        issues.append("%d empty responses" % empty)
    if avg_resp_len < 200:
        issues.append("avg_len=%d" % avg_resp_len)
    if issues:
        gaps.append((name, issues, avg_resp_len))
    quality[name] = {
        "valid": valid, "cot": has_cot, "avg_len": avg_resp_len,
        "short": short_resp, "json_resp": has_json_resp
    }

print("\n=== GAPS FOUND: %d ===" % len(gaps))
for name, issues, avg in gaps:
    print("  %s: %s" % (name, ", ".join(issues)))

print("\n=== QUALITY SUMMARY ===")
cot_scores = [v["cot"] for v in quality.values()]
lens = [v["avg_len"] for v in quality.values()]
json_scores = [v["json_resp"] for v in quality.values()]
print("  CoT range: %d-%d/300 (avg: %d)" % (min(cot_scores), max(cot_scores), sum(cot_scores)//len(cot_scores)))
print("  Resp len range: %d-%d chars (avg: %d)" % (min(lens), max(lens), sum(lens)//len(lens)))
shorts = [v["short"] for v in quality.values()]
print("  Short responses: %d total across all tasks" % sum(shorts))
print("  JSON-parseable responses: %d-%d/300 (avg: %d)" % (min(json_scores), max(json_scores), sum(json_scores)//len(json_scores)))

# Top 5 worst by CoT
print("\n=== WORST 5 BY CoT REASONING ===")
worst_cot = sorted(quality.items(), key=lambda x: x[1]["cot"])[:5]
for name, v in worst_cot:
    print("  %s: cot=%d, avg_len=%d, json=%d" % (name, v["cot"], v["avg_len"], v["json_resp"]))

# Top 5 shortest responses
print("\n=== WORST 5 BY RESPONSE LENGTH ===")
worst_len = sorted(quality.items(), key=lambda x: x[1]["avg_len"])[:5]
for name, v in worst_len:
    print("  %s: avg_len=%d, cot=%d" % (name, v["avg_len"], v["cot"]))

# Check training progress
print("\n=== TRAINING PROGRESS ===")
log_file = "/workspace/training/logs/gpu_training.log"
if os.path.exists(log_file):
    lines = open(log_file).readlines()
    # Find last progress line
    for line in reversed(lines[-200:]):
        if "/3452" in line or "/3150" in line or "/1950" in line or "loss" in line.lower():
            print("  " + line.strip()[:120])
            break
    # Find any completed models
    for line in lines:
        if "COMPLETE" in line or "saved" in line.lower() or "finished" in line.lower():
            print("  " + line.strip()[:120])
