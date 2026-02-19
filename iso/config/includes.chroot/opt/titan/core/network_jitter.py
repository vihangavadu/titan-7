"""
TITAN V7.0 SINGULARITY — eBPF-Driven Network Micro-Jitter & Background Noise
Defeats traffic analysis by simulating realistic network entropy

V7 Enhancement: The eBPF network shield is augmented with micro-jitter injection
and background noise traffic generation. Real human users on residential connections
exhibit variance in packet timing due to network congestion and hardware latency.
Static, precise packet timing is a primary indicator of automated systems.

Architecture:
    network_jitter.py       → userspace controller for tc-netem + noise gen
    network_shield.c (eBPF) → kernel-space packet delay via BPF maps
    background_noise.py     → DNS/telemetry noise floor generation

Detection Vectors Neutralized:
    - Constant inter-packet arrival time (bot signature)
    - Zero background traffic during operations (quiet-period detection)
    - ISP-inconsistent latency variance (proxy detection)
    - Missing OS telemetry pings (NTP, OCSP, Windows Update checks)
    - Traffic burst patterns (automated form-fill detection)
"""

import hashlib
import json
import os
import random
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

__version__ = "7.0.0"
__author__ = "Dva.12"


class ConnectionType(Enum):
    """Network connection type profiles for jitter injection."""
    FIBER = "fiber"
    CABLE = "cable"
    DSL = "dsl"
    LTE_4G = "4g_lte"
    LTE_5G = "5g"
    WIFI_HOME = "wifi_home"
    WIFI_PUBLIC = "wifi_public"


@dataclass
class JitterProfile:
    """Latency and jitter parameters for a specific connection type."""
    connection_type: ConnectionType
    base_latency_ms: float          # Base RTT in milliseconds
    jitter_ms: float                # Standard deviation of jitter
    jitter_correlation: float       # Correlation % (temporal consistency)
    loss_rate: float                # Packet loss percentage
    duplicate_rate: float           # Packet duplication percentage
    reorder_rate: float             # Packet reorder percentage
    bandwidth_kbps: int             # Bandwidth limit in kbps (0 = unlimited)
    burst_size_bytes: int           # tc-netem burst size


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTION PROFILES — Realistic network characteristics per connection type
# ══════════════════════════════════════════════════════════════════════════════

