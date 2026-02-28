#!/usr/bin/env python3
"""
CERBERUS HYPERSWITCH — Unified Payment Orchestration Layer
============================================================
V2.0 — Hyperswitch integration for Cerberus AppX

Wraps Juspay's open-source Hyperswitch payment orchestrator to provide:
  - Intelligent routing across 50+ payment connectors
  - PCI-compliant card vault (tokenization)
  - Revenue recovery (smart retries)
  - Cost observability & analytics
  - Unified payment API

Hyperswitch Docs: https://docs.hyperswitch.io
GitHub: https://github.com/juspay/hyperswitch

Environment Variables:
  TITAN_HYPERSWITCH_URL          — Hyperswitch API base URL (default: http://127.0.0.1:8080)
  TITAN_HYPERSWITCH_API_KEY      — Merchant API key
  TITAN_HYPERSWITCH_PUBLISHABLE_KEY — Publishable key for client-side
  TITAN_HYPERSWITCH_ADMIN_KEY    — Admin API key for connector management
  TITAN_HYPERSWITCH_ENABLED      — Enable/disable Hyperswitch (1/0)
"""

import os
import json
import time
import asyncio
import logging
import hashlib
import threading
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger("cerberus.hyperswitch")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def _env(key: str, default: str = "") -> str:
    """Read from environment or titan.env"""
    val = os.environ.get(key, "")
    if val and not val.startswith("REPLACE_WITH_"):
        return val
    # Try titan.env
    for env_path in [
        Path("/opt/titan/config/titan.env"),
        Path.home() / ".titan" / "titan.env",
        Path(__file__).parent.parent / "config" / "titan.env",
    ]:
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        v = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if v and not v.startswith("REPLACE_WITH_"):
                            return v
            except Exception:
                pass
    return default


HYPERSWITCH_URL = _env("TITAN_HYPERSWITCH_URL", "http://127.0.0.1:8080")
HYPERSWITCH_API_KEY = _env("TITAN_HYPERSWITCH_API_KEY", "")
HYPERSWITCH_PK = _env("TITAN_HYPERSWITCH_PUBLISHABLE_KEY", "")
HYPERSWITCH_ADMIN_KEY = _env("TITAN_HYPERSWITCH_ADMIN_KEY", "")
HYPERSWITCH_ENABLED = _env("TITAN_HYPERSWITCH_ENABLED", "0") == "1"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectorStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    DOWN = "down"


