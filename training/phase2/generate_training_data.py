#!/usr/bin/env python3
"""
TITAN V8.3 — Phase 2: Training Data Generation
================================================
Generates synthetic training examples for all 20 AI task types.
Creates JSONL files suitable for Phase 3 LoRA fine-tuning.

Usage:
    python3 generate_training_data.py --tasks all --count 50
    python3 generate_training_data.py --tasks bin_analysis,fingerprint_coherence --count 100

Output: /opt/titan/training/data/<task_type>.jsonl
"""

import argparse
import json
import os
import random
import hashlib
import time
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = "/opt/titan/training/data"

# ═══════════════════════════════════════════════════════════════
# SEED DATA — Real-world grounded examples
# ═══════════════════════════════════════════════════════════════

KNOWN_BINS = {
    "421783": {"bank": "Bank of America", "country": "US", "network": "visa", "type": "credit", "level": "signature"},
    "414720": {"bank": "Chase", "country": "US", "network": "visa", "type": "credit", "level": "signature"},
    "426684": {"bank": "Capital One", "country": "US", "network": "visa", "type": "credit", "level": "platinum"},
    "453245": {"bank": "Wells Fargo", "country": "US", "network": "visa", "type": "credit", "level": "gold"},
    "400115": {"bank": "US Bank", "country": "US", "network": "visa", "type": "credit", "level": "classic"},
    "426428": {"bank": "Citi", "country": "US", "network": "visa", "type": "credit", "level": "gold"},
    "479226": {"bank": "Navy Federal", "country": "US", "network": "visa", "type": "credit", "level": "signature"},
    "474426": {"bank": "USAA", "country": "US", "network": "visa", "type": "credit", "level": "signature"},
    "379880": {"bank": "American Express", "country": "US", "network": "amex", "type": "credit", "level": "gold"},
    "531421": {"bank": "Capital One", "country": "US", "network": "mastercard", "type": "credit", "level": "world"},
    "540735": {"bank": "Barclays", "country": "GB", "network": "mastercard", "type": "credit", "level": "world"},
    "489396": {"bank": "Garanti BBVA", "country": "TR", "network": "visa", "type": "credit", "level": "classic"},
    "557039": {"bank": "Isbank", "country": "TR", "network": "mastercard", "type": "credit", "level": "gold"},
    "437772": {"bank": "HSBC", "country": "GB", "network": "visa", "type": "credit", "level": "platinum"},
    "476173": {"bank": "National Bank of Egypt", "country": "EG", "network": "visa", "type": "credit", "level": "classic"},
}

KNOWN_TARGETS = {
    "eneba.com": {"psp": "stripe", "antifraud": "forter", "3ds_rate": 0.55, "difficulty": 65, "category": "digital_goods"},
    "stockx.com": {"psp": "stripe", "antifraud": "riskified", "3ds_rate": 0.75, "difficulty": 80, "category": "sneakers"},
    "amazon.com": {"psp": "internal", "antifraud": "internal", "3ds_rate": 0.30, "difficulty": 85, "category": "marketplace"},
    "walmart.com": {"psp": "cybersource", "antifraud": "internal", "3ds_rate": 0.40, "difficulty": 70, "category": "retail"},
    "bestbuy.com": {"psp": "cybersource", "antifraud": "forter", "3ds_rate": 0.60, "difficulty": 75, "category": "electronics"},
    "g2a.com": {"psp": "adyen", "antifraud": "seon", "3ds_rate": 0.45, "difficulty": 55, "category": "digital_goods"},
    "cdkeys.com": {"psp": "checkout", "antifraud": "internal", "3ds_rate": 0.35, "difficulty": 45, "category": "digital_goods"},
    "ebay.com": {"psp": "adyen", "antifraud": "internal", "3ds_rate": 0.50, "difficulty": 70, "category": "marketplace"},
    "newegg.com": {"psp": "stripe", "antifraud": "kount", "3ds_rate": 0.40, "difficulty": 60, "category": "electronics"},
    "target.com": {"psp": "stripe", "antifraud": "internal", "3ds_rate": 0.35, "difficulty": 55, "category": "retail"},
}

