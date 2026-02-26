#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TITAN OS — OpenCode + Oh-My-OpenCode + Titan Skill Installer
# Installs on VPS (187.77.186.252) via XRDP/SSH
#
# Usage:
#   bash install_opencode_omo.sh
#
# What this does:
#   1. Installs Bun (JS runtime required by OpenCode + OmO)
#   2. Installs OpenCode CLI (terminal-based AI coding IDE)
#   3. Installs Oh-My-OpenCode plugin via bunx
#   4. Creates the Titan skill for OmO (connects to Dev Hub APIs)
#   5. Creates an opencode.json config wired to local Ollama
#   6. Creates desktop shortcut (XFCE)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

TITAN_ROOT="${TITAN_ROOT:-/root/workspace/titan-7}"
OPENCODE_CONFIG_DIR="$HOME/.config/opencode"
SKILL_DIR="$OPENCODE_CONFIG_DIR/skills/titan"
DEV_HUB_URL="http://localhost:8877"
LOG_FILE="/tmp/install_opencode_omo.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
ok()  { echo -e "\e[32m✓\e[0m $*" | tee -a "$LOG_FILE"; }
err() { echo -e "\e[31m✗\e[0m $*" | tee -a "$LOG_FILE"; }

log "═══ TITAN OpenCode + Oh-My-OpenCode Installer ═══"
log "Log: $LOG_FILE"

# ─── 1. Install Bun ───────────────────────────────────────────────────────────
log "Step 1: Installing Bun..."
if command -v bun &>/dev/null; then
    ok "Bun already installed: $(bun --version)"
else
    curl -fsSL https://bun.sh/install | bash
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
    echo 'export BUN_INSTALL="$HOME/.bun"' >> "$HOME/.bashrc"
    echo 'export PATH="$BUN_INSTALL/bin:$PATH"' >> "$HOME/.bashrc"
    ok "Bun installed: $(bun --version)"
fi

export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$BUN_INSTALL/bin:$PATH"

# ─── 2. Install Node.js (OpenCode dependency) ─────────────────────────────────
log "Step 2: Ensuring Node.js..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    ok "Node.js installed: $(node --version)"
else
    ok "Node.js already present: $(node --version)"
fi

# ─── 3. Install OpenCode CLI ──────────────────────────────────────────────────
log "Step 3: Installing OpenCode CLI..."
if command -v opencode &>/dev/null; then
    OPENCODE_VER=$(opencode --version 2>/dev/null || echo "unknown")
    ok "OpenCode already installed: $OPENCODE_VER"
else
    # Install via npm (official distribution)
    npm install -g opencode-ai 2>>"$LOG_FILE" || {
        log "npm install failed, trying bun..."
        bun install -g opencode-ai 2>>"$LOG_FILE"
    }
    if command -v opencode &>/dev/null; then
        ok "OpenCode installed: $(opencode --version)"
    else
        err "OpenCode install failed. Check $LOG_FILE"
        log "Attempting direct binary install..."
        curl -fsSL https://opencode.ai/install | bash 2>>"$LOG_FILE" || true
    fi
fi

# ─── 4. Create OpenCode config directory ─────────────────────────────────────
log "Step 4: Creating OpenCode config..."
mkdir -p "$OPENCODE_CONFIG_DIR"
mkdir -p "$SKILL_DIR"

# ─── 5. Write opencode.json (wired to local Ollama + OmO plugin) ─────────────
log "Step 5: Writing opencode.json..."
cat > "$OPENCODE_CONFIG_DIR/opencode.json" <<'OPENCODE_JSON'
{
  "plugin": [
    "oh-my-opencode"
  ],
  "model": "ollama/deepseek-r1:8b",
  "provider": {
    "ollama": {
      "models": {
        "deepseek-r1:8b": {
          "name": "deepseek-r1:8b",
          "limit": 8192
        },
        "qwen2.5:7b": {
          "name": "qwen2.5:7b",
          "limit": 8192
        },
        "mistral:7b": {
          "name": "mistral:7b",
          "limit": 8192
        },
        "titan-strategist": {
          "name": "titan-strategist",
          "limit": 8192
        },
        "titan-analyst": {
          "name": "titan-analyst",
          "limit": 8192
        },
        "titan-fast": {
          "name": "titan-fast",
          "limit": 8192
        }
      }
    }
  },
  "keybinds": {
    "leader": "ctrl+o"
  }
}
OPENCODE_JSON
ok "opencode.json written"

