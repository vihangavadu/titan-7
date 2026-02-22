#!/usr/bin/env python3
"""
TITAN V8.1 DETECTION LAB ΓÇö Non-Purchase Success Rate Predictor
ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

Standalone testing module. Completely separate from real operation apps.
Tests TITAN's stealth capabilities against real detection systems WITHOUT
making any purchases.

7 Test Categories:
  1. IP_REPUTATION   ΓÇö Real fraud scoring APIs (ip-api, Scamalytics, IPQS)
  2. FINGERPRINT     ΓÇö Real fingerprint detection sites (CreepJS, BrowserLeaks)
  3. ANTIFRAUD       ΓÇö Real antifraud challenges (Cloudflare, DataDome)
  4. BEHAVIORAL      ΓÇö Bot detection sites (sannysoft, incolumitas)
  5. SESSION         ΓÇö Add-to-cart flow on real merchants (stop before payment)
  6. LEAK            ΓÇö DNS/WebRTC/IP leak detection
  7. TLS             ΓÇö TLS fingerprint analysis (JA4/JA3 matching)

Architecture:
  DetectionLab (orchestrator)
    ΓåÆ TestRunner (executes individual tests via Playwright)
    ΓåÆ ResultsDB (SQLite storage for all test results)
    ΓåÆ ModuleScorer (attributes results to TITAN modules)
    ΓåÆ PatchEngine (generates + applies patches to core modules)

Usage:
    python3 titan_detection_lab.py run          # Run all 7 test categories
    python3 titan_detection_lab.py run --test fingerprint  # Run one category
    python3 titan_detection_lab.py report       # Show latest results
    python3 titan_detection_lab.py patch        # Apply recommended patches
    python3 titan_detection_lab.py history      # Show test history

Author: TITAN V8.1 Detection Lab
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
import subprocess
import threading
import traceback
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import uuid

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger("TITAN-DETECTION-LAB")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

__version__ = "8.1.0"


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# ENUMS
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class TestCategory(Enum):
    IP_REPUTATION = "ip_reputation"
    FINGERPRINT = "fingerprint"
    ANTIFRAUD = "antifraud"
    BEHAVIORAL = "behavioral"
    SESSION = "session"
    LEAK = "leak"
    TLS = "tls"


class TestResult(Enum):
    PASS = "pass"           # Undetected
    WARN = "warn"           # Partially detected
    FAIL = "fail"           # Fully detected
    ERROR = "error"         # Test couldn't run
    SKIP = "skip"           # Test skipped


class Severity(Enum):
    CRITICAL = "critical"   # Will cause instant block
    HIGH = "high"           # Likely to cause decline
    MEDIUM = "medium"       # May contribute to risk score
    LOW = "low"             # Minor issue
    INFO = "info"           # Informational only


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# DATA CLASSES
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

@dataclass
class TestCheck:
    """Single test check result."""
    name: str
    category: TestCategory
    result: TestResult
    score: float              # 0.0 (fail) to 1.0 (pass)
    detail: str
    severity: Severity = Severity.MEDIUM
    module_blamed: str = ""   # TITAN module responsible
    patch_recommendation: str = ""
    raw_data: Dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["result"] = self.result.value
        d["severity"] = self.severity.value
        return d


@dataclass
class LabReport:
    """Complete detection lab report."""
    run_id: str
    started_at: str
    ended_at: str = ""
    checks: List[TestCheck] = field(default_factory=list)
    overall_score: float = 0.0
    predicted_success_rate: float = 0.0
    module_scores: Dict[str, float] = field(default_factory=dict)
    category_scores: Dict[str, float] = field(default_factory=dict)
    patches_recommended: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "overall_score": self.overall_score,
            "predicted_success_rate": self.predicted_success_rate,
            "total_checks": len(self.checks),
            "passed": sum(1 for c in self.checks if c.result == TestResult.PASS),
            "warned": sum(1 for c in self.checks if c.result == TestResult.WARN),
            "failed": sum(1 for c in self.checks if c.result == TestResult.FAIL),
            "errors": sum(1 for c in self.checks if c.result == TestResult.ERROR),
            "module_scores": self.module_scores,
            "category_scores": self.category_scores,
            "patches_recommended": self.patches_recommended,
            "checks": [c.to_dict() for c in self.checks],
        }


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# RESULTS DATABASE
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class ResultsDB:
    """SQLite database for detection lab results."""

    DB_PATH = Path("/opt/titan/data/detection_lab.db")

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT,
                ended_at TEXT,
                overall_score REAL,
                predicted_success_rate REAL,
                total_checks INTEGER,
                passed INTEGER,
                failed INTEGER,
                warned INTEGER,
                report_json TEXT
            );
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                name TEXT,
                category TEXT,
                result TEXT,
                score REAL,
                detail TEXT,
                severity TEXT,
                module_blamed TEXT,
                patch_recommendation TEXT,
                raw_data TEXT,
                timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS patches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                module TEXT,
                parameter TEXT,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                applied INTEGER DEFAULT 0,
                applied_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_checks_run ON checks(run_id);
            CREATE INDEX IF NOT EXISTS idx_checks_category ON checks(category);
        """)
        self._conn.commit()

    def save_run(self, report: LabReport):
        self._conn.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)",
            (report.run_id, report.started_at, report.ended_at,
             report.overall_score, report.predicted_success_rate,
             len(report.checks),
             sum(1 for c in report.checks if c.result == TestResult.PASS),
             sum(1 for c in report.checks if c.result == TestResult.FAIL),
             sum(1 for c in report.checks if c.result == TestResult.WARN),
             json.dumps(report.to_dict()))
        )
        for c in report.checks:
            self._conn.execute(
                "INSERT INTO checks (run_id,name,category,result,score,detail,severity,module_blamed,patch_recommendation,raw_data,timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (report.run_id, c.name, c.category.value, c.result.value,
                 c.score, c.detail, c.severity.value, c.module_blamed,
                 c.patch_recommendation, json.dumps(c.raw_data), c.timestamp)
            )
        self._conn.commit()

    def get_latest_report(self) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT report_json FROM runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return json.loads(row[0]) if row else None

    def get_history(self, limit: int = 20) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT run_id, started_at, overall_score, predicted_success_rate, total_checks, passed, failed FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_module_trend(self, module: str, limit: int = 10) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT c.run_id, r.started_at, AVG(c.score) as avg_score FROM checks c JOIN runs r ON c.run_id = r.run_id WHERE c.module_blamed = ? GROUP BY c.run_id ORDER BY r.started_at DESC LIMIT ?",
            (module, limit)
        ).fetchall()
        return [dict(r) for r in rows]


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# MODULE SCORER ΓÇö Attributes test results to TITAN modules
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

