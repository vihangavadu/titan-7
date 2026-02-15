#!/usr/bin/env python3
"""
LUCID TITAN V7.0 SINGULARITY — READINESS VERIFICATION PROTOCOL
PURPOSE: Pre-flight audit of all critical subsystems before deployment.
AUTHORITY: Dva.12 | OBLIVION KERNEL

Verifies:
  1. Source tree integrity (all core modules present)
  2. Ghost Motor behavioral engine (Bezier, tremors, dwell/flight)
  3. Kill Switch panic sequence (network sever + browser kill)
  4. WebRTC leak protection (consistent across all 4 layers)
  5. Canvas noise determinism (profile UUID seeding)
  6. Firewall default-deny (nftables policy drop)
  7. Sysctl kernel hardening (IPv6 disabled, ASLR, ptrace)
  8. Systemd service alignment (all services reference V7.0)
  9. Package list sanity (XFCE, no GNOME)
 10. Environment config completeness (titan.env)

Usage:
    python3 scripts/verify_v7_readiness.py          (from repo root)
    python3 /opt/titan/scripts/verify_v7_readiness.py  (on live ISO)
"""

import os
import re
import sys

# ── ANSI Colors ──────────────────────────────────────────────────────────────
class Col:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def log(status, message):
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT
    if status == "OK":
        PASS_COUNT += 1
        print(f"  [{Col.GREEN}PASS{Col.RESET}] {message}")
    elif status == "WARN":
        WARN_COUNT += 1
        print(f"  [{Col.YELLOW}WARN{Col.RESET}] {message}")
    elif status == "FAIL":
        FAIL_COUNT += 1
        print(f"  [{Col.RED}FAIL{Col.RESET}] {message}")


def section(title):
    print(f"\n{Col.CYAN}{Col.BOLD}{'═' * 60}{Col.RESET}")
    print(f"{Col.CYAN}{Col.BOLD}  {title}{Col.RESET}")
    print(f"{Col.CYAN}{Col.BOLD}{'═' * 60}{Col.RESET}")


def resolve_root():
    """Find the repo root or live ISO root."""
    # Running from repo
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    chroot = os.path.join(repo_root, "iso", "config", "includes.chroot")
    if os.path.isdir(chroot):
        return repo_root, chroot

    # Running on live ISO
    if os.path.isdir("/opt/titan/core"):
        return "/", "/"

    print(f"[{Col.RED}FATAL{Col.RESET}] Cannot locate TITAN source tree.")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 1: Source Tree Integrity
# ═══════════════════════════════════════════════════════════════════════════
def check_source_tree(chroot):
    section("1. SOURCE TREE INTEGRITY")
    titan_core = os.path.join(chroot, "opt", "titan", "core")

    required = [
        "genesis_core.py", "advanced_profile_generator.py",
        "cerberus_core.py", "cerberus_enhanced.py",
        "kill_switch.py", "fingerprint_injector.py",
        "ghost_motor_v6.py", "tls_parrot.py", "webgl_angle.py",
        "audio_hardener.py", "font_sanitizer.py", "timezone_enforcer.py",
        "network_jitter.py", "canvas_noise.py" if False else "lucid_vpn.py",
        "cockpit_daemon.py", "integration_bridge.py",
        "preflight_validator.py", "target_intelligence.py",
        "three_ds_strategy.py", "handover_protocol.py",
        "proxy_manager.py", "titan_env.py", "__init__.py",
        "hardware_shield_v6.c", "network_shield_v6.c",
    ]

    for mod in required:
        path = os.path.join(titan_core, mod)
        if os.path.isfile(path):
            log("OK", f"core/{mod}")
        else:
            log("FAIL", f"MISSING: core/{mod}")

    # Apps
    apps_dir = os.path.join(chroot, "opt", "titan", "apps")
    for app in ["app_unified.py", "app_genesis.py", "app_cerberus.py", "app_kyc.py"]:
        if os.path.isfile(os.path.join(apps_dir, app)):
            log("OK", f"apps/{app}")
        else:
            log("FAIL", f"MISSING: apps/{app}")

    # Ghost Motor extension
    gm_dir = os.path.join(chroot, "opt", "titan", "extensions", "ghost_motor")
    for ext in ["ghost_motor.js", "manifest.json"]:
        if os.path.isfile(os.path.join(gm_dir, ext)):
            log("OK", f"extensions/ghost_motor/{ext}")
        else:
            log("FAIL", f"MISSING: extensions/ghost_motor/{ext}")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 2: Ghost Motor Behavioral Engine
