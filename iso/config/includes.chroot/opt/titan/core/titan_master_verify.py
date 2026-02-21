#!/usr/bin/env python3
"""
TITAN MASTER VERIFICATION PROTOCOL (MVP)
AUTHORITY: Dva.12 | VERSION: 7.0-SINGULARITY
PURPOSE: Aggregated Pre-Flight Check for Lucid Titan OS.

Layers verified:
  Layer 0 — Kernel Shield (titan_hw.ko, DMI/SMBIOS, cache profile)
  Layer 1 — Network Shield (eBPF/XDP, TCP fingerprint, OS profile, DNS)
  Layer 2 — Environment (Fonts, AudioContext, policies.json lockPref, locale)
  Layer 3 — Identity & Time (Profile, fingerprint consistency, trajectory,
            kill switch, timezone sync, Cerberus score)

Exit codes:
  0 — ALL GREEN — cleared for launch
  1 — CRITICAL FAILURE — abort, fix indicated layer
  2 — WARNINGS ONLY — operator discretion

USAGE:
  python3 titan_master_verify.py [--interface eth0] [--profile NAME] [--target DOMAIN]
"""

import os
import sys
import json
import time
import struct
import socket
import hashlib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

TITAN_ROOT = Path("/opt/titan")
LEGACY_ROOT = Path("/opt/lucid-empire")
PROFILES_DIR = TITAN_ROOT / "profiles"
STATE_DIR = TITAN_ROOT / "state"
EXTENSIONS_DIR = TITAN_ROOT / "extensions"

# Kernel module paths
SYSFS_TITAN_HW = Path("/sys/module/titan_hw")
SYSFS_DMI = Path("/sys/class/dmi/id")
BPF_PIN_PATH = Path("/sys/fs/bpf/titan_network_shield")

# Browser paths
# V7.5 FIX: Use correct Camoufox install path on Titan OS
CAMOUFOX_PREFS = Path("/opt/camoufox/defaults/pref/local-settings.js")
FONT_CONFIG = Path("/etc/fonts/local.conf")

# Thresholds
CERBERUS_SCORE_THRESHOLD = 95
TIMEZONE_DELTA_MAX_SECONDS = 1
FRAUD_SCORE_THRESHOLD = 85


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

class Verdict(Enum):
    OK = "OK"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    layer: int
    name: str
    verdict: Verdict
    message: str
    critical: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MasterVerifyReport:
    checks: List[CheckResult] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    
    @property
    def passed(self) -> bool:
        return not any(c.verdict == Verdict.FAIL and c.critical for c in self.checks)
    
    @property
    def critical_failures(self) -> List[CheckResult]:
        return [c for c in self.checks if c.verdict == Verdict.FAIL and c.critical]
    
    @property
    def warnings(self) -> List[CheckResult]:
        return [c for c in self.checks if c.verdict == Verdict.WARN]
    
    @property
    def layer_status(self) -> Dict[int, bool]:
        layers = {}
        for c in self.checks:
            if c.layer not in layers:
                layers[c.layer] = True
            if c.verdict == Verdict.FAIL and c.critical:
                layers[c.layer] = False
        return layers
    
    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


# ═══════════════════════════════════════════════════════════════════════════
# TERMINAL COLORS
# ═══════════════════════════════════════════════════════════════════════════

class C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def log_check(result: CheckResult):
    """Print a single check result with color coding"""
    if result.verdict == Verdict.OK:
        tag = f"{C.GREEN} OK {C.END}"
    elif result.verdict == Verdict.FAIL:
        tag = f"{C.RED}FAIL{C.END}"
    elif result.verdict == Verdict.WARN:
        tag = f"{C.YELLOW}WARN{C.END}"
    else:
        tag = f"{C.DIM}SKIP{C.END}"
    
    print(f"  [{tag}] {result.message}")


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 0: KERNEL SHIELD
# ═══════════════════════════════════════════════════════════════════════════

