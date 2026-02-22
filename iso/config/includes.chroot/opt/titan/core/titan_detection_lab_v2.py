#!/usr/bin/env python3
"""
TITAN V8.1 DETECTION LAB V2 — Real-World Operation Simulator
═══════════════════════════════════════════════════════════════════════════════

Extends Detection Lab with REAL module testing:
  1. PROFILE_CREATION  — 20 profiles via real Genesis, analyze storage/gaps
  2. PROFILE_AUDIT     — Reverse-engineer each profile: size, components, issues
  3. EMAIL_CREATION    — Create accounts on reputable no-phone email providers
  4. MERCHANT_SESSION  — Browse to checkout on real merchants (stop before payment)
  5. FULL_PIPELINE     — Chain all tests: profile → email → merchant → analysis

Uses ONLY real TITAN apps. No simulation. Results feed back as patches.

Usage:
    python3 titan_detection_lab_v2.py profiles      # Create 20 profiles + audit
    python3 titan_detection_lab_v2.py emails         # Create email accounts
    python3 titan_detection_lab_v2.py merchants      # Session test on real merchants
    python3 titan_detection_lab_v2.py full           # Run everything
    python3 titan_detection_lab_v2.py report         # Show latest results
"""

import os
import sys
import json
import time
import random
import secrets
import sqlite3
import hashlib
import logging
import struct
import traceback
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import uuid

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger("TITAN-DETECTION-LAB-V2")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE PERSONAS — 20 realistic US personas for profile generation
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_PERSONAS = [
    {"name": "James Mitchell", "email": "j.mitchell", "street": "4521 Oak Lane", "city": "Austin", "state": "TX", "zip": "78701", "phone": "512-555-0147", "dob": "1992-03-15", "occupation": "Software Developer"},
    {"name": "Sarah Johnson", "email": "s.johnson", "street": "782 Maple Drive", "city": "Denver", "state": "CO", "zip": "80202", "phone": "303-555-0234", "dob": "1988-07-22", "occupation": "Marketing Manager"},
    {"name": "Michael Chen", "email": "m.chen", "street": "1190 Pine Street", "city": "San Jose", "state": "CA", "zip": "95112", "phone": "408-555-0389", "dob": "1995-11-08", "occupation": "Data Analyst"},
    {"name": "Emily Davis", "email": "e.davis", "street": "3345 Birch Road", "city": "Portland", "state": "OR", "zip": "97201", "phone": "503-555-0456", "dob": "1990-05-30", "occupation": "Graphic Designer"},
    {"name": "Robert Wilson", "email": "r.wilson", "street": "567 Cedar Ave", "city": "Phoenix", "state": "AZ", "zip": "85001", "phone": "602-555-0567", "dob": "1985-09-12", "occupation": "Accountant"},
    {"name": "Jessica Brown", "email": "j.brown", "street": "2201 Elm Street", "city": "Chicago", "state": "IL", "zip": "60601", "phone": "312-555-0678", "dob": "1993-01-25", "occupation": "Nurse"},
    {"name": "David Martinez", "email": "d.martinez", "street": "890 Walnut Blvd", "city": "Houston", "state": "TX", "zip": "77001", "phone": "713-555-0789", "dob": "1991-08-18", "occupation": "Mechanical Engineer"},
    {"name": "Amanda Taylor", "email": "a.taylor", "street": "1567 Spruce Lane", "city": "Seattle", "state": "WA", "zip": "98101", "phone": "206-555-0890", "dob": "1994-12-03", "occupation": "Product Manager"},
    {"name": "Christopher Lee", "email": "c.lee", "street": "4430 Ash Court", "city": "Miami", "state": "FL", "zip": "33101", "phone": "305-555-0912", "dob": "1987-04-27", "occupation": "Financial Analyst"},
    {"name": "Lauren Garcia", "email": "l.garcia", "street": "678 Willow Way", "city": "Atlanta", "state": "GA", "zip": "30301", "phone": "404-555-1023", "dob": "1996-06-14", "occupation": "Teacher"},
    {"name": "Daniel Anderson", "email": "d.anderson", "street": "1122 Poplar Drive", "city": "Nashville", "state": "TN", "zip": "37201", "phone": "615-555-1134", "dob": "1989-10-09", "occupation": "Sales Manager"},
    {"name": "Rachel Thomas", "email": "r.thomas", "street": "3456 Cypress Rd", "city": "Charlotte", "state": "NC", "zip": "28201", "phone": "704-555-1245", "dob": "1992-02-20", "occupation": "HR Specialist"},
    {"name": "Kevin Jackson", "email": "k.jackson", "street": "789 Magnolia St", "city": "Minneapolis", "state": "MN", "zip": "55401", "phone": "612-555-1356", "dob": "1986-07-05", "occupation": "Web Developer"},
    {"name": "Nicole White", "email": "n.white", "street": "2345 Hickory Ln", "city": "Tampa", "state": "FL", "zip": "33601", "phone": "813-555-1467", "dob": "1994-11-16", "occupation": "Pharmacist"},
    {"name": "Andrew Harris", "email": "a.harris", "street": "4567 Sycamore Ave", "city": "Columbus", "state": "OH", "zip": "43201", "phone": "614-555-1578", "dob": "1990-03-28", "occupation": "Civil Engineer"},
    {"name": "Megan Clark", "email": "m.clark", "street": "1234 Redwood Dr", "city": "San Diego", "state": "CA", "zip": "92101", "phone": "619-555-1689", "dob": "1988-08-11", "occupation": "UX Designer"},
    {"name": "Brian Lewis", "email": "b.lewis", "street": "5678 Juniper Ct", "city": "Dallas", "state": "TX", "zip": "75201", "phone": "214-555-1790", "dob": "1993-05-07", "occupation": "IT Consultant"},
    {"name": "Stephanie Robinson", "email": "s.robinson", "street": "901 Chestnut Pl", "city": "Raleigh", "state": "NC", "zip": "27601", "phone": "919-555-1801", "dob": "1991-09-23", "occupation": "Veterinarian"},
    {"name": "Matthew Walker", "email": "m.walker", "street": "3210 Dogwood St", "city": "Salt Lake City", "state": "UT", "zip": "84101", "phone": "801-555-1912", "dob": "1987-01-19", "occupation": "Project Manager"},
    {"name": "Ashley Young", "email": "a.young", "street": "6543 Hawthorn Rd", "city": "Kansas City", "state": "MO", "zip": "64101", "phone": "816-555-2023", "dob": "1995-04-02", "occupation": "Social Media Manager"},
]