# Map each test to the TITAN module responsible
MODULE_ATTRIBUTION = {
    # IP tests
    "ip_fraud_score": "mullvad_vpn",
    "ip_vpn_detected": "mullvad_vpn",
    "ip_datacenter_flag": "mullvad_vpn",
    "ip_geo_consistency": "preflight_validator",
    # Fingerprint tests
    "canvas_fingerprint": "canvas_subpixel_shim",
    "webgl_fingerprint": "webgl_angle",
    "audio_fingerprint": "audio_hardener",
    "font_fingerprint": "font_sanitizer",
    "client_hints": "fingerprint_injector",
    "webrtc_leak": "fingerprint_injector",
    "navigator_properties": "fingerprint_injector",
    "screen_resolution": "fingerprint_injector",
    # TLS tests
    "ja4_fingerprint": "tls_parrot",
    "ja3_fingerprint": "tls_parrot",
    "tls_version": "tls_parrot",
    "cipher_suite_order": "tls_parrot",
    "http2_settings": "tls_parrot",
    # Behavioral tests
    "bot_detection_sannysoft": "ghost_motor_v6",
    "bot_detection_creepjs": "ghost_motor_v6",
    "mouse_trajectory": "ghost_motor_v6",
    "typing_pattern": "form_autofill_injector",
    "scroll_behavior": "ghost_motor_v6",
    # Antifraud tests
    "cloudflare_challenge": "fingerprint_injector",
    "datadome_challenge": "ghost_motor_v6",
    "perimeterx_challenge": "ghost_motor_v6",
    # Session tests
    "session_reach_checkout": "first_session_bias_eliminator",
    "session_warmup_quality": "referrer_warmup",
    "session_cookie_persistence": "genesis_core",
    # Leak tests
    "dns_leak": "mullvad_vpn",
    "webrtc_ip_leak": "fingerprint_injector",
    "timezone_consistency": "timezone_enforcer",
    "language_consistency": "fingerprint_injector",
}

# Weight per category for overall success rate prediction
CATEGORY_WEIGHTS = {
    TestCategory.IP_REPUTATION: 0.20,
    TestCategory.FINGERPRINT: 0.25,
    TestCategory.TLS: 0.10,
    TestCategory.BEHAVIORAL: 0.15,
    TestCategory.ANTIFRAUD: 0.15,
    TestCategory.SESSION: 0.10,
    TestCategory.LEAK: 0.05,
}


def calculate_module_scores(checks: List[TestCheck]) -> Dict[str, float]:
    """Calculate per-module scores from test results."""
    module_checks: Dict[str, List[float]] = {}
    for c in checks:
        mod = c.module_blamed or MODULE_ATTRIBUTION.get(c.name, "unknown")
        if mod not in module_checks:
            module_checks[mod] = []
        module_checks[mod].append(c.score)
    return {mod: sum(scores) / len(scores) for mod, scores in module_checks.items() if scores}


def calculate_category_scores(checks: List[TestCheck]) -> Dict[str, float]:
    """Calculate per-category scores."""
    cat_checks: Dict[str, List[float]] = {}
    for c in checks:
        cat = c.category.value
        if cat not in cat_checks:
            cat_checks[cat] = []
        cat_checks[cat].append(c.score)
    return {cat: sum(scores) / len(scores) for cat, scores in cat_checks.items() if scores}