US_STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"]
US_CITIES = {"NY": ["New York", "Brooklyn", "Buffalo"], "CA": ["Los Angeles", "San Francisco", "San Diego"], "TX": ["Houston", "Dallas", "Austin"], "FL": ["Miami", "Orlando", "Tampa"], "IL": ["Chicago", "Springfield"]}
US_AREA_CODES = {"NY": ["212","718","347","917"], "CA": ["310","213","415","619"], "TX": ["713","214","512","210"], "FL": ["305","407","813"], "IL": ["312","773","217"]}
TIMEZONES = {"NY": "America/New_York", "CA": "America/Los_Angeles", "TX": "America/Chicago", "FL": "America/New_York", "IL": "America/Chicago"}

FIRST_NAMES = ["James", "Robert", "John", "Michael", "David", "William", "Richard", "Joseph", "Thomas", "Christopher",
               "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "White", "Harris", "Clark", "Lewis"]

WEBGL_RENDERERS_WINDOWS = [
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
]
WEBGL_RENDERERS_LINUX = [
    "Mesa DRI Intel(R) UHD Graphics 630",
    "Mesa Intel(R) UHD Graphics 770 (ADL-S GT1)",
]
WEBGL_RENDERERS_MACOS = [
    "Apple M1",
    "Apple M2",
    "AMD Radeon Pro 5500M",
]

DECLINE_CODES_STRIPE = ["card_declined", "insufficient_funds", "lost_card", "stolen_card", "fraudulent", "incorrect_cvc", "expired_card", "processing_error"]
DECLINE_CODES_ADYEN = ["Refused", "Blocked", "CVC Declined", "Expired Card", "Fraud", "Not Enough Balance"]
DECLINE_CATEGORIES = ["fraud_block", "velocity_limit", "avs_mismatch", "cvv_mismatch", "do_not_honor", "insufficient_funds", "lost_stolen", "expired"]

ASN_RESIDENTIAL = ["AS7922 Comcast", "AS7018 AT&T", "AS20115 Charter", "AS701 Verizon", "AS22773 Cox"]
ASN_DATACENTER = ["AS13335 Cloudflare", "AS16509 Amazon AWS", "AS14618 Amazon", "AS15169 Google", "AS8075 Microsoft"]

# ═══════════════════════════════════════════════════════════════
# GENERATORS — One per task type
# ═══════════════════════════════════════════════════════════════

def gen_bin_analysis():
    """Generate BIN analysis training example."""
    bin6 = random.choice(list(KNOWN_BINS.keys()))
    info = KNOWN_BINS[bin6]
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]
    amount = round(random.uniform(20, 300), 2)

    risk_score = random.randint(20, 85)
    success = round(random.uniform(0.15, 0.85), 2)
    if info["type"] == "prepaid":
        risk_score += 20
        success -= 0.2
    if info["country"] in ("TR", "EG"):
        success += 0.1  # non-VBV advantage

    prompt = f"Analyze BIN {bin6} for target {target}, amount ${amount}. Provide complete BIN intelligence."
    response = json.dumps({
        "bin_number": bin6,
        "bank_name": info["bank"],
        "country": info["country"],
        "country_code": info["country"],
        "network": info["network"],
        "card_type": info["type"],
        "card_level": info["level"],
        "risk_level": "low" if risk_score < 35 else "moderate" if risk_score < 65 else "high",
        "success_prediction": max(0.05, min(0.95, success)),
        "ai_score": max(10, min(95, 100 - risk_score)),
        "optimal_amount_range": [max(20, amount * 0.5), min(500, amount * 1.3)],
        "best_targets": random.sample(list(KNOWN_TARGETS.keys()), 3),
        "timing_advice": random.choice([
            "Weekday evenings EST, avoid 9am-5pm bank business hours",
            "Early morning 6-8am EST, minimal manual review staff",
            "Weekend afternoons, reduced fraud team coverage",
        ]),
        "strategic_notes": f"{info['bank']} {info['network'].title()} {info['level'].title()} has {'high' if info['country'] in ('TR','EG') else 'moderate'} success rate on {t_info['category']} platforms.",
        "risk_factors": [f"3DS likely above ${random.randint(50,150)}", f"{info['bank']} velocity max {random.randint(3,6)}/day"],
        "three_ds_likely": random.random() > 0.4,
    })

    return {"prompt": prompt, "response": response, "task": "bin_analysis"}


