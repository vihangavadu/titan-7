#!/usr/bin/env python3
"""V9 Generators — Card/BIN Tasks (5) + Target Tasks (4) + Fingerprint/Environment (5)"""

import random, json
from v9_seed_data import *

# ═══════════════════════════════════════════════════════════════
# CARD / BIN TASKS
# ═══════════════════════════════════════════════════════════════

def gen_bin_analysis():
    b6, bi = pb(); td, ti = pt()
    amt = round(random.uniform(20, min(500, ti["max_amount"]*1.2)), 2)
    p = pred(bi, ti, amt); r = rlevel(p)
    tds = bi["vbv"] and (ti["3ds_rate"] > 0.5 or amt > 100)
    reasoning = f"{bi['bank']} {bi['network'].upper()} {bi['level'].title()} from {bi['country']}. "
    if bi["type"] == "prepaid": reasoning += "Prepaid — many merchants decline prepaid by default. "
    if not bi["vbv"]: reasoning += "Non-VBV — no 3DS challenge expected. "
    else: reasoning += f"VBV-enrolled — 3DS likely above ${random.randint(50,200)} on {td}. "
    reasoning += f"Target {td} uses {ti['psp'].title()} with {ti['antifraud'].title()} (difficulty {ti['difficulty']}/100). "
    if amt > ti["max_amount"]*0.7: reasoning += f"Amount ${amt} near upper limit — elevated scoring. "
    reasoning += f"Velocity: {bi['velocity_day']}/day for this issuer."
    return mk(f"Analyze BIN {b6} for target {td}, amount ${amt}.", {
        "reasoning": reasoning, "bin_number": b6, "bank_name": bi["bank"], "country": bi["country"],
        "network": bi["network"], "card_type": bi["type"], "card_level": bi["level"], "risk_level": r,
        "success_prediction": p, "three_ds_likely": tds,
        "optimal_amount_range": [round(max(20,amt*0.4),2), round(min(ti["max_amount"]*0.6,amt*1.5),2)],
        "best_targets": sorted(random.sample(list(KNOWN_TARGETS.keys()),3), key=lambda x: KNOWN_TARGETS[x]["difficulty"]),
        "timing_advice": random.choice(["Weekday 6-8pm EST","Saturday 2-5pm EST","Tuesday-Thursday 10am-12pm EST"]),
        "risk_factors": [f"Velocity limit: {bi['velocity_day']}/day", f"{'3DS likely' if tds else 'Non-VBV'}", f"{ti['antifraud'].title()} active"],
    }, "bin_analysis")

def gen_bin_generation():
    b6, bi = pb()
    return mk(f"Generate BIN intelligence for {b6}.", {
        "reasoning": f"BIN {b6} issued by {bi['bank']} ({bi['country']}). {bi['network'].upper()} {bi['type']} {bi['level'].title()}. {'Non-VBV — advantageous.' if not bi['vbv'] else 'VBV-enrolled.'}",
        "bin_number": b6, "bank_name": bi["bank"], "country": bi["country"], "network": bi["network"],
        "card_type": bi["type"], "card_level": bi["level"], "vbv_enrolled": bi["vbv"],
        "velocity_limit_day": bi["velocity_day"],
        "recommended_targets": random.sample(list(KNOWN_TARGETS.keys()), 3),
    }, "bin_generation")

def gen_card_target_matching():
    b6, bi = pb(); td, ti = pt()
    amt = round(random.uniform(20, ti["max_amount"]*0.8), 2)
    p = pred(bi, ti, amt)
    compat = "excellent" if p > 0.65 else "good" if p > 0.5 else "fair" if p > 0.35 else "poor"
    reasons = []
    if bi["country"] == "US" and ti["avs"] == "strict": reasons.append("US BIN + strict AVS = good AVS match")
    if bi["country"] not in ("US","GB","CA") and ti["avs"] == "strict": reasons.append(f"International BIN ({bi['country']}) on strict AVS = risk")
    if not bi["vbv"] and ti["3ds_rate"] > 0.5: reasons.append("Non-VBV advantage on high-3DS target")
    if bi["type"] == "prepaid" and ti["difficulty"] > 60: reasons.append("Prepaid on high-difficulty = poor match")
    if bi["level"] in ("signature","platinum","world"): reasons.append("Premium card level reduces issuer friction")
    return mk(f"Score card-target compatibility: BIN {b6} ({bi['bank']}) on {td}, amount ${amt}.", {
        "reasoning": f"Card {bi['bank']} {bi['network'].upper()} {bi['level']} vs {td} ({ti['category']}, difficulty {ti['difficulty']}). {' '.join(reasons)}",
        "compatibility": compat, "success_prediction": p, "score": round(p*100),
        "optimal_amount_range": [round(max(20,ti["max_amount"]*0.1),2), round(ti["max_amount"]*0.5,2)],
        "factors": reasons, "recommendation": "Proceed" if p > 0.5 else "Consider alternative"
    }, "card_target_matching")

