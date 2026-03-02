#!/usr/bin/env python3
"""
TITAN X — KYC AppX Integration Test Suite
==========================================
Verifies KYC Bridge API, camera endpoints, Android endpoints,
liveness endpoints, and provider workflows.

Usage:
    python3 test_kyc_appx_integration.py                    # Test against localhost:36400
    python3 test_kyc_appx_integration.py --host 72.62.72.48 # Test against remote VPS
    python3 test_kyc_appx_integration.py --verbose          # Show response bodies
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)


class KYCAppXTester:
    """Integration tester for KYC AppX Bridge API"""

    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def _req(self, method: str, path: str, json_data: dict = None, timeout: int = 10) -> Tuple[Optional[dict], int]:
        """Make HTTP request and return (json_response, status_code)"""
        url = f"{self.base_url}{path}"
        try:
            if method == "GET":
                r = requests.get(url, timeout=timeout)
            elif method == "POST":
                r = requests.post(url, json=json_data or {}, timeout=timeout)
            else:
                return None, -1

            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text[:500]}

            if self.verbose:
                print(f"    {method} {path} -> {r.status_code}: {json.dumps(body, indent=2)[:300]}")

            return body, r.status_code
        except requests.ConnectionError:
            return None, -2
        except requests.Timeout:
            return None, -3
        except Exception as e:
            return {"error": str(e)}, -4

    def _test(self, name: str, passed: bool, detail: str = ""):
        """Record test result"""
        status = "PASS" if passed else "FAIL"
        self.results.append({"name": name, "status": status, "detail": detail})
        if passed:
            self.passed += 1
            print(f"  \033[32m[PASS]\033[0m {name}")
        else:
            self.failed += 1
            print(f"  \033[31m[FAIL]\033[0m {name} — {detail}")

    def _skip(self, name: str, reason: str):
        """Record skipped test"""
        self.results.append({"name": name, "status": "SKIP", "detail": reason})
        self.skipped += 1
        print(f"  \033[33m[SKIP]\033[0m {name} — {reason}")

    # ═══════════════════════════════════════════════════════════════════════
    # TEST GROUPS
    # ═══════════════════════════════════════════════════════════════════════

    def test_health(self):
        """Test health endpoint"""
        body, code = self._req("GET", "/api/v1/health")
        self._test("Health check", code == 200 and body and body.get("ok") is True,
                    f"status={code}, body={body}")

    def test_status(self):
        """Test status endpoint"""
        body, code = self._req("GET", "/api/v1/status")
        self._test("Status endpoint", code == 200 and body and "modules" in body,
                    f"status={code}")

        if body and "modules" in body:
            modules = body["modules"]
            for mod_name, available in modules.items():
                status = "available" if available else "not loaded"
                if available:
                    self._test(f"Module: {mod_name}", True)
                else:
                    self._skip(f"Module: {mod_name}", f"{mod_name} not loaded on this system")

    def test_camera_endpoints(self):
        """Test camera-related endpoints"""
        # Camera status
        body, code = self._req("GET", "/api/v1/camera/status")
        self._test("Camera status", code == 200 and body is not None,
                    f"status={code}")

        # Start camera (may fail if v4l2loopback not loaded — that's OK)
        body, code = self._req("POST", "/api/v1/camera/start", {"device": "/dev/video2"})
        if code == 200:
            self._test("Camera start", True)
            # Stop camera
            body, code = self._req("POST", "/api/v1/camera/stop")
            self._test("Camera stop", code == 200)
        elif code == 503:
            self._skip("Camera start", "kyc_core not available")
        else:
            self._test("Camera start", False, f"status={code}, body={body}")

    def test_motion_endpoints(self):
        """Test motion/liveness endpoints"""
        # List motions
        body, code = self._req("GET", "/api/v1/motions")
        self._test("List motions", code == 200 and body and "motions" in body,
                    f"status={code}")

        if body and "motions" in body:
            self._test(f"Motion count: {len(body['motions'])}", len(body["motions"]) >= 5)

        # Start motion (may fail without camera)
        body, code = self._req("POST", "/api/v1/motion/start", {"motion": "blink", "intensity": 0.7})
        if code == 200:
            self._test("Start motion", True)
        elif code == 503:
            self._skip("Start motion", "kyc_core not available")
        else:
            self._test("Start motion", False, f"status={code}")

    def test_liveness_endpoints(self):
        """Test liveness spoofing"""
        body, code = self._req("POST", "/api/v1/liveness/spoof", {"challenge": "blink", "provider": "onfido"})
        if code == 200:
            self._test("Liveness spoof", True)
        elif code == 503:
            self._skip("Liveness spoof", "kyc_enhanced not available")
        else:
            self._test("Liveness spoof", False, f"status={code}")

    def test_provider_endpoints(self):
        """Test KYC provider endpoints"""
        # List providers
        body, code = self._req("GET", "/api/v1/providers")
        self._test("List providers", code == 200 and body and "providers" in body,
                    f"status={code}")

        if body and "providers" in body:
            providers = body["providers"]
            self._test(f"Provider count: {len(providers)}", len(providers) >= 4)

            # Test each provider strategy
            for provider_name in ["onfido", "jumio", "veriff", "sumsub"]:
                if provider_name in providers:
                    strat_body, strat_code = self._req("POST", "/api/v1/provider/strategy", {"provider": provider_name})
                    self._test(f"Strategy: {provider_name}",
                               strat_code == 200 and strat_body and "steps" in strat_body,
                               f"status={strat_code}")

    def test_android_endpoints(self):
        """Test Android/Waydroid endpoints"""
        # Android status
        body, code = self._req("GET", "/api/v1/android/status")
        self._test("Android status", code == 200 and body is not None,
                    f"status={code}")

        android_active = body.get("active", False) if body else False

        # List device presets
        body, code = self._req("GET", "/api/v1/devices")
        self._test("List device presets", code == 200 and body and "devices" in body,
                    f"status={code}")

        if body and "devices" in body:
            self._test(f"Device preset count: {len(body['devices'])}", len(body["devices"]) >= 3)

        # Device spoof (test endpoint even if Waydroid not running)
        body, code = self._req("POST", "/api/v1/android/spoof", {"device": "pixel_7"})
        if code == 200:
            self._test("Device spoof (Pixel 7)", True)
        else:
            self._skip("Device spoof", f"Waydroid may not be running (status={code})")

        # Android start (only if not already active — don't disrupt running sessions)
        if not android_active:
            body, code = self._req("POST", "/api/v1/android/start", {"device": "pixel_7", "headless": True})
            if code == 200:
                self._test("Android start (headless)", True)
                time.sleep(2)
                # Stop it again
                body, code = self._req("POST", "/api/v1/android/stop")
                self._test("Android stop", code == 200)
            else:
                self._skip("Android start", f"Waydroid not available (status={code})")
        else:
            self._skip("Android start/stop", "Android already running — not disrupting")

    def test_document_endpoints(self):
        """Test document injection endpoints"""
        # Inject face (will fail without real image — test error handling)
        body, code = self._req("POST", "/api/v1/inject/face", {"image_path": "/nonexistent.jpg"})
        if code == 503:
            self._skip("Inject face", "kyc_core not available")
        elif code == 400:
            self._test("Inject face (validation)", True, "Correctly rejects missing path")
        elif code == 500:
            self._test("Inject face (error handling)", True, "Correctly reports file error")
        else:
            self._test("Inject face", code == 200, f"status={code}")

        # Inject document
        body, code = self._req("POST", "/api/v1/inject/document", {"image_path": "/nonexistent.jpg", "document_type": "passport"})
        if code == 503:
            self._skip("Inject document", "kyc_enhanced not available")
        elif code in (400, 500):
            self._test("Inject document (error handling)", True)
        else:
            self._test("Inject document", code == 200, f"status={code}")

    def test_automation_endpoint(self):
        """Test the full automation workflow endpoint"""
        body, code = self._req("POST", "/api/v1/android/automate", {
            "provider": "onfido",
            "face_image": "/opt/titan/android/assets/test_face.jpg",
            "document_image": "/opt/titan/android/assets/test_doc.jpg",
        })
        if code == 200:
            self._test("Automation workflow (onfido)", True)
            if body and "workflow" in body:
                self._test(f"Workflow steps: {len(body['workflow'])}", len(body["workflow"]) >= 3)
        elif code == 400:
            self._skip("Automation workflow", "Android not running")
        else:
            self._test("Automation workflow", False, f"status={code}")

    # ═══════════════════════════════════════════════════════════════════════
    # RUN ALL
    # ═══════════════════════════════════════════════════════════════════════

    def run_all(self):
        """Run all test groups"""
        print(f"\n{'='*60}")
        print(f" KYC AppX Integration Tests")
        print(f" Target: {self.base_url}")
        print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # Connectivity check
        body, code = self._req("GET", "/api/v1/health", timeout=5)
        if code < 0:
            print(f"\033[31m[FATAL] Cannot connect to {self.base_url}\033[0m")
            print(f"  Ensure KYC Bridge API is running: bash launch_kyc_appx.sh --headless")
            return 1

        print("--- Health & Status ---")
        self.test_health()
        self.test_status()

        print("\n--- Camera ---")
        self.test_camera_endpoints()

        print("\n--- Motion & Liveness ---")
        self.test_motion_endpoints()
        self.test_liveness_endpoints()

        print("\n--- Providers ---")
        self.test_provider_endpoints()

        print("\n--- Android / Waydroid ---")
        self.test_android_endpoints()

        print("\n--- Document Injection ---")
        self.test_document_endpoints()

        print("\n--- Automation ---")
        self.test_automation_endpoint()

        # Summary
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f" Results: {total} tests")
        print(f"   \033[32mPASS: {self.passed}\033[0m")
        print(f"   \033[31mFAIL: {self.failed}\033[0m")
        print(f"   \033[33mSKIP: {self.skipped}\033[0m")
        print(f"{'='*60}\n")

        return 0 if self.failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="KYC AppX Integration Tests")
    parser.add_argument("--host", default="127.0.0.1", help="Bridge API host (default: 127.0.0.1)")
    parser.add_argument("--port", default=36400, type=int, help="Bridge API port (default: 36400)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show response bodies")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    tester = KYCAppXTester(base_url, verbose=args.verbose)
    exit_code = tester.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
