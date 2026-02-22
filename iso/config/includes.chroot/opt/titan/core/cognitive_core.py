"""
TITAN V7.0 SINGULARITY - Cloud Cognitive Core
Replaces v5.2 Local Ollama with Cloud vLLM Integration

The Cloud Brain provides:
- Sub-200ms inference latency (matching human cognitive speed)
- Multimodal analysis (Vision + Text)
- Zero local resource drain
- PagedAttention for concurrent agent support

Architecture:
- Self-hosted vLLM cluster with OpenAI-compatible API
- AWQ quantized Llama-3-70B or Qwen-2.5-72B
- Tensor parallelism across multiple GPUs
"""

import os
import json
import logging
import random
import asyncio
import base64
import time as _time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Union, Tuple
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════
# R4-FIX: Circuit Breaker — prevents hammering dead LLM endpoints
# ═══════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    R4-FIX: Circuit breaker for cognitive core LLM calls.
    
    States:
        CLOSED  — normal operation, requests pass through
        OPEN    — tripped after N failures, rejects immediately
        HALF    — after cooldown, allows ONE probe request
    
    Prevents:
        - Hammering a dead vLLM/Ollama endpoint
        - Blocking the operation pipeline on network timeouts
        - Silent accumulation of errors without operator awareness
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60,
                 hard_timeout_seconds: float = 15.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.hard_timeout_seconds = hard_timeout_seconds
        self._state = self.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time = 0.0
        self._total_trips = 0
        self._lock = threading.Lock()
        self._logger = logging.getLogger("TITAN-CIRCUIT-BREAKER")
    
    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                # Check if cooldown has elapsed → transition to HALF_OPEN
                if _time.time() - self._last_failure_time > self.cooldown_seconds:
                    self._state = self.HALF_OPEN
                    self._logger.info("[CIRCUIT-BREAKER] OPEN → HALF_OPEN (cooldown elapsed)")
            return self._state
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current = self.state  # triggers cooldown check
        if current == self.CLOSED:
            return True
        if current == self.HALF_OPEN:
            return True  # Allow one probe request
        return False  # OPEN — reject
    
    def record_success(self):
        """Record a successful request — resets the breaker."""
        with self._lock:
            if self._state == self.HALF_OPEN:
                self._logger.info("[CIRCUIT-BREAKER] HALF_OPEN → CLOSED (probe succeeded)")
            self._consecutive_failures = 0
            self._state = self.CLOSED
    
    def record_failure(self):
        """Record a failed request — may trip the breaker."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = _time.time()
            
            if self._state == self.HALF_OPEN:
                # Probe failed — go back to OPEN
                self._state = self.OPEN
                self._logger.warning("[CIRCUIT-BREAKER] HALF_OPEN → OPEN (probe failed)")
            elif self._consecutive_failures >= self.failure_threshold:
                if self._state != self.OPEN:
                    self._state = self.OPEN
                    self._total_trips += 1
                    self._logger.error(
                        f"[CIRCUIT-BREAKER] TRIPPED after {self._consecutive_failures} failures "
                        f"(trip #{self._total_trips}, cooldown={self.cooldown_seconds}s)"
                    )
    
    def get_stats(self) -> Dict:
        """Get circuit breaker statistics."""
        return {
            "state": self.state,
            "consecutive_failures": self._consecutive_failures,
            "total_trips": self._total_trips,
            "cooldown_seconds": self.cooldown_seconds,
            "hard_timeout_seconds": self.hard_timeout_seconds,
        }

# Load titan.env if present (populates os.environ for all TITAN_ vars)
_TITAN_ENV = Path("/opt/titan/config/titan.env")
if _TITAN_ENV.exists():
    for _line in _TITAN_ENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip()
            if _v and not _v.startswith("REPLACE_WITH") and _k not in os.environ:
                os.environ[_k] = _v

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class CognitiveMode(Enum):
    """Cognitive processing modes"""
    ANALYSIS = "analysis"       # DOM/page analysis
    DECISION = "decision"       # Action decision making
    CAPTCHA = "captcha"         # CAPTCHA solving (multimodal)
    RISK = "risk"               # Risk assessment
    CONVERSATION = "conversation"  # Natural language generation


@dataclass
class CognitiveRequest:
    """Request to the Cloud Brain"""
    mode: CognitiveMode
    context: str
    screenshot_b64: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 500
    temperature: float = 0.7


@dataclass
class CognitiveResponse:
    """Response from the Cloud Brain"""
    success: bool
    action: str
    reasoning: str
    confidence: float
    data: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TitanCognitiveCore:
    """
    V6 Cloud Brain Interface.
    Replaces v5.2 Local Ollama Assistant.
    
    Key improvements over v5.2:
    1. Cloud inference via vLLM (PagedAttention, AWQ quantization)
    2. Sub-200ms latency (vs 1500-3000ms local)
    3. Multimodal support (Vision + Text)
    4. 32k context window (vs 4k truncated)
    5. 50+ concurrent agents (vs 1 resource lock)
    
    The cognitive latency injection is CRITICAL:
    - vLLM responds in ~150ms
    - Human cognitive response is 200-300ms
    - We inject random delay to match human timing
    - Responses faster than 150ms are BOT FLAGS
    """
    
    # System prompts for different modes
    SYSTEM_PROMPTS = {
        CognitiveMode.ANALYSIS: """You are TITAN's analytical core. Analyze the provided DOM/page context and identify:
1. Form fields and their purposes
2. Security measures (CAPTCHA, 2FA indicators)
3. Trust signals (SSL, badges, reviews)
4. Risk indicators (velocity limits, fraud warnings)
Respond in JSON format with keys: elements, security, trust_score, risks, recommendations.""",

        CognitiveMode.DECISION: """You are TITAN's decision engine. Based on the context, determine the optimal next action.
Consider: timing, element visibility, page state, previous actions.
Respond in JSON format with keys: action, target_element, wait_ms, confidence, reasoning.""",

        CognitiveMode.CAPTCHA: """You are TITAN's CAPTCHA solver. Analyze the visual CAPTCHA and provide the solution.
For text CAPTCHAs: identify all characters including case and special chars.
For image CAPTCHAs: describe what you see and select matching images.
Respond in JSON format with keys: captcha_type, solution, confidence.""",

        CognitiveMode.RISK: """You are TITAN's risk analyst. Evaluate the transaction/action risk based on:
