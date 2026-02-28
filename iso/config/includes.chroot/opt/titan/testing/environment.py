#!/usr/bin/env python3
"""
TITAN V8.1 Test Environment

Complete virtualized testing environment that integrates:
- PSP sandboxes (Stripe, Adyen, Braintree, PayPal, Square)
- Detection emulators (Fingerprint, Behavioral, Network, Device, Velocity)
- Test runner with automated execution
- Report generator with failure analysis

Provides a unified interface for testing TITAN profiles and configurations
against realistic fraud detection systems.
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .psp_sandbox import (
    PSPSandbox, PSPResponse, TransactionRequest, CardData,
    BillingAddress, DeviceFingerprint, BehavioralData,
    create_psp_sandbox,
)
from .detection_emulator import (
    DetectionEmulator, DetectionResult,
    create_detector,
)
from .test_runner import (
    TestRunner, TestCase, TestResult, TestSuite, TestRunSummary,
    create_default_test_suite,
)
from .report_generator import (
    ReportGenerator, TestReport, generate_report,
)

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Configuration for the test environment"""
    # PSP configuration
    enabled_psps: List[str] = field(default_factory=lambda: ["stripe", "adyen", "braintree"])
    psp_risk_threshold: int = 75
    
    # Detection configuration
    enabled_detectors: List[str] = field(default_factory=lambda: [
        "fingerprint", "behavioral", "network", "device", "velocity"
    ])
    detection_threshold: int = 70
    
    # Test configuration
    parallel_tests: bool = False
    test_timeout_seconds: float = 30.0
    
    # Report configuration
    output_dir: Path = field(default_factory=lambda: Path("/opt/titan/testing/reports"))
    report_formats: List[str] = field(default_factory=lambda: ["json", "md", "html"])
    
    # Logging
    log_level: str = "INFO"
    verbose: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled_psps": self.enabled_psps,
            "psp_risk_threshold": self.psp_risk_threshold,
            "enabled_detectors": self.enabled_detectors,
            "detection_threshold": self.detection_threshold,
            "parallel_tests": self.parallel_tests,
            "test_timeout_seconds": self.test_timeout_seconds,
            "output_dir": str(self.output_dir),
            "report_formats": self.report_formats,
            "log_level": self.log_level,
            "verbose": self.verbose,
        }


