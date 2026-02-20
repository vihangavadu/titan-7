#!/usr/bin/env python3
"""
TITAN V7.0.3 — MASTER CODEBASE VERIFICATION
Single unified pre-build verification script.

Replaces all scattered verify_*.py / preflight_scan.py / checklist scripts.
Run this BEFORE building the ISO to ensure every subsystem is wired correctly.

Scope:
  S1 — File Structure (all critical files exist)
  S2 — OS & Infrastructure (sysctl, journald, DNS, coredump, dracut)
  S3 — Kernel & Hardware (titan_hw.c, titan_battery.c, usb_peripheral_synth)
  S4 — Network & eBPF (tcp_fingerprint.c, network_shield.c, tls_parrot)
  S5 — Browser & Extensions (Camoufox, Ghost Motor, TX Monitor, sanitization)
  S6 — AI & KYC (camera_injector, reenactment_engine, biometric_mimicry)
  S7 — Backend Core (genesis, cerberus, purchase_history, multi-PSP)
  S8 — GUI Apps (unified, cerberus, genesis, kyc, bug_reporter)
  S9 — Forensic Sanitization (no branded leaks, no console.log, no window globals)
  S10 — Build Config (live-build, hooks, package lists)

Exit codes:
  0 = ALL PASS
  1 = CRITICAL FAILURES
  2 = WARNINGS ONLY

Usage:
  python master_verify.py
  python master_verify.py --verbose
  python master_verify.py --fix  (auto-fix trivial issues)
"""

import os
import sys
import re
import json
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).parent
ISO_ROOT = REPO_ROOT / "iso"
CHROOT = ISO_ROOT / "config" / "includes.chroot"
TITAN = CHROOT / "opt" / "titan"
LUCID = CHROOT / "opt" / "lucid-empire"
ETC = CHROOT / "etc"
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

# ═══════════════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════════════

class V:
    OK = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"

@dataclass
class Check:
    section: str
    name: str
    verdict: str
    msg: str

RESULTS: List[Check] = []

def check(section: str, name: str, verdict: str, msg: str = ""):
    RESULTS.append(Check(section, name, verdict, msg))

def file_exists(section: str, name: str, path: Path, critical: bool = True):
    if path.exists():
        check(section, name, V.OK, str(path.relative_to(REPO_ROOT)))
    else:
        v = V.FAIL if critical else V.WARN
        check(section, name, v, f"MISSING: {path.relative_to(REPO_ROOT)}")

def file_contains(section: str, name: str, path: Path, pattern: str, should_exist: bool = True):
    if not path.exists():
        check(section, name, V.FAIL, f"File missing: {path.name}")
        return
    content = path.read_text(errors="ignore")
    found = bool(re.search(pattern, content))
    if should_exist and found:
        check(section, name, V.OK, f"Pattern found in {path.name}")
    elif should_exist and not found:
        check(section, name, V.FAIL, f"Pattern NOT found in {path.name}: {pattern}")
    elif not should_exist and not found:
        check(section, name, V.OK, f"Pattern correctly absent from {path.name}")
    else:
        check(section, name, V.FAIL, f"LEAK: Pattern should NOT be in {path.name}: {pattern}")

