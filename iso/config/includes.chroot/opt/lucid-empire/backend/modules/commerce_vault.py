#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LUCID EMPIRE v7.0.0-TITAN :: COMMERCE VAULT MODULE                          ║
║  Trust Token Engineering for Payment Gateway Evasion                         ║
║  Authority: Dva.12 | Classification: ZERO DETECT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Implements trust token generation and injection for commerce platforms:
- Stripe Radar: __stripe_mid, __stripe_sid tokens
- Adyen: _RP_UID, adyen-device-fingerprint
- PayPal: TLTSID, targeted device fingerprint

Reference: Stripe Radar Advanced Fraud Detection whitepaper
"""

import hashlib
import json
import random
import secrets
import string
import struct
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from base64 import b64encode, b64decode


# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE TOKEN ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StripeTokenConfig:
    """Configuration for Stripe token generation"""
    
    # Profile binding
    profile_uuid: str
    
    # Token aging (backdated)
    token_age_days: int = 60  # T-60 days from now
    
    # Device consistency
    device_id: str = None
    browser_fingerprint: str = None
    
    # Merchant binding (optional)
    merchant_account: str = None
    
    def __post_init__(self):
        if self.device_id is None:
            self.device_id = self._generate_device_id()
        if self.browser_fingerprint is None:
            self.browser_fingerprint = self._generate_fingerprint()
    
    def _generate_device_id(self) -> str:
        """Generate deterministic device ID from profile UUID"""
        hash_bytes = hashlib.sha256(f"device:{self.profile_uuid}".encode()).digest()
        return hash_bytes[:16].hex()
    
    def _generate_fingerprint(self) -> str:
        """Generate browser fingerprint hash"""
        hash_bytes = hashlib.sha256(f"fp:{self.profile_uuid}".encode()).digest()
        return hash_bytes[:20].hex()


class StripeTokenGenerator:
    """
    Generates Stripe trust tokens that appear legitimately aged.
    
    Token anatomy:
    - __stripe_mid: Machine ID (persistent device identifier)
    - __stripe_sid: Session ID (refreshed per session)
    
    Both contain embedded timestamps and cryptographic signatures.
    """
    
    # Token version constants
    MID_VERSION = "v3"
    SID_VERSION = "v2"
    
    def __init__(self, config: StripeTokenConfig):
        self.config = config
        self.rng = random.Random(config.profile_uuid)
    
    def generate_mid(self, backdated_days: int = None) -> Dict:
        """
        Generate __stripe_mid token.
        
        Format: {version}|{timestamp}|{device_hash}|{signature}
        Base64 encoded
        """
        if backdated_days is None:
            backdated_days = self.config.token_age_days
        
        # Calculate backdated timestamp
        created_at = datetime.now() - timedelta(days=backdated_days)
        timestamp = int(created_at.timestamp() * 1000)  # Milliseconds
        
        # Device hash (deterministic from profile)
        device_hash = self.config.device_id
        
        # Generate signature (simulated HMAC)
        sig_data = f"{timestamp}|{device_hash}".encode()
        signature = hashlib.sha256(sig_data).hexdigest()[:32]
        
        # Assemble token
        token_parts = [
            self.MID_VERSION,
            str(timestamp),
            device_hash,
            signature
        ]
        token_raw = "|".join(token_parts)
        token = b64encode(token_raw.encode()).decode()
        
        return {
            "name": "__stripe_mid",
            "value": token,
            "created_at": created_at.isoformat(),
            "age_days": backdated_days,
            "domain": ".stripe.com",
            "secure": True,
            "http_only": False,
            "same_site": "None"
        }
    
    def generate_sid(self, mid_token: str = None) -> Dict:
        """
        Generate __stripe_sid token (session token).
        
        Format: {version}|{session_id}|{mid_ref}|{timestamp}|{signature}
        """
        # Session ID is random but deterministic for profile
        session_id = hashlib.sha256(
            f"session:{self.config.profile_uuid}:{time.time()}".encode()
        ).hexdigest()[:24]
        
        # Reference to MID
        mid_ref = self.config.device_id[:8] if mid_token is None else mid_token[:8]
        
        # Current timestamp (session tokens aren't backdated)
        timestamp = int(time.time() * 1000)
        
        # Signature
        sig_data = f"{session_id}|{mid_ref}|{timestamp}".encode()
        signature = hashlib.sha256(sig_data).hexdigest()[:24]
        
        token_parts = [
            self.SID_VERSION,
            session_id,
            mid_ref,
            str(timestamp),
            signature
        ]
        token_raw = "|".join(token_parts)
        token = b64encode(token_raw.encode()).decode()
        
        return {
            "name": "__stripe_sid",
            "value": token,
            "created_at": datetime.now().isoformat(),
            "domain": ".stripe.com",
            "secure": True,
            "http_only": False,
            "same_site": "None",
            "session": True  # Expires with session
        }
    
    def generate_device_data(self) -> Dict:
        """
        Generate Stripe device data object.
        
        This is sent via Stripe.js during checkout.
        """
        return {
            "device_id": self.config.device_id,
            "browser_fingerprint": self.config.browser_fingerprint,
            "browser_language": "en-US",
            "screen_dimensions": "1920x1080",
            "timezone_offset": -300,  # EST
            "user_agent_hash": hashlib.sha256(
                f"ua:{self.config.profile_uuid}".encode()
            ).hexdigest()[:32],
            "referrer": "",
            "charging": False,
            "connection_type": "wifi"
        }
    
    def generate_all_tokens(self) -> Dict:
        """Generate complete Stripe token set"""
        mid = self.generate_mid()
        sid = self.generate_sid(mid["value"])
        device = self.generate_device_data()
        
        return {
            "cookies": [mid, sid],
            "device_data": device,
            "profile_uuid": self.config.profile_uuid
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ADYEN TOKEN ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AdyenTokenConfig:
    """Configuration for Adyen token generation"""
    
    profile_uuid: str
    token_age_days: int = 45
    
    # 3DS2 data
    browser_info: Dict = None
    
    def __post_init__(self):
        if self.browser_info is None:
            self.browser_info = self._default_browser_info()
    
    def _default_browser_info(self) -> Dict:
        """Default 3DS2 browser info"""
        return {
            "acceptHeader": "*/*",
            "colorDepth": 24,
            "javaEnabled": False,
            "language": "en-US",
            "screenHeight": 1080,
            "screenWidth": 1920,
            "timeZoneOffset": -300,
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }


class AdyenTokenGenerator:
    """
    Generates Adyen fraud prevention tokens.
    
    Key tokens:
    - _RP_UID: Risk Prevention User ID
    - adyenDeviceFingerprint: Device fingerprint for 3DS2
    """
    
    def __init__(self, config: AdyenTokenConfig):
        self.config = config
        self.rng = random.Random(config.profile_uuid)
    
    def generate_rp_uid(self) -> Dict:
        """
        Generate _RP_UID cookie.
        
        Format: {device_id}-{timestamp}-{random}
        """
        # Deterministic device ID
        device_id = hashlib.sha256(
            f"adyen:device:{self.config.profile_uuid}".encode()
        ).hexdigest()[:12]
        
        # Backdated timestamp
        created_at = datetime.now() - timedelta(days=self.config.token_age_days)
        timestamp = hex(int(created_at.timestamp()))[2:]
        
        # Random component (deterministic)
        random_part = ''.join(
            self.rng.choices(string.ascii_lowercase + string.digits, k=8)
        )
        
        token = f"{device_id}-{timestamp}-{random_part}"
        
        return {
            "name": "_RP_UID",
            "value": token,
            "created_at": created_at.isoformat(),
            "age_days": self.config.token_age_days,
            "domain": ".adyen.com",
            "secure": True,
            "http_only": True,
            "same_site": "Lax"
        }
    
    def generate_device_fingerprint(self) -> str:
        """
        Generate Adyen device fingerprint for 3DS2.
        
        This is a base64-encoded JSON object.
        """
        fingerprint_data = {
            "deviceId": hashlib.sha256(
                f"adyen:fp:{self.config.profile_uuid}".encode()
            ).hexdigest()[:32],
            "screenInfo": f"{self.config.browser_info['screenWidth']}x{self.config.browser_info['screenHeight']}x{self.config.browser_info['colorDepth']}",
            "timezoneOffset": self.config.browser_info["timeZoneOffset"],
            "language": self.config.browser_info["language"],
            "javaEnabled": self.config.browser_info["javaEnabled"],
            "jsPayload": hashlib.md5(self.config.profile_uuid.encode()).hexdigest(),
            "httpAcceptHeaders": self.config.browser_info["acceptHeader"]
        }
        
        return b64encode(json.dumps(fingerprint_data).encode()).decode()
    
    def generate_3ds2_data(self) -> Dict:
        """Generate complete 3DS2 authentication data"""
        return {
            "browserInfo": {
                **self.config.browser_info,
                "javaScriptEnabled": True
            },
            "deviceFingerprint": self.generate_device_fingerprint(),
            "channel": "Web",
            "notificationURL": ""  # Set by merchant
        }
    
    def generate_all_tokens(self) -> Dict:
        """Generate complete Adyen token set"""
        return {
            "cookies": [self.generate_rp_uid()],
            "device_fingerprint": self.generate_device_fingerprint(),
            "3ds2_data": self.generate_3ds2_data(),
            "profile_uuid": self.config.profile_uuid
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PAYPAL TOKEN ENGINEERING  
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass 
class PayPalTokenConfig:
    """Configuration for PayPal token generation"""
    
    profile_uuid: str
    token_age_days: int = 90
    locale: str = "en_US"


class PayPalTokenGenerator:
    """
    Generates PayPal fraud prevention tokens.
    
    Key tokens:
    - TLTSID: Long-term session ID
    - tsrce: Traffic source tracking
    - x-pp-s: Session signature
    """
    
    def __init__(self, config: PayPalTokenConfig):
        self.config = config
        self.rng = random.Random(config.profile_uuid)
    
    def generate_tltsid(self) -> Dict:
        """Generate TLTSID (long-term tracking cookie)"""
        
        # Backdated creation
        created_at = datetime.now() - timedelta(days=self.config.token_age_days)
        
        # Format: UUID-like with embedded timestamp
        id_part = uuid.UUID(
            int=int(hashlib.sha256(self.config.profile_uuid.encode()).hexdigest()[:32], 16)
        )
        
        timestamp_part = hex(int(created_at.timestamp()))[2:]
        
        token = f"{id_part}:{timestamp_part}"
        
        return {
            "name": "TLTSID",
            "value": token,
            "created_at": created_at.isoformat(),
            "age_days": self.config.token_age_days,
            "domain": ".paypal.com",
            "secure": True,
            "http_only": True,
            "same_site": "Lax"
        }
    
    def generate_session_signature(self) -> Dict:
        """Generate x-pp-s session signature"""
        
        # Current session signature
        sig_data = f"{self.config.profile_uuid}:{time.time()}".encode()
        signature = hashlib.sha256(sig_data).hexdigest()[:40]
        
        return {
            "name": "x-pp-s",
            "value": signature,
            "domain": ".paypal.com",
            "secure": True,
            "http_only": True,
            "session": True
        }
    
    def generate_all_tokens(self) -> Dict:
        """Generate complete PayPal token set"""
        return {
            "cookies": [
                self.generate_tltsid(),
                self.generate_session_signature()
            ],
            "locale": self.config.locale,
            "profile_uuid": self.config.profile_uuid
        }


# ═══════════════════════════════════════════════════════════════════════════════
# COMMERCE VAULT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CommerceVault:
    """
    Unified manager for all commerce trust tokens.
    
    Generates and manages tokens for:
    - Stripe (Radar)
    - Adyen (3DS2, Risk Prevention)
    - PayPal (TLTSID)
    """
    
    def __init__(self, profile_uuid: str, profile_dir: Path = None):
        self.profile_uuid = profile_uuid
        self.profile_dir = profile_dir or Path("./lucid_profile_data")
        
        # Initialize generators
        self.stripe = StripeTokenGenerator(StripeTokenConfig(profile_uuid))
        self.adyen = AdyenTokenGenerator(AdyenTokenConfig(profile_uuid))
        self.paypal = PayPalTokenGenerator(PayPalTokenConfig(profile_uuid))
    
    def generate_all_tokens(self) -> Dict:
        """Generate complete token set for all commerce platforms"""
        return {
            "stripe": self.stripe.generate_all_tokens(),
            "adyen": self.adyen.generate_all_tokens(),
            "paypal": self.paypal.generate_all_tokens(),
            "profile_uuid": self.profile_uuid,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_cookies_for_domain(self, domain: str) -> List[Dict]:
        """
        Get relevant cookies for a specific domain.
        
        Args:
            domain: Target domain (e.g., 'stripe.com', 'amazon.com')
            
        Returns:
            List of cookie configurations
        """
        all_cookies = []
        
        # Get all tokens
        tokens = self.generate_all_tokens()
        
        # Stripe cookies
        if 'stripe' in domain.lower() or domain.endswith('.com'):
            all_cookies.extend(tokens["stripe"]["cookies"])
        
        # Adyen cookies (used by many merchants)
        if 'adyen' in domain.lower() or domain.endswith('.com'):
            all_cookies.extend(tokens["adyen"]["cookies"])
        
        # PayPal cookies
        if 'paypal' in domain.lower():
            all_cookies.extend(tokens["paypal"]["cookies"])
        
        return all_cookies
    
    def export_to_file(self, path: Path = None) -> Path:
        """Export all tokens to JSON file"""
        if path is None:
            config_dir = self.profile_dir / self.profile_uuid
            config_dir.mkdir(parents=True, exist_ok=True)
            path = config_dir / "commerce_vault.json"
        
        tokens = self.generate_all_tokens()
        
        with open(path, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        return path
    
    def inject_cookies_format(self) -> List[Dict]:
        """
        Get cookies in browser injection format.
        
        Returns cookies ready for Playwright/Puppeteer cookie injection.
        """
        all_cookies = []
        tokens = self.generate_all_tokens()
        
        for platform, data in [("stripe", tokens["stripe"]), 
                               ("adyen", tokens["adyen"]),
                               ("paypal", tokens["paypal"])]:
            for cookie in data.get("cookies", []):
                all_cookies.append({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": "/",
                    "secure": cookie.get("secure", True),
                    "httpOnly": cookie.get("http_only", False),
                    "sameSite": cookie.get("same_site", "None"),
                    "expires": self._calculate_expiry(cookie)
                })
        
        return all_cookies
    
    def _calculate_expiry(self, cookie: Dict) -> int:
        """Calculate cookie expiry timestamp"""
        if cookie.get("session"):
            return -1  # Session cookie
        
        # Default: 1 year from now
        return int((datetime.now() + timedelta(days=365)).timestamp())


# ═══════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("LUCID EMPIRE - COMMERCE VAULT MODULE TEST")
    print("=" * 70)
    
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Test Stripe tokens
    print("\n[1] Testing Stripe Token Generation...")
    stripe_config = StripeTokenConfig(profile_uuid=test_uuid)
    stripe_gen = StripeTokenGenerator(stripe_config)
    
    mid = stripe_gen.generate_mid()
    print(f"    __stripe_mid: {mid['value'][:50]}...")
    print(f"    Created: {mid['created_at']}")
    print(f"    Age: {mid['age_days']} days")
    
    sid = stripe_gen.generate_sid()
    print(f"    __stripe_sid: {sid['value'][:50]}...")
    
    # Test Adyen tokens
    print("\n[2] Testing Adyen Token Generation...")
    adyen_config = AdyenTokenConfig(profile_uuid=test_uuid)
    adyen_gen = AdyenTokenGenerator(adyen_config)
    
    rp_uid = adyen_gen.generate_rp_uid()
    print(f"    _RP_UID: {rp_uid['value']}")
    
    device_fp = adyen_gen.generate_device_fingerprint()
    print(f"    Device Fingerprint: {device_fp[:50]}...")
    
    # Test PayPal tokens
    print("\n[3] Testing PayPal Token Generation...")
    paypal_config = PayPalTokenConfig(profile_uuid=test_uuid)
    paypal_gen = PayPalTokenGenerator(paypal_config)
    
    tltsid = paypal_gen.generate_tltsid()
    print(f"    TLTSID: {tltsid['value']}")
    
    # Test Commerce Vault
    print("\n[4] Testing Commerce Vault Manager...")
    vault = CommerceVault(test_uuid)
    
    all_tokens = vault.generate_all_tokens()
    print(f"    Generated tokens for {len(all_tokens) - 2} platforms")
    
    # Test cookie injection format
    injection_cookies = vault.inject_cookies_format()
    print(f"    Total injectable cookies: {len(injection_cookies)}")
    
    for cookie in injection_cookies[:3]:
        print(f"      - {cookie['name']}: {cookie['domain']}")
    
    # Export to file
    export_path = vault.export_to_file()
    print(f"\n[5] Exported to: {export_path}")
    
    print("\n" + "=" * 70)
    print("COMMERCE VAULT MODULE: OPERATIONAL")
    print("=" * 70)
