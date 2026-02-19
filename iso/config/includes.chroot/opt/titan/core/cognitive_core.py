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
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from enum import Enum

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
    timestamp: datetime = field(default_factory=datetime.now)


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
        
        start_time = datetime.now()
        
        try:
            # Build messages
            messages = self._build_messages(request)
            
            # Execute inference via Cloud Brain
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                response_format={"type": "json_object"}
            )
            
            # Calculate actual inference latency
            inference_latency = (datetime.now() - start_time).total_seconds() * 1000
            
            # CRITICAL: Enforce Human Cognitive Latency
            # vLLM responds in ~150ms, but humans take 200-450ms
            # We must inject delay to avoid bot detection
            required_delay = random.uniform(
                self.HUMAN_LATENCY_MIN, 
                self.HUMAN_LATENCY_MAX
            ) - inference_latency
            
            if required_delay > 0:
                await asyncio.sleep(required_delay / 1000)
            
            # Parse response
            total_latency = (datetime.now() - start_time).total_seconds() * 1000
            
            content = response.choices[0].message.content
            parsed = json.loads(content) if content else {}
            
            # Update statistics
            self.total_requests += 1
            self.total_latency_ms += total_latency
            
            return CognitiveResponse(
                success=True,
                action=parsed.get("action", "proceed"),
                reasoning=parsed.get("reasoning", parsed.get("reason", "")),
                confidence=parsed.get("confidence", 0.8),
                data=parsed,
                latency_ms=total_latency
            )
            
        except json.JSONDecodeError as e:
            self.errors += 1
            self.logger.error(f"JSON parse error: {e}")
            return CognitiveResponse(
                success=False,
                action="retry",
                reasoning="response_parse_error",
                confidence=0
            )
        except Exception as e:
            self.errors += 1
            self.logger.error(f"Cognitive fault: {e}")
            return CognitiveResponse(
                success=False,
                action="hold",
                reasoning=f"cognitive_error: {str(e)}",
                confidence=0
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
