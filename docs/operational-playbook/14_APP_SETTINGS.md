# 14 — App: Settings (`app_settings.py`)

**Version:** V9.1 | **Accent:** Indigo `#6366f1` | **Tabs:** 6

---

## Overview

The Settings app is the **unified configuration hub** for all external tools and services that Titan OS depends on. Instead of editing config files manually, operators use this GUI to configure Mullvad VPN, Ollama AI, Redis, Xray, ntfy, Camoufox, API keys, and system environment variables.

Launched from the **middle-right card** in the 3×3 launcher grid.

---

## Tab 1: VPN

Configures Mullvad VPN and Xray relay.

| Field | Description |
|-------|-------------|
| **Mullvad Account** | Account number for Mullvad VPN authentication |
| **Relay Country** | WireGuard relay country selection |
| **Relay City** | Specific city within the selected country |
| **Obfuscation** | Enable/disable DAITA (Defense Against AI-guided Traffic Analysis) |
| **Xray Endpoint** | VLESS+Reality server address for Xray relay |
| **Xray UUID** | Client UUID for Xray authentication |

**Actions:**
- Connect / Disconnect Mullvad
- Test Xray relay connectivity
- Check IP reputation

---

## Tab 2: AI

Configures Ollama LLM inference and model routing.

| Field | Description |
|-------|-------------|
| **Ollama Endpoint** | URL of the Ollama API (default: `http://localhost:11434`) |
| **Active Models** | List of pulled models with size and status |
| **LLM Routing** | Task-to-model mapping from `llm_config.json` |

**Actions:**
- Pull new model
- Delete model
- Test inference speed
- Edit routing rules

**Default Model Routing:**
| Task | Model | Reason |
|------|-------|--------|
| Fast copilot | mistral:7b | Low latency (~10s) |
| BIN analysis | qwen2.5:7b | Structured JSON output |
| 3DS strategy | deepseek-r1:8b | Deep reasoning (~24s) |

---

## Tab 3: SERVICES

Start/stop/restart all external services from one panel.

| Service | systemd Unit | Default Port |
|---------|-------------|-------------|
| **Ollama** | ollama.service | 11434 |
| **Redis** | redis-server.service | 6379 |
| **Xray** | xray.service | 443 |
| **ntfy** | ntfy.service | 8090 |
| **Mullvad** | mullvad-daemon.service | — |

Each service shows:
- **Status dot** (green = running, red = stopped)
- **Start / Stop / Restart** buttons
- **Last log line** from journalctl

---

## Tab 4: BROWSER

Configures Camoufox anti-detect browser and extensions.

| Field | Description |
|-------|-------------|
| **Camoufox Path** | Path to Camoufox binary (default: `/opt/camoufox/`) |
| **Profiles Directory** | Where forged profiles are stored |
| **Ghost Motor Extension** | Path to Ghost Motor browser extension |
| **TX Monitor Extension** | Path to TX Monitor browser extension |
| **Default User-Agent** | Override UA string (optional) |

**Actions:**
- Verify Camoufox installation
- Open profiles directory
- Test extension loading

---

## Tab 5: API KEYS

Manages all external API keys and credentials stored in `titan.env`.

| Key | Purpose |
|-----|---------|
| **Proxy Provider** | IPRoyal / SOAX / Bright Data credentials |
| **Stripe Sandbox** | Test card validation endpoint |
| **OSINT APIs** | Shodan, VirusTotal, etc. |
| **Hostinger API** | VPS management token |
| **ntfy Topic** | Push notification topic name |

All keys are stored in `/opt/titan/titan.env` and loaded at runtime. The GUI masks sensitive values by default.

---

## Tab 6: SYSTEM

Raw environment editor and system diagnostics.

| Feature | Description |
|---------|-------------|
| **titan.env Editor** | Raw text editor for the environment file |
| **Python Packages** | List installed pip packages with versions |
| **Disk Usage** | Current disk space on VPS |
| **Version Info** | Titan OS version, Python version, OS version |
| **Diagnostics** | Run full system health check |

**Actions:**
- Save titan.env changes
- Run `pip list` refresh
- Export diagnostics report

---

## Operator Workflow

1. Open Settings from launcher (indigo card, row 2)
2. **First-time setup:** Enter Mullvad account in VPN tab, pull AI models in AI tab
3. **Before operations:** Check SERVICES tab — ensure Ollama, Redis are running
4. **API keys:** Add proxy provider credentials in API KEYS tab
5. **Browser config:** Verify Camoufox path in BROWSER tab
6. Settings persist in `titan.env` across restarts
