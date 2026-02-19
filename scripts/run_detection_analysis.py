"""TITAN V7.0 — Full Detection Vector Analysis against generated profile"""
import sqlite3, json, re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Config
PERSONA_EMAIL = "malithwishwa@gmail.com"
PERSONA_PHONE = "+94772222222"
CARD_COUNTRY = "LK"
RISKIFIED_MIN_AGE = 60
RISKIFIED_MIN_STORAGE = 400
SEON_THRESHOLD = 50
DISPOSABLE_EMAILS = ["tempmail.com","guerrillamail.com","mailinator.com","yopmail.com"]
FORBIDDEN_FILES = ["commerce_tokens.json","hardware_profile.json","fingerprint_config.json","profile_metadata.json","profile.json","history.json","cookies.json"]
STANDARD_FILES = ["places.sqlite","cookies.sqlite","formhistory.sqlite","favicons.sqlite","permissions.sqlite",
    "content-prefs.sqlite","prefs.js","times.json","compatibility.ini","extensions.json","handlers.json",
    "xulstore.json","search.json","sessionstore.js","SiteSecurityServiceState.bin","cert9.db","key4.db",
    "pkcs11.txt","sessionCheckpoints.json"]

R={"PASS":[],"WARN":[],"FAIL":[],"ANOM":[]}
def P(n,m): R["PASS"].append((n,m)); print(f"  [PASS] {n}: {m}")
def W(n,m): R["WARN"].append((n,m)); print(f"  [WARN] {n}: {m}")
def F(n,m): R["FAIL"].append((n,m)); print(f"  [FAIL] {n}: {m}")
def A(n,m): R["ANOM"].append((n,m)); print(f"  [ANOM] {n}: {m}")

def find_profile():
    pd = Path(__file__).parent / "profiles"
    dirs = [d for d in pd.iterdir() if d.is_dir() and len(d.name)==32] if pd.exists() else []
    return max(dirs, key=lambda d: d.stat().st_mtime) if dirs else None

def run(pp):
    check_structure(pp)
    check_metrics(pp)
    check_history(pp)
    check_cookies(pp)
    check_storage(pp)
    check_formhistory(pp)
    check_session(pp)
    check_seon()
    check_riskified(pp)
    check_adyen(pp)
    summary()

def check_structure(pp):
    print("\n[1/10] PROFILE STRUCTURE")
    print("-"*50)
    for f in STANDARD_FILES:
        P("File",f) if (pp/f).exists() else A("Missing",f)
    for f in FORBIDDEN_FILES:
        F("Artifact",f+" FOUND") if (pp/f).exists() else P("Clean",f+" absent")
    # Check cache2
    if (pp/"cache2"/"entries").exists():
        P("Cache","cache2/entries directory present")
    else:
        A("Cache","cache2/entries missing")

def check_metrics(pp):
    print("\n[2/10] SIZE & AGE")
    print("-"*50)
    total=sum(f.stat().st_size for f in pp.rglob("*") if f.is_file())
    mb=total/(1024*1024)
    P("Size",f"{mb:.0f}MB") if mb>=RISKIFIED_MIN_STORAGE else (W("Size",f"{mb:.0f}MB < {RISKIFIED_MIN_STORAGE}") if mb>=100 else F("Size",f"{mb:.0f}MB too small"))
    tj=pp/"times.json"
    if tj.exists():
        d=json.loads(tj.read_text()); cr=d.get("created",0)
        if cr:
            age=(datetime.now()-datetime.fromtimestamp(cr/1000)).days
            P("Age",f"{age}d") if age>=RISKIFIED_MIN_AGE else F("Age",f"{age}d < {RISKIFIED_MIN_AGE}")
    pf=pp/"prefs.js"
    if pf.exists():
        m=re.search(r'sessionCount.*?(\d+)',pf.read_text())
        if m:
            sc=int(m.group(1))
            P("Sessions",f"{sc}") if sc>50 else W("Sessions",f"{sc} low")

