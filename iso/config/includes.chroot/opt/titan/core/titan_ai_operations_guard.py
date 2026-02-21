"""
TITAN V7.6 SINGULARITY — AI Operations Guard
Silent AI daemon that watches over the entire operation lifecycle.

╔══════════════════════════════════════════════════════════════════════════════╗
║  THE AI OPERATIONS GUARD — WHAT IT DOES                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  The human operator does their work. The AI Guard runs silently behind       ║
║  the OS and handles everything the human CANNOT do:                          ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  PHASE 1: PRE-OPERATION (before browser launches)                   │     ║
║  │  • Analyze target + card + proxy combo for compatibility            │     ║
║  │  • Detect mismatches the human wouldn't notice                      │     ║
║  │  • Pre-optimize fingerprint, timezone, locale for the card          │     ║
║  │  • Warn if proxy geo doesn't match billing address                  │     ║
║  │  • Check if BIN is known to trigger 3DS on this target's PSP       │     ║
║  │  • Score the overall operation probability before committing        │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  PHASE 2: ACTIVE SESSION (while human browses)                      │     ║
║  │  • Monitor session duration vs. normal visitor patterns             │     ║
║  │  • Track pages visited — is the browsing path realistic?            │     ║
║  │  • Detect if antifraud scripts loaded (Forter, Sift, etc.)         │     ║
║  │  • Monitor proxy health in real-time — warn if degrading            │     ║
║  │  • Ensure fingerprint hasn't leaked or changed mid-session          │     ║
║  │  • Suggest optimal checkout timing based on session warmth           │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  PHASE 3: CHECKOUT (human is paying — maximum AI assistance)        │     ║
║  │  • Browser co-pilot handles 3DS/iframe blocking (already built)     │     ║
║  │  • AI Guard monitors from OS side: proxy latency, DNS leaks         │     ║
║  │  • If decline detected: instant analysis of WHY + next action       │     ║
║  │  • If 3DS triggered: assess whether to wait/timeout/abort           │     ║
║  │  • Amount optimization: suggest split if too high for PSP           │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  PHASE 4: POST-OPERATION (after transaction)                        │     ║
║  │  • Log result to vector memory for cross-operation learning         │     ║
║  │  • Analyze decline reason and suggest corrective action             │     ║
║  │  • Update target intelligence with fresh probe data                 │     ║
║  │  • Recommend next target based on what worked/failed                │     ║
║  │  • Track velocity across cards/targets to avoid triggers            │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║                                                                              ║
║  The Guard uses Ollama LLM for complex reasoning that rules can't handle:   ║
║  • "BIN is Ohio credit union but proxy is Miami — should I warn?"           ║
║  • "Session is 45 min with $0 spend — antifraud will flag this"            ║
║  • "Forter just loaded — need 5 min warmup before checkout"                ║
║  • "Card declined for 'do_not_honor' — is it burned or retriable?"         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    from titan_ai_operations_guard import get_operations_guard

    guard = get_operations_guard()

    # Phase 1: Pre-operation check
    pre_check = guard.pre_operation_check(
        target="cdkeys.com", card_bin="401200", card_country="US",
        proxy_ip="1.2.3.4", proxy_country="US", proxy_state="NY",
        billing_state="NY", billing_zip="10001", amount=50
    )

    # Phase 2: Session health monitor (call periodically)
    health = guard.check_session_health(
        session_duration_sec=120, pages_visited=5,
        antifraud_detected=["stripe_radar"], proxy_latency_ms=85
    )

    # Phase 3: Checkout assistance
    checkout = guard.checkout_assist(
        target="cdkeys.com", psp="stripe", amount=50,
        card_country="US", three_ds_status="none"
    )

    # Phase 4: Post-operation analysis
    post = guard.post_operation_analysis(
        target="cdkeys.com", result="declined", decline_code="do_not_honor",
        card_bin="401200", amount=50, psp="stripe"
    )
"""

import os
import json
import time
import logging
import asyncio
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

__version__ = "8.0.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-AI-GUARD")


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATION PHASES
# ═══════════════════════════════════════════════════════════════════════════════