# ═══════════════════════════════════════════════════════════════════════════
def check_ghost_motor(chroot):
    section("2. GHOST MOTOR BEHAVIORAL ENGINE")

    # Python backend
    py_path = os.path.join(chroot, "opt", "titan", "core", "ghost_motor_v6.py")
    if os.path.isfile(py_path):
        content = open(py_path, "r", errors="ignore").read()
        for keyword, label in [
            ("bezier", "Bezier curve pathing"),
            ("micro_tremor", "Micro-tremor hand shake"),
            ("overshoot", "Overshoot simulation"),
            ("minimum.jerk|min.*jerk", "Minimum-jerk velocity"),
            ("correction_probability", "Mid-path correction"),
        ]:
            if re.search(keyword, content, re.IGNORECASE):
                log("OK", f"Python backend: {label}")
            else:
                log("FAIL", f"Python backend: {label} NOT FOUND")
    else:
        log("FAIL", "ghost_motor_v6.py not found")

    # JS extension
    js_path = os.path.join(chroot, "opt", "titan", "extensions", "ghost_motor", "ghost_motor.js")
    if os.path.isfile(js_path):
        content = open(js_path, "r", errors="ignore").read()
        for keyword, label in [
            ("bezierPoint", "JS Bezier curve function"),
            ("microTremor", "JS micro-tremor config"),
            ("overshootProbability", "JS overshoot probability"),
            ("dwellTimeBase", "JS keyboard dwell timing"),
            ("flightTimeBase", "JS keyboard flight timing"),
        ]:
            if keyword in content:
                log("OK", f"JS extension: {label}")
            else:
                log("FAIL", f"JS extension: {label} NOT FOUND")
    else:
        log("FAIL", "ghost_motor.js not found")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 3: Kill Switch Panic Sequence
# ═══════════════════════════════════════════════════════════════════════════
def check_kill_switch(chroot):
    section("3. KILL SWITCH PANIC SEQUENCE")
    ks_path = os.path.join(chroot, "opt", "titan", "core", "kill_switch.py")
    if not os.path.isfile(ks_path):
        log("FAIL", "kill_switch.py not found")
        return

    content = open(ks_path, "r", errors="ignore").read()
    for keyword, label in [
        ("_sever_network", "Step 0: Network sever (nftables DROP)"),
        ("_kill_browser", "Step 1: Browser kill"),
        ("_flush_hardware_id", "Step 2: Hardware ID flush (Netlink)"),
        ("_clear_session_data", "Step 3: Session data clear"),
        ("_rotate_proxy", "Step 4: Proxy rotation"),
        ("_randomize_mac", "Step 5: MAC randomization"),
        ("_restore_network", "Network restore (post-panic recovery)"),
    ]:
        if keyword in content:
            log("OK", label)
        else:
            log("FAIL", f"{label} — NOT FOUND")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 4: WebRTC Leak Protection (Cross-Module Consistency)
# ═══════════════════════════════════════════════════════════════════════════
def check_webrtc(chroot):
    section("4. WEBRTC LEAK PROTECTION (4-LAYER CHECK)")

    checks = [
        ("opt/titan/core/fingerprint_injector.py",
         "media.peerconnection.enabled.*False|peerconnection.enabled.*false",
         "fingerprint_injector: WebRTC disabled"),

        ("opt/lucid-empire/backend/modules/location_spoofer.py",
         "media.peerconnection.enabled.*False|peerconnection.enabled.*false",
         "location_spoofer: WebRTC disabled"),

        ("opt/lucid-empire/backend/handover_protocol.py",
         'peerconnection.enabled.*false',
         "handover_protocol: WebRTC disabled"),

        ("etc/nftables.conf",
         "3478.*5349.*19302.*drop",
         "nftables: STUN/TURN ports blocked"),
    ]

    for rel_path, pattern, label in checks:
        full = os.path.join(chroot, rel_path)
        if os.path.isfile(full):
            content = open(full, "r", errors="ignore").read()
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                log("OK", label)
            else:
                log("FAIL", f"{label} — PATTERN NOT MATCHED")
        else:
            log("WARN", f"{label} — file not found")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 5: Canvas Noise Determinism
