# 18 — External Software Guide

**Version:** V8.2.2 | **Updated:** 2026-02-23

---

## Overview

Titan OS V8.2.2 depends on 10 external software packages. This guide covers installation, configuration, and verification for each.

All external tools are configurable via the **Settings app** (`app_settings.py`).

---

## 1. Ollama (LLM Inference)

| Property | Value |
|----------|-------|
| **Version** | 0.16.3 |
| **Service** | ollama.service |
| **Port** | 11434 |
| **Models** | 6 (mistral:7b, qwen2.5:7b, deepseek-r1:8b + 3 custom) |
| **Disk Usage** | ~15 GB for all models |

### Installation
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull Models
```bash
ollama pull mistral:7b
ollama pull qwen2.5:7b
ollama pull deepseek-r1:8b
```

### Verify
```bash
systemctl status ollama
curl http://localhost:11434/api/tags
```

### Configuration
- Model routing defined in `/opt/titan/llm_config.json`
- 20 task-routing entries map AI functions to optimal models
- Configurable via Settings → AI tab

---

## 2. Camoufox (Anti-Detect Browser)

| Property | Value |
|----------|-------|
| **Version** | 0.4.11 |
| **Path** | /opt/camoufox/ |
| **Based On** | Firefox ESR (modified) |

### Installation
```bash
pip install camoufox
python -m camoufox fetch
```

### Verify
```bash
python -c "import camoufox; print(camoufox.__version__)"
```

### Configuration
- Browser path configurable via Settings → BROWSER tab
- Extensions (Ghost Motor, TX Monitor) loaded at launch
- Profile directory: `/opt/titan/profiles/`

---

## 3. Mullvad VPN

| Property | Value |
|----------|-------|
| **Version** | 2025.14 |
| **Service** | mullvad-daemon.service |
| **Protocol** | WireGuard |
| **Features** | DAITA, kill switch, DNS blocking |

### Installation
```bash
wget https://mullvad.net/media/app/MullvadVPN-2025.14_amd64.deb
dpkg -i MullvadVPN-2025.14_amd64.deb
apt-get install -f
```

### Setup
```bash
mullvad account login <ACCOUNT_NUMBER>
mullvad relay set location us nyc
mullvad connect
```

### Verify
```bash
mullvad status
mullvad relay list
```

### Configuration
- Account and relay configurable via Settings → VPN tab
- Kill switch enabled by default
- DAITA toggle available in GUI

---

## 4. Xray-core (VLESS+Reality Relay)

| Property | Value |
|----------|-------|
| **Version** | 26.2.6 |
| **Service** | xray.service |
| **Protocol** | VLESS + Reality |
| **Config** | /usr/local/etc/xray/config.json |

### Installation
```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

### Verify
```bash
xray version
systemctl status xray
```

### Configuration
- Endpoint and UUID configurable via Settings → VPN tab
- Config file: `/usr/local/etc/xray/config.json`
- Used as fallback when Mullvad is unavailable

---

## 5. Redis (Session/Cache Store)

| Property | Value |
|----------|-------|
| **Version** | 7.0.15 |
| **Service** | redis-server.service |
| **Port** | 6379 |
| **Purpose** | Session state, BIN cache, operation logs |

### Installation
```bash
apt-get install redis-server
```

### Verify
```bash
redis-cli ping
# Expected: PONG
```

### Configuration
- Managed via Settings → SERVICES tab
- Default config: `/etc/redis/redis.conf`
- Bind to localhost only (security)

---

## 6. ntfy (Push Notifications)

| Property | Value |
|----------|-------|
| **Version** | 2.11.0 |
| **Service** | ntfy.service |
| **Port** | 8090 |
| **Purpose** | Operation alerts, decline notifications, system warnings |

### Installation
```bash
wget https://github.com/binwiederhier/ntfy/releases/download/v2.11.0/ntfy_2.11.0_linux_amd64.deb
dpkg -i ntfy_2.11.0_linux_amd64.deb
```

### Verify
```bash
ntfy --version
systemctl status ntfy
```

### Configuration
- Topic name configurable via Settings → API KEYS tab
- Subscribe: `ntfy subscribe <topic>`
- Publish: `ntfy publish <topic> "message"`

---

## 7. curl_cffi (Chrome TLS Fingerprint)

| Property | Value |
|----------|-------|
| **Version** | 0.14.0 |
| **Type** | Python package |
| **Purpose** | Impersonate Chrome TLS fingerprint (JA3/JA4) |

### Installation
```bash
pip install curl_cffi==0.14.0
```

### Verify
```python
import curl_cffi; print(curl_cffi.__version__)
```

### Usage
Used by `tls_mimic.py` and `gamp_triangulation_v2.py` for Chrome 120+ JA3 spoofing.

---

## 8. plyvel (Chrome LevelDB)

| Property | Value |
|----------|-------|
| **Version** | 1.5.1 |
| **Type** | Python package + system lib |
| **Purpose** | Direct writes to Chrome LevelDB localStorage |

### Installation
```bash
apt-get install libleveldb-dev
pip install plyvel==1.5.1
```

### Verify
```python
import plyvel; print(plyvel.__version__)
```

### Usage
Used by `leveldb_writer.py` for injecting localStorage data into forged Chrome profiles.

---

## 9. aioquic (QUIC/HTTP3)

| Property | Value |
|----------|-------|
| **Version** | 1.3.0 |
| **Type** | Python package |
| **Purpose** | QUIC protocol support for network shield |

### Installation
```bash
pip install aioquic==1.3.0
```

### Verify
```python
import aioquic; print(aioquic.__version__)
```

### Usage
Used by `quic_proxy.py` for HTTP/3 QUIC proxy tunneling.

---

## 10. minio (Object Storage)

| Property | Value |
|----------|-------|
| **Version** | 7.2.20 |
| **Type** | Python package |
| **Purpose** | S3-compatible object storage client for profile backups |

### Installation
```bash
pip install minio==7.2.20
```

### Verify
```python
import minio; print(minio.__version__)
```

### Usage
Used for profile backup/restore and artifact storage.

---

## Service Management Quick Reference

```bash
# Start all services
systemctl start ollama redis-server xray ntfy mullvad-daemon

# Check all services
systemctl status ollama redis-server xray ntfy mullvad-daemon

# Stop all services
systemctl stop ollama redis-server xray ntfy mullvad-daemon

# Enable on boot
systemctl enable ollama redis-server xray ntfy mullvad-daemon
```

Or use the **Settings → SERVICES** tab for GUI management.