def check_history(pp):
    print("\n[3/10] HISTORY FORENSICS")
    print("-"*50)
    db=pp/"places.sqlite"
    if not db.exists(): F("History","missing"); return
    conn=sqlite3.connect(db); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM moz_places"); t=c.fetchone()[0]
    P("Count",f"{t}") if t>1000 else (W("Count",f"{t}") if t>500 else F("Count",f"{t} too few"))
    # Visit type mix
    c.execute("SELECT visit_type,COUNT(*) FROM moz_historyvisits GROUP BY visit_type")
    vd=dict(c.fetchall()); tv=sum(vd.values())
    if tv>0:
        lp=vd.get(1,0)/tv*100; tp=vd.get(2,0)/tv*100; bp=vd.get(3,0)/tv*100
        A("Visit Types",f"Link={lp:.0f}% too uniform") if lp>95 else P("Visit Types",f"Link={lp:.0f}% Typed={tp:.0f}% Bkmk={bp:.0f}%")
    # Temporal
    c.execute("SELECT visit_date FROM moz_historyvisits ORDER BY visit_date")
    dates=[r[0] for r in c.fetchall()]
    if dates:
        ds=set(datetime.fromtimestamp(d/1e6).date() for d in dates)
        span=(datetime.fromtimestamp(dates[-1]/1e6)-datetime.fromtimestamp(dates[0]/1e6)).days
        cov=len(ds)/max(span,1)*100 if span>0 else 0
        P("Coverage",f"{len(ds)}/{span}d ({cov:.0f}%)") if cov>40 else W("Coverage",f"{cov:.0f}% sparse")
        # Circadian
        hd=Counter(datetime.fromtimestamp(d/1e6).hour for d in dates)
        np=sum(hd.get(h,0) for h in [0,1,2,3,4])/max(len(dates),1)*100
        P("Circadian",f"Night {np:.1f}%") if np<15 else A("Circadian",f"Night {np:.1f}% too high")
    # Bookmarks
    c.execute("SELECT COUNT(*) FROM moz_bookmarks WHERE type=1"); bk=c.fetchone()[0]
    P("Bookmarks",f"{bk}") if bk>0 else A("Bookmarks","none")
    # Downloads
    c.execute("SELECT COUNT(*) FROM moz_historyvisits WHERE visit_type=7"); dl=c.fetchone()[0]
    P("Downloads",f"{dl}") if dl>0 else A("Downloads","none")
    # URL diversity — check if path is just "/" (true root-only)
    c.execute("SELECT url FROM moz_places LIMIT 500"); urls=[r[0] for r in c.fetchall()]
    ro=0
    for u in urls:
        try:
            # Extract path after domain: https://www.domain.com/path
            after_proto=u.split("://",1)[1] if "://" in u else u
            path_start=after_proto.find("/")
            path=after_proto[path_start:] if path_start>=0 else "/"
            if path=="/" or path=="": ro+=1
        except: ro+=1
    ro_pct=ro/max(len(urls),1)*100
    P("URL Diversity",f"Root-only {ro_pct:.0f}%") if ro_pct<60 else A("URL Diversity",f"Root-only {ro_pct:.0f}% too high")
    # Tables
    for tbl in ["moz_meta","moz_origins","moz_inputhistory"]:
        try:
            c.execute(f"SELECT COUNT(*) FROM {tbl}"); n=c.fetchone()[0]
            P(tbl,f"{n} entries") if n>0 else A(tbl,"empty")
        except: A(tbl,"table missing")
    # url_hash check (should not all be 0)
    c.execute("SELECT COUNT(*) FROM moz_places WHERE url_hash=0 AND hidden=0"); zh=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM moz_places WHERE hidden=0"); th=c.fetchone()[0]
    if th>0:
        zp=zh/th*100
        P("url_hash",f"{zp:.0f}% zero") if zp<5 else A("url_hash",f"{zp:.0f}% zero — all hashes missing")
    # frecency check (should not all be -1)
    c.execute("SELECT COUNT(*) FROM moz_places WHERE frecency=-1 AND visit_count>0"); fh=c.fetchone()[0]
    P("frecency","computed") if fh==0 else A("frecency",f"{fh} visited places have frecency=-1")
    # from_visit chain check (should not all be 0)
    c.execute("SELECT COUNT(*) FROM moz_historyvisits WHERE from_visit>0"); fv=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM moz_historyvisits"); tv2=c.fetchone()[0]
    if tv2>0:
        fvp=fv/tv2*100
        P("from_visit",f"{fvp:.0f}% have referrers") if fvp>10 else A("from_visit",f"{fvp:.0f}% — no referral chains")
    # URL dedup check (same URL should not have multiple place rows)
    c.execute("SELECT url,COUNT(*) as cnt FROM moz_places GROUP BY url HAVING cnt>1")
    dupes=c.fetchall()
    P("URL Dedup","no duplicate URLs") if len(dupes)==0 else A("URL Dedup",f"{len(dupes)} URLs with duplicate place rows")
    # GUID format check (should be base64url, not hex-only)
    c.execute("SELECT guid FROM moz_places WHERE guid IS NOT NULL LIMIT 20")
    guids=[r[0] for r in c.fetchall()]
    hex_only=sum(1 for g in guids if g and all(c in '0123456789abcdef' for c in g))
    P("GUID Format","base64url") if hex_only<len(guids)*0.3 else A("GUID Format",f"{hex_only}/{len(guids)} hex-only GUIDs — detectable")
    conn.close()

