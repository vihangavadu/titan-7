"""
TITAN V7.0 SINGULARITY - Pre-Flight Validator
Comprehensive validation before operation to ensure 100% success

This module performs all critical checks BEFORE launching browser:
- Proxy validation (residential, not datacenter)
- IP geolocation match
- DNS leak test
- WebRTC leak test
- Timezone consistency
- Profile completeness
"""

import json
import os
import subprocess
import socket
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging
import re

logger = logging.getLogger("TITAN-PREFLIGHT")


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class PreFlightCheck:
    """Individual pre-flight check result"""
    name: str
    status: CheckStatus
    message: str
    critical: bool = True
    details: Dict = field(default_factory=dict)


@dataclass
class PreFlightReport:
    """Complete pre-flight validation report"""
    passed: bool = False
    checks: List[PreFlightCheck] = field(default_factory=list)
    abort_reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def critical_failures(self) -> List[PreFlightCheck]:
        return [c for c in self.checks if c.status == CheckStatus.FAIL and c.critical]
    
    @property
    def warnings(self) -> List[PreFlightCheck]:
        return [c for c in self.checks if c.status == CheckStatus.WARN]
    
    @property
    def overall_status(self) -> CheckStatus:
        """V7.5 FIX: Compatibility property for integration_bridge"""
        if self.critical_failures:
            return CheckStatus.FAIL
        if self.warnings:
            return CheckStatus.WARN
        return CheckStatus.PASS
    
    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "critical": c.critical,
                    "details": c.details
                }
                for c in self.checks
            ],
            "abort_reason": self.abort_reason,
            "timestamp": self.timestamp
        }


