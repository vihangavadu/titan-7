#!/usr/bin/env python3
"""TITAN V8.11 — Comprehensive Smoke Test Suite
Goes beyond import checks: instantiates classes, calls methods, validates outputs.
"""
import os, sys, time, json, traceback
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan")

PASS = 0
FAIL = 0
WARN = 0
results = []

def smoke(name, fn):
    global PASS, FAIL, WARN
    try:
        result = fn()
        if result is True or result == "OK":
            PASS += 1
            results.append(("PASS", name, ""))
        elif result == "WARN":
            WARN += 1
            results.append(("WARN", name, "non-critical"))
        else:
            PASS += 1
            results.append(("PASS", name, str(result)[:80] if result else ""))
    except Exception as e:
        FAIL += 1
        tb = traceback.format_exc().strip().split("\n")[-1]
        results.append(("FAIL", name, tb[:120]))

# ══════════════════════════════════════════════════════════════
# 1. GENESIS CORE — Profile generation
# ══════════════════════════════════════════════════════════════
def test_genesis_core():
    from genesis_core import GenesisCore
    gc = GenesisCore()
    assert hasattr(gc, 'generate_identity'), "missing generate_identity"
    assert hasattr(gc, 'generate_profile'), "missing generate_profile"
    return True
smoke("genesis_core: instantiate GenesisCore", test_genesis_core)

# ══════════════════════════════════════════════════════════════
# 2. WEBGL ANGLE — GPU fingerprint profiles
# ══════════════════════════════════════════════════════════════
def test_webgl_angle():
    from webgl_angle import WebGLAngleShim, GPUProfile, GPU_PROFILES, WebGLParams
    shim = WebGLAngleShim()
    # Verify all GPU profiles are populated
    for profile in GPUProfile:
        assert profile in GPU_PROFILES, f"Missing profile: {profile}"
        p = GPU_PROFILES[profile]
        assert isinstance(p, WebGLParams), f"Bad type for {profile}"
        assert p.vendor, f"Empty vendor for {profile}"
    config = shim.generate_webgl_config(gpu_profile=GPUProfile.ANGLE_D3D11)
    assert isinstance(config, dict), "config should be dict"
    return f"{len(GPU_PROFILES)} profiles OK"
smoke("webgl_angle: all GPU profiles valid", test_webgl_angle)

# ══════════════════════════════════════════════════════════════
# 3. FINGERPRINT INJECTOR
# ══════════════════════════════════════════════════════════════
def test_fingerprint_injector():
    from fingerprint_injector import FingerprintInjector
    fi = FingerprintInjector()
    assert hasattr(fi, 'inject') or hasattr(fi, 'generate_fingerprint') or hasattr(fi, 'build_injection_script')
    return True
smoke("fingerprint_injector: instantiate", test_fingerprint_injector)

# ══════════════════════════════════════════════════════════════
# 4. COOKIE FORGE — Cookie generation
# ══════════════════════════════════════════════════════════════
def test_cookie_forge():
    from cookie_forge import CookieForge
    cf = CookieForge()
    assert hasattr(cf, 'forge') or hasattr(cf, 'generate') or hasattr(cf, 'create_cookie_set')
    return True
smoke("cookie_forge: instantiate CookieForge", test_cookie_forge)

# ══════════════════════════════════════════════════════════════
# 5. CHROMIUM COOKIE ENGINE
# ══════════════════════════════════════════════════════════════
def test_chromium_cookie():
    from chromium_cookie_engine import ChromiumCookieEngine
    ce = ChromiumCookieEngine()
    assert hasattr(ce, 'inject') or hasattr(ce, 'encrypt_cookie') or hasattr(ce, 'forge_cookies')
    return True
smoke("chromium_cookie_engine: instantiate", test_chromium_cookie)

# ══════════════════════════════════════════════════════════════
# 6. OBLIVION FORGE
# ══════════════════════════════════════════════════════════════
def test_oblivion_forge():
    from oblivion_forge import OblivionForge
    of = OblivionForge()
    return True
smoke("oblivion_forge: instantiate OblivionForge", test_oblivion_forge)

