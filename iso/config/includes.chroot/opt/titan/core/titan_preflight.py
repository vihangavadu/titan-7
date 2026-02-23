#!/usr/bin/env python3
"""
TITAN OS V9.0 — Pre-Operation Preflight Verification Suite
Runs 10-phase verification before any real-world operation.
Usage:
    python3 titan_preflight.py --full          # All phases
    python3 titan_preflight.py --quick         # OS + Network + Services only
    python3 titan_preflight.py --phase os      # Single phase
    python3 titan_preflight.py --phase profile --profile-path /path/to/profile
"""

import os
import sys
import json
import time
import subprocess
import sqlite3
import re
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

logger = logging.getLogger("TITAN-PREFLIGHT")

# ─── Result Tracking ─────────────────────────────────────────────────────────

class PreflightResults:
    """Tracks PASS/WARN/ANOM/FAIL across all phases."""

    def __init__(self):
        self.results: Dict[str, List[Tuple[str, str, str]]] = {
            "PASS": [], "WARN": [], "ANOM": [], "FAIL": []
        }
        self.current_phase = ""

    def _log(self, level, check, msg):
        self.results[level].append((self.current_phase, check, msg))
        icons = {"PASS": "\033[92m✓\033[0m", "WARN": "\033[93m⚠\033[0m",
                 "ANOM": "\033[95m◆\033[0m", "FAIL": "\033[91m✗\033[0m"}
        print(f"  {icons[level]} [{level}] {check}: {msg}")

    def ok(self, check, msg):   self._log("PASS", check, msg)
    def warn(self, check, msg): self._log("WARN", check, msg)
    def anom(self, check, msg): self._log("ANOM", check, msg)
    def fail(self, check, msg): self._log("FAIL", check, msg)

    def set_phase(self, name):
        self.current_phase = name
        print(f"\n{'='*60}")
        print(f"  PHASE: {name}")
        print(f"{'='*60}")

    def summary(self):
        print(f"\n{'='*60}")
        print(f"  PREFLIGHT SUMMARY")
        print(f"{'='*60}")
        for level in ["PASS", "WARN", "ANOM", "FAIL"]:
            print(f"  {level}: {len(self.results[level])}")
        print(f"{'─'*60}")

        if self.results["FAIL"]:
            print("\n  \033[91mCRITICAL FAILURES:\033[0m")
            for phase, check, msg in self.results["FAIL"]:
                print(f"    [!!] [{phase}] {check}: {msg}")

        if self.results["ANOM"]:
            print("\n  \033[95mANOMALIES (detectable):\033[0m")
            for phase, check, msg in self.results["ANOM"]:
                print(f"    [!!] [{phase}] {check}: {msg}")

        if self.results["WARN"]:
            print("\n  \033[93mWARNINGS:\033[0m")
            for phase, check, msg in self.results["WARN"]:
                print(f"    [..] [{phase}] {check}: {msg}")

        # Verdict
        print(f"\n{'='*60}")
        fails = len(self.results["FAIL"])
        anoms = len(self.results["ANOM"])
        warns = len(self.results["WARN"])

        if fails > 0:
            print("  \033[91mVERDICT: RED — NO-GO. Fix critical failures.\033[0m")
            return "RED"
        elif anoms > 5:
            print("  \033[91mVERDICT: RED — Too many anomalies (%d). Fix before proceeding.\033[0m" % anoms)
            return "RED"
        elif anoms > 0 or warns > 5:
            print("  \033[93mVERDICT: YELLOW — CAUTION. %d anomalies, %d warnings.\033[0m" % (anoms, warns))
            return "YELLOW"
        else:
            print("  \033[92mVERDICT: GREEN — GO. All checks passed.\033[0m")
            return "GREEN"


R = PreflightResults()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def cmd(args, timeout=10):
    """Run a command and return stdout, or None on failure."""
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=timeout).strip()
    except Exception:
        return None

def file_read(path):
    """Read file contents or return None."""
    try:
        return Path(path).read_text(errors="replace").strip()
    except Exception:
        return None


# ─── Phase 1: AI Model Validation ────────────────────────────────────────────

