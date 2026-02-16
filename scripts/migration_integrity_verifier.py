#!/usr/bin/env python3
# TITAN-7 // MIGRATION INTEGRITY VERIFIER [C&C PROTOCOL]
# SCOPE: Debian 12 -> Titan OS Mutation Verification
# AUTHOR: TITAN ARCHITECT
# VERSION: 2.0 (Cross-platform compatible)

import os
import sys
import subprocess
import json
import socket
import platform
from pathlib import Path
from typing import List, Dict, Tuple

# --- CONFIGURATION MATRIX ---
TITAN_ROOT = Path(os.environ.get("TITAN_ROOT", "/opt/titan"))
TITAN_ENV_FILE = TITAN_ROOT / "config/titan.env"
REQUIRED_PACKAGES = {
    "Linux": ["git", "python3", "iptables", "jq"],
    "Darwin": ["git", "python3"],
}
HARDENING_SYSCTL = {
    "net.ipv4.icmp_echo_ignore_all": "1",
    "net.ipv4.conf.all.accept_redirects": "0",
    "net.ipv4.conf.all.send_redirects": "0",
    "net.ipv4.ip_forward": "0",
    "net.ipv6.conf.all.disable_ipv6": "1",
    "kernel.dmesg_restrict": "1",
    "kernel.unprivileged_userns_clone": "0",
    "kernel.kptr_restrict": "2",
    "kernel.yama.ptrace_scope": "2"
}

class ConsoleColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class MigrationVerifier:
    def __init__(self):
        self.os_type = platform.system()
        self.is_linux = self.os_type == "Linux"
        self.is_root = self._check_root()
        self.results = {
            "pass": 0,
            "fail": 0,
            "warn": 0,
            "tests": []
        }

    def _check_root(self) -> bool:
        """Cross-platform root check."""
        if self.is_linux:
            return os.geteuid() == 0
        elif self.os_type == "Windows":
            try:
                import ctypes
                return ctypes.windll.shell.IsUserAnAdmin()
            except:
                return False
        return False

    def log(self, message: str, status: str = "INFO") -> None:
        """Log message with color coding."""
        status_upper = status.upper()
        if status_upper == "PASS":
            prefix = f"{ConsoleColors.OKGREEN}[PASS]{ConsoleColors.ENDC}"
            self.results["pass"] += 1
        elif status_upper == "FAIL":
            prefix = f"{ConsoleColors.FAIL}[FAIL]{ConsoleColors.ENDC}"
            self.results["fail"] += 1
        elif status_upper == "WARN":
            prefix = f"{ConsoleColors.WARNING}[WARN]{ConsoleColors.ENDC}"
            self.results["warn"] += 1
        else:
            prefix = f"{ConsoleColors.OKBLUE}[*]{ConsoleColors.ENDC}"
        
        print(f"{prefix} {message}")
        self.results["tests"].append({"message": message, "status": status_upper})

    def verify_root(self) -> None:
        """Verify root/admin privileges (Linux/macOS only)."""
        if not self.is_linux and self.os_type != "Darwin":
            self.log("Root check skipped on non-Unix platform.", "WARN")
            return
        
        if self.is_root:
            self.log("Root access confirmed.", "PASS")
        else:
            self.log("Root privileges required for deep verification.", "FAIL")
            if self.is_linux:
                self.log("Re-run with: sudo python3 migration_integrity_verifier.py", "WARN")

    def verify_environment(self) -> None:
        """Verify OS environment."""
        self.log(f"Operating System: {self.os_type} ({platform.release()})", "PASS")
        if not self.is_linux:
            self.log("Non-Linux environment detected. Some checks will be skipped.", "WARN")

    def verify_titan_path(self) -> None:
        """Verify Titan installation paths."""
        if TITAN_ROOT.exists() and TITAN_ROOT.is_dir():
            self.log(f"Titan Core found at {TITAN_ROOT}", "PASS")
        else:
            self.log(f"Titan Core NOT found at {TITAN_ROOT}. Migration may have failed.", "FAIL")
            return

        # Check for critical Titan files
        critical_files = [
            "config/titan.env",
            "apps/app_unified.py",
            "core/titan_core.py",
        ]
        
        for file_path in critical_files:
            full_path = TITAN_ROOT / file_path
            if full_path.exists():
                self.log(f"Found: {file_path}", "PASS")
            else:
                self.log(f"Missing: {file_path} (Possible corruption)", "FAIL")

    def verify_dependencies(self) -> None:
        """Verify system dependencies."""
        if not self.is_linux:
            self.log("Dependency check requires Linux.", "WARN")
            return

        packages = REQUIRED_PACKAGES.get(self.os_type, [])
        if not packages:
            self.log("No packages defined for this OS.", "WARN")
            return

        missing = []
        for package in packages:
            try:
                result = subprocess.run(
                    ["which", package],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
                if result.returncode == 0:
                    self.log(f"✓ {package}", "PASS")
                else:
                    missing.append(package)
            except subprocess.TimeoutExpired:
                self.log(f"✗ {package} (timeout)", "FAIL")
                missing.append(package)
            except Exception as e:
                self.log(f"✗ {package} (error: {e})", "WARN")
                missing.append(package)

        if missing:
            self.log(f"Missing dependencies: {', '.join(missing)}", "FAIL")
            self.log("Install with: sudo apt-get install -y " + " ".join(missing), "WARN")
        else:
            self.log("All required packages are present.", "PASS")

    def verify_configuration(self) -> None:
        """Verify Titan configuration files."""
        if not TITAN_ENV_FILE.exists():
            self.log(f"Configuration file missing: {TITAN_ENV_FILE}", "FAIL")
            return

        try:
            with open(TITAN_ENV_FILE, 'r') as f:
                content = f.read()
                
            # Check for required configuration sections
            required_sections = [
                "TITAN_PROXY",
                "TITAN_PRODUCTION",
                "TITAN_LOG_LEVEL"
            ]
            
            found_sections = []
            missing_sections = []
            
            for section in required_sections:
                if section in content:
                    found_sections.append(section)
                    self.log(f"Configuration section found: {section}", "PASS")
                else:
                    missing_sections.append(section)
                    self.log(f"Configuration section missing: {section}", "WARN")
            
            # Check for dangerous placeholders
            dangerous_tokens = [
                "REPLACE_WITH_",
                "YOUR_API_KEY",
                "CHANGE_ME",
                "0.0.0.0"
            ]
            
            dangerous_found = [token for token in dangerous_tokens if token in content]
            if dangerous_found:
                self.log(f"Placeholders found (needs configuration): {dangerous_found}", "WARN")
            else:
                self.log("No dangerous placeholders detected.", "PASS")
                
        except Exception as e:
            self.log(f"Cannot read configuration: {e}", "FAIL")

    def verify_hardening(self) -> None:
        """Verify kernel hardening parameters."""
        if not self.is_linux:
            self.log("Kernel hardening check requires Linux.", "WARN")
            return

        if not self.is_root:
            self.log("Cannot verify hardening without root privileges.", "WARN")
            return

        self.log("Scanning Kernel Parameters...", "INFO")
        failures = 0
        
        for key, expected_value in HARDENING_SYSCTL.items():
            try:
                result = subprocess.run(
                    ["sysctl", "-n", key],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    current_value = result.stdout.strip()
                    if current_value == expected_value:
                        self.log(f"{key} = {current_value} (Hardened ✓)", "PASS")
                    else:
                        self.log(
                            f"{key} = {current_value} (Expected: {expected_value})",
                            "WARN"
                        )
                        failures += 1
                else:
                    self.log(f"Cannot read: {key}", "WARN")
            except subprocess.TimeoutExpired:
                self.log(f"Timeout reading: {key}", "WARN")
            except Exception as e:
                self.log(f"Error reading {key}: {e}", "WARN")

        if failures == 0:
            self.log("All kernel parameters properly hardened.", "PASS")
        else:
            self.log(
                f"{failures} kernel parameters need adjustment.",
                "FAIL"
            )

    def verify_network_stealth(self) -> None:
        """Verify network stealth and security."""
        if not self.is_linux:
            self.log("Network stealth check requires Linux.", "WARN")
            return

        if not self.is_root:
            self.log("Cannot verify network stealth without root privileges.", "WARN")
            return

        try:
            result = subprocess.run(
                ["ss", "-tuln"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Check for dangerous services
                dangerous_services = {
                    "rpcbind": "RPC binding service",
                    "telnet": "Telnet service",
                    "ftp": "FTP service",
                }
                
                found_dangerous = []
                for service, description in dangerous_services.items():
                    if service in output or f":{service}" in output:
                        found_dangerous.append(description)
                
                if found_dangerous:
                    self.log(
                        f"Dangerous services detected: {found_dangerous}",
                        "FAIL"
                    )
                else:
                    self.log("No dangerous services detected (Stealth ✓).", "PASS")
                
                # Check if SSH is properly secured
                if ":22 " in output or ":22\t" in output:
                    self.log("SSH service detected (ensure key-based auth only).", "PASS")
                    
            else:
                self.log("Cannot verify network services (ss command failed).", "WARN")
                
        except subprocess.TimeoutExpired:
            self.log("Network verification timeout.", "WARN")
        except FileNotFoundError:
            self.log("ss command not found. Install with: sudo apt-get install iproute2", "WARN")
        except Exception as e:
            self.log(f"Network verification error: {e}", "WARN")

    def verify_firewall(self) -> None:
        """Verify firewall configuration."""
        if not self.is_linux:
            self.log("Firewall check requires Linux.", "WARN")
            return

        if not self.is_root:
            self.log("Cannot verify firewall without root privileges.", "WARN")
            return

        try:
            # Check for nftables
            result = subprocess.run(
                ["nft", "list", "tables"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.log("nftables firewall is active.", "PASS")
            else:
                self.log("nftables firewall not configured (iptables fallback).", "WARN")
                
        except FileNotFoundError:
            self.log("nftables not installed. Check iptables instead.", "WARN")
        except subprocess.TimeoutExpired:
            self.log("Firewall verification timeout.", "WARN")
        except Exception as e:
            self.log(f"Firewall verification error: {e}", "WARN")

    def verify_modules(self) -> None:
        """Verify kernel modules (eBPF, hardware shield)."""
        if not self.is_linux:
            self.log("Module check requires Linux.", "WARN")
            return

        if not self.is_root:
            self.log("Cannot verify modules without root privileges.", "WARN")
            return

        modules_to_check = ["titan_hw", "ebpf_shields"]
        
        try:
            result = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                loaded_modules = result.stdout
                for module in modules_to_check:
                    if module in loaded_modules:
                        self.log(f"Kernel module loaded: {module}", "PASS")
                    else:
                        self.log(f"Kernel module NOT loaded: {module}", "WARN")
            else:
                self.log("Cannot read loaded modules.", "WARN")
                
        except subprocess.TimeoutExpired:
            self.log("Module verification timeout.", "WARN")
        except Exception as e:
            self.log(f"Module verification error: {e}", "WARN")

    def generate_report(self) -> None:
        """Generate summary report."""
        print("\n" + "=" * 70)
        print(f"{ConsoleColors.BOLD}MIGRATION VERIFICATION SUMMARY{ConsoleColors.ENDC}")
        print("=" * 70)
        print(f"Total Tests:  {len(self.results['tests'])}")
        print(f"{ConsoleColors.OKGREEN}Passed:       {self.results['pass']}{ConsoleColors.ENDC}")
        print(f"{ConsoleColors.WARNING}Warnings:     {self.results['warn']}{ConsoleColors.ENDC}")
        print(f"{ConsoleColors.FAIL}Failed:       {self.results['fail']}{ConsoleColors.ENDC}")
        print("=" * 70)
        
        if self.results['fail'] == 0:
            print(f"{ConsoleColors.OKGREEN}{ConsoleColors.BOLD}[✓] MIGRATION VERIFICATION PASSED{ConsoleColors.ENDC}")
        elif self.results['fail'] < 5:
            print(f"{ConsoleColors.WARNING}{ConsoleColors.BOLD}[!] MIGRATION VERIFICATION PASSED WITH WARNINGS{ConsoleColors.ENDC}")
            print("Review warnings and remediate as needed.")
        else:
            print(f"{ConsoleColors.FAIL}{ConsoleColors.BOLD}[✗] MIGRATION VERIFICATION FAILED{ConsoleColors.ENDC}")
            print("Critical issues detected. Review failures above.")
        
        print("\n" + f"{ConsoleColors.OKCYAN}[INFO] For issues, check:"+f"{ConsoleColors.ENDC}")
        print(f"  - Logs: {TITAN_ROOT}/logs/")
        print(f"  - Config: {TITAN_ENV_FILE}")
        print(f"  - Docs: {TITAN_ROOT}/../docs/TROUBLESHOOTING.md")

    def run_all_checks(self) -> int:
        """Execute all verification checks."""
        print(f"{ConsoleColors.BOLD}TITAN-7 // MIGRATION INTEGRITY VERIFIER (v2.0){ConsoleColors.ENDC}")
        print("=" * 70)
        
        self.verify_environment()
        self.verify_root()
        print()
        
        self.verify_titan_path()
        print()
        
        self.verify_dependencies()
        print()
        
        self.verify_configuration()
        print()
        
        if self.is_root and self.is_linux:
            self.verify_hardening()
            print()
            
            self.verify_network_stealth()
            print()
            
            self.verify_firewall()
            print()
            
            self.verify_modules()
            print()
        
        self.generate_report()
        
        # Return exit code
        return 0 if self.results['fail'] == 0 else 1


def main():
    try:
        verifier = MigrationVerifier()
        exit_code = verifier.run_all_checks()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{ConsoleColors.WARNING}[!] Verification interrupted by user.{ConsoleColors.ENDC}")
        sys.exit(130)
    except Exception as e:
        print(f"{ConsoleColors.FAIL}[FATAL] {e}{ConsoleColors.ENDC}")
        sys.exit(2)


if __name__ == "__main__":
    main()