# Email providers that don't require phone number
EMAIL_PROVIDERS = [
    {"name": "Proton Mail", "domain": "proton.me", "signup_url": "https://account.proton.me/signup",
     "phone_required": False, "captcha": True, "reputation": "excellent",
     "notes": "Swiss privacy. Sometimes asks phone for abuse prevention. Use email verification option."},
    {"name": "Tuta", "domain": "tuta.com", "signup_url": "https://app.tuta.com/#register",
     "phone_required": False, "captcha": True, "reputation": "excellent",
     "notes": "German privacy. No phone ever. CAPTCHA only. 48hr wait for new accounts."},
    {"name": "Disroot", "domain": "disroot.org", "signup_url": "https://user.disroot.org/pwm/public/newuser",
     "phone_required": False, "captcha": True, "reputation": "good",
     "notes": "Dutch non-profit. No phone. Manual approval may take 24-48hrs."},
    {"name": "Mailfence", "domain": "mailfence.com", "signup_url": "https://mailfence.com/en/register",
     "phone_required": False, "captcha": False, "reputation": "good",
     "notes": "Belgian privacy. No phone for free tier. Immediate activation."},
]


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE CREATION TEST — Uses REAL Genesis + AdvancedProfileGenerator
# ═══════════════════════════════════════════════════════════════════════════════

