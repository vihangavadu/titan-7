#!/usr/bin/env python3
"""
TITAN V8.1 Detection System Emulators

Emulates real-world fraud detection systems:
- Fingerprint detection (Canvas, WebGL, Audio, Fonts)
- Behavioral analysis (Mouse, Keyboard, Navigation)
- Network analysis (IP reputation, TLS fingerprint, TCP/IP)
- Device detection (Hardware, Screen, Timezone)
- Velocity tracking (Transaction frequency, Amount patterns)
"""

import hashlib
import json
import math
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskSignal:
    """Individual risk signal from detection"""
    name: str
    category: str
    severity: RiskLevel
    score: float
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "severity": self.severity.value,
            "score": self.score,
            "description": self.description,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }


@dataclass
class DetectionResult:
    """Result from detection system"""
    passed: bool
    risk_score: float
    risk_level: RiskLevel
    signals: List[RiskSignal] = field(default_factory=list)
    detector_name: str = ""
    detection_time_ms: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "signals": [s.to_dict() for s in self.signals],
            "detector_name": self.detector_name,
            "detection_time_ms": self.detection_time_ms,
            "timestamp": self.timestamp,
        }
    
    def get_failure_reasons(self) -> List[str]:
        """Get list of failure reasons"""
        return [s.description for s in self.signals if s.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]]