class TestEnvironment:
    """
    Complete virtualized testing environment for TITAN V7.0
    
    Usage:
        env = TestEnvironment()
        env.initialize()
        
        # Run default test suite
        report = env.run_tests()
        
        # Or test a specific profile
        result = env.test_profile(profile_data)
        
        # Generate report
        env.generate_report(report)
    """
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        self.config = config or EnvironmentConfig()
        self.initialized = False
        
        # Components
        self.psp_sandboxes: Dict[str, PSPSandbox] = {}
        self.detectors: Dict[str, DetectionEmulator] = {}
        self.test_runner: Optional[TestRunner] = None
        self.report_generator: Optional[ReportGenerator] = None
        
        # State
        self.test_history: List[TestRunSummary] = []
        self.profile_cache: Dict[str, Dict] = {}
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def initialize(self) -> bool:
        """Initialize all environment components"""
        try:
            logger.info("Initializing TITAN V8.1 Test Environment...")
            
            # Initialize PSP sandboxes
            for psp_name in self.config.enabled_psps:
                psp_config = {"risk_threshold": self.config.psp_risk_threshold}
                self.psp_sandboxes[psp_name] = create_psp_sandbox(psp_name, psp_config)
                logger.debug(f"Initialized PSP sandbox: {psp_name}")
            
            # Initialize detection emulators
            for detector_name in self.config.enabled_detectors:
                detector_config = {"threshold": self.config.detection_threshold}
                self.detectors[detector_name] = create_detector(detector_name, detector_config)
                logger.debug(f"Initialized detector: {detector_name}")
            
            # Initialize test runner
            runner_config = {
                "psps": self.config.enabled_psps,
                "detectors": self.config.enabled_detectors,
            }
            self.test_runner = TestRunner(runner_config)
            
            # Initialize report generator
            self.report_generator = ReportGenerator()
            
            # Create output directory
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.initialized = True
            logger.info(f"Test environment initialized with {len(self.psp_sandboxes)} PSPs and {len(self.detectors)} detectors")
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to initialize test environment: {e}")
            return False
    
    def run_tests(self, suite: Optional[TestSuite] = None) -> TestReport:
        """Run a test suite and generate report"""
        if not self.initialized:
            self.initialize()
        
        # Use default suite if none provided
        if suite is None:
            suite = create_default_test_suite()
        
        logger.info(f"Running test suite: {suite.name} ({len(suite.get_enabled_tests())} tests)")
        
        # Run tests
        summary = self.test_runner.run_suite(suite)
        self.test_history.append(summary)
        
        # Generate report
        report = self.report_generator.generate_report(summary)
        
        # Save report
        saved_files = report.save(self.config.output_dir, self.config.report_formats)
        logger.info(f"Report saved to: {[str(f) for f in saved_files]}")
        
        return report
    
    def test_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a specific TITAN profile against all detection systems
        
        Args:
            profile_data: Dictionary containing profile configuration
                - fingerprint: Canvas, WebGL, Audio hashes
                - behavioral: Mouse entropy, timing data
                - network: IP, proxy configuration
                - card: Card data for PSP testing
        
        Returns:
            Dictionary with test results and recommendations
        """
        if not self.initialized:
            self.initialize()
        
        results = {
            "profile_id": profile_data.get("profile_id", str(uuid.uuid4())),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_passed": True,
            "overall_risk_score": 0.0,
            "detection_results": {},
            "psp_results": {},
            "failure_reasons": [],
            "recommendations": [],
        }
        
        total_score = 0.0
        
        # Run each detector
        for name, detector in self.detectors.items():
            detector_data = self._extract_detector_data(profile_data, name)
            detection_result = detector.analyze(detector_data)
            
            results["detection_results"][name] = {
                "passed": detection_result.passed,
                "risk_score": detection_result.risk_score,
                "risk_level": detection_result.risk_level.value,
                "signals": [s.to_dict() for s in detection_result.signals],
            }
            
            if not detection_result.passed:
                results["overall_passed"] = False
                results["failure_reasons"].extend(detection_result.get_failure_reasons())
            
            total_score += detection_result.risk_score
        
        # Calculate average risk score
        if self.detectors:
            results["overall_risk_score"] = total_score / len(self.detectors)
        
        # Test against PSPs if card data provided
        if "card" in profile_data:
            request = self._build_transaction_request(profile_data)
            
            for name, psp in self.psp_sandboxes.items():
                psp_response = psp.process_payment(request)
                
                results["psp_results"][name] = {
                    "success": psp_response.success,
                    "transaction_id": psp_response.transaction_id,
                    "decline_reason": psp_response.decline_reason.value if psp_response.decline_reason else None,
                    "risk_score": psp_response.risk_score,
                    "requires_3ds": psp_response.requires_3ds,
                }
                
                if not psp_response.success:
                    results["overall_passed"] = False
                    if psp_response.decline_message:
                        results["failure_reasons"].append(f"{name}: {psp_response.decline_message}")
        
        # Generate recommendations
        results["recommendations"] = self._generate_profile_recommendations(results)
        
        return results
    
    def test_card(self, card_data: Dict[str, str], psp: str = "stripe") -> Dict[str, Any]:
        """
        Quick test of a card against a specific PSP
        
        Args:
            card_data: {"number": "...", "exp_month": "...", "exp_year": "...", "cvv": "..."}
            psp: PSP to test against
        
        Returns:
            PSP response as dictionary
        """
        if not self.initialized:
            self.initialize()
        
        if psp not in self.psp_sandboxes:
            return {"error": f"PSP '{psp}' not available. Available: {list(self.psp_sandboxes.keys())}"}
        
        card = CardData(
            number=card_data.get("number", ""),
            exp_month=card_data.get("exp_month", "12"),
            exp_year=card_data.get("exp_year", "25"),
            cvv=card_data.get("cvv", "123"),
        )
        
        request = TransactionRequest(
            card=card,
            amount=card_data.get("amount", 1.00),
        )
        
        response = self.psp_sandboxes[psp].process_payment(request)
        
        return response.to_dict()
    
    def test_fingerprint(self, fingerprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Quick test of fingerprint configuration
        
        Args:
            fingerprint_data: Canvas, WebGL, Audio, screen data
        
        Returns:
            Detection result as dictionary
        """
        if not self.initialized:
            self.initialize()
        
        if "fingerprint" not in self.detectors:
            return {"error": "Fingerprint detector not available"}
        
        result = self.detectors["fingerprint"].analyze({
            "canvas": {"hash": fingerprint_data.get("canvas_hash", "")},
            "webgl": {
                "vendor": fingerprint_data.get("webgl_vendor", ""),
                "renderer": fingerprint_data.get("webgl_renderer", ""),
            },
            "audio": {"hash": fingerprint_data.get("audio_hash", "")},
            "screen": {
                "width": fingerprint_data.get("screen_width", 1920),
                "height": fingerprint_data.get("screen_height", 1080),
            },
            "user_agent": fingerprint_data.get("user_agent", ""),
        })
        
        return result.to_dict()
    
    def test_behavioral(self, behavioral_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Quick test of behavioral data
        
        Args:
            behavioral_data: Mouse entropy, timing, navigation data
        
        Returns:
            Detection result as dictionary
        """
        if not self.initialized:
            self.initialize()
        
        if "behavioral" not in self.detectors:
            return {"error": "Behavioral detector not available"}
        
        result = self.detectors["behavioral"].analyze({
            "mouse": {
                "entropy": behavioral_data.get("mouse_entropy", 0),
                "movements": behavioral_data.get("mouse_movements", []),
            },
            "keyboard": {
                "timings": behavioral_data.get("keystroke_timing", []),
            },
            "navigation": {
                "referrer": behavioral_data.get("referrer", ""),
                "path": behavioral_data.get("navigation_path", []),
            },
            "timing": {
                "page_time_seconds": behavioral_data.get("time_on_page_seconds", 0),
                "form_fill_seconds": behavioral_data.get("form_fill_time_seconds", 0),
            },
        })
        
        return result.to_dict()
    
    def test_network(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Quick test of network configuration
        
        Args:
            network_data: IP, proxy, geo data
        
        Returns:
            Detection result as dictionary
        """
        if not self.initialized:
            self.initialize()
        
        if "network" not in self.detectors:
            return {"error": "Network detector not available"}
        
        result = self.detectors["network"].analyze({
            "ip": {
                "address": network_data.get("ip_address", ""),
                "type": network_data.get("ip_type", "residential"),
                "reputation": network_data.get("ip_reputation", 80),
            },
            "geo": {
                "ip_country": network_data.get("ip_country", "US"),
                "billing_country": network_data.get("billing_country", "US"),
                "timezone": network_data.get("timezone", "America/New_York"),
            },
        })
        
        return result.to_dict()
    
    def get_test_history(self) -> List[Dict[str, Any]]:
        """Get history of all test runs"""
        return [summary.to_dict() for summary in self.test_history]
    
    def get_success_rate_trend(self) -> List[Dict[str, Any]]:
        """Get success rate trend over test runs"""
        return [
            {
                "run": i + 1,
                "timestamp": summary.timestamp,
                "success_rate": summary.success_rate,
                "total_tests": summary.total_tests,
            }
            for i, summary in enumerate(self.test_history)
        ]
    
    def export_config(self, path: Path) -> None:
        """Export current configuration to file"""
        with open(path, "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)
    
    def import_config(self, path: Path) -> None:
        """Import configuration from file"""
        with open(path, "r") as f:
            config_dict = json.load(f)
        
        self.config = EnvironmentConfig(
            enabled_psps=config_dict.get("enabled_psps", ["stripe"]),
            psp_risk_threshold=config_dict.get("psp_risk_threshold", 75),
            enabled_detectors=config_dict.get("enabled_detectors", ["fingerprint"]),
            detection_threshold=config_dict.get("detection_threshold", 70),
            output_dir=Path(config_dict.get("output_dir", "/opt/titan/testing/reports")),
            report_formats=config_dict.get("report_formats", ["json", "md"]),
        )
        
        # Reinitialize with new config
        self.initialized = False
        self.initialize()
    
    def _extract_detector_data(self, profile_data: Dict, detector_name: str) -> Dict:
        """Extract relevant data for a specific detector"""
        if detector_name == "fingerprint":
            fp = profile_data.get("fingerprint", {})
            return {
                "canvas": {"hash": fp.get("canvas_hash", "")},
                "webgl": {
                    "vendor": fp.get("webgl_vendor", ""),
                    "renderer": fp.get("webgl_renderer", ""),
                },
                "audio": {"hash": fp.get("audio_hash", "")},
                "screen": {
                    "width": fp.get("screen_width", 1920),
                    "height": fp.get("screen_height", 1080),
                },
                "user_agent": fp.get("user_agent", ""),
                "automation_properties": profile_data.get("automation", {}),
            }
        
        elif detector_name == "behavioral":
            beh = profile_data.get("behavioral", {})
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
            net = profile_data.get("network", {})
            billing = profile_data.get("billing", {})
            return {
                "ip": {
                    "address": net.get("ip_address", ""),
                    "type": net.get("ip_type", "residential"),
                    "reputation": net.get("ip_reputation", 80),
                },
                "geo": {
                    "ip_country": net.get("ip_country", "US"),
                    "billing_country": billing.get("country", "US"),
                    "timezone": profile_data.get("fingerprint", {}).get("timezone", ""),
                },
            }
        
        elif detector_name == "device":
            fp = profile_data.get("fingerprint", {})
            return {
                "platform": fp.get("platform", ""),
                "user_agent": fp.get("user_agent", ""),
                "hardware_concurrency": profile_data.get("hardware_concurrency", 8),
            }
        
        elif detector_name == "velocity":
            card = profile_data.get("card", {})
            net = profile_data.get("network", {})
            return {
                "card_bin": card.get("number", "")[:6] if card.get("number") else "",
                "ip_address": net.get("ip_address", ""),
                "amount": profile_data.get("amount", 0),
            }
        
        return profile_data
    
    def _build_transaction_request(self, profile_data: Dict) -> TransactionRequest:
        """Build TransactionRequest from profile data"""
        card_data = profile_data.get("card", {})
        card = CardData(
            number=card_data.get("number", "4111111111111111"),
            exp_month=card_data.get("exp_month", "12"),
            exp_year=card_data.get("exp_year", "25"),
            cvv=card_data.get("cvv", "123"),
        )
        
        billing_data = profile_data.get("billing", {})
        billing = BillingAddress(
            city=billing_data.get("city", ""),
            state=billing_data.get("state", ""),
            postal_code=billing_data.get("postal_code", ""),
            country=billing_data.get("country", "US"),
        ) if billing_data else None
        
        fp_data = profile_data.get("fingerprint", {})
        fingerprint = DeviceFingerprint(
            canvas_hash=fp_data.get("canvas_hash", ""),
            webgl_hash=fp_data.get("webgl_hash", ""),
            ip_address=profile_data.get("network", {}).get("ip_address", ""),
            user_agent=fp_data.get("user_agent", ""),
        ) if fp_data else None
        
        beh_data = profile_data.get("behavioral", {})
        behavioral = BehavioralData(
            mouse_entropy=beh_data.get("mouse_entropy", 0.5),
            time_on_page_seconds=beh_data.get("time_on_page_seconds", 60),
            form_fill_time_seconds=beh_data.get("form_fill_time_seconds", 30),
            referrer=beh_data.get("referrer", ""),
        ) if beh_data else None
        
        return TransactionRequest(
            card=card,
            amount=profile_data.get("amount", 99.99),
            billing=billing,
            fingerprint=fingerprint,
            behavioral=behavioral,
        )
    
    def _generate_profile_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on profile test results"""
        recommendations = []
        
        # Check detection results
        for detector_name, detection in results.get("detection_results", {}).items():
            if not detection.get("passed", True):
                for signal in detection.get("signals", []):
                    if signal.get("remediation"):
                        recommendations.append(signal["remediation"])
        
        # Check PSP results
        for psp_name, psp_result in results.get("psp_results", {}).items():
            if not psp_result.get("success", True):
                if psp_result.get("requires_3ds"):
                    recommendations.append("Card requires 3DS - have SMS/app access ready")
                elif psp_result.get("decline_reason"):
                    recommendations.append(f"Address {psp_name} decline: {psp_result['decline_reason']}")
        
        # Deduplicate
        seen = set()
        unique = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique.append(rec)
        
        return unique[:10]


def create_test_environment(config: Optional[Dict] = None) -> TestEnvironment:
    """Create and initialize a test environment"""
    env_config = None
    if config:
        env_config = EnvironmentConfig(
            enabled_psps=config.get("psps", ["stripe", "adyen", "braintree"]),
            enabled_detectors=config.get("detectors", ["fingerprint", "behavioral", "network"]),
            psp_risk_threshold=config.get("psp_threshold", 75),
            detection_threshold=config.get("detection_threshold", 70),
            output_dir=Path(config.get("output_dir", "/opt/titan/testing/reports")),
        )
    
    env = TestEnvironment(env_config)
    env.initialize()
    return env


# CLI interface
def main():
    """Command-line interface for the test environment"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN V8.1 Test Environment")
    parser.add_argument("--run-tests", action="store_true", help="Run default test suite")
    parser.add_argument("--test-profile", type=str, help="Test a profile from JSON file")
    parser.add_argument("--test-card", type=str, help="Test a card (format: number|exp_month|exp_year|cvv)")
    parser.add_argument("--psp", type=str, default="stripe", help="PSP to test against")
    parser.add_argument("--output", type=str, default="/opt/titan/testing/reports", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Create environment
    config = EnvironmentConfig(
        output_dir=Path(args.output),
        verbose=args.verbose,
    )
    env = TestEnvironment(config)
    env.initialize()
    
    if args.run_tests:
        print("Running default test suite...")
        report = env.run_tests()
        
        print(f"\n{'='*60}")
        print(f"Test Results: {report.summary['passed']}/{report.summary['total_tests']} passed")
        print(f"Success Rate: {report.success_rate:.1f}%")
        print(f"Projected Rate (after fixes): {report.projected_success_rate:.1f}%")
        print(f"{'='*60}")
        
        if report.failure_analyses:
            print(f"\nTop Issues:")
            for fa in report.failure_analyses[:5]:
                print(f"  - {fa.test_name}: {fa.root_cause}")
        
        print(f"\nReport saved to: {args.output}")
    
    elif args.test_profile:
        with open(args.test_profile, "r") as f:
            profile_data = json.load(f)
        
        result = env.test_profile(profile_data)
        
        print(f"\nProfile Test Results:")
        print(f"  Overall Passed: {result['overall_passed']}")
        print(f"  Risk Score: {result['overall_risk_score']:.1f}")
        
        if result['failure_reasons']:
            print(f"\nFailure Reasons:")
            for reason in result['failure_reasons']:
                print(f"  - {reason}")
        
        if result['recommendations']:
            print(f"\nRecommendations:")
            for rec in result['recommendations']:
                print(f"  - {rec}")
    
    elif args.test_card:
        parts = args.test_card.split("|")
        if len(parts) != 4:
            print("Error: Card format should be number|exp_month|exp_year|cvv")
            return
        
        card_data = {
            "number": parts[0],
            "exp_month": parts[1],
            "exp_year": parts[2],
            "cvv": parts[3],
        }
        
        result = env.test_card(card_data, args.psp)
        
        print(f"\nCard Test Result ({args.psp}):")
        print(f"  Success: {result.get('success', False)}")
        if not result.get('success'):
            print(f"  Decline Reason: {result.get('decline_reason', 'unknown')}")
            print(f"  Message: {result.get('decline_message', '')}")
        print(f"  Risk Score: {result.get('risk_score', 0)}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
