#!/usr/bin/env python3
"""
TITAN V8.0 MAXIMUM LEVEL — Autonomous Self-Improving Operation Engine
═══════════════════════════════════════════════════════════════════════════════

24/7 fully automated operation loop with continuous self-improvement:

    ┌─────────────────────────────────────────────────────┐
    │                  AUTONOMOUS LOOP                     │
    │                                                      │
    │  1. INGEST   → Load task queue (cards, targets)      │
    │  2. PROFILE  → Generate full profile (all inputs)    │
    │  3. EXECUTE  → Run operation via orchestrator        │
    │  4. DETECT   → Identify detection signals            │
    │  5. RECORD   → Log result + metrics to SQLite        │
    │  6. LEARN    → Feed result to AI Operations Guard    │
    │  7. PATCH    → Self-patch if success rate drops      │
    │  8. COOLDOWN → Wait adaptive delay, then loop        │
    │                                                      │
    │  END-OF-DAY: Aggregate metrics → analyze failures    │
    │  → generate patch plan → apply → validate → repeat   │
    └─────────────────────────────────────────────────────┘

Components:
    - TaskQueue: Ingests cards + targets from JSON/dir
    - MetricsDB: SQLite tracker for every operation
    - DetectionAnalyzer: Categorizes and tracks detections
    - AdaptiveScheduler: Adjusts timing based on success
    - SelfPatcher: End-of-day failure analysis → param tuning
    - AutonomousEngine: Master loop tying everything together

Usage:
    from titan_autonomous_engine import AutonomousEngine
    
    engine = AutonomousEngine()
    engine.load_tasks("/opt/titan/tasks/")
    engine.start()  # Runs 24/7 in background
    
    # Or one-shot
    engine.run_cycle()

Author: Dva.12
Version: 8.0.0
"""

import json
import hashlib
import logging
import os
import sqlite3
import threading
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger("TITAN-AUTONOMOUS")

__version__ = "8.0.0"
__author__ = "Dva.12"


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DETECTED = "detected"
    COOLDOWN = "cooldown"
    SKIPPED = "skipped"


class PatchAction(Enum):
    INCREASE_WARMUP = "increase_warmup"
    CHANGE_PROXY_GEO = "change_proxy_geo"
    INCREASE_PROFILE_AGE = "increase_profile_age"
    CHANGE_BROWSER_TARGET = "change_browser_target"
    ADJUST_MOUSE_SPEED = "adjust_mouse_speed"
    ADJUST_TYPING_SPEED = "adjust_typing_speed"
    ENABLE_MODULE = "enable_module"
    DISABLE_MODULE = "disable_module"
    ADJUST_THRESHOLD = "adjust_threshold"
    ROTATE_JA4_TARGET = "rotate_ja4_target"
    INCREASE_STORAGE = "increase_storage"
    ADD_LSNG_DATA = "add_lsng_data"


class DetectionCategory(Enum):
    IP_BLOCKED = "ip_blocked"
    FINGERPRINT = "fingerprint"
    BEHAVIORAL = "behavioral"
    VELOCITY = "velocity"
    CARD_DECLINE = "card_decline"
    THREE_DS = "3ds_challenge"
    CAPTCHA = "captcha"
    ACCOUNT_LOCK = "account_lock"
    FRAUD_BLOCK = "fraud_block"
    PROFILE_AGE = "profile_age"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskInput:
    """Single task with all required inputs."""
    task_id: str
    card_number: str
    card_exp: str
    card_cvv: str
    billing_first: str
    billing_last: str
    billing_street: str
    billing_city: str
    billing_state: str
    billing_zip: str
    billing_country: str = "US"
    billing_phone: str = ""
    billing_email: str = ""
    target_url: str = ""
    target_domain: str = ""
    persona_dob: str = "1990-01-15"
    persona_gender: str = "male"
    persona_occupation: str = "Software Engineer"
    profile_age_days: int = 90
    amount: float = 0.0
    priority: int = 5
    max_retries: int = 3
    retries_used: int = 0
    status: str = "queued"
    last_error: str = ""
    last_detection: str = ""
    created_at: str = ""
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"T-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.target_domain and self.target_url:
            from urllib.parse import urlparse
            self.target_domain = urlparse(self.target_url).netloc


@dataclass
class CycleMetrics:
    """Metrics for a single autonomous cycle."""
    cycle_id: str
    started_at: str
    ended_at: str = ""
    tasks_attempted: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_detected: int = 0
    detections: Dict[str, int] = field(default_factory=dict)
    patches_applied: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SelfPatchRecord:
    """Record of a self-improvement patch."""
    patch_id: str
    action: PatchAction
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    applied_at: str
    success_rate_before: float
    success_rate_after: Optional[float] = None
    effective: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS DATABASE — SQLite tracker for every operation
# ═══════════════════════════════════════════════════════════════════════════════