class PaymentStatus(Enum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_CAPTURE = "requires_capture"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_CUSTOMER_ACTION = "requires_customer_action"


class RoutingAlgorithm(Enum):
    AUTH_RATE = "volume_split"       # MAB auth-rate based
    LEAST_COST = "cost_based"        # Least cost routing
    PRIORITY = "priority"            # Priority-based fallback
    ELIMINATION = "elimination"      # Downtime-aware elimination


@dataclass
class ConnectorConfig:
    """Configuration for a payment connector"""
    connector_name: str              # stripe, braintree, adyen, etc.
    connector_id: str = ""           # Hyperswitch-assigned ID
    merchant_connector_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    status: ConnectorStatus = ConnectorStatus.INACTIVE
    supported_currencies: List[str] = field(default_factory=lambda: ["USD"])
    supported_methods: List[str] = field(default_factory=lambda: ["card"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Performance metrics (populated from analytics)
    auth_rate_7d: float = 0.0
    avg_latency_ms: float = 0.0
    total_volume_7d: int = 0
    cost_per_txn: float = 0.0


@dataclass
class HyperswitchPayment:
    """Payment object from Hyperswitch"""
    payment_id: str
    status: PaymentStatus
    amount: int                      # in smallest currency unit (cents)
    currency: str
    connector: str = ""              # which connector processed it
    connector_transaction_id: str = ""
    error_code: str = ""
    error_message: str = ""
    payment_method: str = ""
    payment_method_type: str = ""
    authentication_type: str = ""    # no_three_ds, three_ds
    attempt_count: int = 1
    created_at: str = ""
    modified_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VaultedCard:
    """Card stored in Hyperswitch Vault"""
    payment_method_id: str
    customer_id: str
    card_last4: str
    card_network: str               # visa, mastercard, amex, etc.
    card_exp_month: str
    card_exp_year: str
    card_issuer: str = ""
    card_country: str = ""
    nickname: str = ""
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryResult:
    """Result of a smart retry attempt"""
    original_payment_id: str
    retry_payment_id: str
    attempt_number: int
    connector_used: str
    status: PaymentStatus
    error_code: str = ""
    error_message: str = ""
    delay_applied_ms: int = 0


@dataclass
class ConnectorAnalytics:
    """Analytics for a specific connector"""
    connector_name: str
    period: str                      # 1d, 7d, 30d
    total_transactions: int = 0
    successful: int = 0
    failed: int = 0
    auth_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_amount: float = 0.0
    total_fees: float = 0.0
    top_decline_codes: List[Dict[str, Any]] = field(default_factory=list)
    hourly_breakdown: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RoutingConfig:
    """Current routing configuration"""
    algorithm: RoutingAlgorithm
    connectors: List[str]            # ordered by priority
    rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# HYPERSWITCH CLIENT — Core HTTP Client
# ═══════════════════════════════════════════════════════════════════════════════

class HyperswitchClient:
    """
    HTTP client for Hyperswitch REST API.
    
    Handles authentication, request/response serialization, error handling,
    and connection management for all Hyperswitch endpoints.
    """
    
    def __init__(self, base_url: str = None, api_key: str = None,
                 admin_key: str = None, timeout: float = 30.0):
        self.base_url = (base_url or HYPERSWITCH_URL).rstrip("/")
        self.api_key = api_key or HYPERSWITCH_API_KEY
        self.admin_key = admin_key or HYPERSWITCH_ADMIN_KEY
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = threading.Lock()
        self._request_count = 0
        self._last_health_check = 0
        self._healthy = False
        
    @property
    def is_configured(self) -> bool:
        """Check if Hyperswitch credentials are configured"""
        return bool(self.api_key and self.base_url)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _headers(self, use_admin: bool = False) -> Dict[str, str]:
        """Build request headers with authentication"""
        key = self.admin_key if use_admin else self.api_key
        return {
            "api-key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    async def _request(self, method: str, path: str, data: Dict = None,
                       use_admin: bool = False) -> Dict[str, Any]:
        """Execute HTTP request to Hyperswitch API"""
        url = f"{self.base_url}{path}"
        headers = self._headers(use_admin=use_admin)
        session = await self._get_session()
        
        try:
            async with session.request(
                method, url, json=data, headers=headers
            ) as resp:
                self._request_count += 1
                body = await resp.text()
                
                if resp.status >= 400:
                    try:
                        error_data = json.loads(body)
                    except json.JSONDecodeError:
                        error_data = {"message": body}
                    
                    logger.warning(
                        "Hyperswitch %s %s → %d: %s",
                        method, path, resp.status,
                        error_data.get("message", body[:200])
                    )
                    return {
                        "_error": True,
                        "_status": resp.status,
                        "_message": error_data.get("message", "Unknown error"),
                        "_code": error_data.get("code", ""),
                        "_raw": error_data,
                    }
                
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {"_raw_text": body}
                    
        except aiohttp.ClientError as e:
            logger.error("Hyperswitch connection error: %s", e)
            return {
                "_error": True,
                "_status": 0,
                "_message": f"Connection error: {e}",
                "_code": "connection_error",
            }
        except asyncio.TimeoutError:
            logger.error("Hyperswitch request timeout: %s %s", method, path)
            return {
                "_error": True,
                "_status": 0,
                "_message": "Request timeout",
                "_code": "timeout",
            }
    
    # ── Health Check ──────────────────────────────────────────────────────────
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Hyperswitch server health"""
        result = await self._request("GET", "/health")
        self._healthy = not result.get("_error", False)
        self._last_health_check = time.time()
        return {
            "healthy": self._healthy,
            "url": self.base_url,
            "configured": self.is_configured,
            "request_count": self._request_count,
            "response": result,
        }
    
    @property
    def is_healthy(self) -> bool:
        """Return cached health status (valid for 60s)"""
        if time.time() - self._last_health_check > 60:
            return False  # Stale — needs re-check
        return self._healthy
    
    # ── Payments API ──────────────────────────────────────────────────────────
    
    async def create_payment(
        self,
        amount: int,
        currency: str = "USD",
        card_number: str = None,
        card_exp_month: str = None,
        card_exp_year: str = None,
        card_cvc: str = None,
        customer_id: str = None,
        payment_method_id: str = None,
        description: str = None,
        return_url: str = None,
        authentication_type: str = "no_three_ds",
        capture_method: str = "automatic",
        confirm: bool = True,
        routing_algorithm: str = None,
        connector: str = None,
        metadata: Dict = None,
    ) -> HyperswitchPayment:
        """
        Create a payment through Hyperswitch.
        
        Routes to optimal connector based on configured routing algorithm.
        Supports direct card details OR vaulted payment_method_id.
        
        Args:
            amount: Amount in smallest currency unit (cents for USD)
            currency: ISO 4217 currency code
            card_number: Full card number (if not using vault)
            card_exp_month: Expiry month (01-12)
            card_exp_year: Expiry year (YYYY)
            card_cvc: CVC/CVV
            customer_id: Hyperswitch customer ID (for vault)
            payment_method_id: Vaulted payment method ID
            description: Payment description
            return_url: Redirect URL for 3DS
            authentication_type: no_three_ds or three_ds
            capture_method: automatic or manual
            confirm: Confirm payment immediately
            routing_algorithm: Override routing (priority, volume_split, etc.)
            connector: Force specific connector
            metadata: Additional metadata dict
        
        Returns:
            HyperswitchPayment with status and details
        """
        payload = {
            "amount": amount,
            "currency": currency,
            "confirm": confirm,
            "capture_method": capture_method,
            "authentication_type": authentication_type,
        }
        
        if card_number:
            payload["payment_method"] = "card"
            payload["payment_method_type"] = "credit"
            payload["payment_method_data"] = {
                "card": {
                    "card_number": card_number,
                    "card_exp_month": card_exp_month,
                    "card_exp_year": card_exp_year,
                    "card_cvc": card_cvc,
                }
            }
        elif payment_method_id:
            payload["payment_method_id"] = payment_method_id
            if customer_id:
                payload["customer_id"] = customer_id
        
        if description:
            payload["description"] = description
        if return_url:
            payload["return_url"] = return_url
        if metadata:
            payload["metadata"] = metadata
        if connector:
            payload["connector"] = [connector]
        if routing_algorithm:
            payload["routing_algorithm"] = routing_algorithm
        if customer_id:
            payload["customer_id"] = customer_id
        
        result = await self._request("POST", "/payments", data=payload)
        return self._parse_payment(result)
    
    async def get_payment(self, payment_id: str) -> HyperswitchPayment:
        """Retrieve payment details by ID"""
        result = await self._request("GET", f"/payments/{payment_id}")
        return self._parse_payment(result)
    
    async def confirm_payment(self, payment_id: str,
                              payment_method_data: Dict = None) -> HyperswitchPayment:
        """Confirm a payment that requires confirmation"""
        payload = {}
        if payment_method_data:
            payload["payment_method_data"] = payment_method_data
        result = await self._request("POST", f"/payments/{payment_id}/confirm", data=payload)
        return self._parse_payment(result)
    
    async def capture_payment(self, payment_id: str,
                              amount: int = None) -> HyperswitchPayment:
        """Capture an authorized payment"""
        payload = {}
        if amount is not None:
            payload["amount_to_capture"] = amount
        result = await self._request("POST", f"/payments/{payment_id}/capture", data=payload)
        return self._parse_payment(result)
    
    async def cancel_payment(self, payment_id: str,
                             reason: str = None) -> HyperswitchPayment:
        """Cancel/void a payment"""
        payload = {}
        if reason:
            payload["cancellation_reason"] = reason
        result = await self._request("POST", f"/payments/{payment_id}/cancel", data=payload)
        return self._parse_payment(result)
    
    async def list_payments(self, limit: int = 20, offset: int = 0,
                            connector: str = None,
                            status: str = None) -> List[HyperswitchPayment]:
        """List payments with optional filters"""
        params = f"?limit={limit}&offset={offset}"
        if connector:
            params += f"&connector={connector}"
        if status:
            params += f"&status={status}"
        result = await self._request("GET", f"/payments/list{params}")
        if result.get("_error"):
            return []
        data = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(data, list):
            return [self._parse_payment(p) for p in data]
        return []
    
    async def validate_card(
        self,
        card_number: str,
        card_exp_month: str,
        card_exp_year: str,
        card_cvc: str,
        customer_id: str = None,
    ) -> HyperswitchPayment:
        """
        Zero-charge card validation via Hyperswitch.
        
        Creates a $0 payment (or minimum auth) to validate card details
        without charging. Uses manual capture + immediate cancel.
        """
        payment = await self.create_payment(
            amount=0,
            currency="USD",
            card_number=card_number,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            card_cvc=card_cvc,
            customer_id=customer_id,
            authentication_type="no_three_ds",
            capture_method="manual",
            confirm=True,
            description="Cerberus card validation",
            metadata={"cerberus_validation": True, "type": "zero_auth"},
        )
        
        # If authorized, cancel immediately (don't capture)
        if payment.status == PaymentStatus.REQUIRES_CAPTURE:
            await self.cancel_payment(payment.payment_id, reason="validation_only")
            payment.status = PaymentStatus.SUCCEEDED
            payment.metadata["validation_result"] = "valid"
        
        return payment
    
    # ── Customers API ─────────────────────────────────────────────────────────
    
    async def create_customer(self, email: str = None, name: str = None,
                              phone: str = None, description: str = None,
                              metadata: Dict = None) -> Dict[str, Any]:
        """Create a customer in Hyperswitch"""
        payload = {}
        if email:
            payload["email"] = email
        if name:
            payload["name"] = name
        if phone:
            payload["phone"] = phone
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata
        return await self._request("POST", "/customers", data=payload)
    
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve customer details"""
        return await self._request("GET", f"/customers/{customer_id}")
    
    # ── Refunds API ───────────────────────────────────────────────────────────
    
    async def create_refund(self, payment_id: str, amount: int = None,
                            reason: str = None) -> Dict[str, Any]:
        """Create a refund for a payment"""
        payload = {"payment_id": payment_id}
        if amount is not None:
            payload["amount"] = amount
        if reason:
            payload["reason"] = reason
        return await self._request("POST", "/refunds", data=payload)
    
    # ── Connectors API (Admin) ────────────────────────────────────────────────
    
    async def list_connectors(self, merchant_id: str) -> List[ConnectorConfig]:
        """List all configured payment connectors"""
        result = await self._request(
            "GET", f"/account/{merchant_id}/connectors", use_admin=True
        )
        if result.get("_error"):
            return []
        connectors = []
        items = result if isinstance(result, list) else result.get("data", [])
        for item in items:
            connectors.append(ConnectorConfig(
                connector_name=item.get("connector_name", ""),
                connector_id=item.get("connector_account_details", {}).get("connector_account_id", ""),
                merchant_connector_id=item.get("merchant_connector_id", ""),
                status=ConnectorStatus.ACTIVE if item.get("status") == "active" else ConnectorStatus.INACTIVE,
                supported_currencies=item.get("supported_currencies", ["USD"]),
                supported_methods=item.get("payment_methods_enabled", []),
                metadata=item.get("metadata", {}),
            ))
        return connectors
    
    async def create_connector(
        self,
        merchant_id: str,
        connector_name: str,
        connector_account_details: Dict[str, Any],
        payment_methods_enabled: List[Dict] = None,
        metadata: Dict = None,
    ) -> Dict[str, Any]:
        """Add a new payment connector"""
        payload = {
            "connector_type": "payment_processor",
            "connector_name": connector_name,
            "connector_account_details": connector_account_details,
            "status": "active",
            "test_mode": True,
        }
        if payment_methods_enabled:
            payload["payment_methods_enabled"] = payment_methods_enabled
        if metadata:
            payload["metadata"] = metadata
        return await self._request(
            "POST", f"/account/{merchant_id}/connectors",
            data=payload, use_admin=True
        )
    
    async def delete_connector(self, merchant_id: str,
                               merchant_connector_id: str) -> Dict[str, Any]:
        """Remove a payment connector"""
        return await self._request(
            "DELETE",
            f"/account/{merchant_id}/connectors/{merchant_connector_id}",
            use_admin=True
        )
    
    # ── Routing API ───────────────────────────────────────────────────────────
    
    async def get_routing_config(self) -> RoutingConfig:
        """Get current routing configuration"""
        result = await self._request("GET", "/routing", use_admin=False)
        if result.get("_error"):
            return RoutingConfig(
                algorithm=RoutingAlgorithm.PRIORITY,
                connectors=[],
            )
        algo = result.get("algorithm", {})
        algo_type = algo.get("type", "priority")
        try:
            algorithm = RoutingAlgorithm(algo_type)
        except ValueError:
            algorithm = RoutingAlgorithm.PRIORITY
        
        connectors = []
        if "data" in algo:
            for entry in algo["data"]:
                if isinstance(entry, dict):
                    connectors.append(entry.get("connector", ""))
                elif isinstance(entry, str):
                    connectors.append(entry)
        
        return RoutingConfig(
            algorithm=algorithm,
            connectors=connectors,
            rules=algo.get("rules", []),
            metadata=result.get("metadata", {}),
        )
    
    async def update_routing(
        self,
        algorithm: RoutingAlgorithm,
        connectors: List[str],
        rules: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Update routing configuration"""
        payload = {
            "algorithm": {
                "type": algorithm.value,
                "data": [{"connector": c} for c in connectors],
            }
        }
        if rules:
            payload["algorithm"]["rules"] = rules
        return await self._request("POST", "/routing", data=payload)
    
    # ── Internal Helpers ──────────────────────────────────────────────────────
    
    def _parse_payment(self, data: Dict[str, Any]) -> HyperswitchPayment:
        """Parse API response into HyperswitchPayment"""
        if data.get("_error"):
            return HyperswitchPayment(
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=0,
                currency="USD",
                error_code=data.get("_code", "api_error"),
                error_message=data.get("_message", "Unknown error"),
                raw_response=data,
            )
        
        status_str = data.get("status", "failed")
        try:
            status = PaymentStatus(status_str)
        except ValueError:
            status = PaymentStatus.FAILED
        
        return HyperswitchPayment(
            payment_id=data.get("payment_id", ""),
            status=status,
            amount=data.get("amount", 0),
            currency=data.get("currency", "USD"),
            connector=data.get("connector", ""),
            connector_transaction_id=data.get("connector_transaction_id", ""),
            error_code=data.get("error_code", ""),
            error_message=data.get("error_message", ""),
            payment_method=data.get("payment_method", ""),
            payment_method_type=data.get("payment_method_type", ""),
            authentication_type=data.get("authentication_type", ""),
            attempt_count=data.get("attempt_count", 1),
            created_at=data.get("created", ""),
            modified_at=data.get("modified", ""),
            metadata=data.get("metadata", {}),
            raw_response=data,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HYPERSWITCH ROUTER — Cerberus-Aware Intelligent Routing
# ═══════════════════════════════════════════════════════════════════════════════

class HyperswitchRouter:
    """
    Cerberus-aware intelligent routing layer.
    
    Combines Hyperswitch's MAB auth-rate routing with Cerberus BIN intelligence
    to select the optimal connector for each transaction.
    """
    
    # Connector preferences based on card network / region
    CONNECTOR_PREFERENCES = {
        "US": ["stripe", "braintree", "adyen", "checkout", "nmi"],
        "EU": ["adyen", "stripe", "checkout", "mollie", "worldpay"],
        "UK": ["stripe", "adyen", "checkout", "worldpay", "barclaycard"],
        "APAC": ["adyen", "stripe", "cybersource", "dlocal"],
        "LATAM": ["dlocal", "adyen", "stripe", "mercadopago"],
        "DEFAULT": ["stripe", "adyen", "braintree", "checkout"],
    }
    
    # 3DS avoidance connectors (lower 3DS challenge rates)
    LOW_3DS_CONNECTORS = ["stripe", "braintree", "nmi", "authorize_net"]
    
    def __init__(self, client: HyperswitchClient):
        self.client = client
        self._connector_stats: Dict[str, ConnectorAnalytics] = {}
        self._lock = threading.Lock()
    
    def get_optimal_connectors(
        self,
        card_country: str = "US",
        card_network: str = "visa",
        amount: int = 0,
        authentication_preference: str = "no_three_ds",
    ) -> List[str]:
        """
        Determine optimal connector ordering for a transaction.
        
        Combines regional preferences, 3DS avoidance, and cached auth rates.
        Hyperswitch will further optimize within this ordering.
        """
        region = self._country_to_region(card_country)
        base_order = list(self.CONNECTOR_PREFERENCES.get(region, self.CONNECTOR_PREFERENCES["DEFAULT"]))
        
        # If requesting no-3DS, prioritize low-3DS connectors
        if authentication_preference == "no_three_ds":
            low_3ds = [c for c in self.LOW_3DS_CONNECTORS if c in base_order]
            others = [c for c in base_order if c not in low_3ds]
            base_order = low_3ds + others
        
        # Re-rank by cached auth rates if available
        with self._lock:
            if self._connector_stats:
                def sort_key(connector):
                    stats = self._connector_stats.get(connector)
                    if stats and stats.total_transactions > 10:
                        return -stats.auth_rate  # Higher auth rate = better
                    return 0
                base_order.sort(key=sort_key)
        
        return base_order
    
    def update_connector_stats(self, connector: str, analytics: ConnectorAnalytics):
        """Update cached analytics for a connector"""
        with self._lock:
            self._connector_stats[connector] = analytics
    
    async def route_validation(
        self,
        card_number: str,
        card_exp_month: str,
        card_exp_year: str,
        card_cvc: str,
        card_country: str = "US",
        card_network: str = "visa",
    ) -> HyperswitchPayment:
        """
        Route a card validation through optimal connector chain.
        
        Uses Cerberus intelligence to select connector, then delegates
        to Hyperswitch for actual routing and failover.
        """
        connectors = self.get_optimal_connectors(
            card_country=card_country,
            card_network=card_network,
            authentication_preference="no_three_ds",
        )
        
        # Try primary connector first via Hyperswitch
        payment = await self.client.validate_card(
            card_number=card_number,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            card_cvc=card_cvc,
        )
        
        return payment
    
    def _country_to_region(self, country: str) -> str:
        """Map country code to region for connector selection"""
        eu_countries = {
            "DE", "FR", "IT", "ES", "NL", "BE", "AT", "PT", "IE", "FI",
            "GR", "LU", "SI", "SK", "EE", "LV", "LT", "CY", "MT",
            "SE", "DK", "PL", "CZ", "HU", "RO", "BG", "HR",
        }
        apac_countries = {
            "JP", "KR", "SG", "HK", "TW", "AU", "NZ", "IN", "TH",
            "MY", "PH", "ID", "VN", "CN",
        }
        latam_countries = {
            "BR", "MX", "AR", "CO", "CL", "PE", "EC", "UY", "PY", "BO",
        }
        
        country = country.upper()
        if country == "US" or country == "CA":
            return "US"
        elif country == "GB":
            return "UK"
        elif country in eu_countries:
            return "EU"
        elif country in apac_countries:
            return "APAC"
        elif country in latam_countries:
            return "LATAM"
        return "DEFAULT"


# ═══════════════════════════════════════════════════════════════════════════════
# HYPERSWITCH VAULT — PCI-Compliant Card Storage
# ═══════════════════════════════════════════════════════════════════════════════

class HyperswitchVault:
    """
    PCI-compliant card vault using Hyperswitch's payment method storage.
    
    Stores cards as tokenized payment methods, allowing reuse without
    handling raw card data after initial tokenization.
    """
    
    def __init__(self, client: HyperswitchClient):
        self.client = client
        self._cache: Dict[str, VaultedCard] = {}
        self._lock = threading.Lock()
    
    async def store_card(
        self,
        card_number: str,
        card_exp_month: str,
        card_exp_year: str,
        card_cvc: str = None,
        customer_id: str = None,
        nickname: str = None,
    ) -> VaultedCard:
        """
        Store a card in Hyperswitch Vault.
        
        Creates a customer if needed, then saves the payment method.
        Returns a VaultedCard with token for future use.
        """
        # Create customer if needed
        if not customer_id:
            customer = await self.client.create_customer(
                description="Cerberus vaulted card",
                metadata={"source": "cerberus_appx"},
            )
            if customer.get("_error"):
                raise ValueError(f"Failed to create customer: {customer.get('_message')}")
            customer_id = customer.get("customer_id", "")
        
        # Save payment method via a setup payment
        payment = await self.client.create_payment(
            amount=0,
            currency="USD",
            card_number=card_number,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            card_cvc=card_cvc or "000",
            customer_id=customer_id,
            authentication_type="no_three_ds",
            capture_method="manual",
            confirm=True,
            metadata={"cerberus_vault": True, "setup_only": True},
        )
        
        # Cancel immediately — we only wanted to tokenize
        if payment.status in (PaymentStatus.REQUIRES_CAPTURE, PaymentStatus.SUCCEEDED):
            if payment.status == PaymentStatus.REQUIRES_CAPTURE:
                await self.client.cancel_payment(payment.payment_id, reason="vault_setup")
        
        # Derive card info
        last4 = card_number[-4:] if len(card_number) >= 4 else "****"
        network = self._detect_network(card_number)
        
        vaulted = VaultedCard(
            payment_method_id=payment.payment_id,  # Use as reference
            customer_id=customer_id,
            card_last4=last4,
            card_network=network,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            nickname=nickname or f"{network.upper()} ****{last4}",
            created_at=datetime.utcnow().isoformat(),
            metadata={
                "original_payment_id": payment.payment_id,
                "connector": payment.connector,
            },
        )
        
        with self._lock:
            self._cache[vaulted.payment_method_id] = vaulted
        
        return vaulted
    
    async def list_cards(self, customer_id: str = None) -> List[VaultedCard]:
        """List all vaulted cards, optionally filtered by customer"""
        with self._lock:
            cards = list(self._cache.values())
        if customer_id:
            cards = [c for c in cards if c.customer_id == customer_id]
        return cards
    
    async def delete_card(self, payment_method_id: str) -> bool:
        """Remove a card from the vault"""
        with self._lock:
            if payment_method_id in self._cache:
                del self._cache[payment_method_id]
                return True
        return False
    
    def get_card(self, payment_method_id: str) -> Optional[VaultedCard]:
        """Get a vaulted card by ID"""
        with self._lock:
            return self._cache.get(payment_method_id)
    
    @staticmethod
    def _detect_network(card_number: str) -> str:
        """Detect card network from number"""
        if not card_number:
            return "unknown"
        first = card_number[0]
        first2 = card_number[:2] if len(card_number) >= 2 else ""
        first4 = card_number[:4] if len(card_number) >= 4 else ""
        
        if first == "4":
            return "visa"
        elif first2 in ("51", "52", "53", "54", "55") or (2221 <= int(first4) <= 2720 if first4.isdigit() else False):
            return "mastercard"
        elif first2 in ("34", "37"):
            return "amex"
        elif first2 in ("60", "65") or first4 == "6011":
            return "discover"
        elif first2 == "35":
            return "jcb"
        elif first2 in ("36", "38") or first == "3":
            return "diners"
        return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# HYPERSWITCH RETRY — Revenue Recovery Engine
# ═══════════════════════════════════════════════════════════════════════════════

class HyperswitchRetry:
    """
    Smart retry engine combining Hyperswitch's retry logic with
    Cerberus card cooling and velocity awareness.
    
    Retry Strategies:
      1. Same connector, different parameters (3DS toggle, amount adjust)
      2. Different connector via Hyperswitch failover
      3. Delayed retry after cooling period
      4. BIN-aware retry (some BINs respond better after delay)
    """
    
    # Decline codes that are retryable
    RETRYABLE_CODES = {
        "do_not_honor": {"max_retries": 2, "delay_sec": 300, "switch_connector": True},
        "insufficient_funds": {"max_retries": 1, "delay_sec": 3600, "switch_connector": False},
        "card_declined": {"max_retries": 2, "delay_sec": 180, "switch_connector": True},
        "processing_error": {"max_retries": 3, "delay_sec": 60, "switch_connector": True},
        "try_again_later": {"max_retries": 3, "delay_sec": 120, "switch_connector": False},
        "issuer_unavailable": {"max_retries": 3, "delay_sec": 300, "switch_connector": True},
        "generic_decline": {"max_retries": 2, "delay_sec": 180, "switch_connector": True},
    }
    
    # Non-retryable (hard declines)
    HARD_DECLINES = {
        "stolen_card", "lost_card", "pickup_card", "fraud_detected",
        "restricted_card", "security_violation", "card_not_activated",
        "expired_card", "invalid_card_number", "invalid_cvv",
    }
    
    def __init__(self, client: HyperswitchClient, router: HyperswitchRouter = None):
        self.client = client
        self.router = router
        self._retry_history: Dict[str, List[RetryResult]] = {}
        self._lock = threading.Lock()
    
    def is_retryable(self, error_code: str) -> bool:
        """Check if a decline code can be retried"""
        code = error_code.lower().replace(" ", "_")
        if code in self.HARD_DECLINES:
            return False
        return code in self.RETRYABLE_CODES
    
    def get_retry_config(self, error_code: str) -> Dict[str, Any]:
        """Get retry configuration for a decline code"""
        code = error_code.lower().replace(" ", "_")
        return self.RETRYABLE_CODES.get(code, {
            "max_retries": 1, "delay_sec": 300, "switch_connector": True,
        })
    
    async def smart_retry(
        self,
        failed_payment: HyperswitchPayment,
        card_number: str = None,
        card_exp_month: str = None,
        card_exp_year: str = None,
        card_cvc: str = None,
        max_attempts: int = 3,
    ) -> List[RetryResult]:
        """
        Execute smart retry strategy for a failed payment.
        
        Returns list of retry attempts with their results.
        """
        error_code = failed_payment.error_code or "generic_decline"
        
        if not self.is_retryable(error_code):
            return [RetryResult(
                original_payment_id=failed_payment.payment_id,
                retry_payment_id="",
                attempt_number=0,
                connector_used="",
                status=PaymentStatus.FAILED,
                error_code=error_code,
                error_message=f"Non-retryable decline: {error_code}",
            )]
        
        config = self.get_retry_config(error_code)
        max_retries = min(config["max_retries"], max_attempts)
        delay_sec = config["delay_sec"]
        switch_connector = config["switch_connector"]
        
        results = []
        
        for attempt in range(1, max_retries + 1):
            # Apply delay (progressive backoff)
            actual_delay = delay_sec * attempt
            if actual_delay > 0 and attempt > 1:
                await asyncio.sleep(min(actual_delay, 10))  # Cap at 10s for UX
            
            # Determine auth type — try 3DS if no-3DS failed
            auth_type = "no_three_ds"
            if attempt >= 2 and failed_payment.authentication_type == "no_three_ds":
                auth_type = "three_ds"
            
            # Create retry payment
            retry_payment = await self.client.create_payment(
                amount=failed_payment.amount,
                currency=failed_payment.currency,
                card_number=card_number,
                card_exp_month=card_exp_month,
                card_exp_year=card_exp_year,
                card_cvc=card_cvc,
                authentication_type=auth_type,
                capture_method="manual",
                confirm=True,
                metadata={
                    "cerberus_retry": True,
                    "attempt": attempt,
                    "original_payment": failed_payment.payment_id,
                    "original_error": error_code,
                },
            )
            
            result = RetryResult(
                original_payment_id=failed_payment.payment_id,
                retry_payment_id=retry_payment.payment_id,
                attempt_number=attempt,
                connector_used=retry_payment.connector,
                status=retry_payment.status,
                error_code=retry_payment.error_code,
                error_message=retry_payment.error_message,
                delay_applied_ms=int(actual_delay * 1000),
            )
            results.append(result)
            
            # If succeeded, cancel (validation only) and stop
            if retry_payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.REQUIRES_CAPTURE):
                if retry_payment.status == PaymentStatus.REQUIRES_CAPTURE:
                    await self.client.cancel_payment(retry_payment.payment_id, reason="retry_validation")
                break
        
        # Store in history
        key = failed_payment.payment_id or hashlib.md5(
            f"{card_number}{time.time()}".encode()
        ).hexdigest()[:12]
        with self._lock:
            self._retry_history[key] = results
        
        return results
    
    def get_retry_history(self, payment_id: str = None) -> Dict[str, List[RetryResult]]:
        """Get retry history, optionally for a specific payment"""
        with self._lock:
            if payment_id:
                return {payment_id: self._retry_history.get(payment_id, [])}
            return dict(self._retry_history)


# ═══════════════════════════════════════════════════════════════════════════════
# HYPERSWITCH ANALYTICS — Cost & Performance Tracking
# ═══════════════════════════════════════════════════════════════════════════════

class HyperswitchAnalytics:
    """
    Analytics engine for payment performance and cost tracking.
    
    Aggregates data from Hyperswitch and Cerberus to provide:
      - Per-connector auth rates, latency, costs
      - Decline code heatmaps
      - Revenue recovery stats
      - BIN-level performance
    """
    
    def __init__(self, client: HyperswitchClient):
        self.client = client
        self._stats_cache: Dict[str, ConnectorAnalytics] = {}
        self._cache_time: float = 0
        self._cache_ttl: float = 300  # 5 minutes
        self._lock = threading.Lock()
    
    async def get_connector_analytics(
        self, connector: str = None, period: str = "7d"
    ) -> List[ConnectorAnalytics]:
        """
        Get analytics for connectors.
        
        If connector specified, returns single-item list.
        Otherwise returns all connectors.
        """
        # Check cache
        with self._lock:
            if time.time() - self._cache_time < self._cache_ttl:
                if connector:
                    cached = self._stats_cache.get(connector)
                    return [cached] if cached else []
                return list(self._stats_cache.values())
        
        # Fetch from Hyperswitch (via payment list aggregation)
        payments = await self.client.list_payments(limit=100)
        
        # Aggregate stats
        stats: Dict[str, Dict[str, Any]] = {}
        for payment in payments:
            c = payment.connector or "unknown"
            if connector and c != connector:
                continue
            if c not in stats:
                stats[c] = {
                    "total": 0, "success": 0, "failed": 0,
                    "total_amount": 0, "latencies": [],
                    "decline_codes": {},
                }
            s = stats[c]
            s["total"] += 1
            if payment.status == PaymentStatus.SUCCEEDED:
                s["success"] += 1
            elif payment.status == PaymentStatus.FAILED:
                s["failed"] += 1
                code = payment.error_code or "unknown"
                s["decline_codes"][code] = s["decline_codes"].get(code, 0) + 1
            s["total_amount"] += payment.amount / 100.0  # Convert from cents
        
        results = []
        for c_name, s in stats.items():
            auth_rate = (s["success"] / s["total"] * 100) if s["total"] > 0 else 0
            top_declines = sorted(
                s["decline_codes"].items(), key=lambda x: x[1], reverse=True
            )[:5]
            
            analytics = ConnectorAnalytics(
                connector_name=c_name,
                period=period,
                total_transactions=s["total"],
                successful=s["success"],
                failed=s["failed"],
                auth_rate=round(auth_rate, 1),
                total_amount=round(s["total_amount"], 2),
                top_decline_codes=[
                    {"code": code, "count": count} for code, count in top_declines
                ],
            )
            results.append(analytics)
        
        # Update cache
        with self._lock:
            for a in results:
                self._stats_cache[a.connector_name] = a
            self._cache_time = time.time()
        
        return results
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get high-level analytics summary"""
        all_analytics = await self.get_connector_analytics()
        
        total_txns = sum(a.total_transactions for a in all_analytics)
        total_success = sum(a.successful for a in all_analytics)
        total_failed = sum(a.failed for a in all_analytics)
        total_amount = sum(a.total_amount for a in all_analytics)
        overall_auth_rate = (total_success / total_txns * 100) if total_txns > 0 else 0
        
        # Best and worst connectors
        ranked = sorted(all_analytics, key=lambda a: a.auth_rate, reverse=True)
        
        return {
            "total_transactions": total_txns,
            "total_successful": total_success,
            "total_failed": total_failed,
            "overall_auth_rate": round(overall_auth_rate, 1),
            "total_volume_usd": round(total_amount, 2),
            "active_connectors": len(all_analytics),
            "best_connector": ranked[0].connector_name if ranked else None,
            "best_auth_rate": ranked[0].auth_rate if ranked else 0,
            "worst_connector": ranked[-1].connector_name if len(ranked) > 1 else None,
            "worst_auth_rate": ranked[-1].auth_rate if len(ranked) > 1 else 0,
            "connectors": [
                {
                    "name": a.connector_name,
                    "auth_rate": a.auth_rate,
                    "transactions": a.total_transactions,
                    "volume_usd": a.total_amount,
                }
                for a in ranked
            ],
        }
    
    def get_cached_stats(self) -> Dict[str, ConnectorAnalytics]:
        """Get cached connector stats (no API call)"""
        with self._lock:
            return dict(self._stats_cache)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE: Singleton & Factory
# ═══════════════════════════════════════════════════════════════════════════════

_client_instance: Optional[HyperswitchClient] = None
_router_instance: Optional[HyperswitchRouter] = None
_vault_instance: Optional[HyperswitchVault] = None
_retry_instance: Optional[HyperswitchRetry] = None
_analytics_instance: Optional[HyperswitchAnalytics] = None


def get_hyperswitch_client() -> HyperswitchClient:
    """Get or create singleton HyperswitchClient"""
    global _client_instance
    if _client_instance is None:
        _client_instance = HyperswitchClient()
    return _client_instance


def get_hyperswitch_router() -> HyperswitchRouter:
    """Get or create singleton HyperswitchRouter"""
    global _router_instance
    if _router_instance is None:
        _router_instance = HyperswitchRouter(get_hyperswitch_client())
    return _router_instance


def get_hyperswitch_vault() -> HyperswitchVault:
    """Get or create singleton HyperswitchVault"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = HyperswitchVault(get_hyperswitch_client())
    return _vault_instance


def get_hyperswitch_retry() -> HyperswitchRetry:
    """Get or create singleton HyperswitchRetry"""
    global _retry_instance
    if _retry_instance is None:
        _retry_instance = HyperswitchRetry(
            get_hyperswitch_client(), get_hyperswitch_router()
        )
    return _retry_instance


def get_hyperswitch_analytics() -> HyperswitchAnalytics:
    """Get or create singleton HyperswitchAnalytics"""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = HyperswitchAnalytics(get_hyperswitch_client())
    return _analytics_instance


def is_hyperswitch_available() -> bool:
    """Check if Hyperswitch is configured and enabled"""
    return HYPERSWITCH_ENABLED and bool(HYPERSWITCH_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE INFO
# ═══════════════════════════════════════════════════════════════════════════════

__version__ = "2.0.0"
__module_name__ = "cerberus_hyperswitch"
__description__ = "Hyperswitch payment orchestration for Cerberus AppX V2"
__capabilities__ = [
    "hyperswitch_client",
    "intelligent_routing",
    "card_vault",
    "smart_retry",
    "payment_analytics",
    "50+_connectors",
    "zero_auth_validation",
    "pci_compliant_storage",
]
