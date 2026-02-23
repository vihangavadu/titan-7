"""
TITAN V8.1 — Real-Time AI Co-Pilot Daemon
Continuous AI assistant that silently monitors the human operator and
provides real-time guidance to maximize operation success rate.

╔══════════════════════════════════════════════════════════════════════════╗
║  WHY THIS EXISTS                                                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  The human operator is good at decision-making and adapting.             ║
║  The AI is good at things the human CANNOT do:                          ║
║                                                                          ║
║  1. TIMING — Humans can't count 127 seconds precisely. AI can.         ║
║  2. MEMORY — Humans forget which BINs failed on which targets. AI      ║
║     remembers every operation across every session.                      ║
║  3. PATTERN — Humans can't correlate 200+ decline codes with 50+       ║
║     PSP behaviors across 100+ targets in real-time. AI can.            ║
║  4. MISTAKES — Humans rush to checkout without warmup, use wrong       ║
║     proxy geo, exceed velocity limits. AI catches these instantly.      ║
║  5. COORDINATION — Humans can't simultaneously monitor proxy health,   ║
║     fingerprint consistency, session timing, antifraud signals, and     ║
║     card velocity. AI monitors ALL channels in parallel.               ║
║                                                                          ║
║  This module is the BRAIN that ties all existing AI modules together   ║
║  into a single real-time pipeline. It doesn't replace them — it        ║
║  orchestrates them.                                                     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

Architecture:
    Browser Co-Pilot Script (titan_3ds_ai_exploits.py)
        ↓ events via sendBeacon to :7700/api/copilot/event
    RealtimeCopilot (this module)
        ├── EventProcessor — ingests browser + OS events
        ├── OperatorSessionTracker — state machine tracking operator flow
        ├── TimingIntelligence — optimal delays humans can't maintain
        ├── MistakeDetector — catches errors before they become declines
        ├── OllamaAdvisor — deep reasoning for complex situations
        └── GuidanceQueue — pushes advice to operator in real-time

    Orchestrates:
        ├── titan_ai_operations_guard (4-phase checks)
        ├── ai_intelligence_engine (BIN analysis, target recon)
        ├── transaction_monitor (decline intelligence)
        ├── proxy_manager (proxy health)
        ├── ollama_bridge (LLM reasoning)
        └── titan_vector_memory (cross-session learning)

Usage:
    from titan_realtime_copilot import get_realtime_copilot

    copilot = get_realtime_copilot()
    copilot.start()

    # Operator starts an operation
    copilot.begin_operation(
        target="cdkeys.com", card_bin="401200", card_country="US",
        proxy_country="US", billing_state="NY", amount=49.99
    )

    # Browser events flow in automatically via HTTP
    # Copilot processes them and pushes guidance

    # Get latest guidance (GUI polls this)
    guidance = copilot.get_latest_guidance()

    # End operation
    copilot.end_operation(result="success")
"""

import json
import time
import logging
import threading
import queue
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum
from collections import deque

__version__ = "8.1.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-COPILOT")


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATOR SESSION STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════
# Tracks where the human is in the operation lifecycle.
# Transitions are triggered by browser events + timing analysis.

class OperatorPhase(Enum):
    IDLE = "idle"                        # No active operation
    CONFIGURING = "configuring"          # Setting up target/card/proxy
    PRE_FLIGHT = "pre_flight"            # Pre-flight checks running
    BROWSING = "browsing"                # Human is browsing the target site
    WARMING_UP = "warming_up"            # Browsing product pages (building session)
    APPROACHING_CHECKOUT = "approaching" # Moving toward checkout
    CHECKOUT = "checkout"                # On checkout/cart page
    ENTERING_SHIPPING = "shipping"       # Entering shipping details
    ENTERING_PAYMENT = "payment"         # Entering card details
    REVIEWING_ORDER = "reviewing"        # Final order review before submit
    PROCESSING = "processing"            # Payment is being processed
    THREE_DS = "3ds"                     # 3DS challenge active
    ORDER_COMPLETE = "order_complete"    # Order success page
    COMPLETED = "completed"              # Transaction finished (success or fail)


class GuidanceLevel(Enum):
    INFO = "info"           # Informational — no action needed
    SUGGESTION = "suggest"  # AI suggests an action
    WARNING = "warning"     # Something is wrong, operator should fix
    CRITICAL = "critical"   # Stop — will likely fail if operator continues
    TIMING = "timing"       # Timing guidance (wait/go signals)


@dataclass
class GuidanceMessage:
    """A single piece of real-time guidance for the operator."""
    level: GuidanceLevel
    category: str           # e.g., "timing", "warmup", "proxy", "velocity"
    message: str
    action: str = ""        # What the operator should do
    auto_expires_sec: int = 0  # 0 = manual dismiss, >0 = auto-dismiss
    timestamp: float = field(default_factory=time.time)
    source: str = "copilot" # Which module generated this


@dataclass
class OperationContext:
    """Full context for the current operation."""
    target: str = ""
    card_bin: str = ""
    card_country: str = ""
    proxy_ip: str = ""
    proxy_country: str = ""
    proxy_state: str = ""
    billing_state: str = ""
    billing_zip: str = ""
    amount: float = 0.0
    psp: str = "unknown"
    profile_id: str = ""

    # Runtime state (updated by copilot)
    phase: OperatorPhase = OperatorPhase.IDLE
    phase_entered_at: float = 0.0
    pages_visited: int = 0
    session_start: float = 0.0
    antifraud_detected: List[str] = field(default_factory=list)
    three_ds_triggered: bool = False
    checkout_readiness_score: float = 0.0
    ai_go_decision: bool = True
    pre_flight_passed: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# TIMING INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
# Handles all timing that humans are bad at:
# - Precise warmup durations per target type
# - Optimal checkout windows
# - Velocity spacing between operations
# - Time-of-day optimization