class ProfileCreationTest:
    """Create 20 profiles using real Genesis and analyze each one."""

    EXPECTED_COMPONENTS = {
        "places.sqlite": {"min_size_kb": 50, "description": "Browsing history + bookmarks DB"},
        "cookies.sqlite": {"min_size_kb": 5, "description": "Cookie database"},
        "profile_metadata.json": {"min_size_kb": 0.5, "description": "Profile metadata"},
        "hardware_profile.json": {"min_size_kb": 0.5, "description": "Hardware fingerprint config"},
        "storage/default": {"type": "dir", "description": "localStorage LSNG storage"},
        "permissions.sqlite": {"min_size_kb": 1, "description": "Notification permissions"},
        "favicons.sqlite": {"min_size_kb": 1, "description": "Favicon database"},
        "formhistory.sqlite": {"min_size_kb": 1, "description": "Form autofill data"},
        "xulstore.json": {"min_size_kb": 0.1, "description": "Window state persistence"},
        "sessionstore.jsonlz4": {"min_size_kb": 0.1, "description": "Session restore data"},
    }

    def __init__(self):
        self.results = []
        self.output_dir = Path("/opt/titan/data/detection_lab/profiles")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, count: int = 20) -> Dict:
        """Create profiles and audit each one."""
        logger.info(f"[PROFILE_CREATION] Creating {count} profiles via real Genesis...")

        # Get target presets for profile creation
        targets = self._get_targets()

        profiles_created = 0
        profiles_failed = 0
        all_audits = []

        for i in range(min(count, len(SAMPLE_PERSONAS))):
            persona = SAMPLE_PERSONAS[i]
            target = targets[i % len(targets)]
            logger.info(f"  [{i+1}/{count}] Creating profile for {persona['name']} → {target['domain']}...")

            try:
                profile_result = self._create_single_profile(persona, target, i)
                if profile_result:
                    audit = self._audit_profile(profile_result)
                    all_audits.append(audit)
                    profiles_created += 1
                else:
                    profiles_failed += 1
            except Exception as e:
                logger.error(f"  ✗ Profile {i+1} failed: {e}")
                profiles_failed += 1

        # Aggregate analysis
        report = self._aggregate_analysis(all_audits, profiles_created, profiles_failed)
        return report

    def _get_targets(self) -> List[Dict]:
        """Get checkout-available easy targets from target_discovery."""
        targets = []
        try:
            from target_discovery import TargetDiscovery
            td = TargetDiscovery()
            easy_sites = td.get_sites(difficulty="easy")
            for site in easy_sites[:20]:
                targets.append({
                    "domain": site.domain,
                    "name": site.name,
                    "psp": site.psp.value if hasattr(site.psp, 'value') else str(site.psp),
                    "category": site.category.value if hasattr(site.category, 'value') else str(site.category),
                })
        except Exception as e:
            logger.warning(f"target_discovery unavailable: {e}")

        if not targets:
            targets = [
                {"domain": "cdkeys.com", "name": "CDKeys", "psp": "stripe", "category": "gaming"},
                {"domain": "eneba.com", "name": "Eneba", "psp": "adyen", "category": "gaming"},
                {"domain": "bitrefill.com", "name": "Bitrefill", "psp": "stripe", "category": "crypto"},
                {"domain": "canva.com", "name": "Canva", "psp": "stripe", "category": "subscription"},
                {"domain": "spotify.com", "name": "Spotify", "psp": "adyen", "category": "subscription"},
            ]
        return targets

    def _create_single_profile(self, persona: Dict, target: Dict, index: int) -> Optional[Dict]:
        """Create a single profile using real Genesis engine."""
        profile_id = f"lab_{hashlib.sha256(persona['name'].encode()).hexdigest()[:12]}"

        # Try AdvancedProfileGenerator first (creates 500MB+ profiles)
        try:
            from advanced_profile_generator import AdvancedProfileGenerator, AdvancedProfileConfig
            gen = AdvancedProfileGenerator(output_dir=self.output_dir)
            config = AdvancedProfileConfig(
                profile_uuid=profile_id,
                persona_name=persona["name"],
                persona_email=f"{persona['email']}@proton.me",
                billing_address={
                    "address": persona["street"],
                    "city": persona["city"],
                    "state": persona["state"],
                    "zip": persona["zip"],
                    "country": "US",
                    "phone": persona["phone"],
                },
                profile_age_days=random.randint(60, 120),
                hardware_profile="us_windows_desktop",
            )
            result = gen.generate(config, template="student_developer")
            return {
                "method": "advanced_profile_generator",
                "profile_id": result.profile_id,
                "profile_path": str(result.profile_path),
                "profile_size_mb": result.profile_size_mb,
                "history_entries": result.history_entries,
                "cookies_count": result.cookies_count,
                "localstorage_entries": result.localstorage_entries,
                "persona": persona,
                "target": target,
            }
        except Exception as e:
            logger.debug(f"AdvancedProfileGenerator failed: {e}, trying GenesisEngine...")

        # Fallback: GenesisEngine (lighter profiles)
        try:
            from genesis_core import GenesisEngine, ProfileConfig
            from target_presets import TargetPreset, TargetCategory
            engine = GenesisEngine(output_dir=self.output_dir)

            # Build a minimal target preset
            preset = TargetPreset(
                name=target["name"],
                domain=target["domain"],
                category=TargetCategory.DIGITAL_GOODS,
            )
            config = ProfileConfig(
                target=preset,
                persona_name=persona["name"],
                persona_email=f"{persona['email']}@proton.me",
                persona_address={
                    "address": persona["street"],
                    "city": persona["city"],
                    "state": persona["state"],
                    "zip": persona["zip"],
                    "country": "US",
                },
                age_days=random.randint(60, 120),
                browser="firefox",
            )
            result = engine.forge_profile(config)
            profile_size = sum(f.stat().st_size for f in result.profile_path.rglob("*") if f.is_file()) / (1024 * 1024)
            return {
                "method": "genesis_core",
                "profile_id": result.profile_id,
                "profile_path": str(result.profile_path),
                "profile_size_mb": round(profile_size, 2),
                "history_entries": result.history_count,
                "cookies_count": result.cookies_count,
                "localstorage_entries": 0,
                "persona": persona,
                "target": target,
            }
        except Exception as e:
            logger.error(f"GenesisEngine also failed: {e}")
            traceback.print_exc()
            return None

    def _audit_profile(self, profile_result: Dict) -> Dict:
        """Reverse-engineer a profile directory to identify issues."""
        profile_path = Path(profile_result["profile_path"])
        audit = {
            "profile_id": profile_result["profile_id"],
            "method": profile_result["method"],
            "total_size_mb": 0,
            "components": {},
            "issues": [],
            "scores": {},
            "persona": profile_result["persona"]["name"],
            "target": profile_result["target"]["domain"],
        }

        # Calculate total size
        total_bytes = 0
        for f in profile_path.rglob("*"):
            if f.is_file():
                total_bytes += f.stat().st_size
        audit["total_size_mb"] = round(total_bytes / (1024 * 1024), 2)

        # Check expected components
        for component, spec in self.EXPECTED_COMPONENTS.items():
            comp_path = profile_path / component
            if spec.get("type") == "dir":
                exists = comp_path.is_dir()
                if exists:
                    items = list(comp_path.rglob("*"))
                    size_kb = sum(f.stat().st_size for f in items if f.is_file()) / 1024
                    audit["components"][component] = {
                        "exists": True, "size_kb": round(size_kb, 1),
                        "items": len(items), "description": spec["description"]
                    }
                else:
                    audit["components"][component] = {"exists": False, "description": spec["description"]}
                    audit["issues"].append(f"MISSING: {component} ({spec['description']})")
            else:
                exists = comp_path.is_file()
                if exists:
                    size_kb = comp_path.stat().st_size / 1024
                    audit["components"][component] = {
                        "exists": True, "size_kb": round(size_kb, 1),
                        "description": spec["description"]
                    }
                    min_kb = spec.get("min_size_kb", 0)
                    if size_kb < min_kb:
                        audit["issues"].append(f"TOO_SMALL: {component} ({size_kb:.1f}KB < {min_kb}KB min)")
                else:
                    audit["components"][component] = {"exists": False, "description": spec["description"]}
                    audit["issues"].append(f"MISSING: {component} ({spec['description']})")

        # Deep audit: check history count in places.sqlite
        places_db = profile_path / "places.sqlite"
        if places_db.exists():
            try:
                conn = sqlite3.connect(str(places_db))
                history_count = conn.execute("SELECT COUNT(*) FROM moz_places").fetchone()[0]
                visits_count = conn.execute("SELECT COUNT(*) FROM moz_historyvisits").fetchone()[0]
                conn.close()
                audit["history_entries"] = history_count
                audit["visits_count"] = visits_count
                if history_count < 100:
                    audit["issues"].append(f"LOW_HISTORY: {history_count} entries (need 500+ for aged profile)")
                if history_count < 500:
                    audit["issues"].append(f"WARN_HISTORY: {history_count} entries (recommended 1000+)")
            except Exception as e:
                audit["issues"].append(f"DB_ERROR: places.sqlite: {e}")

        # Deep audit: check cookies count
        cookies_db = profile_path / "cookies.sqlite"
        if cookies_db.exists():
            try:
                conn = sqlite3.connect(str(cookies_db))
                try:
                    cookies_count = conn.execute("SELECT COUNT(*) FROM moz_cookies").fetchone()[0]
                except:
                    cookies_count = 0
                conn.close()
                audit["cookies_count"] = cookies_count
                if cookies_count < 10:
                    audit["issues"].append(f"LOW_COOKIES: {cookies_count} cookies (need 30+ for trust)")
            except Exception as e:
                audit["issues"].append(f"DB_ERROR: cookies.sqlite: {e}")

        # Deep audit: check localStorage size
        storage_dir = profile_path / "storage" / "default"
        if storage_dir.is_dir():
            ls_domains = list(storage_dir.iterdir())
            ls_total_bytes = sum(f.stat().st_size for f in storage_dir.rglob("*") if f.is_file())
            audit["localstorage_domains"] = len(ls_domains)
            audit["localstorage_size_mb"] = round(ls_total_bytes / (1024 * 1024), 2)
            if ls_total_bytes < 100 * 1024 * 1024:  # < 100MB
                audit["issues"].append(f"LOW_STORAGE: localStorage {ls_total_bytes/(1024*1024):.1f}MB (target 500MB+)")

        # Score the profile
        score = 1.0
        for issue in audit["issues"]:
            if "MISSING" in issue:
                score -= 0.15
            elif "TOO_SMALL" in issue:
                score -= 0.1
            elif "LOW_" in issue:
                score -= 0.1
            elif "WARN_" in issue:
                score -= 0.05
        audit["score"] = max(0, round(score, 2))

        return audit

    def _aggregate_analysis(self, audits: List[Dict], created: int, failed: int) -> Dict:
        """Aggregate all profile audits into a report."""
        if not audits:
            return {"profiles_created": created, "profiles_failed": failed, "audits": [], "issues_summary": {}}

        # Collect all issues
        all_issues = {}
        for audit in audits:
            for issue in audit["issues"]:
                issue_type = issue.split(":")[0]
                if issue_type not in all_issues:
                    all_issues[issue_type] = 0
                all_issues[issue_type] += 1

        avg_size = sum(a["total_size_mb"] for a in audits) / len(audits)
        avg_score = sum(a["score"] for a in audits) / len(audits)
        avg_history = sum(a.get("history_entries", 0) for a in audits) / len(audits)

        return {
            "profiles_created": created,
            "profiles_failed": failed,
            "avg_size_mb": round(avg_size, 2),
            "avg_score": round(avg_score, 2),
            "avg_history_entries": round(avg_history),
            "issues_summary": all_issues,
            "audits": audits,
            "recommendations": self._generate_recommendations(all_issues, avg_size, avg_history),
        }

    def _generate_recommendations(self, issues: Dict, avg_size: float, avg_history: float) -> List[str]:
        """Generate actionable recommendations from audit results."""
        recs = []
        if avg_size < 100:
            recs.append(f"CRITICAL: Avg profile size {avg_size:.1f}MB — target is 500MB+. AdvancedProfileGenerator padding may not be working.")
        if avg_size < 300:
            recs.append(f"WARNING: Avg profile size {avg_size:.1f}MB — below 300MB threshold. Increase localStorage/IndexedDB padding.")
        if avg_history < 500:
            recs.append(f"WARNING: Avg history {avg_history:.0f} entries — below 500 minimum. Increase Pareto distribution entries.")
        if issues.get("MISSING", 0) > 0:
            recs.append(f"MISSING COMPONENTS: {issues['MISSING']} profiles have missing files. Check Genesis output.")
        if issues.get("LOW_STORAGE", 0) > 0:
            recs.append(f"LOW STORAGE: {issues['LOW_STORAGE']} profiles under 100MB localStorage. LSNG synthesis may need fixing.")
        return recs


