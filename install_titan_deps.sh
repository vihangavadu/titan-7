#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN X V10.0 — Full Dependency Installer
# Installs ALL Python + system dependencies for 106 core modules + 11 GUI apps
# Run on: Debian 12 (local or VPS)
# ═══════════════════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
log() { echo -e "${CYAN}[TITAN]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC} $1"; }

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  TITAN X V10.0 — Full Dependency Installer"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─── System packages ─────────────────────────────────────────────────────
log "Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-dev python3-venv \
    libleveldb-dev \
    ffmpeg \
    espeak-ng \
    libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0 libxcb-icccm4 \
    libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 libxcb-xkb1 \
    libxcb-image0 \
    curl wget git jq \
    2>/dev/null
ok "System packages installed"

# ─── Python packages (all 106 modules) ──────────────────────────────────
log "Installing Python packages..."
pip3 install --break-system-packages -q \
    flask==3.1.3 \
    flask-cors==6.0.2 \
    aiohttp==3.13.3 \
    aioquic==1.3.0 \
    scipy==1.17.1 \
    chromadb==1.5.2 \
    curl_cffi==0.14.0 \
    python-dateutil==2.9.0.post0 \
    langchain==1.2.10 \
    langchain-core==1.2.16 \
    langchain-ollama==1.0.1 \
    plyvel==1.5.1 \
    onnxruntime==1.24.2 \
    PyQt6==6.10.2 \
    pydantic==2.12.5 \
    ollama==0.6.1 \
    mmh3==5.2.0 \
    flatbuffers==25.12.19 \
    cryptography==46.0.5 \
    2>/dev/null
ok "Python packages installed"

# ─── Ollama (AI inference) ───────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    log "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    ok "Ollama installed"
else
    ok "Ollama already installed ($(ollama --version 2>/dev/null || echo 'unknown'))"
fi

# ─── PYTHONPATH setup ────────────────────────────────────────────────────
TITAN_ROOT="${TITAN_ROOT:-/opt/titan}"
PROFILE_FILE="/etc/profile.d/titan.sh"
if [ -d "$TITAN_ROOT/src" ]; then
    log "Setting up PYTHONPATH in $PROFILE_FILE..."
    cat > "$PROFILE_FILE" << EOF
# TITAN X V10.0 environment
export TITAN_ROOT="$TITAN_ROOT"
export PYTHONPATH="$TITAN_ROOT/src:$TITAN_ROOT/src/core:$TITAN_ROOT/src/apps:\$PYTHONPATH"
EOF
    chmod +x "$PROFILE_FILE"
    ok "PYTHONPATH configured"
fi

# ─── Verify ──────────────────────────────────────────────────────────────
log "Verifying module imports..."
export PYTHONPATH="$TITAN_ROOT/src:$TITAN_ROOT/src/core:$TITAN_ROOT/src/apps"

TOTAL=0
PASS=0
FAIL_LIST=""

for mod in genesis_core cerberus_core cerberus_enhanced ai_intelligence_engine \
    purchase_history_engine indexeddb_lsng_synthesis first_session_bias_eliminator \
    chromium_commerce_injector forensic_synthesis_engine font_sanitizer \
    audio_hardener profile_realism_engine chromium_cookie_engine leveldb_writer \
    three_ds_strategy target_intelligence target_presets target_discovery \
    preflight_validator payment_preflight payment_sandbox_tester \
    proxy_manager timezone_enforcer location_spoofer_linux \
    advanced_profile_generator persona_enrichment_engine form_autofill_injector \
    dynamic_data fingerprint_injector canvas_noise canvas_subpixel_shim \
    webgl_angle usb_peripheral_synth windows_font_provisioner \
    kyc_core kyc_enhanced kyc_voice_engine waydroid_sync \
    cognitive_core tof_depth_synthesis verify_deep_identity \
    titan_realtime_copilot titan_vector_memory titan_web_intel \
    titan_detection_analyzer titan_ai_operations_guard titan_detection_lab \
    ollama_bridge titan_onnx_engine \
    mullvad_vpn lucid_vpn network_shield network_shield_loader \
    network_jitter quic_proxy tls_parrot tls_mimic \
    forensic_monitor forensic_cleaner forensic_alignment \
    kill_switch immutable_os cpuid_rdtsc_shield \
    titan_services titan_env integration_bridge cockpit_daemon \
    titan_master_verify titan_operation_logger bug_patch_bridge \
    titan_automation_orchestrator titan_autonomous_engine mcp_interface \
    titan_session titan_theme titan_enterprise_theme \
    transaction_monitor payment_success_metrics \
    cookie_forge ga_triangulation time_dilator profile_burner \
    journey_simulator temporal_entropy handover_protocol \
    titan_self_hosted_stack ntp_isolation \
    oblivion_forge multilogin_forge antidetect_importer \
    profile_isolation referrer_warmup \
    issuer_algo_defense tra_exemption_engine \
    ghost_motor_v6 titan_agent_chain \
    ja4_permutation_engine gamp_triangulation_v2 \
    titan_3ds_ai_exploits titan_master_automation \
    biometric_mimicry intel_monitor \
    generate_trajectory_model titan_webhook_integrations \
    titan_auto_patcher time_safety_validator; do
    TOTAL=$((TOTAL + 1))
    if python3 -c "import $mod" 2>/dev/null; then
        PASS=$((PASS + 1))
    else
        FAIL_LIST="$FAIL_LIST $mod"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  TITAN X V10.0 — Installation Complete"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo -e "  Core modules: ${GREEN}$PASS/$TOTAL${NC} imported OK"
if [ -n "$FAIL_LIST" ]; then
    echo -e "  ${RED}Failed:${NC}$FAIL_LIST"
fi
echo ""
echo "  System: $(python3 --version) | $(pip3 --version | cut -d' ' -f1-2)"
echo "  Ollama: $(ollama --version 2>/dev/null || echo 'not installed')"
echo "  PyQt6:  $(python3 -c 'import PyQt6; print(PyQt6.__name__)' 2>/dev/null || echo 'not installed')"
echo ""
