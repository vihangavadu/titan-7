#!/usr/bin/env python3
"""
Hostinger API Verification Script
Tests API key authentication and retrieves VPS information.
"""

import requests
import json

API_KEY = "xCdl7txsxWhpUyLWLITkOsYuVzF69I8SuSprZBePad639a01"
BASE_URL = "https://developers.hostinger.com"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_api():
    print("=" * 60)
    print("HOSTINGER API VERIFICATION")
    print("=" * 60)
    
    endpoints = [
        ("/api/vps/v1/virtual-machines", "VPS Virtual Machines"),
        ("/api/vps/v1/data-centers", "Data Centers"),
        ("/api/vps/v1/templates", "OS Templates"),
        ("/api/vps/v1/public-keys", "SSH Public Keys"),
        ("/api/vps/v1/firewall", "Firewall Rules"),
        ("/api/billing/v1/subscriptions", "Subscriptions"),
    ]
    
    results = {}
    
    for endpoint, name in endpoints:
        print(f"\n[TEST] {name}")
        print(f"  Endpoint: {endpoint}")
        
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=15)
            status = response.status_code
            
            if status == 200:
                data = response.json()
                print(f"  Status: ✅ {status} OK")
                print(f"  Response: {json.dumps(data, indent=2)[:500]}...")
                results[name] = {"status": "SUCCESS", "code": status, "data": data}
            elif status == 401:
                print(f"  Status: ❌ {status} Unauthorized - Invalid API Key")
                results[name] = {"status": "UNAUTHORIZED", "code": status}
            elif status == 403:
                print(f"  Status: ⚠️ {status} Forbidden - Insufficient permissions")
                results[name] = {"status": "FORBIDDEN", "code": status}
            elif status == 429:
                print(f"  Status: ⚠️ {status} Rate Limited")
                results[name] = {"status": "RATE_LIMITED", "code": status}
            else:
                print(f"  Status: ⚠️ {status}")
                print(f"  Response: {response.text[:300]}")
                results[name] = {"status": "ERROR", "code": status}
                
        except requests.exceptions.RequestException as e:
            print(f"  Status: ❌ Network Error - {e}")
            results[name] = {"status": "NETWORK_ERROR", "error": str(e)}
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    success = sum(1 for r in results.values() if r.get("status") == "SUCCESS")
    total = len(results)
    
    print(f"\nSuccessful: {success}/{total}")
    
    if success == total:
        print("\n✅ API KEY VERIFIED - Full access confirmed")
    elif success > 0:
        print("\n⚠️ API KEY PARTIAL - Some endpoints accessible")
    else:
        print("\n❌ API KEY INVALID or EXPIRED")
    
    # If we found VPS instances, show detailed info
    if "VPS Virtual Machines" in results and results["VPS Virtual Machines"].get("status") == "SUCCESS":
        vps_data = results["VPS Virtual Machines"].get("data", {})
        if isinstance(vps_data, dict) and "data" in vps_data:
            vms = vps_data["data"]
            print(f"\n{'=' * 60}")
            print("YOUR VPS INSTANCES")
            print("=" * 60)
            for vm in vms:
                print(f"\n  ID: {vm.get('id')}")
                print(f"  Hostname: {vm.get('hostname', 'N/A')}")
                print(f"  State: {vm.get('state', 'N/A')}")
                print(f"  IPv4: {vm.get('ipv4', [])}")
                print(f"  IPv6: {vm.get('ipv6', [])}")
                print(f"  OS: {vm.get('template', {}).get('name', 'N/A')}")
                print(f"  Data Center: {vm.get('data_center', {}).get('name', 'N/A')}")
                print(f"  CPU: {vm.get('cpus', 'N/A')} cores")
                print(f"  RAM: {vm.get('memory', 'N/A')} MB")
                print(f"  Disk: {vm.get('disk', 'N/A')} GB")
    
    return results

if __name__ == "__main__":
    test_api()
