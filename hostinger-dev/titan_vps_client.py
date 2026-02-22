#!/usr/bin/env python3
"""
TITAN V8.1 — Hostinger VPS API Client

Python wrapper for all Hostinger VPS API endpoints relevant to Titan development.
Reads API token from environment variable HOSTINGER_API_TOKEN or from titan.env.

Usage:
    from titan_vps_client import TitanVPSClient

    client = TitanVPSClient(token="YOUR_TOKEN")
    vms = client.list_vms()
    client.restart_vm(vm_id=12345)
    client.create_snapshot(vm_id=12345)
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

logger = logging.getLogger("TITAN-VPS-CLIENT")

BASE_URL = "https://developers.hostinger.com"


class TitanVPSClient:
    """
    Hostinger VPS API client for Titan OS development and deployment.
    """

    def __init__(self, token: str = None):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required: pip install requests")

        self.token = token or os.environ.get("HOSTINGER_API_TOKEN", "")
        if not self.token:
            logger.warning("No API token provided. Set HOSTINGER_API_TOKEN env var.")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _get(self, path: str, params: Dict = None) -> Dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: Dict = None) -> Dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.post(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: Dict = None) -> Dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.put(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str, data: Dict = None) -> Dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.delete(url, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ═══════════════════════════════════════════════════════════════════
    # VPS: Virtual Machine
    # ═══════════════════════════════════════════════════════════════════

    def list_vms(self) -> List[Dict]:
        """List all VPS instances."""
        return self._get("/api/vps/v1/virtual-machines").get("data", [])

    def get_vm(self, vm_id: int) -> Dict:
        """Get VPS details (IP, state, OS, specs)."""
        return self._get(f"/api/vps/v1/virtual-machines/{vm_id}")

    def start_vm(self, vm_id: int) -> Dict:
        """Start a VPS."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/start")

    def stop_vm(self, vm_id: int) -> Dict:
        """Stop a VPS."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/stop")

    def restart_vm(self, vm_id: int) -> Dict:
        """Restart a VPS."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/restart")

    def recreate_vm(self, vm_id: int, template_id: int, password: str,
                    post_install_script_id: int = None) -> Dict:
        """Reinstall OS on VPS (DESTRUCTIVE — all data lost)."""
        data = {"template_id": template_id, "password": password}
        if post_install_script_id:
            data["post_install_script_id"] = post_install_script_id
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/recreate", data)

    def setup_vm(self, vm_id: int, template_id: int, password: str,
                 hostname: str = None, post_install_script_id: int = None) -> Dict:
        """Setup a newly purchased VPS."""
        data = {"template_id": template_id, "password": password}
        if hostname:
            data["hostname"] = hostname
        if post_install_script_id:
            data["post_install_script_id"] = post_install_script_id
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/setup", data)

    def set_hostname(self, vm_id: int, hostname: str) -> Dict:
        """Set VPS hostname."""
        return self._put(f"/api/vps/v1/virtual-machines/{vm_id}/hostname",
                         {"hostname": hostname})

    def set_nameservers(self, vm_id: int, ns1: str, ns2: str = None) -> Dict:
        """Set DNS resolvers."""
        data = {"ns1": ns1}
        if ns2:
            data["ns2"] = ns2
        return self._put(f"/api/vps/v1/virtual-machines/{vm_id}/nameservers", data)

    def reset_root_password(self, vm_id: int, password: str) -> Dict:
        """Reset root password."""
        return self._put(f"/api/vps/v1/virtual-machines/{vm_id}/root-password",
                         {"password": password})

    # ═══════════════════════════════════════════════════════════════════
    # VPS: Firewall
    # ═══════════════════════════════════════════════════════════════════

    def list_firewalls(self) -> List[Dict]:
        """List all firewall configurations."""
        return self._get("/api/vps/v1/firewall").get("data", [])

    def create_firewall(self, name: str) -> Dict:
        """Create a new firewall."""
        return self._post("/api/vps/v1/firewall", {"name": name})

    def activate_firewall(self, fw_id: int, vm_id: int) -> Dict:
        """Activate firewall on VPS."""
        return self._post(f"/api/vps/v1/firewall/{fw_id}/activate/{vm_id}")

    def deactivate_firewall(self, fw_id: int, vm_id: int) -> Dict:
        """Deactivate firewall from VPS."""
        return self._post(f"/api/vps/v1/firewall/{fw_id}/deactivate/{vm_id}")

    def create_firewall_rule(self, fw_id: int, protocol: str, port: str,
                              source: str = "any", action: str = "accept") -> Dict:
        """Add a firewall rule."""
        return self._post(f"/api/vps/v1/firewall/{fw_id}/rules", {
            "protocol": protocol, "port": port,
            "source": source, "action": action,
        })

    # ═══════════════════════════════════════════════════════════════════
    # VPS: SSH Keys
    # ═══════════════════════════════════════════════════════════════════

    def list_ssh_keys(self) -> List[Dict]:
        """List SSH keys."""
        return self._get("/api/vps/v1/public-keys").get("data", [])

    def create_ssh_key(self, name: str, key: str) -> Dict:
        """Add a new SSH key."""
        return self._post("/api/vps/v1/public-keys", {"name": name, "key": key})

    def attach_ssh_key(self, vm_id: int, key_ids: List[int]) -> Dict:
        """Attach SSH keys to VPS."""
        return self._post(f"/api/vps/v1/public-keys/attach/{vm_id}",
                          {"ids": key_ids})

    # ═══════════════════════════════════════════════════════════════════
    # VPS: Backups & Snapshots
    # ═══════════════════════════════════════════════════════════════════

    def list_backups(self, vm_id: int) -> List[Dict]:
        """List available backups."""
        return self._get(f"/api/vps/v1/virtual-machines/{vm_id}/backups").get("data", [])

    def restore_backup(self, vm_id: int, backup_id: int) -> Dict:
        """Restore from backup."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/backups/{backup_id}/restore")

    def get_snapshot(self, vm_id: int) -> Dict:
        """Get current snapshot info."""
        return self._get(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")

    def create_snapshot(self, vm_id: int) -> Dict:
        """Create snapshot (overwrites existing)."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")

    def restore_snapshot(self, vm_id: int) -> Dict:
        """Restore from snapshot."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot/restore")

    def delete_snapshot(self, vm_id: int) -> Dict:
        """Delete snapshot."""
        return self._delete(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")

    # ═══════════════════════════════════════════════════════════════════
    # VPS: Recovery & Actions
    # ═══════════════════════════════════════════════════════════════════

    def start_recovery(self, vm_id: int, root_password: str) -> Dict:
        """Start recovery mode (rescue boot)."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/recovery",
                          {"root_password": root_password})

    def stop_recovery(self, vm_id: int) -> Dict:
        """Stop recovery mode."""
        return self._delete(f"/api/vps/v1/virtual-machines/{vm_id}/recovery")

    def list_actions(self, vm_id: int, page: int = 1) -> List[Dict]:
        """List action history."""
        return self._get(f"/api/vps/v1/virtual-machines/{vm_id}/actions",
                         params={"page": page}).get("data", [])

    def get_action(self, vm_id: int, action_id: int) -> Dict:
        """Get specific action details."""
        return self._get(f"/api/vps/v1/virtual-machines/{vm_id}/actions/{action_id}")

    # ═══════════════════════════════════════════════════════════════════
    # VPS: OS Templates & Post-Install Scripts
    # ═══════════════════════════════════════════════════════════════════

    def list_templates(self) -> List[Dict]:
        """List available OS templates."""
        return self._get("/api/vps/v1/templates").get("data", [])

    def list_post_install_scripts(self) -> List[Dict]:
        """List post-install automation scripts."""
        return self._get("/api/vps/v1/post-install-scripts").get("data", [])

    def create_post_install_script(self, name: str, content: str) -> Dict:
        """Create a post-install script."""
        return self._post("/api/vps/v1/post-install-scripts",
                          {"name": name, "content": content})

    # ═══════════════════════════════════════════════════════════════════
    # VPS: PTR Records
    # ═══════════════════════════════════════════════════════════════════

    def create_ptr(self, vm_id: int, ip_id: int, domain: str) -> Dict:
        """Create PTR (reverse DNS) record."""
        return self._post(f"/api/vps/v1/virtual-machines/{vm_id}/ptr/{ip_id}",
                          {"domain": domain})

    # ═══════════════════════════════════════════════════════════════════
    # DNS
    # ═══════════════════════════════════════════════════════════════════

    def get_dns_records(self, domain: str) -> List[Dict]:
        """Get DNS records for a domain."""
        return self._get(f"/api/dns/v1/zones/{domain}").get("data", [])

    def update_dns_records(self, domain: str, records: List[Dict],
                            overwrite: bool = False) -> Dict:
        """Update DNS records."""
        return self._put(f"/api/dns/v1/zones/{domain}",
                         {"records": records, "overwrite": overwrite})

    # ═══════════════════════════════════════════════════════════════════
    # Billing
    # ═══════════════════════════════════════════════════════════════════

    def list_subscriptions(self) -> List[Dict]:
        """List active subscriptions."""
        return self._get("/api/billing/v1/subscriptions").get("data", [])

    def get_catalog(self, category: str = None) -> List[Dict]:
        """Get available plans and pricing."""
        params = {}
        if category:
            params["category"] = category
        return self._get("/api/billing/v1/catalog", params=params).get("data", [])

    # ═══════════════════════════════════════════════════════════════════
    # Titan-Specific Convenience Methods
    # ═══════════════════════════════════════════════════════════════════

    def find_titan_vm(self) -> Optional[Dict]:
        """Find the Titan VPS by hostname pattern."""
        vms = self.list_vms()
        for vm in vms:
            hostname = vm.get("hostname", "").lower()
            if "titan" in hostname or "lucid" in hostname:
                return vm
        return vms[0] if vms else None

    def safe_restart(self, vm_id: int) -> Dict:
        """Create snapshot then restart VPS."""
        logger.info(f"Creating snapshot before restart...")
        self.create_snapshot(vm_id)
        time.sleep(5)
        logger.info(f"Restarting VPS {vm_id}...")
        return self.restart_vm(vm_id)

    def emergency_recovery(self, vm_id: int, password: str) -> Dict:
        """Emergency recovery mode — use when SSH is broken."""
        logger.warning(f"Starting EMERGENCY RECOVERY on VPS {vm_id}")
        return self.start_recovery(vm_id, root_password=password)

    def get_vm_ip(self, vm_id: int) -> Optional[str]:
        """Get the primary IPv4 address of a VPS."""
        vm = self.get_vm(vm_id)
        ips = vm.get("data", {}).get("ip_addresses", [])
        for ip in ips:
            if ip.get("type") == "ipv4":
                return ip.get("address")
        return None

    def print_status(self):
        """Print status of all VPS instances."""
        vms = self.list_vms()
        if not vms:
            print("No VPS instances found.")
            return
        print(f"\n{'ID':<10} {'Hostname':<30} {'State':<12} {'IP':<18} {'OS':<20}")
        print("=" * 90)
        for vm in vms:
            vm_id = vm.get("id", "?")
            hostname = vm.get("hostname", "—")
            state = vm.get("state", "?")
            ips = vm.get("ip_addresses", [])
            ip = next((i["address"] for i in ips if i.get("type") == "ipv4"), "—")
            os_name = vm.get("template", {}).get("name", "—")
            print(f"{vm_id:<10} {hostname:<30} {state:<12} {ip:<18} {os_name:<20}")


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Titan VPS Client")
    parser.add_argument("action", choices=["status", "restart", "snapshot", "recovery"],
                        help="Action to perform")
    parser.add_argument("--vm-id", type=int, help="VPS ID (auto-detect if not given)")
    parser.add_argument("--token", help="API token (or set HOSTINGER_API_TOKEN)")
    parser.add_argument("--password", help="Password (for recovery mode)")
    args = parser.parse_args()

    client = TitanVPSClient(token=args.token)

    if args.action == "status":
        client.print_status()
    elif args.action == "restart":
        vm_id = args.vm_id or client.find_titan_vm().get("id")
        client.safe_restart(vm_id)
    elif args.action == "snapshot":
        vm_id = args.vm_id or client.find_titan_vm().get("id")
        client.create_snapshot(vm_id)
        print(f"Snapshot created for VPS {vm_id}")
    elif args.action == "recovery":
        vm_id = args.vm_id or client.find_titan_vm().get("id")
        client.emergency_recovery(vm_id, args.password or "TempRecovery123!")