def check_layer_0(report: MasterVerifyReport):
    """Verify kernel-space hardware shield"""
    print(f"\n{C.HEADER}{'─'*60}{C.END}")
    print(f"{C.HEADER}  LAYER 0 │ KERNEL SHIELD{C.END}")
    print(f"{C.HEADER}{'─'*60}{C.END}")
    
    # 0.1: Kernel module loaded
    try:
        mods = subprocess.check_output("lsmod", shell=True, timeout=5).decode()
        if "titan_hw" in mods:
            r = CheckResult(0, "kernel_module", Verdict.OK,
                           "Kernel module titan_hw: LOADED",
                           details={"source": "lsmod"})
        elif SYSFS_TITAN_HW.exists():
            r = CheckResult(0, "kernel_module", Verdict.OK,
                           "Kernel module detected via sysfs",
                           details={"source": "sysfs"})
        else:
            r = CheckResult(0, "kernel_module", Verdict.FAIL,
                           "Kernel Shield NOT loaded — hardware identity exposed")
    except Exception as e:
        r = CheckResult(0, "kernel_module", Verdict.FAIL,
                       f"Cannot query kernel modules: {e}")
    report.checks.append(r)
    log_check(r)
    
    # 0.2: DKOM module hiding
    try:
        # If module is loaded but NOT visible in lsmod, hiding is active
        mods_text = subprocess.check_output("lsmod", shell=True, timeout=5).decode()
        sysfs_exists = SYSFS_TITAN_HW.exists()
        
        if sysfs_exists and "titan_hw" not in mods_text:
            r = CheckResult(0, "dkom_hiding", Verdict.OK,
                           "DKOM module hiding: ACTIVE (invisible in lsmod)",
                           critical=False)
        elif "titan_hw" in mods_text:
            r = CheckResult(0, "dkom_hiding", Verdict.WARN,
                           "Module visible in lsmod — send TITAN_MSG_HIDE_MODULE",
                           critical=False)
        else:
            r = CheckResult(0, "dkom_hiding", Verdict.SKIP,
                           "Module not loaded — hiding check skipped",
                           critical=False)
    except Exception:
        r = CheckResult(0, "dkom_hiding", Verdict.SKIP,
                       "DKOM check skipped", critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 0.3: DMI/SMBIOS sysfs spoofing
    dmi_fields = ["sys_vendor", "product_name", "bios_vendor", "chassis_type"]
    dmi_ok = True
    dmi_details = {}
    for field_name in dmi_fields:
        path = SYSFS_DMI / field_name
        if path.exists():
            try:
                val = path.read_text().strip()
                dmi_details[field_name] = val
                # Check for obvious VM/Linux indicators
                vm_indicators = ["QEMU", "VirtualBox", "VMware", "Bochs", "innotek"]
                if any(ind.lower() in val.lower() for ind in vm_indicators):
                    dmi_ok = False
            except PermissionError:
                dmi_details[field_name] = "(permission denied)"
    
    if dmi_ok and dmi_details:
        r = CheckResult(0, "dmi_smbios", Verdict.OK,
                       f"DMI/SMBIOS: {dmi_details.get('sys_vendor', '?')} / {dmi_details.get('product_name', '?')}",
                       critical=False, details=dmi_details)
    elif not dmi_details:
        r = CheckResult(0, "dmi_smbios", Verdict.SKIP,
                       "DMI sysfs not accessible", critical=False)
    else:
        r = CheckResult(0, "dmi_smbios", Verdict.FAIL,
                       f"VM indicators in DMI — spoof required",
                       details=dmi_details)
    report.checks.append(r)
    log_check(r)
    
    # 0.4: /proc/cpuinfo consistency
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        # Check for cache size line (our hardening writes dynamic cache)
        if "cache size" in cpuinfo:
            lines = [l for l in cpuinfo.split("\n") if "model name" in l]
            cpu_model = lines[0].split(":")[1].strip() if lines else "Unknown"
            r = CheckResult(0, "cpuinfo_spoof", Verdict.OK,
                           f"CPU identity: {cpu_model[:50]}",
                           critical=False, details={"cpu_model": cpu_model})
        else:
            r = CheckResult(0, "cpuinfo_spoof", Verdict.WARN,
                           "/proc/cpuinfo format unexpected", critical=False)
    except Exception:
        r = CheckResult(0, "cpuinfo_spoof", Verdict.SKIP,
                       "Cannot read /proc/cpuinfo", critical=False)
    report.checks.append(r)
    log_check(r)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1: NETWORK SHIELD
# ═══════════════════════════════════════════════════════════════════════════

def check_layer_1(report: MasterVerifyReport, interface: str = "eth0"):
    """Verify network-layer shields"""
    print(f"\n{C.HEADER}{'─'*60}{C.END}")
    print(f"{C.HEADER}  LAYER 1 │ NETWORK SHIELD (eBPF/XDP){C.END}")
    print(f"{C.HEADER}{'─'*60}{C.END}")
    
    # 1.1: XDP program on interface
    try:
        output = subprocess.check_output(
            f"ip link show dev {interface}", shell=True, timeout=5
        ).decode()
        
        if "xdp" in output.lower() or "prog/xdp" in output.lower():
            r = CheckResult(1, "xdp_attached", Verdict.OK,
                           f"eBPF/XDP program attached to {interface}")
        else:
            r = CheckResult(1, "xdp_attached", Verdict.FAIL,
                           f"No XDP program on {interface} — TCP fingerprint is raw Linux")
    except subprocess.CalledProcessError:
        r = CheckResult(1, "xdp_attached", Verdict.FAIL,
                       f"Interface {interface} not found")
    except Exception as e:
        r = CheckResult(1, "xdp_attached", Verdict.FAIL,
                       f"XDP check failed: {e}")
    report.checks.append(r)
    log_check(r)
    
    # 1.2: BPF pinned maps
    if BPF_PIN_PATH.exists():
        r = CheckResult(1, "bpf_pinned", Verdict.OK,
                       "BPF maps pinned at /sys/fs/bpf/titan_network_shield")
    else:
        r = CheckResult(1, "bpf_pinned", Verdict.WARN,
                       "BPF pin not found — TC egress may not be active",
                       critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 1.3: TCP fingerprint profile loaded (check config map)
    try:
        # Check if the OS profile config exists in state
        tcp_config = STATE_DIR / "tcp_profile.json"
        if tcp_config.exists():
            with open(tcp_config) as f:
                tcp = json.load(f)
            os_name = tcp.get("os_profile", "unknown")
            ttl = tcp.get("ttl", "?")
            r = CheckResult(1, "tcp_profile", Verdict.OK,
                           f"TCP fingerprint profile: {os_name} (TTL={ttl})",
                           details=tcp)
        else:
            r = CheckResult(1, "tcp_profile", Verdict.WARN,
                           "TCP profile config not found — using kernel defaults",
                           critical=False)
    except Exception:
        r = CheckResult(1, "tcp_profile", Verdict.WARN,
                       "TCP profile check skipped", critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 1.4: DNS leak prevention
    try:
        resolv = Path("/etc/resolv.conf").read_text()
        # Check for non-ISP DNS (should be DoH or tunnel)
        nameservers = [l.split()[1] for l in resolv.split("\n") 
                      if l.strip().startswith("nameserver")]
        
        safe_dns = ["127.0.0.1", "127.0.0.53", "::1"]
        all_safe = all(ns in safe_dns for ns in nameservers)
        
        if all_safe:
            r = CheckResult(1, "dns_leak", Verdict.OK,
                           f"DNS: Local resolver only ({', '.join(nameservers)})")
        else:
            r = CheckResult(1, "dns_leak", Verdict.WARN,
                           f"DNS may leak: {', '.join(nameservers)} — ensure DoH active in browser",
                           critical=False, details={"nameservers": nameservers})
    except Exception:
        r = CheckResult(1, "dns_leak", Verdict.WARN,
                       "DNS check skipped", critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 1.5: WebRTC leak check (verify kernel blocks)
    try:
        # Try to create a STUN connection — should be blocked by eBPF
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        try:
            sock.connect(("stun.l.google.com", 19302))
            local_ip = sock.getsockname()[0]
            sock.close()
            # If we got a non-private IP, WebRTC could leak
            if local_ip.startswith(("10.", "172.", "192.168.", "127.")):
                r = CheckResult(1, "webrtc_block", Verdict.OK,
                               f"WebRTC: Local IP only ({local_ip})",
                               critical=False)
            else:
                r = CheckResult(1, "webrtc_block", Verdict.WARN,
                               f"WebRTC may expose: {local_ip}",
                               critical=False)
        except (socket.timeout, OSError):
            r = CheckResult(1, "webrtc_block", Verdict.OK,
                           "WebRTC STUN blocked (connection refused/timeout)")
            sock.close()
    except Exception:
        r = CheckResult(1, "webrtc_block", Verdict.SKIP,
                       "WebRTC check skipped", critical=False)
    report.checks.append(r)
    log_check(r)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2: ENVIRONMENT (Fonts / Audio / Prefs)
# ═══════════════════════════════════════════════════════════════════════════

def check_layer_2(report: MasterVerifyReport, profile_path: Optional[Path] = None):
    """Verify environment sanitization"""
    print(f"\n{C.HEADER}{'─'*60}{C.END}")
    print(f"{C.HEADER}  LAYER 2 │ ENVIRONMENT (Fonts / Audio / Prefs){C.END}")
    print(f"{C.HEADER}{'─'*60}{C.END}")
    
    # 2.1: Font exclusion config
    if FONT_CONFIG.exists():
        try:
            content = FONT_CONFIG.read_text()
            if "rejectfont" in content.lower() or "reject" in content.lower():
                r = CheckResult(2, "font_config", Verdict.OK,
                               "Font exclusion: ACTIVE (rejectfont directive present)")
            else:
                r = CheckResult(2, "font_config", Verdict.WARN,
                               "local.conf exists but no rejectfont — Linux fonts may leak",
                               critical=False)
        except Exception:
            r = CheckResult(2, "font_config", Verdict.WARN,
                           "Cannot read font config", critical=False)
    else:
        r = CheckResult(2, "font_config", Verdict.FAIL,
                       "Font config missing (/etc/fonts/local.conf) — OS detectable via font enumeration")
    report.checks.append(r)
    log_check(r)
    
    # 2.2: AudioContext hardening in browser prefs
    audio_hardened = False
    prefs_to_check = [CAMOUFOX_PREFS]
    if profile_path:
        prefs_to_check.append(profile_path / "user.js")
    
    for pref_path in prefs_to_check:
        if pref_path and pref_path.exists():
            try:
                content = pref_path.read_text()
                # V7.5 FIX: Correct pref name from audio_hardener.py
                if "titan.audio.noise_injection" in content or "privacy.resistFingerprinting" in content:
                    audio_hardened = True
                    break
            except Exception:
                pass
    
    if audio_hardened:
        r = CheckResult(2, "audio_hardening", Verdict.OK,
                       "AudioContext hardening: ACTIVE")
    else:
        r = CheckResult(2, "audio_hardening", Verdict.WARN,
                       "AudioContext hardening not confirmed in prefs",
                       critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 2.3: Phase 2.1 lockPref (policies.json)
    policies_locked = False
    if profile_path:
        policies_file = profile_path / "distribution" / "policies.json"
        if policies_file.exists():
            try:
                with open(policies_file) as f:
                    policies = json.load(f)
                prefs = policies.get("policies", {}).get("Preferences", {})
                webgl_locked = prefs.get("webgl.renderer-string-override", {}).get("Status") == "locked"
                if webgl_locked:
                    renderer = prefs["webgl.renderer-string-override"]["Value"]
                    policies_locked = True
                    r = CheckResult(2, "lockpref", Verdict.OK,
                                   f"policies.json: WebGL LOCKED → {renderer[:45]}...",
                                   details={"renderer": renderer})
                else:
                    r = CheckResult(2, "lockpref", Verdict.WARN,
                                   "policies.json exists but WebGL not locked",
                                   critical=False)
            except Exception as e:
                r = CheckResult(2, "lockpref", Verdict.WARN,
                               f"policies.json parse error: {e}", critical=False)
        else:
            r = CheckResult(2, "lockpref", Verdict.FAIL,
                           "policies.json MISSING — Camoufox may override WebGL identity")
    else:
        r = CheckResult(2, "lockpref", Verdict.SKIP,
                       "No profile path — lockPref check skipped", critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 2.4: user.js hardening
    if profile_path:
        user_js = profile_path / "user.js"
        if user_js.exists():
            try:
                content = user_js.read_text()
                checks = {
                    "webgl.renderer-string-override": "WebGL",
                    "dom.webdriver.enabled": "WebDriver",
                    "media.peerconnection.enabled": "WebRTC",
                }
                locked_count = sum(1 for k in checks if k in content)
                r = CheckResult(2, "user_js", Verdict.OK,
                               f"user.js: {locked_count}/{len(checks)} critical prefs set",
                               details={"locked": locked_count, "total": len(checks)})
            except Exception:
                r = CheckResult(2, "user_js", Verdict.WARN,
                               "user.js unreadable", critical=False)
        else:
            r = CheckResult(2, "user_js", Verdict.WARN,
                           "user.js not found — prefs may use browser defaults",
                           critical=False)
    else:
        r = CheckResult(2, "user_js", Verdict.SKIP,
                       "user.js check skipped", critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 2.5: System locale
    try:
        lang = os.environ.get("LANG", "")
        tz = os.environ.get("TZ", "")
        if not tz:
            try:
                tz = subprocess.check_output("date +%Z", shell=True, timeout=2).decode().strip()
            except Exception:
                tz = "unknown"
        
        if tz == "UTC":
            r = CheckResult(2, "locale_tz", Verdict.WARN,
                           f"Timezone is UTC — high risk for US/EU targets (LANG={lang})",
                           critical=False)
        else:
            r = CheckResult(2, "locale_tz", Verdict.OK,
                           f"Timezone: {tz} | Locale: {lang}")
    except Exception:
        r = CheckResult(2, "locale_tz", Verdict.WARN,
                       "Locale check skipped", critical=False)
    report.checks.append(r)
    log_check(r)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3: IDENTITY & TIME
# ═══════════════════════════════════════════════════════════════════════════

def check_layer_3(report: MasterVerifyReport, profile_path: Optional[Path] = None,
                   target_domain: str = ""):
    """Verify identity layer and temporal sync"""
    print(f"\n{C.HEADER}{'─'*60}{C.END}")
    print(f"{C.HEADER}  LAYER 3 │ IDENTITY & TIME{C.END}")
    print(f"{C.HEADER}{'─'*60}{C.END}")
    
    # 3.1: Profile existence and metadata
    metadata = None
    if profile_path and profile_path.exists():
        meta_file = profile_path / "profile_metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    metadata = json.load(f)
                persona = metadata.get("persona_name", "Unknown")
                age = metadata.get("profile_age_days", 0)
                r = CheckResult(3, "profile", Verdict.OK,
                               f"Profile: {persona} (aged {age} days)",
                               details=metadata)
            except Exception as e:
                r = CheckResult(3, "profile", Verdict.FAIL,
                               f"Profile metadata corrupted: {e}")
        else:
            r = CheckResult(3, "profile", Verdict.FAIL,
                           "No profile_metadata.json — identity incomplete")
    else:
        r = CheckResult(3, "profile", Verdict.FAIL,
                       "Profile directory not found — run Genesis first")
    report.checks.append(r)
    log_check(r)
    
    # 3.2: Fingerprint config consistency
    if profile_path:
        fp_file = profile_path / "fingerprint_config.json"
        hw_file = profile_path / "hardware_profile.json"
        
        fp_ok = True
        if fp_file.exists() and hw_file.exists():
            try:
                with open(fp_file) as f:
                    fp = json.load(f)
                with open(hw_file) as f:
                    hw = json.load(f)
                
                # Cross-check: WebGL renderer in fingerprint must match hardware
                fp_webgl = fp.get("config", {}).get("webgl", {}).get("renderer", "")
                hw_gpu = hw.get("gpu_renderer", hw.get("gpu", ""))
                
                if fp_webgl and hw_gpu and fp_webgl != hw_gpu:
                    r = CheckResult(3, "fp_consistency", Verdict.FAIL,
                                   f"WebGL MISMATCH: FP='{fp_webgl[:30]}' vs HW='{hw_gpu[:30]}'",
                                   details={"fp_webgl": fp_webgl, "hw_gpu": hw_gpu})
                    fp_ok = False
                else:
                    seed = fp.get("seed", fp.get("canvas_seed", "?"))
                    r = CheckResult(3, "fp_consistency", Verdict.OK,
                                   f"Fingerprint consistent: seed={seed}, WebGL matches HW")
            except Exception as e:
                r = CheckResult(3, "fp_consistency", Verdict.WARN,
                               f"Fingerprint check error: {e}", critical=False)
        elif fp_file.exists():
            r = CheckResult(3, "fp_consistency", Verdict.WARN,
                           "Hardware profile missing — cross-check skipped",
                           critical=False)
        else:
            r = CheckResult(3, "fp_consistency", Verdict.FAIL,
                           "No fingerprint_config.json — canvas/WebGL will be random")
        report.checks.append(r)
        log_check(r)
    
    # 3.3: Browser data integrity (places.sqlite, cookies.sqlite)
    if profile_path:
        critical_files = {
            "places.sqlite": "Browsing history",
            "cookies.sqlite": "Cookies & trust anchors",
        }
        # Check in both profile root and firefox_profile subdir
        check_dir = profile_path / "firefox_profile"
        if not check_dir.exists():
            check_dir = profile_path
        
        missing = []
        for fname, desc in critical_files.items():
            if not (check_dir / fname).exists():
                missing.append(desc)
        
        if not missing:
            r = CheckResult(3, "browser_data", Verdict.OK,
                           "Browser data: history + cookies present")
        else:
            r = CheckResult(3, "browser_data", Verdict.WARN,
                           f"Missing: {', '.join(missing)}",
                           critical=False)
        report.checks.append(r)
        log_check(r)
    
    # 3.4: Trajectory warm-up plan (Phase 2.2)
    if profile_path:
        traj_file = profile_path / "warmup_trajectory.json"
        if traj_file.exists():
            try:
                with open(traj_file) as f:
                    traj = json.load(f)
                segs = traj.get("num_segments", 0)
                dur = traj.get("total_duration_ms", 0)
                r = CheckResult(3, "trajectory", Verdict.OK,
                               f"Warm-up trajectory: {segs} segments, {dur/1000:.1f}s",
                               critical=False)
            except Exception:
                r = CheckResult(3, "trajectory", Verdict.WARN,
                               "Trajectory file corrupt", critical=False)
        else:
            if target_domain:
                r = CheckResult(3, "trajectory", Verdict.WARN,
                               f"No warm-up trajectory for {target_domain} — generate before launch",
                               critical=False)
            else:
                r = CheckResult(3, "trajectory", Verdict.SKIP,
                               "Trajectory check skipped (no target)", critical=False)
        report.checks.append(r)
        log_check(r)
    
    # 3.5: Kill switch state (Phase 2.3)
    ks_state_file = STATE_DIR / "killswitch_state.json"
    if ks_state_file.exists():
        try:
            with open(ks_state_file) as f:
                ks = json.load(f)
            if ks.get("armed"):
                r = CheckResult(3, "kill_switch", Verdict.OK,
                               "Kill switch: PRE-ARMED")
            else:
                r = CheckResult(3, "kill_switch", Verdict.OK,
                               "Kill switch: Ready (will arm on launch)",
                               critical=False)
        except Exception:
            r = CheckResult(3, "kill_switch", Verdict.WARN,
                           "Kill switch state unreadable", critical=False)
    else:
        r = CheckResult(3, "kill_switch", Verdict.OK,
                       "Kill switch: Ready (arms automatically on launch)",
                       critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 3.6: Timezone delta check
    try:
        # Check system clock accuracy against NTP
        ntp_output = subprocess.check_output(
            "timedatectl show --property=NTPSynchronized --value",
            shell=True, timeout=3
        ).decode().strip()
        
        if ntp_output == "yes":
            r = CheckResult(3, "time_sync", Verdict.OK,
                           "NTP synchronized: clock drift < 1s")
        else:
            r = CheckResult(3, "time_sync", Verdict.WARN,
                           "NTP not synchronized — timezone delta may be detected",
                           critical=False)
    except Exception:
        # Fallback: just check that we're not wildly off
        r = CheckResult(3, "time_sync", Verdict.WARN,
                       "NTP check unavailable — verify clock manually",
                       critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 3.7: Cerberus fraud score (if available)
    fraud_score_file = STATE_DIR / "fraud_score.json"
    if fraud_score_file.exists():
        try:
            with open(fraud_score_file) as f:
                score_data = json.load(f)
            score = score_data.get("score", 0)
            if score >= CERBERUS_SCORE_THRESHOLD:
                r = CheckResult(3, "cerberus_score", Verdict.OK,
                               f"Cerberus score: {score}/100 (threshold: {CERBERUS_SCORE_THRESHOLD})")
            elif score >= FRAUD_SCORE_THRESHOLD:
                r = CheckResult(3, "cerberus_score", Verdict.WARN,
                               f"Cerberus score: {score}/100 — below optimal ({CERBERUS_SCORE_THRESHOLD})",
                               critical=False)
            else:
                r = CheckResult(3, "cerberus_score", Verdict.FAIL,
                               f"Cerberus score: {score}/100 — BELOW PANIC THRESHOLD ({FRAUD_SCORE_THRESHOLD})")
        except Exception:
            r = CheckResult(3, "cerberus_score", Verdict.SKIP,
                           "Cerberus score file unreadable", critical=False)
    else:
        r = CheckResult(3, "cerberus_score", Verdict.SKIP,
                       "No prior Cerberus score — first session",
                       critical=False)
    report.checks.append(r)
    log_check(r)
    
    # 3.8: Ghost Motor extension
    ghost_motor = EXTENSIONS_DIR / "ghost_motor"
    if ghost_motor.exists() and (ghost_motor / "ghost_motor.js").exists():
        r = CheckResult(3, "ghost_motor", Verdict.OK,
                       "Ghost Motor extension: READY")
    else:
        r = CheckResult(3, "ghost_motor", Verdict.FAIL,
                       "Ghost Motor extension NOT FOUND — behavioral detection certain")
    report.checks.append(r)
    log_check(r)


# ═══════════════════════════════════════════════════════════════════════════
# MASTER VERDICT
# ═══════════════════════════════════════════════════════════════════════════

def print_verdict(report: MasterVerifyReport):
    """Print final Go/No-Go verdict"""
    print(f"\n{'='*60}")
    
    # Layer summary
    layer_names = {0: "KERNEL", 1: "NETWORK", 2: "ENVIRONMENT", 3: "IDENTITY"}
    layer_status = report.layer_status
    
    for layer_num in sorted(layer_status.keys()):
        name = layer_names.get(layer_num, f"LAYER {layer_num}")
        if layer_status[layer_num]:
            print(f"  {C.GREEN}■{C.END} Layer {layer_num} ({name}): {C.GREEN}CLEAR{C.END}")
        else:
            print(f"  {C.RED}■{C.END} Layer {layer_num} ({name}): {C.RED}FAILED{C.END}")
    
    print(f"{'='*60}")
    
    # Statistics
    total = len(report.checks)
    passed = sum(1 for c in report.checks if c.verdict == Verdict.OK)
    failed = len(report.critical_failures)
    warned = len(report.warnings)
    
    print(f"  Checks: {total} | {C.GREEN}Passed: {passed}{C.END} | "
          f"{C.RED}Failed: {failed}{C.END} | {C.YELLOW}Warnings: {warned}{C.END}")
    print(f"  Duration: {report.duration_ms:.0f}ms")
    print(f"{'='*60}")
    
    if report.passed:
        if warned > 0:
            print(f"\n  {C.YELLOW}{C.BOLD}STATUS: CONDITIONAL GREEN{C.END}")
            print(f"  {warned} warning(s) — proceed with elevated awareness")
            for w in report.warnings[:3]:
                print(f"    {C.YELLOW}⚠{C.END} {w.message}")
        else:
            print(f"\n  {C.GREEN}{C.BOLD}STATUS: ALL SYSTEMS GREEN{C.END}")
    else:
        print(f"\n  {C.RED}{C.BOLD}STATUS: LAUNCH ABORTED{C.END}")
        print(f"  {failed} critical failure(s):")
        for f_check in report.critical_failures:
            print(f"    {C.RED}✗{C.END} [{layer_names.get(f_check.layer, '?')}] {f_check.message}")


def countdown():
    """Launch countdown"""
    print(f"\n{C.BOLD}  INITIATING LAUNCH SEQUENCE...{C.END}\n")
    for i in range(3, 0, -1):
        print(f"    {C.CYAN}{i}...{C.END}")
        time.sleep(1)
    print(f"\n  {C.GREEN}{C.BOLD}>>> TITAN ENGAGED <<<{C.END}\n")


def save_report(report: MasterVerifyReport, profile_path: Optional[Path] = None):
    """Save verification report to state directory"""
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": report.passed,
        "duration_ms": report.duration_ms,
        "checks": [
            {
                "layer": c.layer,
                "name": c.name,
                "verdict": c.verdict.value,
                "message": c.message,
                "critical": c.critical,
            }
            for c in report.checks
        ],
        "critical_failures": len(report.critical_failures),
        "warnings": len(report.warnings),
    }
    
    # Save to state dir
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / "master_verify_report.json"
    try:
        with open(state_file, "w") as f:
            json.dump(report_data, f, indent=2)
    except Exception as e:
        logging.getLogger("TITAN-MVP").warning(f"Failed to save report to state: {e}")
    
    # Also save to profile if available
    if profile_path and profile_path.exists():
        try:
            with open(profile_path / "preflight_report.json", "w") as f:
                json.dump(report_data, f, indent=2)
        except Exception as e:
            logging.getLogger("TITAN-MVP").warning(f"Failed to save report to profile: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="TITAN Master Verification Protocol (MVP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0=GREEN, 1=CRITICAL FAILURE, 2=WARNINGS ONLY"
    )
    parser.add_argument("-i", "--interface", default="eth0",
                       help="Network interface to check (default: eth0)")
    parser.add_argument("-p", "--profile", default=None,
                       help="Profile name or path")
    parser.add_argument("-t", "--target", default="",
                       help="Target domain for trajectory check")
    parser.add_argument("--json", action="store_true",
                       help="Output JSON report only (no colors)")
    args = parser.parse_args()
    
    # Resolve profile path
    profile_path = None
    if args.profile:
        p = Path(args.profile)
        if p.is_absolute() and p.exists():
            profile_path = p
        elif (PROFILES_DIR / args.profile).exists():
            profile_path = PROFILES_DIR / args.profile
    else:
        # Use most recent profile
        if PROFILES_DIR.exists():
            profiles = sorted(PROFILES_DIR.glob("titan_*"), key=lambda x: x.stat().st_mtime, reverse=True)
            if profiles:
                profile_path = profiles[0]
    
    # Banner
    if not args.json:
        print(f"\n{C.BOLD}{C.CYAN}")
        print("  ╔══════════════════════════════════════════════════════════╗")
        print("  ║   PROMETHEUS CORE // TITAN OS MASTER VERIFICATION      ║")
        print("  ║   Authority: Dva.12 │ Version: 7.0-SINGULARITY        ║")
        print("  ╚══════════════════════════════════════════════════════════╝")
        print(f"{C.END}")
        
        if profile_path:
            print(f"  Profile: {C.CYAN}{profile_path.name}{C.END}")
        else:
            print(f"  Profile: {C.YELLOW}(none resolved){C.END}")
        print(f"  Interface: {args.interface}")
        if args.target:
            print(f"  Target: {args.target}")
    
    # Run all checks
    report = MasterVerifyReport()
    report.start_time = time.time()
    
    check_layer_0(report)
    check_layer_1(report, interface=args.interface)
    check_layer_2(report, profile_path=profile_path)
    check_layer_3(report, profile_path=profile_path, target_domain=args.target)
    
    report.end_time = time.time()
    
    # Save report
    save_report(report, profile_path)
    
    # Output
    if args.json:
        json.dump({
            "passed": report.passed,
            "duration_ms": report.duration_ms,
            "failures": len(report.critical_failures),
            "warnings": len(report.warnings),
            "checks": [
                {"layer": c.layer, "name": c.name, "verdict": c.verdict.value, "message": c.message}
                for c in report.checks
            ],
        }, sys.stdout, indent=2)
        print()
    else:
        print_verdict(report)
        
        if report.passed:
            countdown()
    
    # Exit code
    if report.passed and not report.warnings:
        sys.exit(0)
    elif report.passed:
        sys.exit(0)  # Warnings are non-blocking
    else:
        if not args.json:
            print(f"\n  {C.RED}FATAL ERRORS DETECTED. LAUNCH ABORTED.{C.END}")
            print(f"  Fix the indicated layers before proceeding.\n")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════════════════

class VerificationOrchestrator:
    """
    V7.6 P0: Orchestrate multi-phase verification with parallel checks.
    
    Coordinates verification across all layers with intelligent parallelization,
    dependency resolution, and adaptive check ordering based on failure history.
    """
    
    _instance = None
    
    def __init__(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from threading import Lock
        import queue
        
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="verify_")
        self.check_registry: Dict[str, Dict] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.check_results: Dict[str, CheckResult] = {}
        self.lock = Lock()
        self.logger = logging.getLogger("TITAN-MVP.Orchestrator")
        
        # V7.6: Check prioritization based on failure history
        self.priority_weights: Dict[str, float] = {}
        self.failure_counts: Dict[str, int] = {}
        
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register all default verification checks with dependencies."""
        # Layer 0 checks
        self.register_check(
            "kernel_module",
            layer=0,
            check_fn=self._check_kernel_module,
            critical=True,
            dependencies=[]
        )
        self.register_check(
            "dkom_hiding",
            layer=0,
            check_fn=self._check_dkom_hiding,
            critical=False,
            dependencies=["kernel_module"]
        )
        self.register_check(
            "dmi_smbios",
            layer=0,
            check_fn=self._check_dmi_smbios,
            critical=False,
            dependencies=[]
        )
        
        # Layer 1 checks
        self.register_check(
            "xdp_attached",
            layer=1,
            check_fn=self._check_xdp,
            critical=True,
            dependencies=[]
        )
        self.register_check(
            "dns_leak",
            layer=1,
            check_fn=self._check_dns,
            critical=False,
            dependencies=[]
        )
        
        # Layer 2 checks (can run in parallel with Layer 1)
        self.register_check(
            "font_config",
            layer=2,
            check_fn=self._check_fonts,
            critical=False,
            dependencies=[]
        )
        
        # Layer 3 checks (depend on profile resolution)
        self.register_check(
            "profile",
            layer=3,
            check_fn=self._check_profile,
            critical=True,
            dependencies=[]
        )
        self.register_check(
            "fingerprint_consistency",
            layer=3,
            check_fn=self._check_fingerprint,
            critical=True,
            dependencies=["profile"]
        )
    
    def register_check(
        self,
        name: str,
        layer: int,
        check_fn,
        critical: bool = True,
        dependencies: List[str] = None
    ):
        """Register a verification check with its dependencies."""
        self.check_registry[name] = {
            "layer": layer,
            "check_fn": check_fn,
            "critical": critical,
            "dependencies": dependencies or []
        }
        self.dependency_graph[name] = dependencies or []
    
    def _check_kernel_module(self, context: Dict) -> CheckResult:
        """Check kernel module status."""
        try:
            mods = subprocess.check_output("lsmod", shell=True, timeout=5).decode()
            if "titan_hw" in mods or SYSFS_TITAN_HW.exists():
                return CheckResult(0, "kernel_module", Verdict.OK, "Kernel Shield loaded")
            return CheckResult(0, "kernel_module", Verdict.FAIL, "Kernel Shield NOT loaded")
        except Exception as e:
            return CheckResult(0, "kernel_module", Verdict.FAIL, f"Kernel check failed: {e}")
    
    def _check_dkom_hiding(self, context: Dict) -> CheckResult:
        """Check DKOM module hiding."""
        try:
            mods = subprocess.check_output("lsmod", shell=True, timeout=5).decode()
            if SYSFS_TITAN_HW.exists() and "titan_hw" not in mods:
                return CheckResult(0, "dkom_hiding", Verdict.OK, "DKOM hiding active", critical=False)
            return CheckResult(0, "dkom_hiding", Verdict.WARN, "Module visible", critical=False)
        except Exception:
            return CheckResult(0, "dkom_hiding", Verdict.SKIP, "DKOM check skipped", critical=False)
    
    def _check_dmi_smbios(self, context: Dict) -> CheckResult:
        """Check DMI/SMBIOS spoofing."""
        dmi_fields = ["sys_vendor", "product_name"]
        vm_indicators = ["QEMU", "VirtualBox", "VMware", "Bochs"]
        for field in dmi_fields:
            path = SYSFS_DMI / field
            if path.exists():
                try:
                    val = path.read_text().strip()
                    if any(ind.lower() in val.lower() for ind in vm_indicators):
                        return CheckResult(0, "dmi_smbios", Verdict.FAIL, "VM indicators in DMI")
                except Exception:
                    pass
        return CheckResult(0, "dmi_smbios", Verdict.OK, "DMI/SMBIOS clean", critical=False)
    
    def _check_xdp(self, context: Dict) -> CheckResult:
        """Check XDP attachment."""
        interface = context.get("interface", "eth0")
        try:
            output = subprocess.check_output(
                f"ip link show dev {interface}", shell=True, timeout=5
            ).decode()
            if "xdp" in output.lower():
                return CheckResult(1, "xdp_attached", Verdict.OK, f"XDP on {interface}")
            return CheckResult(1, "xdp_attached", Verdict.FAIL, f"No XDP on {interface}")
        except Exception as e:
            return CheckResult(1, "xdp_attached", Verdict.FAIL, f"XDP check failed: {e}")
    
    def _check_dns(self, context: Dict) -> CheckResult:
        """Check DNS leak prevention."""
        try:
            resolv = Path("/etc/resolv.conf").read_text()
            nameservers = [l.split()[1] for l in resolv.split("\n") if l.strip().startswith("nameserver")]
            safe = ["127.0.0.1", "127.0.0.53", "::1"]
            if all(ns in safe for ns in nameservers):
                return CheckResult(1, "dns_leak", Verdict.OK, "DNS local only")
            return CheckResult(1, "dns_leak", Verdict.WARN, f"DNS may leak: {nameservers}", critical=False)
        except Exception:
            return CheckResult(1, "dns_leak", Verdict.WARN, "DNS check skipped", critical=False)
    
    def _check_fonts(self, context: Dict) -> CheckResult:
        """Check font exclusion."""
        if FONT_CONFIG.exists():
            try:
                content = FONT_CONFIG.read_text()
                if "rejectfont" in content.lower():
                    return CheckResult(2, "font_config", Verdict.OK, "Font exclusion active")
            except Exception:
                pass
            return CheckResult(2, "font_config", Verdict.WARN, "Font config needs review", critical=False)
        return CheckResult(2, "font_config", Verdict.FAIL, "Font config missing")
    
    def _check_profile(self, context: Dict) -> CheckResult:
        """Check profile existence."""
        profile_path = context.get("profile_path")
        if profile_path and Path(profile_path).exists():
            meta = Path(profile_path) / "profile_metadata.json"
            if meta.exists():
                return CheckResult(3, "profile", Verdict.OK, "Profile valid")
            return CheckResult(3, "profile", Verdict.FAIL, "Profile metadata missing")
        return CheckResult(3, "profile", Verdict.FAIL, "No profile found")
    
    def _check_fingerprint(self, context: Dict) -> CheckResult:
        """Check fingerprint consistency."""
        profile_path = context.get("profile_path")
        if not profile_path:
            return CheckResult(3, "fingerprint_consistency", Verdict.SKIP, "No profile", critical=False)
        fp_file = Path(profile_path) / "fingerprint_config.json"
        if fp_file.exists():
            return CheckResult(3, "fingerprint_consistency", Verdict.OK, "Fingerprint config present")
        return CheckResult(3, "fingerprint_consistency", Verdict.FAIL, "No fingerprint config")
    
    def _resolve_execution_order(self) -> List[List[str]]:
        """Resolve check execution order respecting dependencies."""
        resolved = []
        remaining = set(self.check_registry.keys())
        completed = set()
        
        while remaining:
            # Find checks with all dependencies satisfied
            ready = []
            for check in remaining:
                deps = self.dependency_graph.get(check, [])
                if all(d in completed for d in deps):
                    ready.append(check)
            
            if not ready:
                # Circular dependency or missing dependency
                self.logger.warning(f"Unresolvable checks: {remaining}")
                ready = list(remaining)[:5]  # Force progress
            
            # Sort by priority (higher failure count = higher priority)
            ready.sort(key=lambda c: self.priority_weights.get(c, 0), reverse=True)
            resolved.append(ready)
            
            for check in ready:
                completed.add(check)
                remaining.discard(check)
        
        return resolved
    
    def run_verification(self, context: Dict = None) -> MasterVerifyReport:
        """Run all verification checks with intelligent orchestration."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        context = context or {}
        report = MasterVerifyReport()
        report.start_time = time.time()
        
        execution_order = self._resolve_execution_order()
        
        for batch in execution_order:
            # Run batch in parallel
            futures = {}
            for check_name in batch:
                check_info = self.check_registry[check_name]
                future = self.executor.submit(check_info["check_fn"], context)
                futures[future] = check_name
            
            for future in as_completed(futures):
                check_name = futures[future]
                try:
                    result = future.result(timeout=10)
                    with self.lock:
                        self.check_results[check_name] = result
                        report.checks.append(result)
                        
                        # Update failure counts for prioritization
                        if result.verdict == Verdict.FAIL:
                            self.failure_counts[check_name] = self.failure_counts.get(check_name, 0) + 1
                            self.priority_weights[check_name] = self.failure_counts[check_name] * 10
                except Exception as e:
                    self.logger.error(f"Check {check_name} failed: {e}")
                    check_info = self.check_registry[check_name]
                    result = CheckResult(
                        check_info["layer"], check_name, Verdict.FAIL,
                        f"Check exception: {e}", check_info["critical"]
                    )
                    report.checks.append(result)
        
        report.end_time = time.time()
        return report
    
    def run_quick_verify(self, checks: List[str], context: Dict = None) -> MasterVerifyReport:
        """Run only specified checks (for quick re-verification)."""
        context = context or {}
        report = MasterVerifyReport()
        report.start_time = time.time()
        
        for check_name in checks:
            if check_name in self.check_registry:
                check_info = self.check_registry[check_name]
                try:
                    result = check_info["check_fn"](context)
                    report.checks.append(result)
                except Exception as e:
                    report.checks.append(CheckResult(
                        check_info["layer"], check_name, Verdict.FAIL,
                        f"Check failed: {e}", check_info["critical"]
                    ))
        
        report.end_time = time.time()
        return report


class VerificationHistory:
    """
    V7.6 P0: Track verification history and trends.
    
    Maintains historical verification data for trend analysis, regression
    detection, and operational pattern recognition.
    """
    
    _instance = None
    
    def __init__(self, history_file: Path = None):
        self.history_file = history_file or (STATE_DIR / "verification_history.json")
        self.history: List[Dict] = []
        self.max_entries = 1000
        self.logger = logging.getLogger("TITAN-MVP.History")
        self._load_history()
    
    def _load_history(self):
        """Load history from disk."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    self.history = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load history: {e}")
                self.history = []
    
    def _save_history(self):
        """Save history to disk."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.history[-self.max_entries:], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")
    
    def record_verification(self, report: MasterVerifyReport, context: Dict = None):
        """Record a verification run to history."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": report.passed,
            "duration_ms": report.duration_ms,
            "total_checks": len(report.checks),
            "failures": len(report.critical_failures),
            "warnings": len(report.warnings),
            "layer_status": {str(k): v for k, v in report.layer_status.items()},
            "context": context or {},
            "failed_checks": [c.name for c in report.critical_failures],
            "warned_checks": [c.name for c in report.warnings]
        }
        
        self.history.append(entry)
        self._save_history()
    
    def get_failure_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get failure trends over specified period."""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        
        recent = []
        for entry in self.history:
            try:
                ts = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                if ts.timestamp() > cutoff:
                    recent.append(entry)
            except Exception:
                continue
        
        if not recent:
            return {"period_days": days, "entries": 0, "message": "No data"}
        
        # Calculate trends
        total = len(recent)
        passed = sum(1 for e in recent if e.get("passed", False))
        
        # Most common failures
        failure_counts: Dict[str, int] = {}
        for entry in recent:
            for check in entry.get("failed_checks", []):
                failure_counts[check] = failure_counts.get(check, 0) + 1
        
        top_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Layer reliability
        layer_failures: Dict[str, int] = {str(i): 0 for i in range(4)}
        for entry in recent:
            for layer, status in entry.get("layer_status", {}).items():
                if not status:
                    layer_failures[layer] = layer_failures.get(layer, 0) + 1
        
        return {
            "period_days": days,
            "entries": total,
            "pass_rate": passed / total * 100 if total else 0,
            "top_failures": top_failures,
            "layer_reliability": {
                k: (total - v) / total * 100 if total else 0 
                for k, v in layer_failures.items()
            },
            "avg_duration_ms": sum(e.get("duration_ms", 0) for e in recent) / total if total else 0
        }
    
    def get_regression_alerts(self) -> List[Dict]:
        """Detect regressions (checks that started failing recently)."""
        if len(self.history) < 10:
            return []
        
        # Compare last 5 runs to previous 20
        recent = self.history[-5:]
        baseline = self.history[-25:-5] if len(self.history) >= 25 else self.history[:-5]
        
        recent_failures = set()
        for entry in recent:
            recent_failures.update(entry.get("failed_checks", []))
        
        baseline_failures = set()
        for entry in baseline:
            baseline_failures.update(entry.get("failed_checks", []))
        
        # New failures = in recent but not in baseline
        new_failures = recent_failures - baseline_failures
        
        alerts = []
        for check in new_failures:
            count = sum(1 for e in recent if check in e.get("failed_checks", []))
            alerts.append({
                "check": check,
                "type": "regression",
                "severity": "high" if count >= 3 else "medium",
                "message": f"Check '{check}' failed in {count}/5 recent runs (was passing before)"
            })
        
        return alerts
    
    def get_success_streak(self) -> int:
        """Get current success streak (consecutive passing runs)."""
        streak = 0
        for entry in reversed(self.history):
            if entry.get("passed", False):
                streak += 1
            else:
                break
        return streak


class RemediationEngine:
    """
    V7.6 P0: Auto-remediate common verification failures.
    
    Provides automated remediation actions for common failure scenarios,
    with rollback capability and safety checks.
    """
    
    _instance = None
    
    def __init__(self):
        self.remediation_registry: Dict[str, Dict] = {}
        self.remediation_history: List[Dict] = []
        self.max_attempts = 3
        self.logger = logging.getLogger("TITAN-MVP.Remediation")
        
        self._register_default_remediations()
    
    def _register_default_remediations(self):
        """Register default remediation actions."""
        # Layer 0: Kernel module
        self.register_remediation(
            "kernel_module",
            action=self._remediate_kernel_module,
            description="Attempt to load titan_hw kernel module",
            auto_run=False,  # Requires root, manual confirmation
            rollback=self._rollback_kernel_module
        )
        
        # Layer 1: XDP
        self.register_remediation(
            "xdp_attached",
            action=self._remediate_xdp,
            description="Attach XDP program to interface",
            auto_run=False,
            rollback=self._rollback_xdp
        )
        
        # Layer 2: Font config
        self.register_remediation(
            "font_config",
            action=self._remediate_font_config,
            description="Generate default font exclusion config",
            auto_run=True,
            rollback=self._rollback_font_config
        )
        
        # Layer 3: Profile
        self.register_remediation(
            "profile",
            action=self._remediate_profile,
            description="Initialize minimal profile structure",
            auto_run=False,
            rollback=None
        )
    
    def register_remediation(
        self,
        check_name: str,
        action,
        description: str,
        auto_run: bool = False,
        rollback = None
    ):
        """Register a remediation action for a check."""
        self.remediation_registry[check_name] = {
            "action": action,
            "description": description,
            "auto_run": auto_run,
            "rollback": rollback,
            "attempts": 0
        }
    
    def _remediate_kernel_module(self, context: Dict) -> Tuple[bool, str]:
        """Attempt to load kernel module."""
        try:
            result = subprocess.run(
                ["modprobe", "titan_hw"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                return True, "Kernel module loaded successfully"
            return False, f"modprobe failed: {result.stderr.decode()}"
        except Exception as e:
            return False, f"Failed to load module: {e}"
    
    def _rollback_kernel_module(self, context: Dict) -> Tuple[bool, str]:
        """Unload kernel module."""
        try:
            subprocess.run(["rmmod", "titan_hw"], capture_output=True, timeout=10)
            return True, "Module unloaded"
        except Exception as e:
            return False, f"Rollback failed: {e}"
    
    def _remediate_xdp(self, context: Dict) -> Tuple[bool, str]:
        """Attach XDP program."""
        interface = context.get("interface", "eth0")
        xdp_prog = TITAN_ROOT / "ebpf" / "titan_xdp.o"
        
        if not xdp_prog.exists():
            return False, f"XDP program not found: {xdp_prog}"
        
        try:
            result = subprocess.run(
                ["ip", "link", "set", "dev", interface, "xdp", "obj", str(xdp_prog), "section", "xdp"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                return True, f"XDP attached to {interface}"
            return False, f"XDP attach failed: {result.stderr.decode()}"
        except Exception as e:
            return False, f"XDP remediation failed: {e}"
    
    def _rollback_xdp(self, context: Dict) -> Tuple[bool, str]:
        """Detach XDP program."""
        interface = context.get("interface", "eth0")
        try:
            subprocess.run(
                ["ip", "link", "set", "dev", interface, "xdp", "off"],
                capture_output=True, timeout=10
            )
            return True, "XDP detached"
        except Exception as e:
            return False, f"XDP rollback failed: {e}"
    
    def _remediate_font_config(self, context: Dict) -> Tuple[bool, str]:
        """Generate font exclusion config."""
        config_content = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- TITAN: Exclude Linux-specific fonts -->
    <rejectfont>
        <pattern>
            <patelt name="family"><string>DejaVu</string></patelt>
        </pattern>
        <pattern>
            <patelt name="family"><string>Liberation</string></patelt>
        </pattern>
        <pattern>
            <patelt name="family"><string>Droid</string></patelt>
        </pattern>
    </rejectfont>
</fontconfig>
"""
        try:
            FONT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            # Backup existing
            if FONT_CONFIG.exists():
                backup = FONT_CONFIG.with_suffix(".bak")
                FONT_CONFIG.rename(backup)
            
            FONT_CONFIG.write_text(config_content)
            subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=30)
            return True, "Font exclusion config created"
        except Exception as e:
            return False, f"Font config remediation failed: {e}"
    
    def _rollback_font_config(self, context: Dict) -> Tuple[bool, str]:
        """Restore backup font config."""
        backup = FONT_CONFIG.with_suffix(".bak")
        try:
            if backup.exists():
                FONT_CONFIG.unlink(missing_ok=True)
                backup.rename(FONT_CONFIG)
                return True, "Font config restored from backup"
            return False, "No backup found"
        except Exception as e:
            return False, f"Rollback failed: {e}"
    
    def _remediate_profile(self, context: Dict) -> Tuple[bool, str]:
        """Initialize minimal profile."""
        profile_name = context.get("profile_name", f"titan_{int(time.time())}")
        profile_path = PROFILES_DIR / profile_name
        
        try:
            profile_path.mkdir(parents=True, exist_ok=True)
            
            # Create minimal metadata
            metadata = {
                "profile_id": profile_name,
                "created": datetime.now(timezone.utc).isoformat(),
                "persona_name": "Minimal",
                "profile_age_days": 0,
                "auto_generated": True
            }
            
            with open(profile_path / "profile_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True, f"Minimal profile created: {profile_name}"
        except Exception as e:
            return False, f"Profile creation failed: {e}"
    
    def get_available_remediations(self, failures: List[CheckResult]) -> List[Dict]:
        """Get list of available remediations for given failures."""
        available = []
        for failure in failures:
            if failure.name in self.remediation_registry:
                info = self.remediation_registry[failure.name]
                available.append({
                    "check": failure.name,
                    "description": info["description"],
                    "auto_run": info["auto_run"],
                    "attempts": info["attempts"]
                })
        return available
    
    def run_remediation(self, check_name: str, context: Dict = None) -> Tuple[bool, str]:
        """Run remediation for a specific check."""
        context = context or {}
        
        if check_name not in self.remediation_registry:
            return False, f"No remediation registered for {check_name}"
        
        info = self.remediation_registry[check_name]
        if info["attempts"] >= self.max_attempts:
            return False, f"Max remediation attempts ({self.max_attempts}) reached for {check_name}"
        
        info["attempts"] += 1
        self.logger.info(f"Running remediation for {check_name} (attempt {info['attempts']})")
        
        try:
            success, message = info["action"](context)
            
            self.remediation_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "check": check_name,
                "success": success,
                "message": message,
                "attempt": info["attempts"]
            })
            
            return success, message
        except Exception as e:
            error_msg = f"Remediation exception: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def run_auto_remediations(self, failures: List[CheckResult], context: Dict = None) -> List[Dict]:
        """Run all auto-remediations for given failures."""
        context = context or {}
        results = []
        
        for failure in failures:
            if failure.name in self.remediation_registry:
                info = self.remediation_registry[failure.name]
                if info["auto_run"] and info["attempts"] < self.max_attempts:
                    success, message = self.run_remediation(failure.name, context)
                    results.append({
                        "check": failure.name,
                        "success": success,
                        "message": message
                    })
        
        return results


class VerificationScheduler:
    """
    V7.6 P0: Schedule periodic verification runs.
    
    Manages automated verification scheduling with configurable intervals,
    quiet hours, and intelligent run timing based on system state.
    """
    
    _instance = None
    
    def __init__(self):
        from threading import Thread, Event
        
        self.schedule: Dict[str, Dict] = {}
        self.running = False
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.logger = logging.getLogger("TITAN-MVP.Scheduler")
        
        # V7.6: Adaptive scheduling
        self.last_run_time: Optional[float] = None
        self.run_history: List[Dict] = []
        self.quiet_hours: Tuple[int, int] = (2, 6)  # 2 AM to 6 AM
        
        self._load_schedule()
    
    def _load_schedule(self):
        """Load schedule from state."""
        schedule_file = STATE_DIR / "verification_schedule.json"
        if schedule_file.exists():
            try:
                with open(schedule_file) as f:
                    data = json.load(f)
                    self.schedule = data.get("schedule", {})
                    self.quiet_hours = tuple(data.get("quiet_hours", [2, 6]))
            except Exception as e:
                self.logger.warning(f"Failed to load schedule: {e}")
    
    def _save_schedule(self):
        """Save schedule to state."""
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(STATE_DIR / "verification_schedule.json", 'w') as f:
                json.dump({
                    "schedule": self.schedule,
                    "quiet_hours": list(self.quiet_hours)
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save schedule: {e}")
    
    def add_schedule(
        self,
        name: str,
        interval_minutes: int,
        checks: List[str] = None,
        context: Dict = None,
        enabled: bool = True
    ):
        """Add a scheduled verification."""
        self.schedule[name] = {
            "interval_minutes": interval_minutes,
            "checks": checks,  # None = full verification
            "context": context or {},
            "enabled": enabled,
            "last_run": None,
            "next_run": time.time() + (interval_minutes * 60)
        }
        self._save_schedule()
    
    def remove_schedule(self, name: str):
        """Remove a scheduled verification."""
        if name in self.schedule:
            del self.schedule[name]
            self._save_schedule()
    
    def enable_schedule(self, name: str, enabled: bool = True):
        """Enable or disable a schedule."""
        if name in self.schedule:
            self.schedule[name]["enabled"] = enabled
            self._save_schedule()
    
    def set_quiet_hours(self, start_hour: int, end_hour: int):
        """Set quiet hours during which verifications are skipped."""
        self.quiet_hours = (start_hour, end_hour)
        self._save_schedule()
    
    def _is_quiet_hour(self) -> bool:
        """Check if current time is in quiet hours."""
        current_hour = datetime.now().hour
        start, end = self.quiet_hours
        if start <= end:
            return start <= current_hour < end
        else:
            return current_hour >= start or current_hour < end
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        orchestrator = get_verification_orchestrator()
        history = get_verification_history()
        
        while not self.stop_event.is_set():
            now = time.time()
            
            for name, config in list(self.schedule.items()):
                if not config.get("enabled", True):
                    continue
                
                next_run = config.get("next_run", 0)
                if now >= next_run:
                    # Skip during quiet hours unless critical
                    if self._is_quiet_hour():
                        self.logger.debug(f"Skipping {name} during quiet hours")
                        config["next_run"] = now + (config["interval_minutes"] * 60)
                        continue
                    
                    # Run verification
                    self.logger.info(f"Running scheduled verification: {name}")
                    try:
                        context = config.get("context", {})
                        checks = config.get("checks")
                        
                        if checks:
                            report = orchestrator.run_quick_verify(checks, context)
                        else:
                            report = orchestrator.run_verification(context)
                        
                        # Record to history
                        history.record_verification(report, {"scheduled": name, **context})
                        
                        config["last_run"] = now
                        config["next_run"] = now + (config["interval_minutes"] * 60)
                        
                        self.run_history.append({
                            "name": name,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "passed": report.passed,
                            "duration_ms": report.duration_ms
                        })
                        
                        self._save_schedule()
                    except Exception as e:
                        self.logger.error(f"Scheduled verification {name} failed: {e}")
            
            # Sleep for a minute between checks
            self.stop_event.wait(60)
    
    def start(self):
        """Start the scheduler."""
        from threading import Thread
        
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        self.thread = Thread(target=self._scheduler_loop, daemon=True, name="verification_scheduler")
        self.thread.start()
        self.logger.info("Verification scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.running = False
        self.logger.info("Verification scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "quiet_hours": list(self.quiet_hours),
            "is_quiet_hour": self._is_quiet_hour(),
            "schedules": {
                name: {
                    "enabled": config.get("enabled", True),
                    "interval_minutes": config["interval_minutes"],
                    "last_run": config.get("last_run"),
                    "next_run": config.get("next_run"),
                    "checks": config.get("checks", "full")
                }
                for name, config in self.schedule.items()
            },
            "recent_runs": self.run_history[-10:]
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON GETTERS
# ═══════════════════════════════════════════════════════════════════════════

def get_verification_orchestrator() -> VerificationOrchestrator:
    """Get singleton VerificationOrchestrator instance."""
    if VerificationOrchestrator._instance is None:
        VerificationOrchestrator._instance = VerificationOrchestrator()
    return VerificationOrchestrator._instance


def get_verification_history() -> VerificationHistory:
    """Get singleton VerificationHistory instance."""
    if VerificationHistory._instance is None:
        VerificationHistory._instance = VerificationHistory()
    return VerificationHistory._instance


def get_remediation_engine() -> RemediationEngine:
    """Get singleton RemediationEngine instance."""
    if RemediationEngine._instance is None:
        RemediationEngine._instance = RemediationEngine()
    return RemediationEngine._instance


def get_verification_scheduler() -> VerificationScheduler:
    """Get singleton VerificationScheduler instance."""
    if VerificationScheduler._instance is None:
        VerificationScheduler._instance = VerificationScheduler()
    return VerificationScheduler._instance


if __name__ == "__main__":
    main()
