#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# TITAN V7.0 SINGULARITY — One-Shot Cloud ISO Builder
# ══════════════════════════════════════════════════════════════════════════════
# Run this on a fresh Debian 12 / Ubuntu 22.04+ VPS with root access.
#
# USAGE:
#   1. Spin up a Debian 12 VPS on Kamatera (or any provider)
#      - 4 CPU, 8GB RAM, 40GB disk minimum
#      - Debian 12 (Bookworm) x86_64
#
#   2. SSH into the VPS and run:
#      apt-get update && apt-get install -y git
#      git clone <YOUR_REPO_URL> /root/titan-main
#      cd /root/titan-main
#      bash scripts/cloud_build.sh
#
#   OR upload the repo via SCP:
#      scp -r "C:\Users\Administrator\Desktop\final lucid\titan-main" root@<VPS_IP>:/root/titan-main
#      ssh root@<VPS_IP> "cd /root/titan-main && bash scripts/cloud_build.sh"
#
#   3. After build completes (~30-90 min), download the ISO:
#      scp root@<VPS_IP>:/root/titan-main/lucid-titan-v7.0-singularity.iso .
#
# ══════════════════════════════════════════════════════════════════════════════

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[TITAN]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }
hdr()  {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
}

# ── Pre-flight ────────────────────────────────────────────────────────────────

hdr "TITAN V7.0 SINGULARITY — Cloud ISO Builder"

if [ "$EUID" -ne 0 ]; then
    err "Must run as root. Use: sudo bash scripts/cloud_build.sh"
    exit 1
fi

# Detect repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/../iso" ]; then
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"
elif [ -d "./iso" ]; then
    REPO_ROOT="$(pwd)"
else
    err "Cannot find repo root. Run from titan-main/ directory."
    exit 1
fi

cd "$REPO_ROOT"
log "Repo root: $REPO_ROOT"

# Check disk space
AVAIL_GB=$(df --output=avail / | tail -1 | awk '{print int($1/1048576)}')
log "Disk available: ${AVAIL_GB} GB"
if [ "$AVAIL_GB" -lt 15 ]; then
    err "Need at least 15 GB free. Only ${AVAIL_GB} GB available."
    exit 1
fi

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log "Host OS: $PRETTY_NAME"
else
    warn "Cannot detect host OS"
fi

# ── Run the main build script ────────────────────────────────────────────────

hdr "Delegating to build_iso.sh..."

if [ -f "scripts/build_iso.sh" ]; then
    chmod +x scripts/build_iso.sh
    exec bash scripts/build_iso.sh
else
    err "scripts/build_iso.sh not found!"
    exit 1
fi
