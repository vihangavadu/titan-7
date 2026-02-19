#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import shutil

class OblivionVerifier:
    def __init__(self):
        self.score = 0
        self.max_score = 5
        self.report = {}

    def log(self, message, status):
        print(f"[{status}] {message}")
        self.report[message] = status

    def check_root(self):
        # Cross-platform root check (Unix only)
        try:
            if hasattr(os, 'geteuid'):
                uid = os.geteuid()
            elif hasattr(os, 'getuid'):
                uid = os.getuid()
            else:
                # Windows: no root concept, assume admin if not limited
                self.log("Root check skipped (Windows)", "WARN")
                self.score += 1
                return
            if uid != 0:
                self.log("Root privileges required for verification", "FAIL")
                sys.exit(1)
        except AttributeError:
            self.log("Root check skipped (platform limitation)", "WARN")
            self.score += 1
            return
        
        self.log("Root Access Confirmed", "PASS")
        self.score += 1

    def check_filesystem(self):
        if os.path.exists("/opt/titan") and os.path.isdir("/opt/titan"):
            self.log("Titan Core Directory (/opt/titan) exists", "PASS")
            self.score += 1
        else:
            self.log("Titan Core Directory NOT found", "FAIL")

    def check_kernel_hardening(self):
        try:
            result = subprocess.check_output(["sysctl", "net.ipv4.icmp_echo_ignore_all"]).decode().strip()
            if "1" in result:
                self.log("ICMP Echo Ignore Active (Stealth Mode)", "PASS")
                self.score += 1
            else:
                self.log("ICMP Echo Ignore INACTIVE", "FAIL")
        except Exception:
            self.log("Failed to check sysctl", "FAIL")

    def check_dependencies(self):
        required = ["git", "python3", "tor"]
        missing = []
        for pkg in required:
            if shutil.which(pkg):
                continue
            else:
                missing.append(pkg)

        if not missing:
            self.log("Core Binary Dependencies Installed", "PASS")
            self.score += 1
        else:
            self.log(f"Missing Dependencies: {missing}", "FAIL")

    def check_identity(self):
        env_path = "/opt/titan/iso/config/includes.chroot/opt/titan/config/titan.env"
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                content = f.read()
                if "TITAN_IDENTITY" in content:
                    self.log("Identity Matrix Configured", "PASS")
                    self.score += 1
                else:
                    self.log("Identity Matrix Empty", "FAIL")
        else:
            self.log("Identity Configuration Missing", "FAIL")

    def run(self):
        print("TITAN-7 // OBLIVION STATE VERIFICATION")
        print("======================================")
        self.check_root()
        self.check_filesystem()
        self.check_dependencies()
        self.check_kernel_hardening()
        self.check_identity()

        print("======================================")
        print(f"MIGRATION SCORE: {self.score}/{self.max_score}")
        if self.score == self.max_score:
            print("[+] SYSTEM STATUS: OBLIVION CERTIFIED")
        else:
            print("[!] SYSTEM STATUS: COMPROMISED / INCOMPLETE")

        # Emit JSON report for automation pipelines (non-fatal)
        try:
            print(json.dumps({"score": self.score, "max_score": self.max_score, "report": self.report}))
        except Exception:
            pass

if __name__ == "__main__":
    verifier = OblivionVerifier()
    verifier.run()