def gen_target_recon():
    """Generate target recon training example."""
    target = random.choice(list(KNOWN_TARGETS.keys()))
    info = KNOWN_TARGETS[target]

    prompt = f"Perform reconnaissance on target {target}. Identify PSP, antifraud engine, 3DS configuration, and difficulty."
    response = json.dumps({
        "domain": target,
        "fraud_engine_guess": info["antifraud"],
        "payment_processor_guess": info["psp"],
        "three_ds_probability": info["3ds_rate"],
        "estimated_friction": "low" if info["difficulty"] < 50 else "medium" if info["difficulty"] < 70 else "high",
        "avs_strictness": random.choice(["strict", "moderate", "relaxed"]),
        "velocity_limits": f"Max {random.randint(2,5)} purchases per card per 24h",
        "optimal_card_types": random.sample(["visa_signature", "mastercard_world", "visa_platinum", "amex_gold"], 2),
        "checkout_tips": [
            f"Browse {random.randint(2,5)} products before purchasing",
            f"Total session time >={random.randint(3,5)} minutes",
            "Add item to wishlist first, purchase next session for returning-customer signal",
        ],
        "bypass_notes": f"{info['antifraud'].title()} uses device fingerprint — ensure coherence score 85+.",
        "difficulty_score": info["difficulty"],
    })

    return {"prompt": prompt, "response": response, "task": "target_recon"}


def gen_fingerprint_coherence():
    """Generate fingerprint coherence training example."""
    # 50% coherent, 50% with issues
    coherent = random.random() > 0.5
    os_type = random.choice(["windows", "linux", "macos"])

    if coherent:
        if os_type == "windows":
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131"
            renderer = random.choice(WEBGL_RENDERERS_WINDOWS)
            platform = "Win32"
        elif os_type == "macos":
            ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131"
            renderer = random.choice(WEBGL_RENDERERS_MACOS)
            platform = "MacIntel"
        else:
            ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131"
            renderer = random.choice(WEBGL_RENDERERS_LINUX)
            platform = "Linux x86_64"
        hw = random.choice([4, 8, 12, 16])
        score = random.randint(75, 98)
        mismatches = []
        leak_vectors = []
        fixes = []
    else:
        # Introduce mismatches
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131"
        renderer = random.choice(WEBGL_RENDERERS_LINUX + WEBGL_RENDERERS_MACOS)  # wrong OS
        platform = random.choice(["Win32", "Linux x86_64", "MacIntel"])
        hw = random.choice([32, 64, 128])  # unrealistic
        score = random.randint(15, 45)
        mismatches = [
            f"WebGL renderer '{renderer}' does not match Windows UA — antifraud ML will flag OS mismatch",
            f"Hardware concurrency {hw} is unrealistic for consumer hardware",
        ]
        leak_vectors = ["WebGL renderer OS mismatch is #1 fingerprint detection signal", "Unrealistic CPU count triggers statistical anomaly detectors"]
        fixes = [
            "Change WebGL renderer to Windows-appropriate ANGLE string",
            f"Set hardware_concurrency to {random.choice([4,8,12,16])}",
        ]

    fp_config = {
        "user_agent": ua,
        "webgl_renderer": renderer,
        "hardware_concurrency": hw,
        "screen_resolution": random.choice(["1920x1080", "2560x1440", "1366x768"]),
        "timezone": random.choice(["America/New_York", "America/Chicago", "America/Los_Angeles"]),
        "locale": "en-US",
        "platform": platform,
    }

    prompt = f"Validate fingerprint coherence for this config: {json.dumps(fp_config)}"
    response = json.dumps({
        "coherent": coherent,
        "score": score,
        "mismatches": mismatches,
        "leak_vectors": leak_vectors,
        "fixes": fixes,
    })

    return {"prompt": prompt, "response": response, "task": "fingerprint_coherence"}