def gen_validation_strategy():
    b6, bi = pb(); td, ti = pt()
    methods = [
        {"method":"stripe_setup_intent","burn_risk":0.05,"desc":"SetupIntent with no charge — safest"},
        {"method":"zero_auth","burn_risk":0.08,"desc":"$0 auth hold — most PSPs support"},
        {"method":"micro_auth","burn_risk":0.15,"desc":"$1 auth + void — leaves statement trace"},
        {"method":"token_validate","burn_risk":0.03,"desc":"Tokenize only — no auth attempt"},
    ]
    best = random.choice(methods[:2]) if bi["type"] != "prepaid" else methods[2]
    return mk(f"Choose validation strategy for BIN {b6} ({bi['bank']}) targeting {td}.", {
        "reasoning": f"Step 1: {bi['bank']} {bi['type']} card — {'prepaid needs actual auth to confirm balance' if bi['type']=='prepaid' else 'credit/debit can use zero-auth safely'}. Step 2: Target {td} uses {ti['psp']}. Step 3: Best approach: {best['method']} — {best['desc']}.",
        "recommended_method": best["method"], "burn_risk": best["burn_risk"], "description": best["desc"],
        "alternatives": [m["method"] for m in methods if m != best][:2],
    }, "validation_strategy")

def gen_issuer_behavior_prediction():
    b6, bi = pb(); td, ti = pt()
    issuer = bi["bank"]
    ip = ISSUER_PROFILES.get(issuer, {"strict":"moderate","vel":"moderate","geo":"moderate","dev_bind":False,"behav":False,"max_d":5,"escal":"moderate"})
    amt = round(random.uniform(30, ti["max_amount"]*0.8), 2)
    vel_used = random.randint(0, ip["max_d"])
    dp = 0.15
    if ip["strict"] in ("high","very_high"): dp += 0.15
    if vel_used >= ip["max_d"] - 1: dp += 0.25
    if ip["dev_bind"] and random.random() > 0.5: dp += 0.10
    if amt > 500: dp += 0.10
    dp = round(min(0.95, max(0.05, dp + random.gauss(0,0.05))), 2)
    adj = []
    if dp > 0.5: adj.append(f"Reduce amount to ${int(amt*0.5)}")
    if vel_used >= ip["max_d"]-1: adj.append(f"Wait 24h — {vel_used}/{ip['max_d']} daily limit used")
    if ip["dev_bind"]: adj.append("Use consistent device fingerprint")
    return mk(f"Predict issuer behavior: BIN {b6} ({issuer}), target {td}, amount ${amt}, velocity {vel_used}/{ip['max_d']}.", {
        "reasoning": f"Step 1: {issuer} strictness={ip['strict']}, escalation={ip['escal']}. Step 2: Velocity {vel_used}/{ip['max_d']} — {'approaching limit' if vel_used>=ip['max_d']-1 else 'safe range'}. Step 3: {'Device binding active' if ip['dev_bind'] else 'No device binding'}. Step 4: {'Behavioral biometrics active' if ip['behav'] else 'No behavioral'}. Predicted decline prob: {dp}.",
        "decline_probability": dp, "risk_level": rlevel(1-dp),
        "issuer_strictness": ip["strict"], "velocity_status": f"{vel_used}/{ip['max_d']}",
        "adjustments": adj, "optimal_amount": round(amt*0.6,2) if dp > 0.4 else amt,
    }, "issuer_behavior_prediction")


