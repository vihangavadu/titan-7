#!/usr/bin/env python3
"""
CERBERUS BRIDGE API — Flask REST API for Cerberus AppX
=======================================================
Port: 36300
Provides external API access to Cerberus card validation engine.

Endpoints:
  POST /api/v1/validate         — Single card validation
  POST /api/v1/batch            — Batch card validation
  GET  /api/v1/bin/<bin6>       — BIN intelligence lookup
  POST /api/v1/avs/check        — AVS pre-check
  POST /api/v1/decline/decode   — Decline code decoder
  POST /api/v1/3ds/bypass       — 3DS bypass plan
  GET  /api/v1/keys             — List configured keys (masked)
  POST /api/v1/keys             — Add merchant key
  DELETE /api/v1/keys/<id>      — Remove merchant key
  GET  /api/v1/cooling/<card_hash>  — Card cooling status
  GET  /api/v1/velocity         — Issuer velocity stats
  GET  /api/v1/intelligence     — Cross-PSP correlation data
  GET  /api/v1/history          — Validation history
  GET  /api/v1/analytics        — Decline analytics
  GET  /api/v1/status           — Engine status
  GET  /api/v1/health           — Health check
"""

import sys
import os
import json
import asyncio
import logging
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Add core to path
TITAN_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TITAN_ROOT / "src" / "core"))

from flask import Flask, request, jsonify
from flask_cors import CORS

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from cerberus_core import (
        CerberusValidator, BulkValidator, CardAsset, CardStatus,
        CardType, MerchantKey, ValidationResult,
        CardCoolingSystem, IssuerVelocityTracker, CrossPSPCorrelator,
        get_osint_checklist, get_card_quality_guide, get_bank_enrollment_guide,
        CARD_QUALITY_INDICATORS, CARD_LEVEL_COMPATIBILITY
    )
    CERBERUS_CORE = True
except ImportError:
    CERBERUS_CORE = False

try:
    from cerberus_enhanced import (
        AVSEngine, BINScoringEngine, BINScore,
        AVSResult, AVSCheckResult
    )
    CERBERUS_ENHANCED = True
except ImportError:
    CERBERUS_ENHANCED = False

try:
    from decline_decoder import decode_decline
    DECLINE_DECODER = True
except ImportError:
    DECLINE_DECODER = False

try:
    from threed_bypass import get_3ds_bypass_plan
    BYPASS_ENGINE = True
except ImportError:
    BYPASS_ENGINE = False

try:
    from ai_intelligence_engine import AIIntelligenceEngine
    AI_ENGINE = True
except ImportError:
    AI_ENGINE = False

try:
    from cerberus_hyperswitch import (
        get_hyperswitch_client, get_hyperswitch_router,
        get_hyperswitch_vault, get_hyperswitch_retry,
        get_hyperswitch_analytics, is_hyperswitch_available,
        PaymentStatus, RoutingAlgorithm,
    )
    HYPERSWITCH_OK = is_hyperswitch_available()
except ImportError:
    HYPERSWITCH_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BRIDGE_PORT = int(os.environ.get("CERBERUS_BRIDGE_PORT", 36300))
BRIDGE_HOST = os.environ.get("CERBERUS_BRIDGE_HOST", "127.0.0.1")
CONFIG_DIR = Path(os.path.expanduser("~/.cerberus_appx"))
KEYS_FILE = CONFIG_DIR / "keys.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CERBERUS-BRIDGE] %(message)s")
logger = logging.getLogger("cerberus_bridge")

# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def _load_keys() -> Dict[str, List[Dict]]:
    if KEYS_FILE.exists():
        try:
            return json.loads(KEYS_FILE.read_text())
        except Exception:
            pass
    return {"stripe": [], "braintree": [], "adyen": []}


def _save_keys(keys: Dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_FILE.write_text(json.dumps(keys, indent=2))


def _load_history() -> List[Dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []


def _save_history(history: List[Dict]):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history[-10000:], indent=2))


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE STATE
# ═══════════════════════════════════════════════════════════════════════════════