class MetricsDB:
    """Persistent SQLite database for operation metrics and learning."""
    
    DB_PATH = Path("/opt/titan/data/autonomous_metrics.db")
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""CREATE TABLE IF NOT EXISTS operations (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            cycle_id TEXT,
            target_domain TEXT,
            card_bin TEXT,
            status TEXT,
            detection_type TEXT,
            phase_failed TEXT,
            duration_ms REAL,
            profile_age_days INTEGER,
            proxy_country TEXT,
            warmup_duration INTEGER,
            browser_type TEXT,
            success INTEGER,
            error_message TEXT,
            created_at TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT,
            category TEXT,
            details TEXT,
            target_domain TEXT,
            card_bin TEXT,
            created_at TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS patches (
            id TEXT PRIMARY KEY,
            action TEXT,
            parameter TEXT,
            old_value TEXT,
            new_value TEXT,
            reason TEXT,
            success_rate_before REAL,
            success_rate_after REAL,
            effective INTEGER,
            applied_at TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            total_ops INTEGER,
            successes INTEGER,
            failures INTEGER,
            detections INTEGER,
            success_rate REAL,
            top_detection TEXT,
            patches_applied INTEGER,
            avg_duration_ms REAL
        )""")
        
        conn.commit()
    
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def record_operation(self, op_id: str, task_id: str, cycle_id: str,
                         target_domain: str, card_bin: str, status: str,
                         detection_type: str, phase_failed: str,
                         duration_ms: float, profile_age: int,
                         proxy_country: str, warmup: int,
                         browser_type: str, success: bool, error: str):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """INSERT OR REPLACE INTO operations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (op_id, task_id, cycle_id, target_domain, card_bin, status,
                 detection_type, phase_failed, duration_ms, profile_age,
                 proxy_country, warmup, browser_type, int(success), error,
                 datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
    
    def record_detection(self, op_id: str, category: str, details: str,
                         target: str, card_bin: str):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO detections (operation_id, category, details, target_domain, card_bin, created_at) VALUES (?,?,?,?,?,?)",
                (op_id, category, details, target, card_bin,
                 datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
    
    def record_patch(self, record: SelfPatchRecord):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO patches VALUES (?,?,?,?,?,?,?,?,?,?)",
                (record.patch_id, record.action.value, record.parameter,
                 str(record.old_value), str(record.new_value), record.reason,
                 record.success_rate_before, record.success_rate_after,
                 int(record.effective) if record.effective is not None else None,
                 record.applied_at)
            )
            conn.commit()
    
    def get_success_rate(self, hours: int = 24) -> float:
        """Get success rate over last N hours."""
        with self._lock:
            conn = self._get_conn()
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            row = conn.execute(
                "SELECT COUNT(*) as total, SUM(success) as wins FROM operations WHERE created_at > ?",
                (cutoff,)
            ).fetchone()
            if row and row["total"] > 0:
                return (row["wins"] or 0) / row["total"]
            return 0.0
    
    def get_detection_breakdown(self, hours: int = 24) -> Dict[str, int]:
        """Get detection type breakdown."""
        with self._lock:
            conn = self._get_conn()
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            rows = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM detections WHERE created_at > ? GROUP BY category ORDER BY cnt DESC",
                (cutoff,)
            ).fetchall()
            return {r["category"]: r["cnt"] for r in rows}
    
    def get_failure_by_phase(self, hours: int = 24) -> Dict[str, int]:
        """Get failure breakdown by phase."""
        with self._lock:
            conn = self._get_conn()
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            rows = conn.execute(
                "SELECT phase_failed, COUNT(*) as cnt FROM operations WHERE success=0 AND created_at > ? GROUP BY phase_failed ORDER BY cnt DESC",
                (cutoff,)
            ).fetchall()
            return {r["phase_failed"]: r["cnt"] for r in rows}
    
    def get_failure_by_target(self, hours: int = 24) -> Dict[str, float]:
        """Get success rate per target domain."""
        with self._lock:
            conn = self._get_conn()
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            rows = conn.execute(
                "SELECT target_domain, COUNT(*) as total, SUM(success) as wins FROM operations WHERE created_at > ? GROUP BY target_domain HAVING total >= 2 ORDER BY (CAST(wins AS REAL)/total) ASC",
                (cutoff,)
            ).fetchall()
            return {r["target_domain"]: (r["wins"] or 0) / r["total"] for r in rows}
    
    def get_total_ops(self) -> int:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute("SELECT COUNT(*) as cnt FROM operations").fetchone()
            return row["cnt"] if row else 0
    
    def save_daily_summary(self, date_str: str, summary: Dict):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO daily_summary VALUES (?,?,?,?,?,?,?,?,?)",
                (date_str, summary.get("total_ops", 0), summary.get("successes", 0),
                 summary.get("failures", 0), summary.get("detections", 0),
                 summary.get("success_rate", 0), summary.get("top_detection", ""),
                 summary.get("patches_applied", 0), summary.get("avg_duration_ms", 0))
            )
            conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# TASK QUEUE — Ingests cards + targets from JSON files or directories
# ═══════════════════════════════════════════════════════════════════════════════