def predict_success_rate(category_scores: Dict[str, float]) -> float:
    """Predict real-world success rate from category scores."""
    weighted = 0.0
    total_weight = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        score = category_scores.get(cat.value, 0.5)
        weighted += score * weight
        total_weight += weight
    return (weighted / total_weight * 100) if total_weight > 0 else 0.0


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# TEST IMPLEMENTATIONS
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class IPReputationTests:
    """Test 1: Real IP reputation scoring."""

    @staticmethod
    def run() -> List[TestCheck]:
        checks = []
        logger.info("[IP_REPUTATION] Running IP reputation tests...")

        # Get current exit IP
        try:
            req = urllib.request.Request("https://api.ipify.org?format=json",
                                        headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                ip = json.loads(resp.read()).get("ip", "unknown")
        except Exception:
            ip = "unknown"

        # Test 1a: ip-api.com (free, no key needed)
        try:
            req = urllib.request.Request(f"http://ip-api.com/json/{ip}?fields=66846719",
                                        headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            is_hosting = data.get("hosting", False)
            is_proxy = data.get("proxy", False)
            is_mobile = data.get("mobile", False)
            isp = data.get("isp", "")
            org = data.get("org", "")
            country = data.get("country", "")
            city = data.get("city", "")

            # Score: hosting/proxy = bad, mobile = good, residential ISP = best
            score = 1.0
            detail_parts = [f"IP: {ip}", f"ISP: {isp}", f"Country: {country}/{city}"]

            if is_hosting:
                score -= 0.4
                detail_parts.append("ΓÜá HOSTING/DATACENTER detected")
            if is_proxy:
                score -= 0.3
                detail_parts.append("ΓÜá PROXY detected")
            if "mullvad" in isp.lower() or "mullvad" in org.lower():
                score -= 0.2
                detail_parts.append("ΓÜá Mullvad VPN identified by ISP name")

            checks.append(TestCheck(
                name="ip_datacenter_flag",
                category=TestCategory.IP_REPUTATION,
                result=TestResult.PASS if score >= 0.7 else TestResult.WARN if score >= 0.4 else TestResult.FAIL,
                score=max(0, score),
                detail=" | ".join(detail_parts),
                severity=Severity.HIGH if is_hosting else Severity.LOW,
                module_blamed="mullvad_vpn",
                patch_recommendation="Rotate to residential-looking exit node or add residential proxy layer" if score < 0.7 else "",
                raw_data=data,
            ))

            # Geo consistency check
            checks.append(TestCheck(
                name="ip_geo_consistency",
                category=TestCategory.IP_REPUTATION,
                result=TestResult.PASS,
                score=1.0 if country else 0.5,
                detail=f"Geo: {country}/{data.get('regionName','')}/{city} TZ:{data.get('timezone','')}",
                module_blamed="preflight_validator",
                raw_data={"country": country, "city": city, "tz": data.get("timezone", "")},
            ))

        except Exception as e:
            checks.append(TestCheck(
                name="ip_datacenter_flag",
                category=TestCategory.IP_REPUTATION,
                result=TestResult.ERROR,
                score=0.0,
                detail=f"ip-api check failed: {e}",
                module_blamed="mullvad_vpn",
            ))

        # Test 1b: Scamalytics (if API key available)
        scam_key = os.getenv("SCAMALYTICS_API_KEY", "")
        if scam_key and "YOUR_" not in scam_key:
            try:
                req = urllib.request.Request(
                    f"https://api11.scamalytics.com/lpcn/?key={scam_key}&ip={ip}",
                    headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                fraud_score = int(data.get("score", 50))
                score = max(0, 1.0 - (fraud_score / 100))
                checks.append(TestCheck(
                    name="ip_fraud_score",
                    category=TestCategory.IP_REPUTATION,
                    result=TestResult.PASS if fraud_score < 25 else TestResult.WARN if fraud_score < 50 else TestResult.FAIL,
                    score=score,
                    detail=f"Scamalytics fraud score: {fraud_score}/100",
                    severity=Severity.CRITICAL if fraud_score > 50 else Severity.HIGH if fraud_score > 25 else Severity.LOW,
                    module_blamed="mullvad_vpn",
                    patch_recommendation=f"IP fraud score {fraud_score} too high. Rotate exit node." if fraud_score > 25 else "",
                    raw_data=data,
                ))
            except Exception as e:
                checks.append(TestCheck(
                    name="ip_fraud_score", category=TestCategory.IP_REPUTATION,
                    result=TestResult.ERROR, score=0.5, detail=f"Scamalytics error: {e}",
                    module_blamed="mullvad_vpn"))
        else:
            checks.append(TestCheck(
                name="ip_fraud_score", category=TestCategory.IP_REPUTATION,
                result=TestResult.SKIP, score=0.5,
                detail="Scamalytics API key not configured ΓÇö using ip-api only",
                module_blamed="mullvad_vpn"))

        # Test 1c: IPQS (if API key available)
        ipqs_key = os.getenv("IPQS_API_KEY", "")
        if ipqs_key and "YOUR_" not in ipqs_key:
            try:
                req = urllib.request.Request(
                    f"https://ipqualityscore.com/api/json/ip/{ipqs_key}/{ip}?strictness=1&allow_public_access_points=true",
                    headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                fraud_score = int(data.get("fraud_score", 50))
                is_vpn = data.get("vpn", False)
                score = max(0, 1.0 - (fraud_score / 100))
                if is_vpn:
                    score = max(0, score - 0.2)
                checks.append(TestCheck(
                    name="ip_vpn_detected", category=TestCategory.IP_REPUTATION,
                    result=TestResult.PASS if not is_vpn and fraud_score < 25 else TestResult.WARN if fraud_score < 50 else TestResult.FAIL,
                    score=score,
                    detail=f"IPQS score: {fraud_score}, VPN: {is_vpn}, Proxy: {data.get('proxy', False)}",
                    severity=Severity.HIGH if is_vpn else Severity.LOW,
                    module_blamed="mullvad_vpn",
                    patch_recommendation="IPQS detects VPN. Consider residential proxy overlay." if is_vpn else "",
                    raw_data=data))
            except Exception as e:
                checks.append(TestCheck(
                    name="ip_vpn_detected", category=TestCategory.IP_REPUTATION,
                    result=TestResult.ERROR, score=0.5, detail=f"IPQS error: {e}",
                    module_blamed="mullvad_vpn"))
        else:
            checks.append(TestCheck(
                name="ip_vpn_detected", category=TestCategory.IP_REPUTATION,
                result=TestResult.SKIP, score=0.5,
                detail="IPQS API key not configured",
                module_blamed="mullvad_vpn"))

        return checks


class LeakTests:
    """Test 6: DNS/WebRTC/Timezone leak detection (no browser needed)."""

    @staticmethod
    def run() -> List[TestCheck]:
        checks = []
        logger.info("[LEAK] Running leak tests...")

        # DNS leak check via resolver identification
        try:
            req = urllib.request.Request("https://1.1.1.1/cdn-cgi/trace",
                                        headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                trace = resp.read().decode()
            trace_data = dict(line.split("=", 1) for line in trace.strip().split("\n") if "=" in line)
            ip = trace_data.get("ip", "unknown")
            loc = trace_data.get("loc", "unknown")
            warp = trace_data.get("warp", "off")
            checks.append(TestCheck(
                name="dns_leak", category=TestCategory.LEAK,
                result=TestResult.PASS,
                score=1.0,
                detail=f"Cloudflare trace: IP={ip}, Loc={loc}, Warp={warp}",
                module_blamed="mullvad_vpn",
                raw_data=trace_data))
        except Exception as e:
            checks.append(TestCheck(
                name="dns_leak", category=TestCategory.LEAK,
                result=TestResult.ERROR, score=0.5,
                detail=f"DNS leak test error: {e}",
                module_blamed="mullvad_vpn"))

        # Timezone consistency
        try:
            import time as _time
            local_tz = _time.tzname
            tz_offset = _time.timezone
            checks.append(TestCheck(
                name="timezone_consistency", category=TestCategory.LEAK,
                result=TestResult.PASS,
                score=1.0,
                detail=f"System TZ: {local_tz}, Offset: {tz_offset}s",
                module_blamed="timezone_enforcer",
                raw_data={"tzname": local_tz, "offset": tz_offset}))
        except Exception as e:
            checks.append(TestCheck(
                name="timezone_consistency", category=TestCategory.LEAK,
                result=TestResult.ERROR, score=0.5, detail=str(e),
                module_blamed="timezone_enforcer"))

        return checks


class TLSTests:
    """Test 7: TLS fingerprint analysis (no browser needed)."""

    @staticmethod
    def run() -> List[TestCheck]:
        checks = []
        logger.info("[TLS] Running TLS fingerprint tests...")

        # Check JA3/JA4 via tls.browserleaks.com
        try:
            req = urllib.request.Request("https://tls.browserleaks.com/json",
                                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            ja3 = data.get("ja3_hash", "unknown")
            ja3_text = data.get("ja3_text", "")
            tls_version = data.get("tls_version", "")

            # Check if JA3 matches known Python urllib (which is detectable)
            python_ja3s = [
                "b32309a26951912be7dba376398abc3b",  # Python 3.11
                "a26d288e39dab14e6e4d1cbc93b5e30e",  # Python requests
            ]
            is_python = ja3 in python_ja3s or "python" in ja3_text.lower()

            score = 0.2 if is_python else 0.8  # urllib always looks like Python
            checks.append(TestCheck(
                name="tls_version", category=TestCategory.TLS,
                result=TestResult.WARN if is_python else TestResult.PASS,
                score=score,
                detail=f"TLS: {tls_version} | JA3: {ja3[:32]}... | {'ΓÜá Python detected' if is_python else 'Browser-like'}",
                severity=Severity.MEDIUM,
                module_blamed="tls_parrot",
                patch_recommendation="This test uses urllib (Python JA3). Real browser via Camoufox will have correct JA4." if is_python else "",
                raw_data={"ja3": ja3, "tls_version": tls_version}))
        except Exception as e:
            checks.append(TestCheck(
                name="tls_version", category=TestCategory.TLS,
                result=TestResult.ERROR, score=0.5, detail=f"TLS test error: {e}",
                module_blamed="tls_parrot"))

        return checks


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# BROWSER-BASED TESTS (Require Playwright + Camoufox/Firefox)
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class BrowserTests:
    """Tests that require a real browser (fingerprint, behavioral, antifraud, session)."""

    @staticmethod
    def run_all(headless: bool = True) -> List[TestCheck]:
        """Run all browser-based tests using Camoufox Python API or Playwright Firefox."""
        checks = []
        browser = None
        page = None
        use_camoufox = False

        # Method 1: Try Camoufox Python API (best ΓÇö includes anti-detection)
        try:
            from camoufox.sync_api import Camoufox
            use_camoufox = True
            logger.info("[BROWSER] Launching via Camoufox Python API (anti-detection active)...")
        except ImportError:
            logger.info("[BROWSER] Camoufox API not available, trying Playwright Firefox...")

        try:
            if use_camoufox:
                from camoufox.sync_api import Camoufox
                cm = Camoufox(headless=headless, humanize=True)
                browser = cm.__enter__()
                page = browser.new_page()
                page.set_default_timeout(30000)
                logger.info("[BROWSER] Camoufox launched with humanize=True")

                checks.append(TestCheck(
                    name="browser_launch", category=TestCategory.BEHAVIORAL,
                    result=TestResult.PASS, score=1.0,
                    detail="Camoufox launched via Python API with anti-detection + humanize",
                    module_blamed="integration_bridge"))

                # Run all browser tests
                checks.extend(BrowserTests._test_bot_sannysoft(page))
                checks.extend(BrowserTests._test_browserleaks_canvas(page))
                checks.extend(BrowserTests._test_browserleaks_webrtc(page))
                checks.extend(BrowserTests._test_creepjs(page))
                checks.extend(BrowserTests._test_cloudflare(page))

                cm.__exit__(None, None, None)

            else:
                # Method 2: Playwright Firefox directly
                from playwright.sync_api import sync_playwright
                pw_ctx = sync_playwright()
                pw = pw_ctx.__enter__()

                # Find Playwright's own Firefox binary
                firefox_path = "/root/.cache/ms-playwright/firefox-1509/firefox/firefox"
                launch_args = {"headless": headless}
                if os.path.exists(firefox_path):
                    launch_args["executable_path"] = firefox_path
                    logger.info(f"[BROWSER] Using Playwright Firefox: {firefox_path}")
                else:
                    logger.info("[BROWSER] Using default Playwright Firefox")

                browser = pw.firefox.launch(**launch_args)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
                    locale="en-US",
                    timezone_id="America/New_York",
                )
                page = context.new_page()
                page.set_default_timeout(30000)

                checks.append(TestCheck(
                    name="browser_launch", category=TestCategory.BEHAVIORAL,
                    result=TestResult.WARN, score=0.6,
                    detail="Playwright Firefox launched (no Camoufox anti-detection)",
                    module_blamed="integration_bridge"))

                # Run all browser tests
                checks.extend(BrowserTests._test_bot_sannysoft(page))
                checks.extend(BrowserTests._test_browserleaks_canvas(page))
                checks.extend(BrowserTests._test_browserleaks_webrtc(page))
                checks.extend(BrowserTests._test_creepjs(page))
                checks.extend(BrowserTests._test_cloudflare(page))

                browser.close()
                pw_ctx.__exit__(None, None, None)

        except Exception as e:
            logger.error(f"Browser test error: {e}")
            traceback.print_exc()
            checks.append(TestCheck(
                name="browser_launch", category=TestCategory.BEHAVIORAL,
                result=TestResult.ERROR, score=0.0,
                detail=f"Browser launch failed: {e}",
                severity=Severity.CRITICAL,
                module_blamed="integration_bridge"))

        return checks

    @staticmethod
    def _test_bot_sannysoft(page) -> List[TestCheck]:
        """Bot detection via sannysoft."""
        checks = []
        try:
            page.goto("https://bot.sannysoft.com/", wait_until="networkidle", timeout=20000)
            time.sleep(3)

            # Count passed/failed tests on page
            results = page.evaluate("""() => {
                const rows = document.querySelectorAll('table tr');
                let pass_count = 0, fail_count = 0, tests = [];
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        const name = cells[0].textContent.trim();
                        const result = cells[1].textContent.trim();
                        const passed = cells[1].classList.contains('passed') ||
                                       result.toLowerCase().includes('ok') ||
                                       !cells[1].classList.contains('failed');
                        if (passed) pass_count++; else fail_count++;
                        tests.push({name, result, passed});
                    }
                });
                return {pass_count, fail_count, tests: tests.slice(0, 30)};
            }""")

            total = results["pass_count"] + results["fail_count"]
            score = results["pass_count"] / max(total, 1)

            failed_tests = [t["name"] for t in results.get("tests", []) if not t.get("passed")]

            checks.append(TestCheck(
                name="bot_detection_sannysoft",
                category=TestCategory.BEHAVIORAL,
                result=TestResult.PASS if score > 0.9 else TestResult.WARN if score > 0.7 else TestResult.FAIL,
                score=score,
                detail=f"Sannysoft: {results['pass_count']}/{total} passed | Failed: {', '.join(failed_tests[:5]) if failed_tests else 'none'}",
                severity=Severity.HIGH if score < 0.7 else Severity.MEDIUM,
                module_blamed="ghost_motor_v6",
                patch_recommendation=f"Fix failed checks: {', '.join(failed_tests[:3])}" if failed_tests else "",
                raw_data=results))

        except Exception as e:
            checks.append(TestCheck(
                name="bot_detection_sannysoft", category=TestCategory.BEHAVIORAL,
                result=TestResult.ERROR, score=0.5, detail=f"Sannysoft error: {e}",
                module_blamed="ghost_motor_v6"))
        return checks

    @staticmethod
    def _test_browserleaks_canvas(page) -> List[TestCheck]:
        """Canvas fingerprint via browserleaks."""
        checks = []
        try:
            page.goto("https://browserleaks.com/canvas", wait_until="networkidle", timeout=20000)
            time.sleep(2)

            # Check if canvas fingerprint is unique or randomized
            result = page.evaluate("""() => {
                const el = document.querySelector('#canvas-hash') || document.querySelector('.hash');
                return el ? el.textContent.trim() : 'not_found';
            }""")

            has_hash = result and result != "not_found" and len(result) > 8
            checks.append(TestCheck(
                name="canvas_fingerprint", category=TestCategory.FINGERPRINT,
                result=TestResult.PASS if has_hash else TestResult.WARN,
                score=0.8 if has_hash else 0.4,
                detail=f"Canvas hash: {result[:32]}..." if has_hash else "Canvas hash not detected",
                module_blamed="canvas_subpixel_shim",
                raw_data={"hash": result}))
        except Exception as e:
            checks.append(TestCheck(
                name="canvas_fingerprint", category=TestCategory.FINGERPRINT,
                result=TestResult.ERROR, score=0.5, detail=str(e),
                module_blamed="canvas_subpixel_shim"))
        return checks

    @staticmethod
    def _test_browserleaks_webrtc(page) -> List[TestCheck]:
        """WebRTC IP leak detection."""
        checks = []
        try:
            page.goto("https://browserleaks.com/webrtc", wait_until="networkidle", timeout=20000)
            time.sleep(3)

            leak_data = page.evaluate("""() => {
                const el = document.querySelector('#webrtc-leak-test');
                const ips = document.querySelectorAll('.ip-address, .local-ip');
                const localIPs = [];
                ips.forEach(e => { if (e.textContent.trim()) localIPs.push(e.textContent.trim()); });
                return {localIPs, text: el ? el.textContent.substring(0, 500) : ''};
            }""")

            local_ips = leak_data.get("localIPs", [])
            has_leak = any(ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.") for ip in local_ips)

            checks.append(TestCheck(
                name="webrtc_ip_leak", category=TestCategory.LEAK,
                result=TestResult.FAIL if has_leak else TestResult.PASS,
                score=0.0 if has_leak else 1.0,
                detail=f"WebRTC local IPs: {local_ips}" if has_leak else "No WebRTC IP leak detected",
                severity=Severity.CRITICAL if has_leak else Severity.LOW,
                module_blamed="fingerprint_injector",
                patch_recommendation="WebRTC leaking local IPs! Disable WebRTC or inject fake IPs." if has_leak else "",
                raw_data=leak_data))
        except Exception as e:
            checks.append(TestCheck(
                name="webrtc_ip_leak", category=TestCategory.LEAK,
                result=TestResult.ERROR, score=0.5, detail=str(e),
                module_blamed="fingerprint_injector"))
        return checks

    @staticmethod
    def _test_creepjs(page) -> List[TestCheck]:
        """CreepJS advanced bot/fingerprint detection."""
        checks = []
        try:
            page.goto("https://abrahamjuliot.github.io/creepjs/", wait_until="networkidle", timeout=30000)
            time.sleep(8)  # CreepJS takes time to run all tests

            result = page.evaluate("""() => {
                const trustEl = document.querySelector('.trust-score') || document.querySelector('[class*="trust"]');
                const gradeEl = document.querySelector('.grade') || document.querySelector('[class*="grade"]');
                const lies = document.querySelectorAll('.lies, [class*="lie"]');
                return {
                    trust: trustEl ? trustEl.textContent.trim() : 'unknown',
                    grade: gradeEl ? gradeEl.textContent.trim() : 'unknown',
                    lie_count: lies.length,
                    page_text: document.body.textContent.substring(0, 2000)
                };
            }""")

            trust = result.get("trust", "unknown")
            grade = result.get("grade", "unknown")

            # Parse trust score if numeric
            trust_num = 0
            try:
                trust_num = float(trust.replace("%", "").strip())
            except:
                pass

            score = trust_num / 100 if trust_num > 0 else 0.5

            checks.append(TestCheck(
                name="bot_detection_creepjs", category=TestCategory.FINGERPRINT,
                result=TestResult.PASS if score > 0.7 else TestResult.WARN if score > 0.4 else TestResult.FAIL,
                score=score,
                detail=f"CreepJS trust: {trust}, Grade: {grade}, Lies detected: {result.get('lie_count', 0)}",
                severity=Severity.HIGH if score < 0.5 else Severity.MEDIUM,
                module_blamed="fingerprint_injector",
                patch_recommendation=f"CreepJS trust score low ({trust}). Review fingerprint consistency." if score < 0.7 else "",
                raw_data=result))
        except Exception as e:
            checks.append(TestCheck(
                name="bot_detection_creepjs", category=TestCategory.FINGERPRINT,
                result=TestResult.ERROR, score=0.5, detail=f"CreepJS error: {e}",
                module_blamed="fingerprint_injector"))
        return checks

    @staticmethod
    def _test_cloudflare(page) -> List[TestCheck]:
        """Test Cloudflare challenge pass-through."""
        checks = []
        try:
            # Visit a Cloudflare-protected site
            page.goto("https://www.cloudflare.com/", wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)

            # Check if we got through (no challenge page)
            title = page.title()
            url = page.url
            is_challenge = "challenge" in url.lower() or "just a moment" in title.lower() or "ray id" in title.lower()
            is_blocked = "blocked" in title.lower() or "access denied" in title.lower()

            if is_blocked:
                result = TestResult.FAIL
                score = 0.0
                detail = f"Cloudflare BLOCKED us. Title: {title}"
            elif is_challenge:
                result = TestResult.WARN
                score = 0.3
                detail = f"Cloudflare challenge triggered. URL: {url}"
            else:
                result = TestResult.PASS
                score = 1.0
                detail = f"Cloudflare passed cleanly. Title: {title[:50]}"

            checks.append(TestCheck(
                name="cloudflare_challenge", category=TestCategory.ANTIFRAUD,
                result=result, score=score, detail=detail,
                severity=Severity.HIGH if score < 0.5 else Severity.LOW,
                module_blamed="fingerprint_injector",
                patch_recommendation="Cloudflare challenge triggered. Improve TLS + fingerprint consistency." if score < 0.7 else "",
                raw_data={"title": title, "url": url}))
        except Exception as e:
            checks.append(TestCheck(
                name="cloudflare_challenge", category=TestCategory.ANTIFRAUD,
                result=TestResult.ERROR, score=0.5, detail=str(e),
                module_blamed="fingerprint_injector"))
        return checks


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# PATCH ENGINE ΓÇö Generates and applies patches to TITAN core modules
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class PatchEngine:
    """Generates patch recommendations and can apply them to core modules."""

    PATCH_RULES = {
        "mullvad_vpn": {
            "ip_fraud_score": {"action": "rotate_exit", "param": "MULLVAD_COUNTRY", "description": "Rotate to different Mullvad country"},
            "ip_vpn_detected": {"action": "add_residential", "param": "TITAN_PROXY_MODE", "description": "Add residential proxy overlay"},
            "ip_datacenter_flag": {"action": "rotate_exit", "param": "MULLVAD_CITY", "description": "Try different city exit"},
        },
        "fingerprint_injector": {
            "webrtc_ip_leak": {"action": "disable_webrtc", "param": "media.peerconnection.enabled", "description": "Disable WebRTC in browser prefs"},
            "navigator_properties": {"action": "update_nav", "param": "fingerprint_navigator_override", "description": "Update navigator property overrides"},
        },
        "canvas_subpixel_shim": {
            "canvas_fingerprint": {"action": "increase_noise", "param": "canvas_noise_amplitude", "description": "Increase canvas noise amplitude"},
        },
        "ghost_motor_v6": {
            "bot_detection_sannysoft": {"action": "adjust_motion", "param": "mouse_speed_variance", "description": "Adjust mouse movement variance"},
            "bot_detection_creepjs": {"action": "adjust_timing", "param": "interaction_delay_ms", "description": "Adjust interaction timing"},
        },
        "tls_parrot": {
            "ja4_fingerprint": {"action": "rotate_target", "param": "tls_target_browser", "description": "Rotate TLS target browser profile"},
        },
    }

    @staticmethod
    def generate_patches(checks: List[TestCheck]) -> List[Dict]:
        """Generate patch recommendations from test results."""
        patches = []
        for check in checks:
            if check.result in (TestResult.FAIL, TestResult.WARN) and check.score < 0.7:
                module = check.module_blamed
                test_name = check.name
                rule = PatchEngine.PATCH_RULES.get(module, {}).get(test_name)
                if rule:
                    patches.append({
                        "module": module,
                        "test": test_name,
                        "action": rule["action"],
                        "parameter": rule["param"],
                        "description": rule["description"],
                        "current_score": check.score,
                        "severity": check.severity.value,
                        "detail": check.detail,
                    })
                elif check.patch_recommendation:
                    patches.append({
                        "module": module,
                        "test": test_name,
                        "action": "manual",
                        "parameter": "",
                        "description": check.patch_recommendation,
                        "current_score": check.score,
                        "severity": check.severity.value,
                    })
        return patches


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# DETECTION LAB ΓÇö Main Orchestrator
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class DetectionLab:
    """
    Main detection lab orchestrator. Runs all tests, scores modules,
    predicts success rate, and generates patch recommendations.
    """

    def __init__(self):
        self.db = ResultsDB()
        self.report: Optional[LabReport] = None

    def run(self, categories: Optional[List[TestCategory]] = None,
            headless: bool = True) -> LabReport:
        """Run detection lab tests."""
        run_id = f"DL-{datetime.now().strftime('%Y%m%d_%H%M%S')}-{uuid.uuid4().hex[:6]}"
        categories = categories or list(TestCategory)

        self.report = LabReport(
            run_id=run_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info("=" * 70)
        logger.info(f"  TITAN DETECTION LAB ΓÇö Run {run_id}")
        logger.info(f"  Categories: {[c.value for c in categories]}")
        logger.info("=" * 70)

        # Load titan.env
        try:
            from titan_env import load_env
            load_env()
        except:
            pass

        # Run non-browser tests first
        if TestCategory.IP_REPUTATION in categories:
            self.report.checks.extend(IPReputationTests.run())

        if TestCategory.LEAK in categories:
            self.report.checks.extend(LeakTests.run())

        if TestCategory.TLS in categories:
            self.report.checks.extend(TLSTests.run())

        # Run browser-based tests
        browser_cats = {TestCategory.FINGERPRINT, TestCategory.BEHAVIORAL,
                        TestCategory.ANTIFRAUD, TestCategory.SESSION}
        if browser_cats & set(categories):
            self.report.checks.extend(BrowserTests.run_all(headless=headless))

        # Calculate scores
        self.report.module_scores = calculate_module_scores(self.report.checks)
        self.report.category_scores = calculate_category_scores(self.report.checks)
        self.report.overall_score = sum(c.score for c in self.report.checks) / max(len(self.report.checks), 1)
        self.report.predicted_success_rate = predict_success_rate(self.report.category_scores)
        self.report.patches_recommended = PatchEngine.generate_patches(self.report.checks)
        self.report.ended_at = datetime.now(timezone.utc).isoformat()

        # Save to DB
        self.db.save_run(self.report)

        # Print report
        self._print_report()

        # Save JSON report
        report_path = Path("/opt/titan/data/detection_lab_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(self.report.to_dict(), indent=2))
        logger.info(f"\nReport saved: {report_path}")

        return self.report

    def _print_report(self):
        r = self.report
        print(f"\n{'='*70}")
        print(f"  DETECTION LAB REPORT ΓÇö {r.run_id}")
        print(f"{'='*70}")

        passed = sum(1 for c in r.checks if c.result == TestResult.PASS)
        warned = sum(1 for c in r.checks if c.result == TestResult.WARN)
        failed = sum(1 for c in r.checks if c.result == TestResult.FAIL)
        errors = sum(1 for c in r.checks if c.result == TestResult.ERROR)
        skipped = sum(1 for c in r.checks if c.result == TestResult.SKIP)

        print(f"\n  PASS: {passed}  |  WARN: {warned}  |  FAIL: {failed}  |  ERROR: {errors}  |  SKIP: {skipped}")
        print(f"  OVERALL SCORE: {r.overall_score:.1%}")
        print(f"  PREDICTED SUCCESS RATE: {r.predicted_success_rate:.1f}%")

        print(f"\n  ΓöÇΓöÇ MODULE SCORES ΓöÇΓöÇ")
        for mod, score in sorted(r.module_scores.items(), key=lambda x: x[1]):
            bar = "Γûê" * int(score * 20) + "Γûæ" * (20 - int(score * 20))
            icon = "Γ£ô" if score >= 0.7 else "ΓÜá" if score >= 0.4 else "Γ£ù"
            print(f"    {icon} {mod:40s} {bar} {score:.0%}")

        print(f"\n  ΓöÇΓöÇ CATEGORY SCORES ΓöÇΓöÇ")
        for cat, score in sorted(r.category_scores.items(), key=lambda x: x[1]):
            bar = "Γûê" * int(score * 20) + "Γûæ" * (20 - int(score * 20))
            print(f"    {cat:20s} {bar} {score:.0%}")

        if r.patches_recommended:
            print(f"\n  ΓöÇΓöÇ PATCH RECOMMENDATIONS ({len(r.patches_recommended)}) ΓöÇΓöÇ")
            for p in r.patches_recommended:
                print(f"    [{p['severity'].upper()}] {p['module']}: {p['description']}")

        print(f"\n{'='*70}")


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# CLI
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

def main():
    import argparse
    parser = argparse.ArgumentParser(description="TITAN Detection Lab")
    parser.add_argument("action", choices=["run", "report", "history", "patch"],
                        help="Action to perform")
    parser.add_argument("--test", "-t", choices=[c.value for c in TestCategory],
                        help="Run specific test category only")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser in headless mode (default)")
    parser.add_argument("--visible", action="store_true",
                        help="Run browser in visible mode (needs DISPLAY)")
    args = parser.parse_args()

    lab = DetectionLab()

    if args.action == "run":
        categories = [TestCategory(args.test)] if args.test else None
        headless = not args.visible
        lab.run(categories=categories, headless=headless)

    elif args.action == "report":
        report = lab.db.get_latest_report()
        if report:
            print(json.dumps(report, indent=2))
        else:
            print("No reports found. Run 'python3 titan_detection_lab.py run' first.")

    elif args.action == "history":
        history = lab.db.get_history()
        if history:
            print(f"{'Run ID':40s} {'Score':8s} {'Rate':8s} {'Pass':6s} {'Fail':6s}")
            print("-" * 70)
            for h in history:
                print(f"{h['run_id']:40s} {h['overall_score']:7.1%} {h['predicted_success_rate']:6.1f}% {h['passed']:5d} {h['failed']:5d}")
        else:
            print("No history found.")

    elif args.action == "patch":
        report = lab.db.get_latest_report()
        if report and report.get("patches_recommended"):
            print(f"Patches from latest run:")
            for p in report["patches_recommended"]:
                print(f"  [{p['severity']}] {p['module']}: {p['description']}")
            print(f"\nTotal: {len(report['patches_recommended'])} patches recommended")
        else:
            print("No patches recommended. Run tests first.")


if __name__ == "__main__":
    main()
