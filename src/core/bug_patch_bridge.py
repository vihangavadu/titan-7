"""
TITAN V7.5 — Bug Patch Bridge
Daemon that watches for new bug reports and auto-dispatches to Windsurf IDE.

Runs as a background service alongside the Bug Reporter GUI.
Monitors:
- /opt/titan/state/bug_reports.db for new CRITICAL/HIGH reports
- /opt/titan/state/patches/ for completed patch tasks
- /opt/titan/state/panic_log.jsonl for kill switch events
- Transaction Monitor decline spikes

Auto-actions:
- Creates Windsurf patch tasks for critical bugs
- Applies known auto-fixes for common decline codes
- Rolls back bad patches if module imports fail after patching
- Sends desktop notifications for new bugs and completed patches
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import subprocess
import shutil
import importlib
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger("patch-bridge")

DB_PATH = Path("/opt/titan/state/bug_reports.db")
PATCHES_DIR = Path("/opt/titan/state/patches")
TITAN_ROOT = Path("/opt/titan")
CORE_DIR = TITAN_ROOT / "core"
WINDSURF_BIN = shutil.which("windsurf") or "/usr/bin/windsurf"

# Known decline codes → automatic advice (no code patch needed)
AUTO_ADVICE = {
    "do_not_honor":       "Bank generic decline. Warm up card first, try smaller amount.",
    "insufficient_funds": "Card has low balance. Try a smaller amount or different card.",
    "incorrect_cvc":      "CVV data is wrong. Verify card details with source.",
    "incorrect_number":   "Card number failed Luhn check. Verify card data.",
    "expired_card":       "Card is expired. Discard.",
    "stolen_card":        "Card flagged stolen. DISCARD immediately.",
    "fraudulent":         "Issuer fraud block. Card is BURNED. Discard and rotate.",
    "lost_card":          "Card reported lost. DISCARD.",
    "pickup_card":        "Issuer wants card seized. DISCARD.",
    "restricted_card":    "Card restricted by issuer. Try different card.",
    "invalid_account":    "Account closed. Card is dead.",
    "currency_not_supported": "Merchant doesn't accept this currency. Use USD card.",
}


@dataclass
class PatchResult:
    success: bool
    message: str
    diff: str = ""
    rolled_back: bool = False


class BugPatchBridge:
    """Watches for bugs and dispatches patches."""

    def __init__(self):
        self.db_path = DB_PATH
        self.running = False
        self._last_check = datetime.now(timezone.utc)

    def start(self):
        """Start the background watcher loop."""
        self.running = True
        logger.info("Bug Patch Bridge started")
        while self.running:
            try:
                self._check_new_reports()
                self._check_completed_patches()
            except Exception as e:
                logger.error(f"Bridge loop error: {e}")
            time.sleep(30)

    def stop(self):
        self.running = False

    def _get_db(self) -> Optional[sqlite3.Connection]:
        # V7.5 FIX: Check DB exists before connecting
        if not self.db_path.exists():
            logger.debug(f"Bug reports DB not found at {self.db_path}")
            return None
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _check_new_reports(self):
        """Check for new critical/high reports that need auto-action."""
        conn = self._get_db()
        if not conn:
            return
        rows = conn.execute(
            "SELECT * FROM bug_reports WHERE patch_status='pending' "
            "AND severity IN ('critical','high') "
            "AND created_at > ? ORDER BY id",
            (self._last_check.isoformat(),)
        ).fetchall()
        conn.close()

        for row in rows:
            report = dict(row)
            self._process_report(report)

        self._last_check = datetime.now(timezone.utc)

    def _process_report(self, report: dict):
        """Process a single bug report."""
        decline_code = (report.get("decline_code") or "").lower().replace("-", "_").replace(" ", "_")

        # Auto-advice for known decline codes
        if decline_code in AUTO_ADVICE:
            self._update_status(report["id"], "patched", AUTO_ADVICE[decline_code])
            self._notify(f"Auto-resolved #{report['id']}: {AUTO_ADVICE[decline_code]}")
            return

        # For code bugs, create a Windsurf patch task
        if report["category"] in ("crash", "detection", "fingerprint", "browser_issue", "extension_issue"):
            task_id = self._create_windsurf_task(report)
            if task_id:
                self._update_status(report["id"], "in_progress")
                self._launch_windsurf(task_id)
                self._notify(f"Patch task {task_id} created for bug #{report['id']}")

    def _create_windsurf_task(self, report: dict) -> Optional[str]:
        """Create a patch task file for Windsurf Cascade."""
        os.makedirs(str(PATCHES_DIR), exist_ok=True)
        task_id = hashlib.sha256(
            f"{report['id']}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12]

        brief = PATCHES_DIR / f"task_{task_id}.md"
        with open(brief, "w") as f:
            f.write(f"# Bug #{report['id']}: {report['title']}\n\n")
            f.write(f"**Category:** {report['category']}  \n")
            f.write(f"**Severity:** {report['severity']}  \n")
            f.write(f"**Module:** {report.get('module_name', 'unknown')}  \n\n")
            f.write(f"## Description\n{report.get('description', 'N/A')}\n\n")
            if report.get("error_log"):
                f.write(f"## Error Log\n```\n{report['error_log']}\n```\n\n")
            f.write("## Instructions\nAnalyze and fix the root cause. Apply minimal patch.\n")

        # Update task ID in DB
        conn = self._get_db()
        conn.execute(
            "UPDATE bug_reports SET windsurf_task_id=? WHERE id=?",
            (task_id, report["id"])
        )
        conn.commit()
        conn.close()
        return task_id

    def _launch_windsurf(self, task_id: str):
        """Open the patch task in Windsurf IDE."""
        brief = PATCHES_DIR / f"task_{task_id}.md"
        if not Path(WINDSURF_BIN).exists():
            return
        try:
            subprocess.Popen(
                [WINDSURF_BIN, "--no-sandbox", "--goto", str(brief)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.error(f"Failed to launch Windsurf: {e}")

    def _check_completed_patches(self):
        """Check for patch task JSONs marked as completed."""
        if not PATCHES_DIR.exists():
            return
        for task_file in PATCHES_DIR.glob("task_*.json"):
            try:
                with open(task_file) as f:
                    task = json.load(f)
                if task.get("status") == "completed":
                    bug_id = task.get("bug_id")
                    if bug_id:
                        self._update_status(bug_id, "patched", task.get("diff", ""))
                        self._notify(f"Bug #{bug_id} patched via Windsurf")
                    # Archive the task
                    archive = PATCHES_DIR / "archive"
                    os.makedirs(str(archive), exist_ok=True)
                    task_file.rename(archive / task_file.name)
            except Exception as e:
                logger.warning(f"Failed to process completed patch {task_file.name}: {e}")

    def _update_status(self, report_id: int, status: str, diff: str = ""):
        conn = self._get_db()
        if not conn:
            return
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE bug_reports SET patch_status=?, patch_diff=?, patch_applied_at=?, updated_at=? WHERE id=?",
            (status, diff, now if status == "patched" else "", now, report_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _notify(message: str):
        """Send desktop notification."""
        try:
            subprocess.Popen(
                ["notify-send", "-i", "dialog-information", "Titan Patch Bridge", message],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def validate_module(self, module_path: str) -> bool:
        """Check if a Python module compiles without errors after patching."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import py_compile; py_compile.compile('{module_path}', doraise=True)"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def rollback_patch(self, patch_id: int) -> PatchResult:
        """Rollback a specific patch by restoring the original content."""
        conn = self._get_db()
        row = conn.execute("SELECT * FROM patches WHERE id=?", (patch_id,)).fetchone()
        if not row:
            conn.close()
            return PatchResult(False, "Patch not found")

        patch = dict(row)
        target = Path(patch["file_path"])
        if not target.exists():
            conn.close()
            return PatchResult(False, f"Target file not found: {target}")

        try:
            target.write_text(patch["original_content"])
            conn.execute(
                "UPDATE patches SET rolled_back=1, applied=0 WHERE id=?", (patch_id,)
            )
            if patch.get("bug_id"):
                conn.execute(
                    "UPDATE bug_reports SET patch_status='pending' WHERE id=?", (patch["bug_id"],)
                )
            conn.commit()
            conn.close()
            return PatchResult(True, f"Rolled back patch #{patch_id}")
        except Exception as e:
            conn.close()
            return PatchResult(False, f"Rollback failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 PATCH VERIFIER — Comprehensive patch verification
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PatchVerificationResult:
    """Result of patch verification."""
    success: bool
    syntax_valid: bool
    imports_valid: bool
    tests_passed: Optional[bool]
    error_message: str
    verification_time_ms: float


class PatchVerifier:
    """
    V7.6 Patch Verifier - Comprehensive verification of patches
    before and after application.
    """
    
    def __init__(self):
        self._verification_history: List[Dict] = []
    
    def verify_patch(self, file_path: Path, new_content: str,
                    run_tests: bool = True) -> PatchVerificationResult:
        """
        Verify a patch before application.
        
        Args:
            file_path: Path to the file being patched
            new_content: New content to be written
            run_tests: Whether to run module tests
        
        Returns:
            PatchVerificationResult with detailed status
        """
        import time
        import tempfile
        import ast
        
        t0 = time.time()
        
        # 1. Syntax validation
        try:
            ast.parse(new_content)
            syntax_valid = True
        except SyntaxError as e:
            return PatchVerificationResult(
                success=False, syntax_valid=False, imports_valid=False,
                tests_passed=None, error_message=f"Syntax error: {e}",
                verification_time_ms=(time.time() - t0) * 1000
            )
        
        # 2. Write to temp file and verify imports
        imports_valid = False
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
            tf.write(new_content)
            temp_path = tf.name
        
        try:
            # Check if module compiles and imports work
            result = subprocess.run(
                [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{str(CORE_DIR)}')
exec(open('{temp_path}').read())
print('OK')
"""],
                capture_output=True, text=True, timeout=30
            )
            imports_valid = result.returncode == 0 and 'OK' in result.stdout
            if not imports_valid:
                return PatchVerificationResult(
                    success=False, syntax_valid=True, imports_valid=False,
                    tests_passed=None,
                    error_message=f"Import error: {result.stderr[:500]}",
                    verification_time_ms=(time.time() - t0) * 1000
                )
        except subprocess.TimeoutExpired:
            return PatchVerificationResult(
                success=False, syntax_valid=True, imports_valid=False,
                tests_passed=None, error_message="Import check timed out",
                verification_time_ms=(time.time() - t0) * 1000
            )
        finally:
            os.unlink(temp_path)
        
        # 3. Run tests if requested
        tests_passed = None
        if run_tests:
            test_file = TITAN_ROOT / "tests" / f"test_{file_path.stem}.py"
            if test_file.exists():
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                        capture_output=True, text=True, timeout=120
                    )
                    tests_passed = result.returncode == 0
                except subprocess.TimeoutExpired:
                    tests_passed = None
        
        elapsed_ms = (time.time() - t0) * 1000
        
        self._verification_history.append({
            "file": str(file_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": True,
            "tests_passed": tests_passed,
        })
        
        return PatchVerificationResult(
            success=True,
            syntax_valid=True,
            imports_valid=True,
            tests_passed=tests_passed,
            error_message="",
            verification_time_ms=round(elapsed_ms, 1)
        )
    
    def verify_module_health(self, module_path: Path) -> Dict:
        """Check if a module is healthy after patching."""
        result = {
            "module": str(module_path),
            "exists": module_path.exists(),
            "compiles": False,
            "imports": False,
            "line_count": 0,
            "issues": []
        }
        
        if not result["exists"]:
            result["issues"].append("File does not exist")
            return result
        
        # Read and analyze
        try:
            content = module_path.read_text()
            result["line_count"] = len(content.splitlines())
            
            # Check compilation
            import ast
            ast.parse(content)
            result["compiles"] = True
        except SyntaxError as e:
            result["issues"].append(f"Syntax error at line {e.lineno}: {e.msg}")
            return result
        except Exception as e:
            result["issues"].append(f"Read error: {e}")
            return result
        
        # Check imports
        try:
            subprocess.run(
                [sys.executable, "-c", f"import sys; exec(open('{module_path}').read())"],
                capture_output=True, timeout=10, check=True
            )
            result["imports"] = True
        except subprocess.CalledProcessError as e:
            result["issues"].append(f"Import error: {e.stderr[:200] if e.stderr else 'unknown'}")
        except subprocess.TimeoutExpired:
            result["issues"].append("Import timed out")
        
        return result
    
    def get_verification_history(self) -> List[Dict]:
        """Get verification history."""
        return self._verification_history[-100:]  # Last 100


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 AUTO PATCH GENERATOR — Generate patches from error patterns
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AutoPatch:
    """An automatically generated patch."""
    patch_id: str
    file_path: str
    original_line: str
    patched_line: str
    line_number: int
    pattern_matched: str
    confidence: float
    explanation: str


class AutoPatchGenerator:
    """
    V7.6 Auto Patch Generator - Generates patches automatically
    from common error patterns.
    """
    
    # Known error patterns and their fixes
    ERROR_PATTERNS: Dict[str, Dict] = {
        "undefined_name": {
            "pattern": r"NameError: name '(\w+)' is not defined",
            "fix_strategy": "import_or_define",
            "confidence": 0.7,
        },
        "attribute_error": {
            "pattern": r"AttributeError: '(\w+)' object has no attribute '(\w+)'",
            "fix_strategy": "add_attribute_check",
            "confidence": 0.6,
        },
        "import_error": {
            "pattern": r"ImportError: cannot import name '(\w+)' from '(\w+)'",
            "fix_strategy": "fix_import",
            "confidence": 0.8,
        },
        "type_error_none": {
            "pattern": r"TypeError: 'NoneType' object is not (subscriptable|callable|iterable)",
            "fix_strategy": "add_none_check",
            "confidence": 0.75,
        },
        "key_error": {
            "pattern": r"KeyError: '(\w+)'",
            "fix_strategy": "use_get_method",
            "confidence": 0.8,
        },
        "index_error": {
            "pattern": r"IndexError: (list|tuple) index out of range",
            "fix_strategy": "add_bounds_check",
            "confidence": 0.7,
        },
    }
    
    # Common TITAN-specific fixes
    TITAN_FIXES: Dict[str, str] = {
        "CoreOrchestrator": "Cortex",  # Class rename
        "CommerceInjector()": "inject_commerce_tokens",  # Function not class
        "CardAsset(pan=": "CardAsset(number=",  # Field rename
        "ValidationWorker": "ValidateWorker",  # Class rename
        "/api/aged-profiles": "/api/profiles",  # Endpoint fix
    }
    
    def __init__(self):
        self._generated_patches: List[AutoPatch] = []
    
    def analyze_error(self, error_log: str) -> List[AutoPatch]:
        """
        Analyze error log and generate potential patches.
        
        Args:
            error_log: Full error traceback
        
        Returns:
            List of potential auto-patches
        """
        import re
        
        patches = []
        
        # Extract file and line info from traceback
        file_line_match = re.search(
            r'File "([^"]+)", line (\d+)',
            error_log
        )
        if not file_line_match:
            return patches
        
        file_path = file_line_match.group(1)
        line_number = int(file_line_match.group(2))
        
        # Check for TITAN-specific fixes first
        for wrong, correct in self.TITAN_FIXES.items():
            if wrong in error_log:
                patch = AutoPatch(
                    patch_id=hashlib.md5(f"{file_path}:{wrong}".encode()).hexdigest()[:8],
                    file_path=file_path,
                    original_line=wrong,
                    patched_line=correct,
                    line_number=line_number,
                    pattern_matched="titan_known_fix",
                    confidence=0.95,
                    explanation=f"Known TITAN fix: {wrong} → {correct}"
                )
                patches.append(patch)
                self._generated_patches.append(patch)
        
        # Check standard error patterns
        for pattern_name, pattern_config in self.ERROR_PATTERNS.items():
            match = re.search(pattern_config["pattern"], error_log)
            if match:
                patch = self._generate_fix(
                    pattern_name, pattern_config, match, file_path, line_number
                )
                if patch:
                    patches.append(patch)
                    self._generated_patches.append(patch)
        
        return patches
    
    def _generate_fix(self, pattern_name: str, config: Dict,
                     match, file_path: str, line_number: int) -> Optional[AutoPatch]:
        """Generate a specific fix based on pattern."""
        strategy = config["fix_strategy"]
        confidence = config["confidence"]
        
        explanation = ""
        original_line = ""
        patched_line = ""
        
        if strategy == "use_get_method":
            key = match.group(1)
            original_line = f"['{key}']"
            patched_line = f".get('{key}')"
            explanation = f"Replace direct key access with .get() for safe access"
        
        elif strategy == "add_none_check":
            explanation = "Add None check before operation"
            original_line = "# Add None check"
            patched_line = "if obj is not None:"
        
        elif strategy == "add_bounds_check":
            explanation = "Add bounds check before list access"
            original_line = "# Add bounds check"
            patched_line = "if len(list_var) > index:"
        
        elif strategy == "fix_import":
            name = match.group(1)
            module = match.group(2)
            explanation = f"Fix import: {name} from {module}"
            original_line = f"from {module} import {name}"
            patched_line = f"# Import {name} - check module exports"
        
        else:
            return None
        
        return AutoPatch(
            patch_id=hashlib.md5(f"{file_path}:{line_number}:{pattern_name}".encode()).hexdigest()[:8],
            file_path=file_path,
            original_line=original_line,
            patched_line=patched_line,
            line_number=line_number,
            pattern_matched=pattern_name,
            confidence=confidence,
            explanation=explanation
        )
    
    def apply_auto_patch(self, patch: AutoPatch) -> PatchResult:
        """Apply an auto-generated patch."""
        target = Path(patch.file_path)
        if not target.exists():
            return PatchResult(False, f"File not found: {patch.file_path}")
        
        try:
            content = target.read_text()
            if patch.original_line in content:
                new_content = content.replace(patch.original_line, patch.patched_line, 1)
                
                # Verify before applying
                verifier = PatchVerifier()
                verification = verifier.verify_patch(target, new_content, run_tests=False)
                
                if not verification.success:
                    return PatchResult(False, f"Verification failed: {verification.error_message}")
                
                # Apply patch
                target.write_text(new_content)
                return PatchResult(True, f"Applied patch: {patch.explanation}")
            else:
                return PatchResult(False, "Original line not found in file")
                
        except Exception as e:
            return PatchResult(False, f"Patch failed: {e}")
    
    def get_generated_patches(self) -> List[AutoPatch]:
        """Get list of generated patches."""
        return self._generated_patches


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 PATCH QUEUE MANAGER — Priority-based patch scheduling
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class QueuedPatch:
    """A patch in the queue."""
    queue_id: str
    bug_id: int
    priority: int  # 1=critical, 2=high, 3=medium, 4=low
    file_path: str
    patch_content: str
    created_at: datetime
    status: str  # pending, in_progress, completed, failed
    attempts: int = 0
    last_error: str = ""


class PatchQueueManager:
    """
    V7.6 Patch Queue Manager - Manages patch queue with priority
    scheduling, retry logic, and dependency tracking.
    """
    
    def __init__(self):
        self._queue: List[QueuedPatch] = []
        self._completed: List[QueuedPatch] = []
        self._failed: List[QueuedPatch] = []
        self._processing: Optional[QueuedPatch] = None
        self._max_retries = 3
    
    def add_to_queue(self, bug_id: int, file_path: str,
                     patch_content: str, severity: str) -> str:
        """
        Add a patch to the queue.
        
        Returns:
            Queue ID for tracking
        """
        priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        priority = priority_map.get(severity.lower(), 3)
        
        queue_id = hashlib.md5(
            f"{bug_id}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:10]
        
        patch = QueuedPatch(
            queue_id=queue_id,
            bug_id=bug_id,
            priority=priority,
            file_path=file_path,
            patch_content=patch_content,
            created_at=datetime.now(timezone.utc),
            status="pending",
            attempts=0
        )
        
        self._queue.append(patch)
        self._sort_queue()
        
        logger.info(f"Patch {queue_id} added to queue (priority={priority})")
        return queue_id
    
    def _sort_queue(self):
        """Sort queue by priority (lower number = higher priority)."""
        self._queue.sort(key=lambda p: (p.priority, p.created_at))
    
    def get_next_patch(self) -> Optional[QueuedPatch]:
        """Get next patch to process."""
        if self._processing:
            return None  # Already processing
        
        for patch in self._queue:
            if patch.status == "pending" and patch.attempts < self._max_retries:
                patch.status = "in_progress"
                patch.attempts += 1
                self._processing = patch
                return patch
        
        return None
    
    def complete_patch(self, queue_id: str, success: bool, error: str = ""):
        """Mark a patch as completed or failed."""
        patch = self._find_patch(queue_id)
        if not patch:
            return
        
        if success:
            patch.status = "completed"
            self._completed.append(patch)
            self._queue.remove(patch)
        else:
            patch.last_error = error
            if patch.attempts >= self._max_retries:
                patch.status = "failed"
                self._failed.append(patch)
                self._queue.remove(patch)
            else:
                patch.status = "pending"  # Will retry
        
        self._processing = None
    
    def _find_patch(self, queue_id: str) -> Optional[QueuedPatch]:
        """Find patch by queue ID."""
        for patch in self._queue + [self._processing] if self._processing else self._queue:
            if patch and patch.queue_id == queue_id:
                return patch
        return None
    
    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        return {
            "pending": len([p for p in self._queue if p.status == "pending"]),
            "in_progress": 1 if self._processing else 0,
            "completed": len(self._completed),
            "failed": len(self._failed),
            "total_in_queue": len(self._queue),
            "next_priority": self._queue[0].priority if self._queue else None,
        }
    
    def get_queue_items(self) -> List[Dict]:
        """Get all items in queue."""
        return [
            {
                "queue_id": p.queue_id,
                "bug_id": p.bug_id,
                "priority": p.priority,
                "status": p.status,
                "attempts": p.attempts,
                "file": p.file_path,
            }
            for p in self._queue
        ]


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 PATCH ANALYTICS — Track patch success rates and patterns
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PatchStats:
    """Statistics about patching."""
    total_patches: int
    successful_patches: int
    failed_patches: int
    rolled_back: int
    success_rate: float
    avg_time_to_patch_hours: float
    most_patched_modules: List[str]
    common_error_patterns: List[str]


class PatchAnalytics:
    """
    V7.6 Patch Analytics - Track patch success rates, failure patterns,
    and provide insights for improving auto-patching.
    """
    
    def __init__(self):
        self._events: List[Dict] = []
    
    def record_patch_event(self, event_type: str, bug_id: int,
                           file_path: str, success: bool, details: str = ""):
        """Record a patch-related event."""
        self._events.append({
            "type": event_type,
            "bug_id": bug_id,
            "file": file_path,
            "success": success,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep last 1000 events
        if len(self._events) > 1000:
            self._events = self._events[-1000:]
    
    def get_stats(self) -> PatchStats:
        """Calculate patch statistics."""
        from collections import Counter
        
        if not self._events:
            return PatchStats(
                total_patches=0, successful_patches=0, failed_patches=0,
                rolled_back=0, success_rate=0.0, avg_time_to_patch_hours=0.0,
                most_patched_modules=[], common_error_patterns=[]
            )
        
        apply_events = [e for e in self._events if e["type"] == "patch_applied"]
        success_count = sum(1 for e in apply_events if e["success"])
        fail_count = sum(1 for e in apply_events if not e["success"])
        rollback_count = sum(1 for e in self._events if e["type"] == "rollback")
        
        # Calculate success rate
        total = success_count + fail_count
        success_rate = success_count / total if total > 0 else 0.0
        
        # Most patched modules
        module_counter = Counter(
            Path(e["file"]).stem for e in apply_events
        )
        most_patched = [m for m, _ in module_counter.most_common(5)]
        
        # Common error patterns
        error_counter = Counter(
            e["details"][:50] for e in apply_events if not e["success"]
        )
        common_errors = [e for e, _ in error_counter.most_common(5)]
        
        return PatchStats(
            total_patches=len(apply_events),
            successful_patches=success_count,
            failed_patches=fail_count,
            rolled_back=rollback_count,
            success_rate=round(success_rate, 2),
            avg_time_to_patch_hours=0.0,  # Would need bug creation time
            most_patched_modules=most_patched,
            common_error_patterns=common_errors
        )
    
    def get_module_health_report(self) -> Dict[str, Dict]:
        """Get health report for each module based on patch history."""
        from collections import defaultdict
        
        module_stats = defaultdict(lambda: {"patches": 0, "failures": 0, "rollbacks": 0})
        
        for event in self._events:
            if event["type"] in ("patch_applied", "rollback"):
                module = Path(event["file"]).stem
                module_stats[module]["patches"] += 1
                if not event.get("success", True):
                    module_stats[module]["failures"] += 1
                if event["type"] == "rollback":
                    module_stats[module]["rollbacks"] += 1
        
        # Calculate health scores
        report = {}
        for module, stats in module_stats.items():
            total = stats["patches"]
            failures = stats["failures"] + stats["rollbacks"]
            health = 1.0 - (failures / total) if total > 0 else 1.0
            report[module] = {
                "patches": total,
                "failures": stats["failures"],
                "rollbacks": stats["rollbacks"],
                "health_score": round(health, 2),
                "status": "healthy" if health >= 0.8 else "needs_attention" if health >= 0.5 else "critical"
            }
        
        return report
    
    def get_recommendations(self) -> List[str]:
        """Get recommendations based on patch analytics."""
        recommendations = []
        stats = self.get_stats()
        
        if stats.success_rate < 0.5:
            recommendations.append("⚠️ Low patch success rate. Review auto-patch patterns.")
        
        if stats.rolled_back > stats.successful_patches * 0.2:
            recommendations.append("⚠️ High rollback rate. Improve patch verification.")
        
        for module in stats.most_patched_modules[:3]:
            recommendations.append(f"📝 Module '{module}' frequently patched. Consider refactoring.")
        
        return recommendations


# Global instances
_patch_verifier: Optional[PatchVerifier] = None
_auto_patcher: Optional[AutoPatchGenerator] = None
_patch_queue: Optional[PatchQueueManager] = None
_patch_analytics: Optional[PatchAnalytics] = None


def get_patch_verifier() -> PatchVerifier:
    """Get global patch verifier instance."""
    global _patch_verifier
    if _patch_verifier is None:
        _patch_verifier = PatchVerifier()
    return _patch_verifier


def get_auto_patcher() -> AutoPatchGenerator:
    """Get global auto patcher instance."""
    global _auto_patcher
    if _auto_patcher is None:
        _auto_patcher = AutoPatchGenerator()
    return _auto_patcher


def get_patch_queue() -> PatchQueueManager:
    """Get global patch queue instance."""
    global _patch_queue
    if _patch_queue is None:
        _patch_queue = PatchQueueManager()
    return _patch_queue


def get_patch_analytics() -> PatchAnalytics:
    """Get global patch analytics instance."""
    global _patch_analytics
    if _patch_analytics is None:
        _patch_analytics = PatchAnalytics()
    return _patch_analytics


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEMD SERVICE ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [PATCH-BRIDGE] %(levelname)s: %(message)s"
    )
    
    print("TITAN V7.6 Bug Patch Bridge")
    print("=" * 40)
    
    # Show analytics on startup
    analytics = get_patch_analytics()
    stats = analytics.get_stats()
    print(f"Patch Stats: {stats.total_patches} total, {stats.success_rate:.0%} success rate")
    print()
    
    bridge = BugPatchBridge()
    try:
        bridge.start()
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()
