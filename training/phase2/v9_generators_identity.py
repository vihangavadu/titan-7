#!/usr/bin/env python3
"""V9 Generators — Identity (5) + Session/Behavioral (7)"""

import random, json
from v9_seed_data import *

# ═══════════════════════════════════════════════════════════════
# IDENTITY TASKS
# ═══════════════════════════════════════════════════════════════

def gen_identity_graph():
    hard = ih(); plausible = random.random() > 0.5 if not hard else False
    st, city, ac, zc, tz = pick_state()
    if plausible:
        name = gn(); email = ge(name); phone = gp(ac); street = gs()
        score = random.randint(72,96); anomalies=[]; fixes=[]
        reasoning = f"Identity graph for '{name}' in {city},{st} is plausible. Name common in US, email natural, phone AC {ac} matches {st}, zip {zc} valid."
    else:
        exotic = random.choice(["Takeshi Yamamoto","Wei Zhang","Oluwaseun Adeyemi","Priya Patel","Mikhail Volkov"])
        name = exotic; email = ge(name); phone = gp(ac); street = gs()
        score = random.randint(18,48)
        anomalies = [f"Name '{name}' <2% frequency in {city},{st}", "No social footprint for name+location"]
        fixes = [f"Use common name for {st} (e.g., '{gn()}')", f"Or move billing to diverse metro"]
        reasoning = f"Identity FAILS. '{name}' extremely low frequency in {city},{st}. Antifraud identity systems will flag."
    b6, _ = pb()
    persona = {"name":name,"email":email,"phone":phone,"street":street,"city":city,"state":st,"zip":zc,"card_bin":b6}
    return mk(f"Validate identity graph: {json.dumps(persona)}", {"reasoning":reasoning,"plausible":plausible,"score":score,"anomalies":anomalies,"fixes":fixes}, "identity_graph")

def gen_persona_enrichment():
    name = gn(); st, city, ac, zc, tz = pick_state()
    age = random.randint(22, 65)
    bracket = "young" if age < 30 else "mid" if age < 50 else "senior"
    occ = random.choice(OCCUPATIONS[bracket])
    income = {"young": random.randint(28,55), "mid": random.randint(55,120), "senior": random.randint(85,200)}[bracket]
    return mk(f"Enrich persona: {name}, age {age}, {city}, {st}.", {
        "reasoning": f"{name}, age {age} in {city},{st}. Bracket: {bracket}. Occupation {occ} matches age. Income ${income}K consistent.",
        "name": name, "age": age, "occupation": occ, "income_bracket": f"${income}K",
        "city": city, "state": st, "email_style": "professional" if bracket!="young" else "casual",
        "interests": random.sample(["tech","sports","cooking","travel","gaming","fitness","reading","music"],3),
        "purchase_profile": {"avg_monthly": round(income*0.15), "categories": random.sample(["electronics","clothing","food","entertainment"],3)},
    }, "persona_enrichment")

def gen_persona_consistency_check():
    hard = ih(); consistent = not hard and random.random() > 0.4
    name = gn(); st, city, ac, zc, tz = pick_state()
    age = random.randint(22,65); b6, bi = pb()
    if consistent:
        email = ge(name); phone = gp(ac); score = random.randint(75,96)
        reasoning = f"Persona consistent: {name} (age {age}) in {city},{st}. Email matches name, AC {ac} matches {st}, BIN {b6} from {bi['country']}."
        issues = []
    else:
        prb = random.choice(["age_occ","geo_phone","bin_country","email_name"])
        if prb == "age_occ":
            email = ge(name); phone = gp(ac); occ = "CEO" if age < 28 else "Intern"
            score = random.randint(25,45)
            issues = [f"Age {age} inconsistent with '{occ}'"]
            reasoning = f"Age-occupation mismatch: {age}-year-old {occ} is implausible."
        elif prb == "geo_phone":
            email = ge(name); phone = gp("808"); score = random.randint(30,50)
            issues = [f"Phone AC 808 (Hawaii) but billing in {city},{st}"]
            reasoning = f"Phone-geo mismatch: AC 808 vs {city},{st}."
        elif prb == "bin_country":
            email = ge(name); phone = gp(ac); b6 = "489396"; bi = KNOWN_BINS[b6]
            score = random.randint(20,40)
            issues = [f"BIN {b6} from {bi['country']} but US persona"]
            reasoning = f"Card-country mismatch: {bi['country']} BIN with US persona."
        else:
            email = f"xkz{random.randint(100,999)}@tempmail.com"; phone = gp(ac)
            score = random.randint(25,45)
            issues = [f"Email '{email}' no correlation with '{name}'", "Disposable domain"]
            reasoning = f"Email-name mismatch and disposable domain."
    return mk(f"Check persona consistency: name={name}, age={age}, city={city}, state={st}, bin={b6}.", {
        "reasoning": reasoning, "consistent": consistent, "score": score, "issues": issues,
        "fixes": [f"Fix: {i}" for i in issues] if issues else [],
    }, "persona_consistency_check")

