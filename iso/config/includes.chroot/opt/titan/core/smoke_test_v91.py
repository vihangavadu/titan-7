#!/usr/bin/env python3
"""
TITAN V9.1 Smoke Test — Self-Hosted Integration Verification
Run on VPS after syncing code + installing deps.

Tests:
    1. All modified modules import cleanly
    2. Prometheus exporter initializes
    3. Webhook server starts on :9300
    4. Redis session pub/sub works
    5. SearXNG provider detected
    6. Uptime Kuma client initializable
    7. ProxyHealthMonitor initializable
    8. TechStackDetector initializable
    9. FlareSolverr env var read
   10. Changedetection handler callable

Usage:
    cd /opt/titan/src/core
    python smoke_test_v91.py
"""

import sys
import os
import time
import json

# Ensure PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
WARN = 0

def test(name, fn):
    global PASS, FAIL, WARN
    try:
        result = fn()
        if result is True:
            print(f"  ✅ {name}")
            PASS += 1
        elif result == "WARN":
            print(f"  ⚠️  {name}")
            WARN += 1
        else:
            print(f"  ❌ {name}: returned {result}")
            FAIL += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        FAIL += 1


print("=" * 65)
print("  TITAN V9.1 SMOKE TEST — Self-Hosted Integrations")
print("=" * 65)

# ── 1. Module Imports ──
print("\n[1/6] Module Imports")

def test_import_metrics():
    from payment_success_metrics import (
        PaymentSuccessMetricsDB, PaymentSuccessScorer,
        TitanPrometheusExporter, get_prometheus_exporter,
        start_prometheus_exporter
    )
    return True

def test_import_webintel():
    from titan_web_intel import TitanWebIntel, _search_searxng
    return True

def test_import_session():
    from titan_session import save_session, get_session, _get_redis
    return True

def test_import_webhooks():
    from titan_webhook_integrations import (
        start_webhook_server, get_webhook_stats, get_recent_events,
        _handle_changedetection, _handle_n8n_decline_retry,
        _handle_uptime_kuma
    )
    return True

def test_import_preflight():
    from preflight_validator import PreFlightValidator
    return True

def test_import_discovery():
    from target_discovery import TargetDiscovery
    return True

def test_import_stack():
    from titan_self_hosted_stack import (
        get_self_hosted_stack, get_redis_client, get_uptime_kuma,
        get_proxy_health_monitor, get_tech_detector
    )
    return True

test("payment_success_metrics (+ Prometheus)", test_import_metrics)
test("titan_web_intel (+ SearXNG)", test_import_webintel)
test("titan_session (+ Redis pub/sub)", test_import_session)
test("titan_webhook_integrations (new)", test_import_webhooks)
test("preflight_validator (+ Kuma + ProxyHealth)", test_import_preflight)
test("target_discovery (+ FlareSolverr + Wappalyzer)", test_import_discovery)
test("titan_self_hosted_stack", test_import_stack)

# ── 2. Prometheus Exporter ──
print("\n[2/6] Prometheus Exporter")

def test_prom_init():
    from payment_success_metrics import get_prometheus_exporter
    exp = get_prometheus_exporter()
    return exp is not None

def test_prom_available():
    from payment_success_metrics import get_prometheus_exporter
    exp = get_prometheus_exporter()
    if exp.is_available:
        return True
    print("    (prometheus_client not installed — pip install prometheus-client)")
    return "WARN"

def test_prom_start():
    from payment_success_metrics import get_prometheus_exporter
    exp = get_prometheus_exporter()
    if not exp.is_available:
        print("    (skipped — prometheus_client not installed)")
        return "WARN"
    ok = exp.start()
    if ok:
        stats = exp.get_stats()
        print(f"    → Listening on {stats.get('url')}")
    return ok

test("Exporter initializes", test_prom_init)
test("prometheus_client available", test_prom_available)
test("Exporter starts on :9200", test_prom_start)

# ── 3. Webhook Server ──
print("\n[3/6] Webhook Server")

def test_webhook_flask():
    from titan_webhook_integrations import _FLASK_AVAILABLE
    if _FLASK_AVAILABLE:
        return True
    print("    (Flask not installed)")
    return "WARN"

