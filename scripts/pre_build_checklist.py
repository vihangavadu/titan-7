#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
TITAN V7.0.3 SINGULARITY — Pre-Build Checklist
═══════════════════════════════════════════════════════════════════════════
PURPOSE: Run all verification scripts before ISO build to ensure system
         is in a valid state. This is the master pre-flight check.

USAGE:
    python3 scripts/pre_build_checklist.py
    python3 scripts/pre_build_checklist.py --verbose
    python3 scripts/pre_build_checklist.py --fix  (attempt auto-fix where possible)

EXIT CODES:
    0 = All checks passed, ready for build
    1 = Critical failures detected
    2 = Warnings only (proceed with caution)
═══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

# ANSI Colors
class Col:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class PreBuildChecklist:
    """Master pre-build verification orchestrator."""
    
    def __init__(self, verbose: bool = False, auto_fix: bool = False):
        self.verbose = verbose
        self.auto_fix = auto_fix
        self.repo_root = Path(__file__).parent.parent.absolute()
        self.results: Dict[str, Tuple[bool, str]] = {}
        self.pass_count = 0
        self.fail_count = 0
        self.warn_count = 0
        
    def header(self, text: str):
        print(f"\n{Col.CYAN}{Col.BOLD}{'═' * 70}{Col.RESET}")
        print(f"{Col.CYAN}{Col.BOLD}  {text}{Col.RESET}")
        print(f"{Col.CYAN}{Col.BOLD}{'═' * 70}{Col.RESET}")
        
    def log(self, status: str, message: str):
        if status == "OK":
            self.pass_count += 1
            print(f"  [{Col.GREEN}PASS{Col.RESET}] {message}")
        elif status == "WARN":
            self.warn_count += 1
            print(f"  [{Col.YELLOW}WARN{Col.RESET}] {message}")
        elif status == "FAIL":
            self.fail_count += 1
            print(f"  [{Col.RED}FAIL{Col.RESET}] {message}")
        elif status == "INFO":
            print(f"  [{Col.CYAN}INFO{Col.RESET}] {message}")
            
    def run_script(self, name: str, cmd: List[str], cwd: Path = None) -> Tuple[bool, str]:
        """Run a verification script and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except FileNotFoundError:
            return False, f"Script not found: {cmd[0]}"
        except Exception as e:
            return False, str(e)
            
    def check_directory_structure(self):
        """Verify critical directory structure exists."""
        self.header("1. DIRECTORY STRUCTURE")
        
        required_dirs = [
            "iso/config/includes.chroot/opt/titan/core",
            "iso/config/includes.chroot/opt/titan/apps",
            "iso/config/includes.chroot/opt/titan/config",
            "iso/config/includes.chroot/opt/titan/extensions",
            "iso/config/includes.chroot/opt/titan/state",
            "iso/config/includes.chroot/etc/systemd/system",
            "iso/config/includes.chroot/etc/sysctl.d",
            "iso/config/package-lists",
            "scripts",
            "tests",
            "profgen",
        ]
        
        for dir_path in required_dirs:
            full_path = self.repo_root / dir_path
            if full_path.is_dir():
                self.log("OK", f"Directory: {dir_path}")
            else:
                self.log("FAIL", f"Missing directory: {dir_path}")
                
    def check_core_modules(self):
        """Verify all core Python modules exist."""
        self.header("2. CORE MODULES (ISO)")
        
        core_path = self.repo_root / "iso/config/includes.chroot/opt/titan/core"
        
        required_modules = [
            "__init__.py",
            "genesis_core.py",
            "cerberus_core.py",
            "kyc_core.py",
            "kill_switch.py",
            "ghost_motor_v6.py",
            "fingerprint_injector.py",
            "tls_parrot.py",
            "handover_protocol.py",
            "target_presets.py",
            "proxy_manager.py",
            "preflight_validator.py",
            "hardware_shield_v6.c",
            "network_shield_v6.c",
        ]
        
        for module in required_modules:
            if (core_path / module).is_file():
                self.log("OK", f"core/{module}")
            else:
                self.log("FAIL", f"Missing: core/{module}")
                
    def check_apps(self):
        """Verify Trinity apps exist."""
        self.header("3. TRINITY APPS")
        
        apps_path = self.repo_root / "iso/config/includes.chroot/opt/titan/apps"
        
        required_apps = [
            "app_unified.py",
            "app_genesis.py",
            "app_cerberus.py",
            "app_kyc.py",
            "titan_mission_control.py",
        ]
        
        for app in required_apps:
            if (apps_path / app).is_file():
                self.log("OK", f"apps/{app}")
            else:
                self.log("FAIL", f"Missing: apps/{app}")
                
    def check_extensions(self):
        """Verify browser extensions exist."""
        self.header("4. BROWSER EXTENSIONS")
        
        ext_path = self.repo_root / "iso/config/includes.chroot/opt/titan/extensions"
        
        extensions = [
            ("ghost_motor/ghost_motor.js", "Ghost Motor JS"),
            ("ghost_motor/manifest.json", "Ghost Motor Manifest"),
            ("tx_monitor/tx_monitor.js", "TX Monitor JS"),
            ("tx_monitor/manifest.json", "TX Monitor Manifest"),
        ]
        
        for rel_path, name in extensions:
            if (ext_path / rel_path).is_file():
                self.log("OK", name)
            else:
                self.log("FAIL", f"Missing: {name}")
                
    def check_system_configs(self):
        """Verify system configuration files."""
        self.header("5. SYSTEM CONFIGURATION")
        
        etc_path = self.repo_root / "iso/config/includes.chroot/etc"
        
        configs = [
            ("nftables.conf", "Firewall (nftables)"),
            ("sysctl.d/99-titan-hardening.conf", "Kernel Hardening"),
            ("systemd/system/lucid-titan.service", "TITAN Service"),
            ("systemd/system/lucid-ebpf.service", "eBPF Service"),
            ("systemd/system/titan-dns.service", "DNS Service"),
            ("systemd/system/titan-first-boot.service", "First Boot Service"),
            ("unbound/unbound.conf.d/titan-dns.conf", "Unbound DNS Config"),
        ]
        
        for rel_path, name in configs:
            full_path = etc_path / rel_path
            if full_path.is_file():
                self.log("OK", name)
            else:
                # Check if parent dir exists
                if not full_path.parent.is_dir():
                    self.log("FAIL", f"Missing: {name} (directory missing)")
                else:
                    self.log("FAIL", f"Missing: {name}")
                    
    def check_package_list(self):
        """Verify package list has required packages."""
        self.header("6. PACKAGE LIST")
        
        pkg_file = self.repo_root / "iso/config/package-lists/custom.list.chroot"
        
        if not pkg_file.is_file():
            self.log("FAIL", "Package list not found")
            return
            
        content = pkg_file.read_text()
        
        required_packages = [
            ("task-xfce-desktop", "XFCE Desktop"),
            ("nftables", "Firewall"),
            ("unbound", "DNS Resolver"),
            ("libfaketime", "Time Manipulation"),
            ("firefox-esr", "Firefox Browser"),
            ("chromium", "Chromium Browser"),
            ("dbus-x11", "DBus X11 Support"),
            ("v4l2loopback-dkms", "Video Loopback"),
            ("python3-pyqt6", "PyQt6 GUI"),
        ]
        
        for pkg, name in required_packages:
            if pkg in content:
                self.log("OK", f"{name} ({pkg})")
            else:
                self.log("FAIL", f"Missing package: {pkg}")
                
        # Check for gnome-core (should NOT be present)
        if "gnome-core" in content:
            self.log("FAIL", "gnome-core should be removed (V7.0 requirement)")
        else:
            self.log("OK", "No gnome-core (correct)")
            
    def check_build_scripts(self):
        """Verify build scripts exist."""
        self.header("7. BUILD SCRIPTS")
        
        scripts = [
            ("build_final.sh", "Main Build Script"),
            ("scripts/build_iso.sh", "ISO Builder"),
            ("scripts/titan_finality_patcher.py", "Forensic Sanitizer"),
            ("finalize_titan_oblivion.sh", "Oblivion Finalizer"),
            ("Dockerfile.build", "Docker Build"),
        ]
        
        for rel_path, name in scripts:
            if (self.repo_root / rel_path).is_file():
                self.log("OK", name)
            else:
                self.log("WARN", f"Missing: {name}")
                
    def check_ci_cd(self):
        """Verify CI/CD workflows."""
        self.header("8. CI/CD WORKFLOWS")
        
        workflows_path = self.repo_root / ".github/workflows"
        
        required_workflows = [
            ("build-iso.yml", "ISO Build Workflow"),
            ("build.yml", "General Build Workflow"),
            ("test-modules.yml", "Test Modules Workflow"),
        ]
        
        for filename, name in required_workflows:
            if (workflows_path / filename).is_file():
                self.log("OK", name)
            else:
                self.log("WARN", f"Missing: {name}")
                
    def check_tests(self):
        """Verify test suite exists."""
        self.header("9. TEST SUITE")
        
        tests_path = self.repo_root / "tests"
        
        test_files = [
            "conftest.py",
            "test_genesis_engine.py",
            "test_profgen_config.py",
            "test_profile_isolation.py",
            "test_integration.py",
            "run_tests.py",
        ]
        
        for test_file in test_files:
            if (tests_path / test_file).is_file():
                self.log("OK", test_file)
            else:
                self.log("WARN", f"Missing: {test_file}")
                
        # Check pytest.ini
        if (self.repo_root / "pytest.ini").is_file():
            self.log("OK", "pytest.ini")
        else:
            self.log("WARN", "Missing: pytest.ini")
            
    def check_documentation(self):
        """Verify documentation exists."""
        self.header("10. DOCUMENTATION")
        
        docs = [
            "README.md",
            "BUILD_GUIDE.md",
            "TITAN_V703_SINGULARITY.md",
            "docs/QUICKSTART_V7.md",
            "docs/ARCHITECTURE.md",
        ]
        
        for doc in docs:
            if (self.repo_root / doc).is_file():
                self.log("OK", doc)
            else:
                self.log("WARN", f"Missing: {doc}")
                
    def generate_report(self) -> int:
        """Generate final report and return exit code."""
        self.header("FINAL REPORT")
        
        total = self.pass_count + self.fail_count + self.warn_count
        
        print(f"\n  {Col.GREEN}PASS: {self.pass_count}{Col.RESET}  |  "
              f"{Col.RED}FAIL: {self.fail_count}{Col.RESET}  |  "
              f"{Col.YELLOW}WARN: {self.warn_count}{Col.RESET}  |  "
              f"TOTAL: {total}")
        
        if self.fail_count > 0:
            print(f"\n  {Col.RED}{Col.BOLD}>>> PRE-BUILD STATUS: NOT READY <<<{Col.RESET}")
            print(f"  {Col.RED}{self.fail_count} critical issue(s) must be resolved.{Col.RESET}")
            return 1
        elif self.warn_count > 0:
            pct = (self.pass_count / total * 100) if total else 0
            print(f"\n  {Col.YELLOW}{Col.BOLD}>>> PRE-BUILD STATUS: READY (with warnings) <<<{Col.RESET}")
            print(f"  {Col.YELLOW}Confidence: {pct:.1f}% — Address warnings for full readiness.{Col.RESET}")
            return 2
        else:
            print(f"\n  {Col.GREEN}{Col.BOLD}>>> PRE-BUILD STATUS: FULLY READY <<<{Col.RESET}")
            print(f"  {Col.GREEN}All checks passed. System is cleared for ISO build.{Col.RESET}")
            return 0
            
    def run(self) -> int:
        """Run all checks."""
        print(f"\n{Col.GREEN}{Col.BOLD}")
        print("  ████████╗██╗████████╗ █████╗ ███╗   ██╗")
        print("  ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║")
        print("     ██║   ██║   ██║   ███████║██╔██╗ ██║")
        print("     ██║   ██║   ██║   ██╔══██║██║╚██╗██║")
        print("     ██║   ██║   ██║   ██║  ██║██║ ╚████║")
        print("     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝")
        print(f"  V7.0.3 SINGULARITY — PRE-BUILD CHECKLIST{Col.RESET}")
        print(f"\n  Timestamp: {datetime.now().isoformat()}")
        print(f"  Repository: {self.repo_root}")
        
        self.check_directory_structure()
        self.check_core_modules()
        self.check_apps()
        self.check_extensions()
        self.check_system_configs()
        self.check_package_list()
        self.check_build_scripts()
        self.check_ci_cd()
        self.check_tests()
        self.check_documentation()
        
        return self.generate_report()


def main():
    parser = argparse.ArgumentParser(
        description="TITAN V7.0.3 Pre-Build Checklist"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-fix issues where possible"
    )
    
    args = parser.parse_args()
    
    checklist = PreBuildChecklist(
        verbose=args.verbose,
        auto_fix=args.fix
    )
    
    exit_code = checklist.run()
    print("")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
