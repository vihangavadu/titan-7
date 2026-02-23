#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# TITAN V8.3 — CPU-Optimized ML Training Setup
# ═══════════════════════════════════════════════════════════════
# Target: AMD EPYC 9354P (8 vCPU, 32GB RAM, AVX-512 + VNNI)
# Disk: SSD (QEMU/NVMe-backed on Hostinger)
# NumPy: OpenBLAS 0.3.31 already linked ✓
# ONNX Runtime: 1.24.2 already installed ✓
# ═══════════════════════════════════════════════════════════════

set -e
echo "=== TITAN V8.3 CPU-Optimized ML Training Setup ==="
echo "CPU: AMD EPYC 9354P | AVX-512 + VNNI"
echo ""

# ───────────────────────────────────────────────────────────────
# Step 1: System-level optimizations
# ───────────────────────────────────────────────────────────────
echo "[1/6] Setting system-level CPU optimizations..."

# OpenMP thread tuning for AMD EPYC
cat > /etc/profile.d/titan_ml.sh << 'EOF'
# TITAN ML CPU Optimizations for AMD EPYC
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export GOMP_CPU_AFFINITY="0-7"
export OMP_SCHEDULE="static"
export OMP_PROC_BIND=close
export OMP_PLACES=cores

# PyTorch CPU optimizations
export PYTORCH_ENABLE_MPS_FALLBACK=0
export TORCH_CPU_ALLOCATOR=native
export DNNL_MAX_CPU_ISA=AVX512_CORE_VNNI

# ONNX Runtime optimizations
export ORT_DISABLE_ALL_LOGS=1

# Avoid NUMA issues on VPS
export MALLOC_ARENA_MAX=2
EOF

source /etc/profile.d/titan_ml.sh
echo "  ✓ OMP_NUM_THREADS=8, OPENBLAS_NUM_THREADS=8, AVX512_CORE_VNNI enabled"

# ───────────────────────────────────────────────────────────────
# Step 2: Install PyTorch CPU-only (no CUDA bloat)
# ───────────────────────────────────────────────────────────────
echo ""
echo "[2/6] Installing PyTorch CPU-only (AVX-512 optimized)..."
pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -5
echo "  ✓ PyTorch CPU installed"

# ───────────────────────────────────────────────────────────────
# Step 3: Install HuggingFace ecosystem
# ───────────────────────────────────────────────────────────────
echo ""
echo "[3/6] Installing HuggingFace transformers + training stack..."
pip3 install --no-cache-dir \
    transformers==4.48.0 \
    datasets==3.3.0 \
    accelerate==1.3.0 \
    peft==0.14.0 \
    sentencepiece==0.2.0 \
    protobuf==5.29.0 \
    safetensors==0.5.0 \
    tokenizers==0.21.0 \
    2>&1 | tail -5
echo "  ✓ HuggingFace stack installed"

# ───────────────────────────────────────────────────────────────
# Step 4: Install ONNX tools for model export + fast inference
# ───────────────────────────────────────────────────────────────
echo ""
echo "[4/6] Installing ONNX optimization tools..."
pip3 install --no-cache-dir \
    onnx==1.17.0 \
    optimum[onnxruntime]==1.24.0 \
    2>&1 | tail -5
echo "  ✓ ONNX + Optimum installed (CPU inference acceleration)"

# ───────────────────────────────────────────────────────────────
# Step 5: Install AMD-optimized libraries
# ───────────────────────────────────────────────────────────────
echo ""
echo "[5/6] Installing AMD-optimized libraries..."
# libomp for AMD EPYC OpenMP performance
apt-get install -y libomp-dev 2>/dev/null | tail -2
# Ensure OpenBLAS is system-level available
apt-get install -y libopenblas-dev 2>/dev/null | tail -2
echo "  ✓ libomp + OpenBLAS system libs installed"

# ───────────────────────────────────────────────────────────────
# Step 6: Verify installation
# ───────────────────────────────────────────────────────────────
echo ""
echo "[6/6] Verifying installation..."

python3 << 'PYEOF'
import sys
print(f"Python: {sys.version}")

# PyTorch
try:
    import torch
    print(f"PyTorch: {torch.__version__}")
    print(f"  CPU threads: {torch.get_num_threads()}")
    print(f"  Inter-op threads: {torch.get_num_interop_threads()}")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    
    # Test AVX-512
    x = torch.randn(1000, 1000)
    import time
    t0 = time.time()
    for _ in range(100):
        _ = torch.mm(x, x)
    elapsed = time.time() - t0
    print(f"  MatMul benchmark (1000x1000, 100 iters): {elapsed:.2f}s")
except ImportError:
    print("PyTorch: NOT INSTALLED")

# Transformers
try:
    import transformers
    print(f"Transformers: {transformers.__version__}")
except ImportError:
    print("Transformers: NOT INSTALLED")

# PEFT
try:
    import peft
    print(f"PEFT: {peft.__version__}")
except ImportError:
    print("PEFT: NOT INSTALLED")

# Datasets
try:
    import datasets
    print(f"Datasets: {datasets.__version__}")
except ImportError:
    print("Datasets: NOT INSTALLED")

# Accelerate
try:
    import accelerate
    print(f"Accelerate: {accelerate.__version__}")
except ImportError:
    print("Accelerate: NOT INSTALLED")

# ONNX Runtime
try:
    import onnxruntime as ort
    print(f"ONNX Runtime: {ort.__version__}")
    print(f"  Providers: {ort.get_available_providers()}")
except ImportError:
    print("ONNX Runtime: NOT INSTALLED")

# Optimum
try:
    import optimum
    print(f"Optimum: {optimum.__version__}")
except ImportError:
    print("Optimum: NOT INSTALLED")

# NumPy BLAS
import numpy as np
print(f"NumPy: {np.__version__}")

# OpenBLAS check
import os
print(f"\nEnvironment:")
print(f"  OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS', 'NOT SET')}")
print(f"  OPENBLAS_NUM_THREADS: {os.environ.get('OPENBLAS_NUM_THREADS', 'NOT SET')}")
print(f"  DNNL_MAX_CPU_ISA: {os.environ.get('DNNL_MAX_CPU_ISA', 'NOT SET')}")
PYEOF

echo ""
echo "=== Setup Complete ==="
echo "Disk I/O check:"
dd if=/dev/zero of=/tmp/disktest bs=1M count=256 oflag=direct 2>&1 | tail -1
rm -f /tmp/disktest