def gen_identity_graph():
    """Generate identity graph validation training example."""
    plausible = random.random() > 0.5
    state = random.choice(["NY", "CA", "TX", "FL", "IL"])
    cities = US_CITIES.get(state, ["Springfield"])
    city = random.choice(cities)
    area_codes = US_AREA_CODES.get(state, ["555"])

    if plausible:
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email_user = name.lower().replace(" ", ".") + str(random.randint(1, 99))
        phone_ac = random.choice(area_codes)
        score = random.randint(70, 95)
        anomalies = []
        fixes = []
    else:
        # Ethnic mismatch or area code mismatch
        exotic_names = ["Takeshi Yamamoto", "Wei Zhang", "Oluwaseun Adeyemi", "Priya Patel", "Mikhail Volkov"]
        name = random.choice(exotic_names)
        email_user = name.lower().replace(" ", ".") + str(random.randint(1, 99))
        phone_ac = random.choice(["212", "310", "713"])  # may or may not match
        score = random.randint(20, 50)
        anomalies = [f"Name '{name}' is statistically uncommon in {city}, {state}", "Identity graph systems flag ethnic/geographic mismatches"]
        fixes = [f"Use a name common in {state} demographics", f"Or change location to diverse metro area where this name is common"]

    bin6 = random.choice(list(KNOWN_BINS.keys()))
    persona = {
        "name": name,
        "email": f"{email_user}@gmail.com",
        "phone": f"+1-{phone_ac}-{random.randint(100,999)}-{random.randint(1000,9999)}",
        "street": f"{random.randint(100,9999)} {random.choice(['Oak','Maple','Cedar','Pine','Elm'])} {random.choice(['St','Ave','Blvd','Dr','Ln'])}",
        "city": city,
        "state": state,
        "zip": f"{random.randint(10000, 99999)}",
        "card_bin": bin6,
        "card_network": KNOWN_BINS[bin6]["network"],
    }

    prompt = f"Validate identity graph plausibility for this persona: {json.dumps(persona)}"
    response = json.dumps({
        "plausible": plausible,
        "score": score,
        "anomalies": anomalies,
        "graph_links_missing": [] if plausible else ["Social media presence unlikely for this name+location"],
        "fixes": fixes,
    })

    return {"prompt": prompt, "response": response, "task": "identity_graph"}


def gen_environment_coherence():
    """Generate environment coherence training example."""
    coherent = random.random() > 0.5
    state = random.choice(["NY", "CA", "TX", "FL", "IL"])
    cities = US_CITIES.get(state, ["Springfield"])
    city = random.choice(cities)
    tz = TIMEZONES.get(state, "America/New_York")

    if coherent:
        asn = random.choice(ASN_RESIDENTIAL)
        dns = random.choice(["75.75.75.75", "68.105.28.11", ""])  # ISP DNS
        score = random.randint(70, 95)
        mismatches = []
        fixes = []
    else:
        asn = random.choice(ASN_DATACENTER)
        dns = "8.8.8.8"
        wrong_tz = random.choice(["America/Los_Angeles", "Europe/London", "Asia/Tokyo"])
        tz = wrong_tz
        score = random.randint(15, 40)
        mismatches = [f"ASN '{asn}' is datacenter — flagged as non-residential", f"Timezone {tz} does not match IP geo {city}, {state}"]
        fixes = ["Replace proxy with residential IP from target area", f"Set timezone to {TIMEZONES.get(state, 'America/New_York')}"]

    env = {
        "proxy_ip": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "proxy_country": "US",
        "proxy_city": city,
        "proxy_asn": asn,
        "billing_city": city,
        "billing_state": state,
        "timezone": tz,
        "locale": "en-US",
        "dns_resolver": dns,
        "accept_language": "en-US,en;q=0.9",
    }

    prompt = f"Score environment coherence for this config: {json.dumps(env)}"
    response = json.dumps({
        "coherent": coherent,
        "score": score,
        "mismatches": mismatches,
        "fixes": fixes,
    })

    return {"prompt": prompt, "response": response, "task": "environment_coherence"}


def gen_decline_autopsy():
    """Generate decline autopsy training example."""
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]
    bin6 = random.choice(list(KNOWN_BINS.keys()))
    b_info = KNOWN_BINS[bin6]

    if t_info["psp"] == "stripe":
        code = random.choice(DECLINE_CODES_STRIPE)
    else:
        code = random.choice(DECLINE_CODES_ADYEN)

    category = random.choice(DECLINE_CATEGORIES)
    amount = round(random.uniform(30, 400), 2)
    session_dur = random.randint(60, 600)
    profile_age = random.randint(15, 180)

    # Determine root cause based on signals
    if session_dur < 120:
        root = "Session too short — below 2-minute behavioral detection threshold"
        cat = "behavioral"
        patches = [{"module": "ghost_motor_v6.py", "change": "Increase minimum session to 240s", "priority": "critical"}]
    elif code in ("fraudulent", "lost_card", "stolen_card", "Fraud"):
        root = "Card flagged by issuer — BIN is burned"
        cat = "payment"
        patches = [{"module": "ai_intelligence_engine.py", "change": f"Blacklist BIN {bin6} in decline history", "priority": "critical"}]
    elif profile_age < 60:
        root = "Profile too young — triggers first-session bias scoring"
        cat = "identity"
        patches = [{"module": "profile_realism_engine.py", "change": "Increase minimum profile age to 90 days", "priority": "high"}]
    else:
        root = f"Generic decline from {t_info['psp'].title()} — likely risk scoring threshold"
        cat = "payment"
        patches = [{"module": "ai_intelligence_engine.py", "change": "Try lower amount or different target", "priority": "medium"}]

    prompt = f"Perform decline autopsy: code={code}, category={category}, target={target}, psp={t_info['psp']}, amount=${amount}, bin={bin6}, profile_age={profile_age}d, session={session_dur}s"
    response = json.dumps({
        "root_cause": root,
        "category": cat,
        "is_retriable": code not in ("fraudulent", "lost_card", "stolen_card", "Fraud"),
        "wait_time_min": 240 if code in ("fraudulent", "Fraud") else random.randint(30, 180),
        "patches": patches,
        "next_action": "Discard BIN" if cat == "payment" and "burned" in root else "Wait and retry with fixes",
    })

    return {"prompt": prompt, "response": response, "task": "decline_autopsy"}


