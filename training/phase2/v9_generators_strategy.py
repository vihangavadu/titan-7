#!/usr/bin/env python3
"""V9 Generators — Strategy (4) + Decline/Detection (6) + Velocity/Rotation (2)"""

import random, json
from v9_seed_data import *

# ═══════════════════════════════════════════════════════════════
# STRATEGY TASKS
# ═══════════════════════════════════════════════════════════════

def gen_three_ds_strategy():
    b6, bi = pb(); td, ti = pt()
    amt = round(random.uniform(20, ti["max_amount"]*0.8), 2)
    exemptions = []
    if amt < 30: exemptions.append({"type":"low_value","applies":True,"reason":f"${amt} < EUR 30 threshold"})
    elif amt < 100: exemptions.append({"type":"TRA","applies":True,"reason":f"${amt} < EUR 100 TRA threshold if acquirer fraud <0.13%"})
    if not bi["vbv"]: exemptions.append({"type":"non_vbv","applies":True,"reason":f"BIN {b6} not enrolled in VBV/SecureCode"})
    if bi["country"] not in ("US","GB","DE","FR","NL","ES","IT"): exemptions.append({"type":"one_leg_out","applies":True,"reason":f"Card from {bi['country']} (non-EU) on EU merchant = no SCA"})
    bypass = len(exemptions) > 0
    confidence = round(0.3 + len(exemptions)*0.2 + random.gauss(0,0.05), 2)
    confidence = min(0.95, max(0.1, confidence))
    reasoning = f"Step 1: BIN {b6} ({bi['bank']}, {bi['country']}), {'VBV' if bi['vbv'] else 'non-VBV'}. Step 2: Target {td} uses {ti['psp']}, 3DS rate {int(ti['3ds_rate']*100)}%. Step 3: Amount ${amt}. Step 4: Applicable exemptions: {len(exemptions)}. {'Best route: '+exemptions[0]['type'] if exemptions else 'No exemptions — must handle 3DS challenge.'}."
    return mk(f"Plan 3DS strategy: BIN {b6} ({bi['bank']}), target {td}, amount ${amt}.", {
        "reasoning": reasoning,
        "bypass_possible": bypass, "confidence": confidence,
        "exemptions": exemptions,
        "recommended_strategy": exemptions[0]["type"] if exemptions else "handle_3ds_challenge",
        "fallback": "reduce amount below EUR 30 for low-value exemption" if not bypass else None,
        "risk_notes": [f"3DS rate on {td}: {int(ti['3ds_rate']*100)}%", f"PSP: {ti['psp']}"],
    }, "three_ds_strategy")

def gen_operation_planning():
    td, ti = pt(); b6, bi = pb()
    amt = round(random.uniform(30, ti["max_amount"]*0.6), 2)
    st, city, ac, zc, tz = pick_state()
    name = gn()
    p = pred(bi, ti, amt)
    phases = [
        {"phase":"setup","tasks":["VPN to residential IP matching billing","Set timezone/locale","Load profile"],"est_min":5},
        {"phase":"warmup","tasks":[f"Browse {td} for {random.randint(3,5)} pages",f"Dwell {random.randint(30,60)}s per page"],"est_min":random.randint(3,8)},
        {"phase":"cart","tasks":["Add target item","Review cart","Proceed to checkout"],"est_min":random.randint(2,5)},
        {"phase":"checkout","tasks":["Fill shipping (human cadence)","Fill payment","Review order"],"est_min":random.randint(3,8)},
        {"phase":"submit","tasks":["Submit order","Handle 3DS if triggered","Confirm"],"est_min":random.randint(1,3)},
    ]
    reasoning = f"Step 1: Target {td} (difficulty {ti['difficulty']}, {ti['antifraud']}). Step 2: BIN {b6} ({bi['bank']}, success pred {p}). Step 3: Amount ${amt} within safe range. Step 4: Persona {name} in {city},{st}. Step 5: {'Non-VBV — skip 3DS prep.' if not bi['vbv'] else '3DS likely — prepare exemption strategy.'} Total estimated time: {sum(p['est_min'] for p in phases)} minutes."
    return mk(f"Plan operation: target {td}, BIN {b6}, amount ${amt}, persona {name} in {city},{st}.", {
        "reasoning": reasoning,
        "success_prediction": p, "risk_level": rlevel(p),
        "phases": phases, "total_time_min": sum(ph["est_min"] for ph in phases),
        "critical_checks": ["fingerprint coherence 80+","environment coherence 80+","profile age 30d+"],
        "abort_conditions": ["fingerprint score <70","datacenter IP detected","3DS challenge with no exemption"],
    }, "operation_planning")