class CerberusEngine:
    """Manages the Cerberus validation engine state"""

    def __init__(self):
        self.merchant_keys = _load_keys()
        self.history = _load_history()
        self.cooling = CardCoolingSystem() if CERBERUS_CORE else None
        self.velocity = IssuerVelocityTracker() if CERBERUS_CORE else None
        self.correlator = CrossPSPCorrelator() if CERBERUS_CORE else None
        self.avs_engine = AVSEngine() if CERBERUS_ENHANCED else None
        self.bin_scorer = BINScoringEngine() if CERBERUS_ENHANCED else None
        self.started_at = datetime.now()
        self.total_validations = len(self.history)

    def build_validator(self) -> Optional['CerberusValidator']:
        if not CERBERUS_CORE:
            return None
        validator = CerberusValidator()
        for provider, key_list in self.merchant_keys.items():
            for k in key_list:
                if k.get("public_key") and k.get("secret_key"):
                    validator.add_key(MerchantKey(
                        provider=provider,
                        public_key=k["public_key"],
                        secret_key=k["secret_key"],
                        merchant_id=k.get("merchant_id"),
                        is_live=k.get("is_live", True)
                    ))
        return validator

    def record_result(self, result_dict: Dict):
        result_dict["timestamp"] = datetime.now().isoformat()
        self.history.append(result_dict)
        self.total_validations += 1
        _save_history(self.history)


engine = CerberusEngine()

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)


@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "cerberus-bridge", "port": BRIDGE_PORT})


