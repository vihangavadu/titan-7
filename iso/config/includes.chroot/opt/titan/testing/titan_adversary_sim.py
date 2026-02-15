#!/usr/bin/env python3
"""
TITAN V7.0 SINGULARITY — Top-Tier Adversary Detection Simulation
Authority: Dva.12 | Version: 7.0

Simulates 5 real-world antifraud detection algorithms to test Titan
sessions BEFORE going live. Each algorithm models a top-tier vendor:

  1. GraphLinkAnalyzer          — Entity graph clustering  (Riskified/Sift)
  2. FingerprintAnomalyScorer   — Statistical anomaly       (ThreatMetrix/LexisNexis)
  3. BiometricTrajectoryAnalyzer— Behavioral biometrics     (BioCatch/Forter)
  4. ProfileConsistencyScorer   — Identity consistency      (Forter/Signifyd)
  5. MultiLayerRiskFusion       — Weighted ensemble         (Stripe Radar/Adyen)

Usage:
    from titan_adversary_sim import AdversarySimulator, TitanSession
    sim = AdversarySimulator()
    session = TitanSession(ip_type='residential', ...)
    report = sim.run_all(session)
    AdversarySimulator.print_report(report)

Run standalone demo:  python titan_adversary_sim.py
"""
import hashlib, math, statistics, time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple
import logging
logger = logging.getLogger(__name__)

class Verdict(Enum):
    PASS="PASS"; REVIEW="REVIEW"; BLOCK="BLOCK"

@dataclass
class Signal:
    name:str; weight:float; score:float; detail:str; titan_defense:str=""

@dataclass
class AlgoResult:
    algorithm:str; vendor:str; verdict:Verdict; risk:float; detect_prob:float
    signals:List[Signal]=field(default_factory=list); ms:float=0.0

@dataclass
class MouseEvent:
    x:float; y:float; t:float

@dataclass
class KeyEvent:
    key:str; down:float; up:float

@dataclass
class TitanSession:
    session_id:str=""; operator_id:str=""; email:str=""; phone:str=""
    user_agent:str=""; platform:str="Win32"
    screen_w:int=1920; screen_h:int=1080; hw_conc:int=8; dev_mem:float=8.0
    canvas_hash:str=""; webgl_vendor:str=""; webgl_renderer:str=""
    audio_hash:str=""; timezone:str="America/New_York"; language:str="en-US"
    ip_address:str=""; ip_type:str="residential"; ip_country:str="US"
    ip_city:str="New York"; ip_rep:float=85.0; tcp_ttl:int=128
    tcp_window:int=65535; tcp_os:str="Windows"; tls_ja3:str=""
    profile_age:int=90; history_count:int=5000; cookie_count:int=800
    ls_domains:int=120; profile_mb:float=450.0; has_purchases:bool=True
    mouse:List[MouseEvent]=field(default_factory=list)
    keys:List[KeyEvent]=field(default_factory=list)
    scrolls:List[float]=field(default_factory=list)
    session_secs:float=300.0; pages:int=6; form_secs:float=45.0
    referrers:List[str]=field(default_factory=list)
    card_bin:str=""; card_country:str="US"; avs:str="Y"; cvv:str="M"
    billing_country:str="US"; billing_city:str="New York"
    amount:float=150.0; merchant_cat:str="digital_goods"

def _v(s): return Verdict.PASS if s<35 else Verdict.REVIEW if s<70 else Verdict.BLOCK
def _ent(d,b=20):
    if len(d)<2: return 0.0
    mn,mx=min(d),max(d)
    if mx==mn: return 0.0
    w=(mx-mn)/b; c=[0]*b
    for v in d: c[min(int((v-mn)/w),b-1)]+=1
    t=len(d); e=sum(-p/t*math.log2(p/t) for p in c if p>0)
    return e/math.log2(b)