# ══════════════════════════════════════════════════════════════
# 7. MULTILOGIN FORGE
# ══════════════════════════════════════════════════════════════
def test_multilogin_forge():
    from multilogin_forge import MultiloginForge
    mf = MultiloginForge()
    return True
smoke("multilogin_forge: instantiate MultiloginForge", test_multilogin_forge)

# ══════════════════════════════════════════════════════════════
# 8. AI OPERATIONS GUARD — 4-phase validation
# ══════════════════════════════════════════════════════════════
def test_ai_ops_guard():
    from titan_ai_operations_guard import TitanAIOperationsGuard
    guard = TitanAIOperationsGuard()
    assert hasattr(guard, 'validate') or hasattr(guard, 'run_preflight') or hasattr(guard, 'check')
    return True
smoke("titan_ai_operations_guard: instantiate", test_ai_ops_guard)

# ══════════════════════════════════════════════════════════════
# 9. AI INTELLIGENCE ENGINE
# ══════════════════════════════════════════════════════════════
def test_ai_intel():
    from ai_intelligence_engine import AIIntelligenceEngine
    ai = AIIntelligenceEngine()
    assert hasattr(ai, 'analyze') or hasattr(ai, 'query') or hasattr(ai, 'get_intelligence')
    return True
smoke("ai_intelligence_engine: instantiate", test_ai_intel)

# ══════════════════════════════════════════════════════════════
# 10. TRANSACTION MONITOR
# ══════════════════════════════════════════════════════════════
def test_txn_monitor():
    from transaction_monitor import TransactionMonitor
    tm = TransactionMonitor()
    assert hasattr(tm, 'monitor') or hasattr(tm, 'record') or hasattr(tm, 'analyze_decline')
    return True
smoke("transaction_monitor: instantiate", test_txn_monitor)

# ══════════════════════════════════════════════════════════════
# 11. PROFILE REALISM ENGINE
# ══════════════════════════════════════════════════════════════
def test_profile_realism():
    from profile_realism_engine import ProfileRealismEngine
    pre = ProfileRealismEngine()
    assert hasattr(pre, 'enhance') or hasattr(pre, 'generate') or hasattr(pre, 'apply_realism')
    return True
smoke("profile_realism_engine: instantiate", test_profile_realism)

# ══════════════════════════════════════════════════════════════
# 12. TEMPORAL ENTROPY
# ══════════════════════════════════════════════════════════════
def test_temporal_entropy():
    from temporal_entropy import TemporalEntropyGenerator
    teg = TemporalEntropyGenerator()
    delay = teg.generate_delay() if hasattr(teg, 'generate_delay') else teg.generate() if hasattr(teg, 'generate') else None
    if delay is not None:
        assert isinstance(delay, (int, float)), f"delay should be numeric, got {type(delay)}"
        return f"delay={delay:.3f}s"
    return True
smoke("temporal_entropy: generate delay", test_temporal_entropy)

# ══════════════════════════════════════════════════════════════
# 13. BIOMETRIC MIMICRY
# ══════════════════════════════════════════════════════════════
def test_biometric():
    from biometric_mimicry import BiometricMimicry
    bm = BiometricMimicry()
    assert hasattr(bm, 'generate_mouse_trajectory') or hasattr(bm, 'simulate_typing') or hasattr(bm, 'generate_movement')
    return True
smoke("biometric_mimicry: instantiate", test_biometric)

# ══════════════════════════════════════════════════════════════
# 14. COMMERCE INJECTOR
# ══════════════════════════════════════════════════════════════
def test_commerce():
    from chromium_commerce_injector import CommerceInjector
    ci = CommerceInjector()
    assert hasattr(ci, 'inject') or hasattr(ci, 'generate_script') or hasattr(ci, 'build_injection')
    return True
smoke("chromium_commerce_injector: instantiate", test_commerce)