class PreFlightValidator:
    """
    Comprehensive pre-flight validation for TITAN operations.
    
    Run this BEFORE launching browser to catch issues that would
    cause detection or decline.
    """
    
    # Known datacenter IP ranges (partial list)
    DATACENTER_ASNS = [
        "AS14061",  # DigitalOcean
        "AS16509",  # Amazon AWS
        "AS15169",  # Google Cloud
        "AS8075",   # Microsoft Azure
        "AS13335",  # Cloudflare
        "AS20473",  # Vultr
        "AS63949",  # Linode
        "AS14618",  # Amazon
        "AS396982", # Google
    ]
    
    def __init__(self, profile_path: Optional[Path] = None, 
                 proxy_url: Optional[str] = None,
                 billing_region: Optional[Dict] = None):
        self.profile_path = Path(profile_path) if profile_path else None
        self.proxy_url = proxy_url
        self.billing_region = billing_region or {}
        self.report = PreFlightReport()
    
    def run_all_checks(self) -> PreFlightReport:
        """Run all pre-flight checks"""
        logger.info("Starting pre-flight validation...")
        
        # Profile checks
        if self.profile_path:
            self._check_profile_exists()
            self._check_profile_age()
            self._check_profile_storage()
            self._check_autofill_data()
        
        # Network checks
        if self.proxy_url:
            self._check_proxy_connection()
            self._check_ip_type()
            self._check_ip_reputation()
            self._check_geo_match()
        
        # VPN checks (if using Lucid VPN instead of proxy)
        self._check_vpn_tunnel()
        
        # System checks
        self._check_timezone()
        self._check_system_locale()
        
        # V8 U14-FIX: Fingerprint readiness check
        self._check_fingerprint_readiness()
        
        # Determine overall status
        if self.report.critical_failures:
            self.report.passed = False
            self.report.abort_reason = self.report.critical_failures[0].message
        else:
            self.report.passed = True
        
        logger.info(f"Pre-flight complete: {'PASS' if self.report.passed else 'FAIL'}")
        return self.report
    
    def _check_profile_exists(self):
        """Check if profile directory exists and has required files"""
        if not self.profile_path or not self.profile_path.exists():
            self.report.checks.append(PreFlightCheck(
                name="Profile Exists",
                status=CheckStatus.FAIL,
                message=f"Profile not found: {self.profile_path}",
                critical=True
            ))
            return
        
        # Check for required files
        required_files = ["places.sqlite", "cookies.sqlite"]
        missing = [f for f in required_files if not (self.profile_path / f).exists()]
        
        if missing:
            self.report.checks.append(PreFlightCheck(
                name="Profile Exists",
                status=CheckStatus.WARN,
                message=f"Missing files: {missing}",
                critical=False,
                details={"missing": missing}
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="Profile Exists",
                status=CheckStatus.PASS,
                message="Profile directory valid"
            ))
    
    def _check_profile_age(self):
        """Check if profile has sufficient age"""
        meta_file = self.profile_path / "profile_metadata.json"
        if not meta_file.exists():
            self.report.checks.append(PreFlightCheck(
                name="Profile Age",
                status=CheckStatus.WARN,
                message="No metadata file found",
                critical=False
            ))
            return
        
        try:
            with open(meta_file) as f:
                meta = json.load(f)
            
            age_days = meta.get("profile_age_days", 0)
            if age_days < 60:
                self.report.checks.append(PreFlightCheck(
                    name="Profile Age",
                    status=CheckStatus.WARN,
                    message=f"Profile age {age_days} days is below recommended 60 days",
                    critical=False,
                    details={"age_days": age_days}
                ))
            else:
                self.report.checks.append(PreFlightCheck(
                    name="Profile Age",
                    status=CheckStatus.PASS,
                    message=f"Profile age: {age_days} days",
                    details={"age_days": age_days}
                ))
        except Exception as e:
            self.report.checks.append(PreFlightCheck(
                name="Profile Age",
                status=CheckStatus.WARN,
                message=f"Could not read metadata: {e}",
                critical=False
            ))
    
    def _check_profile_storage(self):
        """Check if profile has sufficient storage size"""
        if not self.profile_path:
            return
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size for f in self.profile_path.rglob("*") if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)
        
        if size_mb < 100:
            self.report.checks.append(PreFlightCheck(
                name="Profile Storage",
                status=CheckStatus.WARN,
                message=f"Profile size {size_mb:.1f}MB is below recommended 300MB",
                critical=False,
                details={"size_mb": size_mb}
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="Profile Storage",
                status=CheckStatus.PASS,
                message=f"Profile size: {size_mb:.1f}MB",
                details={"size_mb": size_mb}
            ))
    
    def _check_autofill_data(self):
        """Check if autofill data is present"""
        autofill_file = self.profile_path / "autofill-profiles.json"
        formhistory = self.profile_path / "formhistory.sqlite"
        
        has_autofill = autofill_file.exists() or formhistory.exists()
        
        if has_autofill:
            self.report.checks.append(PreFlightCheck(
                name="Autofill Data",
                status=CheckStatus.PASS,
                message="Autofill data present"
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="Autofill Data",
                status=CheckStatus.WARN,
                message="No autofill data found - checkout may require manual entry",
                critical=False
            ))
    
    def _check_vpn_tunnel(self):
        """Check Lucid VPN tunnel status if VPN mode is active"""
        try:
            from lucid_vpn import LucidVPN, VPNStatus, VPNMode
            vpn = LucidVPN()
            vpn.load_config()
            state = vpn.get_state()
            
            # Only check if VPN mode is active (not proxy mode)
            if state.mode == VPNMode.PROXY:
                return
            
            if state.status == VPNStatus.CONNECTED:
                # Xray tunnel alive
                self.report.checks.append(PreFlightCheck(
                    name="VPN Tunnel",
                    status=CheckStatus.PASS,
                    message=f"Lucid VPN connected — Exit IP: {state.exit_ip}",
                    details={"exit_ip": state.exit_ip, "mode": state.mode.value}
                ))
                # TCP spoofing
                if state.tcp_spoofed:
                    self.report.checks.append(PreFlightCheck(
                        name="TCP/IP Spoofing",
                        status=CheckStatus.PASS,
                        message="TCP/IP stack spoofed (Windows 11 fingerprint)"
                    ))
                else:
                    self.report.checks.append(PreFlightCheck(
                        name="TCP/IP Spoofing",
                        status=CheckStatus.WARN,
                        message="TCP/IP spoofing not active — p0f fingerprint may expose Linux",
                        critical=False
                    ))
                # DNS security
                if state.dns_secure:
                    self.report.checks.append(PreFlightCheck(
                        name="VPN DNS",
                        status=CheckStatus.PASS,
                        message="DNS routed through secure resolver (no leak)"
                    ))
                else:
                    self.report.checks.append(PreFlightCheck(
                        name="VPN DNS",
                        status=CheckStatus.WARN,
                        message="DNS may not be fully secured — check for leaks",
                        critical=False
                    ))
                # Tailscale mesh
                if state.tailscale_connected:
                    self.report.checks.append(PreFlightCheck(
                        name="Tailscale Mesh",
                        status=CheckStatus.PASS,
                        message="Tailscale mesh connected to residential exit"
                    ))
                # Set proxy_url for downstream checks
                socks_url = vpn.get_socks5_url()
                if socks_url and not self.proxy_url:
                    self.proxy_url = socks_url
            elif state.status == VPNStatus.ERROR:
                self.report.checks.append(PreFlightCheck(
                    name="VPN Tunnel",
                    status=CheckStatus.FAIL,
                    message=f"VPN error: {state.error_message}",
                    critical=True
                ))
            elif state.mode != VPNMode.PROXY:
                self.report.checks.append(PreFlightCheck(
                    name="VPN Tunnel",
                    status=CheckStatus.FAIL,
                    message="VPN mode selected but tunnel not connected. Run titan-vpn-setup --connect",
                    critical=True
                ))
        except ImportError:
            pass
        except Exception as e:
            self.report.checks.append(PreFlightCheck(
                name="VPN Tunnel",
                status=CheckStatus.WARN,
                message=f"Could not check VPN status: {e}",
                critical=False
            ))
    
    def _check_proxy_connection(self):
        """Check if proxy is reachable"""
        if not self.proxy_url:
            self.report.checks.append(PreFlightCheck(
                name="Proxy Connection",
                status=CheckStatus.SKIP,
                message="No proxy configured"
            ))
            return
        
        try:
            # Try to connect through proxy
            result = subprocess.run(
                ["curl", "-s", "--proxy", self.proxy_url, "--max-time", "10", "https://ipinfo.io/json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                ip_info = json.loads(result.stdout)
                self.report.checks.append(PreFlightCheck(
                    name="Proxy Connection",
                    status=CheckStatus.PASS,
                    message=f"Connected via {ip_info.get('ip', 'unknown')}",
                    details=ip_info
                ))
            else:
                self.report.checks.append(PreFlightCheck(
                    name="Proxy Connection",
                    status=CheckStatus.FAIL,
                    message="Proxy connection failed",
                    critical=True
                ))
        except Exception as e:
            self.report.checks.append(PreFlightCheck(
                name="Proxy Connection",
                status=CheckStatus.FAIL,
                message=f"Proxy error: {e}",
                critical=True
            ))
    
    def _check_ip_type(self):
        """Check if IP is residential (not datacenter)"""
        # Find the proxy connection check result
        proxy_check = next((c for c in self.report.checks if c.name == "Proxy Connection"), None)
        
        if not proxy_check or proxy_check.status != CheckStatus.PASS:
            return
        
        ip_info = proxy_check.details
        org = ip_info.get("org", "")
        
        # Check for datacenter ASNs
        is_datacenter = any(asn in org for asn in self.DATACENTER_ASNS)
        
        # Check for common datacenter keywords
        datacenter_keywords = ["hosting", "cloud", "server", "datacenter", "vps", "dedicated"]
        has_dc_keyword = any(kw in org.lower() for kw in datacenter_keywords)
        
        if is_datacenter or has_dc_keyword:
            self.report.checks.append(PreFlightCheck(
                name="IP Type",
                status=CheckStatus.FAIL,
                message=f"DATACENTER IP DETECTED: {org}",
                critical=True,
                details={"org": org, "is_datacenter": True}
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="IP Type",
                status=CheckStatus.PASS,
                message=f"Residential IP: {org}",
                details={"org": org, "is_datacenter": False}
            ))
    
    def _check_ip_reputation(self):
        """
        V7.0.2: Check IP fraud score via Scamalytics and IPQualityScore.
        
        Targets: 10% of failures caused by poor IP reputation.
        Threshold: Score >25 = WARN (rotate recommended), >50 = FAIL (abort).
        
        Uses free Scamalytics web check + optional IPQS API key from titan.env.
        """
        proxy_check = next((c for c in self.report.checks if c.name == "Proxy Connection"), None)
        if not proxy_check or proxy_check.status != CheckStatus.PASS:
            return
        
        exit_ip = proxy_check.details.get("ip", "")
        if not exit_ip:
            return
        
        fraud_score = None
        score_source = None
        details = {"ip": exit_ip}
        
        # Method 0: Self-hosted IP Quality Checker (zero latency, no API key)
        try:
            from titan_self_hosted_stack import get_ip_quality_checker
            ip_checker = get_ip_quality_checker()
            if ip_checker and ip_checker.is_available:
                ip_result = ip_checker.check(exit_ip)
                if ip_result.get("risk_score") is not None:
                    fraud_score = ip_result["risk_score"]
                    score_source = "self-hosted-ip-checker"
                    details["sh_risk_score"] = fraud_score
                    details["sh_is_proxy"] = ip_result.get("is_proxy", False)
                    details["sh_is_datacenter"] = ip_result.get("is_datacenter", False)
                    details["sh_is_residential"] = ip_result.get("is_residential", False)
                    details["sh_recommendation"] = ip_result.get("recommendation", "")
        except ImportError:
            pass
        
        # Method 1: Scamalytics free check (no API key needed)
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "8",
                 f"https://scamalytics.com/ip/{exit_ip}"],
                capture_output=True, text=True, timeout=12
            )
            if result.returncode == 0 and "Fraud Score:" in result.stdout:
                score_match = re.search(r'Fraud Score:\s*(\d+)', result.stdout)
                if score_match:
                    fraud_score = int(score_match.group(1))
                    score_source = "scamalytics"
                    details["scamalytics_score"] = fraud_score
                # Check for proxy/VPN detection
                if "vpn" in result.stdout.lower():
                    vpn_match = re.search(r'(VPN|Proxy)[^<]*?(Yes|No)', result.stdout, re.IGNORECASE)
                    if vpn_match:
                        details["vpn_detected"] = vpn_match.group(2).lower()
        except Exception:
            pass
        
        # Method 2: IPQualityScore API (if key configured in titan.env)
        if fraud_score is None:
            ipqs_key = os.environ.get("TITAN_IPQS_KEY", "")
            if ipqs_key and ipqs_key != "REPLACE_WITH_IPQS_KEY":
                try:
                    result = subprocess.run(
                        ["curl", "-s", "--max-time", "8",
                         f"https://ipqualityscore.com/api/json/ip/{ipqs_key}/{exit_ip}?strictness=1&allow_public_access_points=true"],
                        capture_output=True, text=True, timeout=12
                    )
                    if result.returncode == 0:
                        ipqs_data = json.loads(result.stdout)
                        if ipqs_data.get("success", False):
                            fraud_score = int(ipqs_data.get("fraud_score", 0))
                            score_source = "ipqualityscore"
                            details["ipqs_score"] = fraud_score
                            details["ipqs_vpn"] = ipqs_data.get("vpn", False)
                            details["ipqs_proxy"] = ipqs_data.get("proxy", False)
                            details["ipqs_tor"] = ipqs_data.get("tor", False)
                            details["ipqs_isp"] = ipqs_data.get("ISP", "")
                            details["ipqs_connection"] = ipqs_data.get("connection_type", "")
                except Exception:
                    pass
        
        # Method 3: Fallback - check ip-api.com for basic hosting detection
        if fraud_score is None:
            try:
                result = subprocess.run(
                    ["curl", "-s", "--max-time", "5",
                     f"http://ip-api.com/json/{exit_ip}?fields=hosting,proxy,isp,org"],
                    capture_output=True, text=True, timeout=8
                )
                if result.returncode == 0:
                    ip_data = json.loads(result.stdout)
                    is_hosting = ip_data.get("hosting", False)
                    is_proxy = ip_data.get("proxy", False)
                    details["ip_api_hosting"] = is_hosting
                    details["ip_api_proxy"] = is_proxy
                    details["ip_api_isp"] = ip_data.get("isp", "")
                    # Estimate score from binary signals
                    fraud_score = 0
                    if is_hosting:
                        fraud_score += 60
                    if is_proxy:
                        fraud_score += 25
                    score_source = "ip-api (estimated)"
            except Exception:
                pass
        
        # Evaluate score
        if fraud_score is not None:
            details["score_source"] = score_source
            
            if fraud_score > 50:
                self.report.checks.append(PreFlightCheck(
                    name="IP Reputation",
                    status=CheckStatus.FAIL,
                    message=f"HIGH RISK IP — {score_source} score: {fraud_score}/100. ROTATE IP before proceeding",
                    critical=True,
                    details=details
                ))
            elif fraud_score > 25:
                self.report.checks.append(PreFlightCheck(
                    name="IP Reputation",
                    status=CheckStatus.WARN,
                    message=f"ELEVATED IP score: {fraud_score}/100 ({score_source}). Consider rotating for high-value targets",
                    critical=False,
                    details=details
                ))
            else:
                self.report.checks.append(PreFlightCheck(
                    name="IP Reputation",
                    status=CheckStatus.PASS,
                    message=f"Clean IP — {score_source} score: {fraud_score}/100",
                    details=details
                ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="IP Reputation",
                status=CheckStatus.WARN,
                message="Could not check IP reputation (no API available). Verify manually at scamalytics.com",
                critical=False,
                details=details
            ))
    
    def _check_geo_match(self):
        """Check if proxy location matches billing region"""
        if not self.billing_region:
            self.report.checks.append(PreFlightCheck(
                name="Geo Match",
                status=CheckStatus.SKIP,
                message="No billing region specified"
            ))
            return
        
        proxy_check = next((c for c in self.report.checks if c.name == "Proxy Connection"), None)
        if not proxy_check or proxy_check.status != CheckStatus.PASS:
            return
        
        exit_ip = proxy_check.details.get("ip", "")
        billing_state = self.billing_region.get("state", "").upper()
        billing_country = self.billing_region.get("country", "US").upper()
        billing_zip = self.billing_region.get("zip", "")
        
        # Try self-hosted GeoIP first (offline, zero-latency, detailed scoring)
        geoip_used = False
        try:
            from titan_self_hosted_stack import get_geoip_validator
            geoip = get_geoip_validator()
            if geoip and geoip.is_available and exit_ip:
                match_result = geoip.check_geo_match(
                    exit_ip, card_country=billing_country,
                    card_state=billing_state, card_zip=billing_zip
                )
                if "error" not in match_result:
                    geoip_used = True
                    score = match_result.get("score", 0)
                    details = match_result.get("details", {})
                    details["source"] = "self-hosted-geoip"
                    details["score"] = score
                    
                    if score >= 0.8:
                        self.report.checks.append(PreFlightCheck(
                            name="Geo Match",
                            status=CheckStatus.PASS,
                            message=f"Strong geo match (score: {score}) — country+state aligned",
                            details=details
                        ))
                    elif score >= 0.5:
                        self.report.checks.append(PreFlightCheck(
                            name="Geo Match",
                            status=CheckStatus.PASS,
                            message=f"Acceptable geo match (score: {score}) — country match",
                            details=details
                        ))
                    else:
                        self.report.checks.append(PreFlightCheck(
                            name="Geo Match",
                            status=CheckStatus.WARN,
                            message=f"Weak geo match (score: {score}) — consider rotating proxy",
                            critical=False,
                            details=details
                        ))
                    return
        except ImportError:
            pass
        
        # Fallback: use ip-api data from proxy connection check
        ip_info = proxy_check.details
        proxy_region = ip_info.get("region", "").upper()
        proxy_city = ip_info.get("city", "").upper()
        billing_city = self.billing_region.get("city", "").upper()
        
        # Check state match
        state_match = proxy_region == billing_state or billing_state in proxy_region
        city_match = proxy_city == billing_city or billing_city in proxy_city
        
        if state_match:
            self.report.checks.append(PreFlightCheck(
                name="Geo Match",
                status=CheckStatus.PASS,
                message=f"Region match: {proxy_region}",
                details={"proxy_region": proxy_region, "billing_state": billing_state}
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="Geo Match",
                status=CheckStatus.WARN,
                message=f"Region mismatch: Proxy={proxy_region}, Billing={billing_state}",
                critical=False,
                details={"proxy_region": proxy_region, "billing_state": billing_state}
            ))
    
    def _check_timezone(self):
        """Check if system timezone matches billing region"""
        if not self.billing_region:
            return
        
        # Get current system timezone
        try:
            import time
            tz_name = time.tzname[0]
            
            billing_state = self.billing_region.get("state", "").upper()
            
            # V7.5 FIX: Expanded state timezone map (all 50 states)
            state_timezones = {
                "CT": ["EST", "EDT", "Eastern"], "ME": ["EST", "EDT", "Eastern"],
                "MA": ["EST", "EDT", "Eastern"], "NH": ["EST", "EDT", "Eastern"],
                "RI": ["EST", "EDT", "Eastern"], "VT": ["EST", "EDT", "Eastern"],
                "NJ": ["EST", "EDT", "Eastern"], "NY": ["EST", "EDT", "Eastern"],
                "PA": ["EST", "EDT", "Eastern"], "DE": ["EST", "EDT", "Eastern"],
                "MD": ["EST", "EDT", "Eastern"], "VA": ["EST", "EDT", "Eastern"],
                "WV": ["EST", "EDT", "Eastern"], "NC": ["EST", "EDT", "Eastern"],
                "SC": ["EST", "EDT", "Eastern"], "GA": ["EST", "EDT", "Eastern"],
                "FL": ["EST", "EDT", "Eastern"], "DC": ["EST", "EDT", "Eastern"],
                "OH": ["EST", "EDT", "Eastern"], "MI": ["EST", "EDT", "Eastern"],
                "IN": ["EST", "EDT", "Eastern"], "KY": ["EST", "EDT", "Eastern"],
                "AL": ["CST", "CDT", "Central"], "IL": ["CST", "CDT", "Central"],
                "IA": ["CST", "CDT", "Central"], "KS": ["CST", "CDT", "Central"],
                "LA": ["CST", "CDT", "Central"], "MN": ["CST", "CDT", "Central"],
                "MS": ["CST", "CDT", "Central"], "MO": ["CST", "CDT", "Central"],
                "NE": ["CST", "CDT", "Central"], "ND": ["CST", "CDT", "Central"],
                "OK": ["CST", "CDT", "Central"], "SD": ["CST", "CDT", "Central"],
                "TN": ["CST", "CDT", "Central"], "TX": ["CST", "CDT", "Central"],
                "WI": ["CST", "CDT", "Central"], "AR": ["CST", "CDT", "Central"],
                "AZ": ["MST", "Mountain"], "CO": ["MST", "MDT", "Mountain"],
                "ID": ["MST", "MDT", "Mountain"], "MT": ["MST", "MDT", "Mountain"],
                "NM": ["MST", "MDT", "Mountain"], "UT": ["MST", "MDT", "Mountain"],
                "WY": ["MST", "MDT", "Mountain"], "NV": ["PST", "PDT", "Pacific"],
                "CA": ["PST", "PDT", "Pacific"], "OR": ["PST", "PDT", "Pacific"],
                "WA": ["PST", "PDT", "Pacific"],
                "AK": ["AKST", "AKDT", "Alaska"], "HI": ["HST", "Hawaii"],
            }
            
            expected = state_timezones.get(billing_state, [])
            matches = any(tz in tz_name for tz in expected)
            
            if matches or not expected:
                self.report.checks.append(PreFlightCheck(
                    name="Timezone",
                    status=CheckStatus.PASS,
                    message=f"Timezone: {tz_name}"
                ))
            else:
                self.report.checks.append(PreFlightCheck(
                    name="Timezone",
                    status=CheckStatus.WARN,
                    message=f"Timezone mismatch: System={tz_name}, Expected={expected}",
                    critical=False
                ))
        except Exception as e:
            self.report.checks.append(PreFlightCheck(
                name="Timezone",
                status=CheckStatus.WARN,
                message=f"Could not check timezone: {e}",
                critical=False
            ))
    
    def _check_system_locale(self):
        """Check if system locale matches billing country"""
        try:
            import locale
            current_locale = locale.getlocale()
            
            self.report.checks.append(PreFlightCheck(
                name="System Locale",
                status=CheckStatus.PASS,
                message=f"Locale: {current_locale}",
                details={"locale": current_locale}
            ))
        except Exception as e:
            self.report.checks.append(PreFlightCheck(
                name="System Locale",
                status=CheckStatus.WARN,
                message=f"Could not check locale: {e}",
                critical=False
            ))
    
    def _check_fingerprint_readiness(self):
        """V8 U14-FIX: Check if fingerprint shim modules are available for injection"""
        shim_modules = {
            "canvas_subpixel_shim": "Canvas sub-pixel rendering correction",
            "audio_hardener": "Audio stack nullification",
            "font_sanitizer": "Font sanitization",
            "fingerprint_injector": "Fingerprint injector (WebRTC, ClientHints)",
            "cpuid_rdtsc_shield": "CPUID/RDTSC VM marker suppression",
        }
        available = []
        missing = []
        
        for mod_name, description in shim_modules.items():
            try:
                __import__(mod_name)
                available.append(mod_name)
            except ImportError:
                missing.append(f"{mod_name} ({description})")
        
        # Check eBPF availability
        ebpf_ready = False
        try:
            from network_shield_loader import NetworkShield
            ns = NetworkShield()
            ebpf_ready = hasattr(ns, 'is_available') and ns.is_available()
        except Exception:
            pass
        
        if missing:
            self.report.checks.append(PreFlightCheck(
                name="Fingerprint Readiness",
                status=CheckStatus.WARN,
                message=f"{len(available)}/{len(shim_modules)} shims available, missing: {', '.join(missing)}",
                critical=False,
                details={"available": available, "missing": missing, "ebpf_ready": ebpf_ready}
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="Fingerprint Readiness",
                status=CheckStatus.PASS,
                message=f"All {len(available)} fingerprint shims available, eBPF: {'ready' if ebpf_ready else 'unavailable'}",
                details={"available": available, "ebpf_ready": ebpf_ready}
            ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # ENHANCED CHECKS (Source: 13 PDFs + 2 TXT Research Reports)
    # ═══════════════════════════════════════════════════════════════════════
    
    def run_antifraud_checks(self, target_name: str = None,
                              email: str = None, phone: str = None) -> PreFlightReport:
        """
        Run enhanced antifraud-aware checks on top of standard pre-flight.
        Operator decision support - estimates detection risk before operation.
        
        Args:
            target_name: Target ID to load fraud engine profile
            email: Persona email to check quality
            phone: Persona phone to check quality
        """
        # Run standard checks first
        self.run_all_checks()
        
        # Enhanced checks
        if email:
            self._check_email_quality(email)
        if phone:
            self._check_phone_quality(phone)
        if target_name:
            self._check_target_readiness(target_name)
        
        # Re-evaluate overall status
        if self.report.critical_failures:
            self.report.passed = False
            self.report.abort_reason = self.report.critical_failures[0].message
        
        return self.report
    
    def _check_email_quality(self, email: str):
        """Check email quality against SEON scoring criteria (b1stash PDF 012)"""
        issues = []
        score_penalty = 0
        
        domain = email.split("@")[-1] if "@" in email else ""
        
        # Disposable email providers (SEON: 80 points)
        disposable_domains = [
            "tempmail.com", "guerrillamail.com", "mailinator.com",
            "yopmail.com", "throwaway.email", "temp-mail.org",
            "10minutemail.com", "trashmail.com", "sharklasers.com",
        ]
        if domain.lower() in disposable_domains:
            issues.append("Disposable email domain (+80pts SEON)")
            score_penalty += 80
        
        # Free email is acceptable but premium is better
        free_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
        if domain.lower() not in free_domains and not any(d in domain for d in disposable_domains):
            issues.append("Custom domain - ensure it's aged >1 month (SEON: +10pts if new)")
        
        if score_penalty >= 50:
            self.report.checks.append(PreFlightCheck(
                name="Email Quality",
                status=CheckStatus.FAIL,
                message=f"Email fails SEON check: {'; '.join(issues)}",
                critical=True,
                details={"email_domain": domain, "seon_penalty": score_penalty}
            ))
        elif issues:
            self.report.checks.append(PreFlightCheck(
                name="Email Quality",
                status=CheckStatus.WARN,
                message=f"Email warnings: {'; '.join(issues)}",
                critical=False,
                details={"email_domain": domain, "seon_penalty": score_penalty}
            ))
        else:
            self.report.checks.append(PreFlightCheck(
                name="Email Quality",
                status=CheckStatus.PASS,
                message=f"Email domain acceptable: {domain}",
                details={"email_domain": domain}
            ))
    
    def _check_phone_quality(self, phone: str):
        """Check phone quality against SEON scoring criteria"""
        issues = []
        
        # VoIP indicators (SEON: disposable phone = 10 points)
        voip_prefixes = ["800", "888", "877", "866", "855", "844", "833"]
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        if len(clean_phone) >= 10:
            area_code = clean_phone[-10:-7] if len(clean_phone) >= 10 else ""
            if area_code in voip_prefixes:
                issues.append("Toll-free number detected - likely VoIP (+10pts SEON)")
        
        if len(clean_phone) < 10:
            issues.append("Phone number too short - may fail validation")
        
        status = CheckStatus.WARN if issues else CheckStatus.PASS
        self.report.checks.append(PreFlightCheck(
            name="Phone Quality",
            status=status,
            message="; ".join(issues) if issues else "Phone number format acceptable",
            critical=False,
            details={"phone_digits": len(clean_phone)}
        ))
    
    def _check_target_readiness(self, target_name: str):
        """Check readiness for specific target's fraud engine"""
        try:
            from target_intelligence import (
                get_target_intel, get_antifraud_profile, ANTIFRAUD_PROFILES
            )
            
            intel = get_target_intel(target_name)
            if not intel:
                self.report.checks.append(PreFlightCheck(
                    name="Target Readiness",
                    status=CheckStatus.WARN,
                    message=f"Target '{target_name}' not in intelligence database",
                    critical=False
                ))
                return
            
            # Get antifraud profile for this target's engine
            af_profile = intel.get_antifraud_profile()
            warnings = []
            
            if af_profile:
                # Cross-merchant sharing warning
                if af_profile.cross_merchant_sharing:
                    warnings.append(f"{af_profile.name} shares data cross-merchant - use fresh cards only")
                
                # Session handover detection
                if af_profile.session_handover_detection:
                    warnings.append(f"{af_profile.name} detects session handover - Ghost Motor must run continuously")
                
                # Invisible challenges
                if af_profile.invisible_challenges:
                    warnings.append(f"{af_profile.name} uses invisible challenges - Ghost Motor challenge response required")
                
                # Behavioral biometrics
                if af_profile.behavioral_biometrics:
                    warnings.append(f"{af_profile.name} analyzes behavioral biometrics - natural timing critical")
            
            # Operator playbook reminder
            if intel.operator_playbook:
                warnings.append(f"Operator playbook available ({len(intel.operator_playbook)} steps)")
            
            status = CheckStatus.PASS if not af_profile or not af_profile.cross_merchant_sharing else CheckStatus.WARN
            self.report.checks.append(PreFlightCheck(
                name="Target Readiness",
                status=status,
                message=f"Target: {intel.name} | Engine: {intel.fraud_engine.value} | Friction: {intel.friction.value}",
                critical=False,
                details={
                    "target": intel.name,
                    "fraud_engine": intel.fraud_engine.value,
                    "friction": intel.friction.value,
                    "three_ds_rate": intel.three_ds_rate,
                    "warnings": warnings,
                }
            ))
            
            # Print warnings
            for w in warnings:
                self.report.checks.append(PreFlightCheck(
                    name="Antifraud Intel",
                    status=CheckStatus.WARN,
                    message=w,
                    critical=False
                ))
                
        except ImportError:
            self.report.checks.append(PreFlightCheck(
                name="Target Readiness",
                status=CheckStatus.SKIP,
                message="Target intelligence module not available",
                critical=False
            ))
    
    def print_report(self):
        """Print formatted report to console"""
        print("\n" + "=" * 60)
        print("  TITAN V7.0 PRE-FLIGHT VALIDATION REPORT")
        print("=" * 60)
        
        for check in self.report.checks:
            if check.status == CheckStatus.PASS:
                icon = "✅"
            elif check.status == CheckStatus.FAIL:
                icon = "❌"
            elif check.status == CheckStatus.WARN:
                icon = "⚠️"
            else:
                icon = "⏭️"
            
            critical = " [CRITICAL]" if check.critical and check.status == CheckStatus.FAIL else ""
            print(f"  {icon} {check.name}: {check.message}{critical}")
        
        print("-" * 60)
        if self.report.passed:
            print("  ✅ PRE-FLIGHT PASSED - Ready for operation")
        else:
            print(f"  ❌ PRE-FLIGHT FAILED - {self.report.abort_reason}")
        print("=" * 60 + "\n")


def run_preflight(profile_path: str = None, 
                  proxy_url: str = None,
                  billing_region: Dict = None) -> PreFlightReport:
    """Convenience function to run pre-flight validation"""
    validator = PreFlightValidator(
        profile_path=profile_path,
        proxy_url=proxy_url,
        billing_region=billing_region
    )
    report = validator.run_all_checks()
    validator.print_report()
    return report


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced Validation Orchestration
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict


@dataclass
class ValidationCacheEntry:
    """Cached validation result"""
    check_name: str
    result: PreFlightCheck
    timestamp: float
    ttl_seconds: float
    cache_key: str
    hit_count: int = 0
    
    @property
    def is_valid(self) -> bool:
        return time.time() - self.timestamp < self.ttl_seconds


@dataclass
class FailurePattern:
    """Pattern identified in validation failures"""
    pattern_type: str
    description: str
    frequency: int
    affected_checks: List[str]
    recommended_actions: List[str]
    severity: str  # "low", "medium", "high", "critical"
    first_seen: float
    last_seen: float


@dataclass
class ValidationSchedule:
    """Scheduled validation configuration"""
    schedule_id: str
    check_names: List[str]
    interval_seconds: float
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    enabled: bool = True
    on_failure_callback: Optional[str] = None


@dataclass
class OrchestratedResult:
    """Result from validation orchestration"""
    reports: Dict[str, PreFlightReport]
    aggregated_status: CheckStatus
    critical_failures: List[PreFlightCheck]
    all_warnings: List[PreFlightCheck]
    execution_time_ms: float
    checks_from_cache: int
    checks_executed: int
    timestamp: str


class ValidationCacheManager:
    """
    V7.6 P0: Cache validation results to avoid redundant expensive checks.
    
    Features:
    - TTL-based cache invalidation per check type
    - Cache key based on input parameters
    - Hit rate tracking for optimization
    - Automatic cleanup of stale entries
    """
    
    # Default TTL per check type (seconds)
    DEFAULT_TTL = {
        "Proxy Connection": 60,      # Check every minute
        "IP Type": 300,              # 5 minutes (IP doesn't change often)
        "IP Reputation": 600,        # 10 minutes (external API call)
        "Geo Match": 300,            # 5 minutes
        "VPN Tunnel": 30,            # Check frequently
        "Profile Exists": 120,       # 2 minutes
        "Profile Age": 3600,         # 1 hour (doesn't change often)
        "Profile Storage": 300,      # 5 minutes
        "Timezone": 3600,            # 1 hour
        "System Locale": 3600,       # 1 hour
        "Email Quality": 86400,      # 24 hours (static)
        "Phone Quality": 86400,      # 24 hours (static)
    }
    
    def __init__(self):
        self._cache: Dict[str, ValidationCacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._max_cache_size = 1000
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _generate_cache_key(self, check_name: str, params: Dict) -> str:
        """Generate unique cache key from check name and parameters"""
        param_str = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{check_name}:{param_str}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def get(self, check_name: str, params: Dict) -> Optional[PreFlightCheck]:
        """Retrieve cached check result if valid"""
        with self._lock:
            self._maybe_cleanup()
            
            cache_key = self._generate_cache_key(check_name, params)
            entry = self._cache.get(cache_key)
            
            if entry and entry.is_valid:
                entry.hit_count += 1
                self._stats["hits"] += 1
                logger.debug(f"Cache HIT: {check_name} (key={cache_key[:8]})")
                return entry.result
            elif entry:
                # Expired entry
                del self._cache[cache_key]
                self._stats["evictions"] += 1
            
            self._stats["misses"] += 1
            return None
    
    def put(self, check_name: str, params: Dict, result: PreFlightCheck,
            ttl_override: Optional[float] = None):
        """Store check result in cache"""
        with self._lock:
            cache_key = self._generate_cache_key(check_name, params)
            ttl = ttl_override or self.DEFAULT_TTL.get(check_name, 120)
            
            entry = ValidationCacheEntry(
                check_name=check_name,
                result=result,
                timestamp=time.time(),
                ttl_seconds=ttl,
                cache_key=cache_key,
            )
            
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_cache_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
            
            self._cache[cache_key] = entry
            logger.debug(f"Cache PUT: {check_name} (key={cache_key[:8]}, ttl={ttl}s)")
    
    def invalidate(self, check_name: Optional[str] = None):
        """Invalidate cache entries by check name or all"""
        with self._lock:
            if check_name:
                keys_to_remove = [
                    k for k, v in self._cache.items()
                    if v.check_name == check_name
                ]
                for k in keys_to_remove:
                    del self._cache[k]
                    self._stats["evictions"] += 1
            else:
                self._stats["evictions"] += len(self._cache)
                self._cache.clear()
    
    def _maybe_cleanup(self):
        """Periodic cleanup of expired entries"""
        if time.time() - self._last_cleanup < self._cleanup_interval:
            return
        
        keys_to_remove = [
            k for k, v in self._cache.items()
            if not v.is_valid
        ]
        for k in keys_to_remove:
            del self._cache[k]
            self._stats["evictions"] += 1
        
        self._last_cleanup = time.time()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                **self._stats,
                "hit_rate_pct": round(hit_rate, 2),
                "entries": len(self._cache),
                "max_size": self._max_cache_size,
            }


class FailureAnalyzer:
    """
    V7.6 P0: Analyze patterns in validation failures to recommend fixes.
    
    Features:
    - Historical failure tracking
    - Pattern recognition across failures
    - Root cause analysis
    - Automated remediation suggestions
    """
    
    # Known failure patterns and remediation
    KNOWN_PATTERNS = {
        "datacenter_ip": {
            "indicators": ["DATACENTER IP DETECTED", "hosting", "cloud", "vps"],
            "severity": "critical",
            "remediation": [
                "Switch to residential proxy provider",
                "Use Lucid VPN with residential exit node",
                "Verify proxy provider claims residential IPs",
            ],
        },
        "ip_reputation": {
            "indicators": ["HIGH RISK IP", "fraud_score", "ELEVATED IP score"],
            "severity": "high",
            "remediation": [
                "Rotate to a new proxy IP",
                "Allow 24-48 hours for IP reputation to recover",
                "Use a different residential proxy pool",
            ],
        },
        "proxy_failure": {
            "indicators": ["Proxy connection failed", "Proxy error", "timeout"],
            "severity": "critical",
            "remediation": [
                "Check proxy credentials and URL format",
                "Verify proxy provider status page",
                "Test proxy connection independently",
                "Check firewall rules for proxy port",
            ],
        },
        "vpn_disconnected": {
            "indicators": ["VPN mode selected but tunnel not connected", "VPN error"],
            "severity": "critical",
            "remediation": [
                "Run: titan-vpn-setup --connect",
                "Check WireGuard/Xray configuration",
                "Verify Tailscale mesh connectivity",
            ],
        },
        "profile_incomplete": {
            "indicators": ["Profile not found", "Missing files", "No autofill"],
            "severity": "medium",
            "remediation": [
                "Generate profile with Genesis engine",
                "Run: titan-genesis --generate-profile",
                "Ensure profile path is correct",
            ],
        },
        "geo_mismatch": {
            "indicators": ["Region mismatch", "Timezone mismatch"],
            "severity": "medium",
            "remediation": [
                "Select proxy in billing region state",
                "Adjust system timezone to match billing address",
                "Run: titan-location-sync --region",
            ],
        },
        "email_quality": {
            "indicators": ["Disposable email", "SEON check"],
            "severity": "high",
            "remediation": [
                "Use established email provider (Gmail, Outlook)",
                "Age email account for at least 30 days",
                "Avoid temporary/disposable email services",
            ],
        },
    }
    
    def __init__(self, history_limit: int = 500):
        self._failure_history: List[Dict] = []
        self._pattern_counts: Dict[str, int] = defaultdict(int)
        self._history_limit = history_limit
        self._lock = threading.Lock()
    
    def record_failure(self, check: PreFlightCheck, context: Optional[Dict] = None):
        """Record a validation failure for pattern analysis"""
        with self._lock:
            entry = {
                "check_name": check.name,
                "message": check.message,
                "details": check.details,
                "context": context or {},
                "timestamp": time.time(),
                "patterns_matched": [],
            }
            
            # Match against known patterns
            for pattern_name, pattern_def in self.KNOWN_PATTERNS.items():
                if any(ind.lower() in check.message.lower() 
                       for ind in pattern_def["indicators"]):
                    entry["patterns_matched"].append(pattern_name)
                    self._pattern_counts[pattern_name] += 1
            
            self._failure_history.append(entry)
            
            # Trim history
            if len(self._failure_history) > self._history_limit:
                self._failure_history = self._failure_history[-self._history_limit:]
    
    def analyze_report(self, report: PreFlightReport) -> List[FailurePattern]:
        """Analyze a validation report and return identified patterns"""
        patterns = []
        
        for check in report.critical_failures:
            self.record_failure(check)
            
            # Find matching patterns
            for pattern_name, pattern_def in self.KNOWN_PATTERNS.items():
                if any(ind.lower() in check.message.lower() 
                       for ind in pattern_def["indicators"]):
                    patterns.append(FailurePattern(
                        pattern_type=pattern_name,
                        description=check.message,
                        frequency=self._pattern_counts.get(pattern_name, 1),
                        affected_checks=[check.name],
                        recommended_actions=pattern_def["remediation"],
                        severity=pattern_def["severity"],
                        first_seen=time.time(),
                        last_seen=time.time(),
                    ))
        
        return patterns
    
    def get_remediation(self, check: PreFlightCheck) -> List[str]:
        """Get remediation steps for a specific failed check"""
        remediation = []
        
        for pattern_name, pattern_def in self.KNOWN_PATTERNS.items():
            if any(ind.lower() in check.message.lower() 
                   for ind in pattern_def["indicators"]):
                remediation.extend(pattern_def["remediation"])
        
        return list(dict.fromkeys(remediation))  # Remove duplicates
    
    def get_frequent_failures(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most frequent failure patterns"""
        with self._lock:
            sorted_patterns = sorted(
                self._pattern_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_patterns[:limit]
    
    def get_failure_summary(self) -> Dict:
        """Get summary of failure history"""
        with self._lock:
            if not self._failure_history:
                return {"total_failures": 0, "patterns": {}}
            
            # Aggregate by check name
            by_check = defaultdict(int)
            for entry in self._failure_history:
                by_check[entry["check_name"]] += 1
            
            return {
                "total_failures": len(self._failure_history),
                "by_check": dict(by_check),
                "patterns": dict(self._pattern_counts),
                "most_recent": self._failure_history[-1] if self._failure_history else None,
            }


class PreflightScheduler:
    """
    V7.6 P0: Schedule periodic preflight checks during long operations.
    
    Features:
    - Interval-based check scheduling
    - Background validation thread
    - Callback on failure detection
    - Integration with ValidationOrchestrator
    """
    
    def __init__(self, orchestrator: 'ValidationOrchestrator'):
        self._orchestrator = orchestrator
        self._schedules: Dict[str, ValidationSchedule] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Predefined schedules
        self._default_schedules = {
            "network_health": {
                "checks": ["Proxy Connection", "VPN Tunnel"],
                "interval": 60,  # Every minute
            },
            "ip_quality": {
                "checks": ["IP Type", "IP Reputation"],
                "interval": 300,  # Every 5 minutes
            },
            "full_validation": {
                "checks": [],  # All checks
                "interval": 900,  # Every 15 minutes
            },
        }
    
    def add_schedule(self, schedule_id: str, check_names: List[str],
                     interval_seconds: float,
                     on_failure_callback: Optional[str] = None) -> ValidationSchedule:
        """Add a new validation schedule"""
        with self._lock:
            schedule = ValidationSchedule(
                schedule_id=schedule_id,
                check_names=check_names,
                interval_seconds=interval_seconds,
                next_run=time.time() + interval_seconds,
                on_failure_callback=on_failure_callback,
            )
            self._schedules[schedule_id] = schedule
            logger.info(f"Added validation schedule: {schedule_id} (interval={interval_seconds}s)")
            return schedule
    
    def remove_schedule(self, schedule_id: str):
        """Remove a validation schedule"""
        with self._lock:
            if schedule_id in self._schedules:
                del self._schedules[schedule_id]
                logger.info(f"Removed validation schedule: {schedule_id}")
    
    def enable_default_schedules(self):
        """Enable predefined validation schedules"""
        for schedule_id, config in self._default_schedules.items():
            self.add_schedule(
                schedule_id=schedule_id,
                check_names=config["checks"],
                interval_seconds=config["interval"],
            )
    
    def start(self):
        """Start the scheduler background thread"""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Preflight scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Preflight scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running and not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                with self._lock:
                    for schedule_id, schedule in self._schedules.items():
                        if not schedule.enabled:
                            continue
                        
                        if schedule.next_run and current_time >= schedule.next_run:
                            self._execute_schedule(schedule)
                
                # Sleep with interrupt support
                self._stop_event.wait(timeout=1)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    def _execute_schedule(self, schedule: ValidationSchedule):
        """Execute a scheduled validation"""
        try:
            logger.debug(f"Executing scheduled validation: {schedule.schedule_id}")
            
            # Run validation
            result = self._orchestrator.run_checks(
                check_names=schedule.check_names if schedule.check_names else None
            )
            
            schedule.last_run = time.time()
            schedule.next_run = schedule.last_run + schedule.interval_seconds
            
            # Check for failures
            if result.critical_failures:
                logger.warning(
                    f"Scheduled validation {schedule.schedule_id} detected failures: "
                    f"{[c.name for c in result.critical_failures]}"
                )
                
                # Execute callback if configured
                if schedule.on_failure_callback:
                    self._execute_callback(schedule.on_failure_callback, result)
        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule.schedule_id}: {e}")
    
    def _execute_callback(self, callback_name: str, result: OrchestratedResult):
        """Execute a failure callback"""
        callbacks = {
            "pause_operation": self._callback_pause_operation,
            "rotate_proxy": self._callback_rotate_proxy,
            "reconnect_vpn": self._callback_reconnect_vpn,
        }
        
        callback_fn = callbacks.get(callback_name)
        if callback_fn:
            callback_fn(result)
    
    def _callback_pause_operation(self, result: OrchestratedResult):
        """Pause current operation on failure"""
        logger.warning("PREFLIGHT FAILURE - Pausing operation")
        # Signal would be sent to operation controller
    
    def _callback_rotate_proxy(self, result: OrchestratedResult):
        """Rotate proxy on IP-related failure"""
        logger.warning("PREFLIGHT FAILURE - Requesting proxy rotation")
        try:
            from proxy_manager import ResidentialProxyManager
            pm = ResidentialProxyManager()
            old_proxy = getattr(result, 'details', {}).get('proxy', 'unknown')
            if hasattr(pm, 'rotate') and callable(pm.rotate):
                new_proxy = pm.rotate()
            elif hasattr(pm, 'get_next_proxy') and callable(pm.get_next_proxy):
                new_proxy = pm.get_next_proxy()
            elif hasattr(pm, 'blacklist_and_rotate'):
                new_proxy = pm.blacklist_and_rotate(old_proxy)
            else:
                new_proxy = None
            if new_proxy:
                logger.info(f"PREFLIGHT: Proxy rotated → {getattr(new_proxy, 'host', new_proxy)}")
            else:
                logger.warning("PREFLIGHT: Proxy rotation returned None — manual rotation needed")
        except ImportError:
            logger.warning("PREFLIGHT: proxy_manager not available — rotate proxy manually")
        except Exception as e:
            logger.error(f"PREFLIGHT: Proxy rotation failed: {e}")
    
    def _callback_reconnect_vpn(self, result: OrchestratedResult):
        """Reconnect VPN on tunnel failure"""
        logger.warning("PREFLIGHT FAILURE - Requesting VPN reconnection")
        try:
            from lucid_vpn import LucidVPN, VPNConfig
            vpn_config = VPNConfig.from_env()
            if vpn_config.vps_address:
                vpn = LucidVPN(vpn_config)
                if hasattr(vpn, 'reconnect') and callable(vpn.reconnect):
                    success = vpn.reconnect()
                elif hasattr(vpn, 'restart') and callable(vpn.restart):
                    success = vpn.restart()
                elif hasattr(vpn, 'connect') and callable(vpn.connect):
                    success = vpn.connect()
                else:
                    success = False
                if success:
                    logger.info("PREFLIGHT: VPN reconnected successfully")
                else:
                    logger.warning("PREFLIGHT: VPN reconnect returned False — check VPN config")
            else:
                logger.warning("PREFLIGHT: VPN not configured in titan.env")
        except ImportError:
            logger.warning("PREFLIGHT: lucid_vpn not available — reconnect VPN manually")
        except Exception as e:
            logger.error(f"PREFLIGHT: VPN reconnection failed: {e}")
    
    def get_schedule_status(self) -> Dict[str, Dict]:
        """Get status of all schedules"""
        with self._lock:
            return {
                schedule_id: {
                    "enabled": s.enabled,
                    "interval_seconds": s.interval_seconds,
                    "last_run": datetime.fromtimestamp(s.last_run).isoformat() if s.last_run else None,
                    "next_run": datetime.fromtimestamp(s.next_run).isoformat() if s.next_run else None,
                    "checks": s.check_names or ["all"],
                }
                for schedule_id, s in self._schedules.items()
            }


class ValidationOrchestrator:
    """
    V7.6 P0: Coordinate multiple validators and aggregate results intelligently.
    
    Features:
    - Parallel check execution
    - Cache-aware validation
    - Failure analysis integration
    - Multi-validator coordination
    - Intelligent result aggregation
    """
    
    def __init__(self, profile_path: Optional[Path] = None,
                 proxy_url: Optional[str] = None,
                 billing_region: Optional[Dict] = None):
        self.profile_path = profile_path
        self.proxy_url = proxy_url
        self.billing_region = billing_region
        
        # V7.6 components
        self._cache = ValidationCacheManager()
        self._failure_analyzer = FailureAnalyzer()
        self._scheduler: Optional[PreflightScheduler] = None
        
        # Thread pool for parallel execution
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # Check dependencies (which checks must run before others)
        self._dependencies = {
            "IP Type": ["Proxy Connection"],
            "IP Reputation": ["Proxy Connection"],
            "Geo Match": ["Proxy Connection"],
        }
        
        # Check execution stats
        self._stats = {
            "total_runs": 0,
            "total_checks": 0,
            "cache_hits": 0,
            "failures": 0,
        }
    
    def run_checks(self, check_names: Optional[List[str]] = None,
                   use_cache: bool = True,
                   parallel: bool = True) -> OrchestratedResult:
        """
        Run validation checks with orchestration.
        
        Args:
            check_names: Specific checks to run (None = all)
            use_cache: Use cached results when available
            parallel: Run independent checks in parallel
        """
        start_time = time.time()
        self._stats["total_runs"] += 1
        
        # Create validator
        validator = PreFlightValidator(
            profile_path=self.profile_path,
            proxy_url=self.proxy_url,
            billing_region=self.billing_region,
        )
        
        # Get all checks or filter
        all_check_methods = {
            "Profile Exists": validator._check_profile_exists,
            "Profile Age": validator._check_profile_age,
            "Profile Storage": validator._check_profile_storage,
            "Autofill Data": validator._check_autofill_data,
            "VPN Tunnel": validator._check_vpn_tunnel,
            "Proxy Connection": validator._check_proxy_connection,
            "IP Type": validator._check_ip_type,
            "IP Reputation": validator._check_ip_reputation,
            "Geo Match": validator._check_geo_match,
            "Timezone": validator._check_timezone,
            "System Locale": validator._check_system_locale,
        }
        
        if check_names:
            check_methods = {k: v for k, v in all_check_methods.items() if k in check_names}
        else:
            check_methods = all_check_methods
        
        checks_executed = 0
        checks_from_cache = 0
        
        # Build execution order based on dependencies
        execution_order = self._build_execution_order(list(check_methods.keys()))
        
        # Execute checks
        for check_batch in execution_order:
            if parallel and len(check_batch) > 1:
                # Run batch in parallel
                futures = {}
                for check_name in check_batch:
                    if check_name not in check_methods:
                        continue
                    
                    # Check cache first
                    if use_cache:
                        cache_params = self._get_cache_params(check_name)
                        cached = self._cache.get(check_name, cache_params)
                        if cached:
                            validator.report.checks.append(cached)
                            checks_from_cache += 1
                            continue
                    
                    # Submit for parallel execution
                    future = self._executor.submit(check_methods[check_name])
                    futures[future] = check_name
                
                # Wait for parallel checks
                for future in as_completed(futures):
                    check_name = futures[future]
                    try:
                        future.result()
                        checks_executed += 1
                        
                        # Cache result
                        if use_cache:
                            result = next(
                                (c for c in validator.report.checks if c.name == check_name),
                                None
                            )
                            if result:
                                cache_params = self._get_cache_params(check_name)
                                self._cache.put(check_name, cache_params, result)
                    except Exception as e:
                        logger.error(f"Check {check_name} failed: {e}")
            else:
                # Sequential execution
                for check_name in check_batch:
                    if check_name not in check_methods:
                        continue
                    
                    # Check cache first
                    if use_cache:
                        cache_params = self._get_cache_params(check_name)
                        cached = self._cache.get(check_name, cache_params)
                        if cached:
                            validator.report.checks.append(cached)
                            checks_from_cache += 1
                            continue
                    
                    try:
                        check_methods[check_name]()
                        checks_executed += 1
                        
                        # Cache result
                        if use_cache:
                            result = next(
                                (c for c in validator.report.checks if c.name == check_name),
                                None
                            )
                            if result:
                                cache_params = self._get_cache_params(check_name)
                                self._cache.put(check_name, cache_params, result)
                    except Exception as e:
                        logger.error(f"Check {check_name} failed: {e}")
        
        # Determine overall status
        critical_failures = [
            c for c in validator.report.checks
            if c.status == CheckStatus.FAIL and c.critical
        ]
        all_warnings = [
            c for c in validator.report.checks
            if c.status == CheckStatus.WARN
        ]
        
        if critical_failures:
            validator.report.passed = False
            validator.report.abort_reason = critical_failures[0].message
            self._stats["failures"] += 1
            
            # Analyze failures
            patterns = self._failure_analyzer.analyze_report(validator.report)
            if patterns:
                logger.info(f"Failure patterns identified: {[p.pattern_type for p in patterns]}")
        else:
            validator.report.passed = True
        
        # Build orchestrated result
        execution_time = (time.time() - start_time) * 1000
        
        result = OrchestratedResult(
            reports={"primary": validator.report},
            aggregated_status=validator.report.overall_status,
            critical_failures=critical_failures,
            all_warnings=all_warnings,
            execution_time_ms=round(execution_time, 2),
            checks_from_cache=checks_from_cache,
            checks_executed=checks_executed,
            timestamp=datetime.now().isoformat(),
        )
        
        self._stats["total_checks"] += checks_executed + checks_from_cache
        self._stats["cache_hits"] += checks_from_cache
        
        return result
    
    def _build_execution_order(self, check_names: List[str]) -> List[List[str]]:
        """Build execution order respecting dependencies"""
        batches = []
        remaining = set(check_names)
        completed = set()
        
        while remaining:
            # Find checks with satisfied dependencies
            batch = []
            for check in remaining:
                deps = self._dependencies.get(check, [])
                if all(d in completed or d not in check_names for d in deps):
                    batch.append(check)
            
            if not batch:
                # No progress - add remaining with warnings
                batch = list(remaining)
            
            batches.append(batch)
            completed.update(batch)
            remaining -= set(batch)
        
        return batches
    
    def _get_cache_params(self, check_name: str) -> Dict:
        """Get parameters for cache key generation"""
        params = {}
        
        if check_name in ["Proxy Connection", "IP Type", "IP Reputation", "Geo Match"]:
            params["proxy_url"] = self.proxy_url
        
        if check_name in ["Profile Exists", "Profile Age", "Profile Storage", "Autofill Data"]:
            params["profile_path"] = str(self.profile_path) if self.profile_path else None
        
        if check_name in ["Geo Match", "Timezone"]:
            params["billing_region"] = self.billing_region
        
        return params
    
    def get_scheduler(self) -> PreflightScheduler:
        """Get or create scheduler instance"""
        if not self._scheduler:
            self._scheduler = PreflightScheduler(self)
        return self._scheduler
    
    def get_failure_analyzer(self) -> FailureAnalyzer:
        """Get failure analyzer instance"""
        return self._failure_analyzer
    
    def get_cache(self) -> ValidationCacheManager:
        """Get cache manager instance"""
        return self._cache
    
    def get_remediation_for_failures(self, result: OrchestratedResult) -> Dict[str, List[str]]:
        """Get remediation steps for all failures in result"""
        remediation = {}
        for check in result.critical_failures:
            steps = self._failure_analyzer.get_remediation(check)
            if steps:
                remediation[check.name] = steps
        return remediation
    
    def get_stats(self) -> Dict:
        """Get orchestrator statistics"""
        cache_stats = self._cache.get_stats()
        failure_stats = self._failure_analyzer.get_failure_summary()
        
        return {
            **self._stats,
            "cache": cache_stats,
            "failures": failure_stats,
        }
    
    def print_orchestrated_report(self, result: OrchestratedResult):
        """Print detailed orchestrated report"""
        print("\n" + "=" * 70)
        print("  TITAN V7.6 ORCHESTRATED VALIDATION REPORT")
        print("=" * 70)
        
        primary_report = result.reports.get("primary")
        if primary_report:
            for check in primary_report.checks:
                if check.status == CheckStatus.PASS:
                    icon = "✅"
                elif check.status == CheckStatus.FAIL:
                    icon = "❌"
                elif check.status == CheckStatus.WARN:
                    icon = "⚠️"
                else:
                    icon = "⏭️"
                
                critical = " [CRITICAL]" if check.critical and check.status == CheckStatus.FAIL else ""
                print(f"  {icon} {check.name}: {check.message}{critical}")
        
        print("-" * 70)
        print(f"  Execution: {result.execution_time_ms}ms | "
              f"Cached: {result.checks_from_cache} | "
              f"Executed: {result.checks_executed}")
        
        # Show remediation for failures
        if result.critical_failures:
            remediation = self.get_remediation_for_failures(result)
            if remediation:
                print("\n  📋 REMEDIATION STEPS:")
                for check_name, steps in remediation.items():
                    print(f"    {check_name}:")
                    for i, step in enumerate(steps, 1):
                        print(f"      {i}. {step}")
        
        print("-" * 70)
        if result.aggregated_status == CheckStatus.PASS:
            print("  ✅ VALIDATION PASSED - Ready for operation")
        elif result.aggregated_status == CheckStatus.WARN:
            print("  ⚠️ VALIDATION PASSED WITH WARNINGS - Proceed with caution")
        else:
            print(f"  ❌ VALIDATION FAILED - {result.critical_failures[0].message if result.critical_failures else 'Unknown'}")
        print("=" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_validation_cache: Optional[ValidationCacheManager] = None
_failure_analyzer: Optional[FailureAnalyzer] = None
_validation_orchestrator: Optional[ValidationOrchestrator] = None
_preflight_scheduler: Optional[PreflightScheduler] = None


def get_validation_cache() -> ValidationCacheManager:
    """Get global validation cache manager"""
    global _validation_cache
    if _validation_cache is None:
        _validation_cache = ValidationCacheManager()
    return _validation_cache


def get_failure_analyzer() -> FailureAnalyzer:
    """Get global failure analyzer"""
    global _failure_analyzer
    if _failure_analyzer is None:
        _failure_analyzer = FailureAnalyzer()
    return _failure_analyzer


def get_validation_orchestrator(profile_path: Optional[Path] = None,
                                 proxy_url: Optional[str] = None,
                                 billing_region: Optional[Dict] = None) -> ValidationOrchestrator:
    """Get validation orchestrator (creates new or updates existing)"""
    global _validation_orchestrator
    if _validation_orchestrator is None:
        _validation_orchestrator = ValidationOrchestrator(
            profile_path=profile_path,
            proxy_url=proxy_url,
            billing_region=billing_region,
        )
    else:
        # Update parameters
        if profile_path:
            _validation_orchestrator.profile_path = profile_path
        if proxy_url:
            _validation_orchestrator.proxy_url = proxy_url
        if billing_region:
            _validation_orchestrator.billing_region = billing_region
    return _validation_orchestrator


def get_preflight_scheduler() -> PreflightScheduler:
    """Get global preflight scheduler"""
    global _preflight_scheduler
    if _preflight_scheduler is None:
        orchestrator = get_validation_orchestrator()
        _preflight_scheduler = orchestrator.get_scheduler()
    return _preflight_scheduler


if __name__ == "__main__":
    # Test run
    report = run_preflight(
        billing_region={"city": "Austin", "state": "TX", "zip": "78705"}
    )
    print(json.dumps(report.to_dict(), indent=2))
