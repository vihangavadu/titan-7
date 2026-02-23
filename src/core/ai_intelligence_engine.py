"""
TITAN V8.1 SINGULARITY — AI Intelligence Engine
Unified Ollama-powered intelligence for all operational modules.

Hooks local Ollama (qwen2.5:7b + mistral:7b) into:
1. BIN Deep Analysis     — enrich unknown BINs with AI-inferred bank/risk data
2. Pre-Flight Advisor    — synthesize all checks into strategic go/no-go
3. Target Recon          — real-time merchant antifraud analysis for unknown targets
4. 3DS Bypass Advisor    — optimal checkout flow/timing/amount strategy
5. Profile Forensic AI   — detect profile inconsistencies before browser launch
6. Behavioral Tuning     — adapt Ghost Motor params per target antifraud engine

All inference runs LOCALLY via Ollama — zero external API calls.
"""

import json
import time
import logging
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum

__version__ = "8.0.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-AI")


# ═══════════════════════════════════════════════════════════════════════════════
# V8.3 FIX #1: Global model lock — prevents concurrent OOM-inducing model swaps
# ═══════════════════════════════════════════════════════════════════════════════

_MODEL_LOCK = threading.Lock()
_CURRENT_MODEL: Optional[str] = None

# V8.3 FIX #4: Task-specific timeouts (seconds) — prevents 60s cascade failures
_TASK_TIMEOUTS: Dict[str, int] = {
    "bin_analysis":          45,
    "bin_generation":        45,
    "site_discovery":        45,
    "target_recon":          45,
    "behavioral_tuning":     30,
    "default":               60,
    "profile_audit":         90,
    "3ds_strategy":         120,
    "decline_autopsy":      180,
    "operation_planning":   150,
    "card_rotation":        120,
    "velocity_schedule":    120,
    "session_rhythm":        90,
    "defense_tracking":      90,
    "cross_session":        120,
    "fingerprint_coherence": 60,
    "identity_graph":        60,
    "environment_coherence": 45,
    "navigation_path":       30,
    "form_fill_cadence":     30,
    "avs_prevalidation":     30,
}


def _get_task_timeout(task_type: str) -> int:
    """Return the appropriate timeout for a given task type."""
    return _TASK_TIMEOUTS.get(task_type, _TASK_TIMEOUTS["default"])


def _query_ollama_with_retry(prompt: str, task_type: str = "default",
                              temperature: float = 0.3, max_tokens: int = 4096,
                              max_retries: int = 2) -> Optional[str]:
    """Query Ollama with task-specific timeout and exponential backoff retry."""
    timeout = _get_task_timeout(task_type)
    for attempt in range(max_retries + 1):
        try:
            result = _query_ollama(prompt, task_type=task_type,
                                   temperature=temperature,
                                   max_tokens=max_tokens, timeout=timeout)
            if result is not None:
                return result
        except Exception as e:
            logger.error(f"Ollama query attempt {attempt + 1} failed [{task_type}]: {e}",
                         exc_info=True)
        if attempt < max_retries:
            wait = 2 ** attempt
            logger.debug(f"Retrying [{task_type}] in {wait}s (attempt {attempt + 2}/{max_retries + 1})")
            time.sleep(wait)
    return None


def _query_ollama_json_with_retry(prompt: str, task_type: str = "default",
                                   temperature: float = 0.2, max_tokens: int = 4096,
                                   max_retries: int = 2) -> Optional[Any]:
    """Query Ollama expecting JSON, with task-specific timeout and retry."""
    timeout = _get_task_timeout(task_type)
    for attempt in range(max_retries + 1):
        try:
            result = _query_ollama_json(prompt, task_type=task_type,
                                        temperature=temperature,
                                        max_tokens=max_tokens, timeout=timeout)
            if result is not None:
                return result
        except Exception as e:
            logger.error(f"Ollama JSON query attempt {attempt + 1} failed [{task_type}]: {e}",
                         exc_info=True)
        if attempt < max_retries:
            wait = 2 ** attempt
            logger.debug(f"Retrying JSON [{task_type}] in {wait}s (attempt {attempt + 2}/{max_retries + 1})")
            time.sleep(wait)
    return None


def _check_ollama_memory_headroom(model_name: str) -> bool:
    """V8.3 FIX #1: Verify RAM headroom before loading a model. Returns True if safe."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=3) as resp:
            data = json.loads(resp.read())
        loaded = data.get("models", [])
        loaded_names = [m.get("name", "") for m in loaded]
        if model_name in loaded_names:
            return True
        total_vram = sum(m.get("size", 0) for m in loaded)
        if total_vram > 10 * 1024 ** 3:
            logger.warning(f"[MODEL_LOCK] >10GB already loaded, unloading before swap to {model_name}")
            _unload_inactive_ollama_models(loaded_names, keep=model_name)
        return True
    except Exception as e:
        logger.debug(f"Ollama /api/ps check failed: {e}")
        return True


def _unload_inactive_ollama_models(loaded_names: List[str], keep: str) -> None:
    """Force-unload all models except the one we need."""
    import urllib.request
    for name in loaded_names:
        if name == keep:
            continue
        try:
            payload = json.dumps({"model": name, "keep_alive": 0}).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
            logger.info(f"[MODEL_LOCK] Unloaded inactive model: {name}")
        except Exception as e:
            logger.debug(f"Failed to unload {name}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA BRIDGE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def _query_ollama(prompt: str, task_type: str = "default",
                  temperature: float = 0.3, max_tokens: int = 4096,
                  timeout: int = 60) -> Optional[str]:
    """Query Ollama via the bridge with fallback."""
    try:
        from ollama_bridge import query_llm
        return query_llm(prompt, task_type=task_type, temperature=temperature,
                         max_tokens=max_tokens, timeout=timeout)
    except ImportError:
        return _query_ollama_direct(prompt, temperature, max_tokens, timeout)


def _query_ollama_json(prompt: str, task_type: str = "default",
                       temperature: float = 0.2, max_tokens: int = 4096,
                       timeout: int = 60) -> Optional[Any]:
    """Query Ollama expecting JSON response."""
    try:
        from ollama_bridge import query_llm_json
        return query_llm_json(prompt, task_type=task_type,
                              temperature=temperature, max_tokens=max_tokens,
                              timeout=timeout)
    except ImportError:
        raw = _query_ollama_direct(prompt, temperature, max_tokens, timeout)
        if raw:
            return _extract_json(raw)
        return None


def _load_default_model_name() -> str:
    """V8.3 FIX #10: Load default model from llm_config.json, never hardcoded."""
    try:
        cfg_path = Path(__file__).parent.parent / "config" / "llm_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            routing = cfg.get("task_routing", {})
            default_route = routing.get("default", [{}])
            if default_route and isinstance(default_route, list):
                return default_route[0].get("model", "mistral:7b")
        return "mistral:7b"
    except Exception:
        return "mistral:7b"


