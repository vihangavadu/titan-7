# 17 — App: Browser Launch (`app_browser_launch.py`)

**Version:** V9.1 | **Accent:** Green `#22c55e` | **Tabs:** 3

---

## Overview

Browser Launch is a **focused app** for launching forged profiles in Camoufox, monitoring live transactions, and executing the handover protocol. It extracts the launch/monitor workflow from the Operations Center into a dedicated window with real-time TX tracking and decline decoding.

Launched from the **bottom-right card** in the 3×3 launcher grid.

---

## Tab 1: LAUNCH

Preflight validation and Camoufox browser launch.

### Preflight Checklist

Before launching, the app runs automated checks:

| Check | Module | What It Verifies |
|-------|--------|-----------------|
| **Profile Exists** | — | Profile directory is present and non-empty |
| **VPN Active** | mullvad_vpn | Mullvad or Xray tunnel is connected |
| **IP Clean** | proxy_manager | IP not on known blacklists |
| **DNS Secure** | network_shield | No DNS leaks detected |
| **Timezone Match** | timezone_enforcer | System TZ matches proxy geo |
| **Fingerprint Ready** | fingerprint_injector | Canvas, WebGL, audio, font layers applied |
| **Ghost Motor** | ghost_motor_v6 | Behavioral extension loaded |
| **TX Monitor** | transaction_monitor | TX monitoring extension loaded |

### Launch Controls

| Control | Description |
|---------|-------------|
| **Profile Selector** | Dropdown of available forged profiles |
| **Target Site** | Pre-filled from profile metadata |
| **Proxy Override** | Optional proxy URL override |
| **Launch Button** | Starts Camoufox with selected profile |
| **Preflight Status** | Green/red indicators for each check |

### Launch Sequence

1. Select profile from dropdown
2. Review preflight checklist (all green = ready)
3. Click **Launch** — Camoufox opens with:
   - Forged profile loaded
   - Ghost Motor extension active
   - TX Monitor extension active
   - Proxy/VPN routing configured
   - Timezone and locale matched
4. Browser opens to target site warmup page

---

## Tab 2: MONITOR

Live transaction monitoring and decline decoding.

### TX Log Table

| Column | Description |
|--------|-------------|
| **Time** | Timestamp of the event |
| **Event** | Page load, form fill, payment submit, response |
| **Status** | Success / Decline / Pending / Error |
| **Code** | Decline code if applicable |
| **Details** | Human-readable explanation |

### Decline Decoder

When a decline occurs, the decoder provides:

| Field | Description |
|-------|-------------|
| **Raw Code** | Gateway decline code (e.g., `05`, `51`, `N7`) |
| **Meaning** | Human-readable translation |
| **Category** | Issuer / Gateway / Fraud / 3DS / AVS |
| **Severity** | Soft decline (retry) vs Hard decline (stop) |
| **Recommendation** | AI-generated next steps |

### Common Decline Codes

| Code | Meaning | Action |
|------|---------|--------|
| 05 | Do Not Honor | Try different card |
| 51 | Insufficient Funds | Lower amount or different card |
| 14 | Invalid Card Number | Check card details |
| 65 | Activity Limit Exceeded | Wait 24h or use different card |
| N7 | CVV Mismatch | Verify CVV |
| 3DS_FAIL | 3DS Challenge Failed | Review 3DS strategy |

---

## Tab 3: HANDOVER

Manual handover protocol and post-operation analysis.

### Handover Protocol

The handover is the critical moment when the automated system passes control to the human operator for the final payment step.

| Phase | Description |
|-------|-------------|
| **Pre-Handover** | System fills cart, applies coupons, enters shipping |
| **Handover Signal** | Alert: "Ready for payment — take manual control" |
| **Manual Phase** | Operator types card details with human timing |
| **Post-Submit** | System monitors for success/decline |
| **Cleanup** | Forensic cleanup if needed |

### Post-Op Analysis

After each operation (success or failure):

| Metric | Description |
|--------|-------------|
| **Session Duration** | Total time from launch to completion |
| **Pages Visited** | Count of pages loaded |
| **Timing Score** | How human-like the timing was |
| **Detection Events** | Any antifraud triggers detected |
| **Fingerprint Consistency** | Were any fingerprint leaks detected |
| **Recommendation** | AI analysis of what to improve |

---

## Operator Workflow

1. Open Browser Launch from launcher (bottom-right card)
2. Select a forged profile in LAUNCH tab
3. Review preflight checklist — fix any red items
4. Click **Launch** — Camoufox opens
5. Switch to MONITOR tab to watch live TX events
6. When handover signal appears, take manual control
7. Complete payment with human-like timing
8. After completion, review post-op analysis in HANDOVER tab
9. If declined, check decline decoder for next steps