# ═══════════════════════════════════════════════════════════════
# TARGET TASKS
# ═══════════════════════════════════════════════════════════════

def gen_target_recon():
    td, ti = pt(); af = ANTIFRAUD_INFO.get(ti["antifraud"], ANTIFRAUD_INFO["internal"])
    reasoning = f"{td} is a {ti['category']} merchant using {ti['psp'].title()}. Antifraud: {ti['antifraud'].title()} ({af['type']}-based, {'ML + behavioral biometrics' if af['biometric'] else 'rule-based'}). 3DS rate: {int(ti['3ds_rate']*100)}%. AVS: {ti['avs']}. Difficulty: {ti['difficulty']}/100."
    warmup = [f"Browse {random.randint(2,5)} products", f"Session: {random.randint(3,8)} min minimum"]
    if ti["category"] in ("marketplace","retail"): warmup.insert(0, "Create account 7+ days before purchase")
    return mk(f"Perform target reconnaissance on {td}.", {
        "reasoning": reasoning, "domain": td, "fraud_engine": ti["antifraud"], "psp": ti["psp"],
        "three_ds_probability": ti["3ds_rate"], "difficulty_score": ti["difficulty"], "avs_strictness": ti["avs"],
        "optimal_card_types": ["visa_signature","mastercard_world"] if ti["difficulty"]>60 else ["visa_classic"],
        "warmup_strategy": warmup, "category": ti["category"],
    }, "target_recon")

def gen_site_discovery():
    cats = list(set(t["category"] for t in KNOWN_TARGETS.values()))
    cat = random.choice(cats)
    matches = [(d,i) for d,i in KNOWN_TARGETS.items() if i["category"] == cat]
    sm = sorted(matches, key=lambda x: x[1]["difficulty"])
    return mk(f"Find viable targets in {cat} category.", {
        "reasoning": "Scanning {cat}: {n} known targets. Sorted by difficulty: {top}. Best: {best} at difficulty {bd}/100.".format(cat=cat, n=len(matches), top=", ".join("{}({})".format(d, i["difficulty"]) for d,i in sm[:3]), best=sm[0][0], bd=sm[0][1]["difficulty"]),
        "category": cat, "total_found": len(matches),
        "targets": [{"domain":d,"difficulty":i["difficulty"],"psp":i["psp"]} for d,i in sm[:5]],
        "recommended": sm[0][0],
    }, "site_discovery")

def gen_live_target_scoring():
    td, ti = pt()
    ops = random.randint(5,30); succ = random.randint(0,ops)
    rate = round(succ/max(ops,1),2); trend = random.choice(["improving","stable","declining","volatile"])
    score = min(100, max(5, round(rate*100*(0.8 if trend=="declining" else 1.1 if trend=="improving" else 1.0))))
    return mk(f"Score target {td} vulnerability. Recent: {succ}/{ops} success, trend: {trend}.", {
        "reasoning": f"{td}: {succ}/{ops} recent ({int(rate*100)}%), trend {trend}. {'Defense upgraded — reduce volume.' if trend=='declining' else 'Stable — maintain.' if trend=='stable' else 'Improving — increase carefully.'}",
        "domain": td, "vulnerability_score": score, "success_rate": rate, "trend": trend,
        "recommendation": "Increase" if trend=="improving" and rate>0.5 else "Maintain" if trend=="stable" else "Reduce and investigate",
    }, "live_target_scoring")

def gen_preset_generation():
    td, ti = pt()
    return mk(f"Generate target preset for {td}.", {
        "reasoning": f"Preset for {td}: {ti['psp'].title()} PSP, {ti['antifraud'].title()} antifraud, {ti['avs']} AVS, {int(ti['3ds_rate']*100)}% 3DS.",
        "domain": td, "psp": ti["psp"], "antifraud": ti["antifraud"],
        "three_ds_rate": ti["3ds_rate"], "avs_level": ti["avs"], "category": ti["category"],
        "max_amount": ti["max_amount"], "difficulty": ti["difficulty"],
        "min_profile_age_days": 90 if ti["difficulty"]>65 else 30,
        "min_session_seconds": 300 if ti["difficulty"]>65 else 180,
    }, "preset_generation")


