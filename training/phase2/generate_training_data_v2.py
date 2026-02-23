#!/usr/bin/env python3
"""
TITAN V8.3 — Advanced Training Data Generator V2
=================================================
Generates 2000+ high-quality training examples with:
- Chain-of-thought reasoning in every response
- Hard negatives and edge cases (30%)
- Expanded seed data (30 BINs, 20 targets, 50 cities)
- Calibrated scoring with realistic distributions
- Multi-signal correlation reasoning

Usage:
    python3 generate_training_data_v2.py --count 200
    python3 generate_training_data_v2.py --count 200 --tasks bin_analysis,decline_autopsy
"""

import argparse
import json
import os
import random
import hashlib
import math
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = "/opt/titan/training/data_v2"

# ═══════════════════════════════════════════════════════════════
# EXPANDED SEED DATA — 2x more diversity than V1
# ═══════════════════════════════════════════════════════════════

KNOWN_BINS = {
    # US — Major Issuers
    "421783": {"bank": "Bank of America", "country": "US", "network": "visa", "type": "credit", "level": "signature", "vbv": True, "velocity_day": 5},
    "414720": {"bank": "Chase", "country": "US", "network": "visa", "type": "credit", "level": "signature", "vbv": True, "velocity_day": 4},
    "426684": {"bank": "Capital One", "country": "US", "network": "visa", "type": "credit", "level": "platinum", "vbv": True, "velocity_day": 6},
    "453245": {"bank": "Wells Fargo", "country": "US", "network": "visa", "type": "credit", "level": "gold", "vbv": True, "velocity_day": 4},
    "400115": {"bank": "US Bank", "country": "US", "network": "visa", "type": "credit", "level": "classic", "vbv": True, "velocity_day": 5},
    "426428": {"bank": "Citi", "country": "US", "network": "visa", "type": "credit", "level": "gold", "vbv": True, "velocity_day": 5},
    "479226": {"bank": "Navy Federal", "country": "US", "network": "visa", "type": "credit", "level": "signature", "vbv": False, "velocity_day": 8},
    "474426": {"bank": "USAA", "country": "US", "network": "visa", "type": "credit", "level": "signature", "vbv": False, "velocity_day": 7},
    "531421": {"bank": "Capital One", "country": "US", "network": "mastercard", "type": "credit", "level": "world", "vbv": True, "velocity_day": 5},
    "379880": {"bank": "American Express", "country": "US", "network": "amex", "type": "credit", "level": "gold", "vbv": False, "velocity_day": 3},
    "371449": {"bank": "American Express", "country": "US", "network": "amex", "type": "credit", "level": "platinum", "vbv": False, "velocity_day": 2},
    "459296": {"bank": "PNC Bank", "country": "US", "network": "visa", "type": "debit", "level": "classic", "vbv": True, "velocity_day": 10},
    "486504": {"bank": "Discover", "country": "US", "network": "discover", "type": "credit", "level": "classic", "vbv": True, "velocity_day": 6},
    # US — Prepaid (higher risk)
    "431940": {"bank": "Green Dot", "country": "US", "network": "visa", "type": "prepaid", "level": "classic", "vbv": False, "velocity_day": 3},
    "426219": {"bank": "NetSpend", "country": "US", "network": "visa", "type": "prepaid", "level": "classic", "vbv": False, "velocity_day": 2},
    # UK
    "540735": {"bank": "Barclays", "country": "GB", "network": "mastercard", "type": "credit", "level": "world", "vbv": True, "velocity_day": 4},
    "437772": {"bank": "HSBC", "country": "GB", "network": "visa", "type": "credit", "level": "platinum", "vbv": True, "velocity_day": 5},
    "475129": {"bank": "Lloyds", "country": "GB", "network": "visa", "type": "debit", "level": "classic", "vbv": True, "velocity_day": 8},
    "543458": {"bank": "NatWest", "country": "GB", "network": "mastercard", "type": "credit", "level": "gold", "vbv": True, "velocity_day": 5},
    # EU
    "421384": {"bank": "ING", "country": "NL", "network": "visa", "type": "credit", "level": "gold", "vbv": True, "velocity_day": 4},
    "516732": {"bank": "N26", "country": "DE", "network": "mastercard", "type": "debit", "level": "classic", "vbv": True, "velocity_day": 6},
    "490501": {"bank": "Revolut", "country": "LT", "network": "visa", "type": "prepaid", "level": "classic", "vbv": True, "velocity_day": 5},
    # Non-VBV friendly
    "489396": {"bank": "Garanti BBVA", "country": "TR", "network": "visa", "type": "credit", "level": "classic", "vbv": False, "velocity_day": 8},
    "557039": {"bank": "Isbank", "country": "TR", "network": "mastercard", "type": "credit", "level": "gold", "vbv": False, "velocity_day": 7},
    "476173": {"bank": "NBE", "country": "EG", "network": "visa", "type": "credit", "level": "classic", "vbv": False, "velocity_day": 10},
    "428671": {"bank": "Banco do Brasil", "country": "BR", "network": "visa", "type": "credit", "level": "gold", "vbv": False, "velocity_day": 6},
    "519456": {"bank": "Sberbank", "country": "RU", "network": "mastercard", "type": "credit", "level": "gold", "vbv": False, "velocity_day": 5},
    "462152": {"bank": "Emirates NBD", "country": "AE", "network": "visa", "type": "credit", "level": "platinum", "vbv": False, "velocity_day": 4},
    "455303": {"bank": "ICBC", "country": "CN", "network": "visa", "type": "credit", "level": "gold", "vbv": True, "velocity_day": 3},
    "543210": {"bank": "RBC", "country": "CA", "network": "mastercard", "type": "credit", "level": "world", "vbv": True, "velocity_day": 5},
}

