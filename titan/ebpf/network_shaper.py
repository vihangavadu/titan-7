#!/usr/bin/env python3
"""
TITAN Network Behavioral Shaper — TC/NetEm Residential Wire Signature

Authority: Dva.12 | Status: TITAN_ACTIVE | Version: 7.0

Defeats temporal network fingerprinting by injecting realistic latency,
jitter, and packet loss patterns using Linux Traffic Control (TC) with
the NetEm (Network Emulation) scheduler.

Static header spoofing (TTL, TCP Window) via eBPF is necessary but
insufficient. Datacenter connections exhibit flatline latency (~1ms jitter)
while residential connections show 5-50ms jitter with occasional loss.
A "Verizon Fios Residential User" with AWS-like latency consistency is
mathematically detectable.

This module layers AFTER the eBPF Network Shield to ensure shaped packets
also carry correct OS fingerprint headers.

Network topology:
  Application → TC/NetEm (jitter/loss) → eBPF/XDP (header rewrite) → Wire

Manual operation model: The user selects a network profile from the TITAN
Console before starting a session. No browser automation.
"""

import subprocess
import logging
import json
import os
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional

PROFILE_PATH = "/opt/lucid-empire/profiles/active"

# ============================================================================
# Pre-defined residential network profiles
# ============================================================================

@dataclass
class NetworkProfile:
    """Defines the temporal characteristics of a network connection type."""
    name: str
    description: str
    delay_ms: int           # Base one-way delay (ms)
    jitter_ms: int          # Delay variance (ms)
    distribution: str       # "normal", "pareto", "paretonormal"
    loss_percent: float     # Packet loss rate (%)
    loss_correlation: float # Loss correlation (% — bursty loss)
    duplicate_percent: float  # Packet duplication rate (%)
    reorder_percent: float  # Packet reordering rate (%)
    rate_kbit: Optional[int] = None  # Bandwidth cap (kbit/s), None = unlimited
    corrupt_percent: float = 0.0


# Residential profiles based on real-world ISP measurements
NETWORK_PROFILES = {
    "residential_fiber": NetworkProfile(
        name="residential_fiber",
        description="Residential Fiber (Verizon Fios / AT&T Fiber)",
        delay_ms=8,
        jitter_ms=3,
        distribution="normal",
        loss_percent=0.01,
        loss_correlation=25.0,
        duplicate_percent=0.0,
        reorder_percent=0.0,
        rate_kbit=None,  # Fiber — no meaningful cap
    ),
    "residential_cable": NetworkProfile(
        name="residential_cable",
        description="Residential Cable (Comcast / Spectrum)",
        delay_ms=18,
        jitter_ms=8,
        distribution="normal",
        loss_percent=0.05,
        loss_correlation=30.0,
        duplicate_percent=0.01,
        reorder_percent=0.1,
        rate_kbit=None,
    ),
    "residential_dsl": NetworkProfile(
        name="residential_dsl",
        description="Residential DSL (CenturyLink / Frontier)",
        delay_ms=35,
        jitter_ms=12,
        distribution="normal",
        loss_percent=0.1,
        loss_correlation=25.0,
        duplicate_percent=0.02,
        reorder_percent=0.2,
        rate_kbit=50000,  # 50 Mbps
    ),
    "mobile_4g": NetworkProfile(
        name="mobile_4g",
        description="4G LTE Mobile (T-Mobile / Verizon)",
        delay_ms=45,
        jitter_ms=20,
        distribution="paretonormal",
        loss_percent=0.3,
        loss_correlation=35.0,
        duplicate_percent=0.05,
        reorder_percent=0.5,
        rate_kbit=30000,  # 30 Mbps
    ),
    "mobile_5g": NetworkProfile(
        name="mobile_5g",
        description="5G Mobile (mmWave / Sub-6)",
        delay_ms=15,
        jitter_ms=10,
        distribution="normal",
        loss_percent=0.1,
        loss_correlation=20.0,
        duplicate_percent=0.02,
        reorder_percent=0.3,
        rate_kbit=100000,  # 100 Mbps
    ),
    "coffee_shop_wifi": NetworkProfile(
        name="coffee_shop_wifi",
        description="Public WiFi (Starbucks / Airport)",
        delay_ms=25,
        jitter_ms=15,
        distribution="paretonormal",
        loss_percent=0.5,
        loss_correlation=40.0,
        duplicate_percent=0.1,
        reorder_percent=1.0,
        rate_kbit=20000,  # 20 Mbps
    ),
    "datacenter": NetworkProfile(
        name="datacenter",
        description="Datacenter / VPS (DO NOT USE for residential personas)",
        delay_ms=1,
        jitter_ms=0,
        distribution="normal",
        loss_percent=0.0,
        loss_correlation=0.0,
        duplicate_percent=0.0,
        reorder_percent=0.0,
    ),
}


