#!/usr/bin/env python3
"""
TITAN V7.6 OPERATION LOGGER
============================
Comprehensive logging and analytics system for automated operations.

Purpose:
  - Log every operation step with detailed metrics
  - Store operation results for detection research
  - Track success/failure patterns over time
  - Enable 2-day detection research cycle
  - Generate analytics reports

Storage:
  - /opt/titan/logs/operations/ - Individual operation logs
  - /opt/titan/logs/analytics/ - Aggregated analytics
  - /opt/titan/logs/detection/ - Detection research data

Usage:
    from titan_operation_logger import TitanOperationLogger
    
    logger = TitanOperationLogger()
    logger.log_operation_start(config)
    logger.log_phase_result(operation_id, phase_result)
    logger.log_operation_complete(result)
    
    # Get analytics
    stats = logger.get_success_rate_by_target()
    patterns = logger.get_detection_patterns(days=2)
"""

import os
import sys
import json
import time
import gzip
import shutil
import sqlite3
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import logging

logger = logging.getLogger("TITAN-LOGGER")


# ═══════════════════════════════════════════════════════════════════════════════
# STORAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_LOG_DIR = Path("/opt/titan/logs")
OPERATIONS_DIR = DEFAULT_LOG_DIR / "operations"
ANALYTICS_DIR = DEFAULT_LOG_DIR / "analytics"
DETECTION_DIR = DEFAULT_LOG_DIR / "detection"
DATABASE_PATH = DEFAULT_LOG_DIR / "titan_operations.db"

# Retention settings
MAX_LOG_AGE_DAYS = 30
MAX_ANALYTICS_AGE_DAYS = 90
COMPRESS_AFTER_DAYS = 7


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: float
    level: str
    operation_id: str
    phase: str
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json_line(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class OperationLog:
    """Complete log for an operation."""
    operation_id: str
    start_time: float
    end_time: Optional[float]
    config: Dict
    entries: List[LogEntry]
    result: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "operation_id": self.operation_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "config": self.config,
            "entries": [e.to_dict() for e in self.entries],
            "result": self.result
        }


@dataclass
class AnalyticsSnapshot:
    """Analytics snapshot for a time period."""
    period_start: float
    period_end: float
    total_operations: int
    success_count: int
    failure_count: int
    detection_count: int
    avg_duration_ms: float
    success_rate: float
    detection_rate: float
    by_target: Dict[str, Dict]
    by_detection_type: Dict[str, int]
    by_phase_failure: Dict[str, int]
    top_errors: List[Tuple[str, int]]
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# TITAN OPERATION LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