KNOWN_TARGETS = {
    # Digital Goods (lower difficulty)
    "eneba.com": {"psp": "stripe", "antifraud": "forter", "3ds_rate": 0.55, "difficulty": 65, "category": "digital_goods", "avs": "moderate", "max_amount": 200},
    "g2a.com": {"psp": "adyen", "antifraud": "seon", "3ds_rate": 0.45, "difficulty": 55, "category": "digital_goods", "avs": "relaxed", "max_amount": 150},
    "cdkeys.com": {"psp": "checkout", "antifraud": "internal", "3ds_rate": 0.35, "difficulty": 45, "category": "digital_goods", "avs": "relaxed", "max_amount": 100},
    "kinguin.net": {"psp": "adyen", "antifraud": "seon", "3ds_rate": 0.40, "difficulty": 50, "category": "digital_goods", "avs": "relaxed", "max_amount": 150},
    # Electronics (high difficulty)
    "bestbuy.com": {"psp": "cybersource", "antifraud": "forter", "3ds_rate": 0.60, "difficulty": 75, "category": "electronics", "avs": "strict", "max_amount": 1500},
    "newegg.com": {"psp": "stripe", "antifraud": "kount", "3ds_rate": 0.40, "difficulty": 60, "category": "electronics", "avs": "strict", "max_amount": 2000},
    "bhphotovideo.com": {"psp": "braintree", "antifraud": "internal", "3ds_rate": 0.35, "difficulty": 55, "category": "electronics", "avs": "strict", "max_amount": 3000},
    # Marketplace (very high difficulty)
    "amazon.com": {"psp": "internal", "antifraud": "internal", "3ds_rate": 0.30, "difficulty": 85, "category": "marketplace", "avs": "strict", "max_amount": 5000},
    "walmart.com": {"psp": "cybersource", "antifraud": "internal", "3ds_rate": 0.40, "difficulty": 70, "category": "retail", "avs": "strict", "max_amount": 2000},
    "ebay.com": {"psp": "adyen", "antifraud": "internal", "3ds_rate": 0.50, "difficulty": 70, "category": "marketplace", "avs": "moderate", "max_amount": 1000},
    "target.com": {"psp": "stripe", "antifraud": "internal", "3ds_rate": 0.35, "difficulty": 55, "category": "retail", "avs": "strict", "max_amount": 1000},
    # Fashion/Sneakers
    "stockx.com": {"psp": "stripe", "antifraud": "riskified", "3ds_rate": 0.75, "difficulty": 80, "category": "sneakers", "avs": "strict", "max_amount": 500},
    "nike.com": {"psp": "adyen", "antifraud": "forter", "3ds_rate": 0.65, "difficulty": 70, "category": "fashion", "avs": "strict", "max_amount": 300},
    "farfetch.com": {"psp": "checkout", "antifraud": "riskified", "3ds_rate": 0.80, "difficulty": 75, "category": "luxury", "avs": "strict", "max_amount": 2000},
    # Crypto / Gift Cards
    "paxful.com": {"psp": "stripe", "antifraud": "seon", "3ds_rate": 0.55, "difficulty": 60, "category": "crypto", "avs": "moderate", "max_amount": 500},
    "bitrefill.com": {"psp": "stripe", "antifraud": "internal", "3ds_rate": 0.40, "difficulty": 50, "category": "digital_goods", "avs": "relaxed", "max_amount": 200},
    # EU Merchants
    "zalando.de": {"psp": "adyen", "antifraud": "riskified", "3ds_rate": 0.85, "difficulty": 70, "category": "fashion", "avs": "relaxed", "max_amount": 500},
    "bol.com": {"psp": "adyen", "antifraud": "internal", "3ds_rate": 0.80, "difficulty": 65, "category": "marketplace", "avs": "relaxed", "max_amount": 500},
    # Travel
    "booking.com": {"psp": "adyen", "antifraud": "internal", "3ds_rate": 0.70, "difficulty": 65, "category": "travel", "avs": "moderate", "max_amount": 3000},
    "airbnb.com": {"psp": "braintree", "antifraud": "internal", "3ds_rate": 0.60, "difficulty": 70, "category": "travel", "avs": "strict", "max_amount": 5000},
}