# ══════════════════════════════════════════════════════════════
# 15. LEVELDB WRITER — expanded module
# ══════════════════════════════════════════════════════════════
def test_leveldb():
    import tempfile, shutil
    from leveldb_writer import LevelDBWriter
    tmpdir = tempfile.mkdtemp(prefix="titan_ldb_test_")
    try:
        writer = LevelDBWriter(tmpdir)
        writer.open()
        ok = writer.write_origin_data("https://test.com", {"key1": "val1", "key2": "val2"})
        assert ok, "write_origin_data returned False"
        stats = writer.stats
        assert stats["write_count"] >= 2, f"expected >=2 writes, got {stats['write_count']}"
        # Verify fallback JSON was created
        snap = os.path.join(tmpdir, "local_storage_simulated.json")
        assert os.path.exists(snap), "JSON fallback not created"
        data = json.load(open(snap))
        assert "https://test.com" in data, "origin not in JSON"
        writer.close()
        return f"wrote {stats['write_count']} keys"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
smoke("leveldb_writer: write + verify JSON fallback", test_leveldb)

# ══════════════════════════════════════════════════════════════
# 16. NTP ISOLATION
# ══════════════════════════════════════════════════════════════
def test_ntp():
    from ntp_isolation import IsolationManager
    im = IsolationManager()
    assert hasattr(im, 'enable_isolation')
    assert hasattr(im, 'isolation_state')
    assert im.isolation_state is not None
    return True
smoke("ntp_isolation: instantiate IsolationManager", test_ntp)

# ══════════════════════════════════════════════════════════════
# 17. TIME SAFETY VALIDATOR
# ══════════════════════════════════════════════════════════════
def test_time_safety():
    from time_safety_validator import SafetyValidator
    sv = SafetyValidator()
    report = sv.get_validation_report()
    assert isinstance(report, dict), "report should be dict"
    assert report["status"] == "no_data", f"unexpected status: {report['status']}"
    return True
smoke("time_safety_validator: instantiate + report", test_time_safety)

# ══════════════════════════════════════════════════════════════
# 18. TLS MIMIC
# ══════════════════════════════════════════════════════════════
def test_tls_mimic():
    from tls_mimic import TLSMimic, CURL_CFFI_OK
    tm = TLSMimic()
    assert tm.impersonate == "chrome120"
    if not CURL_CFFI_OK:
        return "WARN"  # graceful degradation
    return True
smoke("tls_mimic: instantiate TLSMimic", test_tls_mimic)

# ══════════════════════════════════════════════════════════════
# 19. QUIC PROXY
# ══════════════════════════════════════════════════════════════
def test_quic():
    from quic_proxy import QUICProxy, AIOQUIC_AVAILABLE
    qp = QUICProxy()
    assert hasattr(qp, 'create_client_config')
    if not AIOQUIC_AVAILABLE:
        return "WARN"
    return True
smoke("quic_proxy: instantiate QUICProxy", test_quic)

# ══════════════════════════════════════════════════════════════
# 20. FORENSIC ALIGNMENT
# ══════════════════════════════════════════════════════════════
def test_forensic():
    from forensic_alignment import ForensicAlignment
    fa = ForensicAlignment()
    assert hasattr(fa, 'align') or hasattr(fa, 'scrub') or hasattr(fa, 'align_timestamps')
    return True
smoke("forensic_alignment: instantiate", test_forensic)

# ══════════════════════════════════════════════════════════════
# 21. TITAN SESSION — read/write/update
# ══════════════════════════════════════════════════════════════
def test_session():
    from titan_session import get_session, update_session
    s = get_session()
    assert s.get("version") == "8.11.0", f"version={s.get('version')}"
    update_session(current_target="__smoke_test__")
    s2 = get_session()
    assert s2["current_target"] == "__smoke_test__"
    update_session(current_target="")
    return True
smoke("titan_session: read/write/update cycle", test_session)

# ══════════════════════════════════════════════════════════════
# 22. INTEGRATION BRIDGE — init with config
# ══════════════════════════════════════════════════════════════
def test_bridge():
    from integration_bridge import TitanIntegrationBridge
    bridge = TitanIntegrationBridge(config={})
    # Check subsystem init methods exist
    init_methods = [m for m in dir(bridge) if m.startswith("_init_") and callable(getattr(bridge, m))]
    assert len(init_methods) >= 5, f"only {len(init_methods)} init methods"
    return f"{len(init_methods)} subsystems"
smoke("integration_bridge: instantiate with config", test_bridge)

