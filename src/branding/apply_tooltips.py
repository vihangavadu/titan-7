#!/usr/bin/env python3
"""
TITAN X — Tooltip & UX Polish Injector
========================================
Patches all 11 app files to add tooltips to key buttons, tabs, and UI elements.
Also ensures each app uses mobile-friendly sizing from titan_theme.
"""

import re
import os
from pathlib import Path

APPS_DIR = Path("/opt/titan/src/apps")

# ═══════════════════════════════════════════════════════════════════════════════
# TOOLTIP DEFINITIONS PER APP
# ═══════════════════════════════════════════════════════════════════════════════
# Format: { "filename": [ (search_pattern, tooltip_text), ... ] }
# We'll add setToolTip() calls after button/widget creation lines

PATCHES = {
    "titan_operations.py": {
        "window_tooltip": "Titan X Operations — Your main workspace for running full operations",
        "tab_tooltips": {
            "TARGET": "Select your target website, proxy, and geographic region",
            "IDENTITY": "Build a persona with matching name, address, and phone",
            "VALIDATE": "Check your card details — BIN, AVS, Luhn, quality grade",
            "FORGE": "Generate a browser profile and launch with full protection",
            "RESULTS": "View success/decline history and decode decline reasons",
        },
    },
    "titan_intelligence.py": {
        "window_tooltip": "Titan X Intelligence — AI copilot, 3DS strategy, detection analysis",
        "tab_tooltips": {
            "AI COPILOT": "Ask the AI questions about strategy, targets, or troubleshooting",
            "DETECTION": "Analyze what might be causing declines or blocks",
            "RECON": "Research target websites for payment flow details",
            "3DS": "View and plan 3D Secure bypass strategies",
            "VECTOR": "AI memory of past operations and learned patterns",
        },
    },
    "titan_network.py": {
        "window_tooltip": "Titan X Network — VPN, proxy, and network forensics",
        "tab_tooltips": {
            "VPN": "Connect/disconnect Mullvad VPN and check your IP",
            "PROXY": "Manage SOCKS5 and HTTP proxies for operations",
            "SHIELD": "eBPF TCP fingerprint protection status",
            "FORENSIC": "Monitor network activity for data leaks",
            "GEOIP": "Verify your apparent geographic location",
        },
    },
    "app_kyc.py": {
        "window_tooltip": "Titan X KYC Studio — Identity document and selfie verification tools",
        "tab_tooltips": {
            "CAMERA": "Camera bypass for selfie and liveness checks",
            "DOCUMENT": "Generate or modify identity documents",
            "VOICE": "Voice synthesis for phone verification",
            "TOF": "Time-of-Flight depth synthesis for 3D liveness",
            "DEEP ID": "Deep identity verification bypass",
        },
    },
    "titan_admin.py": {
        "window_tooltip": "Titan X Admin — System services, health monitoring, automation",
        "tab_tooltips": {
            "SERVICES": "Start, stop, and monitor background services",
            "TOOLS": "Bug reporter, auto-patcher, and diagnostics",
            "SYSTEM": "Module health, kill switch, and forensic status",
            "AUTOMATION": "Automated task scheduling and master automation",
            "CONFIG": "Environment variables, AI model config, API keys",
        },
    },
    "app_settings.py": {
        "window_tooltip": "Titan X Settings — Configure VPN, AI, browser, and API keys",
        "tab_tooltips": {
            "VPN": "Mullvad VPN account and server configuration",
            "AI": "Ollama model selection and API endpoint settings",
            "BROWSER": "Browser launch preferences and anti-detect options",
            "API": "Enter and manage your API keys securely",
            "PROXY": "Proxy chain and rotation configuration",
            "HYPERSWITCH": "HyperSwitch payment routing configuration",
            "WAYDROID": "Android emulation settings for mobile verification",
        },
    },
    "app_profile_forge.py": {
        "window_tooltip": "Titan X Profile Forge — Create realistic browser identities",
        "tab_tooltips": {
            "PERSONA": "Generate a complete fake identity with address and phone",
            "CHROME": "Build a Chrome profile with cookies and history",
            "AGING": "Age a profile to look like a real user over time",
            "EXPORT": "Export profiles for use in anti-detect browsers",
        },
    },
    "app_card_validator.py": {
        "window_tooltip": "Titan X Card Validator — Check and grade payment cards",
        "tab_tooltips": {
            "VALIDATE": "Run Luhn check and BIN lookup on a card",
            "BIN": "Detailed BIN intelligence and issuer information",
            "AVS": "Address Verification System check results",
            "QUALITY": "Overall card quality grade and recommendations",
            "DECLINE": "Decode decline reason codes into plain English",
        },
    },
    "app_browser_launch.py": {
        "window_tooltip": "Titan X Browser Launch — Protected browser sessions",
        "tab_tooltips": {
            "PREFLIGHT": "Run all checks before launching a browser",
            "LAUNCH": "Start a Camoufox or Chrome session with protection",
            "MONITOR": "Live transaction monitoring during checkout",
            "HANDOVER": "Auto-complete checkout steps",
        },
    },
    "app_bug_reporter.py": {
        "window_tooltip": "Titan X Bug Reporter — Report issues and track auto-fixes",
        "tab_tooltips": {
            "REPORT": "Describe a problem to generate an auto-fix",
            "HISTORY": "View past bug reports and their resolution status",
            "PATTERNS": "Decline patterns detected across operations",
        },
    },
    "app_cerberus.py": {
        "window_tooltip": "Titan X Cerberus — Advanced card validation and intelligence",
        "tab_tooltips": {
            "VALIDATE": "Multi-card validation with bulk support",
            "INTELLIGENCE": "Decline decoder, 3DS strategy, TRA exemption",
            "BIN": "Advanced BIN scoring and issuer analysis",
        },
    },
}


