import urllib.request, ssl, json, sys
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0'

print('='*60)
print('LUCID EMPIRE - LIVE ANTI-FRAUD DEFENSE TESTING')
print('='*60)

print('\n[1] TLS CONFIGURATION (howsmyssl.com)')
try:
    req = urllib.request.Request('https://www.howsmyssl.com/a/check', headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        d = json.loads(r.read().decode())
        print(f"  TLS Version: {d.get('tls_version')}")
        print(f"  Rating: {d.get('rating')}")
        print(f"  Ciphers: {len(d.get('given_cipher_suites', []))}")
        print('  STATUS: PASS')
except Exception as e:
    print(f'  ERROR: {e}')

print('\n[2] JA3 FINGERPRINT (ja3er.com)')
try:
    req = urllib.request.Request('https://ja3er.com/json', headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        d = json.loads(r.read().decode())
        print(f"  JA3 Hash: {d.get('ja3_hash')}")
        print('  STATUS: PASS')
except Exception as e:
    print(f'  ERROR: {e}')

print('\n[3] IP DETECTION (ipapi.co)')
try:
    req = urllib.request.Request('https://ipapi.co/json/', headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        d = json.loads(r.read().decode())
        print(f"  IP: {d.get('ip')}")
        print(f"  Location: {d.get('city')}, {d.get('country_name')}")
        print(f"  Org: {d.get('org')}")
        dc = ['amazon','google','microsoft','digitalocean','linode','vultr']
        is_dc = any(k in str(d.get('org','')).lower() for k in dc)
        print(f"  Datacenter IP: {'YES - WARNING' if is_dc else 'NO - PASS'}")
except Exception as e:
    print(f'  ERROR: {e}')

print('\n[4] HTTP HEADERS (httpbin.org)')
try:
    req = urllib.request.Request('https://httpbin.org/headers', headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        d = json.loads(r.read().decode())
        h = d.get('headers', {})
        print(f"  User-Agent: {h.get('User-Agent', '?')[:50]}")
        sus = [k for k in ['X-Forwarded-For','Via','X-Real-Ip'] if k in h]
        print(f"  Suspicious Headers: {sus if sus else 'None - PASS'}")
except Exception as e:
    print(f'  ERROR: {e}')

print('\n[5] SITE ACCESSIBILITY')
sites = [('BrowserLeaks','https://browserleaks.com'),('CreepJS','https://abrahamjuliot.github.io/creepjs/')]
for name, url in sites:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': ua})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            print(f"  {name}: OK ({r.status})")
    except Exception as e:
        print(f"  {name}: FAIL - {str(e)[:30]}")

print('\n' + '='*60)
print('TESTING COMPLETE')
print('='*60)
