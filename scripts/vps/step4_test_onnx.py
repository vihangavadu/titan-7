#!/usr/bin/env python3
"""Test Phi-4-mini ONNX model with corrected 0.12 API."""
import os
import sys
import time
import glob

print("=== STEP 4: Test ONNX Model (0.12 API) ===")

MODEL_DIR = "/opt/titan/models/phi4-mini-onnx"
MODEL_SUBDIR = "cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4"
FULL_PATH = os.path.join(MODEL_DIR, MODEL_SUBDIR)

# Find model
model_path = None
for candidate in [FULL_PATH, MODEL_DIR]:
    if os.path.exists(candidate) and glob.glob(os.path.join(candidate, "*.onnx")):
        model_path = candidate
        break
if not model_path:
    for f in glob.glob(os.path.join(MODEL_DIR, "**", "*.onnx"), recursive=True):
        model_path = os.path.dirname(f)
        break

if not model_path:
    print("  ERROR: No ONNX model found")
    sys.exit(1)

print(f"  Model path: {model_path}")

try:
    import onnxruntime_genai as og
    print(f"  onnxruntime-genai: {og.__version__}")
except ImportError:
    print("  onnxruntime-genai not installed")
    sys.exit(1)

# Load model
print("  Loading model...")
start = time.time()
model = og.Model(model_path)
tokenizer = og.Tokenizer(model)
print(f"  Loaded in {time.time()-start:.1f}s")

# Test generation with 0.12 API (append_tokens instead of input_ids)
print("  Testing generation (0.12 API)...")

prompt = "You are an expert analyst. What is 2+2? Answer briefly."

params = og.GeneratorParams(model)
params.set_search_options(max_length=100, temperature=0.3)

input_tokens = tokenizer.encode(prompt)
print(f"  Input tokens: {len(input_tokens)}")

gen_start = time.time()
generator = og.Generator(model, params)
generator.append_tokens(input_tokens)

output_tokens = []
while not generator.is_done() and len(output_tokens) < 50:
    generator.generate_next_token()
    new_token = generator.get_next_tokens()[0]
    output_tokens.append(new_token)

text = tokenizer.decode(output_tokens)
gen_time = time.time() - gen_start
tps = len(output_tokens) / gen_time if gen_time > 0 else 0

print(f"  Generated {len(output_tokens)} tokens in {gen_time:.1f}s ({tps:.1f} tok/s)")
print(f"  Output: {text[:200]}")

# Test operator prompt
print("")
print("  Testing operator prompt...")
operator_prompt = (
    "You are TITAN-OPERATOR, an expert AI copilot. "
    "Assess: BIN 421783 (Bank of America, Visa). Target: eneba.com. "
    "3 declines today. Should I proceed?"
)

params2 = og.GeneratorParams(model)
params2.set_search_options(max_length=300, temperature=0.3)

input_tokens2 = tokenizer.encode(operator_prompt)
gen_start2 = time.time()
generator2 = og.Generator(model, params2)
generator2.append_tokens(input_tokens2)

output_tokens2 = []
while not generator2.is_done() and len(output_tokens2) < 200:
    generator2.generate_next_token()
    new_token = generator2.get_next_tokens()[0]
    output_tokens2.append(new_token)

text2 = tokenizer.decode(output_tokens2)
gen_time2 = time.time() - gen_start2
tps2 = len(output_tokens2) / gen_time2 if gen_time2 > 0 else 0

print(f"  Generated {len(output_tokens2)} tokens in {gen_time2:.1f}s ({tps2:.1f} tok/s)")
print(f"  Output preview: {text2[:300]}")

print("")
print("  ONNX MODEL FULLY OPERATIONAL")
print(f"  Average speed: {(tps + tps2) / 2:.1f} tokens/sec on CPU")
print("")
print("=== STEP 4 DONE ===")
