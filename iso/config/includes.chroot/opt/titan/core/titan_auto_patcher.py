#!/usr/bin/env python3
"""
TITAN V8.0 AUTO-PATCHER
========================
Automatic patching system based on detection research feedback.

Purpose:
  - Apply patches recommended by detection analyzer
  - Adjust module parameters in real-time
  - Track patch effectiveness
  - Roll back ineffective patches
  - Maintain patch history

Feedback Loop:
  1. Detection Analyzer generates recommendations
  2. Auto-Patcher evaluates and applies patches
  3. Operations continue with patches applied
  4. Logger tracks new success rates
  5. Auto-Patcher validates patch effectiveness
  6. Loop continues

Usage:
    from titan_auto_patcher import AutoPatcher
    
    patcher = AutoPatcher()
    
    # Apply patches from research
    patcher.apply_patches_from_research(research_report)
    
    # Or apply patches automatically
    patcher.run_auto_patch_cycle()
"""

import os
import sys
import json
import time
import shutil
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import re

logger = logging.getLogger("TITAN-AUTO-PATCHER")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class PatchStatus(Enum):
    """Patch application status."""
    PENDING = "pending"
    APPLIED = "applied"
    VALIDATED = "validated"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class PatchType(Enum):
    """Types of patches."""
    CONFIG_CHANGE = "config_change"      # Configuration file changes
    PARAMETER_TUNE = "parameter_tune"    # Runtime parameter adjustment
    MODULE_ENABLE = "module_enable"      # Enable a module
    MODULE_DISABLE = "module_disable"    # Disable a module
    STRATEGY_SWITCH = "strategy_switch"  # Change strategy
    THRESHOLD_ADJUST = "threshold_adjust"  # Adjust thresholds


# Patchable configurations
PATCHABLE_CONFIGS = {
    "proxy_manager": {
        "config_file": "/opt/titan/config/proxy_config.json",
        "runtime_vars": ["PROXY_QUALITY_THRESHOLD", "ENABLE_ROTATION", "GEO_MATCH_REQUIRED"]
    },
    "ja4_permutation_engine": {
        "config_file": "/opt/titan/config/ja4_config.json",
        "runtime_vars": ["ENABLE_GREASE", "SHUFFLE_EXTENSIONS", "TARGET_BROWSER"]
    },
    "ghost_motor_v6": {
        "config_file": "/opt/titan/config/ghost_motor.json",
        "runtime_vars": ["MOUSE_SPEED_VARIANCE", "TYPING_SPEED_CPM", "ENABLE_PAUSES"]
    },
    "genesis_core": {
        "config_file": "/opt/titan/config/genesis_config.json",
        "runtime_vars": ["MIN_PROFILE_AGE", "STORAGE_TARGET_MB", "ENABLE_LSNG"]
    },
    "cerberus_core": {
        "config_file": "/opt/titan/config/cerberus_config.json",
        "runtime_vars": ["ENABLE_TRA", "RETRY_ON_SOFT_DECLINE", "MAX_ATTEMPTS"]
    },
    "preflight_validator": {
        "config_file": "/opt/titan/config/preflight_config.json",
        "runtime_vars": ["IP_SCORE_THRESHOLD", "SKIP_WARNINGS", "REQUIRED_CHECKS"]
    },
    "integration_bridge": {
        "config_file": "/opt/titan/config/bridge_config.json",
        "runtime_vars": ["WARMUP_DURATION", "ENABLE_FSB_ELIMINATION", "ENABLE_ISSUER_DEFENSE"]
    }
}

