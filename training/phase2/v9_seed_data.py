#!/usr/bin/env python3
"""TITAN V9.0 — Shared Seed Data & Helpers for Training Data Generation"""

import random
import json
import hashlib

KNOWN_BINS = {
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
    "431940": {"bank": "Green Dot", "country": "US", "network": "visa", "type": "prepaid", "level": "classic", "vbv": False, "velocity_day": 3},
    "426219": {"bank": "NetSpend", "country": "US", "network": "visa", "type": "prepaid", "level": "classic", "vbv": False, "velocity_day": 2},
    "540735": {"bank": "Barclays", "country": "GB", "network": "mastercard", "type": "credit", "level": "world", "vbv": True, "velocity_day": 4},
    "437772": {"bank": "HSBC", "country": "GB", "network": "visa", "type": "credit", "level": "platinum", "vbv": True, "velocity_day": 5},
    "475129": {"bank": "Lloyds", "country": "GB", "network": "visa", "type": "debit", "level": "classic", "vbv": True, "velocity_day": 8},
    "489396": {"bank": "Garanti BBVA", "country": "TR", "network": "visa", "type": "credit", "level": "classic", "vbv": False, "velocity_day": 8},
    "557039": {"bank": "Isbank", "country": "TR", "network": "mastercard", "type": "credit", "level": "gold", "vbv": False, "velocity_day": 7},
    "476173": {"bank": "NBE", "country": "EG", "network": "visa", "type": "credit", "level": "classic", "vbv": False, "velocity_day": 10},
    "428671": {"bank": "Banco do Brasil", "country": "BR", "network": "visa", "type": "credit", "level": "gold", "vbv": False, "velocity_day": 6},
    "462152": {"bank": "Emirates NBD", "country": "AE", "network": "visa", "type": "credit", "level": "platinum", "vbv": False, "velocity_day": 4},
    "543210": {"bank": "RBC", "country": "CA", "network": "mastercard", "type": "credit", "level": "world", "vbv": True, "velocity_day": 5},
}

KNOWN_TARGETS = {
    "eneba.com": {"psp": "stripe", "antifraud": "forter", "3ds_rate": 0.55, "difficulty": 65, "category": "digital_goods", "avs": "moderate", "max_amount": 200},
    "g2a.com": {"psp": "adyen", "antifraud": "seon", "3ds_rate": 0.45, "difficulty": 55, "category": "digital_goods", "avs": "relaxed", "max_amount": 150},
    "cdkeys.com": {"psp": "checkout", "antifraud": "internal", "3ds_rate": 0.35, "difficulty": 45, "category": "digital_goods", "avs": "relaxed", "max_amount": 100},
    "kinguin.net": {"psp": "adyen", "antifraud": "seon", "3ds_rate": 0.40, "difficulty": 50, "category": "digital_goods", "avs": "relaxed", "max_amount": 150},
    "bestbuy.com": {"psp": "cybersource", "antifraud": "forter", "3ds_rate": 0.60, "difficulty": 75, "category": "electronics", "avs": "strict", "max_amount": 1500},
    "newegg.com": {"psp": "stripe", "antifraud": "kount", "3ds_rate": 0.40, "difficulty": 60, "category": "electronics", "avs": "strict", "max_amount": 2000},
    "amazon.com": {"psp": "internal", "antifraud": "internal", "3ds_rate": 0.30, "difficulty": 85, "category": "marketplace", "avs": "strict", "max_amount": 5000},
    "walmart.com": {"psp": "cybersource", "antifraud": "internal", "3ds_rate": 0.40, "difficulty": 70, "category": "retail", "avs": "strict", "max_amount": 2000},
    "ebay.com": {"psp": "adyen", "antifraud": "internal", "3ds_rate": 0.50, "difficulty": 70, "category": "marketplace", "avs": "moderate", "max_amount": 1000},
    "stockx.com": {"psp": "stripe", "antifraud": "riskified", "3ds_rate": 0.75, "difficulty": 80, "category": "sneakers", "avs": "strict", "max_amount": 500},
    "nike.com": {"psp": "adyen", "antifraud": "forter", "3ds_rate": 0.65, "difficulty": 70, "category": "fashion", "avs": "strict", "max_amount": 300},
    "farfetch.com": {"psp": "checkout", "antifraud": "riskified", "3ds_rate": 0.80, "difficulty": 75, "category": "luxury", "avs": "strict", "max_amount": 2000},
    "paxful.com": {"psp": "stripe", "antifraud": "seon", "3ds_rate": 0.55, "difficulty": 60, "category": "crypto", "avs": "moderate", "max_amount": 500},
    "bitrefill.com": {"psp": "stripe", "antifraud": "internal", "3ds_rate": 0.40, "difficulty": 50, "category": "digital_goods", "avs": "relaxed", "max_amount": 200},
    "zalando.de": {"psp": "adyen", "antifraud": "riskified", "3ds_rate": 0.85, "difficulty": 70, "category": "fashion", "avs": "relaxed", "max_amount": 500},
    "booking.com": {"psp": "adyen", "antifraud": "internal", "3ds_rate": 0.70, "difficulty": 65, "category": "travel", "avs": "moderate", "max_amount": 3000},
}

