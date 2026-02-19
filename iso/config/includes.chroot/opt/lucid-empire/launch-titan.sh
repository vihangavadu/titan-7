#!/bin/bash
# =============================================================================
# LUCID EMPIRE TITAN - Main Launcher (No-Fork Edition)
# =============================================================================
# ARCHITECTURE: Naked Browser Protocol
# - Standard Firefox ESR / Chromium with Kernel-Level Hardware Masking
# - No forked browsers - true sovereignty
# - NO LD_PRELOAD - Hardware masking via kernel module (Ring-0)
# =============================================================================

set -e

TITAN_HOME="/opt/lucid-empire"
TITAN_DATA="${HOME}/.lucid-empire"
KERNEL_MODULE=""
# Search for kernel module in known locations
for kmod_path in \
    "/opt/lucid-empire/kernel-modules/titan_hw.ko" \
    "/opt/lucid-empire/hardware_shield/titan_hw.ko" \
    "/opt/titan/core/hardware_shield_v6.ko"; do
    if [[ -f "${kmod_path}" ]]; then
        KERNEL_MODULE="${kmod_path}"
        break
    fi
done
LOG_DIR="${TITAN_DATA}/logs"
VENV_PATH="${TITAN_HOME}/venv"

# Create data directories
mkdir -p "${TITAN_DATA}"/{profiles,logs,cache,commerce_vault}

# Initialize logging
LOG_FILE="${LOG_DIR}/titan-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=============================================="
echo "  LUCID EMPIRE V7.0-TITAN SINGULARITY (No-Fork Edition)"
echo "  Architecture: Naked Browser Protocol"
echo "  Hardware Masking: Kernel Module (Ring-0)"
echo "  Starting Console..."
echo "=============================================="
echo ""
echo "[$(date)] TITAN Console starting..."
echo "[$(date)] Data directory: ${TITAN_DATA}"
echo "[$(date)] Log file: ${LOG_FILE}"

# Check for Kernel Module (Hardware Shield V7)
if lsmod | grep -q titan_hw; then
    echo "[$(date)] ✓ Kernel Hardware Masking: ACTIVE"
    echo "[$(date)] ✓ Zero-Detect Protocol: OPERATIONAL"
elif [[ -n "${KERNEL_MODULE}" ]]; then
    echo "[$(date)] ⚠ Kernel Module found at: ${KERNEL_MODULE}"
    echo "[$(date)]   Attempting to load..."
    if sudo insmod "${KERNEL_MODULE}" 2>/dev/null; then
        echo "[$(date)] ✓ Kernel Module loaded successfully"
    else
        echo "[$(date)] ⚠ Could not load module (try: sudo insmod ${KERNEL_MODULE})"
    fi
else
    echo "[$(date)] ⚠ Kernel Module not found in any search path"
    echo "[$(date)]   Build with: cd /opt/titan/core && make install"
fi

# Verify NO LD_PRELOAD (security check)
if [[ -n "${LD_PRELOAD}" ]]; then
    echo "[$(date)] ⚠ WARNING: LD_PRELOAD detected: ${LD_PRELOAD}"
    echo "[$(date)] This may indicate userspace interception (detectable)"
    echo "[$(date)] Kernel module should handle all masking"
fi

# Check for eBPF capabilities
if [[ -f /sys/kernel/btf/vmlinux ]]; then
    echo "[$(date)] BTF available - eBPF features enabled"
else
    echo "[$(date)] WARNING: BTF not available, eBPF features may be limited"
fi

# Set environment variables
export TITAN_HOME
export TITAN_DATA
export PYTHONDONTWRITEBYTECODE=1
export QT_AUTO_SCREEN_SCALE_FACTOR=1

# libfaketime setup (activated per-profile)
export FAKETIME_DONT_FAKE_MONOTONIC=1
export FAKETIME_NO_CACHE=1

# Determine Python path
if [[ -d "${VENV_PATH}" ]] && [[ -f "${VENV_PATH}/bin/python3" ]]; then
    PYTHON="${VENV_PATH}/bin/python3"
    echo "[$(date)] Using venv Python: ${PYTHON}"
else
    PYTHON="python3"
    echo "[$(date)] Using system Python: ${PYTHON}"
fi

# Launch TITAN V7.0 Unified Operation Center
cd /opt/titan/apps
echo "[$(date)] Launching TITAN V7.0 Unified Operation Center..."
exec "${PYTHON}" /opt/titan/apps/app_unified.py "$@"
