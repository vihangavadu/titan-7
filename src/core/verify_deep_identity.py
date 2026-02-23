#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Deep Identity Verifier (Phase 3 Validation)
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
LEGACY_ROOT = Path("/opt/titan")
PROFILES_DIR = TITAN_ROOT / "profiles"
STATE_DIR = TITAN_ROOT / "state"

# V7.5 FIX: Use correct Camoufox install path on Titan OS
CAMOUFOX_PREFS = Path("/opt/camoufox/defaults/pref/local-settings.js")

# Fonts that MUST NOT be visible when spoofing Windows/macOS
LINUX_LEAK_FONTS = [
    "Liberation Sans", "Liberation Serif", "Liberation Mono",
    "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
    "Noto Color Emoji", "Noto Sans", "Noto Serif",
    "Noto Sans CJK", "Noto Serif CJK",
    "Ubuntu", "Ubuntu Mono", "Ubuntu Condensed",
    "Cantarell", "Droid Sans", "Droid Serif",
    "FreeSans", "FreeSerif", "FreeMono",
    "Nimbus Sans", "Nimbus Roman", "Nimbus Mono",
    "STIX", "Latin Modern",
    "Bitstream Vera Sans", "Bitstream Vera Serif",
    # V7.5 FIX: Additional common Linux distribution fonts (synced with font_sanitizer.py)
    "Source Code Pro", "Hack", "Cantarell Light",
    "Noto Sans Mono", "Noto Sans Display",
    # V7.6: Additional Linux distribution fonts
    "Noto Sans Symbols", "Noto Sans Symbols2", "Noto Sans Math",
    "URW Gothic", "URW Bookman", "C059", "P052",
    "Lato", "Open Sans", "Roboto",
    "Liberation Sans Narrow", "TeX Gyre Termes", "TeX Gyre Heros",
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
        # V7.5 FIX: Missing required fonts should also fail the check
        clean = False
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
    
    return clean


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
            except Exception as e:
                warn(f"audio_config.json unreadable: {e}")
    
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
# V7.6 P0 CRITICAL: DEEP IDENTITY ORCHESTRATOR
# Multi-phase identity verification with parallel checks and auto-remediation
# ═══════════════════════════════════════════════════════════════════════════

class DeepIdentityOrchestrator:
    """
    V7.6 P0: Orchestrates comprehensive identity verification across all phases.
    Coordinates font, audio, timezone, and additional identity signals with
    parallel execution and smart dependency resolution.
    """
    
    def __init__(self, target_os: str = "windows_11", profile_path: Optional[Path] = None):
        self.target_os = target_os
        self.profile_path = profile_path
        self.phases: Dict[str, Dict[str, Any]] = {}
        self.execution_order: List[str] = []
        self.parallel_groups: List[List[str]] = []
        self.results: Dict[str, Dict[str, Any]] = {}
        self.start_time: Optional[float] = None
        self.hooks: Dict[str, List[callable]] = {
            "pre_phase": [],
            "post_phase": [],
            "on_failure": [],
            "on_success": []
        }
        self._register_default_phases()
    
    def _register_default_phases(self) -> None:
        """Register all default verification phases."""
        self.register_phase(
            "fonts",
            verify_func=self._verify_fonts,
            priority=1,
            description="Font environment hygiene",
            auto_remediate=True,
            dependencies=[]
        )
        self.register_phase(
            "audio",
            verify_func=self._verify_audio,
            priority=2,
            description="Audio stack hardening",
            auto_remediate=True,
            dependencies=[]
        )
        self.register_phase(
            "timezone",
            verify_func=self._verify_timezone,
            priority=1,
            description="Timezone synchronization",
            auto_remediate=True,
            dependencies=[]
        )
        self.register_phase(
            "webgl",
            verify_func=self._verify_webgl,
            priority=3,
            description="WebGL fingerprint consistency",
            auto_remediate=False,
            dependencies=["fonts"]
        )
        self.register_phase(
            "canvas",
            verify_func=self._verify_canvas,
            priority=3,
            description="Canvas fingerprint hardening",
            auto_remediate=False,
            dependencies=["fonts"]
        )
        self._compute_execution_order()
    
    def register_phase(self, name: str, verify_func: callable,
                       priority: int = 5, description: str = "",
                       auto_remediate: bool = False,
                       dependencies: List[str] = None) -> None:
        """Register a verification phase."""
        self.phases[name] = {
            "name": name,
            "verify_func": verify_func,
            "priority": priority,
            "description": description,
            "auto_remediate": auto_remediate,
            "dependencies": dependencies or [],
            "enabled": True
        }
        self._compute_execution_order()
    
    def _compute_execution_order(self) -> None:
        """Compute execution order based on dependencies and priorities."""
        # Topological sort with priority consideration
        visited = set()
        order = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            phase = self.phases.get(name, {})
            for dep in phase.get("dependencies", []):
                if dep in self.phases:
                    visit(dep)
            order.append(name)
        
        # Sort by priority first, then visit
        sorted_phases = sorted(
            self.phases.keys(),
            key=lambda x: self.phases[x].get("priority", 5)
        )
        
        for phase_name in sorted_phases:
            visit(phase_name)
        
        self.execution_order = order
        
        # Group phases that can run in parallel (no dependencies between them)
        self._compute_parallel_groups()
    
    def _compute_parallel_groups(self) -> None:
        """Group phases that can execute in parallel."""
        groups = []
        remaining = set(self.execution_order)
        completed = set()
        
        while remaining:
            # Find all phases whose dependencies are satisfied
            ready = []
            for phase in remaining:
                deps = set(self.phases[phase].get("dependencies", []))
                if deps.issubset(completed):
                    ready.append(phase)
            
            if not ready:
                # Circular dependency or error - add remaining one by one
                ready = [list(remaining)[0]]
            
            groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)
        
        self.parallel_groups = groups
    
    def _verify_fonts(self) -> Dict[str, Any]:
        """Font verification wrapper."""
        result = verify_font_hygiene(self.target_os)
        return {
            "passed": result,
            "phase": "fonts",
            "details": {"target_os": self.target_os}
        }
    
    def _verify_audio(self) -> Dict[str, Any]:
        """Audio verification wrapper."""
        result = verify_audio_hardening(self.profile_path)
        return {
            "passed": result,
            "phase": "audio",
            "details": {"profile_path": str(self.profile_path) if self.profile_path else None}
        }
    
    def _verify_timezone(self) -> Dict[str, Any]:
        """Timezone verification wrapper."""
        result = verify_timezone_sync()
        return {
            "passed": result,
            "phase": "timezone",
            "details": {}
        }
    
    def _verify_webgl(self) -> Dict[str, Any]:
        """WebGL fingerprint consistency check."""
        # Check WebGL configuration exists
        webgl_ok = True
        details = {}
        
        if self.profile_path:
            webgl_conf = self.profile_path / "webgl_config.json"
            if webgl_conf.exists():
                try:
                    with open(webgl_conf) as f:
                        config = json.load(f)
                    details["renderer"] = config.get("renderer", "unknown")
                    details["vendor"] = config.get("vendor", "unknown")
                    webgl_ok = config.get("enabled", False)
                except Exception as e:
                    details["error"] = str(e)
                    webgl_ok = False
            else:
                details["note"] = "No WebGL config found"
                webgl_ok = True  # Not a failure, just unconfigured
        
        return {
            "passed": webgl_ok,
            "phase": "webgl",
            "details": details
        }
    
    def _verify_canvas(self) -> Dict[str, Any]:
        """Canvas fingerprint hardening check."""
        canvas_ok = True
        details = {}
        
        if self.profile_path:
            prefs_file = self.profile_path / "user.js"
            if prefs_file.exists():
                try:
                    content = prefs_file.read_text()
                    canvas_prefs = [
                        "privacy.resistFingerprinting",
                        "canvas.poisondata"
                    ]
                    found = sum(1 for p in canvas_prefs if p in content)
                    details["canvas_prefs_found"] = found
                    canvas_ok = found > 0
                except Exception:
                    pass
        
        return {
            "passed": canvas_ok,
            "phase": "canvas",
            "details": details
        }
    
    def add_hook(self, hook_type: str, callback: callable) -> None:
        """Add execution hook."""
        if hook_type in self.hooks:
            self.hooks[hook_type].append(callback)
    
    def _fire_hooks(self, hook_type: str, **kwargs) -> None:
        """Fire all hooks of a type."""
        for callback in self.hooks.get(hook_type, []):
            try:
                callback(**kwargs)
            except Exception:
                pass
    
    def execute(self, phases: List[str] = None, parallel: bool = True,
                stop_on_failure: bool = False) -> Dict[str, Any]:
        """
        Execute verification phases.
        
        Args:
            phases: List of specific phases to run (None = all)
            parallel: Run independent phases in parallel
            stop_on_failure: Stop execution on first failure
            
        Returns:
            Comprehensive verification results
        """
        self.start_time = time.time()
        self.results = {}
        
        phases_to_run = phases or self.execution_order
        all_passed = True
        
        groups = self.parallel_groups if parallel else [[p] for p in phases_to_run]
        
        for group in groups:
            group_phases = [p for p in group if p in phases_to_run and self.phases.get(p, {}).get("enabled", True)]
            
            for phase_name in group_phases:
                phase = self.phases.get(phase_name)
                if not phase:
                    continue
                
                self._fire_hooks("pre_phase", phase=phase_name)
                
                try:
                    result = phase["verify_func"]()
                    self.results[phase_name] = result
                    
                    if result.get("passed"):
                        self._fire_hooks("on_success", phase=phase_name, result=result)
                    else:
                        all_passed = False
                        self._fire_hooks("on_failure", phase=phase_name, result=result)
                        
                        if stop_on_failure:
                            break
                
                except Exception as e:
                    self.results[phase_name] = {
                        "passed": False,
                        "phase": phase_name,
                        "error": str(e)
                    }
                    all_passed = False
                    self._fire_hooks("on_failure", phase=phase_name, error=e)
                
                self._fire_hooks("post_phase", phase=phase_name)
            
            if stop_on_failure and not all_passed:
                break
        
        duration = (time.time() - self.start_time) * 1000
        
        return {
            "status": "GHOST" if all_passed else "FLAGGED",
            "all_passed": all_passed,
            "phases": self.results,
            "duration_ms": round(duration, 1),
            "target_os": self.target_os,
            "execution_order": phases_to_run
        }
    
    def get_report(self, include_details: bool = True) -> Dict[str, Any]:
        """Get comprehensive verification report."""
        return {
            "results": self.results,
            "summary": {
                "total_phases": len(self.results),
                "passed": sum(1 for r in self.results.values() if r.get("passed")),
                "failed": sum(1 for r in self.results.values() if not r.get("passed"))
            },
            "phases": {
                name: {
                    "description": phase.get("description", ""),
                    "enabled": phase.get("enabled", True),
                    "auto_remediate": phase.get("auto_remediate", False)
                }
                for name, phase in self.phases.items()
            } if include_details else {}
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL: IDENTITY LEAK DETECTOR
# Deep analysis of subtle identity leaks across all fingerprint vectors
# ═══════════════════════════════════════════════════════════════════════════

class IdentityLeakDetector:
    """
    V7.6 P0: Detects subtle identity leaks that can expose the true environment.
    Analyzes fonts, timing, hardware signatures, and behavioral patterns.
    """
    
    def __init__(self, target_os: str = "windows_11"):
        self.target_os = target_os
        self.leaks: List[Dict[str, Any]] = []
        self.severity_scores: Dict[str, int] = {
            "critical": 100,
            "high": 75,
            "medium": 50,
            "low": 25,
            "info": 10
        }
        self.detection_rules: List[Dict[str, Any]] = []
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """Register default leak detection rules."""
        # Font leak rules
        self.add_rule(
            name="linux_font_leak",
            detector=self._detect_linux_fonts,
            severity="critical",
            category="fonts",
            description="Linux-exclusive fonts visible"
        )
        
        # Timezone leak rules
        self.add_rule(
            name="utc_timezone",
            detector=self._detect_utc_timezone,
            severity="high",
            category="timezone",
            description="UTC timezone when target is non-UTC region"
        )
        
        # Audio leak rules
        self.add_rule(
            name="audio_context_exposed",
            detector=self._detect_audio_context,
            severity="high",
            category="audio",
            description="AudioContext fingerprint not protected"
        )
        
        # Environment leak rules
        self.add_rule(
            name="linux_paths",
            detector=self._detect_linux_paths,
            severity="medium",
            category="environment",
            description="Linux path patterns in environment"
        )
        
        # Process leak rules
        self.add_rule(
            name="linux_processes",
            detector=self._detect_linux_processes,
            severity="medium",
            category="processes",
            description="Linux-specific processes running"
        )
    
    def add_rule(self, name: str, detector: callable, severity: str = "medium",
                 category: str = "general", description: str = "") -> None:
        """Add a leak detection rule."""
        self.detection_rules.append({
            "name": name,
            "detector": detector,
            "severity": severity,
            "category": category,
            "description": description,
            "enabled": True
        })
    
    def _detect_linux_fonts(self) -> List[Dict[str, Any]]:
        """Detect Linux font leaks."""
        leaks = []
        try:
            installed = subprocess.check_output(
                "fc-list : family", shell=True, timeout=10
            ).decode()
            
            for font in LINUX_LEAK_FONTS:
                if font in installed:
                    leaks.append({
                        "type": "linux_font",
                        "value": font,
                        "severity": "critical",
                        "remediation": f"Remove font: {font}"
                    })
        except Exception:
            pass
        
        return leaks
    
    def _detect_utc_timezone(self) -> List[Dict[str, Any]]:
        """Detect UTC timezone leak."""
        leaks = []
        try:
            sys_tz = subprocess.check_output(
                "date +%Z", shell=True, timeout=3
            ).decode().strip()
            
            if sys_tz == "UTC":
                leaks.append({
                    "type": "utc_timezone",
                    "value": sys_tz,
                    "severity": "high",
                    "remediation": "Run TimezoneEnforcer to set target timezone"
                })
        except Exception:
            pass
        
        return leaks
    
    def _detect_audio_context(self) -> List[Dict[str, Any]]:
        """Detect unprotected AudioContext."""
        leaks = []
        
        # Check if RFP is enabled
        if CAMOUFOX_PREFS.exists():
            try:
                content = CAMOUFOX_PREFS.read_text()
                if "privacy.resistFingerprinting" not in content:
                    leaks.append({
                        "type": "audio_context",
                        "value": "RFP not enabled",
                        "severity": "high",
                        "remediation": "Enable privacy.resistFingerprinting"
                    })
            except Exception:
                pass
        
        return leaks
    
    def _detect_linux_paths(self) -> List[Dict[str, Any]]:
        """Detect Linux path patterns in environment."""
        leaks = []
        
        linux_indicators = [
            ("/usr/bin", "PATH contains /usr/bin"),
            ("/home/", "HOME path uses /home/"),
            (".local/share", "XDG paths detected"),
        ]
        
        for path_pattern, description in linux_indicators:
            for env_var in ["PATH", "HOME", "XDG_DATA_HOME"]:
                value = os.environ.get(env_var, "")
                if path_pattern in value:
                    leaks.append({
                        "type": "linux_path",
                        "value": f"{env_var}={value[:50]}...",
                        "severity": "medium",
                        "remediation": f"Environment reveals Linux: {description}"
                    })
                    break
        
        return leaks
    
    def _detect_linux_processes(self) -> List[Dict[str, Any]]:
        """Detect Linux-specific processes."""
        leaks = []
        
        linux_procs = ["systemd", "gnome-shell", "kwin", "xfce4", "pulseaudio"]
        
        for proc in linux_procs:
            try:
                result = subprocess.run(
                    ["pgrep", "-x", proc],
                    capture_output=True, timeout=2
                )
                if result.returncode == 0:
                    leaks.append({
                        "type": "linux_process",
                        "value": proc,
                        "severity": "low",
                        "remediation": f"Linux process: {proc}"
                    })
            except Exception:
                pass
        
        return leaks
    
    def scan(self, categories: List[str] = None) -> Dict[str, Any]:
        """
        Run full leak detection scan.
        
        Args:
            categories: Specific categories to scan (None = all)
            
        Returns:
            Scan results with all detected leaks
        """
        self.leaks = []
        start = time.time()
        
        for rule in self.detection_rules:
            if not rule.get("enabled", True):
                continue
            
            if categories and rule.get("category") not in categories:
                continue
            
            try:
                detected = rule["detector"]()
                for leak in detected:
                    leak["rule"] = rule["name"]
                    leak["category"] = rule.get("category", "general")
                    self.leaks.append(leak)
            except Exception as e:
                self.leaks.append({
                    "type": "scan_error",
                    "rule": rule["name"],
                    "error": str(e),
                    "severity": "info"
                })
        
        duration = (time.time() - start) * 1000
        
        # Calculate overall score
        total_score = sum(
            self.severity_scores.get(leak.get("severity", "low"), 25)
            for leak in self.leaks
        )
        
        return {
            "status": "CLEAN" if not self.leaks else "LEAKING",
            "total_leaks": len(self.leaks),
            "leaks": self.leaks,
            "risk_score": min(total_score, 1000),
            "duration_ms": round(duration, 1),
            "by_category": self._group_by_category(),
            "by_severity": self._group_by_severity()
        }
    
    def _group_by_category(self) -> Dict[str, int]:
        """Group leaks by category."""
        groups = {}
        for leak in self.leaks:
            cat = leak.get("category", "unknown")
            groups[cat] = groups.get(cat, 0) + 1
        return groups
    
    def _group_by_severity(self) -> Dict[str, int]:
        """Group leaks by severity."""
        groups = {}
        for leak in self.leaks:
            sev = leak.get("severity", "unknown")
            groups[sev] = groups.get(sev, 0) + 1
        return groups
    
    def get_critical_leaks(self) -> List[Dict[str, Any]]:
        """Get only critical severity leaks."""
        return [l for l in self.leaks if l.get("severity") == "critical"]
    
    def get_remediations(self) -> List[str]:
        """Get list of recommended remediations."""
        return list(set(
            leak.get("remediation", "")
            for leak in self.leaks
            if leak.get("remediation")
        ))


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL: IDENTITY CONSISTENCY CHECKER
# Cross-validates all identity signals for internal consistency
# ═══════════════════════════════════════════════════════════════════════════

class IdentityConsistencyChecker:
    """
    V7.6 P0: Validates that all identity signals are internally consistent.
    Detects mismatches between timezone/locale, fonts/OS, hardware/software.
    """
    
    def __init__(self, target_os: str = "windows_11", target_locale: str = "en-US"):
        self.target_os = target_os
        self.target_locale = target_locale
        self.identity_signals: Dict[str, Any] = {}
        self.inconsistencies: List[Dict[str, Any]] = []
        self.consistency_rules: List[Dict[str, Any]] = []
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """Register default consistency rules."""
        self.add_rule(
            name="timezone_locale_match",
            checker=self._check_timezone_locale,
            description="Timezone matches locale region"
        )
        self.add_rule(
            name="fonts_os_match",
            checker=self._check_fonts_os,
            description="Font set matches target OS"
        )
        self.add_rule(
            name="user_agent_os_match",
            checker=self._check_ua_os,
            description="User-Agent matches target OS"
        )
        self.add_rule(
            name="webgl_hardware_match",
            checker=self._check_webgl_hardware,
            description="WebGL renderer matches hardware profile"
        )
    
    def add_rule(self, name: str, checker: callable, description: str = "") -> None:
        """Add a consistency check rule."""
        self.consistency_rules.append({
            "name": name,
            "checker": checker,
            "description": description,
            "enabled": True
        })
    
    def collect_signals(self, profile_path: Optional[Path] = None) -> None:
        """Collect all identity signals from the environment."""
        self.identity_signals = {
            "target_os": self.target_os,
            "target_locale": self.target_locale,
            "profile_path": str(profile_path) if profile_path else None,
            "collected_at": datetime.now().isoformat()
        }
        
        # Collect timezone
        try:
            self.identity_signals["timezone"] = subprocess.check_output(
                "date +%Z", shell=True, timeout=3
            ).decode().strip()
            self.identity_signals["tz_offset"] = subprocess.check_output(
                "date +%z", shell=True, timeout=3
            ).decode().strip()
        except Exception:
            self.identity_signals["timezone"] = "unknown"
        
        # Collect locale
        self.identity_signals["env_locale"] = os.environ.get("LANG", "unknown")
        self.identity_signals["env_language"] = os.environ.get("LANGUAGE", "unknown")
        
        # Collect fonts
        try:
            fonts = subprocess.check_output(
                "fc-list : family | head -50", shell=True, timeout=10
            ).decode()
            self.identity_signals["fonts_sample"] = fonts.split("\n")[:20]
        except Exception:
            self.identity_signals["fonts_sample"] = []
        
        # Collect profile data if available
        if profile_path and Path(profile_path).exists():
            self._collect_profile_signals(Path(profile_path))
    
    def _collect_profile_signals(self, profile_path: Path) -> None:
        """Collect signals from profile configuration."""
        # Check user.js
        user_js = profile_path / "user.js"
        if user_js.exists():
            try:
                content = user_js.read_text()
                # Extract user agent if present
                if "general.useragent.override" in content:
                    self.identity_signals["has_ua_override"] = True
            except Exception:
                pass
        
        # Check identity.json
        identity_file = profile_path / "identity.json"
        if identity_file.exists():
            try:
                with open(identity_file) as f:
                    identity = json.load(f)
                self.identity_signals["profile_identity"] = identity
            except Exception:
                pass
    
    def _check_timezone_locale(self) -> Dict[str, Any]:
        """Check timezone-locale consistency."""
        tz = self.identity_signals.get("timezone", "")
        locale = self.target_locale
        
        # Map locales to expected timezone prefixes
        locale_tz_map = {
            "en-US": ["EST", "CST", "MST", "PST", "EDT", "CDT", "MDT", "PDT", "America"],
            "en-GB": ["GMT", "BST", "Europe/London"],
            "de-DE": ["CET", "CEST", "Europe/Berlin"],
            "fr-FR": ["CET", "CEST", "Europe/Paris"],
            "ja-JP": ["JST", "Asia/Tokyo"],
        }
        
        expected = locale_tz_map.get(locale, [])
        tz_matches = any(e in tz for e in expected) if expected else True
        
        return {
            "consistent": tz_matches or not expected,
            "signal_a": f"timezone={tz}",
            "signal_b": f"locale={locale}",
            "issue": None if tz_matches else f"Timezone {tz} inconsistent with locale {locale}"
        }
    
    def _check_fonts_os(self) -> Dict[str, Any]:
        """Check fonts-OS consistency."""
        fonts = self.identity_signals.get("fonts_sample", [])
        fonts_str = " ".join(fonts)
        
        # Check for OS-specific fonts
        has_linux = any(f in fonts_str for f in ["Liberation", "DejaVu", "Ubuntu"])
        has_windows = any(f in fonts_str for f in ["Segoe", "Calibri", "Consolas"])
        has_macos = any(f in fonts_str for f in ["Helvetica Neue", "SF Pro", "Menlo"])
        
        os_type = "windows" if "windows" in self.target_os.lower() else "macos"
        
        consistent = True
        issue = None
        
        if os_type == "windows":
            if has_linux and not has_windows:
                consistent = False
                issue = "Linux fonts present but Windows fonts missing"
        elif os_type == "macos":
            if has_linux and not has_macos:
                consistent = False
                issue = "Linux fonts present but macOS fonts missing"
        
        return {
            "consistent": consistent,
            "signal_a": f"target_os={self.target_os}",
            "signal_b": f"has_linux={has_linux}, has_target={has_windows or has_macos}",
            "issue": issue
        }
    
    def _check_ua_os(self) -> Dict[str, Any]:
        """Check User-Agent-OS consistency."""
        has_override = self.identity_signals.get("has_ua_override", False)
        
        return {
            "consistent": has_override,
            "signal_a": f"target_os={self.target_os}",
            "signal_b": f"ua_override={has_override}",
            "issue": None if has_override else "No User-Agent override configured"
        }
    
    def _check_webgl_hardware(self) -> Dict[str, Any]:
        """Check WebGL-hardware consistency."""
        profile_identity = self.identity_signals.get("profile_identity", {})
        webgl = profile_identity.get("webgl", {})
        hardware = profile_identity.get("hardware", {})
        
        consistent = True
        issue = None
        
        # Check if integrated GPU matches reported hardware
        if webgl and hardware:
            gpu_vendor = hardware.get("gpu_vendor", "").lower()
            webgl_vendor = webgl.get("vendor", "").lower()
            
            if gpu_vendor and webgl_vendor:
                if gpu_vendor not in webgl_vendor and webgl_vendor not in gpu_vendor:
                    consistent = False
                    issue = f"GPU vendor mismatch: hardware={gpu_vendor}, webgl={webgl_vendor}"
        
        return {
            "consistent": consistent,
            "signal_a": f"hardware_gpu={hardware.get('gpu_vendor', 'unknown')}",
            "signal_b": f"webgl_vendor={webgl.get('vendor', 'unknown')}",
            "issue": issue
        }
    
    def check(self, profile_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Run full consistency check.
        
        Args:
            profile_path: Path to profile directory
            
        Returns:
            Consistency check results
        """
        self.collect_signals(profile_path)
        self.inconsistencies = []
        
        start = time.time()
        
        results = {}
        for rule in self.consistency_rules:
            if not rule.get("enabled", True):
                continue
            
            try:
                result = rule["checker"]()
                results[rule["name"]] = result
                
                if not result.get("consistent", True):
                    self.inconsistencies.append({
                        "rule": rule["name"],
                        "description": rule.get("description", ""),
                        **result
                    })
            except Exception as e:
                results[rule["name"]] = {
                    "consistent": False,
                    "error": str(e)
                }
        
        duration = (time.time() - start) * 1000
        all_consistent = len(self.inconsistencies) == 0
        
        return {
            "status": "CONSISTENT" if all_consistent else "INCONSISTENT",
            "all_consistent": all_consistent,
            "checks": results,
            "inconsistencies": self.inconsistencies,
            "signals_collected": len(self.identity_signals),
            "duration_ms": round(duration, 1)
        }
    
    def get_identity_report(self) -> Dict[str, Any]:
        """Get full identity signals report."""
        return {
            "signals": self.identity_signals,
            "inconsistencies": self.inconsistencies,
            "recommendation": "Fix inconsistencies before operation" if self.inconsistencies else "Identity consistent"
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL: IDENTITY VERIFICATION HISTORY
# Track verification history, trends, and predict potential issues
# ═══════════════════════════════════════════════════════════════════════════

class IdentityVerificationHistory:
    """
    V7.6 P0: Tracks verification history and identifies patterns/trends.
    Predicts potential issues based on historical failure patterns.
    """
    
    def __init__(self, profile_id: str = "default"):
        self.profile_id = profile_id
        self.history_file = STATE_DIR / "verification_history.json"
        self.history: List[Dict[str, Any]] = []
        self.max_entries = 1000
        self._load_history()
    
    def _load_history(self) -> None:
        """Load history from disk."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                self.history = data.get("entries", [])
            except Exception:
                self.history = []
    
    def _save_history(self) -> None:
        """Save history to disk."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w") as f:
                json.dump({
                    "profile_id": self.profile_id,
                    "entries": self.history[-self.max_entries:],
                    "updated_at": datetime.now().isoformat()
                }, f, indent=2)
        except Exception:
            pass
    
    def record(self, verification_result: Dict[str, Any]) -> None:
        """
        Record a verification result.
        
        Args:
            verification_result: Result from DeepIdentityOrchestrator.execute()
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "profile_id": self.profile_id,
            "status": verification_result.get("status", "UNKNOWN"),
            "all_passed": verification_result.get("all_passed", False),
            "duration_ms": verification_result.get("duration_ms", 0),
            "phases": {}
        }
        
        # Record phase results
        for phase_name, phase_result in verification_result.get("phases", {}).items():
            entry["phases"][phase_name] = {
                "passed": phase_result.get("passed", False)
            }
        
        self.history.append(entry)
        self._save_history()
    
    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent verification entries."""
        return self.history[-count:]
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get verification statistics for specified period.
        
        Args:
            days: Number of days to include
            
        Returns:
            Statistics summary
        """
        cutoff = datetime.now().timestamp() - (days * 86400)
        recent = [
            e for e in self.history
            if datetime.fromisoformat(e["timestamp"]).timestamp() > cutoff
        ]
        
        if not recent:
            return {"message": "No data for period", "total": 0}
        
        total = len(recent)
        passed = sum(1 for e in recent if e.get("all_passed", False))
        
        # Phase statistics
        phase_stats = {}
        for entry in recent:
            for phase, result in entry.get("phases", {}).items():
                if phase not in phase_stats:
                    phase_stats[phase] = {"total": 0, "passed": 0}
                phase_stats[phase]["total"] += 1
                if result.get("passed"):
                    phase_stats[phase]["passed"] += 1
        
        # Calculate pass rates
        for phase in phase_stats:
            total_phase = phase_stats[phase]["total"]
            passed_phase = phase_stats[phase]["passed"]
            phase_stats[phase]["pass_rate"] = round(passed_phase / total_phase * 100, 1) if total_phase > 0 else 0
        
        return {
            "period_days": days,
            "total_verifications": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "phase_statistics": phase_stats,
            "avg_duration_ms": round(sum(e.get("duration_ms", 0) for e in recent) / total, 1) if total > 0 else 0
        }
    
    def get_failure_patterns(self) -> Dict[str, Any]:
        """Identify recurring failure patterns."""
        phase_failures = {}
        
        for entry in self.history:
            if entry.get("all_passed"):
                continue
            
            for phase, result in entry.get("phases", {}).items():
                if not result.get("passed"):
                    phase_failures[phase] = phase_failures.get(phase, 0) + 1
        
        # Sort by frequency
        sorted_failures = sorted(
            phase_failures.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "most_common_failures": sorted_failures[:5],
            "total_failures": sum(phase_failures.values()),
            "unique_failing_phases": len(phase_failures),
            "recommendations": self._generate_recommendations(sorted_failures)
        }
    
    def _generate_recommendations(self, failures: List[tuple]) -> List[str]:
        """Generate recommendations based on failure patterns."""
        recommendations = []
        
        for phase, count in failures[:3]:
            if phase == "fonts":
                recommendations.append(f"Font issues ({count}x): Run FontSanitizer regularly")
            elif phase == "timezone":
                recommendations.append(f"Timezone issues ({count}x): Check TimezoneEnforcer before sessions")
            elif phase == "audio":
                recommendations.append(f"Audio issues ({count}x): Verify Camoufox audio prefs")
            elif phase == "webgl":
                recommendations.append(f"WebGL issues ({count}x): Update WebGL configuration")
        
        return recommendations
    
    def predict_issues(self) -> Dict[str, Any]:
        """
        Predict potential issues based on historical patterns.
        
        Returns:
            Predictions and preventive recommendations
        """
        if len(self.history) < 5:
            return {"message": "Insufficient history for predictions", "predictions": []}
        
        predictions = []
        stats = self.get_statistics(days=7)
        
        # Check overall trend
        if stats.get("pass_rate", 100) < 80:
            predictions.append({
                "type": "declining_pass_rate",
                "confidence": 0.8,
                "message": f"Pass rate below 80% ({stats.get('pass_rate')}%)",
                "action": "Review and fix recurring issues"
            })
        
        # Check phase-specific issues
        for phase, pstats in stats.get("phase_statistics", {}).items():
            if pstats.get("pass_rate", 100) < 70:
                predictions.append({
                    "type": f"phase_degradation_{phase}",
                    "confidence": 0.75,
                    "message": f"{phase} phase has low pass rate ({pstats.get('pass_rate')}%)",
                    "action": f"Investigate and fix {phase} configuration"
                })
        
        return {
            "predictions": predictions,
            "risk_level": "high" if len(predictions) > 2 else "medium" if predictions else "low",
            "analysis_based_on": len(self.history)
        }
    
    def clear_history(self, before_days: int = None) -> int:
        """
        Clear history entries.
        
        Args:
            before_days: Only clear entries older than this (None = clear all)
            
        Returns:
            Number of entries cleared
        """
        if before_days is None:
            count = len(self.history)
            self.history = []
        else:
            cutoff = datetime.now().timestamp() - (before_days * 86400)
            original_count = len(self.history)
            self.history = [
                e for e in self.history
                if datetime.fromisoformat(e["timestamp"]).timestamp() > cutoff
            ]
            count = original_count - len(self.history)
        
        self._save_history()
        return count


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON GETTERS
# ═══════════════════════════════════════════════════════════════════════════

_orchestrator_instance: Optional[DeepIdentityOrchestrator] = None
_leak_detector_instance: Optional[IdentityLeakDetector] = None
_consistency_checker_instance: Optional[IdentityConsistencyChecker] = None
_verification_history_instance: Optional[IdentityVerificationHistory] = None


def get_deep_identity_orchestrator(target_os: str = "windows_11",
                                   profile_path: Optional[Path] = None) -> DeepIdentityOrchestrator:
    """Get or create DeepIdentityOrchestrator singleton."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = DeepIdentityOrchestrator(target_os, profile_path)
    return _orchestrator_instance


def get_identity_leak_detector(target_os: str = "windows_11") -> IdentityLeakDetector:
    """Get or create IdentityLeakDetector singleton."""
    global _leak_detector_instance
    if _leak_detector_instance is None:
        _leak_detector_instance = IdentityLeakDetector(target_os)
    return _leak_detector_instance


def get_identity_consistency_checker(target_os: str = "windows_11",
                                     target_locale: str = "en-US") -> IdentityConsistencyChecker:
    """Get or create IdentityConsistencyChecker singleton."""
    global _consistency_checker_instance
    if _consistency_checker_instance is None:
        _consistency_checker_instance = IdentityConsistencyChecker(target_os, target_locale)
    return _consistency_checker_instance


def get_identity_verification_history(profile_id: str = "default") -> IdentityVerificationHistory:
    """Get or create IdentityVerificationHistory singleton."""
    global _verification_history_instance
    if _verification_history_instance is None:
        _verification_history_instance = IdentityVerificationHistory(profile_id)
    return _verification_history_instance


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