# ═══════════════════════════════════════════════════════════════════════════════
# MERCHANT SESSION TEST — Browse to checkout on real merchants
# ═══════════════════════════════════════════════════════════════════════════════

class MerchantSessionTest:
    """Test session quality by browsing real merchants to checkout page."""

    def run(self, count: int = 5, headless: bool = True) -> Dict:
        """Browse easy checkout-available merchants, stop before payment."""
        logger.info(f"[MERCHANT_SESSION] Testing {count} merchant sessions...")

        targets = self._get_checkout_targets(count)
        results = []

        try:
            from camoufox.sync_api import Camoufox
        except ImportError:
            return {"error": "Camoufox not available", "results": []}

        for i, target in enumerate(targets):
            logger.info(f"  [{i+1}/{len(targets)}] Testing {target['name']} ({target['domain']})...")
            result = self._test_single_merchant(target, headless)
            results.append(result)
            time.sleep(random.uniform(2, 5))  # Delay between merchants

        # Aggregate
        passed = sum(1 for r in results if r["reached_checkout"])
        blocked = sum(1 for r in results if r.get("blocked"))
        captcha = sum(1 for r in results if r.get("captcha_triggered"))

        return {
            "merchants_tested": len(results),
            "reached_checkout": passed,
            "blocked": blocked,
            "captcha_triggered": captcha,
            "session_pass_rate": round(passed / max(len(results), 1) * 100, 1),
            "results": results,
        }

    def _get_checkout_targets(self, count: int) -> List[Dict]:
        """Get easy merchants with checkout from target_discovery."""
        try:
            from target_discovery import TargetDiscovery
            td = TargetDiscovery()
            easy = td.get_sites(difficulty="easy")
            # Prefer digital/gaming/gift_card (instant delivery, easy checkout)
            digital = [s for s in easy if s.category.value in ("gaming", "gift_cards", "digital", "crypto", "subscriptions")]
            if not digital:
                digital = easy
            selected = random.sample(digital, min(count, len(digital)))
            return [{"domain": s.domain, "name": s.name, "psp": s.psp.value,
                      "url": f"https://www.{s.domain}/"} for s in selected]
        except:
            return [
                {"domain": "cdkeys.com", "name": "CDKeys", "psp": "stripe", "url": "https://www.cdkeys.com/"},
                {"domain": "eneba.com", "name": "Eneba", "psp": "adyen", "url": "https://www.eneba.com/"},
                {"domain": "canva.com", "name": "Canva", "psp": "stripe", "url": "https://www.canva.com/"},
            ][:count]

    def _test_single_merchant(self, target: Dict, headless: bool) -> Dict:
        """Navigate to a merchant and attempt to reach checkout."""
        result = {
            "domain": target["domain"],
            "name": target["name"],
            "psp": target["psp"],
            "reached_site": False,
            "reached_product": False,
            "reached_cart": False,
            "reached_checkout": False,
            "blocked": False,
            "captcha_triggered": False,
            "error": None,
            "page_title": "",
            "duration_ms": 0,
            "detection_signals": [],
        }
        start = time.time()

        try:
            from camoufox.sync_api import Camoufox
            with Camoufox(headless=headless, humanize=True) as browser:
                page = browser.new_page()
                page.set_default_timeout(20000)

                # Step 1: Navigate to homepage
                resp = page.goto(target["url"], wait_until="domcontentloaded")
                time.sleep(random.uniform(2, 4))
                result["reached_site"] = True
                result["page_title"] = page.title()

                # Check for blocks
                content = page.content().lower()
                title = page.title().lower()

                if "access denied" in content or "blocked" in title:
                    result["blocked"] = True
                    result["detection_signals"].append("ACCESS_DENIED on homepage")
                    return result

                if "captcha" in content or "challenge" in title or "verify you are human" in content:
                    result["captcha_triggered"] = True
                    result["detection_signals"].append("CAPTCHA on homepage")

                # Step 2: Try to find and click a product
                product_selectors = [
                    "a[href*='product']", "a[href*='item']",
                    ".product-card a", ".product-link",
                    "a[href*='/buy/']", "a[href*='/p/']",
                    ".card a", ".item a",
                ]
                product_found = False
                for selector in product_selectors:
                    try:
                        links = page.query_selector_all(selector)
                        if links:
                            links[0].click()
                            time.sleep(random.uniform(2, 4))
                            result["reached_product"] = True
                            product_found = True
                            break
                    except:
                        continue

                if not product_found:
                    # Try generic navigation
                    try:
                        page.click("a[href]:not([href='#'])", timeout=5000)
                        time.sleep(2)
                    except:
                        pass

                # Step 3: Try to find add-to-cart button
                cart_selectors = [
                    "button[class*='cart']", "button[class*='add']",
                    "[data-action='add-to-cart']", ".add-to-cart",
                    "button:has-text('Add to Cart')", "button:has-text('Buy')",
                    "button:has-text('Add to cart')", "button:has-text('buy now')",
                ]
                for selector in cart_selectors:
                    try:
                        btn = page.query_selector(selector)
                        if btn:
                            btn.click()
                            time.sleep(random.uniform(2, 3))
                            result["reached_cart"] = True
                            break
                    except:
                        continue

                # Step 4: Try to reach checkout
                checkout_selectors = [
                    "a[href*='checkout']", "button:has-text('Checkout')",
                    "a[href*='cart']", "button:has-text('Proceed')",
                    ".checkout-btn", ".cart-checkout",
                ]
                for selector in checkout_selectors:
                    try:
                        el = page.query_selector(selector)
                        if el:
                            el.click()
                            time.sleep(random.uniform(2, 3))
                            current_url = page.url.lower()
                            if "checkout" in current_url or "cart" in current_url or "payment" in current_url:
                                result["reached_checkout"] = True
                            break
                    except:
                        continue

                # Final check: any detection on checkout page
                if result["reached_checkout"]:
                    checkout_content = page.content().lower()
                    if "captcha" in checkout_content or "verify" in checkout_content:
                        result["captcha_triggered"] = True
                        result["detection_signals"].append("CAPTCHA on checkout page")

                page.close()

        except Exception as e:
            result["error"] = str(e)[:200]

        result["duration_ms"] = round((time.time() - start) * 1000)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL PROVIDER TEST — Check which providers we can register on