1. BIN/card data patterns
2. Merchant risk profile
3. Velocity indicators
4. Geographic anomalies
Respond in JSON format with keys: risk_score (0-100), risk_factors, recommendation, proceed.""",

        CognitiveMode.CONVERSATION: """You are a natural human user. Generate realistic, contextual responses for:
- Customer service chats
- Verification questions
- Account recovery flows
Match the tone and style of a typical user. Be concise but natural."""
    }
    
    # Human cognitive latency range (milliseconds)
    HUMAN_LATENCY_MIN = 200
    HUMAN_LATENCY_MAX = 450
    
    def __init__(self, 
                 endpoint_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None):
        """
        Initialize Cloud Brain connection.
        
        Args:
            endpoint_url: vLLM server URL (default from env TITAN_CLOUD_URL)
            api_key: API key (default from env TITAN_API_KEY)
            model: Model name (default from env TITAN_MODEL)
        """
        self.endpoint_url = endpoint_url or os.getenv("TITAN_CLOUD_URL", "")
        self.api_key = api_key or os.getenv("TITAN_API_KEY", "")
        self.model = model or os.getenv(
            "TITAN_MODEL",
            "meta-llama/Meta-Llama-3-70B-Instruct"
        )
        
        self.logger = logging.getLogger("TITAN-V7-BRAIN")
        self.client: Optional[AsyncOpenAI] = None
        self._connected = False
        
        # Statistics
        self.total_requests = 0
        self.total_latency_ms = 0
        self.errors = 0
        
        # R4-FIX: Circuit breaker — trips after 5 consecutive failures, 60s cooldown
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            cooldown_seconds=60,
            hard_timeout_seconds=15.0
        )
        
        self._init_client()
    
    def _init_client(self):
        """Initialize the OpenAI-compatible client"""
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI client not available. Install with: pip install openai")
            return
        
        if not self.endpoint_url or not self.api_key:
            # Try Ollama local fallback before giving up
            ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/v1")
            try:
                import urllib.request
                urllib.request.urlopen(ollama_url.replace("/v1", ""), timeout=2)
                self.endpoint_url = ollama_url
                self.api_key = "ollama"
                self.model = os.getenv("OLLAMA_MODEL", "llama3:8b")
                self.logger.info(f"Cloud Brain not configured — using local Ollama at {ollama_url}")
            except Exception:
                self.logger.warning(
                    "Cloud Brain not configured. Set TITAN_CLOUD_URL and TITAN_API_KEY env vars, "
                    "or start Ollama locally. Using rule-based local fallback."
                )
                self._connected = False
                return
        
        try:
            self.client = AsyncOpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key,
                timeout=10.0,
                max_retries=2
            )
            self._connected = True
            self.logger.info(f"Cloud Brain connected: {self.endpoint_url}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Cloud Brain: {e}")
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self.client is not None
    
    @property
    def average_latency(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.total_latency_ms / self.total_requests
    
    async def process(self, request: CognitiveRequest) -> CognitiveResponse:
        """
        Process a cognitive request through the Cloud Brain.
        
        R4-FIX: Now protected by circuit breaker + hard timeout.
        
        Args:
            request: CognitiveRequest with mode, context, optional screenshot
            
        Returns:
            CognitiveResponse with action, reasoning, confidence
        """
        if not self.is_connected:
            return CognitiveResponse(
                success=False,
                action="hold",
                reasoning="neural_disconnect",
                confidence=0
            )
        
        # R4-FIX: Circuit breaker gate — reject immediately if breaker is OPEN
        if not self._circuit_breaker.allow_request():
            cb_stats = self._circuit_breaker.get_stats()
            self.logger.warning(
                f"[CIRCUIT-BREAKER] Request REJECTED (state={cb_stats['state']}, "
                f"failures={cb_stats['consecutive_failures']}, trips={cb_stats['total_trips']})"
            )
            return CognitiveResponse(
                success=False,
                action="hold",
                reasoning=f"circuit_breaker_open: {cb_stats['consecutive_failures']} consecutive failures, "
                          f"cooldown {cb_stats['cooldown_seconds']}s",
                confidence=0,
                data={"circuit_breaker": cb_stats}
            )
        
        start_time = datetime.now()
        
        try:
            # Build messages
            messages = self._build_messages(request)
            
            # Execute inference via Cloud Brain
            # V7.5 FIX: Only use response_format for models that support it
            create_kwargs = dict(
                model=self.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            if self.api_key != "ollama":
                create_kwargs["response_format"] = {"type": "json_object"}
            
            # R4-FIX: Hard timeout — never wait longer than circuit breaker timeout
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**create_kwargs),
                timeout=self._circuit_breaker.hard_timeout_seconds
            )
            
            # Calculate actual inference latency
            inference_latency = (datetime.now() - start_time).total_seconds() * 1000
            
            # CRITICAL: Enforce Human Cognitive Latency
            # vLLM responds in ~150ms, but humans take 200-450ms
            # We must inject delay to match human timing
            required_delay = random.uniform(
                self.HUMAN_LATENCY_MIN, 
                self.HUMAN_LATENCY_MAX
            ) - inference_latency
            
            # V7.5 FIX: Cap delay to avoid excessive waits
            if 0 < required_delay < 500:
                await asyncio.sleep(required_delay / 1000)
            
            # Parse response
            total_latency = (datetime.now() - start_time).total_seconds() * 1000
            
            content = response.choices[0].message.content
            parsed = json.loads(content) if content else {}
            
            # Update statistics
            self.total_requests += 1
            self.total_latency_ms += total_latency
            
            # R4-FIX: Record success — resets circuit breaker
            self._circuit_breaker.record_success()
            
            return CognitiveResponse(
                success=True,
                action=parsed.get("action", "proceed"),
                reasoning=parsed.get("reasoning", parsed.get("reason", "")),
                confidence=parsed.get("confidence", 0.8),
                data=parsed,
                latency_ms=total_latency
            )
            
        except asyncio.TimeoutError:
            self.errors += 1
            self._circuit_breaker.record_failure()
            timeout_s = self._circuit_breaker.hard_timeout_seconds
            self.logger.error(f"[R4] Hard timeout ({timeout_s}s) exceeded for {request.mode.value} request")
            return CognitiveResponse(
                success=False,
                action="hold",
                reasoning=f"hard_timeout_{timeout_s}s",
                confidence=0,
                data={"circuit_breaker": self._circuit_breaker.get_stats()}
            )
        except json.JSONDecodeError as e:
            self.errors += 1
            # JSON parse errors are NOT circuit breaker failures (endpoint is alive)
            self.logger.error(f"JSON parse error: {e}")
            return CognitiveResponse(
                success=False,
                action="retry",
                reasoning="response_parse_error",
                confidence=0
            )
        except Exception as e:
            self.errors += 1
            self._circuit_breaker.record_failure()
            self.logger.error(f"Cognitive fault: {e}")
            return CognitiveResponse(
                success=False,
                action="hold",
                reasoning=f"cognitive_error: {str(e)}",
                confidence=0,
                data={"circuit_breaker": self._circuit_breaker.get_stats()}
            )
    
    def _build_messages(self, request: CognitiveRequest) -> List[Dict]:
        """Build the message payload for the API"""
        system_prompt = self.SYSTEM_PROMPTS.get(
            request.mode, 
            self.SYSTEM_PROMPTS[CognitiveMode.ANALYSIS]
        )
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Build user message (potentially multimodal)
        if request.screenshot_b64:
            # Multimodal message with image
            user_content = [
                {"type": "text", "text": f"Context:\n{request.context}"},
                {
                    "type": "image_url", 
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{request.screenshot_b64}"
                    }
                }
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            # Text-only message
            messages.append({"role": "user", "content": request.context})
        
        return messages
    
    async def analyze_context(self, 
                              dom_snippet: str, 
                              screenshot_b64: Optional[str] = None) -> Dict:
        """
        Analyze page context for decision making.
        Convenience method wrapping process().
        """
        request = CognitiveRequest(
            mode=CognitiveMode.ANALYSIS,
            context=dom_snippet,
            screenshot_b64=screenshot_b64
        )
        response = await self.process(request)
        return response.data if response.success else {"error": response.reasoning}
    
    async def decide_action(self, 
                            page_state: str,
                            available_actions: List[str]) -> Dict:
        """
        Decide the next action based on page state.
        """
        context = f"""Page State:
{page_state}

