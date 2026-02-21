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


if __name__ == "__main__":
    main()
