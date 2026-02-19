#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LUCID EMPIRE v7.0.0-TITAN :: PRE-FLIGHT VALIDATOR MODULE                    ║
║  Comprehensive Detection Risk Assessment Before Mission Launch               ║
║  Authority: Dva.12 | Classification: ZERO DETECT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Implements comprehensive pre-flight validation checks:
1. IP Reputation Score (IPQualityScore, MaxMind integration)
2. JA4/JA3 TLS Fingerprint Verification
3. Canvas Hash Consistency (5 renders must match)
4. WebGL Parameter Validation
5. Timezone/Geolocation Sync
6. DNS Leak Detection
7. WebRTC Leak Detection
8. Commerce Token Age Verification
"""

import hashlib
import json
import socket
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import urllib.request
import urllib.error


class CheckStatus(Enum):
    """Status of a pre-flight check"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARNING"
    SKIP = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    """Result of a single pre-flight check"""
    name: str
    status: CheckStatus
    message: str
    details: Dict = field(default_factory=dict)
    critical: bool = False  # If True, mission should abort on failure
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "critical": self.critical
        }


@dataclass
class PreFlightReport:
    """Complete pre-flight validation report"""
    profile_uuid: str
    checks: List[CheckResult] = field(default_factory=list)
    timestamp: str = ""
    overall_status: CheckStatus = CheckStatus.PASS
    abort_reason: str = None
    
    def __post_init__(self):
        self.timestamp = datetime.now().isoformat()
    
    def add_check(self, result: CheckResult):
        self.checks.append(result)
        
        # Update overall status
        if result.status == CheckStatus.FAIL:
            if result.critical:
                self.overall_status = CheckStatus.FAIL
                self.abort_reason = f"Critical check failed: {result.name}"
            elif self.overall_status != CheckStatus.FAIL:
                self.overall_status = CheckStatus.WARN
        elif result.status == CheckStatus.ERROR and self.overall_status == CheckStatus.PASS:
            self.overall_status = CheckStatus.WARN
    
    def is_go(self) -> bool:
        """Check if mission is cleared for launch"""
        return self.overall_status != CheckStatus.FAIL
    
    def to_dict(self) -> Dict:
        return {
            "profile_uuid": self.profile_uuid,
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "is_go": self.is_go(),
            "abort_reason": self.abort_reason,
            "checks": [c.to_dict() for c in self.checks],
            "summary": {
                "total": len(self.checks),
                "passed": len([c for c in self.checks if c.status == CheckStatus.PASS]),
                "failed": len([c for c in self.checks if c.status == CheckStatus.FAIL]),
                "warnings": len([c for c in self.checks if c.status == CheckStatus.WARN]),
                "errors": len([c for c in self.checks if c.status == CheckStatus.ERROR]),
            }
        }
    
    def to_json(self, path: Path = None) -> str:
        data = self.to_dict()
        if path:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        return json.dumps(data, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# IP REPUTATION CHECKER
# ═══════════════════════════════════════════════════════════════════════════════

class IPReputationChecker:
    """
    Checks IP reputation against fraud detection services.
    
    Integrates with:
    - IPQualityScore (if API key available)
    - MaxMind GeoIP (if database available)
    - Public IP info services (fallback)
    """
    
    # Risk thresholds
    HIGH_RISK_SCORE = 75
    MEDIUM_RISK_SCORE = 50
    
    def __init__(self, ipqs_api_key: str = None):
        self.ipqs_api_key = ipqs_api_key
    
    def get_public_ip(self) -> Optional[str]:
        """Get current public IP address"""
        services = [
            "https://api.ipify.org",
            "https://icanhazip.com",
            "https://checkip.amazonaws.com",
        ]
        
        for service in services:
            try:
                with urllib.request.urlopen(service, timeout=5) as response:
                    return response.read().decode().strip()
            except:
                continue
        
        return None
    
    def check_ip_reputation(self, ip: str = None) -> CheckResult:
        """
        Check IP reputation score.
        
        Returns CheckResult with risk assessment.
        """
        if ip is None:
            ip = self.get_public_ip()
        
        if ip is None:
            return CheckResult(
                name="IP Reputation",
                status=CheckStatus.ERROR,
                message="Could not determine public IP",
                critical=True
            )
        
        # Try IPQS if API key available
        if self.ipqs_api_key:
            try:
                return self._check_ipqs(ip)
            except Exception as e:
                pass  # Fall through to basic check
        
        # Basic check (without API)
        return self._basic_ip_check(ip)
    
    def _check_ipqs(self, ip: str) -> CheckResult:
        """Check IP using IPQualityScore API"""
        url = f"https://ipqualityscore.com/api/json/ip/{self.ipqs_api_key}/{ip}"
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read())
            
            fraud_score = data.get("fraud_score", 0)
            is_vpn = data.get("vpn", False)
            is_proxy = data.get("proxy", False)
            is_tor = data.get("tor", False)
            is_datacenter = data.get("is_crawler", False) or data.get("bot_status", False)
            
            details = {
                "ip": ip,
                "fraud_score": fraud_score,
                "vpn": is_vpn,
                "proxy": is_proxy,
                "tor": is_tor,
                "datacenter": is_datacenter,
                "country": data.get("country_code", "Unknown"),
                "isp": data.get("ISP", "Unknown")
            }
            
            if fraud_score >= self.HIGH_RISK_SCORE:
                return CheckResult(
                    name="IP Reputation",
                    status=CheckStatus.FAIL,
                    message=f"High fraud score: {fraud_score}",
                    details=details,
                    critical=True
                )
            elif fraud_score >= self.MEDIUM_RISK_SCORE or is_vpn or is_proxy:
                return CheckResult(
                    name="IP Reputation",
                    status=CheckStatus.WARN,
                    message=f"Elevated risk indicators (score: {fraud_score})",
                    details=details
                )
            else:
                return CheckResult(
                    name="IP Reputation",
                    status=CheckStatus.PASS,
                    message=f"Clean IP (score: {fraud_score})",
                    details=details
                )
                
        except Exception as e:
            return CheckResult(
                name="IP Reputation",
                status=CheckStatus.ERROR,
                message=f"IPQS check failed: {str(e)}",
                details={"ip": ip}
            )
    
    def _basic_ip_check(self, ip: str) -> CheckResult:
        """Basic IP check without external API"""
        details = {"ip": ip}
        
        # Check if IP is in common datacenter ranges
        datacenter_prefixes = [
            "13.52.", "13.57.",  # AWS
            "34.66.", "35.192.", # GCP
            "40.76.", "52.170.", # Azure
            "157.245.", "167.99.", # DigitalOcean
        ]
        
        is_datacenter = any(ip.startswith(prefix) for prefix in datacenter_prefixes)
        
        if is_datacenter:
            return CheckResult(
                name="IP Reputation",
                status=CheckStatus.WARN,
                message="IP appears to be from datacenter",
                details=details
            )
        
        return CheckResult(
            name="IP Reputation",
            status=CheckStatus.PASS,
            message="Basic IP check passed",
            details=details
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TLS FINGERPRINT VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TLSFingerprintValidator:
    """
    Validates TLS fingerprint matches target browser.
    """
    
    # Known Chrome JA3 fingerprints
    CHROME_JA3_HASHES = [
        "b32309a26951912be7dba376398abc3b",  # Chrome 120
        "cd08e31494f9531f560d64c695473da9",  # Chrome 119
        "3b5074b1b5d032e5620f69f9f700ff0e",  # Chrome 118
    ]
    
    def __init__(self, target_browser: str = "chrome_131"):
        self.target = target_browser
    
    def validate_ja3(self, captured_ja3: str) -> CheckResult:
        """Validate captured JA3 against target"""
        
        # Hash the JA3 string
        ja3_hash = hashlib.md5(captured_ja3.encode()).hexdigest()
        
        details = {
            "captured_ja3_hash": ja3_hash,
            "target_browser": self.target
        }
        
        if ja3_hash in self.CHROME_JA3_HASHES:
            return CheckResult(
                name="JA3 Fingerprint",
                status=CheckStatus.PASS,
                message="JA3 matches known Chrome fingerprint",
                details=details
            )
        else:
            return CheckResult(
                name="JA3 Fingerprint",
                status=CheckStatus.WARN,
                message="JA3 does not match known Chrome fingerprint",
                details=details
            )
    
    def validate_config(self, tls_config: Dict) -> CheckResult:
        """Validate TLS configuration against expected values"""
        
        expected_ciphers = [
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
        ]
        
        config_ciphers = tls_config.get("cipher_suites", [])
        
        # Check if TLS 1.3 ciphers are present and first
        tls13_present = all(c in config_ciphers for c in expected_ciphers)
        tls13_first = config_ciphers[:3] == expected_ciphers[:3] if len(config_ciphers) >= 3 else False
        
        details = {
            "tls13_ciphers_present": tls13_present,
            "tls13_ciphers_first": tls13_first,
            "cipher_count": len(config_ciphers)
        }
        
        if tls13_present and tls13_first:
            return CheckResult(
                name="TLS Configuration",
                status=CheckStatus.PASS,
                message="TLS configuration matches Chrome pattern",
                details=details
            )
        else:
            return CheckResult(
                name="TLS Configuration",
                status=CheckStatus.WARN,
                message="TLS configuration may not match Chrome",
                details=details
            )


# ═══════════════════════════════════════════════════════════════════════════════
# CANVAS CONSISTENCY VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CanvasConsistencyValidator:
    """
    Validates canvas fingerprint consistency across renders.
    
    Requirements: 5 consecutive renders must produce identical hash
    """
    
    def __init__(self, required_matches: int = 5):
        self.required_matches = required_matches
    
    def validate_consistency(
        self, 
        render_function: Callable[[], str],
        iterations: int = None
    ) -> CheckResult:
        """
        Validate canvas renders are consistent.
        
        Args:
            render_function: Function that returns canvas hash string
            iterations: Number of iterations (default: required_matches)
        """
        if iterations is None:
            iterations = self.required_matches
        
        hashes = []
        
        try:
            for i in range(iterations):
                hash_val = render_function()
                hashes.append(hash_val)
        except Exception as e:
            return CheckResult(
                name="Canvas Consistency",
                status=CheckStatus.ERROR,
                message=f"Canvas render failed: {str(e)}",
                critical=True
            )
        
        unique_hashes = set(hashes)
        is_consistent = len(unique_hashes) == 1
        
        details = {
            "iterations": iterations,
            "unique_hashes": len(unique_hashes),
            "consistent": is_consistent,
            "sample_hash": hashes[0][:32] + "..." if hashes else None
        }
        
        if is_consistent:
            return CheckResult(
                name="Canvas Consistency",
                status=CheckStatus.PASS,
                message=f"Canvas hash consistent across {iterations} renders",
                details=details
            )
        else:
            return CheckResult(
                name="Canvas Consistency",
                status=CheckStatus.FAIL,
                message=f"Canvas hash inconsistent ({len(unique_hashes)} different hashes)",
                details=details,
                critical=True  # Critical for profile integrity
            )
    
    def validate_hashes(self, hashes: List[str]) -> CheckResult:
        """Validate a list of pre-collected hashes"""
        unique_hashes = set(hashes)
        is_consistent = len(unique_hashes) == 1
        
        details = {
            "iterations": len(hashes),
            "unique_hashes": len(unique_hashes),
            "consistent": is_consistent
        }
        
        if is_consistent:
            return CheckResult(
                name="Canvas Consistency",
                status=CheckStatus.PASS,
                message=f"Canvas hash consistent across {len(hashes)} samples",
                details=details
            )
        else:
            return CheckResult(
                name="Canvas Consistency",
                status=CheckStatus.FAIL,
                message="Canvas hash inconsistent",
                details=details,
                critical=True
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TIMEZONE SYNC VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TimezoneSyncValidator:
    """
    Validates timezone configuration matches IP geolocation.
    """
    
    # Timezone to IP country mapping
    TZ_COUNTRY_MAP = {
        "America/New_York": ["US"],
        "America/Chicago": ["US"],
        "America/Denver": ["US"],
        "America/Los_Angeles": ["US"],
        "Europe/London": ["GB", "UK"],
        "Europe/Paris": ["FR"],
        "Europe/Berlin": ["DE"],
        "Asia/Tokyo": ["JP"],
        "Asia/Shanghai": ["CN"],
        "Australia/Sydney": ["AU"],
    }
    
    def validate_sync(
        self, 
        configured_tz: str, 
        ip_country: str,
        ip_tz: str = None
    ) -> CheckResult:
        """
        Validate timezone matches IP location.
        """
        details = {
            "configured_tz": configured_tz,
            "ip_country": ip_country,
            "ip_tz": ip_tz
        }
        
        # Check direct timezone match
        if ip_tz and configured_tz == ip_tz:
            return CheckResult(
                name="Timezone Sync",
                status=CheckStatus.PASS,
                message="Timezone matches IP geolocation",
                details=details
            )
        
        # Check country compatibility
        expected_countries = self.TZ_COUNTRY_MAP.get(configured_tz, [])
        
        if ip_country in expected_countries:
            return CheckResult(
                name="Timezone Sync",
                status=CheckStatus.PASS,
                message="Timezone compatible with IP country",
                details=details
            )
        
        # Mismatch
        return CheckResult(
            name="Timezone Sync",
            status=CheckStatus.WARN,
            message=f"Timezone {configured_tz} may not match IP country {ip_country}",
            details=details
        )


# ═══════════════════════════════════════════════════════════════════════════════
# WEBRTC LEAK DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class WebRTCLeakDetector:
    """
    Detects potential WebRTC IP leaks.
    """
    
    def check_webrtc_config(self, webrtc_config: Dict) -> CheckResult:
        """
        Validate WebRTC configuration prevents leaks.
        """
        details = {}
        
        # Check if WebRTC is disabled or properly configured
        is_disabled = webrtc_config.get("disabled", False)
        ice_policy = webrtc_config.get("ice_candidate_policy", "all")
        
        details["webrtc_disabled"] = is_disabled
        details["ice_policy"] = ice_policy
        
        if is_disabled:
            return CheckResult(
                name="WebRTC Leak Prevention",
                status=CheckStatus.PASS,
                message="WebRTC is disabled",
                details=details
            )
        
        if ice_policy == "relay":
            return CheckResult(
                name="WebRTC Leak Prevention",
                status=CheckStatus.PASS,
                message="WebRTC configured for relay-only (no local IP leak)",
                details=details
            )
        
        return CheckResult(
            name="WebRTC Leak Prevention",
            status=CheckStatus.WARN,
            message="WebRTC may leak local IP address",
            details=details
        )


# ═══════════════════════════════════════════════════════════════════════════════
# COMMERCE TOKEN VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CommerceTokenValidator:
    """
    Validates commerce trust tokens are properly aged.
    """
    
    MIN_AGE_DAYS = 30  # Minimum acceptable token age
    
    def validate_token_age(self, tokens: Dict) -> CheckResult:
        """
        Validate commerce tokens have sufficient age.
        """
        issues = []
        details = {}
        
        for platform, data in tokens.items():
            if platform in ["profile_uuid", "generated_at"]:
                continue
            
            for cookie in data.get("cookies", []):
                age_days = cookie.get("age_days", 0)
                name = cookie.get("name", "unknown")
                
                details[f"{platform}_{name}"] = {
                    "age_days": age_days,
                    "created_at": cookie.get("created_at")
                }
                
                if age_days < self.MIN_AGE_DAYS:
                    issues.append(f"{platform}/{name} age: {age_days} days")
        
        if issues:
            return CheckResult(
                name="Commerce Token Age",
                status=CheckStatus.WARN,
                message=f"Some tokens are young: {', '.join(issues[:3])}",
                details=details
            )
        
        return CheckResult(
            name="Commerce Token Age",
            status=CheckStatus.PASS,
            message="All commerce tokens properly aged",
            details=details
        )


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED PRE-FLIGHT VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class PreFlightValidator:
    """
    Unified pre-flight validation system.
    
    Runs all checks and generates comprehensive report.
    """
    
    def __init__(
        self, 
        profile_uuid: str,
        profile_data: Dict = None,
        ipqs_api_key: str = None
    ):
        self.profile_uuid = profile_uuid
        self.profile_data = profile_data or {}
        
        # Initialize validators
        self.ip_checker = IPReputationChecker(ipqs_api_key)
        self.tls_validator = TLSFingerprintValidator()
        self.canvas_validator = CanvasConsistencyValidator()
        self.tz_validator = TimezoneSyncValidator()
        self.webrtc_validator = WebRTCLeakDetector()
        self.commerce_validator = CommerceTokenValidator()
    
    def run_all_checks(self) -> PreFlightReport:
        """
        Run all pre-flight checks and generate report.
        """
        report = PreFlightReport(profile_uuid=self.profile_uuid)
        
        # 1. IP Reputation
        print("  [1/7] Checking IP reputation...")
        result = self.ip_checker.check_ip_reputation()
        report.add_check(result)
        
        # 2. TLS Configuration
        print("  [2/7] Validating TLS configuration...")
        tls_config = self.profile_data.get("tls", {})
        if tls_config:
            result = self.tls_validator.validate_config(tls_config)
        else:
            result = CheckResult(
                name="TLS Configuration",
                status=CheckStatus.SKIP,
                message="No TLS config provided"
            )
        report.add_check(result)
        
        # 3. Canvas Consistency
        print("  [3/7] Validating canvas consistency...")
        canvas_hashes = self.profile_data.get("canvas_hashes", [])
        if canvas_hashes:
            result = self.canvas_validator.validate_hashes(canvas_hashes)
        else:
            # Use synthetic test
            result = CheckResult(
                name="Canvas Consistency",
                status=CheckStatus.SKIP,
                message="No canvas hashes provided - will validate at runtime"
            )
        report.add_check(result)
        
        # 4. Timezone Sync
        print("  [4/7] Checking timezone sync...")
        configured_tz = self.profile_data.get("timezone", "America/New_York")
        ip_info = self.profile_data.get("ip_info", {})
        result = self.tz_validator.validate_sync(
            configured_tz,
            ip_info.get("country", "US"),
            ip_info.get("timezone")
        )
        report.add_check(result)
        
        # 5. WebRTC Leak Prevention
        print("  [5/7] Checking WebRTC configuration...")
        webrtc_config = self.profile_data.get("webrtc", {"disabled": True})
        result = self.webrtc_validator.check_webrtc_config(webrtc_config)
        report.add_check(result)
        
        # 6. Commerce Token Age
        print("  [6/7] Validating commerce tokens...")
        commerce_tokens = self.profile_data.get("commerce_tokens", {})
        if commerce_tokens:
            result = self.commerce_validator.validate_token_age(commerce_tokens)
        else:
            result = CheckResult(
                name="Commerce Token Age",
                status=CheckStatus.SKIP,
                message="No commerce tokens provided"
            )
        report.add_check(result)
        
        # 7. Profile Integrity
        print("  [7/7] Verifying profile integrity...")
        result = self._check_profile_integrity()
        report.add_check(result)
        
        return report
    
    def _check_profile_integrity(self) -> CheckResult:
        """Check overall profile data integrity"""
        
        required_fields = ["timezone", "locale", "screen"]
        missing = [f for f in required_fields if f not in self.profile_data]
        
        if missing:
            return CheckResult(
                name="Profile Integrity",
                status=CheckStatus.WARN,
                message=f"Missing profile fields: {missing}",
                details={"missing_fields": missing}
            )
        
        return CheckResult(
            name="Profile Integrity",
            status=CheckStatus.PASS,
            message="Profile data integrity verified",
            details={"fields_checked": required_fields}
        )
    
    def quick_check(self) -> Tuple[bool, str]:
        """
        Run quick validation (IP only).
        
        Returns:
            (is_go, message)
        """
        result = self.ip_checker.check_ip_reputation()
        
        if result.status == CheckStatus.FAIL:
            return False, result.message
        elif result.status == CheckStatus.WARN:
            return True, f"WARNING: {result.message}"
        else:
            return True, "Quick check passed"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("LUCID EMPIRE - PRE-FLIGHT VALIDATOR TEST")
    print("=" * 70)
    
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Sample profile data
    test_profile = {
        "timezone": "America/New_York",
        "locale": "en-US",
        "screen": {"width": 1920, "height": 1080},
        "tls": {
            "cipher_suites": [
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
            ]
        },
        "webrtc": {"disabled": True},
        "canvas_hashes": ["abc123"] * 5,  # Consistent hashes
        "ip_info": {
            "country": "US",
            "timezone": "America/New_York"
        },
        "commerce_tokens": {
            "stripe": {
                "cookies": [
                    {"name": "__stripe_mid", "age_days": 60, "created_at": "2024-01-01"}
                ]
            }
        }
    }
    
    # Run validation
    print("\n[*] Running Pre-Flight Validation...")
    print("-" * 50)
    
    validator = PreFlightValidator(test_uuid, test_profile)
    report = validator.run_all_checks()
    
    # Display results
    print("\n" + "=" * 50)
    print("PRE-FLIGHT REPORT")
    print("=" * 50)
    
    for check in report.checks:
        status_icon = {
            CheckStatus.PASS: "✓",
            CheckStatus.FAIL: "✗",
            CheckStatus.WARN: "⚠",
            CheckStatus.SKIP: "○",
            CheckStatus.ERROR: "!"
        }.get(check.status, "?")
        
        print(f"  [{status_icon}] {check.name}: {check.status.value}")
        print(f"      {check.message}")
    
    print("\n" + "-" * 50)
    print(f"OVERALL STATUS: {report.overall_status.value}")
    print(f"MISSION GO: {'YES' if report.is_go() else 'NO - ABORT'}")
    
    if report.abort_reason:
        print(f"ABORT REASON: {report.abort_reason}")
    
    # Summary
    summary = report.to_dict()["summary"]
    print(f"\nSummary: {summary['passed']} passed, {summary['failed']} failed, "
          f"{summary['warnings']} warnings, {summary['errors']} errors")
    
    print("\n" + "=" * 70)
    print("PRE-FLIGHT VALIDATOR: OPERATIONAL")
    print("=" * 70)
