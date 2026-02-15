#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V7.0.3 — CLEANUP SCRIPT
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# PURPOSE: Clean unnecessary files from titan-main directory
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.0.3 — Cleanup Script                              ║"
echo "║  Authority: Dva.12 | Status: OBLIVION_ACTIVE               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get initial file count
INITIAL_FILES=$(find . -type f 2>/dev/null | wc -l)
INITIAL_SIZE=$(du -sh . 2>/dev/null | cut -f1)

echo "Initial state:"
echo "  Files: $INITIAL_FILES"
echo "  Size: $INITIAL_SIZE"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: CLEAN BUILD ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════
echo "[1/6] Cleaning build artifacts..."

# Clean live-build cache
if [ -d "iso/.build" ]; then
    echo "  [*] Cleaning live-build cache..."
    rm -rf iso/.build
fi

if [ -d "iso/cache" ]; then
    echo "  [*] Cleaning package cache..."
    rm -rf iso/cache
fi

if [ -d "iso/chroot" ]; then
    echo "  [*] Cleaning chroot directory..."
    rm -rf iso/chroot
fi

# Clean build logs
if [ -f "iso/build.log" ]; then
    echo "  [*] Removing build log..."
    rm -f iso/build.log
fi

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: CLEAN PYTHON CACHE
# ═══════════════════════════════════════════════════════════════════════════
echo "[2/6] Cleaning Python cache..."

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: CLEAN TEMPORARY FILES
# ═══════════════════════════════════════════════════════════════════════════
echo "[3/6] Cleaning temporary files..."

find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: CLEAN LOG FILES
# ═══════════════════════════════════════════════════════════════════════════
echo "[4/6] Cleaning log files..."

find . -name "*.log" -delete 2>/dev/null || true
find . -name "*.log.*" -delete 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: CLEAN DEVELOPMENT ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════
echo "[5/6] Cleaning development artifacts..."

# Remove old ISO files
find . -name "*.iso" -delete 2>/dev/null || true
find . -name "*.iso.sha256" -delete 2>/dev/null || true
find . -name "*.iso.md5" -delete 2>/dev/null || true

# Remove old lucid-titan files (if any)
find . -name "lucid-titan*.iso*" -delete 2>/dev/null || true

# Remove test artifacts
if [ -d "tests/__pycache__" ]; then
    rm -rf tests/__pycache__
fi

if [ -f ".coverage" ]; then
    rm -f .coverage
fi

if [ -f "pytest.log" ]; then
    rm -f pytest.log
fi

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: CLEAN DUPLICATE/OLD FILES
# ═══════════════════════════════════════════════════════════════════════════
echo "[6/6] Checking for duplicate/old files..."

# Remove duplicate build scripts (keep only the latest)
echo "  [*] Checking for duplicate build scripts..."
BUILD_SCRIPTS=("build_docker.sh" "build_docker.ps1" "build_docker.bat" "build_simple.bat" "build_direct.bat")

# Keep the main ones, remove duplicates
for script in "${BUILD_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "    Keeping: $script"
    fi
done

# Remove old verification scripts if we have newer ones
if [ -f "verify_titan_features.py" ] && [ -f "verify_storage_structure.py" ]; then
    echo "  [*] Keeping verification scripts"
fi

# ═══════════════════════════════════════════════════════════════════════════
# FINAL RESULTS
# ═══════════════════════════════════════════════════════════════════════════
FINAL_FILES=$(find . -type f 2>/dev/null | wc -l)
FINAL_SIZE=$(du -sh . 2>/dev/null | cut -f1)
FILES_REMOVED=$((INITIAL_FILES - FINAL_FILES))

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  CLEANUP COMPLETE                                          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Initial files: $INITIAL_FILES                                ║"
echo "║  Final files:   $FINAL_FILES                                  ║"
echo "║  Files removed: $FILES_REMOVED                                ║"
echo "║  Initial size:  $INITIAL_SIZE                                ║"
echo "║  Final size:    $FINAL_SIZE                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "Essential files preserved:"
echo "  ✓ Core modules (iso/config/includes.chroot/opt/titan/core/)"
echo "  ✓ Build configuration (iso/config/)"
echo "  ✓ Profile generator (profgen/)"
echo "  ✓ Build scripts (build_*.sh, build_*.ps1, build_*.bat)"
echo "  ✓ Documentation (*.md)"
echo "  ✓ Finalization script (iso/finalize_titan.sh)"
echo ""

echo "Ready for Docker build!"