# ═══════════════════════════════════════════════════════════════════════════════

class EmailProviderTest:
    """Test email provider signup page reachability and CAPTCHA presence."""

    def run(self, headless: bool = True) -> Dict:
        """Test each email provider signup page."""
        logger.info("[EMAIL_PROVIDERS] Testing email provider signup pages...")
        results = []

        try:
            from camoufox.sync_api import Camoufox
        except ImportError:
            return {"error": "Camoufox not available", "results": []}

        for provider in EMAIL_PROVIDERS:
            logger.info(f"  Testing {provider['name']} ({provider['domain']})...")
            result = self._test_provider(provider, headless)
            results.append(result)
            time.sleep(random.uniform(1, 3))

        accessible = sum(1 for r in results if r["signup_accessible"])
        return {
            "providers_tested": len(results),
            "signup_accessible": accessible,
            "results": results,
            "recommended": [r["provider"] for r in results if r["signup_accessible"] and not r.get("phone_detected")],
        }

    def _test_provider(self, provider: Dict, headless: bool) -> Dict:
        """Test a single email provider's signup page."""
        result = {
            "provider": provider["name"],
            "domain": provider["domain"],
            "signup_url": provider["signup_url"],
            "signup_accessible": False,
            "phone_detected": False,
            "captcha_detected": False,
            "page_title": "",
            "error": None,
        }
        try:
            from camoufox.sync_api import Camoufox
            with Camoufox(headless=headless, humanize=True) as browser:
                page = browser.new_page()
                page.set_default_timeout(20000)
                page.goto(provider["signup_url"], wait_until="domcontentloaded")
                time.sleep(3)

                result["page_title"] = page.title()
                content = page.content().lower()

                # Check if signup page loaded
                if "sign up" in content or "register" in content or "create" in content or "new account" in content:
                    result["signup_accessible"] = True

                # Check for phone number field
                phone_indicators = ["phone", "mobile", "sms", "tel"]
                for indicator in phone_indicators:
                    if f'type="{indicator}"' in content or f'name="{indicator}"' in content or f'placeholder="*{indicator}' in content:
                        result["phone_detected"] = True
                        break

                # Check for CAPTCHA
                captcha_indicators = ["captcha", "recaptcha", "hcaptcha", "turnstile", "challenge"]
                for indicator in captcha_indicators:
                    if indicator in content:
                        result["captcha_detected"] = True
                        break

                page.close()
        except Exception as e:
            result["error"] = str(e)[:200]

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class DetectionLabV2:
    """Orchestrates all V2 detection lab tests."""

    def __init__(self):
        self.report_dir = Path("/opt/titan/data/detection_lab")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_profiles(self, count: int = 20) -> Dict:
        """Run profile creation + audit test."""
        test = ProfileCreationTest()
        report = test.run(count)
        self._save_report("profiles", report)
        self._print_profile_report(report)
        return report

    def run_merchants(self, count: int = 5, headless: bool = True) -> Dict:
        """Run merchant session test."""
        test = MerchantSessionTest()
        report = test.run(count, headless)
        self._save_report("merchants", report)
        self._print_merchant_report(report)
        return report

    def run_emails(self, headless: bool = True) -> Dict:
        """Run email provider test."""
        test = EmailProviderTest()
        report = test.run(headless)
        self._save_report("emails", report)
        self._print_email_report(report)
        return report

    def run_full(self, headless: bool = True) -> Dict:
        """Run everything."""
        logger.info("=" * 70)
        logger.info("  TITAN DETECTION LAB V2 — FULL PIPELINE TEST")
        logger.info("=" * 70)

        results = {}
        results["profiles"] = self.run_profiles(20)
        results["emails"] = self.run_emails(headless)
        results["merchants"] = self.run_merchants(5, headless)

        # Overall analysis
        results["overall"] = self._generate_overall_analysis(results)
        self._save_report("full", results)
        self._print_overall(results["overall"])
        return results

    def _generate_overall_analysis(self, results: Dict) -> Dict:
        """Generate overall analysis with issues and solutions."""
        issues = []
        solutions = []

        # Profile issues
        p = results.get("profiles", {})
        if p.get("avg_size_mb", 0) < 300:
            issues.append({
                "category": "PROFILE_SIZE",
                "severity": "HIGH",
                "detail": f"Average profile size {p.get('avg_size_mb', 0):.1f}MB — below 300MB target",
                "module": "advanced_profile_generator",
            })
            solutions.append({
                "issue": "PROFILE_SIZE",
                "fix": "Increase localStorage padding in _generate_localstorage(). Current target_size_bytes calculation may undercount. Also ensure IndexedDB padding is included.",
                "module": "advanced_profile_generator",
            })

        if p.get("avg_score", 0) < 0.7:
            issues.append({
                "category": "PROFILE_QUALITY",
                "severity": "HIGH",
                "detail": f"Average profile score {p.get('avg_score', 0):.0%} — missing critical components",
                "module": "genesis_core",
            })

        for issue_type, count in p.get("issues_summary", {}).items():
            if issue_type == "MISSING" and count > 5:
                issues.append({
                    "category": "MISSING_FILES",
                    "severity": "CRITICAL",
                    "detail": f"{count} profiles have missing component files",
                    "module": "genesis_core",
                })
                solutions.append({
                    "issue": "MISSING_FILES",
                    "fix": "Ensure forge_profile() generates ALL expected files: permissions.sqlite, favicons.sqlite, formhistory.sqlite, xulstore.json, sessionstore.jsonlz4",
                    "module": "genesis_core",
                })

        # Email issues
        e = results.get("emails", {})
        if e.get("signup_accessible", 0) == 0:
            issues.append({
                "category": "EMAIL_BLOCKED",
                "severity": "HIGH",
                "detail": "Cannot access any email provider signup pages",
                "module": "mullvad_vpn",
            })
            solutions.append({
                "issue": "EMAIL_BLOCKED",
                "fix": "Email providers may block datacenter IPs. Install Mullvad VPN to use residential-looking exit nodes.",
                "module": "mullvad_vpn",
            })

        # Merchant issues
        m = results.get("merchants", {})
        if m.get("session_pass_rate", 0) < 50:
            issues.append({
                "category": "MERCHANT_BLOCKED",
                "severity": "HIGH",
                "detail": f"Only {m.get('session_pass_rate', 0):.0f}% of merchants reached checkout",
                "module": "fingerprint_injector",
            })
            solutions.append({
                "issue": "MERCHANT_BLOCKED",
                "fix": "Improve browser fingerprint (WebGL, Canvas) and ensure Mullvad VPN is active to hide datacenter IP.",
                "module": "fingerprint_injector",
            })

        if m.get("captcha_triggered", 0) > 0:
            issues.append({
                "category": "CAPTCHA",
                "severity": "MEDIUM",
                "detail": f"{m.get('captcha_triggered', 0)} merchants triggered CAPTCHA",
                "module": "ghost_motor_v6",
            })
            solutions.append({
                "issue": "CAPTCHA",
                "fix": "Improve behavioral patterns (mouse, scroll, timing). Ensure Ghost Motor humanize is active. Consider longer warmup browsing.",
                "module": "ghost_motor_v6",
            })

        return {
            "issues_found": len(issues),
            "issues": issues,
            "solutions": solutions,
            "ready_for_operations": len([i for i in issues if i["severity"] == "CRITICAL"]) == 0,
        }

    def _save_report(self, name: str, report: Dict):
        path = self.report_dir / f"lab_v2_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"Report saved: {path}")

    def _print_profile_report(self, report: Dict):
        print(f"\n{'='*70}")
        print(f"  PROFILE CREATION REPORT")
        print(f"{'='*70}")
        print(f"  Created: {report['profiles_created']}  |  Failed: {report['profiles_failed']}")
        print(f"  Avg Size: {report.get('avg_size_mb', 0):.1f} MB  |  Avg Score: {report.get('avg_score', 0):.0%}")
        print(f"  Avg History: {report.get('avg_history_entries', 0)} entries")
        if report.get("issues_summary"):
            print(f"\n  Issues:")
            for issue, count in report["issues_summary"].items():
                print(f"    {issue}: {count} profiles")
        if report.get("recommendations"):
            print(f"\n  Recommendations:")
            for rec in report["recommendations"]:
                print(f"    → {rec}")
        print(f"{'='*70}")

    def _print_merchant_report(self, report: Dict):
        print(f"\n{'='*70}")
        print(f"  MERCHANT SESSION REPORT")
        print(f"{'='*70}")
        print(f"  Tested: {report.get('merchants_tested', 0)}  |  Reached Checkout: {report.get('reached_checkout', 0)}")
        print(f"  Blocked: {report.get('blocked', 0)}  |  CAPTCHA: {report.get('captcha_triggered', 0)}")
        print(f"  Session Pass Rate: {report.get('session_pass_rate', 0):.1f}%")
        for r in report.get("results", []):
            icon = "✓" if r["reached_checkout"] else "⚠" if r["reached_site"] else "✗"
            print(f"    {icon} {r['name']:25s} Site:{r['reached_site']}  Product:{r['reached_product']}  Cart:{r['reached_cart']}  Checkout:{r['reached_checkout']}")
        print(f"{'='*70}")

    def _print_email_report(self, report: Dict):
        print(f"\n{'='*70}")
        print(f"  EMAIL PROVIDER REPORT")
        print(f"{'='*70}")
        for r in report.get("results", []):
            icon = "✓" if r["signup_accessible"] else "✗"
            phone = "📱" if r["phone_detected"] else "  "
            captcha = "🔒" if r["captcha_detected"] else "  "
            print(f"    {icon} {r['provider']:20s} Accessible:{r['signup_accessible']}  Phone:{phone}  CAPTCHA:{captcha}")
        if report.get("recommended"):
            print(f"\n  Recommended (no phone): {', '.join(report['recommended'])}")
        print(f"{'='*70}")

    def _print_overall(self, overall: Dict):
        print(f"\n{'='*70}")
        print(f"  OVERALL ANALYSIS")
        print(f"{'='*70}")
        print(f"  Issues Found: {overall['issues_found']}")
        print(f"  Ready for Operations: {'YES' if overall['ready_for_operations'] else 'NO'}")
        if overall.get("issues"):
            print(f"\n  Issues:")
            for i in overall["issues"]:
                print(f"    [{i['severity']}] {i['category']}: {i['detail']}")
        if overall.get("solutions"):
            print(f"\n  Solutions:")
            for s in overall["solutions"]:
                print(f"    → [{s['module']}] {s['fix']}")
        print(f"{'='*70}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="TITAN Detection Lab V2")
    parser.add_argument("action", choices=["profiles", "emails", "merchants", "full", "report"],
                        help="Test to run")
    parser.add_argument("--count", "-n", type=int, default=20, help="Number of profiles/merchants")
    parser.add_argument("--visible", action="store_true", help="Run browser visibly")
    args = parser.parse_args()

    lab = DetectionLabV2()
    headless = not args.visible

    if args.action == "profiles":
        lab.run_profiles(args.count)
    elif args.action == "emails":
        lab.run_emails(headless)
    elif args.action == "merchants":
        lab.run_merchants(args.count, headless)
    elif args.action == "full":
        lab.run_full(headless)
    elif args.action == "report":
        report_dir = Path("/opt/titan/data/detection_lab")
        reports = sorted(report_dir.glob("lab_v2_full_*.json"), reverse=True)
        if reports:
            print(json.dumps(json.loads(reports[0].read_text()), indent=2))
        else:
            print("No full reports found. Run: python3 titan_detection_lab_v2.py full")


if __name__ == "__main__":
    main()