# ═══════════════════════════════════════════════════════════════════════════
def check_canvas_noise(chroot):
    section("5. CANVAS NOISE DETERMINISM")
    cn_path = os.path.join(chroot, "opt", "lucid-empire", "backend", "modules", "canvas_noise.py")
    if not os.path.isfile(cn_path):
        log("WARN", "canvas_noise.py not found at lucid-empire path")
        return

    content = open(cn_path, "r", errors="ignore").read()
    for keyword, label in [
        ("from_profile_uuid", "Seed derived from profile UUID"),
        ("sha256", "SHA-256 hash for deterministic seed"),
        ("PerlinNoise", "Perlin noise generator"),
        ("deterministic", "Deterministic seeding documented"),
    ]:
        if re.search(keyword, content, re.IGNORECASE):
            log("OK", label)
        else:
            log("FAIL", f"{label} — NOT FOUND")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 6: Firewall Default-Deny
# ═══════════════════════════════════════════════════════════════════════════
def check_firewall(chroot):
    section("6. FIREWALL (nftables DEFAULT-DENY)")
    nft = os.path.join(chroot, "etc", "nftables.conf")
    if not os.path.isfile(nft):
        log("FAIL", "nftables.conf not found")
        return

    content = open(nft, "r", errors="ignore").read()
    for chain in ["input", "output", "forward"]:
        pattern = rf"chain\s+{chain}\s*\{{[^}}]*policy\s+drop"
        if re.search(pattern, content, re.DOTALL):
            log("OK", f"Chain '{chain}': policy drop")
        else:
            log("FAIL", f"Chain '{chain}': policy drop NOT SET")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 7: Sysctl Kernel Hardening
# ═══════════════════════════════════════════════════════════════════════════
def check_sysctl(chroot):
    section("7. KERNEL HARDENING (sysctl)")
    sysctl = os.path.join(chroot, "etc", "sysctl.d", "99-titan-hardening.conf")
    if not os.path.isfile(sysctl):
        log("FAIL", "99-titan-hardening.conf not found")
        return

    content = open(sysctl, "r", errors="ignore").read()
    for param, label in [
        ("net.ipv6.conf.all.disable_ipv6 = 1", "IPv6 fully disabled"),
        ("kernel.randomize_va_space = 2", "Full ASLR enabled"),
        ("kernel.yama.ptrace_scope = 2", "Ptrace restricted"),
        ("kernel.dmesg_restrict = 1", "dmesg restricted"),
        ("net.ipv4.tcp_syncookies = 1", "SYN cookies enabled"),
        ("net.core.bpf_jit_enable = 1", "eBPF JIT enabled"),
    ]:
        if param in content:
            log("OK", label)
        else:
            log("FAIL", f"{label} — NOT SET")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 8: Systemd Services
# ═══════════════════════════════════════════════════════════════════════════
def check_systemd(chroot):
    section("8. SYSTEMD SERVICES")
    svc_dir = os.path.join(chroot, "etc", "systemd", "system")
    if not os.path.isdir(svc_dir):
        log("FAIL", "systemd/system directory not found")
        return

    required = [
        "lucid-titan.service",
        "lucid-console.service",
        "lucid-ebpf.service",
        "titan-first-boot.service",
        "titan-dns.service",
    ]
    for svc in required:
        path = os.path.join(svc_dir, svc)
        if os.path.isfile(path):
            content = open(path, "r", errors="ignore").read()
            if "V7.0" in content or "V7" in content:
                log("OK", f"{svc} (V7.0 aligned)")
            else:
                log("WARN", f"{svc} exists but no V7.0 reference in Description")
        else:
            log("FAIL", f"MISSING: {svc}")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 9: Package List
# ═══════════════════════════════════════════════════════════════════════════
def check_packages(repo_root):
    section("9. PACKAGE LIST SANITY")
    pkg = os.path.join(repo_root, "iso", "config", "package-lists", "custom.list.chroot")
    if not os.path.isfile(pkg):
        log("WARN", "Package list not found (only needed for build)")
        return

    content = open(pkg, "r", errors="ignore").read()

    if "task-xfce-desktop" in content:
        log("OK", "Desktop: XFCE4 (lightweight)")
    else:
        log("FAIL", "Desktop: task-xfce-desktop MISSING")

    if "gnome-core" in content:
        log("FAIL", "Stale: gnome-core still in package list")
    else:
        log("OK", "No gnome-core (removed per V7.0 plan)")

    for pkg_name in ["nftables", "unbound", "libfaketime", "rofi", "dbus-x11"]:
        if pkg_name in content:
            log("OK", f"Package: {pkg_name}")
        else:
            log("FAIL", f"Package MISSING: {pkg_name}")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 10: Environment Config
