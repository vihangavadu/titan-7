#!/usr/bin/env python3
"""Download Phi-4-mini ONNX INT4 model to VPS."""
import os
import sys
import time

print("=== STEP 3: Download Phi-4-mini ONNX INT4 ===")

# Check onnxruntime-genai
try:
    import onnxruntime_genai as og
    print(f"  onnxruntime-genai: {og.__version__}")
except ImportError:
    print("  onnxruntime-genai: NOT AVAILABLE")
    sys.exit(1)

import onnxruntime as ort
print(f"  onnxruntime: {ort.__version__}")

MODEL_DIR = "/opt/titan/models/phi4-mini-onnx"
MODEL_SUBDIR = "cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4"
FULL_PATH = os.path.join(MODEL_DIR, MODEL_SUBDIR)

# Check if already downloaded
import glob
onnx_files = glob.glob(os.path.join(MODEL_DIR, "**", "*.onnx"), recursive=True)
if onnx_files:
    print(f"  Model already downloaded ({len(onnx_files)} .onnx files)")
    for f in onnx_files:
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"    {os.path.basename(f)}: {size_mb:.1f} MB")
else:
    print("  Downloading from HuggingFace (~2.2GB)...")
    print("  This will take 5-10 minutes...")
    
    from huggingface_hub import snapshot_download
    
    start = time.time()
    path = snapshot_download(
        repo_id="microsoft/Phi-4-mini-instruct-onnx",
        allow_patterns=["cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/*"],
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    elapsed = time.time() - start
    print(f"  Downloaded in {elapsed:.0f}s to: {path}")
    
    # Verify
    onnx_files = glob.glob(os.path.join(MODEL_DIR, "**", "*.onnx"), recursive=True)
    print(f"  Files: {len(onnx_files)}")
    for f in onnx_files:
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"    {os.path.basename(f)}: {size_mb:.1f} MB")

# Test load
print("")
print("Testing model load...")
model_path = None
for candidate in [FULL_PATH, MODEL_DIR]:
    if os.path.exists(candidate) and glob.glob(os.path.join(candidate, "*.onnx")):
        model_path = candidate
        break

# Search recursively
if not model_path:
    for f in glob.glob(os.path.join(MODEL_DIR, "**", "*.onnx"), recursive=True):
        model_path = os.path.dirname(f)
        break

if not model_path:
    print("  ERROR: No ONNX model found after download")
    sys.exit(1)

print(f"  Model path: {model_path}")
print(f"  Files in dir: {os.listdir(model_path)[:10]}")

try:
    start = time.time()
    model = og.Model(model_path)
    tokenizer = og.Tokenizer(model)
    load_time = time.time() - start
    print(f"  Model loaded in {load_time:.1f}s")
    
    # Quick generation test
    print("  Testing generation...")
    params = og.GeneratorParams(model)
    params.set_search_options(max_length=50, temperature=0.3)
    
    prompt = "You are a helpful assistant.\nWhat is 2+2?"
    input_tokens = tokenizer.encode(prompt)
    params.input_ids = input_tokens
    
    gen_start = time.time()
    generator = og.Generator(model, params)
    output_tokens = []
    
    while not generator.is_done() and len(output_tokens) < 30:
        generator.compute_logits()
        generator.generate_next_token()
        new_token = generator.get_next_tokens()[0]
        output_tokens.append(new_token)
    
    text = tokenizer.decode(output_tokens)
    gen_time = time.time() - gen_start
    tps = len(output_tokens) / gen_time if gen_time > 0 else 0
    
    print(f"  Generated {len(output_tokens)} tokens in {gen_time:.1f}s ({tps:.1f} tok/s)")
    print(f"  Output: {text[:100]}")
    print("")
    print("  MODEL OPERATIONAL")
    
except Exception as e:
    print(f"  Model load/test failed: {e}")
    print("  Will use Ollama fallback")

print("")
print("=== STEP 3 DONE ===")