def gen_preflight_advisor():
    td, ti = pt(); b6, bi = pb()
    fp_score = random.randint(30, 98); env_score = random.randint(30, 98)
    profile_age = random.randint(5, 200); amt = round(random.uniform(20, ti["max_amount"]*0.8), 2)
    go = fp_score >= 75 and env_score >= 75 and profile_age >= 30
    issues = []
    if fp_score < 75: issues.append(f"Fingerprint coherence {fp_score}/100 below 75 minimum")
    if env_score < 75: issues.append(f"Environment coherence {env_score}/100 below 75 minimum")
    if profile_age < 30: issues.append(f"Profile age {profile_age}d below 30d minimum")
    reasoning = f"Preflight for {td}: FP={fp_score}, ENV={env_score}, profile_age={profile_age}d, amount=${amt}. {'ALL CLEAR — proceed.' if go else 'HOLD — '+str(len(issues))+' issue(s): '+'; '.join(issues)}"
    return mk(f"Preflight check: target {td}, BIN {b6}, fp_score={fp_score}, env_score={env_score}, profile_age={profile_age}d, amount=${amt}.", {
        "reasoning": reasoning,
        "decision": "GO" if go else "NO-GO",
        "issues": issues, "fixes": [f"Fix: {i.split(' below')[0]}" for i in issues],
        "confidence": round(0.9 if go else 0.3 + random.gauss(0,0.05), 2),
    }, "preflight_advisor")

def gen_copilot_abort_prediction():
    td, ti = pt()
    session_s = random.randint(30, 300)
    fraud_score_trajectory = [random.randint(10, 40) for _ in range(3)]
    fraud_score_trajectory.sort()
    latest = fraud_score_trajectory[-1]
    slope = (fraud_score_trajectory[-1] - fraud_score_trajectory[0]) / max(len(fraud_score_trajectory)-1, 1)
    should_abort = latest > 65 or slope > 15
    time_to_detection = random.randint(15, 60) if should_abort else None
    signals = []
    if latest > 65: signals.append(f"Fraud score {latest} exceeding 65 threshold")
    if slope > 15: signals.append(f"Score rising at {slope:.0f} points/interval — accelerating")
    if session_s < 120: signals.append(f"Session only {session_s}s — behavioral flag imminent")
    reasoning = f"Step 1: Fraud score trajectory {fraud_score_trajectory} — {'rapidly rising' if slope>15 else 'stable' if slope<5 else 'slowly rising'}. Step 2: Latest score {latest} — {'above danger threshold' if latest>65 else 'within safe range'}. Step 3: Session {session_s}s. Step 4: {'ABORT RECOMMENDED — detection in ~{time_to_detection}s.' if should_abort else 'Continue — scores within safe range.'}"
    return mk(f"Predict abort: target {td}, session {session_s}s, fraud_scores {fraud_score_trajectory}.", {
        "reasoning": reasoning,
        "should_abort": should_abort,
        "confidence": round(0.75 + random.gauss(0,0.05), 2) if should_abort else round(0.6 + random.gauss(0,0.05), 2),
        "estimated_time_to_detection_s": time_to_detection,
        "signals": signals,
        "recommended_action": "Abort immediately — close browser, rotate IP" if should_abort else "Continue operation",
    }, "copilot_abort_prediction")


# ═══════════════════════════════════════════════════════════════
# DECLINE / DETECTION TASKS
# ═══════════════════════════════════════════════════════════════

