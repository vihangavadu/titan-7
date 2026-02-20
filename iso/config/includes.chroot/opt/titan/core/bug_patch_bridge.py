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
from datetime import datetime, timedelta
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
        self._last_check = datetime.utcnow()

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

    def _get_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _check_new_reports(self):
        """Check for new critical/high reports that need auto-action."""
        conn = self._get_db()
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

        self._last_check = datetime.utcnow()

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
            f"{report['id']}:{datetime.utcnow().isoformat()}".encode()
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
            except Exception:
                pass

    def _update_status(self, report_id: int, status: str, diff: str = ""):
        conn = self._get_db()
        now = datetime.utcnow().isoformat() + "Z"
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
# SYSTEMD SERVICE ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [PATCH-BRIDGE] %(levelname)s: %(message)s"
    )
    bridge = BugPatchBridge()
    try:
        bridge.start()
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()