US_STATES = {
    "NY": {"cities": ["New York","Brooklyn","Buffalo"], "acs": ["212","718","347"], "tz": "America/New_York", "zr": (10000,14999)},
    "CA": {"cities": ["Los Angeles","San Francisco","San Diego"], "acs": ["310","213","415"], "tz": "America/Los_Angeles", "zr": (90000,96199)},
    "TX": {"cities": ["Houston","Dallas","Austin"], "acs": ["713","214","512"], "tz": "America/Chicago", "zr": (73301,79999)},
    "FL": {"cities": ["Miami","Orlando","Tampa"], "acs": ["305","407","813"], "tz": "America/New_York", "zr": (32000,34999)},
    "IL": {"cities": ["Chicago","Springfield","Naperville"], "acs": ["312","773","217"], "tz": "America/Chicago", "zr": (60000,62999)},
    "PA": {"cities": ["Philadelphia","Pittsburgh","Allentown"], "acs": ["215","412","610"], "tz": "America/New_York", "zr": (15000,19699)},
    "OH": {"cities": ["Columbus","Cleveland","Cincinnati"], "acs": ["614","216","513"], "tz": "America/New_York", "zr": (43000,45999)},
    "GA": {"cities": ["Atlanta","Savannah","Augusta"], "acs": ["404","912","706"], "tz": "America/New_York", "zr": (30000,31999)},
    "WA": {"cities": ["Seattle","Tacoma","Spokane"], "acs": ["206","253","509"], "tz": "America/Los_Angeles", "zr": (98000,99499)},
    "CO": {"cities": ["Denver","Colorado Springs","Boulder"], "acs": ["303","719","720"], "tz": "America/Denver", "zr": (80000,81699)},
}