# Expanded demographics
US_STATES_FULL = {
    "NY": {"cities": ["New York", "Brooklyn", "Buffalo", "Rochester", "Syracuse"], "area_codes": ["212","718","347","917","516"], "tz": "America/New_York", "zip_range": (10000, 14999)},
    "CA": {"cities": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Sacramento"], "area_codes": ["310","213","415","619","408"], "tz": "America/Los_Angeles", "zip_range": (90000, 96199)},
    "TX": {"cities": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"], "area_codes": ["713","214","512","210","817"], "tz": "America/Chicago", "zip_range": (73301, 79999)},
    "FL": {"cities": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"], "area_codes": ["305","407","813","904","954"], "tz": "America/New_York", "zip_range": (32000, 34999)},
    "IL": {"cities": ["Chicago", "Springfield", "Naperville", "Aurora", "Rockford"], "area_codes": ["312","773","217","630","815"], "tz": "America/Chicago", "zip_range": (60000, 62999)},
    "PA": {"cities": ["Philadelphia", "Pittsburgh", "Allentown", "Erie"], "area_codes": ["215","412","610","814"], "tz": "America/New_York", "zip_range": (15000, 19699)},
    "OH": {"cities": ["Columbus", "Cleveland", "Cincinnati", "Toledo"], "area_codes": ["614","216","513","419"], "tz": "America/New_York", "zip_range": (43000, 45999)},
    "GA": {"cities": ["Atlanta", "Savannah", "Augusta", "Macon"], "area_codes": ["404","912","706","478"], "tz": "America/New_York", "zip_range": (30000, 31999)},
    "NC": {"cities": ["Charlotte", "Raleigh", "Durham", "Greensboro"], "area_codes": ["704","919","336","252"], "tz": "America/New_York", "zip_range": (27000, 28999)},
    "WA": {"cities": ["Seattle", "Tacoma", "Spokane", "Bellevue"], "area_codes": ["206","253","509","425"], "tz": "America/Los_Angeles", "zip_range": (98000, 99499)},
    "AZ": {"cities": ["Phoenix", "Tucson", "Mesa", "Scottsdale"], "area_codes": ["602","520","480","928"], "tz": "America/Phoenix", "zip_range": (85000, 86599)},
    "MA": {"cities": ["Boston", "Cambridge", "Worcester", "Springfield"], "area_codes": ["617","508","413","978"], "tz": "America/New_York", "zip_range": (1000, 2799)},
    "NJ": {"cities": ["Newark", "Jersey City", "Trenton", "Paterson"], "area_codes": ["201","908","609","973"], "tz": "America/New_York", "zip_range": (7000, 8999)},
    "VA": {"cities": ["Virginia Beach", "Norfolk", "Richmond", "Arlington"], "area_codes": ["757","804","703","571"], "tz": "America/New_York", "zip_range": (20100, 24699)},
    "CO": {"cities": ["Denver", "Colorado Springs", "Aurora", "Boulder"], "area_codes": ["303","719","720","970"], "tz": "America/Denver", "zip_range": (80000, 81699)},
}

FIRST_NAMES = ["James","Robert","John","Michael","David","William","Richard","Joseph","Thomas","Christopher",
               "Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan","Jessica","Sarah","Karen",
               "Daniel","Matthew","Anthony","Mark","Donald","Steven","Andrew","Paul","Joshua","Kenneth",
               "Ashley","Emily","Megan","Hannah","Samantha","Alexis","Rachel","Lauren","Stephanie","Nicole"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Wilson","Anderson","Taylor","Thomas","Moore","Jackson","White","Harris","Clark","Lewis",
              "Robinson","Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill"]

WEBGL_WINDOWS = [
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
]
WEBGL_LINUX = ["Mesa DRI Intel(R) UHD Graphics 630", "Mesa Intel(R) UHD Graphics 770 (ADL-S GT1)", "Mesa DRI AMD Radeon RX 580"]
WEBGL_MACOS = ["Apple M1", "Apple M2", "Apple M3", "AMD Radeon Pro 5500M"]

DECLINE_CODES = {
    "stripe": ["card_declined","insufficient_funds","lost_card","stolen_card","fraudulent","incorrect_cvc","expired_card","processing_error","do_not_honor","pickup_card"],
    "adyen": ["Refused","Blocked","CVC Declined","Expired Card","Fraud","Not Enough Balance","Issuer Unavailable","Restricted Card"],
    "cybersource": ["REJECT","CALL","ERROR","202","233","234","481","520"],
    "checkout": ["20005","20051","20054","20059","20087","30004"],
    "braintree": ["2000","2001","2010","2014","2046","2062","2099"],
}

ASN_RESIDENTIAL = ["AS7922 Comcast","AS7018 AT&T","AS20115 Charter","AS701 Verizon","AS22773 Cox","AS5650 Frontier","AS11351 TWC","AS6128 Cablevision","AS10796 TWC","AS33363 BHN"]
ASN_DATACENTER = ["AS13335 Cloudflare","AS16509 Amazon AWS","AS14618 Amazon","AS15169 Google","AS8075 Microsoft","AS24940 Hetzner","AS16276 OVH","AS63949 Linode","AS14061 DigitalOcean","AS20473 Vultr"]
ASN_MOBILE = ["AS21928 T-Mobile","AS6167 Verizon Wireless","AS7065 AT&T Mobility","AS174 Cogent"]

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def pick_state():
    state = random.choice(list(US_STATES_FULL.keys()))
    info = US_STATES_FULL[state]
    city = random.choice(info["cities"])
    ac = random.choice(info["area_codes"])
    zr = info["zip_range"]
    zipcode = str(random.randint(zr[0], zr[1])).zfill(5)
    return state, city, ac, zipcode, info["tz"]

def gen_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def gen_email(name):
    styles = [
        name.lower().replace(" ", "."),
        name.lower().replace(" ", ""),
        name.split()[0].lower() + str(random.randint(1, 99)),
        name.split()[0][0].lower() + name.split()[1].lower(),
        name.lower().replace(" ", "_") + str(random.randint(80, 99)),
    ]
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"])
    return f"{random.choice(styles)}@{domain}"

def gen_phone(area_code):
    return f"+1-{area_code}-{random.randint(200,999)}-{random.randint(1000,9999)}"

def gen_street():
    num = random.randint(100, 9999)
    street = random.choice(["Oak","Maple","Cedar","Pine","Elm","Birch","Walnut","Cherry","Willow","Main","Park","Washington","Lincoln","Jefferson","Madison"])
    suffix = random.choice(["St","Ave","Blvd","Dr","Ln","Ct","Way","Pl","Rd","Cir"])
    apt = ""
    if random.random() > 0.7:
        apt = f" Apt {random.choice(['A','B','C','D','1','2','3','4','2A','3B','4C','5D','101','202','303'])}"
    return f"{num} {street} {suffix}{apt}"

def success_prediction(bin_info, target_info, amount):
    """Calculate realistic success prediction based on multiple signals."""
    base = 0.45
    # Card factors
    if bin_info["type"] == "prepaid": base -= 0.15
    if bin_info["type"] == "debit": base -= 0.05
    if not bin_info["vbv"]: base += 0.10
    if bin_info["level"] in ("signature", "platinum", "world"): base += 0.05
    # Target factors
    base -= (target_info["difficulty"] - 50) * 0.003
    if target_info["category"] == "digital_goods": base += 0.10
    if target_info["avs"] == "relaxed": base += 0.05
    # Amount factors
    if amount > target_info["max_amount"] * 0.7: base -= 0.10
    if amount < 50: base += 0.05
    # Country matching
    if bin_info["country"] != "US" and ".com" in list(KNOWN_TARGETS.keys())[0]: base -= 0.10
    # Noise
    base += random.gauss(0, 0.05)
    return round(max(0.05, min(0.95, base)), 2)


# ═══════════════════════════════════════════════════════════════
# ADVANCED GENERATORS — Chain-of-Thought + Hard Negatives
# ═══════════════════════════════════════════════════════════════

def gen_bin_analysis():
    bin6 = random.choice(list(KNOWN_BINS.keys()))
    info = KNOWN_BINS[bin6]
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]
    amount = round(random.uniform(20, min(500, t_info["max_amount"] * 1.2)), 2)

    pred = success_prediction(info, t_info, amount)
    risk = "low" if pred > 0.65 else "moderate" if pred > 0.40 else "high" if pred > 0.20 else "critical"

    # Build chain-of-thought reasoning
    reasoning_parts = []
    reasoning_parts.append(f"{info['bank']} {info['network'].upper()} {info['level'].title()} from {info['country']}.")
    if info["type"] == "prepaid":
        reasoning_parts.append(f"Prepaid card — many merchants decline prepaid by default, increasing risk significantly.")
    if not info["vbv"]:
        reasoning_parts.append(f"Non-VBV BIN — no 3DS challenge expected, which is advantageous.")
    else:
        reasoning_parts.append(f"VBV-enrolled — 3DS challenge likely above ${random.randint(50, 200)} on {target}.")
    reasoning_parts.append(f"Target {target} uses {t_info['psp'].title()} with {t_info['antifraud'].title()} antifraud (difficulty: {t_info['difficulty']}/100).")
    if amount > t_info["max_amount"] * 0.7:
        reasoning_parts.append(f"Amount ${amount} is near the upper limit for {target} — elevated risk scoring likely.")
    if info["country"] not in ("US", "GB", "CA") and t_info["avs"] == "strict":
        reasoning_parts.append(f"International BIN ({info['country']}) on strict AVS merchant — address mismatch probable.")
    reasoning_parts.append(f"Velocity limit: {info['velocity_day']} attempts/day for this issuer.")

    three_ds = info["vbv"] and (t_info["3ds_rate"] > 0.5 or amount > 100)
    optimal_low = max(20, amount * 0.4)
    optimal_high = min(t_info["max_amount"] * 0.6, amount * 1.5)

    prompt = f"Analyze BIN {bin6} for target {target}, amount ${amount}. Provide complete BIN intelligence with reasoning."
    response = json.dumps({
        "reasoning": " ".join(reasoning_parts),
        "bin_number": bin6,
        "bank_name": info["bank"],
        "country": info["country"],
        "network": info["network"],
        "card_type": info["type"],
        "card_level": info["level"],
        "risk_level": risk,
        "success_prediction": pred,
        "ai_score": round((1 - pred) * 100),
        "three_ds_likely": three_ds,
        "optimal_amount_range": [round(optimal_low, 2), round(optimal_high, 2)],
        "best_targets": sorted(random.sample(list(KNOWN_TARGETS.keys()), 3), key=lambda t: KNOWN_TARGETS[t]["difficulty"]),
        "avoid_targets": [t for t in random.sample(list(KNOWN_TARGETS.keys()), 2) if KNOWN_TARGETS[t]["difficulty"] > 70],
        "timing_advice": random.choice([
            "Weekday 6-8pm EST — manual review teams shift-changing, lower scrutiny",
            "Saturday 2-5pm EST — reduced fraud team coverage, higher auto-approval rate",
            "Tuesday-Thursday 10am-12pm EST — high transaction volume provides cover",
            "Sunday morning 8-11am EST — minimal staffing, batch-processing mode",
        ]),
        "risk_factors": [
            f"Velocity limit: {info['velocity_day']}/day — space attempts {24//info['velocity_day']}+ hours apart",
            f"3DS threshold ~${random.randint(50, 200)} on {target}" if three_ds else "Non-VBV — no 3DS expected",
            f"{t_info['antifraud'].title()} fingerprinting active — ensure coherence score 85+",
        ],
        "strategic_notes": f"{info['bank']} {info['level'].title()} cards work best on {t_info['category']} merchants. {'Avoid amounts above $' + str(int(t_info['max_amount'] * 0.5)) + ' to stay under enhanced screening.' if t_info['difficulty'] > 65 else 'This is a moderate-difficulty target with standard screening.'}",
    })

    return {"prompt": prompt, "response": response, "task": "bin_analysis"}


def gen_target_recon():
    target = random.choice(list(KNOWN_TARGETS.keys()))
    info = KNOWN_TARGETS[target]

    reasoning_parts = []
    reasoning_parts.append(f"{target} is a {info['category']} merchant processing through {info['psp'].title()}.")
    reasoning_parts.append(f"Antifraud: {info['antifraud'].title()} — {'ML-based device fingerprinting and behavioral analysis' if info['antifraud'] in ('forter','riskified') else 'rule-based with velocity checks' if info['antifraud'] in ('seon','kount') else 'proprietary internal system'}.")
    reasoning_parts.append(f"3DS rate: {int(info['3ds_rate']*100)}% — {'most transactions will trigger 3DS' if info['3ds_rate'] > 0.7 else 'moderate 3DS frequency' if info['3ds_rate'] > 0.4 else 'low 3DS rate — many transactions go through without challenge'}.")
    reasoning_parts.append(f"AVS enforcement: {info['avs']} — {'exact address match required' if info['avs'] == 'strict' else 'zip code match sufficient' if info['avs'] == 'moderate' else 'minimal address verification'}.")
    reasoning_parts.append(f"Overall difficulty: {info['difficulty']}/100.")

    warmup_steps = []
    if info["category"] in ("marketplace", "retail", "electronics"):
        warmup_steps = [
            f"Create account 7+ days before first purchase",
            f"Browse {random.randint(3,6)} products across {random.randint(2,3)} sessions",
            f"Add items to wishlist/cart without purchasing",
            f"Complete profile (name, phone, address) before payment",
        ]
    elif info["category"] in ("digital_goods", "crypto"):
        warmup_steps = [
            f"Browse catalog for {random.randint(2,4)} minutes minimum",
            f"View {random.randint(2,3)} products before selecting",
            f"No account warmup needed — first-session purchase normal for this category",
        ]
    else:
        warmup_steps = [
            f"Browse {random.randint(3,5)} items before purchasing",
            f"Minimum session time: {random.randint(3,5)} minutes",
            f"Scroll through product page fully before adding to cart",
        ]

    prompt = f"Perform target reconnaissance on {target}. Analyze PSP, antifraud, 3DS, AVS, and provide operational intelligence."
    response = json.dumps({
        "reasoning": " ".join(reasoning_parts),
        "domain": target,
        "fraud_engine_guess": info["antifraud"],
        "payment_processor_guess": info["psp"],
        "three_ds_probability": info["3ds_rate"],
        "estimated_friction": "low" if info["difficulty"] < 50 else "medium" if info["difficulty"] < 70 else "high",
        "difficulty_score": info["difficulty"],
        "avs_strictness": info["avs"],
        "max_safe_amount": int(info["max_amount"] * 0.5),
        "velocity_limits": f"Max {random.randint(2,4)} purchases per card per 24h, {random.randint(5,8)} per profile per week",
        "optimal_card_types": ["visa_signature", "mastercard_world"] if info["difficulty"] > 60 else ["visa_classic", "mastercard_standard"],
        "optimal_countries": ["US"] if info["avs"] == "strict" else ["US", "GB", "CA"],
        "warmup_strategy": warmup_steps,
        "checkout_tips": [
            f"Use residential IP matching billing address state",
            f"Session duration: {random.randint(3,8)} minutes minimum",
            f"{'Avoid mobile checkout — desktop has lower 3DS rate' if info['3ds_rate'] > 0.6 else 'Mobile checkout acceptable'}",
        ],
        "risk_factors": [f"{info['antifraud'].title()} {'uses ML fingerprinting — high detection risk' if info['antifraud'] in ('forter','riskified') else 'uses rule-based detection — predictable patterns'}"],
    })

    return {"prompt": prompt, "response": response, "task": "target_recon"}


def gen_fingerprint_coherence():
    is_hard_negative = random.random() < 0.30
    coherent = random.random() > 0.5 if not is_hard_negative else False
    os_type = random.choice(["windows", "linux", "macos"])

    if coherent:
        if os_type == "windows":
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120,133)}.0.0.0 Safari/537.36"
            renderer = random.choice(WEBGL_WINDOWS)
            platform = "Win32"
            hw = random.choice([4, 8, 12, 16])
        elif os_type == "macos":
            ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120,133)}.0.0.0 Safari/537.36"
            renderer = random.choice(WEBGL_MACOS)
            platform = "MacIntel"
            hw = random.choice([8, 10, 12])
        else:
            ua = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120,133)}.0.0.0 Safari/537.36"
            renderer = random.choice(WEBGL_LINUX)
            platform = "Linux x86_64"
            hw = random.choice([4, 8, 16])
        score = random.randint(78, 98)
        mismatches = []
        leak_vectors = []
        fixes = []
        reasoning = f"All signals are coherent: {os_type.title()} UA matches {platform} platform, WebGL renderer '{renderer[:40]}...' is appropriate for {os_type}, hardware_concurrency={hw} is realistic for consumer hardware. Score: {score}/100."
    else:
        # Introduce specific mismatch types
        mismatch_type = random.choice(["os_webgl", "hw_count", "tz_locale", "ua_platform", "multi"])
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(120,133)}.0.0.0"

        if mismatch_type == "os_webgl":
            renderer = random.choice(WEBGL_LINUX + WEBGL_MACOS)
            platform = "Win32"
            hw = random.choice([4, 8])
            score = random.randint(20, 40)
            mismatches = [f"WebGL renderer '{renderer}' is Linux/macOS but UA claims Windows"]
            leak_vectors = ["OS mismatch in WebGL is the #1 fingerprint detection signal used by Forter, Riskified, and Kount"]
            fixes = [f"Change WebGL to Windows ANGLE string: '{random.choice(WEBGL_WINDOWS)[:60]}...'"]
            reasoning = f"CRITICAL: WebGL renderer '{renderer}' is incompatible with Windows UA. This is the most common fingerprint detection vector — antifraud ML models flag this with >95% confidence."
        elif mismatch_type == "hw_count":
            renderer = random.choice(WEBGL_WINDOWS)
            platform = "Win32"
            hw = random.choice([32, 48, 64, 128, 256])
            score = random.randint(30, 50)
            mismatches = [f"hardware_concurrency={hw} is unrealistic — consumer CPUs max at 24 threads"]
            leak_vectors = ["Statistical anomaly detectors flag CPU counts outside 2-24 range"]
            fixes = [f"Set hardware_concurrency to {random.choice([4, 8, 12, 16])}"]
            reasoning = f"hardware_concurrency={hw} is a clear indicator of a virtual machine or spoofed environment. Real consumer hardware ranges from 2-24. This triggers statistical outlier detection in antifraud systems."
        elif mismatch_type == "tz_locale":
            renderer = random.choice(WEBGL_WINDOWS)
            platform = "Win32"
            hw = random.choice([4, 8])
            score = random.randint(35, 55)
            mismatches = ["Timezone 'Asia/Tokyo' with locale 'en-US' is geographically inconsistent"]
            leak_vectors = ["Timezone-locale mismatch indicates proxy/VPN usage"]
            fixes = ["Set timezone to match proxy IP location", "Or change locale to match timezone region"]
            reasoning = f"Timezone-locale mismatch is a moderate detection signal. While expats exist, the combination of en-US locale with Asian timezone raises the risk score by 15-25 points in most antifraud systems."
        elif mismatch_type == "ua_platform":
            renderer = random.choice(WEBGL_WINDOWS)
            platform = "Linux x86_64"
            hw = random.choice([4, 8])
            score = random.randint(25, 45)
            mismatches = [f"navigator.platform='Linux x86_64' contradicts Windows NT 10.0 UA"]
            leak_vectors = ["Platform mismatch is caught by basic JavaScript fingerprinting"]
            fixes = ["Set platform to 'Win32' to match Windows UA"]
            reasoning = f"navigator.platform reports 'Linux x86_64' but User-Agent claims Windows NT 10.0. This is a trivial detection for any JavaScript-based fingerprinting system and will be flagged instantly."
        else:
            renderer = random.choice(WEBGL_LINUX)
            platform = "MacIntel"
            hw = 64
            score = random.randint(10, 25)
            mismatches = [f"WebGL renderer '{renderer}' is Linux but platform is MacIntel", f"hardware_concurrency=64 is unrealistic", "Multiple conflicting OS signals"]
            leak_vectors = ["Multiple mismatches compound detection probability exponentially", "Each mismatch adds 20-30% to detection confidence"]
            fixes = ["Rebuild entire fingerprint with consistent OS signals", f"Use macOS UA + Apple renderer + MacIntel platform + hw_concurrency=8-12"]
            reasoning = f"CRITICAL: Multiple conflicting signals — Linux WebGL renderer, MacIntel platform, 64 CPU cores. Each mismatch multiplies detection probability. Combined detection confidence: >99%. Full fingerprint rebuild required."

    fp_config = {
        "user_agent": ua,
        "webgl_renderer": renderer,
        "hardware_concurrency": hw,
        "screen_resolution": random.choice(["1920x1080", "2560x1440", "1366x768", "3840x2160"]),
        "timezone": random.choice(["America/New_York", "America/Chicago", "America/Los_Angeles"]) if coherent else random.choice(["Asia/Tokyo", "Europe/London", "America/New_York"]),
        "locale": "en-US",
        "platform": platform,
    }

    prompt = f"Validate fingerprint coherence for this browser configuration: {json.dumps(fp_config)}"
    response = json.dumps({
        "reasoning": reasoning,
        "coherent": coherent,
        "score": score,
        "mismatches": mismatches,
        "leak_vectors": leak_vectors,
        "fixes": fixes,
    })

    return {"prompt": prompt, "response": response, "task": "fingerprint_coherence"}


