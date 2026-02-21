"""
TITAN V7.0 SINGULARITY - Form Autofill Injector
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
    
    def inject_all(self, persona: PersonaAutofill, age_days: int = 90):
        """Inject all autofill data"""
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
    print("TITAN V7.0 Form Autofill Injector Demo")
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