class DetectionEmulator(ABC):
    """Base class for detection system emulators"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.name = "base"
        self.threshold = self.config.get("threshold", 70)
    
    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> DetectionResult:
        """Analyze data and return detection result"""
        pass
    
    def _calculate_risk_level(self, score: float) -> RiskLevel:
        """Calculate risk level from score"""
        if score < 30:
            return RiskLevel.LOW
        elif score < 60:
            return RiskLevel.MEDIUM
        elif score < 85:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


class FingerprintDetector(DetectionEmulator):
    """
    Browser Fingerprint Detection Emulator
    
    Detects:
    - Canvas fingerprint anomalies
    - WebGL fingerprint inconsistencies
    - Audio fingerprint manipulation
    - Font enumeration patterns
    - Screen/viewport anomalies
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "fingerprint_detector"
        
        # Known good fingerprint patterns
        self.known_canvas_hashes: Set[str] = set()
        self.known_webgl_vendors = {
            "Google Inc. (NVIDIA)",
            "Google Inc. (AMD)",
            "Google Inc. (Intel)",
            "Apple Inc.",
            "Intel Inc.",
            "NVIDIA Corporation",
            "ATI Technologies Inc.",
        }
        
        self.known_renderers = {
            "ANGLE",
            "GeForce",
            "Radeon",
            "Intel",
            "Apple",
            "Mali",
            "Adreno",
        }
        
        # Suspicious patterns
        self.headless_indicators = [
            "HeadlessChrome",
            "PhantomJS",
            "Selenium",
            "WebDriver",
            "puppeteer",
        ]
        
        self.automation_indicators = [
            "webdriver",
            "__selenium",
            "__webdriver",
            "_phantom",
            "callPhantom",
            "_Selenium",
        ]
    
    def analyze(self, data: Dict[str, Any]) -> DetectionResult:
        start_time = time.time()
        signals = []
        total_score = 0.0
        
        # Canvas fingerprint analysis
        canvas_score, canvas_signals = self._analyze_canvas(data.get("canvas", {}))
        total_score += canvas_score
        signals.extend(canvas_signals)
        
        # WebGL fingerprint analysis
        webgl_score, webgl_signals = self._analyze_webgl(data.get("webgl", {}))
        total_score += webgl_score
        signals.extend(webgl_signals)
        
        # Audio fingerprint analysis
        audio_score, audio_signals = self._analyze_audio(data.get("audio", {}))
        total_score += audio_score
        signals.extend(audio_signals)
        
        # Screen/viewport analysis
        screen_score, screen_signals = self._analyze_screen(data.get("screen", {}))
        total_score += screen_score
        signals.extend(screen_signals)
        
        # User agent analysis
        ua_score, ua_signals = self._analyze_user_agent(data.get("user_agent", ""))
        total_score += ua_score
        signals.extend(ua_signals)
        
        # Automation detection
        auto_score, auto_signals = self._detect_automation(data)
        total_score += auto_score
        signals.extend(auto_signals)
        
        # Normalize score
        total_score = min(100, total_score)
        risk_level = self._calculate_risk_level(total_score)
        
        return DetectionResult(
            passed=total_score < self.threshold,
            risk_score=total_score,
            risk_level=risk_level,
            signals=signals,
            detector_name=self.name,
            detection_time_ms=(time.time() - start_time) * 1000,
        )
    
    def _analyze_canvas(self, canvas_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        canvas_hash = canvas_data.get("hash", "")
        
        if not canvas_hash:
            score += 30
            signals.append(RiskSignal(
                name="missing_canvas",
                category="fingerprint",
                severity=RiskLevel.HIGH,
                score=30,
                description="Canvas fingerprint is missing or blocked",
                evidence={"canvas_hash": None},
                remediation="Enable canvas fingerprint with deterministic noise injection",
            ))
        elif len(canvas_hash) < 10:
            score += 25
            signals.append(RiskSignal(
                name="invalid_canvas_hash",
                category="fingerprint",
                severity=RiskLevel.HIGH,
                score=25,
                description="Canvas hash appears invalid or too short",
                evidence={"canvas_hash": canvas_hash},
                remediation="Generate proper canvas fingerprint using FingerprintInjector",
            ))
        
        # Check for known spoofing patterns
        if canvas_data.get("is_blocked"):
            score += 20
            signals.append(RiskSignal(
                name="canvas_blocked",
                category="fingerprint",
                severity=RiskLevel.MEDIUM,
                score=20,
                description="Canvas API appears to be blocked",
                remediation="Use Camoufox with canvas noise instead of blocking",
            ))
        
        return score, signals
    
    def _analyze_webgl(self, webgl_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        vendor = webgl_data.get("vendor", "")
        renderer = webgl_data.get("renderer", "")
        
        if not vendor or not renderer:
            score += 25
            signals.append(RiskSignal(
                name="missing_webgl",
                category="fingerprint",
                severity=RiskLevel.HIGH,
                score=25,
                description="WebGL vendor/renderer information missing",
                evidence={"vendor": vendor, "renderer": renderer},
                remediation="Configure WebGL spoofing with realistic vendor/renderer",
            ))
        else:
            # Check for known vendors
            vendor_known = any(v in vendor for v in self.known_webgl_vendors)
            renderer_known = any(r in renderer for r in self.known_renderers)
            
            if not vendor_known:
                score += 15
                signals.append(RiskSignal(
                    name="unknown_webgl_vendor",
                    category="fingerprint",
                    severity=RiskLevel.MEDIUM,
                    score=15,
                    description=f"Unknown WebGL vendor: {vendor}",
                    evidence={"vendor": vendor},
                    remediation="Use a known GPU vendor string",
                ))
            
            if not renderer_known:
                score += 15
                signals.append(RiskSignal(
                    name="unknown_webgl_renderer",
                    category="fingerprint",
                    severity=RiskLevel.MEDIUM,
                    score=15,
                    description=f"Unknown WebGL renderer: {renderer}",
                    evidence={"renderer": renderer},
                    remediation="Use a known GPU renderer string",
                ))
            
            # Check for VM indicators
            vm_indicators = ["llvmpipe", "SwiftShader", "VirtualBox", "VMware"]
            for indicator in vm_indicators:
                if indicator.lower() in renderer.lower():
                    score += 35
                    signals.append(RiskSignal(
                        name="vm_detected",
                        category="fingerprint",
                        severity=RiskLevel.CRITICAL,
                        score=35,
                        description=f"Virtual machine detected in WebGL: {indicator}",
                        evidence={"renderer": renderer, "indicator": indicator},
                        remediation="Use hardware GPU passthrough or realistic GPU spoofing",
                    ))
                    break
        
        return score, signals
    
    def _analyze_audio(self, audio_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        audio_hash = audio_data.get("hash", "")
        
        if not audio_hash:
            score += 15
            signals.append(RiskSignal(
                name="missing_audio",
                category="fingerprint",
                severity=RiskLevel.MEDIUM,
                score=15,
                description="Audio fingerprint is missing",
                remediation="Enable audio fingerprint with noise injection",
            ))
        
        return score, signals
    
    def _analyze_screen(self, screen_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        width = screen_data.get("width", 0)
        height = screen_data.get("height", 0)
        color_depth = screen_data.get("color_depth", 0)
        
        # Check for unusual resolutions
        common_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (2560, 1440), (3840, 2160), (1680, 1050),
        ]
        
        if width and height:
            if (width, height) not in common_resolutions:
                # Check if it's close to a common resolution
                is_close = any(
                    abs(width - w) < 50 and abs(height - h) < 50
                    for w, h in common_resolutions
                )
                if not is_close:
                    score += 10
                    signals.append(RiskSignal(
                        name="unusual_resolution",
                        category="fingerprint",
                        severity=RiskLevel.LOW,
                        score=10,
                        description=f"Unusual screen resolution: {width}x{height}",
                        evidence={"width": width, "height": height},
                        remediation="Use a common screen resolution",
                    ))
        else:
            score += 20
            signals.append(RiskSignal(
                name="missing_screen_info",
                category="fingerprint",
                severity=RiskLevel.MEDIUM,
                score=20,
                description="Screen information is missing",
                remediation="Provide screen resolution data",
            ))
        
        return score, signals
    
    def _analyze_user_agent(self, user_agent: str) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        if not user_agent:
            score += 25
            signals.append(RiskSignal(
                name="missing_user_agent",
                category="fingerprint",
                severity=RiskLevel.HIGH,
                score=25,
                description="User agent is missing",
                remediation="Provide a valid user agent string",
            ))
            return score, signals
        
        # Check for headless indicators
        for indicator in self.headless_indicators:
            if indicator.lower() in user_agent.lower():
                score += 40
                signals.append(RiskSignal(
                    name="headless_browser",
                    category="fingerprint",
                    severity=RiskLevel.CRITICAL,
                    score=40,
                    description=f"Headless browser detected: {indicator}",
                    evidence={"user_agent": user_agent, "indicator": indicator},
                    remediation="Use Camoufox or a non-headless browser",
                ))
                break
        
        return score, signals
    
    def _detect_automation(self, data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        # Check for automation properties
        automation_props = data.get("automation_properties", {})
        
        if automation_props.get("webdriver"):
            score += 50
            signals.append(RiskSignal(
                name="webdriver_detected",
                category="automation",
                severity=RiskLevel.CRITICAL,
                score=50,
                description="WebDriver property detected - automation tool in use",
                remediation="Use Camoufox which removes WebDriver indicators",
            ))
        
        if automation_props.get("selenium"):
            score += 45
            signals.append(RiskSignal(
                name="selenium_detected",
                category="automation",
                severity=RiskLevel.CRITICAL,
                score=45,
                description="Selenium automation detected",
                remediation="Use manual operation with titan-browser",
            ))
        
        return score, signals


class BehavioralDetector(DetectionEmulator):
    """
    Behavioral Analysis Detection Emulator
    
    Detects:
    - Mouse movement patterns (entropy, velocity, acceleration)
    - Keyboard patterns (timing, rhythm)
    - Navigation patterns (referrer chain, page flow)
    - Timing anomalies (too fast, too consistent)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "behavioral_detector"
        
        # Thresholds
        self.min_mouse_entropy = 0.3
        self.min_form_fill_time = 5.0  # seconds
        self.min_page_time = 10.0  # seconds
        self.min_keystroke_variance = 0.05  # seconds
    
    def analyze(self, data: Dict[str, Any]) -> DetectionResult:
        start_time = time.time()
        signals = []
        total_score = 0.0
        
        # Mouse analysis
        mouse_score, mouse_signals = self._analyze_mouse(data.get("mouse", {}))
        total_score += mouse_score
        signals.extend(mouse_signals)
        
        # Keyboard analysis
        keyboard_score, keyboard_signals = self._analyze_keyboard(data.get("keyboard", {}))
        total_score += keyboard_score
        signals.extend(keyboard_signals)
        
        # Navigation analysis
        nav_score, nav_signals = self._analyze_navigation(data.get("navigation", {}))
        total_score += nav_score
        signals.extend(nav_signals)
        
        # Timing analysis
        timing_score, timing_signals = self._analyze_timing(data.get("timing", {}))
        total_score += timing_score
        signals.extend(timing_signals)
        
        total_score = min(100, total_score)
        risk_level = self._calculate_risk_level(total_score)
        
        return DetectionResult(
            passed=total_score < self.threshold,
            risk_score=total_score,
            risk_level=risk_level,
            signals=signals,
            detector_name=self.name,
            detection_time_ms=(time.time() - start_time) * 1000,
        )
    
    def _analyze_mouse(self, mouse_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        entropy = mouse_data.get("entropy", 0)
        movements = mouse_data.get("movements", [])
        
        if entropy < self.min_mouse_entropy:
            score += 35
            signals.append(RiskSignal(
                name="low_mouse_entropy",
                category="behavioral",
                severity=RiskLevel.HIGH,
                score=35,
                description=f"Mouse movement entropy too low: {entropy:.3f} (min: {self.min_mouse_entropy})",
                evidence={"entropy": entropy, "threshold": self.min_mouse_entropy},
                remediation="Use Ghost Motor DMTG for human-like mouse trajectories",
            ))
        
        if not movements:
            score += 25
            signals.append(RiskSignal(
                name="no_mouse_movements",
                category="behavioral",
                severity=RiskLevel.HIGH,
                score=25,
                description="No mouse movements recorded",
                remediation="Ensure mouse movement tracking is enabled",
            ))
        elif len(movements) < 10:
            score += 15
            signals.append(RiskSignal(
                name="few_mouse_movements",
                category="behavioral",
                severity=RiskLevel.MEDIUM,
                score=15,
                description=f"Very few mouse movements: {len(movements)}",
                evidence={"movement_count": len(movements)},
                remediation="Increase natural mouse movement during session",
            ))
        
        # Check for linear movements (bot indicator)
        if movements and len(movements) > 5:
            linearity = self._calculate_linearity(movements)
            if linearity > 0.95:
                score += 30
                signals.append(RiskSignal(
                    name="linear_mouse_movement",
                    category="behavioral",
                    severity=RiskLevel.HIGH,
                    score=30,
                    description="Mouse movements are too linear (bot-like)",
                    evidence={"linearity": linearity},
                    remediation="Use Ghost Motor for curved, natural trajectories",
                ))
        
        return score, signals
    
    def _calculate_linearity(self, movements: List[Dict]) -> float:
        """Calculate how linear the mouse movements are (1.0 = perfectly linear)"""
        if len(movements) < 3:
            return 0.0
        
        # Simplified linearity check
        try:
            total_distance = 0
            direct_distance = 0
            
            for i in range(1, len(movements)):
                dx = movements[i].get("x", 0) - movements[i-1].get("x", 0)
                dy = movements[i].get("y", 0) - movements[i-1].get("y", 0)
                total_distance += math.sqrt(dx*dx + dy*dy)
            
            if movements:
                dx = movements[-1].get("x", 0) - movements[0].get("x", 0)
                dy = movements[-1].get("y", 0) - movements[0].get("y", 0)
                direct_distance = math.sqrt(dx*dx + dy*dy)
            
            if total_distance > 0:
                return direct_distance / total_distance
        except:
            pass
        
        return 0.0
    
    def _analyze_keyboard(self, keyboard_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        keystroke_timings = keyboard_data.get("timings", [])
        
        if keystroke_timings:
            # Check variance
            if len(keystroke_timings) > 2:
                mean_timing = sum(keystroke_timings) / len(keystroke_timings)
                variance = sum((t - mean_timing) ** 2 for t in keystroke_timings) / len(keystroke_timings)
                std_dev = math.sqrt(variance)
                
                if std_dev < self.min_keystroke_variance:
                    score += 25
                    signals.append(RiskSignal(
                        name="uniform_keystrokes",
                        category="behavioral",
                        severity=RiskLevel.HIGH,
                        score=25,
                        description="Keystroke timing is too uniform (bot-like)",
                        evidence={"std_dev": std_dev, "threshold": self.min_keystroke_variance},
                        remediation="Add natural variance to keystroke timing",
                    ))
                
                # Check for impossibly fast typing
                if mean_timing < 0.03:  # 30ms between keystrokes
                    score += 30
                    signals.append(RiskSignal(
                        name="superhuman_typing",
                        category="behavioral",
                        severity=RiskLevel.CRITICAL,
                        score=30,
                        description="Typing speed is impossibly fast",
                        evidence={"mean_timing_ms": mean_timing * 1000},
                        remediation="Slow down form filling to human speed",
                    ))
        
        return score, signals
    
    def _analyze_navigation(self, nav_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        referrer = nav_data.get("referrer", "")
        path = nav_data.get("path", [])
        
        if not referrer:
            score += 20
            signals.append(RiskSignal(
                name="no_referrer",
                category="behavioral",
                severity=RiskLevel.MEDIUM,
                score=20,
                description="No referrer - direct navigation detected",
                remediation="Use ReferrerWarmup to create organic navigation path",
            ))
        
        if not path or len(path) < 2:
            score += 15
            signals.append(RiskSignal(
                name="short_navigation_path",
                category="behavioral",
                severity=RiskLevel.MEDIUM,
                score=15,
                description="Navigation path is too short",
                evidence={"path_length": len(path) if path else 0},
                remediation="Browse naturally through site before checkout",
            ))
        
        return score, signals
    
    def _analyze_timing(self, timing_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        page_time = timing_data.get("page_time_seconds", 0)
        form_fill_time = timing_data.get("form_fill_seconds", 0)
        
        if page_time < self.min_page_time:
            score += 25
            signals.append(RiskSignal(
                name="short_page_time",
                category="behavioral",
                severity=RiskLevel.HIGH,
                score=25,
                description=f"Time on page too short: {page_time:.1f}s (min: {self.min_page_time}s)",
                evidence={"page_time": page_time, "threshold": self.min_page_time},
                remediation="Spend more time on each page (45-90 seconds recommended)",
            ))
        
        if form_fill_time < self.min_form_fill_time:
            score += 30
            signals.append(RiskSignal(
                name="fast_form_fill",
                category="behavioral",
                severity=RiskLevel.HIGH,
                score=30,
                description=f"Form filled too quickly: {form_fill_time:.1f}s (min: {self.min_form_fill_time}s)",
                evidence={"form_fill_time": form_fill_time, "threshold": self.min_form_fill_time},
                remediation="Fill forms at human speed with pauses",
            ))
        
        return score, signals


class NetworkDetector(DetectionEmulator):
    """
    Network Analysis Detection Emulator
    
    Detects:
    - IP reputation issues
    - Datacenter/proxy detection
    - TLS fingerprint anomalies
    - TCP/IP fingerprint mismatches
    - Geographic inconsistencies
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "network_detector"
        
        # Known datacenter IP ranges (simplified)
        self.datacenter_ranges = [
            "10.", "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
            "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
            "172.30.", "172.31.", "192.168.",
        ]
        
        # Known cloud provider ranges (simplified patterns)
        self.cloud_patterns = [
            "amazonaws", "googlecloud", "azure", "digitalocean",
            "linode", "vultr", "ovh", "hetzner",
        ]
    
    def analyze(self, data: Dict[str, Any]) -> DetectionResult:
        start_time = time.time()
        signals = []
        total_score = 0.0
        
        # IP analysis
        ip_score, ip_signals = self._analyze_ip(data.get("ip", {}))
        total_score += ip_score
        signals.extend(ip_signals)
        
        # TLS analysis
        tls_score, tls_signals = self._analyze_tls(data.get("tls", {}))
        total_score += tls_score
        signals.extend(tls_signals)
        
        # TCP/IP analysis
        tcp_score, tcp_signals = self._analyze_tcp(data.get("tcp", {}))
        total_score += tcp_score
        signals.extend(tcp_signals)
        
        # Geographic analysis
        geo_score, geo_signals = self._analyze_geo(data.get("geo", {}))
        total_score += geo_score
        signals.extend(geo_signals)
        
        total_score = min(100, total_score)
        risk_level = self._calculate_risk_level(total_score)
        
        return DetectionResult(
            passed=total_score < self.threshold,
            risk_score=total_score,
            risk_level=risk_level,
            signals=signals,
            detector_name=self.name,
            detection_time_ms=(time.time() - start_time) * 1000,
        )
    
    def _analyze_ip(self, ip_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        ip_address = ip_data.get("address", "")
        ip_type = ip_data.get("type", "unknown")
        reputation = ip_data.get("reputation", 50)
        
        if not ip_address:
            score += 30
            signals.append(RiskSignal(
                name="missing_ip",
                category="network",
                severity=RiskLevel.HIGH,
                score=30,
                description="IP address information missing",
                remediation="Ensure IP is properly detected",
            ))
            return score, signals
        
        # Check for private IP
        for prefix in self.datacenter_ranges:
            if ip_address.startswith(prefix):
                score += 25
                signals.append(RiskSignal(
                    name="private_ip",
                    category="network",
                    severity=RiskLevel.HIGH,
                    score=25,
                    description=f"Private/internal IP detected: {ip_address}",
                    evidence={"ip": ip_address},
                    remediation="Use residential proxy with public IP",
                ))
                break
        
        # Check IP type
        if ip_type == "datacenter":
            score += 40
            signals.append(RiskSignal(
                name="datacenter_ip",
                category="network",
                severity=RiskLevel.CRITICAL,
                score=40,
                description="Datacenter IP detected",
                evidence={"ip": ip_address, "type": ip_type},
                remediation="Use residential proxy instead of datacenter",
            ))
        elif ip_type == "vpn":
            score += 30
            signals.append(RiskSignal(
                name="vpn_ip",
                category="network",
                severity=RiskLevel.HIGH,
                score=30,
                description="VPN IP detected",
                evidence={"ip": ip_address, "type": ip_type},
                remediation="Use residential proxy instead of VPN",
            ))
        
        # Check reputation
        if reputation < 30:
            score += 35
            signals.append(RiskSignal(
                name="low_ip_reputation",
                category="network",
                severity=RiskLevel.CRITICAL,
                score=35,
                description=f"IP has low reputation score: {reputation}",
                evidence={"ip": ip_address, "reputation": reputation},
                remediation="Use a different residential proxy with better reputation",
            ))
        elif reputation < 50:
            score += 20
            signals.append(RiskSignal(
                name="medium_ip_reputation",
                category="network",
                severity=RiskLevel.MEDIUM,
                score=20,
                description=f"IP has medium reputation score: {reputation}",
                evidence={"ip": ip_address, "reputation": reputation},
                remediation="Consider using a proxy with higher reputation",
            ))
        
        return score, signals
    
    def _analyze_tls(self, tls_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        ja3_hash = tls_data.get("ja3", "")
        ja4_hash = tls_data.get("ja4", "")
        
        # Check for known bot JA3 hashes
        bot_ja3_patterns = [
            "e7d705a3286e19ea42f587b344ee6865",  # Python requests
            "3b5074b1b5d032e5620f69f9f700ff0e",  # curl
        ]
        
        if ja3_hash in bot_ja3_patterns:
            score += 45
            signals.append(RiskSignal(
                name="bot_tls_fingerprint",
                category="network",
                severity=RiskLevel.CRITICAL,
                score=45,
                description="TLS fingerprint matches known bot/tool",
                evidence={"ja3": ja3_hash},
                remediation="Use Camoufox which has browser-like TLS fingerprint",
            ))
        
        return score, signals
    
    def _analyze_tcp(self, tcp_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        ttl = tcp_data.get("ttl", 0)
        window_size = tcp_data.get("window_size", 0)
        os_detected = tcp_data.get("os", "")
        
        # Check for OS mismatch
        user_agent_os = tcp_data.get("user_agent_os", "")
        if os_detected and user_agent_os:
            if os_detected.lower() != user_agent_os.lower():
                score += 30
                signals.append(RiskSignal(
                    name="os_mismatch",
                    category="network",
                    severity=RiskLevel.HIGH,
                    score=30,
                    description=f"TCP/IP OS ({os_detected}) doesn't match User-Agent OS ({user_agent_os})",
                    evidence={"tcp_os": os_detected, "ua_os": user_agent_os},
                    remediation="Use Network Shield eBPF to mask TCP/IP fingerprint",
                ))
        
        return score, signals
    
    def _analyze_geo(self, geo_data: Dict) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        ip_country = geo_data.get("ip_country", "")
        ip_city = geo_data.get("ip_city", "")
        timezone = geo_data.get("timezone", "")
        billing_country = geo_data.get("billing_country", "")
        billing_city = geo_data.get("billing_city", "")
        
        # Check country mismatch
        if ip_country and billing_country:
            if ip_country != billing_country:
                score += 35
                signals.append(RiskSignal(
                    name="country_mismatch",
                    category="network",
                    severity=RiskLevel.CRITICAL,
                    score=35,
                    description=f"IP country ({ip_country}) doesn't match billing country ({billing_country})",
                    evidence={"ip_country": ip_country, "billing_country": billing_country},
                    remediation="Use proxy in same country as billing address",
                ))
        
        # Check timezone mismatch
        if timezone and ip_country:
            # Simplified timezone check
            if ip_country == "US" and "Europe" in timezone:
                score += 25
                signals.append(RiskSignal(
                    name="timezone_mismatch",
                    category="network",
                    severity=RiskLevel.HIGH,
                    score=25,
                    description=f"Timezone ({timezone}) doesn't match IP location ({ip_country})",
                    evidence={"timezone": timezone, "ip_country": ip_country},
                    remediation="Configure browser timezone to match proxy location",
                ))
        
        return score, signals


class DeviceDetector(DetectionEmulator):
    """
    Device Detection Emulator
    
    Detects:
    - Hardware inconsistencies
    - Platform mismatches
    - Battery API anomalies
    - Sensor availability
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "device_detector"
    
    def analyze(self, data: Dict[str, Any]) -> DetectionResult:
        start_time = time.time()
        signals = []
        total_score = 0.0
        
        # Platform analysis
        platform = data.get("platform", "")
        user_agent = data.get("user_agent", "")
        
        if platform and user_agent:
            # Check for platform/UA mismatch
            if "Win" in platform and "Mac" in user_agent:
                total_score += 40
                signals.append(RiskSignal(
                    name="platform_ua_mismatch",
                    category="device",
                    severity=RiskLevel.CRITICAL,
                    score=40,
                    description="Platform doesn't match User-Agent",
                    evidence={"platform": platform, "user_agent": user_agent[:100]},
                    remediation="Ensure platform matches user agent",
                ))
        
        # Hardware concurrency check
        hardware_concurrency = data.get("hardware_concurrency", 0)
        if hardware_concurrency == 0:
            total_score += 20
            signals.append(RiskSignal(
                name="missing_hardware_concurrency",
                category="device",
                severity=RiskLevel.MEDIUM,
                score=20,
                description="Hardware concurrency not available",
                remediation="Enable hardware concurrency reporting",
            ))
        elif hardware_concurrency > 128:
            total_score += 15
            signals.append(RiskSignal(
                name="unusual_cpu_count",
                category="device",
                severity=RiskLevel.MEDIUM,
                score=15,
                description=f"Unusual CPU count: {hardware_concurrency}",
                evidence={"hardware_concurrency": hardware_concurrency},
                remediation="Use realistic CPU count (4-16 for desktop)",
            ))
        
        total_score = min(100, total_score)
        risk_level = self._calculate_risk_level(total_score)
        
        return DetectionResult(
            passed=total_score < self.threshold,
            risk_score=total_score,
            risk_level=risk_level,
            signals=signals,
            detector_name=self.name,
            detection_time_ms=(time.time() - start_time) * 1000,
        )


class VelocityDetector(DetectionEmulator):
    """
    Velocity Detection Emulator
    
    Detects:
    - Transaction frequency anomalies
    - Amount patterns
    - Card usage patterns
    - Account velocity
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "velocity_detector"
        
        # Velocity limits
        self.max_transactions_per_hour = config.get("max_tx_per_hour", 5) if config else 5
        self.max_transactions_per_day = config.get("max_tx_per_day", 20) if config else 20
        self.max_amount_per_day = config.get("max_amount_per_day", 5000) if config else 5000
        
        # Tracking
        self.transaction_history: Dict[str, List[Dict]] = {}
    
    def analyze(self, data: Dict[str, Any]) -> DetectionResult:
        start_time = time.time()
        signals = []
        total_score = 0.0
        
        card_bin = data.get("card_bin", "")
        ip_address = data.get("ip_address", "")
        amount = data.get("amount", 0)
        
        # Check card velocity
        card_key = f"card_{card_bin}"
        card_score, card_signals = self._check_velocity(card_key, amount, "card")
        total_score += card_score
        signals.extend(card_signals)
        
        # Check IP velocity
        ip_key = f"ip_{ip_address}"
        ip_score, ip_signals = self._check_velocity(ip_key, amount, "ip")
        total_score += ip_score
        signals.extend(ip_signals)
        
        total_score = min(100, total_score)
        risk_level = self._calculate_risk_level(total_score)
        
        return DetectionResult(
            passed=total_score < self.threshold,
            risk_score=total_score,
            risk_level=risk_level,
            signals=signals,
            detector_name=self.name,
            detection_time_ms=(time.time() - start_time) * 1000,
        )
    
    def _check_velocity(self, key: str, amount: float, entity_type: str) -> Tuple[float, List[RiskSignal]]:
        score = 0.0
        signals = []
        
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        if key not in self.transaction_history:
            self.transaction_history[key] = []
        
        # Clean old entries
        self.transaction_history[key] = [
            tx for tx in self.transaction_history[key]
            if datetime.fromisoformat(tx["timestamp"]) > day_ago
        ]
        
        # Count transactions
        hourly_count = sum(
            1 for tx in self.transaction_history[key]
            if datetime.fromisoformat(tx["timestamp"]) > hour_ago
        )
        daily_count = len(self.transaction_history[key])
        daily_amount = sum(tx["amount"] for tx in self.transaction_history[key])
        
        # Check limits
        if hourly_count >= self.max_transactions_per_hour:
            score += 40
            signals.append(RiskSignal(
                name=f"{entity_type}_hourly_velocity",
                category="velocity",
                severity=RiskLevel.CRITICAL,
                score=40,
                description=f"Hourly transaction limit exceeded for {entity_type}",
                evidence={"count": hourly_count, "limit": self.max_transactions_per_hour},
                remediation=f"Wait before making more transactions with this {entity_type}",
            ))
        
        if daily_count >= self.max_transactions_per_day:
            score += 35
            signals.append(RiskSignal(
                name=f"{entity_type}_daily_velocity",
                category="velocity",
                severity=RiskLevel.HIGH,
                score=35,
                description=f"Daily transaction limit exceeded for {entity_type}",
                evidence={"count": daily_count, "limit": self.max_transactions_per_day},
                remediation=f"Wait 24 hours before using this {entity_type} again",
            ))
        
        if daily_amount + amount > self.max_amount_per_day:
            score += 30
            signals.append(RiskSignal(
                name=f"{entity_type}_amount_velocity",
                category="velocity",
                severity=RiskLevel.HIGH,
                score=30,
                description=f"Daily amount limit exceeded for {entity_type}",
                evidence={"total": daily_amount + amount, "limit": self.max_amount_per_day},
                remediation="Reduce transaction amounts or wait 24 hours",
            ))
        
        # Record this transaction
        self.transaction_history[key].append({
            "timestamp": now.isoformat(),
            "amount": amount,
        })
        
        return score, signals


# Factory function
def create_detector(detector_type: str, config: Optional[Dict] = None) -> DetectionEmulator:
    """Create a detector by type"""
    detectors = {
        "fingerprint": FingerprintDetector,
        "behavioral": BehavioralDetector,
        "network": NetworkDetector,
        "device": DeviceDetector,
        "velocity": VelocityDetector,
    }
    
    if detector_type.lower() not in detectors:
        raise ValueError(f"Unknown detector: {detector_type}. Available: {list(detectors.keys())}")
    
    return detectors[detector_type.lower()](config)


if __name__ == "__main__":
    # Demo usage
    fingerprint = FingerprintDetector()
    
    result = fingerprint.analyze({
        "canvas": {"hash": "abc123def456"},
        "webgl": {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, GeForce RTX 3060)"},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "screen": {"width": 1920, "height": 1080},
    })
    
    print(f"Passed: {result.passed}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Signals: {[s.name for s in result.signals]}")