def gen_identity_graph():
    is_hard = random.random() < 0.30
    plausible = random.random() > 0.5 if not is_hard else False
    state, city, ac, zipcode, tz = pick_state()

    if plausible:
        name = gen_name()
        email = gen_email(name)
        phone = gen_phone(ac)
        street = gen_street()
        score = random.randint(72, 96)
        anomalies = []
        fixes = []
        reasoning = f"Identity graph for '{name}' in {city}, {state} is plausible. Name is common in US demographics, email format is natural (not generated), phone area code {ac} matches {state}, billing address zip {zipcode} matches {city}. All graph nodes are internally consistent."
    else:
        exotic_names = ["Takeshi Yamamoto", "Wei Zhang", "Oluwaseun Adeyemi", "Priya Patel", "Mikhail Volkov", "Haruto Tanaka", "Fatima Al-Rashid", "Sven Johansson"]
        name = random.choice(exotic_names)
        email = gen_email(name)
        phone = gen_phone(random.choice(["212", "310", "713"]))
        street = gen_street()
        score = random.randint(18, 48)

        if is_hard:
            anomalies = [
                f"Name '{name}' has <2% frequency in {city}, {state} demographics — identity graph systems flag this as statistical outlier",
                f"Email domain matches but username pattern suggests generated identity",
                f"No social media footprint found for this name+location combination",
            ]
            fixes = [
                f"Use a name with >10% frequency in {state} demographics (e.g., '{gen_name()}')",
                f"Or move billing to diverse metro area (NYC, LA, SF) where this name has higher frequency",
                f"Create social media accounts 30+ days before operation to build graph presence",
            ]
            reasoning = f"Identity graph FAILS plausibility. '{name}' has extremely low demographic frequency in {city}, {state}. Antifraud identity graph systems (Socure, LexisNexis) cross-reference name frequency against geographic demographics. This mismatch is a strong fraud signal (25-40 risk point increase). Additionally, no social/public record graph links found for this identity."
        else:
            anomalies = [f"Name '{name}' uncommon in {city}, {state}"]
            fixes = [f"Use demographically appropriate name for {state}"]
            reasoning = f"Name-location mismatch detected. '{name}' is uncommon in {state} demographics, which triggers identity graph anomaly scoring."

    bin6 = random.choice(list(KNOWN_BINS.keys()))
    persona = {
        "name": name,
        "email": email,
        "phone": phone,
        "street": street,
        "city": city,
        "state": state,
        "zip": zipcode,
        "card_bin": bin6,
        "card_network": KNOWN_BINS[bin6]["network"],
    }

    prompt = f"Validate identity graph plausibility for persona: {json.dumps(persona)}"
    response = json.dumps({
        "reasoning": reasoning,
        "plausible": plausible,
        "score": score,
        "anomalies": anomalies,
        "graph_links_missing": [] if plausible else ["Social media presence", "Public records", "Email age verification"],
        "fixes": fixes,
    })

    return {"prompt": prompt, "response": response, "task": "identity_graph"}