class TimingIntelligence:
    """
    AI-powered timing engine. Humans are bad at:
    - Counting exact seconds (rush or wait too long)
    - Maintaining consistent pace (speed up under stress)
    - Timing operations relative to each other (velocity)
    - Knowing optimal time-of-day per target
    """

    # Minimum warmup seconds by target type
    WARMUP_TARGETS = {
        "high_security": 300,    # 5 min: Amazon, PayPal, major banks
        "enterprise_af": 240,    # 4 min: Sites with Forter/Riskified
        "moderate": 120,         # 2 min: Most e-commerce
        "low_friction": 60,      # 1 min: Digital goods, game keys
        "unknown": 180,          # 3 min: Default for unknown targets
    }

    # Known antifraud → minimum session warmup
    ANTIFRAUD_WARMUP = {
        "forter": 300,
        "riskified": 300,
        "sift": 240,
        "signifyd": 240,
        "datadome": 180,
        "perimeterx": 180,
        "akamai": 180,
        "cloudflare": 120,
        "stripe_radar": 120,
        "adyen_risk": 150,
    }

    # Pages needed before checkout looks organic
    MIN_PAGES_BEFORE_CHECKOUT = {
        "high_security": 5,
        "enterprise_af": 4,
        "moderate": 3,
        "low_friction": 2,
        "unknown": 3,
    }

    # Optimal checkout hours (UTC) — when human operators are common
    OPTIMAL_HOURS_UTC = {
        "US": list(range(14, 24)) + list(range(0, 6)),   # 9 AM - 1 AM ET
        "UK": list(range(8, 23)),                          # 8 AM - 11 PM GMT
        "EU": list(range(7, 23)),                          # 8 AM - midnight CET
        "default": list(range(9, 23)),
    }

    def __init__(self):
        self._operation_timestamps: Dict[str, List[float]] = {}  # bin → [timestamps]

    def classify_target(self, target: str, antifraud: List[str] = None) -> str:
        """Classify target by security level."""
        high_sec = ["amazon", "paypal", "ebay", "walmart", "bestbuy", "apple",
                     "target.com", "newegg", "costco"]
        low_friction = ["cdkeys", "g2a", "eneba", "kinguin", "gamivo",
                         "instant-gaming", "steam"]

        domain = target.lower()
        for h in high_sec:
            if h in domain:
                return "high_security"
        for l in low_friction:
            if l in domain:
                return "low_friction"
        if antifraud:
            for af in antifraud:
                if af.lower() in ("forter", "riskified", "sift", "signifyd"):
                    return "enterprise_af"
        return "moderate"

    def get_required_warmup(self, target: str, antifraud: List[str] = None) -> int:
        """Get minimum warmup seconds needed before checkout."""
        target_class = self.classify_target(target, antifraud)
        base_warmup = self.WARMUP_TARGETS.get(target_class, 180)

        # If specific antifraud detected, use the longer warmup
        if antifraud:
            for af in antifraud:
                af_warmup = self.ANTIFRAUD_WARMUP.get(af.lower(), 0)
                base_warmup = max(base_warmup, af_warmup)

        return base_warmup

    def get_required_pages(self, target: str, antifraud: List[str] = None) -> int:
        """Get minimum pages to visit before checkout looks organic."""
        target_class = self.classify_target(target, antifraud)
        return self.MIN_PAGES_BEFORE_CHECKOUT.get(target_class, 3)

    def check_velocity(self, card_bin: str, cooldown_sec: int = 1800) -> Dict:
        """Check if card BIN is safe to use (velocity tracking)."""
        bin6 = card_bin[:6] if card_bin else ""
        if not bin6:
            return {"safe": True, "reason": "No BIN provided"}

        now = time.time()
        timestamps = self._operation_timestamps.get(bin6, [])
        # Clean old entries (>24h)
        timestamps = [t for t in timestamps if now - t < 86400]
        self._operation_timestamps[bin6] = timestamps

        recent_1h = [t for t in timestamps if now - t < 3600]
        recent_30m = [t for t in timestamps if now - t < cooldown_sec]

        if len(recent_1h) >= 3:
            return {
                "safe": False,
                "reason": f"BIN {bin6} has {len(recent_1h)} attempts in last hour (max 3)",
                "wait_seconds": int(3600 - (now - min(recent_1h))),
            }
        if len(recent_30m) >= 1:
            wait = int(cooldown_sec - (now - max(recent_30m)))
            return {
                "safe": False,
                "reason": f"BIN {bin6} used {len(recent_30m)} time(s) in last {cooldown_sec//60}min. Wait {wait}s",
                "wait_seconds": wait,
            }
        return {"safe": True, "reason": "Velocity OK"}

    def record_attempt(self, card_bin: str):
        """Record a checkout attempt for velocity tracking."""
        bin6 = card_bin[:6] if card_bin else ""
        if bin6:
            if bin6 not in self._operation_timestamps:
                self._operation_timestamps[bin6] = []
            self._operation_timestamps[bin6].append(time.time())

    def is_optimal_hour(self, card_country: str = "US") -> Dict:
        """Check if current hour is optimal for the target region."""
        current_utc = datetime.now(timezone.utc).hour
        region = card_country.upper()
        if region in ("US", "CA"):
            region_key = "US"
        elif region in ("GB", "UK"):
            region_key = "UK"
        elif region in ("DE", "FR", "IT", "ES", "NL", "BE", "AT", "PT"):
            region_key = "EU"
        else:
            region_key = "default"

        optimal = self.OPTIMAL_HOURS_UTC.get(region_key, self.OPTIMAL_HOURS_UTC["default"])
        is_good = current_utc in optimal

        return {
            "optimal": is_good,
            "current_utc_hour": current_utc,
            "reason": "Good timing — normal shopping hours" if is_good
                      else "Off-peak hours — higher scrutiny from antifraud systems",
        }

    # HITL Phase Dwell Time Guardrails (seconds)
    # From architectural document §HITL Operational Execution
    # Format: {phase: (min_dwell, optimal_min, optimal_max, max_dwell)}
    PHASE_DWELL_TIMES = {
        OperatorPhase.BROWSING: (30, 45, 90, 180),           # Product Discovery
        OperatorPhase.APPROACHING_CHECKOUT: (5, 8, 15, 30),  # Cart Addition
        OperatorPhase.CHECKOUT: (10, 20, 40, 60),            # Cart Review
        OperatorPhase.ENTERING_SHIPPING: (15, 30, 60, 120),  # Shipping Entry
        OperatorPhase.ENTERING_PAYMENT: (20, 45, 90, 180),   # Payment Entry
        OperatorPhase.REVIEWING_ORDER: (10, 20, 45, 90),     # Final Review
        OperatorPhase.ORDER_COMPLETE: (5, 10, 20, 60),       # Order Success page
    }

    def check_phase_dwell(self, phase: 'OperatorPhase', dwell_seconds: float) -> Dict:
        """
        Validate operator dwell time against HITL guardrails.
        Returns timing assessment with warnings if too fast or too slow.
        """
        bounds = self.PHASE_DWELL_TIMES.get(phase)
        if not bounds:
            return {"ok": True, "phase": phase.value, "message": "No timing constraints"}

        min_dwell, opt_min, opt_max, max_dwell = bounds
        result = {
            "phase": phase.value,
            "dwell_sec": round(dwell_seconds, 1),
            "min": min_dwell, "optimal_min": opt_min,
            "optimal_max": opt_max, "max": max_dwell,
        }

        if dwell_seconds < min_dwell:
            result["ok"] = False
            result["severity"] = "critical"
            result["message"] = (
                f"TOO FAST — {phase.value} completed in {dwell_seconds:.0f}s "
                f"(minimum {min_dwell}s). This triggers bot heuristics."
            )
        elif dwell_seconds < opt_min:
            result["ok"] = True
            result["severity"] = "warning"
            result["message"] = (
                f"Slightly fast — {phase.value} at {dwell_seconds:.0f}s "
                f"(optimal {opt_min}-{opt_max}s). Slow down slightly."
            )
        elif dwell_seconds > max_dwell:
            result["ok"] = True
            result["severity"] = "warning"
            result["message"] = (
                f"Slow — {phase.value} at {dwell_seconds:.0f}s "
                f"(max {max_dwell}s). May trigger abandoned cart detection."
            )
        elif opt_min <= dwell_seconds <= opt_max:
            result["ok"] = True
            result["severity"] = "good"
            result["message"] = f"Perfect timing — {phase.value} at {dwell_seconds:.0f}s"
        else:
            result["ok"] = True
            result["severity"] = "info"
            result["message"] = f"Acceptable — {phase.value} at {dwell_seconds:.0f}s"

        return result

    def get_checkout_countdown(self, session_start: float, pages_visited: int,
                                target: str, antifraud: List[str] = None) -> Dict:
        """
        Real-time countdown to checkout readiness.
        Returns seconds remaining and readiness percentage.
        """
        elapsed = time.time() - session_start if session_start > 0 else 0
        required_warmup = self.get_required_warmup(target, antifraud)
        required_pages = self.get_required_pages(target, antifraud)

        time_pct = min(100, (elapsed / required_warmup) * 100) if required_warmup > 0 else 100
        page_pct = min(100, (pages_visited / required_pages) * 100) if required_pages > 0 else 100
        overall_pct = (time_pct * 0.6 + page_pct * 0.4)  # Time weighted more

        remaining = max(0, required_warmup - elapsed)

        return {
            "ready": overall_pct >= 100,
            "readiness_pct": round(overall_pct, 1),
            "seconds_remaining": int(remaining),
            "time_pct": round(time_pct, 1),
            "pages_pct": round(page_pct, 1),
            "elapsed_sec": int(elapsed),
            "required_warmup_sec": required_warmup,
            "pages_visited": pages_visited,
            "pages_needed": required_pages,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MISTAKE DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
# Catches operator errors BEFORE they cause a decline.

class MistakeDetector:
    """
    Watches operator behavior and catches common mistakes:
    - Going to checkout too early
    - Wrong geo match (proxy vs card vs billing)
    - Using a burned/exhausted card
    - Exceeding velocity limits
    - Skipping warmup pages
    - Attempting during off-peak hours
    """

    def __init__(self, timing: TimingIntelligence):
        self._timing = timing
        self._burned_bins: set = set()
        self._failed_targets: Dict[str, int] = {}  # domain → consecutive fails

    def mark_bin_burned(self, card_bin: str):
        """Mark a BIN as burned (from decline analysis)."""
        if card_bin:
            self._burned_bins.add(card_bin[:6])

    def record_target_result(self, target: str, success: bool):
        """Track consecutive failures per target."""
        if success:
            self._failed_targets.pop(target, None)
        else:
            self._failed_targets[target] = self._failed_targets.get(target, 0) + 1

    def check_all(self, ctx: OperationContext) -> List[GuidanceMessage]:
        """Run all mistake checks against current operation context."""
        mistakes = []

        # 1. Burned card check
        if ctx.card_bin and ctx.card_bin[:6] in self._burned_bins:
            mistakes.append(GuidanceMessage(
                level=GuidanceLevel.CRITICAL,
                category="card",
                message=f"BIN {ctx.card_bin[:6]} was previously marked BURNED",
                action="Switch to a different card immediately. This BIN will decline.",
            ))

        # 2. Geo mismatch
        if ctx.proxy_country and ctx.card_country:
            if ctx.proxy_country.upper() != ctx.card_country.upper():
                mistakes.append(GuidanceMessage(
                    level=GuidanceLevel.CRITICAL,
                    category="geo",
                    message=f"Proxy country ({ctx.proxy_country}) != card country ({ctx.card_country})",
                    action=f"Switch to a {ctx.card_country} proxy before proceeding.",
                ))
        if ctx.proxy_state and ctx.billing_state:
            if ctx.proxy_state.upper() != ctx.billing_state.upper():
                mistakes.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="geo",
                    message=f"Proxy state ({ctx.proxy_state}) != billing state ({ctx.billing_state})",
                    action=f"Best to use a {ctx.billing_state} proxy for state-level match.",
                ))

        # 3. Velocity check
        velocity = self._timing.check_velocity(ctx.card_bin)
        if not velocity["safe"]:
            mistakes.append(GuidanceMessage(
                level=GuidanceLevel.CRITICAL,
                category="velocity",
                message=velocity["reason"],
                action=f"Wait {velocity.get('wait_seconds', 0)} seconds or use a different card.",
            ))

        # 4. Checkout too early
        if ctx.phase in (OperatorPhase.CHECKOUT, OperatorPhase.ENTERING_PAYMENT,
                         OperatorPhase.APPROACHING_CHECKOUT):
            countdown = self._timing.get_checkout_countdown(
                ctx.session_start, ctx.pages_visited,
                ctx.target, ctx.antifraud_detected
            )
            if not countdown["ready"]:
                remaining = countdown["seconds_remaining"]
                pages_needed = countdown["pages_needed"] - ctx.pages_visited
                msg_parts = []
                if remaining > 0:
                    msg_parts.append(f"Wait {remaining}s more")
                if pages_needed > 0:
                    msg_parts.append(f"visit {pages_needed} more page(s)")
                mistakes.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="warmup",
                    message=f"Checkout readiness: {countdown['readiness_pct']}% — too early!",
                    action=" and ".join(msg_parts) + " before checkout.",
                ))

        # 5. Target with repeated failures
        if ctx.target:
            fails = self._failed_targets.get(ctx.target, 0)
            if fails >= 3:
                mistakes.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="target",
                    message=f"Target {ctx.target} has {fails} consecutive failures",
                    action="Consider switching to a different target. This one may be blocking your setup.",
                ))

        # 6. Time-of-day check
        hour_check = self._timing.is_optimal_hour(ctx.card_country)
        if not hour_check["optimal"]:
            mistakes.append(GuidanceMessage(
                level=GuidanceLevel.INFO,
                category="timing",
                message=hour_check["reason"],
                action="Consider waiting for peak shopping hours for better success rate.",
                auto_expires_sec=60,
            ))

        return mistakes


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA REAL-TIME ADVISOR
# ═══════════════════════════════════════════════════════════════════════════════
# Uses local Ollama for complex reasoning that rules can't handle.