# ═══════════════════════════════════════════════════════════════
# FINGERPRINT / ENVIRONMENT TASKS
# ═══════════════════════════════════════════════════════════════

def gen_fingerprint_coherence():
    hard = ih(); coherent = random.random() > 0.5 if not hard else False
    os_t = random.choice(["windows","linux","macos"])
    if coherent:
        ua = f"Mozilla/5.0 ({'Windows NT 10.0; Win64; x64' if os_t=='windows' else 'Macintosh; Intel Mac OS X 10_15_7' if os_t=='macos' else 'X11; Linux x86_64'}) AppleWebKit/537.36 Chrome/{random.randint(120,133)}.0.0.0"
        renderer = random.choice(WEBGL_WIN if os_t=="windows" else WEBGL_MAC if os_t=="macos" else WEBGL_LIN)
        platform = {"windows":"Win32","macos":"MacIntel","linux":"Linux x86_64"}[os_t]
        hw = random.choice([4,8,12,16]); score = random.randint(78,98)
        reasoning = f"All signals coherent: {os_t.title()} UA matches {platform}, WebGL appropriate, hw={hw} realistic. Score: {score}/100."
        mm=[]; fx=[]
    else:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0"
        mt = random.choice(["os_webgl","hw_count","ua_platform","multi"])
        if mt == "os_webgl":
            renderer = random.choice(WEBGL_LIN+WEBGL_MAC); platform="Win32"; hw=8; score=random.randint(20,40)
            mm=[f"WebGL '{renderer}' incompatible with Windows UA"]; fx=[f"Use '{random.choice(WEBGL_WIN)[:50]}...'"]
            reasoning = f"CRITICAL: WebGL renderer mismatch with Windows UA. Detection >95%."
        elif mt == "hw_count":
            renderer = random.choice(WEBGL_WIN); platform="Win32"; hw=random.choice([64,128]); score=random.randint(30,50)
            mm=[f"hw_concurrency={hw} unrealistic"]; fx=[f"Set to {random.choice([4,8,12])}"]
            reasoning = f"hw_concurrency={hw} indicates VM/spoofed. Real: 2-24."
        elif mt == "ua_platform":
            renderer = random.choice(WEBGL_WIN); platform="Linux x86_64"; hw=8; score=random.randint(25,45)
            mm=["platform='Linux x86_64' contradicts Windows UA"]; fx=["Set platform to 'Win32'"]
            reasoning = "Platform mismatch — trivial detection."
        else:
            renderer = random.choice(WEBGL_LIN); platform="MacIntel"; hw=64; score=random.randint(10,25)
            mm=["Linux WebGL + MacIntel + 64 cores"]; fx=["Full fingerprint rebuild"]
            reasoning = "CRITICAL: Multiple mismatches. Detection >99%."
    fp = {"user_agent":ua,"webgl_renderer":renderer,"hardware_concurrency":hw,"platform":platform}
    return mk(f"Validate fingerprint coherence: {json.dumps(fp)}", {"reasoning":reasoning,"coherent":coherent,"score":score,"mismatches":mm,"fixes":fx}, "fingerprint_coherence")