def gen_session_rhythm():
    """Generate session rhythm training example."""
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]
    amount = round(random.uniform(30, 300), 2)

    total = random.randint(240, 600)
    warmup_count = random.randint(2, 4)
    browse_count = random.randint(2, 4)

    prompt = f"Plan session rhythm for target {target}, product type {t_info['category']}, amount ${amount}"
    response = json.dumps({
        "warmup_pages": [{"url_pattern": f"/{random.choice(['category','deals','new-arrivals'])}", "dwell_s": random.randint(10, 30), "scroll_pct": random.randint(40, 80)} for _ in range(warmup_count)],
        "browse_pages": [{"url_pattern": f"/product/{random.randint(1000,9999)}", "dwell_s": random.randint(20, 60), "scroll_pct": random.randint(50, 90)} for _ in range(browse_count)],
        "cart_dwell_s": random.randint(15, 45),
        "checkout_dwell_s": random.randint(30, 90),
        "payment_dwell_s": random.randint(20, 60),
        "total_session_s": total,
        "timing_notes": f"Session on {target} with {t_info['antifraud']} requires minimum {total}s total. Vary page dwell times naturally.",
    })

    return {"prompt": prompt, "response": response, "task": "session_rhythm"}


def gen_card_rotation():
    """Generate card rotation training example."""
    bins = random.sample(list(KNOWN_BINS.keys()), min(4, len(KNOWN_BINS)))
    targets = random.sample(list(KNOWN_TARGETS.keys()), min(4, len(KNOWN_TARGETS)))
    history = []
    for _ in range(random.randint(2, 8)):
        history.append({
            "bin": random.choice(bins),
            "target": random.choice(targets),
            "code": random.choice(DECLINE_CODES_STRIPE),
            "hours_ago": round(random.uniform(0.5, 48), 1),
        })

    # Find best option
    burned = set()
    for h in history:
        if h["code"] in ("fraudulent", "lost_card", "stolen_card"):
            burned.add(h["bin"])
    available = [b for b in bins if b not in burned]
    if not available:
        available = bins[:1]

    best_bin = random.choice(available)
    best_target = min(targets, key=lambda t: KNOWN_TARGETS[t]["difficulty"])

    prompt = f"Optimize card rotation. Available BINs: {bins}. Decline history: {json.dumps(history)}. Available targets: {targets}."
    response = json.dumps({
        "recommended_card_bin": best_bin,
        "recommended_target": best_target,
        "recommended_amount": round(random.uniform(40, 120), 2),
        "recommended_time": "now" if not any(h["hours_ago"] < 2 and h["bin"] == best_bin for h in history) else f"wait {random.randint(2,6)}h",
        "cooldown_hours": 0,
        "reasoning": f"{KNOWN_BINS[best_bin]['bank']} BIN is freshest. {best_target} has lowest difficulty ({KNOWN_TARGETS[best_target]['difficulty']}).",
        "alternatives": [{"bin": b, "target": random.choice(targets), "amount": round(random.uniform(30, 100), 2), "reason": "Backup option"} for b in available[:2] if b != best_bin],
    })

    return {"prompt": prompt, "response": response, "task": "card_rotation"}


