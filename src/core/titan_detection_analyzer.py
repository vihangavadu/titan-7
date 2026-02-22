#!/usr/bin/env python3
"""
TITAN V7.6 DETECTION ANALYZER
==============================
Advanced detection research and pattern analysis module.

Purpose:
  - Analyze 2-day operation logs for detection patterns
  - Correlate failures with specific modules/configurations
  - Identify root causes of detection
  - Generate actionable patch recommendations
  - Track detection evolution over time

Research Cycle:
  1. Collect operation logs for 2 days
  2. Analyze detection patterns and correlations
  3. Identify root causes
  4. Generate patch recommendations
  5. Feed back to auto-patcher

Usage:
    from titan_detection_analyzer import DetectionAnalyzer
    
    analyzer = DetectionAnalyzer()
    
    # Run 2-day analysis
    report = analyzer.run_research_cycle(days=2)
    
    # Get patch recommendations
    patches = analyzer.generate_patch_recommendations()
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from enum import Enum
import logging
import re

logger = logging.getLogger("TITAN-DETECTION-ANALYZER")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class DetectionCategory(Enum):
    """High-level detection categories."""
    NETWORK = "network"          # IP, proxy, VPN issues
    FINGERPRINT = "fingerprint"  # Browser/device fingerprint
    BEHAVIORAL = "behavioral"    # Mouse, typing, timing
    PAYMENT = "payment"          # Card, 3DS, issuer
    IDENTITY = "identity"        # KYC, verification
    VELOCITY = "velocity"        # Rate limiting, cooling
    UNKNOWN = "unknown"


class RootCauseType(Enum):
    """Types of root causes."""
    CONFIGURATION = "configuration"    # Wrong settings
    MODULE_FAILURE = "module_failure"  # Module not working
    OUTDATED_DATA = "outdated_data"    # Old fingerprints, BINs
    TIMING_ISSUE = "timing_issue"      # Too fast/slow
    CORRELATION = "correlation"        # Data mismatch
    EXTERNAL = "external"              # Target-side changes
    UNKNOWN = "unknown"


class PatchPriority(Enum):
    """Patch priority levels."""
    CRITICAL = "critical"  # Fix immediately
    HIGH = "high"          # Fix within 24h
    MEDIUM = "medium"      # Fix within 1 week
    LOW = "low"            # Monitor and fix if persists


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectionSignature:
    """A detection signature pattern."""
    signature_id: str
    category: DetectionCategory
    pattern: str
    description: str
    indicators: List[str]
    occurrence_count: int = 0
    first_seen: float = 0
    last_seen: float = 0
    affected_operations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "signature_id": self.signature_id,
            "category": self.category.value,
            "pattern": self.pattern,
            "description": self.description,
            "indicators": self.indicators,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "affected_count": len(self.affected_operations)
        }


@dataclass
class RootCauseAnalysis:
    """Root cause analysis result."""
    cause_id: str
    cause_type: RootCauseType
    detection_category: DetectionCategory
    description: str
    contributing_factors: List[str]
    affected_modules: List[str]
    confidence: float  # 0.0 - 1.0
    evidence: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            "cause_id": self.cause_id,
            "cause_type": self.cause_type.value,
            "detection_category": self.detection_category.value,
            "description": self.description,
            "contributing_factors": self.contributing_factors,
            "affected_modules": self.affected_modules,
            "confidence": self.confidence,
            "evidence_count": len(self.evidence)
        }


@dataclass
class PatchRecommendation:
    """A recommended patch."""
    patch_id: str
    priority: PatchPriority
    category: DetectionCategory
    root_cause: RootCauseAnalysis
    title: str
    description: str
    affected_module: str
    current_value: Optional[str]
    recommended_value: Optional[str]
    implementation: str  # Code or config change
    expected_improvement: float  # Estimated success rate improvement
    risk: str  # Risk of implementing this patch
    
    def to_dict(self) -> Dict:
        return {
            "patch_id": self.patch_id,
            "priority": self.priority.value,
            "category": self.category.value,
            "root_cause_id": self.root_cause.cause_id,
            "title": self.title,
            "description": self.description,
            "affected_module": self.affected_module,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "implementation": self.implementation,
            "expected_improvement": self.expected_improvement,
            "risk": self.risk
        }


@dataclass
class ResearchReport:
    """Complete research cycle report."""
    report_id: str
    period_start: float
    period_end: float
    operations_analyzed: int
    success_rate: float
    detection_signatures: List[DetectionSignature]
    root_causes: List[RootCauseAnalysis]
    patch_recommendations: List[PatchRecommendation]
    target_analysis: Dict[str, Dict]
    temporal_patterns: Dict[str, Any]
    correlation_matrix: Dict[str, Dict]
    executive_summary: str
    
    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "period_start": datetime.fromtimestamp(self.period_start).isoformat(),
            "period_end": datetime.fromtimestamp(self.period_end).isoformat(),
            "operations_analyzed": self.operations_analyzed,
            "success_rate": self.success_rate,
            "detection_signatures": [s.to_dict() for s in self.detection_signatures],
            "root_causes": [r.to_dict() for r in self.root_causes],
            "patch_recommendations": [p.to_dict() for p in self.patch_recommendations],
            "target_analysis": self.target_analysis,
            "temporal_patterns": self.temporal_patterns,
            "correlation_matrix": self.correlation_matrix,
            "executive_summary": self.executive_summary
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION SIGNATURES DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

KNOWN_DETECTION_SIGNATURES = {
    # Network-based detections
    "NET-001": {
        "category": DetectionCategory.NETWORK,
        "pattern": r"datacenter|hosting|cloud",
        "description": "Datacenter IP detected",
        "indicators": ["ip_type=datacenter", "asn_type=hosting", "scamalytics>50"]
    },
    "NET-002": {
        "category": DetectionCategory.NETWORK,
        "pattern": r"proxy|vpn|tor",
        "description": "VPN/Proxy detected",
        "indicators": ["proxy_detected=true", "vpn_detected=true"]
    },
    "NET-003": {
        "category": DetectionCategory.NETWORK,
        "pattern": r"geo.?mismatch|location.?mismatch",
        "description": "Geographic location mismatch",
        "indicators": ["ip_country!=billing_country", "timezone_mismatch"]
    },
    
    # Fingerprint detections
    "FP-001": {
        "category": DetectionCategory.FINGERPRINT,
        "pattern": r"canvas|webgl|audio",
        "description": "Fingerprint inconsistency",
        "indicators": ["canvas_hash_changed", "webgl_mismatch", "audio_mismatch"]
    },
    "FP-002": {
        "category": DetectionCategory.FINGERPRINT,
        "pattern": r"ja[34]|tls|cipher",
        "description": "TLS fingerprint mismatch",
        "indicators": ["ja4_mismatch", "ja3_anomaly", "cipher_suspicious"]
    },
    "FP-003": {
        "category": DetectionCategory.FINGERPRINT,
        "pattern": r"user.?agent|navigator|screen",
        "description": "Browser configuration anomaly",
        "indicators": ["ua_mismatch", "navigator_anomaly", "screen_resolution_odd"]
    },
    "FP-004": {
        "category": DetectionCategory.FINGERPRINT,
        "pattern": r"first.?session|new.?visitor|fresh.?profile",
        "description": "First-session bias detected",
        "indicators": ["no_history", "empty_localstorage", "no_cookies"]
    },
    
    # Behavioral detections
    "BH-001": {
        "category": DetectionCategory.BEHAVIORAL,
        "pattern": r"mouse|cursor|click",
        "description": "Mouse behavior anomaly",
        "indicators": ["linear_movement", "perfect_curves", "instant_clicks"]
    },
    "BH-002": {
        "category": DetectionCategory.BEHAVIORAL,
        "pattern": r"typing|keyboard|input",
        "description": "Typing pattern anomaly",
        "indicators": ["constant_delay", "perfect_accuracy", "paste_detected"]
    },
    "BH-003": {
        "category": DetectionCategory.BEHAVIORAL,
        "pattern": r"timing|speed|too.?fast",
        "description": "Navigation too fast",
        "indicators": ["checkout_under_30s", "form_filled_instantly"]
    },
    
    # Payment detections
    "PAY-001": {
        "category": DetectionCategory.PAYMENT,
        "pattern": r"decline|rejected|refused",
        "description": "Card declined by issuer",
        "indicators": ["decline_code", "soft_decline", "hard_decline"]
    },
    "PAY-002": {
        "category": DetectionCategory.PAYMENT,
        "pattern": r"3ds|challenge|verification",
        "description": "3DS challenge triggered",
        "indicators": ["3ds_required", "sca_challenge", "frictionless_failed"]
    },
    "PAY-003": {
        "category": DetectionCategory.PAYMENT,
        "pattern": r"velocity|too.?many|rate.?limit",
        "description": "Velocity check failed",
        "indicators": ["card_used_recently", "ip_velocity", "device_velocity"]
    },
    
    # Identity detections
    "ID-001": {
        "category": DetectionCategory.IDENTITY,
        "pattern": r"kyc|liveness|face",
        "description": "KYC liveness check failed",
        "indicators": ["liveness_failed", "depth_rejected", "motion_missing"]
    },
    "ID-002": {
        "category": DetectionCategory.IDENTITY,
        "pattern": r"document|id.?check|passport",
        "description": "Document verification failed",
        "indicators": ["document_rejected", "ocr_mismatch", "tampering_detected"]
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class DetectionAnalyzer:
    """
    Advanced detection pattern analyzer.
    
    Analyzes operation logs to identify detection patterns,
    root causes, and generate patch recommendations.
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the detection analyzer.
        
        Args:
            log_dir: Directory containing operation logs
        """
        self.log_dir = log_dir or Path("/opt/titan/logs")
        self.db_path = self.log_dir / "titan_operations.db"
        self.research_dir = self.log_dir / "research"
        self.research_dir.mkdir(parents=True, exist_ok=True)
        
        # Analysis state
        self._signatures: Dict[str, DetectionSignature] = {}
        self._root_causes: List[RootCauseAnalysis] = []
        self._patches: List[PatchRecommendation] = []
        
        logger.info("Detection Analyzer initialized")
    
    def run_research_cycle(self, days: int = 2) -> ResearchReport:
        """
        Run complete research cycle.
        
        This is the main entry point for the 2-day research cycle.
        
        Args:
            days: Number of days to analyze (default: 2)
            
        Returns:
            Complete research report
        """
        logger.info(f"Starting research cycle for {days} days of data...")
        
        period_end = time.time()
        period_start = period_end - (days * 86400)
        
        # Fetch operation data
        operations = self._fetch_operations(period_start, period_end)
        phases = self._fetch_phases(period_start, period_end)
        signals = self._fetch_detection_signals(period_start, period_end)
        
        if not operations:
            logger.warning("No operations found in the specified period")
            return self._create_empty_report(period_start, period_end)
        
        logger.info(f"Analyzing {len(operations)} operations...")
        
        # Calculate success rate
        success_count = sum(1 for op in operations if op["success"])
        success_rate = success_count / len(operations) if operations else 0
        
        # Step 1: Detect signatures
        self._signatures = self._detect_signatures(operations, phases, signals)
        
        # Step 2: Perform root cause analysis
        self._root_causes = self._analyze_root_causes(operations, phases)
        
        # Step 3: Analyze by target
        target_analysis = self._analyze_by_target(operations)
        
        # Step 4: Analyze temporal patterns
        temporal_patterns = self._analyze_temporal_patterns(operations)
        
        # Step 5: Build correlation matrix
        correlation_matrix = self._build_correlation_matrix(operations, phases)
        
        # Step 6: Generate patch recommendations
        self._patches = self._generate_patches()
        
        # Step 7: Write executive summary
        executive_summary = self._write_executive_summary(
            len(operations), success_rate, self._signatures.values(),
            self._root_causes, self._patches
        )
        
        # Create report
        report = ResearchReport(
            report_id=f"RESEARCH-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            period_start=period_start,
            period_end=period_end,
            operations_analyzed=len(operations),
            success_rate=success_rate,
            detection_signatures=list(self._signatures.values()),
            root_causes=self._root_causes,
            patch_recommendations=self._patches,
            target_analysis=target_analysis,
            temporal_patterns=temporal_patterns,
            correlation_matrix=correlation_matrix,
            executive_summary=executive_summary
        )
        
        # Save report
        self._save_report(report)
        
        logger.info(f"Research cycle complete: {len(self._patches)} patches recommended")
        return report
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA FETCHING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _fetch_operations(self, start: float, end: float) -> List[Dict]:
        """Fetch operations from database."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM operations
            WHERE start_time >= ? AND start_time < ?
            ORDER BY start_time DESC
        """, (start, end))
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    
    def _fetch_phases(self, start: float, end: float) -> List[Dict]:
        """Fetch phases from database."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM phases
            WHERE start_time >= ? AND start_time < ?
            ORDER BY start_time
        """, (start, end))
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    
    def _fetch_detection_signals(self, start: float, end: float) -> List[Dict]:
        """Fetch detection signals from database."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM detection_signals
            WHERE timestamp >= ? AND timestamp < ?
            ORDER BY timestamp
        """, (start, end))
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIGNATURE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _detect_signatures(self, operations: List[Dict],
                           phases: List[Dict],
                           signals: List[Dict]) -> Dict[str, DetectionSignature]:
        """Detect known signatures in the data."""
        signatures = {}
        
        # Group data by operation
        ops_by_id = {op["operation_id"]: op for op in operations}
        phases_by_op = defaultdict(list)
        for phase in phases:
            phases_by_op[phase["operation_id"]].append(phase)
        signals_by_op = defaultdict(list)
        for signal in signals:
            signals_by_op[signal["operation_id"]].append(signal)
        
        # Check each failed operation against signatures
        for op in operations:
            if op["success"]:
                continue
            
            op_id = op["operation_id"]
            
            # Combine all text for matching
            text_blob = ""
            text_blob += op.get("error_message", "") or ""
            text_blob += op.get("detection_type", "") or ""
            
            for phase in phases_by_op.get(op_id, []):
                text_blob += phase.get("error_message", "") or ""
                text_blob += phase.get("detection_type", "") or ""
                text_blob += phase.get("metrics_json", "") or ""
            
            for signal in signals_by_op.get(op_id, []):
                text_blob += signal.get("details", "") or ""
                text_blob += signal.get("detection_type", "") or ""
            
            text_blob = text_blob.lower()
            
            # Match against known signatures
            for sig_id, sig_def in KNOWN_DETECTION_SIGNATURES.items():
                if re.search(sig_def["pattern"], text_blob, re.IGNORECASE):
                    if sig_id not in signatures:
                        signatures[sig_id] = DetectionSignature(
                            signature_id=sig_id,
                            category=sig_def["category"],
                            pattern=sig_def["pattern"],
                            description=sig_def["description"],
                            indicators=sig_def["indicators"],
                            first_seen=op["start_time"],
                            last_seen=op["start_time"]
                        )
                    
                    sig = signatures[sig_id]
                    sig.occurrence_count += 1
                    sig.affected_operations.append(op_id)
                    sig.last_seen = max(sig.last_seen, op["start_time"])
        
        return signatures
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ROOT CAUSE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_root_causes(self, operations: List[Dict],
                             phases: List[Dict]) -> List[RootCauseAnalysis]:
        """Perform root cause analysis on detected issues."""
        root_causes = []
        
        # Group phases by operation
        phases_by_op = defaultdict(list)
        for phase in phases:
            phases_by_op[phase["operation_id"]].append(phase)
        
        # Analyze failure patterns
        failure_patterns = defaultdict(list)
        for op in operations:
            if not op["success"]:
                key = (op["final_phase"], op["detection_type"])
                failure_patterns[key].append(op)
        
        # Generate root cause for each pattern
        for (phase, detection), ops in failure_patterns.items():
            if len(ops) < 2:  # Need at least 2 occurrences
                continue
            
            # Determine category
            category = self._detection_type_to_category(detection)
            
            # Analyze contributing factors
            factors = self._analyze_contributing_factors(ops, phases_by_op)
            
            # Identify affected modules
            modules = self._identify_affected_modules(phase, detection)
            
            # Calculate confidence based on sample size and consistency
            confidence = min(0.95, 0.5 + (len(ops) / 20))
            
            # Build evidence
            evidence = [{
                "operation_id": op["operation_id"],
                "error": op.get("error_message", ""),
                "timestamp": op["start_time"]
            } for op in ops[:5]]  # Limit to 5 examples
            
            root_cause = RootCauseAnalysis(
                cause_id=f"RC-{phase}-{detection}"[:50],
                cause_type=self._determine_cause_type(phase, detection, factors),
                detection_category=category,
                description=f"Failures at {phase} phase due to {detection}",
                contributing_factors=factors,
                affected_modules=modules,
                confidence=confidence,
                evidence=evidence
            )
            
            root_causes.append(root_cause)
        
        # Sort by occurrence count (number of affected ops)
        root_causes.sort(key=lambda x: len(x.evidence), reverse=True)
        
        return root_causes
    
    def _detection_type_to_category(self, detection_type: str) -> DetectionCategory:
        """Convert detection type to category."""
        detection_type = detection_type.lower()
        
        if any(x in detection_type for x in ["ip", "proxy", "vpn", "network", "geo"]):
            return DetectionCategory.NETWORK
        elif any(x in detection_type for x in ["fingerprint", "canvas", "webgl", "ja4", "tls"]):
            return DetectionCategory.FINGERPRINT
        elif any(x in detection_type for x in ["behavior", "mouse", "timing", "bot"]):
            return DetectionCategory.BEHAVIORAL
        elif any(x in detection_type for x in ["card", "decline", "3ds", "payment"]):
            return DetectionCategory.PAYMENT
        elif any(x in detection_type for x in ["kyc", "liveness", "identity"]):
            return DetectionCategory.IDENTITY
        elif any(x in detection_type for x in ["velocity", "rate", "limit"]):
            return DetectionCategory.VELOCITY
        
        return DetectionCategory.UNKNOWN
    
    def _analyze_contributing_factors(self, ops: List[Dict],
                                       phases_by_op: Dict) -> List[str]:
        """Identify contributing factors for failures."""
        factors = []
        
        # Check target diversity
        targets = set(op.get("target_domain", "") for op in ops)
        if len(targets) == 1:
            factors.append(f"All failures on same target: {list(targets)[0]}")
        
        # Check timing patterns
        times = [op["start_time"] for op in ops]
        hours = [datetime.fromtimestamp(t).hour for t in times]
        most_common_hour = Counter(hours).most_common(1)[0]
        if most_common_hour[1] > len(ops) * 0.5:
            factors.append(f"Most failures occur at hour {most_common_hour[0]}")
        
        # Check card BIN patterns
        bins = [op.get("card_bin", "")[:6] for op in ops if op.get("card_bin")]
        if bins:
            common_bins = Counter(bins).most_common(3)
            if common_bins[0][1] > len(ops) * 0.3:
                factors.append(f"BIN {common_bins[0][0]} has high failure rate")
        
        # Check geography patterns
        countries = [op.get("billing_country", "") for op in ops if op.get("billing_country")]
        if countries:
            common_country = Counter(countries).most_common(1)[0]
            if common_country[1] > len(ops) * 0.5:
                factors.append(f"Most failures from {common_country[0]}")
        
        return factors
    
    def _identify_affected_modules(self, phase: str, detection: str) -> List[str]:
        """Identify modules affected by this root cause."""
        modules = []
        
        # Phase-based module mapping
        phase_modules = {
            "card_validation": ["cerberus_core", "three_ds_strategy", "issuer_algo_defense"],
            "profile_generation": ["genesis_core", "fingerprint_injector", "indexeddb_lsng_synthesis"],
            "network_setup": ["lucid_vpn", "proxy_manager", "ja4_permutation_engine"],
            "preflight_validation": ["preflight_validator", "timezone_enforcer"],
            "browser_launch": ["integration_bridge", "ghost_motor_v6"],
            "navigation": ["referrer_warmup", "ghost_motor_v6"],
            "checkout": ["form_autofill_injector", "tra_exemption_engine"],
            "3ds_handling": ["three_ds_strategy", "tra_exemption_engine"],
            "kyc_bypass": ["kyc_core", "tof_depth_synthesis", "kyc_voice_engine"],
        }
        
        if phase in phase_modules:
            modules.extend(phase_modules[phase])
        
        # Detection-based module additions
        detection = detection.lower()
        if "fingerprint" in detection:
            modules.extend(["fingerprint_injector", "canvas_subpixel_shim", "webgl_angle"])
        if "ja4" in detection or "tls" in detection:
            modules.extend(["ja4_permutation_engine", "tls_parrot"])
        if "ip" in detection or "proxy" in detection:
            modules.extend(["proxy_manager", "lucid_vpn"])
        if "behavior" in detection:
            modules.extend(["ghost_motor_v6", "network_jitter"])
        
        return list(set(modules))
    
    def _determine_cause_type(self, phase: str, detection: str,
                              factors: List[str]) -> RootCauseType:
        """Determine the type of root cause."""
        detection = detection.lower()
        
        # Check for configuration issues
        if "mismatch" in detection or "invalid" in detection:
            return RootCauseType.CONFIGURATION
        
        # Check for timing issues
        if "timing" in detection or "fast" in detection or "slow" in detection:
            return RootCauseType.TIMING_ISSUE
        
        # Check for outdated data
        if "expired" in detection or "old" in detection:
            return RootCauseType.OUTDATED_DATA
        
        # Check for correlation issues
        if "correlation" in detection or factors:
            return RootCauseType.CORRELATION
        
        # Default based on phase
        if phase in ["card_validation", "3ds_handling"]:
            return RootCauseType.EXTERNAL  # Often issuer-side
        
        return RootCauseType.MODULE_FAILURE
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TARGET ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_by_target(self, operations: List[Dict]) -> Dict[str, Dict]:
        """Analyze success rates and patterns by target domain."""
        by_target = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failures": [],
            "detection_types": defaultdict(int),
            "avg_duration": 0,
            "durations": []
        })
        
        for op in operations:
            target = op.get("target_domain", "unknown")
            stats = by_target[target]
            
            stats["total"] += 1
            if op["success"]:
                stats["success"] += 1
            else:
                stats["failures"].append(op["error_message"][:100] if op.get("error_message") else "")
            
            if op.get("detection_type") and op["detection_type"] != "none":
                stats["detection_types"][op["detection_type"]] += 1
            
            if op.get("duration_ms"):
                stats["durations"].append(op["duration_ms"])
        
        # Calculate final stats
        result = {}
        for target, stats in by_target.items():
            result[target] = {
                "total_operations": stats["total"],
                "success_count": stats["success"],
                "failure_count": stats["total"] - stats["success"],
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0,
                "detection_types": dict(stats["detection_types"]),
                "avg_duration_ms": statistics.mean(stats["durations"]) if stats["durations"] else 0,
                "sample_errors": stats["failures"][:3]
            }
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEMPORAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_temporal_patterns(self, operations: List[Dict]) -> Dict:
        """Analyze temporal patterns in success/failure."""
        hourly = defaultdict(lambda: {"total": 0, "success": 0})
        daily = defaultdict(lambda: {"total": 0, "success": 0})
        
        for op in operations:
            dt = datetime.fromtimestamp(op["start_time"])
            hour = dt.hour
            day = dt.strftime("%Y-%m-%d")
            
            hourly[hour]["total"] += 1
            daily[day]["total"] += 1
            
            if op["success"]:
                hourly[hour]["success"] += 1
                daily[day]["success"] += 1
        
        # Calculate rates
        hourly_rates = {}
        for hour, stats in hourly.items():
            hourly_rates[hour] = {
                "total": stats["total"],
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0
            }
        
        daily_rates = {}
        for day, stats in daily.items():
            daily_rates[day] = {
                "total": stats["total"],
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0
            }
        
        # Find best/worst times
        best_hour = max(hourly_rates.items(), key=lambda x: x[1]["success_rate"]) if hourly_rates else (0, {"success_rate": 0})
        worst_hour = min(hourly_rates.items(), key=lambda x: x[1]["success_rate"]) if hourly_rates else (0, {"success_rate": 0})
        
        return {
            "hourly_pattern": hourly_rates,
            "daily_pattern": daily_rates,
            "best_hour": best_hour[0],
            "worst_hour": worst_hour[0],
            "best_rate": best_hour[1]["success_rate"],
            "worst_rate": worst_hour[1]["success_rate"],
            "recommendation": f"Prefer operations at {best_hour[0]}:00 UTC (success rate: {best_hour[1]['success_rate']*100:.1f}%)"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CORRELATION ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _build_correlation_matrix(self, operations: List[Dict],
                                  phases: List[Dict]) -> Dict:
        """Build correlation matrix between factors and success."""
        correlations = {}
        
        # Correlation: target_domain vs success
        target_success = defaultdict(lambda: {"success": 0, "total": 0})
        for op in operations:
            target = op.get("target_domain", "unknown")
            target_success[target]["total"] += 1
            if op["success"]:
                target_success[target]["success"] += 1
        
        correlations["target_domain"] = {
            k: v["success"] / v["total"] if v["total"] > 0 else 0
            for k, v in target_success.items()
        }
        
        # Correlation: billing_country vs success
        country_success = defaultdict(lambda: {"success": 0, "total": 0})
        for op in operations:
            country = op.get("billing_country", "unknown")
            country_success[country]["total"] += 1
            if op["success"]:
                country_success[country]["success"] += 1
        
        correlations["billing_country"] = {
            k: v["success"] / v["total"] if v["total"] > 0 else 0
            for k, v in country_success.items()
        }
        
        # Correlation: final_phase (for failures) vs detection_type
        phase_detection = defaultdict(lambda: defaultdict(int))
        for op in operations:
            if not op["success"]:
                phase = op.get("final_phase", "unknown")
                detection = op.get("detection_type", "unknown")
                phase_detection[phase][detection] += 1
        
        correlations["phase_detection"] = {
            phase: dict(detections) for phase, detections in phase_detection.items()
        }
        
        return correlations
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PATCH GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _generate_patches(self) -> List[PatchRecommendation]:
        """Generate patch recommendations based on analysis."""
        patches = []
        
        # Generate patches for each root cause
        for root_cause in self._root_causes:
            patch = self._create_patch_for_root_cause(root_cause)
            if patch:
                patches.append(patch)
        
        # Generate patches for high-frequency signatures
        for sig_id, sig in self._signatures.items():
            if sig.occurrence_count >= 3:
                patch = self._create_patch_for_signature(sig)
                if patch:
                    patches.append(patch)
        
        # Sort by priority
        priority_order = {
            PatchPriority.CRITICAL: 0,
            PatchPriority.HIGH: 1,
            PatchPriority.MEDIUM: 2,
            PatchPriority.LOW: 3
        }
        patches.sort(key=lambda x: priority_order[x.priority])
        
        return patches
    
    def _create_patch_for_root_cause(self, root_cause: RootCauseAnalysis) -> Optional[PatchRecommendation]:
        """Create patch recommendation for a root cause."""
        category = root_cause.detection_category
        cause_type = root_cause.cause_type
        
        # Determine priority
        if len(root_cause.evidence) >= 10:
            priority = PatchPriority.CRITICAL
        elif len(root_cause.evidence) >= 5:
            priority = PatchPriority.HIGH
        elif len(root_cause.evidence) >= 3:
            priority = PatchPriority.MEDIUM
        else:
            priority = PatchPriority.LOW
        
        # Generate patch based on category and cause
        if category == DetectionCategory.NETWORK:
            return self._generate_network_patch(root_cause, priority)
        elif category == DetectionCategory.FINGERPRINT:
            return self._generate_fingerprint_patch(root_cause, priority)
        elif category == DetectionCategory.BEHAVIORAL:
            return self._generate_behavioral_patch(root_cause, priority)
        elif category == DetectionCategory.PAYMENT:
            return self._generate_payment_patch(root_cause, priority)
        elif category == DetectionCategory.IDENTITY:
            return self._generate_identity_patch(root_cause, priority)
        
        return None
    
    def _generate_network_patch(self, root_cause: RootCauseAnalysis,
                                priority: PatchPriority) -> PatchRecommendation:
        """Generate network-related patch."""
        return PatchRecommendation(
            patch_id=f"PATCH-NET-{int(time.time())}",
            priority=priority,
            category=DetectionCategory.NETWORK,
            root_cause=root_cause,
            title="Improve Network Identity",
            description="Switch to higher quality residential proxies and enable rotation",
            affected_module="proxy_manager",
            current_value="datacenter/low-quality proxies",
            recommended_value="residential proxies with state-level targeting",
            implementation="""