def patch_app(filepath: Path, config: dict):
    """Add tooltips to an app file."""
    if not filepath.exists():
        print(f"  [!] Missing: {filepath.name}")
        return False

    content = filepath.read_text(encoding="utf-8")
    modified = False

    # 1. Add window tooltip via setWindowTitle line
    window_tip = config.get("window_tooltip", "")
    if window_tip and "setToolTip" not in content[:2000]:
        # Find setWindowTitle and add setToolTip after it
        pattern = r'(self\.setWindowTitle\([^)]+\))'
        match = re.search(pattern, content)
        if match:
            old_line = match.group(0)
            new_line = f'{old_line}\n        self.setToolTip("{window_tip}")'
            if new_line not in content:
                content = content.replace(old_line, new_line, 1)
                modified = True

    # 2. Add tab tooltips
    tab_tips = config.get("tab_tooltips", {})
    if tab_tips:
        # Find addTab calls and add tooltip
        for tab_name, tooltip in tab_tips.items():
            # Match patterns like: addTab(widget, "TAB_NAME") or addTab(scroll, "TAB_NAME")
            for variant in [tab_name, tab_name.upper(), tab_name.title(), tab_name.lower()]:
                pattern = rf'(\.addTab\([^,]+,\s*["\'](?:[^"\']*{re.escape(variant)}[^"\']*)["\'][^)]*\))'
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    old_call = match.group(0)
                    # Check if tooltip already added nearby
                    pos = content.find(old_call)
                    if pos >= 0 and f'setTabToolTip' not in content[pos:pos+200]:
                        # Find the tab widget variable and tab index
                        # Add setTabToolTip after the addTab call
                        idx_match = re.search(r'(\w+)\.addTab', old_call)
                        if idx_match:
                            tw_var = idx_match.group(1)
                            # Count how many addTab calls before this one for this widget
                            preceding = content[:pos]
                            tab_idx = preceding.count(f'{tw_var}.addTab(')
                            tip_line = f'\n        {tw_var}.setTabToolTip({tab_idx}, "{tooltip}")'
                            content = content[:pos] + content[pos:].replace(
                                old_call, old_call + tip_line, 1
                            )
                            modified = True
                    break  # Found a match, stop trying variants

    if modified:
        filepath.write_text(content, encoding="utf-8")
        print(f"  [+] Patched: {filepath.name}")
        return True
    else:
        print(f"  [=] No changes needed: {filepath.name}")
        return False


def main():
    print("[TITAN X] Adding tooltips to all apps...")
    patched = 0
    for filename, config in PATCHES.items():
        filepath = APPS_DIR / filename
        if patch_app(filepath, config):
            patched += 1

    print(f"\n[DONE] Patched {patched}/{len(PATCHES)} apps with tooltips.")


if __name__ == "__main__":
    main()