JITTER_PROFILES: Dict[ConnectionType, JitterProfile] = {
    ConnectionType.FIBER: JitterProfile(
        connection_type=ConnectionType.FIBER,
        base_latency_ms=2.0,
        jitter_ms=0.5,
        jitter_correlation=25.0,
        loss_rate=0.001,
        duplicate_rate=0.0,
        reorder_rate=0.0,
        bandwidth_kbps=0,
        burst_size_bytes=32768,
    ),
    ConnectionType.CABLE: JitterProfile(
        connection_type=ConnectionType.CABLE,
        base_latency_ms=12.0,
        jitter_ms=3.0,
        jitter_correlation=30.0,
        loss_rate=0.01,
        duplicate_rate=0.001,
        reorder_rate=0.005,
        bandwidth_kbps=0,
        burst_size_bytes=16384,
    ),
    ConnectionType.DSL: JitterProfile(
        connection_type=ConnectionType.DSL,
        base_latency_ms=25.0,
        jitter_ms=8.0,
        jitter_correlation=40.0,
        loss_rate=0.05,
        duplicate_rate=0.002,
        reorder_rate=0.01,
        bandwidth_kbps=0,
        burst_size_bytes=8192,
    ),
    ConnectionType.LTE_4G: JitterProfile(
        connection_type=ConnectionType.LTE_4G,
        base_latency_ms=35.0,
        jitter_ms=15.0,
        jitter_correlation=50.0,
        loss_rate=0.1,
        duplicate_rate=0.005,
        reorder_rate=0.02,
        bandwidth_kbps=0,
        burst_size_bytes=4096,
    ),
    ConnectionType.LTE_5G: JitterProfile(
        connection_type=ConnectionType.LTE_5G,
        base_latency_ms=10.0,
        jitter_ms=5.0,
        jitter_correlation=35.0,
        loss_rate=0.02,
        duplicate_rate=0.001,
        reorder_rate=0.005,
        bandwidth_kbps=0,
        burst_size_bytes=16384,
    ),
    ConnectionType.WIFI_HOME: JitterProfile(
        connection_type=ConnectionType.WIFI_HOME,
        base_latency_ms=5.0,
        jitter_ms=2.0,
        jitter_correlation=20.0,
        loss_rate=0.005,
        duplicate_rate=0.0,
        reorder_rate=0.001,
        bandwidth_kbps=0,
        burst_size_bytes=32768,
    ),
    ConnectionType.WIFI_PUBLIC: JitterProfile(
        connection_type=ConnectionType.WIFI_PUBLIC,
        base_latency_ms=20.0,
        jitter_ms=10.0,
        jitter_correlation=45.0,
        loss_rate=0.2,
        duplicate_rate=0.01,
        reorder_rate=0.03,
        bandwidth_kbps=0,
        burst_size_bytes=4096,
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND NOISE — Domains and intervals for ambient traffic generation
# ══════════════════════════════════════════════════════════════════════════════

NOISE_DNS_DOMAINS = [
    "www.google.com", "www.googleapis.com", "clients1.google.com",
    "fonts.googleapis.com", "ajax.googleapis.com", "play.google.com",
    "www.facebook.com", "static.xx.fbcdn.net", "connect.facebook.net",
    "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com",
    "api.github.com", "github.githubassets.com",
    "www.amazon.com", "images-na.ssl-images-amazon.com",
    "www.youtube.com", "i.ytimg.com", "yt3.ggpht.com",
    "www.reddit.com", "styles.redditmedia.com",
    "twitter.com", "abs.twimg.com", "pbs.twimg.com",
    "www.linkedin.com", "static.licdn.com",
    "login.microsoftonline.com", "settings-win.data.microsoft.com",
    "ocsp.digicert.com", "ocsp.pki.goog",
    "time.windows.com", "time.google.com",
]

NOISE_TELEMETRY_URLS = [
    ("time.windows.com", 123, "udp"),      # NTP
    ("time.google.com", 123, "udp"),        # NTP
    ("ocsp.digicert.com", 80, "tcp"),       # OCSP
    ("ocsp.pki.goog", 80, "tcp"),           # OCSP
    ("crl.microsoft.com", 80, "tcp"),       # CRL
]


class NetworkJitterEngine:
    """
    eBPF-driven network micro-jitter controller.

    Applies tc-netem rules to simulate realistic network latency variance
    that matches the spoofed ISP/connection type declared in the browser profile.

    Usage:
        engine = NetworkJitterEngine()
        engine.apply_jitter(
            interface="eth0",
            connection_type=ConnectionType.CABLE
        )
        engine.start_background_noise()
        # ... operation ...
        engine.stop()
    """

    def __init__(self, interface: str = "eth0"):
        self._interface = interface
        self._active = False
        self._noise_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def apply_jitter(
        self,
        interface: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.CABLE,
        custom_profile: Optional[JitterProfile] = None,
    ) -> bool:
        """
        Apply tc-netem jitter rules to the specified network interface.
        Returns True if rules were applied successfully.
        """
        iface = interface or self._interface
        profile = custom_profile or JITTER_PROFILES.get(connection_type)
        if not profile:
            return False

        # Remove existing netem rules
        self._clear_netem(iface)

        # Build tc-netem command
        cmd = [
            "tc", "qdisc", "add", "dev", iface, "root", "netem",
            "delay", f"{profile.base_latency_ms}ms",
            f"{profile.jitter_ms}ms", f"{profile.jitter_correlation}%",
        ]

        if profile.loss_rate > 0:
            cmd.extend(["loss", "random", f"{profile.loss_rate}%"])

        if profile.duplicate_rate > 0:
            cmd.extend(["duplicate", f"{profile.duplicate_rate}%"])

        if profile.reorder_rate > 0:
            cmd.extend(["reorder", f"{profile.reorder_rate}%"])

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            self._active = True
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _clear_netem(self, interface: str) -> None:
        """Remove existing tc-netem rules from interface."""
        try:
            subprocess.run(
                ["tc", "qdisc", "del", "dev", interface, "root"],
                capture_output=True, timeout=5,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def start_background_noise(
        self,
        interval_range: Tuple[float, float] = (5.0, 30.0),
        dns_only: bool = False,
    ) -> None:
        """
        Start background noise traffic generation in a separate thread.

        Generates low-volume DNS queries and OS telemetry pings to create
        a realistic ambient traffic noise floor. This prevents "quiet period"
        detection that characterizes automated bots.
        """
        if self._noise_thread and self._noise_thread.is_alive():
            return

        self._stop_event.clear()
        self._noise_thread = threading.Thread(
            target=self._noise_loop,
            args=(interval_range, dns_only),
            daemon=True,
            name="titan-bg-noise",
        )
        self._noise_thread.start()

    def _noise_loop(
        self,
        interval_range: Tuple[float, float],
        dns_only: bool,
    ) -> None:
        """Background noise generation loop."""
        import socket

        while not self._stop_event.is_set():
            try:
                # Random DNS lookup
                domain = random.choice(NOISE_DNS_DOMAINS)
                try:
                    socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
                except (socket.gaierror, OSError):
                    pass

                # Occasional telemetry ping (not every cycle)
                if not dns_only and random.random() < 0.15:
                    host, port, proto = random.choice(NOISE_TELEMETRY_URLS)
                    try:
                        if proto == "tcp":
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(2.0)
                            s.connect((host, port))
                            s.close()
                        elif proto == "udp":
                            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            s.settimeout(2.0)
                            # NTP request (minimal 48-byte packet)
                            s.sendto(b'\x1b' + 47 * b'\0', (host, port))
                            s.close()
                    except (OSError, socket.timeout):
                        pass

            except Exception:
                pass

            # Random sleep between cycles
            delay = random.uniform(*interval_range)
            self._stop_event.wait(delay)

    def stop(self) -> None:
        """Stop background noise and remove jitter rules."""
        self._stop_event.set()
        if self._noise_thread:
            self._noise_thread.join(timeout=5.0)
        self._clear_netem(self._interface)
        self._active = False

    def get_status(self) -> Dict:
        """Get current jitter engine status."""
        return {
            "active": self._active,
            "interface": self._interface,
            "noise_running": bool(self._noise_thread and self._noise_thread.is_alive()),
        }

    def select_connection_for_isp(self, isp_name: str) -> ConnectionType:
        """Auto-select connection type based on ISP/proxy provider info."""
        isp_lower = isp_name.lower()
        if any(x in isp_lower for x in ["fiber", "fios", "att fiber", "google fiber"]):
            return ConnectionType.FIBER
        elif any(x in isp_lower for x in ["comcast", "xfinity", "spectrum", "cox", "cable"]):
            return ConnectionType.CABLE
        elif any(x in isp_lower for x in ["centurylink", "dsl", "windstream"]):
            return ConnectionType.DSL
        elif any(x in isp_lower for x in ["t-mobile", "verizon wireless", "at&t wireless", "4g", "lte"]):
            return ConnectionType.LTE_4G
        elif any(x in isp_lower for x in ["5g"]):
            return ConnectionType.LTE_5G
        else:
            return ConnectionType.CABLE


def apply_network_jitter(
    interface: str = "eth0",
    connection_type: str = "cable",
    start_noise: bool = True,
) -> NetworkJitterEngine:
    """Convenience function: apply jitter + start noise in one call."""
    engine = NetworkJitterEngine(interface=interface)
    conn = ConnectionType(connection_type)
    engine.apply_jitter(connection_type=conn)
    if start_noise:
        engine.start_background_noise()
    return engine