# ─── 6. Write oh-my-opencode.json (agent model overrides for local Ollama) ───
log "Step 6: Writing oh-my-opencode.json agent overrides..."
cat > "$OPENCODE_CONFIG_DIR/oh-my-opencode.json" <<'OMO_JSON'
{
  "agents": {
    "sisyphus":   { "model": "ollama/deepseek-r1:8b" },
    "prometheus": { "model": "ollama/deepseek-r1:8b" },
    "hephaestus": { "model": "ollama/qwen2.5:7b" },
    "atlas":      { "model": "ollama/mistral:7b" }
  }
}
OMO_JSON
ok "oh-my-opencode.json written"

# ─── 7. Install Oh-My-OpenCode plugin ─────────────────────────────────────────
log "Step 7: Installing Oh-My-OpenCode plugin..."
if bunx oh-my-opencode --version &>/dev/null 2>&1; then
    ok "oh-my-opencode already accessible via bunx"
else
    bunx oh-my-opencode install \
        --no-tui \
        --claude=no \
        --gemini=no \
        --copilot=no \
        2>>"$LOG_FILE" || {
        log "OmO install via CLI failed, plugin registered in opencode.json directly"
    }
    ok "Oh-My-OpenCode plugin registered"
fi

# ─── 8. Write Titan SKILL.md ──────────────────────────────────────────────────
log "Step 8: Writing Titan skill..."
cat > "$SKILL_DIR/SKILL.md" <<SKILL_EOF
# Titan OS Development Skill

## Purpose
This skill gives you full control over the Titan OS platform running on this VPS.
You can scan the codebase, run AI pipelines, control services, and deploy changes
via the Titan Dev Hub API at ${DEV_HUB_URL}.