Available Actions:
{json.dumps(available_actions, indent=2)}

Determine the optimal next action."""
        
        request = CognitiveRequest(
            mode=CognitiveMode.DECISION,
            context=context,
            temperature=0.5  # Lower temperature for more deterministic decisions
        )
        response = await self.process(request)
        return response.data if response.success else {"action": "wait", "error": response.reasoning}
    
    async def solve_captcha(self, 
                            captcha_image_b64: str,
                            captcha_type: str = "unknown") -> Dict:
        """
        Solve a CAPTCHA using multimodal analysis.
        """
        request = CognitiveRequest(
            mode=CognitiveMode.CAPTCHA,
            context=f"CAPTCHA Type: {captcha_type}\nSolve this CAPTCHA:",
            screenshot_b64=captcha_image_b64,
            temperature=0.3  # Low temperature for accuracy
        )
        response = await self.process(request)
        return response.data if response.success else {"error": response.reasoning}
    
    async def assess_risk(self,
                          bin_data: Dict,
                          merchant_info: Dict,
                          transaction_history: List[Dict] = None) -> Dict:
        """
        Assess transaction risk using the Cloud Brain.
        """
        context = f"""Risk Assessment Request:

BIN Data:
{json.dumps(bin_data, indent=2)}

Merchant Info:
{json.dumps(merchant_info, indent=2)}

Transaction History:
{json.dumps(transaction_history or [], indent=2)}

Analyze risk factors and provide a risk score (0-100)."""
        
        request = CognitiveRequest(
            mode=CognitiveMode.RISK,
            context=context,
            max_tokens=800
        )
        response = await self.process(request)
        return response.data if response.success else {"risk_score": 100, "error": response.reasoning}
    
    async def generate_response(self,
                                conversation_context: str,
                                persona: str = "casual_user") -> str:
        """
        Generate a natural human-like response for conversations.
        """
        context = f"""Persona: {persona}

Conversation Context:
{conversation_context}

