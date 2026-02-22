#!/bin/bash
#
# TITAN OS — OSINT Tools Installation Script
# ═══════════════════════════════════════════════════════════════════════════
#
# Installs self-hosted OSINT tools for persona enrichment engine.
# All tools are OPTIONAL — Titan works without them.
#
# Tools installed:
#   1. Sherlock — GitHub username → social profiles
#   2. Holehe — Email → registered accounts
#   3. Maigret — Username → 2500+ sites
#   4. theHarvester — Email → public data sources
#   5. Photon — Web scraper for person data
#
# Usage:
#   sudo ./install_osint_tools.sh [all|minimal|custom]
#
# Modes:
#   all      — Install all 5 tools (recommended)
#   minimal  — Install only Sherlock + Holehe (fastest)
#   custom   — Interactive selection
#
# Version: 8.1.0
# ═══════════════════════════════════════════════════════════════════════════

set -e

INSTALL_DIR="/opt/titan/osint_tools"
MODE="${1:-all}"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "  TITAN OS — OSINT Tools Installation"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo "Mode: $MODE"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERROR: This script must be run as root (sudo)"
    exit 1
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# ═══════════════════════════════════════════════════════════════════════════
# INSTALL DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════

echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip git curl wget > /dev/null 2>&1
echo "✅ System dependencies installed"

# ═══════════════════════════════════════════════════════════════════════════
# TOOL INSTALLATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

install_sherlock() {
    echo "[2/6] Installing Sherlock (username → social profiles)..."
    if [ -d "sherlock" ]; then
        echo "⏭️  Sherlock already installed"
        return
    fi
    
    git clone https://github.com/sherlock-project/sherlock.git > /dev/null 2>&1
    cd sherlock
    python3 -m pip install -r requirements.txt > /dev/null 2>&1
    cd ..
    echo "✅ Sherlock installed"
}

install_holehe() {
    echo "[3/6] Installing Holehe (email → registered accounts)..."
    if [ -d "holehe" ]; then
        echo "⏭️  Holehe already installed"
        return
    fi
    
    git clone https://github.com/megadose/holehe.git > /dev/null 2>&1
    cd holehe
    python3 -m pip install -r requirements.txt > /dev/null 2>&1
    python3 setup.py install > /dev/null 2>&1
    cd ..
    echo "✅ Holehe installed"
}

install_maigret() {
    echo "[4/6] Installing Maigret (username → 2500+ sites)..."
    if [ -d "maigret" ]; then
        echo "⏭️  Maigret already installed"
        return
    fi
    
    git clone https://github.com/soxoj/maigret.git > /dev/null 2>&1
    cd maigret
    python3 -m pip install -r requirements.txt > /dev/null 2>&1
    cd ..
    echo "✅ Maigret installed"
}

install_theharvester() {
    echo "[5/6] Installing theHarvester (email → public data)..."
    if [ -d "theHarvester" ]; then
        echo "⏭️  theHarvester already installed"
        return
    fi
    
    git clone https://github.com/laramies/theHarvester.git > /dev/null 2>&1
    cd theHarvester
    python3 -m pip install -r requirements/base.txt > /dev/null 2>&1
    cd ..
    echo "✅ theHarvester installed"
}

install_photon() {
    echo "[6/6] Installing Photon (web scraper)..."
    if [ -d "Photon" ]; then
        echo "⏭️  Photon already installed"
        return
    fi
    
    git clone https://github.com/s0md3v/Photon.git > /dev/null 2>&1
    cd Photon
    python3 -m pip install -r requirements.txt > /dev/null 2>&1
    cd ..
    echo "✅ Photon installed"
}

# ═══════════════════════════════════════════════════════════════════════════
# INSTALLATION LOGIC
# ═══════════════════════════════════════════════════════════════════════════

case "$MODE" in
    all)
        echo "Installing ALL tools..."
        install_sherlock
        install_holehe
        install_maigret
        install_theharvester
        install_photon
        ;;
    
    minimal)
        echo "Installing MINIMAL tools (Sherlock + Holehe)..."
        install_sherlock
        install_holehe
        ;;
    
    custom)
        echo "Custom installation mode:"
        echo ""
        read -p "Install Sherlock? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_sherlock
        fi
        
        read -p "Install Holehe? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_holehe
        fi
        
        read -p "Install Maigret? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_maigret
        fi
        
        read -p "Install theHarvester? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_theharvester
        fi
        
        read -p "Install Photon? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_photon
        fi
        ;;
    
    *)
        echo "❌ ERROR: Invalid mode '$MODE'"
        echo "Usage: $0 [all|minimal|custom]"
        exit 1
        ;;
esac

# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  Installation Complete"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Installed tools:"
[ -d "sherlock" ] && echo "  ✅ Sherlock"
[ -d "holehe" ] && echo "  ✅ Holehe"
[ -d "maigret" ] && echo "  ✅ Maigret"
[ -d "theHarvester" ] && echo "  ✅ theHarvester"
[ -d "Photon" ] && echo "  ✅ Photon"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
echo "To enable OSINT enrichment in Titan:"
echo "  1. Edit persona_enrichment_engine.py"
echo "  2. Set enable_osint=True when creating PersonaEnrichmentEngine"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
