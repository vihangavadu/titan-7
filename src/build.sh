#!/bin/bash
# TITAN V8.1 SINGULARITY - Master Build Script
# Compiles all C/eBPF components and verifies Python dependencies
set -e

TITAN_ROOT="$(cd "$(dirname "$0")" && pwd)"
CORE_DIR="${TITAN_ROOT}/core"
INSTALL_DIR="/opt/lucid-empire"

echo "╔══════════════════════════════════════════════╗"
echo "║  TITAN V8.1 SINGULARITY — Master Build      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Phase 1: Check build dependencies ───────────────────────
echo "[1/5] Checking build dependencies..."
MISSING=()

command -v gcc >/dev/null 2>&1 || MISSING+=("gcc")
command -v make >/dev/null 2>&1 || MISSING+=("make")
command -v clang >/dev/null 2>&1 || MISSING+=("clang")
command -v python3 >/dev/null 2>&1 || MISSING+=("python3")

KERNEL_VERSION=$(uname -r)
if [ ! -d "/lib/modules/${KERNEL_VERSION}/build" ]; then
    MISSING+=("linux-headers-${KERNEL_VERSION}")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  ERROR: Missing dependencies: ${MISSING[*]}"
    echo "  Install with: apt install ${MISSING[*]}"
    exit 1
fi
echo "  All build dependencies present."

# ─── Phase 2: Build kernel module ─────────────────────────────
echo ""
echo "[2/5] Building Hardware Shield kernel module..."
if [ -f "${CORE_DIR}/Makefile" ]; then
    cd "${CORE_DIR}"
    make clean 2>/dev/null || true
    make module
    if [ -f "${CORE_DIR}/hardware_shield_v6.ko" ]; then
        mkdir -p "${INSTALL_DIR}/hardware_shield"
        mkdir -p "${INSTALL_DIR}/kernel-modules"
        cp hardware_shield_v6.ko "${INSTALL_DIR}/hardware_shield/titan_hw.ko"
        cp hardware_shield_v6.ko "${INSTALL_DIR}/kernel-modules/titan_hw.ko"
        echo "  ✓ hardware_shield_v6.ko → ${INSTALL_DIR}/kernel-modules/titan_hw.ko"
    else
        echo "  ✗ Kernel module build failed"
    fi
else
    echo "  ✗ No Makefile found at ${CORE_DIR}/Makefile"
fi

# ─── Phase 3: Build eBPF programs ─────────────────────────────
echo ""
echo "[3/5] Building Network Shield eBPF programs..."
if [ -f "${CORE_DIR}/build_ebpf.sh" ]; then
    chmod +x "${CORE_DIR}/build_ebpf.sh"
    bash "${CORE_DIR}/build_ebpf.sh" build || echo "  ✗ eBPF build failed (non-fatal)"
else
    echo "  ✗ No build_ebpf.sh found"
fi

# ─── Phase 4: Verify Python dependencies ──────────────────────
echo ""
echo "[4/5] Verifying Python dependencies..."
PYTHON="python3"
REQ_FILE="${INSTALL_DIR}/requirements.txt"

if [ -f "${REQ_FILE}" ]; then
    # Check critical packages
    CRITICAL_PKGS=("PyQt6" "aiohttp" "numpy")
    for pkg in "${CRITICAL_PKGS[@]}"; do
        if ${PYTHON} -c "import ${pkg,,}" 2>/dev/null; then
            echo "  ✓ ${pkg}"
        else
            echo "  ✗ ${pkg} — install with: pip install ${pkg}"
        fi
    done
    
    # Check optional packages
    OPTIONAL_PKGS=("scipy" "onnxruntime" "openai" "aioquic")
    for pkg in "${OPTIONAL_PKGS[@]}"; do
        if ${PYTHON} -c "import ${pkg,,}" 2>/dev/null; then
            echo "  ✓ ${pkg} (optional)"
        else
            echo "  ○ ${pkg} (optional, not installed)"
        fi
    done
else
    echo "  No requirements.txt found at ${REQ_FILE}"
fi

# ─── Phase 5: Create directory structure ──────────────────────
echo ""
echo "[5/5] Ensuring directory structure..."
DIRS=(
    "${INSTALL_DIR}/profiles"
    "${INSTALL_DIR}/data"
    "${INSTALL_DIR}/logs"
    "${TITAN_ROOT}/assets/motions"
    "${TITAN_ROOT}/vpn"
    "/opt/titan/state"
    "/opt/titan/models"
    "/opt/titan/profiles"
    "/opt/titan/data"
    "/opt/titan/data/tx_monitor"
    "/opt/titan/data/services"
    "/opt/titan/data/target_discovery"
    "/opt/titan/data/intel_monitor"
    "/opt/titan/data/intel_monitor/sessions"
    "/opt/titan/data/intel_monitor/sessions/browser_profiles"
    "/opt/titan/data/intel_monitor/feed_cache"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "${dir}" 2>/dev/null && echo "  ✓ ${dir}" || echo "  ✗ ${dir} (permission denied)"
done

# ─── Summary ──────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Build Summary                               ║"
echo "╠══════════════════════════════════════════════╣"

if [ -f "${INSTALL_DIR}/kernel-modules/titan_hw.ko" ]; then
    echo "║  Kernel Module:  ✓ BUILT                    ║"
else
    echo "║  Kernel Module:  ✗ NOT BUILT                ║"
fi

if [ -f "${INSTALL_DIR}/ebpf/network_shield_v6.o" ]; then
    echo "║  eBPF Programs:  ✓ BUILT                    ║"
else
    echo "║  eBPF Programs:  ✗ NOT BUILT                ║"
fi

echo "║  Python Core:    ✓ SOURCE READY              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Install missing Python packages: pip install -r ${REQ_FILE}"
echo "  2. Install Camoufox browser (see docs)"
echo "  3. Load kernel module: sudo insmod ${INSTALL_DIR}/kernel-modules/titan_hw.ko"
echo "  4. Load eBPF: sudo bash ${CORE_DIR}/build_ebpf.sh load"
echo "  5. Launch: bash ${INSTALL_DIR}/launch-titan.sh"