def phase_ai():
    R.set_phase("AI Models")

    # Ollama service
    status = cmd(["systemctl", "is-active", "ollama"])
    if status == "active":
        R.ok("Ollama Service", "running")
    else:
        R.fail("Ollama Service", "not running (got: %s)" % status)
        return

    # Model list
    out = cmd(["ollama", "list"])
    if out:
        models = [line.split()[0] for line in out.strip().split("\n")[1:] if line.strip()]
        required = ["qwen2.5:7b", "deepseek-r1:8b", "mistral:7b"]
        for m in required:
            found = any(m in mod for mod in models)
            R.ok("Model", m) if found else R.fail("Model", "%s not found" % m)
    else:
        R.fail("Model List", "ollama list failed")

    # LoRA adapters
    lora_dir = Path("/opt/titan/training/models_v9")
    if lora_dir.exists():
        adapters = [d.name for d in lora_dir.iterdir() if d.is_dir()]
        expected = ["titan-analyst-v9-lora", "titan-strategist-v9-lora", "titan-fast-v9-lora"]
        for e in expected:
            R.ok("LoRA Adapter", e) if e in adapters else R.warn("LoRA Adapter", "%s missing" % e)
    else:
        R.warn("LoRA Dir", "models_v9 directory not found")

    # llm_config.json
    cfg_path = Path("/opt/titan/config/llm_config.json")
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            tasks = cfg.get("task_routes", cfg.get("tasks", {}))
            count = len(tasks) if isinstance(tasks, (dict, list)) else 0
            R.ok("Task Routes", "%d configured" % count) if count >= 50 else R.warn("Task Routes", "only %d (expected 57)" % count)
        except Exception as e:
            R.fail("Config", "llm_config.json parse error: %s" % e)
    else:
        R.warn("Config", "llm_config.json not found")

    # Quick inference test
    try:
        import requests
        resp = requests.post("http://localhost:11434/api/generate",
                             json={"model": "mistral:7b", "prompt": "Say OK", "stream": False},
                             timeout=30)
        if resp.status_code == 200:
            R.ok("Inference", "mistral:7b responds (%.1fs)" % resp.elapsed.total_seconds())
        else:
            R.warn("Inference", "HTTP %d" % resp.status_code)
    except Exception as e:
        R.warn("Inference", "test failed: %s" % str(e)[:80])


# ─── Phase 2: OS Forensic Sweep ──────────────────────────────────────────────