# =====================================================================
# ALGO 1: Graph-Based Entity Link Analysis  (Riskified / Sift)
# =====================================================================
class GraphLinkAnalyzer:
    """Builds entity graph across sessions. Detects IP fan-out,
    device FP reuse, BIN clustering, email-domain concentration."""

    def __init__(self):
        self.history: List[TitanSession] = []

    def ingest(self, s: TitanSession):
        self.history.append(s)

    def analyze(self, cur: TitanSession) -> AlgoResult:
        t0 = time.time()
        sigs, score = [], 0.0
        pool = self.history + [cur]
        ip_m, dev_m, bin_m, dom_m = (defaultdict(set) for _ in range(4))
        for s in pool:
            uid = s.operator_id or s.session_id or str(id(s))
            if s.ip_address:
                ip_m[s.ip_address].add(uid)
            dfp = hashlib.md5(
                f"{s.user_agent}:{s.canvas_hash}:{s.webgl_renderer}:{s.audio_hash}".encode()
            ).hexdigest()[:12]
            dev_m[dfp].add(uid)
            if s.card_bin:
                bin_m[s.card_bin].add(uid)
            if s.email and "@" in s.email:
                dom_m[s.email.split("@")[1]].add(uid)

        def _fan(m, thresh, name, w, mult, cap, defense):
            nonlocal score
            fan = max((len(v) for v in m.values()), default=1)
            if fan > thresh:
                p = min(cap, fan * mult)
                score += p
                sigs.append(Signal(name, w, p,
                    f"{name}: {fan} identities share attribute", defense))

        _fan(ip_m, 3, "ip_fanout", .30, 8, 40,
             "Lucid VPN unique residential exit per session")
        _fan(dev_m, 2, "device_reuse", .25, 7, 35,
             "Camoufox+FingerprintInjector unique per profile")
        _fan(bin_m, 2, "bin_cluster", .20, 10, 30,
             "Diversify BINs across sessions")
        _fan(dom_m, 3, "email_domain", .15, 5, 25,
             "Use diverse email providers")

        n = len(pool)
        if n > 5:
            p = min(20, n * 3)
            score += p
            sigs.append(Signal("temporal_burst", .10, p,
                f"{n} sessions in window", "Space operations across time"))

        score = min(100, score)
        return AlgoResult("GraphLinkAnalyzer", "Riskified/Sift",
            _v(score), score, min(1.0, score/100), sigs, (time.time()-t0)*1000)


