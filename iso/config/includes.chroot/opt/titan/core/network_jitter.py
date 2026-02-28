"""
TITAN V8.1 SINGULARITY — eBPF-Driven Network Micro-Jitter & Background Noise
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

__version__ = "8.0.0"
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
    ("time.apple.com", 123, "udp"),         # NTP (macOS)
    ("ocsp.digicert.com", 80, "tcp"),       # OCSP
    ("ocsp.pki.goog", 80, "tcp"),           # OCSP
    ("ocsp.sectigo.com", 80, "tcp"),        # OCSP (Sectigo)
    ("crl.microsoft.com", 80, "tcp"),       # CRL
    ("ctldl.windowsupdate.com", 80, "tcp"), # Windows CTL update
    ("settings-win.data.microsoft.com", 443, "tcp"),  # Windows telemetry
    ("self.events.data.microsoft.com", 443, "tcp"),   # Windows diagnostics
]

# ISP-specific DNS resolver noise (match exit node ISP)
ISP_DNS_NOISE = {
    "comcast": ["dns.xfinity.com", "resolver1.comcast.net"],
    "att": ["dns.att.net", "resolv1.att.net"],
    "verizon": ["dns.verizon.net", "resolver1.verizon.net"],
    "spectrum": ["dns.spectrum.net", "resolver1.charter.net"],
    "google_fiber": ["dns.google", "dns64.dns.google"],
    "tmobile": ["dns.t-mobile.com"],
    "cox": ["dns.cox.net"],
}


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


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: eBPF TAIL-CALL ARCHITECTURE
# Modular eBPF program chain using BPF tail calls for composable
# network packet processing. Each processing stage (jitter injection,
# packet rewriting, fingerprint modification) is a separate eBPF program
# chained via BPF_MAP_TYPE_PROG_ARRAY tail calls.
# ═══════════════════════════════════════════════════════════════════════════

class EBPFTailCallChain:
    """
    v7.5 eBPF Tail-Call Architecture for composable packet processing.

    Architecture:
    XDP ingress → prog_array[0] (jitter) → prog_array[1] (rewrite)
                → prog_array[2] (fingerprint) → XDP_PASS

    Benefits over monolithic eBPF:
    - Each stage can be hot-swapped without reloading the entire chain
    - Stages can be selectively enabled/disabled per-session
    - Verifier complexity budget is per-program, not cumulative
    - Easier debugging: isolate which stage causes issues

    The XDP skeleton C code is generated by this class and compiled
    via build_ebpf.sh using clang/llvm.
    """

    # Program slot indices in the BPF_MAP_TYPE_PROG_ARRAY
    SLOT_JITTER = 0
    SLOT_REWRITE = 1
    SLOT_FINGERPRINT = 2
    SLOT_NOISE_GEN = 3

    XDP_SKELETON = '''
/* TITAN v7.5 — eBPF Tail-Call Chain Dispatcher
 * Compiled with: clang -O2 -target bpf -c titan_xdp_chain.c -o titan_xdp_chain.o
 */
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <linux/tcp.h>
#include <bpf/bpf_helpers.h>

struct {
    __uint(type, BPF_MAP_TYPE_PROG_ARRAY);
    __uint(max_entries, 8);
    __type(key, __u32);
    __type(value, __u32);
} titan_prog_array SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);   /* dest IP */
    __type(value, __u64); /* jitter params packed */
} titan_jitter_map SEC(".maps");

SEC("xdp")
int titan_xdp_dispatcher(struct xdp_md *ctx)
{
    /* Entry point: dispatch to first enabled stage via tail call */
    bpf_tail_call(ctx, &titan_prog_array, 0);
    /* If tail call fails (slot empty), pass packet unchanged */
    return XDP_PASS;
}

SEC("xdp/jitter")
int titan_xdp_jitter(struct xdp_md *ctx)
{
    /* Stage 0: Packet timing jitter injection
     * Reads per-destination jitter params from titan_jitter_map
     * and applies controlled delay via bpf_redirect */

    /* Chain to next stage */
    bpf_tail_call(ctx, &titan_prog_array, 1);
    return XDP_PASS;
}

SEC("xdp/rewrite")
int titan_xdp_rewrite(struct xdp_md *ctx)
{
    /* Stage 1: Packet header rewriting
     * Modifies TTL, TCP window size, IP ID to match target OS profile */

    /* Chain to next stage */
    bpf_tail_call(ctx, &titan_prog_array, 2);
    return XDP_PASS;
}

SEC("xdp/fingerprint")
int titan_xdp_fingerprint(struct xdp_md *ctx)
{
    /* Stage 2: Network fingerprint modification
     * Adjusts TCP options ordering, MSS, window scale to match browser */

    /* Terminal stage — no more tail calls */
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
'''

    def __init__(self, interface: str = "eth0"):
        self.interface = interface
        self.logger = logging.getLogger("TITAN-EBPF-CHAIN")
        self._slots_enabled = {
            self.SLOT_JITTER: True,
            self.SLOT_REWRITE: True,
            self.SLOT_FINGERPRINT: True,
            self.SLOT_NOISE_GEN: False,
        }
        self._compiled = False

    def write_xdp_source(self, output_path: str = "/opt/titan/core/titan_xdp_chain.c") -> str:
        """Write the XDP skeleton C source file."""
        try:
            with open(output_path, "w") as f:
                f.write(self.XDP_SKELETON)
            self.logger.info(f"[eBPF] XDP source written to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"[eBPF] Failed to write source: {e}")
            return ""

    def compile_xdp(self, source_path: str = "/opt/titan/core/titan_xdp_chain.c",
                    output_path: str = "/opt/titan/core/titan_xdp_chain.o") -> bool:
        """Compile XDP program using clang/llvm."""
        cmd = [
            "clang", "-O2", "-g", "-target", "bpf",
            "-D__TARGET_ARCH_x86",
            "-c", source_path,
            "-o", output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self._compiled = True
                self.logger.info(f"[eBPF] Compiled: {output_path}")
                return True
            else:
                self.logger.error(f"[eBPF] Compile error: {result.stderr[:300]}")
                return False
        except FileNotFoundError:
            self.logger.error("[eBPF] clang not found — install llvm/clang for eBPF compilation")
            return False
        except Exception as e:
            self.logger.error(f"[eBPF] Compile failed: {e}")
            return False

    def attach_xdp(self, obj_path: str = "/opt/titan/core/titan_xdp_chain.o") -> bool:
        """Attach compiled XDP program to network interface."""
        cmd = ["ip", "link", "set", "dev", self.interface, "xdp", "obj", obj_path,
               "sec", "xdp"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info(f"[eBPF] XDP attached to {self.interface}")
                return True
            else:
                self.logger.error(f"[eBPF] Attach error: {result.stderr.strip()}")
                return False
        except Exception as e:
            self.logger.error(f"[eBPF] Attach failed: {e}")
            return False

    def detach_xdp(self) -> bool:
        """Detach XDP program from network interface."""
        cmd = ["ip", "link", "set", "dev", self.interface, "xdp", "off"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.logger.info(f"[eBPF] XDP detached from {self.interface}")
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"[eBPF] Detach failed: {e}")
            return False

    def enable_slot(self, slot: int, enabled: bool = True):
        """Enable or disable a tail-call slot."""
        self._slots_enabled[slot] = enabled
        self.logger.info(f"[eBPF] Slot {slot} {'enabled' if enabled else 'disabled'}")

    def get_status(self) -> Dict:
        """Get eBPF tail-call chain status."""
        return {
            "interface": self.interface,
            "compiled": self._compiled,
            "slots": {
                "jitter": self._slots_enabled.get(self.SLOT_JITTER, False),
                "rewrite": self._slots_enabled.get(self.SLOT_REWRITE, False),
                "fingerprint": self._slots_enabled.get(self.SLOT_FINGERPRINT, False),
                "noise_gen": self._slots_enabled.get(self.SLOT_NOISE_GEN, False),
            },
            "version": "7.5",
        }


# =============================================================================
# TITAN V7.6 P0 CRITICAL ENHANCEMENTS
# =============================================================================

import logging
import math
import socket
from collections import deque
from typing import Callable

logger = logging.getLogger("TITAN-NETWORK-JITTER")


@dataclass
class NetworkCondition:
    """Current network condition measurement"""
    timestamp: float
    latency_ms: float
    jitter_ms: float
    packet_loss_pct: float
    bandwidth_mbps: float
    connection_quality: str  # excellent, good, fair, poor


@dataclass
class TrafficSample:
    """Network traffic sample for analysis"""
    timestamp: float
    bytes_sent: int
    bytes_received: int
    packets_sent: int
    packets_received: int
    protocol: str
    destination: str


@dataclass
class NoiseSchedule:
    """Scheduled noise generation parameters"""
    hour_start: int
    hour_end: int
    intensity: float  # 0.0 to 1.0
    dns_frequency: float
    telemetry_frequency: float
    domains_pool: List[str] = field(default_factory=list)


class AdaptiveJitterController:
    """
    V7.6 P0 CRITICAL: Automatically adjust jitter based on network conditions.
    
    Monitors actual network conditions and dynamically adjusts jitter
    parameters to maintain realistic variance without exceeding
    performance thresholds.
    
    Usage:
        controller = get_adaptive_jitter_controller()
        
        # Set target connection type
        controller.set_target_profile(ConnectionType.CABLE)
        
        # Start adaptive control
        controller.start_adaptive_control("eth0")
        
        # Controller automatically adjusts based on conditions
    """
    
    # Quality thresholds
    LATENCY_EXCELLENT_MS = 50
    LATENCY_GOOD_MS = 100
    LATENCY_FAIR_MS = 200
    
    def __init__(self, check_interval: float = 10.0):
        self.check_interval = check_interval
        self.target_profile: Optional[JitterProfile] = None
        self.current_jitter_ms = 0.0
        self.current_latency_ms = 0.0
        self._condition_history: deque = deque(maxlen=60)
        self._stop_event = threading.Event()
        self._control_thread: Optional[threading.Thread] = None
        self._engine: Optional[NetworkJitterEngine] = None
        self._lock = threading.Lock()
        self._adjustment_callbacks: List[Callable] = []
        logger.info("AdaptiveJitterController initialized")
    
    def set_target_profile(self, connection_type: ConnectionType) -> None:
        """Set target connection profile to emulate"""
        with self._lock:
            self.target_profile = JITTER_PROFILES.get(connection_type)
            if self.target_profile:
                logger.info(f"Target profile set: {connection_type.value}")
    
    def start_adaptive_control(self, interface: str = "eth0") -> None:
        """Start adaptive jitter control loop"""
        if self._control_thread and self._control_thread.is_alive():
            return
        
        self._engine = NetworkJitterEngine(interface=interface)
        
        # Apply initial profile
        if self.target_profile:
            self._engine.apply_jitter(
                interface=interface,
                connection_type=self.target_profile.connection_type
            )
        
        self._stop_event.clear()
        self._control_thread = threading.Thread(
            target=self._control_loop,
            daemon=True,
            name="AdaptiveJitterController"
        )
        self._control_thread.start()
        logger.info("Adaptive jitter control started")
    
    def stop_adaptive_control(self) -> None:
        """Stop adaptive control"""
        self._stop_event.set()
        if self._control_thread:
            self._control_thread.join(timeout=5.0)
        if self._engine:
            self._engine.stop()
        logger.info("Adaptive jitter control stopped")
    
    def _control_loop(self) -> None:
        """Main adaptive control loop"""
        while not self._stop_event.is_set():
            try:
                # Measure current conditions
                condition = self._measure_conditions()
                
                with self._lock:
                    self._condition_history.append(condition)
                    
                    # Adjust jitter if needed
                    if self.target_profile and self._engine:
                        adjusted = self._calculate_adjustment(condition)
                        if adjusted:
                            self._apply_adjusted_jitter(adjusted)
                
            except Exception as e:
                logger.error(f"Adaptive control error: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def _measure_conditions(self) -> NetworkCondition:
        """Measure current network conditions"""
        latency = 0.0
        jitter = 0.0
        
        # Ping test to measure baseline latency
        test_hosts = ["8.8.8.8", "1.1.1.1"]
        latencies = []
        
        for host in test_hosts:
            try:
                start = time.time()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                result = s.connect_ex((host, 443))
                s.close()
                if result == 0:
                    latencies.append((time.time() - start) * 1000)
            except Exception:
                pass
        
        if latencies:
            latency = sum(latencies) / len(latencies)
            if len(latencies) > 1:
                jitter = max(latencies) - min(latencies)
        
        # Determine quality
        if latency < self.LATENCY_EXCELLENT_MS:
            quality = "excellent"
        elif latency < self.LATENCY_GOOD_MS:
            quality = "good"
        elif latency < self.LATENCY_FAIR_MS:
            quality = "fair"
        else:
            quality = "poor"
        
        return NetworkCondition(
            timestamp=time.time(),
            latency_ms=latency,
            jitter_ms=jitter,
            packet_loss_pct=0.0,  # Would need ICMP for accurate measurement
            bandwidth_mbps=0.0,
            connection_quality=quality
        )
    
    def _calculate_adjustment(self, condition: NetworkCondition) -> Optional[JitterProfile]:
        """Calculate jitter adjustment based on conditions"""
        if not self.target_profile:
            return None
        
        # If network is already degraded, reduce artificial jitter
        if condition.connection_quality == "poor":
            # Reduce jitter to compensate for real network issues
            scale = 0.3
        elif condition.connection_quality == "fair":
            scale = 0.6
        elif condition.connection_quality == "good":
            scale = 0.9
        else:
            scale = 1.0
        
        # Only adjust if significant change needed
        target_jitter = self.target_profile.jitter_ms * scale
        if abs(target_jitter - self.current_jitter_ms) < 1.0:
            return None
        
        # Create adjusted profile
        adjusted = JitterProfile(
            connection_type=self.target_profile.connection_type,
            base_latency_ms=self.target_profile.base_latency_ms * scale,
            jitter_ms=target_jitter,
            jitter_correlation=self.target_profile.jitter_correlation,
            loss_rate=self.target_profile.loss_rate * scale,
            duplicate_rate=self.target_profile.duplicate_rate,
            reorder_rate=self.target_profile.reorder_rate * scale,
            bandwidth_kbps=self.target_profile.bandwidth_kbps,
            burst_size_bytes=self.target_profile.burst_size_bytes,
        )
        
        return adjusted
    
    def _apply_adjusted_jitter(self, profile: JitterProfile) -> None:
        """Apply adjusted jitter profile"""
        if not self._engine:
            return
        
        self._engine.apply_jitter(custom_profile=profile)
        self.current_jitter_ms = profile.jitter_ms
        self.current_latency_ms = profile.base_latency_ms
        
        # Notify callbacks
        for callback in self._adjustment_callbacks:
            try:
                callback(profile)
            except Exception as e:
                logger.error(f"Adjustment callback error: {e}")
        
        logger.debug(f"Jitter adjusted: {profile.jitter_ms}ms")
    
    def on_adjustment(self, callback: Callable[[JitterProfile], None]) -> None:
        """Register callback for jitter adjustments"""
        with self._lock:
            self._adjustment_callbacks.append(callback)
    
    def get_status(self) -> Dict:
        """Get controller status"""
        with self._lock:
            recent = list(self._condition_history)[-5:]
        
        avg_latency = 0
        avg_jitter = 0
        if recent:
            avg_latency = sum(c.latency_ms for c in recent) / len(recent)
            avg_jitter = sum(c.jitter_ms for c in recent) / len(recent)
        
        return {
            "active": self._control_thread is not None and self._control_thread.is_alive(),
            "target_profile": self.target_profile.connection_type.value if self.target_profile else None,
            "current_jitter_ms": round(self.current_jitter_ms, 2),
            "current_latency_ms": round(self.current_latency_ms, 2),
            "measured_latency_ms": round(avg_latency, 2),
            "measured_jitter_ms": round(avg_jitter, 2),
            "samples_collected": len(self._condition_history),
        }


# Singleton instance
_adaptive_controller: Optional[AdaptiveJitterController] = None

def get_adaptive_jitter_controller() -> AdaptiveJitterController:
    """Get singleton AdaptiveJitterController instance"""
    global _adaptive_controller
    if _adaptive_controller is None:
        _adaptive_controller = AdaptiveJitterController()
    return _adaptive_controller


class TrafficPatternAnalyzer:
    """
    V7.6 P0 CRITICAL: Analyze outgoing traffic patterns to detect anomalies.
    
    Monitors traffic patterns to identify potential detection vectors
    and optimizes jitter parameters for more realistic behavior.
    
    Usage:
        analyzer = get_traffic_pattern_analyzer()
        
        # Start analysis
        analyzer.start_analysis("eth0")
        
        # Get pattern report
        report = analyzer.get_pattern_report()
    """
    
    # Detection thresholds
    BURST_THRESHOLD_PACKETS = 50
    BURST_WINDOW_MS = 100
    QUIET_PERIOD_THRESHOLD_SEC = 30
    
    def __init__(self):
        self.samples: deque = deque(maxlen=1000)
        self._stop_event = threading.Event()
        self._analyze_thread: Optional[threading.Thread] = None
        self._anomaly_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._detected_anomalies: List[Dict] = []
        logger.info("TrafficPatternAnalyzer initialized")
    
    def start_analysis(self, interface: str = "eth0") -> None:
        """Start traffic pattern analysis"""
        if self._analyze_thread and self._analyze_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._analyze_thread = threading.Thread(
            target=self._analyze_loop,
            args=(interface,),
            daemon=True,
            name="TrafficPatternAnalyzer"
        )
        self._analyze_thread.start()
        logger.info(f"Traffic pattern analysis started on {interface}")
    
    def stop_analysis(self) -> None:
        """Stop traffic analysis"""
        self._stop_event.set()
        if self._analyze_thread:
            self._analyze_thread.join(timeout=5.0)
        logger.info("Traffic pattern analysis stopped")
    
    def _analyze_loop(self, interface: str) -> None:
        """Main analysis loop"""
        last_stats = self._get_interface_stats(interface)
        
        while not self._stop_event.is_set():
            try:
                time.sleep(1.0)  # Sample every second
                
                current_stats = self._get_interface_stats(interface)
                if current_stats and last_stats:
                    sample = TrafficSample(
                        timestamp=time.time(),
                        bytes_sent=current_stats["tx_bytes"] - last_stats["tx_bytes"],
                        bytes_received=current_stats["rx_bytes"] - last_stats["rx_bytes"],
                        packets_sent=current_stats["tx_packets"] - last_stats["tx_packets"],
                        packets_received=current_stats["rx_packets"] - last_stats["rx_packets"],
                        protocol="mixed",
                        destination="aggregate"
                    )
                    
                    with self._lock:
                        self.samples.append(sample)
                    
                    # Check for anomalies
                    self._check_anomalies(sample)
                
                last_stats = current_stats
                
            except Exception as e:
                logger.error(f"Traffic analysis error: {e}")
    
    def _get_interface_stats(self, interface: str) -> Optional[Dict]:
        """Get interface statistics from /proc/net/dev"""
        try:
            with open("/proc/net/dev") as f:
                for line in f:
                    if interface in line:
                        parts = line.split()
                        return {
                            "rx_bytes": int(parts[1]),
                            "rx_packets": int(parts[2]),
                            "tx_bytes": int(parts[9]),
                            "tx_packets": int(parts[10]),
                        }
        except Exception:
            pass
        return None
    
    def _check_anomalies(self, sample: TrafficSample) -> None:
        """Check for traffic anomalies"""
        anomalies = []
        
        # Check for traffic bursts
        if sample.packets_sent > self.BURST_THRESHOLD_PACKETS:
            anomalies.append({
                "type": "traffic_burst",
                "severity": "medium",
                "details": f"High packet rate: {sample.packets_sent} packets/sec",
                "timestamp": sample.timestamp
            })
        
        # Check for quiet periods
        with self._lock:
            if len(self.samples) >= 30:
                recent = list(self.samples)[-30:]
                total_traffic = sum(s.bytes_sent + s.bytes_received for s in recent)
                if total_traffic < 1000:  # Less than 1KB in 30 seconds
                    anomalies.append({
                        "type": "quiet_period",
                        "severity": "high",
                        "details": "Unusually low traffic - potential bot indicator",
                        "timestamp": sample.timestamp
                    })
        
        # Store and notify
        if anomalies:
            with self._lock:
                self._detected_anomalies.extend(anomalies)
                # Keep only recent anomalies
                cutoff = time.time() - 3600
                self._detected_anomalies = [
                    a for a in self._detected_anomalies 
                    if a["timestamp"] > cutoff
                ]
            
            for callback in self._anomaly_callbacks:
                for anomaly in anomalies:
                    try:
                        callback(anomaly)
                    except Exception as e:
                        logger.error(f"Anomaly callback error: {e}")
    
    def on_anomaly(self, callback: Callable[[Dict], None]) -> None:
        """Register callback for anomaly detection"""
        with self._lock:
            self._anomaly_callbacks.append(callback)
    
    def get_pattern_report(self) -> Dict:
        """Generate traffic pattern report"""
        with self._lock:
            samples = list(self.samples)
            anomalies = list(self._detected_anomalies)
        
        if not samples:
            return {"status": "no_data", "samples": 0}
        
        # Calculate statistics
        total_sent = sum(s.bytes_sent for s in samples)
        total_received = sum(s.bytes_received for s in samples)
        duration = samples[-1].timestamp - samples[0].timestamp if len(samples) > 1 else 1
        
        # Packet rate statistics
        packet_rates = [s.packets_sent for s in samples]
        avg_rate = sum(packet_rates) / len(packet_rates)
        variance = sum((r - avg_rate) ** 2 for r in packet_rates) / len(packet_rates)
        std_dev = math.sqrt(variance)
        
        return {
            "status": "active",
            "duration_seconds": round(duration, 1),
            "samples_collected": len(samples),
            "total_bytes_sent": total_sent,
            "total_bytes_received": total_received,
            "avg_packet_rate": round(avg_rate, 2),
            "packet_rate_std_dev": round(std_dev, 2),
            "anomalies_detected": len(anomalies),
            "recent_anomalies": anomalies[-5:],
            "pattern_score": self._calculate_pattern_score(samples),
        }
    
    def _calculate_pattern_score(self, samples: List[TrafficSample]) -> float:
        """Calculate a human-likeness score for traffic pattern (0-100)"""
        if len(samples) < 10:
            return 50.0
        
        score = 100.0
        
        # Penalize constant packet rates (bot indicator)
        packet_rates = [s.packets_sent for s in samples]
        if len(set(packet_rates)) < len(packet_rates) * 0.5:
            score -= 20
        
        # Penalize zero-traffic periods
        zero_periods = sum(1 for s in samples if s.packets_sent == 0 and s.packets_received == 0)
        if zero_periods > len(samples) * 0.3:
            score -= 15
        
        # Reward variance (human-like)
        if len(packet_rates) > 1:
            mean = sum(packet_rates) / len(packet_rates)
            if mean > 0:
                cv = (sum((r - mean) ** 2 for r in packet_rates) / len(packet_rates)) ** 0.5 / mean
                if 0.2 < cv < 2.0:  # Healthy coefficient of variation
                    score += 10
        
        return max(0, min(100, score))


# Singleton instance
_traffic_analyzer: Optional[TrafficPatternAnalyzer] = None

def get_traffic_pattern_analyzer() -> TrafficPatternAnalyzer:
    """Get singleton TrafficPatternAnalyzer instance"""
    global _traffic_analyzer
    if _traffic_analyzer is None:
        _traffic_analyzer = TrafficPatternAnalyzer()
    return _traffic_analyzer


class NoisePatternGenerator:
    """
    V7.6 P0 CRITICAL: Generate realistic noise patterns based on time-of-day.
    
    Real users generate different traffic patterns at different times.
    This generator creates time-appropriate background noise.
    
    Usage:
        generator = get_noise_pattern_generator()
        
        # Configure schedules
        generator.add_schedule(NoiseSchedule(
            hour_start=9, hour_end=17,
            intensity=0.8, dns_frequency=0.5, telemetry_frequency=0.1
        ))
        
        # Start generation
        generator.start()
    """
    
    # Default schedules by time of day
    DEFAULT_SCHEDULES = [
        # Night (00:00 - 06:00): Very low activity
        NoiseSchedule(hour_start=0, hour_end=6, intensity=0.1, 
                     dns_frequency=0.05, telemetry_frequency=0.02),
        # Early morning (06:00 - 09:00): Light activity
        NoiseSchedule(hour_start=6, hour_end=9, intensity=0.3,
                     dns_frequency=0.2, telemetry_frequency=0.05),
        # Work hours (09:00 - 17:00): High activity
        NoiseSchedule(hour_start=9, hour_end=17, intensity=0.8,
                     dns_frequency=0.5, telemetry_frequency=0.1),
        # Evening (17:00 - 22:00): Moderate activity
        NoiseSchedule(hour_start=17, hour_end=22, intensity=0.6,
                     dns_frequency=0.4, telemetry_frequency=0.08),
        # Late night (22:00 - 00:00): Low activity
        NoiseSchedule(hour_start=22, hour_end=24, intensity=0.2,
                     dns_frequency=0.1, telemetry_frequency=0.03),
    ]
    
    def __init__(self):
        self.schedules: List[NoiseSchedule] = list(self.DEFAULT_SCHEDULES)
        self._stop_event = threading.Event()
        self._generator_thread: Optional[threading.Thread] = None
        self._current_schedule: Optional[NoiseSchedule] = None
        self._lock = threading.Lock()
        self._stats = {
            "dns_queries": 0,
            "telemetry_pings": 0,
            "total_noise_bytes": 0,
        }
        logger.info("NoisePatternGenerator initialized")
    
    def add_schedule(self, schedule: NoiseSchedule) -> None:
        """Add a noise schedule"""
        with self._lock:
            self.schedules.append(schedule)
    
    def clear_schedules(self) -> None:
        """Clear all schedules"""
        with self._lock:
            self.schedules.clear()
    
    def reset_to_default(self) -> None:
        """Reset to default schedules"""
        with self._lock:
            self.schedules = list(self.DEFAULT_SCHEDULES)
    
    def start(self) -> None:
        """Start noise generation"""
        if self._generator_thread and self._generator_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._generator_thread = threading.Thread(
            target=self._generator_loop,
            daemon=True,
            name="NoisePatternGenerator"
        )
        self._generator_thread.start()
        logger.info("Noise pattern generation started")
    
    def stop(self) -> None:
        """Stop noise generation"""
        self._stop_event.set()
        if self._generator_thread:
            self._generator_thread.join(timeout=5.0)
        logger.info("Noise pattern generation stopped")
    
    def _get_current_schedule(self) -> Optional[NoiseSchedule]:
        """Get schedule for current hour"""
        from datetime import datetime
        current_hour = datetime.now().hour
        
        with self._lock:
            for schedule in self.schedules:
                if schedule.hour_start <= current_hour < schedule.hour_end:
                    return schedule
        return None
    
    def _generator_loop(self) -> None:
        """Main generation loop"""
        while not self._stop_event.is_set():
            try:
                schedule = self._get_current_schedule()
                
                with self._lock:
                    self._current_schedule = schedule
                
                if schedule and schedule.intensity > 0:
                    # Generate DNS noise
                    if random.random() < schedule.dns_frequency:
                        self._generate_dns_noise(schedule)
                    
                    # Generate telemetry noise
                    if random.random() < schedule.telemetry_frequency:
                        self._generate_telemetry_noise()
                
                # Wait based on intensity
                if schedule:
                    wait_time = random.uniform(
                        5.0 / max(schedule.intensity, 0.1),
                        15.0 / max(schedule.intensity, 0.1)
                    )
                else:
                    wait_time = 30.0
                
                self._stop_event.wait(min(wait_time, 60.0))
                
            except Exception as e:
                logger.error(f"Noise generation error: {e}")
                self._stop_event.wait(10.0)
    
    def _generate_dns_noise(self, schedule: NoiseSchedule) -> None:
        """Generate DNS lookup noise"""
        # Use schedule-specific domains or default
        domains = schedule.domains_pool if schedule.domains_pool else NOISE_DNS_DOMAINS
        domain = random.choice(domains)
        
        try:
            socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
            with self._lock:
                self._stats["dns_queries"] += 1
                self._stats["total_noise_bytes"] += 100  # Approximate DNS query size
        except Exception:
            pass
    
    def _generate_telemetry_noise(self) -> None:
        """Generate telemetry connection noise"""
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
                s.sendto(b'\x1b' + 47 * b'\0', (host, port))
                s.close()
            
            with self._lock:
                self._stats["telemetry_pings"] += 1
                self._stats["total_noise_bytes"] += 48
        except Exception:
            pass
    
    def get_status(self) -> Dict:
        """Get generator status"""
        with self._lock:
            stats = dict(self._stats)
            current = self._current_schedule
        
        return {
            "active": self._generator_thread is not None and self._generator_thread.is_alive(),
            "current_schedule": {
                "hours": f"{current.hour_start}:00 - {current.hour_end}:00",
                "intensity": current.intensity,
            } if current else None,
            "schedules_configured": len(self.schedules),
            "stats": stats,
        }


# Singleton instance
_noise_generator: Optional[NoisePatternGenerator] = None

def get_noise_pattern_generator() -> NoisePatternGenerator:
    """Get singleton NoisePatternGenerator instance"""
    global _noise_generator
    if _noise_generator is None:
        _noise_generator = NoisePatternGenerator()
    return _noise_generator


class JitterSynchronizer:
    """
    V7.6 P0 CRITICAL: Synchronize jitter across multiple network interfaces.
    
    When operating with multiple network paths (e.g., primary + failover),
    ensures consistent jitter behavior to avoid detection from
    inconsistent network characteristics.
    
    Usage:
        sync = get_jitter_synchronizer()
        
        # Register interfaces
        sync.register_interface("eth0", ConnectionType.CABLE)
        sync.register_interface("wlan0", ConnectionType.WIFI_HOME)
        
        # Apply synchronized jitter
        sync.apply_synchronized_jitter()
    """
    
    def __init__(self):
        self.interfaces: Dict[str, Dict] = {}
        self.engines: Dict[str, NetworkJitterEngine] = {}
        self._master_profile: Optional[JitterProfile] = None
        self._lock = threading.Lock()
        logger.info("JitterSynchronizer initialized")
    
    def register_interface(self, interface: str, 
                          connection_type: ConnectionType) -> None:
        """Register a network interface for synchronization"""
        with self._lock:
            self.interfaces[interface] = {
                "connection_type": connection_type,
                "active": False,
                "last_applied": None,
            }
            self.engines[interface] = NetworkJitterEngine(interface=interface)
        logger.info(f"Registered interface: {interface} ({connection_type.value})")
    
    def unregister_interface(self, interface: str) -> None:
        """Unregister an interface"""
        with self._lock:
            if interface in self.interfaces:
                if interface in self.engines:
                    self.engines[interface].stop()
                    del self.engines[interface]
                del self.interfaces[interface]
    
    def set_master_profile(self, connection_type: ConnectionType) -> None:
        """Set the master profile that all interfaces should emulate"""
        with self._lock:
            self._master_profile = JITTER_PROFILES.get(connection_type)
        logger.info(f"Master profile set: {connection_type.value}")
    
    def apply_synchronized_jitter(self) -> Dict[str, bool]:
        """Apply jitter to all registered interfaces"""
        results = {}
        
        with self._lock:
            profile = self._master_profile
            
            for interface, info in self.interfaces.items():
                if interface not in self.engines:
                    continue
                
                # Use master profile if set, otherwise interface-specific
                apply_profile = profile or JITTER_PROFILES.get(info["connection_type"])
                
                if apply_profile:
                    success = self.engines[interface].apply_jitter(
                        custom_profile=apply_profile
                    )
                    results[interface] = success
                    info["active"] = success
                    info["last_applied"] = time.time() if success else None
        
        return results
    
    def start_all_noise(self) -> None:
        """Start background noise on all interfaces"""
        with self._lock:
            for interface, engine in self.engines.items():
                engine.start_background_noise()
                self.interfaces[interface]["active"] = True
    
    def stop_all(self) -> None:
        """Stop jitter and noise on all interfaces"""
        with self._lock:
            for interface, engine in self.engines.items():
                engine.stop()
                self.interfaces[interface]["active"] = False
    
    def get_synchronized_status(self) -> Dict:
        """Get synchronization status"""
        with self._lock:
            return {
                "interface_count": len(self.interfaces),
                "master_profile": self._master_profile.connection_type.value if self._master_profile else None,
                "interfaces": {
                    iface: {
                        "connection_type": info["connection_type"].value,
                        "active": info["active"],
                        "last_applied": info["last_applied"],
                    }
                    for iface, info in self.interfaces.items()
                }
            }
    
    def verify_synchronization(self) -> Dict:
        """Verify all interfaces have consistent jitter behavior"""
        with self._lock:
            issues = []
            
            # Check all interfaces are active
            inactive = [iface for iface, info in self.interfaces.items() 
                       if not info["active"]]
            if inactive:
                issues.append(f"Inactive interfaces: {inactive}")
            
            # Check for stale applications
            cutoff = time.time() - 3600  # 1 hour
            stale = [iface for iface, info in self.interfaces.items()
                    if info["last_applied"] and info["last_applied"] < cutoff]
            if stale:
                issues.append(f"Stale jitter config: {stale}")
            
            return {
                "synchronized": len(issues) == 0,
                "issues": issues,
                "interfaces_ok": len(self.interfaces) - len(inactive),
                "interfaces_total": len(self.interfaces),
            }


# Singleton instance
_jitter_sync: Optional[JitterSynchronizer] = None

def get_jitter_synchronizer() -> JitterSynchronizer:
    """Get singleton JitterSynchronizer instance"""
    global _jitter_sync
    if _jitter_sync is None:
        _jitter_sync = JitterSynchronizer()
    return _jitter_sync