def phase_os():
    R.set_phase("OS Forensics")

    # Hostname
    hostname = cmd(["hostname"])
    suspicious_hosts = ["titan", "kali", "parrot", "pentest", "hack", "vbox", "vmware"]
    if hostname:
        if any(s in hostname.lower() for s in suspicious_hosts):
            R.fail("Hostname", "'%s' is suspicious" % hostname)
        else:
            R.ok("Hostname", hostname)

    # DMI/SMBIOS — VM detection
    dmi_paths = {
        "product_name": "/sys/class/dmi/id/product_name",
        "sys_vendor": "/sys/class/dmi/id/sys_vendor",
        "board_vendor": "/sys/class/dmi/id/board_vendor",
        "bios_vendor": "/sys/class/dmi/id/bios_vendor",
    }
    vm_strings = ["virtualbox", "vmware", "qemu", "kvm", "xen", "bochs", "innotek",
                  "virtual machine", "bhyve", "parallels", "microsoft corporation"]
    for name, path in dmi_paths.items():
        val = file_read(path)
        if val:
            if any(v in val.lower() for v in vm_strings):
                R.fail("DMI/%s" % name, "'%s' reveals VM" % val)
            else:
                R.ok("DMI/%s" % name, val)

    # CPUID hypervisor bit
    cpuinfo = file_read("/proc/cpuinfo")
    if cpuinfo:
        if "hypervisor" in cpuinfo.lower():
            R.anom("CPUID", "hypervisor flag present in /proc/cpuinfo")
        else:
            R.ok("CPUID", "no hypervisor flag")

    # MAC address — VM vendor OUI
    vm_ouis = ["08:00:27", "52:54:00", "00:0c:29", "00:50:56", "00:1c:42", "00:16:3e"]
    ifaces = cmd(["ip", "-o", "link", "show"])
    if ifaces:
        mac_found = False
        for line in ifaces.split("\n"):
            m = re.search(r"link/ether\s+([0-9a-f:]+)", line)
            if m:
                mac = m.group(1)
                prefix = mac[:8]
                if prefix in vm_ouis:
                    R.fail("MAC Address", "%s has VM vendor OUI" % mac)
                else:
                    R.ok("MAC Address", mac)
                mac_found = True
        if not mac_found:
            R.warn("MAC Address", "no ethernet interfaces found")

    # Kernel modules — VM
    vm_modules = ["vboxguest", "vboxsf", "vboxvideo", "vmw_balloon", "vmw_vmci",
                  "vmwgfx", "virtio_balloon", "virtio_net", "xen_blkfront"]
    lsmod = cmd(["lsmod"])
    if lsmod:
        loaded = [line.split()[0] for line in lsmod.split("\n")[1:] if line.strip()]
        for vm_mod in vm_modules:
            if vm_mod in loaded:
                R.fail("Kernel Module", "%s loaded (VM indicator)" % vm_mod)
        if not any(vm_mod in loaded for vm_mod in vm_modules):
            R.ok("Kernel Modules", "no VM modules detected")

    # Process list — VM/Titan processes
    suspicious_procs = ["VBoxService", "VBoxClient", "vmtoolsd", "qemu-ga",
                        "spice-vdagent", "titan_daemon", "titan_api"]
    ps = cmd(["ps", "aux"])
    if ps:
        found_sus = [p for p in suspicious_procs if p.lower() in ps.lower()]
        if found_sus:
            R.anom("Processes", "suspicious: %s" % ", ".join(found_sus))
        else:
            R.ok("Processes", "no suspicious processes")

    # Filesystem — Titan visibility
    titan_paths = ["/opt/titan", "/etc/titan", "/var/lib/titan"]
    for tp in titan_paths:
        if Path(tp).exists():
            # Check if it's hidden/encrypted
            if Path(tp).is_mount() or not os.access(tp, os.R_OK):
                R.ok("Filesystem", "%s exists but protected" % tp)
            else:
                R.warn("Filesystem", "%s is visible and readable" % tp)

    # Systemd services
    svc_out = cmd(["systemctl", "list-units", "--type=service", "--all", "--no-pager"])
    if svc_out:
        titan_svcs = [line for line in svc_out.split("\n") if "titan" in line.lower()]
        if titan_svcs:
            R.anom("Services", "%d titan-related services visible" % len(titan_svcs))
        else:
            R.ok("Services", "no titan services visible in systemctl")

    # dpkg — installed packages
    dpkg = cmd(["dpkg", "-l"])
    if dpkg:
        titan_pkgs = [line for line in dpkg.split("\n") if "titan" in line.lower()]
        if titan_pkgs:
            R.anom("Packages", "%d titan packages in dpkg" % len(titan_pkgs))
        else:
            R.ok("Packages", "no titan packages in dpkg")

    # Bash history
    hist_files = [Path.home() / ".bash_history", Path("/root/.bash_history")]
    for hf in hist_files:
        if hf.exists():
            content = file_read(str(hf))
            if content and ("titan" in content.lower() or "ollama" in content.lower()):
                R.anom("Bash History", "%s contains titan/ollama references" % hf)
            elif content:
                R.ok("Bash History", "%s clean" % hf)

    # Log files
    log_dir = Path("/var/log")
    if log_dir.exists():
        titan_logs = list(log_dir.glob("*titan*")) + list(log_dir.glob("*ollama*"))
        if titan_logs:
            R.anom("Log Files", "%d titan/ollama log files in /var/log" % len(titan_logs))
        else:
            R.ok("Log Files", "no titan logs in /var/log")

    # Timezone
    tz = cmd(["timedatectl", "show", "--property=Timezone", "--value"])
    if tz:
        R.ok("Timezone", tz)
    else:
        tz_file = file_read("/etc/timezone")
        R.ok("Timezone", tz_file) if tz_file else R.warn("Timezone", "could not determine")


# ─── Phase 3: Network & VPN ──────────────────────────────────────────────────

def phase_network():
    R.set_phase("Network & VPN")

    # VPN status
    mullvad = cmd(["mullvad", "status"])
    if mullvad:
        if "connected" in mullvad.lower():
            R.ok("Mullvad VPN", mullvad.split("\n")[0])
        else:
            R.fail("Mullvad VPN", "not connected: %s" % mullvad.split("\n")[0])
    else:
        # Check WireGuard
        wg = cmd(["wg", "show"])
        if wg and wg.strip():
            R.ok("WireGuard", "active tunnel")
        else:
            R.fail("VPN", "no VPN connection detected (Mullvad/WireGuard)")

    # External IP
    try:
        import requests
        resp = requests.get("https://ipinfo.io/json", timeout=10)
        if resp.status_code == 200:
            ip_info = resp.json()
            ip = ip_info.get("ip", "?")
            country = ip_info.get("country", "?")
            org = ip_info.get("org", "?")
            R.ok("External IP", "%s (%s, %s)" % (ip, country, org))

            # ASN reputation check
            org_lower = org.lower()
            datacenter_keywords = ["hosting", "server", "cloud", "datacenter", "data center",
                                   "ovh", "hetzner", "digitalocean", "linode", "vultr", "aws", "azure", "gcp"]
            if any(kw in org_lower for kw in datacenter_keywords):
                R.anom("ASN", "'%s' looks like datacenter (not residential)" % org)
            else:
                R.ok("ASN", "appears residential/ISP")
        else:
            R.warn("External IP", "ipinfo.io returned %d" % resp.status_code)
    except Exception as e:
        R.warn("External IP", "check failed: %s" % str(e)[:60])

    # DNS leak check
    resolv = file_read("/etc/resolv.conf")
    if resolv:
        nameservers = re.findall(r"nameserver\s+(\S+)", resolv)
        local_dns = [ns for ns in nameservers if ns.startswith("10.") or ns.startswith("127.") or ns == "::1"]
        public_dns = [ns for ns in nameservers if ns not in local_dns]
        if public_dns:
            R.warn("DNS", "public nameservers in resolv.conf: %s (potential leak)" % ", ".join(public_dns))
        else:
            R.ok("DNS", "nameservers: %s (VPN/local)" % ", ".join(nameservers))

    # IPv6 check
    ipv6_out = cmd(["ip", "-6", "addr", "show", "scope", "global"])
    if ipv6_out and ipv6_out.strip():
        R.warn("IPv6", "global IPv6 address found — potential leak")
    else:
        R.ok("IPv6", "no global IPv6 (good)")

    # Open ports
    ss = cmd(["ss", "-tlnp"])
    if ss:
        listening = [line for line in ss.split("\n")[1:] if line.strip()]
        external = [l for l in listening if "0.0.0.0:" in l or ":::"]
        if len(external) > 10:
            R.warn("Open Ports", "%d listening ports (review for exposure)" % len(external))
        else:
            R.ok("Open Ports", "%d listening" % len(listening))