# =====================================================================
# ALGO 2: Fingerprint Anomaly Detection  (ThreatMetrix / LexisNexis)
# =====================================================================
class FingerprintAnomalyScorer:
    """RMS z-score across device/network features vs population model.
    Catches OS mismatches, datacenter IPs, bot TLS, outlier hardware."""

    POP = {"screen_w":(1920,350), "screen_h":(1080,200), "hw_conc":(8,4),
           "dev_mem":(8,4), "tcp_ttl":(128,15), "tcp_window":(65535,10000),
           "ip_rep":(75,15)}
    PLAT = {"Win32","MacIntel","Linux x86_64","Linux aarch64"}
    US_TZ = {"America/New_York","America/Chicago","America/Denver",
             "America/Los_Angeles","America/Phoenix","America/Anchorage",
             "Pacific/Honolulu"}

    def analyze(self, s: TitanSession) -> AlgoResult:
        t0 = time.time()
        sigs, zs = [], []
        feats = {"screen_w":s.screen_w, "screen_h":s.screen_h,
                 "hw_conc":s.hw_conc, "dev_mem":s.dev_mem,
                 "tcp_ttl":s.tcp_ttl, "tcp_window":s.tcp_window,
                 "ip_rep":s.ip_rep}
        for fn, val in feats.items():
            mu, sg = self.POP[fn]
            z = abs(val-mu)/sg if sg>0 else 0
            zs.append(z)
            if z > 2.5:
                sigs.append(Signal(f"outlier_{fn}", .12, min(30,z*10),
                    f"{fn}={val} is {z:.1f}σ from mean({mu})",
                    f"Hardware Shield normalizes {fn}"))

        if s.platform not in self.PLAT:
            zs.append(3.0)
            sigs.append(Signal("unknown_platform", .10, 25,
                f"Platform '{s.platform}' unknown", "Camoufox standard platform"))

        ua_os = "Windows" if "Windows" in s.user_agent else \
                "Mac" if "Mac" in s.user_agent else \
                "Linux" if "Linux" in s.user_agent else ""
        if s.tcp_os and ua_os and s.tcp_os.lower() not in ua_os.lower() \
                and ua_os.lower() not in s.tcp_os.lower():
            zs.append(4.0)
            sigs.append(Signal("os_mismatch", .20, 35,
                f"TCP OS='{s.tcp_os}' vs UA='{ua_os}'",
                "eBPF Network Shield rewrites TCP stack"))

        if s.ip_country == "US" and s.timezone not in self.US_TZ:
            zs.append(2.5)
            sigs.append(Signal("tz_geo_mismatch", .12, 25,
                f"TZ='{s.timezone}' unusual for US",
                "TimezoneEnforcer aligns TZ with proxy geo"))

        if s.ip_type == "datacenter":
            zs.append(5.0)
            sigs.append(Signal("datacenter_ip", .20, 45,
                "Datacenter IP — high risk",
                "Lucid VPN residential Tailscale exit"))
        elif s.ip_type == "vpn":
            zs.append(3.0)
            sigs.append(Signal("vpn_detected", .15, 30,
                "Known VPN range", "VLESS+Reality undetectable by DPI"))

        BOT_JA3 = {"e7d705a3286e19ea42f587b344ee6865",
                    "3b5074b1b5d032e5620f69f9f700ff0e"}
        if s.tls_ja3 in BOT_JA3:
            zs.append(6.0)
            sigs.append(Signal("bot_tls", .20, 50,
                "TLS JA3 matches known bot", "Camoufox native browser TLS"))

        rms = math.sqrt(sum(z**2 for z in zs)/max(len(zs),1)) if zs else 0
        risk = min(100, rms*20)
        return AlgoResult("FingerprintAnomalyScorer", "ThreatMetrix/LexisNexis",
            _v(risk), risk, min(1.0, risk/100), sigs, (time.time()-t0)*1000)