def gen_environment_coherence():
    hard = ih(); coherent = random.random() > 0.5 if not hard else False
    st, city, ac, zc, tz = pick_state()
    if coherent:
        asn = random.choice(ASN_RES); score = random.randint(75,96)
        reasoning = f"Environment coherent: Residential IP ({asn}), TZ {tz} matches {city},{st}."
        mm=[]; fx=[]
    else:
        mt = random.choice(["datacenter","tz","geo","multi"])
        if mt == "datacenter":
            asn=random.choice(ASN_DC); score=random.randint(15,35)
            mm=[f"ASN '{asn}' is datacenter"]; fx=[f"Use residential IP from {st}"]
            reasoning = f"CRITICAL: Datacenter ASN ({asn}). Guaranteed detection."
        elif mt == "tz":
            asn=random.choice(ASN_RES); score=random.randint(35,55)
            mm=[f"TZ wrong for {city},{st}"]; fx=[f"Set TZ to '{tz}'"]
            reasoning = f"TZ mismatch raises risk 15-25 points."
        elif mt == "geo":
            asn=random.choice(ASN_RES); s2,c2,_,_,_ = pick_state(); score=random.randint(25,45)
            mm=[f"IP in {city},{st} but billing {c2},{s2}"]; fx=[f"Use proxy from {s2}"]
            reasoning = f"Geographic mismatch: IP {city},{st} vs billing {c2},{s2}."
        else:
            asn=random.choice(ASN_DC); score=random.randint(5,20)
            mm=["Datacenter ASN","TZ mismatch","Public DNS"]; fx=["Residential IP","Fix TZ","ISP DNS"]
            reasoning = "CRITICAL: Multiple failures. Detection >99%."
    env = {"proxy_asn":asn,"proxy_city":city,"proxy_state":st,"billing_state":st,"timezone":tz if coherent else "Asia/Tokyo"}
    return mk(f"Score environment coherence: {json.dumps(env)}", {"reasoning":reasoning,"coherent":coherent,"score":score,"mismatches":mm,"fixes":fx}, "environment_coherence")

def gen_hardware_profile_coherence():
    coherent = not ih() and random.random() > 0.4
    os_claim = random.choice(["Windows 11","Windows 10","macOS Ventura"])
    if coherent:
        usb = [{"vendor":"Logitech","product":"USB Receiver"},{"vendor":"Realtek","product":"USB Audio"}]
        score = random.randint(75,95)
        reasoning = f"USB tree consistent with {os_claim}. Consumer peripherals, no VM indicators."
    else:
        usb = [{"vendor":"QEMU","product":"QEMU USB Tablet"},{"vendor":"Red Hat","product":"VirtIO"}]
        score = random.randint(10,35)
        reasoning = f"CRITICAL: VM indicators (QEMU/VirtIO). Claimed {os_claim} but devices indicate VM."
    return mk(f"Validate hardware: OS={os_claim}, USB={json.dumps(usb)}", {
        "reasoning": reasoning, "coherent": coherent, "score": score,
        "issues": [] if coherent else ["VM USB devices detected"],
        "fixes": [] if coherent else ["Use USB passthrough or gadgetfs synthesis"],
    }, "hardware_profile_coherence")

def gen_tls_profile_selection():
    td, ti = pt()
    cdn = random.choice(["cloudflare","akamai","fastly","cloudfront","none"])
    ja4_check = cdn in ("cloudflare","akamai")
    browser = random.choice(["Chrome","Firefox"])
    ja4 = f"t13d1517h2_{random.randbytes(6).hex()}" if browser=="Chrome" else f"t13d1516h2_{random.randbytes(6).hex()}"
    return mk(f"Select TLS profile for {td} (CDN: {cdn}, browser: {browser}/Windows).", {
        "reasoning": f"{td} behind {cdn}. {'JA4 fingerprinting active — must match exactly.' if ja4_check else 'No JA4 check.'} {browser}/Windows profile selected. {'GREASE extensions required.' if browser=='Chrome' else ''}",
        "recommended_profile": f"{browser.lower()}_win", "ja4_hash": ja4,
        "browser": browser, "grease_required": browser=="Chrome",
        "cdn_checks_ja4": ja4_check, "risk_level": "high" if ja4_check else "low",
    }, "tls_profile_selection")

def gen_coherence_check():
    st, city, ac, zc, tz = pick_state(); name = gn()
    coherent = random.random() > 0.4
    if coherent:
        return mk(f"Check coherence: name={name}, city={city}, state={st}, tz={tz}, locale=en-US.", {
            "reasoning": f"All signals consistent: {name} in {city},{st}, TZ {tz} matches, locale en-US appropriate.",
            "coherent": True, "score": random.randint(78,96), "issues": [],
        }, "coherence_check")
    else:
        return mk(f"Check coherence: name={name}, city={city}, state={st}, tz=Asia/Tokyo, locale=ja-JP.", {
            "reasoning": f"Multiple mismatches: US city with Japanese TZ/locale. Identity graph flags this.",
            "coherent": False, "score": random.randint(15,40), "issues": ["TZ/locale mismatch with geo"],
        }, "coherence_check")