class OperationPhase(Enum):
    PRE_OP = "pre_operation"
    ACTIVE_SESSION = "active_session"
    CHECKOUT = "checkout"
    POST_OP = "post_operation"


class RiskLevel(Enum):
    GREEN = "green"      # All clear — proceed
    YELLOW = "yellow"    # Caution — fixable issues
    RED = "red"          # Stop — critical issues


@dataclass
class GuardVerdict:
    """Result from the AI Guard's analysis"""
    phase: OperationPhase
    risk_level: RiskLevel
    proceed: bool
    issues: List[Dict[str, str]]       # List of {severity, message, fix}
    recommendations: List[str]
    ai_reasoning: str = ""              # LLM's reasoning (if Ollama was consulted)
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════════════════════════
# AI OPERATIONS GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class AIOperationsGuard:
    """
    Silent AI daemon that monitors the entire operation lifecycle.
    Uses rule-based checks for speed, escalates to Ollama LLM for
    complex reasoning that rules can't handle.

    The guard NEVER blocks the human — it only advises.
    All interventions are suggestions, not hard stops.
    """

    def __init__(self):
        self._ollama_available = False
        self._ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
        self._ollama_model = os.getenv("OLLAMA_MODEL", "llama3:8b")
        self._operation_log: List[Dict] = []
        self._velocity_tracker: Dict[str, List[float]] = {}  # card_bin → [timestamps]
        self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is available for LLM reasoning."""
        try:
            import urllib.request
            urllib.request.urlopen(self._ollama_url, timeout=2)
            self._ollama_available = True
            logger.info(f"AI Guard: Ollama connected at {self._ollama_url}")
        except Exception:
            self._ollama_available = False
            logger.info("AI Guard: Ollama not available — using rule-based mode")

    def _ask_ollama(self, prompt: str, max_tokens: int = 300) -> str:
        """Ask Ollama for complex reasoning. Returns empty string if unavailable."""
        if not self._ollama_available:
            return ""
        try:
            import urllib.request
            data = json.dumps({
                "model": self._ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            }).encode()
            req = urllib.request.Request(
                f"{self._ollama_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                return result.get("response", "").strip()
        except Exception as e:
            logger.debug(f"Ollama query failed: {e}")
            return ""

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1: PRE-OPERATION CHECK
    # ═══════════════════════════════════════════════════════════════════════
    # Before the human even opens the browser, the AI analyzes the entire
    # setup: target + card + proxy + billing. Catches mismatches that
    # the human wouldn't notice and that would cause declines.

    def pre_operation_check(self, target: str, card_bin: str = "",
                            card_country: str = "US",
                            proxy_ip: str = "", proxy_country: str = "",
                            proxy_state: str = "",
                            billing_state: str = "", billing_zip: str = "",
                            amount: float = 100) -> GuardVerdict:
        """
        Comprehensive pre-operation analysis.
        Catches issues BEFORE the human commits to a target.
        """
        issues = []
        recommendations = []

        # ── Check 1: Geo mismatch (proxy vs billing) ──
        if proxy_country and card_country:
            if proxy_country.upper() != card_country.upper():
                issues.append({
                    "severity": "critical",
                    "message": f"Proxy country ({proxy_country}) does not match card country ({card_country})",
                    "fix": f"Use a {card_country} proxy or switch to a {proxy_country} card",
                })

        if proxy_state and billing_state:
            if proxy_state.upper() != billing_state.upper():
                issues.append({
                    "severity": "warning",
                    "message": f"Proxy state ({proxy_state}) differs from billing state ({billing_state})",
                    "fix": f"Ideally use a proxy in {billing_state} for state-level match",
                })

        # ── Check 2: BIN + PSP 3DS likelihood ──
        try:
            from titan_target_intel_v2 import get_target_intel_v2
            intel = get_target_intel_v2()
            score = intel.score_target(
                target, card_country=card_country, amount=amount
            )
            gp_score = score.get("golden_path_score", 0)

            if gp_score >= 85:
                recommendations.append(
                    f"Golden target: {target} scores {gp_score}/100. Excellent choice."
                )
            elif gp_score >= 60:
                recommendations.append(
                    f"Moderate target: {target} scores {gp_score}/100. Proceed with caution."
                )
            else:
                issues.append({
                    "severity": "warning",
                    "message": f"Target {target} scores only {gp_score}/100 — higher 3DS/decline risk",
                    "fix": "Consider a higher-scoring target or lower the amount",
                })
        except Exception:
            pass

        # ── Check 3: Amount optimization ──
        if amount > 500:
            issues.append({
                "severity": "warning",
                "message": f"Amount ${amount:.0f} is high — increases 3DS probability on most PSPs",
                "fix": "Consider splitting into 2-3 orders under $200 each",
            })
        elif amount > 200:
            recommendations.append(
                f"Amount ${amount:.0f} is moderate. Most PSPs won't trigger 3DS under $200."
            )
        else:
            recommendations.append(
                f"Amount ${amount:.0f} is optimal. Low 3DS risk."
            )

        # ── Check 4: Velocity check ──
        if card_bin:
            now = time.time()
            bin_key = card_bin[:6]
            if bin_key not in self._velocity_tracker:
                self._velocity_tracker[bin_key] = []
            # Clean old entries (>1 hour)
            self._velocity_tracker[bin_key] = [
                t for t in self._velocity_tracker[bin_key] if now - t < 3600
            ]
            recent_count = len(self._velocity_tracker[bin_key])
            if recent_count >= 3:
                issues.append({
                    "severity": "critical",
                    "message": f"BIN {bin_key} has {recent_count} attempts in the last hour — velocity risk",
                    "fix": "Wait at least 30 minutes or switch to a different card",
                })
            elif recent_count >= 1:
                recommendations.append(
                    f"BIN {bin_key} has {recent_count} recent attempt(s). "
                    f"Spacing looks OK but don't exceed 3/hour."
                )

        # ── Check 5: Ask Ollama for deeper analysis (if available) ──
        ai_reasoning = ""
        if self._ollama_available and (issues or amount > 200):
            prompt = (
                f"You are a transaction risk analyst. Briefly analyze this setup:\n"
                f"Target: {target}\n"
                f"Card: BIN {card_bin[:6] if card_bin else 'unknown'}, country {card_country}\n"
                f"Proxy: {proxy_country}/{proxy_state}\n"
                f"Billing: {billing_state}, {billing_zip}\n"
                f"Amount: ${amount:.2f}\n"
                f"Known issues: {json.dumps([i['message'] for i in issues])}\n\n"
                f"In 2-3 sentences, assess the risk and suggest the single most "
                f"important thing to fix or watch out for. Be direct."
            )
            ai_reasoning = self._ask_ollama(prompt)
            if ai_reasoning:
                recommendations.append(f"AI: {ai_reasoning}")

        # ── Determine risk level ──
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")

        if critical_count > 0:
            risk_level = RiskLevel.RED
        elif warning_count > 1:
            risk_level = RiskLevel.YELLOW
        else:
            risk_level = RiskLevel.GREEN

        return GuardVerdict(
            phase=OperationPhase.PRE_OP,
            risk_level=risk_level,
            proceed=critical_count == 0,
            issues=issues,
            recommendations=recommendations,
            ai_reasoning=ai_reasoning,
            confidence=0.85 if ai_reasoning else 0.70,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2: ACTIVE SESSION HEALTH MONITOR
    # ═══════════════════════════════════════════════════════════════════════
    # While the human browses, the guard monitors session health signals.
    # It detects patterns that antifraud systems look for:
    # - Sessions that are too short (bot-like) or too long (suspicious)
    # - Too few pages visited before checkout (no browsing behavior)
    # - Proxy latency spikes (residential proxy failing)
    # - Antifraud scripts loading (need more warmup)

    def check_session_health(self, session_duration_sec: int = 0,
                              pages_visited: int = 0,
                              antifraud_detected: List[str] = None,
                              proxy_latency_ms: int = 0,
                              fingerprint_consistent: bool = True) -> GuardVerdict:
        """
        Monitor the active browsing session for health issues.
        Call this periodically (every 30-60 seconds) during the session.
        """
        issues = []
        recommendations = []
        antifraud_detected = antifraud_detected or []

        # ── Session duration analysis ──
        if session_duration_sec < 30:
            # Too early to analyze
            pass
        elif session_duration_sec < 60 and pages_visited < 2:
            issues.append({
                "severity": "warning",
                "message": "Session is very short with few pages — looks bot-like",
                "fix": "Browse at least 3-5 pages and spend 2+ minutes before checkout",
            })
        elif session_duration_sec > 1800:  # 30 min
            recommendations.append(
                "Session is 30+ minutes. Consider completing checkout soon — "
                "very long sessions can look suspicious to some antifraud systems."
            )

        # ── Pages visited analysis ──
        if pages_visited >= 3:
            recommendations.append(
                f"Good browsing depth ({pages_visited} pages). "
                f"Session looks organic to antifraud systems."
            )
        elif pages_visited < 2 and session_duration_sec > 60:
            issues.append({
                "severity": "warning",
                "message": "Only visited 1 page in 60+ seconds — low engagement",
                "fix": "Browse product pages, view details. Antifraud expects browsing behavior.",
            })

        # ── Antifraud detection ──
        for af in antifraud_detected:
            af_lower = af.lower()
            if af_lower in ("forter", "riskified"):
                issues.append({
                    "severity": "warning",
                    "message": f"Enterprise antifraud ({af}) detected on this site",
                    "fix": (
                        f"Spend at least 3-5 minutes browsing before checkout. "
                        f"{af.title()} uses behavioral analysis — need organic session."
                    ),
                })
            elif af_lower == "sift":
                recommendations.append(
                    "Sift detected — behavioral analysis active. "
                    "Natural browsing pace is important."
                )
            elif af_lower in ("datadome", "perimeterx", "akamai"):
                issues.append({
                    "severity": "critical",
                    "message": f"Aggressive bot detection ({af}) active",
                    "fix": "Ensure Camoufox fingerprint is solid. Avoid rapid navigation.",
                })

        # ── Proxy health ──
        if proxy_latency_ms > 500:
            issues.append({
                "severity": "warning",
                "message": f"Proxy latency is high ({proxy_latency_ms}ms) — may cause timeouts",
                "fix": "Consider rotating to a faster proxy before checkout",
            })
        elif proxy_latency_ms > 200:
            recommendations.append(
                f"Proxy latency ({proxy_latency_ms}ms) is acceptable but not ideal. "
                f"Under 150ms is best."
            )

        # ── Fingerprint consistency ──
        if not fingerprint_consistent:
            issues.append({
                "severity": "critical",
                "message": "Fingerprint inconsistency detected mid-session",
                "fix": "DO NOT proceed to checkout. Restart session with fresh profile.",
            })

        # ── Determine risk level ──
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")

        if critical_count > 0:
            risk_level = RiskLevel.RED
        elif warning_count > 0:
            risk_level = RiskLevel.YELLOW
        else:
            risk_level = RiskLevel.GREEN

        # ── Checkout readiness ──
        is_checkout_ready = (
            session_duration_sec >= 90 and
            pages_visited >= 3 and
            critical_count == 0 and
            proxy_latency_ms < 500 and
            fingerprint_consistent
        )

        if is_checkout_ready and not any(i["severity"] == "warning" for i in issues
                                          if "antifraud" in i.get("message", "").lower()):
            recommendations.append(
                "✅ Session looks healthy. You're clear to proceed to checkout."
            )

        return GuardVerdict(
            phase=OperationPhase.ACTIVE_SESSION,
            risk_level=risk_level,
            proceed=critical_count == 0,
            issues=issues,
            recommendations=recommendations,
            confidence=0.80,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: CHECKOUT ASSISTANCE
    # ═══════════════════════════════════════════════════════════════════════
    # The human is at checkout. The browser co-pilot handles 3DS/iframe
    # blocking. This guard provides OS-level intelligence:
    # - Optimal amount for this PSP/card combo
    # - Whether to use guest checkout or account
    # - What to expect (3DS likelihood, decline probability)

    def checkout_assist(self, target: str, psp: str = "unknown",
                        amount: float = 100, card_country: str = "US",
                        card_bin: str = "",
                        three_ds_status: str = "unknown") -> GuardVerdict:
        """
        Real-time checkout assistance.
        Called when the human reaches the payment page.
        """
        issues = []
        recommendations = []

        # ── 3DS prediction ──
        try:
            from titan_target_intel_v2 import PSP_3DS_BEHAVIOR
            psp_info = PSP_3DS_BEHAVIOR.get(psp.lower(), {})
            default_3ds = psp_info.get("default_3ds", "unknown")

            if default_3ds == "OFF":
                recommendations.append(
                    f"PSP {psp}: 3DS is OFF by default. Expect smooth checkout. "
                    f"AI Co-Pilot iframe shield active as precaution."
                )
            elif default_3ds == "RISK_BASED":
                rate = psp_info.get("3ds_adoption_rate", 0.5)
                recommendations.append(
                    f"PSP {psp}: risk-based 3DS (~{int(rate*100)}% trigger rate). "
                    f"AI Co-Pilot is monitoring. Low amount + {card_country} card helps."
                )
            elif default_3ds == "ENFORCED_EU":
                from titan_target_intel_v2 import GEO_3DS_ENFORCEMENT
                if card_country in GEO_3DS_ENFORCEMENT.get("no_mandate", {}).get("countries", []):
                    recommendations.append(
                        f"PSP {psp}: EU-enforced BUT your {card_country} card is "
                        f"one-leg-out exempt. 3DS rate drops to ~15%."
                    )
                else:
                    issues.append({
                        "severity": "warning",
                        "message": f"PSP {psp} enforces 3DS for {card_country} cards (PSD2)",
                        "fix": f"Keep amount under 30 EUR for low-value exemption, or use US/CA/AU card",
                    })
        except ImportError:
            pass

        # ── Amount advice ──
        if three_ds_status == "none":
            recommendations.append("Target has NO 3DS. Amount is not constrained by 3DS thresholds.")
        elif amount > 200 and three_ds_status != "none":
            recommendations.append(
                f"Amount ${amount:.0f} may trigger 3DS on conditional merchants. "
                f"Under $100 is safest for risk-based PSPs."
            )

        # ── Velocity tracking ──
        if card_bin:
            bin_key = card_bin[:6]
            now = time.time()
            if bin_key not in self._velocity_tracker:
                self._velocity_tracker[bin_key] = []
            self._velocity_tracker[bin_key].append(now)

        # ── Ask Ollama for checkout strategy (if available) ──
        ai_reasoning = ""
        if self._ollama_available:
            prompt = (
                f"You are a payment processing expert. The operator is about to "
                f"submit payment on {target} (PSP: {psp}). Card: {card_country}, "
                f"amount: ${amount:.2f}, 3DS status: {three_ds_status}.\n\n"
                f"In 2 sentences, give the single most important tactical advice "
                f"for this specific checkout. Be concrete and actionable."
            )
            ai_reasoning = self._ask_ollama(prompt)
            if ai_reasoning:
                recommendations.append(f"AI: {ai_reasoning}")

        risk_level = RiskLevel.GREEN
        if any(i["severity"] == "critical" for i in issues):
            risk_level = RiskLevel.RED
        elif any(i["severity"] == "warning" for i in issues):
            risk_level = RiskLevel.YELLOW

        return GuardVerdict(
            phase=OperationPhase.CHECKOUT,
            risk_level=risk_level,
            proceed=True,
            issues=issues,
            recommendations=recommendations,
            ai_reasoning=ai_reasoning,
            confidence=0.85 if ai_reasoning else 0.75,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 4: POST-OPERATION ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════
    # After the transaction, the guard analyzes what happened and learns.
    # On success: logs what worked for future reference.
    # On decline: analyzes WHY and recommends corrective action.
    # On 3DS: analyzes whether the card is enrolled, PSP is strict, etc.

    def post_operation_analysis(self, target: str, result: str,
                                 decline_code: str = "",
                                 card_bin: str = "", amount: float = 0,
                                 psp: str = "unknown",
                                 three_ds_triggered: bool = False) -> GuardVerdict:
        """
        Post-operation analysis and learning.
        Called after the transaction completes (success or failure).
        """
        issues = []
        recommendations = []

        # Log the operation
        op_record = {
            "target": target,
            "result": result,
            "decline_code": decline_code,
            "card_bin": card_bin[:6] if card_bin else "",
            "amount": amount,
            "psp": psp,
            "three_ds_triggered": three_ds_triggered,
            "timestamp": time.time(),
        }
        self._operation_log.append(op_record)

        if result.lower() in ("success", "approved", "succeeded"):
            # ── SUCCESS PATH ──
            recommendations.append(
                f"✅ Success on {target} (PSP: {psp}, ${amount:.2f}). "
                f"This target + card combo works. Logged for future reference."
            )
            if not three_ds_triggered:
                recommendations.append(
                    "No 3DS triggered — this is a clean path. "
                    "Can reuse this target for similar cards."
                )

            # Store in vector memory if available
            try:
                from titan_vector_memory import get_vector_memory
                vm = get_vector_memory()
                if vm:
                    vm.store(
                        collection="operations",
                        text=f"SUCCESS: {target} | PSP:{psp} | BIN:{card_bin[:6]} | "
                             f"${amount} | 3DS:{three_ds_triggered}",
                        metadata=op_record,
                    )
            except Exception:
                pass

        elif result.lower() in ("declined", "failed", "decline"):
            # ── DECLINE PATH ──
            decline_analysis = self._analyze_decline(decline_code, card_bin, target, psp, amount)
            issues.extend(decline_analysis["issues"])
            recommendations.extend(decline_analysis["recommendations"])

            # Ask Ollama for deeper analysis
            ai_reasoning = ""
            if self._ollama_available:
                recent_ops = [
                    op for op in self._operation_log[-10:]
                    if op.get("card_bin") == (card_bin[:6] if card_bin else "")
                ]
                prompt = (
                    f"A transaction was DECLINED. Analyze and advise:\n"
                    f"Target: {target}, PSP: {psp}\n"
                    f"Card BIN: {card_bin[:6] if card_bin else 'unknown'}, Amount: ${amount:.2f}\n"
                    f"Decline code: {decline_code}\n"
                    f"3DS triggered: {three_ds_triggered}\n"
                    f"Recent history for this card: {len(recent_ops)} attempts\n\n"
                    f"In 3 sentences: (1) Why was this likely declined? "
                    f"(2) Is the card burned or retriable? "
                    f"(3) What should the operator do next?"
                )
                ai_reasoning = self._ask_ollama(prompt, max_tokens=200)
                if ai_reasoning:
                    recommendations.append(f"AI Analysis: {ai_reasoning}")

        elif three_ds_triggered:
            # ── 3DS TRIGGERED ──
            issues.append({
                "severity": "warning",
                "message": f"3DS was triggered on {target} (PSP: {psp})",
                "fix": "Card may be VBV-enrolled. Try a different BIN or lower amount.",
            })
            recommendations.append(
                "3DS trigger doesn't burn the card. You can retry on a different target "
                "with lower 3DS probability."
            )

        # ── FEEDBACK LOOP: Update target intelligence with real results ──
        self._feed_back_to_target_intel(target, result, psp, decline_code,
                                         three_ds_triggered, amount)

        # ── Recommend next target ──
        if result.lower() in ("declined", "failed", "decline"):
            try:
                from titan_target_intel_v2 import get_target_intel_v2
                intel = get_target_intel_v2()
                golden = intel.find_golden_targets(
                    card_country=card_bin[:2] if len(card_bin) >= 2 else "US",
                    max_amount=amount,
                    min_score=80,
                )
                if golden:
                    top = golden[0]
                    recommendations.append(
                        f"Next target suggestion: {top['domain']} "
                        f"(score: {top['golden_path_score']}/100)"
                    )
            except Exception:
                pass

        # Determine risk level
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        risk_level = RiskLevel.RED if critical_count > 0 else (
            RiskLevel.YELLOW if issues else RiskLevel.GREEN
        )

        return GuardVerdict(
            phase=OperationPhase.POST_OP,
            risk_level=risk_level,
            proceed=True,
            issues=issues,
            recommendations=recommendations,
            confidence=0.80,
        )

    def _analyze_decline(self, decline_code: str, card_bin: str,
                          target: str, psp: str, amount: float) -> Dict:
        """Rule-based decline analysis."""
        issues = []
        recommendations = []
        code = decline_code.lower().replace(" ", "_").replace("-", "_")

        DECLINE_MAP = {
            "do_not_honor": {
                "meaning": "Issuer rejected without specific reason",
                "card_burned": False,
                "retriable": True,
                "action": "Try a different merchant or wait 30 minutes and retry",
            },
            "insufficient_funds": {
                "meaning": "Card doesn't have enough balance",
                "card_burned": False,
                "retriable": False,
                "action": "Card has insufficient funds. Try lower amount or different card.",
            },
            "card_declined": {
                "meaning": "Generic decline from issuer",
                "card_burned": False,
                "retriable": True,
                "action": "Generic decline. Retry on different target or wait.",
            },
            "fraudulent": {
                "meaning": "Issuer flagged as potential fraud",
                "card_burned": True,
                "retriable": False,
                "action": "Card is likely burned. Do NOT retry — use a different card.",
            },
            "pickup_card": {
                "meaning": "Card reported lost/stolen",
                "card_burned": True,
                "retriable": False,
                "action": "Card is burned (lost/stolen flag). Discard immediately.",
            },
            "restricted_card": {
                "meaning": "Card restricted by issuer",
                "card_burned": True,
                "retriable": False,
                "action": "Card is restricted. Cannot be used. Switch cards.",
            },
            "security_violation": {
                "meaning": "Security rules violated (velocity, geo, etc.)",
                "card_burned": False,
                "retriable": True,
                "action": "Security trigger — likely velocity or geo mismatch. "
                          "Wait 1 hour, fix proxy geo, and retry.",
            },
            "transaction_not_allowed": {
                "meaning": "Card not allowed for this transaction type",
                "card_burned": False,
                "retriable": True,
                "action": "Card can't be used for this merchant type. Try different target.",
            },
            "invalid_card": {
                "meaning": "Card number is invalid",
                "card_burned": True,
                "retriable": False,
                "action": "Card number is invalid. Check the number and try again.",
            },
            "expired_card": {
                "meaning": "Card has expired",
                "card_burned": True,
                "retriable": False,
                "action": "Card is expired. Discard.",
            },
        }

        info = DECLINE_MAP.get(code, {
            "meaning": f"Unknown decline code: {decline_code}",
            "card_burned": False,
            "retriable": True,
            "action": "Unknown decline. Card may still be usable. Try different target.",
        })

        severity = "critical" if info["card_burned"] else "warning"
        issues.append({
            "severity": severity,
            "message": f"Decline: {info['meaning']}",
            "fix": info["action"],
        })

        if info["card_burned"]:
            recommendations.append(
                f"⛔ Card BIN {card_bin[:6] if card_bin else '?'} is likely BURNED. "
                f"Do not retry this card."
            )
        elif info["retriable"]:
            recommendations.append(
                f"Card is NOT burned. Retriable on a different target or after a wait."
            )

        return {"issues": issues, "recommendations": recommendations}

    # ═══════════════════════════════════════════════════════════════════════
    # FEEDBACK LOOP: Learn from operation results
    # ═══════════════════════════════════════════════════════════════════════

    def _feed_back_to_target_intel(self, target: str, result: str,
                                    psp: str, decline_code: str,
                                    three_ds_triggered: bool,
                                    amount: float):
        """
        Feed operation results back into target intelligence systems.
        This is the LEARNING LOOP — without this, Titan OS never improves.

        Updates:
        1. target_discovery.py — update success_rate for the target
        2. target_intel_v2.py — store observed PSP behavior
        3. operation_logger — persist to disk for cross-session learning
        """
        is_success = result.lower() in ("success", "approved", "succeeded")
        is_decline = result.lower() in ("declined", "failed", "decline")

        # 1. Update target_discovery success rate
        try:
            from target_discovery import TargetDiscovery
            td = TargetDiscovery()
            if hasattr(td, 'update_site_stats'):
                td.update_site_stats(target, success=is_success,
                                      three_ds=three_ds_triggered)
            elif hasattr(td, 'sites'):
                for site in td.sites:
                    domain = getattr(site, 'domain', '') or site.get('domain', '')
                    if domain and target.lower() in domain.lower():
                        if hasattr(site, 'success_rate'):
                            # Exponential moving average: new = 0.9*old + 0.1*result
                            old_rate = site.success_rate or 0.5
                            site.success_rate = round(
                                0.9 * old_rate + 0.1 * (1.0 if is_success else 0.0), 3
                            )
                        break
            logger.debug(f"Feedback: target_discovery updated for {target}")
        except Exception as e:
            logger.debug(f"Feedback: target_discovery update skipped: {e}")

        # 2. Store observed 3DS behavior for this target+PSP
        try:
            feedback_dir = Path("/opt/titan/data/feedback")
            feedback_dir.mkdir(parents=True, exist_ok=True)
            feedback_file = feedback_dir / "operation_results.jsonl"
            record = {
                "target": target,
                "psp": psp,
                "result": result,
                "decline_code": decline_code,
                "three_ds_triggered": three_ds_triggered,
                "amount": amount,
                "timestamp": time.time(),
            }
            with open(feedback_file, "a") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug(f"Feedback: operation result persisted to {feedback_file}")
        except Exception as e:
            logger.debug(f"Feedback: disk write skipped: {e}")

        # 3. Store in vector memory for semantic retrieval
        try:
            from titan_vector_memory import get_vector_memory
            vm = get_vector_memory()
            if vm:
                status = "SUCCESS" if is_success else "DECLINE"
                text = (
                    f"{status}: {target} | PSP:{psp} | amount:${amount:.0f} | "
                    f"3DS:{three_ds_triggered} | decline:{decline_code}"
                )
                vm.store(collection="operations", text=text, metadata=record)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # CONVENIENCE: FULL OPERATION LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    def get_operation_history(self, card_bin: str = None,
                               limit: int = 20) -> List[Dict]:
        """Get recent operation history, optionally filtered by BIN."""
        ops = self._operation_log
        if card_bin:
            ops = [op for op in ops if op.get("card_bin") == card_bin[:6]]
        return ops[-limit:]

    def get_velocity_status(self, card_bin: str) -> Dict:
        """Check velocity status for a card BIN."""
        bin_key = card_bin[:6]
        now = time.time()
        timestamps = self._velocity_tracker.get(bin_key, [])
        recent_1h = [t for t in timestamps if now - t < 3600]
        recent_24h = [t for t in timestamps if now - t < 86400]

        return {
            "bin": bin_key,
            "attempts_1h": len(recent_1h),
            "attempts_24h": len(recent_24h),
            "safe_to_proceed": len(recent_1h) < 3,
            "recommendation": (
                "Safe" if len(recent_1h) < 2 else
                "Caution — approaching velocity limits" if len(recent_1h) < 3 else
                "STOP — too many attempts. Wait at least 30 minutes."
            ),
        }

    def get_guard_status(self) -> Dict:
        """Get overall guard status."""
        return {
            "ollama_available": self._ollama_available,
            "ollama_model": self._ollama_model if self._ollama_available else None,
            "operations_logged": len(self._operation_log),
            "cards_tracked": len(self._velocity_tracker),
            "mode": "ai_enhanced" if self._ollama_available else "rule_based",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_guard: Optional[AIOperationsGuard] = None
_guard_lock = threading.Lock()


def get_operations_guard() -> AIOperationsGuard:
    """Get singleton AIOperationsGuard instance."""
    global _guard
    with _guard_lock:
        if _guard is None:
            _guard = AIOperationsGuard()
    return _guard


# Convenience functions
def pre_op_check(**kwargs) -> GuardVerdict:
    return get_operations_guard().pre_operation_check(**kwargs)

def session_health(**kwargs) -> GuardVerdict:
    return get_operations_guard().check_session_health(**kwargs)

def checkout_assist(**kwargs) -> GuardVerdict:
    return get_operations_guard().checkout_assist(**kwargs)

def post_op_analysis(**kwargs) -> GuardVerdict:
    return get_operations_guard().post_operation_analysis(**kwargs)