# =====================================================================
# ALGO 3: Behavioral Biometrics Trajectory  (BioCatch / Forter)
# =====================================================================
class BiometricTrajectoryAnalyzer:
    """Statistical analysis of mouse/keyboard/scroll biometrics.
    Checks velocity entropy, CV, straightness, jerk, hold-time variance,
    inter-key intervals, scroll regularity, and session cadence."""

    def analyze(self, s: TitanSession) -> AlgoResult:
        t0 = time.time()
        sigs, subs = [], []
        if len(s.mouse) > 10:
            ms, mg = self._mouse(s.mouse)
            subs.append(ms); sigs.extend(mg)
        else:
            subs.append(30)
            sigs.append(Signal("low_mouse", .20, 30,
                f"Only {len(s.mouse)} mouse events", "Ghost Motor continuous movement"))
        if len(s.keys) > 5:
            ks, kg = self._keys(s.keys)
            subs.append(ks); sigs.extend(kg)
        else:
            subs.append(15)
        if len(s.scrolls) > 3:
            ss, sg2 = self._scroll(s.scrolls)
            subs.append(ss); sigs.extend(sg2)
        else:
            subs.append(10)
        sl, slg = self._session(s)
        subs.append(sl); sigs.extend(slg)
        risk = min(100, statistics.mean(subs)) if subs else 50
        return AlgoResult("BiometricTrajectoryAnalyzer", "BioCatch/Forter",
            _v(risk), risk, min(1.0, risk/100), sigs, (time.time()-t0)*1000)

    def _mouse(self, evts: List[MouseEvent]) -> Tuple[float, List[Signal]]:
        sigs, score = [], 0.0
        vels = []
        for i in range(1, len(evts)):
            dt = evts[i].t - evts[i-1].t
            if dt <= 0: continue
            dx = evts[i].x - evts[i-1].x
            dy = evts[i].y - evts[i-1].y
            vels.append(math.sqrt(dx*dx + dy*dy) / dt)
        if not vels:
            return 40.0, [Signal("no_velocity", .20, 40, "No velocity data", "")]
        # Velocity entropy
        ve = _ent(vels)
        if ve < 0.4:
            p = (0.4 - ve) * 80
            score += p
            sigs.append(Signal("low_vel_entropy", .20, p,
                f"Velocity entropy={ve:.3f}<0.4 — too uniform",
                "Ghost Motor DMTG fractal noise"))
        # Velocity CV
        vm = statistics.mean(vels)
        vs = statistics.stdev(vels) if len(vels)>1 else 0
        cv = vs/vm if vm>0 else 0
        if cv < 0.3:
            p = (0.3 - cv) * 60
            score += p
            sigs.append(Signal("low_vel_cv", .15, p,
                f"Velocity CV={cv:.3f}<0.3 — too consistent",
                "Ghost Motor varies velocity per persona"))
        # Straightness
        tp = sum(math.sqrt((evts[i].x-evts[i-1].x)**2 + (evts[i].y-evts[i-1].y)**2)
                 for i in range(1, len(evts)))
        disp = math.sqrt((evts[-1].x-evts[0].x)**2 + (evts[-1].y-evts[0].y)**2)
        sr = disp/tp if tp > 0 else 1.0
        if sr > 0.92:
            p = min(35, (sr - 0.92) * 400)
            score += p
            sigs.append(Signal("straight_path", .15, p,
                f"Straightness={sr:.3f}>0.92 — bot-like",
                "Ghost Motor Bezier curves with jitter"))
        # Jerk analysis
        if len(vels) > 3:
            accels = [abs(vels[i]-vels[i-1]) for i in range(1, len(vels))]
            am = statistics.mean(accels)
            jcv = statistics.stdev(accels)/am if am > 0 else 0
            if jcv < 0.25:
                p = (0.25 - jcv) * 50
                score += p
                sigs.append(Signal("smooth_accel", .10, p,
                    f"Jerk CV={jcv:.3f}<0.25 — too smooth",
                    "Ghost Motor micro-tremor noise"))
        return min(100, score), sigs

    def _keys(self, evts: List[KeyEvent]) -> Tuple[float, List[Signal]]:
        sigs, score = [], 0.0
        holds = [e.up - e.down for e in evts if e.up > e.down]
        if not holds: return 20.0, []
        if len(holds) > 1:
            hstd = statistics.stdev(holds)
            if hstd < 0.015:
                p = min(30, (0.015 - hstd) * 2000)
                score += p
                sigs.append(Signal("uniform_hold", .15, p,
                    f"Hold σ={hstd:.4f}s — too uniform",
                    "Ghost Motor per-key hold variance"))
        intervals = [evts[i].down - evts[i-1].up
                     for i in range(1, len(evts)) if evts[i].down > evts[i-1].up]
        if len(intervals) > 2:
            iv = statistics.stdev(intervals)
            if iv < 0.02:
                p = min(25, (0.02 - iv) * 1500)
                score += p
                sigs.append(Signal("uniform_interval", .10, p,
                    f"Inter-key σ={iv:.4f}s — bot cadence",
                    "Ghost Motor natural typing rhythm"))
        if intervals:
            fastest = min(intervals)
            if fastest < 0.025:
                score += 25
                sigs.append(Signal("superhuman_typing", .15, 25,
                    f"Fastest={fastest*1000:.0f}ms — superhuman",
                    "Ghost Motor 40ms minimum"))
        return min(100, score), sigs

    def _scroll(self, evts: List[float]) -> Tuple[float, List[Signal]]:
        sigs, score = [], 0.0
        se = _ent(evts)
        if se < 0.3:
            p = (0.3 - se) * 60
            score += p
            sigs.append(Signal("uniform_scroll", .10, p,
                f"Scroll entropy={se:.3f}<0.3 — too regular",
                "Ghost Motor varies scroll distance"))
        return min(100, score), sigs

    def _session(self, s: TitanSession) -> Tuple[float, List[Signal]]:
        sigs, score = [], 0.0
        if s.session_secs < 30:
            score += 35
            sigs.append(Signal("short_session", .15, 35,
                f"Session={s.session_secs:.0f}s — too fast",
                "Ghost Motor enforces dwell time"))
        elif s.session_secs < 60:
            score += 15
        if s.form_secs < 8:
            score += 25
            sigs.append(Signal("fast_form", .15, 25,
                f"Form={s.form_secs:.0f}s — inhuman",
                "Ghost Motor 40-80 WPM with pauses"))
        if s.pages < 2:
            score += 20
            sigs.append(Signal("direct_checkout", .10, 20,
                "No browsing before checkout",
                "ReferrerWarmup organic navigation"))
        return min(100, score), sigs