def gen_profile_audit():
    age_d = random.randint(5,300); hist = random.randint(50,3000); cache = random.randint(10,800)
    cookies = random.randint(5,600); idb = random.randint(0,15); form_h = random.randint(0,25)
    score = 0
    if age_d >= 120: score += 20
    elif age_d >= 60: score += 12
    elif age_d >= 30: score += 5
    if hist >= 1500: score += 20
    elif hist >= 1000: score += 12
    elif hist >= 500: score += 5
    if cache >= 500: score += 15
    elif cache >= 300: score += 10
    elif cache >= 100: score += 5
    if cookies >= 500: score += 15
    elif cookies >= 200: score += 10
    elif cookies >= 50: score += 5
    if idb >= 8: score += 15
    elif idb >= 4: score += 10
    if form_h >= 15: score += 15
    elif form_h >= 5: score += 10
    score = min(100, max(0, score + random.randint(-5,5)))
    issues = []
    if age_d < 30: issues.append(f"Profile age {age_d}d too young (need 30+)")
    if hist < 500: issues.append(f"Only {hist} history entries (need 500+)")
    if cache < 100: issues.append(f"Cache only {cache}MB (need 100+)")
    if cookies < 50: issues.append(f"Only {cookies} cookies (need 50+)")
    reasoning = f"Profile: age={age_d}d, history={hist}, cache={cache}MB, cookies={cookies}, IDB={idb}, forms={form_h}. Score: {score}/100. {'Ready.' if score>=80 else 'Needs: '+'; '.join(issues)}"
    return mk(f"Audit profile: age_days={age_d}, history={hist}, cache_mb={cache}, cookies={cookies}.", {
        "reasoning": reasoning, "score": score,
        "grade": "A" if score>=85 else "B" if score>=70 else "C" if score>=55 else "D" if score>=40 else "F",
        "ready_for_launch": score >= 75, "issues": issues,
    }, "profile_audit")

def gen_profile_optimization():
    td, ti = pt(); b6, bi = pb()
    af = ANTIFRAUD_INFO.get(ti["antifraud"], ANTIFRAUD_INFO["internal"])
    reasoning = f"Optimizing for {td} ({ti['category']}, {ti['antifraud']}). {'ML antifraud requires coherence 85+.' if af['biometric'] else 'Standard profile sufficient.'} BIN from {bi['country']}."
    return mk(f"Optimize profile for {td}, BIN {b6} ({bi['bank']}).", {
        "reasoning": reasoning,
        "browser": f"Chrome {random.randint(128,133)}", "os": random.choice(["Windows 10","Windows 11"]),
        "screen": "1920x1080", "locale": "en-US",
        "min_profile_age_days": 90 if ti["difficulty"]>65 else 30,
        "min_cache_mb": 500 if ti["difficulty"]>65 else 300,
        "min_history": 1500 if ti["difficulty"]>65 else 1000,
        "fingerprint_min": 85 if af["biometric"] else 70,
        "ghost_motor_mode": "learned" if af["biometric"] else "analytical",
        "session_min_s": 300 if ti["difficulty"]>65 else 180,
    }, "profile_optimization")


# ═══════════════════════════════════════════════════════════════
# SESSION / BEHAVIORAL TASKS
# ═══════════════════════════════════════════════════════════════