Generate a natural, human-like response."""
        
        request = CognitiveRequest(
            mode=CognitiveMode.CONVERSATION,
            context=context,
            temperature=0.9  # Higher temperature for natural variation
        )
        response = await self.process(request)
        return response.data.get("response", "") if response.success else ""
    
    def get_stats(self) -> Dict:
        """Get cognitive core statistics"""
        return {
            "connected": self.is_connected,
            "endpoint": self.endpoint_url,
            "model": self.model,
            "total_requests": self.total_requests,
            "average_latency_ms": round(self.average_latency, 2),
            "errors": self.errors,
            "error_rate": round(self.errors / max(1, self.total_requests) * 100, 2)
        }


class CognitiveCoreLocal:
    """
    Fallback local cognitive core when cloud is unavailable.
    Uses rule-based heuristics instead of LLM inference.
    
    This is a degraded mode - success rate drops to ~70%.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("TITAN-V7-LOCAL")
        self.logger.warning("Running in LOCAL FALLBACK mode - reduced capabilities")
    
    @property
    def is_connected(self) -> bool:
        return False
    
    async def analyze_context(self, dom_snippet: str, **kwargs) -> Dict:
        """Rule-based DOM analysis using keyword and pattern matching"""
        analysis = {
            "elements": [],
            "security": [],
            "trust_score": 50,
            "risks": [],
            "recommendations": []
        }
        
        dom_lower = dom_snippet.lower()
        
        # Security detection
        if "captcha" in dom_lower or "recaptcha" in dom_lower or "hcaptcha" in dom_lower:
            analysis["security"].append("captcha_detected")
            analysis["risks"].append("manual_intervention_required")
            analysis["recommendations"].append("pause_for_operator_captcha_solve")
        
        if "2fa" in dom_lower or "two-factor" in dom_lower or "verification code" in dom_lower:
            analysis["security"].append("2fa_detected")
            analysis["recommendations"].append("check_for_sms_or_email_code")
        
        if "3d secure" in dom_lower or "3ds" in dom_lower or "verified by visa" in dom_lower:
            analysis["security"].append("3ds_challenge")
            analysis["recommendations"].append("wait_for_3ds_iframe")
        
        # Form detection
        for field_type in ["input", "select", "textarea", "button", "form"]:
            if f"<{field_type}" in dom_lower:
                analysis["elements"].append(field_type)
        
        # Trust signals
        if "ssl" in dom_lower or "secure checkout" in dom_lower or "encrypted" in dom_lower:
            analysis["trust_score"] += 10
        if "mcafee" in dom_lower or "norton" in dom_lower or "trustpilot" in dom_lower:
            analysis["trust_score"] += 5
        
        # Risk signals
        if "error" in dom_lower or "declined" in dom_lower or "failed" in dom_lower:
            analysis["risks"].append("error_state_detected")
            analysis["trust_score"] -= 20
        if "suspicious" in dom_lower or "fraud" in dom_lower or "blocked" in dom_lower:
            analysis["risks"].append("fraud_detection_triggered")
            analysis["trust_score"] -= 30
        if "out of stock" in dom_lower or "unavailable" in dom_lower:
            analysis["risks"].append("product_unavailable")
        if "rate limit" in dom_lower or "too many" in dom_lower:
            analysis["risks"].append("rate_limited")
            analysis["recommendations"].append("wait_and_retry_with_backoff")
        
        # Page state detection
        if "order confirm" in dom_lower or "thank you" in dom_lower or "success" in dom_lower:
            analysis["trust_score"] += 20
            analysis["recommendations"].append("order_likely_successful")
        if "cart" in dom_lower and ("empty" in dom_lower or "0 item" in dom_lower):
            analysis["risks"].append("cart_emptied")
        
        return analysis
    
    async def decide_action(self, page_state: str, available_actions: List[str]) -> Dict:
        """Rule-based action decision with priority ordering"""
        state_lower = page_state.lower()
        
        # Priority-ordered action matching
        priority_map = [
            ("captcha", "solve_captcha", 0.9),
            ("3d secure", "wait_3ds", 0.85),
            ("declined", "abort", 0.95),
            ("blocked", "abort", 0.95),
            ("error", "retry", 0.7),
            ("confirm", "confirm_order", 0.8),
            ("checkout", "proceed_checkout", 0.8),
            ("cart", "view_cart", 0.7),
            ("login", "fill_login", 0.75),
            ("payment", "fill_payment", 0.8),
            ("address", "fill_address", 0.8),
            ("shipping", "select_shipping", 0.75),
        ]
        
        for keyword, action, confidence in priority_map:
            if keyword in state_lower and action in available_actions:
                return {
                    "action": action,
                    "confidence": confidence,
                    "reasoning": f"local_rule_match: '{keyword}' detected in page state"
                }
        
        # Fallback: first available action
        return {
            "action": available_actions[0] if available_actions else "wait",
            "confidence": 0.5,
            "reasoning": "local_fallback: no rule matched, using first available action"
        }
    
    async def assess_risk(self, bin_data: Dict, **kwargs) -> Dict:
        """Rule-based risk assessment using BIN properties"""
        risk_score = 30
        risk_factors = []
        
        bin_prefix = bin_data.get("bin", "")[:6]
        card_type = bin_data.get("type", "credit")
        card_level = bin_data.get("level", "classic")
        country = bin_data.get("country", "US")
        
        # Card type risk
        if card_type == "prepaid":
            risk_score += 30
            risk_factors.append("prepaid_card_high_risk")
        elif card_type == "debit":
            risk_score += 10
            risk_factors.append("debit_card_moderate_risk")
        
        # Card level trust
        if card_level in ("centurion", "platinum", "signature", "world_elite"):
            risk_score -= 10
            risk_factors.append("premium_card_lower_risk")
        
        # Amex higher scrutiny
        if bin_prefix[:2] in ("34", "37"):
            risk_score += 10
            risk_factors.append("amex_higher_avs_scrutiny")
        
        # International risk
        merchant_info = kwargs.get("merchant_info", {})
        merchant_country = merchant_info.get("country", "US")
        if country != merchant_country:
            risk_score += 15
            risk_factors.append(f"cross_border_{country}_to_{merchant_country}")
        
        # Transaction history velocity
        history = kwargs.get("transaction_history", [])
        if len(history) > 3:
            risk_score += 10
            risk_factors.append("high_velocity_multiple_transactions")
        
        risk_score = max(0, min(100, risk_score))
        
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors if risk_factors else ["baseline_assessment"],
            "recommendation": "proceed" if risk_score < 50 else ("proceed_with_caution" if risk_score < 70 else "abort"),
            "proceed": risk_score < 70
        }
    
    async def solve_captcha(self, captcha_image_b64: str, captcha_type: str = "unknown") -> Dict:
        """V7.5 FIX: Local fallback — cannot solve CAPTCHAs without LLM"""
        return {"error": "captcha_requires_cloud_brain", "captcha_type": captcha_type,
                "recommendation": "manual_solve_required"}
    
    async def generate_response(self, conversation_context: str, persona: str = "casual_user") -> str:
        """V7.5 FIX: Local fallback — generic response"""
        return "I'll need a moment to check on that."


def get_cognitive_core(prefer_cloud: bool = True) -> Union[TitanCognitiveCore, CognitiveCoreLocal]:
    """
    Factory function to get the appropriate cognitive core.
    
    Args:
        prefer_cloud: If True, try cloud first, fallback to local
        
    Returns:
        TitanCognitiveCore if cloud available, else CognitiveCoreLocal
    """
    if prefer_cloud and OPENAI_AVAILABLE:
        core = TitanCognitiveCore()
        if core.is_connected:
            return core
    
    return CognitiveCoreLocal()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: ANTIFRAUD PATTERN RECOGNIZER
# Recognize and adapt to antifraud detection patterns
# ═══════════════════════════════════════════════════════════════════════════

