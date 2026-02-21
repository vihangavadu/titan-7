#!/usr/bin/env python3
"""
TITAN V7.0 Test Runner

Automated test execution framework for PSP and detection system testing.
Runs comprehensive test suites and generates detailed failure reports.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

from .psp_sandbox import (
    PSPSandbox, PSPResponse, TransactionRequest, CardData,
    BillingAddress, DeviceFingerprint, BehavioralData,
    StripeSandbox, AdyenSandbox, BraintreeSandbox, PayPalSandbox,
    create_psp_sandbox,
)
from .detection_emulator import (
    DetectionEmulator, DetectionResult, RiskSignal,
    FingerprintDetector, BehavioralDetector, NetworkDetector,
    DeviceDetector, VelocityDetector,
    create_detector,
)

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestCase:
    """Individual test case definition"""
    name: str
    description: str
    category: str
    test_data: Dict[str, Any]
    expected_result: str  # "pass" or "fail"
    tags: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "expected_result": self.expected_result,
            "tags": self.tags,
            "enabled": self.enabled,
        }


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_case: TestCase
    status: TestStatus
    actual_result: str
    execution_time_ms: float
    psp_response: Optional[PSPResponse] = None
    detection_results: List[DetectionResult] = field(default_factory=list)
    error_message: Optional[str] = None
    failure_reasons: List[str] = field(default_factory=list)
    risk_signals: List[RiskSignal] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_case.name,
            "status": self.status.value,
            "actual_result": self.actual_result,
            "expected_result": self.test_case.expected_result,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "failure_reasons": self.failure_reasons,
            "risk_signals": [s.to_dict() for s in self.risk_signals],
            "timestamp": self.timestamp,
        }
    
    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED


@dataclass
class TestSuite:
    """Collection of test cases"""
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_fn: Optional[Callable] = None
    teardown_fn: Optional[Callable] = None
    
    def add_test(self, test_case: TestCase):
        self.test_cases.append(test_case)
    
    def get_enabled_tests(self) -> List[TestCase]:
        return [tc for tc in self.test_cases if tc.enabled]


@dataclass
class TestRunSummary:
    """Summary of a complete test run"""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    success_rate: float
    total_time_ms: float
    results: List[TestResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "success_rate": self.success_rate,
            "total_time_ms": self.total_time_ms,
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp,
        }


class TestRunner:
    """
    Main test runner for TITAN V7.0 testing environment
    
    Executes test suites against PSP sandboxes and detection emulators,
    collecting results and generating detailed failure analysis.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize PSP sandboxes
        self.psp_sandboxes: Dict[str, PSPSandbox] = {}
        for psp in self.config.get("psps", ["stripe", "adyen", "braintree"]):
            self.psp_sandboxes[psp] = create_psp_sandbox(psp, self.config.get(f"{psp}_config"))
        
        # Initialize detection emulators
        self.detectors: Dict[str, DetectionEmulator] = {}
        for detector in self.config.get("detectors", ["fingerprint", "behavioral", "network", "device", "velocity"]):
            self.detectors[detector] = create_detector(detector, self.config.get(f"{detector}_config"))
        
        # Test results storage
        self.results: List[TestResult] = []
        self.current_suite: Optional[TestSuite] = None
    
    def run_suite(self, suite: TestSuite) -> TestRunSummary:
        """Run a complete test suite"""
        self.current_suite = suite
        self.results = []
        
        start_time = time.time()
        
        # Run setup if defined
        if suite.setup_fn:
            try:
                suite.setup_fn()
            except Exception as e:
                logger.error(f"Suite setup failed: {e}")
        
        # Run each test
        for test_case in suite.get_enabled_tests():
            result = self._run_test(test_case)
            self.results.append(result)
        
        # Run teardown if defined
        if suite.teardown_fn:
            try:
                suite.teardown_fn()
            except Exception as e:
                logger.error(f"Suite teardown failed: {e}")
        
        total_time = (time.time() - start_time) * 1000
        
        # Calculate summary
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        total = len(self.results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return TestRunSummary(
            suite_name=suite.name,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            success_rate=success_rate,
            total_time_ms=total_time,
            results=self.results,
        )
    
    def _run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        start_time = time.time()
        
        try:
            # Build transaction request from test data
            request = self._build_request(test_case.test_data)
            
            # Run detection emulators first
            detection_results = []
            all_signals = []
            detection_passed = True
            
            for name, detector in self.detectors.items():
                detector_data = self._extract_detector_data(test_case.test_data, name)
                result = detector.analyze(detector_data)
                detection_results.append(result)
                all_signals.extend(result.signals)
                
                if not result.passed:
                    detection_passed = False
            
            # Run PSP sandbox tests
            psp_responses = []
            psp_passed = True
            
            target_psp = test_case.test_data.get("target_psp", "stripe")
            if target_psp in self.psp_sandboxes:
                psp = self.psp_sandboxes[target_psp]
                response = psp.process_payment(request)
                psp_responses.append(response)
                
                if not response.success:
                    psp_passed = False
                    all_signals.extend([
                        RiskSignal(
                            name=f"psp_{response.decline_reason.value if response.decline_reason else 'unknown'}",
                            category="psp",
                            severity=self._map_psp_severity(response.risk_score),
                            score=response.risk_score,
                            description=response.decline_message or "Transaction declined",
                            evidence={"decline_code": response.decline_code},
                        )
                        for _ in [1] if response.decline_reason
                    ])
            
            # Determine overall result
            actual_passed = detection_passed and psp_passed
            actual_result = "pass" if actual_passed else "fail"
            
            # Check against expected
            expected_pass = test_case.expected_result == "pass"
            test_passed = (actual_passed == expected_pass)
            
            # Collect failure reasons
            failure_reasons = []
            if not test_passed:
                if expected_pass and not actual_passed:
                    # Expected to pass but failed
                    for dr in detection_results:
                        failure_reasons.extend(dr.get_failure_reasons())
                    for pr in psp_responses:
                        if not pr.success:
                            failure_reasons.append(pr.decline_message or f"PSP declined: {pr.decline_reason}")
                elif not expected_pass and actual_passed:
                    # Expected to fail but passed
                    failure_reasons.append("Test expected to fail but passed - detection may be too lenient")
            
            execution_time = (time.time() - start_time) * 1000
            
            return TestResult(
                test_case=test_case,
                status=TestStatus.PASSED if test_passed else TestStatus.FAILED,
                actual_result=actual_result,
                execution_time_ms=execution_time,
                psp_response=psp_responses[0] if psp_responses else None,
                detection_results=detection_results,
                failure_reasons=failure_reasons,
                risk_signals=all_signals,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.exception(f"Test error: {test_case.name}")
            
            return TestResult(
                test_case=test_case,
                status=TestStatus.ERROR,
                actual_result="error",
                execution_time_ms=execution_time,
                error_message=str(e),
                failure_reasons=[f"Test execution error: {str(e)}"],
            )
    
    def _build_request(self, test_data: Dict) -> TransactionRequest:
        """Build TransactionRequest from test data"""
        card_data = test_data.get("card", {})
        card = CardData(
            number=card_data.get("number", "4111111111111111"),
            exp_month=card_data.get("exp_month", "12"),
            exp_year=card_data.get("exp_year", "25"),
            cvv=card_data.get("cvv", "123"),
            holder_name=card_data.get("holder_name", "Test User"),
        )
        
        billing_data = test_data.get("billing", {})
        billing = BillingAddress(
            line1=billing_data.get("line1", "123 Test St"),
            city=billing_data.get("city", "New York"),
            state=billing_data.get("state", "NY"),
            postal_code=billing_data.get("postal_code", "10001"),
            country=billing_data.get("country", "US"),
        ) if billing_data else None
        
        fp_data = test_data.get("fingerprint", {})
        fingerprint = DeviceFingerprint(
            canvas_hash=fp_data.get("canvas_hash", ""),
            webgl_hash=fp_data.get("webgl_hash", ""),
            audio_hash=fp_data.get("audio_hash", ""),
            screen_resolution=fp_data.get("screen_resolution", "1920x1080"),
            timezone=fp_data.get("timezone", "America/New_York"),
            language=fp_data.get("language", "en-US"),
            platform=fp_data.get("platform", "Win32"),
            user_agent=fp_data.get("user_agent", ""),
            ip_address=fp_data.get("ip_address", ""),
            session_id=fp_data.get("session_id", str(uuid.uuid4())),
        ) if fp_data else None
        
        beh_data = test_data.get("behavioral", {})
        behavioral = BehavioralData(
            mouse_entropy=beh_data.get("mouse_entropy", 0.5),
            keystroke_timing=beh_data.get("keystroke_timing", []),
            time_on_page_seconds=beh_data.get("time_on_page_seconds", 60),
            form_fill_time_seconds=beh_data.get("form_fill_time_seconds", 30),
            navigation_path=beh_data.get("navigation_path", []),
            referrer=beh_data.get("referrer", ""),
        ) if beh_data else None
        
        return TransactionRequest(
            card=card,
            amount=test_data.get("amount", 99.99),
            currency=test_data.get("currency", "USD"),
            billing=billing,
            fingerprint=fingerprint,
            behavioral=behavioral,
        )
    
    def _extract_detector_data(self, test_data: Dict, detector_name: str) -> Dict:
        """Extract relevant data for a specific detector"""
        if detector_name == "fingerprint":
            fp = test_data.get("fingerprint", {})
            return {
                "canvas": {"hash": fp.get("canvas_hash", "")},
                "webgl": {
                    "vendor": fp.get("webgl_vendor", ""),
                    "renderer": fp.get("webgl_renderer", ""),
                },
                "audio": {"hash": fp.get("audio_hash", "")},
                "screen": {
                    "width": int(fp.get("screen_resolution", "1920x1080").split("x")[0]),
                    "height": int(fp.get("screen_resolution", "1920x1080").split("x")[1]),
                },
                "user_agent": fp.get("user_agent", ""),
                "automation_properties": test_data.get("automation", {}),
            }
        
        elif detector_name == "behavioral":
            beh = test_data.get("behavioral", {})
            return {
                "mouse": {
                    "entropy": beh.get("mouse_entropy", 0),
                    "movements": beh.get("mouse_movements", []),
                },
                "keyboard": {
                    "timings": beh.get("keystroke_timing", []),
                },
                "navigation": {
                    "referrer": beh.get("referrer", ""),
                    "path": beh.get("navigation_path", []),
                },
                "timing": {
                    "page_time_seconds": beh.get("time_on_page_seconds", 0),
                    "form_fill_seconds": beh.get("form_fill_time_seconds", 0),
                },
            }
        
        elif detector_name == "network":
            fp = test_data.get("fingerprint", {})
            billing = test_data.get("billing", {})
            return {
                "ip": {
                    "address": fp.get("ip_address", ""),
                    "type": test_data.get("ip_type", "residential"),
                    "reputation": test_data.get("ip_reputation", 80),
                },
                "tls": {
                    "ja3": test_data.get("ja3_hash", ""),
                    "ja4": test_data.get("ja4_hash", ""),
                },
                "tcp": {
                    "ttl": test_data.get("tcp_ttl", 64),
                    "os": test_data.get("tcp_os", ""),
                    "user_agent_os": self._extract_os_from_ua(fp.get("user_agent", "")),
                },
                "geo": {
                    "ip_country": test_data.get("ip_country", "US"),
                    "ip_city": test_data.get("ip_city", ""),
                    "timezone": fp.get("timezone", ""),
                    "billing_country": billing.get("country", "US"),
                    "billing_city": billing.get("city", ""),
                },
            }
        
        elif detector_name == "device":
            fp = test_data.get("fingerprint", {})
            return {
                "platform": fp.get("platform", ""),
                "user_agent": fp.get("user_agent", ""),
                "hardware_concurrency": test_data.get("hardware_concurrency", 8),
            }
        
        elif detector_name == "velocity":
            card = test_data.get("card", {})
            fp = test_data.get("fingerprint", {})
            return {
                "card_bin": card.get("number", "")[:6],
                "ip_address": fp.get("ip_address", ""),
                "amount": test_data.get("amount", 0),
            }
        
        return test_data
    
    def _extract_os_from_ua(self, user_agent: str) -> str:
        """Extract OS from user agent string"""
        if "Windows" in user_agent:
            return "Windows"
        elif "Mac" in user_agent:
            return "macOS"
        elif "Linux" in user_agent:
            return "Linux"
        elif "Android" in user_agent:
            return "Android"
        elif "iOS" in user_agent or "iPhone" in user_agent:
            return "iOS"
        return ""
    
    def _map_psp_severity(self, risk_score: float):
        """Map PSP risk score to severity level"""
        from .detection_emulator import RiskLevel
        if risk_score < 30:
            return RiskLevel.LOW
        elif risk_score < 60:
            return RiskLevel.MEDIUM
        elif risk_score < 85:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL


def create_default_test_suite() -> TestSuite:
    """Create a default comprehensive test suite"""
    suite = TestSuite(
        name="TITAN V7.0 Comprehensive Test Suite",
        description="Full test coverage for PSP and detection systems",
    )
    
    # Good profile tests (should pass)
    suite.add_test(TestCase(
        name="valid_profile_stripe",
        description="Valid profile with all fingerprints should pass Stripe",
        category="psp",
        expected_result="pass",
        tags=["stripe", "positive"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "billing": {"city": "New York", "state": "NY", "postal_code": "10001", "country": "US"},
            "fingerprint": {
                "canvas_hash": "abc123def456789",
                "webgl_vendor": "Google Inc. (NVIDIA)",
                "webgl_renderer": "ANGLE (NVIDIA, GeForce RTX 3060)",
                "audio_hash": "xyz789audio",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": "203.0.113.50",
                "timezone": "America/New_York",
                "platform": "Win32",
            },
            "behavioral": {
                "mouse_entropy": 0.75,
                "time_on_page_seconds": 120,
                "form_fill_time_seconds": 45,
                "referrer": "https://www.google.com/search?q=amazon",
                "navigation_path": ["google.com", "amazon.com", "product", "cart", "checkout"],
            },
            "ip_type": "residential",
            "ip_reputation": 85,
            "ip_country": "US",
        },
    ))
    
    suite.add_test(TestCase(
        name="valid_profile_adyen",
        description="Valid profile should pass Adyen",
        category="psp",
        expected_result="pass",
        tags=["adyen", "positive"],
        test_data={
            "target_psp": "adyen",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 149.99,
            "billing": {"city": "Los Angeles", "state": "CA", "postal_code": "90001", "country": "US"},
            "fingerprint": {
                "canvas_hash": "def456ghi789",
                "webgl_vendor": "Google Inc. (AMD)",
                "webgl_renderer": "ANGLE (AMD, Radeon RX 6700)",
                "audio_hash": "audio123hash",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": "198.51.100.25",
                "timezone": "America/Los_Angeles",
                "platform": "Win32",
                "session_id": "adyen_session_123",
            },
            "behavioral": {
                "mouse_entropy": 0.68,
                "time_on_page_seconds": 90,
                "form_fill_time_seconds": 35,
                "referrer": "https://www.google.com/",
            },
            "ip_type": "residential",
            "ip_reputation": 90,
            "ip_country": "US",
        },
    ))
    
    # Bad profile tests (should fail)
    suite.add_test(TestCase(
        name="missing_fingerprint",
        description="Missing canvas fingerprint should fail",
        category="detection",
        expected_result="fail",
        tags=["fingerprint", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "fingerprint": {
                "canvas_hash": "",  # Missing
                "webgl_vendor": "",
                "webgl_renderer": "",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "203.0.113.50",
            },
            "behavioral": {
                "mouse_entropy": 0.5,
                "time_on_page_seconds": 60,
                "form_fill_time_seconds": 30,
            },
        },
    ))
    
    suite.add_test(TestCase(
        name="headless_browser_detected",
        description="Headless browser should be detected and fail",
        category="detection",
        expected_result="fail",
        tags=["fingerprint", "automation", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "fingerprint": {
                "canvas_hash": "abc123",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessChrome/91.0",
                "ip_address": "203.0.113.50",
            },
            "automation": {"webdriver": True},
        },
    ))
    
    suite.add_test(TestCase(
        name="bot_mouse_movement",
        description="Low mouse entropy should fail behavioral detection",
        category="behavioral",
        expected_result="fail",
        tags=["behavioral", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "fingerprint": {
                "canvas_hash": "abc123",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "203.0.113.50",
            },
            "behavioral": {
                "mouse_entropy": 0.1,  # Too low
                "time_on_page_seconds": 5,  # Too fast
                "form_fill_time_seconds": 2,  # Too fast
                "referrer": "",  # No referrer
            },
        },
    ))
    
    suite.add_test(TestCase(
        name="datacenter_ip",
        description="Datacenter IP should fail network detection",
        category="network",
        expected_result="fail",
        tags=["network", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "fingerprint": {
                "canvas_hash": "abc123",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "10.0.0.1",  # Private IP
            },
            "ip_type": "datacenter",
            "ip_reputation": 20,
        },
    ))
    
    suite.add_test(TestCase(
        name="country_mismatch",
        description="IP country not matching billing should fail",
        category="network",
        expected_result="fail",
        tags=["network", "geo", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "billing": {"city": "New York", "state": "NY", "country": "US"},
            "fingerprint": {
                "canvas_hash": "abc123",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "203.0.113.50",
                "timezone": "Europe/London",
            },
            "ip_country": "GB",  # Mismatch with US billing
            "ip_type": "residential",
        },
    ))
    
    suite.add_test(TestCase(
        name="declined_card",
        description="Known declined card should fail",
        category="psp",
        expected_result="fail",
        tags=["psp", "card", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4000000000000002", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "fingerprint": {
                "canvas_hash": "abc123",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "203.0.113.50",
            },
            "behavioral": {
                "mouse_entropy": 0.7,
                "time_on_page_seconds": 60,
                "form_fill_time_seconds": 30,
            },
        },
    ))
    
    suite.add_test(TestCase(
        name="3ds_required",
        description="3DS required card should trigger authentication",
        category="psp",
        expected_result="fail",
        tags=["psp", "3ds", "negative"],
        test_data={
            "target_psp": "stripe",
            "card": {"number": "4000000000003220", "exp_month": "12", "exp_year": "25", "cvv": "123"},
            "amount": 99.99,
            "fingerprint": {
                "canvas_hash": "abc123",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "203.0.113.50",
            },
        },
    ))
    
    return suite


def run_full_test(config: Optional[Dict] = None) -> TestRunSummary:
    """Run the full default test suite"""
    runner = TestRunner(config)
    suite = create_default_test_suite()
    return runner.run_suite(suite)


if __name__ == "__main__":
    # Run tests
    summary = run_full_test()
    
    print(f"\n{'='*60}")
    print(f"Test Suite: {summary.suite_name}")
    print(f"{'='*60}")
    print(f"Total Tests: {summary.total_tests}")
    print(f"Passed: {summary.passed}")
    print(f"Failed: {summary.failed}")
    print(f"Errors: {summary.errors}")
    print(f"Success Rate: {summary.success_rate:.1f}%")
    print(f"Total Time: {summary.total_time_ms:.0f}ms")
    print(f"{'='*60}")
    
    # Show failures
    failures = [r for r in summary.results if r.status == TestStatus.FAILED]
    if failures:
        print(f"\nFailed Tests ({len(failures)}):")
        for result in failures:
            print(f"\n  - {result.test_case.name}")
            print(f"    Expected: {result.test_case.expected_result}, Got: {result.actual_result}")
            for reason in result.failure_reasons[:3]:
                print(f"    Reason: {reason}")