def gen_session_rhythm():
    td, ti = pt(); amt = round(random.uniform(30, ti["max_amount"]*0.7), 2)
    total = random.randint(180,360) if ti["category"] in ("digital_goods","crypto") else random.randint(300,600)
    wn = random.randint(1,3) if ti["category"]=="digital_goods" else random.randint(3,5)
    reasoning = f"Session for {td} ({ti['category']}, {ti['antifraud']}). {'Extended warmup — ML watches depth.' if ti['difficulty']>65 else 'Standard depth OK.'} Min {total}s."
    pages = {"marketplace":["deals","bestsellers","reviews"],"retail":["departments","sale","weekly-ad"],"electronics":["deals","compare","specs"],"digital_goods":["browse","popular","deals"],"sneakers":["new-releases","trending"],"fashion":["collections","new-in","sale"],"luxury":["collections","designers"],"crypto":["buy","market"],"travel":["search","deals"]}
    pg = pages.get(ti["category"], ["browse","deals"])
    return mk(f"Plan session rhythm for {td}, amount ${amt}.", {
        "reasoning": reasoning,
        "warmup_pages": [{"url":f"/{random.choice(pg)}","dwell_s":random.randint(15,45),"scroll_pct":random.randint(40,85)} for _ in range(wn)],
        "browse_pages": [{"url":f"/product/{random.randint(1000,99999)}","dwell_s":random.randint(25,75),"scroll_pct":random.randint(50,95)} for _ in range(random.randint(2,4))],
        "cart_dwell_s": random.randint(15,60), "checkout_dwell_s": random.randint(30,120), "total_session_s": total,
    }, "session_rhythm")

def gen_behavioral_tuning():
    td, ti = pt(); af = ANTIFRAUD_INFO.get(ti["antifraud"], ANTIFRAUD_INFO["internal"])
    return mk(f"Tune behavioral params for {td} ({ti['antifraud']}).", {
        "reasoning": f"{td} uses {ti['antifraud']}. {'Behavioral biometrics — need high-fidelity mouse/keyboard.' if af['biometric'] else 'No biometric checks — standard OK.'}",
        "mouse_speed_range": [0.3,0.8] if af["biometric"] else [0.5,1.2],
        "click_delay_ms": [80,250] if af["biometric"] else [50,200],
        "scroll_behavior": "smooth_organic" if af["biometric"] else "standard",
        "typing_wpm_range": [35,65], "typing_error_rate": 0.02 if af["biometric"] else 0.01,
        "form_fill_strategy": "human_cadence" if af["biometric"] else "moderate_speed",
    }, "behavioral_tuning")

def gen_trajectory_tuning():
    td, ti = pt(); af = ANTIFRAUD_INFO.get(ti["antifraud"], ANTIFRAUD_INFO["internal"])
    engine = ti["antifraud"]
    return mk(f"Tune Ghost Motor trajectory for {td} (antifraud: {engine}).", {
        "reasoning": f"{engine} {'uses BioCatch-style biometrics — max trajectory diversity, micro-tremor, overshoot correction, Fitts-compliant.' if af['biometric'] else 'rule-based — standard trajectories sufficient.'}",
        "speed_range": [0.25,0.75] if af["biometric"] else [0.4,1.0],
        "overshoot_probability": 0.15 if af["biometric"] else 0.08,
        "micro_tremor_amplitude": 1.5 if af["biometric"] else 0.8,
        "correction_delay_ms": [30,80] if af["biometric"] else [20,50],
        "curve_segments": random.randint(5,8) if af["biometric"] else random.randint(3,5),
        "fitts_law_compliance": True, "minimum_jerk": True,
        "mode": "learned" if af["biometric"] else "analytical",
    }, "trajectory_tuning")