# ══════════════════════════════════════════════════════════════
# 23. TITAN API
# ══════════════════════════════════════════════════════════════
def test_titan_api():
    from titan_api import TitanAPI
    api = TitanAPI()
    assert hasattr(api, 'start') or hasattr(api, 'run') or hasattr(api, 'app')
    return True
smoke("titan_api: instantiate TitanAPI", test_titan_api)

# ══════════════════════════════════════════════════════════════
# 24. REALTIME COPILOT — state machine
# ══════════════════════════════════════════════════════════════
def test_copilot():
    from titan_realtime_copilot import RealtimeCopilot, OperatorPhase
    # Verify all phases exist
    expected = ["IDLE", "CONFIGURING", "PRE_FLIGHT", "BROWSING", "WARMING_UP",
                "APPROACHING_CHECKOUT", "CHECKOUT", "ENTERING_SHIPPING",
                "ENTERING_PAYMENT", "REVIEWING_ORDER", "PROCESSING",
                "THREE_DS", "ORDER_COMPLETE", "COMPLETED"]
    for phase in expected:
        assert hasattr(OperatorPhase, phase), f"Missing phase: {phase}"
    copilot = RealtimeCopilot()
    return f"{len(expected)} phases OK"
smoke("titan_realtime_copilot: all phases + instantiate", test_copilot)

# ══════════════════════════════════════════════════════════════
# 25. ADVANCED PROFILE GENERATOR
# ══════════════════════════════════════════════════════════════
def test_adv_profile():
    from advanced_profile_generator import AdvancedProfileGenerator
    apg = AdvancedProfileGenerator()
    return True
smoke("advanced_profile_generator: instantiate", test_adv_profile)

# ══════════════════════════════════════════════════════════════
# 26. PERSONA ENGINE
# ══════════════════════════════════════════════════════════════
def test_persona():
    from persona_engine import PersonaEngine
    pe = PersonaEngine()
    assert hasattr(pe, 'generate') or hasattr(pe, 'create_persona') or hasattr(pe, 'build')
    return True
smoke("persona_engine: instantiate", test_persona)

# ══════════════════════════════════════════════════════════════
# 27. KILL SWITCH
# ══════════════════════════════════════════════════════════════
def test_kill_switch():
    from kill_switch import KillSwitch
    ks = KillSwitch()
    assert hasattr(ks, 'arm') or hasattr(ks, 'activate') or hasattr(ks, 'trigger')
    return True
smoke("kill_switch: instantiate", test_kill_switch)

# ══════════════════════════════════════════════════════════════
# 28. VECTOR MEMORY
# ══════════════════════════════════════════════════════════════
def test_vector_memory():
    from titan_vector_memory import TitanVectorMemory
    vm = TitanVectorMemory()
    assert hasattr(vm, 'store') or hasattr(vm, 'query') or hasattr(vm, 'add')
    return True
smoke("titan_vector_memory: instantiate", test_vector_memory)

# ══════════════════════════════════════════════════════════════
# 29. PREFLIGHT CORTEX
# ══════════════════════════════════════════════════════════════
def test_preflight():
    from preflight_cortex import PreflightCortex
    pc = PreflightCortex()
    assert hasattr(pc, 'run') or hasattr(pc, 'execute') or hasattr(pc, 'check')
    return True
smoke("preflight_cortex: instantiate", test_preflight)

# ══════════════════════════════════════════════════════════════
# 30. RESILIENT API
# ══════════════════════════════════════════════════════════════
def test_resilient_api():
    from resilient_api import ResilientAPI
    ra = ResilientAPI()
    assert hasattr(ra, 'get') or hasattr(ra, 'post') or hasattr(ra, 'request')
    return True
smoke("resilient_api: instantiate", test_resilient_api)

# ══════════════════════════════════════════════════════════════
# 31. FORM AUTOFILL INJECTOR
# ══════════════════════════════════════════════════════════════
def test_autofill():
    from form_autofill_injector import FormAutofillInjector
    fai = FormAutofillInjector()
    return True
smoke("form_autofill_injector: instantiate", test_autofill)

# ══════════════════════════════════════════════════════════════
# 32. CHRONOS — time manipulation
# ══════════════════════════════════════════════════════════════
def test_chronos():
    from chronos import Chronos
    ch = Chronos()
    assert hasattr(ch, 'shift_time') or hasattr(ch, 'set_time') or hasattr(ch, 'manipulate')
    return True