def py_compiles(section: str, name: str, path: Path):
    if not path.exists():
        check(section, name, V.FAIL, f"MISSING: {path.name}")
        return
    try:
        import py_compile
        py_compile.compile(str(path), doraise=True)
        check(section, name, V.OK, f"{path.name} compiles")
    except py_compile.PyCompileError as e:
        check(section, name, V.FAIL, f"Syntax error in {path.name}: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# S1: FILE STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

def verify_s1():
    S = "S1-Structure"
    # ISO build
    file_exists(S, "auto/config", ISO_ROOT / "auto" / "config")
    file_exists(S, "auto/build", ISO_ROOT / "auto" / "build")
    file_exists(S, "auto/clean", ISO_ROOT / "auto" / "clean")
    # Hooks
    hooks = ISO_ROOT / "config" / "hooks" / "live"
    file_exists(S, "hooks/live dir", hooks)
    # Package lists
    file_exists(S, "package-lists", ISO_ROOT / "config" / "package-lists")
    # Core directories
    file_exists(S, "opt/titan/core", TITAN / "core")
    file_exists(S, "opt/titan/apps", TITAN / "apps")
    file_exists(S, "opt/titan/extensions", TITAN / "extensions")
    file_exists(S, "opt/lucid-empire/backend", LUCID / "backend")
    file_exists(S, "opt/lucid-empire/camoufox", LUCID / "camoufox")
    file_exists(S, "opt/lucid-empire/ebpf", LUCID / "ebpf")
    file_exists(S, "opt/lucid-empire/hardware_shield", LUCID / "hardware_shield")

# ═══════════════════════════════════════════════════════════════════════════
# S2: OS & INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

def verify_s2():
    S = "S2-OS"
    # Anti-forensics
    file_exists(S, "ramwipe/titan-wipe.sh", CHROOT / "usr" / "lib" / "dracut" / "modules.d" / "99ramwipe" / "titan-wipe.sh")
    file_exists(S, "ramwipe/module-setup.sh", CHROOT / "usr" / "lib" / "dracut" / "modules.d" / "99ramwipe" / "module-setup.sh")
    # Systemd stealth
    file_exists(S, "no-coredump", ETC / "systemd" / "coredump.conf.d" / "titan-no-coredump.conf")
    file_exists(S, "journald-volatile", ETC / "systemd" / "journald.conf.d" / "titan-privacy.conf")
    file_contains(S, "journald=volatile", ETC / "systemd" / "journald.conf.d" / "titan-privacy.conf", r"Storage=volatile")
    file_contains(S, "coredump=none", ETC / "systemd" / "coredump.conf.d" / "titan-no-coredump.conf", r"Storage=none")
    # Kernel hardening
    file_exists(S, "sysctl-stealth", ETC / "sysctl.d" / "99-titan-stealth.conf")
    file_exists(S, "sysctl-hardening", ETC / "sysctl.d" / "99-titan-hardening.conf")
    file_contains(S, "TTL=128", ETC / "sysctl.d" / "99-titan-hardening.conf", r"ip_default_ttl\s*=\s*128")
    file_contains(S, "tcp_timestamps=0", ETC / "sysctl.d" / "99-titan-hardening.conf", r"tcp_timestamps\s*=\s*0")
    file_contains(S, "IPv6=disabled", ETC / "sysctl.d" / "99-titan-hardening.conf", r"disable_ipv6\s*=\s*1")
    # DNS
    file_exists(S, "unbound-dns", ETC / "unbound" / "unbound.conf.d" / "titan-dns.conf")
    file_contains(S, "DNS-over-TLS", ETC / "unbound" / "unbound.conf.d" / "titan-dns.conf", r"forward-tls-upstream:\s*yes")
    # GRUB sanitized
    file_contains(S, "GRUB-no-branding", ETC / "default" / "grub.d" / "titan-branding.cfg", r'GRUB_DISTRIBUTOR="Debian', should_exist=True)
    file_contains(S, "GRUB-no-TITAN", ETC / "default" / "grub.d" / "titan-branding.cfg", r'GRUB_DISTRIBUTOR="TITAN', should_exist=False)
    # VPN
    file_exists(S, "xray-client", TITAN / "vpn" / "xray-client.json")
    file_exists(S, "setup-vps-relay", TITAN / "vpn" / "setup-vps-relay.sh")
    # Services
    file_exists(S, "lucid-titan.service", ETC / "systemd" / "system" / "lucid-titan.service")
    file_exists(S, "titan-dns.service", ETC / "systemd" / "system" / "titan-dns.service")
    file_exists(S, "titan-first-boot.service", ETC / "systemd" / "system" / "titan-first-boot.service")
    file_exists(S, "patch-bridge.service", ETC / "systemd" / "system" / "titan-patch-bridge.service")

# ═══════════════════════════════════════════════════════════════════════════
# S3: KERNEL & HARDWARE
# ═══════════════════════════════════════════════════════════════════════════

def verify_s3():
    S = "S3-Kernel"
    file_exists(S, "titan_hw.c", LUCID / "hardware_shield" / "titan_hw.c")
    file_exists(S, "titan_hw Makefile", LUCID / "hardware_shield" / "Makefile")
    file_exists(S, "titan_battery.c", TITAN / "core" / "titan_battery.c")
    file_exists(S, "hardware_shield.c", LUCID / "lib" / "hardware_shield.c")
    file_exists(S, "hardware_shield_v6.c", TITAN / "core" / "hardware_shield_v6.c")
    py_compiles(S, "usb_peripheral_synth.py", TITAN / "core" / "usb_peripheral_synth.py")

# ═══════════════════════════════════════════════════════════════════════════
# S4: NETWORK & eBPF
# ═══════════════════════════════════════════════════════════════════════════

def verify_s4():
    S = "S4-Network"
    file_exists(S, "network_shield.c", LUCID / "ebpf" / "network_shield.c")
    file_exists(S, "network_shield.o", LUCID / "ebpf" / "network_shield.o")
    file_exists(S, "tcp_fingerprint.c", LUCID / "ebpf" / "tcp_fingerprint.c")
    file_exists(S, "tcp_fingerprint.o", LUCID / "ebpf" / "tcp_fingerprint.o")
    file_exists(S, "xdp_loader.c", LUCID / "backend" / "network" / "xdp_loader.c")
    file_exists(S, "xdp_outbound.c", LUCID / "backend" / "network" / "xdp_outbound.c")
    py_compiles(S, "tls_masquerade.py", LUCID / "backend" / "network" / "tls_masquerade.py")
    py_compiles(S, "tls_parrot.py (V7)", TITAN / "core" / "tls_parrot.py")
    py_compiles(S, "quic_proxy.py", TITAN / "core" / "quic_proxy.py")
    py_compiles(S, "network_jitter.py", TITAN / "core" / "network_jitter.py")
    py_compiles(S, "lucid_vpn.py", TITAN / "core" / "lucid_vpn.py")

# ═══════════════════════════════════════════════════════════════════════════
# S5: BROWSER & EXTENSIONS
# ═══════════════════════════════════════════════════════════════════════════

def verify_s5():
    S = "S5-Browser"
    # Camoufox
    file_exists(S, "lucid_browser.cfg", LUCID / "camoufox" / "settings" / "lucid_browser.cfg")
    file_exists(S, "policies.json", LUCID / "camoufox" / "settings" / "distribution" / "policies.json")
    file_exists(S, "camoufox.cfg", LUCID / "camoufox" / "settings" / "camoufox.cfg")
    # Ghost Motor extension
    gm = TITAN / "extensions" / "ghost_motor"
    file_exists(S, "ghost_motor.js", gm / "ghost_motor.js")
    file_exists(S, "ghost_motor/manifest.json", gm / "manifest.json")
    # TX Monitor extension
    tx = TITAN / "extensions" / "tx_monitor"
    file_exists(S, "tx_monitor.js", tx / "tx_monitor.js")
    file_exists(S, "tx_monitor/background.js", tx / "background.js")
    file_exists(S, "tx_monitor/manifest.json", tx / "manifest.json")
    # Firefox ESR hardening
    file_exists(S, "titan-hardening.js", CHROOT / "usr" / "lib" / "firefox-esr" / "defaults" / "pref" / "titan-hardening.js")
    # Core browser modules
    py_compiles(S, "fingerprint_injector.py", TITAN / "core" / "fingerprint_injector.py")
    py_compiles(S, "webgl_angle.py", TITAN / "core" / "webgl_angle.py")
    py_compiles(S, "font_sanitizer.py", TITAN / "core" / "font_sanitizer.py")
    py_compiles(S, "audio_hardener.py", TITAN / "core" / "audio_hardener.py")

# ═══════════════════════════════════════════════════════════════════════════
# S6: AI & KYC
# ═══════════════════════════════════════════════════════════════════════════

def verify_s6():
    S = "S6-KYC"
    kyc = LUCID / "backend" / "modules" / "kyc_module"
    py_compiles(S, "camera_injector.py", kyc / "camera_injector.py")
    py_compiles(S, "reenactment_engine.py", kyc / "reenactment_engine.py")
    file_exists(S, "renderer_3d.js", kyc / "renderer_3d.js")
    file_exists(S, "integrity_shield.c", kyc / "integrity_shield.c")
    py_compiles(S, "kyc_core.py (V7)", TITAN / "core" / "kyc_core.py")
    py_compiles(S, "kyc_enhanced.py (V7)", TITAN / "core" / "kyc_enhanced.py")
    py_compiles(S, "biometric_mimicry.py", LUCID / "backend" / "modules" / "biometric_mimicry.py")

# ═══════════════════════════════════════════════════════════════════════════
# S7: BACKEND CORE (Genesis, Cerberus, Multi-PSP, Trinity)
# ═══════════════════════════════════════════════════════════════════════════

def verify_s7():
    S = "S7-Backend"
    core = TITAN / "core"
    # Genesis + Profile
    py_compiles(S, "genesis_core.py", core / "genesis_core.py")
    py_compiles(S, "advanced_profile_generator.py", core / "advanced_profile_generator.py")
    py_compiles(S, "purchase_history_engine.py", core / "purchase_history_engine.py")
    # Cerberus
    py_compiles(S, "cerberus_core.py", core / "cerberus_core.py")
    py_compiles(S, "cerberus_enhanced.py", core / "cerberus_enhanced.py")
    # Operations
    py_compiles(S, "integration_bridge.py", core / "integration_bridge.py")
    py_compiles(S, "handover_protocol.py", core / "handover_protocol.py")
    py_compiles(S, "kill_switch.py", core / "kill_switch.py")
    py_compiles(S, "transaction_monitor.py", core / "transaction_monitor.py")
    py_compiles(S, "target_intelligence.py", core / "target_intelligence.py")
    py_compiles(S, "target_discovery.py", core / "target_discovery.py")
    py_compiles(S, "three_ds_strategy.py", core / "three_ds_strategy.py")
    py_compiles(S, "preflight_validator.py", core / "preflight_validator.py")
    py_compiles(S, "cognitive_core.py", core / "cognitive_core.py")
    py_compiles(S, "referrer_warmup.py", core / "referrer_warmup.py")
    py_compiles(S, "timezone_enforcer.py", core / "timezone_enforcer.py")
    py_compiles(S, "proxy_manager.py", core / "proxy_manager.py")
    py_compiles(S, "titan_services.py", core / "titan_services.py")
    py_compiles(S, "bug_patch_bridge.py", core / "bug_patch_bridge.py")
    # Legacy backend
    py_compiles(S, "warming_engine.py", LUCID / "backend" / "warming_engine.py")
    py_compiles(S, "forensic_validator.py", LUCID / "backend" / "validation" / "forensic_validator.py")
    # Multi-PSP check: purchase_history must have > 5 processors
    phe = core / "purchase_history_engine.py"
    if phe.exists():
        content = phe.read_text(errors="ignore")
        psps = set(re.findall(r'"processor":\s*"(\w+)"', content))
        if len(psps) >= 5:
            check(S, f"multi-PSP ({len(psps)} processors)", V.OK, ", ".join(sorted(psps)))
        else:
            check(S, f"multi-PSP ({len(psps)} processors)", V.FAIL, f"Need >=5, got: {psps}")

# ═══════════════════════════════════════════════════════════════════════════
# S8: GUI APPS
# ═══════════════════════════════════════════════════════════════════════════

def verify_s8():
    S = "S8-GUI"
    apps = TITAN / "apps"
    py_compiles(S, "app_unified.py", apps / "app_unified.py")
    py_compiles(S, "app_cerberus.py", apps / "app_cerberus.py")
    py_compiles(S, "app_genesis.py", apps / "app_genesis.py")
    py_compiles(S, "app_kyc.py", apps / "app_kyc.py")
    py_compiles(S, "app_bug_reporter.py", apps / "app_bug_reporter.py")
    py_compiles(S, "titan_mission_control.py", apps / "titan_mission_control.py")
    # Desktop entries
    desk = CHROOT / "usr" / "share" / "applications"
    file_exists(S, "unified.desktop", desk / "titan-unified.desktop")
    file_exists(S, "browser.desktop", desk / "titan-browser.desktop")
    file_exists(S, "bug-reporter.desktop", desk / "titan-bug-reporter.desktop")

# ═══════════════════════════════════════════════════════════════════════════
# S9: FORENSIC SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════

def verify_s9():
    S = "S9-Forensic"
    gm_js = TITAN / "extensions" / "ghost_motor" / "ghost_motor.js"
    tx_js = TITAN / "extensions" / "tx_monitor" / "tx_monitor.js"
    tx_bg = TITAN / "extensions" / "tx_monitor" / "background.js"
    gm_mf = TITAN / "extensions" / "ghost_motor" / "manifest.json"
    tx_mf = TITAN / "extensions" / "tx_monitor" / "manifest.json"

    # No branded console.log in JS
    for name, path in [("ghost_motor.js", gm_js), ("tx_monitor.js", tx_js), ("background.js", tx_bg)]:
        file_contains(S, f"no-console.log({name})", path, r"console\.(log|warn|error|info|debug)\(", should_exist=False)

    # No branded window globals
    file_contains(S, "no-__titan-globals", gm_js, r"window\.__titan", should_exist=False)
    file_contains(S, "no-__ghost-globals", gm_js, r"window\.__ghost", should_exist=False)
    file_contains(S, "no-_txMon-props", tx_js, r"_txMon", should_exist=False)

    # Manifest names sanitized
    if gm_mf.exists():
        mf = json.loads(gm_mf.read_text())
        if "ghost" in mf.get("name", "").lower() or "titan" in mf.get("name", "").lower():
            check(S, "ghost_motor manifest name", V.FAIL, f"Branded: {mf['name']}")
        else:
            check(S, "ghost_motor manifest name", V.OK, mf.get("name", ""))
    if tx_mf.exists():
        mf = json.loads(tx_mf.read_text())
        if "monitor" in mf.get("name", "").lower() or "titan" in mf.get("name", "").lower():
            check(S, "tx_monitor manifest name", V.FAIL, f"Branded: {mf['name']}")
        else:
            check(S, "tx_monitor manifest name", V.OK, mf.get("name", ""))

    # Stripe cookie format: must use UUID v4, NOT hash.timestamp.random
    phe = TITAN / "core" / "purchase_history_engine.py"
    if phe.exists():
        c = phe.read_text(errors="ignore")
        if re.search(r'f"\{device_hash\}\.\{timestamp\}\.\{random', c):
            check(S, "stripe_mid format", V.FAIL, "Old hash.timestamp.random format found")
        else:
            check(S, "stripe_mid format", V.OK, "UUID v4 format")
        if re.search(r'stripe_sid.*token_hex\(24\)', c):
            check(S, "stripe_sid format", V.FAIL, "Raw hex format found")
        else:
            check(S, "stripe_sid format", V.OK, "UUID v4 format")

    # GRUB no TITAN branding
    grub = ETC / "default" / "grub.d" / "titan-branding.cfg"
    file_contains(S, "GRUB-clean", grub, r'DISTRIBUTOR="TITAN', should_exist=False)

# ═══════════════════════════════════════════════════════════════════════════
# S10: BUILD CONFIG
# ═══════════════════════════════════════════════════════════════════════════

def verify_s10():
    S = "S10-Build"
    # auto/config must exist and have key settings
    ac = ISO_ROOT / "auto" / "config"
    file_contains(S, "distribution=bookworm", ac, r"--distribution bookworm")
    file_contains(S, "arch=amd64", ac, r"--architectures amd64")
    file_contains(S, "bootloader=grub-efi", ac, r"--bootloader grub-efi")
    file_contains(S, "binary=iso-hybrid", ac, r"--binary-images iso-hybrid")
    # Hooks exist
    hooks = ISO_ROOT / "config" / "hooks" / "live"
    if hooks.exists():
        hook_count = len(list(hooks.glob("*.hook.chroot")))
        if hook_count >= 5:
            check(S, f"chroot hooks ({hook_count})", V.OK, "")
        else:
            check(S, f"chroot hooks ({hook_count})", V.WARN, "Expected >=5 hooks")
    # Package lists
    pkg = ISO_ROOT / "config" / "package-lists"
    if pkg.exists():
        pkg_count = len(list(pkg.glob("*.list.chroot")))
        if pkg_count >= 1:
            check(S, f"package lists ({pkg_count})", V.OK, "")
        else:
            check(S, f"package lists ({pkg_count})", V.WARN, "No .list.chroot files found")

# ═══════════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════════

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[1m"
D = "\033[2m"
E = "\033[0m"
C_CYAN = "\033[96m"

def print_report():
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r.verdict == V.OK)
    failed = sum(1 for r in RESULTS if r.verdict == V.FAIL)
    warned = sum(1 for r in RESULTS if r.verdict == V.WARN)

    print(f"\n{B}{'='*70}{E}")
    print(f"{B} TITAN V7.0.3 — MASTER CODEBASE VERIFICATION{E}")
    print(f"{B}{'='*70}{E}\n")

    # Group by section
    sections = {}
    for r in RESULTS:
        sections.setdefault(r.section, []).append(r)

    for sec_name, checks in sections.items():
        sec_pass = all(c.verdict != V.FAIL for c in checks)
        sec_tag = f"{G}PASS{E}" if sec_pass else f"{R}FAIL{E}"
        sec_warns = sum(1 for c in checks if c.verdict == V.WARN)
        warn_str = f" {Y}({sec_warns} warn){E}" if sec_warns else ""
        print(f"  {B}{sec_name}{E}  [{sec_tag}]{warn_str}")

        if VERBOSE or not sec_pass:
            for c in checks:
                if c.verdict == V.OK and not VERBOSE:
                    continue
                if c.verdict == V.OK:
                    tag = f"{G} OK {E}"
                elif c.verdict == V.FAIL:
                    tag = f"{R}FAIL{E}"
                elif c.verdict == V.WARN:
                    tag = f"{Y}WARN{E}"
                else:
                    tag = f"{D}SKIP{E}"
                detail = f" — {c.msg}" if c.msg else ""
                print(f"    [{tag}] {c.name}{D}{detail}{E}")
        print()

    print(f"{B}{'─'*70}{E}")
    print(f"  Total: {total}  |  {G}Pass: {passed}{E}  |  {R}Fail: {failed}{E}  |  {Y}Warn: {warned}{E}")

    if failed == 0 and warned == 0:
        print(f"\n  {G}{B}██ ALL SYSTEMS GREEN — READY TO BUILD ISO ██{E}\n")
    elif failed == 0:
        print(f"\n  {Y}{B}██ WARNINGS ONLY — BUILD AT OPERATOR DISCRETION ██{E}\n")
    else:
        print(f"\n  {R}{B}██ CRITICAL FAILURES — FIX BEFORE BUILD ██{E}\n")
        for r in RESULTS:
            if r.verdict == V.FAIL:
                print(f"    {R}✗{E} [{r.section}] {r.name}: {r.msg}")
        print()

    return 0 if failed == 0 and warned == 0 else (1 if failed > 0 else 2)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{C_CYAN}{B}TITAN V7.0.3 MASTER CODEBASE VERIFICATION{E}")
    print(f"{D}Scanning {REPO_ROOT}...{E}\n")

    verify_s1()
    verify_s2()
    verify_s3()
    verify_s4()
    verify_s5()
    verify_s6()
    verify_s7()
    verify_s8()
    verify_s9()
    verify_s10()

    code = print_report()
    sys.exit(code)

if __name__ == "__main__":
    main()
