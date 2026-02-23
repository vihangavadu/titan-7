# TITAN V8.2.2 — Research Resources

**Version:** 8.2.2 | **Author:** Dva.12 | **Updated:** 2026-02-23

---

## Overview

This document is the top-level entry point for all research documentation, external tools, APIs, and learning resources used by Titan OS.

---

## Research Documents

17 in-depth technical documents covering every subsystem:

→ [**research/README.md**](research/README.md) — Full index with descriptions

**Key documents:**
- [System Architecture](research/01_TITAN_ARCHITECTURE_OVERVIEW.md) — 7-ring defense model
- [Genesis Profile Engine](research/02_GENESIS_PROFILE_ENGINE.md) — 9-stage forge pipeline
- [Cerberus Transaction Engine](research/03_CERBERUS_TRANSACTION_ENGINE.md) — Card validation + BIN intel
- [Detection Evasion Matrix](research/09_DETECTION_EVASION_MATRIX.md) — 21 antifraud platforms mapped
- [Full Architecture Whitepaper](research/14_TITAN_WHITEPAPER_FULL_ARCHITECTURE.md) — Complete technical reference

---

## External Software Stack

### Installed on VPS (10 tools)

| Tool | Version | Type | Purpose |
|------|---------|------|---------|
| **Ollama** | 0.16.3 | LLM Server | Local AI inference — 6 models |
| **Camoufox** | 0.4.11 | Browser | Anti-detect Firefox fork |
| **Mullvad VPN** | 2025.14 | VPN | WireGuard privacy VPN with DAITA |
| **Xray-core** | 26.2.6 | Relay | VLESS+Reality protocol |
| **Redis** | 7.0.15 | Database | Session/cache store |
| **ntfy** | 2.11.0 | Notifications | Push alerts for operations |
| **curl_cffi** | 0.14.0 | Library | Chrome TLS fingerprint (JA3/JA4) |
| **plyvel** | 1.5.1 | Library | Chrome LevelDB writes |
| **aioquic** | 1.3.0 | Library | QUIC/HTTP3 protocol |
| **minio** | 7.2.20 | Library | S3-compatible object storage |

### Installation Guide
→ [**operational-playbook/18_EXTERNAL_SOFTWARE.md**](operational-playbook/18_EXTERNAL_SOFTWARE.md)

---

## AI Models

| Model | Size | Latency | Best For |
|-------|------|---------|----------|
| **mistral:7b** | 4.4 GB | ~10s | Fast copilot, warmup, behavioral tuning |
| **qwen2.5:7b** | 4.7 GB | ~9s | BIN analysis, recon, persona enrichment, JSON output |
| **deepseek-r1:8b** | 5.2 GB | ~24s | 3DS strategy, detection analysis, operation planning |
| **titan-fast** | 4.4 GB | ~10s | Custom: fast general queries |
| **titan-analyst** | 4.7 GB | ~9s | Custom: structured analysis |
| **titan-strategist** | 4.7 GB | ~9s | Custom: operation strategy |

**Routing config:** `/opt/titan/llm_config.json` (20 task-routing entries)

---

## Proxy & IP Providers

| Provider | Type | Website | Notes |
|----------|------|---------|-------|
| **IPRoyal** | Residential/ISP | iproyal.com | High-quality residential, good for US targets |
| **SOAX** | Residential/Mobile | soax.com | Mobile carrier IPs, good for 3DS bypass |
| **Bright Data** | Residential/DC | brightdata.com | Largest pool, advanced geo-targeting |
| **Oxylabs** | Residential/DC | oxylabs.io | Enterprise-grade, reliable |
| **Smartproxy** | Residential | smartproxy.com | Budget option, decent quality |

---

## OSINT & Intelligence APIs

| API | Purpose | Website |
|-----|---------|---------|
| **IPQS** | IP quality scoring, fraud risk | ipqualityscore.com |
| **SEON** | Device fingerprint intelligence | seon.io |
| **Shodan** | Network/device reconnaissance | shodan.io |
| **VirusTotal** | URL/file reputation | virustotal.com |
| **MaxMind** | GeoIP database | maxmind.com |
| **BINList** | Free BIN lookup | binlist.net |

---

## Antifraud Platforms Reference

| Platform | Focus | Key Detection Vectors |
|----------|-------|----------------------|
| **Forter** | Behavioral biometrics | Mouse dynamics, device fingerprint, session behavior |
| **BioCatch** | Behavioral biometrics | Keystroke dynamics, cognitive patterns, mouse micro-movements |
| **Riskified** | ML fraud scoring | Device graph, behavioral patterns, order history |
| **Sift** | Real-time fraud | Account takeover, payment fraud, content abuse |
| **Kount** | Device intelligence | Device ID, IP intelligence, behavioral analytics |
| **Signifyd** | Guaranteed protection | Identity network, transaction history |
| **Stripe Radar** | Payment fraud ML | Card testing detection, velocity checks |
| **Adyen Risk** | Payment risk | RevenueProtect, risk rules engine |
| **CyberSource** | Decision Manager | 260+ fraud detection tests |
| **Accertify** | Digital identity | Cross-channel fraud, identity trust |
| **ThreatMetrix** | Device/identity graph | 78B+ events, device profiling |
| **iovation** | Device reputation | 6B+ devices tracked |

---

## Browser & Fingerprint Resources

| Resource | Purpose |
|----------|---------|
| **BrowserLeaks** (browserleaks.com) | Test browser fingerprint leaks |
| **CreepJS** (abrahamjuliot.github.io/creepjs) | Advanced fingerprint detection |
| **AmIUnique** (amiunique.org) | Browser uniqueness analysis |
| **Pixelscan** (pixelscan.net) | Anti-detect browser verification |
| **BotD** (fingerprint.com/products/bot-detection) | Bot detection testing |
| **JA3er** (ja3er.com) | JA3 TLS fingerprint lookup |

---

## Network & VPN Resources

| Resource | Purpose |
|----------|---------|
| **IPLeak** (ipleak.net) | DNS/WebRTC/IPv6 leak testing |
| **DNSLeakTest** (dnsleaktest.com) | DNS leak verification |
| **Mullvad Check** (mullvad.net/check) | VPN connection verification |
| **Scamalytics** (scamalytics.com) | IP fraud score checking |
| **IPInfo** (ipinfo.io) | IP geolocation and ASN lookup |

---

## Related Documentation

| Document | Location |
|----------|----------|
| **App Architecture** | [APP_ARCHITECTURE.md](APP_ARCHITECTURE.md) |
| **Operational Playbook** | [OPERATIONAL_PLAYBOOK.md](OPERATIONAL_PLAYBOOK.md) |
| **Module Audit Report** | [MODULE_AUDIT_REPORT.md](MODULE_AUDIT_REPORT.md) |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |
| **Detailed Playbook** | [operational-playbook/00_INDEX.md](operational-playbook/00_INDEX.md) |
| **Research Index** | [research/README.md](research/README.md) |

---

*V8.2.2 — 10 external tools, 6 AI models, 5 proxy providers, 4 OSINT APIs, 12 antifraud platforms studied.*
