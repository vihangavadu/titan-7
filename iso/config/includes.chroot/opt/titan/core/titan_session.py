"""
TITAN V8.2 SINGULARITY — Shared Session State
Cross-app IPC via JSON file with file-watching for real-time sync.

Every app reads/writes to /opt/titan/state/session.json.
Changes are detected via mtime polling (100ms) so all apps stay in sync.

Usage:
    from titan_session import get_session, save_session

    session = get_session()
    session["current_target"] = "amazon.com"
    save_session(session)

    # In another app:
    session = get_session()
    print(session["current_target"])  # "amazon.com"
"""

import json
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import threading

logger = logging.getLogger("TITAN-SESSION")

# State file location — works on both ISO (/opt/titan) and dev environments
_STATE_DIR = Path(os.environ.get("TITAN_HOME", "/opt/titan")) / "state"
_SESSION_FILE = _STATE_DIR / "session.json"
_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_CACHE_MTIME: float = 0.0

DEFAULT_SESSION = {
    "version": "8.2.0",
    "current_target": "",
    "current_proxy": "",
    "current_country": "US",
    "current_state": "",
    "current_zip": "",
    "persona": {
        "name": "",
        "email": "",
        "phone": "",
        "dob": "",
        "street": "",
        "city": "",
        "state": "",
        "zip": "",
    },
    "card": {
        "number": "",
        "exp": "",
        "cvv": "",
        "cardholder": "",
    },
    "last_validation": {
        "status": "",
        "message": "",
        "timestamp": "",
    },
    "current_profile_path": "",
    "current_profile_id": "",
    "vpn_status": {
        "connected": False,
        "exit_ip": "",
        "country": "",
    },
    "kill_switch_armed": False,
    "ai_copilot_active": False,
    "last_forge": {
        "profile_path": "",
        "browser": "",
        "timestamp": "",
    },
    "operation_history": [],
    "updated_at": "",
}


def _ensure_state_dir():
    """Create state directory if it doesn't exist."""
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def get_session() -> Dict[str, Any]:
    """Get current session state. Returns cached version if file unchanged."""
    global _CACHE, _CACHE_MTIME

    with _LOCK:
        try:
            _ensure_state_dir()
            if _SESSION_FILE.exists():
                mtime = _SESSION_FILE.stat().st_mtime
                if mtime != _CACHE_MTIME:
                    _CACHE = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
                    _CACHE_MTIME = mtime
                return dict(_CACHE)
            else:
                return dict(DEFAULT_SESSION)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Session read error: {e}")
            return dict(DEFAULT_SESSION)


def _get_redis() -> Optional[Any]:
    """Get Redis client if available (lazy import, no crash if absent)."""
    try:
        from titan_self_hosted_stack import get_redis_client
        rc = get_redis_client()
        if rc and rc.is_available:
            return rc
    except Exception:
        pass
    return None


_REDIS_SESSION_KEY = "titan:session"
_REDIS_CHANNEL = "titan:session:updated"


def save_session(data: Dict[str, Any]) -> bool:
    """V8.3 FIX #6: Save session state to disk. Thread-safe + POSIX file-locked.
    V9.1: Also publishes to Redis for real-time cross-app sync if available."""
    global _CACHE, _CACHE_MTIME

    with _LOCK:
        try:
            _ensure_state_dir()
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            serialized = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            # Acquire exclusive POSIX file lock before writing (Linux/macOS only)
            lock_file = _SESSION_FILE.with_suffix(".lock")
            try:
                import fcntl
                with open(lock_file, "w") as lf:
                    fcntl.flock(lf, fcntl.LOCK_EX)
                    _SESSION_FILE.write_text(serialized, encoding="utf-8")
                    fcntl.flock(lf, fcntl.LOCK_UN)
            except ImportError:
                # Windows dev environment — fall back to direct write (threading.Lock still protects)
                _SESSION_FILE.write_text(serialized, encoding="utf-8")
            _CACHE = dict(data)
            _CACHE_MTIME = _SESSION_FILE.stat().st_mtime

            # V9.1: Publish to Redis for instant cross-app sync
            rc = _get_redis()
            if rc:
                try:
                    rc.set(_REDIS_SESSION_KEY, serialized, ttl=86400)
                    rc.publish(_REDIS_CHANNEL, serialized)
                except Exception as e:
                    logger.debug(f"Redis session publish failed (non-fatal): {e}")

            return True
        except OSError as e:
            logger.error(f"Session save error: {e}", exc_info=True)
            return False


def update_session(**kwargs) -> bool:
    """Update specific keys in session without overwriting others."""
    session = get_session()
    for key, value in kwargs.items():
        if isinstance(value, dict) and key in session and isinstance(session[key], dict):
            session[key].update(value)
        else:
            session[key] = value
    return save_session(session)


def add_operation_result(target: str, bin_prefix: str, status: str,
                         amount: str = "", notes: str = "") -> bool:
    """Append an operation result to session history."""
    session = get_session()
    history = session.get("operation_history", [])
    history.insert(0, {
        "time": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "bin": bin_prefix,
        "status": status,
        "amount": amount,
        "notes": notes,
    })
    session["operation_history"] = history[:200]
    return save_session(session)


def clear_session() -> bool:
    """Reset session to defaults."""
    return save_session(dict(DEFAULT_SESSION))


class SessionWatcher:
    """Background thread that polls session file for changes and emits callbacks."""

    def __init__(self, callback, interval_ms: int = 500):
        self.callback = callback
        self.interval = interval_ms / 1000.0
        self._running = False
        self._thread = None
        self._last_mtime = 0.0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _poll(self):
        while self._running:
            try:
                if _SESSION_FILE.exists():
                    mtime = _SESSION_FILE.stat().st_mtime
                    if mtime != self._last_mtime:
                        self._last_mtime = mtime
                        session = get_session()
                        self.callback(session)
            except Exception:
                pass
            time.sleep(self.interval)