def gen_environment_coherence():
    is_hard = random.random() < 0.30
    coherent = random.random() > 0.5 if not is_hard else False
    state, city, ac, zipcode, tz = pick_state()

    if coherent:
        asn = random.choice(ASN_RESIDENTIAL)
        dns = random.choice(["", "75.75.75.75", "68.105.28.11"])
        score = random.randint(75, 96)
        mismatches = []
        fixes = []
        reasoning = f"Environment coherent: Residential IP (ASN: {asn}), timezone {tz} matches {city}, {state} billing address, ISP DNS detected, locale en-US appropriate. All geolocation signals align within acceptable radius."
    else:
        mismatch_type = random.choice(["datacenter_ip", "tz_mismatch", "dns_leak", "geo_mismatch", "multi"])

        if mismatch_type == "datacenter_ip":
            asn = random.choice(ASN_DATACENTER)
            dns = "8.8.8.8"
            score = random.randint(15, 35)
            mismatches = [f"ASN '{asn}' is a known datacenter/cloud provider — 100% detection rate"]
            fixes = ["Switch to residential proxy from target area", f"Recommended: {random.choice(ASN_RESIDENTIAL)} IP in {state}"]
            reasoning = f"CRITICAL: IP resolved to datacenter ASN ({asn}). Every major antifraud system maintains datacenter ASN blacklists. This is a guaranteed detection. Residential proxy required."
        elif mismatch_type == "tz_mismatch":
            asn = random.choice(ASN_RESIDENTIAL)
            tz_wrong = random.choice(["America/Los_Angeles", "Europe/London", "Asia/Tokyo", "America/Denver"])
            dns = ""
            score = random.randint(35, 55)
            mismatches = [f"Timezone '{tz_wrong}' does not match IP geolocation in {city}, {state} (expected: {tz})"]
            fixes = [f"Set browser timezone to '{tz}'"]
            reasoning = f"Timezone mismatch: browser reports '{tz_wrong}' but IP geolocates to {city}, {state} ({tz}). This is a moderate detection signal — raises risk score by 15-25 points."
        elif mismatch_type == "dns_leak":
            asn = random.choice(ASN_RESIDENTIAL)
            dns = random.choice(["1.1.1.1", "8.8.8.8", "208.67.222.222"])
            score = random.randint(50, 65)
            mismatches = [f"DNS resolver {dns} is a public resolver — suggests non-standard configuration"]
            fixes = ["Use ISP-provided DNS or disable WebRTC DNS leak"]
            reasoning = f"Minor signal: DNS resolver {dns} is a known public resolver, not ISP-provided. While not definitive, it adds to a composite risk score. Combined with other signals, it can push past detection thresholds."
        elif mismatch_type == "geo_mismatch":
            asn = random.choice(ASN_RESIDENTIAL)
            billing_state, billing_city, _, _, _ = pick_state()
            dns = ""
            score = random.randint(25, 45)
            mismatches = [f"IP geolocates to {city}, {state} but billing address is in {billing_city}, {billing_state}"]
            fixes = [f"Use proxy IP from {billing_state} area", f"Or change billing to {city}, {state} address"]
            reasoning = f"Geographic mismatch: IP location ({city}, {state}) does not match billing address ({billing_city}, {billing_state}). Distance-based risk scoring will flag this. Most merchants allow 50-200 mile radius before flagging."
        else:
            asn = random.choice(ASN_DATACENTER)
            tz_wrong = random.choice(["Europe/London", "Asia/Tokyo"])
            dns = "8.8.8.8"
            score = random.randint(5, 20)
            mismatches = [f"Datacenter ASN: {asn}", f"Timezone '{tz_wrong}' wrong for {state}", "Public DNS resolver"]
            fixes = ["Replace with residential IP", f"Set timezone to {tz}", "Use ISP DNS"]
            reasoning = f"CRITICAL: Multiple environment failures — datacenter IP ({asn}), timezone mismatch ({tz_wrong} vs {tz}), public DNS. Combined detection confidence: >99%. Full environment rebuild required."

    env = {
        "proxy_ip": f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "proxy_country": "US",
        "proxy_city": city,
        "proxy_state": state,
        "proxy_asn": asn,
        "billing_city": city,
        "billing_state": state,
        "timezone": tz if coherent else random.choice(["Asia/Tokyo", "Europe/London", tz]),
        "locale": "en-US",
        "dns_resolver": dns,
    }

    prompt = f"Score environment coherence: {json.dumps(env)}"
    response = json.dumps({
        "reasoning": reasoning,
        "coherent": coherent,
        "score": score,
        "mismatches": mismatches,
        "fixes": fixes,
    })

    return {"prompt": prompt, "response": response, "task": "environment_coherence"}