def check_cookies(pp):
    print("\n[4/10] COOKIE FORENSICS")
    print("-"*50)
    db=pp/"cookies.sqlite"
    if not db.exists(): F("Cookies","missing"); return
    conn=sqlite3.connect(db); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM moz_cookies"); t=c.fetchone()[0]
    P("Count",f"{t}") if t>=50 else (W("Count",f"{t}") if t>=20 else F("Count",f"{t}"))
    # Spread
    c.execute("SELECT creationTime FROM moz_cookies ORDER BY creationTime"); ts=[r[0] for r in c.fetchall()]
    if len(ts)>=2:
        sp=(datetime.fromtimestamp(ts[-1]/1e6)-datetime.fromtimestamp(ts[0]/1e6)).days
        P("Age Spread",f"{sp} days") if sp>30 else A("Age Spread",f"{sp}d — batch creation")
    # Trust anchors
    c.execute("SELECT DISTINCT host FROM moz_cookies"); hosts=set(r[0] for r in c.fetchall())
    for ta in [".google.com",".youtube.com",".facebook.com",".github.com"]:
        P("Trust",ta) if ta in hosts else W("Trust",f"{ta} missing")
    for ch in [".stripe.com",".paypal.com",".adyen.com"]:
        P("Commerce",ch) if ch in hosts else W("Commerce",f"{ch} missing")
    P("Target","eneba.com present") if ".eneba.com" in hosts else W("Target","eneba missing")
    # Cookie expiry variance check
    c.execute("SELECT DISTINCT expiry FROM moz_cookies"); exps=[r[0] for r in c.fetchall()]
    P("Expiry Variance",f"{len(exps)} unique expiry values") if len(exps)>5 else A("Expiry Variance",f"Only {len(exps)} unique — batch creation")
    # Stripe mid age
    c.execute("SELECT value FROM moz_cookies WHERE name='__stripe_mid'"); row=c.fetchone()
    if row:
        parts=row[0].split(".")
        if len(parts)>=2:
            try:
                age=(datetime.now().timestamp()-int(parts[1]))/86400
                P("Stripe MID",f"{age:.0f}d old") if age>30 else W("Stripe MID",f"{age:.0f}d — too fresh")
            except: pass
    conn.close()

def check_storage(pp):
    print("\n[5/10] LOCALSTORAGE ANALYSIS")
    print("-"*50)
    sd=pp/"storage"/"default"
    if not sd.exists(): F("Storage","storage/default missing"); return
    domains=[d.name for d in sd.iterdir() if d.is_dir()]
    P("Domains",f"{len(domains)} domain dirs")
    # Check key patterns
    synthetic=0; total_keys=0
    for dom_dir in sd.iterdir():
        ls_db=dom_dir/"ls"/"data.sqlite"
        if not ls_db.exists(): continue
        conn=sqlite3.connect(ls_db); c=conn.cursor()
        try:
            c.execute("SELECT key FROM data"); keys=[r[0] for r in c.fetchall()]
            total_keys+=len(keys)
            for k in keys:
                if re.match(r'^_c_\d+$',k) or re.match(r'^pad_\d+$',k) or re.match(r'^cache_\d+$',k):
                    synthetic+=1
        except: pass
        conn.close()
    P("Total Keys",f"{total_keys}")
    if synthetic>0:
        A("Synthetic Keys",f"{synthetic} obvious padding keys (_c_*, pad_*, cache_*)")
    else:
        P("Key Quality","No obvious synthetic padding patterns")
    # Check localStorage schema correctness
    schema_bad=0
    for dom_dir in sd.iterdir():
        ls_db=dom_dir/"ls"/"data.sqlite"
        if not ls_db.exists(): continue
        conn2=sqlite3.connect(ls_db); c2=conn2.cursor()
        try:
            c2.execute("PRAGMA table_info(data)"); cols=[r[1] for r in c2.fetchall()]
            if "originKey" in cols or "originAttributes" in cols:
                schema_bad+=1
        except: pass
        conn2.close()
    P("LS Schema","correct Firefox schema") if schema_bad==0 else A("LS Schema",f"{schema_bad} DBs have non-Firefox columns (originKey/originAttributes)")
    # Check IDB
    idb_count=0
    for dom_dir in sd.iterdir():
        idb_dir=dom_dir/"idb"
        if idb_dir.exists():
            idb_count+=len(list(idb_dir.glob("*.sqlite")))
    P("IndexedDB",f"{idb_count} databases") if idb_count>0 else A("IndexedDB","none")