# In proxy_manager.py configuration:
PROXY_QUALITY_THRESHOLD = 0.8  # Increase quality threshold
ENABLE_ROTATION = True
ROTATION_INTERVAL = 300  # 5 minutes
PREFER_RESIDENTIAL = True
GEO_MATCH_REQUIRED = True
            """,
            expected_improvement=0.15,  # 15% improvement
            risk="Low - proxy rotation may cause session issues on some sites"
        )
    
    def _generate_fingerprint_patch(self, root_cause: RootCauseAnalysis,
                                    priority: PatchPriority) -> PatchRecommendation:
        """Generate fingerprint-related patch."""
        return PatchRecommendation(
            patch_id=f"PATCH-FP-{int(time.time())}",
            priority=priority,
            category=DetectionCategory.FINGERPRINT,
            root_cause=root_cause,
            title="Strengthen Fingerprint Consistency",
            description="Enable JA4+ permutation and verify profile age",
            affected_module="ja4_permutation_engine",
            current_value="static fingerprint",
            recommended_value="browser-matched JA4+ with permutation",
            implementation="""
# In integration_bridge.py:
# Ensure JA4 permutation is enabled
if self._ja4_engine:
    config = PermutationConfig(
        enable_grease=True,
        shuffle_extensions=True,
        target_browser=BrowserTarget.CHROME_131,
        target_os=OSTarget.WINDOWS_11
    )
    self._ja4_engine.configure(config)

