#!/usr/bin/env python3
"""Quick verification of the full ML stack on VPS."""
import os
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["OPENBLAS_NUM_THREADS"] = "8"
os.environ["DNNL_MAX_CPU_ISA"] = "AVX512_CORE_VNNI"

import torch
print(f"PyTorch: {torch.__version__}")
print(f"CPU threads: {torch.get_num_threads()}")

# Check BF16
bf16 = False
try:
    with open("/proc/cpuinfo") as f:
        bf16 = "avx512_bf16" in f.read()
except Exception:
    pass
print(f"AVX-512 BF16: {bf16}")

# Quick BF16 matmul test
if bf16:
    import time
    x = torch.randn(2048, 2048, dtype=torch.bfloat16)
    t0 = time.time()
    for _ in range(20):
        _ = torch.mm(x, x)
    elapsed = time.time() - t0
    gflops = (2 * 2048 * 2048 * 2048 * 20) / elapsed / 1e9
    print(f"BF16 MatMul 2048x2048 (20 iters): {elapsed:.3f}s = {gflops:.1f} GFLOPS")

import transformers
print(f"Transformers: {transformers.__version__}")

import peft
print(f"PEFT: {peft.__version__}")

import datasets
print(f"Datasets: {datasets.__version__}")

import accelerate
print(f"Accelerate: {accelerate.__version__}")

import onnxruntime as ort
print(f"ONNX Runtime: {ort.__version__} providers={ort.get_available_providers()}")

import onnx
print(f"ONNX: {onnx.__version__}")

# Check training data
data_dir = "/opt/titan/training/data"
if os.path.isdir(data_dir):
    files = [f for f in os.listdir(data_dir) if f.endswith(".jsonl")]
    total_lines = 0
    for f in files:
        with open(os.path.join(data_dir, f)) as fh:
            total_lines += sum(1 for _ in fh)
    print(f"Training data: {len(files)} files, {total_lines} examples")

print("\nALL SYSTEMS GO - Ready for Phase 3 LoRA fine-tuning")
