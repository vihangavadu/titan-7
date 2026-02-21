"""
TITAN V7.5 SINGULARITY — AI Intelligence Engine
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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum

__version__ = "7.5.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-AI")


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


def _query_ollama_direct(prompt: str, temperature: float = 0.3,
                         max_tokens: int = 4096, timeout: int = 60) -> Optional[str]:
    """Direct Ollama HTTP API call as fallback."""
    import urllib.request
    try:
        payload = json.dumps({
            "model": "titan-mistral",
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
    """Extract JSON from LLM response text."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try finding JSON array or object
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
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

    prompt = BIN_ANALYSIS_PROMPT.format(
        bin_number=bin6, known_info=known_str,
        target=target or "unknown", amount=amount or "unknown"
    ) + decline_ctx

    result = _query_ollama_json(prompt, task_type="bin_generation",
                                temperature=0.2, timeout=45)

    if result and isinstance(result, dict):
        analysis = AIBINAnalysis(
            bin_number=bin6,
            bank_name=result.get("bank_name", static_info.get("bank", "Unknown")),
            country=result.get("country", static_info.get("country", "US")),
            card_type=result.get("card_type", "credit"),
            card_level=result.get("card_level", "classic"),
            network=result.get("network", static_info.get("network", "visa")),
            risk_level=RiskLevel(result.get("risk_level", "medium")),
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

    result = _query_ollama_json(prompt, task_type="default",
                                temperature=0.2, timeout=45)

    if result and isinstance(result, dict):
        advice = AIPreFlightAdvice(
            go_decision=result.get("go_decision", False),
            confidence=float(result.get("confidence", 0.5)),
            risk_level=RiskLevel(result.get("risk_level", "medium")),
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

    result = _query_ollama_json(prompt, task_type="site_discovery",
                                temperature=0.3, timeout=45)

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
                    name=intel.name,
                    fraud_engine_guess=intel.fraud_engine.value,
                    payment_processor_guess=intel.payment_gateway.value,
                    estimated_friction=intel.friction.value,
                    three_ds_probability=intel.three_ds_rate,
                    optimal_card_types=["credit"],
                    optimal_countries=["US", "CA", "GB"],
                    warmup_strategy=intel.warmup_sites,
                    checkout_tips=intel.operator_playbook,
                    risk_factors=intel.notes,
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

    result = _query_ollama_json(prompt, task_type="default",
                                temperature=0.2, timeout=45)

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

    result = _query_ollama_json(prompt, task_type="default",
                                temperature=0.1, timeout=60)

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

    result = _query_ollama_json(prompt, task_type="default",
                                temperature=0.4, timeout=30)

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

    return AIOperationPlan(
        bin_analysis=bin_analysis,
        target_recon=target_recon,
        threeds_strategy=threeds,
        behavioral_tuning=behavior,
        overall_score=round(score, 1),
        go_decision=go,
        executive_summary=summary,
        ai_powered=all_ai,
    )


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
    
    import time
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
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

def is_ai_available() -> bool:
    """Check if AI intelligence engine is operational."""
    return _is_ollama_available()


def get_ai_status() -> Dict:
    """Get AI engine status for GUI display."""
    available = _is_ollama_available()
    return {
        "available": available,
        "provider": "ollama" if available else "none",
        "features": [
            "bin_analysis", "preflight_advisor", "target_recon",
            "3ds_strategy", "profile_audit", "behavioral_tuning",
            "operation_planner"
        ] if available else [],
        "version": __version__,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

    print("TITAN AI Intelligence Engine V7.5")
    print(f"Ollama available: {_is_ollama_available()}")
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
    else:
        print("Ollama offline — run 'ollama serve' to enable AI features")