class AntifraudPatternRecognizer:
    """
    V7.6: Recognizes antifraud system patterns and suggests evasion strategies.
    
    Detects:
    - Forter/Riskified/Signifyd fingerprint collection
    - Device intelligence scripts (ThreatMetrix, Iovation)
    - Session recording (FullStory, Hotjar)
    - Bot detection (PerimeterX, DataDome, Kasada)
    
    This allows pre-emptive counter-measures before transaction.
    """
    
    # Detection signatures per antifraud vendor
    SIGNATURES = {
        'forter': {
            'scripts': ['forter.com', 'forter.min.js', 'forterToken'],
            'cookies': ['forterToken', 'ftr_blst', 'ftr_ncd'],
            'dom': ['data-forter', 'forter-snippet'],
            'threat_level': 'high',
        },
        'riskified': {
            'scripts': ['beacon-v2', 'riskified.com', 'RISKX'],
            'cookies': ['riskified_session', 'rCookie'],
            'dom': ['riskified-beacon', 'riskx'],
            'threat_level': 'high',
        },
        'signifyd': {
            'scripts': ['signifyd.com', 'sig-api.js', 'deviceFingerprint'],
            'cookies': ['signifyd_session'],
            'dom': ['signifyd-device', 'sig_deviceId'],
            'threat_level': 'medium',
        },
        'sift': {
            'scripts': ['cdn.sift.com', 'sift.js', 's.siftscience'],
            'cookies': ['_sift_session'],
            'dom': ['data-sift', 'sift-beacon'],
            'threat_level': 'high',
        },
        'threatmetrix': {
            'scripts': ['h.online-metrix.net', 'tmx_', 'threatmetrix'],
            'cookies': ['tmx_', 'online-metrix'],
            'dom': ['tmx_profiling'],
            'threat_level': 'high',
        },
        'iovation': {
            'scripts': ['iovation.com', 'ioBlackBox', 'iobb'],
            'cookies': ['io_token', 'iovation'],
            'dom': ['ioBlackBox', 'io-beacon'],
            'threat_level': 'medium',
        },
        'perimeterx': {
            'scripts': ['px-client', 'perimeterx', '_pxmvid'],
            'cookies': ['_pxvid', '_pxff_', '_pxmvid'],
            'dom': ['px-captcha', '_px'],
            'threat_level': 'very_high',
        },
        'datadome': {
            'scripts': ['datadome.co', 'dd.js', 'ddjskey'],
            'cookies': ['datadome', 'dd_cookie'],
            'dom': ['datadome-captcha'],
            'threat_level': 'very_high',
        },
        'kasada': {
            'scripts': ['kasada', 'cd-kogmv'],
            'cookies': ['cd-kogmv', 'x-kpsdk'],
            'dom': ['kasada-challenge'],
            'threat_level': 'very_high',
        },
        'fullstory': {
            'scripts': ['fullstory.com', 'fs.js', '_fs_'],
            'cookies': ['fs_uid', '_fs_'],
            'dom': ['fs-highlight'],
            'threat_level': 'low',  # Session recording, not blocking
        },
    }
    
    # Counter-measures per threat level
    COUNTERMEASURES = {
        'very_high': {
            'delay_range': (3000, 8000),
            'human_simulation': 'extensive',
            'fingerprint_stability': 'critical',
            'retry_limit': 1,
            'abort_on_challenge': True,
        },
        'high': {
            'delay_range': (2000, 5000),
            'human_simulation': 'moderate',
            'fingerprint_stability': 'high',
            'retry_limit': 2,
            'abort_on_challenge': False,
        },
        'medium': {
            'delay_range': (1000, 3000),
            'human_simulation': 'basic',
            'fingerprint_stability': 'moderate',
            'retry_limit': 3,
            'abort_on_challenge': False,
        },
        'low': {
            'delay_range': (500, 2000),
            'human_simulation': 'minimal',
            'fingerprint_stability': 'low',
            'retry_limit': 5,
            'abort_on_challenge': False,
        },
    }
    
    def __init__(self):
        self._detected_vendors = []
        self._threat_level = 'low'
        self._detection_cache = {}
    
    def analyze_page(self, html_content: str, cookies: Dict = None, 
                      network_requests: List[str] = None) -> Dict:
        """
        Analyze page for antifraud presence.
        
        Args:
            html_content: Page HTML
            cookies: Current cookies dict
            network_requests: List of request URLs
        """
        html_lower = html_content.lower()
        cookies = cookies or {}
        network_requests = network_requests or []
        
        detected = []
        highest_threat = 'low'
        
        for vendor, sig in self.SIGNATURES.items():
            score = 0
            
            # Check scripts in HTML
            for script_sig in sig['scripts']:
                if script_sig.lower() in html_lower:
                    score += 2
                # Check network requests
                for req in network_requests:
                    if script_sig.lower() in req.lower():
                        score += 3
            
            # Check cookies
            for cookie_sig in sig['cookies']:
                if any(cookie_sig.lower() in k.lower() for k in cookies.keys()):
                    score += 2
            
            # Check DOM elements
            for dom_sig in sig['dom']:
                if dom_sig.lower() in html_lower:
                    score += 1
            
            if score >= 2:
                detected.append({
                    'vendor': vendor,
                    'confidence': min(score / 5, 1.0),
                    'threat_level': sig['threat_level'],
                })
                
                # Track highest threat
                threat_order = ['low', 'medium', 'high', 'very_high']
                if threat_order.index(sig['threat_level']) > threat_order.index(highest_threat):
                    highest_threat = sig['threat_level']
        
        self._detected_vendors = detected
        self._threat_level = highest_threat
        
        return {
            'vendors_detected': detected,
            'threat_level': highest_threat,
            'countermeasures': self.COUNTERMEASURES[highest_threat],
            'evasion_strategy': self._generate_evasion_strategy(detected),
        }
    
    def _generate_evasion_strategy(self, detected: List[Dict]) -> Dict:
        """Generate specific evasion strategy for detected vendors."""
        strategy = {
            'recommendations': [],
            'required_modules': [],
            'timing_profile': 'normal',
        }
        
        vendors = [d['vendor'] for d in detected]
        
        if any(v in vendors for v in ['perimeterx', 'datadome', 'kasada']):
            strategy['recommendations'].append('Use residential proxy with clean IP')
            strategy['recommendations'].append('Enable full GhostMotor human simulation')
            strategy['required_modules'].append('ghost_motor_v6')
            strategy['timing_profile'] = 'very_slow'
        
        if any(v in vendors for v in ['forter', 'riskified', 'sift']):
            strategy['recommendations'].append('Use aged profile with history')
            strategy['recommendations'].append('Warm card with small transactions first')
            strategy['required_modules'].append('genesis_core')
            strategy['timing_profile'] = 'natural'
        
        if any(v in vendors for v in ['threatmetrix', 'iovation']):
            strategy['recommendations'].append('Ensure fingerprint consistency')
            strategy['required_modules'].append('fingerprint_injector')
            strategy['timing_profile'] = 'normal'
        
        if 'fullstory' in vendors:
            strategy['recommendations'].append('Avoid erratic mouse movements')
            strategy['timing_profile'] = 'natural'
        
        return strategy
    
    def get_current_threat_level(self) -> str:
        """Get current assessed threat level."""
        return self._threat_level
    
    def get_detected_vendors(self) -> List[Dict]:
        """Get list of detected antifraud vendors."""
        return self._detected_vendors


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: SESSION CONTEXT MANAGER
# Track session context across multiple AI decisions
# ═══════════════════════════════════════════════════════════════════════════