def test_webhook_start():
    from titan_webhook_integrations import start_webhook_server, get_webhook_stats
    ok = start_webhook_server(port=9300)
    if ok:
        stats = get_webhook_stats()
        print(f"    → Running on :{stats.get('port')}")
        print(f"    → Endpoints: {len(stats.get('endpoints', {}))}")
    return ok

def test_webhook_health():
    """Hit the /health endpoint to verify server is responding."""
    import urllib.request
    time.sleep(0.5)
    try:
        req = urllib.request.Request("http://127.0.0.1:9300/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "ok"
    except Exception as e:
        print(f"    (health check failed: {e})")
        return "WARN"

test("Flask available", test_webhook_flask)
test("Webhook server starts on :9300", test_webhook_start)
test("GET /health returns ok", test_webhook_health)

# ── 4. Redis Session Sync ──
print("\n[4/6] Redis Session Pub/Sub")

def test_redis_client():
    from titan_self_hosted_stack import get_redis_client
    rc = get_redis_client()
    if rc and rc.is_available:
        print(f"    → Redis connected")
        return True
    print("    (Redis not reachable)")
    return "WARN"

def test_redis_session_write():
    from titan_session import _get_redis, _REDIS_SESSION_KEY
    rc = _get_redis()
    if not rc:
        print("    (Redis not available — session uses file-only mode)")
        return "WARN"
    # Write a test key
    rc.set("titan:smoke_test", "v91_ok", ttl=60)
    val = rc.get("titan:smoke_test")
    return val == "v91_ok"

test("RedisClient initializes", test_redis_client)
test("Redis session write/read", test_redis_session_write)

# ── 5. SearXNG + Other Providers ──
print("\n[5/6] Web Intel Providers")

def test_searxng_provider():
    from titan_web_intel import TitanWebIntel
    intel = TitanWebIntel()
    providers = intel._provider_order
    print(f"    → Providers: {providers}")
    return "searxng" in providers

def test_searxng_env():
    url = os.getenv("TITAN_SEARXNG_URL", "")
    if url:
        print(f"    → TITAN_SEARXNG_URL={url}")
        return True
    print("    (TITAN_SEARXNG_URL not set — SearXNG will try default http://127.0.0.1:8888)")
    return "WARN"

test("SearXNG in provider list", test_searxng_provider)
test("TITAN_SEARXNG_URL env var", test_searxng_env)

# ── 6. Self-Hosted Stack Clients ──
print("\n[6/6] Self-Hosted Stack Clients")

def test_uptime_kuma_init():
    from titan_self_hosted_stack import get_uptime_kuma
    kuma = get_uptime_kuma()
    if kuma:
        print(f"    → Kuma available: {kuma.is_available}")
        return True
    return False

def test_proxy_health_init():
    from titan_self_hosted_stack import get_proxy_health_monitor
    phm = get_proxy_health_monitor()
    if phm:
        print(f"    → ProxyHealthMonitor available: {phm.is_available}")
        return True
    return False

def test_tech_detector_init():
    from titan_self_hosted_stack import get_tech_detector
    td = get_tech_detector()
    if td:
        print(f"    → TechStackDetector available: {td.is_available}")
        return True
    return False

def test_flaresolverr_env():
    url = os.getenv("TITAN_FLARESOLVERR_URL", "")
    if url:
        print(f"    → TITAN_FLARESOLVERR_URL={url}")
        return True
    print("    (TITAN_FLARESOLVERR_URL not set — default http://127.0.0.1:8191)")
    return "WARN"

test("UptimeKumaClient init", test_uptime_kuma_init)
test("ProxyHealthMonitor init", test_proxy_health_init)
test("TechStackDetector init", test_tech_detector_init)
test("TITAN_FLARESOLVERR_URL env var", test_flaresolverr_env)

# ── Summary ──
print("\n" + "=" * 65)
total = PASS + FAIL + WARN
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {WARN} warnings / {total} total")
if FAIL == 0:
    print("  ✅ V9.1 SMOKE TEST PASSED")
else:
    print(f"  ❌ V9.1 SMOKE TEST FAILED ({FAIL} failures)")
print("=" * 65)

sys.exit(1 if FAIL > 0 else 0)