# In genesis_core.py:
# Ensure profile age >= 60 days
MIN_PROFILE_AGE = 60
            """,
            expected_improvement=0.20,
            risk="Medium - incorrect browser targeting may cause issues"
        )
    
    def _generate_behavioral_patch(self, root_cause: RootCauseAnalysis,
                                    priority: PatchPriority) -> PatchRecommendation:
        """Generate behavioral-related patch."""
        return PatchRecommendation(
            patch_id=f"PATCH-BH-{int(time.time())}",
            priority=priority,
            category=DetectionCategory.BEHAVIORAL,
            root_cause=root_cause,
            title="Enhance Human Behavior Simulation",
            description="Increase warmup duration and enable Ghost Motor humanization",
            affected_module="ghost_motor_v6",
            current_value="basic mouse movement",
            recommended_value="full humanization with Ghost Motor",
            implementation="""
# In titan_automation_orchestrator.py:
config.warmup_duration = 60  # Increase to 60 seconds
config.warmup_enabled = True

# In integration_bridge.py:
from ghost_motor_v6 import GhostMotorEngine, HumanBehaviorProfile

profile = HumanBehaviorProfile(
    mouse_speed_variance=0.3,
    typing_speed_cpm=250,
    typing_variance=0.2,
    enable_pauses=True,
    pause_probability=0.1
)
ghost_motor = GhostMotorEngine(profile)
            """,
            expected_improvement=0.10,
            risk="Low - may increase operation time"
        )
    
    def _generate_payment_patch(self, root_cause: RootCauseAnalysis,
                                priority: PatchPriority) -> PatchRecommendation:
        """Generate payment-related patch."""
        return PatchRecommendation(
            patch_id=f"PATCH-PAY-{int(time.time())}",
            priority=priority,
            category=DetectionCategory.PAYMENT,
            root_cause=root_cause,
            title="Optimize Payment Flow",
            description="Enable TRA exemption and check issuer defense",
            affected_module="tra_exemption_engine",
            current_value="standard 3DS flow",
            recommended_value="TRA exemption with issuer defense",
            implementation="""
