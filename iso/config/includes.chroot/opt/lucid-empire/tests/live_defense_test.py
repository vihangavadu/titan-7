#!/usr/bin/env python3
"""
LUCID EMPIRE - Live Anti-Fraud Defense System Testing
Tests against public fingerprinting and bot detection services
"""

import urllib.request
import ssl
import json
import sys
import hashlib
import time
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

class LiveDefenseTester:
    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.results = {}
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        
    def make_request(self, url, timeout=15):
        """Make HTTP request with proper headers"""
        req = urllib.request.Request(url, headers={
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        return urllib.request.urlopen(req, timeout=timeout, context=self.ctx)
    
    def test_howsmyssl(self):
        """Test TLS configuration against howsmyssl.com"""
        print("\n" + "="*70)
        print("[TEST 1] TLS CONFIGURATION (howsmyssl.com)")
        print("="*70)
        
        try:
            with self.make_request('https://www.howsmyssl.com/a/check') as resp:
                data = json.loads(resp.read().decode())
                
                tls_version = data.get('tls_version', 'Unknown')
                rating = data.get('rating', 'Unknown')
                ciphers = data.get('given_cipher_suites', [])
                
                print(f"  TLS Version: {tls_version}")
                print(f"  Rating: {rating}")
                print(f"  Cipher Suites: {len(ciphers)} offered")
                print(f"  Ephemeral Keys: {data.get('ephemeral_keys_supported', False)}")
                print(f"  Session Tickets: {data.get('session_ticket_supported', False)}")
                
                # Score the TLS config
                if tls_version == 'TLS 1.3':
                    status = "EXCELLENT"
                elif tls_version == 'TLS 1.2':
                    status = "GOOD"
                else:
                    status = "OUTDATED"
                    
                print(f"\n  >> TLS STATUS: {status}")
                self.results['tls'] = {'status': status, 'version': tls_version, 'rating': rating}
                return True
                
        except Exception as e:
            print(f"  ERROR: {e}")
            self.results['tls'] = {'status': 'FAILED', 'error': str(e)}
            return False
    
    def test_ja3_fingerprint(self):
        """Test JA3 TLS fingerprint"""
        print("\n" + "="*70)
        print("[TEST 2] JA3 TLS FINGERPRINT (ja3er.com)")
        print("="*70)
        
        try:
            with self.make_request('https://ja3er.com/json') as resp:
                data = json.loads(resp.read().decode())
                
                ja3_hash = data.get('ja3_hash', 'Unknown')
                ja3_text = data.get('ja3', 'Unknown')
                user_agent = data.get('User-Agent', 'Unknown')
                
                print(f"  JA3 Hash: {ja3_hash}")
                print(f"  User-Agent Detected: {user_agent[:60]}...")
                
                # Known browser JA3 hashes for comparison
                known_hashes = {
                    'b32309a26951912be7dba376398abc3b': 'Chrome 120',
                    '0e93e1cdb68b8e47e5a1ae5c0e86f1ac': 'Firefox 120',
                    'e7d705a3286e19ea42f587b344ee6865': 'Safari 17',
                }
                
                match = known_hashes.get(ja3_hash, 'Custom/Unknown')
                print(f"  Fingerprint Match: {match}")
                
                if match != 'Custom/Unknown':
                    status = "PASS - Matches known browser"
                else:
                    status = "CAUTION - Custom fingerprint (may be flagged)"
                    
                print(f"\n  >> JA3 STATUS: {status}")
                self.results['ja3'] = {'status': status, 'hash': ja3_hash, 'match': match}
                return True
                
        except Exception as e:
            print(f"  ERROR: {e}")
            self.results['ja3'] = {'status': 'FAILED', 'error': str(e)}
            return False
    
    def test_ip_info(self):
        """Test IP and geolocation detection"""
        print("\n" + "="*70)
        print("[TEST 3] IP & GEOLOCATION (ipapi.co)")
        print("="*70)
        
        try:
            with self.make_request('https://ipapi.co/json/') as resp:
                data = json.loads(resp.read().decode())
                
                ip = data.get('ip', 'Unknown')
                city = data.get('city', 'Unknown')
                region = data.get('region', 'Unknown')
                country = data.get('country_name', 'Unknown')
                org = data.get('org', 'Unknown')
                asn = data.get('asn', 'Unknown')
                
                print(f"  IP Address: {ip}")
                print(f"  Location: {city}, {region}, {country}")
                print(f"  Organization: {org}")
                print(f"  ASN: {asn}")
                
                # Check for datacenter/VPN indicators
                datacenter_keywords = ['amazon', 'google', 'microsoft', 'digitalocean', 'linode', 'vultr', 'ovh', 'hetzner']
                is_datacenter = any(kw in org.lower() for kw in datacenter_keywords)
                
                if is_datacenter:
                    status = "WARNING - Datacenter IP detected"
                else:
                    status = "PASS - Residential IP appearance"
                    
                print(f"\n  >> IP STATUS: {status}")
                self.results['ip'] = {'status': status, 'ip': ip, 'location': f"{city}, {country}", 'is_datacenter': is_datacenter}
                return True
                
        except Exception as e:
            print(f"  ERROR: {e}")
            self.results['ip'] = {'status': 'FAILED', 'error': str(e)}
            return False
    
    def test_site_accessibility(self):
        """Test accessibility of key fingerprinting sites"""
        print("\n" + "="*70)
        print("[TEST 4] FINGERPRINT SITE ACCESSIBILITY")
        print("="*70)
        
        sites = [
            ('BrowserLeaks Canvas', 'https://browserleaks.com/canvas'),
            ('BrowserLeaks WebGL', 'https://browserleaks.com/webgl'),
            ('CreepJS', 'https://abrahamjuliot.github.io/creepjs/'),
            ('AmIUnique', 'https://amiunique.org/'),
        ]
        
        accessible = 0
        for name, url in sites:
            try:
                with self.make_request(url, timeout=5) as resp:
                    status = resp.status
                    if status == 200:
                        print(f"  PASS: {name} (HTTP {status})")
                        accessible += 1
                    else:
                        print(f"  WARN: {name} (HTTP {status})")
            except Exception as e:
                err_msg = str(e)[:35]
                print(f"  SKIP: {name} - {err_msg}")
        
        print(f"\n  >> ACCESSIBILITY: {accessible}/{len(sites)} sites reachable")
        self.results['accessibility'] = {'status': f'{accessible}/{len(sites)}', 'accessible': accessible, 'total': len(sites)}
        return True
    
    def test_http_headers(self):
        """Analyze HTTP headers sent"""
        print("\n" + "="*70)
        print("[TEST 5] HTTP HEADERS ANALYSIS (httpbin.org)")
        print("="*70)
        
        try:
            with self.make_request('https://httpbin.org/headers') as resp:
                data = json.loads(resp.read().decode())
                headers = data.get('headers', {})
                
                print("  Headers Sent:")
                for key, value in headers.items():
                    if key.lower() != 'host':
                        print(f"    {key}: {value[:60]}{'...' if len(str(value)) > 60 else ''}")
                
                # Check for suspicious headers
                suspicious = []
                if 'X-Forwarded-For' in headers:
                    suspicious.append('X-Forwarded-For present')
                if 'Via' in headers:
                    suspicious.append('Via header present')
                if 'X-Real-Ip' in headers:
                    suspicious.append('X-Real-IP present')
                    
                if suspicious:
                    status = f"WARNING - {', '.join(suspicious)}"
                else:
                    status = "PASS - Clean headers"
                    
                print(f"\n  >> HEADER STATUS: {status}")
                self.results['headers'] = {'status': status, 'suspicious': suspicious}
                return True
                
        except Exception as e:
            print(f"  ERROR: {e}")
            self.results['headers'] = {'status': 'FAILED', 'error': str(e)}
            return False
    
    def test_webrtc_leak(self):
        """Check WebRTC leak potential (informational)"""
        print("\n" + "="*70)
        print("[TEST 6] WebRTC LEAK CHECK")
        print("="*70)
        
        print("  NOTE: WebRTC leak detection requires browser environment")
        print("  This test verifies the service is available")
        
        try:
            with self.make_request('https://browserleaks.com/webrtc', timeout=10) as resp:
                if resp.status == 200:
                    print("  BrowserLeaks WebRTC: ACCESSIBLE")
                    print("\n  >> To test WebRTC: Visit https://browserleaks.com/webrtc in LUCID browser")
                    self.results['webrtc'] = {'status': 'REQUIRES_BROWSER', 'accessible': True}
                    return True
        except Exception as e:
            print(f"  ERROR: {e}")
            self.results['webrtc'] = {'status': 'FAILED', 'error': str(e)}
            return False
    
    def generate_report(self):
        """Generate final test report"""
        print("\n")
        print("="*70)
        print("           LUCID EMPIRE - DEFENSE TEST REPORT")
        print("="*70)
        print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*70)
        
        # Summary table
        print("\n  TEST RESULTS SUMMARY:")
        print("  " + "-"*50)
        
        test_names = {
            'tls': 'TLS Configuration',
            'ja3': 'JA3 Fingerprint',
            'ip': 'IP Detection',
            'accessibility': 'Site Accessibility',
            'headers': 'HTTP Headers',
            'webrtc': 'WebRTC Check'
        }
        
        passed = 0
        warnings = 0
        failed = 0
        
        for key, name in test_names.items():
            if key in self.results:
                status = self.results[key].get('status', 'Unknown')
                if 'PASS' in str(status) or 'EXCELLENT' in str(status) or 'GOOD' in str(status):
                    icon = "[+]"
                    passed += 1
                elif 'WARNING' in str(status) or 'CAUTION' in str(status) or 'REQUIRES' in str(status):
                    icon = "[!]"
                    warnings += 1
                else:
                    icon = "[-]"
                    failed += 1
                print(f"  {icon} {name}: {status[:45]}")
            else:
                print(f"  [?] {name}: Not tested")
        
        print("  " + "-"*50)
        print(f"\n  TOTAL: {passed} Passed, {warnings} Warnings, {failed} Failed")
        
        # Overall assessment
        print("\n" + "="*70)
        print("  OVERALL ASSESSMENT:")
        print("="*70)
        
        if failed == 0 and warnings <= 2:
            overall = "EXCELLENT"
            desc = "System ready for deployment"
        elif failed <= 1 and warnings <= 3:
            overall = "GOOD"
            desc = "Minor issues, generally safe"
        elif failed <= 2:
            overall = "FAIR"
            desc = "Some concerns, review warnings"
        else:
            overall = "NEEDS ATTENTION"
            desc = "Multiple issues detected"
        
        print(f"\n  Rating: {overall}")
        print(f"  {desc}")
        
        # Next steps
        print("\n" + "-"*70)
        print("  NEXT STEPS FOR FULL TESTING:")
        print("-"*70)
        print("  1. Launch LUCID browser with a generated profile")
        print("  2. Visit https://browserleaks.com/canvas - verify consistent hash")
        print("  3. Visit https://pixelscan.net/ - should show 'Consistent' status")
        print("  4. Visit https://creepjs.com/ - check trust score")
        print("  5. Test Stripe sandbox: https://dashboard.stripe.com/test")
        print("     - Use card: 4242424242424242, any future date, any CVC")
        print("="*70)
        
        return overall

def main():
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "    LUCID EMPIRE V7.0-TITAN SINGULARITY    ".center(68) + "*")
    print("*" + "    ANTI-FRAUD DEFENSE LIVE TESTING    ".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    
    tester = LiveDefenseTester()
    
    # Run all tests
    tester.test_howsmyssl()
    tester.test_ja3_fingerprint()
    tester.test_ip_info()
    tester.test_site_accessibility()
    tester.test_http_headers()
    tester.test_webrtc_leak()
    
    # Generate report
    overall = tester.generate_report()
    
    return 0 if overall in ['EXCELLENT', 'GOOD'] else 1

if __name__ == '__main__':
    sys.exit(main())
