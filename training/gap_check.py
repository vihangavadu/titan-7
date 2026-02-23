#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/opt/titan')

results = {}

# 1. hardware_concurrency in FingerprintConfig
try:
    from core.fingerprint_injector import FingerprintConfig, FingerprintInjector
    fc = FingerprintConfig(profile_uuid='test')
    results['fp_hardware_concurrency_field'] = hasattr(fc, 'hardware_concurrency')
    fi = FingerprintInjector(fc)
    results['fp_cdp_inject_method'] = hasattr(fi, 'inject_cdp_preload')
    results['fp_hw_concurrency_script'] = hasattr(fi, 'generate_hardware_concurrency_script')
    results['fp_chrome_version_default'] = getattr(fi, 'config', None) and True
except Exception as e:
    results['fingerprint_injector_error'] = str(e)

# 2. OffscreenCanvas protection
try:
    content = open('/opt/titan/core/canvas_subpixel_shim.py').read()
    results['offscreen_canvas_class'] = 'OffscreenCanvasProtection' in content
    results['offscreen_canvas_shim_method'] = 'generate_offscreen_canvas_shim' in content
except Exception as e:
    results['canvas_subpixel_error'] = str(e)

# 3. profile_realism_engine - compat.ini OS-aware
try:
    content = open('/opt/titan/core/profile_realism_engine.py').read()
    results['compat_ini_os_aware'] = 'WINNT_x86_64' in content
    results['gmp_abi_os_aware'] = 'x86_64-msvc' in content
    results['indexeddb_bug_fixed'] = 'rid<1000000' in content or 'rid < 1000000' in content
    results['tracking_protection_removed'] = 'privacy.trackingprotection.enabled' not in content
except Exception as e:
    results['profile_realism_error'] = str(e)

# 4. gen_storage.py - O(n^2) fix
try:
    content = open('/opt/titan/profgen/gen_storage.py').read()
    results['gen_storage_current_size_opt'] = 'current_size' in content
    results['gen_storage_ga_domains_set'] = 'ga_domains = {' in content
except Exception as e:
    results['gen_storage_error'] = str(e)

# 5. profile_isolation - Camoufox integration
try:
    content = open('/opt/titan/core/profile_isolation.py').read()
    results['profile_isolation_camoufox'] = 'camoufox' in content.lower() or 'launch_browser_isolated' in content
    results['profile_isolation_bwrap'] = 'bwrap' in content or 'bubblewrap' in content
except Exception as e:
    results['profile_isolation_error'] = str(e)

# 6. Client Hints default Chrome version
try:
    content = open('/opt/titan/core/fingerprint_injector.py').read()
    results['chrome_133_default'] = "chrome_version: str = '133'" in content or "chrome_version='133'" in content
    results['chrome_134_brand'] = "'134'" in content
    results['firefox_buildid_spoof'] = 'buildID' in content or 'navigator.buildID' in content
except Exception as e:
    results['chrome_version_error'] = str(e)

# 7. advanced_profile_generator - webgl cross-ref
try:
    content = open('/opt/titan/core/advanced_profile_generator.py').read()
    results['apg_webgl_hardware_crossref'] = 'hardware_profile' in content and 'webgl_renderer' in content
    results['apg_eu_narrative'] = 'eu_' in content.lower() or 'european' in content.lower()
    results['apg_mobile_narrative'] = 'mobile' in content.lower()
except Exception as e:
    results['apg_error'] = str(e)

# 8. genesis_core - Chrome 133 UA
try:
    content = open('/opt/titan/core/genesis_core.py').read()
    results['genesis_chrome133_ua'] = 'Chrome/133' in content
    results['genesis_chrome134_ua'] = 'Chrome/134' in content
    results['genesis_duplicate_prefs_fixed'] = content.count('privacy.trackingprotection') <= 1
except Exception as e:
    results['genesis_error'] = str(e)

# 9. TCP fingerprint / eBPF modules
results['tcp_fingerprint_c'] = os.path.exists('/opt/titan/lib/tcp_fingerprint.c')
results['xdp_loader_c'] = os.path.exists('/opt/titan/lib/xdp_loader.c')
results['network_shield_original_c'] = os.path.exists('/opt/titan/lib/network_shield_original.c')

# 10. validation dashboard
results['validation_dashboard_html'] = os.path.exists('/opt/titan/apps/validation_dashboard.html')

# 11. GAMP triangulation v2
try:
    from core.gamp_triangulation_v2 import GampTriangulationV2
    results['gamp_v2_importable'] = True
except Exception as e:
    results['gamp_v2_importable'] = False
    results['gamp_v2_error'] = str(e)

# 12. journey_simulator
try:
    from core.journey_simulator import JourneySimulator
    results['journey_simulator_importable'] = True
except Exception as e:
    results['journey_simulator_importable'] = False

# 13. temporal_entropy
try:
    from core.temporal_entropy import TemporalEntropy
    results['temporal_entropy_importable'] = True
except Exception as e:
    results['temporal_entropy_importable'] = False

# 14. titan_preflight exists
results['titan_preflight_deployed'] = os.path.exists('/opt/titan/core/titan_preflight.py')

# 15. smoke_test_v91
results['smoke_test_v91'] = os.path.exists('/opt/titan/core/smoke_test_v91.py')

# Print results
print("\n=== TITAN OS V8.3 GAP ANALYSIS ===\n")
gaps = []
present = []
for k, v in sorted(results.items()):
    if v is True:
        present.append(k)
        print(f"  [OK]  {k}")
    elif v is False:
        gaps.append(k)
        print(f"  [GAP] {k}")
    else:
        print(f"  [ERR] {k}: {v}")

print(f"\n  PRESENT: {len(present)}")
print(f"  GAPS:    {len(gaps)}")
print("\n  GAPS LIST:")
for g in gaps:
    print(f"    - {g}")