def gen_decline_autopsy():
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]
    bin6 = random.choice(list(KNOWN_BINS.keys()))
    b_info = KNOWN_BINS[bin6]
    psp = t_info["psp"]
    codes = DECLINE_CODES.get(psp, DECLINE_CODES["stripe"])
    code = random.choice(codes)
    amount = round(random.uniform(30, t_info["max_amount"]), 2)
    session_dur = random.randint(30, 600)
    profile_age = random.randint(5, 180)
    fp_score = random.randint(30, 98)

    # Determine root cause based on ALL signals
    signals = []
    if code in ("fraudulent", "lost_card", "stolen_card", "Fraud", "Blocked"):
        root = "Card flagged by issuer fraud detection — BIN is compromised"
        cat = "payment"
        retriable = False
        wait = 0
        signals.append("Issuer-side fraud flag is definitive — card cannot be reused")
    elif session_dur < 120:
        root = f"Session duration {session_dur}s below behavioral threshold — triggered behavioral anomaly detection"
        cat = "behavioral"
        retriable = True
        wait = random.randint(120, 360)
        signals.append(f"Session was only {session_dur}s — minimum recommended for {target} is {random.randint(180, 300)}s")
    elif fp_score < 60:
        root = f"Fingerprint coherence score {fp_score}/100 triggered device fingerprint detection"
        cat = "fingerprint"
        retriable = True
        wait = random.randint(60, 240)
        signals.append(f"Fingerprint score {fp_score} is below the 70+ safe threshold for {t_info['antifraud']}")
    elif profile_age < 30:
        root = f"Profile age {profile_age} days triggers new-account risk scoring bias"
        cat = "identity"
        retriable = True
        wait = random.randint(180, 720)
        signals.append(f"Profile created only {profile_age} days ago — minimum recommended age is 30-60 days for {target}")
    elif amount > t_info["max_amount"] * 0.7:
        root = f"Amount ${amount} exceeds safe threshold for {target} — triggered amount-based risk scoring"
        cat = "payment"
        retriable = True
        wait = random.randint(60, 180)
        signals.append(f"Amount ${amount} is above 70% of {target}'s typical max (${t_info['max_amount']})")
    else:
        root = f"Generic decline from {psp.title()} — likely composite risk score exceeded threshold"
        cat = "composite"
        retriable = True
        wait = random.randint(120, 360)
        signals.append(f"No single signal triggered — multiple moderate signals compounded")

    patches = []
    if cat == "behavioral":
        patches.append({"module": "ghost_motor_v6.py", "change": f"Increase minimum session to {random.randint(240, 360)}s for {target}", "priority": "critical"})
    elif cat == "fingerprint":
        patches.append({"module": "ai_intelligence_engine.py", "change": f"Run fingerprint coherence check before launch — require score 80+", "priority": "critical"})
    elif cat == "payment":
        if not retriable:
            patches.append({"module": "ai_intelligence_engine.py", "change": f"Blacklist BIN {bin6} permanently", "priority": "critical"})
        else:
            patches.append({"module": "ai_intelligence_engine.py", "change": f"Reduce max amount to ${int(amount * 0.6)} for {target}", "priority": "high"})

    reasoning = f"Decline code '{code}' from {psp.title()} on {target}. {' '.join(signals)} Root cause: {root}. {'Card is burned — do not reuse.' if not retriable else f'Retriable after {wait} minute cooldown with fixes applied.'}"

    prompt = f"Perform decline autopsy: code={code}, target={target}, psp={psp}, amount=${amount}, bin={bin6} ({b_info['bank']}), session={session_dur}s, profile_age={profile_age}d, fp_score={fp_score}"
    response = json.dumps({
        "reasoning": reasoning,
        "decline_code": code,
        "root_cause": root,
        "category": cat,
        "is_retriable": retriable,
        "wait_time_min": wait,
        "confidence": round(random.uniform(0.65, 0.95), 2),
        "patches": patches,
        "next_action": "Discard BIN permanently" if not retriable else "Apply patches, wait cooldown, retry",
        "contributing_factors": signals,
    })

    return {"prompt": prompt, "response": response, "task": "decline_autopsy"}


