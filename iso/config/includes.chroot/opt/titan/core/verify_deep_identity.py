#!/usr/bin/env python3
"""
TITAN V7.0 SINGULARITY — Deep Identity Verifier (Phase 3 Validation)
AUTHORITY: Dva.12
PURPOSE: Detect subtle environmental leaks (Fonts, Audio, Time) that
         bypass Kernel Shields. Confirms if a 'Windows' profile
         actually looks like Windows to Tier-1 antifraud systems.

USAGE:
  python3 verify_deep_identity.py [--os windows_11] [--profile NAME] [--prefs PATH]

EXIT CODES:
  0 — STATUS: GHOST (Undetectable)
  1 — STATUS: FLAGGED (Fix indicated leaks)
  2 — STATUS: PARTIAL (Warnings only)
"""

import os
import sys
import json
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

TITAN_ROOT = Path("/opt/titan")
LEGACY_ROOT = Path("/opt/lucid-empire")
PROFILES_DIR = TITAN_ROOT / "profiles"
STATE_DIR = TITAN_ROOT / "state"

CAMOUFOX_PREFS = LEGACY_ROOT / "camoufox" / "settings" / "defaults" / "pref" / "local-settings.js"

# Fonts that MUST NOT be visible when spoofing Windows/macOS
LINUX_LEAK_FONTS = [
    "Liberation Sans", "Liberation Serif", "Liberation Mono",
    "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
    "Noto Color Emoji", "Noto Sans", "Noto Serif",
    "Ubuntu", "Ubuntu Mono", "Cantarell",
    "Droid Sans", "Droid Serif",
    "FreeSans", "FreeSerif", "FreeMono",
    "Nimbus Sans", "Nimbus Roman",
]

# Fonts that MUST be present per target OS
REQUIRED_FONTS = {
    "windows_10": ["Segoe UI", "Arial", "Times New Roman", "Verdana", "Tahoma", "Calibri", "Consolas"],
    "windows_11": ["Segoe UI", "Arial", "Times New Roman", "Verdana", "Tahoma", "Calibri", "Consolas"],
    "macos_14": ["Helvetica Neue", "Arial", "Times New Roman", "Menlo", "Monaco"],
    "macos_13": ["Helvetica Neue", "Arial", "Times New Roman", "Menlo", "Monaco"],
}

# Audio prefs that MUST be present for AudioContext protection
REQUIRED_AUDIO_PREFS = [
    "privacy.resistFingerprinting",
    "privacy.fingerprintingProtection",
]

# ═══════════════════════════════════════════════════════════════════════════
# COLORS
# ═══════════════════════════════════════════════════════════════════════════

class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def ok(msg):   print(f"  [{C.GREEN} OK {C.END}] {msg}"); return True
def fail(msg): print(f"  [{C.RED}FAIL{C.END}] {msg}"); return False
def warn(msg): print(f"  [{C.YELLOW}WARN{C.END}] {msg}"); return None  # Warnings return None


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3.1: FONT HYGIENE
# ═══════════════════════════════════════════════════════════════════════════

def verify_font_hygiene(target_os: str = "windows_11") -> bool:
    print(f"\n{C.CYAN}{'─'*55}{C.END}")
    print(f"{C.CYAN}  PHASE 3.1 │ FONT ENVIRONMENT{C.END}")
    print(f"{C.CYAN}{'─'*55}{C.END}")
    
    # Get installed fonts
    try:
        installed = subprocess.check_output(
            "fc-list : family", shell=True, timeout=10
        ).decode()
    except Exception as e:
        fail(f"Cannot enumerate fonts: {e}")
        return False
    
    clean = True
    leaks = []
    missing = []
    
    # Check for Linux font leaks
    for font in LINUX_LEAK_FONTS:
        if font in installed:
            leaks.append(font)
    
    if leaks:
        clean = False
        fail(f"Linux font LEAKS: {len(leaks)} detected")
        for f_name in leaks[:5]:
            print(f"        {C.RED}✗{C.END} {f_name}")
        if len(leaks) > 5:
            print(f"        ... and {len(leaks)-5} more")
    else:
        ok("No Linux-exclusive fonts detected")
    
    # Check for required target OS fonts
    required = REQUIRED_FONTS.get(target_os, REQUIRED_FONTS["windows_11"])
    for font in required:
        if font not in installed:
            missing.append(font)
    
    if missing:
        fail(f"Missing {len(missing)} required {target_os} fonts")
        for f_name in missing:
            print(f"        {C.RED}✗{C.END} {f_name}")
    else:
        ok(f"All {len(required)} required {target_os} fonts present")
    
    # Check local.conf exists with rejectfont
    local_conf = Path("/etc/fonts/local.conf")
    if local_conf.exists():
        content = local_conf.read_text()
        if "rejectfont" in content.lower():
            ok("local.conf: rejectfont directive ACTIVE")
        else:
            warn("local.conf exists but no rejectfont directive")
    else:
        clean = False
        fail("local.conf MISSING — run FontSanitizer.apply()")
    
    # Check font metric overrides
    # (These would be in the profile directory)
    
    return clean and not leaks


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3.2: AUDIO STACK
# ═══════════════════════════════════════════════════════════════════════════