class SessionContextManager:
    """
    V7.6: Manages session context for consistent AI decision-making.
    
    Tracks:
    - Page navigation history
    - Action history and outcomes
    - Detected antifraud systems
    - Profile state (logged in, cart contents, etc.)
    - Error/retry patterns
    
    This context improves AI decision accuracy over session lifetime.
    """
    
    def __init__(self, session_id: str = None):
        import uuid
        import time
        
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.created_at = time.time()
        
        self._page_history = []
        self._action_history = []
        self._context = {
            'logged_in': False,
            'cart_items': 0,
            'cart_value': 0.0,
            'checkout_stage': None,
            'errors_count': 0,
            'retries_count': 0,
        }
        self._antifraud = None
        self._flags = set()
    
    def record_page_visit(self, url: str, title: str = '', 
                          dom_snapshot: str = None):
        """Record a page visit."""
        import time
        
        self._page_history.append({
            'timestamp': time.time(),
            'url': url,
            'title': title,
            'dom_length': len(dom_snapshot) if dom_snapshot else 0,
        })
        
        # Auto-detect context from URL/title
        self._auto_update_context(url, title)
        
        # Limit history size
        if len(self._page_history) > 50:
            self._page_history = self._page_history[-50:]
    
    def record_action(self, action: str, result: str, 
                       details: Dict = None):
        """Record an action and its outcome."""
        import time
        
        self._action_history.append({
            'timestamp': time.time(),
            'action': action,
            'result': result,
            'details': details or {},
        })
        
        # Update error/retry counters
        if result in ('error', 'failed'):
            self._context['errors_count'] += 1
        if action.startswith('retry'):
            self._context['retries_count'] += 1
        
        # Limit history size
        if len(self._action_history) > 100:
            self._action_history = self._action_history[-100:]
    
    def _auto_update_context(self, url: str, title: str):
        """Auto-update context based on page URL/title."""
        url_lower = url.lower()
        title_lower = title.lower()
        combined = f"{url_lower} {title_lower}"
        
        # Checkout stage detection
        if 'cart' in combined:
            self._context['checkout_stage'] = 'cart'
        elif 'shipping' in combined or 'delivery' in combined:
            self._context['checkout_stage'] = 'shipping'
        elif 'payment' in combined or 'billing' in combined:
            self._context['checkout_stage'] = 'payment'
        elif 'review' in combined or 'confirm' in combined:
            self._context['checkout_stage'] = 'review'
        elif 'success' in combined or 'thank' in combined:
            self._context['checkout_stage'] = 'complete'
        
        # Login state
        if 'login' in combined or 'sign in' in combined:
            self._context['logged_in'] = False
        elif 'account' in combined or 'profile' in combined:
            self._context['logged_in'] = True
    
    def set_context(self, key: str, value):
        """Set a context value."""
        self._context[key] = value
    
    def get_context(self, key: str = None):
        """Get context value or full context."""
        if key:
            return self._context.get(key)
        return self._context.copy()
    
    def set_antifraud_analysis(self, analysis: Dict):
        """Store antifraud analysis results."""
        self._antifraud = analysis
    
    def add_flag(self, flag: str):
        """Add a warning flag (e.g., 'rate_limited', 'suspicious')."""
        self._flags.add(flag)
    
    def has_flag(self, flag: str) -> bool:
        """Check if flag is set."""
        return flag in self._flags
    
    def get_summary(self) -> Dict:
        """Get session summary for AI context."""
        import time
        
        return {
            'session_id': self.session_id,
            'duration_seconds': round(time.time() - self.created_at, 1),
            'pages_visited': len(self._page_history),
            'actions_taken': len(self._action_history),
            'current_context': self._context,
            'antifraud_detected': bool(self._antifraud),
            'threat_level': self._antifraud.get('threat_level') if self._antifraud else 'unknown',
            'flags': list(self._flags),
            'recent_pages': [p['url'] for p in self._page_history[-5:]],
            'recent_actions': [
                {'action': a['action'], 'result': a['result']} 
                for a in self._action_history[-5:]
            ],
        }
    
    def get_ai_context_prompt(self) -> str:
        """Generate context prompt for AI decision-making."""
        summary = self.get_summary()
        
        prompt = f"""Session Context:
- Duration: {summary['duration_seconds']}s
- Checkout Stage: {self._context.get('checkout_stage', 'browsing')}
- Cart: {self._context.get('cart_items', 0)} items, ${self._context.get('cart_value', 0):.2f}
- Logged In: {self._context.get('logged_in', False)}
- Errors: {self._context.get('errors_count', 0)}, Retries: {self._context.get('retries_count', 0)}
- Antifraud: {summary['threat_level']}
- Flags: {', '.join(summary['flags']) or 'none'}

Recent Actions:
"""
        for action in summary['recent_actions'][-3:]:
            prompt += f"- {action['action']}: {action['result']}\n"
        
        return prompt


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: BEHAVIORAL ADAPTATION ENGINE
# Adapt behavior based on AI analysis and session state
# ═══════════════════════════════════════════════════════════════════════════