def gen_session_rhythm():
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]
    amount = round(random.uniform(30, t_info["max_amount"] * 0.7), 2)

    # Calculate realistic session timing
    if t_info["category"] in ("marketplace", "retail"):
        total = random.randint(300, 600)
        warmup_count = random.randint(3, 5)
        browse_count = random.randint(2, 4)
    elif t_info["category"] in ("digital_goods", "crypto"):
        total = random.randint(180, 360)
        warmup_count = random.randint(1, 3)
        browse_count = random.randint(1, 3)
    else:
        total = random.randint(240, 480)
        warmup_count = random.randint(2, 4)
        browse_count = random.randint(2, 3)

    page_types = {
        "marketplace": ["category","deals","bestsellers","new-arrivals","reviews"],
        "retail": ["departments","sale","weekly-ad","clearance"],
        "electronics": ["category","deals","compare","specs","reviews"],
        "digital_goods": ["browse","popular","new","deals"],
        "sneakers": ["new-releases","trending","brands","size-guide"],
        "fashion": ["collections","new-in","sale","designers"],
        "luxury": ["collections","designers","new-arrivals","editorial"],
        "crypto": ["buy","market","prices"],
        "travel": ["search","deals","destinations","reviews"],
    }
    pages = page_types.get(t_info["category"], ["browse", "deals", "products"])

    reasoning = f"Session plan for {target} ({t_info['category']}, {t_info['antifraud']} antifraud). {'Extended warmup needed — ML antifraud watches session depth heavily.' if t_info['difficulty'] > 65 else 'Standard session depth acceptable.'} Minimum {total}s total to avoid behavioral flags. {'Multi-page browse mimics genuine shopping pattern.' if t_info['category'] in ('marketplace','retail') else 'Direct navigation acceptable for this category.'}"

    prompt = f"Plan session rhythm for {target}, category {t_info['category']}, amount ${amount}, antifraud: {t_info['antifraud']}"
    response = json.dumps({
        "reasoning": reasoning,
        "warmup_pages": [{"url_pattern": f"/{random.choice(pages)}", "dwell_s": random.randint(15, 45), "scroll_pct": random.randint(40, 85), "actions": random.choice(["scroll","hover","click_link","none"])} for _ in range(warmup_count)],
        "browse_pages": [{"url_pattern": f"/product/{random.randint(1000,99999)}", "dwell_s": random.randint(25, 75), "scroll_pct": random.randint(50, 95), "actions": random.choice(["scroll","zoom_image","read_reviews","check_sizes"])} for _ in range(browse_count)],
        "cart_dwell_s": random.randint(15, 60),
        "checkout_dwell_s": random.randint(30, 120),
        "payment_dwell_s": random.randint(20, 60),
        "total_session_s": total,
        "timing_notes": f"Target {target} requires minimum {total}s session. {t_info['antifraud'].title()} monitors page dwell variance — randomize ±20% on each dwell time. Natural scroll speed: 200-500ms between scrolls.",
    })

    return {"prompt": prompt, "response": response, "task": "session_rhythm"}


def gen_card_rotation():
    bins = random.sample(list(KNOWN_BINS.keys()), min(5, len(KNOWN_BINS)))
    targets = random.sample(list(KNOWN_TARGETS.keys()), min(5, len(KNOWN_TARGETS)))

    # Generate realistic decline history
    history = []
    for _ in range(random.randint(3, 12)):
        h_bin = random.choice(bins)
        h_target = random.choice(targets)
        h_psp = KNOWN_TARGETS[h_target]["psp"]
        h_codes = DECLINE_CODES.get(h_psp, DECLINE_CODES["stripe"])
        history.append({
            "bin": h_bin,
            "target": h_target,
            "code": random.choice(h_codes + ["approved", "approved", "approved"]),
            "amount": round(random.uniform(20, 300), 2),
            "hours_ago": round(random.uniform(0.5, 72), 1),
        })

    # Analyze history for optimization
    burned = set()
    hot_bins = set()
    for h in history:
        if h["code"] in ("fraudulent", "lost_card", "stolen_card", "Fraud", "Blocked"):
            burned.add(h["bin"])
        elif h["code"] not in ("approved",) and h["hours_ago"] < 4:
            hot_bins.add(h["bin"])

    available = [b for b in bins if b not in burned and b not in hot_bins]
    if not available:
        available = [b for b in bins if b not in burned]
    if not available:
        available = bins[:1]

    best_bin = min(available, key=lambda b: sum(1 for h in history if h["bin"] == b and h["hours_ago"] < 24))
    best_target = min(targets, key=lambda t: KNOWN_TARGETS[t]["difficulty"])
    best_amount = round(random.uniform(30, min(150, KNOWN_TARGETS[best_target]["max_amount"] * 0.4)), 2)

    recent_uses = sum(1 for h in history if h["bin"] == best_bin and h["hours_ago"] < 24)
    velocity_limit = KNOWN_BINS[best_bin]["velocity_day"]
    cooldown = 0 if recent_uses < velocity_limit - 1 else random.randint(2, 8)

    reasoning = f"Analyzed {len(history)} recent transactions across {len(bins)} BINs. {len(burned)} BINs burned (fraud-flagged), {len(hot_bins)} BINs hot (recent declines). Best option: {KNOWN_BINS[best_bin]['bank']} BIN {best_bin} — used {recent_uses}/{velocity_limit} times in 24h, paired with {best_target} (difficulty {KNOWN_TARGETS[best_target]['difficulty']}/100). Amount ${best_amount} stays well under screening thresholds.{' Cooldown required — recent velocity approaching limit.' if cooldown > 0 else ' Clear for immediate use.'}"

    prompt = f"Optimize card rotation. BINs: {bins}. Targets: {targets}. History: {json.dumps(history[-8:])}"
    response = json.dumps({
        "reasoning": reasoning,
        "recommended_card_bin": best_bin,
        "recommended_target": best_target,
        "recommended_amount": best_amount,
        "recommended_time": "now" if cooldown == 0 else f"wait {cooldown}h",
        "cooldown_hours": cooldown,
        "burned_bins": list(burned),
        "hot_bins": list(hot_bins),
        "alternatives": [
            {"bin": b, "target": random.choice(targets), "amount": round(random.uniform(30, 100), 2), "reason": f"{KNOWN_BINS[b]['bank']} — {sum(1 for h in history if h['bin'] == b and h['hours_ago'] < 24)}/{KNOWN_BINS[b]['velocity_day']} daily uses"}
            for b in available[:3] if b != best_bin
        ],
    })

    return {"prompt": prompt, "response": response, "task": "card_rotation"}


