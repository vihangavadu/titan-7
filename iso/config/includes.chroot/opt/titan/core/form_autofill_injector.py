"""
TITAN V8.1 SINGULARITY - Form Autofill Injector
Injects form history and saved payment methods for zero-decline

Critical for:
1. Autofill triggers trust signals (vs paste/keypress)
2. Saved payment method = "Use saved card?" prompt
3. Form history shows established user pattern

Reference: Advanced Identity Injection Protocol - "Use saved card ending in 8921?"
"""

import json
import sqlite3
import secrets
import hashlib
import base64
import os
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("TITAN-V7-AUTOFILL")


def _fx_sqlite(db_path, page_size=32768):
    """SQLite connection with Firefox-matching PRAGMA settings."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"PRAGMA page_size = {page_size}")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA auto_vacuum = INCREMENTAL")
    c.execute("PRAGMA wal_autocheckpoint = 512")
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn


@dataclass
class PersonaAutofill:
    """Persona autofill data for form injection"""
    full_name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    address_line1: str
    address_line2: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "US"
    
    # Card info (last 4 only for display, full for autofill)
    card_last4: str = ""
    card_exp_month: str = ""
    card_exp_year: str = ""
    card_type: str = "visa"  # visa, mastercard, amex


@dataclass
class FormHistoryEntry:
    """Single form history entry"""
    field_name: str
    value: str
    times_used: int = 1
    first_used: Optional[datetime] = None
    last_used: Optional[datetime] = None


class FormAutofillInjector:
    """
    Injects form autofill data into Firefox profile.
    
    Creates:
    - formhistory.sqlite - Form field history
    - autofill-profiles.json - Address autofill
    - logins.json - Saved credentials (optional)
    
    Usage:
        injector = FormAutofillInjector(profile_path)
        
        persona = PersonaAutofill(
            full_name="Alex J. Mercer",
            first_name="Alex",
            last_name="Mercer",
            email="a.mercer.dev@gmail.com",
            phone="512-555-0123",
            address_line1="2400 NUECES ST",
            address_line2="APT 402",
            city="AUSTIN",
            state="TX",
            zip_code="78705",
            card_last4="8921",
            card_exp_month="12",
            card_exp_year="2027"
        )
        
        injector.inject_all(persona, age_days=90)
    """
    
    def __init__(self, profile_path: str):
        self.profile_path = Path(profile_path)
        self.profile_path.mkdir(parents=True, exist_ok=True)
        self._rng = None  # Seeded per inject_all call
    
    def inject_all(self, persona: PersonaAutofill, age_days: int = 90):
        """Inject all autofill data"""
        # Seed RNG from persona for deterministic autofill data
        seed_str = f"{persona.full_name}_{persona.email}_{age_days}"
        seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16)
        self._rng = random.Random(seed)
        random.seed(seed)
        
        self.inject_form_history(persona, age_days)
        self.inject_autofill_profiles(persona, age_days)
        self.inject_saved_addresses(persona, age_days)
        # V7.5 FIX: Also inject card hint if card data is present
        if persona.card_last4:
            self.inject_credit_card_hint(persona, age_days)
        logger.info(f"[+] Autofill data injected for {persona.full_name}")
    
    def inject_form_history(self, persona: PersonaAutofill, age_days: int = 90):
        """
        Inject form history into formhistory.sqlite.
        
        This populates the autocomplete dropdown for form fields.
        """
        db_path = self.profile_path / "formhistory.sqlite"
        conn = _fx_sqlite(db_path)
        cursor = conn.cursor()
        
        # Create schema
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS moz_formhistory (
                id INTEGER PRIMARY KEY,
                fieldname TEXT NOT NULL,
                value TEXT NOT NULL,
                timesUsed INTEGER DEFAULT 1,
                firstUsed INTEGER,
                lastUsed INTEGER,
                guid TEXT
            );
            
            CREATE INDEX IF NOT EXISTS moz_formhistory_index 
            ON moz_formhistory (fieldname);
            
            CREATE INDEX IF NOT EXISTS moz_formhistory_lastused_index 
            ON moz_formhistory (lastUsed);
            
            CREATE TABLE IF NOT EXISTS moz_deleted_formhistory (
                id INTEGER PRIMARY KEY,
                timeDeleted INTEGER,
                guid TEXT
            );
        """)
        
        base_time = datetime.now(timezone.utc)
        first_used = base_time - timedelta(days=age_days)
        
        # Common form field names and values
        form_entries = [
            # Name fields
            ("name", persona.full_name, 15),
            ("full-name", persona.full_name, 12),
            ("fullname", persona.full_name, 8),
            ("first-name", persona.first_name, 10),
            ("firstname", persona.first_name, 8),
            ("last-name", persona.last_name, 10),
            ("lastname", persona.last_name, 8),
            ("given-name", persona.first_name, 5),
            ("family-name", persona.last_name, 5),
            
            # Email fields
            ("email", persona.email, 25),
            ("email-address", persona.email, 8),
            ("emailaddress", persona.email, 5),
            ("e-mail", persona.email, 3),
            
            # Phone fields
            ("phone", persona.phone, 10),
            ("telephone", persona.phone, 5),
            ("tel", persona.phone, 8),
            ("phone-number", persona.phone, 6),
            ("mobile", persona.phone, 4),
            
            # Address fields
            ("address", persona.address_line1, 12),
            ("address-line1", persona.address_line1, 10),
            ("address1", persona.address_line1, 8),
            ("street-address", persona.address_line1, 6),
            ("address-line2", persona.address_line2, 8) if persona.address_line2 else None,
            ("address2", persona.address_line2, 5) if persona.address_line2 else None,
            ("apt", persona.address_line2, 4) if persona.address_line2 else None,
            
            # City/State/Zip
            ("city", persona.city, 12),
            ("locality", persona.city, 5),
            ("state", persona.state, 12),
            ("region", persona.state, 5),
            ("province", persona.state, 3),
            ("zip", persona.zip_code, 12),
            ("postal-code", persona.zip_code, 10),
            ("postalcode", persona.zip_code, 8),
            ("zipcode", persona.zip_code, 6),
            
            # Country
            ("country", persona.country, 10),
            ("country-code", persona.country, 5),
        ]
        
        for entry in form_entries:
            if entry is None:
                continue
            
            field_name, value, times_used = entry
            if not value:
                continue
            
            # Randomize timestamps
            first_ts = int((first_used + timedelta(days=random.randint(0, 30))).timestamp() * 1000000)
            last_ts = int((base_time - timedelta(days=random.randint(0, 7))).timestamp() * 1000000)
            # V7.5 FIX: Use URL-safe Base64 GUID to match Firefox format
            guid = secrets.token_urlsafe(9)[:12]
            
            cursor.execute("""
                INSERT INTO moz_formhistory 
                (fieldname, value, timesUsed, firstUsed, lastUsed, guid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (field_name, value, times_used, first_ts, last_ts, guid))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[+] Form history injected: {len([e for e in form_entries if e])} entries")
    
    def inject_autofill_profiles(self, persona: PersonaAutofill, age_days: int = 90):
        """
        Inject autofill profiles for Firefox.
        
        Creates autofill-profiles.json with address data.
        """
        base_time = datetime.now(timezone.utc)
        created = base_time - timedelta(days=age_days)
        
        profile = {
            "guid": secrets.token_urlsafe(9)[:12],
            "version": 3,
            "timeCreated": int(created.timestamp() * 1000),
            "timeLastUsed": int((base_time - timedelta(days=2)).timestamp() * 1000),
            "timeLastModified": int((base_time - timedelta(days=30)).timestamp() * 1000),
            "timesUsed": random.randint(5, 20),
            
            "given-name": persona.first_name,
            "additional-name": "",
            "family-name": persona.last_name,
            "name": persona.full_name,
            
            "organization": "",
            
            "street-address": f"{persona.address_line1}\n{persona.address_line2}".strip(),
            "address-line1": persona.address_line1,
            "address-line2": persona.address_line2,
            "address-line3": "",
            "address-level1": persona.state,
            "address-level2": persona.city,
            "postal-code": persona.zip_code,
            "country": persona.country,
            "country-name": "United States" if persona.country == "US" else persona.country,
            
            "tel": persona.phone,
            "tel-country-code": "+1" if persona.country == "US" else "",
            "tel-national": persona.phone,
            
            "email": persona.email,
        }
        
        autofill_data = {
            "version": 1,
            "addresses": [profile]
        }
        
        autofill_file = self.profile_path / "autofill-profiles.json"
        with open(autofill_file, "w") as f:
            json.dump(autofill_data, f, indent=2)
        
        logger.info(f"[+] Autofill profile created: {persona.full_name}")
    
    def inject_saved_addresses(self, persona: PersonaAutofill, age_days: int = 90):
        """
        Inject saved addresses into Firefox's storage.
        
        Uses the newer storage format for address autofill.
        """
        storage_dir = self.profile_path / "storage" / "permanent" / "chrome"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create formautofill storage
        autofill_dir = storage_dir / "formautofill"
        autofill_dir.mkdir(parents=True, exist_ok=True)
        
        base_time = datetime.now(timezone.utc)
        created = base_time - timedelta(days=age_days)
        
        address_record = {
            "guid": secrets.token_urlsafe(9)[:12],
            "version": 3,
            "timeCreated": int(created.timestamp() * 1000),
            "timeLastUsed": int((base_time - timedelta(days=1)).timestamp() * 1000),
            "timeLastModified": int((base_time - timedelta(days=15)).timestamp() * 1000),
            "timesUsed": random.randint(8, 25),
            "given-name": persona.first_name,
            "family-name": persona.last_name,
            "street-address": persona.address_line1,
            "address-level2": persona.city,
            "address-level1": persona.state,
            "postal-code": persona.zip_code,
            "country": persona.country,
            "tel": persona.phone,
            "email": persona.email,
        }
        
        # Write to JSON storage
        addresses_file = autofill_dir / "addresses.json"
        with open(addresses_file, "w") as f:
            json.dump({"addresses": [address_record]}, f, indent=2)
    
    def inject_credit_card_hint(self, persona: PersonaAutofill, age_days: int = 90):
        """
        Inject credit card hint for autofill prompt.
        
        NOTE: This creates a hint that triggers "Use saved card?" prompt
        without storing actual card data (which would be encrypted).
        
        The actual card number is entered by the operator, but the
        browser recognizes the pattern and offers to save/use it.
        """
        storage_dir = self.profile_path / "storage" / "permanent" / "chrome"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        autofill_dir = storage_dir / "formautofill"
        autofill_dir.mkdir(parents=True, exist_ok=True)
        
        base_time = datetime.now(timezone.utc)
        created = base_time - timedelta(days=age_days)
        
        # Card type detection
        card_network = {
            "visa": "VISA",
            "mastercard": "MASTERCARD",
            "amex": "AMEX",
            "discover": "DISCOVER",
        }.get(persona.card_type.lower(), "VISA")
        
        # Create card hint (masked, for display only)
        card_hint = {
            "guid": secrets.token_urlsafe(9)[:12],
            "version": 4,
            "timeCreated": int(created.timestamp() * 1000),
            "timeLastUsed": int((base_time - timedelta(days=3)).timestamp() * 1000),
            "timeLastModified": int((base_time - timedelta(days=20)).timestamp() * 1000),
            "timesUsed": random.randint(3, 12),
            "cc-name": persona.full_name,
            "cc-number-encrypted": "",  # Would be encrypted in real Firefox
            "cc-number-last4": persona.card_last4,
            "cc-exp-month": int(persona.card_exp_month) if persona.card_exp_month else 12,
            "cc-exp-year": int(persona.card_exp_year) if persona.card_exp_year else 2027,
            "cc-type": card_network,
        }
        
        # Write to JSON storage
        cards_file = autofill_dir / "creditCards.json"
        with open(cards_file, "w") as f:
            json.dump({"creditCards": [card_hint]}, f, indent=2)
        
        logger.info(f"[+] Card hint injected: **** **** **** {persona.card_last4}")


def inject_autofill_to_profile(
    profile_path: str,
    full_name: str,
    email: str,
    phone: str,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    card_last4: str = "",
    age_days: int = 90
) -> bool:
    """
    Convenience function to inject autofill data.
    
    Args:
        profile_path: Path to Firefox profile
        full_name: Full name (e.g., "Alex J. Mercer")
        email: Email address
        phone: Phone number
        address: Street address
        city: City
        state: State code (e.g., "TX")
        zip_code: ZIP code
        card_last4: Last 4 digits of card (optional)
        age_days: Profile age in days
        
    Returns:
        True if successful
    """
    try:
        # Parse name
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""
        
        # Parse address for apt/unit
        address_parts = address.split(",")
        address_line1 = address_parts[0].strip()
        address_line2 = address_parts[1].strip() if len(address_parts) > 1 else ""
        
        persona = PersonaAutofill(
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            zip_code=zip_code,
            card_last4=card_last4,
        )
        
        injector = FormAutofillInjector(profile_path)
        injector.inject_all(persona, age_days)
        
        if card_last4:
            injector.inject_credit_card_hint(persona, age_days)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to inject autofill: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Demo
    print("TITAN V8.1 Form Autofill Injector Demo")
    print("-" * 40)
    
    success = inject_autofill_to_profile(
        profile_path="/tmp/test_profile",
        full_name="Alex J. Mercer",
        email="a.mercer.dev@gmail.com",
        phone="512-555-0123",
        address="2400 NUECES ST, APT 402",
        city="AUSTIN",
        state="TX",
        zip_code="78705",
        card_last4="8921",
        age_days=90
    )
    
    print(f"\nInjection: {'SUCCESS' if success else 'FAILED'}")


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 FORM FIELD MAPPER — Smart field name mapping across different sites
# ═══════════════════════════════════════════════════════════════════════════════

import re
import time
from typing import Set, Tuple
from collections import defaultdict


@dataclass
class FieldMapping:
    """A mapping from site-specific field name to standard field."""
    site_pattern: str
    site_field_name: str
    standard_field: str
    confidence: float


class FormFieldMapper:
    """
    V7.6 Form Field Mapper - Intelligently maps form field names
    from various sites to standard persona fields.
    """
    
    # Standard field types
    STANDARD_FIELDS = {
        "name": ["name", "full-name", "fullname", "full_name"],
        "first_name": ["first-name", "firstname", "fname", "first_name", "given-name", "givenname"],
        "last_name": ["last-name", "lastname", "lname", "last_name", "family-name", "familyname", "surname"],
        "email": ["email", "e-mail", "email_address", "emailaddress", "email-address", "mail"],
        "phone": ["phone", "telephone", "tel", "phone-number", "phonenumber", "mobile", "cell"],
        "address": ["address", "address-line1", "address1", "street", "street-address", "streetaddress"],
        "address2": ["address-line2", "address2", "apt", "suite", "unit", "apartment"],
        "city": ["city", "locality", "town", "address-level2"],
        "state": ["state", "region", "province", "address-level1", "state_code"],
        "zip": ["zip", "postal-code", "postalcode", "zipcode", "postal", "zip_code"],
        "country": ["country", "country-code", "countrycode", "country_code"],
        "card_number": ["cc-number", "ccnumber", "cardnumber", "card-number", "pan"],
        "card_exp": ["cc-exp", "ccexp", "expiry", "expiration", "card-expiry", "exp-date"],
        "card_cvv": ["cc-csc", "cvv", "cvc", "security-code", "card-cvc", "cvv2"],
        "card_name": ["cc-name", "cardholder", "card-holder", "nameoncard", "card_name"],
    }
    
    # Site-specific known mappings
    SITE_MAPPINGS = {
        "amazon.com": {
            "enterAddressFullName": "name",
            "enterAddressPhoneNumber": "phone",
            "enterAddressAddressLine1": "address",
            "enterAddressAddressLine2": "address2",
            "enterAddressCity": "city",
            "enterAddressStateOrRegion": "state",
            "enterAddressPostalCode": "zip",
        },
        "shopify.com": {
            "checkout_shipping_address_first_name": "first_name",
            "checkout_shipping_address_last_name": "last_name",
            "checkout_email": "email",
            "checkout_shipping_address_address1": "address",
            "checkout_shipping_address_city": "city",
            "checkout_shipping_address_zip": "zip",
        },
        "stripe.com": {
            "billing_name": "name",
            "billing_address_line1": "address",
            "billing_address_city": "city",
            "billing_address_state": "state",
            "billing_address_zip": "zip",
        },
    }
    
    def __init__(self):
        self._custom_mappings: Dict[str, Dict[str, str]] = {}
        self._learned_mappings: List[FieldMapping] = []
        self._mapping_cache: Dict[str, str] = {}
    
    def map_field(self, field_name: str, site_domain: str = "") -> Tuple[str, float]:
        """
        Map a field name to a standard field type.
        
        Args:
            field_name: The field name from the form
            site_domain: Optional site domain for site-specific mappings
        
        Returns:
            (standard_field_name, confidence_score)
        """
        cache_key = f"{site_domain}:{field_name}"
        if cache_key in self._mapping_cache:
            return self._mapping_cache[cache_key], 1.0
        
        # Check site-specific mappings
        if site_domain:
            for pattern, mappings in self.SITE_MAPPINGS.items():
                if pattern in site_domain:
                    if field_name in mappings:
                        result = mappings[field_name]
                        self._mapping_cache[cache_key] = result
                        return result, 1.0
        
        # Check custom mappings
        for pattern, mappings in self._custom_mappings.items():
            if pattern in site_domain:
                if field_name in mappings:
                    result = mappings[field_name]
                    self._mapping_cache[cache_key] = result
                    return result, 0.95
        
        # Normalize field name
        normalized = field_name.lower().replace("-", "_").replace(" ", "_")
        
        # Check standard mappings
        for standard_field, variations in self.STANDARD_FIELDS.items():
            if normalized in variations:
                self._mapping_cache[cache_key] = standard_field
                return standard_field, 0.9
            
            # Fuzzy match
            for var in variations:
                if var in normalized or normalized in var:
                    self._mapping_cache[cache_key] = standard_field
                    return standard_field, 0.7
        
        # Check learned mappings
        for mapping in self._learned_mappings:
            if mapping.site_field_name == field_name:
                if not mapping.site_pattern or mapping.site_pattern in site_domain:
                    return mapping.standard_field, mapping.confidence
        
        # Fallback to heuristics
        return self._heuristic_match(normalized), 0.3
    
    def _heuristic_match(self, field_name: str) -> str:
        """Use heuristics to guess field type."""
        if any(pat in field_name for pat in ["email", "mail"]):
            return "email"
        if any(pat in field_name for pat in ["phone", "tel", "mobile"]):
            return "phone"
        if any(pat in field_name for pat in ["addr", "street"]):
            return "address"
        if any(pat in field_name for pat in ["city", "town"]):
            return "city"
        if any(pat in field_name for pat in ["state", "region", "province"]):
            return "state"
        if any(pat in field_name for pat in ["zip", "postal"]):
            return "zip"
        if any(pat in field_name for pat in ["first", "fname", "given"]):
            return "first_name"
        if any(pat in field_name for pat in ["last", "lname", "family", "surname"]):
            return "last_name"
        if any(pat in field_name for pat in ["name"]):
            return "name"
        
        return "unknown"
    
    def add_site_mapping(self, site_pattern: str, mappings: Dict[str, str]):
        """Add custom site-specific mappings."""
        self._custom_mappings[site_pattern] = mappings
        # Clear cache for this site
        self._mapping_cache = {
            k: v for k, v in self._mapping_cache.items() 
            if site_pattern not in k
        }
    
    def learn_mapping(self, site_pattern: str, field_name: str, 
                     standard_field: str, confidence: float = 0.8):
        """Learn a new field mapping."""
        self._learned_mappings.append(FieldMapping(
            site_pattern=site_pattern,
            site_field_name=field_name,
            standard_field=standard_field,
            confidence=confidence
        ))
    
    def get_all_mappings_for_site(self, site_domain: str) -> Dict[str, str]:
        """Get all known mappings for a specific site."""
        result = {}
        
        for pattern, mappings in self.SITE_MAPPINGS.items():
            if pattern in site_domain:
                result.update(mappings)
        
        for pattern, mappings in self._custom_mappings.items():
            if pattern in site_domain:
                result.update(mappings)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 AUTOFILL BEHAVIOR SIMULATOR — Simulate realistic autofill behavior
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AutofillEvent:
    """A simulated autofill event."""
    field_name: str
    value: str
    delay_ms: int
    event_type: str  # "focus", "input", "change", "blur"
    timestamp: float


class AutofillBehaviorSimulator:
    """
    V7.6 Autofill Behavior Simulator - Simulates realistic autofill
    timing and event sequences to avoid detection.
    """
    
    # Realistic timing patterns (milliseconds)
    TIMING_PATTERNS = {
        "slow": {"focus_delay": (100, 300), "type_delay": (50, 150), "field_gap": (200, 500)},
        "normal": {"focus_delay": (50, 150), "type_delay": (20, 80), "field_gap": (100, 300)},
        "fast": {"focus_delay": (20, 60), "type_delay": (5, 20), "field_gap": (50, 150)},
        "autofill": {"focus_delay": (0, 10), "type_delay": (0, 5), "field_gap": (5, 20)},
    }
    
    # Event sequences for different fill types
    EVENT_SEQUENCES = {
        "manual_type": ["focus", "keydown", "input", "keyup", "change", "blur"],
        "paste": ["focus", "paste", "input", "change", "blur"],
        "autofill": ["focus", "input", "change", "blur"],
        "dropdown": ["focus", "change", "blur"],
    }
    
    def __init__(self, speed: str = "normal"):
        """
        Initialize simulator.
        
        Args:
            speed: Typing speed ("slow", "normal", "fast", "autofill")
        """
        self.speed = speed
        self.timing = self.TIMING_PATTERNS.get(speed, self.TIMING_PATTERNS["normal"])
        self._event_log: List[AutofillEvent] = []
    
    def simulate_field_fill(self, field_name: str, value: str, 
                           fill_type: str = "autofill") -> List[AutofillEvent]:
        """
        Simulate filling a single field.
        
        Args:
            field_name: Form field name
            value: Value to fill
            fill_type: How to fill ("manual_type", "paste", "autofill", "dropdown")
        
        Returns:
            List of autofill events
        """
        events = []
        base_time = time.time()
        current_offset = 0
        
        sequence = self.EVENT_SEQUENCES.get(fill_type, self.EVENT_SEQUENCES["autofill"])
        
        for event_type in sequence:
            delay = random.randint(*self.timing["type_delay"])
            current_offset += delay
            
            event = AutofillEvent(
                field_name=field_name,
                value=value if event_type in ("input", "change", "paste") else "",
                delay_ms=delay,
                event_type=event_type,
                timestamp=base_time + (current_offset / 1000)
            )
            events.append(event)
        
        self._event_log.extend(events)
        return events
    
    def simulate_form_fill(self, field_values: Dict[str, str],
                          fill_type: str = "autofill") -> List[AutofillEvent]:
        """
        Simulate filling an entire form.
        
        Args:
            field_values: Dict of field_name -> value
            fill_type: How to fill the form
        
        Returns:
            List of all autofill events
        """
        all_events = []
        
        for field_name, value in field_values.items():
            # Add gap between fields
            gap = random.randint(*self.timing["field_gap"])
            
            events = self.simulate_field_fill(field_name, value, fill_type)
            all_events.extend(events)
        
        return all_events
    
    def generate_timing_script(self, events: List[AutofillEvent]) -> str:
        """
        Generate JavaScript for executing events with realistic timing.
        
        Args:
            events: List of events to execute
        
        Returns:
            JavaScript code string
        """
        script_parts = ["(async function() {"]
        
        for event in events:
            script_parts.append(f"  await new Promise(r => setTimeout(r, {event.delay_ms}));")
            
            if event.event_type == "focus":
                script_parts.append(f"  document.querySelector('[name=\"{event.field_name}\"]')?.focus();")
            elif event.event_type == "input":
                script_parts.append(f"  var el = document.querySelector('[name=\"{event.field_name}\"]');")
                script_parts.append(f"  if(el) {{ el.value = '{event.value}'; el.dispatchEvent(new Event('input', {{bubbles: true}})); }}")
            elif event.event_type == "change":
                script_parts.append(f"  var el = document.querySelector('[name=\"{event.field_name}\"]');")
                script_parts.append(f"  if(el) {{ el.dispatchEvent(new Event('change', {{bubbles: true}})); }}")
            elif event.event_type == "blur":
                script_parts.append(f"  document.querySelector('[name=\"{event.field_name}\"]')?.blur();")
        
        script_parts.append("})();")
        return "\n".join(script_parts)
    
    def get_event_log(self) -> List[AutofillEvent]:
        """Get all simulated events."""
        return self._event_log.copy()
    
    def clear_event_log(self):
        """Clear the event log."""
        self._event_log.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 FORM HISTORY ANALYZER — Analyze and optimize form history patterns
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HistoryAnalysis:
    """Analysis of form history."""
    total_entries: int
    unique_fields: int
    avg_times_used: float
    age_days: int
    consistency_score: float
    issues: List[str]
    recommendations: List[str]


class FormHistoryAnalyzer:
    """
    V7.6 Form History Analyzer - Analyzes form history for
    consistency and realism, provides optimization recommendations.
    """
    
    # Expected usage patterns for common fields
    EXPECTED_PATTERNS = {
        "email": {"min_uses": 10, "max_uses": 100, "required": True},
        "name": {"min_uses": 8, "max_uses": 80, "required": True},
        "phone": {"min_uses": 5, "max_uses": 50, "required": True},
        "address": {"min_uses": 5, "max_uses": 40, "required": True},
        "city": {"min_uses": 5, "max_uses": 40, "required": True},
        "zip": {"min_uses": 5, "max_uses": 40, "required": True},
    }
    
    def __init__(self, profile_path: str):
        self.profile_path = Path(profile_path)
    
    def analyze(self) -> HistoryAnalysis:
        """Analyze form history in profile."""
        db_path = self.profile_path / "formhistory.sqlite"
        
        if not db_path.exists():
            return HistoryAnalysis(
                total_entries=0,
                unique_fields=0,
                avg_times_used=0,
                age_days=0,
                consistency_score=0,
                issues=["Form history database not found"],
                recommendations=["Run form history injection"]
            )
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get entries
            cursor.execute("""
                SELECT fieldname, value, timesUsed, firstUsed, lastUsed 
                FROM moz_formhistory
            """)
            entries = cursor.fetchall()
            conn.close()
            
            return self._analyze_entries(entries)
            
        except Exception as e:
            return HistoryAnalysis(
                total_entries=0,
                unique_fields=0,
                avg_times_used=0,
                age_days=0,
                consistency_score=0,
                issues=[f"Failed to read database: {e}"],
                recommendations=["Check database integrity"]
            )
    
    def _analyze_entries(self, entries: List[Tuple]) -> HistoryAnalysis:
        """Analyze database entries."""
        if not entries:
            return HistoryAnalysis(
                total_entries=0,
                unique_fields=0,
                avg_times_used=0,
                age_days=0,
                consistency_score=0,
                issues=["No form history entries"],
                recommendations=["Run form history injection"]
            )
        
        issues = []
        recommendations = []
        
        # Basic stats
        total = len(entries)
        unique_fields = len(set(e[0] for e in entries))
        avg_uses = sum(e[2] for e in entries) / total if total > 0 else 0
        
        # Calculate age
        first_used_times = [e[3] for e in entries if e[3]]
        if first_used_times:
            oldest = min(first_used_times)
            age_days = int((time.time() * 1000000 - oldest) / (1000000 * 86400))
        else:
            age_days = 0
        
        # Check for required fields
        field_names = {e[0].lower() for e in entries}
        for required_field in ["email", "name", "phone"]:
            found = any(required_field in f for f in field_names)
            if not found:
                issues.append(f"Missing common field: {required_field}")
                recommendations.append(f"Add {required_field} to form history")
        
        # Check usage counts
        for field_name, value, times_used, _, _ in entries:
            for pattern, expected in self.EXPECTED_PATTERNS.items():
                if pattern in field_name.lower():
                    if times_used < expected["min_uses"]:
                        issues.append(f"Low usage count for {field_name}: {times_used}")
                    elif times_used > expected["max_uses"] * 2:
                        issues.append(f"Suspicious high usage for {field_name}: {times_used}")
        
        # Check age consistency
        if age_days < 30:
            issues.append("Form history appears too new")
            recommendations.append("Increase profile age to 90+ days")
        
        # Calculate consistency score
        score = 1.0
        score -= len(issues) * 0.1
        score = max(0, min(1, score))
        
        return HistoryAnalysis(
            total_entries=total,
            unique_fields=unique_fields,
            avg_times_used=round(avg_uses, 1),
            age_days=age_days,
            consistency_score=round(score, 2),
            issues=issues,
            recommendations=recommendations
        )
    
    def optimize(self) -> Dict[str, Any]:
        """Optimize form history based on analysis."""
        analysis = self.analyze()
        
        if analysis.consistency_score >= 0.9:
            return {"status": "optimal", "changes": 0}
        
        # Apply fixes
        changes = 0
        db_path = self.profile_path / "formhistory.sqlite"
        
        if not db_path.exists():
            return {"status": "no_database", "changes": 0}
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Fix low usage counts
            cursor.execute("""
                UPDATE moz_formhistory 
                SET timesUsed = timesUsed + ? 
                WHERE timesUsed < 5
            """, (random.randint(5, 15),))
            changes += cursor.rowcount
            
            # Fix age
            if analysis.age_days < 30:
                age_offset = 90 * 24 * 60 * 60 * 1000000  # 90 days in microseconds
                cursor.execute("""
                    UPDATE moz_formhistory 
                    SET firstUsed = firstUsed - ?
                """, (age_offset,))
                changes += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return {"status": "optimized", "changes": changes}
            
        except Exception as e:
            return {"status": "error", "error": str(e), "changes": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 MULTI-PROFILE AUTOFILL MANAGER — Manage autofill across profiles
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProfileAutofillStatus:
    """Status of autofill for a profile."""
    profile_path: str
    persona_name: str
    email: str
    has_form_history: bool
    has_autofill_profiles: bool
    has_card_hint: bool
    age_days: int
    consistency_score: float


class MultiProfileAutofillManager:
    """
    V7.6 Multi-Profile Autofill Manager - Manages autofill data
    across multiple browser profiles.
    """
    
    def __init__(self, profiles_dir: str = "/opt/titan/profiles"):
        self.profiles_dir = Path(profiles_dir)
        self._profile_cache: Dict[str, ProfileAutofillStatus] = {}
    
    def scan_profiles(self) -> List[ProfileAutofillStatus]:
        """Scan all profiles and get autofill status."""
        statuses = []
        
        if not self.profiles_dir.exists():
            return statuses
        
        for profile_dir in self.profiles_dir.iterdir():
            if profile_dir.is_dir():
                status = self._check_profile(profile_dir)
                statuses.append(status)
                self._profile_cache[str(profile_dir)] = status
        
        return statuses
    
    def _check_profile(self, profile_path: Path) -> ProfileAutofillStatus:
        """Check autofill status for a single profile."""
        has_form_history = (profile_path / "formhistory.sqlite").exists()
        has_autofill = (profile_path / "autofill-profiles.json").exists()
        has_card = (profile_path / "storage" / "permanent" / "chrome" / "formautofill" / "creditCards.json").exists()
        
        persona_name = ""
        email = ""
        age_days = 0
        
        # Try to extract persona info
        if has_autofill:
            try:
                with open(profile_path / "autofill-profiles.json") as f:
                    data = json.load(f)
                    if data.get("addresses"):
                        addr = data["addresses"][0]
                        persona_name = addr.get("name", "")
                        email = addr.get("email", "")
                        time_created = addr.get("timeCreated", 0)
                        if time_created:
                            age_days = int((time.time() * 1000 - time_created) / (1000 * 86400))
            except Exception:
                pass
        
        # Analyze form history
        consistency = 0.0
        if has_form_history:
            analyzer = FormHistoryAnalyzer(str(profile_path))
            analysis = analyzer.analyze()
            consistency = analysis.consistency_score
        
        return ProfileAutofillStatus(
            profile_path=str(profile_path),
            persona_name=persona_name,
            email=email,
            has_form_history=has_form_history,
            has_autofill_profiles=has_autofill,
            has_card_hint=has_card,
            age_days=age_days,
            consistency_score=consistency
        )
    
    def inject_to_all(self, personas: List[PersonaAutofill], age_days: int = 90) -> Dict[str, Any]:
        """
        Inject autofill data to all profiles using provided personas.
        
        Args:
            personas: List of personas to use
            age_days: Profile age
        
        Returns:
            Summary of injection results
        """
        results = {"success": 0, "failed": 0, "errors": []}
        
        profiles = list(self.profiles_dir.iterdir()) if self.profiles_dir.exists() else []
        
        for i, profile_dir in enumerate(profiles):
            if not profile_dir.is_dir():
                continue
            
            # Rotate through personas
            persona = personas[i % len(personas)]
            
            try:
                injector = FormAutofillInjector(str(profile_dir))
                injector.inject_all(persona, age_days)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{profile_dir.name}: {e}")
        
        return results
    
    def cleanup_profile(self, profile_path: str) -> bool:
        """Remove all autofill data from a profile."""
        path = Path(profile_path)
        cleaned = False
        
        # Remove form history
        form_history = path / "formhistory.sqlite"
        if form_history.exists():
            form_history.unlink()
            cleaned = True
        
        # Remove autofill profiles
        autofill = path / "autofill-profiles.json"
        if autofill.exists():
            autofill.unlink()
            cleaned = True
        
        # Remove card hints
        cards = path / "storage" / "permanent" / "chrome" / "formautofill" / "creditCards.json"
        if cards.exists():
            cards.unlink()
            cleaned = True
        
        # Remove addresses
        addresses = path / "storage" / "permanent" / "chrome" / "formautofill" / "addresses.json"
        if addresses.exists():
            addresses.unlink()
            cleaned = True
        
        return cleaned
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all profiles' autofill status."""
        statuses = self.scan_profiles()
        
        return {
            "total_profiles": len(statuses),
            "with_form_history": sum(1 for s in statuses if s.has_form_history),
            "with_autofill": sum(1 for s in statuses if s.has_autofill_profiles),
            "with_card_hints": sum(1 for s in statuses if s.has_card_hint),
            "avg_age_days": sum(s.age_days for s in statuses) / len(statuses) if statuses else 0,
            "avg_consistency": sum(s.consistency_score for s in statuses) / len(statuses) if statuses else 0,
        }


# Global instances
_field_mapper: Optional[FormFieldMapper] = None
_behavior_simulator: Optional[AutofillBehaviorSimulator] = None
_profile_manager: Optional[MultiProfileAutofillManager] = None


def get_field_mapper() -> FormFieldMapper:
    """Get global form field mapper."""
    global _field_mapper
    if _field_mapper is None:
        _field_mapper = FormFieldMapper()
    return _field_mapper


def get_behavior_simulator(speed: str = "normal") -> AutofillBehaviorSimulator:
    """Get global autofill behavior simulator."""
    global _behavior_simulator
    if _behavior_simulator is None:
        _behavior_simulator = AutofillBehaviorSimulator(speed)
    return _behavior_simulator


def get_profile_manager(profiles_dir: str = "/opt/titan/profiles") -> MultiProfileAutofillManager:
    """Get global multi-profile autofill manager."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = MultiProfileAutofillManager(profiles_dir)
    return _profile_manager