# ─── Phase 4: Browser Profile Forensics ──────────────────────────────────────

def phase_profile(profile_path=None):
    R.set_phase("Browser Profile")

    if profile_path:
        pp = Path(profile_path)
    else:
        # Auto-detect profile
        pp = _find_profile()

    if not pp or not pp.exists():
        R.fail("Profile", "no profile found (use --profile-path)")
        return

    R.ok("Profile Path", str(pp))

    # Structure check
    standard_files = ["places.sqlite", "cookies.sqlite", "prefs.js", "times.json",
                      "compatibility.ini", "extensions.json", "handlers.json",
                      "cert9.db", "key4.db", "sessionstore.js"]
    forbidden_files = ["commerce_tokens.json", "hardware_profile.json",
                       "fingerprint_config.json", "profile_metadata.json"]

    for f in standard_files:
        R.ok("File", f) if (pp / f).exists() else R.anom("Missing", f)
    for f in forbidden_files:
        R.fail("Artifact", "%s FOUND" % f) if (pp / f).exists() else R.ok("Clean", "%s absent" % f)

    # Size & age
    total = sum(f.stat().st_size for f in pp.rglob("*") if f.is_file())
    mb = total / (1024 * 1024)
    if mb >= 400:
        R.ok("Size", "%.0fMB" % mb)
    elif mb >= 100:
        R.warn("Size", "%.0fMB < 400MB" % mb)
    else:
        R.fail("Size", "%.0fMB too small" % mb)

    tj = pp / "times.json"
    if tj.exists():
        try:
            d = json.loads(tj.read_text())
            cr = d.get("created", 0)
            if cr:
                age = (datetime.now() - datetime.fromtimestamp(cr / 1000)).days
                R.ok("Age", "%dd" % age) if age >= 60 else R.fail("Age", "%dd < 60" % age)
        except Exception:
            pass

    # History forensics
    _check_history(pp)
    _check_cookies(pp)
    _check_storage(pp)
    _check_formhistory(pp)
    _check_session(pp)


def _find_profile():
    """Auto-detect most recent browser profile."""
    search_dirs = [
        Path("/opt/titan/profiles"),
        Path.home() / ".camoufox" / "profiles",
        Path.home() / ".mozilla" / "firefox",
    ]
    for sd in search_dirs:
        if sd.exists():
            dirs = [d for d in sd.iterdir() if d.is_dir() and (d / "places.sqlite").exists()]
            if dirs:
                return max(dirs, key=lambda d: d.stat().st_mtime)
    return None