def _query_ollama_direct(prompt: str, temperature: float = 0.3,
                         max_tokens: int = 4096, timeout: int = 60) -> Optional[str]:
    """Direct Ollama HTTP API call as fallback."""
    import urllib.request
    model_name = _load_default_model_name()
    try:
        payload = json.dumps({
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")
    except Exception as e:
        logger.warning(f"Ollama direct query failed: {e}")
        return None


def _extract_json(text: str) -> Optional[Any]:
    """V8.3 FIX #8: Hardened JSON extraction — strips all markdown variants, finds outermost brackets."""
    import re
    if not text:
        return None
    text = text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    text = re.sub(r'^```[a-zA-Z]*\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find outermost JSON object or array using regex to handle nested structures
    for pattern in (r'(\{[\s\S]*\})', r'(\[[\s\S]*\])'):
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    logger.debug(f"_extract_json: failed to parse response (len={len(text)})")
    return None


def _is_ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        from ollama_bridge import is_ollama_available
        return is_ollama_available()
    except ImportError:
        import urllib.request
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _safe_risk_level(value: str) -> RiskLevel:
    """V7.5 FIX: Safely parse RiskLevel from LLM output."""
    try:
        return RiskLevel(value)
    except ValueError:
        return RiskLevel.MEDIUM


@dataclass
class AIBINAnalysis:
    """AI-enriched BIN analysis result."""
    bin_number: str
    bank_name: str
    country: str
    card_type: str
    card_level: str
    network: str
    risk_level: RiskLevel
    ai_score: float                      # 0-100
    success_prediction: float            # 0.0-1.0
    best_targets: List[str]
    avoid_targets: List[str]
    optimal_amount_range: Tuple[float, float]
    timing_advice: str
    risk_factors: List[str]
    strategic_notes: str
    ai_powered: bool = True


@dataclass
class AIPreFlightAdvice:
    """AI-synthesized pre-flight advisory."""
    go_decision: bool
    confidence: float                    # 0.0-1.0
    risk_level: RiskLevel
    summary: str
    critical_issues: List[str]
    warnings: List[str]
    strategic_advice: List[str]
    optimal_timing: str
    abort_triggers: List[str]
    ai_powered: bool = True


@dataclass
class AITargetRecon:
    """AI-generated target intelligence."""
    domain: str
    name: str
    fraud_engine_guess: str
    payment_processor_guess: str
    estimated_friction: str
    three_ds_probability: float
    optimal_card_types: List[str]
    optimal_countries: List[str]
    warmup_strategy: List[str]
    checkout_tips: List[str]
    risk_factors: List[str]
    ai_powered: bool = True


@dataclass
class AI3DSStrategy:
    """AI-generated 3DS bypass strategy."""
    recommended_approach: str
    success_probability: float
    timing_window: str
    amount_strategy: str
    card_type_preference: str
    checkout_flow: List[str]
    fallback_plan: str
    risk_factors: List[str]
    ai_powered: bool = True


@dataclass
class AIProfileAudit:
    """AI forensic profile validation result."""
    clean: bool
    score: float                         # 0-100
    inconsistencies: List[str]
    leak_vectors: List[str]
    recommendations: List[str]
    ai_powered: bool = True


@dataclass
class AIBehavioralTuning:
    """AI-tuned Ghost Motor parameters per target."""
    target: str
    mouse_speed_range: Tuple[float, float]
    click_delay_ms: Tuple[int, int]
    scroll_behavior: str
    typing_wpm_range: Tuple[int, int]
    typing_error_rate: float
    idle_pattern: str
    form_fill_strategy: str
    page_dwell_seconds: Tuple[int, int]
    ai_powered: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AI BIN DEEP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

_bin_cache: Dict[str, AIBINAnalysis] = {}

BIN_ANALYSIS_PROMPT = """You are a payment card security analyst. Analyze this credit card BIN for operational risk.

BIN: {bin_number}
Known info: {known_info}
Target merchant: {target}
Transaction amount: ${amount}

Respond with a JSON object:
{{
    "bank_name": "issuing bank name",
    "country": "2-letter country code",
    "card_type": "credit/debit/prepaid",
    "card_level": "classic/gold/platinum/signature/world/infinite",
    "network": "visa/mastercard/amex/discover",
    "risk_level": "low/medium/high/critical",
    "ai_score": 0-100,
    "success_prediction": 0.0-1.0,
    "best_targets": ["domain1.com", "domain2.com"],
    "avoid_targets": ["domain3.com"],
    "optimal_amount_min": 10,
    "optimal_amount_max": 500,
    "timing_advice": "best time of day/week for this BIN",
    "risk_factors": ["factor1", "factor2"],
    "strategic_notes": "2-3 sentence operational advice"
}}

Be realistic and specific. Consider: 3DS enrollment, AVS strictness, velocity limits, cross-border policies."""


def analyze_bin(bin_number: str, target: str = "", amount: float = 0,
                known_info: Dict = None) -> AIBINAnalysis:
    """
    AI-powered BIN deep analysis. Enriches static BIN data with
    AI-inferred intelligence about risk, timing, and strategy.
    """
    bin6 = bin_number[:6]

    # Check cache
    cache_key = f"{bin6}_{target}_{int(amount)}"
    if cache_key in _bin_cache:
        return _bin_cache[cache_key]

    # Get static BIN info as base context
    static_info = _get_static_bin_info(bin6)
    known_str = json.dumps(known_info or static_info, indent=2)

    # Inject decline history for per-BIN learning
    decline_ctx = get_enriched_bin_context(bin6)

    # V7.6: Inject vector memory context for richer analysis
    vector_ctx = _get_vector_memory_context(bin6, target, amount)

    prompt = BIN_ANALYSIS_PROMPT.format(
        bin_number=bin6, known_info=known_str,
        target=target or "unknown", amount=amount or "unknown"
    ) + decline_ctx + vector_ctx

    result = _query_ollama_json_with_retry(prompt, task_type="bin_generation",
                                           temperature=0.2)

    if result and isinstance(result, dict):
        analysis = AIBINAnalysis(
            bin_number=bin6,
            bank_name=result.get("bank_name", static_info.get("bank", "Unknown")),
            country=result.get("country", static_info.get("country", "US")),
            card_type=result.get("card_type", "credit"),
            card_level=result.get("card_level", "classic"),
            network=result.get("network", static_info.get("network", "visa")),
            risk_level=_safe_risk_level(result.get("risk_level", "medium")),
            ai_score=float(result.get("ai_score", 50)),
            success_prediction=float(result.get("success_prediction", 0.5)),
            best_targets=result.get("best_targets", []),
            avoid_targets=result.get("avoid_targets", []),
            optimal_amount_range=(
                float(result.get("optimal_amount_min", 10)),
                float(result.get("optimal_amount_max", 500))
            ),
            timing_advice=result.get("timing_advice", "Business hours US Eastern"),
            risk_factors=result.get("risk_factors", []),
            strategic_notes=result.get("strategic_notes", ""),
            ai_powered=True,
        )
        _bin_cache[cache_key] = analysis
        logger.info(f"AI BIN analysis: {bin6} → score={analysis.ai_score}, "
                     f"success={analysis.success_prediction:.0%}")

        # V7.6: Store analysis in vector memory for future recall
        _store_bin_to_vector_memory(analysis)

        return analysis

    # Ollama failed to parse response — use static
    fallback = _static_bin_fallback(bin6, target, amount, static_info)
    _bin_cache[cache_key] = fallback
    return fallback


def _get_static_bin_info(bin6: str) -> Dict:
    """Get static BIN info from cerberus_enhanced if available."""
    try:
        from cerberus_enhanced import BINScoringEngine
        engine = BINScoringEngine()
        info = engine.BIN_DATABASE.get(bin6, engine._infer_bin(bin6))
        return info
    except ImportError:
        network = "visa"
        if bin6[:2] in ("51", "52", "53", "54", "55"):
            network = "mastercard"
        elif bin6[:2] in ("34", "37"):
            network = "amex"
        return {"bank": "Unknown", "country": "US", "type": "credit",
                "level": "classic", "network": network}


def _static_bin_fallback(bin6: str, target: str, amount: float,
                         info: Dict) -> AIBINAnalysis:
    """Fallback when Ollama is unavailable."""
    return AIBINAnalysis(
        bin_number=bin6,
        bank_name=info.get("bank", "Unknown"),
        country=info.get("country", "US"),
        card_type=info.get("type", "credit"),
        card_level=info.get("level", "classic"),
        network=info.get("network", "visa"),
        risk_level=RiskLevel.MEDIUM,
        ai_score=50.0,
        success_prediction=0.5,
        best_targets=[target] if target else ["g2a.com", "eneba.com"],
        avoid_targets=[],
        optimal_amount_range=(10, 500),
        timing_advice="Business hours US Eastern",
        risk_factors=["AI analysis unavailable — using static data"],
        strategic_notes="Ollama offline — run with static scoring only.",
        ai_powered=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AI PRE-FLIGHT ADVISOR
# ═══════════════════════════════════════════════════════════════════════════════

PREFLIGHT_PROMPT = """You are an operational security advisor for a payment testing system. Given these pre-flight check results, provide a strategic GO/NO-GO decision.

Pre-flight checks:
{checks_summary}

Card info: {card_info}
Target: {target}
Amount: ${amount}

Respond with JSON:
{{
    "go_decision": true/false,
    "confidence": 0.0-1.0,
    "risk_level": "low/medium/high/critical",
    "summary": "1-2 sentence decision summary",
    "critical_issues": ["issue that must be fixed before proceeding"],
    "warnings": ["non-critical but noteworthy"],
    "strategic_advice": ["specific actionable advice for this operation"],
    "optimal_timing": "when to execute (time of day, day of week)",
    "abort_triggers": ["conditions during operation that should trigger abort"]
}}

Be specific and actionable. Consider: proxy quality, profile age, geo-match, target antifraud engine, card quality."""


def advise_preflight(checks: List[Dict], card_info: Dict = None,
                     target: str = "", amount: float = 0) -> AIPreFlightAdvice:
    """
    AI-powered pre-flight advisor. Takes raw check results and
    synthesizes a strategic go/no-go decision with advice.
    """
    checks_str = "\n".join(
        f"- {c.get('name', '?')}: {c.get('status', '?')} — {c.get('message', '')}"
        for c in checks
    )

    prompt = PREFLIGHT_PROMPT.format(
        checks_summary=checks_str,
        card_info=json.dumps(card_info or {}, indent=2),
        target=target or "unknown",
        amount=amount or "unknown"
    )

    result = _query_ollama_json_with_retry(prompt, task_type="default",
                                           temperature=0.2)

    if result and isinstance(result, dict):
        advice = AIPreFlightAdvice(
            go_decision=result.get("go_decision", False),
            confidence=float(result.get("confidence", 0.5)),
            risk_level=_safe_risk_level(result.get("risk_level", "medium")),
            summary=result.get("summary", "Analysis complete"),
            critical_issues=result.get("critical_issues", []),
            warnings=result.get("warnings", []),
            strategic_advice=result.get("strategic_advice", []),
            optimal_timing=result.get("optimal_timing", "Business hours"),
            abort_triggers=result.get("abort_triggers", []),
            ai_powered=True,
        )
        logger.info(f"AI pre-flight: {'GO' if advice.go_decision else 'NO-GO'} "
                     f"(confidence={advice.confidence:.0%})")
        return advice

    return _static_preflight_fallback(checks)


def _static_preflight_fallback(checks: List[Dict]) -> AIPreFlightAdvice:
    """Fallback when Ollama unavailable."""
    fails = [c for c in checks if c.get("status") == "fail" and c.get("critical", True)]
    warns = [c for c in checks if c.get("status") == "warn"]
    return AIPreFlightAdvice(
        go_decision=len(fails) == 0,
        confidence=0.6 if not fails else 0.2,
        risk_level=RiskLevel.HIGH if fails else RiskLevel.MEDIUM,
        summary=f"{len(fails)} critical failures, {len(warns)} warnings",
        critical_issues=[f["message"] for f in fails],
        warnings=[w["message"] for w in warns],
        strategic_advice=["AI advisor offline — review checks manually"],
        optimal_timing="Business hours US Eastern",
        abort_triggers=["Any 3DS challenge", "Address verification failure"],
        ai_powered=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AI TARGET RECONNAISSANCE
# ═══════════════════════════════════════════════════════════════════════════════

_target_cache: Dict[str, AITargetRecon] = {}

TARGET_RECON_PROMPT = """You are a payment security researcher. Analyze this merchant website for its antifraud defenses and payment processing.

Target: {domain}
Category: {category}

Respond with JSON:
{{
    "name": "merchant name",
    "fraud_engine_guess": "forter/riskified/sift/kount/seon/signifyd/none/unknown",
    "payment_processor_guess": "stripe/adyen/braintree/authorize_net/worldpay/checkout_com/shopify_payments/unknown",
    "estimated_friction": "low/medium/high",
    "three_ds_probability": 0.0-1.0,
    "optimal_card_types": ["credit", "debit"],
    "optimal_countries": ["US", "CA", "GB"],
    "warmup_strategy": ["step 1", "step 2"],
    "checkout_tips": ["specific tip for this merchant"],
    "risk_factors": ["what to watch for"]
}}

Be realistic. Consider: the merchant's size, industry, typical fraud engine for their category, payment processor patterns."""


def recon_target(domain: str, category: str = "") -> AITargetRecon:
    """
    AI-powered target reconnaissance. Uses static DB as base data,
    then ALWAYS enriches with Ollama for dynamic intelligence.
    """
    domain_clean = domain.lower().replace("www.", "").strip()

    # Get static base data (used as context for Ollama, not returned directly)
    static_base = _get_static_target(domain_clean)

    # Build context-aware prompt with static data if available
    static_context = ""
    if static_base:
        static_context = (f"\nKnown intel: fraud_engine={static_base.fraud_engine_guess}, "
                          f"psp={static_base.payment_processor_guess}, "
                          f"3ds_rate={static_base.three_ds_probability:.0%}, "
                          f"friction={static_base.estimated_friction}")

    prompt = TARGET_RECON_PROMPT.format(
        domain=domain_clean, category=category or "ecommerce"
    ) + static_context + "\nEnrich and expand on the known intel with your analysis."

    result = _query_ollama_json_with_retry(prompt, task_type="site_discovery",
                                           temperature=0.3)

    if result and isinstance(result, dict):
        # Merge: AI result takes priority, static fills gaps
        base = static_base or _static_target_fallback(domain_clean)
        recon = AITargetRecon(
            domain=domain_clean,
            name=result.get("name", base.name),
            fraud_engine_guess=result.get("fraud_engine_guess", base.fraud_engine_guess),
            payment_processor_guess=result.get("payment_processor_guess", base.payment_processor_guess),
            estimated_friction=result.get("estimated_friction", base.estimated_friction),
            three_ds_probability=float(result.get("three_ds_probability", base.three_ds_probability)),
            optimal_card_types=result.get("optimal_card_types", base.optimal_card_types),
            optimal_countries=result.get("optimal_countries", base.optimal_countries),
            warmup_strategy=result.get("warmup_strategy", base.warmup_strategy),
            checkout_tips=result.get("checkout_tips", base.checkout_tips),
            risk_factors=result.get("risk_factors", base.risk_factors),
            ai_powered=True,
        )
        _target_cache[domain_clean] = recon
        logger.info(f"AI target recon: {domain_clean} → "
                     f"engine={recon.fraud_engine_guess}, "
                     f"3DS={recon.three_ds_probability:.0%}")

        # V7.6: Store recon in vector memory
        _store_target_to_vector_memory(recon)

        return recon

    # Ollama failed to respond: return static or fallback
    if static_base:
        return static_base
    return _static_target_fallback(domain_clean)


def _get_static_target(domain: str) -> Optional[AITargetRecon]:
    """Check static target_intelligence database."""
    try:
        from target_intelligence import get_target_intel, TARGETS
        for key, intel in TARGETS.items():
            if domain in intel.domain or intel.domain in domain:
                return AITargetRecon(
                    domain=domain,
                    # V7.5 FIX: Use getattr with defaults for optional attributes
                    name=getattr(intel, 'name', domain),
                    fraud_engine_guess=getattr(intel.fraud_engine, 'value', 'unknown') if hasattr(intel, 'fraud_engine') else 'unknown',
                    payment_processor_guess=getattr(intel.payment_gateway, 'value', 'unknown') if hasattr(intel, 'payment_gateway') else 'unknown',
                    estimated_friction=getattr(intel.friction, 'value', 'medium') if hasattr(intel, 'friction') else 'medium',
                    three_ds_probability=getattr(intel, 'three_ds_rate', 0.3),
                    optimal_card_types=["credit"],
                    optimal_countries=["US", "CA", "GB"],
                    warmup_strategy=getattr(intel, 'warmup_sites', []),
                    checkout_tips=getattr(intel, 'operator_playbook', []),
                    risk_factors=getattr(intel, 'notes', []),
                    ai_powered=False,
                )
    except ImportError:
        pass
    return None


def _static_target_fallback(domain: str) -> AITargetRecon:
    """Fallback for unknown targets when Ollama offline."""
    return AITargetRecon(
        domain=domain, name=domain,
        fraud_engine_guess="unknown",
        payment_processor_guess="unknown",
        estimated_friction="medium",
        three_ds_probability=0.3,
        optimal_card_types=["credit"],
        optimal_countries=["US"],
        warmup_strategy=["Browse 2-3 pages before checkout"],
        checkout_tips=["Use residential proxy matching card country"],
        risk_factors=["Unknown target — AI recon unavailable"],
        ai_powered=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AI 3DS BYPASS STRATEGY
# ═══════════════════════════════════════════════════════════════════════════════

THREEDS_PROMPT = """You are a 3D Secure analysis expert. Given the card and target, recommend the optimal strategy to minimize 3DS challenge probability.

Card BIN: {bin_number}
Card country: {card_country}
Card type: {card_type}
Card level: {card_level}
Target: {target}
Amount: ${amount}
Target's fraud engine: {fraud_engine}
Target's 3DS rate: {three_ds_rate}

Respond with JSON:
{{
    "recommended_approach": "specific strategy name",
    "success_probability": 0.0-1.0,
    "timing_window": "best time to attempt",
    "amount_strategy": "advice on amount optimization",
    "card_type_preference": "credit/debit and why",
    "checkout_flow": ["step 1", "step 2", "step 3"],
    "fallback_plan": "what to do if 3DS triggers",
    "risk_factors": ["factors that increase 3DS risk"]
}}

Consider: PSD2 exemptions (<30 EUR), mobile vs desktop friction, time-of-day patterns, velocity throttling, low-value exemptions, trusted beneficiary status."""


def advise_3ds(bin_number: str, target: str, amount: float,
               card_info: Dict = None, target_info: Dict = None) -> AI3DSStrategy:
    """
    AI-powered 3DS avoidance strategy. Analyzes card+target+amount
    combination and recommends optimal checkout approach.
    """
    card = card_info or {}
    target_data = target_info or {}

    prompt = THREEDS_PROMPT.format(
        bin_number=bin_number[:6],
        card_country=card.get("country", "US"),
        card_type=card.get("type", "credit"),
        card_level=card.get("level", "classic"),
        target=target,
        amount=amount,
        fraud_engine=target_data.get("fraud_engine", "unknown"),
        three_ds_rate=target_data.get("three_ds_rate", "unknown"),
    )

    result = _query_ollama_json_with_retry(prompt, task_type="3ds_strategy",
                                           temperature=0.2)

    if result and isinstance(result, dict):
        strategy = AI3DSStrategy(
            recommended_approach=result.get("recommended_approach", "Standard"),
            success_probability=float(result.get("success_probability", 0.5)),
            timing_window=result.get("timing_window", "Business hours"),
            amount_strategy=result.get("amount_strategy", "Keep under $200"),
            card_type_preference=result.get("card_type_preference", "credit"),
            checkout_flow=result.get("checkout_flow", []),
            fallback_plan=result.get("fallback_plan", "Try different card"),
            risk_factors=result.get("risk_factors", []),
        )
        logger.info(f"AI 3DS strategy: {strategy.recommended_approach} "
                     f"(success={strategy.success_probability:.0%})")
        return strategy

    return _static_3ds_fallback(amount)


def _static_3ds_fallback(amount: float) -> AI3DSStrategy:
    """Fallback 3DS strategy."""
    return AI3DSStrategy(
        recommended_approach="Low-value exemption" if amount <= 30 else "Standard checkout",
        success_probability=0.7 if amount <= 30 else 0.5,
        timing_window="Tuesday-Thursday 10am-3pm EST",
        amount_strategy=f"{'Under 30 EUR/USD for SCA exemption' if amount <= 30 else 'Split into sub-$200 orders if possible'}",
        card_type_preference="credit",
        checkout_flow=["Browse 2-3 pages", "Add to cart", "Wait 30-60s", "Checkout"],
        fallback_plan="Try different card from different issuer",
        risk_factors=["AI advisor offline"],
        ai_powered=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AI PROFILE FORENSIC VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

PROFILE_AUDIT_PROMPT = """You are a browser forensics expert. Analyze this Firefox browser profile metadata for inconsistencies that could reveal it as synthetic.

Profile info:
{profile_info}

Check for:
1. Temporal inconsistencies (timestamps out of order, impossible dates)
2. User-Agent vs OS mismatch (claiming Windows but Linux artifacts present)
3. Cookie domain consistency (cookies from sites not in browsing history)
4. Storage size anomalies (too uniform, too small, too large)
5. Missing expected files for claimed browser version
6. Language/locale mismatches
7. Timezone vs geolocation conflicts

Respond with JSON:
{{
    "clean": true/false,
    "score": 0-100,
    "inconsistencies": ["specific inconsistency found"],
    "leak_vectors": ["what an antifraud system would detect"],
    "recommendations": ["how to fix each issue"]
}}"""


def audit_profile(profile_path: str, metadata: Dict = None) -> AIProfileAudit:
    """
    AI-powered profile forensic validation. Checks for inconsistencies
    that antifraud systems could detect.
    """
    profile_info = metadata or _collect_profile_metadata(profile_path)

    if not _is_ollama_available():
        return _static_profile_fallback(profile_info)

    prompt = PROFILE_AUDIT_PROMPT.format(
        profile_info=json.dumps(profile_info, indent=2, default=str)
    )

    result = _query_ollama_json_with_retry(prompt, task_type="profile_audit",
                                           temperature=0.1)

    if result and isinstance(result, dict):
        audit = AIProfileAudit(
            clean=result.get("clean", False),
            score=float(result.get("score", 50)),
            inconsistencies=result.get("inconsistencies", []),
            leak_vectors=result.get("leak_vectors", []),
            recommendations=result.get("recommendations", []),
        )
        logger.info(f"AI profile audit: score={audit.score}, "
                     f"clean={audit.clean}, issues={len(audit.inconsistencies)}")
        return audit

    return _static_profile_fallback(profile_info)


def _collect_profile_metadata(profile_path: str) -> Dict:
    """Collect basic profile metadata for AI analysis."""
    p = Path(profile_path)
    info = {"path": str(p), "exists": p.exists(), "files": [], "size_mb": 0}
    if p.exists():
        all_files = list(p.rglob("*"))
        info["total_files"] = len(all_files)
        info["size_mb"] = round(sum(f.stat().st_size for f in all_files if f.is_file()) / 1048576, 1)
        # Key files
        for key_file in ["places.sqlite", "cookies.sqlite", "prefs.js",
                         "compatibility.ini", "cert9.db", "key4.db"]:
            fp = p / key_file
            if fp.exists():
                info["files"].append({"name": key_file, "size": fp.stat().st_size})
        # Check compatibility.ini content
        compat = p / "compatibility.ini"
        if compat.exists():
            info["compatibility_ini"] = compat.read_text()[:500]
        # Check prefs.js for leaks
        prefs = p / "prefs.js"
        if prefs.exists():
            content = prefs.read_text()[:2000]
            info["prefs_snippet"] = content
    return info


def _static_profile_fallback(info: Dict) -> AIProfileAudit:
    """Fallback profile audit."""
    issues = []
    if info.get("size_mb", 0) < 100:
        issues.append("Profile under 100MB — may appear too fresh")
    if info.get("total_files", 0) < 500:
        issues.append("Under 500 files — typical aged profile has 1000+")
    return AIProfileAudit(
        clean=len(issues) == 0,
        score=70.0 if not issues else 40.0,
        inconsistencies=issues,
        leak_vectors=["AI audit unavailable — manual review needed"],
        recommendations=["Run full audit when Ollama is available"],
        ai_powered=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. AI BEHAVIORAL TUNING (Ghost Motor)
# ═══════════════════════════════════════════════════════════════════════════════

BEHAVIORAL_PROMPT = """You are a behavioral biometrics expert. Generate optimal mouse/keyboard/scroll parameters for interacting with this specific merchant's antifraud system.

Target: {target}
Fraud engine: {fraud_engine}
User persona: {persona}
Device type: {device_type}

Respond with JSON:
{{
    "mouse_speed_min": 200,
    "mouse_speed_max": 800,
    "click_delay_min_ms": 80,
    "click_delay_max_ms": 250,
    "scroll_behavior": "smooth/stepped/natural",
    "typing_wpm_min": 35,
    "typing_wpm_max": 65,
    "typing_error_rate": 0.02,
    "idle_pattern": "description of natural idle behavior",
    "form_fill_strategy": "how to fill forms naturally",
    "page_dwell_min_s": 8,
    "page_dwell_max_s": 45
}}

Consider: {fraud_engine} specifically analyzes behavioral biometrics. Make the parameters match a real {persona} user on {device_type}. Avoid robotic uniformity."""


def tune_behavior(target: str, fraud_engine: str = "unknown",
                  persona: str = "US adult, casual shopper",
                  device_type: str = "desktop") -> AIBehavioralTuning:
    """
    AI-tuned Ghost Motor parameters for specific target's antifraud engine.
    Generates human-realistic behavioral patterns.
    """
    prompt = BEHAVIORAL_PROMPT.format(
        target=target, fraud_engine=fraud_engine,
        persona=persona, device_type=device_type
    )

    result = _query_ollama_json_with_retry(prompt, task_type="behavioral_tuning",
                                           temperature=0.4)

    if result and isinstance(result, dict):
        tuning = AIBehavioralTuning(
            target=target,
            mouse_speed_range=(
                float(result.get("mouse_speed_min", 200)),
                float(result.get("mouse_speed_max", 800))
            ),
            click_delay_ms=(
                int(result.get("click_delay_min_ms", 80)),
                int(result.get("click_delay_max_ms", 250))
            ),
            scroll_behavior=result.get("scroll_behavior", "natural"),
            typing_wpm_range=(
                int(result.get("typing_wpm_min", 35)),
                int(result.get("typing_wpm_max", 65))
            ),
            typing_error_rate=float(result.get("typing_error_rate", 0.02)),
            idle_pattern=result.get("idle_pattern", "Random 2-8s pauses"),
            form_fill_strategy=result.get("form_fill_strategy", "Tab between fields"),
            page_dwell_seconds=(
                int(result.get("page_dwell_min_s", 8)),
                int(result.get("page_dwell_max_s", 45))
            ),
        )
        logger.info(f"AI behavioral tuning for {target}: "
                     f"typing={tuning.typing_wpm_range}wpm, "
                     f"mouse={tuning.mouse_speed_range}")
        return tuning

    return _default_behavioral_tuning(target)


def _default_behavioral_tuning(target: str) -> AIBehavioralTuning:
    """Default Ghost Motor parameters."""
    return AIBehavioralTuning(
        target=target,
        mouse_speed_range=(200, 800),
        click_delay_ms=(80, 250),
        scroll_behavior="natural",
        typing_wpm_range=(35, 65),
        typing_error_rate=0.02,
        idle_pattern="Random 2-8s pauses between actions",
        form_fill_strategy="Tab between fields with natural delays",
        page_dwell_seconds=(8, 45),
        ai_powered=False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED OPERATION PLANNER — Combines all AI hooks into single call
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIOperationPlan:
    """Complete AI-generated operation plan."""
    bin_analysis: AIBINAnalysis
    target_recon: AITargetRecon
    threeds_strategy: AI3DSStrategy
    behavioral_tuning: AIBehavioralTuning
    overall_score: float
    go_decision: bool
    executive_summary: str
    ai_powered: bool = True


def plan_operation(bin_number: str, target: str, amount: float,
                   card_info: Dict = None) -> AIOperationPlan:
    """
    Full AI operation planning — runs all 4 intelligence hooks and
    synthesizes a complete operational plan.
    """
    t0 = time.time()

    # Run all analyses
    bin_analysis = analyze_bin(bin_number, target, amount, card_info)
    target_recon = recon_target(target)
    threeds = advise_3ds(
        bin_number, target, amount,
        card_info=card_info,
        target_info={
            "fraud_engine": target_recon.fraud_engine_guess,
            "three_ds_rate": target_recon.three_ds_probability,
        }
    )
    behavior = tune_behavior(
        target, fraud_engine=target_recon.fraud_engine_guess
    )

    # Calculate overall score
    score = (bin_analysis.ai_score * 0.4 +
             threeds.success_probability * 100 * 0.3 +
             (1 - target_recon.three_ds_probability) * 100 * 0.3)

    go = score >= 55 and bin_analysis.risk_level != RiskLevel.CRITICAL

    elapsed = time.time() - t0
    all_ai = all([bin_analysis.ai_powered, target_recon.ai_powered,
                  threeds.ai_powered, behavior.ai_powered])

    summary = (
        f"{'GO' if go else 'NO-GO'} | Score: {score:.0f}/100 | "
        f"BIN: {bin_analysis.bank_name} {bin_analysis.card_level} "
        f"({bin_analysis.network}) → {target} | "
        f"3DS: {threeds.success_probability:.0%} bypass | "
        f"Engine: {target_recon.fraud_engine_guess} | "
        f"AI: {'full' if all_ai else 'partial'} | "
        f"{elapsed:.1f}s"
    )

    logger.info(f"AI Operation Plan: {summary}")

    plan = AIOperationPlan(
        bin_analysis=bin_analysis,
        target_recon=target_recon,
        threeds_strategy=threeds,
        behavioral_tuning=behavior,
        overall_score=round(score, 1),
        go_decision=go,
        executive_summary=summary,
        ai_powered=all_ai,
    )

    # V7.6: Store operation plan in vector memory
    _store_operation_to_vector_memory(plan)

    return plan


# ═══════════════════════════════════════════════════════════════════════════════
# 8. POST-DECLINE FEEDBACK LOOP
# ═══════════════════════════════════════════════════════════════════════════════

_decline_history: Dict[str, List[Dict]] = {}  # bin6 -> [{target, code, category, timestamp}]

def record_decline(bin_number: str, target: str, decline_code: str,
                   decline_category: str, amount: float = 0):
    """
    Record a decline event for per-BIN learning.
    This data feeds back into future BIN analysis prompts so the AI
    can learn which BINs fail on which targets and why.
    """
    bin6 = bin_number[:6]
    if bin6 not in _decline_history:
        _decline_history[bin6] = []
    
    _decline_history[bin6].append({
        "target": target,
        "code": decline_code,
        "category": decline_category,
        "amount": amount,
        "timestamp": time.time(),
    })
    
    # Keep only last 50 declines per BIN to avoid memory bloat
    if len(_decline_history[bin6]) > 50:
        _decline_history[bin6] = _decline_history[bin6][-50:]
    
    # Invalidate BIN cache so next analysis includes decline history
    keys_to_remove = [k for k in _bin_cache if k.startswith(bin6)]
    for k in keys_to_remove:
        del _bin_cache[k]
    
    logger.info(f"Decline recorded: BIN {bin6} → {target} [{decline_code}/{decline_category}]")

    # V7.6: Store decline in vector memory for semantic pattern matching
    _store_decline_to_vector_memory(bin6, target, decline_code, decline_category, amount)


def get_bin_decline_pattern(bin_number: str) -> Dict:
    """
    Analyze decline patterns for a BIN. Returns summary of:
    - Total declines, unique targets, most common decline category
    - Per-target breakdown
    - Recommended action based on pattern
    """
    bin6 = bin_number[:6]
    history = _decline_history.get(bin6, [])
    
    if not history:
        return {"bin": bin6, "total_declines": 0, "pattern": "no_data",
                "recommendation": "No decline history — proceed normally"}
    
    from collections import Counter
    import time
    
    categories = Counter(d["category"] for d in history)
    targets = Counter(d["target"] for d in history)
    recent = [d for d in history if time.time() - d["timestamp"] < 3600]  # last hour
    
    # Determine pattern
    top_cat = categories.most_common(1)[0] if categories else ("unknown", 0)
    
    if top_cat[0] in ("lost_stolen", "fraud_block"):
        pattern = "burned"
        recommendation = "🔴 BIN is BURNED — multiple fraud/stolen flags. Discard all cards from this BIN."
    elif top_cat[0] == "velocity_limit" and len(recent) >= 3:
        pattern = "velocity_hot"
        recommendation = f"🟠 BIN is HOT — {len(recent)} declines in last hour. Wait 4-6 hours before retry."
    elif top_cat[0] == "do_not_honor" and top_cat[1] >= 3:
        pattern = "bank_flagged"
        recommendation = "🟠 Bank is flagging this BIN. Try different merchant category or lower amount."
    elif top_cat[0] in ("avs_mismatch", "cvv_mismatch"):
        pattern = "data_quality"
        recommendation = "🟡 Card data quality issue — verify billing address and CVV via OSINT."
    elif top_cat[0] == "insufficient_funds":
        pattern = "drained"
        recommendation = "🟡 Card may be drained. Try lower amount or different card."
    else:
        pattern = "mixed"
        recommendation = f"Mixed decline pattern. Top reason: {top_cat[0]} ({top_cat[1]}x)."
    
    return {
        "bin": bin6,
        "total_declines": len(history),
        "recent_declines": len(recent),
        "pattern": pattern,
        "top_category": top_cat[0],
        "top_category_count": top_cat[1],
        "targets_tried": dict(targets.most_common(5)),
        "categories": dict(categories.most_common()),
        "recommendation": recommendation,
    }


def get_enriched_bin_context(bin_number: str) -> str:
    """
    Build enriched context string for BIN analysis prompts that includes
    decline history. This makes AI analysis more accurate over time.
    """
    pattern = get_bin_decline_pattern(bin_number)
    if pattern["total_declines"] == 0:
        return ""
    
    ctx = f"\nDECLINE HISTORY for BIN {bin_number[:6]}:\n"
    ctx += f"  Total declines: {pattern['total_declines']}\n"
    ctx += f"  Recent (1h): {pattern['recent_declines']}\n"
    ctx += f"  Pattern: {pattern['pattern']}\n"
    ctx += f"  Top decline: {pattern['top_category']} ({pattern['top_category_count']}x)\n"
    ctx += f"  Targets tried: {pattern['targets_tried']}\n"
    ctx += f"  Assessment: {pattern['recommendation']}\n"
    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 VECTOR MEMORY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def _get_vector_memory_context(bin6: str, target: str, amount: float) -> str:
    """Build enriched context from vector memory for LLM prompts."""
    try:
        from titan_vector_memory import get_vector_memory
        mem = get_vector_memory()
        if not mem.is_available:
            return ""
        return mem.build_operation_context(bin6, target, amount)
    except ImportError:
        return ""
    except Exception as e:
        logger.debug(f"Vector memory context failed: {e}")
        return ""


def _store_bin_to_vector_memory(analysis) -> None:
    """Store BIN analysis result into vector memory for future recall."""
    try:
        from titan_vector_memory import get_vector_memory
        mem = get_vector_memory()
        if not mem.is_available:
            return
        mem.store_bin_intel(analysis.bin_number, {
            "bank": analysis.bank_name,
            "country": analysis.country,
            "card_type": analysis.card_type,
            "card_level": analysis.card_level,
            "network": analysis.network,
            "risk_level": analysis.risk_level.value,
            "success_rate": f"{analysis.success_prediction:.0%}",
            "best_targets": analysis.best_targets,
            "notes": analysis.strategic_notes,
        })
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Vector memory BIN store failed: {e}")


def _store_target_to_vector_memory(recon) -> None:
    """Store target recon result into vector memory."""
    try:
        from titan_vector_memory import get_vector_memory
        mem = get_vector_memory()
        if not mem.is_available:
            return
        mem.store_target_intel(recon.domain, {
            "fraud_engine": recon.fraud_engine_guess,
            "payment_processor": recon.payment_processor_guess,
            "friction": recon.estimated_friction,
            "three_ds_rate": recon.three_ds_probability,
            "best_cards": recon.optimal_card_types,
            "notes": "; ".join(recon.checkout_tips[:3]),
        })
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Vector memory target store failed: {e}")


def _store_operation_to_vector_memory(plan) -> None:
    """Store operation plan result into vector memory."""
    try:
        from titan_vector_memory import get_vector_memory
        mem = get_vector_memory()
        if not mem.is_available:
            return
        mem.store_operation({
            "bin": plan.bin_analysis.bin_number,
            "target": plan.target_recon.domain,
            "amount": plan.bin_analysis.optimal_amount_range[0],
            "result": "go" if plan.go_decision else "no_go",
            "reason": plan.executive_summary[:200],
            "fraud_engine": plan.target_recon.fraud_engine_guess,
            "card_type": plan.bin_analysis.card_type,
            "card_level": plan.bin_analysis.card_level,
            "notes": f"Score: {plan.overall_score}/100",
        })
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Vector memory operation store failed: {e}")


def _store_decline_to_vector_memory(bin_number: str, target: str,
                                     decline_code: str, decline_category: str,
                                     amount: float) -> None:
    """Store decline event into vector memory."""
    try:
        from titan_vector_memory import get_vector_memory
        mem = get_vector_memory()
        if not mem.is_available:
            return
        mem.store_decline({
            "bin": bin_number[:6],
            "target": target,
            "code": decline_code,
            "category": decline_category,
            "amount": amount,
        })
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Vector memory decline store failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

def is_ai_available() -> bool:
    """Check if AI intelligence engine is operational."""
    return _is_ollama_available()


def get_ai_status() -> Dict:
    """Get AI engine status for GUI display."""
    available = _is_ollama_available()

    # V7.6: Check enhanced AI capabilities
    vector_available = False
    agent_available = False
    web_intel_available = False
    try:
        from titan_vector_memory import is_vector_memory_available
        vector_available = is_vector_memory_available()
    except ImportError:
        pass
    try:
        from titan_agent_chain import is_agent_available
        agent_available = is_agent_available()
    except ImportError:
        pass
    try:
        from titan_web_intel import is_web_intel_available
        web_intel_available = is_web_intel_available()
    except ImportError:
        pass

    features = []
    if available:
        features.extend([
            "bin_analysis", "preflight_advisor", "target_recon",
            "3ds_strategy", "profile_audit", "behavioral_tuning",
            "operation_planner",
        ])
        # V8.3: Detection vector sanitization tasks
        features.extend([
            "fingerprint_coherence", "identity_graph",
            "session_rhythm", "environment_coherence", "navigation_path",
            "card_rotation", "form_fill_cadence", "velocity_schedule",
            "avs_prevalidation", "defense_tracking", "decline_autopsy",
            "cross_session_learning",
        ])
    if vector_available:
        features.append("vector_memory")
    if agent_available:
        features.append("agentic_reasoning")
    if web_intel_available:
        features.append("web_intelligence")

    return {
        "available": available,
        "provider": "ollama" if available else "none",
        "features": features,
        "feature_count": len(features),
        "enhancements": {
            "vector_memory": vector_available,
            "agentic_chain": agent_available,
            "web_intel": web_intel_available,
            "v83_detection_sanitization": available,
        },
        "version": __version__,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 AI MODEL SELECTOR — Dynamic model selection by task type
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIModelProfile:
    """Profile for an AI model's capabilities."""
    name: str
    provider: str  # ollama, openai, anthropic, vllm
    context_length: int
    speed_tier: str  # fast, medium, slow
    reasoning_score: float  # 0.0-1.0
    specialties: List[str]  # bin_analysis, code, reasoning, etc.
    cost_per_1k_tokens: float


class AIModelSelector:
    """
    V7.6 Dynamic AI Model Selector - Chooses optimal model based on
    task type, latency requirements, and model capabilities.
    """
    
    MODEL_PROFILES: Dict[str, AIModelProfile] = {
        "mistral:7b": AIModelProfile(
            name="mistral:7b", provider="ollama", context_length=8192,
            speed_tier="fast", reasoning_score=0.75,
            specialties=["general", "bin_analysis", "target_recon"],
            cost_per_1k_tokens=0.0
        ),
        "llama3:8b": AIModelProfile(
            name="llama3:8b", provider="ollama", context_length=8192,
            speed_tier="fast", reasoning_score=0.80,
            specialties=["general", "reasoning", "behavioral"],
            cost_per_1k_tokens=0.0
        ),
        "llama3:70b": AIModelProfile(
            name="llama3:70b", provider="ollama", context_length=8192,
            speed_tier="slow", reasoning_score=0.95,
            specialties=["complex_reasoning", "3ds_strategy", "audit"],
            cost_per_1k_tokens=0.0
        ),
        "qwen2.5:72b": AIModelProfile(
            name="qwen2.5:72b", provider="vllm", context_length=32768,
            speed_tier="medium", reasoning_score=0.92,
            specialties=["bin_analysis", "target_recon", "operation_planning"],
            cost_per_1k_tokens=0.0
        ),
        "codellama:13b": AIModelProfile(
            name="codellama:13b", provider="ollama", context_length=16384,
            speed_tier="medium", reasoning_score=0.70,
            specialties=["code", "technical_analysis"],
            cost_per_1k_tokens=0.0
        ),
    }
    
    TASK_REQUIREMENTS: Dict[str, Dict] = {
        "bin_analysis": {"min_reasoning": 0.70, "max_latency": "medium", "preferred_specialty": "bin_analysis"},
        "target_recon": {"min_reasoning": 0.65, "max_latency": "fast", "preferred_specialty": "target_recon"},
        "3ds_strategy": {"min_reasoning": 0.85, "max_latency": "slow", "preferred_specialty": "3ds_strategy"},
        "behavioral_tuning": {"min_reasoning": 0.70, "max_latency": "fast", "preferred_specialty": "behavioral"},
        "profile_audit": {"min_reasoning": 0.80, "max_latency": "medium", "preferred_specialty": "audit"},
        "operation_planning": {"min_reasoning": 0.85, "max_latency": "medium", "preferred_specialty": "operation_planning"},
    }
    
    def __init__(self):
        self._available_models: Dict[str, bool] = {}
        self._model_latencies: Dict[str, float] = {}
        # P1-4 FIX: Don't call _refresh_available_models() here — it runs
        # `ollama list` via subprocess which blocks for 5s if Ollama is down.
        # Instead, defer to first select_model() call with 5-minute cache.
        self._models_refreshed_at: float = 0.0
    
    def _refresh_available_models(self):
        """Check which models are actually available. Cached for 5 min."""
        import time as _t
        now = _t.time()
        if self._models_refreshed_at and (now - self._models_refreshed_at) < 300:
            return  # Use cached result
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        self._available_models[model_name] = True
        except Exception as e:
            logger.debug(f"Ollama model list refresh failed: {e}")
        self._models_refreshed_at = now
    
    def select_model(self, task_type: str, urgency: str = "normal") -> str:
        """
        Select optimal model for task.
        
        Args:
            task_type: One of bin_analysis, target_recon, 3ds_strategy, etc.
            urgency: "critical" (fastest), "normal", "thorough" (best quality)
        
        Returns:
            Model name string
        """
        # P1-4 FIX: Lazy model refresh on first use (not in __init__)
        self._refresh_available_models()
        
        requirements = self.TASK_REQUIREMENTS.get(task_type, {
            "min_reasoning": 0.70, "max_latency": "medium", "preferred_specialty": "general"
        })
        
        # Adjust requirements based on urgency
        if urgency == "critical":
            requirements["max_latency"] = "fast"
        elif urgency == "thorough":
            requirements["min_reasoning"] = max(requirements["min_reasoning"], 0.85)
            requirements["max_latency"] = "slow"
        
        # Score each available model
        best_model = "mistral:7b"  # Default fallback
        best_score = 0.0
        
        for model_name, profile in self.MODEL_PROFILES.items():
            if not self._available_models.get(model_name, False):
                # Check if base model name matches
                base_name = model_name.split(":")[0]
                if not any(base_name in m for m in self._available_models):
                    continue
            
            score = 0.0
            
            # Check reasoning threshold
            if profile.reasoning_score >= requirements["min_reasoning"]:
                score += profile.reasoning_score * 40
            else:
                continue  # Doesn't meet minimum reasoning requirement
            
            # Check latency requirement
            latency_ok = self._latency_meets_requirement(
                profile.speed_tier, requirements["max_latency"]
            )
            if not latency_ok:
                continue
            
            # Bonus for specialty match
            if requirements["preferred_specialty"] in profile.specialties:
                score += 30
            
            # Bonus for "general" specialty (versatile)
            if "general" in profile.specialties:
                score += 10
            
            # Prefer fast models if equally capable
            if profile.speed_tier == "fast":
                score += 15
            elif profile.speed_tier == "medium":
                score += 8
            
            if score > best_score:
                best_score = score
                best_model = model_name
        
        logger.debug(f"Model selection for {task_type}: {best_model} (score={best_score:.1f})")
        return best_model
    
    def _latency_meets_requirement(self, model_tier: str, required_max: str) -> bool:
        """Check if model speed tier meets latency requirement."""
        tier_order = {"fast": 0, "medium": 1, "slow": 2}
        return tier_order.get(model_tier, 2) <= tier_order.get(required_max, 2)
    
    def get_model_stats(self) -> Dict:
        """Get statistics about available models."""
        return {
            "available_models": list(self._available_models.keys()),
            "model_count": len(self._available_models),
            "profiles_defined": len(self.MODEL_PROFILES),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 AI PROMPT OPTIMIZER — Cached prompt templates & optimization
# ═══════════════════════════════════════════════════════════════════════════════

class AIPromptOptimizer:
    """
    V7.6 Prompt Optimizer - Manages optimized prompt templates,
    caches successful prompts, and improves response quality.
    """
    
    # Optimized prompt templates by task type
    PROMPT_TEMPLATES: Dict[str, str] = {
        "bin_analysis": """You are a BIN intelligence analyst. Analyze this card BIN for fraud transaction success probability.

BIN: {bin_number}
Target: {target}
Amount: ${amount}

Known BIN data: {bin_data}
{decline_history}

Respond in EXACTLY this JSON format:
{{
    "bank_name": "string",
    "card_type": "credit|debit|prepaid",
    "card_level": "classic|gold|platinum|signature|infinite",
    "network": "visa|mastercard|amex|discover",
    "success_probability": 0.0-1.0,
    "ai_score": 0-100,
    "risk_factors": ["list", "of", "risks"],
    "recommended_targets": ["target1", "target2"],
    "reasoning": "brief explanation"
}}""",

        "target_recon": """You are a merchant fraud system analyst. Analyze this target's fraud defenses.

Target: {target}
Category: {category}

Respond in EXACTLY this JSON format:
{{
    "fraud_engine": "forter|riskified|seon|stripe_radar|cybersource|internal|unknown",
    "payment_processor": "stripe|adyen|checkout|braintree|paypal|internal",
    "three_ds_probability": 0.0-1.0,
    "avs_strictness": "strict|moderate|relaxed",
    "velocity_limits": "description of limits",
    "bypass_tips": ["tip1", "tip2"],
    "difficulty_score": 0-100
}}""",

        "3ds_strategy": """You are a 3DS bypass specialist. Analyze this transaction for 3DS challenge probability and bypass strategy.

BIN: {bin_number}
Target: {target}
Amount: ${amount}
Device: {device_type}
Card info: {card_info}
Target info: {target_info}

Respond in EXACTLY this JSON format:
{{
    "challenge_probability": 0.0-1.0,
    "bypass_probability": 0.0-1.0,
    "recommended_strategy": "string",
    "amount_threshold": number,
    "timing_recommendation": "string",
    "device_recommendations": ["rec1", "rec2"],
    "reasoning": "brief explanation"
}}""",

        "behavioral_tuning": """You are a behavioral biometrics specialist for Ghost Motor. Configure optimal human simulation parameters.

Target: {target}
Fraud engine: {fraud_engine}

Respond in EXACTLY this JSON format:
{{
    "mouse_speed_min": 200-400,
    "mouse_speed_max": 600-1200,
    "click_delay_min_ms": 60-120,
    "click_delay_max_ms": 200-400,
    "typing_wpm_min": 25-45,
    "typing_wpm_max": 55-85,
    "typing_error_rate": 0.01-0.05,
    "scroll_behavior": "natural|smooth|stepped",
    "idle_pattern": "description",
    "page_dwell_min_s": 5-15,
    "page_dwell_max_s": 30-60
}}""",
    }
    
    # Cache of successful prompts (prompt_hash -> response)
    _prompt_cache: Dict[str, Dict] = {}
    _cache_hits: int = 0
    _cache_misses: int = 0
    
    @classmethod
    def get_optimized_prompt(cls, task_type: str, **kwargs) -> str:
        """
        Get optimized prompt for task type with variable substitution.
        """
        template = cls.PROMPT_TEMPLATES.get(task_type)
        if not template:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Fill in template variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing prompt variable: {e}")
            # Fill missing with placeholder
            for key in ["bin_number", "target", "amount", "category", "device_type",
                       "card_info", "target_info", "bin_data", "decline_history",
                       "fraud_engine"]:
                if key not in kwargs:
                    kwargs[key] = "unknown"
            return template.format(**kwargs)
    
    @classmethod
    def cache_response(cls, prompt_hash: str, response: Dict):
        """Cache a successful AI response."""
        cls._prompt_cache[prompt_hash] = {
            "response": response,
            "timestamp": time.time(),
            "hits": 0
        }
        # Limit cache size
        if len(cls._prompt_cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                cls._prompt_cache.keys(),
                key=lambda k: cls._prompt_cache[k]["timestamp"]
            )
            for key in sorted_keys[:200]:
                del cls._prompt_cache[key]
    
    @classmethod
    def get_cached_response(cls, prompt_hash: str) -> Optional[Dict]:
        """Get cached response if available and not stale."""
        cached = cls._prompt_cache.get(prompt_hash)
        if cached:
            age_hours = (time.time() - cached["timestamp"]) / 3600
            if age_hours < 24:  # Cache valid for 24 hours
                cached["hits"] += 1
                cls._cache_hits += 1
                return cached["response"]
            else:
                del cls._prompt_cache[prompt_hash]
        cls._cache_misses += 1
        return None
    
    @classmethod
    def get_prompt_hash(cls, task_type: str, **kwargs) -> str:
        """Generate hash for prompt caching."""
        import hashlib
        key_parts = [task_type]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()[:16]
    
    @classmethod
    def get_cache_stats(cls) -> Dict:
        """Get cache statistics."""
        total = cls._cache_hits + cls._cache_misses
        hit_rate = cls._cache_hits / total if total > 0 else 0
        return {
            "cache_size": len(cls._prompt_cache),
            "cache_hits": cls._cache_hits,
            "cache_misses": cls._cache_misses,
            "hit_rate": f"{hit_rate:.1%}",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 AI RESPONSE VALIDATOR — Validate AI responses & detect hallucinations
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIValidationResult:
    """Result of AI response validation."""
    valid: bool
    confidence: float
    issues: List[str]
    corrected_response: Optional[Dict]
    hallucination_score: float  # 0.0 = definitely real, 1.0 = definitely hallucinated


class AIResponseValidator:
    """
    V7.6 Response Validator - Validates AI responses for accuracy,
    detects hallucinations, and ensures actionable output.
    """
    
    # Known valid values for validation
    VALID_NETWORKS = {"visa", "mastercard", "amex", "discover", "jcb", "unionpay"}
    VALID_CARD_TYPES = {"credit", "debit", "prepaid", "charge"}
    VALID_CARD_LEVELS = {"classic", "standard", "gold", "platinum", "signature", "infinite", "black", "world", "world_elite"}
    VALID_FRAUD_ENGINES = {"forter", "riskified", "seon", "stripe_radar", "cybersource", "kount", "maxmind", "accertify", "internal", "unknown"}
    VALID_PSPS = {"stripe", "adyen", "checkout", "braintree", "paypal", "worldpay", "authorize", "square", "internal"}
    
    # Known BIN prefixes for hallucination detection
    KNOWN_BIN_BANKS: Dict[str, str] = {
        "421783": "Bank of America", "414720": "Chase", "426684": "Capital One",
        "453245": "Wells Fargo", "400115": "US Bank", "426428": "Citi",
        "479226": "Navy Federal", "474426": "USAA", "379880": "Amex",
    }
    
    @classmethod
    def validate_bin_analysis(cls, response: Dict, bin_number: str) -> AIValidationResult:
        """Validate BIN analysis response."""
        issues = []
        hallucination_score = 0.0
        corrected = response.copy()
        
        # Check required fields
        required = ["bank_name", "card_type", "network", "success_probability", "ai_score"]
        for field in required:
            if field not in response:
                issues.append(f"Missing required field: {field}")
        
        # Validate network
        network = response.get("network", "").lower()
        if network and network not in cls.VALID_NETWORKS:
            issues.append(f"Invalid network: {network}")
            # Try to correct based on BIN
            if bin_number.startswith("4"):
                corrected["network"] = "visa"
            elif bin_number.startswith("5") or bin_number.startswith("2"):
                corrected["network"] = "mastercard"
            elif bin_number.startswith("3"):
                corrected["network"] = "amex"
        
        # Validate card_type
        card_type = response.get("card_type", "").lower()
        if card_type and card_type not in cls.VALID_CARD_TYPES:
            issues.append(f"Invalid card type: {card_type}")
            corrected["card_type"] = "credit"  # Default assumption
        
        # Validate probability ranges
        for prob_field in ["success_probability"]:
            val = response.get(prob_field, 0)
            if isinstance(val, (int, float)):
                if val < 0 or val > 1:
                    issues.append(f"{prob_field} out of range: {val}")
                    corrected[prob_field] = max(0, min(1, val))
        
        # Validate ai_score range
        ai_score = response.get("ai_score", 50)
        if isinstance(ai_score, (int, float)):
            if ai_score < 0 or ai_score > 100:
                issues.append(f"ai_score out of range: {ai_score}")
                corrected["ai_score"] = max(0, min(100, ai_score))
        
        # Check for bank name hallucination
        bin6 = bin_number[:6]
        if bin6 in cls.KNOWN_BIN_BANKS:
            expected_bank = cls.KNOWN_BIN_BANKS[bin6]
            claimed_bank = response.get("bank_name", "")
            if claimed_bank and expected_bank.lower() not in claimed_bank.lower():
                hallucination_score += 0.5
                issues.append(f"Bank mismatch: expected '{expected_bank}', got '{claimed_bank}'")
                corrected["bank_name"] = expected_bank
        
        valid = len(issues) == 0
        confidence = 1.0 - (len(issues) * 0.15) - hallucination_score
        
        return AIValidationResult(
            valid=valid,
            confidence=max(0, confidence),
            issues=issues,
            corrected_response=corrected if issues else None,
            hallucination_score=hallucination_score
        )
    
    @classmethod
    def validate_target_recon(cls, response: Dict, target: str) -> AIValidationResult:
        """Validate target reconnaissance response."""
        issues = []
        hallucination_score = 0.0
        corrected = response.copy()
        
        # Validate fraud engine
        engine = response.get("fraud_engine", "").lower()
        if engine and engine not in cls.VALID_FRAUD_ENGINES:
            issues.append(f"Unknown fraud engine: {engine}")
            corrected["fraud_engine"] = "unknown"
            hallucination_score += 0.3
        
        # Validate PSP
        psp = response.get("payment_processor", "").lower()
        if psp and psp not in cls.VALID_PSPS:
            issues.append(f"Unknown PSP: {psp}")
            corrected["payment_processor"] = "internal"
        
        # Validate probability ranges
        for prob_field in ["three_ds_probability"]:
            val = response.get(prob_field, 0)
            if isinstance(val, (int, float)):
                if val < 0 or val > 1:
                    issues.append(f"{prob_field} out of range: {val}")
                    corrected[prob_field] = max(0, min(1, val))
        
        valid = len(issues) == 0
        confidence = 1.0 - (len(issues) * 0.2) - hallucination_score
        
        return AIValidationResult(
            valid=valid,
            confidence=max(0, confidence),
            issues=issues,
            corrected_response=corrected if issues else None,
            hallucination_score=hallucination_score
        )
    
    @classmethod
    def validate_json_response(cls, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Validate and parse JSON response from AI.
        Returns: (success, parsed_dict, error_message)
        """
        import json
        import re
        
        # Try to extract JSON from response
        text = response_text.strip()
        
        # Try direct parse
        try:
            return True, json.loads(text), ""
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON block
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return True, json.loads(json_match.group()), ""
            except json.JSONDecodeError as e:
                return False, None, f"JSON parse error: {e}"
        
        # Try to find JSON in code block
        code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_match:
            try:
                return True, json.loads(code_match.group(1)), ""
            except json.JSONDecodeError as e:
                return False, None, f"JSON parse error in code block: {e}"
        
        return False, None, "No valid JSON found in response"


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 UNIFIED AI ORCHESTRATOR — Parallel AI calls with result aggregation
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIOrchestrationResult:
    """Result of orchestrated AI operations."""
    results: Dict[str, Any]
    total_time_ms: float
    parallel_tasks: int
    cache_hits: int
    model_used: str
    validation_confidence: float


class UnifiedAIOrchestrator:
    """
    V7.6 Unified AI Orchestrator - Coordinates multiple AI calls in parallel,
    manages model selection, caching, and result aggregation.
    """
    
    def __init__(self):
        self.model_selector = AIModelSelector()
        self._executor: Optional[Any] = None
    
    def _get_executor(self):
        """Get or create thread pool executor."""
        if self._executor is None:
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=4)
        return self._executor
    
    def orchestrate_operation_intel(self, bin_number: str, target: str,
                                    amount: float, card_info: Dict = None,
                                    urgency: str = "normal") -> AIOrchestrationResult:
        """
        Orchestrate full operation intelligence gathering.
        Runs BIN analysis, target recon, 3DS strategy, and behavioral tuning
        in parallel where possible.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        t0 = time.time()
        cache_hits = 0
        results = {}
        
        # Define tasks
        tasks = {
            "bin_analysis": lambda: self._run_with_cache(
                "bin_analysis", analyze_bin,
                bin_number, target, amount, card_info
            ),
            "target_recon": lambda: self._run_with_cache(
                "target_recon", recon_target, target
            ),
        }
        
        # Run first batch in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(task): name for name, task in tasks.items()}
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result, hit = future.result()
                    results[name] = result
                    if hit:
                        cache_hits += 1
                except Exception as e:
                    logger.error(f"AI task {name} failed: {e}")
                    results[name] = None
        
        # Sequential tasks that depend on previous results
        if results.get("target_recon"):
            fraud_engine = results["target_recon"].fraud_engine_guess
            target_info = {
                "fraud_engine": fraud_engine,
                "three_ds_rate": results["target_recon"].three_ds_probability
            }
            
            # 3DS strategy depends on target info
            results["3ds_strategy"], hit = self._run_with_cache(
                "3ds_strategy", advise_3ds,
                bin_number, target, amount, card_info=card_info, target_info=target_info
            )
            if hit:
                cache_hits += 1
            
            # Behavioral tuning
            results["behavioral"], hit = self._run_with_cache(
                "behavioral", tune_behavior, target, fraud_engine=fraud_engine
            )
            if hit:
                cache_hits += 1
        
        elapsed_ms = (time.time() - t0) * 1000
        
        # Calculate validation confidence
        confidences = []
        for name, result in results.items():
            if result and hasattr(result, 'ai_powered'):
                confidences.append(0.9 if result.ai_powered else 0.6)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return AIOrchestrationResult(
            results=results,
            total_time_ms=round(elapsed_ms, 1),
            parallel_tasks=len(tasks),
            cache_hits=cache_hits,
            model_used=self.model_selector.select_model("operation_planning", urgency),
            validation_confidence=round(avg_confidence, 2)
        )
    
    def _run_with_cache(self, task_type: str, func: callable, *args, **kwargs) -> Tuple[Any, bool]:
        """Run task with prompt caching."""
        # Generate cache key
        cache_key = AIPromptOptimizer.get_prompt_hash(
            task_type, args=str(args), kwargs=str(kwargs)
        )
        
        # Check cache
        cached = AIPromptOptimizer.get_cached_response(cache_key)
        if cached:
            return cached, True
        
        # Run function
        result = func(*args, **kwargs)
        
        # Cache result if successful
        if result:
            AIPromptOptimizer.cache_response(cache_key, result)
        
        return result, False
    
    def get_orchestrator_stats(self) -> Dict:
        """Get orchestrator statistics."""
        return {
            "model_selector": self.model_selector.get_model_stats(),
            "prompt_cache": AIPromptOptimizer.get_cache_stats(),
        }


# Global orchestrator instance
_ai_orchestrator: Optional[UnifiedAIOrchestrator] = None


def get_ai_orchestrator() -> UnifiedAIOrchestrator:
    """Get or create global AI orchestrator."""
    global _ai_orchestrator
    if _ai_orchestrator is None:
        _ai_orchestrator = UnifiedAIOrchestrator()
    return _ai_orchestrator


def orchestrate_intel(bin_number: str, target: str, amount: float,
                      card_info: Dict = None, urgency: str = "normal") -> AIOrchestrationResult:
    """
    Convenience function for orchestrated intelligence gathering.
    
    Usage:
        result = orchestrate_intel("421783", "eneba.com", 150)
        print(result.results["bin_analysis"].ai_score)
        print(result.total_time_ms, "ms")
    """
    return get_ai_orchestrator().orchestrate_operation_intel(
        bin_number, target, amount, card_info, urgency
    )


# ═══════════════════════════════════════════════════════════════════════════════
# V8.3 — NEW AI TASKS: DETECTION VECTOR SANITIZATION (12 tasks)
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Fingerprint Coherence + Identity Graph
# Phase 2: Session Rhythm + Environment Coherence + Navigation Path
# Phase 3: Card Rotation + Form Fill + Velocity + AVS + Defense Tracker + Decline Autopsy
# Phase 4: Cross-Session Learning
# ═══════════════════════════════════════════════════════════════════════════════


# ─── RESULT TYPES (V8.3) ─────────────────────────────────────────────────────

@dataclass
class AIFingerprintCoherence:
    """Result of fingerprint cross-signal coherence validation."""
    coherent: bool
    score: float                         # 0-100
    mismatches: List[str]
    leak_vectors: List[str]
    fixes: List[str]
    ai_powered: bool = True


@dataclass
class AIIdentityGraphResult:
    """Result of identity graph plausibility validation."""
    plausible: bool
    score: float                         # 0-100
    anomalies: List[str]
    graph_links_missing: List[str]
    fixes: List[str]
    ai_powered: bool = True


@dataclass
class AISessionRhythm:
    """AI-generated session timeline with realistic timing."""
    target: str
    warmup_pages: List[Dict]             # [{url, dwell_s, scroll_pct}]
    browse_pages: List[Dict]
    cart_dwell_s: int
    checkout_dwell_s: int
    payment_dwell_s: int
    total_session_s: int
    timing_notes: str
    ai_powered: bool = True


@dataclass
class AIEnvironmentCoherence:
    """Result of network+geo+locale+timezone coherence scoring."""
    coherent: bool
    score: float                         # 0-100
    mismatches: List[str]
    fixes: List[str]
    ai_powered: bool = True


@dataclass
class AINavigationPath:
    """AI-generated realistic navigation path for a target."""
    target: str
    pages: List[Dict]                    # [{url, type, dwell_s, actions}]
    referrer_chain: List[str]
    search_query: str
    total_pages: int
    ai_powered: bool = True


@dataclass
class AICardRotation:
    """AI-optimized card-target-timing recommendation."""
    recommended_card_bin: str
    recommended_target: str
    recommended_amount: float
    recommended_time: str
    cooldown_hours: float
    reasoning: str
    alternatives: List[Dict]
    ai_powered: bool = True


@dataclass
class AIFormFillCadence:
    """AI-tuned form fill timing per persona type."""
    field_delays_ms: Dict[str, Tuple[int, int]]  # field_name -> (min_ms, max_ms)
    tab_vs_click: str
    typo_rate: float
    correction_style: str
    paste_allowed_fields: List[str]
    ai_powered: bool = True


@dataclass
class AIVelocitySchedule:
    """AI-planned velocity schedule for card usage."""
    card_bin: str
    max_attempts_per_hour: int
    max_attempts_per_day: int
    cooldown_after_decline_min: int
    cooldown_after_success_min: int
    optimal_spacing_min: int
    reasoning: str
    ai_powered: bool = True


@dataclass
class AIAVSPreValidation:
    """AI pre-validation of AVS data before submission."""
    avs_likely_pass: bool
    confidence: float
    issues: List[str]
    address_fixes: List[str]
    zip_format_ok: bool
    ai_powered: bool = True


@dataclass
class AIDefenseTracker:
    """AI analysis of target defense changes over time."""
    target: str
    current_engine: str
    previous_engine: str
    changes_detected: List[str]
    new_risks: List[str]
    strategy_adjustments: List[str]
    ai_powered: bool = True


@dataclass
class AIDeclineAutopsy:
    """AI deep analysis of a decline with auto-patch recommendations."""
    decline_code: str
    root_cause: str
    category: str
    is_retriable: bool
    wait_time_min: int
    patches: List[Dict]                  # [{module, change, priority}]
    next_action: str
    ai_powered: bool = True


@dataclass
class AICrossSessionInsight:
    """AI insight from cross-session pattern analysis."""
    pattern_type: str
    insight: str
    affected_bins: List[str]
    affected_targets: List[str]
    recommendation: str
    confidence: float
    ai_powered: bool = True


# ─── TASK 1: FINGERPRINT COHERENCE VALIDATOR ─────────────────────────────────

FINGERPRINT_COHERENCE_PROMPT = """You are a browser fingerprint forensics expert. Analyze this fingerprint configuration for cross-signal inconsistencies that antifraud ML models would detect.

Fingerprint config:
{fp_config}

Check for these cross-signal correlations:
1. User-Agent OS vs WebGL renderer (e.g., claiming Windows but ANGLE says macOS GPU)
2. Hardware concurrency vs GPU tier (16 cores with integrated Intel GPU = suspicious)
3. Screen resolution vs device type (4K on claimed mobile device)
4. Canvas hash stability (should be deterministic per profile)
5. Audio fingerprint vs OS (Windows vs Linux audio stack differences)
6. Font list vs OS/locale (Windows fonts on Linux, missing locale-specific fonts)
7. WebGL vendor/renderer vs User-Agent browser (Chrome ANGLE vs Firefox Mesa)
8. Timezone vs locale vs Accept-Language header
9. Platform string vs navigator.platform vs UA

Respond with JSON:
{{
    "coherent": true/false,
    "score": 0-100,
    "mismatches": ["specific cross-signal mismatch found"],
    "leak_vectors": ["what antifraud would detect and flag"],
    "fixes": ["specific fix for each mismatch"]
}}"""


def validate_fingerprint_coherence(fp_config: Dict) -> AIFingerprintCoherence:
    """
    V8.3: AI-powered fingerprint cross-signal coherence validation.
    Detects mismatches between canvas, WebGL, audio, fonts, screen, UA, OS, GPU
    that antifraud ML models would catch.
    """
    prompt = FINGERPRINT_COHERENCE_PROMPT.format(
        fp_config=json.dumps(fp_config, indent=2, default=str)
    )
    result = _query_ollama_json(prompt, task_type="fingerprint_coherence",
                                temperature=0.1, timeout=60)
    if result and isinstance(result, dict):
        r = AIFingerprintCoherence(
            coherent=result.get("coherent", False),
            score=float(result.get("score", 50)),
            mismatches=result.get("mismatches", []),
            leak_vectors=result.get("leak_vectors", []),
            fixes=result.get("fixes", []),
        )
        logger.info(f"AI fingerprint coherence: score={r.score}, coherent={r.coherent}")
        return r
    return AIFingerprintCoherence(
        coherent=True, score=60, mismatches=[],
        leak_vectors=["AI unavailable — manual review needed"],
        fixes=[], ai_powered=False)


# ─── TASK 2: IDENTITY GRAPH VALIDATOR ────────────────────────────────────────

IDENTITY_GRAPH_PROMPT = """You are an identity verification expert working for ThreatMetrix/Accertify. Analyze this persona for identity graph anomalies that would flag it as synthetic.

Persona:
{persona}

Check for:
1. Name ethnicity vs billing geo (e.g., Japanese name + rural Alabama address)
2. Email domain age and reputation (free vs corporate, disposable domains)
3. Phone area code vs billing state (212 area code but billing in Texas)
4. Shipping vs billing address distance and plausibility
5. Email username vs real name correlation
6. Card BIN country vs billing country
7. Age plausibility (DOB vs email creation patterns)
8. Cross-site identity signals (would this person have social media, Amazon account, etc.)

Respond with JSON:
{{
    "plausible": true/false,
    "score": 0-100,
    "anomalies": ["specific identity graph anomaly"],
    "graph_links_missing": ["expected identity links not present"],
    "fixes": ["how to fix each anomaly"]
}}"""


def validate_identity_graph(persona: Dict) -> AIIdentityGraphResult:
    """
    V8.3: AI-powered identity graph plausibility validation.
    Detects implausible correlations in name/email/phone/address/card
    that identity graph systems would flag.
    """
    prompt = IDENTITY_GRAPH_PROMPT.format(
        persona=json.dumps(persona, indent=2, default=str)
    )
    result = _query_ollama_json(prompt, task_type="identity_graph",
                                temperature=0.2, timeout=60)
    if result and isinstance(result, dict):
        r = AIIdentityGraphResult(
            plausible=result.get("plausible", False),
            score=float(result.get("score", 50)),
            anomalies=result.get("anomalies", []),
            graph_links_missing=result.get("graph_links_missing", []),
            fixes=result.get("fixes", []),
        )
        logger.info(f"AI identity graph: score={r.score}, plausible={r.plausible}")
        return r
    return AIIdentityGraphResult(
        plausible=True, score=60, anomalies=[],
        graph_links_missing=["AI unavailable"], fixes=[], ai_powered=False)


# ─── TASK 3: SESSION RHYTHM PLANNER ──────────────────────────────────────────

SESSION_RHYTHM_PROMPT = """You are a behavioral analytics expert. Generate a realistic session timeline for purchasing on this target site.

Target: {target}
Fraud engine: {fraud_engine}
Product type: {product_type}
Amount: ${amount}

Generate a complete session plan that mimics a real returning customer. Include warmup browsing, product discovery, cart, and checkout with realistic timing.

Respond with JSON:
{{
    "warmup_pages": [{{"url_pattern": "/category/...", "dwell_s": 15, "scroll_pct": 60}}],
    "browse_pages": [{{"url_pattern": "/product/...", "dwell_s": 45, "scroll_pct": 80}}],
    "cart_dwell_s": 30,
    "checkout_dwell_s": 60,
    "payment_dwell_s": 45,
    "total_session_s": 420,
    "timing_notes": "specific timing advice for this target's fraud engine"
}}

Consider: {fraud_engine} analyzes session depth, page dwell distribution, and checkout velocity. Make timing natural."""


def plan_session_rhythm(target: str, fraud_engine: str = "unknown",
                        product_type: str = "digital goods",
                        amount: float = 100) -> AISessionRhythm:
    """
    V8.3: AI-generated session timeline with realistic timing distributions
    tuned per target's antifraud engine.
    """
    prompt = SESSION_RHYTHM_PROMPT.format(
        target=target, fraud_engine=fraud_engine,
        product_type=product_type, amount=amount
    )
    result = _query_ollama_json(prompt, task_type="session_rhythm",
                                temperature=0.4, timeout=45)
    if result and isinstance(result, dict):
        return AISessionRhythm(
            target=target,
            warmup_pages=result.get("warmup_pages", []),
            browse_pages=result.get("browse_pages", []),
            cart_dwell_s=int(result.get("cart_dwell_s", 30)),
            checkout_dwell_s=int(result.get("checkout_dwell_s", 60)),
            payment_dwell_s=int(result.get("payment_dwell_s", 45)),
            total_session_s=int(result.get("total_session_s", 420)),
            timing_notes=result.get("timing_notes", ""),
        )
    return AISessionRhythm(
        target=target, warmup_pages=[], browse_pages=[],
        cart_dwell_s=30, checkout_dwell_s=60, payment_dwell_s=45,
        total_session_s=420, timing_notes="AI unavailable", ai_powered=False)


# ─── TASK 4: ENVIRONMENT COHERENCE SCORER ────────────────────────────────────

ENVIRONMENT_COHERENCE_PROMPT = """You are a network forensics expert. Analyze this environment configuration for coherence issues that antifraud systems detect.

Environment:
{env_config}

Check for:
1. IP geolocation vs billing address (city/state/country match)
2. Timezone vs IP geo vs browser locale (3-way consistency)
3. ASN type (datacenter vs residential vs mobile) — datacenter = instant flag
4. DNS resolver vs ISP of proxy IP (Google DNS from Comcast IP = suspicious)
5. Accept-Language header vs IP country vs card country
6. Connection type indicators (WiFi vs Ethernet vs Mobile) vs claimed device
7. IP reputation score and blacklist status
8. WebRTC local IP vs proxy IP subnet

Respond with JSON:
{{
    "coherent": true/false,
    "score": 0-100,
    "mismatches": ["specific environment mismatch"],
    "fixes": ["how to fix each mismatch"]
}}"""


def score_environment_coherence(env_config: Dict) -> AIEnvironmentCoherence:
    """
    V8.3: AI-powered environment coherence scoring.
    Validates IP+geo+locale+timezone+ASN+DNS as a coherent identity.
    """
    prompt = ENVIRONMENT_COHERENCE_PROMPT.format(
        env_config=json.dumps(env_config, indent=2, default=str)
    )
    result = _query_ollama_json(prompt, task_type="environment_coherence",
                                temperature=0.1, timeout=45)
    if result and isinstance(result, dict):
        return AIEnvironmentCoherence(
            coherent=result.get("coherent", False),
            score=float(result.get("score", 50)),
            mismatches=result.get("mismatches", []),
            fixes=result.get("fixes", []),
        )
    return AIEnvironmentCoherence(
        coherent=True, score=60, mismatches=[],
        fixes=["AI unavailable"], ai_powered=False)


# ─── TASK 5: NAVIGATION PATH GENERATOR ───────────────────────────────────────

NAVIGATION_PATH_PROMPT = """You are a web analytics expert. Generate a realistic navigation path for a returning customer on this site.

Target: {target}
Product category: {category}
Entry source: {entry_source}

Generate a realistic browsing path that a real customer would take before purchasing. Include referrer chain, search query if organic, and page-by-page navigation.

Respond with JSON:
{{
    "search_query": "what the user searched on Google to find this site",
    "referrer_chain": ["google.com/search?q=...", "{target}/"],
    "pages": [
        {{"url": "/", "type": "landing", "dwell_s": 8, "actions": ["scroll", "click_nav"]}},
        {{"url": "/category/...", "type": "browse", "dwell_s": 15, "actions": ["scroll", "filter"]}},
        {{"url": "/product/...", "type": "product", "dwell_s": 45, "actions": ["scroll", "read_reviews", "add_to_cart"]}}
    ],
    "total_pages": 5
}}"""


def generate_navigation_path(target: str, category: str = "general",
                              entry_source: str = "google_organic") -> AINavigationPath:
    """
    V8.3: AI-generated realistic navigation path for target site.
    Creates believable browse-to-purchase journey.
    """
    prompt = NAVIGATION_PATH_PROMPT.format(
        target=target, category=category, entry_source=entry_source
    )
    result = _query_ollama_json(prompt, task_type="navigation_path",
                                temperature=0.5, timeout=45)
    if result and isinstance(result, dict):
        return AINavigationPath(
            target=target,
            pages=result.get("pages", []),
            referrer_chain=result.get("referrer_chain", []),
            search_query=result.get("search_query", ""),
            total_pages=int(result.get("total_pages", 5)),
        )
    return AINavigationPath(
        target=target, pages=[], referrer_chain=[],
        search_query="", total_pages=0, ai_powered=False)


# ─── TASK 6: CARD ROTATION OPTIMIZER ─────────────────────────────────────────

CARD_ROTATION_PROMPT = """You are a payment operations strategist. Given the decline history and available cards, recommend the optimal next card-target-amount-timing combination.

Available cards (BINs): {available_bins}
Recent decline history: {decline_history}
Available targets: {available_targets}
Time since last attempt: {hours_since_last}h

Respond with JSON:
{{
    "recommended_card_bin": "best BIN to use next",
    "recommended_target": "best target for this card",
    "recommended_amount": 99.99,
    "recommended_time": "now / wait Xh / specific time",
    "cooldown_hours": 0,
    "reasoning": "why this combination",
    "alternatives": [{{"bin": "...", "target": "...", "amount": 0, "reason": "..."}}]
}}"""


def optimize_card_rotation(available_bins: List[str], decline_history: List[Dict],
                            available_targets: List[str],
                            hours_since_last: float = 0) -> AICardRotation:
    """
    V8.3: AI-optimized card rotation strategy using decline history
    and vector memory to recommend optimal card-target-amount-timing.
    """
    vector_ctx = ""
    try:
        from titan_vector_memory import get_vector_memory
        mem = get_vector_memory()
        if mem.is_available:
            vector_ctx = mem.build_rotation_context(available_bins, available_targets)
    except (ImportError, Exception):
        pass

    prompt = CARD_ROTATION_PROMPT.format(
        available_bins=json.dumps(available_bins),
        decline_history=json.dumps(decline_history[-20:], default=str),
        available_targets=json.dumps(available_targets),
        hours_since_last=hours_since_last
    ) + vector_ctx
    result = _query_ollama_json(prompt, task_type="card_rotation",
                                temperature=0.3, timeout=45)
    if result and isinstance(result, dict):
        return AICardRotation(
            recommended_card_bin=result.get("recommended_card_bin", available_bins[0] if available_bins else ""),
            recommended_target=result.get("recommended_target", available_targets[0] if available_targets else ""),
            recommended_amount=float(result.get("recommended_amount", 100)),
            recommended_time=result.get("recommended_time", "now"),
            cooldown_hours=float(result.get("cooldown_hours", 0)),
            reasoning=result.get("reasoning", ""),
            alternatives=result.get("alternatives", []),
        )
    return AICardRotation(
        recommended_card_bin=available_bins[0] if available_bins else "",
        recommended_target=available_targets[0] if available_targets else "",
        recommended_amount=100, recommended_time="now", cooldown_hours=0,
        reasoning="AI unavailable", alternatives=[], ai_powered=False)


# ─── TASK 7: FORM FILL CADENCE TUNER ─────────────────────────────────────────

FORM_FILL_PROMPT = """You are a behavioral biometrics expert specializing in form interaction patterns. Generate realistic form fill timing for this persona type.

Persona: {persona_type}
Age range: {age_range}
Device: {device_type}
Target form: {form_type}

Generate per-field timing that matches how a real {persona_type} would fill out a {form_type} form.

Respond with JSON:
{{
    "field_delays_ms": {{
        "first_name": [800, 1500],
        "last_name": [600, 1200],
        "email": [1500, 3000],
        "address": [2000, 4000],
        "city": [800, 1500],
        "state": [400, 800],
        "zip": [600, 1200],
        "card_number": [3000, 6000],
        "card_exp": [800, 1500],
        "card_cvv": [600, 1200]
    }},
    "tab_vs_click": "tab/click/mixed",
    "typo_rate": 0.02,
    "correction_style": "backspace/select_all/mouse_select",
    "paste_allowed_fields": ["email"]
}}"""


def tune_form_fill_cadence(persona_type: str = "casual_shopper",
                            age_range: str = "25-45",
                            device_type: str = "desktop",
                            form_type: str = "checkout") -> AIFormFillCadence:
    """
    V8.3: AI-tuned form fill timing per persona type.
    Generates per-field delays that match real human patterns.
    """
    prompt = FORM_FILL_PROMPT.format(
        persona_type=persona_type, age_range=age_range,
        device_type=device_type, form_type=form_type
    )
    result = _query_ollama_json(prompt, task_type="form_fill_cadence",
                                temperature=0.4, timeout=30)
    if result and isinstance(result, dict):
        raw_delays = result.get("field_delays_ms", {})
        delays = {}
        for field, vals in raw_delays.items():
            if isinstance(vals, list) and len(vals) == 2:
                delays[field] = (int(vals[0]), int(vals[1]))
        return AIFormFillCadence(
            field_delays_ms=delays,
            tab_vs_click=result.get("tab_vs_click", "mixed"),
            typo_rate=float(result.get("typo_rate", 0.02)),
            correction_style=result.get("correction_style", "backspace"),
            paste_allowed_fields=result.get("paste_allowed_fields", []),
        )
    return AIFormFillCadence(
        field_delays_ms={"first_name": (800, 1500), "email": (1500, 3000),
                         "card_number": (3000, 6000)},
        tab_vs_click="mixed", typo_rate=0.02,
        correction_style="backspace", paste_allowed_fields=[], ai_powered=False)


# ─── TASK 8: VELOCITY SCHEDULER ──────────────────────────────────────────────

VELOCITY_SCHEDULE_PROMPT = """You are a payment velocity management expert. Given this card's decline history, generate an optimal velocity schedule.

Card BIN: {card_bin}
Decline history: {decline_history}
Target: {target}
Target's known velocity limits: {velocity_info}

Respond with JSON:
{{
    "max_attempts_per_hour": 2,
    "max_attempts_per_day": 5,
    "cooldown_after_decline_min": 120,
    "cooldown_after_success_min": 30,
    "optimal_spacing_min": 45,
    "reasoning": "why these limits"
}}"""


def schedule_velocity(card_bin: str, decline_history: List[Dict],
                      target: str = "", velocity_info: str = "") -> AIVelocitySchedule:
    """
    V8.3: AI-planned velocity schedule for card usage.
    Prevents velocity-based declines by spacing attempts optimally.
    """
    prompt = VELOCITY_SCHEDULE_PROMPT.format(
        card_bin=card_bin[:6], decline_history=json.dumps(decline_history[-10:], default=str),
        target=target, velocity_info=velocity_info or "unknown"
    )
    result = _query_ollama_json(prompt, task_type="velocity_schedule",
                                temperature=0.2, timeout=30)
    if result and isinstance(result, dict):
        return AIVelocitySchedule(
            card_bin=card_bin[:6],
            max_attempts_per_hour=int(result.get("max_attempts_per_hour", 2)),
            max_attempts_per_day=int(result.get("max_attempts_per_day", 5)),
            cooldown_after_decline_min=int(result.get("cooldown_after_decline_min", 120)),
            cooldown_after_success_min=int(result.get("cooldown_after_success_min", 30)),
            optimal_spacing_min=int(result.get("optimal_spacing_min", 45)),
            reasoning=result.get("reasoning", ""),
        )
    return AIVelocitySchedule(
        card_bin=card_bin[:6], max_attempts_per_hour=2, max_attempts_per_day=5,
        cooldown_after_decline_min=120, cooldown_after_success_min=30,
        optimal_spacing_min=45, reasoning="AI unavailable — using safe defaults",
        ai_powered=False)


# ─── TASK 9: AVS PRE-VALIDATOR ───────────────────────────────────────────────

AVS_PREVALIDATION_PROMPT = """You are an AVS (Address Verification System) expert. Pre-validate this billing address before payment submission.

Billing address:
{address}

Card BIN country: {card_country}
Target merchant: {target}

Check for:
1. ZIP code format matches country (US: 5 or 9 digit, UK: postcode format)
2. State/province code is valid for the country
3. Street address format is realistic (not "123 Main St" generic)
4. City matches ZIP code region
5. Address is not a known PO Box (many merchants reject these)
6. Address is not a known freight forwarder

Respond with JSON:
{{
    "avs_likely_pass": true/false,
    "confidence": 0.0-1.0,
    "issues": ["specific AVS issue found"],
    "address_fixes": ["how to fix each issue"],
    "zip_format_ok": true/false
}}"""


def pre_validate_avs(address: Dict, card_country: str = "US",
                      target: str = "") -> AIAVSPreValidation:
    """
    V8.3: AI pre-validation of AVS data before payment submission.
    Catches address format issues that would trigger AVS mismatch declines.
    """
    prompt = AVS_PREVALIDATION_PROMPT.format(
        address=json.dumps(address, indent=2),
        card_country=card_country, target=target
    )
    result = _query_ollama_json(prompt, task_type="avs_prevalidation",
                                temperature=0.1, timeout=30)
    if result and isinstance(result, dict):
        return AIAVSPreValidation(
            avs_likely_pass=result.get("avs_likely_pass", False),
            confidence=float(result.get("confidence", 0.5)),
            issues=result.get("issues", []),
            address_fixes=result.get("address_fixes", []),
            zip_format_ok=result.get("zip_format_ok", True),
        )
    return AIAVSPreValidation(
        avs_likely_pass=True, confidence=0.5, issues=[],
        address_fixes=["AI unavailable"], zip_format_ok=True, ai_powered=False)


# ─── TASK 10: ADAPTIVE DEFENSE TRACKER ───────────────────────────────────────

DEFENSE_TRACKER_PROMPT = """You are an antifraud intelligence analyst. Analyze recent operation results against this target to detect if their fraud defenses have changed.

Target: {target}
Recent results (last 7 days): {recent_results}
Historical baseline: {baseline}

Detect:
1. Sudden increase in decline rate (defense upgrade?)
2. New decline codes not seen before (new fraud rules?)
3. 3DS challenge rate change (policy update?)
4. New behavioral checks (BioCatch/Forter script changes?)
5. Velocity limit changes (tighter/looser?)

Respond with JSON:
{{
    "current_engine": "best guess of current fraud engine",
    "previous_engine": "what it was before",
    "changes_detected": ["specific change detected"],
    "new_risks": ["new risk factors"],
    "strategy_adjustments": ["how to adapt strategy"]
}}"""


def track_defense_changes(target: str, recent_results: List[Dict],
                           baseline: Dict = None) -> AIDefenseTracker:
    """
    V8.3: AI-powered adaptive defense tracking.
    Detects when a target has upgraded/changed its antifraud system.
    """
    prompt = DEFENSE_TRACKER_PROMPT.format(
        target=target,
        recent_results=json.dumps(recent_results[-20:], default=str),
        baseline=json.dumps(baseline or {}, default=str)
    )
    result = _query_ollama_json(prompt, task_type="defense_tracking",
                                temperature=0.2, timeout=45)
    if result and isinstance(result, dict):
        return AIDefenseTracker(
            target=target,
            current_engine=result.get("current_engine", "unknown"),
            previous_engine=result.get("previous_engine", "unknown"),
            changes_detected=result.get("changes_detected", []),
            new_risks=result.get("new_risks", []),
            strategy_adjustments=result.get("strategy_adjustments", []),
        )
    return AIDefenseTracker(
        target=target, current_engine="unknown", previous_engine="unknown",
        changes_detected=[], new_risks=[], strategy_adjustments=[],
        ai_powered=False)


# ─── TASK 11: DECLINE AUTOPSY + AUTO-PATCH ───────────────────────────────────

DECLINE_AUTOPSY_PROMPT = """You are a payment decline forensics expert. Perform a deep autopsy on this decline and recommend specific code patches.

Decline details:
  Code: {decline_code}
  Category: {decline_category}
  Target: {target}
  PSP: {psp}
  Amount: ${amount}
  Card BIN: {card_bin}
  Card country: {card_country}
  Proxy country: {proxy_country}
  Profile age: {profile_age} days
  Session duration: {session_duration}s

Recent history for this BIN: {bin_history}

Perform root cause analysis and recommend specific module patches.

Respond with JSON:
{{
    "root_cause": "specific root cause of decline",
    "category": "network/fingerprint/behavioral/payment/identity/velocity",
    "is_retriable": true/false,
    "wait_time_min": 0,
    "patches": [
        {{"module": "module_name.py", "change": "specific change needed", "priority": "critical/high/medium"}}
    ],
    "next_action": "specific next step for operator"
}}"""


def autopsy_decline(decline_code: str, decline_category: str, target: str,
                     psp: str = "unknown", amount: float = 0,
                     card_bin: str = "", card_country: str = "US",
                     proxy_country: str = "US", profile_age: int = 90,
                     session_duration: int = 0,
                     bin_history: List[Dict] = None) -> AIDeclineAutopsy:
    """
    V8.3: AI deep decline autopsy with auto-patch recommendations.
    Analyzes root cause and suggests specific module-level fixes.
    """
    prompt = DECLINE_AUTOPSY_PROMPT.format(
        decline_code=decline_code, decline_category=decline_category,
        target=target, psp=psp, amount=amount,
        card_bin=card_bin[:6] if card_bin else "unknown",
        card_country=card_country, proxy_country=proxy_country,
        profile_age=profile_age, session_duration=session_duration,
        bin_history=json.dumps(bin_history or [], default=str)
    )
    result = _query_ollama_json(prompt, task_type="decline_autopsy",
                                temperature=0.2, timeout=60)
    if result and isinstance(result, dict):
        return AIDeclineAutopsy(
            decline_code=decline_code,
            root_cause=result.get("root_cause", "unknown"),
            category=result.get("category", "unknown"),
            is_retriable=result.get("is_retriable", False),
            wait_time_min=int(result.get("wait_time_min", 0)),
            patches=result.get("patches", []),
            next_action=result.get("next_action", "Try different card"),
        )
    return AIDeclineAutopsy(
        decline_code=decline_code, root_cause="AI unavailable",
        category="unknown", is_retriable=False, wait_time_min=60,
        patches=[], next_action="Manual analysis required", ai_powered=False)


# ─── TASK 12: CROSS-SESSION LEARNING OPTIMIZER ───────────────────────────────

CROSS_SESSION_PROMPT = """You are a data scientist specializing in payment fraud patterns. Analyze these cross-session operation results and extract actionable insights.

Operation history (last 50 operations):
{operation_history}

Identify:
1. Which BIN+target combinations have highest success rates
2. Which time-of-day patterns correlate with success
3. Which profile configurations (age, size, layers) correlate with success
4. Which decline patterns indicate systemic issues vs random failures
5. Emerging trends (targets getting harder/easier, BINs burning faster)

Respond with JSON:
{{
    "pattern_type": "success_correlation/failure_pattern/trend/anomaly",
    "insight": "specific actionable insight",
    "affected_bins": ["BINs involved"],
    "affected_targets": ["targets involved"],
    "recommendation": "specific action to take",
    "confidence": 0.0-1.0
}}"""


def optimize_cross_session(operation_history: List[Dict]) -> AICrossSessionInsight:
    """
    V8.3: AI cross-session learning optimizer.
    Analyzes patterns across all operations to extract actionable insights.
    """
    prompt = CROSS_SESSION_PROMPT.format(
        operation_history=json.dumps(operation_history[-50:], default=str)
    )
    result = _query_ollama_json(prompt, task_type="cross_session",
                                temperature=0.3, timeout=60)
    if result and isinstance(result, dict):
        return AICrossSessionInsight(
            pattern_type=result.get("pattern_type", "unknown"),
            insight=result.get("insight", ""),
            affected_bins=result.get("affected_bins", []),
            affected_targets=result.get("affected_targets", []),
            recommendation=result.get("recommendation", ""),
            confidence=float(result.get("confidence", 0.5)),
        )
    return AICrossSessionInsight(
        pattern_type="unknown", insight="AI unavailable",
        affected_bins=[], affected_targets=[],
        recommendation="Manual analysis required",
        confidence=0.0, ai_powered=False)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

    print("TITAN AI Intelligence Engine V7.6")
    print(f"Ollama available: {_is_ollama_available()}")
    print()
    
    # Test V7.6 components
    print("=== V7.6 Model Selector ===")
    selector = AIModelSelector()
    print(f"  Available models: {selector.get_model_stats()}")
    print(f"  BIN analysis model: {selector.select_model('bin_analysis')}")
    print(f"  3DS strategy model: {selector.select_model('3ds_strategy', 'thorough')}")
    print()
    
    print("=== V7.6 Prompt Cache ===")
    print(f"  Stats: {AIPromptOptimizer.get_cache_stats()}")
    print()

    if _is_ollama_available():
        # Test BIN analysis
        print("=== BIN Analysis ===")
        analysis = analyze_bin("421783", "eneba.com", 150)
        print(f"  Bank: {analysis.bank_name}")
        print(f"  Score: {analysis.ai_score}")
        print(f"  Success: {analysis.success_prediction:.0%}")
        print(f"  Best targets: {analysis.best_targets}")
        print()

        # Test target recon
        print("=== Target Recon ===")
        recon = recon_target("stockx.com", "sneakers")
        print(f"  Engine: {recon.fraud_engine_guess}")
        print(f"  PSP: {recon.payment_processor_guess}")
        print(f"  3DS: {recon.three_ds_probability:.0%}")
        print()

        # Test full operation plan
        print("=== Full Operation Plan ===")
        plan = plan_operation("421783", "eneba.com", 150)
        print(f"  {plan.executive_summary}")
        print()
        
        # Test V7.6 orchestrator
        print("=== V7.6 Orchestrated Intel ===")
        result = orchestrate_intel("421783", "eneba.com", 150)
        print(f"  Total time: {result.total_time_ms}ms")
        print(f"  Cache hits: {result.cache_hits}")
        print(f"  Model: {result.model_used}")
    else:
        print("Ollama offline — run 'ollama serve' to enable AI features")