def gen_decline_autopsy():
    td, ti = pt(); b6, bi = pb()
    psp = ti["psp"]; codes = DECLINE_CODES.get(psp, DECLINE_CODES["stripe"])
    code = random.choice(codes); amt = round(random.uniform(30, ti["max_amount"]), 2)
    session_dur = random.randint(30,600); fp_score = random.randint(30,98); profile_age = random.randint(5,180)
    if code in ("fraudulent","lost_card","stolen_card","Fraud","Blocked"):
        root = "Card flagged by issuer — BIN compromised"; cat = "payment"; retriable = False; wait = 0
    elif session_dur < 120:
        root = f"Session {session_dur}s below behavioral threshold"; cat = "behavioral"; retriable = True; wait = random.randint(120,360)
    elif fp_score < 60:
        root = f"Fingerprint score {fp_score} triggered detection"; cat = "fingerprint"; retriable = True; wait = random.randint(60,240)
    elif profile_age < 30:
        root = f"Profile age {profile_age}d triggers new-account bias"; cat = "identity"; retriable = True; wait = random.randint(180,720)
    else:
        root = f"Composite risk score exceeded threshold"; cat = "composite"; retriable = True; wait = random.randint(120,360)
    patches = []
    if cat == "behavioral": patches.append({"module":"ghost_motor_v6.py","change":f"Increase min session to {random.randint(240,360)}s","priority":"critical"})
    elif cat == "fingerprint": patches.append({"module":"ai_intelligence_engine.py","change":"Require FP score 80+ before launch","priority":"critical"})
    elif cat == "payment" and not retriable: patches.append({"module":"ai_intelligence_engine.py","change":f"Blacklist BIN {b6}","priority":"critical"})
    reasoning = f"Decline '{code}' from {psp.title()} on {td}. Root: {root}. {'Card burned — do not reuse.' if not retriable else f'Retriable after {wait}min cooldown.'}"
    return mk(f"Decline autopsy: code={code}, target={td}, psp={psp}, amount=${amt}, bin={b6}, session={session_dur}s, fp={fp_score}.", {
        "reasoning": reasoning, "decline_code": code, "root_cause": root, "category": cat,
        "is_retriable": retriable, "wait_time_min": wait, "patches": patches,
        "confidence": round(random.uniform(0.65,0.95),2),
    }, "decline_autopsy")

def gen_decline_analysis():
    td, ti = pt()
    declines = random.randint(5,30); total = declines + random.randint(1,20)
    rate = round(declines/total, 2)
    top_codes = random.sample(DECLINE_CODES.get(ti["psp"], DECLINE_CODES["stripe"]), min(3,len(DECLINE_CODES.get(ti["psp"],[]))))
    pattern = random.choice(["velocity","time_of_day","amount_threshold","bin_specific","behavioral"])
    return mk(f"Analyze decline patterns on {td}: {declines}/{total} declines.", {
        "reasoning": f"{td}: {declines}/{total} declines ({int(rate*100)}%). Top codes: {', '.join(top_codes)}. Pattern detected: {pattern}. {'Velocity limit hit — slow down.' if pattern=='velocity' else 'Adjust approach based on pattern.'}",
        "decline_rate": rate, "total_operations": total,
        "top_decline_codes": top_codes, "detected_pattern": pattern,
        "recommendation": f"Address {pattern} pattern — {'reduce frequency' if pattern=='velocity' else 'adjust timing' if pattern=='time_of_day' else 'lower amounts' if pattern=='amount_threshold' else 'rotate BINs' if pattern=='bin_specific' else 'improve behavioral realism'}",
    }, "decline_analysis")

def gen_detection_analysis():
    td, ti = pt()
    vectors = random.sample(["fingerprint_mismatch","behavioral_anomaly","velocity_spike","geo_inconsistency","device_repeat","session_too_short","tls_mismatch"], random.randint(1,3))
    severity = random.choice(["low","moderate","high","critical"])
    return mk(f"Analyze detection events on {td}: vectors={vectors}.", {
        "reasoning": f"Detection on {td} ({ti['antifraud']}). Vectors: {', '.join(vectors)}. Severity: {severity}. {'Multiple vectors compound exponentially.' if len(vectors)>1 else 'Single vector — targeted fix.'} {ti['antifraud'].title()} is {'ML-based — adapts to patterns' if ANTIFRAUD_INFO.get(ti['antifraud'],{}).get('type')=='ml' else 'rule-based — predictable thresholds'}.",
        "detection_vectors": vectors, "severity": severity,
        "antifraud_engine": ti["antifraud"],
        "recommended_actions": [f"Fix {v}" for v in vectors],
        "cooldown_hours": random.randint(4,48) if severity in ("high","critical") else random.randint(1,8),
    }, "detection_analysis")