# =====================================================================
# ALGO 4: Profile & History Consistency  (Forter / Signifyd)
# =====================================================================
class ProfileConsistencyScorer:
    """Cross-validates profile depth, age-activity ratio, geo consistency,
    AVS/CVV, referrer chain, and trust-token presence."""

    def analyze(self, s: TitanSession) -> AlgoResult:
        t0 = time.time()
        sigs, score = [], 0.0
        depth = min(100, (
            min(s.history_count / 50, 30) +
            min(s.cookie_count / 10, 20) +
            min(s.ls_domains / 5, 15) +
            min(s.profile_mb / 30, 15) +
            (10 if s.has_purchases else 0) +
            (10 if len(s.referrers) >= 2 else 0)
        ))
        if depth < 40:
            p = (40 - depth) * 0.6
            score += p
            sigs.append(Signal("shallow_profile", .20, p,
                f"Depth={depth:.0f}/100 — thin",
                "Genesis 500MB+ Pareto history"))
        if s.profile_age > 0:
            expected = s.profile_age * 50
            ratio = s.history_count / max(expected, 1)
            if ratio > 2.0:
                p = min(25, (ratio - 2.0) * 15)
                score += p
                sigs.append(Signal("overstuffed", .15, p,
                    f"History/age={ratio:.1f}x — dense",
                    "Genesis calibrates to age"))
            elif ratio < 0.1:
                p = min(30, (0.1 - ratio) * 200)
                score += p
                sigs.append(Signal("sparse_profile", .15, p,
                    f"History/age={ratio:.2f}x — sparse",
                    "Genesis populates volumes"))
        if s.ip_country and s.billing_country and s.ip_country != s.billing_country:
            score += 30
            sigs.append(Signal("ip_billing_geo", .20, 30,
                f"IP={s.ip_country} vs billing={s.billing_country}",
                "Match proxy to billing country"))
        if s.card_country and s.ip_country and s.card_country != s.ip_country:
            score += 25
            sigs.append(Signal("card_ip_geo", .15, 25,
                f"Card={s.card_country} vs IP={s.ip_country}",
                "Match card issuer to proxy"))
        if s.avs not in ("Y", "X", "D", "F", "M"):
            score += 20
            sigs.append(Signal("avs_fail", .15, 20,
                f"AVS='{s.avs}' — not full match",
                "Use verified billing address"))
        if s.cvv not in ("M", "P"):
            score += 15
            sigs.append(Signal("cvv_fail", .10, 15,
                f"CVV='{s.cvv}' — not matched",
                "Always use correct CVV"))
        if not s.referrers:
            score += 15
            sigs.append(Signal("no_referrer", .10, 15,
                "Direct access — no referrer",
                "ReferrerWarmup organic path"))
        if s.amount > 500:
            p = min(20, (s.amount - 500) / 50)
            score += p
            sigs.append(Signal("high_amount", .10, p,
                f"${s.amount:.0f} — elevated tier",
                "Start with lower amounts"))
        score = min(100, score)
        return AlgoResult("ProfileConsistencyScorer", "Forter/Signifyd",
            _v(score), score, min(1.0, score/100), sigs, (time.time()-t0)*1000)