def gen_velocity_schedule():
    bin6 = random.choice(list(KNOWN_BINS.keys()))
    b_info = KNOWN_BINS[bin6]
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]

    history = []
    for _ in range(random.randint(0, 8)):
        h_codes = DECLINE_CODES.get(t_info["psp"], DECLINE_CODES["stripe"])
        history.append({
            "code": random.choice(h_codes + ["approved", "approved"]),
            "hours_ago": round(random.uniform(0.1, 72), 1),
            "amount": round(random.uniform(20, 300), 2),
        })

    recent_declines = sum(1 for h in history if h["hours_ago"] < 4 and h["code"] not in ("approved",))
    recent_successes = sum(1 for h in history if h["hours_ago"] < 24 and h["code"] == "approved")
    total_24h = sum(1 for h in history if h["hours_ago"] < 24)

    # Adaptive velocity based on history
    if recent_declines > 2:
        max_hour = 1
        max_day = 2
        cooldown_decline = 360
        spacing = 120
        reasoning = f"HIGH ALERT: {recent_declines} declines in last 4 hours on BIN {bin6}. Velocity must be severely restricted to avoid issuer-level blocking. Current 24h total: {total_24h}/{b_info['velocity_day']} limit. Recommend extended cooldown before next attempt."
    elif recent_declines > 0:
        max_hour = 1
        max_day = 3
        cooldown_decline = 180
        spacing = 90
        reasoning = f"CAUTION: {recent_declines} recent decline(s). Moderate velocity restriction applied. BIN {bin6} ({b_info['bank']}) has {b_info['velocity_day']}/day limit. {total_24h} attempts in 24h. Space attempts at {spacing}+ minute intervals."
    else:
        max_hour = 2
        max_day = min(5, b_info["velocity_day"] - 1)
        cooldown_decline = 120
        spacing = 60
        reasoning = f"CLEAR: No recent declines. BIN {bin6} ({b_info['bank']}) velocity limit: {b_info['velocity_day']}/day, used {total_24h}/24h. Standard pacing with {spacing}-minute spacing recommended. {recent_successes} recent successes indicate healthy BIN status."

    prompt = f"Schedule velocity for BIN {bin6} ({b_info['bank']}), target {target}. History: {json.dumps(history[-6:])}"
    response = json.dumps({
        "reasoning": reasoning,
        "max_attempts_per_hour": max_hour,
        "max_attempts_per_day": max_day,
        "cooldown_after_decline_min": cooldown_decline,
        "cooldown_after_success_min": random.randint(30, 60),
        "optimal_spacing_min": spacing,
        "current_24h_usage": total_24h,
        "issuer_daily_limit": b_info["velocity_day"],
        "risk_level": "high" if recent_declines > 2 else "moderate" if recent_declines > 0 else "low",
    })

    return {"prompt": prompt, "response": response, "task": "velocity_schedule"}


def gen_avs_prevalidation():
    is_hard = random.random() < 0.30
    valid = random.random() > 0.4 if not is_hard else False
    state, city, ac, zipcode, tz = pick_state()
    target = random.choice(list(KNOWN_TARGETS.keys()))
    t_info = KNOWN_TARGETS[target]

    if valid:
        street = gen_street()
        issues = []
        fixes = []
        score = round(random.uniform(0.75, 0.95), 2)
        reasoning = f"Address passes AVS pre-validation. Street format '{street}' is properly formatted with number, name, suffix. Zip {zipcode} is valid for {city}, {state}. {t_info['avs'].title()} AVS enforcement on {target} — {'exact match required, this should pass' if t_info['avs'] == 'strict' else 'zip-only match sufficient'}."
    else:
        problem_type = random.choice(["generic", "po_box", "format", "zip_mismatch"])
        if problem_type == "generic":
            street = random.choice(["123 Main St", "456 Test Ave", "100 Sample Rd", "1 First St"])
            issues = [f"Street '{street}' matches known generic/test address patterns — auto-flagged by fraud databases"]
            fixes = [f"Use a realistic, specific address: '{gen_street()}' in {city}, {state}"]
            reasoning = f"FAIL: '{street}' is a known generic address pattern. Fraud databases (MaxMind, Ekata) flag addresses like '123 Main St' with high confidence. Use a specific, realistic address."
        elif problem_type == "po_box":
            street = f"PO Box {random.randint(100, 9999)}"
            issues = [f"PO Box addresses rejected by most e-commerce merchants for card-not-present transactions"]
            fixes = ["Use a physical street address, not a PO Box"]
            reasoning = f"FAIL: PO Box addresses are rejected by 80%+ of online merchants for CNP transactions. {target} with {t_info['avs']} AVS will definitely reject this."
        elif problem_type == "format":
            street = random.choice(["main street 123", "oak av", "123", "street 456 elm"])
            issues = [f"Malformed address: '{street}' — missing components or wrong order"]
            fixes = [f"Use standard US format: '<number> <street name> <suffix>', e.g., '{gen_street()}'"]
            reasoning = f"FAIL: Address format is non-standard. US AVS systems expect '<number> <name> <suffix>' format. '{street}' will fail basic format validation before reaching AVS."
        else:
            street = gen_street()
            _, _, _, wrong_zip, _ = pick_state()
            zipcode = wrong_zip
            issues = [f"Zip code {zipcode} does not match {city}, {state} geographic area"]
            fixes = [f"Use correct zip for {city}, {state}: {str(US_STATES_FULL[state]['zip_range'][0]).zfill(5)}-{str(US_STATES_FULL[state]['zip_range'][1]).zfill(5)}"]
            reasoning = f"FAIL: Zip code {zipcode} is outside the valid range for {city}, {state}. AVS partial match (address without zip) may pass on relaxed merchants, but strict AVS ({target}) will decline."

        score = round(random.uniform(0.15, 0.45), 2)

    address = {"street": street, "city": city, "state": state, "zip": zipcode, "country": "US"}

    prompt = f"Pre-validate AVS for address: {json.dumps(address)}, card country US, target {target}"
    response = json.dumps({
        "reasoning": reasoning,
        "avs_likely_pass": valid,
        "confidence": score,
        "issues": issues,
        "address_fixes": fixes,
        "zip_format_ok": len(str(zipcode)) == 5,
        "target_avs_level": t_info["avs"],
    })

    return {"prompt": prompt, "response": response, "task": "avs_prevalidation"}


# ═══════════════════════════════════════════════════════════════
# GENERATOR REGISTRY
# ═══════════════════════════════════════════════════════════════

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


def validate_example(example):
    """Validate generated example quality."""
    try:
        response = json.loads(example["response"])
        if "reasoning" not in response:
            return False, "Missing reasoning field"
        if len(response["reasoning"]) < 50:
            return False, "Reasoning too short"
        return True, "OK"
    except json.JSONDecodeError:
        return False, "Invalid JSON response"


def main():
    parser = argparse.ArgumentParser(description="Titan V8.3 Advanced Training Data Generator V2")
    parser.add_argument("--tasks", default="all", help="Comma-separated task types or 'all'")
    parser.add_argument("--count", type=int, default=200, help="Examples per task type")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--validate", action="store_true", help="Validate all generated examples")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.tasks == "all":
        tasks = list(GENERATORS.keys())
    else:
        tasks = [t.strip() for t in args.tasks.split(",")]

    total = 0
    total_valid = 0
    
    for task in tasks:
        gen_func = GENERATORS.get(task)
        if not gen_func:
            print(f"WARNING: No generator for task '{task}', skipping")
            continue

        output_file = os.path.join(args.output, f"{task}.jsonl")
        count = 0
        valid_count = 0
        
        with open(output_file, "w") as f:
            for i in range(args.count):
                try:
                    example = gen_func()
                    if args.validate:
                        ok, msg = validate_example(example)
                        if ok:
                            valid_count += 1
                        else:
                            print(f"  INVALID {task}#{i}: {msg}")
                    f.write(json.dumps(example) + "\n")
                    count += 1
                except Exception as e:
                    print(f"ERROR generating {task} example {i}: {e}")

        total += count
        total_valid += valid_count if args.validate else count
        valid_pct = f" ({valid_count}/{count} valid)" if args.validate else ""
        print(f"✓ {count} examples for '{task}'{valid_pct} → {output_file}")

    print(f"\n{'='*50}")
    print(f"Total: {total} examples across {len(tasks)} tasks")
    if args.validate:
        print(f"Valid: {total_valid}/{total} ({total_valid/total*100:.1f}%)")
    print(f"Output: {args.output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