## Dev Hub API
Base URL: ${DEV_HUB_URL}
All endpoints return JSON with \`ok: true/false\`.

### Key Endpoints

**AI Agents (OmO-style):**
- POST /api/agents/ultrawork — Full auto orchestration (Sisyphus → parallel subtasks)
- POST /api/agents/prometheus/interview — Prometheus planning interview
- POST /api/agents/start-work — Execute a Prometheus plan
- POST /api/agents/single — Invoke one agent directly
- GET  /api/agents/profiles — List agent profiles and models

**System Operations:**
- POST /api/scan/full — Scan all Python modules for syntax errors
- POST /api/scan/paths — Scan specific paths
- GET  /api/ops/services — List systemd services
- POST /api/ops/services/action — start/stop/restart/status a service
- POST /api/ops/verify — Run a verification script
- GET  /api/ops/ai-model-assignments — Show LLM task routing

**File Operations:**
- GET  /api/file?path=<path> — Read a file
- POST /api/file/save — Write a file with backup + syntax validation
- GET  /api/files?root=<dir> — List files in a directory

**AI Chat:**
- POST /api/ai/chat — Single provider or ensemble (Windsurf+Copilot)

**Infrastructure:**
- GET  /api/hostinger/vps — VPS status via Hostinger API
- GET  /api/git/status — Git status

## Titan Root
/root/workspace/titan-7/

## Key Paths
- Core modules:  /root/workspace/titan-7/src/core/
- GUI apps:      /root/workspace/titan-7/src/apps/
- Config:        /root/workspace/titan-7/src/config/
- Dev Hub:       /root/workspace/titan-7/iso/config/includes.chroot/opt/titan/apps/titan_dev_hub.py
- LLM config:    /root/workspace/titan-7/src/config/llm_config.json

## Services
- titan-dev-hub  (port 8877) — This IDE
- ollama         (port 11434) — Local LLM inference
- redis-server   (port 6379) — Session/cache
- xray                        — Network proxy
- ntfy           (port 8084) — Push notifications

## Ollama Models
- deepseek-r1:8b  → Deep reasoning (strategist/planner)
- qwen2.5:7b      → Structured analysis (analyst)
- mistral:7b      → Fast execution (operator)
- titan-strategist, titan-analyst, titan-fast → Custom fine-tuned models

## Instructions for Agent
1. When modifying Titan OS files, ALWAYS use /api/file/save (creates backup + validates syntax)
2. After modifying services, restart via /api/ops/services/action
3. After modifying titan_dev_hub.py, restart titan-dev-hub service
4. Use ultrawork for complex multi-step tasks
5. Use Prometheus mode for tasks requiring upfront planning
6. Always verify after changes: POST /api/scan/full
SKILL_EOF
ok "Titan SKILL.md written to $SKILL_DIR/SKILL.md"

# ─── 9. Create XFCE desktop shortcut ─────────────────────────────────────────
log "Step 9: Creating desktop shortcut..."
DESKTOP_DIR="$HOME/Desktop"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/opencode.desktop" <<DESK_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=OpenCode (Titan)
Comment=OpenCode AI IDE with Oh-My-OpenCode + Titan Skill
Exec=bash -c 'cd /root/workspace/titan-7 && opencode'
Icon=utilities-terminal
Terminal=true
Categories=Development;IDE;
DESK_EOF
chmod +x "$DESKTOP_DIR/opencode.desktop"
ok "Desktop shortcut created"

# ─── 10. Create launch wrapper ────────────────────────────────────────────────
log "Step 10: Creating launch wrapper..."
cat > /usr/local/bin/titan-opencode <<'WRAPPER_EOF'
#!/usr/bin/env bash
# Launch OpenCode with Titan workspace
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$BUN_INSTALL/bin:$PATH"
cd "${TITAN_ROOT:-/root/workspace/titan-7}"
exec opencode "$@"
WRAPPER_EOF
chmod +x /usr/local/bin/titan-opencode
ok "Launch wrapper: titan-opencode"

# ─── 11. Generate AGENTS.md in Titan workspace ───────────────────────────────
log "Step 11: Writing AGENTS.md to Titan workspace..."
cat > "${TITAN_ROOT}/AGENTS.md" <<'AGENTS_EOF'
# AGENTS.md — Titan OS Development Context

## Project
Titan OS: A Python-based autonomous operations platform deployed on a Debian 12 VPS.
- Core: 115+ Python modules in src/core/
- GUI: PyQt5 desktop apps in src/apps/
- Web IDE: Flask-based Dev Hub at port 8877
- Config: JSON configs in src/config/

## Architecture
- titan_api.py      — 59 REST API endpoints
- integration_bridge.py — Central subsystem registry (69 subsystems)
- titan_session.py  — Redis pub/sub session manager
- llm_config.json   — AI task routing (57 tasks → 3 models)
- titan_dev_hub.py  — Web IDE with discipline agents

## Discipline Agents (Oh-My-OpenCode style)
- **Sisyphus**   — Orchestrator → deepseek-r1:8b. Decomposes and drives complex tasks.
- **Prometheus** — Planner → deepseek-r1:8b. Interviews and builds verified plans.
- **Hephaestus** — Deep Worker → qwen2.5:7b. Full implementations end-to-end.
- **Atlas**      — Executor → mistral:7b. Specific, well-defined task execution.

## Dev Hub API
http://localhost:8877/api/...
Use /api/agents/ultrawork for complex tasks. Use /api/file/save to edit files safely.

## Critical Rules
1. Never edit /etc/passwd, /etc/shadow, /etc/sudoers directly
2. Always use /api/file/save for Titan files (creates backups, validates Python syntax)
3. Restart titan-dev-hub after editing titan_dev_hub.py:
   systemctl restart titan-dev-hub
4. Run /api/scan/full after major changes to verify no syntax errors
AGENTS_EOF
ok "AGENTS.md written"

# ─── 12. Verify ──────────────────────────────────────────────────────────────
log ""
log "═══ Installation Summary ═══"

check() {
    if command -v "$1" &>/dev/null; then
        ok "$1: $(command -v $1)"
    else
        err "$1: NOT FOUND"
    fi
}

check bun
check node
check opencode || log "  Note: opencode may need PATH reload — run: source ~/.bashrc"

log ""
log "Config files:"
[ -f "$OPENCODE_CONFIG_DIR/opencode.json" ]      && ok "  opencode.json"      || err "  opencode.json missing"
[ -f "$OPENCODE_CONFIG_DIR/oh-my-opencode.json" ] && ok "  oh-my-opencode.json" || err "  oh-my-opencode.json missing"
[ -f "$SKILL_DIR/SKILL.md" ]                      && ok "  Titan SKILL.md"     || err "  Titan SKILL.md missing"
[ -f "${TITAN_ROOT}/AGENTS.md" ]                  && ok "  AGENTS.md"           || err "  AGENTS.md missing"
[ -f "/usr/local/bin/titan-opencode" ]            && ok "  titan-opencode cmd"  || err "  titan-opencode missing"

log ""
log "To launch: titan-opencode"
log "Or in terminal: cd /root/workspace/titan-7 && opencode"
log ""
log "Done. Full log: $LOG_FILE"