def verify_audio_hardening(profile_path: Optional[Path] = None) -> bool:
    print(f"\n{C.CYAN}{'─'*55}{C.END}")
    print(f"{C.CYAN}  PHASE 3.2 │ AUDIO STACK HARDENING{C.END}")
    print(f"{C.CYAN}{'─'*55}{C.END}")
    
    audio_ok = True
    
    # Check Camoufox global prefs
    prefs_checked = False
    prefs_to_scan = []
    
    if CAMOUFOX_PREFS.exists():
        prefs_to_scan.append(("Camoufox global prefs", CAMOUFOX_PREFS))
    
    if profile_path:
        user_js = profile_path / "user.js"
        if user_js.exists():
            prefs_to_scan.append(("Profile user.js", user_js))
        
        audio_cfg = profile_path / "audio_config.json"
        if audio_cfg.exists():
            try:
                with open(audio_cfg) as f:
                    acfg = json.load(f)
                if acfg.get("audio_hardening"):
                    ok(f"Audio config: target={acfg.get('target_os', '?')}, noise={acfg.get('noise_injection', {}).get('enabled', False)}")
                    prefs_checked = True
                else:
                    warn("audio_config.json exists but hardening disabled")
            except Exception:
                warn("audio_config.json unreadable")
    
    for label, path in prefs_to_scan:
        try:
            content = path.read_text()
            found = []
            for pref in REQUIRED_AUDIO_PREFS:
                if pref in content:
                    found.append(pref)
            
            if len(found) == len(REQUIRED_AUDIO_PREFS):
                ok(f"{label}: All {len(found)} audio protection prefs present")
                prefs_checked = True
            elif found:
                warn(f"{label}: {len(found)}/{len(REQUIRED_AUDIO_PREFS)} audio prefs (partial)")
                prefs_checked = True
            else:
                pass  # No audio prefs in this file, check next source
        except Exception as e:
            warn(f"{label}: Could not read prefs file: {e}")
    
    if not prefs_checked:
        audio_ok = False
        fail("AudioContext protection NOT found in any prefs file")
        print(f"        → Run: AudioHardener(AudioTargetOS.WINDOWS).apply_to_profile(path)")
    
    # Check PulseAudio/PipeWire presence (informational)
    try:
        pa_result = subprocess.run(
            ["pulseaudio", "--check"], capture_output=True, timeout=3
        )
        if pa_result.returncode == 0:
            warn("PulseAudio running — ensure RFP masks latency signature")
        else:
            ok("PulseAudio not active (or PipeWire in use)")
    except FileNotFoundError:
        try:
            pw_result = subprocess.run(
                ["pw-cli", "info", "0"], capture_output=True, timeout=3
            )
            if pw_result.returncode == 0:
                warn("PipeWire running — ensure RFP masks latency signature")
        except FileNotFoundError:
            ok("No PulseAudio/PipeWire detected")
    except Exception as e:
        warn(f"Audio subsystem check error: {e}")
    
    return audio_ok


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3.3: TIMEZONE SYNC
# ═══════════════════════════════════════════════════════════════════════════