FIRST_NAMES = ["James","Robert","John","Michael","David","William","Richard","Joseph","Thomas","Christopher","Mary","Patricia","Jennifer","Linda","Elizabeth","Susan","Jessica","Sarah","Karen","Ashley","Emily","Megan","Hannah","Samantha","Daniel","Matthew","Anthony","Mark","Andrew","Paul"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Wilson","Anderson","Taylor","Thomas","Moore","Jackson","White","Harris","Clark","Lewis"]
WEBGL_WIN = ["ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)","ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)","ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)","ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)"]
WEBGL_LIN = ["Mesa DRI Intel(R) UHD Graphics 630","Mesa DRI AMD Radeon RX 580"]
WEBGL_MAC = ["Apple M1","Apple M2","Apple M3"]
DECLINE_CODES = {"stripe":["card_declined","insufficient_funds","lost_card","stolen_card","fraudulent","incorrect_cvc","expired_card","do_not_honor"],"adyen":["Refused","Blocked","CVC Declined","Fraud","Not Enough Balance"],"cybersource":["REJECT","CALL","ERROR","233"],"checkout":["20005","20051","20054","20087"],"braintree":["2000","2001","2010","2046"]}
ASN_RES = ["AS7922 Comcast","AS7018 AT&T","AS20115 Charter","AS701 Verizon","AS22773 Cox"]
ASN_DC = ["AS13335 Cloudflare","AS16509 Amazon AWS","AS15169 Google","AS8075 Microsoft","AS24940 Hetzner"]

ANTIFRAUD_INFO = {
    "forter": {"type":"ml","biometric":True,"bypass":"high"},
    "riskified": {"type":"ml","biometric":True,"bypass":"high"},
    "sift": {"type":"ml","biometric":False,"bypass":"high"},
    "kount": {"type":"ml","biometric":False,"bypass":"medium"},
    "seon": {"type":"rule","biometric":False,"bypass":"medium"},
    "internal": {"type":"rule","biometric":False,"bypass":"low"},
}

ISSUER_PROFILES = {
    "Chase": {"strict":"high","vel":"high","geo":"high","dev_bind":True,"behav":True,"max_d":4,"escal":"fast"},
    "Bank of America": {"strict":"moderate","vel":"moderate","geo":"moderate","dev_bind":False,"behav":False,"max_d":5,"escal":"moderate"},
    "Capital One": {"strict":"high","vel":"moderate","geo":"moderate","dev_bind":True,"behav":True,"max_d":6,"escal":"moderate"},
    "Citi": {"strict":"moderate","vel":"moderate","geo":"low","dev_bind":False,"behav":False,"max_d":5,"escal":"slow"},
    "Wells Fargo": {"strict":"moderate","vel":"moderate","geo":"moderate","dev_bind":False,"behav":False,"max_d":4,"escal":"moderate"},
    "American Express": {"strict":"very_high","vel":"high","geo":"high","dev_bind":True,"behav":True,"max_d":3,"escal":"fast"},
    "Barclays": {"strict":"high","vel":"moderate","geo":"moderate","dev_bind":False,"behav":False,"max_d":4,"escal":"moderate"},
    "HSBC": {"strict":"moderate","vel":"low","geo":"low","dev_bind":False,"behav":False,"max_d":5,"escal":"slow"},
}

OCCUPATIONS = {"young":["Student","Intern","Junior Developer","Barista","Retail Associate"],"mid":["Software Engineer","Accountant","Marketing Manager","Nurse","Teacher"],"senior":["Senior Engineer","Director","VP Sales","Principal Architect"]}

def pick_state():
    st = random.choice(list(US_STATES.keys())); i = US_STATES[st]
    return st, random.choice(i["cities"]), random.choice(i["acs"]), str(random.randint(*i["zr"])).zfill(5), i["tz"]

def gn(): return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def ge(name):
    s = [name.lower().replace(" ","."), name.split()[0].lower()+str(random.randint(1,99)), name.split()[0][0].lower()+name.split()[1].lower()]
    return f"{random.choice(s)}@{random.choice(['gmail.com','yahoo.com','outlook.com','icloud.com'])}"

def gp(ac): return f"+1-{ac}-{random.randint(200,999)}-{random.randint(1000,9999)}"

def gs():
    n = random.randint(100,9999); s = random.choice(["Oak","Maple","Cedar","Pine","Elm","Main","Park","Washington"])
    x = random.choice(["St","Ave","Blvd","Dr","Ln","Rd"]); a = f" Apt {random.choice(['A','B','2A','101','303'])}" if random.random()>0.7 else ""
    return f"{n} {s} {x}{a}"

def pred(b, t, amt):
    base = 0.45
    if b["type"]=="prepaid": base -= 0.15
    if not b["vbv"]: base += 0.10
    if b["level"] in ("signature","platinum","world"): base += 0.05
    base -= (t["difficulty"]-50)*0.003
    if t["category"]=="digital_goods": base += 0.10
    if t["avs"]=="relaxed": base += 0.05
    if amt > t["max_amount"]*0.7: base -= 0.10
    return round(max(0.05, min(0.95, base + random.gauss(0,0.05))), 2)

def rlevel(p): return "low" if p>0.65 else "moderate" if p>0.40 else "high" if p>0.20 else "critical"
def pb(): b=random.choice(list(KNOWN_BINS.keys())); return b, KNOWN_BINS[b]
def pt(): t=random.choice(list(KNOWN_TARGETS.keys())); return t, KNOWN_TARGETS[t]
def ih(): return random.random() < 0.30

def mk(prompt, response, task):
    if isinstance(response, dict): response = json.dumps(response)
    return {"prompt": prompt, "response": response, "task": task}