def _check_history(pp):
    db = pp / "places.sqlite"
    if not db.exists():
        R.fail("History", "places.sqlite missing")
        return
    try:
        conn = sqlite3.connect(str(db))
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM moz_places")
        count = c.fetchone()[0]
        if count >= 1000:
            R.ok("History Count", "%d URLs" % count)
        elif count >= 500:
            R.warn("History Count", "%d URLs (want ≥1000)" % count)
        else:
            R.fail("History Count", "%d URLs too few" % count)

        # Visit type distribution
        c.execute("SELECT visit_type, COUNT(*) FROM moz_historyvisits GROUP BY visit_type")
        vd = dict(c.fetchall())
        tv = sum(vd.values())
        if tv > 0:
            link_pct = vd.get(1, 0) / tv * 100
            if link_pct > 95:
                R.anom("Visit Types", "%.0f%% link-only (too uniform)" % link_pct)
            else:
                typed_pct = vd.get(2, 0) / tv * 100
                bkmk_pct = vd.get(3, 0) / tv * 100
                R.ok("Visit Types", "Link=%.0f%% Typed=%.0f%% Bkmk=%.0f%%" % (link_pct, typed_pct, bkmk_pct))

        # Temporal spread
        c.execute("SELECT visit_date FROM moz_historyvisits ORDER BY visit_date")
        dates = [r[0] for r in c.fetchall()]
        if dates:
            unique_days = set(datetime.fromtimestamp(d / 1e6).date() for d in dates)
            span = (datetime.fromtimestamp(dates[-1] / 1e6) - datetime.fromtimestamp(dates[0] / 1e6)).days
            if span >= 60:
                R.ok("Temporal Spread", "%d days, %d unique" % (span, len(unique_days)))
            elif span >= 30:
                R.warn("Temporal Spread", "%d days (want ≥60)" % span)
            else:
                R.anom("Temporal Spread", "%d days — too short" % span)

            # Circadian
            hours = Counter(datetime.fromtimestamp(d / 1e6).hour for d in dates)
            night = sum(hours.get(h, 0) for h in [0, 1, 2, 3, 4]) / max(len(dates), 1) * 100
            R.ok("Circadian", "Night %.1f%%" % night) if night < 15 else R.anom("Circadian", "Night %.1f%% too high" % night)

        # Referral chains
        c.execute("SELECT COUNT(*) FROM moz_historyvisits WHERE from_visit > 0")
        fv = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM moz_historyvisits")
        tv2 = c.fetchone()[0]
        if tv2 > 0:
            fvp = fv / tv2 * 100
            R.ok("Referral Chains", "%.0f%% have referrers" % fvp) if fvp > 10 else R.anom("Referral Chains", "%.0f%% — no referral chains" % fvp)

        # Bookmarks
        c.execute("SELECT COUNT(*) FROM moz_bookmarks WHERE type=1")
        bk = c.fetchone()[0]
        R.ok("Bookmarks", "%d" % bk) if bk > 0 else R.anom("Bookmarks", "none")

        # GUID format
        c.execute("SELECT guid FROM moz_places WHERE guid IS NOT NULL LIMIT 20")
        guids = [r[0] for r in c.fetchall()]
        hex_only = sum(1 for g in guids if g and all(ch in '0123456789abcdef' for ch in g))
        if len(guids) > 0:
            R.ok("GUID Format", "base64url") if hex_only < len(guids) * 0.3 else R.anom("GUID Format", "%d/%d hex-only" % (hex_only, len(guids)))

        conn.close()
    except Exception as e:
        R.fail("History", "analysis error: %s" % str(e)[:80])


def _check_cookies(pp):
    db = pp / "cookies.sqlite"
    if not db.exists():
        R.fail("Cookies", "missing")
        return
    try:
        conn = sqlite3.connect(str(db))
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM moz_cookies")
        count = c.fetchone()[0]
        R.ok("Cookie Count", "%d" % count) if count >= 50 else R.warn("Cookie Count", "%d (want ≥50)" % count)

        # Age spread
        c.execute("SELECT creationTime FROM moz_cookies ORDER BY creationTime")
        ts = [r[0] for r in c.fetchall()]
        if len(ts) >= 2:
            spread = (datetime.fromtimestamp(ts[-1] / 1e6) - datetime.fromtimestamp(ts[0] / 1e6)).days
            R.ok("Cookie Age Spread", "%d days" % spread) if spread > 30 else R.anom("Cookie Age Spread", "%dd — batch creation" % spread)

        # Trust anchors
        c.execute("SELECT DISTINCT host FROM moz_cookies")
        hosts = set(r[0] for r in c.fetchall())
        for ta in [".google.com", ".youtube.com", ".facebook.com"]:
            R.ok("Trust Cookie", ta) if ta in hosts else R.warn("Trust Cookie", "%s missing" % ta)
        for ch in [".stripe.com", ".paypal.com", ".adyen.com"]:
            R.ok("Commerce Cookie", ch) if ch in hosts else R.warn("Commerce Cookie", "%s missing" % ch)

        # Expiry variance
        c.execute("SELECT DISTINCT expiry FROM moz_cookies")
        exps = c.fetchall()
        R.ok("Expiry Variance", "%d unique" % len(exps)) if len(exps) > 5 else R.anom("Expiry Variance", "only %d unique — batch" % len(exps))

        conn.close()
    except Exception as e:
        R.fail("Cookies", "error: %s" % str(e)[:80])


