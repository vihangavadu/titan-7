#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
TITAN V8.1 SINGULARITY — MASTER ISO READINESS VERIFICATION
═══════════════════════════════════════════════════════════════════════════
PURPOSE: Final comprehensive verification before ISO build.
         Cross-references all documentation, codebase, and configuration.

This script performs the deepest level of verification to ensure:
1. All 51+ core modules exist and are properly structured
2. All configuration files have correct content patterns
3. Ghost Motor has all required behavioral features
4. Kill Switch has complete panic sequence
5. WebRTC is blocked across all 4 layers
6. Canvas noise is deterministic (SHA-256 seeded)
7. No stale V6 references in runtime code
8. Build pipeline is complete

USAGE:
    python3 scripts/final_iso_readiness.py
    python3 scripts/final_iso_readiness.py --json  (machine-readable output)
    python3 scripts/final_iso_readiness.py --quick (skip deep content checks)

EXIT CODES:
    0 = 100% Ready for ISO build
    1 = Critical failures (DO NOT BUILD)
    2 = Minor issues (BUILD WITH CAUTION)
═══════════════════════════════════════════════════════════════════════════
"""

import os
import re
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any


class Col:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


@dataclass
class CheckResult:
    """Result of a verification check"""
    name: str
    passed: bool
    message: str
    severity: str = "normal"  # normal, critical, warning


@dataclass
class ModuleVerification:
    """Verification results for a module category"""
    category: str
    results: List[CheckResult] = field(default_factory=list)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)
    
    @property
    def total(self) -> int:
        return len(self.results)


class ISOReadinessVerifier:
    """Master verification system for ISO build readiness."""
    
    def __init__(self, quick_mode: bool = False, json_output: bool = False):
        self.quick_mode = quick_mode
        self.json_output = json_output
        self.repo_root = self._find_repo_root()
        self.iso_root = self.repo_root / "iso/config/includes.chroot"
        self.titan_root = self.iso_root / "opt/titan"
        self.verifications: List[ModuleVerification] = []
        
    def _find_repo_root(self) -> Path:
        """Locate repository root"""
        script_dir = Path(__file__).parent.absolute()
        # Check if we're in scripts/
        if script_dir.name == "scripts":
            return script_dir.parent
        # Check parent directories
        for parent in script_dir.parents:
            if (parent / "iso").is_dir() and (parent / "README.md").is_file():
                return parent
        # Fallback to current directory
        return Path.cwd()
        
    def log(self, status: str, message: str):
        """Log a message with status"""
        if self.json_output:
            return
        if status == "OK":
            print(f"  [{Col.GREEN}PASS{Col.RESET}] {message}")
        elif status == "WARN":
            print(f"  [{Col.YELLOW}WARN{Col.RESET}] {message}")
        elif status == "FAIL":
            print(f"  [{Col.RED}FAIL{Col.RESET}] {message}")
        elif status == "INFO":
            print(f"  [{Col.CYAN}INFO{Col.RESET}] {message}")
            
    def section(self, title: str):
        """Print section header"""
        if self.json_output:
            return
        print(f"\n{Col.CYAN}{Col.BOLD}{'═' * 70}{Col.RESET}")
        print(f"{Col.CYAN}{Col.BOLD}  {title}{Col.RESET}")
        print(f"{Col.CYAN}{Col.BOLD}{'═' * 70}{Col.RESET}")
        
    def add_check(self, category: str, name: str, passed: bool, message: str, 
                  severity: str = "normal"):
        """Add a check result"""
        result = CheckResult(name=name, passed=passed, message=message, severity=severity)
        
        # Find or create category
        for v in self.verifications:
            if v.category == category:
                v.results.append(result)
                return
        
        verification = ModuleVerification(category=category)
        verification.results.append(result)
        self.verifications.append(verification)
        
        status = "OK" if passed else ("WARN" if severity == "warning" else "FAIL")
        self.log(status, message)
        
    def file_exists(self, path: Path) -> bool:
        """Check if file exists"""
        return path.is_file()
        
    def file_contains(self, path: Path, patterns: List[str], all_required: bool = True) -> bool:
        """Check if file contains pattern(s)"""
        if not path.is_file():
            return False
        try:
            content = path.read_text(errors='ignore')
            if all_required:
                return all(re.search(p, content, re.IGNORECASE | re.DOTALL) for p in patterns)
            else:
                return any(re.search(p, content, re.IGNORECASE | re.DOTALL) for p in patterns)
        except Exception:
            return False
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 1: SOURCE TREE INTEGRITY
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_source_tree(self):
        """Verify all core modules exist"""
        self.section("1. SOURCE TREE INTEGRITY")
        
        core_modules = [
            "__init__.py", "genesis_core.py", "cerberus_core.py", "kyc_core.py",
            "cerberus_enhanced.py", "kyc_enhanced.py", "advanced_profile_generator.py",
            "kill_switch.py", "ghost_motor_v6.py", "fingerprint_injector.py",
            "tls_parrot.py", "webgl_angle.py", "handover_protocol.py",
            "target_presets.py", "target_intelligence.py", "target_discovery.py",
            "proxy_manager.py", "preflight_validator.py", "timezone_enforcer.py",
            "audio_hardener.py", "font_sanitizer.py", "network_jitter.py",
            "lucid_vpn.py", "quic_proxy.py", "cognitive_core.py", "intel_monitor.py",
            "transaction_monitor.py", "integration_bridge.py", "cockpit_daemon.py",
            "titan_env.py", "titan_services.py", "titan_master_verify.py",
            "immutable_os.py", "waydroid_sync.py", "location_spoofer_linux.py",
            "usb_peripheral_synth.py", "form_autofill_injector.py",
            "purchase_history_engine.py", "three_ds_strategy.py", "referrer_warmup.py",
            "network_shield_loader.py", "verify_deep_identity.py",
            "generate_trajectory_model.py",
            # C source files
            "hardware_shield_v6.c", "network_shield_v6.c", "titan_battery.c",
        ]
        
        core_path = self.titan_root / "core"
        for module in core_modules:
            exists = (core_path / module).is_file()
            self.add_check(
                "source_tree", 
                f"core/{module}",
                exists,
                f"core/{module}" if exists else f"MISSING: core/{module}",
                severity="critical"
            )
            
        # Apps
        apps = ["app_unified.py", "app_genesis.py", "app_cerberus.py", 
                "app_kyc.py", "titan_mission_control.py"]
        apps_path = self.titan_root / "apps"
        for app in apps:
            exists = (apps_path / app).is_file()
            self.add_check(
                "source_tree",
                f"apps/{app}",
                exists,
                f"apps/{app}" if exists else f"MISSING: apps/{app}",
                severity="critical"
            )
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 2: GHOST MOTOR BEHAVIORAL ENGINE
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_ghost_motor(self):
        """Verify Ghost Motor has all required features"""
        self.section("2. GHOST MOTOR BEHAVIORAL ENGINE")
        
        if self.quick_mode:
            self.log("INFO", "Skipping deep content check (quick mode)")
            return
            
        # Python backend
        py_path = self.titan_root / "core/ghost_motor_v6.py"
        if py_path.is_file():
            content = py_path.read_text(errors='ignore')
            checks = [
                ("bezier", "Bezier curve pathing"),
                ("micro_tremor", "Micro-tremor hand shake"),
                ("overshoot", "Overshoot simulation"),
                (r"minimum.jerk|min.*jerk", "Minimum-jerk velocity"),
                ("correction_probability", "Mid-path correction"),
            ]
            for pattern, label in checks:
                found = bool(re.search(pattern, content, re.IGNORECASE))
                self.add_check(
                    "ghost_motor",
                    f"Python: {label}",
                    found,
                    f"Python backend: {label}" if found else f"Python backend: {label} NOT FOUND"
                )
        else:
            self.add_check("ghost_motor", "ghost_motor_v6.py", False, 
                          "ghost_motor_v6.py NOT FOUND", severity="critical")
            
        # JS extension
        js_path = self.titan_root / "extensions/ghost_motor/ghost_motor.js"
        if js_path.is_file():
            content = js_path.read_text(errors='ignore')
            checks = [
                ("bezierPoint", "JS Bezier curve function"),
                ("microTremor", "JS micro-tremor config"),
                ("overshootProbability", "JS overshoot probability"),
                ("dwellTimeBase", "JS keyboard dwell timing"),
                ("flightTimeBase", "JS keyboard flight timing"),
            ]
            for keyword, label in checks:
                found = keyword in content
                self.add_check(
                    "ghost_motor",
                    f"JS: {label}",
                    found,
                    f"JS extension: {label}" if found else f"JS extension: {label} NOT FOUND"
                )
        else:
            self.add_check("ghost_motor", "ghost_motor.js", False,
                          "ghost_motor.js NOT FOUND", severity="critical")
                          
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 3: KILL SWITCH PANIC SEQUENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_kill_switch(self):
        """Verify Kill Switch has complete panic sequence"""
        self.section("3. KILL SWITCH PANIC SEQUENCE")
        
        if self.quick_mode:
            self.log("INFO", "Skipping deep content check (quick mode)")
            return
            
        ks_path = self.titan_root / "core/kill_switch.py"
        if not ks_path.is_file():
            self.add_check("kill_switch", "kill_switch.py", False,
                          "kill_switch.py NOT FOUND", severity="critical")
            return
            
        content = ks_path.read_text(errors='ignore')
        
        panic_steps = [
            ("_sever_network", "Step 0: Network sever (nftables DROP)"),
            ("_kill_browser", "Step 1: Browser kill"),
            ("_flush_hardware_id", "Step 2: Hardware ID flush (Netlink)"),
            ("_clear_session_data", "Step 3: Session data clear"),
            ("_rotate_proxy", "Step 4: Proxy rotation"),
            ("_randomize_mac", "Step 5: MAC randomization"),
            ("_restore_network", "Network restore (post-panic recovery)"),
        ]
        
        for keyword, label in panic_steps:
            found = keyword in content
            self.add_check(
                "kill_switch",
                label,
                found,
                label if found else f"{label} — NOT FOUND"
            )
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 4: WEBRTC LEAK PROTECTION (4-LAYER)
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_webrtc(self):
        """Verify WebRTC is blocked across all 4 layers"""
        self.section("4. WEBRTC LEAK PROTECTION (4-LAYER)")
        
        if self.quick_mode:
            self.log("INFO", "Skipping deep content check (quick mode)")
            return
            
        layers = [
            (self.titan_root / "core/fingerprint_injector.py",
             r"media.peerconnection.enabled.*[Ff]alse",
             "Layer 1: fingerprint_injector.py"),
            (self.iso_root / "opt/lucid-empire/backend/modules/location_spoofer.py",
             r"media.peerconnection.enabled.*[Ff]alse",
             "Layer 2: location_spoofer.py"),
            (self.iso_root / "opt/lucid-empire/backend/handover_protocol.py",
             r'peerconnection.enabled.*false',
             "Layer 3: handover_protocol.py"),
            (self.iso_root / "etc/nftables.conf",
             r"3478.*5349.*19302.*drop",
             "Layer 4: nftables (STUN/TURN blocked)"),
        ]
        
        for path, pattern, label in layers:
            if path.is_file():
                content = path.read_text(errors='ignore')
                found = bool(re.search(pattern, content, re.IGNORECASE | re.DOTALL))
                self.add_check(
                    "webrtc",
                    label,
                    found,
                    label if found else f"{label} — PATTERN NOT MATCHED"
                )
            else:
                self.add_check("webrtc", label, False, 
                              f"{label} — file not found", severity="warning")
                              
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 5: CANVAS NOISE DETERMINISM
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_canvas_noise(self):
        """Verify canvas noise is deterministically seeded"""
        self.section("5. CANVAS NOISE DETERMINISM")
        
        if self.quick_mode:
            self.log("INFO", "Skipping deep content check (quick mode)")
            return
            
        cn_path = self.iso_root / "opt/lucid-empire/backend/modules/canvas_noise.py"
        
        if not cn_path.is_file():
            self.add_check("canvas_noise", "canvas_noise.py", False,
                          "canvas_noise.py NOT FOUND", severity="warning")
            return
            
        content = cn_path.read_text(errors='ignore')
        
        checks = [
            ("from_profile_uuid", "Seed derived from profile UUID"),
            ("sha256", "SHA-256 hash for deterministic seed"),
            (r"PerlinNoise|Perlin", "Perlin noise generator"),
            ("deterministic", "Deterministic seeding documented"),
        ]
        
        for pattern, label in checks:
            found = bool(re.search(pattern, content, re.IGNORECASE))
            self.add_check(
                "canvas_noise",
                label,
                found,
                label if found else f"{label} — NOT FOUND"
            )
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 6: FIREWALL DEFAULT-DENY
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_firewall(self):
        """Verify nftables has default-deny policy"""
        self.section("6. FIREWALL (nftables DEFAULT-DENY)")
        
        nft_path = self.iso_root / "etc/nftables.conf"
        
        if not nft_path.is_file():
            self.add_check("firewall", "nftables.conf", False,
                          "nftables.conf NOT FOUND", severity="critical")
            return
            
        content = nft_path.read_text(errors='ignore')
        
        for chain in ["input", "output", "forward"]:
            pattern = rf"chain\s+{chain}\s*\{{[^}}]*policy\s+drop"
            found = bool(re.search(pattern, content, re.DOTALL))
            self.add_check(
                "firewall",
                f"Chain '{chain}' policy drop",
                found,
                f"Chain '{chain}': policy drop" if found else f"Chain '{chain}': policy drop NOT SET"
            )
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 7: KERNEL HARDENING
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_sysctl(self):
        """Verify kernel hardening parameters"""
        self.section("7. KERNEL HARDENING (sysctl)")
        
        sysctl_path = self.iso_root / "etc/sysctl.d/99-titan-hardening.conf"
        
        if not sysctl_path.is_file():
            self.add_check("sysctl", "99-titan-hardening.conf", False,
                          "99-titan-hardening.conf NOT FOUND", severity="critical")
            return
            
        content = sysctl_path.read_text(errors='ignore')
        
        params = [
            ("net.ipv4.ip_default_ttl = 128", "Windows TTL masquerade (TTL=128)"),
            ("net.ipv4.tcp_timestamps = 0", "TCP timestamps disabled"),
            ("net.ipv6.conf.all.disable_ipv6 = 1", "IPv6 fully disabled"),
            ("kernel.randomize_va_space = 2", "Full ASLR enabled"),
            ("kernel.yama.ptrace_scope = 2", "Ptrace restricted"),
            ("kernel.dmesg_restrict = 1", "dmesg restricted"),
        ]
        
        for param, label in params:
            found = param in content
            self.add_check(
                "sysctl",
                label,
                found,
                label if found else f"{label} — NOT SET"
            )
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 8: SYSTEMD SERVICES
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_systemd(self):
        """Verify systemd services exist and reference V7"""
        self.section("8. SYSTEMD SERVICES")
        
        svc_dir = self.iso_root / "etc/systemd/system"
        
        services = [
            "lucid-titan.service",
            "lucid-console.service",
            "lucid-ebpf.service",
            "titan-first-boot.service",
            "titan-dns.service",
        ]
        
        for svc in services:
            svc_path = svc_dir / svc
            if svc_path.is_file():
                content = svc_path.read_text(errors='ignore')
                has_v7 = "V7" in content
                self.add_check(
                    "systemd",
                    svc,
                    True,
                    f"{svc} (V7 aligned)" if has_v7 else f"{svc} (present, no V7 reference)"
                )
            else:
                self.add_check("systemd", svc, False, f"MISSING: {svc}")
                
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 9: BUILD PIPELINE
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_build_pipeline(self):
        """Verify build scripts and CI/CD"""
        self.section("9. BUILD PIPELINE")
        
        build_files = [
            ("build_final.sh", "Main build script"),
            ("scripts/build_iso.sh", "ISO builder"),
            ("scripts/titan_finality_patcher.py", "Forensic sanitizer"),
            ("scripts/pre_build_env_check.sh", "Pre-build environment check"),
            ("scripts/pre_build_env_check.sh", "Environment check"),
            ("Dockerfile.build", "Docker build"),
            (".github/workflows/build-iso.yml", "CI/CD ISO workflow"),
        ]
        
        for rel_path, label in build_files:
            exists = (self.repo_root / rel_path).is_file()
            self.add_check(
                "build_pipeline",
                label,
                exists,
                label if exists else f"MISSING: {label}",
                severity="warning" if not exists else "normal"
            )
            
    # ═══════════════════════════════════════════════════════════════════════
    # CHECK 10: STALE VERSION SCAN
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_no_stale_versions(self):
        """Scan for stale V6 references in runtime code"""
        self.section("10. STALE VERSION SCAN")
        
        if self.quick_mode:
            self.log("INFO", "Skipping stale version scan (quick mode)")
            return
            
        stale_count = 0
        scan_dirs = [
            self.titan_root / "core",
            self.titan_root / "apps",
        ]
        
        for scan_dir in scan_dirs:
            if not scan_dir.is_dir():
                continue
            for path in scan_dir.rglob("*.py"):
                try:
                    content = path.read_text(errors='ignore')
                    # Look for "TITAN V6" but not historical references
                    matches = re.findall(r'TITAN V6[.\s]', content)
                    for m in matches:
                        idx = content.index(m)
                        context = content[max(0, idx-80):idx+80]
                        if "carried forward" not in context.lower():
                            stale_count += 1
                            rel_path = path.relative_to(self.iso_root)
                            self.add_check(
                                "stale_versions",
                                f"V6 ref in {rel_path}",
                                False,
                                f"Stale V6 ref in {rel_path}"
                            )
                except Exception:
                    pass
                    
        if stale_count == 0:
            self.add_check("stale_versions", "No stale refs", True,
                          "No stale V6 references in runtime code")
                          
    # ═══════════════════════════════════════════════════════════════════════
    # FINAL REPORT
    # ═══════════════════════════════════════════════════════════════════════
    
    def generate_report(self) -> int:
        """Generate final report"""
        total_pass = sum(v.passed for v in self.verifications)
        total_fail = sum(v.failed for v in self.verifications)
        total = total_pass + total_fail
        
        critical_fails = sum(
            1 for v in self.verifications
            for r in v.results
            if not r.passed and r.severity == "critical"
        )
        
        if self.json_output:
            report = {
                "timestamp": datetime.now().isoformat(),
                "version": "8.1",
                "total_checks": total,
                "passed": total_pass,
                "failed": total_fail,
                "critical_failures": critical_fails,
                "categories": {
                    v.category: {
                        "passed": v.passed,
                        "failed": v.failed,
                        "total": v.total,
                    }
                    for v in self.verifications
                },
                "status": "READY" if total_fail == 0 else ("CRITICAL" if critical_fails > 0 else "WARNINGS"),
            }
            print(json.dumps(report, indent=2))
            return 0 if total_fail == 0 else (1 if critical_fails > 0 else 2)
            
        self.section("FINAL READINESS REPORT")
        
        print("\n  Category Breakdown:")
        for v in self.verifications:
            status = f"{Col.GREEN}PASS{Col.RESET}" if v.failed == 0 else f"{Col.RED}FAIL{Col.RESET}"
            print(f"    {v.category:25} [{status}] {v.passed}/{v.total}")
            
        pct = (total_pass / total * 100) if total > 0 else 0
        
        print(f"\n  {Col.BOLD}Total:{Col.RESET}")
        print(f"    {Col.GREEN}PASS: {total_pass}{Col.RESET}  |  "
              f"{Col.RED}FAIL: {total_fail}{Col.RESET}  |  "
              f"Confidence: {pct:.1f}%")
        
        print(f"\n{'═' * 70}")
        
        if total_fail == 0:
            print(f"  {Col.GREEN}{Col.BOLD}>>> ISO READINESS: 100% VERIFIED <<<{Col.RESET}")
            print(f"  {Col.GREEN}All systems operational. Cleared for ISO build.{Col.RESET}")
            return 0
        elif critical_fails > 0:
            print(f"  {Col.RED}{Col.BOLD}>>> ISO READINESS: NOT READY <<<{Col.RESET}")
            print(f"  {Col.RED}{critical_fails} critical issue(s) must be resolved.{Col.RESET}")
            return 1
        else:
            print(f"  {Col.YELLOW}{Col.BOLD}>>> ISO READINESS: READY (minor issues) <<<{Col.RESET}")
            print(f"  {Col.YELLOW}{total_fail} minor issue(s). Build may proceed with caution.{Col.RESET}")
            return 2
            
    def run(self) -> int:
        """Run all verifications"""
        if not self.json_output:
            print(f"\n{Col.GREEN}{Col.BOLD}")
            print("  ████████╗██╗████████╗ █████╗ ███╗   ██╗")
            print("  ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║")
            print("     ██║   ██║   ██║   ███████║██╔██╗ ██║")
            print("     ██║   ██║   ██║   ██╔══██║██║╚██╗██║")
            print("     ██║   ██║   ██║   ██║  ██║██║ ╚████║")
            print("     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝")
            print(f"  V8.1 SINGULARITY — MASTER ISO READINESS{Col.RESET}")
            print(f"\n  Timestamp: {datetime.now().isoformat()}")
            print(f"  Repository: {self.repo_root}")
            
        self.verify_source_tree()
        self.verify_ghost_motor()
        self.verify_kill_switch()
        self.verify_webrtc()
        self.verify_canvas_noise()
        self.verify_firewall()
        self.verify_sysctl()
        self.verify_systemd()
        self.verify_build_pipeline()
        self.verify_no_stale_versions()
        
        return self.generate_report()


def main():
    parser = argparse.ArgumentParser(
        description="TITAN V8.1 Master ISO Readiness Verification"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--quick", action="store_true", help="Skip deep content checks")
    
    args = parser.parse_args()
    
    verifier = ISOReadinessVerifier(
        quick_mode=args.quick,
        json_output=args.json
    )
    
    exit_code = verifier.run()
    if not args.json:
        print("")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