class TitanOperationLogger:
    """
    Comprehensive operation logging system.
    
    Provides structured logging, persistence, and analytics
    for all automated operations.
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the operation logger.
        
        Args:
            log_dir: Base directory for logs (default: /opt/titan/logs)
        """
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.operations_dir = self.log_dir / "operations"
        self.analytics_dir = self.log_dir / "analytics"
        self.detection_dir = self.log_dir / "detection"
        self.db_path = self.log_dir / "titan_operations.db"
        
        # Create directories
        self.operations_dir.mkdir(parents=True, exist_ok=True)
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        self.detection_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # In-memory cache for active operations
        self._active_operations: Dict[str, OperationLog] = {}
        self._lock = threading.Lock()
        
        logger.info(f"Operation logger initialized: {self.log_dir}")
    
    def _init_database(self):
        """Initialize SQLite database for analytics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                operation_id TEXT PRIMARY KEY,
                start_time REAL,
                end_time REAL,
                duration_ms REAL,
                status TEXT,
                success INTEGER,
                target_domain TEXT,
                target_url TEXT,
                card_bin TEXT,
                billing_country TEXT,
                billing_state TEXT,
                detection_type TEXT,
                risk_level TEXT,
                final_phase TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT,
                phase TEXT,
                status TEXT,
                start_time REAL,
                end_time REAL,
                duration_ms REAL,
                success INTEGER,
                detection_type TEXT,
                error_message TEXT,
                metrics_json TEXT,
                FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
            )
        """)
        
        # Detection signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detection_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT,
                detection_type TEXT,
                severity TEXT,
                details TEXT,
                timestamp REAL,
                FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
            )
        """)
        
        # Daily analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_analytics (
                date TEXT PRIMARY KEY,
                total_operations INTEGER,
                success_count INTEGER,
                failure_count INTEGER,
                detection_count INTEGER,
                avg_duration_ms REAL,
                success_rate REAL,
                by_target_json TEXT,
                by_detection_json TEXT,
                by_phase_json TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ops_start ON operations(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ops_target ON operations(target_domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ops_status ON operations(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_phases_op ON phases(operation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detect_op ON detection_signals(operation_id)")
        
        conn.commit()
        conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOGGING METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def log_operation_start(self, config) -> str:
        """
        Log operation start.
        
        Args:
            config: OperationConfig instance
            
        Returns:
            Operation ID
        """
        operation_id = config.operation_id
        start_time = time.time()
        
        with self._lock:
            op_log = OperationLog(
                operation_id=operation_id,
                start_time=start_time,
                end_time=None,
                config=config.to_dict(),
                entries=[]
            )
            self._active_operations[operation_id] = op_log
        
        # Log entry
        entry = LogEntry(
            timestamp=start_time,
            level="INFO",
            operation_id=operation_id,
            phase="start",
            message="Operation started",
            metrics={"config": config.to_dict()}
        )
        
        self._write_log_entry(operation_id, entry)
        
        logger.info(f"[{operation_id}] Operation started")
        return operation_id
    
    def log_phase_result(self, operation_id: str, phase_result) -> None:
        """
        Log phase result.
        
        Args:
            operation_id: Operation ID
            phase_result: PhaseResult instance
        """
        entry = LogEntry(
            timestamp=phase_result.end_time,
            level="INFO" if phase_result.success else "ERROR",
            operation_id=operation_id,
            phase=phase_result.phase.value,
            message=f"Phase {phase_result.phase.value}: {phase_result.status.value}",
            metrics={
                "duration_ms": phase_result.duration_ms,
                "success": phase_result.success,
                "detection_type": phase_result.detection_type.value,
                "error": phase_result.error_message,
                **phase_result.metrics
            }
        )
        
        self._write_log_entry(operation_id, entry)
        
        # Store in active operations
        with self._lock:
            if operation_id in self._active_operations:
                self._active_operations[operation_id].entries.append(entry)
        
        # Store phase in database
        self._store_phase_result(operation_id, phase_result)
    
    def log_operation_complete(self, result) -> None:
        """
        Log operation completion.
        
        Args:
            result: OperationResult instance
        """
        operation_id = result.operation_id
        
        # Final entry
        entry = LogEntry(
            timestamp=result.end_time,
            level="INFO" if result.success else "ERROR",
            operation_id=operation_id,
            phase="complete",
            message=f"Operation {result.status.value}: {'SUCCESS' if result.success else 'FAILED'}",
            metrics={
                "total_duration_ms": result.total_duration_ms,
                "success": result.success,
                "detection_type": result.detection_type.value,
                "final_phase": result.final_phase.value,
                "risk_level": result.risk_level.value,
                "transaction_id": result.transaction_id,
                "error": result.error_message
            }
        )
        
        self._write_log_entry(operation_id, entry)
        
        # Finalize operation log
        with self._lock:
            if operation_id in self._active_operations:
                op_log = self._active_operations[operation_id]
                op_log.end_time = result.end_time
                op_log.result = result.to_dict()
                op_log.entries.append(entry)
                
                # Write complete log file
                self._write_operation_log(op_log)
                
                # Remove from active
                del self._active_operations[operation_id]
        
        # Store in database
        self._store_operation_result(result)
        
        logger.info(f"[{operation_id}] Operation logged: {result.status.value}")
    
    def log_detection_signal(self, operation_id: str, detection_type: str,
                            details: str, severity: str = "high") -> None:
        """
        Log a detection signal.
        
        Args:
            operation_id: Operation ID
            detection_type: Type of detection
            details: Detection details
            severity: Severity level (low, medium, high, critical)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO detection_signals 
            (operation_id, detection_type, severity, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (operation_id, detection_type, severity, details, time.time()))
        
        conn.commit()
        conn.close()
        
        # Also log to file
        entry = LogEntry(
            timestamp=time.time(),
            level="WARNING",
            operation_id=operation_id,
            phase="detection",
            message=f"Detection signal: {detection_type}",
            metrics={
                "detection_type": detection_type,
                "severity": severity,
                "details": details
            }
        )
        self._write_log_entry(operation_id, entry)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FILE I/O
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _write_log_entry(self, operation_id: str, entry: LogEntry) -> None:
        """Write log entry to file."""
        # Daily log file
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.operations_dir / f"{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(entry.to_json_line() + "\n")
    
    def _write_operation_log(self, op_log: OperationLog) -> None:
        """Write complete operation log to file."""
        # Operation-specific file
        op_file = self.operations_dir / f"{op_log.operation_id}.json"
        
        with open(op_file, 'w') as f:
            json.dump(op_log.to_dict(), f, indent=2)
    
    def _store_phase_result(self, operation_id: str, phase_result) -> None:
        """Store phase result in database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO phases 
            (operation_id, phase, status, start_time, end_time, 
             duration_ms, success, detection_type, error_message, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operation_id,
            phase_result.phase.value,
            phase_result.status.value,
            phase_result.start_time,
            phase_result.end_time,
            phase_result.duration_ms,
            1 if phase_result.success else 0,
            phase_result.detection_type.value,
            phase_result.error_message,
            json.dumps(phase_result.metrics)
        ))
        
        conn.commit()
        conn.close()
    
    def _store_operation_result(self, result) -> None:
        """Store operation result in database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Extract config info
        config = result.metadata.get("config", {})
        
        cursor.execute("""
            INSERT OR REPLACE INTO operations 
            (operation_id, start_time, end_time, duration_ms, status, success,
             target_domain, target_url, card_bin, billing_country, billing_state,
             detection_type, risk_level, final_phase, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.operation_id,
            result.start_time,
            result.end_time,
            result.total_duration_ms,
            result.status.value,
            1 if result.success else 0,
            config.get("target_domain", ""),
            config.get("target_url", ""),
            config.get("card_number_masked", "")[:6] if config.get("card_number_masked") else "",
            config.get("billing_address", {}).get("country", ""),
            config.get("billing_address", {}).get("state", ""),
            result.detection_type.value,
            result.risk_level.value,
            result.final_phase.value,
            result.error_message
        ))
        
        conn.commit()
        conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYTICS METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_success_rate(self, days: int = 7) -> Dict:
        """
        Get success rate for the past N days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Success rate statistics
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = time.time() - (days * 86400)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(success) as successes,
                AVG(duration_ms) as avg_duration
            FROM operations
            WHERE start_time >= ?
        """, (cutoff,))
        
        row = cursor.fetchone()
        conn.close()
        
        total = row[0] or 0
        successes = row[1] or 0
        avg_duration = row[2] or 0
        
        return {
            "period_days": days,
            "total_operations": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0,
            "avg_duration_ms": avg_duration
        }
    
    def get_success_rate_by_target(self, days: int = 7) -> Dict[str, Dict]:
        """
        Get success rate grouped by target domain.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Success rates by target
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = time.time() - (days * 86400)
        
        cursor.execute("""
            SELECT 
                target_domain,
                COUNT(*) as total,
                SUM(success) as successes,
                AVG(duration_ms) as avg_duration
            FROM operations
            WHERE start_time >= ? AND target_domain != ''
            GROUP BY target_domain
            ORDER BY total DESC
        """, (cutoff,))
        
        results = {}
        for row in cursor.fetchall():
            domain = row[0]
            total = row[1]
            successes = row[2]
            results[domain] = {
                "total": total,
                "successes": successes,
                "failures": total - successes,
                "success_rate": successes / total if total > 0 else 0,
                "avg_duration_ms": row[3]
            }
        
        conn.close()
        return results
    
    def get_detection_patterns(self, days: int = 2) -> Dict:
        """
        Analyze detection patterns over the past N days.
        
        This is the key method for the 2-day detection research cycle.
        
        Args:
            days: Number of days to analyze (default: 2)
            
        Returns:
            Detection pattern analysis
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = time.time() - (days * 86400)
        
        # Detection type breakdown
        cursor.execute("""
            SELECT 
                detection_type,
                COUNT(*) as count,
                AVG(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_rate
            FROM operations
            WHERE start_time >= ? AND detection_type != 'none'
            GROUP BY detection_type
            ORDER BY count DESC
        """, (cutoff,))
        
        detection_breakdown = {}
        for row in cursor.fetchall():
            detection_breakdown[row[0]] = {
                "count": row[1],
                "failure_rate": row[2]
            }
        
        # Phase failure analysis
        cursor.execute("""
            SELECT 
                phase,
                detection_type,
                COUNT(*) as count
            FROM phases
            WHERE start_time >= ? AND success = 0
            GROUP BY phase, detection_type
            ORDER BY count DESC
        """, (cutoff,))
        
        phase_failures = {}
        for row in cursor.fetchall():
            phase = row[0]
            if phase not in phase_failures:
                phase_failures[phase] = {}
            phase_failures[phase][row[1]] = row[2]
        
        # Detection signals analysis
        cursor.execute("""
            SELECT 
                detection_type,
                severity,
                details,
                COUNT(*) as count
            FROM detection_signals
            WHERE timestamp >= ?
            GROUP BY detection_type, severity
            ORDER BY count DESC
            LIMIT 20
        """, (cutoff,))
        
        top_signals = []
        for row in cursor.fetchall():
            top_signals.append({
                "type": row[0],
                "severity": row[1],
                "sample_details": row[2][:100] if row[2] else "",
                "count": row[3]
            })
        
        # Target-specific detection rates
        cursor.execute("""
            SELECT 
                target_domain,
                detection_type,
                COUNT(*) as count
            FROM operations
            WHERE start_time >= ? AND detection_type != 'none'
            GROUP BY target_domain, detection_type
            ORDER BY count DESC
        """, (cutoff,))
        
        target_detections = defaultdict(dict)
        for row in cursor.fetchall():
            target_detections[row[0]][row[1]] = row[2]
        
        # Temporal patterns (by hour)
        cursor.execute("""
            SELECT 
                CAST((start_time % 86400) / 3600 AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(success) as successes
            FROM operations
            WHERE start_time >= ?
            GROUP BY hour
            ORDER BY hour
        """, (cutoff,))
        
        hourly_pattern = {}
        for row in cursor.fetchall():
            hour = row[0]
            total = row[1]
            successes = row[2]
            hourly_pattern[hour] = {
                "total": total,
                "success_rate": successes / total if total > 0 else 0
            }
        
        conn.close()
        
        return {
            "period_days": days,
            "period_start": datetime.fromtimestamp(cutoff).isoformat(),
            "period_end": datetime.now().isoformat(),
            "detection_breakdown": detection_breakdown,
            "phase_failures": phase_failures,
            "top_signals": top_signals,
            "target_detections": dict(target_detections),
            "hourly_pattern": hourly_pattern,
            "recommendations": self._generate_recommendations(
                detection_breakdown, phase_failures, target_detections
            )
        }
    
    def _generate_recommendations(self, detection_breakdown: Dict,
                                   phase_failures: Dict,
                                   target_detections: Dict) -> List[Dict]:
        """Generate recommendations based on detection patterns."""
        recommendations = []
        
        # IP reputation issues
        if detection_breakdown.get("ip_reputation", {}).get("count", 0) > 3:
            recommendations.append({
                "priority": "high",
                "category": "network",
                "issue": "High IP reputation detection rate",
                "action": "Switch to higher quality residential proxies or enable proxy rotation",
                "affected_count": detection_breakdown["ip_reputation"]["count"]
            })
        
        # Fingerprint mismatches
        if detection_breakdown.get("fingerprint_mismatch", {}).get("count", 0) > 2:
            recommendations.append({
                "priority": "high",
                "category": "fingerprint",
                "issue": "Fingerprint consistency failures",
                "action": "Verify JA4+ permutation is active and profile age is sufficient",
                "affected_count": detection_breakdown["fingerprint_mismatch"]["count"]
            })
        
        # 3DS challenges
        if detection_breakdown.get("3ds_challenge", {}).get("count", 0) > 5:
            recommendations.append({
                "priority": "medium",
                "category": "payment",
                "issue": "High 3DS challenge rate",
                "action": "Enable TRA exemption engine and check BIN quality",
                "affected_count": detection_breakdown["3ds_challenge"]["count"]
            })
        
        # Card declines
        if detection_breakdown.get("card_decline", {}).get("count", 0) > 10:
            recommendations.append({
                "priority": "medium",
                "category": "payment",
                "issue": "High card decline rate",
                "action": "Check issuer defense and card cooling system",
                "affected_count": detection_breakdown["card_decline"]["count"]
            })
        
        # Behavioral detection
        if detection_breakdown.get("behavioral", {}).get("count", 0) > 2:
            recommendations.append({
                "priority": "high",
                "category": "behavior",
                "issue": "Behavioral detection triggered",
                "action": "Increase warmup duration and enable Ghost Motor humanization",
                "affected_count": detection_breakdown["behavioral"]["count"]
            })
        
        # Phase-specific recommendations
        if phase_failures.get("preflight", {}):
            recommendations.append({
                "priority": "high",
                "category": "preflight",
                "issue": "Pre-flight failures blocking operations",
                "action": "Review preflight checks and fix blocking issues",
                "details": phase_failures["preflight"]
            })
        
        return recommendations
    
    def get_failure_analysis(self, days: int = 7) -> Dict:
        """
        Detailed failure analysis.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Failure analysis with root causes
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = time.time() - (days * 86400)
        
        # Failures by phase
        cursor.execute("""
            SELECT 
                final_phase,
                COUNT(*) as count,
                GROUP_CONCAT(DISTINCT error_message) as errors
            FROM operations
            WHERE start_time >= ? AND success = 0
            GROUP BY final_phase
            ORDER BY count DESC
        """, (cutoff,))
        
        by_phase = {}
        for row in cursor.fetchall():
            by_phase[row[0]] = {
                "count": row[1],
                "sample_errors": (row[2] or "")[:500]
            }
        
        # Common error patterns
        cursor.execute("""
            SELECT 
                error_message,
                COUNT(*) as count
            FROM operations
            WHERE start_time >= ? AND success = 0 AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT 10
        """, (cutoff,))
        
        common_errors = []
        for row in cursor.fetchall():
            common_errors.append({
                "error": row[0][:200] if row[0] else "",
                "count": row[1]
            })
        
        conn.close()
        
        return {
            "period_days": days,
            "failures_by_phase": by_phase,
            "common_errors": common_errors,
            "total_failures": sum(v["count"] for v in by_phase.values())
        }
    
    def generate_daily_report(self, date: Optional[str] = None) -> Dict:
        """
        Generate daily analytics report.
        
        Args:
            date: Date string (YYYY-MM-DD), default today
            
        Returns:
            Daily report
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse date
        dt = datetime.strptime(date, "%Y-%m-%d")
        start_ts = dt.timestamp()
        end_ts = (dt + timedelta(days=1)).timestamp()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(success) as successes,
                AVG(duration_ms) as avg_duration
            FROM operations
            WHERE start_time >= ? AND start_time < ?
        """, (start_ts, end_ts))
        
        row = cursor.fetchone()
        total = row[0] or 0
        successes = row[1] or 0
        avg_duration = row[2] or 0
        
        # By target
        cursor.execute("""
            SELECT 
                target_domain,
                COUNT(*) as total,
                SUM(success) as successes
            FROM operations
            WHERE start_time >= ? AND start_time < ?
            GROUP BY target_domain
        """, (start_ts, end_ts))
        
        by_target = {}
        for row in cursor.fetchall():
            domain = row[0] or "unknown"
            t = row[1]
            s = row[2]
            by_target[domain] = {
                "total": t,
                "successes": s,
                "success_rate": s / t if t > 0 else 0
            }
        
        # By detection
        cursor.execute("""
            SELECT 
                detection_type,
                COUNT(*) as count
            FROM operations
            WHERE start_time >= ? AND start_time < ?
            GROUP BY detection_type
        """, (start_ts, end_ts))
        
        by_detection = {}
        for row in cursor.fetchall():
            by_detection[row[0]] = row[1]
        
        conn.close()
        
        report = {
            "date": date,
            "total_operations": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0,
            "avg_duration_ms": avg_duration,
            "by_target": by_target,
            "by_detection": by_detection
        }
        
        # Save report
        report_file = self.analytics_dir / f"daily_{date}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAINTENANCE METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def cleanup_old_logs(self) -> Dict:
        """
        Clean up old log files.
        
        Returns:
            Cleanup statistics
        """
        stats = {
            "compressed": 0,
            "deleted": 0,
            "space_freed_mb": 0
        }
        
        now = time.time()
        compress_cutoff = now - (COMPRESS_AFTER_DAYS * 86400)
        delete_cutoff = now - (MAX_LOG_AGE_DAYS * 86400)
        
        # Process operation logs
        for log_file in self.operations_dir.glob("*.json"):
            mtime = log_file.stat().st_mtime
            
            if mtime < delete_cutoff:
                # Delete old files
                size = log_file.stat().st_size
                log_file.unlink()
                stats["deleted"] += 1
                stats["space_freed_mb"] += size / (1024 * 1024)
                
            elif mtime < compress_cutoff and not log_file.suffix.endswith('.gz'):
                # Compress older files
                with open(log_file, 'rb') as f_in:
                    with gzip.open(str(log_file) + '.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                log_file.unlink()
                stats["compressed"] += 1
        
        logger.info(f"Cleanup complete: {stats}")
        return stats
    
    def export_to_csv(self, output_path: Path, days: int = 30) -> str:
        """
        Export operations to CSV for external analysis.
        
        Args:
            output_path: Output file path
            days: Number of days to export
            
        Returns:
            Output file path
        """
        import csv
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = time.time() - (days * 86400)
        
        cursor.execute("""
            SELECT * FROM operations
            WHERE start_time >= ?
            ORDER BY start_time DESC
        """, (cutoff,))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        logger.info(f"Exported {len(rows)} operations to {output_path}")
        return str(output_path)


# ═══════════════════════════════════════════════════════════════════════════════
# REAL-TIME DASHBOARD DATA PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardDataProvider:
    """
    Real-time data provider for dashboard visualization.
    """
    
    def __init__(self, logger_instance: TitanOperationLogger):
        """Initialize with logger instance."""
        self.logger = logger_instance
    
    def get_realtime_stats(self) -> Dict:
        """Get real-time dashboard statistics."""
        return {
            "last_hour": self.logger.get_success_rate(days=1/24),
            "today": self.logger.get_success_rate(days=1),
            "this_week": self.logger.get_success_rate(days=7),
            "active_operations": len(self.logger._active_operations),
            "timestamp": time.time()
        }
    
    def get_charts_data(self, days: int = 7) -> Dict:
        """Get data for dashboard charts."""
        return {
            "success_by_target": self.logger.get_success_rate_by_target(days),
            "detection_patterns": self.logger.get_detection_patterns(days),
            "failure_analysis": self.logger.get_failure_analysis(days)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN Operation Logger")
    parser.add_argument("--stats", action="store_true", help="Show success rate stats")
    parser.add_argument("--detection", action="store_true", help="Show detection patterns")
    parser.add_argument("--failures", action="store_true", help="Show failure analysis")
    parser.add_argument("--report", action="store_true", help="Generate daily report")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old logs")
    parser.add_argument("--export", help="Export to CSV file")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze")
    parser.add_argument("--log-dir", help="Log directory path")
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir) if args.log_dir else None
    op_logger = TitanOperationLogger(log_dir)
    
    if args.stats:
        stats = op_logger.get_success_rate(args.days)
        print(json.dumps(stats, indent=2))
        
    elif args.detection:
        patterns = op_logger.get_detection_patterns(args.days)
        print(json.dumps(patterns, indent=2))
        
    elif args.failures:
        analysis = op_logger.get_failure_analysis(args.days)
        print(json.dumps(analysis, indent=2))
        
    elif args.report:
        report = op_logger.generate_daily_report()
        print(json.dumps(report, indent=2))
        
    elif args.cleanup:
        stats = op_logger.cleanup_old_logs()
        print(json.dumps(stats, indent=2))
        
    elif args.export:
        path = op_logger.export_to_csv(Path(args.export), args.days)
        print(f"Exported to: {path}")
        
    else:
        # Show all stats
        print("=== TITAN Operation Logger ===\n")
        
        stats = op_logger.get_success_rate(args.days)
        print(f"Success Rate ({args.days} days):")
        print(f"  Total: {stats['total_operations']}")
        print(f"  Success Rate: {stats['success_rate']*100:.1f}%")
        print(f"  Avg Duration: {stats['avg_duration_ms']:.0f}ms\n")
        
        patterns = op_logger.get_detection_patterns(2)
        print("Detection Patterns (2 days):")
        for dt, data in patterns.get("detection_breakdown", {}).items():
            print(f"  {dt}: {data['count']} occurrences")
        
        if patterns.get("recommendations"):
            print("\nRecommendations:")
            for rec in patterns["recommendations"][:3]:
                print(f"  [{rec['priority'].upper()}] {rec['issue']}")
                print(f"    → {rec['action']}")


if __name__ == "__main__":
    main()
