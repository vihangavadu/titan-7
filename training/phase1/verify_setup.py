#!/usr/bin/env python3
"""Verify CPU-optimized ML stack and benchmark PyTorch on AMD EPYC."""
import sys
import os
import time

print("=" * 60)
print("TITAN V8.3 — CPU-Optimized ML Stack Verification")
print("=" * 60)
print(f"Python: {sys.version}")
print()

# Environment
print("--- Environment ---")
for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "DNNL_MAX_CPU_ISA"]:
    print(f"  {k}: {os.environ.get(k, 'NOT SET')}")
print()

# PyTorch
print("--- PyTorch ---")
try:
    import torch
    print(f"  Version: {torch.__version__}")
    print(f"  CPU threads: {torch.get_num_threads()}")
    print(f"  Inter-op threads: {torch.get_num_interop_threads()}")
    print(f"  CUDA: {torch.cuda.is_available()}")

    # Set optimal threads for AMD EPYC 8 vCPU
    torch.set_num_threads(8)
    torch.set_num_interop_threads(4)

    # MatMul benchmark
    sizes = [(512, 512), (1024, 1024), (2048, 2048)]
    for n, m in sizes:
        x = torch.randn(n, m)
        # Warmup
        for _ in range(5):
            _ = torch.mm(x, x)
        # Benchmark
        t0 = time.time()
        iters = 50
        for _ in range(iters):
            _ = torch.mm(x, x)
        elapsed = time.time() - t0
        gflops = (2 * n * m * m * iters) / elapsed / 1e9
        print(f"  MatMul {n}x{m} ({iters} iters): {elapsed:.3f}s = {gflops:.1f} GFLOPS")
except ImportError as e:
    print(f"  NOT INSTALLED: {e}")
print()

# Transformers
print("--- HuggingFace Stack ---")
pkgs = [
    ("transformers", "transformers"),
    ("datasets", "datasets"),
    ("accelerate", "accelerate"),
    ("peft", "peft"),
    ("sentencepiece", "sentencepiece"),
    ("safetensors", "safetensors"),
    ("tokenizers", "tokenizers"),
]
for name, mod in pkgs:
    try:
        m = __import__(mod)
        ver = getattr(m, "__version__", "?")
        print(f"  {name}: {ver}")
    except ImportError:
        print(f"  {name}: NOT INSTALLED")
print()

# ONNX
print("--- ONNX Stack ---")
try:
    import onnxruntime as ort
    print(f"  ONNX Runtime: {ort.__version__}")
    print(f"  Providers: {ort.get_available_providers()}")
except ImportError:
    print("  ONNX Runtime: NOT INSTALLED")
try:
    import onnx
    print(f"  ONNX: {onnx.__version__}")
except ImportError:
    print("  ONNX: NOT INSTALLED")
try:
    import optimum
    print(f"  Optimum: {optimum.__version__}")
except ImportError:
    print("  Optimum: NOT INSTALLED")
print()

# NumPy BLAS
print("--- Math Libraries ---")
import numpy as np
print(f"  NumPy: {np.__version__}")
# Quick BLAS test
n = 2000
a = np.random.randn(n, n).astype(np.float32)
t0 = time.time()
for _ in range(10):
    _ = a @ a
elapsed = time.time() - t0
gflops = (2 * n * n * n * 10) / elapsed / 1e9
print(f"  NumPy MatMul {n}x{n} (10 iters): {elapsed:.3f}s = {gflops:.1f} GFLOPS (OpenBLAS)")
print()

# Disk I/O
print("--- Disk I/O ---")
test_file = "/tmp/titan_disktest"
data = os.urandom(256 * 1024 * 1024)  # 256MB
t0 = time.time()
with open(test_file, "wb") as f:
    f.write(data)
write_speed = 256 / (time.time() - t0)
t0 = time.time()
with open(test_file, "rb") as f:
    _ = f.read()
read_speed = 256 / (time.time() - t0)
os.remove(test_file)
print(f"  Write: {write_speed:.0f} MB/s")
print(f"  Read: {read_speed:.0f} MB/s")
print()

# Summary
print("=" * 60)
print("READY FOR TRAINING")
print("=" * 60)