# ═══════════════════════════════════════════════════════════════════════════
def check_env_config(chroot):
    section("10. ENVIRONMENT CONFIGURATION (titan.env)")
    env_path = os.path.join(chroot, "opt", "titan", "config", "titan.env")
    if not os.path.isfile(env_path):
        log("FAIL", "titan.env not found")
        return

    content = open(env_path, "r", errors="ignore").read()
    required_keys = [
        "TITAN_CLOUD_URL", "TITAN_API_KEY", "TITAN_PROXY_PROVIDER",
        "TITAN_VPN_SERVER_IP", "TITAN_VPN_UUID",
        "TITAN_EBPF_ENABLED", "TITAN_HW_SHIELD_ENABLED",
        "TITAN_PROFILES_DIR", "TITAN_STATE_DIR",
    ]
    for key in required_keys:
        if key in content:
            # Check if it's a placeholder
            line = [l for l in content.splitlines() if key in l and not l.strip().startswith("#")]
            if line and "REPLACE_WITH" in line[0]:
                log("WARN", f"{key}: placeholder (operator must configure)")
            else:
                log("OK", f"{key}: configured")
        else:
            log("FAIL", f"{key}: MISSING from titan.env")


# ═══════════════════════════════════════════════════════════════════════════
# CHECK 11: Stale Version References
# ═══════════════════════════════════════════════════════════════════════════
def check_stale_versions(chroot):
    section("11. STALE VERSION SCAN (V6 in runtime code)")
    stale_count = 0
    scan_dirs = [
        os.path.join(chroot, "opt", "titan", "core"),
        os.path.join(chroot, "opt", "titan", "apps"),
        os.path.join(chroot, "opt", "titan", "testing"),
        os.path.join(chroot, "opt", "lucid-empire", "backend"),
        os.path.join(chroot, "etc", "systemd", "system"),
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, _, files in os.walk(scan_dir):
            for fname in files:
                if not fname.endswith((".py", ".sh", ".service", ".conf")):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = open(fpath, "r", errors="ignore").read()
                    # Match "TITAN V6" but NOT "V6.2 Foundation (carried forward"
                    matches = re.findall(r'TITAN V6[.\s]', content)
                    # Filter out historical context references
                    for m in matches:
                        rel = os.path.relpath(fpath, chroot)
                        if "carried forward" not in content[max(0, content.index(m)-80):content.index(m)+80]:
                            log("FAIL", f"Stale V6 ref in {rel}")
                            stale_count += 1
                except Exception:
                    pass

    if stale_count == 0:
        log("OK", "No stale V6 references in runtime code")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print(f"\n{Col.GREEN}{Col.BOLD}")
    print("  ████████╗██╗████████╗ █████╗ ███╗   ██╗")
    print("  ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║")
    print("     ██║   ██║   ██║   ███████║██╔██╗ ██║")
    print("     ██║   ██║   ██║   ██╔══██║██║╚██╗██║")
    print("     ██║   ██║   ██║   ██║  ██║██║ ╚████║")
    print("     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝")
    print(f"  V7.0 SINGULARITY — READINESS VERIFICATION{Col.RESET}")

    repo_root, chroot = resolve_root()
    print(f"\n  Repo root: {repo_root}")
    print(f"  Chroot:    {chroot}")

    check_source_tree(chroot)
    check_ghost_motor(chroot)
    check_kill_switch(chroot)
    check_webrtc(chroot)
    check_canvas_noise(chroot)
    check_firewall(chroot)
    check_sysctl(chroot)
    check_systemd(chroot)
    check_packages(repo_root)
    check_env_config(chroot)
    check_stale_versions(chroot)

    # ── VERDICT ──────────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    total = PASS_COUNT + FAIL_COUNT + WARN_COUNT
    print(f"  {Col.GREEN}PASS: {PASS_COUNT}{Col.RESET}  |  "
          f"{Col.RED}FAIL: {FAIL_COUNT}{Col.RESET}  |  "
          f"{Col.YELLOW}WARN: {WARN_COUNT}{Col.RESET}  |  "
          f"TOTAL: {total}")

    if FAIL_COUNT == 0:
        pct = (PASS_COUNT / total * 100) if total else 0
        print(f"\n  {Col.GREEN}{Col.BOLD}>>> SYSTEM STATUS: OPERATIONAL <<<{Col.RESET}")
        print(f"  {Col.GREEN}Confidence: {pct:.1f}%  |  CLEARED FOR DEPLOYMENT{Col.RESET}")
    else:
        print(f"\n  {Col.RED}{Col.BOLD}>>> SYSTEM STATUS: NOT READY <<<{Col.RESET}")
        print(f"  {Col.RED}{FAIL_COUNT} critical issue(s) must be resolved.{Col.RESET}")

    print(f"{'═' * 60}\n")
    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
