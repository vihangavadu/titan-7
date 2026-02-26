# TITAN OS V9.1 — Operational Playbook

## Complete System Documentation

This playbook covers every aspect of Titan OS V9.1 — from architecture to daily operations. It is the definitive reference for understanding what every module does, how the **9 GUI applications** work feature-by-feature, and how a human operator uses the system in real-world scenarios.

---

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 01 | [Introduction](01_INTRODUCTION.md) | What is Titan OS, philosophy, design principles, system overview |
| 02 | [Techniques & Methods](02_TECHNIQUES_AND_METHODS.md) | Anti-detection techniques, fingerprint evasion, network masquerade, behavioral mimicry |
| 03 | [Core Modules Reference](03_CORE_MODULES.md) | All 115 modules — purpose, function, how each helps operations |
| 04 | [App: Operations Center](04_APP_OPERATIONS_CENTER.md) | 5 tabs: Target → Identity → Validate → Forge → Results |
| 05 | [App: Intelligence Center](05_APP_INTELLIGENCE_CENTER.md) | 5 tabs: AI Copilot → 3DS Strategy → Detection → Recon → Memory |
| 06 | [App: Network Center](06_APP_NETWORK_CENTER.md) | 5 tabs: Mullvad VPN → Network Shield → Forensic → Proxy/DNS → TLS |
| 07 | [App: KYC Studio](07_APP_KYC_STUDIO.md) | 3 tabs: Camera → Documents → Voice |
| 08 | [App: Admin Panel](08_APP_ADMIN_PANEL.md) | 5 tabs: Services → System → Logs → Automation → Config |
| 09 | [Operator Workflow](09_OPERATOR_WORKFLOW.md) | Step-by-step: what the human operator inputs, what comes out, complete flow |
| 10 | [Real-World Operations](10_REAL_WORLD_OPERATIONS.md) | Practical capabilities, success factors, what Titan can actually do |
| 11 | [Version History](11_VERSION_HISTORY.md) | Evolution from concept through V8.2.2 |
| 12 | [Gap Analysis](12_GAP_ANALYSIS.md) | Known gaps and planned improvements |
| 13 | [Version Comparison](13_VERSION_COMPARISON.md) | Side-by-side V7.6 vs V8.1 vs V8.2.2 |
| 14 | [App: Settings](14_APP_SETTINGS.md) | **NEW** — 6 tabs: VPN → AI → Services → Browser → API Keys → System |
| 15 | [App: Profile Forge](15_APP_PROFILE_FORGE.md) | **NEW** — 3 tabs: Identity → Forge (9-stage) → Profiles |
| 16 | [App: Card Validator](16_APP_CARD_VALIDATOR.md) | **NEW** — 3 tabs: Validate → Intelligence → History |
| 17 | [App: Browser Launch](17_APP_BROWSER_LAUNCH.md) | **NEW** — 3 tabs: Launch → Monitor → Handover |
| 18 | [External Software Guide](18_EXTERNAL_SOFTWARE.md) | **NEW** — Mullvad, Xray, Redis, ntfy, Ollama, Camoufox setup |

---

## Quick Reference

- **Total Core Modules:** 115 Python + 3 C + 2 Shell
- **GUI Applications:** 9 apps + launcher (22 .py files in apps/) — 38+ tabs total
- **Browser Extensions:** 3 (Ghost Motor, TX Monitor, Golden Trap)
- **External Tools:** 10 (Mullvad, Xray, Redis, ntfy, Ollama, Camoufox, curl_cffi, plyvel, aioquic, minio)
- **AI Models:** 6 Ollama (mistral:7b, qwen2.5:7b, deepseek-r1:8b + titan-analyst, titan-strategist, titan-fast) + Phi-4-mini ONNX INT4
- **ONNX Engine:** Phi-4-mini INT4 for CPU inference (33 task routes) with Ollama fallback
- **Training Data:** 2,200 operator examples (ChatML JSONL)
- **Platform:** Debian 12 | Python 3.11 | Camoufox 0.4.11 | PyQt6
- **Architecture:** Six-Ring Defense Model + 9-stage Forge Pipeline
- **Automation:** 12-phase orchestrator + 24/7 autonomous engine
- **Android/KYC:** Waydroid container + kyc_android_console + titan-android CLI

---

*Updated for V9.1 (Feb 2026). 115 core modules verified importable on VPS. ONNX inference engine added for CPU-only AI. 6 Ollama models + Phi-4-mini ONNX. Waydroid Android KYC module deployed. 2,200 operator training examples generated.*