# =====================================================================
# ALGO 5: Multi-Layer Risk Fusion  (Stripe Radar / Adyen Risk)
# =====================================================================
class MultiLayerRiskFusion:
    """Weighted ensemble of all 4 algos + payment signals.
    Simulates how Stripe Radar / Adyen fuse risk dimensions."""

    W = {"GraphLinkAnalyzer": .20, "FingerprintAnomalyScorer": .20,
         "BiometricTrajectoryAnalyzer": .25, "ProfileConsistencyScorer": .20,
         "payment": .15}

    def analyze(self, s: TitanSession, subs: List[AlgoResult]) -> AlgoResult:
        t0 = time.time()
        sigs = []
        wsum, tw = 0.0, 0.0
        for r in subs:
            w = self.W.get(r.algorithm, .15)
            wsum += r.risk * w
            tw += w
            if r.risk > 50:
                sigs.append(Signal(f"sub_{r.algorithm}", w, r.risk,
                    f"{r.algorithm}: risk={r.risk:.0f} → {r.verdict.value}", ""))
        pay = 0.0
        if s.amount > 1000:
            pay += 15
            sigs.append(Signal("high_value", .10, 15,
                f"${s.amount:.0f} high-value", "Split transactions"))
        risky_types = {"prepaid", "virtual", "business"}
        if hasattr(s, 'card_type') and getattr(s, 'card_type', '').lower() in risky_types:
            pay += 20
            sigs.append(Signal("risky_card", .10, 20,
                "Risky card type", "Use consumer credit"))
        risky_mcc = {"gambling", "crypto", "adult", "digital_goods"}
        if s.merchant_cat in risky_mcc:
            pay += 10
            sigs.append(Signal("risky_mcc", .05, 10,
                f"MCC='{s.merchant_cat}'", "Lower-risk MCC first"))
        if s.amount > 250:
            pay += 10
            sigs.append(Signal("likely_3ds", .05, 10,
                ">$250 likely 3DS", "Prepare three_ds_strategy"))
        wsum += pay * self.W["payment"]
        tw += self.W["payment"]
        risk = min(100, wsum / tw) if tw > 0 else 50
        hc = sum(1 for r in subs if r.risk > 60)
        if hc >= 3:
            risk = min(100, risk * 1.3)
            sigs.append(Signal("multi_corr", .15, 15,
                f"{hc}/4 algos high — correlated boost",
                "Must pass ALL layers"))
        elif hc >= 2:
            risk = min(100, risk * 1.15)
        return AlgoResult("MultiLayerRiskFusion", "Stripe Radar/Adyen",
            _v(risk), risk, min(1.0, risk/100), sigs, (time.time()-t0)*1000)


# =====================================================================
# UNIFIED RUNNER
# =====================================================================
class AdversarySimulator:
    """Runs all 5 algorithms against a TitanSession and produces a report."""

    def __init__(self):
        self.graph = GraphLinkAnalyzer()
        self.fp = FingerprintAnomalyScorer()
        self.bio = BiometricTrajectoryAnalyzer()
        self.prof = ProfileConsistencyScorer()
        self.fusion = MultiLayerRiskFusion()

    def ingest_history(self, sessions: List[TitanSession]):
        for s in sessions:
            self.graph.ingest(s)

    def run_all(self, session: TitanSession) -> Dict[str, Any]:
        r1 = self.graph.analyze(session)
        r2 = self.fp.analyze(session)
        r3 = self.bio.analyze(session)
        r4 = self.prof.analyze(session)
        subs = [r1, r2, r3, r4]
        r5 = self.fusion.analyze(session, subs)
        results = [r1, r2, r3, r4, r5]
        return {
            "session_id": session.session_id,
            "final_verdict": r5.verdict.value,
            "final_risk": round(r5.risk, 2),
            "final_detect_prob": round(r5.detect_prob, 4),
            "algorithms": {r.algorithm: {
                "vendor": r.vendor,
                "verdict": r.verdict.value,
                "risk": round(r.risk, 2),
                "detect_prob": round(r.detect_prob, 4),
                "signals": [{"name": sg.name, "score": round(sg.score, 1),
                             "detail": sg.detail, "defense": sg.titan_defense}
                            for sg in r.signals],
                "ms": round(r.ms, 2),
            } for r in results},
        }

    @staticmethod
    def print_report(report: Dict[str, Any]):
        print("=" * 72)
        print("  TITAN V7.0 ADVERSARY DETECTION SIMULATION REPORT")
        print("=" * 72)
        print(f"  Session:  {report['session_id']}")
        print(f"  VERDICT:  {report['final_verdict']}")
        print(f"  Risk:     {report['final_risk']:.1f}/100")
        print(f"  Detect%:  {report['final_detect_prob']*100:.1f}%")
        print("-" * 72)
        for algo, data in report["algorithms"].items():
            icon = "✓" if data["verdict"] == "PASS" else \
                   "⚠" if data["verdict"] == "REVIEW" else "✗"
            print(f"\n  [{icon}] {algo}  ({data['vendor']})")
            print(f"      Verdict: {data['verdict']}  "
                  f"Risk: {data['risk']:.1f}  "
                  f"Detect: {data['detect_prob']*100:.1f}%  "
                  f"({data['ms']:.1f}ms)")
            for sg in data["signals"]:
                print(f"        → {sg['name']}: {sg['detail']}")
                if sg["defense"]:
                    print(f"          Defense: {sg['defense']}")
        print("\n" + "=" * 72)