class NetworkShaper:
    """
    Manages TC/NetEm qdisc rules to shape outgoing traffic to match
    a residential network profile.
    """

    def __init__(self, interface="eth0"):
        self.interface = interface
        self.logger = logging.getLogger("NetworkShaper")
        logging.basicConfig(level=logging.INFO,
                            format="[TITAN-NET] %(levelname)s: %(message)s")
        self.active_profile = None
        self._monitor_thread = None
        self._monitor_stop = threading.Event()

    def _run_tc(self, args, check=True):
        """Execute a tc command."""
        cmd = ["tc"] + args
        self.logger.debug(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=10)
            if check and result.returncode != 0:
                # Ignore "RTNETLINK: No such file" (qdisc doesn't exist yet)
                if "No such file" not in result.stderr:
                    self.logger.warning(f"tc command failed: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            self.logger.error("tc command timed out")
            return None
        except FileNotFoundError:
            self.logger.error("tc binary not found — install iproute2")
            return None

    def _detect_interface(self):
        """Auto-detect the primary network interface."""
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if "dev" in parts:
                    idx = parts.index("dev") + 1
                    if idx < len(parts):
                        detected = parts[idx]
                        self.logger.info(f"Auto-detected interface: {detected}")
                        return detected
        except Exception:
            pass
        return self.interface

    def clear(self):
        """Remove all existing tc/netem rules from the interface."""
        self._run_tc(["qdisc", "del", "dev", self.interface, "root"],
                     check=False)
        self.active_profile = None
        self.logger.info(f"Cleared all TC rules on {self.interface}")

    def apply_profile(self, profile_name="residential_fiber"):
        """
        Apply a network shaping profile to the interface.

        Args:
            profile_name: Key into NETWORK_PROFILES or path to custom JSON.
        """
        # Try loading from active persona first
        profile = self._load_profile_override()

        if profile is None:
            if profile_name in NETWORK_PROFILES:
                profile = NETWORK_PROFILES[profile_name]
            else:
                self.logger.error(f"Unknown profile: {profile_name}")
                return False

        # Auto-detect interface if needed
        self.interface = self._detect_interface()

        # Clear existing rules
        self.clear()

        # Build netem command
        netem_args = [
            "qdisc", "add", "dev", self.interface, "root", "netem",
            "delay", f"{profile.delay_ms}ms", f"{profile.jitter_ms}ms",
        ]

        # Distribution (requires /usr/lib/tc/ distribution tables)
        if profile.distribution in ("normal", "pareto", "paretonormal"):
            netem_args.extend(["distribution", profile.distribution])

        # Packet loss with correlation
        if profile.loss_percent > 0:
            netem_args.extend([
                "loss", f"{profile.loss_percent}%",
                f"{profile.loss_correlation}%"
            ])

        # Packet duplication
        if profile.duplicate_percent > 0:
            netem_args.extend(["duplicate", f"{profile.duplicate_percent}%"])

        # Packet reordering
        if profile.reorder_percent > 0:
            netem_args.extend([
                "reorder", f"{100 - profile.reorder_percent}%",
                f"50%"  # Reorder correlation
            ])

        # Packet corruption
        if profile.corrupt_percent > 0:
            netem_args.extend(["corrupt", f"{profile.corrupt_percent}%"])

        # Apply netem qdisc
        result = self._run_tc(netem_args)
        if result is None or result.returncode != 0:
            self.logger.error("Failed to apply netem qdisc")
            return False

        # Apply bandwidth cap if specified (using tbf as child qdisc)
        if profile.rate_kbit is not None and profile.rate_kbit > 0:
            # Token Bucket Filter for rate limiting
            rate = f"{profile.rate_kbit}kbit"
            burst = max(profile.rate_kbit // 8, 1600)  # bytes
            latency_ms = max(profile.delay_ms * 2, 50)

            tbf_args = [
                "qdisc", "add", "dev", self.interface,
                "parent", "1:1", "handle", "10:",
                "tbf", "rate", rate,
                "burst", str(burst),
                "latency", f"{latency_ms}ms",
            ]
            self._run_tc(tbf_args, check=False)

        self.active_profile = profile
        self.logger.info(
            f"Applied network profile: {profile.name} "
            f"(delay={profile.delay_ms}±{profile.jitter_ms}ms, "
            f"loss={profile.loss_percent}%)")
        return True

    def _load_profile_override(self):
        """Load custom network profile from active persona directory."""
        profile_file = os.path.join(PROFILE_PATH, "network_profile.json")
        if os.path.exists(profile_file):
            try:
                with open(profile_file, 'r') as f:
                    data = json.load(f)
                return NetworkProfile(**data)
            except (json.JSONDecodeError, TypeError, IOError) as e:
                self.logger.warning(f"Failed to load network profile override: {e}")
        return None

    def get_status(self):
        """Return current shaping status for console display."""
        result = self._run_tc(
            ["qdisc", "show", "dev", self.interface], check=False)

        status = {
            "interface": self.interface,
            "active": self.active_profile is not None,
            "profile": self.active_profile.name if self.active_profile else None,
            "tc_output": result.stdout.strip() if result else "unavailable",
        }

        if self.active_profile:
            status["parameters"] = {
                "delay_ms": self.active_profile.delay_ms,
                "jitter_ms": self.active_profile.jitter_ms,
                "loss_percent": self.active_profile.loss_percent,
                "distribution": self.active_profile.distribution,
            }

        return status

    # ========================================================================
    # Passive RTT Monitoring (Adaptive Shaping Feedback Loop)
    # ========================================================================

    def start_rtt_monitor(self, target_delay_ms=None, interval_sec=30):
        """
        Start a background thread that monitors actual RTT and adjusts
        local netem parameters to maintain the target residential profile.

        If the upstream proxy introduces unexpected latency, the local
        jitter is reduced to compensate, keeping total delay in range.
        """
        if self.active_profile is None:
            self.logger.warning("No active profile — cannot start RTT monitor")
            return

        target = target_delay_ms or self.active_profile.delay_ms
        self._monitor_stop.clear()

        def _monitor_loop():
            while not self._monitor_stop.is_set():
                measured_rtt = self._measure_rtt()
                if measured_rtt is not None and self.active_profile:
                    # If actual RTT exceeds target, reduce local netem delay
                    excess = measured_rtt - target
                    if excess > 5:  # More than 5ms over target
                        adjusted_delay = max(
                            1, self.active_profile.delay_ms - int(excess))
                        self.logger.info(
                            f"RTT monitor: measured={measured_rtt}ms, "
                            f"adjusting local delay to {adjusted_delay}ms")
                        self._adjust_delay(adjusted_delay,
                                           self.active_profile.jitter_ms)
                self._monitor_stop.wait(interval_sec)

        self._monitor_thread = threading.Thread(
            target=_monitor_loop, daemon=True, name="titan-rtt-monitor")
        self._monitor_thread.start()
        self.logger.info(
            f"RTT monitor started (target={target}ms, interval={interval_sec}s)")

    def stop_rtt_monitor(self):
        """Stop the background RTT monitoring thread."""
        self._monitor_stop.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        self.logger.info("RTT monitor stopped")

    def _measure_rtt(self):
        """
        Measure actual RTT to a well-known server via TCP connect timing.
        Uses a lightweight approach — no ICMP pings (often blocked).
        """
        import socket
        targets = [
            ("www.google.com", 443),
            ("www.amazon.com", 443),
            ("www.cloudflare.com", 443),
        ]

        for host, port in targets:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                start = time.monotonic()
                sock.connect((host, port))
                rtt = (time.monotonic() - start) * 1000  # ms
                sock.close()
                return round(rtt, 1)
            except (socket.timeout, OSError):
                continue
        return None

    def _adjust_delay(self, new_delay_ms, jitter_ms):
        """Dynamically adjust netem delay without tearing down the qdisc."""
        self._run_tc([
            "qdisc", "change", "dev", self.interface, "root", "netem",
            "delay", f"{new_delay_ms}ms", f"{jitter_ms}ms",
            "distribution", self.active_profile.distribution,
        ], check=False)


def list_profiles():
    """Print available network profiles."""
    print("\nAvailable Network Profiles:")
    print("-" * 70)
    for key, profile in NETWORK_PROFILES.items():
        print(f"  {key:25s} | {profile.delay_ms:3d}±{profile.jitter_ms:<3d}ms "
              f"| loss {profile.loss_percent:.2f}% | {profile.description}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="TITAN Network Behavioral Shaper")
    parser.add_argument("action", choices=["apply", "clear", "status", "list"],
                        help="Action to perform")
    parser.add_argument("--profile", "-p", default="residential_fiber",
                        help="Network profile name")
    parser.add_argument("--interface", "-i", default="eth0",
                        help="Network interface")
    args = parser.parse_args()

    shaper = NetworkShaper(interface=args.interface)

    if args.action == "list":
        list_profiles()
    elif args.action == "apply":
        shaper.apply_profile(args.profile)
    elif args.action == "clear":
        shaper.clear()
    elif args.action == "status":
        status = shaper.get_status()
        print(json.dumps(status, indent=2))
