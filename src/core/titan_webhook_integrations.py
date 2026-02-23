"""
TITAN V9.1 — Webhook Integration Hub
Receives webhooks from self-hosted Docker services and routes them
into the Titan operation pipeline.

Integrations:
    1. Changedetection.io  — Target defense change alerts
    2. n8n                 — Workflow automation triggers
    3. Uptime Kuma         — Service health alerts

Architecture:
    - Flask-based HTTP server on TITAN_WEBHOOK_PORT (default: 9300)
    - Each endpoint validates payload, logs, and dispatches to relevant module
    - Thread-safe, non-blocking
    - Auto-starts if TITAN_WEBHOOK_ENABLED=true in titan.env

Usage:
    from titan_webhook_integrations import start_webhook_server, get_webhook_stats

    start_webhook_server()  # Starts on :9300
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("TITAN-WEBHOOKS")

_FLASK_AVAILABLE = False
try:
    from flask import Flask, request as flask_request, jsonify
    _FLASK_AVAILABLE = True
except ImportError:
    logger.debug("Flask not installed — webhook server disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK EVENT LOG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WebhookEvent:
    source: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    processed: bool = False
    error: str = ""


_event_log: List[WebhookEvent] = []
_event_lock = threading.Lock()
_MAX_EVENTS = 500


def _log_event(event: WebhookEvent):
    with _event_lock:
        _event_log.insert(0, event)
        if len(_event_log) > _MAX_EVENTS:
            _event_log.pop()


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGEDETECTION.IO HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_changedetection(payload: Dict) -> Dict:
    """
    Handle webhook from Changedetection.io when a monitored target page changes.

    Changedetection sends POST with:
        - url: the watched URL
        - title: page title
        - current_snapshot: current page hash
        - previous_snapshot: previous page hash
        - diff_url: URL to view the diff

    We route this to track_defense_changes() in ai_intelligence_engine.py
    so the AI can analyze what changed (new antifraud scripts, updated versions, etc).
    """
    url = payload.get("url", "")
    title = payload.get("title", "")
    diff_url = payload.get("diff_url", "")

    logger.info(f"[CHANGEDETECT] Target change detected: {url}")

    event = WebhookEvent(
        source="changedetection",
        event_type="target_defense_change",
        payload=payload,
    )

    # Route to AI engine for analysis
    analysis = {}
    try:
        from ai_intelligence_engine import track_defense_changes
        analysis = track_defense_changes(
            domain=_extract_domain(url),
            change_summary=f"Page changed: {title}. Diff: {diff_url}",
            change_type="dom_change",
        )
        event.processed = True
        logger.info(f"[CHANGEDETECT] AI analysis complete for {url}")
    except ImportError:
        event.error = "ai_intelligence_engine not available"
        logger.warning("[CHANGEDETECT] AI engine not available for analysis")
    except Exception as e:
        event.error = str(e)
        logger.error(f"[CHANGEDETECT] Analysis failed: {e}")

    # Send ntfy alert
    try:
        from titan_self_hosted_stack import get_ntfy_client
        ntfy = get_ntfy_client()
        if ntfy and ntfy.is_available:
            domain = _extract_domain(url)
            ntfy.send(
                f"🔄 Target defense change: {domain}\n{title}",
                priority="high",
                tags=["warning", "target_change"],
            )
    except Exception:
        pass

    _log_event(event)

    return {
        "status": "processed",
        "domain": _extract_domain(url),
        "ai_analysis": analysis if analysis else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# N8N WEBHOOK HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_n8n_decline_retry(payload: Dict) -> Dict:
    """
    Handle n8n workflow trigger for decline → analyze → retry.

    n8n sends POST with:
        - operation_id: original op ID
        - decline_code: the decline code
        - target: target domain
        - bin_prefix: card BIN
        - amount: transaction amount
        - retry_params: adjusted params from n8n workflow

    We run AI autopsy and return recommendation.
    """
    op_id = payload.get("operation_id", "")
    decline_code = payload.get("decline_code", "")
    target = payload.get("target", "")
    bin_prefix = payload.get("bin_prefix", "")
    amount = payload.get("amount", 0)

    logger.info(f"[N8N] Decline retry request: op={op_id} code={decline_code} target={target}")

    event = WebhookEvent(
        source="n8n",
        event_type="decline_retry",
        payload=payload,
    )

    # Run AI decline autopsy
    recommendation = {}
    try:
        from ai_intelligence_engine import autopsy_decline
        recommendation = autopsy_decline(
            decline_code=decline_code,
            target=target,
            bin6=bin_prefix,
            amount=float(amount),
        )
        event.processed = True
    except ImportError:
        event.error = "ai_intelligence_engine.autopsy_decline not available"
    except Exception as e:
        event.error = str(e)
        logger.error(f"[N8N] Decline autopsy failed: {e}")

    _log_event(event)

    return {
        "status": "analyzed",
        "operation_id": op_id,
        "recommendation": recommendation,
    }


def _handle_n8n_target_recon(payload: Dict) -> Dict:
    """
    Handle n8n workflow trigger for target recon.

    n8n sends POST with:
        - domain: target domain to recon
    """
    domain = payload.get("domain", "")
    logger.info(f"[N8N] Target recon request: {domain}")

    event = WebhookEvent(
        source="n8n",
        event_type="target_recon",
        payload=payload,
    )

    recon = {}
    try:
        from ai_intelligence_engine import analyze_target
        recon = analyze_target(domain)
        event.processed = True
    except ImportError:
        event.error = "ai_intelligence_engine.analyze_target not available"
    except Exception as e:
        event.error = str(e)
        logger.error(f"[N8N] Target recon failed: {e}")

    _log_event(event)

    return {
        "status": "analyzed",
        "domain": domain,
        "recon": recon,
    }


def _handle_n8n_generic(payload: Dict) -> Dict:
    """Handle generic n8n webhook — log and acknowledge."""
    event = WebhookEvent(
        source="n8n",
        event_type=payload.get("event", "generic"),
        payload=payload,
        processed=True,
    )
    _log_event(event)
    return {"status": "received", "event": payload.get("event", "generic")}


# ═══════════════════════════════════════════════════════════════════════════════
# UPTIME KUMA HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_uptime_kuma(payload: Dict) -> Dict:
    """
    Handle Uptime Kuma alert webhook when a service goes down/up.

    Kuma sends:
        - monitor: {name, url, type}
        - heartbeat: {status, msg, time}
        - msg: human-readable message
    """
    monitor = payload.get("monitor", {})
    heartbeat = payload.get("heartbeat", {})
    name = monitor.get("name", "unknown")
    status = heartbeat.get("status", 0)
    msg = payload.get("msg", "")

    status_str = "UP" if status == 1 else "DOWN"
    logger.warning(f"[KUMA] Service {name}: {status_str} — {msg}")

    event = WebhookEvent(
        source="uptime_kuma",
        event_type=f"service_{status_str.lower()}",
        payload=payload,
        processed=True,
    )
    _log_event(event)

    # Forward to ntfy for push notification
    try:
        from titan_self_hosted_stack import get_ntfy_client
        ntfy = get_ntfy_client()
        if ntfy and ntfy.is_available:
            priority = "urgent" if status != 1 else "default"
            emoji = "🔴" if status != 1 else "🟢"
            ntfy.send(
                f"{emoji} {name}: {status_str}\n{msg}",
                priority=priority,
                tags=["service_alert"],
            )
    except Exception:
        pass

    return {"status": "received", "service": name, "service_status": status_str}


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.hostname or url
    except Exception:
        return url


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK APP + SERVER
# ═══════════════════════════════════════════════════════════════════════════════

_app: Optional[Flask] = None
_server_thread: Optional[threading.Thread] = None
_server_started = False


def _create_app() -> Optional[Flask]:
    """Create Flask app with webhook routes."""
    if not _FLASK_AVAILABLE:
        return None

    app = Flask("titan-webhooks")
    app.logger.setLevel(logging.WARNING)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "titan-webhooks"})

    @app.route("/webhook/changedetection", methods=["POST"])
    def changedetection_webhook():
        try:
            payload = flask_request.get_json(force=True, silent=True) or {}
            result = _handle_changedetection(payload)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Changedetection webhook error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook/n8n/decline-retry", methods=["POST"])
    def n8n_decline_retry():
        try:
            payload = flask_request.get_json(force=True, silent=True) or {}
            result = _handle_n8n_decline_retry(payload)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"n8n decline-retry webhook error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook/n8n/target-recon", methods=["POST"])
    def n8n_target_recon():
        try:
            payload = flask_request.get_json(force=True, silent=True) or {}
            result = _handle_n8n_target_recon(payload)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"n8n target-recon webhook error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook/n8n", methods=["POST"])
    def n8n_generic():
        try:
            payload = flask_request.get_json(force=True, silent=True) or {}
            result = _handle_n8n_generic(payload)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook/uptime-kuma", methods=["POST"])
    def uptime_kuma_webhook():
        try:
            payload = flask_request.get_json(force=True, silent=True) or {}
            result = _handle_uptime_kuma(payload)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Uptime Kuma webhook error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook/events", methods=["GET"])
    def list_events():
        """List recent webhook events for debugging."""
        with _event_lock:
            events = [
                {
                    "source": e.source,
                    "type": e.event_type,
                    "time": datetime.fromtimestamp(e.timestamp, tz=timezone.utc).isoformat(),
                    "processed": e.processed,
                    "error": e.error,
                }
                for e in _event_log[:50]
            ]
        return jsonify({"events": events, "total": len(_event_log)})

    return app


def start_webhook_server(port: int = None) -> bool:
    """Start the webhook integration server in a background thread."""
    global _app, _server_thread, _server_started

    if _server_started:
        return True

    if not _FLASK_AVAILABLE:
        logger.warning("Flask not installed — webhook server cannot start")
        return False

    _app = _create_app()
    if not _app:
        return False

    port = port or int(os.getenv("TITAN_WEBHOOK_PORT", "9300"))

    def _run():
        global _server_started
        try:
            _server_started = True
            logger.info(f"Webhook server starting on :{port}")
            _app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Webhook server failed: {e}")
            _server_started = False

    _server_thread = threading.Thread(target=_run, daemon=True, name="titan-webhook-server")
    _server_thread.start()
    time.sleep(0.5)
    return _server_started


def get_webhook_stats() -> Dict:
    """Get webhook server status and event statistics."""
    with _event_lock:
        sources = {}
        for e in _event_log:
            sources[e.source] = sources.get(e.source, 0) + 1

    return {
        "server_running": _server_started,
        "flask_available": _FLASK_AVAILABLE,
        "port": int(os.getenv("TITAN_WEBHOOK_PORT", "9300")),
        "total_events": len(_event_log),
        "events_by_source": sources,
        "endpoints": {
            "changedetection": "/webhook/changedetection",
            "n8n_decline_retry": "/webhook/n8n/decline-retry",
            "n8n_target_recon": "/webhook/n8n/target-recon",
            "n8n_generic": "/webhook/n8n",
            "uptime_kuma": "/webhook/uptime-kuma",
            "events_log": "/webhook/events",
            "health": "/health",
        },
    }


def get_recent_events(source: str = None, limit: int = 20) -> List[Dict]:
    """Get recent webhook events, optionally filtered by source."""
    with _event_lock:
        filtered = _event_log if not source else [e for e in _event_log if e.source == source]
        return [
            {
                "source": e.source,
                "type": e.event_type,
                "timestamp": e.timestamp,
                "processed": e.processed,
                "error": e.error,
                "payload_keys": list(e.payload.keys()),
            }
            for e in filtered[:limit]
        ]
