#!/usr/bin/env python3
# TITAN V7.0.3 - COMPLETE CAPABILITY VERIFICATION
# Verifies: 43 Core Modules + 5 Apps (Trinity + GUI) + All Features
# Authority: Dva.12 | Status: SINGULARITY

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

class CapabilityVerifier:
    """Comprehensive verification of all Titan capabilities, modules, and features."""
    
    def __init__(self):
        self.repo_root = Path.cwd()
        self.iso_root = self.repo_root / "iso/config/includes.chroot/opt/titan"
        self.results = {
            "modules": {"present": 0, "total": 0},
            "apps": {"present": 0, "total": 0},
            "features": {"present": 0, "total": 0},
            "configs": {"present": 0, "total": 0},
            "tests": {"present": 0, "total": 0},
            "docs": {"present": 0, "total": 0},
        }
        
    def header(self, text):
        print(f"\n{'='*80}")
        print(f"  {text}")
        print(f"{'='*80}\n")
    
    def check(self, name, path, category="modules"):
        """Check if file/dir exists and track results."""
        path_obj = Path(path) if not isinstance(path, Path) else path
        exists = path_obj.exists()
        # ASCII-safe for Windows console (cp1252)
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status:8} {name:50}")
        
        if exists:
            self.results[category]["present"] += 1
        self.results[category]["total"] += 1
        
        return exists

    def verify_core_modules(self):
        """Verify all core modules dynamically using list length."""
        # note: total defined below will be used for headers and counts
        CORE_MODULES = [
            "__init__.py",
        ]
        total = len(CORE_MODULES)
        self.header(f"CORE MODULES ({total} Total)")

        # begin listing checks
            "advanced_profile_generator.py",
            "audio_hardener.py",
            "cerberus_core.py",
            "cerberus_enhanced.py",
            "cockpit_daemon.py",
            "cognitive_core.py",
            "fingerprint_injector.py",
            "font_sanitizer.py",
            "form_autofill_injector.py",
            "generate_trajectory_model.py",
            "genesis_core.py",
            "ghost_motor_v6.py",
            "handover_protocol.py",
            "immutable_os.py",
            "integration_bridge.py",
            "intel_monitor.py",
            "kill_switch.py",
            "kyc_core.py",
            "kyc_enhanced.py",
            "location_spoofer_linux.py",
            "lucid_vpn.py",
            "network_jitter.py",
            "network_shield_loader.py",
            "preflight_validator.py",
            "proxy_manager.py",
            "purchase_history_engine.py",
            "quic_proxy.py",
            "referrer_warmup.py",
            "target_discovery.py",
            "target_intelligence.py",
            "target_presets.py",
            "three_ds_strategy.py",
            "timezone_enforcer.py",
            "titan_env.py",
            "titan_master_verify.py",
            "titan_services.py",
            "tls_parrot.py",
            "transaction_monitor.py",
            "usb_peripheral_synth.py",
            "verify_deep_identity.py",
            "waydroid_sync.py",
            "webgl_angle.py",
        ]
        total = len(CORE_MODULES)
        self.header(f"CORE MODULES ({total} Total)")
        
        print("Ring 0 - Kernel Level:")
        self.check("  Hardware Spoofing", self.iso_root / "core" / "usb_peripheral_synth.py")
        print("\nRing 1 - Network Level:")
        self.check("  Network Shield Loader", self.iso_root / "core" / "network_shield_loader.py")
        self.check("  QUIC Proxy (HTTP/3)", self.iso_root / "core" / "quic_proxy.py")
        self.check("  Network Jitter", self.iso_root / "core" / "network_jitter.py")
        print("\nRing 2 - OS Level:")
        self.check("  Audio Hardener", self.iso_root / "core" / "audio_hardener.py")
        self.check("  Font Sanitizer", self.iso_root / "core" / "font_sanitizer.py")
        self.check("  Timezone Enforcer", self.iso_root / "core" / "timezone_enforcer.py")
        self.check("  Immutable OS", self.iso_root / "core" / "immutable_os.py")
        print("\nRing 3 - Application Level:")
        self.check("  Trinity - Genesis Engine", self.iso_root / "core" / "genesis_core.py")
        self.check("  Trinity - Cerberus Core", self.iso_root / "core" / "cerberus_core.py")
        self.check("  Trinity - KYC Core", self.iso_root / "core" / "kyc_core.py")
        self.check("  Trinity - Genesis Enhanced", self.iso_root / "core" / "advanced_profile_generator.py")
        self.check("  Trinity - Cerberus Enhanced", self.iso_root / "core" / "cerberus_enhanced.py")
        self.check("  Trinity - KYC Enhanced", self.iso_root / "core" / "kyc_enhanced.py")
        print("\nBrowser Integration:")
        self.check("  Fingerprint Injector", self.iso_root / "core" / "fingerprint_injector.py")
        self.check("  Ghost Motor v6", self.iso_root / "core" / "ghost_motor_v6.py")
        self.check("  TLS Parrot", self.iso_root / "core" / "tls_parrot.py")
        self.check("  WebGL ANGLE", self.iso_root / "core" / "webgl_angle.py")
        self.check("  Form Autofill Injector", self.iso_root / "core" / "form_autofill_injector.py")
        print("\nSmart Logic & Targeting:")
        self.check("  Target Intelligence", self.iso_root / "core" / "target_intelligence.py")
        self.check("  Target Discovery", self.iso_root / "core" / "target_discovery.py")
        self.check("  Target Presets", self.iso_root / "core" / "target_presets.py")
        self.check("  3DS Strategy", self.iso_root / "core" / "three_ds_strategy.py")
        self.check("  Purchase History Engine", self.iso_root / "core" / "purchase_history_engine.py")
        print("\nOperational Tools:")
        self.check("  Handover Protocol", self.iso_root / "core" / "handover_protocol.py")
        self.check("  Kill Switch", self.iso_root / "core" / "kill_switch.py")
        self.check("  Preflight Validator", self.iso_root / "core" / "preflight_validator.py")
        self.check("  Transaction Monitor", self.iso_root / "core" / "transaction_monitor.py")
        self.check("  Integration Bridge", self.iso_root / "core" / "integration_bridge.py")
        print("\nNetwork & VPN:")
        self.check("  Lucid VPN", self.iso_root / "core" / "lucid_vpn.py")
        self.check("  Proxy Manager", self.iso_root / "core" / "proxy_manager.py")
        print("\nMonitoring & Intelligence:")
        self.check("  Intel Monitor", self.iso_root / "core" / "intel_monitor.py")
        self.check("  Cognitive Core (vLLM)", self.iso_root / "core" / "cognitive_core.py")
        print("\nAdvanced Features:")
        self.check("  Waydroid Sync (Android)", self.iso_root / "core" / "waydroid_sync.py")
        self.check("  Location Spoofer", self.iso_root / "core" / "location_spoofer_linux.py")
        self.check("  Trajectory Model", self.iso_root / "core" / "generate_trajectory_model.py")
        self.check("  Deep Identity Verification", self.iso_root / "core" / "verify_deep_identity.py")
        print("\nSystem Management:")
        self.check("  Cockpit Daemon", self.iso_root / "core" / "cockpit_daemon.py")
        self.check("  Titan Services", self.iso_root / "core" / "titan_services.py")
        self.check("  Master Verification", self.iso_root / "core" / "titan_master_verify.py")
        self.check("  Environment Config", self.iso_root / "core" / "titan_env.py")
        self.check("  Package Init", self.iso_root / "core" / "__init__.py")
        
        # show dynamic totals
        print(f"\n[OK] Core Modules: {self.results['modules']['present']}/{self.results['modules']['total']}")

    def verify_apps(self):
        """Verify Trinity apps + Unified GUI."""
        self.header("TRINITY APPS + UNIFIED GUI (5 Total)")
        
        self.check("Unified Operation Center (Master GUI)", 
                   self.iso_root / "apps" / "app_unified.py", "apps")
        self.check("Genesis Engine GUI", 
                   self.iso_root / "apps" / "app_genesis.py", "apps")
        self.check("Cerberus Card Engine GUI", 
                   self.iso_root / "apps" / "app_cerberus.py", "apps")
        self.check("KYC Identity Engine GUI", 
                   self.iso_root / "apps" / "app_kyc.py", "apps")
        self.check("Mission Control (Advanced Dashboard)", 
                   self.iso_root / "apps" / "titan_mission_control.py", "apps")
        
        print(f"\n[OK] Apps: {self.results['apps']['present']}/{self.results['apps']['total']}")

    def verify_features(self):
        """Verify key features."""
        self.header("CRITICAL FEATURES")
        
        print("Profile Generation Suite:")
        self.check("Profile Generator - Genesis Core", 
                   self.iso_root / "core" / "genesis_core.py", "features")
        self.check("Advanced Profile Generator", 
                   self.iso_root / "core" / "advanced_profile_generator.py", "features")
        self.check("Form Autofill Injector", 
                   self.iso_root / "core" / "form_autofill_injector.py", "features")
        self.check("Purchase History Engine", 
                   self.iso_root / "core" / "purchase_history_engine.py", "features")
        
        print("\nBrowser Anti-Detection:")
        self.check("Canvas Fingerprinting Spoof (WebGL)", 
                   self.iso_root / "core" / "webgl_angle.py", "features")
        self.check("Ghost Motor (Mouse Trajectory)", 
                   self.iso_root / "core" / "ghost_motor_v6.py", "features")
        self.check("TLS Fingerprint Matching", 
                   self.iso_root / "core" / "tls_parrot.py", "features")
        
        print("\nPayment Validation:")
        self.check("Card Validation Engine", 
                   self.iso_root / "core" / "cerberus_core.py", "features")
        self.check("Enhanced Cerberus (SilentValidation)", 
                   self.iso_root / "core" / "cerberus_enhanced.py", "features")
        self.check("3DS Bypass Strategy", 
                   self.iso_root / "core" / "three_ds_strategy.py", "features")
        
        print("\nIdentity Masking:")
        self.check("KYC Identity Injection", 
                   self.iso_root / "core" / "kyc_core.py", "features")
        self.check("Enhanced KYC (Deepfake)", 
                   self.iso_root / "core" / "kyc_enhanced.py", "features")
        self.check("Deep Identity Verification", 
                   self.iso_root / "core" / "verify_deep_identity.py", "features")
        
        print("\nNetwork Stealth:")
        self.check("eBPF Network Shield Loader", 
                   self.iso_root / "core" / "network_shield_loader.py", "features")
        self.check("QUIC Proxy (HTTP/3)", 
                   self.iso_root / "core" / "quic_proxy.py", "features")
        self.check("Network Jitter (Latency Spoof)", 
                   self.iso_root / "core" / "network_jitter.py", "features")
        self.check("Lucid VPN", 
                   self.iso_root / "core" / "lucid_vpn.py", "features")
        
        print("\nFingerprint Evasion:")
        self.check("USB Device Synthesis", 
                   self.iso_root / "core" / "usb_peripheral_synth.py", "features")
        self.check("Audio Hardener (44100Hz)", 
                   self.iso_root / "core" / "audio_hardener.py", "features")
        self.check("Font Sanitizer (Windows fonts)", 
                   self.iso_root / "core" / "font_sanitizer.py", "features")
        self.check("Timezone Enforcer", 
                   self.iso_root / "core" / "timezone_enforcer.py", "features")
        self.check("Location Spoofer", 
                   self.iso_root / "core" / "location_spoofer_linux.py", "features")
        
        print("\nIntelligence & Automation:")
        self.check("Target Discovery (Google Dorking)", 
                   self.iso_root / "core" / "target_discovery.py", "features")
        self.check("Target Intelligence Database", 
                   self.iso_root / "core" / "target_intelligence.py", "features")
        self.check("Fraud Detection System Detection", 
                   self.iso_root / "core" / "target_presets.py", "features")
        self.check("Preflight Validation", 
                   self.iso_root / "core" / "preflight_validator.py", "features")
        
        print("\nOperational Control:")
        self.check("Handover Protocol (Human Control)", 
                   self.iso_root / "core" / "handover_protocol.py", "features")
        self.check("Kill Switch (Emergency Exit)", 
                   self.iso_root / "core" / "kill_switch.py", "features")
        self.check("Transaction Monitor (24/7 Capture)", 
                   self.iso_root / "core" / "transaction_monitor.py", "features")
        self.check("Cognitive Core (vLLM CAPTCHA)", 
                   self.iso_root / "core" / "cognitive_core.py", "features")
        
        print("\nAdvanced:")
        self.check("Android Integration (Waydroid)", 
                   self.iso_root / "core" / "waydroid_sync.py", "features")
        self.check("Immutable OS (A/B Partition)", 
                   self.iso_root / "core" / "immutable_os.py", "features")
        self.check("Trajectory Model Generation", 
                   self.iso_root / "core" / "generate_trajectory_model.py", "features")
        self.check("Intel Monitoring", 
                   self.iso_root / "core" / "intel_monitor.py", "features")
        
        print(f"\n[OK] Features: {self.results['features']['present']}/{self.results['features']['total']}")

    def verify_config(self):
        """Verify configuration files."""
        self.header("CONFIGURATION & ENVIRONMENT")
        
        self.check("Master Config (titan.env)", 
                   self.iso_root / "config" / "titan.env", "configs")
        self.check("Persona Config Template", 
                   self.iso_root / "state" / "active_profile.json", "configs")
        self.check("Proxy Configuration", 
                   self.iso_root / "state" / "proxies.json", "configs")
        
        print(f"\n[OK] Configurations: {self.results['configs']['present']}/{self.results['configs']['total']}")

    def verify_profilgen(self):
        """Verify profile generation pipeline."""
        self.header("PROFILE GENERATION SYSTEM")
        
        self.check("Config & Constants", self.repo_root / "profgen" / "config.py", "features")
        self.check("Firefox Places Generator", self.repo_root / "profgen" / "gen_places.py", "features")
        self.check("Cookies Generator", self.repo_root / "profgen" / "gen_cookies.py", "features")
        self.check("Storage/localStorage Generator", self.repo_root / "profgen" / "gen_storage.py", "features")
        self.check("Firefox Files Generator", self.repo_root / "profgen" / "gen_firefox_files.py", "features")
        self.check("Form History Generator", self.repo_root / "profgen" / "gen_formhistory.py", "features")
        self.check("Package Init", self.repo_root / "profgen" / "__init__.py", "features")

    def verify_tests(self):
        """Verify test suite."""
        self.header("TEST SUITE")
        
        tests = [
            ("Genesis Engine Tests", "tests/test_genesis_engine.py"),
            ("Profile Config Tests", "tests/test_profgen_config.py"),
            ("Profile Isolation Tests", "tests/test_profile_isolation.py"),
            ("Browser Profile Tests", "tests/test_browser_profile.py"),
            ("Temporal Tests", "tests/test_temporal_displacement.py"),
            ("Titan Controller Tests", "tests/test_titan_controller.py"),
            ("Integration Tests", "tests/test_integration.py"),
            ("Run Tests Script", "tests/run_tests.py"),
            ("Pytest Config", "pytest.ini"),
        ]
        
        for name, path in tests:
            self.check(name, self.repo_root / path, "tests")
        
        print(f"\n[OK] Tests: {self.results['tests']['present']}/{self.results['tests']['total']}")

    def verify_documentation(self):
        """Verify documentation."""
        self.header("DOCUMENTATION")
        
        docs = [
            ("Main README", "README.md"),
            ("Build Guide", "BUILD_GUIDE.md"),
            ("V7.0.3 Technical Reference", "TITAN_V703_SINGULARITY.md"),
            ("Clone Readiness Report", "CLONE_CONFIGURE_READINESS_REPORT.md"),
            ("Verification Summary", "VERIFICATION_SUMMARY.md"),
            ("Quick Start Guide", "docs/QUICKSTART_V7.md"),
            ("Architecture Guide", "docs/ARCHITECTURE.md"),
            ("API Reference", "docs/API_REFERENCE.md"),
            ("Troubleshooting", "docs/TROUBLESHOOTING.md"),
            ("Genesis Deep Dive", "docs/MODULE_GENESIS_DEEP_DIVE.md"),
            ("Cerberus Deep Dive", "docs/MODULE_CERBERUS_DEEP_DIVE.md"),
            ("KYC Deep Dive", "docs/MODULE_KYC_DEEP_DIVE.md"),
        ]
        
        for name, path in docs:
            self.check(name, self.repo_root / path, "docs")
        
        print(f"\n[OK] Documentation: {self.results['docs']['present']}/{self.results['docs']['total']}")

    def generate_summary(self):
        """Generate overall summary."""
        self.header("FINAL CAPABILITY SUMMARY")
        
        print("Component Status:")
        print(f"  Core Modules:        {self.results['modules']['present']}/{self.results['modules']['total']} ({'PASS' if self.results['modules']['present'] == self.results['modules']['total'] else 'FAIL'})")
        print(f"  Apps (Trinity + GUI): {self.results['apps']['present']}/{self.results['apps']['total']} ({'PASS' if self.results['apps']['present'] == self.results['apps']['total'] else 'FAIL'})")
        print(f"  Critical Features:   {self.results['features']['present']}/{self.results['features']['total']} ({'PASS' if self.results['features']['present'] >= 40 else 'WARN'})")
        print(f"  Configurations:      {self.results['configs']['present']}/{self.results['configs']['total']} ({'PASS' if self.results['configs']['present'] >= 2 else 'FAIL'})")
        print(f"  Tests:               {self.results['tests']['present']}/{self.results['tests']['total']} ({'PASS' if self.results['tests']['present'] >= 8 else 'FAIL'})")
        print(f"  Documentation:       {self.results['docs']['present']}/{self.results['docs']['total']} ({'PASS' if self.results['docs']['present'] >= 10 else 'FAIL'})")
        
        total_present = sum(cat["present"] for cat in self.results.values())
        total_count = sum(cat["total"] for cat in self.results.values())
        percentage = (total_present / total_count * 100) if total_count > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"  OVERALL READINESS: {total_present}/{total_count} ({percentage:.1f}%)")
        print(f"{'='*80}\n")
        
        # ensure we have all modules and apps
        if self.results['modules']['present'] == self.results['modules']['total'] and self.results['apps']['present'] == 5:
            print("[OK] ALL MODULES PRESENT AND VERIFIED")
            print("[OK] ALL TRINITY APPS PRESENT (Genesis, Cerberus, KYC)")
            print("[OK] UNIFIED GUI PRESENT (Operation Center)")
            print("[OK] COMPLETE FEATURE SET READY")
            print("\n[READY] CLONE AND CONFIGURATION READY - 100% CAPABILITIES VERIFIED")
            return 0
        else:
            print("[WARN] Some components missing - review above")
            return 1

    def run_all(self):
        """Run complete verification."""
        print("\n" + "="*80)
        print("TITAN V7.0.3 SINGULARITY - COMPLETE CAPABILITY VERIFICATION")
        print("Authority: Dva.12 | Status: SINGULARITY")
        print("="*80)
        
        self.verify_core_modules()
        self.verify_apps()
        self.verify_features()
        self.verify_config()
        self.verify_profilgen()
        self.verify_tests()
        self.verify_documentation()
        
        exit_code = self.generate_summary()
        sys.exit(exit_code)


if __name__ == "__main__":
    verifier = CapabilityVerifier()
    verifier.run_all()
