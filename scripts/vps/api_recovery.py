#!/usr/bin/env python3
"""Quick script to start VPS recovery mode and diagnose boot issues via Hostinger API."""
import requests
import json
import sys
import time

TOKEN = "hsogco6RgOaj1HlRetspyhtcNSaBIKKHOy9LjNd3d3718fd6"
BASE = "https://developers.hostinger.com"
VM_ID = 1400969
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def api_get(path):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=30)
    return r.status_code, r.json()

def api_post(path, data=None):
    r = requests.post(f"{BASE}{path}", headers=HEADERS, json=data or {}, timeout=30)
    return r.status_code, r.json()

def api_delete(path):
    r = requests.delete(f"{BASE}{path}", headers=HEADERS, timeout=30)
    return r.status_code, r.json()

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"

    if action == "status":
        code, data = api_get(f"/api/vps/v1/virtual-machines/{VM_ID}")
        vm = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(vm, dict):
            print(f"State: {vm.get('state', '?')}")
            print(f"IP: {vm.get('ipv4', [{}])[0].get('address', '?') if vm.get('ipv4') else '?'}")
            print(f"Hostname: {vm.get('hostname', '?')}")
            print(f"Firewall: {vm.get('firewall_group_id', 'none')}")
            print(f"Actions Lock: {vm.get('actions_lock', '?')}")
        else:
            print(json.dumps(data, indent=2))

    elif action == "actions":
        code, data = api_get(f"/api/vps/v1/virtual-machines/{VM_ID}/actions")
        actions = data.get("data", [])
        for a in actions[:15]:
            print(f"  {a['created_at']} | {a['name']:<25} | {a['state']}")

    elif action == "recovery-start":
        print("Starting recovery mode...")
        code, data = api_post(f"/api/vps/v1/virtual-machines/{VM_ID}/recovery", {
            "root_password": "TitanRecovery2026!"
        })
        print(f"Status: {code}")
        print(json.dumps(data, indent=2))

    elif action == "recovery-stop":
        print("Stopping recovery mode...")
        code, data = api_delete(f"/api/vps/v1/virtual-machines/{VM_ID}/recovery")
        print(f"Status: {code}")
        print(json.dumps(data, indent=2))

    elif action == "restart":
        print("Restarting VPS...")
        code, data = api_post(f"/api/vps/v1/virtual-machines/{VM_ID}/restart")
        print(f"Status: {code}")
        print(json.dumps(data, indent=2))

    elif action == "stop":
        print("Stopping VPS...")
        code, data = api_post(f"/api/vps/v1/virtual-machines/{VM_ID}/stop")
        print(f"Status: {code}")
        print(json.dumps(data, indent=2))

    elif action == "start":
        print("Starting VPS...")
        code, data = api_post(f"/api/vps/v1/virtual-machines/{VM_ID}/start")
        print(f"Status: {code}")
        print(json.dumps(data, indent=2))

    elif action == "firewall":
        code, data = api_get("/api/vps/v1/firewall")
        if isinstance(data, list):
            print(json.dumps(data, indent=2))
        else:
            firewalls = data.get("data", data)
            print(json.dumps(firewalls, indent=2))

    else:
        print(f"Unknown action: {action}")
        print("Usage: python api_recovery.py [status|actions|recovery-start|recovery-stop|restart|stop|start|firewall]")

if __name__ == "__main__":
    main()