class BehavioralAdaptationEngine:
    """
    V7.6: Adapts automation behavior based on real-time analysis.
    
    Adjusts:
    - Action timing (delays, typing speed)
    - Mouse movement patterns
    - Retry strategies
    - Abort conditions
    
    Based on detected antifraud systems and session state.
    """
    
    # Behavior profiles
    PROFILES = {
        'stealth': {
            'delay_multiplier': 2.5,
            'typing_speed_wpm': 35,
            'mouse_smoothness': 0.9,
            'thinking_pauses': True,
            'scroll_before_action': True,
        },
        'normal': {
            'delay_multiplier': 1.0,
            'typing_speed_wpm': 65,
            'mouse_smoothness': 0.7,
            'thinking_pauses': False,
            'scroll_before_action': False,
        },
        'fast': {
            'delay_multiplier': 0.5,
            'typing_speed_wpm': 120,
            'mouse_smoothness': 0.4,
            'thinking_pauses': False,
            'scroll_before_action': False,
        },
        'recovery': {
            'delay_multiplier': 3.0,
            'typing_speed_wpm': 25,
            'mouse_smoothness': 0.95,
            'thinking_pauses': True,
            'scroll_before_action': True,
        },
    }
    
    def __init__(self, initial_profile: str = 'normal'):
        import random
        self._random = random.Random()
        self._profile_name = initial_profile
        self._profile = self.PROFILES[initial_profile].copy()
        self._adaptations = []
    
    def adapt_to_threat_level(self, threat_level: str):
        """Adapt behavior based on antifraud threat level."""
        mapping = {
            'very_high': 'stealth',
            'high': 'stealth',
            'medium': 'normal',
            'low': 'normal',
        }
        
        new_profile = mapping.get(threat_level, 'normal')
        if new_profile != self._profile_name:
            self._profile_name = new_profile
            self._profile = self.PROFILES[new_profile].copy()
            self._adaptations.append(f'threat_level_{threat_level}')
    
    def adapt_to_errors(self, error_count: int):
        """Adapt behavior based on error frequency."""
        if error_count >= 3:
            self._profile_name = 'recovery'
            self._profile = self.PROFILES['recovery'].copy()
            self._adaptations.append('recovery_mode')
        elif error_count >= 1:
            self._profile['delay_multiplier'] *= 1.5
            self._adaptations.append('increased_delays')
    
    def get_delay(self, base_delay_ms: int) -> int:
        """Get adapted delay with variance."""
        multiplier = self._profile['delay_multiplier']
        variance = self._random.uniform(0.8, 1.2)
        return int(base_delay_ms * multiplier * variance)
    
    def get_typing_delay(self, char_count: int) -> int:
        """Get time to type N characters in milliseconds."""
        wpm = self._profile['typing_speed_wpm']
        cpm = wpm * 5  # Average 5 chars per word
        base_ms = (char_count / cpm) * 60 * 1000
        
        # Add variance
        variance = self._random.uniform(0.85, 1.15)
        return int(base_ms * variance)
    
    def should_add_thinking_pause(self) -> bool:
        """Should we add a thinking pause before action?"""
        if not self._profile['thinking_pauses']:
            return False
        return self._random.random() < 0.3
    
    def get_thinking_pause_ms(self) -> int:
        """Get duration of thinking pause."""
        return self._random.randint(800, 2500)
    
    def should_scroll_before_action(self) -> bool:
        """Should we scroll element into view before clicking?"""
        return self._profile['scroll_before_action']
    
    def get_mouse_smoothness(self) -> float:
        """Get mouse movement smoothness (0-1)."""
        return self._profile['mouse_smoothness']
    
    def get_current_profile(self) -> Dict:
        """Get current behavior profile."""
        return {
            'name': self._profile_name,
            'settings': self._profile.copy(),
            'adaptations': self._adaptations.copy(),
        }
    
    def should_abort(self, session_context: SessionContextManager) -> Tuple[bool, str]:
        """Determine if session should abort."""
        ctx = session_context.get_context()
        flags = session_context._flags
        
        # Hard abort conditions
        if ctx.get('errors_count', 0) >= 5:
            return True, 'too_many_errors'
        
        if 'rate_limited' in flags:
            return True, 'rate_limited'
        
        if 'fraud_detected' in flags:
            return True, 'fraud_detected'
        
        if ctx.get('retries_count', 0) >= 10:
            return True, 'excessive_retries'
        
        return False, ''


# V7.6 Convenience exports
def create_antifraud_recognizer() -> AntifraudPatternRecognizer:
    """V7.6: Create antifraud pattern recognizer"""
    return AntifraudPatternRecognizer()

def create_session_context(session_id: str = None) -> SessionContextManager:
    """V7.6: Create session context manager"""
    return SessionContextManager(session_id)

def create_behavioral_adapter(profile: str = 'normal') -> BehavioralAdaptationEngine:
    """V7.6: Create behavioral adaptation engine"""
    return BehavioralAdaptationEngine(profile)


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 AI ENHANCEMENT INTEGRATION
# ChromaDB Vector Memory + LangChain Agent + Web Intelligence
# ═══════════════════════════════════════════════════════════════════════════

def get_agent():
    """V7.6: Get the LangChain-powered autonomous agent."""
    try:
        from titan_agent_chain import get_titan_agent
        return get_titan_agent()
    except ImportError:
        logging.getLogger("TITAN-V7-BRAIN").warning(
            "titan_agent_chain not available. Install: pip install langchain langchain-ollama"
        )
        return None


def get_vector_memory():
    """V7.6: Get the ChromaDB vector memory store."""
    try:
        from titan_vector_memory import get_vector_memory as _get_vm
        return _get_vm()
    except ImportError:
        logging.getLogger("TITAN-V7-BRAIN").warning(
            "titan_vector_memory not available. Install: pip install chromadb"
        )
        return None


def get_web_intel():
    """V7.6: Get the web intelligence engine."""
    try:
        from titan_web_intel import get_web_intel as _get_wi
        return _get_wi()
    except ImportError:
        logging.getLogger("TITAN-V7-BRAIN").warning(
            "titan_web_intel not available. Install: pip install duckduckgo-search"
        )
        return None


def get_ai_enhancement_status() -> Dict:
    """V7.6: Get status of all AI enhancements."""
    status = {
        "vector_memory": {"available": False},
        "agent_chain": {"available": False},
        "web_intel": {"available": False},
    }

    try:
        from titan_vector_memory import get_vector_memory as _get_vm
        mem = _get_vm()
        status["vector_memory"] = mem.get_stats()
    except Exception:
        pass

    try:
        from titan_agent_chain import get_titan_agent
        agent = get_titan_agent()
        status["agent_chain"] = agent.get_status()
    except Exception:
        pass

    try:
        from titan_web_intel import get_web_intel as _get_wi
        intel = _get_wi()
        status["web_intel"] = intel.get_stats()
    except Exception:
        pass

    return status


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SELF-HOSTED TOOL STACK INTEGRATION
# GeoIP, IP Quality, Redis, Ntfy, Proxy Monitor, Target Prober, etc.
# ═══════════════════════════════════════════════════════════════════════════

def get_self_hosted_stack():
    """V7.6: Get the unified self-hosted tool stack manager."""
    try:
        from titan_self_hosted_stack import get_self_hosted_stack as _get_stack
        return _get_stack()
    except ImportError:
        logging.getLogger("TITAN-V7-BRAIN").debug(
            "titan_self_hosted_stack not available"
        )
        return None