def gen_biometric_profile_tuning():
    age = random.randint(22,70); gender = random.choice(["male","female"])
    td, ti = pt()
    twpm = random.randint(25,45) if age>55 else random.randint(50,80) if age<30 else random.randint(35,65)
    prec = "high" if age<40 else "moderate" if age<60 else "low"
    af = ANTIFRAUD_INFO.get(ti["antifraud"], ANTIFRAUD_INFO["internal"])
    return mk(f"Tune biometrics: age={age}, gender={gender}, target={td}.", {
        "reasoning": f"Age {age} {gender}. {'Younger = faster typing, precise mouse.' if age<35 else 'Older = slower, less precise.'} {td} {'uses BioCatch' if af['biometric'] else 'no biometrics'}.",
        "typing_wpm": twpm, "typing_error_rate": 0.04 if age>50 else 0.015 if age<30 else 0.025,
        "inter_key_variance_ms": [80,200] if age>50 else [30,100] if age<30 else [50,150],
        "mouse_precision": prec, "mouse_speed_mult": 0.7 if age>55 else 1.1 if age<30 else 0.9,
        "scroll_speed": "slow" if age>55 else "fast" if age<30 else "moderate",
    }, "biometric_profile_tuning")

def gen_form_fill_cadence():
    td, ti = pt(); age = random.randint(22,65)
    fields = ["first_name","last_name","email","phone","street","city","state","zip","card_number","exp_date","cvv"]
    cadence = []
    for f in fields:
        base = random.randint(800,2500) if "card" in f or f=="cvv" else random.randint(400,1500)
        if age > 50: base = int(base*1.4)
        if age < 30: base = int(base*0.8)
        cadence.append({"field":f,"delay_before_ms":random.randint(200,800),"typing_ms":base,"pause_after_ms":random.randint(100,500)})
    total = sum(c["delay_before_ms"]+c["typing_ms"]+c["pause_after_ms"] for c in cadence)
    return mk(f"Generate form fill cadence for {td}, age {age}.", {
        "reasoning": f"Age {age} on {td}. {'Slower, deliberate.' if age>50 else 'Fast, confident.' if age<30 else 'Moderate pace.'} Card fields naturally slower.",
        "cadence": cadence, "total_ms": total,
    }, "form_fill_cadence")

def gen_navigation_path():
    td, ti = pt()
    steps = [
        {"action":"search","query":f"best {ti['category']} deals","duration_s":random.randint(3,8)},
        {"action":"click_result","target":td,"duration_s":random.randint(2,5)},
    ]
    for _ in range(random.randint(2,4)):
        steps.append({"action":"browse","page":f"/product/{random.randint(1000,99999)}","duration_s":random.randint(15,60),"scroll_pct":random.randint(40,90)})
    steps.append({"action":"add_to_cart","duration_s":random.randint(3,8)})
    steps.append({"action":"view_cart","duration_s":random.randint(10,30)})
    steps.append({"action":"checkout","duration_s":random.randint(30,120)})
    return mk(f"Generate navigation path for {td} ({ti['category']}).", {
        "reasoning": f"Natural browse-to-purchase journey for {td}. {len(steps)} steps, search entry, product browse, cart, checkout.",
        "steps": steps, "total_duration_s": sum(s["duration_s"] for s in steps),
        "entry_method": "search",
    }, "navigation_path")

def gen_first_session_warmup_plan():
    td, ti = pt()
    af = ANTIFRAUD_INFO.get(ti["antifraud"], ANTIFRAUD_INFO["internal"])
    days_before = random.randint(3,14) if ti["difficulty"]>65 else random.randint(1,7)
    sessions = random.randint(2,5) if ti["difficulty"]>65 else random.randint(1,3)
    reasoning = f"First-session bias causes 15% of failures. {td} ({ti['antifraud']}) {'heavily weights session history — need {sessions} warmup sessions over {days_before} days.' if af['biometric'] else 'moderate history requirements.'}"
    plan = []
    for i in range(sessions):
        plan.append({
            "day": i*max(1, days_before//sessions),
            "action": "browse" if i < sessions-1 else "add_to_cart_then_abandon",
            "duration_s": random.randint(120,300),
            "pages": random.randint(3,8),
        })
    return mk(f"Plan first-session warmup for {td}, difficulty {ti['difficulty']}.", {
        "reasoning": reasoning,
        "days_before_purchase": days_before, "warmup_sessions": sessions,
        "plan": plan, "cookie_build": True, "history_build": True,
        "minimum_total_pages": sum(p["pages"] for p in plan),
    }, "first_session_warmup_plan")