def check_formhistory(pp):
    print("\n[6/10] FORM HISTORY")
    print("-"*50)
    db=pp/"formhistory.sqlite"
    if not db.exists(): A("FormHistory","missing"); return
    conn=sqlite3.connect(db); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM moz_formhistory"); t=c.fetchone()[0]
    P("Count",f"{t}") if t>20 else (W("Count",f"{t}") if t>5 else A("Count",f"{t} too few"))
    # Diversity check
    c.execute("SELECT DISTINCT fieldname FROM moz_formhistory"); fields=[r[0] for r in c.fetchall()]
    persona_only=all(f in ["name","email","tel","address-line1","address-level2","address-level1",
        "postal-code","country","given-name","family-name","cc-name"] for f in fields)
    if persona_only and len(fields)>0:
        A("Diversity","Only persona fields — real users search and fill random forms")
    elif len(fields)>8:
        P("Diversity",f"{len(fields)} field types (persona + searches + misc)")
    else:
        W("Diversity",f"Only {len(fields)} field types")
    # Search history
    c.execute("SELECT COUNT(*) FROM moz_formhistory WHERE fieldname='searchbar-history'"); sh=c.fetchone()[0]
    P("Searches",f"{sh} search entries") if sh>0 else A("Searches","No search bar history")
    conn.close()

def check_session(pp):
    print("\n[7/10] SESSION STORE")
    print("-"*50)
    sf=pp/"sessionstore.js"
    if not sf.exists(): A("Session","sessionstore.js missing"); return
    s=json.loads(sf.read_bytes())
    # Open tabs
    wins=s.get("windows",[])
    tabs=sum(len(w.get("tabs",[])) for w in wins)
    P("Open Tabs",f"{tabs}") if tabs>1 else A("Open Tabs","Only 1 tab — suspicious")
    # Closed tabs
    ct=sum(len(w.get("_closedTabs",[])) for w in wins)
    P("Closed Tabs",f"{ct}") if ct>0 else A("Closed Tabs","None — real users close tabs")
    # Closed windows
    cw=len(s.get("_closedWindows",[]))
    P("Closed Windows",f"{cw}") if cw>0 else W("Closed Windows","None")
    # Crashes
    crashes=s.get("session",{}).get("recentCrashes",0)
    P("Crashes",f"{crashes}") if crashes<=5 else W("Crashes",f"{crashes} too many")
    # Session age
    st=s.get("session",{}).get("startTime",0)
    lu=s.get("session",{}).get("lastUpdate",0)
    if st and lu:
        span=(lu-st)/86400000
        P("Session Span",f"{span:.0f} days") if span>30 else W("Session Span",f"{span:.0f}d short")

def check_seon():
    print("\n[8/10] SEON SCORING SIMULATION")
    print("-"*50)
    score=0; flags=[]
    # Email
    domain=PERSONA_EMAIL.split("@")[-1]
    if domain in DISPOSABLE_EMAILS:
        score+=80; flags.append(f"disposable_email: +80")
    else:
        P("Email",f"{domain} — not disposable")
    # Phone
    clean=re.sub(r'[^0-9]',''  ,PERSONA_PHONE)
    if len(clean)<10:
        score+=10; flags.append("short_phone: +10")
    voip=["800","888","877","866","855"]
    if len(clean)>=10 and clean[-10:-7] in voip:
        score+=10; flags.append("voip_phone: +10")
    # Browser spoof (our profile claims Mac but we're on Windows)
    score+=8; flags.append("browser_spoofing: +8 (Mac UA on Windows host)")
    # Social profiles check
    score+=10; flags.append("email_no_social_profiles: +10 (gmail but no verified social)")
    P("SEON Score",f"{score}/{SEON_THRESHOLD}") if score<SEON_THRESHOLD else W("SEON Score",f"{score}/{SEON_THRESHOLD} — AT RISK")
    for fl in flags: print(f"    -> {fl}")