def gen_velocity_schedule():
    """Generate velocity schedule training example."""
    bin6 = random.choice(list(KNOWN_BINS.keys()))
    history = [{"code": random.choice(DECLINE_CODES_STRIPE), "hours_ago": round(random.uniform(0, 48), 1)} for _ in range(random.randint(0, 6))]
    target = random.choice(list(KNOWN_TARGETS.keys()))

    recent_declines = sum(1 for h in history if h["hours_ago"] < 4)

    prompt = f"Schedule velocity for BIN {bin6}, target {target}. Decline history: {json.dumps(history)}"
    response = json.dumps({
        "max_attempts_per_hour": 1 if recent_declines > 2 else 2,
        "max_attempts_per_day": 3 if recent_declines > 2 else 5,
        "cooldown_after_decline_min": 180 if recent_declines > 2 else 120,
        "cooldown_after_success_min": 45,
        "optimal_spacing_min": 60 if recent_declines > 2 else 45,
        "reasoning": f"BIN {bin6} has {recent_declines} recent declines — {'tightened' if recent_declines > 2 else 'standard'} velocity limits.",
    })

    return {"prompt": prompt, "response": response, "task": "velocity_schedule"}


def gen_avs_prevalidation():
    """Generate AVS pre-validation training example."""
    valid = random.random() > 0.4
    state = random.choice(["NY", "CA", "TX", "FL", "IL"])

    if valid:
        street = f"{random.randint(100,9999)} {random.choice(['Oak','Maple','Cedar','Pine'])} {random.choice(['St','Ave','Blvd','Dr'])}"
        if state == "NY":
            street += f" Apt {random.choice(['2A','3B','4C','5D'])}"
        zipcode = f"{random.randint(10000, 99999)}"
        issues = []
        fixes = []
        score = round(random.uniform(0.75, 0.95), 2)
    else:
        street = random.choice(["123 Main St", "PO Box 1234", "1 Test Ave"])
        zipcode = f"{random.randint(10000, 99999)}"
        issues = [f"Street '{street}' is {'generic/blacklisted' if '123' in street else 'a PO Box — rejected by many merchants'}"]
        fixes = ["Use a realistic, specific street address"]
        score = round(random.uniform(0.2, 0.5), 2)

    address = {"street": street, "city": random.choice(US_CITIES.get(state, ["Springfield"])), "state": state, "zip": zipcode, "country": "US"}

    prompt = f"Pre-validate AVS for this address: {json.dumps(address)}, card country US, target {random.choice(list(KNOWN_TARGETS.keys()))}"
    response = json.dumps({
        "avs_likely_pass": valid,
        "confidence": score,
        "issues": issues,
        "address_fixes": fixes,
        "zip_format_ok": len(zipcode) == 5,
    })

    return {"prompt": prompt, "response": response, "task": "avs_prevalidation"}


GENERATORS = {
    "bin_analysis": gen_bin_analysis,
    "target_recon": gen_target_recon,
    "fingerprint_coherence": gen_fingerprint_coherence,
    "identity_graph": gen_identity_graph,
    "environment_coherence": gen_environment_coherence,
    "decline_autopsy": gen_decline_autopsy,
    "session_rhythm": gen_session_rhythm,
    "card_rotation": gen_card_rotation,
    "velocity_schedule": gen_velocity_schedule,
    "avs_prevalidation": gen_avs_prevalidation,
}


def main():
    parser = argparse.ArgumentParser(description="Titan V8.3 Training Data Generator")
    parser.add_argument("--tasks", default="all", help="Comma-separated task types or 'all'")
    parser.add_argument("--count", type=int, default=50, help="Examples per task type")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.tasks == "all":
        tasks = list(GENERATORS.keys())
    else:
        tasks = [t.strip() for t in args.tasks.split(",")]

    total = 0
    for task in tasks:
        gen_func = GENERATORS.get(task)
        if not gen_func:
            print(f"WARNING: No generator for task '{task}', skipping")
            continue

        output_file = os.path.join(args.output, f"{task}.jsonl")
        count = 0
        with open(output_file, "w") as f:
            for i in range(args.count):
                try:
                    example = gen_func()
                    f.write(json.dumps(example) + "\n")
                    count += 1
                except Exception as e:
                    print(f"ERROR generating {task} example {i}: {e}")

        total += count
        print(f"Generated {count} examples for '{task}' -> {output_file}")

    print(f"\nTotal: {total} training examples across {len(tasks)} task types")
    print(f"Output directory: {args.output}")


if __name__ == "__main__":
    main()