# Default configuration values
DEFAULT_CONFIGS = {
    "proxy_manager": {
        "PROXY_QUALITY_THRESHOLD": 0.7,
        "ENABLE_ROTATION": True,
        "ROTATION_INTERVAL": 600,
        "GEO_MATCH_REQUIRED": True,
        "PREFER_RESIDENTIAL": True,
        "MAX_DATACENTER_SCORE": 30
    },
    "ja4_permutation_engine": {
        "ENABLE_GREASE": True,
        "SHUFFLE_EXTENSIONS": True,
        "TARGET_BROWSER": "CHROME_131",
        "TARGET_OS": "WINDOWS_11",
        "PERMUTATION_SEED": "auto"
    },
    "ghost_motor_v6": {
        "MOUSE_SPEED_VARIANCE": 0.3,
        "TYPING_SPEED_CPM": 250,
        "TYPING_VARIANCE": 0.2,
        "ENABLE_PAUSES": True,
        "PAUSE_PROBABILITY": 0.1,
        "SCROLL_VARIANCE": 0.25
    },
    "genesis_core": {
        "MIN_PROFILE_AGE": 60,
        "STORAGE_TARGET_MB": 500,
        "ENABLE_LSNG": True,
        "HISTORY_ENTRIES": 1000,
        "COOKIE_COUNT": 200
    },
    "cerberus_core": {
        "ENABLE_TRA": True,
        "RETRY_ON_SOFT_DECLINE": True,
        "MAX_ATTEMPTS": 3,
        "ENABLE_ISSUER_DEFENSE": True,
        "VELOCITY_CHECK": True
    },
    "preflight_validator": {
        "IP_SCORE_THRESHOLD": 50,
        "SKIP_WARNINGS": False,
        "REQUIRED_CHECKS": ["ip_type", "geo_match", "profile_age"],
        "OPTIONAL_CHECKS": ["fingerprint_consistency"]
    },
    "integration_bridge": {
        "WARMUP_DURATION": 30,
        "ENABLE_FSB_ELIMINATION": True,
        "ENABLE_ISSUER_DEFENSE": True,
        "ENABLE_TRA_EXEMPTION": True,
        "ENABLE_JA4_PERMUTATION": True
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PatchRecord:
    """Record of an applied patch."""
    patch_id: str
    patch_type: PatchType
    module: str
    parameter: str
    old_value: Any
    new_value: Any
    status: PatchStatus
    applied_at: float
    validated_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    success_rate_before: float = 0
    success_rate_after: Optional[float] = None
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "patch_id": self.patch_id,
            "patch_type": self.patch_type.value,
            "module": self.module,
            "parameter": self.parameter,
            "old_value": str(self.old_value),
            "new_value": str(self.new_value),
            "status": self.status.value,
            "applied_at": datetime.fromtimestamp(self.applied_at).isoformat(),
            "validated_at": datetime.fromtimestamp(self.validated_at).isoformat() if self.validated_at else None,
            "success_rate_before": self.success_rate_before,
            "success_rate_after": self.success_rate_after,
            "effectiveness": self._calculate_effectiveness(),
            "notes": self.notes
        }
    
    def _calculate_effectiveness(self) -> Optional[float]:
        """Calculate patch effectiveness."""
        if self.success_rate_after is None:
            return None
        return self.success_rate_after - self.success_rate_before


@dataclass
class PatchPlan:
    """A plan of patches to apply."""
    plan_id: str
    created_at: float
    patches: List[Dict]
    source: str  # "research" or "manual"
    estimated_improvement: float
    risk_level: str
    approved: bool = False
    executed: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-PATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class AutoPatcher:
    """
    Automatic patching system for TITAN.
    
    Applies patches based on detection research feedback and
    validates their effectiveness.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the auto-patcher.
        
        Args:
            config_dir: Configuration directory
        """
        self.config_dir = config_dir or Path("/opt/titan/config")
        self.patch_history_dir = self.config_dir / "patch_history"
        self.backup_dir = self.config_dir / "backups"
        
        # Create directories
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.patch_history_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Runtime state
        self._runtime_configs: Dict[str, Dict] = {}
        self._patch_records: List[PatchRecord] = []
        self._pending_validations: List[PatchRecord] = []
        
        # Load existing configs
        self._load_runtime_configs()
        
        # Load patch history
        self._load_patch_history()
        
        logger.info("Auto-Patcher initialized")
    
    def _load_runtime_configs(self):
        """Load current runtime configurations."""
        for module, info in PATCHABLE_CONFIGS.items():
            config_path = Path(info["config_file"])
            
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        self._runtime_configs[module] = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load config for {module}: {e}")
                    self._runtime_configs[module] = DEFAULT_CONFIGS.get(module, {})
            else:
                # Create default config
                self._runtime_configs[module] = DEFAULT_CONFIGS.get(module, {})
                self._save_config(module)
    
    def _backup_config(self, module: str):
        """P1-8 FIX: Save config snapshot before patching so rollback can restore original."""
        if module not in PATCHABLE_CONFIGS:
            return
        config_path = Path(PATCHABLE_CONFIGS[module]["config_file"])
        if config_path.exists():
            backup_dir = self.patch_history_dir / "config_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{module}_{int(time.time())}.json"
            try:
                import shutil
                shutil.copy2(config_path, backup_path)
                # Keep only last 10 backups per module
                backups = sorted(backup_dir.glob(f"{module}_*.json"))
                for old in backups[:-10]:
                    old.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Config backup failed for {module}: {e}")

    def _restore_config_backup(self, module: str) -> bool:
        """P1-8 FIX: Restore most recent config backup for a module."""
        backup_dir = self.patch_history_dir / "config_backups"
        backups = sorted(backup_dir.glob(f"{module}_*.json"))
        if not backups:
            logger.warning(f"No config backup found for {module}")
            return False
        config_path = Path(PATCHABLE_CONFIGS[module]["config_file"])
        try:
            import shutil
            shutil.copy2(backups[-1], config_path)
            with open(config_path) as f:
                self._runtime_configs[module] = json.load(f)
            logger.info(f"Restored config backup for {module} from {backups[-1].name}")
            return True
        except Exception as e:
            logger.error(f"Config restore failed for {module}: {e}")
            return False

    def _save_config(self, module: str):
        """Save configuration for a module."""
        if module not in PATCHABLE_CONFIGS:
            return
        
        # P1-8 FIX: Backup before overwriting
        self._backup_config(module)
        
        config_path = Path(PATCHABLE_CONFIGS[module]["config_file"])
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(self._runtime_configs.get(module, {}), f, indent=2)
    
    def _load_patch_history(self):
        """Load patch history from files."""
        history_file = self.patch_history_dir / "patch_history.json"
        
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                    # Reconstruct PatchRecord objects
                    for record_dict in data.get("records", []):
                        record = PatchRecord(
                            patch_id=record_dict["patch_id"],
                            patch_type=PatchType(record_dict["patch_type"]),
                            module=record_dict["module"],
                            parameter=record_dict["parameter"],
                            old_value=record_dict["old_value"],
                            new_value=record_dict["new_value"],
                            status=PatchStatus(record_dict["status"]),
                            applied_at=record_dict["applied_at"],
                            validated_at=record_dict.get("validated_at"),
                            success_rate_before=record_dict.get("success_rate_before", 0),
                            success_rate_after=record_dict.get("success_rate_after")
                        )
                        self._patch_records.append(record)
            except Exception as e:
                logger.warning(f"Could not load patch history: {e}")
    
    def _save_patch_history(self):
        """Save patch history to file."""
        history_file = self.patch_history_dir / "patch_history.json"
        
        data = {
            "last_updated": time.time(),
            "records": [
                {
                    "patch_id": r.patch_id,
                    "patch_type": r.patch_type.value,
                    "module": r.module,
                    "parameter": r.parameter,
                    "old_value": r.old_value,
                    "new_value": r.new_value,
                    "status": r.status.value,
                    "applied_at": r.applied_at,
                    "validated_at": r.validated_at,
                    "success_rate_before": r.success_rate_before,
                    "success_rate_after": r.success_rate_after
                }
                for r in self._patch_records
            ]
        }
        
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PATCH APPLICATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def apply_patches_from_research(self, research_report) -> List[PatchRecord]:
        """
        Apply patches from a research report.
        
        Args:
            research_report: ResearchReport from detection analyzer
            
        Returns:
            List of applied patch records
        """
        applied = []
        
        for recommendation in research_report.patch_recommendations:
            # Convert recommendation to patch
            patch_record = self._apply_patch_recommendation(recommendation)
            if patch_record:
                applied.append(patch_record)
        
        # Save updated configs
        for module in set(p.module for p in applied):
            self._save_config(module)
        
        # Save patch history
        self._save_patch_history()
        
        logger.info(f"Applied {len(applied)} patches from research")
        return applied
    
    def _apply_patch_recommendation(self, recommendation) -> Optional[PatchRecord]:
        """Apply a single patch recommendation."""
        module = recommendation.affected_module
        
        if module not in self._runtime_configs:
            logger.warning(f"Module {module} not patchable")
            return None
        
        # Parse the recommendation
        patches = self._parse_patch_implementation(recommendation.implementation, module)
        
        if not patches:
            logger.warning(f"Could not parse patch for {recommendation.patch_id}")
            return None
        
        # Get current success rate for baseline
        success_rate_before = self._get_current_success_rate()
        
        # Apply patches
        for param, value in patches.items():
            old_value = self._runtime_configs[module].get(param)
            self._runtime_configs[module][param] = value
            
            # Create patch record
            record = PatchRecord(
                patch_id=recommendation.patch_id,
                patch_type=PatchType.PARAMETER_TUNE,
                module=module,
                parameter=param,
                old_value=old_value,
                new_value=value,
                status=PatchStatus.APPLIED,
                applied_at=time.time(),
                success_rate_before=success_rate_before,
                notes=recommendation.description
            )
            
            self._patch_records.append(record)
            self._pending_validations.append(record)
            
            logger.info(f"Applied patch: {module}.{param} = {value}")
            
            return record
        
        return None
    
    def _parse_patch_implementation(self, implementation: str, 
                                    module: str) -> Dict[str, Any]:
        """Parse patch implementation code to extract parameter changes."""
        patches = {}
        
        # Look for assignments
        patterns = [
            r'(\w+)\s*=\s*(["\']?[^#\n]+["\']?)',  # VAR = value
            r'config\.(\w+)\s*=\s*([^#\n]+)',       # config.VAR = value
            r'"(\w+)":\s*([^,}\n]+)',               # "VAR": value in dict
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, implementation)
            for match in matches:
                param = match[0].strip()
                value_str = match[1].strip().rstrip(',')
                
                # Skip non-config lines
                if param.lower() in ['import', 'from', 'class', 'def', 'return']:
                    continue
                
                # Parse value
                try:
                    value = self._parse_value(value_str)
                    if value is not None:
                        patches[param] = value
                except Exception:
                    pass
        
        return patches
    
    def _parse_value(self, value_str: str) -> Any:
        """Parse a string value to Python type."""
        value_str = value_str.strip()
        
        # Boolean
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        
        # Number
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass
        
        # String (remove quotes)
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        # List (simple case)
        if value_str.startswith('[') and value_str.endswith(']'):
            try:
                return json.loads(value_str.replace("'", '"'))
            except Exception:
                pass
        
        return value_str
    
    def apply_manual_patch(self, module: str, parameter: str, 
                           value: Any, notes: str = "") -> Optional[PatchRecord]:
        """
        Apply a manual patch.
        
        Args:
            module: Module to patch
            parameter: Parameter name
            value: New value
            notes: Notes about the patch
            
        Returns:
            PatchRecord if successful
        """
        if module not in self._runtime_configs:
            logger.error(f"Unknown module: {module}")
            return None
        
        # Backup current config
        self._backup_config(module)
        
        # Get old value
        old_value = self._runtime_configs[module].get(parameter)
        success_rate_before = self._get_current_success_rate()
        
        # Apply patch
        self._runtime_configs[module][parameter] = value
        self._save_config(module)
        
        # Create record
        record = PatchRecord(
            patch_id=f"MANUAL-{int(time.time())}",
            patch_type=PatchType.PARAMETER_TUNE,
            module=module,
            parameter=parameter,
            old_value=old_value,
            new_value=value,
            status=PatchStatus.APPLIED,
            applied_at=time.time(),
            success_rate_before=success_rate_before,
            notes=notes
        )
        
        self._patch_records.append(record)
        self._pending_validations.append(record)
        self._save_patch_history()
        
        logger.info(f"Manual patch applied: {module}.{parameter} = {value}")
        return record
    
    def _backup_config(self, module: str):
        """Create backup of module config."""
        if module not in PATCHABLE_CONFIGS:
            return
        
        config_path = Path(PATCHABLE_CONFIGS[module]["config_file"])
        if config_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{module}_{timestamp}.json"
            shutil.copy(config_path, backup_path)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PATCH VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def validate_pending_patches(self, min_operations: int = 10) -> List[PatchRecord]:
        """
        Validate pending patches against new operation data.
        
        Args:
            min_operations: Minimum operations required for validation
            
        Returns:
            List of validated patches
        """
        validated = []
        current_rate = self._get_current_success_rate()
        
        for record in self._pending_validations[:]:
            # Check if enough time has passed
            hours_since = (time.time() - record.applied_at) / 3600
            if hours_since < 1:  # At least 1 hour
                continue
            
            # Get success rate since patch
            rate_since_patch = self._get_success_rate_since(record.applied_at)
            if rate_since_patch is None:
                continue  # Not enough data
            
            record.success_rate_after = rate_since_patch
            record.validated_at = time.time()
            
            # Determine if patch was effective
            improvement = rate_since_patch - record.success_rate_before
            
            if improvement >= 0.01:  # At least 1% improvement
                record.status = PatchStatus.VALIDATED
                record.notes += f" | Validated: +{improvement*100:.1f}% improvement"
                logger.info(f"Patch {record.patch_id} validated: +{improvement*100:.1f}%")
            elif improvement < -0.05:  # More than 5% worse
                # Roll back
                self._rollback_patch(record)
                record.notes += f" | Rolled back: {improvement*100:.1f}% degradation"
                logger.warning(f"Patch {record.patch_id} rolled back: {improvement*100:.1f}%")
            else:
                record.status = PatchStatus.VALIDATED
                record.notes += f" | Validated: neutral effect ({improvement*100:.1f}%)"
            
            validated.append(record)
            self._pending_validations.remove(record)
        
        self._save_patch_history()
        return validated
    
    def _rollback_patch(self, record: PatchRecord):
        """Roll back a patch."""
        module = record.module
        parameter = record.parameter
        
        # Restore old value
        self._runtime_configs[module][parameter] = record.old_value
        self._save_config(module)
        
        record.status = PatchStatus.ROLLED_BACK
        record.rolled_back_at = time.time()
        
        logger.info(f"Rolled back: {module}.{parameter} = {record.old_value}")
    
    def rollback_patch_by_id(self, patch_id: str) -> bool:
        """
        Roll back a specific patch by ID.
        
        Args:
            patch_id: Patch ID to roll back
            
        Returns:
            True if rolled back successfully
        """
        for record in self._patch_records:
            if record.patch_id == patch_id and record.status == PatchStatus.APPLIED:
                self._rollback_patch(record)
                self._save_patch_history()
                return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AUTO-PATCH CYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_auto_patch_cycle(self, days: int = 2) -> Dict:
        """
        Run complete auto-patch cycle.
        
        1. Run detection analysis
        2. Apply recommended patches
        3. Schedule validation
        
        Args:
            days: Days of data to analyze
            
        Returns:
            Cycle results
        """
        logger.info("Starting auto-patch cycle...")
        
        # Import detection analyzer
        try:
            from titan_detection_analyzer import DetectionAnalyzer
            analyzer = DetectionAnalyzer()
        except ImportError:
            logger.error("Detection analyzer not available")
            return {"error": "Detection analyzer not available"}
        
        # Run research
        report = analyzer.run_research_cycle(days)
        
        # Apply patches
        applied = self.apply_patches_from_research(report)
        
        # Validate previous patches
        validated = self.validate_pending_patches()
        
        results = {
            "cycle_time": datetime.now().isoformat(),
            "operations_analyzed": report.operations_analyzed,
            "current_success_rate": report.success_rate,
            "patches_applied": len(applied),
            "patches_validated": len(validated),
            "pending_validation": len(self._pending_validations),
            "applied_patches": [p.to_dict() for p in applied],
            "validated_patches": [p.to_dict() for p in validated]
        }
        
        # Save cycle results
        cycle_file = self.patch_history_dir / f"cycle_{int(time.time())}.json"
        with open(cycle_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Auto-patch cycle complete: {len(applied)} applied, {len(validated)} validated")
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_current_success_rate(self, days: int = 1) -> float:
        """Get current success rate from logger."""
        try:
            from titan_operation_logger import TitanOperationLogger
            op_logger = TitanOperationLogger()
            stats = op_logger.get_success_rate(days)
            return stats.get("success_rate", 0)
        except Exception as e:
            logger.warning(f"Could not get success rate: {e}")
            return 0
    
    def _get_success_rate_since(self, timestamp: float) -> Optional[float]:
        """Get success rate since a specific timestamp."""
        try:
            from titan_operation_logger import TitanOperationLogger
            import sqlite3
            
            op_logger = TitanOperationLogger()
            db_path = op_logger.db_path
            
            if not db_path.exists():
                return None
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*), SUM(success)
                FROM operations
                WHERE start_time >= ?
            """, (timestamp,))
            
            row = cursor.fetchone()
            conn.close()
            
            total = row[0] or 0
            successes = row[1] or 0
            
            if total < 5:  # Not enough data
                return None
            
            return successes / total
            
        except Exception as e:
            logger.warning(f"Could not get success rate since: {e}")
            return None
    
    def get_config(self, module: str) -> Dict:
        """Get current config for a module."""
        return self._runtime_configs.get(module, {}).copy()
    
    def get_all_configs(self) -> Dict[str, Dict]:
        """Get all current configs."""
        return {k: v.copy() for k, v in self._runtime_configs.items()}
    
    def get_patch_history(self, limit: int = 50) -> List[Dict]:
        """Get patch history."""
        records = self._patch_records[-limit:]
        return [r.to_dict() for r in reversed(records)]
    
    def get_pending_validations(self) -> List[Dict]:
        """Get patches pending validation."""
        return [r.to_dict() for r in self._pending_validations]
    
    def get_effectiveness_report(self) -> Dict:
        """Get overall effectiveness report."""
        validated = [r for r in self._patch_records if r.status == PatchStatus.VALIDATED]
        rolled_back = [r for r in self._patch_records if r.status == PatchStatus.ROLLED_BACK]
        
        if not validated and not rolled_back:
            return {"total_patches": len(self._patch_records), "validated": 0, "rolled_back": 0}
        
        # Calculate average improvement
        improvements = []
        for r in validated:
            if r.success_rate_after is not None:
                improvements.append(r.success_rate_after - r.success_rate_before)
        
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        
        return {
            "total_patches": len(self._patch_records),
            "validated": len(validated),
            "rolled_back": len(rolled_back),
            "pending": len(self._pending_validations),
            "avg_improvement": avg_improvement,
            "best_patches": sorted(
                [r.to_dict() for r in validated if r.success_rate_after],
                key=lambda x: x.get("effectiveness", 0) or 0,
                reverse=True
            )[:5]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED AUTO-PATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class ScheduledAutoPatcher:
    """
    Scheduled auto-patcher that runs on intervals.
    """
    
    def __init__(self, patcher: AutoPatcher = None):
        """Initialize scheduled auto-patcher."""
        self.patcher = patcher or AutoPatcher()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycle_results: List[Dict] = []
    
    def start(self, interval_hours: int = 24, research_days: int = 2):
        """
        Start scheduled auto-patching.
        
        Args:
            interval_hours: Hours between cycles
            research_days: Days of data to analyze per cycle
        """
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(interval_hours, research_days),
            daemon=True
        )
        self._thread.start()
        logger.info(f"Scheduled auto-patcher started (every {interval_hours}h)")
    
    def stop(self):
        """Stop scheduled auto-patching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduled auto-patcher stopped")
    
    def _run_loop(self, interval_hours: int, research_days: int):
        """Main loop."""
        interval_seconds = interval_hours * 3600
        
        while self._running:
            try:
                results = self.patcher.run_auto_patch_cycle(research_days)
                self._cycle_results.append(results)
                
                # Keep last 100 results
                if len(self._cycle_results) > 100:
                    self._cycle_results = self._cycle_results[-100:]
                    
            except Exception as e:
                logger.error(f"Auto-patch cycle error: {e}")
            
            # Wait for next cycle
            for _ in range(interval_seconds):
                if not self._running:
                    break
                time.sleep(1)
    
    def get_cycle_history(self) -> List[Dict]:
        """Get cycle history."""
        return list(self._cycle_results)


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDBACK LOOP MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class FeedbackLoopManager:
    """
    Manages the complete feedback loop:
    
    Operations → Logger → Analyzer → Patcher → Operations
    """
    
    def __init__(self):
        """Initialize feedback loop manager."""
        self.patcher = AutoPatcher()
        self.scheduler = ScheduledAutoPatcher(self.patcher)
        
        # Status
        self._enabled = False
        self._cycles_run = 0
    
    def enable(self, interval_hours: int = 24, research_days: int = 2):
        """Enable the feedback loop."""
        if self._enabled:
            return
        
        self.scheduler.start(interval_hours, research_days)
        self._enabled = True
        logger.info("Feedback loop enabled")
    
    def disable(self):
        """Disable the feedback loop."""
        if not self._enabled:
            return
        
        self.scheduler.stop()
        self._enabled = False
        logger.info("Feedback loop disabled")
    
    def run_now(self, days: int = 2) -> Dict:
        """Run feedback cycle immediately."""
        return self.patcher.run_auto_patch_cycle(days)
    
    def get_status(self) -> Dict:
        """Get feedback loop status."""
        return {
            "enabled": self._enabled,
            "cycles_run": len(self.scheduler.get_cycle_history()),
            "pending_validations": len(self.patcher.get_pending_validations()),
            "effectiveness": self.patcher.get_effectiveness_report()
        }
    
    def get_current_configs(self) -> Dict:
        """Get all current configurations."""
        return self.patcher.get_all_configs()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN Auto-Patcher")
    parser.add_argument("--cycle", action="store_true", help="Run auto-patch cycle")
    parser.add_argument("--days", type=int, default=2, help="Days to analyze")
    parser.add_argument("--validate", action="store_true", help="Validate pending patches")
    parser.add_argument("--history", action="store_true", help="Show patch history")
    parser.add_argument("--effectiveness", action="store_true", help="Show effectiveness report")
    parser.add_argument("--configs", action="store_true", help="Show current configs")
    parser.add_argument("--patch", nargs=3, metavar=("MODULE", "PARAM", "VALUE"), help="Apply manual patch")
    parser.add_argument("--rollback", help="Rollback patch by ID")
    
    args = parser.parse_args()
    
    patcher = AutoPatcher()
    
    if args.cycle:
        results = patcher.run_auto_patch_cycle(args.days)
        print(json.dumps(results, indent=2))
        
    elif args.validate:
        validated = patcher.validate_pending_patches()
        print(f"Validated {len(validated)} patches:")
        for p in validated:
            print(json.dumps(p.to_dict(), indent=2))
        
    elif args.history:
        history = patcher.get_patch_history()
        print(json.dumps(history, indent=2))
        
    elif args.effectiveness:
        report = patcher.get_effectiveness_report()
        print(json.dumps(report, indent=2))
        
    elif args.configs:
        configs = patcher.get_all_configs()
        print(json.dumps(configs, indent=2))
        
    elif args.patch:
        module, param, value = args.patch
        # Try to parse value
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        
        record = patcher.apply_manual_patch(module, param, value)
        if record:
            print(f"Patch applied: {record.to_dict()}")
        else:
            print("Patch failed")
        
    elif args.rollback:
        success = patcher.rollback_patch_by_id(args.rollback)
        if success:
            print(f"Rolled back patch: {args.rollback}")
        else:
            print(f"Patch not found or already rolled back: {args.rollback}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