class OllamaRealtimeAdvisor:
    """
    Consults Ollama for complex situational reasoning.
    Only called when rule-based checks aren't enough:
    - Ambiguous decline codes
    - Complex geo/velocity/timing combinations
    - Target-specific strategy
    - Mid-session tactical adjustments
    """

    def __init__(self):
        self._available = False
        self._model = "mistral:7b-instruct-v0.2-q4_0"
        self._url = "http://127.0.0.1:11434"
        self._last_query_time = 0
        self._min_query_interval = 5.0  # Don't spam Ollama
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama is running."""
        try:
            import urllib.request
            req = urllib.request.Request(f"{self._url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                self._available = "models" in data
                if self._available:
                    # Find best available model
                    models = [m.get("name", "") for m in data.get("models", [])]
                    for preferred in ["mistral:7b-instruct-v0.2-q4_0", "mistral",
                                       "llama3:8b", "deepseek-r1:7b", "qwen2.5:7b"]:
                        for m in models:
                            if preferred in m:
                                self._model = m
                                break
                        if self._model != "mistral:7b-instruct-v0.2-q4_0":
                            break
                    logger.info(f"Ollama available: model={self._model}")
        except Exception:
            self._available = False
            logger.info("Ollama not available — co-pilot using rule-based mode only")

    @property
    def is_available(self) -> bool:
        return self._available

    def _query(self, prompt: str, max_tokens: int = 250, temperature: float = 0.3) -> str:
        """Query Ollama with rate limiting."""
        if not self._available:
            return ""
        now = time.time()
        if now - self._last_query_time < self._min_query_interval:
            return ""

        self._last_query_time = now
        try:
            import urllib.request
            payload = json.dumps({
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature}
            }).encode()
            req = urllib.request.Request(
                f"{self._url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get("response", "").strip()
        except Exception as e:
            logger.debug(f"Ollama query failed: {e}")
            return ""

    def analyze_situation(self, ctx: OperationContext,
                          recent_events: List[Dict]) -> Optional[GuidanceMessage]:
        """
        Ask Ollama to analyze the current situation and provide tactical advice.
        Called sparingly — only at key decision points.
        """
        if not self._available:
            return None

        elapsed = int(time.time() - ctx.session_start) if ctx.session_start > 0 else 0
        events_summary = ", ".join([
            f"{e.get('event', '?')}@{int(e.get('timestamp', 0) - ctx.session_start)}s"
            for e in recent_events[-5:]
        ]) if recent_events else "none"

        prompt = (
            f"You are a real-time transaction advisor. The operator is at phase '{ctx.phase.value}'. "
            f"Analyze and give ONE specific tactical instruction (max 2 sentences).\n\n"
            f"Target: {ctx.target} | PSP: {ctx.psp}\n"
            f"Card: BIN {ctx.card_bin[:6] if ctx.card_bin else '?'}, {ctx.card_country}\n"
            f"Proxy: {ctx.proxy_country}/{ctx.proxy_state}\n"
            f"Amount: ${ctx.amount:.2f}\n"
            f"Session: {elapsed}s elapsed, {ctx.pages_visited} pages\n"
            f"Antifraud: {', '.join(ctx.antifraud_detected) if ctx.antifraud_detected else 'none detected'}\n"
            f"Recent events: {events_summary}\n\n"
            f"Give the single most important thing to do RIGHT NOW. Be concrete."
        )

        response = self._query(prompt)
        if response:
            return GuidanceMessage(
                level=GuidanceLevel.SUGGESTION,
                category="ai_advisor",
                message=response,
                source="ollama",
                auto_expires_sec=30,
            )
        return None

    def analyze_decline(self, ctx: OperationContext,
                         decline_code: str) -> Optional[GuidanceMessage]:
        """Ask Ollama to deeply analyze a decline and recommend next action."""
        if not self._available:
            return None

        prompt = (
            f"Transaction DECLINED on {ctx.target} (PSP: {ctx.psp}).\n"
            f"Decline code: {decline_code}\n"
            f"Card: BIN {ctx.card_bin[:6] if ctx.card_bin else '?'}, {ctx.card_country}\n"
            f"Amount: ${ctx.amount:.2f}\n"
            f"Session was: {int(time.time() - ctx.session_start)}s, {ctx.pages_visited} pages\n\n"
            f"In 2 sentences: (1) Is the card burned or retriable? "
            f"(2) What should the operator do next — specific action."
        )

        response = self._query(prompt, max_tokens=150)
        if response:
            return GuidanceMessage(
                level=GuidanceLevel.WARNING,
                category="decline_analysis",
                message=response,
                source="ollama",
            )
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# REAL-TIME CO-PILOT DAEMON
# ═══════════════════════════════════════════════════════════════════════════════
# The main daemon that ties everything together.

class RealtimeCopilot:
    """
    Real-time AI co-pilot that silently monitors and assists the human operator.

    Lifecycle:
        1. copilot.start() — starts background monitoring thread
        2. copilot.begin_operation(target, card, proxy, ...) — starts tracking
        3. Browser events flow in via ingest_browser_event()
        4. Copilot continuously analyzes and pushes guidance
        5. copilot.end_operation(result) — logs result, learns
        6. copilot.stop() — stops background thread

    Guidance is available via:
        - get_latest_guidance() — returns list of GuidanceMessage
        - get_dashboard() — returns full copilot status dict
        - API route: GET /api/copilot/guidance (polled by GUI)
    """

    def __init__(self):
        self._timing = TimingIntelligence()
        self._mistakes = MistakeDetector(self._timing)
        self._ollama = OllamaRealtimeAdvisor()

        # Current operation context
        self._ctx = OperationContext()
        self._active = False

        # Event and guidance queues
        self._event_queue: queue.Queue = queue.Queue(maxsize=500)
        self._recent_events: deque = deque(maxlen=100)
        self._guidance: deque = deque(maxlen=50)
        self._guidance_lock = threading.Lock()

        # Background monitoring
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._monitor_interval = 5.0  # Check every 5 seconds

        # Cross-session learning
        self._session_history: List[Dict] = []
        self._history_file = Path("/opt/titan/data/copilot_history.jsonl")

        # Integration handles (lazy-loaded)
        self._guard = None
        self._intel_engine = None

        logger.info("RealtimeCopilot initialized (Ollama: %s)", self._ollama.is_available)

    # ─── LIFECYCLE ────────────────────────────────────────────────────────

    def start(self):
        """Start the background monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="CopilotMonitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("Real-time co-pilot monitoring started")

    def stop(self):
        """Stop background monitoring."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Real-time co-pilot stopped")

    def begin_operation(self, target: str, card_bin: str = "",
                        card_country: str = "US", proxy_ip: str = "",
                        proxy_country: str = "", proxy_state: str = "",
                        billing_state: str = "", billing_zip: str = "",
                        amount: float = 0.0, psp: str = "unknown",
                        profile_id: str = "") -> List[GuidanceMessage]:
        """
        Start tracking a new operation.
        Runs pre-flight checks and returns initial guidance.
        """
        self._ctx = OperationContext(
            target=target, card_bin=card_bin, card_country=card_country,
            proxy_ip=proxy_ip, proxy_country=proxy_country,
            proxy_state=proxy_state, billing_state=billing_state,
            billing_zip=billing_zip, amount=amount, psp=psp,
            profile_id=profile_id,
            phase=OperatorPhase.PRE_FLIGHT,
            phase_entered_at=time.time(),
            session_start=time.time(),
        )
        self._active = True
        self._recent_events.clear()

        logger.info(f"Operation started: {target} | BIN:{card_bin[:6] if card_bin else '?'} | ${amount}")

        # Run pre-flight checks
        guidance = []

        # 1. Mistake detection (geo, velocity, burned cards)
        mistakes = self._mistakes.check_all(self._ctx)
        guidance.extend(mistakes)

        # 2. Timing checks
        hour_check = self._timing.is_optimal_hour(card_country)
        if not hour_check["optimal"]:
            guidance.append(GuidanceMessage(
                level=GuidanceLevel.INFO,
                category="timing",
                message=hour_check["reason"],
                auto_expires_sec=120,
            ))

        # 3. Warmup requirements
        warmup = self._timing.get_required_warmup(target)
        pages = self._timing.get_required_pages(target)
        guidance.append(GuidanceMessage(
            level=GuidanceLevel.INFO,
            category="warmup",
            message=f"Target requires {warmup}s warmup + {pages} pages before checkout",
            auto_expires_sec=warmup,
        ))

        # 4. Operations Guard pre-flight (if available)
        guard_verdict = self._run_guard_pre_check()
        if guard_verdict:
            for issue in guard_verdict.get("issues", []):
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING if issue.get("severity") == "warning"
                          else GuidanceLevel.CRITICAL,
                    category="guard",
                    message=issue.get("message", ""),
                    action=issue.get("fix", ""),
                    source="operations_guard",
                ))
            for rec in guard_verdict.get("recommendations", []):
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.INFO,
                    category="guard",
                    message=rec,
                    source="operations_guard",
                    auto_expires_sec=60,
                ))

        # 5. AI analysis (if complex setup)
        critical_count = sum(1 for g in guidance if g.level == GuidanceLevel.CRITICAL)
        if self._ollama.is_available and (critical_count > 0 or amount > 200):
            ai_advice = self._ollama.analyze_situation(self._ctx, [])
            if ai_advice:
                guidance.append(ai_advice)

        # 6. BIN intelligence (if available)
        bin_guidance = self._get_bin_intelligence()
        if bin_guidance:
            guidance.extend(bin_guidance)

        # Store pre-flight result
        self._ctx.pre_flight_passed = critical_count == 0
        self._ctx.ai_go_decision = critical_count == 0

        # Push all guidance
        with self._guidance_lock:
            for g in guidance:
                self._guidance.append(g)

        # Transition to browsing phase
        if self._ctx.pre_flight_passed:
            self._transition_phase(OperatorPhase.BROWSING)

        return guidance

    def end_operation(self, result: str, decline_code: str = "") -> List[GuidanceMessage]:
        """
        End the current operation. Analyzes result and learns.
        """
        guidance = []

        if not self._active:
            return guidance

        self._transition_phase(OperatorPhase.COMPLETED)
        elapsed = int(time.time() - self._ctx.session_start)

        is_success = result.lower() in ("success", "approved", "succeeded")
        is_decline = result.lower() in ("declined", "failed", "decline")

        # Record velocity
        if is_decline or is_success:
            self._timing.record_attempt(self._ctx.card_bin)

        # Decline analysis
        if is_decline:
            # Mark burned cards
            burned_codes = {"fraudulent", "pickup_card", "lost_card", "do_not_try_again",
                            "restricted_card", "stolen_card", "expired_card", "invalid_card"}
            if decline_code.lower().replace(" ", "_").replace("-", "_") in burned_codes:
                self._mistakes.mark_bin_burned(self._ctx.card_bin)
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.CRITICAL,
                    category="card",
                    message=f"Card BIN {self._ctx.card_bin[:6]} is BURNED ({decline_code})",
                    action="Do NOT retry this card. Switch to a different card.",
                ))
            else:
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="decline",
                    message=f"Declined: {decline_code}. Card may be retriable.",
                    action="Wait 30+ minutes then try a different target.",
                ))

            # Track target failures
            self._mistakes.record_target_result(self._ctx.target, False)

            # AI decline analysis
            ai_decline = self._ollama.analyze_decline(self._ctx, decline_code)
            if ai_decline:
                guidance.append(ai_decline)

            # Suggest next target
            next_target = self._suggest_next_target()
            if next_target:
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.SUGGESTION,
                    category="next_action",
                    message=f"Suggested next target: {next_target}",
                    source="target_intel",
                ))

        elif is_success:
            self._mistakes.record_target_result(self._ctx.target, True)
            guidance.append(GuidanceMessage(
                level=GuidanceLevel.INFO,
                category="success",
                message=f"SUCCESS on {self._ctx.target} (${self._ctx.amount:.2f}) in {elapsed}s. "
                        f"Logged for future reference.",
            ))

        # Run post-op guard analysis
        guard_post = self._run_guard_post_check(result, decline_code)
        if guard_post:
            for rec in guard_post.get("recommendations", []):
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.INFO,
                    category="post_analysis",
                    message=rec,
                    source="operations_guard",
                ))

        # Persist to history
        self._save_operation_result(result, decline_code, elapsed)

        # Store in vector memory
        self._store_in_vector_memory(result, decline_code)

        # Push guidance
        with self._guidance_lock:
            for g in guidance:
                self._guidance.append(g)

        self._active = False
        return guidance

    # ─── BROWSER EVENT PROCESSING ─────────────────────────────────────────

    def ingest_browser_event(self, event: Dict):
        """
        Process a real-time event from the browser co-pilot script.
        Events arrive via POST /api/copilot/event from sendBeacon.
        """
        try:
            self._event_queue.put_nowait(event)
        except queue.Full:
            pass  # Drop old events if queue is full

    def _process_browser_event(self, event: Dict):
        """Process a single browser event and generate guidance."""
        event_type = event.get("event", "")
        event["_processed_at"] = time.time()
        self._recent_events.append(event)

        guidance = []

        if event_type == "state_change":
            new_state = event.get("data", {}).get("to", "")
            self._handle_browser_state_change(new_state, event, guidance)

        elif event_type == "checkout_detected":
            psp = event.get("psp", "unknown")
            if psp != "unknown":
                self._ctx.psp = psp
            self._transition_phase(OperatorPhase.CHECKOUT)

            # Check if ready for checkout
            countdown = self._timing.get_checkout_countdown(
                self._ctx.session_start, self._ctx.pages_visited,
                self._ctx.target, self._ctx.antifraud_detected
            )
            if not countdown["ready"]:
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="timing",
                    message=f"Checkout detected but session only {countdown['readiness_pct']}% ready",
                    action=f"Ideally browse {countdown['seconds_remaining']}s more and visit "
                           f"{max(0, countdown['pages_needed'] - self._ctx.pages_visited)} more pages",
                ))
            else:
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.TIMING,
                    category="timing",
                    message=f"Session is {countdown['readiness_pct']}% ready. Clear to checkout.",
                    auto_expires_sec=30,
                ))

        elif event_type == "payment_active":
            self._transition_phase(OperatorPhase.ENTERING_PAYMENT)
            guidance.append(GuidanceMessage(
                level=GuidanceLevel.INFO,
                category="payment",
                message="Payment form detected. AI monitoring at maximum alertness.",
                auto_expires_sec=10,
            ))

        elif event_type == "3ds_detected":
            self._ctx.three_ds_triggered = True
            self._transition_phase(OperatorPhase.THREE_DS)
            blocked = event.get("data", {}).get("blocked", 0)
            guidance.append(GuidanceMessage(
                level=GuidanceLevel.WARNING,
                category="3ds",
                message=f"3DS challenge detected (blocked: {blocked}). AI shield active.",
                action="Wait for AI co-pilot to handle. Do not interact with 3DS iframe.",
            ))

        elif event_type == "transaction_complete":
            self._transition_phase(OperatorPhase.COMPLETED)

        elif event_type == "page_visit":
            self._ctx.pages_visited += 1
            url = event.get("url", "")
            logger.debug(f"Page visit #{self._ctx.pages_visited}: {url}")

        elif event_type == "antifraud_detected":
            af_name = event.get("data", {}).get("name", "")
            if af_name and af_name not in self._ctx.antifraud_detected:
                self._ctx.antifraud_detected.append(af_name)
                warmup = self._timing.ANTIFRAUD_WARMUP.get(af_name.lower(), 0)
                if warmup > 0:
                    guidance.append(GuidanceMessage(
                        level=GuidanceLevel.WARNING,
                        category="antifraud",
                        message=f"Antifraud '{af_name}' detected. Requires {warmup}s warmup.",
                        action=f"Browse naturally for at least {warmup}s before checkout.",
                    ))

        # Audit-13: Clipboard paste detection — instant form fill is a red flag
        elif event_type == "clipboard_paste":
            field = event.get("data", {}).get("field", "unknown")
            guidance.append(GuidanceMessage(
                level=GuidanceLevel.CRITICAL,
                category="behavioral",
                message=f"Clipboard PASTE detected on '{field}' — instant form fill triggers bot detection",
                action="DELETE the pasted content and TYPE it manually with natural cadence. "
                       "Allow minor typos and backspace corrections for realism.",
            ))

        # Audit-14: Scroll behavior — no scroll before checkout = bot indicator
        elif event_type == "scroll":
            if not hasattr(self._ctx, '_has_scrolled'):
                self._ctx._has_scrolled = True

        # Audit-12: Total checkout time guard — completing entire checkout in <2min is a red flag
        if (self._ctx.phase in (OperatorPhase.CHECKOUT, OperatorPhase.ENTERING_PAYMENT,
                                 OperatorPhase.REVIEWING_ORDER)
                and self._ctx.session_start > 0):
            total_elapsed = time.time() - self._ctx.session_start
            if total_elapsed < 120:
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="timing",
                    message=f"Total session time is only {int(total_elapsed)}s — "
                            f"completing checkout in under 2 minutes guarantees detection.",
                    action=f"Wait {int(120 - total_elapsed)}s more. Browse or review items.",
                    auto_expires_sec=30,
                ))

            # Check scroll behavior when entering checkout
            if not getattr(self._ctx, '_has_scrolled', False):
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="behavioral",
                    message="No scroll activity detected before checkout — zero scroll = bot indicator",
                    action="Scroll through product pages naturally using the mouse wheel.",
                    auto_expires_sec=60,
                ))

        # Push any generated guidance
        if guidance:
            with self._guidance_lock:
                for g in guidance:
                    self._guidance.append(g)

    def _handle_browser_state_change(self, new_state: str, event: Dict,
                                       guidance: List[GuidanceMessage]):
        """Handle browser co-pilot state transitions."""
        state_map = {
            "watching": OperatorPhase.BROWSING,
            "checkout": OperatorPhase.CHECKOUT,
            "payment": OperatorPhase.ENTERING_PAYMENT,
            "3ds": OperatorPhase.THREE_DS,
            "complete": OperatorPhase.COMPLETED,
            "dormant": OperatorPhase.BROWSING,
        }
        phase = state_map.get(new_state)
        if phase:
            self._transition_phase(phase)

    def _transition_phase(self, new_phase: OperatorPhase):
        """Transition the operator session state machine."""
        old_phase = self._ctx.phase
        if old_phase == new_phase:
            return

        # HITL dwell time validation on the phase we're leaving
        if self._ctx.phase_entered_at > 0:
            dwell = time.time() - self._ctx.phase_entered_at
            dwell_check = self._timing.check_phase_dwell(old_phase, dwell)
            if dwell_check.get("severity") in ("critical", "warning"):
                with self._guidance_lock:
                    level = GuidanceLevel.CRITICAL if dwell_check["severity"] == "critical" else GuidanceLevel.WARNING
                    self._guidance.append(GuidanceMessage(
                        level=level,
                        category="timing",
                        message=dwell_check["message"],
                        action="Adjust pace to match natural human behavior.",
                        source="timing_intelligence",
                    ))

        self._ctx.phase = new_phase
        self._ctx.phase_entered_at = time.time()
        logger.info(f"Operator phase: {old_phase.value} -> {new_phase.value}")

    # ─── BACKGROUND MONITORING LOOP ───────────────────────────────────────

    def _monitoring_loop(self):
        """
        Background thread that continuously monitors the operation.
        Runs every N seconds while an operation is active.
        """
        while not self._stop_event.is_set():
            try:
                # Process queued browser events
                while not self._event_queue.empty():
                    try:
                        event = self._event_queue.get_nowait()
                        self._process_browser_event(event)
                    except queue.Empty:
                        break

                # Run continuous checks if operation is active
                if self._active:
                    self._run_continuous_checks()

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            self._stop_event.wait(self._monitor_interval)

    def _run_continuous_checks(self):
        """Periodic checks during an active operation."""
        guidance = []

        # 1. Update checkout readiness countdown
        if self._ctx.phase in (OperatorPhase.BROWSING, OperatorPhase.WARMING_UP):
            countdown = self._timing.get_checkout_countdown(
                self._ctx.session_start, self._ctx.pages_visited,
                self._ctx.target, self._ctx.antifraud_detected
            )
            self._ctx.checkout_readiness_score = countdown["readiness_pct"]

            # Push timing update when checkout becomes ready
            if countdown["ready"] and self._ctx.checkout_readiness_score >= 100:
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.TIMING,
                    category="timing",
                    message="Session is warmed up. You are clear to proceed to checkout.",
                    auto_expires_sec=60,
                ))

        # 2. Check for mistakes at current phase
        mistakes = self._mistakes.check_all(self._ctx)
        # Only push new critical/warning mistakes (avoid repeating info)
        for m in mistakes:
            if m.level in (GuidanceLevel.CRITICAL, GuidanceLevel.WARNING):
                guidance.append(m)

        # 3. Session duration warnings
        if self._ctx.session_start > 0:
            elapsed = time.time() - self._ctx.session_start
            if elapsed > 1800 and self._ctx.phase not in (
                OperatorPhase.COMPLETED, OperatorPhase.IDLE
            ):
                guidance.append(GuidanceMessage(
                    level=GuidanceLevel.WARNING,
                    category="session",
                    message=f"Session is {int(elapsed/60)}min. Very long sessions look suspicious.",
                    action="Finish checkout soon or restart with a fresh session.",
                    auto_expires_sec=120,
                ))

        # 4. Proxy health check (if available)
        proxy_guidance = self._check_proxy_health()
        if proxy_guidance:
            guidance.append(proxy_guidance)

        # 5. AI situational analysis (called sparingly)
        if (self._ollama.is_available and
            self._ctx.phase in (OperatorPhase.CHECKOUT, OperatorPhase.ENTERING_PAYMENT) and
            time.time() - self._ollama._last_query_time > 30):
            ai_advice = self._ollama.analyze_situation(
                self._ctx, list(self._recent_events)
            )
            if ai_advice:
                guidance.append(ai_advice)

        # Push guidance
        if guidance:
            with self._guidance_lock:
                for g in guidance:
                    self._guidance.append(g)

    # ─── INTEGRATION WITH EXISTING MODULES ────────────────────────────────

    def _get_guard(self):
        """Lazy-load the operations guard."""
        if self._guard is None:
            try:
                from titan_ai_operations_guard import get_operations_guard
                self._guard = get_operations_guard()
            except ImportError:
                pass
        return self._guard

    def _run_guard_pre_check(self) -> Optional[Dict]:
        """Run the operations guard pre-flight check."""
        guard = self._get_guard()
        if not guard:
            return None
        try:
            verdict = guard.pre_operation_check(
                target=self._ctx.target,
                card_bin=self._ctx.card_bin,
                card_country=self._ctx.card_country,
                proxy_ip=self._ctx.proxy_ip,
                proxy_country=self._ctx.proxy_country,
                proxy_state=self._ctx.proxy_state,
                billing_state=self._ctx.billing_state,
                billing_zip=self._ctx.billing_zip,
                amount=self._ctx.amount,
            )
            return {
                "risk_level": verdict.risk_level.value,
                "proceed": verdict.proceed,
                "issues": verdict.issues,
                "recommendations": verdict.recommendations,
                "ai_reasoning": verdict.ai_reasoning,
                "confidence": verdict.confidence,
            }
        except Exception as e:
            logger.debug(f"Guard pre-check failed: {e}")
            return None

    def _run_guard_post_check(self, result: str, decline_code: str) -> Optional[Dict]:
        """Run the operations guard post-operation analysis."""
        guard = self._get_guard()
        if not guard:
            return None
        try:
            verdict = guard.post_operation_analysis(
                target=self._ctx.target,
                result=result,
                decline_code=decline_code,
                card_bin=self._ctx.card_bin,
                amount=self._ctx.amount,
                psp=self._ctx.psp,
                three_ds_triggered=self._ctx.three_ds_triggered,
            )
            return {
                "risk_level": verdict.risk_level.value,
                "issues": verdict.issues,
                "recommendations": verdict.recommendations,
            }
        except Exception as e:
            logger.debug(f"Guard post-check failed: {e}")
            return None

    def _get_bin_intelligence(self) -> List[GuidanceMessage]:
        """Get AI BIN intelligence for the current card."""
        guidance = []
        if not self._ctx.card_bin:
            return guidance
        try:
            from ai_intelligence_engine import analyze_bin
            analysis = analyze_bin(
                self._ctx.card_bin,
                target=self._ctx.target,
                amount=self._ctx.amount,
            )
            if analysis and analysis.ai_powered:
                if analysis.success_prediction < 0.3:
                    guidance.append(GuidanceMessage(
                        level=GuidanceLevel.WARNING,
                        category="bin_intel",
                        message=f"BIN {self._ctx.card_bin[:6]}: Low success prediction "
                                f"({analysis.success_prediction:.0%}). {analysis.strategic_notes}",
                        action="Consider using a different card with higher success prediction.",
                    ))
                elif analysis.timing_advice:
                    guidance.append(GuidanceMessage(
                        level=GuidanceLevel.INFO,
                        category="bin_intel",
                        message=f"BIN intel: {analysis.timing_advice}",
                        auto_expires_sec=60,
                    ))
        except Exception as e:
            logger.debug(f"BIN intelligence failed: {e}")
        return guidance

    def _check_proxy_health(self) -> Optional[GuidanceMessage]:
        """Check current proxy health."""
        try:
            from proxy_manager import get_residential_proxy_manager
            mgr = get_residential_proxy_manager()
            if mgr and self._ctx.proxy_ip:
                # Check if proxy is still healthy
                for proxy in mgr.pool:
                    if proxy.host == self._ctx.proxy_ip:
                        if hasattr(proxy, 'status') and str(proxy.status) == "ProxyStatus.DEAD":
                            return GuidanceMessage(
                                level=GuidanceLevel.CRITICAL,
                                category="proxy",
                                message="Current proxy is DEAD. Session will fail.",
                                action="Rotate to a healthy proxy immediately.",
                            )
                        break
        except Exception:
            pass
        return None

    def _suggest_next_target(self) -> Optional[str]:
        """Suggest the next target based on intelligence."""
        try:
            from titan_target_intel_v2 import get_target_intel_v2
            intel = get_target_intel_v2()
            golden = intel.find_golden_targets(
                card_country=self._ctx.card_country,
                max_amount=self._ctx.amount,
                min_score=75,
            )
            if golden:
                # Skip current target
                for t in golden:
                    if t.get("domain", "") != self._ctx.target:
                        return f"{t['domain']} (score: {t.get('golden_path_score', 0)}/100)"
        except Exception:
            pass
        return None

    def _store_in_vector_memory(self, result: str, decline_code: str):
        """Store operation result in vector memory for cross-session learning."""
        try:
            from titan_vector_memory import get_vector_memory
            vm = get_vector_memory()
            if vm:
                elapsed = int(time.time() - self._ctx.session_start)
                status = "SUCCESS" if result.lower() in ("success", "approved") else "DECLINE"
                text = (
                    f"{status}: {self._ctx.target} | PSP:{self._ctx.psp} | "
                    f"BIN:{self._ctx.card_bin[:6] if self._ctx.card_bin else '?'} | "
                    f"${self._ctx.amount:.0f} | {elapsed}s | "
                    f"pages:{self._ctx.pages_visited} | "
                    f"3DS:{self._ctx.three_ds_triggered} | "
                    f"decline:{decline_code}"
                )
                vm.store(collection="copilot_operations", text=text, metadata={
                    "target": self._ctx.target,
                    "result": result,
                    "decline_code": decline_code,
                    "amount": self._ctx.amount,
                    "elapsed_sec": elapsed,
                    "pages_visited": self._ctx.pages_visited,
                    "psp": self._ctx.psp,
                })
        except Exception:
            pass

    def _save_operation_result(self, result: str, decline_code: str, elapsed: int):
        """Persist operation result to disk for cross-session learning."""
        record = {
            "target": self._ctx.target,
            "card_bin": self._ctx.card_bin[:6] if self._ctx.card_bin else "",
            "card_country": self._ctx.card_country,
            "proxy_country": self._ctx.proxy_country,
            "amount": self._ctx.amount,
            "psp": self._ctx.psp,
            "result": result,
            "decline_code": decline_code,
            "elapsed_sec": elapsed,
            "pages_visited": self._ctx.pages_visited,
            "three_ds": self._ctx.three_ds_triggered,
            "antifraud": self._ctx.antifraud_detected,
            "phase_at_end": self._ctx.phase.value,
            "timestamp": time.time(),
        }
        self._session_history.append(record)
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.debug(f"History write failed: {e}")

    # ─── PUBLIC QUERY API ─────────────────────────────────────────────────

    def get_latest_guidance(self, limit: int = 10) -> List[Dict]:
        """Get the latest guidance messages (GUI polls this)."""
        with self._guidance_lock:
            now = time.time()
            messages = []
            for g in list(self._guidance)[-limit:]:
                # Skip auto-expired messages
                if g.auto_expires_sec > 0 and (now - g.timestamp) > g.auto_expires_sec:
                    continue
                messages.append({
                    "level": g.level.value,
                    "category": g.category,
                    "message": g.message,
                    "action": g.action,
                    "source": g.source,
                    "age_sec": int(now - g.timestamp),
                })
            return messages

    def get_dashboard(self) -> Dict:
        """Get full copilot status for the GUI dashboard."""
        countdown = {}
        if self._active and self._ctx.session_start > 0:
            countdown = self._timing.get_checkout_countdown(
                self._ctx.session_start, self._ctx.pages_visited,
                self._ctx.target, self._ctx.antifraud_detected,
            )

        velocity = {}
        if self._ctx.card_bin:
            velocity = self._timing.check_velocity(self._ctx.card_bin)

        return {
            "active": self._active,
            "phase": self._ctx.phase.value,
            "target": self._ctx.target,
            "card_bin": self._ctx.card_bin[:6] if self._ctx.card_bin else "",
            "amount": self._ctx.amount,
            "psp": self._ctx.psp,
            "session_elapsed_sec": int(time.time() - self._ctx.session_start)
                                    if self._ctx.session_start > 0 else 0,
            "pages_visited": self._ctx.pages_visited,
            "antifraud_detected": self._ctx.antifraud_detected,
            "three_ds_triggered": self._ctx.three_ds_triggered,
            "checkout_countdown": countdown,
            "velocity": velocity,
            "pre_flight_passed": self._ctx.pre_flight_passed,
            "ai_go_decision": self._ctx.ai_go_decision,
            "ollama_available": self._ollama.is_available,
            "ollama_model": self._ollama._model if self._ollama.is_available else None,
            "guidance_count": len(self._guidance),
            "events_processed": len(self._recent_events),
            "operations_this_session": len(self._session_history),
            "latest_guidance": self.get_latest_guidance(5),
        }

    def get_operation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent operation history."""
        return self._session_history[-limit:]

    def get_timing_status(self) -> Dict:
        """Get current timing intelligence status."""
        if not self._active:
            return {"active": False}
        return {
            "active": True,
            "countdown": self._timing.get_checkout_countdown(
                self._ctx.session_start, self._ctx.pages_visited,
                self._ctx.target, self._ctx.antifraud_detected,
            ),
            "velocity": self._timing.check_velocity(self._ctx.card_bin),
            "optimal_hour": self._timing.is_optimal_hour(self._ctx.card_country),
            "target_class": self._timing.classify_target(
                self._ctx.target, self._ctx.antifraud_detected
            ),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_copilot: Optional[RealtimeCopilot] = None
_copilot_lock = threading.Lock()


def get_realtime_copilot() -> RealtimeCopilot:
    """Get singleton RealtimeCopilot instance."""
    global _copilot
    with _copilot_lock:
        if _copilot is None:
            _copilot = RealtimeCopilot()
    return _copilot


def start_copilot() -> RealtimeCopilot:
    """Get and start the real-time co-pilot."""
    copilot = get_realtime_copilot()
    copilot.start()
    return copilot


def stop_copilot():
    """Stop the real-time co-pilot."""
    if _copilot:
        _copilot.stop()


# Convenience functions for external callers
def begin_op(**kwargs) -> List[Dict]:
    """Begin an operation and get initial guidance."""
    copilot = get_realtime_copilot()
    msgs = copilot.begin_operation(**kwargs)
    return [{"level": m.level.value, "message": m.message, "action": m.action} for m in msgs]


def end_op(**kwargs) -> List[Dict]:
    """End an operation and get final analysis."""
    copilot = get_realtime_copilot()
    msgs = copilot.end_operation(**kwargs)
    return [{"level": m.level.value, "message": m.message, "action": m.action} for m in msgs]


def get_guidance(limit: int = 10) -> List[Dict]:
    """Get latest guidance messages."""
    return get_realtime_copilot().get_latest_guidance(limit)


def get_dashboard() -> Dict:
    """Get full copilot dashboard."""
    return get_realtime_copilot().get_dashboard()