def _check_storage(pp):
    sd = pp / "storage" / "default"
    if not sd.exists():
        R.anom("LocalStorage", "storage/default missing")
        return

    domains = [d for d in sd.iterdir() if d.is_dir()]
    R.ok("Storage Domains", "%d" % len(domains))

    synthetic = 0
    total_keys = 0
    for dom_dir in domains:
        ls_db = dom_dir / "ls" / "data.sqlite"
        if not ls_db.exists():
            continue
        try:
            conn = sqlite3.connect(str(ls_db))
            c = conn.cursor()
            c.execute("SELECT key FROM data")
            keys = [r[0] for r in c.fetchall()]
            total_keys += len(keys)
            for k in keys:
                if re.match(r'^_c_\d+$', k) or re.match(r'^pad_\d+$', k) or re.match(r'^cache_\d+$', k):
                    synthetic += 1
            conn.close()
        except Exception:
            pass

    R.ok("Total LS Keys", "%d" % total_keys) if total_keys > 0 else R.anom("Total LS Keys", "0 keys")
    if synthetic > 0:
        R.anom("Synthetic Keys", "%d obvious padding patterns" % synthetic)
    else:
        R.ok("Key Quality", "no synthetic padding detected")


def _check_formhistory(pp):
    db = pp / "formhistory.sqlite"
    if not db.exists():
        R.anom("Form History", "missing")
        return
    try:
        conn = sqlite3.connect(str(db))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM moz_formhistory")
        count = c.fetchone()[0]
        R.ok("Form Entries", "%d" % count) if count > 20 else R.warn("Form Entries", "%d (want >20)" % count)

        c.execute("SELECT DISTINCT fieldname FROM moz_formhistory")
        fields = [r[0] for r in c.fetchall()]
        persona_only = all(f in ["name", "email", "tel", "address-line1", "address-level2",
                                  "address-level1", "postal-code", "country", "given-name",
                                  "family-name", "cc-name"] for f in fields)
        if persona_only and len(fields) > 0:
            R.anom("Form Diversity", "only persona fields — real users fill random forms")
        elif len(fields) > 8:
            R.ok("Form Diversity", "%d field types" % len(fields))
        else:
            R.warn("Form Diversity", "only %d field types" % len(fields))

        c.execute("SELECT COUNT(*) FROM moz_formhistory WHERE fieldname='searchbar-history'")
        sh = c.fetchone()[0]
        R.ok("Search History", "%d entries" % sh) if sh > 0 else R.anom("Search History", "no search bar history")

        conn.close()
    except Exception as e:
        R.warn("Form History", "error: %s" % str(e)[:80])


def _check_session(pp):
    sf = pp / "sessionstore.js"
    if not sf.exists():
        R.anom("Session Store", "missing")
        return
    try:
        s = json.loads(sf.read_bytes())
        wins = s.get("windows", [])
        tabs = sum(len(w.get("tabs", [])) for w in wins)
        R.ok("Open Tabs", "%d" % tabs) if tabs > 1 else R.anom("Open Tabs", "only 1 — suspicious")

        ct = sum(len(w.get("_closedTabs", [])) for w in wins)
        R.ok("Closed Tabs", "%d" % ct) if ct > 0 else R.anom("Closed Tabs", "none — real users close tabs")
    except Exception as e:
        R.warn("Session Store", "parse error: %s" % str(e)[:80])


# ─── Phase 5: Fingerprint Coherence ──────────────────────────────────────────