# In cerberus_core.py or checkout flow:
from tra_exemption_engine import TRAExemptionEngine
from issuer_algo_defense import IssuerDefenseEngine

tra = TRAExemptionEngine()
issuer_defense = IssuerDefenseEngine()

# Get optimal exemption
exemption = tra.get_optimal_exemption(amount, currency, issuer_country)
if exemption:
    apply_exemption(exemption)

# Check issuer risk before transaction
risk = issuer_defense.calculate_risk(bin, amount, mcc)
if risk['risk_level'] == 'high':
    apply_mitigations(risk['mitigations'])
            """,
            expected_improvement=0.12,
            risk="Medium - some issuers may require 3DS"
        )
    
    def _generate_identity_patch(self, root_cause: RootCauseAnalysis,
                                 priority: PatchPriority) -> PatchRecommendation:
        """Generate identity/KYC-related patch."""
        return PatchRecommendation(
            patch_id=f"PATCH-ID-{int(time.time())}",
            priority=priority,
            category=DetectionCategory.IDENTITY,
            root_cause=root_cause,
            title="Improve KYC Bypass",
            description="Enable ToF depth synthesis and improve liveness motions",
            affected_module="tof_depth_synthesis",
            current_value="basic liveness",
            recommended_value="ToF depth with advanced motions",
            implementation="""