@app.route("/api/v1/status", methods=["GET"])
def status():
    return jsonify({
        "service": "cerberus-bridge",
        "version": "9.2.1",
        "started_at": engine.started_at.isoformat(),
        "total_validations": engine.total_validations,
        "modules": {
            "cerberus_core": CERBERUS_CORE,
            "cerberus_enhanced": CERBERUS_ENHANCED,
            "decline_decoder": DECLINE_DECODER,
            "bypass_engine": BYPASS_ENGINE,
            "ai_engine": AI_ENGINE,
            "hyperswitch": HYPERSWITCH_OK,
        },
        "keys_configured": {
            provider: len(keys) for provider, keys in engine.merchant_keys.items()
        },
        "history_entries": len(engine.history),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/validate", methods=["POST"])
def validate_card():
    """Validate a single card"""
    data = request.json or {}
    card_data = data.get("card") or data.get("card_data")

    if not card_data:
        return jsonify({"error": "Missing 'card' field. Format: PAN|MM|YY|CVV"}), 400

    if not CERBERUS_CORE:
        return jsonify({"error": "cerberus_core not available — BIN lookup only", "fallback": True}), 503

    validator = engine.build_validator()
    card = validator.parse_card_input(card_data)
    if not card:
        return jsonify({"error": "Could not parse card input"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(validator.validate(card))
        display = CerberusValidator.format_result_for_display(result)

        # Record
        engine.record_result(display)

        # Enrich with cooling/velocity info
        if engine.cooling:
            is_cool, wait_sec, heat = engine.cooling.is_cool(card)
            display["cooling"] = {"is_cool": is_cool, "wait_seconds": wait_sec, "heat_level": heat}
            engine.cooling.record_usage(card, "api", result.status.value)

        if engine.velocity:
            can_val, wait_sec, count, limit = engine.velocity.can_validate(card)
            display["velocity"] = {"can_validate": can_val, "wait_seconds": wait_sec, "count": count, "limit": limit}
            engine.velocity.record_validation(card)

        if engine.correlator:
            engine.correlator.record_result(card, "api", result.status.value)
            display["correlation"] = engine.correlator.get_correlation_risk(card)

        return jsonify(display)
    finally:
        loop.close()


@app.route("/api/v1/batch", methods=["POST"])
def batch_validate():
    """Batch card validation"""
    data = request.json or {}
    cards = data.get("cards", [])
    rate_limit = data.get("rate_limit", 1.0)

    if not cards:
        return jsonify({"error": "Missing 'cards' field (list of card strings)"}), 400

    if not CERBERUS_CORE:
        return jsonify({"error": "cerberus_core not available"}), 503

    validator = engine.build_validator()
    results = []

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        for card_data in cards:
            card = validator.parse_card_input(card_data)
            if card:
                result = loop.run_until_complete(validator.validate(card))
                display = CerberusValidator.format_result_for_display(result)
            else:
                display = {"status": "ERROR", "message": "Parse failed", "card": card_data[:20]}
            results.append(display)
            engine.record_result(display)

            if rate_limit > 0:
                import time
                time.sleep(rate_limit)
    finally:
        loop.close()

    # Summary
    total = len(results)
    live = sum(1 for r in results if r.get("status") == "LIVE")
    dead = sum(1 for r in results if r.get("status") == "DEAD")

    return jsonify({
        "results": results,
        "summary": {
            "total": total,
            "live": live,
            "dead": dead,
            "unknown": total - live - dead,
            "live_rate": f"{live/total*100:.1f}%" if total else "0%",
        }
    })


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/bin/<bin6>", methods=["GET"])
def bin_lookup(bin6: str):
    """BIN intelligence lookup"""
    result = {"bin": bin6}

    if CERBERUS_CORE:
        core_info = CerberusValidator.BIN_DATABASE.get(bin6, {})
        if core_info:
            result["core"] = core_info

    if CERBERUS_ENHANCED and engine.bin_scorer:
        try:
            score = engine.bin_scorer.score_bin(bin6)
            result["score"] = {
                "overall": score.overall_score,
                "bank": score.bank,
                "country": score.country,
                "card_type": score.card_type,
                "card_level": score.card_level,
                "network": score.network,
                "risk_factors": score.risk_factors,
                "recommendations": score.recommendations,
                "target_compatibility": score.target_compatibility,
                "estimated_3ds_rate": score.estimated_3ds_rate,
                "estimated_success_rate": score.estimated_success_rate,
                "avs_strictness": score.avs_strictness,
                "max_single_amount": score.max_single_amount,
                "velocity_limit_daily": score.velocity_limit_daily,
            }
        except Exception as e:
            result["score_error"] = str(e)

    if not result.get("core") and not result.get("score"):
        result["message"] = "BIN not found in database"

    return jsonify(result)


@app.route("/api/v1/avs/check", methods=["POST"])
def avs_check():
    """AVS pre-check"""
    if not CERBERUS_ENHANCED or not engine.avs_engine:
        return jsonify({"error": "cerberus_enhanced not available"}), 503

    data = request.json or {}
    required = ["card_address", "card_zip", "card_state", "input_address", "input_zip", "input_state"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    result = engine.avs_engine.check_avs(
        card_billing_address=data["card_address"],
        card_billing_zip=data["card_zip"],
        card_billing_state=data["card_state"],
        input_address=data["input_address"],
        input_zip=data["input_zip"],
        input_state=data["input_state"],
    )

    return jsonify({
        "avs_code": result.avs_code.value if hasattr(result.avs_code, 'value') else str(result.avs_code),
        "street_match": result.street_match,
        "zip_match": result.zip_match,
        "confidence": result.confidence,
        "recommendation": result.recommendation,
        "details": result.details,
    })


@app.route("/api/v1/decline/decode", methods=["POST"])
def decline_decode():
    """Decode a decline code"""
    if not DECLINE_DECODER:
        return jsonify({"error": "decline_decoder not available"}), 503

    data = request.json or {}
    code = data.get("code")
    psp = data.get("psp", "stripe")

    if not code:
        return jsonify({"error": "Missing 'code' field"}), 400

    decoded = decode_decline(code, psp=psp)
    return jsonify(decoded)


@app.route("/api/v1/3ds/bypass", methods=["POST"])
def bypass_plan():
    """Generate 3DS bypass plan"""
    if not BYPASS_ENGINE:
        return jsonify({"error": "3ds_bypass engine not available"}), 503

    data = request.json or {}
    target = data.get("target", "unknown")
    psp = data.get("psp", "stripe")
    country = data.get("country", "US")
    amount = data.get("amount", 200)

    plan = get_3ds_bypass_plan(target, psp=psp, card_country=country, amount=amount)
    return jsonify(plan)


# ═══════════════════════════════════════════════════════════════════════════════
# KEY MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/keys", methods=["GET"])
def list_keys():
    """List configured keys (masked)"""
    masked = {}
    for provider, key_list in engine.merchant_keys.items():
        masked[provider] = []
        for k in key_list:
            pk = k.get("public_key", "")
            masked[provider].append({
                "public_key": f"{pk[:8]}...{pk[-4:]}" if len(pk) > 12 else pk,
                "is_live": k.get("is_live", False),
                "added_at": k.get("added_at"),
                "success_count": k.get("success_count", 0),
                "fail_count": k.get("fail_count", 0),
            })
    return jsonify(masked)


@app.route("/api/v1/keys", methods=["POST"])
def add_key():
    """Add a merchant key"""
    data = request.json or {}
    provider = data.get("provider", "stripe")
    public_key = data.get("public_key")
    secret_key = data.get("secret_key")

    if not public_key or not secret_key:
        return jsonify({"error": "Missing public_key or secret_key"}), 400

    if provider not in engine.merchant_keys:
        engine.merchant_keys[provider] = []

    engine.merchant_keys[provider].append({
        "public_key": public_key,
        "secret_key": secret_key,
        "merchant_id": data.get("merchant_id"),
        "is_live": data.get("is_live", False),
        "added_at": datetime.now().isoformat(),
        "success_count": 0,
        "fail_count": 0,
    })

    _save_keys(engine.merchant_keys)
    return jsonify({"ok": True, "message": f"{provider} key added"})


@app.route("/api/v1/keys/<provider>/<int:index>", methods=["DELETE"])
def remove_key(provider: str, index: int):
    """Remove a merchant key"""
    if provider in engine.merchant_keys and index < len(engine.merchant_keys[provider]):
        engine.merchant_keys[provider].pop(index)
        _save_keys(engine.merchant_keys)
        return jsonify({"ok": True, "message": "Key removed"})
    return jsonify({"error": "Key not found"}), 404


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATIONAL INTELLIGENCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/cooling/<card_hash>", methods=["GET"])
def cooling_status(card_hash: str):
    """Get card cooling status"""
    if not engine.cooling:
        return jsonify({"error": "Cooling system not available"}), 503

    # Look up card in cooling system
    heat = engine.cooling.card_heat.get(card_hash, 0)
    usage_count = len(engine.cooling.card_usage.get(card_hash, []))
    return jsonify({
        "card_hash": card_hash,
        "heat_level": heat,
        "usage_count": usage_count,
    })


@app.route("/api/v1/velocity", methods=["GET"])
def velocity_stats():
    """Get issuer velocity stats"""
    if not engine.velocity:
        return jsonify({"error": "Velocity tracker not available"}), 503
    return jsonify(engine.velocity.get_issuer_stats())


@app.route("/api/v1/intelligence", methods=["GET"])
def intelligence():
    """Get cross-PSP correlation data"""
    if not engine.correlator:
        return jsonify({"error": "PSP correlator not available"}), 503
    return jsonify({
        "tracked_cards": len(engine.correlator.card_flags),
        "fraud_networks": engine.correlator.PSP_FRAUD_NETWORKS,
    })


@app.route("/api/v1/history", methods=["GET"])
def history():
    """Get validation history"""
    limit = request.args.get("limit", 100, type=int)
    status_filter = request.args.get("status")

    entries = engine.history[-limit:]
    if status_filter:
        entries = [e for e in entries if e.get("status") == status_filter.upper()]

    return jsonify({
        "entries": entries,
        "total": len(engine.history),
        "returned": len(entries),
    })


@app.route("/api/v1/analytics", methods=["GET"])
def analytics():
    """Get decline analytics"""
    total = len(engine.history)
    if total == 0:
        return jsonify({"message": "No validation history"})

    live = sum(1 for h in engine.history if h.get("status") == "LIVE")
    dead = sum(1 for h in engine.history if h.get("status") == "DEAD")
    unknown = sum(1 for h in engine.history if h.get("status") == "UNKNOWN")
    risky = sum(1 for h in engine.history if h.get("status") == "RISKY")

    decline_reasons = {}
    banks = {}
    countries = {}
    for h in engine.history:
        reason = h.get("decline_reason") or h.get("decline_category")
        if reason:
            decline_reasons[reason] = decline_reasons.get(reason, 0) + 1
        bank = h.get("bank")
        if bank and bank != "Unknown":
            if bank not in banks:
                banks[bank] = {"total": 0, "live": 0, "dead": 0}
            banks[bank]["total"] += 1
            if h.get("status") == "LIVE":
                banks[bank]["live"] += 1
            elif h.get("status") == "DEAD":
                banks[bank]["dead"] += 1
        country = h.get("country")
        if country and country != "Unknown":
            countries[country] = countries.get(country, 0) + 1

    return jsonify({
        "total": total,
        "live": live, "dead": dead, "unknown": unknown, "risky": risky,
        "live_rate": f"{live/total*100:.1f}%",
        "top_decline_reasons": dict(sorted(decline_reasons.items(), key=lambda x: -x[1])[:10]),
        "bank_breakdown": banks,
        "country_breakdown": countries,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# REFERENCE ENDPOINTS (OSINT, quality guides)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/reference/osint", methods=["GET"])
def osint_checklist():
    if not CERBERUS_CORE:
        return jsonify({"error": "Core not loaded"}), 503
    return jsonify(get_osint_checklist())


@app.route("/api/v1/reference/quality", methods=["GET"])
def quality_guide():
    if not CERBERUS_CORE:
        return jsonify({"error": "Core not loaded"}), 503
    return jsonify(get_card_quality_guide())


@app.route("/api/v1/reference/enrollment", methods=["GET"])
def enrollment_guide():
    if not CERBERUS_CORE:
        return jsonify({"error": "Core not loaded"}), 503
    return jsonify(get_bank_enrollment_guide())


# ═══════════════════════════════════════════════════════════════════════════════
# V2 HYPERSWITCH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v2/validate", methods=["POST"])
def v2_validate():
    """Validate card via Hyperswitch (50+ connectors)"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured", "fallback": "/api/v1/validate"}), 503

    data = request.json or {}
    card_data = data.get("card") or data.get("card_data")
    if not card_data:
        return jsonify({"error": "Missing 'card' field"}), 400

    parts = card_data.split("|")
    if len(parts) < 4:
        return jsonify({"error": "Format: PAN|MM|YY|CVV"}), 400

    client = get_hyperswitch_client()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        payment = loop.run_until_complete(client.validate_card(
            card_number=parts[0].strip(),
            card_exp_month=parts[1].strip(),
            card_exp_year=parts[2].strip(),
            card_cvc=parts[3].strip(),
        ))
        result = {
            "payment_id": payment.payment_id,
            "status": payment.status.value,
            "connector": payment.connector,
            "error_code": payment.error_code,
            "error_message": payment.error_message,
            "authentication_type": payment.authentication_type,
            "validated": payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.REQUIRES_CAPTURE),
        }
        engine.record_result({
            "status": "LIVE" if result["validated"] else "DEAD",
            "message": f"Hyperswitch ({payment.connector}): {payment.status.value}",
            "card": f"{parts[0][:6]}******{parts[0][-4:]}",
            "gateways_tried": ["hyperswitch"],
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/v2/connectors", methods=["GET"])
def v2_connectors():
    """List active Hyperswitch connectors + health"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    router = get_hyperswitch_router()
    connectors = router.get_optimal_connectors()
    return jsonify({
        "connectors": connectors,
        "routing_algorithm": "auth_rate_mab",
        "hyperswitch_url": get_hyperswitch_client().base_url,
    })


@app.route("/api/v2/routing", methods=["GET"])
def v2_routing_get():
    """Get current routing configuration"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    client = get_hyperswitch_client()
    loop = asyncio.new_event_loop()
    try:
        config = loop.run_until_complete(client.get_routing_config())
        return jsonify({
            "algorithm": config.algorithm.value,
            "connectors": config.connectors,
            "rules": config.rules,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/v2/vault/cards", methods=["GET"])
def v2_vault_list():
    """List vaulted cards"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    vault = get_hyperswitch_vault()
    loop = asyncio.new_event_loop()
    try:
        cards = loop.run_until_complete(vault.list_cards())
        return jsonify({
            "cards": [
                {
                    "id": c.payment_method_id,
                    "last4": c.card_last4,
                    "network": c.card_network,
                    "exp": f"{c.card_exp_month}/{c.card_exp_year}",
                    "nickname": c.nickname,
                }
                for c in cards
            ],
            "total": len(cards),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/v2/vault/store", methods=["POST"])
def v2_vault_store():
    """Store a card in the vault"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    data = request.json or {}
    card_data = data.get("card") or data.get("card_data")
    if not card_data:
        return jsonify({"error": "Missing 'card' field"}), 400

    parts = card_data.split("|")
    if len(parts) < 3:
        return jsonify({"error": "Format: PAN|MM|YY[|CVV]"}), 400

    vault = get_hyperswitch_vault()
    loop = asyncio.new_event_loop()
    try:
        vaulted = loop.run_until_complete(vault.store_card(
            card_number=parts[0].strip(),
            card_exp_month=parts[1].strip(),
            card_exp_year=parts[2].strip(),
            card_cvc=parts[3].strip() if len(parts) > 3 else None,
            nickname=data.get("nickname"),
        ))
        return jsonify({
            "id": vaulted.payment_method_id,
            "last4": vaulted.card_last4,
            "network": vaulted.card_network,
            "nickname": vaulted.nickname,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/v2/analytics/summary", methods=["GET"])
def v2_analytics_summary():
    """Analytics dashboard summary"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    analytics = get_hyperswitch_analytics()
    loop = asyncio.new_event_loop()
    try:
        summary = loop.run_until_complete(analytics.get_summary())
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/v2/analytics/connector/<connector_name>", methods=["GET"])
def v2_analytics_connector(connector_name: str):
    """Per-connector analytics"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    analytics = get_hyperswitch_analytics()
    loop = asyncio.new_event_loop()
    try:
        data = loop.run_until_complete(analytics.get_connector_analytics(connector=connector_name))
        if data:
            a = data[0]
            return jsonify({
                "connector": a.connector_name,
                "transactions": a.total_transactions,
                "successful": a.successful,
                "failed": a.failed,
                "auth_rate": a.auth_rate,
                "total_amount": a.total_amount,
                "top_decline_codes": a.top_decline_codes,
            })
        return jsonify({"error": "Connector not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/v2/retry", methods=["POST"])
def v2_retry():
    """Trigger smart retry for failed payment"""
    if not HYPERSWITCH_OK:
        return jsonify({"error": "Hyperswitch not configured"}), 503

    data = request.json or {}
    card_data = data.get("card")
    payment_id = data.get("payment_id")

    if not card_data:
        return jsonify({"error": "Missing 'card' field"}), 400

    parts = card_data.split("|")
    if len(parts) < 4:
        return jsonify({"error": "Format: PAN|MM|YY|CVV"}), 400

    retry_engine = get_hyperswitch_retry()
    client = get_hyperswitch_client()
    loop = asyncio.new_event_loop()
    try:
        # Get failed payment if ID provided
        if payment_id:
            failed = loop.run_until_complete(client.get_payment(payment_id))
        else:
            # Create a mock failed payment for retry
            from cerberus_hyperswitch import HyperswitchPayment
            failed = HyperswitchPayment(
                payment_id="manual_retry",
                status=PaymentStatus.FAILED,
                amount=data.get("amount", 0),
                currency=data.get("currency", "USD"),
                error_code=data.get("error_code", "generic_decline"),
                authentication_type="no_three_ds",
            )

        results = loop.run_until_complete(retry_engine.smart_retry(
            failed_payment=failed,
            card_number=parts[0].strip(),
            card_exp_month=parts[1].strip(),
            card_exp_year=parts[2].strip(),
            card_cvc=parts[3].strip(),
            max_attempts=data.get("max_attempts", 3),
        ))

        return jsonify({
            "retry_results": [
                {
                    "attempt": r.attempt_number,
                    "connector": r.connector_used,
                    "status": r.status.value,
                    "error_code": r.error_code,
                    "delay_ms": r.delay_applied_ms,
                }
                for r in results
            ],
            "success": any(r.status in (PaymentStatus.SUCCEEDED, PaymentStatus.REQUIRES_CAPTURE) for r in results),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info(f"Starting Cerberus Bridge API V2 on {BRIDGE_HOST}:{BRIDGE_PORT}")
    logger.info(f"Core: {CERBERUS_CORE} | Enhanced: {CERBERUS_ENHANCED} | Hyperswitch: {HYPERSWITCH_OK} | AI: {AI_ENGINE}")
    app.run(host=BRIDGE_HOST, port=BRIDGE_PORT, debug=False)