# =====================================================================
# DEMO: Simulate a well-configured Titan session
# =====================================================================
def _generate_demo_mouse(n=200):
    """Generate realistic-looking DMTG mouse trajectory."""
    import random
    events = []
    x, y, t = 500.0, 400.0, 0.0
    for _ in range(n):
        dt = random.uniform(0.008, 0.06)
        t += dt
        angle = random.gauss(0, 0.8)
        speed = random.gauss(400, 150)
        x += math.cos(angle) * speed * dt + random.gauss(0, 2)
        y += math.sin(angle) * speed * dt + random.gauss(0, 2)
        x = max(0, min(1920, x))
        y = max(0, min(1080, y))
        events.append(MouseEvent(x, y, t))
    return events

def _generate_demo_keys(text="John Smith 123 Main St"):
    """Generate realistic keystroke events."""
    import random
    events = []
    t = 0.0
    for ch in text:
        hold = random.gauss(0.09, 0.025)
        hold = max(0.04, hold)
        gap = random.gauss(0.15, 0.05)
        gap = max(0.04, gap)
        t += gap
        events.append(KeyEvent(ch, t, t + hold))
        t += hold
    return events


if __name__ == "__main__":
    import random
    random.seed(42)

    session = TitanSession(
        session_id="demo-001",
        operator_id="op-alpha",
        email="john.smith42@gmail.com",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        platform="Win32",
        screen_w=1920, screen_h=1080, hw_conc=8, dev_mem=8.0,
        canvas_hash="a3f8c2e91b4d7056", webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, GeForce RTX 3060 Ti)",
        audio_hash="b7e2f1a09c3d8456",
        timezone="America/New_York", language="en-US",
        ip_address="73.162.45.128", ip_type="residential",
        ip_country="US", ip_city="New York", ip_rep=88.0,
        tcp_ttl=128, tcp_window=65535, tcp_os="Windows",
        tls_ja3="cd08e31494f9531f560d64c695473da9",
        profile_age=120, history_count=6200, cookie_count=950,
        ls_domains=135, profile_mb=480.0, has_purchases=True,
        mouse=_generate_demo_mouse(200),
        keys=_generate_demo_keys("John Smith 10001"),
        scrolls=[random.gauss(300, 80) for _ in range(15)],
        session_secs=285.0, pages=7, form_secs=52.0,
        referrers=["https://www.google.com/search?q=shoes",
                    "https://www.nike.com/",
                    "https://www.nike.com/w/mens-shoes"],
        card_bin="414720", card_country="US",
        avs="Y", cvv="M",
        billing_country="US", billing_city="New York",
        amount=189.99, merchant_cat="retail",
    )

    sim = AdversarySimulator()
    report = sim.run_all(session)
    AdversarySimulator.print_report(report)