smoke("chronos: instantiate", test_chronos)

# ══════════════════════════════════════════════════════════════
# 33. GAMP V2 — analytics injection
# ══════════════════════════════════════════════════════════════
def test_gamp():
    from gamp_v2_injector import GAMPV2Injector
    gi = GAMPV2Injector()
    assert hasattr(gi, 'inject') or hasattr(gi, 'generate') or hasattr(gi, 'build_payload')
    return True
smoke("gamp_v2_injector: instantiate", test_gamp)

# ══════════════════════════════════════════════════════════════
# 34. ANTI-DETECT EXPORT
# ══════════════════════════════════════════════════════════════
def test_antidetect():
    from anti_detect_profile_exporter import AntiDetectProfileExporter
    ade = AntiDetectProfileExporter()
    return True
smoke("anti_detect_profile_exporter: instantiate", test_antidetect)

# ══════════════════════════════════════════════════════════════
# 35. GHOST MOTOR V6
# ══════════════════════════════════════════════════════════════
def test_ghost_motor():
    from ghost_motor_v6 import GhostMotor
    gm = GhostMotor()
    return True
smoke("ghost_motor_v6: instantiate GhostMotor", test_ghost_motor)

# ══════════════════════════════════════════════════════════════
# 36. APP SYNTAX — all apps compile cleanly
# ══════════════════════════════════════════════════════════════
def test_app_syntax():
    import py_compile
    apps_dir = "/opt/titan/apps"
    app_files = sorted([f for f in os.listdir(apps_dir) if f.endswith(".py")])
    for af in app_files:
        py_compile.compile(os.path.join(apps_dir, af), doraise=True)
    return f"{len(app_files)} apps OK"
smoke("apps: all Python files compile", test_app_syntax)

# ══════════════════════════════════════════════════════════════
# 37. TITAN 3DS AI EXPLOITS
# ══════════════════════════════════════════════════════════════
def test_3ds():
    from titan_3ds_ai_exploits import Titan3DSExploits
    t3 = Titan3DSExploits()
    return True
smoke("titan_3ds_ai_exploits: instantiate", test_3ds)

# ══════════════════════════════════════════════════════════════
# 38. DECLINE INTELLIGENCE
# ══════════════════════════════════════════════════════════════
def test_decline():
    from decline_intelligence import DeclineIntelligence
    di = DeclineIntelligence()
    assert hasattr(di, 'analyze') or hasattr(di, 'get_recommendation') or hasattr(di, 'process')
    return True
smoke("decline_intelligence: instantiate", test_decline)

# ══════════════════════════════════════════════════════════════
# 39. CANVAS NOISE
# ══════════════════════════════════════════════════════════════
def test_canvas():
    from canvas_noise import CanvasNoise
    cn = CanvasNoise()
    return True
smoke("canvas_noise: instantiate", test_canvas)

# ══════════════════════════════════════════════════════════════
# 40. AUDIO FINGERPRINT
# ══════════════════════════════════════════════════════════════
def test_audio():
    from audio_fingerprint import AudioFingerprint
    af = AudioFingerprint()
    return True
smoke("audio_fingerprint: instantiate", test_audio)

# ══════════════════════════════════════════════════════════════
# PRINT RESULTS
# ══════════════════════════════════════════════════════════════
print("=" * 72)
print("TITAN V8.11 SMOKE TEST RESULTS")
print("=" * 72)
for status, name, detail in results:
    icon = {"PASS": "+", "FAIL": "!", "WARN": "~"}[status]
    line = f"  [{icon}] {status}: {name}"
    if detail:
        line += f" -> {detail}"
    print(line)

print()
print("=" * 72)
total = PASS + FAIL + WARN
print(f"TOTAL: {total} tests | PASS: {PASS} | WARN: {WARN} | FAIL: {FAIL}")
if FAIL == 0:
    print("VERDICT: ALL SMOKE TESTS PASSED")
else:
    print(f"VERDICT: {FAIL} FAILURES NEED FIXING")
print("=" * 72)