def gen_detection_root_cause():
    td, ti = pt()
    logs = [{"timestamp":f"T+{random.randint(10,300)}s","event":random.choice(["fp_check","velocity_check","behavioral_score","geo_verify","device_match"]),"result":random.choice(["pass","fail","warn"]),"score":random.randint(10,95)} for _ in range(random.randint(4,8))]
    fails = [l for l in logs if l["result"]=="fail"]
    warns = [l for l in logs if l["result"]=="warn"]
    if fails:
        root = f"Primary failure: {fails[0]['event']} at T+{fails[0]['timestamp'].split('+')[1]} with score {fails[0]['score']}"
        module = {"fp_check":"fingerprint_shims.py","velocity_check":"ai_intelligence_engine.py","behavioral_score":"ghost_motor_v6.py","geo_verify":"proxy_manager.py","device_match":"genesis_core.py"}.get(fails[0]["event"],"unknown")
    else:
        root = f"Compound risk: {len(warns)} warnings pushed composite score above threshold"
        module = "ai_intelligence_engine.py"
    reasoning = f"Step 1: Analyzed {len(logs)} detection log entries. Step 2: {len(fails)} hard failures, {len(warns)} warnings. Step 3: Root cause: {root}. Step 4: Module to patch: {module}."
    return mk(f"Find detection root cause on {td}. Logs: {json.dumps(logs[:5])}", {
        "reasoning": reasoning, "root_cause": root, "module_to_patch": module,
        "failed_checks": [f["event"] for f in fails],
        "warning_checks": [w["event"] for w in warns],
        "patch_suggestion": f"Improve {fails[0]['event'] if fails else 'composite scoring'} in {module}",
        "confidence": round(0.7 + len(fails)*0.05 + random.gauss(0,0.03), 2),
    }, "detection_root_cause")

def gen_detection_prediction():
    td, ti = pt()
    scores = sorted([random.randint(15,50) for _ in range(4)])
    latest = scores[-1]; slope = (scores[-1]-scores[0])/max(len(scores)-1,1)
    will_detect = latest > 55 or slope > 10
    eta = random.randint(15,45) if will_detect else None
    return mk(f"Predict detection: target {td}, fraud_score_history {scores}.", {
        "reasoning": f"Score trajectory {scores}, slope={slope:.1f}/interval. Latest {latest}. {'Detection imminent in ~{eta}s — abort recommended.' if will_detect else 'Trajectory safe — continue.'}",
        "detection_imminent": will_detect,
        "estimated_seconds": eta,
        "current_score": latest, "trajectory_slope": round(slope,1),
        "action": "ABORT" if will_detect else "CONTINUE",
    }, "detection_prediction")

def gen_defense_tracking():
    td, ti = pt()
    change_type = random.choice(["3ds_increase","new_antifraud","velocity_tightened","new_captcha","fingerprint_upgrade"])
    old_val = random.choice(["Stripe Radar v1","no captcha","5/day velocity","basic fingerprint"])
    new_val = random.choice(["Stripe Radar v2 + Forter","Turnstile captcha added","3/day velocity","advanced fingerprint + behavioral"])
    impact = random.choice(["high","moderate","low"])
    return mk(f"Track defense changes on {td}: detected {change_type}.", {
        "reasoning": f"{td} changed from '{old_val}' to '{new_val}'. Impact: {impact}. {'Must adapt approach immediately.' if impact=='high' else 'Monitor and adjust gradually.'}",
        "domain": td, "change_type": change_type,
        "old_defense": old_val, "new_defense": new_val,
        "impact": impact,
        "adaptation_required": impact in ("high","moderate"),
        "recommended_changes": [f"Update preset for {td}","Re-evaluate difficulty score","Test with small amount first"],
    }, "defense_tracking")


# ═══════════════════════════════════════════════════════════════
# VELOCITY / ROTATION TASKS
# ═══════════════════════════════════════════════════════════════