def get_geoip():
    """V7.6: Get GeoIP validator for proxy geo-match checks."""
    try:
        from titan_self_hosted_stack import get_geoip_validator
        return get_geoip_validator()
    except ImportError:
        return None


def get_ip_checker():
    """V7.6: Get IP quality checker for proxy reputation scoring."""
    try:
        from titan_self_hosted_stack import get_ip_quality_checker
        return get_ip_quality_checker()
    except ImportError:
        return None


def get_redis():
    """V7.6: Get Redis client for fast inter-module state."""
    try:
        from titan_self_hosted_stack import get_redis_client
        return get_redis_client()
    except ImportError:
        return None


def get_ntfy():
    """V7.6: Get Ntfy client for push notifications."""
    try:
        from titan_self_hosted_stack import get_ntfy_client
        return get_ntfy_client()
    except ImportError:
        return None


def get_target_prober():
    """V7.6: Get Playwright-based target site prober."""
    try:
        from titan_self_hosted_stack import get_target_prober
        return get_target_prober()
    except ImportError:
        return None


def get_stack_status() -> Dict:
    """V7.6: Get combined status of AI enhancements + self-hosted stack."""
    status = get_ai_enhancement_status()
    try:
        from titan_self_hosted_stack import get_self_hosted_stack as _get_stack
        stack = _get_stack()
        status["self_hosted_stack"] = stack.get_status()
    except Exception:
        status["self_hosted_stack"] = {"available": False}
    return status


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 TARGET INTELLIGENCE V2 — GOLDEN PATH SCORING
# 8-vector analysis for 100% hit probability identification
# ═══════════════════════════════════════════════════════════════════════════

def get_target_intel_v2():
    """V7.6: Get Target Intelligence V2 engine for golden path scoring."""
    try:
        from titan_target_intel_v2 import get_target_intel_v2 as _get
        return _get()
    except ImportError:
        return None


def score_target_golden(domain: str, card_country: str = "US",
                        amount: float = 100, **kwargs) -> Dict:
    """V7.6: Score a target across all 8 vectors for hit probability."""
    try:
        from titan_target_intel_v2 import get_target_intel_v2
        return get_target_intel_v2().score_target(
            domain, card_country=card_country, amount=amount, **kwargs
        )
    except ImportError:
        return {"error": "titan_target_intel_v2 not available"}


def find_golden_targets(card_country: str = "US", max_amount: float = 200) -> list:
    """V7.6: Find all targets with 100% hit probability (golden path)."""
    try:
        from titan_target_intel_v2 import get_target_intel_v2
        return get_target_intel_v2().find_golden_targets(
            card_country=card_country, max_amount=max_amount
        )
    except ImportError:
        return []


def full_target_brief(domain: str, card_country: str = "US",
                      amount: float = 100) -> Dict:
    """V7.6: Full operational brief for a target with all intelligence."""
    try:
        from titan_target_intel_v2 import get_target_intel_v2
        return get_target_intel_v2().full_target_analysis(
            domain, card_country=card_country, amount=amount
        )
    except ImportError:
        return {"error": "titan_target_intel_v2 not available"}


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 3DS AI-SPEED EXPLOIT ENGINE
# Sub-human-speed techniques for 3DS avoidance
# ═══════════════════════════════════════════════════════════════════════════

def get_3ds_ai_engine():
    """V7.6: Get 3DS AI-Speed Exploit Engine."""
    try:
        from titan_3ds_ai_exploits import get_3ds_ai_engine as _get
        return _get()
    except ImportError:
        return None


def get_ai_exploit_stack(domain: str = "", psp: str = "unknown",
                         card_country: str = "US", amount: float = 100) -> Dict:
    """V7.6: Get co-pilot config for a target."""
    try:
        from titan_3ds_ai_exploits import get_3ds_ai_engine
        return get_3ds_ai_engine().get_copilot_config(
            psp=psp, card_country=card_country, amount=amount
        )
    except ImportError:
        return {"error": "titan_3ds_ai_exploits not available"}


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 AI OPERATIONS GUARD
# Silent Ollama-powered operation lifecycle monitor
# ═══════════════════════════════════════════════════════════════════════════

def get_operations_guard():
    """V7.6: Get AI Operations Guard (Ollama-powered operation lifecycle monitor)."""
    try:
        from titan_ai_operations_guard import get_operations_guard as _get
        return _get()
    except ImportError:
        return None


def guard_pre_op(target: str, card_bin: str = "", card_country: str = "US",
                 proxy_country: str = "", billing_state: str = "",
                 amount: float = 100, **kwargs) -> Dict:
    """V7.6: Pre-operation check — catches issues before you commit."""
    try:
        from titan_ai_operations_guard import get_operations_guard
        guard = get_operations_guard()
        verdict = guard.pre_operation_check(
            target=target, card_bin=card_bin, card_country=card_country,
            proxy_country=proxy_country, billing_state=billing_state,
            amount=amount, **kwargs
        )
        return {
            "risk_level": verdict.risk_level.value,
            "proceed": verdict.proceed,
            "issues": verdict.issues,
            "recommendations": verdict.recommendations,
            "ai_reasoning": verdict.ai_reasoning,
        }
    except ImportError:
        return {"error": "titan_ai_operations_guard not available"}


def guard_session_health(**kwargs) -> Dict:
    """V7.6: Check active session health."""
    try:
        from titan_ai_operations_guard import get_operations_guard
        guard = get_operations_guard()
        verdict = guard.check_session_health(**kwargs)
        return {
            "risk_level": verdict.risk_level.value,
            "proceed": verdict.proceed,
            "issues": verdict.issues,
            "recommendations": verdict.recommendations,
        }
    except ImportError:
        return {"error": "titan_ai_operations_guard not available"}


def guard_post_op(target: str, result: str, decline_code: str = "",
                  card_bin: str = "", amount: float = 0, **kwargs) -> Dict:
    """V7.6: Post-operation analysis — learn from results."""
    try:
        from titan_ai_operations_guard import get_operations_guard
        guard = get_operations_guard()
        verdict = guard.post_operation_analysis(
            target=target, result=result, decline_code=decline_code,
            card_bin=card_bin, amount=amount, **kwargs
        )
        return {
            "risk_level": verdict.risk_level.value,
            "issues": verdict.issues,
            "recommendations": verdict.recommendations,
            "ai_reasoning": verdict.ai_reasoning,
        }
    except ImportError:
        return {"error": "titan_ai_operations_guard not available"}