# In kyc_core.py:
from tof_depth_synthesis import ToFDepthSynthesizer, DepthQuality, SensorType

tof = ToFDepthSynthesizer()

# Generate high-quality depth map
depth_map = tof.generate(
    image_path,
    sensor=SensorType.TRUEDEPTH,
    quality=DepthQuality.HIGH
)

# Enable all liveness motions
LIVENESS_MOTIONS = [
    "BLINK", "SMILE", "HEAD_LEFT", "HEAD_RIGHT",
    "NOD_YES", "OPEN_MOUTH"
]
            """,
            expected_improvement=0.08,
            risk="High - ToF synthesis requires GPU"
        )
    
    def _create_patch_for_signature(self, sig: DetectionSignature) -> Optional[PatchRecommendation]:
        """Create patch for a detection signature."""
        # Use category-specific patch generation
        dummy_cause = RootCauseAnalysis(
            cause_id=f"SIG-{sig.signature_id}",
            cause_type=RootCauseType.MODULE_FAILURE,
            detection_category=sig.category,
            description=sig.description,
            contributing_factors=[],
            affected_modules=[],
            confidence=0.7,
            evidence=[]
        )
        
        priority = PatchPriority.HIGH if sig.occurrence_count >= 5 else PatchPriority.MEDIUM
        
        if sig.category == DetectionCategory.NETWORK:
            return self._generate_network_patch(dummy_cause, priority)
        elif sig.category == DetectionCategory.FINGERPRINT:
            return self._generate_fingerprint_patch(dummy_cause, priority)
        elif sig.category == DetectionCategory.BEHAVIORAL:
            return self._generate_behavioral_patch(dummy_cause, priority)
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REPORTING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _write_executive_summary(self, total_ops: int, success_rate: float,
                                 signatures: List, root_causes: List,
                                 patches: List) -> str:
        """Write executive summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("TITAN DETECTION RESEARCH - EXECUTIVE SUMMARY")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Operations Analyzed: {total_ops}")
        lines.append(f"Overall Success Rate: {success_rate*100:.1f}%")
        lines.append(f"Detection Signatures Found: {len(list(signatures))}")
        lines.append(f"Root Causes Identified: {len(root_causes)}")
        lines.append(f"Patches Recommended: {len(patches)}")
        lines.append("")
        
        # Top issues
        lines.append("TOP ISSUES:")
        for i, sig in enumerate(list(signatures)[:3], 1):
            lines.append(f"  {i}. {sig.description} ({sig.occurrence_count} occurrences)")
        
        # Recommended actions
        lines.append("")
        lines.append("RECOMMENDED ACTIONS:")
        for i, patch in enumerate(patches[:3], 1):
            lines.append(f"  {i}. [{patch.priority.value.upper()}] {patch.title}")
            lines.append(f"     Expected improvement: +{patch.expected_improvement*100:.0f}%")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _save_report(self, report: ResearchReport) -> None:
        """Save research report to file."""
        report_file = self.research_dir / f"{report.report_id}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        # Also save human-readable summary
        summary_file = self.research_dir / f"{report.report_id}_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(report.executive_summary)
        
        logger.info(f"Research report saved: {report_file}")
    
    def _create_empty_report(self, start: float, end: float) -> ResearchReport:
        """Create empty report when no data available."""
        return ResearchReport(
            report_id=f"RESEARCH-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            period_start=start,
            period_end=end,
            operations_analyzed=0,
            success_rate=0,
            detection_signatures=[],
            root_causes=[],
            patch_recommendations=[],
            target_analysis={},
            temporal_patterns={},
            correlation_matrix={},
            executive_summary="No operations found in the specified period."
        )
    
    def generate_patch_recommendations(self) -> List[PatchRecommendation]:
        """Get current patch recommendations."""
        return self._patches


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN Detection Analyzer")
    parser.add_argument("--research", action="store_true", help="Run research cycle")
    parser.add_argument("--days", type=int, default=2, help="Days to analyze")
    parser.add_argument("--patches", action="store_true", help="Show patch recommendations")
    parser.add_argument("--signatures", action="store_true", help="Show detection signatures")
    parser.add_argument("--log-dir", help="Log directory path")
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir) if args.log_dir else None
    analyzer = DetectionAnalyzer(log_dir)
    
    if args.research:
        report = analyzer.run_research_cycle(args.days)
        print(report.executive_summary)
        print(f"\nFull report saved to: {analyzer.research_dir}")
        
    elif args.patches:
        report = analyzer.run_research_cycle(args.days)
        print("\nPATCH RECOMMENDATIONS:")
        print("=" * 60)
        for patch in report.patch_recommendations:
            print(f"\n[{patch.priority.value.upper()}] {patch.title}")
            print(f"  Module: {patch.affected_module}")
            print(f"  Expected improvement: +{patch.expected_improvement*100:.0f}%")
            print(f"  Risk: {patch.risk}")
            print(f"  Implementation:")
            for line in patch.implementation.strip().split("\n")[:5]:
                print(f"    {line}")
        
    elif args.signatures:
        report = analyzer.run_research_cycle(args.days)
        print("\nDETECTION SIGNATURES:")
        print("=" * 60)
        for sig in report.detection_signatures:
            print(f"\n{sig.signature_id}: {sig.description}")
            print(f"  Category: {sig.category.value}")
            print(f"  Occurrences: {sig.occurrence_count}")
            print(f"  Pattern: {sig.pattern}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