def phase_fingerprint():
    R.set_phase("Fingerprint Coherence")

    # Check if fingerprint_injector config exists
    fp_config = Path("/opt/titan/config/fingerprint.json")
    if fp_config.exists():
        try:
            fp = json.loads(fp_config.read_text())
            # UA ↔ Platform consistency
            ua = fp.get("userAgent", "")
            platform = fp.get("platform", "")
            if "Windows" in ua and "Win" not in platform:
                R.anom("UA↔Platform", "UA says Windows but platform='%s'" % platform)
            elif "Mac" in ua and "Mac" not in platform:
                R.anom("UA↔Platform", "UA says Mac but platform='%s'" % platform)
            elif "Linux" in ua and "Linux" not in platform:
                R.anom("UA↔Platform", "UA says Linux but platform='%s'" % platform)
            else:
                R.ok("UA↔Platform", "aligned")

            # Screen resolution
            screen = fp.get("screen", {})
            w = screen.get("width", 0)
            h = screen.get("height", 0)
            common = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900),
                      (1280, 720), (2560, 1440), (3840, 2160), (1600, 900)]
            if (w, h) in common:
                R.ok("Screen", "%dx%d (common)" % (w, h))
            elif w > 0:
                R.warn("Screen", "%dx%d (uncommon)" % (w, h))

            # Hardware concurrency
            cores = fp.get("hardwareConcurrency", 0)
            if cores in [2, 4, 6, 8, 12, 16]:
                R.ok("CPU Cores", "%d (realistic)" % cores)
            elif cores > 0:
                R.warn("CPU Cores", "%d (unusual)" % cores)

            # Device memory
            mem = fp.get("deviceMemory", 0)
            if mem in [4, 8, 16, 32]:
                R.ok("Device Memory", "%dGB" % mem)
            elif mem > 0:
                R.warn("Device Memory", "%dGB (unusual)" % mem)

            R.ok("Fingerprint Config", "loaded with %d properties" % len(fp))
        except Exception as e:
            R.warn("Fingerprint Config", "parse error: %s" % str(e)[:80])
    else:
        R.warn("Fingerprint Config", "fingerprint.json not found — using Camoufox defaults")

    # JA4 / TLS check
    ja4_config = Path("/opt/titan/config/ja4_profile.json")
    if ja4_config.exists():
        R.ok("JA4 Profile", "configured")
    else:
        R.warn("JA4 Profile", "no ja4_profile.json — using default TLS")

    # Check Camoufox binary
    camoufox = Path("/opt/camoufox/camoufox")
    if camoufox.exists():
        R.ok("Camoufox", "binary present")
    else:
        R.warn("Camoufox", "binary not found at /opt/camoufox/camoufox")


# ─── Phase 6: Identity & Persona ─────────────────────────────────────────────

def phase_identity():
    R.set_phase("Identity & Persona")

    # Look for active persona
    persona_paths = [
        Path("/opt/titan/data/active_persona.json"),
        Path("/opt/titan/config/persona.json"),
        Path("/opt/titan/profiles/active/persona.json"),
    ]

    persona = None
    for pp in persona_paths:
        if pp.exists():
            try:
                persona = json.loads(pp.read_text())
                R.ok("Persona File", str(pp))
                break
            except Exception:
                pass

    if not persona:
        R.warn("Persona", "no active persona file found — manual check needed")
        return

    # Field presence
    required = ["first_name", "last_name", "email", "phone", "address", "city", "state", "zip", "country"]
    for field in required:
        if persona.get(field):
            R.ok("Field", "%s = %s" % (field, str(persona[field])[:30]))
        else:
            R.fail("Field", "%s is missing" % field)

    # Email domain check
    email = persona.get("email", "")
    if email:
        domain = email.split("@")[-1] if "@" in email else ""
        disposable = ["tempmail.com", "guerrillamail.com", "mailinator.com", "yopmail.com",
                      "throwaway.email", "10minutemail.com", "trashmail.com"]
        if domain in disposable:
            R.fail("Email", "'%s' is disposable" % domain)
        elif domain in ["gmail.com", "outlook.com", "yahoo.com", "icloud.com", "protonmail.com"]:
            R.ok("Email", "%s (major provider)" % domain)
        else:
            R.warn("Email", "'%s' — verify it's established" % domain)

    # Phone ↔ Country
    phone = persona.get("phone", "")
    country = persona.get("country", "")
    if phone and country:
        # Basic check: US phone should start with +1
        country_codes = {"US": "+1", "GB": "+44", "DE": "+49", "FR": "+33", "AU": "+61", "CA": "+1"}
        expected = country_codes.get(country, "")
        if expected and phone.startswith(expected):
            R.ok("Phone↔Country", "aligned (%s → %s)" % (country, expected))
        elif expected:
            R.warn("Phone↔Country", "phone '%s' doesn't match country %s (expected %s)" % (phone[:6], country, expected))


# ─── Phase 7: Service Health ─────────────────────────────────────────────────