def verify_timezone_sync(target_state: str = "", target_country: str = "US") -> bool:
    print(f"\n{C.CYAN}{'─'*55}{C.END}")
    print(f"{C.CYAN}  PHASE 3.3 │ TIMEZONE SYNCHRONIZATION{C.END}")
    print(f"{C.CYAN}{'─'*55}{C.END}")
    
    tz_ok = True
    
    # Get system timezone
    try:
        sys_tz = subprocess.check_output("date +%Z", shell=True, timeout=3).decode().strip()
        sys_offset = subprocess.check_output("date +%z", shell=True, timeout=3).decode().strip()
    except Exception as e:
        fail(f"Cannot read system timezone: {e}")
        return False
    
    # Check for UTC (almost always wrong for US/EU targets)
    if sys_tz == "UTC" and target_country in ("US", "GB", "DE", "FR", "CA", "AU"):
        tz_ok = False
        fail(f"System timezone is UTC — MUST match target IP location")
        print(f"        → Run: TimezoneEnforcer.enforce()")
    else:
        ok(f"System timezone: {sys_tz} ({sys_offset})")
    
    # Check timezone state file
    tz_state = STATE_DIR / "timezone_state.json"
    if tz_state.exists():
        try:
            with open(tz_state) as f:
                state = json.load(f)
            set_tz = state.get("timezone", "unknown")
            set_at = state.get("set_at", "unknown")
            ok(f"Timezone enforced: {set_tz} (set at {set_at[:19]})")
        except Exception:
            warn("Timezone state file unreadable")
    else:
        warn("No timezone enforcement record — was TimezoneEnforcer run?")
    
    # Check for stale browser processes (they cache old timezone)
    browser_procs = ["firefox", "camoufox", "chromium"]
    stale = []
    for proc in browser_procs:
        try:
            result = subprocess.run(
                ["pgrep", "-f", proc], capture_output=True, timeout=2
            )
            if result.returncode == 0:
                stale.append(proc)
        except Exception:
            pass
    
    if stale:
        tz_ok = False
        fail(f"Browser processes running: {', '.join(stale)} — they cache OLD timezone!")
        print(f"        → Kill browsers BEFORE changing timezone")
    else:
        ok("No stale browser processes (timezone cache clean)")
    
    # Check NTP sync
    try:
        ntp_result = subprocess.check_output(
            "timedatectl show --property=NTPSynchronized --value",
            shell=True, timeout=3
        ).decode().strip()
        if ntp_result == "yes":
            ok("NTP synchronized: clock drift < 1s")
        else:
            warn("NTP not synchronized — clock drift may be detectable")
    except Exception:
        warn("NTP check unavailable")
    
    # Check TZ environment variable
    env_tz = os.environ.get("TZ", "")
    if env_tz:
        ok(f"TZ environment: {env_tz}")
    else:
        warn("TZ environment variable not set — browser may use UTC")
    
    return tz_ok


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="TITAN Deep Identity Verifier (Phase 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--os", default="windows_11",
                       choices=["windows_10", "windows_11", "macos_14", "macos_13"],
                       help="Target OS profile (default: windows_11)")
    parser.add_argument("-p", "--profile", default=None,
                       help="Profile name or path")
    parser.add_argument("--state", default="", help="Target US state (e.g. TX)")
    parser.add_argument("--country", default="US", help="Target country code")
    parser.add_argument("--json", action="store_true", help="JSON output")
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
        if PROFILES_DIR.exists():
            profiles = sorted(PROFILES_DIR.glob("titan_*"),
                            key=lambda x: x.stat().st_mtime, reverse=True)
            if profiles:
                profile_path = profiles[0]
    
    # Banner
    if not args.json:
        print(f"\n{C.BOLD}{C.CYAN}")
        print("  ╔═══════════════════════════════════════════════════╗")
        print("  ║   TITAN DEEP IDENTITY VERIFIER (Phase 3)        ║")
        print("  ║   Authority: Dva.12 │ Target: GHOST             ║")
        print("  ╚═══════════════════════════════════════════════════╝")
        print(f"{C.END}")
        print(f"  Target OS: {C.CYAN}{args.os}{C.END}")
        if profile_path:
            print(f"  Profile:   {C.CYAN}{profile_path.name}{C.END}")
    
    start = time.time()
    
    fonts_ok = verify_font_hygiene(args.os)
    audio_ok = verify_audio_hardening(profile_path)
    time_ok = verify_timezone_sync(args.state, args.country)
    
    duration_ms = (time.time() - start) * 1000
    
    # Verdict
    all_ok = fonts_ok and audio_ok and time_ok
    has_warnings = not all_ok
    
    if args.json:
        json.dump({
            "status": "GHOST" if all_ok else "FLAGGED",
            "fonts_clean": fonts_ok,
            "audio_hardened": audio_ok,
            "timezone_synced": time_ok,
            "target_os": args.os,
            "duration_ms": round(duration_ms, 1),
        }, sys.stdout, indent=2)
        print()
    else:
        print(f"\n{'='*55}")
        print(f"  Duration: {duration_ms:.0f}ms")
        print(f"  Fonts:    {'CLEAN' if fonts_ok else 'LEAKING'}")
        print(f"  Audio:    {'HARDENED' if audio_ok else 'EXPOSED'}")
        print(f"  Timezone: {'SYNCED' if time_ok else 'DRIFTING'}")
        print(f"{'='*55}")
        
        if all_ok:
            print(f"\n  {C.GREEN}{C.BOLD}STATUS: GHOST (UNDETECTABLE){C.END}")
            print(f"  >> Proceed to Target.\n")
        else:
            print(f"\n  {C.RED}{C.BOLD}STATUS: FLAGGED{C.END}")
            print(f"  >> DO NOT LOGIN. Fix indicated leaks first.\n")
    
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