def gen_card_rotation():
    bins = random.sample(list(KNOWN_BINS.keys()), min(5, len(KNOWN_BINS)))
    targets = random.sample(list(KNOWN_TARGETS.keys()), min(5, len(KNOWN_TARGETS)))
    history = []
    for _ in range(random.randint(3,12)):
        hb = random.choice(bins); ht = random.choice(targets)
        hpsp = KNOWN_TARGETS[ht]["psp"]; hcodes = DECLINE_CODES.get(hpsp, DECLINE_CODES["stripe"])
        history.append({"bin":hb,"target":ht,"code":random.choice(hcodes+["approved"]*3),"amount":round(random.uniform(20,300),2),"hours_ago":round(random.uniform(0.5,72),1)})
    burned = set(); hot = set()
    for h in history:
        if h["code"] in ("fraudulent","lost_card","stolen_card","Fraud","Blocked"): burned.add(h["bin"])
        elif h["code"] not in ("approved",) and h["hours_ago"] < 4: hot.add(h["bin"])
    available = [b for b in bins if b not in burned and b not in hot]
    if not available: available = [b for b in bins if b not in burned]
    if not available: available = bins[:1]
    best_bin = min(available, key=lambda b: sum(1 for h in history if h["bin"]==b and h["hours_ago"]<24))
    best_target = min(targets, key=lambda t: KNOWN_TARGETS[t]["difficulty"])
    best_amt = round(random.uniform(30, min(150, KNOWN_TARGETS[best_target]["max_amount"]*0.4)), 2)
    recent = sum(1 for h in history if h["bin"]==best_bin and h["hours_ago"]<24)
    vlimit = KNOWN_BINS[best_bin]["velocity_day"]
    cd = 0 if recent < vlimit-1 else random.randint(2,8)
    reasoning = f"Analyzed {len(history)} transactions. {len(burned)} burned, {len(hot)} hot. Best: {KNOWN_BINS[best_bin]['bank']} BIN {best_bin} — {recent}/{vlimit} daily uses. Paired with {best_target} (difficulty {KNOWN_TARGETS[best_target]['difficulty']}). Amount ${best_amt} safe.{' Cooldown needed.' if cd>0 else ' Clear for use.'}"
    return mk(f"Optimize card rotation. BINs: {bins}. Targets: {targets}. History: {json.dumps(history[-6:])}", {
        "reasoning": reasoning,
        "recommended_bin": best_bin, "recommended_target": best_target,
        "recommended_amount": best_amt, "cooldown_hours": cd,
        "burned_bins": list(burned), "hot_bins": list(hot),
    }, "card_rotation")

def gen_velocity_schedule():
    b6, bi = pb(); td, ti = pt()
    history = [{"code":random.choice(DECLINE_CODES.get(ti["psp"],DECLINE_CODES["stripe"])+["approved"]*2),"hours_ago":round(random.uniform(0.1,72),1)} for _ in range(random.randint(0,8))]
    rd = sum(1 for h in history if h["hours_ago"]<4 and h["code"]!="approved")
    t24 = sum(1 for h in history if h["hours_ago"]<24)
    if rd > 2:
        mh=1; md=2; cdm=360; sp=120
        reasoning = f"HIGH ALERT: {rd} declines in 4h on BIN {b6}. Severely restrict velocity. {t24}/{bi['velocity_day']} in 24h."
    elif rd > 0:
        mh=1; md=3; cdm=180; sp=90
        reasoning = f"CAUTION: {rd} recent decline(s). {t24}/{bi['velocity_day']} in 24h. Space at {sp}min+."
    else:
        mh=2; md=min(5,bi["velocity_day"]-1); cdm=120; sp=60
        reasoning = f"CLEAR: No recent declines. {t24}/{bi['velocity_day']} daily. Standard {sp}min spacing."
    return mk(f"Schedule velocity for BIN {b6} ({bi['bank']}), target {td}. History: {json.dumps(history[-4:])}", {
        "reasoning": reasoning,
        "max_per_hour": mh, "max_per_day": md, "cooldown_decline_min": cdm,
        "optimal_spacing_min": sp, "current_24h": t24, "issuer_limit": bi["velocity_day"],
        "risk_level": "high" if rd>2 else "moderate" if rd>0 else "low",
    }, "velocity_schedule")
