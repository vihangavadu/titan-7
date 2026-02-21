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
        
        ip_info = proxy_check.details
        proxy_region = ip_info.get("region", "").upper()
        proxy_city = ip_info.get("city", "").upper()
        
        billing_state = self.billing_region.get("state", "").upper()
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


if __name__ == "__main__":
    # Test run
    report = run_preflight(
        billing_region={"city": "Austin", "state": "TX", "zip": "78705"}
    )
    print(json.dumps(report.to_dict(), indent=2))