def check_riskified(pp):
    print("\n[9/10] RISKIFIED DETECTION VECTORS (Eneba)")
    print("-"*50)
    # Shadow linking: clipboard paste detection
    W("Shadow Linking","Riskified detects card# paste from clipboard — must TYPE manually")
    # Cross-merchant sharing
    W("Cross-Merchant","Riskified shares data across merchants — use fresh cards only")
    # Commerce history
    db=pp/"cookies.sqlite"
    if db.exists():
        conn=sqlite3.connect(db); c=conn.cursor()
        c.execute("SELECT COUNT(*) FROM moz_cookies WHERE host LIKE '%.stripe.com' OR host LIKE '%.paypal.com' OR host LIKE '%.adyen.com'")
        cm=c.fetchone()[0]; conn.close()
        P("Commerce History",f"{cm} commerce cookies") if cm>0 else A("Commerce History","No commerce cookies — Riskified flags first-time buyers")
    # Behavioral biometrics
    W("Biometrics","Riskified analyzes typing/mouse — Ghost Motor must run continuously")
    # International billing
    if CARD_COUNTRY!="US":
        W("Billing Region",f"International card ({CARD_COUNTRY}) — higher scrutiny on US-facing target")

def check_adyen(pp):
    print("\n[10/10] ADYEN PAYMENT GATEWAY")
    print("-"*50)
    # 3DS
    P("3DS Rate",f"Eneba/Adyen 3DS rate: {15}% for non-EU cards")
    # EU PSD2
    if CARD_COUNTRY in ["DE","FR","IT","ES","NL","BE","AT","SE","NO","DK","FI","PL","LK"]:
        if CARD_COUNTRY in ["DE","FR","IT","ES","NL","BE","AT","SE","NO","DK","FI","PL"]:
            W("PSD2","EU card — Strong Customer Authentication required, 3DS likely mandatory")
        else:
            P("PSD2",f"{CARD_COUNTRY} not EU — PSD2 SCA not enforced")
    # AVS
    avs_countries=["US","CA","GB"]
    if CARD_COUNTRY in avs_countries:
        W("AVS",f"{CARD_COUNTRY} card requires exact AVS match")
    else:
        P("AVS",f"{CARD_COUNTRY} is non-AVS country — AVS check skipped (advantage)")
    # Device fingerprint
    db=pp/"cookies.sqlite"
    if db.exists():
        conn=sqlite3.connect(db); c=conn.cursor()
        c.execute("SELECT COUNT(*) FROM moz_cookies WHERE host LIKE '%.adyen.com'")
        ac=c.fetchone()[0]; conn.close()
        P("Adyen FP","Adyen device fingerprint cookie present") if ac>0 else W("Adyen FP","No Adyen cookie — fresh device")

def summary():
    print("\n" + "="*60)
    print("  DETECTION ANALYSIS SUMMARY")
    print("="*60)
    print(f"  PASS:      {len(R['PASS'])}")
    print(f"  WARNINGS:  {len(R['WARN'])}")
    print(f"  ANOMALIES: {len(R['ANOM'])}")
    print(f"  FAILURES:  {len(R['FAIL'])}")
    print("-"*60)
    if R["FAIL"]:
        print("\n  CRITICAL FAILURES (will cause decline):")
        for n,m in R["FAIL"]: print(f"    [!!] {n}: {m}")
    if R["ANOM"]:
        print("\n  ANOMALIES (detectable by forensic analysis):")
        for n,m in R["ANOM"]: print(f"    [!!] {n}: {m}")
    if R["WARN"]:
        print("\n  WARNINGS (risk factors):")
        for n,m in R["WARN"]: print(f"    [..] {n}: {m}")
    # Verdict
    print("\n" + "="*60)
    if R["FAIL"]:
        print("  VERDICT: DECLINE LIKELY — fix critical failures first")
    elif len(R["ANOM"])>3:
        print("  VERDICT: HIGH RISK — multiple anomalies detectable")
    elif R["ANOM"]:
        print(f"  VERDICT: MODERATE RISK — {len(R['ANOM'])} anomalies remain")
    else:
        print("  VERDICT: LOW RISK — profile passes all detection vectors")
    print("="*60)

if __name__=="__main__":
    pp=find_profile()
    if pp:
        print(f"Profile: {pp.name}")
        run(pp)
    else:
        print("No profile found")