def phase_services():
    R.set_phase("Service Health")

    services = {
        "Redis": ("redis-cli", ["redis-cli", "ping"], "PONG"),
        "Ollama": ("systemctl", ["systemctl", "is-active", "ollama"], "active"),
        "Xray": ("systemctl", ["systemctl", "is-active", "xray"], "active"),
    }

    for name, (_, cmd_args, expected) in services.items():
        result = cmd(cmd_args)
        if result and expected.lower() in result.lower():
            R.ok(name, result)
        else:
            R.fail(name, "expected '%s', got '%s'" % (expected, result))

    # Mullvad (warn only, not fail — might use WireGuard directly)
    mullvad = cmd(["mullvad", "status"])
    if mullvad and "connected" in mullvad.lower():
        R.ok("Mullvad", mullvad.split("\n")[0])
    else:
        R.warn("Mullvad", "not connected (check WireGuard manually)")

    # ntfy
    try:
        import requests
        resp = requests.get("http://localhost:8090/health", timeout=5)
        R.ok("ntfy", "healthy") if resp.status_code == 200 else R.warn("ntfy", "HTTP %d" % resp.status_code)
    except Exception:
        R.warn("ntfy", "not reachable on :8090")

    # Camoufox
    camoufox = Path("/opt/camoufox/camoufox")
    R.ok("Camoufox", "binary present") if camoufox.exists() else R.fail("Camoufox", "not found")

    # Core module imports
    try:
        sys.path.insert(0, "/opt/titan")
        importable = 0
        total = 0
        core_dir = Path("/opt/titan/core")
        if core_dir.exists():
            for py in core_dir.glob("*.py"):
                if py.name.startswith("__"):
                    continue
                total += 1
                mod_name = py.stem
                try:
                    __import__("core.%s" % mod_name)
                    importable += 1
                except Exception:
                    pass
            if total > 0:
                pct = importable / total * 100
                R.ok("Core Modules", "%d/%d importable (%.0f%%)" % (importable, total, pct)) if pct > 95 else R.warn("Core Modules", "%d/%d importable (%.0f%%)" % (importable, total, pct))
    except Exception as e:
        R.warn("Core Modules", "import test failed: %s" % str(e)[:60])


# ─── Phase 9: AI-Powered Analysis ────────────────────────────────────────────

def phase_ai_analysis():
    R.set_phase("AI Deep Analysis")

    try:
        import requests
    except ImportError:
        R.warn("AI Analysis", "requests module not available")
        return

    tasks = [
        ("detection_prediction", "mistral:7b",
         "Analyze this system for antifraud detection risks. List top 5 detection vectors that could flag this as automated/synthetic. System: Linux Debian, Camoufox browser, VPN active, synthetic browser profile."),
        ("persona_consistency_check", "qwen2.5:7b",
         "Check this persona for consistency issues: Name: John Smith, Email: john.smith@gmail.com, Phone: +1-555-0123, Country: US, City: New York. List any inconsistencies or red flags."),
    ]

    for task_name, model, prompt in tasks:
        try:
            resp = requests.post("http://localhost:11434/api/generate",
                                 json={"model": model, "prompt": prompt, "stream": False},
                                 timeout=60)
            if resp.status_code == 200:
                answer = resp.json().get("response", "")
                if len(answer) > 50:
                    R.ok("AI/%s" % task_name, "responded (%d chars, %.1fs)" % (len(answer), resp.elapsed.total_seconds()))
                else:
                    R.warn("AI/%s" % task_name, "short response (%d chars)" % len(answer))
            else:
                R.warn("AI/%s" % task_name, "HTTP %d" % resp.status_code)
        except Exception as e:
            R.warn("AI/%s" % task_name, "failed: %s" % str(e)[:60])


# ─── Main ────────────────────────────────────────────────────────────────────

PHASES = {
    "ai": phase_ai,
    "os": phase_os,
    "network": phase_network,
    "profile": phase_profile,
    "fingerprint": phase_fingerprint,
    "identity": phase_identity,
    "services": phase_services,
    "ai-analysis": phase_ai_analysis,
}

QUICK_PHASES = ["os", "network", "services"]
FULL_PHASES = ["ai", "os", "network", "services", "fingerprint", "identity", "profile", "ai-analysis"]


def main():
    parser = argparse.ArgumentParser(description="TITAN OS Pre-Operation Preflight")
    parser.add_argument("--full", action="store_true", help="Run all phases")
    parser.add_argument("--quick", action="store_true", help="Quick check (OS + Network + Services)")
    parser.add_argument("--phase", type=str, help="Run specific phase")
    parser.add_argument("--profile-path", type=str, help="Path to browser profile directory")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  TITAN OS V9.0 — PRE-OPERATION PREFLIGHT")
    print("  %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    if args.phase:
        if args.phase not in PHASES:
            print("Unknown phase: %s\nAvailable: %s" % (args.phase, ", ".join(PHASES.keys())))
            sys.exit(1)
        if args.phase == "profile":
            phase_profile(args.profile_path)
        else:
            PHASES[args.phase]()
    elif args.quick:
        for p in QUICK_PHASES:
            PHASES[p]()
    elif args.full:
        for p in FULL_PHASES:
            if p == "profile":
                phase_profile(args.profile_path)
            else:
                PHASES[p]()
    else:
        # Default: full
        for p in FULL_PHASES:
            if p == "profile":
                phase_profile(args.profile_path)
            else:
                PHASES[p]()

    verdict = R.summary()
    print()
    sys.exit(0 if verdict == "GREEN" else 1)


if __name__ == "__main__":
    main()