class TaskQueue:
    """Manages the queue of tasks to execute."""
    
    QUEUE_DIR = Path("/opt/titan/tasks")
    
    def __init__(self, queue_dir: Optional[Path] = None):
        self.queue_dir = queue_dir or self.QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: List[TaskInput] = []
        self._lock = threading.Lock()
    
    @staticmethod
    def _read_json_locked(filepath: Path) -> Any:
        """P1-7 FIX: Read JSON file with file locking to prevent partial reads."""
        f = open(filepath, "r")
        try:
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared read lock
            except (ImportError, OSError):
                pass  # Windows or unsupported — thread lock is sufficient
            data = json.load(f)
        finally:
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            f.close()
        return data

    def load_from_directory(self):
        """Load all task JSON files from the tasks directory."""
        with self._lock:
            for json_file in sorted(self.queue_dir.glob("*.json")):
                if json_file.name.startswith("_"):
                    continue  # Skip internal state files
                try:
                    data = self._read_json_locked(json_file)
                    if isinstance(data, list):
                        for item in data:
                            self._add_task_from_dict(item)
                    elif isinstance(data, dict):
                        if "tasks" in data:
                            for item in data["tasks"]:
                                self._add_task_from_dict(item)
                        else:
                            self._add_task_from_dict(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Malformed JSON in {json_file.name} — skipping: {e}")
                except Exception as e:
                    logger.warning(f"Failed to load task file {json_file}: {e}")
            
            logger.info(f"Task queue loaded: {len(self._tasks)} tasks from {self.queue_dir}")
    
    def _add_task_from_dict(self, d: Dict):
        """Parse a dict into a TaskInput and add to queue."""
        try:
            # Support nested card/billing/persona format
            card = d.get("card", {})
            billing = d.get("billing", {})
            persona = d.get("persona", {})
            
            task = TaskInput(
                task_id=d.get("task_id", ""),
                card_number=card.get("number", d.get("card_number", "")),
                card_exp=card.get("exp", d.get("card_exp", "")),
                card_cvv=card.get("cvv", d.get("card_cvv", "")),
                billing_first=billing.get("first_name", d.get("billing_first", "")),
                billing_last=billing.get("last_name", d.get("billing_last", "")),
                billing_street=billing.get("street", d.get("billing_street", "")),
                billing_city=billing.get("city", d.get("billing_city", "")),
                billing_state=billing.get("state", d.get("billing_state", "")),
                billing_zip=billing.get("zip_code", d.get("billing_zip", "")),
                billing_country=billing.get("country", d.get("billing_country", "US")),
                billing_phone=billing.get("phone", d.get("billing_phone", "")),
                billing_email=billing.get("email", d.get("billing_email", "")),
                target_url=d.get("target_url", d.get("target", {}).get("url", "")),
                target_domain=d.get("target_domain", ""),
                persona_dob=persona.get("dob", d.get("persona_dob", "1990-01-15")),
                persona_gender=persona.get("gender", d.get("persona_gender", "male")),
                persona_occupation=persona.get("occupation", d.get("persona_occupation", "Software Engineer")),
                profile_age_days=d.get("profile_age_days", 90),
                amount=d.get("amount", 0.0),
                priority=d.get("priority", 5),
                max_retries=d.get("max_retries", 3),
            )
            
            if task.card_number:
                self._tasks.append(task)
        except Exception as e:
            logger.warning(f"Failed to parse task: {e}")
    
    def add_task(self, task: TaskInput):
        with self._lock:
            self._tasks.append(task)
    
    def get_next(self) -> Optional[TaskInput]:
        """Get the next queued task (highest priority first)."""
        with self._lock:
            queued = [t for t in self._tasks if t.status == "queued"]
            if not queued:
                return None
            queued.sort(key=lambda t: t.priority, reverse=True)
            task = queued[0]
            task.status = "running"
            return task
    
    def mark_done(self, task_id: str, status: str, error: str = "", detection: str = ""):
        with self._lock:
            for t in self._tasks:
                if t.task_id == task_id:
                    t.status = status
                    t.last_error = error
                    t.last_detection = detection
                    if status in ("failed", "detected") and t.retries_used < t.max_retries:
                        t.retries_used += 1
                        t.status = "queued"  # Re-queue for retry
                    break
    
    def requeue_failed(self):
        """Re-queue failed tasks that have retries remaining."""
        with self._lock:
            for t in self._tasks:
                if t.status in ("failed", "detected") and t.retries_used < t.max_retries:
                    t.status = "queued"
    
    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks if t.status == "queued")
    
    def stats(self) -> Dict[str, int]:
        with self._lock:
            counts = defaultdict(int)
            for t in self._tasks:
                counts[t.status] += 1
            return dict(counts)
    
    def save_state(self):
        """Persist queue state to disk."""
        state_file = self.queue_dir / "_queue_state.json"
        with self._lock:
            data = [asdict(t) for t in self._tasks]
            state_file.write_text(json.dumps(data, indent=2))
    
    def load_state(self):
        """Load persisted queue state."""
        state_file = self.queue_dir / "_queue_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                self._tasks = []
                for d in data:
                    self._tasks.append(TaskInput(**d))
            except Exception as e:
                logger.warning(f"Failed to load queue state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION ANALYZER — Categorizes detections and finds patterns
# ═══════════════════════════════════════════════════════════════════════════════

class DetectionAnalyzer:
    """Analyzes detection patterns and recommends countermeasures."""
    
    # Detection → likely root cause → patch action mapping
    COUNTERMEASURE_MAP = {
        DetectionCategory.IP_BLOCKED: [
            (PatchAction.CHANGE_PROXY_GEO, "proxy_manager", "GEO_MATCH_REQUIRED", True),
        ],
        DetectionCategory.FINGERPRINT: [
            (PatchAction.ROTATE_JA4_TARGET, "ja4_permutation_engine", "TARGET_BROWSER", "CHROME_133"),
            (PatchAction.INCREASE_STORAGE, "genesis_core", "STORAGE_TARGET_MB", 700),
        ],
        DetectionCategory.BEHAVIORAL: [
            (PatchAction.ADJUST_MOUSE_SPEED, "ghost_motor_v6", "MOUSE_SPEED_VARIANCE", 0.4),
            (PatchAction.ADJUST_TYPING_SPEED, "ghost_motor_v6", "TYPING_SPEED_CPM", 200),
            (PatchAction.INCREASE_WARMUP, "integration_bridge", "WARMUP_DURATION", 60),
        ],
        DetectionCategory.VELOCITY: [
            (PatchAction.ADJUST_THRESHOLD, "cerberus_core", "MAX_ATTEMPTS", 2),
        ],
        DetectionCategory.PROFILE_AGE: [
            (PatchAction.INCREASE_PROFILE_AGE, "genesis_core", "MIN_PROFILE_AGE", 120),
            (PatchAction.ADD_LSNG_DATA, "integration_bridge", "ENABLE_FSB_ELIMINATION", True),
        ],
        DetectionCategory.CAPTCHA: [
            (PatchAction.INCREASE_WARMUP, "integration_bridge", "WARMUP_DURATION", 45),
        ],
        DetectionCategory.THREE_DS: [
            (PatchAction.ENABLE_MODULE, "cerberus_core", "ENABLE_TRA", True),
            (PatchAction.ENABLE_MODULE, "integration_bridge", "ENABLE_ISSUER_DEFENSE", True),
        ],
    }
    
    def __init__(self, metrics_db: MetricsDB):
        self.db = metrics_db
    
    def analyze(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze detection patterns over last N hours."""
        detections = self.db.get_detection_breakdown(hours)
        phase_failures = self.db.get_failure_by_phase(hours)
        target_rates = self.db.get_failure_by_target(hours)
        success_rate = self.db.get_success_rate(hours)
        
        # Find top detection
        top_detection = max(detections, key=detections.get) if detections else "none"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(detections, phase_failures, success_rate)
        
        return {
            "period_hours": hours,
            "success_rate": success_rate,
            "detection_breakdown": detections,
            "phase_failures": phase_failures,
            "worst_targets": {k: v for k, v in list(target_rates.items())[:5]},
            "top_detection": top_detection,
            "recommendations": recommendations,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _generate_recommendations(self, detections: Dict, phase_failures: Dict,
                                   success_rate: float) -> List[Dict]:
        """Generate patch recommendations based on detection patterns."""
        recs = []
        
        for det_str, count in detections.items():
            if count < 2:
                continue
            try:
                category = DetectionCategory(det_str)
            except ValueError:
                continue
            
            actions = self.COUNTERMEASURE_MAP.get(category, [])
            for action, module, param, value in actions:
                recs.append({
                    "action": action.value,
                    "module": module,
                    "parameter": param,
                    "suggested_value": value,
                    "reason": f"{det_str} detected {count} times in last period",
                    "priority": count,
                })
        
        # Sort by priority (most frequent detection first)
        recs.sort(key=lambda r: r["priority"], reverse=True)
        return recs


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-PATCHER — Applies parameter adjustments based on analysis
# ═══════════════════════════════════════════════════════════════════════════════

class SelfPatcher:
    """Applies and tracks self-improvement patches."""
    
    CONFIG_DIR = Path("/opt/titan/config")
    
    def __init__(self, metrics_db: MetricsDB, config_dir: Optional[Path] = None):
        self.db = metrics_db
        self.config_dir = config_dir or self.CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._configs: Dict[str, Dict] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all patchable module configs."""
        from titan_auto_patcher import PATCHABLE_CONFIGS, DEFAULT_CONFIGS
        
        for module, info in PATCHABLE_CONFIGS.items():
            cfg_path = Path(info["config_file"])
            if cfg_path.exists():
                try:
                    self._configs[module] = json.loads(cfg_path.read_text())
                except Exception:
                    self._configs[module] = DEFAULT_CONFIGS.get(module, {})
            else:
                self._configs[module] = DEFAULT_CONFIGS.get(module, {})
    
    def apply_recommendations(self, recommendations: List[Dict]) -> List[SelfPatchRecord]:
        """Apply patch recommendations and record them."""
        applied = []
        current_rate = self.db.get_success_rate(24)
        
        for rec in recommendations:
            module = rec["module"]
            param = rec["parameter"]
            new_value = rec["suggested_value"]
            
            if module not in self._configs:
                continue
            
            old_value = self._configs[module].get(param)
            
            # Skip if already at suggested value
            if old_value == new_value:
                continue
            
            # Apply patch
            self._configs[module][param] = new_value
            
            # Save config
            self._save_config(module)
            
            # Create record
            record = SelfPatchRecord(
                patch_id=f"SP-{uuid.uuid4().hex[:8]}",
                action=PatchAction(rec["action"]),
                parameter=f"{module}.{param}",
                old_value=old_value,
                new_value=new_value,
                reason=rec["reason"],
                applied_at=datetime.now(timezone.utc).isoformat(),
                success_rate_before=current_rate,
            )
            
            self.db.record_patch(record)
            applied.append(record)
            
            logger.info(f"[SELF-PATCH] {module}.{param}: {old_value} → {new_value} ({rec['reason']})")
        
        return applied
    
    def _save_config(self, module: str):
        from titan_auto_patcher import PATCHABLE_CONFIGS
        if module in PATCHABLE_CONFIGS:
            cfg_path = Path(PATCHABLE_CONFIGS[module]["config_file"])
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(json.dumps(self._configs[module], indent=2))
    
    def validate_patches(self, hours_after: int = 4) -> List[SelfPatchRecord]:
        """Validate if patches improved success rate after N hours."""
        current_rate = self.db.get_success_rate(hours_after)
        validated = []
        
        with self.db._lock:
            conn = self.db._get_conn()
            rows = conn.execute(
                "SELECT * FROM patches WHERE effective IS NULL"
            ).fetchall()
        
        for row in rows:
            effective = current_rate > row["success_rate_before"]
            record = SelfPatchRecord(
                patch_id=row["id"],
                action=PatchAction(row["action"]),
                parameter=row["parameter"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                reason=row["reason"],
                applied_at=row["applied_at"],
                success_rate_before=row["success_rate_before"],
                success_rate_after=current_rate,
                effective=effective,
            )
            self.db.record_patch(record)
            validated.append(record)
            
            if not effective:
                logger.warning(f"[SELF-PATCH] Patch {row['id']} NOT effective — rolling back")
                # Roll back: restore old value
                parts = row["parameter"].split(".", 1)
                if len(parts) == 2:
                    module, param = parts
                    if module in self._configs:
                        self._configs[module][param] = json.loads(row["old_value"]) if row["old_value"].startswith(("{", "[", "\"")) else row["old_value"]
                        self._save_config(module)
        
        return validated


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE SCHEDULER — Adjusts delays based on success rate
# ═══════════════════════════════════════════════════════════════════════════════

class AdaptiveScheduler:
    """Dynamically adjusts operation timing based on success patterns."""
    
    MIN_DELAY = 10       # Minimum seconds between operations
    MAX_DELAY = 300      # Maximum seconds between operations
    BASE_DELAY = 30      # Base delay when success rate is good
    
    def __init__(self, metrics_db: MetricsDB):
        self.db = metrics_db
        self._consecutive_failures = 0
        self._consecutive_successes = 0
    
    def get_delay(self) -> float:
        """Calculate adaptive delay before next operation."""
        success_rate = self.db.get_success_rate(1)  # Last hour
        
        # Exponential backoff on consecutive failures
        if self._consecutive_failures > 0:
            backoff = min(self.BASE_DELAY * (2 ** self._consecutive_failures), self.MAX_DELAY)
            return backoff
        
        # Speed up on high success rate
        if success_rate > 0.8 and self._consecutive_successes > 3:
            return self.MIN_DELAY
        
        # Normal operation
        if success_rate > 0.5:
            return self.BASE_DELAY
        
        # Slow down on low success rate
        return min(self.BASE_DELAY * 3, self.MAX_DELAY)
    
    def record_result(self, success: bool):
        if success:
            self._consecutive_successes += 1
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
    
    def should_pause(self) -> Tuple[bool, str]:
        """Check if we should pause operations."""
        # Pause if 5+ consecutive failures
        if self._consecutive_failures >= 5:
            return True, f"5+ consecutive failures ({self._consecutive_failures})"
        
        # Pause if success rate < 10% over last hour
        rate = self.db.get_success_rate(1)
        total = self.db.get_total_ops()
        if total > 10 and rate < 0.1:
            return True, f"Success rate too low: {rate:.0%}"
        
        return False, ""


# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS ENGINE — Master 24/7 loop
# ═══════════════════════════════════════════════════════════════════════════════

class AutonomousEngine:
    """
    TITAN V8.0 — Fully autonomous 24/7 self-improving operation engine.
    
    Continuously:
    1. Picks tasks from queue
    2. Generates profiles with all inputs
    3. Executes operations via TitanOrchestrator
    4. Tracks detections and metrics
    5. Feeds results to AI Operations Guard
    6. Self-patches based on failure patterns
    7. Repeats forever
    """
    
    STATE_DIR = Path("/opt/titan/state/autonomous")
    
    def __init__(self, task_dir: Optional[Path] = None, 
                 state_dir: Optional[Path] = None):
        self.state_dir = state_dir or self.STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Core components
        self.metrics_db = MetricsDB()
        self.task_queue = TaskQueue(task_dir)
        self.analyzer = DetectionAnalyzer(self.metrics_db)
        self.patcher = SelfPatcher(self.metrics_db)
        self.scheduler = AdaptiveScheduler(self.metrics_db)
        
        # Orchestrator (lazy loaded)
        self._orchestrator = None
        
        # Runtime state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycle_count = 0
        self._current_cycle: Optional[CycleMetrics] = None
        self._last_daily_patch = ""
        self._last_patch_validation = 0.0
        
        logger.info("TITAN Autonomous Engine V8.0 initialized")
    
    def _get_orchestrator(self):
        """Lazy-load orchestrator."""
        if self._orchestrator is None:
            try:
                from titan_automation_orchestrator import TitanOrchestrator
                self._orchestrator = TitanOrchestrator()
            except Exception as e:
                logger.error(f"Failed to load orchestrator: {e}")
        return self._orchestrator
    
    def load_tasks(self, path: Optional[str] = None):
        """Load tasks from directory or file."""
        if path:
            p = Path(path)
            if p.is_dir():
                self.task_queue.queue_dir = p
            elif p.is_file():
                data = json.loads(p.read_text())
                if isinstance(data, list):
                    for d in data:
                        self.task_queue._add_task_from_dict(d)
                return
        
        self.task_queue.load_from_directory()
        
        # Also try to load persisted state
        self.task_queue.load_state()
    
    def start(self):
        """Start the autonomous engine in background thread."""
        if self._running:
            logger.warning("Engine already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._main_loop, daemon=True, name="TitanAutonomous")
        self._thread.start()
        logger.info("═" * 60)
        logger.info("  TITAN AUTONOMOUS ENGINE STARTED — 24/7 MODE")
        logger.info(f"  Tasks queued: {self.task_queue.pending_count()}")
        logger.info("═" * 60)
    
    def stop(self):
        """Stop the engine gracefully."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=30)
        self.task_queue.save_state()
        logger.info("Autonomous engine stopped")
    
    def run_cycle(self) -> Optional[CycleMetrics]:
        """Run a single autonomous cycle (all queued tasks)."""
        cycle_id = f"C-{datetime.now().strftime('%Y%m%d_%H%M%S')}-{self._cycle_count}"
        self._cycle_count += 1
        
        cycle = CycleMetrics(
            cycle_id=cycle_id,
            started_at=datetime.now(timezone.utc).isoformat()
        )
        self._current_cycle = cycle
        
        logger.info(f"[CYCLE {cycle_id}] Starting — {self.task_queue.pending_count()} tasks queued")
        
        durations = []
        
        while self.task_queue.pending_count() > 0 and self._running:
            # Check if we should pause
            should_pause, reason = self.scheduler.should_pause()
            if should_pause:
                logger.warning(f"[CYCLE] Pausing: {reason}")
                # Run self-patch before pause
                self._run_self_patch_cycle()
                time.sleep(300)  # 5 min pause
                self.scheduler._consecutive_failures = 0  # Reset after pause
                continue
            
            # Get next task
            task = self.task_queue.get_next()
            if not task:
                break
            
            # Execute task
            cycle.tasks_attempted += 1
            result = self._execute_task(task, cycle_id)
            
            # Track metrics
            if result.get("success"):
                cycle.tasks_succeeded += 1
                self.scheduler.record_result(True)
            elif result.get("detection_type", "none") != "none":
                cycle.tasks_detected += 1
                det = result.get("detection_type", "unknown")
                cycle.detections[det] = cycle.detections.get(det, 0) + 1
                self.scheduler.record_result(False)
            else:
                cycle.tasks_failed += 1
                self.scheduler.record_result(False)
            
            if result.get("duration_ms"):
                durations.append(result["duration_ms"])
            
            # Adaptive delay
            delay = self.scheduler.get_delay()
            logger.info(f"[CYCLE] Next op in {delay:.0f}s (rate: {self.metrics_db.get_success_rate(1):.0%})")
            
            # Interruptible sleep
            for _ in range(int(delay)):
                if not self._running:
                    break
                time.sleep(1)
        
        # Finalize cycle
        cycle.ended_at = datetime.now(timezone.utc).isoformat()
        cycle.success_rate = cycle.tasks_succeeded / max(cycle.tasks_attempted, 1)
        cycle.avg_duration_ms = sum(durations) / max(len(durations), 1)
        
        logger.info(f"[CYCLE {cycle_id}] Complete — "
                     f"{cycle.tasks_succeeded}/{cycle.tasks_attempted} succeeded "
                     f"({cycle.success_rate:.0%})")
        
        return cycle
    
    def _execute_task(self, task: TaskInput, cycle_id: str) -> Dict:
        """Execute a single task through the full pipeline."""
        op_id = f"OP-{task.task_id}-{int(time.time())}"
        start = time.time()
        result = {"success": False, "detection_type": "none", "phase_failed": "", "error": ""}
        
        try:
            orchestrator = self._get_orchestrator()
            if not orchestrator:
                result["error"] = "Orchestrator not available"
                self._record_result(op_id, task, cycle_id, result, time.time() - start)
                self.task_queue.mark_done(task.task_id, "failed", error=result["error"])
                return result
            
            # Build OperationConfig from TaskInput
            from titan_automation_orchestrator import (
                OperationConfig, BillingAddress, PersonaConfig
            )
            
            billing = BillingAddress(
                first_name=task.billing_first,
                last_name=task.billing_last,
                street=task.billing_street,
                city=task.billing_city,
                state=task.billing_state,
                zip_code=task.billing_zip,
                country=task.billing_country,
                phone=task.billing_phone,
                email=task.billing_email,
            )
            
            persona = PersonaConfig(
                first_name=task.billing_first,
                last_name=task.billing_last,
                dob=task.persona_dob,
                gender=task.persona_gender,
                occupation=task.persona_occupation,
            )
            
            op_config = OperationConfig(
                card_number=task.card_number,
                card_exp=task.card_exp,
                card_cvv=task.card_cvv,
                billing_address=billing,
                persona=persona,
                target_url=task.target_url,
                target_domain=task.target_domain,
                profile_age_days=task.profile_age_days,
                browser_type="camoufox",
                warmup_enabled=True,
                operation_id=op_id,
            )
            
            # Run operation
            op_result = orchestrator.run_operation(op_config)
            
            duration_ms = (time.time() - start) * 1000
            result["success"] = op_result.success
            result["duration_ms"] = duration_ms
            result["detection_type"] = op_result.detection_type.value
            result["phase_failed"] = op_result.final_phase.value if not op_result.success else ""
            result["error"] = op_result.error_message or ""
            
            # Record to metrics DB
            self._record_result(op_id, task, cycle_id, result, duration_ms)
            
            # Feed to AI Operations Guard
            self._feed_to_guard(op_id, task, op_result)
            
            # Mark task done
            status = "success" if op_result.success else (
                "detected" if op_result.detection_type.value != "none" else "failed"
            )
            self.task_queue.mark_done(task.task_id, status, 
                                      error=result["error"],
                                      detection=result["detection_type"])
            
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            result["error"] = str(e)
            result["duration_ms"] = duration_ms
            logger.error(f"[TASK {task.task_id}] Exception: {e}")
            self._record_result(op_id, task, cycle_id, result, duration_ms)
            self.task_queue.mark_done(task.task_id, "failed", error=str(e))
        
        return result
    
    def _record_result(self, op_id: str, task: TaskInput, cycle_id: str,
                       result: Dict, duration_ms: float):
        """Record operation result to metrics DB."""
        card_bin = task.card_number[:6] if task.card_number else ""
        
        self.metrics_db.record_operation(
            op_id=op_id,
            task_id=task.task_id,
            cycle_id=cycle_id,
            target_domain=task.target_domain,
            card_bin=card_bin,
            status="success" if result.get("success") else "failed",
            detection_type=result.get("detection_type", "none"),
            phase_failed=result.get("phase_failed", ""),
            duration_ms=duration_ms,
            profile_age=task.profile_age_days,
            proxy_country=task.billing_country,
            warmup=30,
            browser_type="camoufox",
            success=result.get("success", False),
            error=result.get("error", ""),
        )
        
        # Record detection if any
        if result.get("detection_type", "none") != "none":
            self.metrics_db.record_detection(
                op_id=op_id,
                category=result["detection_type"],
                details=result.get("error", ""),
                target=task.target_domain,
                card_bin=card_bin,
            )
    
    def _feed_to_guard(self, op_id: str, task: TaskInput, op_result):
        """Feed operation result to AI Operations Guard for learning."""
        try:
            from titan_ai_operations_guard import get_operations_guard
            guard = get_operations_guard()
            if guard:
                guard.post_operation_analysis({
                    "operation_id": op_id,
                    "target_domain": task.target_domain,
                    "status": "success" if op_result.success else "failed",
                    "decline_code": op_result.error_message or "",
                    "decline_category": op_result.detection_type.value,
                    "duration_ms": op_result.total_duration_ms,
                    "card_bin": task.card_number[:6],
                    "profile_age_days": task.profile_age_days,
                })
        except Exception:
            pass
    
    def _run_self_patch_cycle(self):
        """Analyze failures and apply self-patches."""
        logger.info("[SELF-PATCH] Running analysis cycle...")
        
        analysis = self.analyzer.analyze(hours=24)
        recommendations = analysis.get("recommendations", [])
        
        if recommendations:
            applied = self.patcher.apply_recommendations(recommendations[:5])  # Max 5 patches at a time
            logger.info(f"[SELF-PATCH] Applied {len(applied)} patches")
            
            if self._current_cycle:
                self._current_cycle.patches_applied += len(applied)
        else:
            logger.info("[SELF-PATCH] No patches needed — success rate: "
                        f"{analysis['success_rate']:.0%}")
    
    def _run_end_of_day(self):
        """End-of-day summary, self-patch, and task re-queue."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._last_daily_patch == today:
            return
        self._last_daily_patch = today
        
        logger.info("═" * 60)
        logger.info("  END-OF-DAY SELF-IMPROVEMENT CYCLE")
        logger.info("═" * 60)
        
        # 1. Generate daily analysis
        analysis = self.analyzer.analyze(hours=24)
        
        # 2. Save daily summary
        self.metrics_db.save_daily_summary(today, {
            "total_ops": analysis.get("detection_breakdown", {}),
            "successes": 0,
            "failures": 0,
            "detections": sum(analysis.get("detection_breakdown", {}).values()),
            "success_rate": analysis["success_rate"],
            "top_detection": analysis.get("top_detection", ""),
            "patches_applied": 0,
            "avg_duration_ms": 0,
        })
        
        # 3. Validate previous patches
        validated = self.patcher.validate_patches(hours_after=8)
        effective = sum(1 for v in validated if v.effective)
        logger.info(f"[EOD] Validated {len(validated)} patches — {effective} effective")
        
        # 4. Apply new patches based on analysis
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            applied = self.patcher.apply_recommendations(recommendations)
            logger.info(f"[EOD] Applied {len(applied)} new patches")
        
        # 5. Re-queue failed tasks
        self.task_queue.requeue_failed()
        logger.info(f"[EOD] Re-queued tasks — {self.task_queue.pending_count()} pending")
        
        # 6. Save queue state
        self.task_queue.save_state()
        
        # 7. Log summary
        logger.info(f"[EOD] Success rate: {analysis['success_rate']:.0%}")
        logger.info(f"[EOD] Top detection: {analysis.get('top_detection', 'none')}")
        logger.info(f"[EOD] Worst targets: {list(analysis.get('worst_targets', {}).keys())[:3]}")
        logger.info("═" * 60)
    
    def _main_loop(self):
        """Main 24/7 autonomous loop."""
        logger.info("[LOOP] Autonomous main loop started")
        
        while self._running:
            try:
                # Check for end-of-day (run at 3 AM UTC)
                now = datetime.now(timezone.utc)
                if now.hour == 3:
                    self._run_end_of_day()
                
                # Validate patches periodically (every 4 hours)
                if time.time() - self._last_patch_validation > 14400:
                    self.patcher.validate_patches()
                    self._last_patch_validation = time.time()
                
                # Reload tasks if queue is empty
                if self.task_queue.pending_count() == 0:
                    self.task_queue.load_from_directory()
                    self.task_queue.requeue_failed()
                
                # Run a cycle if tasks available
                if self.task_queue.pending_count() > 0:
                    cycle = self.run_cycle()
                    
                    # Self-patch after each cycle if success rate drops
                    if cycle and cycle.success_rate < 0.5 and cycle.tasks_attempted >= 3:
                        self._run_self_patch_cycle()
                else:
                    logger.info("[LOOP] No tasks queued — waiting 60s before recheck")
                    for _ in range(60):
                        if not self._running:
                            break
                        time.sleep(1)
                
            except Exception as e:
                logger.error(f"[LOOP] Exception in main loop: {e}")
                traceback.print_exc()
                time.sleep(30)
    
    def get_status(self) -> Dict:
        """Get current engine status."""
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "queue": self.task_queue.stats(),
            "success_rate_1h": self.metrics_db.get_success_rate(1),
            "success_rate_24h": self.metrics_db.get_success_rate(24),
            "total_operations": self.metrics_db.get_total_ops(),
            "detections_24h": self.metrics_db.get_detection_breakdown(24),
            "current_delay": self.scheduler.get_delay(),
            "consecutive_failures": self.scheduler._consecutive_failures,
        }
    
    def get_daily_report(self) -> Dict:
        """Get comprehensive daily report."""
        analysis = self.analyzer.analyze(hours=24)
        status = self.get_status()
        
        return {
            "status": status,
            "analysis": analysis,
            "queue_stats": self.task_queue.stats(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_engine_instance: Optional[AutonomousEngine] = None


def get_autonomous_engine() -> AutonomousEngine:
    """Get or create the singleton autonomous engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AutonomousEngine()
    return _engine_instance


def start_autonomous(task_dir: str = "/opt/titan/tasks") -> AutonomousEngine:
    """Start the autonomous engine with tasks from directory."""
    engine = get_autonomous_engine()
    engine.load_tasks(task_dir)
    engine.start()
    return engine


def stop_autonomous():
    """Stop the autonomous engine."""
    global _engine_instance
    if _engine_instance:
        _engine_instance.stop()


def get_autonomous_status() -> Dict:
    """Get autonomous engine status."""
    engine = get_autonomous_engine()
    return engine.get_status()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN V8.0 Autonomous Engine")
    parser.add_argument("command", choices=["start", "status", "cycle", "analyze", "patch"],
                        help="Command to execute")
    parser.add_argument("--tasks", "-t", default="/opt/titan/tasks",
                        help="Task directory or file")
    parser.add_argument("--hours", type=int, default=24,
                        help="Analysis period in hours")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    engine = AutonomousEngine(task_dir=Path(args.tasks))
    engine.load_tasks()
    
    if args.command == "start":
        engine.start()
        print("Autonomous engine started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            engine.stop()
    
    elif args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.command == "cycle":
        cycle = engine.run_cycle()
        if cycle:
            print(json.dumps(cycle.to_dict(), indent=2))
    
    elif args.command == "analyze":
        analysis = engine.analyzer.analyze(hours=args.hours)
        print(json.dumps(analysis, indent=2, default=str))
    
    elif args.command == "patch":
        analysis = engine.analyzer.analyze(hours=args.hours)
        recs = analysis.get("recommendations", [])
        if recs:
            applied = engine.patcher.apply_recommendations(recs)
            print(f"Applied {len(applied)} patches")
            for p in applied:
                print(f"  {p.parameter}: {p.old_value} → {p.new_value} ({p.reason})")
        else:
            print("No patches recommended")


if __name__ == "__main__":
    main()
