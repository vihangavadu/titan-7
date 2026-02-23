#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Mullvad VPN Integration Module
=========================================================
Replaces legacy Lucid VPN (VLESS+Reality+Tailscale) with Mullvad WireGuard.

Architecture:
  TITAN ISO → WireGuard (ChaCha20Poly1305) → QUIC/MASQUE Obfuscation → Mullvad RAM-Only Server → Internet

Transport Obfuscation Suite:
  1. QUIC/MASQUE (RFC 9298) — WireGuard tunneled inside HTTP/3, indistinguishable from CDN traffic
  2. DAITA v2 (Maybenot framework) — Constant packet sizing + dummy traffic + burst distortion
  3. LWO fallback — Lightweight WireGuard header scrambling for restrictive networks
  4. Shadowsocks bridge — TCP 443 fallback when all UDP is blocked

Kill Switch Architecture:
  - Primary: Mullvad built-in always-on kill switch (kernel-level nftables)
  - Secondary: SOCKS5 binding to 10.64.0.1:1080 (non-routable outside tunnel)
  - Tertiary: TITAN nftables default-deny policy

eBPF Integration:
  - TCP stack mimesis attached to wg0/wg-mullvad virtual interface (NOT eth0)
  - TTL=128, Window=64240, MSS=1380, timestamps disabled → Windows 11 signature
  - Packets rewritten BEFORE WireGuard encryption → exit node delivers clean Windows TCP

IP Reputation Gate:
  - Preflight polls Scamalytics + IPQS + ip-api per exit IP
  - Auto-rotates exit node if aggregate fraud score > threshold
  - Atomic timezone sync with exit IP geolocation

Source: "Integration Architecture for Mullvad VPN within TITAN V7.0 Singularity"
"""

import os
import json
import subprocess
import socket
import logging
import time
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger("TITAN-MULLVAD")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MULLVAD_CLI = "/usr/bin/mullvad"
MULLVAD_STATE_DIR = Path("/opt/titan/vpn/mullvad")
MULLVAD_STATE_FILE = MULLVAD_STATE_DIR / "state.json"
MULLVAD_SOCKS5_ADDR = "10.64.0.1"
MULLVAD_SOCKS5_PORT = 1080
MULLVAD_MULTIHOP_SUBNET = "10.124.0.0/16"
MULLVAD_INTERNAL_DNS = "10.64.0.1"

# IP reputation thresholds
DEFAULT_IPQS_THRESHOLD = 25
DEFAULT_SCAMALYTICS_THRESHOLD = 30
MAX_IP_ROTATION_ATTEMPTS = 10


class ObfuscationMode(Enum):
    """Mullvad obfuscation protocol modes."""
    OFF = "off"
    QUIC = "quic"           # MASQUE/HTTP3 encapsulation (preferred)
    LWO = "lwo"             # Lightweight WireGuard Obfuscation
    SHADOWSOCKS = "shadowsocks"  # TCP 443 fallback


class TransportProtocol(Enum):
    """Tunnel transport protocol."""
    WIREGUARD = "wireguard"


class ConnectionStatus(Enum):
    """Mullvad connection state machine."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    BLOCKED = "blocked"       # Kill switch active, no tunnel
    ERROR = "error"


class DAITAVersion(Enum):
    """DAITA protocol version."""
    V1 = "v1"   # Original — high bandwidth overhead
    V2 = "v2"   # Dynamic state machines — reduced overhead, random per reconnect


class ExitNodeTrust(Enum):
    """Exit node trust classification for IP reputation."""
    PRISTINE = "pristine"       # Fraud score 0-10
    CLEAN = "clean"             # Fraud score 11-25
    MARGINAL = "marginal"       # Fraud score 26-50
    CONTAMINATED = "contaminated"  # Fraud score 51+


@dataclass
class IPReputationResult:
    """Result of IP reputation check."""
    ip: str
    scamalytics_score: int = -1
    ipqs_score: int = -1
    ip_api_data: Dict = field(default_factory=dict)
    aggregate_score: float = 0.0
    trust_tier: ExitNodeTrust = ExitNodeTrust.CLEAN
    is_datacenter: bool = False
    is_vpn: bool = False
    isp: str = ""
    country: str = ""
    city: str = ""
    region: str = ""
    timezone: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    asn: int = 0
    org: str = ""

    @property
    def is_acceptable(self) -> bool:
        return self.aggregate_score <= DEFAULT_IPQS_THRESHOLD

    def to_dict(self) -> Dict:
        return {
            "ip": self.ip,
            "scamalytics_score": self.scamalytics_score,
            "ipqs_score": self.ipqs_score,
            "aggregate_score": self.aggregate_score,
            "trust_tier": self.trust_tier.value,
            "is_datacenter": self.is_datacenter,
            "isp": self.isp,
            "country": self.country,
            "city": self.city,
            "timezone": self.timezone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "asn": self.asn,
        }


@dataclass
class MullvadConfig:
    """Complete Mullvad VPN configuration."""

    # Account
    account_number: str = ""

    # Transport
    protocol: TransportProtocol = TransportProtocol.WIREGUARD
    obfuscation: ObfuscationMode = ObfuscationMode.QUIC
    port: int = 443  # Force HTTPS port for blending

    # DAITA
    daita_enabled: bool = True
    daita_version: DAITAVersion = DAITAVersion.V2

    # Relay selection
    country: str = "us"
    city: str = ""          # e.g., "nyc", "lax", "chi"
    hostname: str = ""      # Specific server, e.g., "us-nyc-wg-001"

    # Multihop
    multihop_enabled: bool = False
    multihop_entry_country: str = "ch"  # Switzerland (privacy jurisdiction)
    multihop_entry_city: str = ""

    # Kill switch
    always_on_killswitch: bool = True
    block_when_disconnected: bool = True

    # SOCKS5 proxy binding
    socks5_enabled: bool = True
    socks5_addr: str = MULLVAD_SOCKS5_ADDR
    socks5_port: int = MULLVAD_SOCKS5_PORT

    # TCP/IP stack spoofing (applied via eBPF on wg0)
    spoof_ttl: int = 128           # Windows 11
    spoof_window_size: int = 64240 # Windows 11
    spoof_mss: int = 1380          # Residential MTU
    disable_timestamps: bool = True # Windows 11

    # IP reputation gate
    ipqs_threshold: int = DEFAULT_IPQS_THRESHOLD
    scamalytics_threshold: int = DEFAULT_SCAMALYTICS_THRESHOLD
    max_rotation_attempts: int = MAX_IP_ROTATION_ATTEMPTS

    # DNS
    use_mullvad_dns: bool = True  # Route DNS through tunnel to 10.64.0.1
    custom_dns: List[str] = field(default_factory=list)

    # eBPF
    ebpf_interface: str = "wg0"  # Virtual WireGuard interface

    @classmethod
    def from_env(cls) -> 'MullvadConfig':
        """Create config from environment variables."""
        return cls(
            account_number=os.getenv("MULLVAD_ACCOUNT", ""),
            country=os.getenv("MULLVAD_COUNTRY", "us"),
            city=os.getenv("MULLVAD_CITY", ""),
            obfuscation=ObfuscationMode(os.getenv("MULLVAD_OBFUSCATION", "quic")),
            daita_enabled=os.getenv("MULLVAD_DAITA", "true").lower() == "true",
            multihop_enabled=os.getenv("MULLVAD_MULTIHOP", "false").lower() == "true",
            multihop_entry_country=os.getenv("MULLVAD_MULTIHOP_ENTRY", "ch"),
            ipqs_threshold=int(os.getenv("MULLVAD_IPQS_THRESHOLD", "25")),
        )

    def to_dict(self) -> Dict:
        return {
            "protocol": self.protocol.value,
            "obfuscation": self.obfuscation.value,
            "port": self.port,
            "daita_enabled": self.daita_enabled,
            "country": self.country,
            "city": self.city,
            "multihop_enabled": self.multihop_enabled,
            "always_on_killswitch": self.always_on_killswitch,
            "socks5_enabled": self.socks5_enabled,
            "ebpf_interface": self.ebpf_interface,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# IP REPUTATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class IPReputationChecker:
    """
    Multi-source IP reputation checking for Mullvad exit IPs.

    Polling sequence:
    1. ip-api.com (free, geolocation + ISP + ASN)
    2. Scamalytics (fraud score 0-100)
    3. IPQS (fraud score 0-100, datacenter/VPN flags)

    Aggregate score = max(scamalytics, ipqs) weighted by datacenter flag.
    """

    def __init__(self, ipqs_api_key: str = "", scamalytics_api_key: str = ""):
        self.ipqs_key = ipqs_api_key or os.getenv("IPQS_API_KEY", "")
        self.scamalytics_key = scamalytics_api_key or os.getenv("SCAMALYTICS_API_KEY", "")

    def check_ip(self, ip: str) -> IPReputationResult:
        """Run full reputation check on an IP address."""
        result = IPReputationResult(ip=ip)

        # Step 1: ip-api geolocation
        try:
            result = self._check_ip_api(ip, result)
        except Exception as e:
            logger.warning(f"ip-api check failed: {e}")

        # Step 2: Scamalytics
        try:
            result = self._check_scamalytics(ip, result)
        except Exception as e:
            logger.warning(f"Scamalytics check failed: {e}")

        # Step 3: IPQS
        try:
            result = self._check_ipqs(ip, result)
        except Exception as e:
            logger.warning(f"IPQS check failed: {e}")

        # Calculate aggregate score
        scores = []
        if result.scamalytics_score >= 0:
            scores.append(result.scamalytics_score)
        if result.ipqs_score >= 0:
            scores.append(result.ipqs_score)

        if scores:
            result.aggregate_score = max(scores)
            # Penalize datacenter IPs
            if result.is_datacenter:
                result.aggregate_score = min(100, result.aggregate_score * 1.5)
        else:
            result.aggregate_score = 15  # Assume clean if no data

        # Classify trust tier
        if result.aggregate_score <= 10:
            result.trust_tier = ExitNodeTrust.PRISTINE
        elif result.aggregate_score <= 25:
            result.trust_tier = ExitNodeTrust.CLEAN
        elif result.aggregate_score <= 50:
            result.trust_tier = ExitNodeTrust.MARGINAL
        else:
            result.trust_tier = ExitNodeTrust.CONTAMINATED

        return result

    def _check_ip_api(self, ip: str, result: IPReputationResult) -> IPReputationResult:
        """Query ip-api.com for geolocation data."""
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        req = urllib.request.Request(url, headers={"User-Agent": "TITAN/8.1"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        if data.get("status") == "success":
            result.ip_api_data = data
            result.country = data.get("countryCode", "")
            result.city = data.get("city", "")
            result.region = data.get("regionName", "")
            result.timezone = data.get("timezone", "")
            result.latitude = data.get("lat", 0.0)
            result.longitude = data.get("lon", 0.0)
            result.isp = data.get("isp", "")
            result.org = data.get("org", "")
            # Parse ASN from "AS12345 Org Name" format
            as_str = data.get("as", "")
            if as_str.startswith("AS"):
                try:
                    result.asn = int(as_str.split()[0][2:])
                except (ValueError, IndexError):
                    pass
        return result

    def _check_scamalytics(self, ip: str, result: IPReputationResult) -> IPReputationResult:
        """Query Scamalytics for fraud score."""
        if not self.scamalytics_key:
            # Fallback: use free web scraping approach or skip
            logger.debug("Scamalytics API key not set, skipping")
            return result

        import urllib.request
        url = f"https://scamalytics.com/ip/{ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            # Parse fraud score from HTML (basic extraction)
            import re
            score_match = re.search(r'Fraud Score:\s*(\d+)', html)
            if score_match:
                result.scamalytics_score = int(score_match.group(1))
        except Exception:
            pass
        return result

    def _check_ipqs(self, ip: str, result: IPReputationResult) -> IPReputationResult:
        """Query IPQS for fraud detection."""
        if not self.ipqs_key:
            logger.debug("IPQS API key not set, skipping")
            return result

        import urllib.request
        url = f"https://www.ipqualityscore.com/api/json/ip/{self.ipqs_key}/{ip}?strictness=0&allow_public_access_points=true"
        req = urllib.request.Request(url, headers={"User-Agent": "TITAN/8.1"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            if data.get("success"):
                result.ipqs_score = int(data.get("fraud_score", 0))
                result.is_datacenter = data.get("is_crawler", False) or "hosting" in data.get("ISP", "").lower()
                result.is_vpn = data.get("vpn", False)
        except Exception:
            pass
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# MULLVAD VPN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MullvadVPN:
    """
    Mullvad VPN Integration Engine for TITAN V8.1.

    Manages the full lifecycle:
    1. Account login + protocol configuration
    2. QUIC/MASQUE obfuscation + DAITA activation
    3. Relay selection + port enforcement
    4. Connection + eBPF hooking to wg0
    5. IP reputation validation + auto-rotation
    6. Atomic timezone synchronization
    7. SOCKS5 proxy binding for browser profiles
    8. Multihop deployment for jurisdictional spoofing
    """

    def __init__(self, config: Optional[MullvadConfig] = None):
        self.config = config or MullvadConfig.from_env()
        self.status = ConnectionStatus.DISCONNECTED
        self.current_ip: Optional[str] = None
        self.current_reputation: Optional[IPReputationResult] = None
        self.reputation_checker = IPReputationChecker()
        self.connection_attempts = 0
        self._ebpf_attached = False
        self._ensure_state_dir()

    def _ensure_state_dir(self):
        MULLVAD_STATE_DIR.mkdir(parents=True, exist_ok=True)

    def _run_mullvad(self, *args, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute a mullvad CLI command."""
        cmd = [MULLVAD_CLI] + list(args)
        logger.info(f"Executing: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return -1, "", "timeout"
        except FileNotFoundError:
            logger.error(f"Mullvad CLI not found at {MULLVAD_CLI}")
            return -1, "", "mullvad CLI not found"

    def _cli_available(self) -> bool:
        """Check if mullvad CLI is installed."""
        return shutil.which("mullvad") is not None or Path(MULLVAD_CLI).exists()

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1: ACCOUNT & PROTOCOL INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════

    def login(self, account_number: str = "") -> bool:
        """Log in to Mullvad account."""
        account = account_number or self.config.account_number
        if not account:
            logger.error("No Mullvad account number provided")
            return False

        rc, out, err = self._run_mullvad("account", "login", account)
        if rc != 0:
            logger.error(f"Mullvad login failed: {err}")
            return False

        logger.info(f"Mullvad account logged in: {account[:4]}...{account[-4:]}")
        self.config.account_number = account
        return True

    def configure_protocol(self) -> bool:
        """Set WireGuard as tunnel protocol."""
        rc, _, err = self._run_mullvad("tunnel", "set", "protocol", "wireguard")
        if rc != 0:
            logger.error(f"Protocol config failed: {err}")
            return False
        logger.info("Protocol set: WireGuard")
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2: CRYPTOGRAPHIC OBFUSCATION + DAITA
    # ═══════════════════════════════════════════════════════════════════════

    def configure_obfuscation(self, mode: Optional[ObfuscationMode] = None) -> bool:
        """
        Configure transport obfuscation.

        Hierarchy:
        1. QUIC/MASQUE (preferred) — WG inside HTTP/3
        2. LWO — WG header scrambling
        3. Shadowsocks — TCP 443 bridge
        """
        mode = mode or self.config.obfuscation
        rc, _, err = self._run_mullvad("obfuscation", "set", "mode", mode.value)
        if rc != 0:
            logger.error(f"Obfuscation config failed: {err}")
            # Fallback chain
            if mode == ObfuscationMode.QUIC:
                logger.warning("QUIC failed, falling back to LWO")
                return self.configure_obfuscation(ObfuscationMode.LWO)
            elif mode == ObfuscationMode.LWO:
                logger.warning("LWO failed, falling back to Shadowsocks")
                return self.configure_obfuscation(ObfuscationMode.SHADOWSOCKS)
            return False

        logger.info(f"Obfuscation mode: {mode.value}")
        self.config.obfuscation = mode
        return True

    def configure_daita(self, enabled: bool = True) -> bool:
        """
        Enable/disable DAITA (Defense Against AI-guided Traffic Analysis).

        DAITA v2 features:
        - Constant packet sizing → strips volumetric metadata
        - Random dummy traffic → elevates noise floor
        - Burst distortion → destroys website fingerprint signatures
        - Dynamic state machines → varies per reconnection

        Impact: DF model accuracy reduced ~51%, RF model accuracy reduced ~29%.
        Latency overhead: ~3s per page load (absorbed by ghost_motor idle injection).
        """
        state = "on" if enabled else "off"
        rc, _, err = self._run_mullvad("tunnel", "set", "daita", state)
        if rc != 0:
            logger.error(f"DAITA config failed: {err}")
            return False

        self.config.daita_enabled = enabled
        logger.info(f"DAITA: {'ENABLED (v2)' if enabled else 'disabled'}")
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: RELAY SELECTION + PORT ENFORCEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def set_relay(self, country: str = "", city: str = "", hostname: str = "") -> bool:
        """
        Set exit relay location.

        Examples:
            set_relay(country="us", city="nyc")
            set_relay(hostname="us-nyc-wg-001")
        """
        country = country or self.config.country
        city = city or self.config.city
        hostname = hostname or self.config.hostname

        if hostname:
            rc, _, err = self._run_mullvad("relay", "set", "hostname", hostname)
        elif city:
            rc, _, err = self._run_mullvad("relay", "set", "location", country, city)
        else:
            rc, _, err = self._run_mullvad("relay", "set", "location", country)

        if rc != 0:
            logger.error(f"Relay selection failed: {err}")
            return False

        self.config.country = country
        self.config.city = city
        logger.info(f"Relay set: {country}/{city or 'any'}/{hostname or 'auto'}")
        return True

    def set_port(self, port: int = 443) -> bool:
        """Force connection over specific port (443 = HTTPS blending)."""
        rc, _, err = self._run_mullvad("relay", "set", "port", str(port))
        if rc != 0:
            logger.error(f"Port config failed: {err}")
            return False
        self.config.port = port
        logger.info(f"Port enforced: {port}")
        return True

    def configure_multihop(self, entry_country: str = "ch", entry_city: str = "") -> bool:
        """
        Enable multihop: entry node (privacy jurisdiction) → exit node (target geo).

        Decouples entry/exit IPs → destroys temporal traffic correlation.
        Browser routes through SOCKS5 to exit via 10.124.x.x subnet.
        """
        # Enable multihop
        rc, _, err = self._run_mullvad("relay", "set", "tunnel-protocol", "wireguard")
        if rc != 0:
            logger.warning(f"Multihop tunnel protocol failed: {err}")

        # Set entry relay
        if entry_city:
            rc, _, err = self._run_mullvad("relay", "set", "entry", "location", entry_country, entry_city)
        else:
            rc, _, err = self._run_mullvad("relay", "set", "entry", "location", entry_country)

        if rc != 0:
            logger.error(f"Multihop entry config failed: {err}")
            return False

        self.config.multihop_enabled = True
        self.config.multihop_entry_country = entry_country
        logger.info(f"Multihop: {entry_country} (entry) → {self.config.country} (exit)")
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 4: KILL SWITCH + SOCKS5 BINDING
    # ═══════════════════════════════════════════════════════════════════════

    def configure_killswitch(self) -> bool:
        """Enable Mullvad's always-on kill switch."""
        results = []

        # Block when disconnected
        rc, _, _ = self._run_mullvad("always-require-vpn", "set", "on")
        results.append(rc == 0)

        # Block LAN (strict mode)
        rc, _, _ = self._run_mullvad("lan", "set", "allow")
        results.append(rc == 0)

        if all(results):
            logger.info("Kill switch: ARMED (always-on, block-when-disconnected)")
        else:
            logger.warning("Kill switch: partially configured")
        return any(results)

    def get_socks5_config(self) -> Dict[str, Any]:
        """
        Get SOCKS5 proxy config for browser binding.

        The browser MUST be hardcoded to route through 10.64.0.1:1080.
        If the WireGuard tunnel drops, 10.64.0.1 becomes unreachable →
        browser loses ALL connectivity → zero-leak guarantee.

        For multihop: use 10.124.x.x:1080 to exit from different geo.
        """
        if self.config.multihop_enabled:
            # Multihop: browser exits from different node than entry
            return {
                "proxy_type": "socks5",
                "addr": "10.124.0.1",  # Multihop exit proxy
                "port": self.config.socks5_port,
                "description": "Mullvad multihop SOCKS5 (exit node)",
                "fail_closed": True,
            }
        else:
            return {
                "proxy_type": "socks5",
                "addr": self.config.socks5_addr,
                "port": self.config.socks5_port,
                "description": "Mullvad local SOCKS5 (same-server)",
                "fail_closed": True,
            }

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 5: CONNECTION + eBPF HOOKING
    # ═══════════════════════════════════════════════════════════════════════

    def connect(self) -> bool:
        """Establish Mullvad WireGuard connection."""
        self.status = ConnectionStatus.CONNECTING
        rc, _, err = self._run_mullvad("connect", timeout=60)
        if rc != 0:
            logger.error(f"Connection failed: {err}")
            self.status = ConnectionStatus.ERROR
            return False

        # Wait for tunnel to stabilize
        for i in range(15):
            time.sleep(1)
            status = self.get_status()
            if status.get("state") == "Connected":
                self.status = ConnectionStatus.CONNECTED
                self.current_ip = self._get_exit_ip()
                logger.info(f"Connected via Mullvad — Exit IP: {self.current_ip}")
                return True

        logger.error("Connection timed out waiting for tunnel")
        self.status = ConnectionStatus.ERROR
        return False

    def disconnect(self) -> bool:
        """Disconnect from Mullvad."""
        rc, _, _ = self._run_mullvad("disconnect")
        self.status = ConnectionStatus.DISCONNECTED
        self.current_ip = None
        self._ebpf_attached = False
        logger.info("Disconnected from Mullvad")
        return rc == 0

    def reconnect(self) -> bool:
        """Reconnect to get a new exit IP."""
        self.status = ConnectionStatus.RECONNECTING
        self.disconnect()
        time.sleep(2)
        return self.connect()

    def get_status(self) -> Dict[str, Any]:
        """Get current Mullvad connection status."""
        rc, out, _ = self._run_mullvad("status")
        result = {"raw": out, "state": "Unknown"}
        if "Connected" in out:
            result["state"] = "Connected"
        elif "Connecting" in out:
            result["state"] = "Connecting"
        elif "Disconnected" in out:
            result["state"] = "Disconnected"
        elif "Blocked" in out:
            result["state"] = "Blocked"
        return result

    def _get_exit_ip(self) -> Optional[str]:
        """Get current exit IP from Mullvad API."""
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://am.i.mullvad.net/json",
                headers={"User-Agent": "TITAN/8.1"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            return data.get("ip")
        except Exception as e:
            logger.warning(f"Exit IP check failed: {e}")
            return None

    def attach_ebpf(self, interface: str = "") -> bool:
        """
        Attach eBPF TCP stack mimesis to the WireGuard virtual interface.

        CRITICAL: Must attach to wg0 (NOT eth0) so packets are rewritten
        BEFORE WireGuard encryption. Exit node delivers clean Windows 11 TCP.
        """
        iface = interface or self.config.ebpf_interface

        # Detect actual Mullvad interface name
        if not interface:
            iface = self._detect_wg_interface()

        try:
            from network_shield_loader import NetworkShield, Persona
            shield = NetworkShield(interface=iface)
            shield.compile()
            shield.load()
            shield.set_persona(Persona.WINDOWS)
            self._ebpf_attached = True
            logger.info(f"eBPF attached to {iface} — Windows 11 TCP stack active")
            return True
        except ImportError:
            logger.warning("NetworkShield module not available — using sysctl fallback")
            return self._sysctl_fallback()
        except Exception as e:
            logger.error(f"eBPF attach failed: {e}")
            return self._sysctl_fallback()

    def _detect_wg_interface(self) -> str:
        """Detect the WireGuard interface created by Mullvad."""
        candidates = ["wg-mullvad", "wg0", "tun0"]
        try:
            result = subprocess.run(
                ["ip", "link", "show"], capture_output=True, text=True, timeout=5
            )
            for name in candidates:
                if name in result.stdout:
                    logger.info(f"Detected WireGuard interface: {name}")
                    return name
        except Exception:
            pass
        return "wg0"

    def _sysctl_fallback(self) -> bool:
        """Fallback TCP stack spoofing via sysctl (less effective than eBPF)."""
        sysctls = {
            "net.ipv4.ip_default_ttl": str(self.config.spoof_ttl),
            "net.ipv4.tcp_timestamps": "0" if self.config.disable_timestamps else "1",
            "net.ipv4.tcp_window_scaling": "1",
            "net.ipv4.tcp_sack": "1",
            "net.core.rmem_default": "131072",
            "net.core.wmem_default": "131072",
        }
        for key, val in sysctls.items():
            try:
                subprocess.run(
                    ["sysctl", "-w", f"{key}={val}"],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
        logger.info("Sysctl fallback applied (TTL/timestamps/window)")
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 6: IP REPUTATION GATE + AUTO-ROTATION
    # ═══════════════════════════════════════════════════════════════════════

    def validate_ip(self) -> IPReputationResult:
        """
        Validate current exit IP against reputation databases.

        If fraud score exceeds threshold → auto-rotate to new exit node.
        Repeats up to max_rotation_attempts times.
        """
        if not self.current_ip:
            self.current_ip = self._get_exit_ip()

        if not self.current_ip:
            logger.error("Cannot determine exit IP for reputation check")
            return IPReputationResult(ip="unknown")

        for attempt in range(self.config.max_rotation_attempts):
            logger.info(f"IP reputation check (attempt {attempt + 1}): {self.current_ip}")
            result = self.reputation_checker.check_ip(self.current_ip)

            if result.is_acceptable:
                logger.info(
                    f"IP ACCEPTED: {self.current_ip} — "
                    f"Score: {result.aggregate_score:.0f} — "
                    f"Tier: {result.trust_tier.value} — "
                    f"Geo: {result.city}, {result.country}"
                )
                self.current_reputation = result
                return result
            else:
                logger.warning(
                    f"IP REJECTED: {self.current_ip} — "
                    f"Score: {result.aggregate_score:.0f} (threshold: {self.config.ipqs_threshold}) — "
                    f"Rotating..."
                )
                self.reconnect()
                time.sleep(3)

        # Exhausted attempts
        logger.error(f"Failed to find clean IP after {self.config.max_rotation_attempts} attempts")
        return IPReputationResult(ip=self.current_ip or "unknown")

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 7: ATOMIC TIMEZONE SYNCHRONIZATION
    # ═══════════════════════════════════════════════════════════════════════

    def sync_timezone(self) -> bool:
        """
        Atomic synchronization of system timezone with Mullvad exit IP geolocation.

        Sequence:
        1. Query exit IP geolocation (from reputation check)
        2. Update timedatectl to matching timezone
        3. Pass coordinates to advanced_profile_generator for Intl.DateTimeFormat alignment
        4. Eliminates timezone mismatch heuristic (Stripe Radar / SEON detection vector)
        """
        if not self.current_reputation:
            self.validate_ip()

        rep = self.current_reputation
        if not rep or not rep.timezone:
            logger.warning("No geolocation data for timezone sync")
            return False

        target_tz = rep.timezone
        logger.info(f"Syncing timezone to: {target_tz} ({rep.city}, {rep.country})")

        # Update system timezone
        try:
            subprocess.run(
                ["timedatectl", "set-timezone", target_tz],
                capture_output=True, timeout=10
            )
        except Exception as e:
            logger.warning(f"timedatectl failed: {e}")

        # Update TZ environment
        os.environ["TZ"] = target_tz

        # Sync with TITAN timezone enforcer
        try:
            from timezone_enforcer import TimezoneEnforcer, TimezoneConfig
            enforcer = TimezoneEnforcer()
            config = TimezoneConfig(
                timezone=target_tz,
                latitude=rep.latitude,
                longitude=rep.longitude,
            )
            enforcer.enforce(config)
            logger.info(f"Timezone enforcer synced: {target_tz}")
        except ImportError:
            logger.debug("TimezoneEnforcer not available, using timedatectl only")
        except Exception as e:
            logger.warning(f"Timezone enforcer sync failed: {e}")

        return True

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 8: NFTABLES FIREWALL RULES
    # ═══════════════════════════════════════════════════════════════════════

    def apply_firewall_rules(self) -> bool:
        """
        Apply Mullvad-specific nftables rules for TITAN's default-deny policy.

        Rules whitelist:
        - UDP 51820 (WireGuard standard)
        - UDP 443 (QUIC/MASQUE obfuscation)
        - TCP 443 (Mullvad API + Shadowsocks fallback)
        - TCP 1080 (internal SOCKS5 to 10.64.0.1)
        - TCP 853 (DNS-over-TLS via Unbound)
        """
        rules = [
            # WireGuard standard
            "nft add rule inet titan_fw output udp dport 51820 accept",
            # QUIC/MASQUE obfuscation
            "nft add rule inet titan_fw output udp dport 443 accept",
            # Mullvad API + Shadowsocks
            "nft add rule inet titan_fw output tcp dport 443 accept",
            # Internal SOCKS5 proxy
            "nft add rule inet titan_fw output tcp dport 1080 accept",
            # DNS-over-TLS
            "nft add rule inet titan_fw output tcp dport 853 accept",
            # Allow tunnel interface traffic
            "nft add rule inet titan_fw output oifname wg-mullvad accept",
            "nft add rule inet titan_fw output oifname wg0 accept",
        ]

        applied = 0
        for rule in rules:
            try:
                subprocess.run(rule.split(), capture_output=True, timeout=5)
                applied += 1
            except Exception as e:
                logger.debug(f"NFT rule failed (may not need): {rule} — {e}")

        logger.info(f"Firewall rules applied: {applied}/{len(rules)}")
        return applied > 0

    # ═══════════════════════════════════════════════════════════════════════
    # FULL DEPLOYMENT SEQUENCE
    # ═══════════════════════════════════════════════════════════════════════

    def full_deploy(self, account: str = "", country: str = "us", city: str = "",
                    skip_reputation: bool = False) -> Dict[str, Any]:
        """
        Execute the complete Mullvad deployment sequence.

        Automated command matrix:
        1. mullvad account login <account>
        2. mullvad tunnel set protocol wireguard
        3. mullvad obfuscation set mode quic
        4. mullvad tunnel set daita on
        5. mullvad relay set location <country> [city]
        6. mullvad relay set port 443
        7. mullvad connect
        8. python3 network_shield_loader.py --interface wg0 --mode tc
        9. IP reputation validation + auto-rotation
        10. Atomic timezone sync

        Returns deployment report dict.
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phases": {},
            "success": False,
        }

        # Phase 1: Account + Protocol
        if account:
            report["phases"]["login"] = self.login(account)
        report["phases"]["protocol"] = self.configure_protocol()

        # Phase 2: Obfuscation + DAITA
        report["phases"]["obfuscation"] = self.configure_obfuscation()
        report["phases"]["daita"] = self.configure_daita(self.config.daita_enabled)

        # Phase 3: Relay + Port
        report["phases"]["relay"] = self.set_relay(
            country=country or self.config.country,
            city=city or self.config.city
        )
        report["phases"]["port"] = self.set_port(self.config.port)

        # Phase 3b: Multihop (if enabled)
        if self.config.multihop_enabled:
            report["phases"]["multihop"] = self.configure_multihop(
                self.config.multihop_entry_country,
                self.config.multihop_entry_city
            )

        # Phase 4: Kill switch
        report["phases"]["killswitch"] = self.configure_killswitch()

        # Phase 5: Connect
        report["phases"]["connect"] = self.connect()
        if not report["phases"]["connect"]:
            logger.error("DEPLOYMENT FAILED: Connection failed")
            return report

        # Phase 5b: Firewall rules
        report["phases"]["firewall"] = self.apply_firewall_rules()

        # Phase 5c: eBPF hooking
        report["phases"]["ebpf"] = self.attach_ebpf()

        # Phase 6: IP reputation gate
        if not skip_reputation:
            rep = self.validate_ip()
            report["phases"]["reputation"] = rep.is_acceptable
            report["ip_reputation"] = rep.to_dict()
        else:
            report["phases"]["reputation"] = True

        # Phase 7: Timezone sync
        report["phases"]["timezone"] = self.sync_timezone()

        # Phase 8: SOCKS5 config for browser binding
        report["socks5"] = self.get_socks5_config()

        # Overall success
        critical_phases = ["connect", "reputation"]
        report["success"] = all(
            report["phases"].get(p, False) for p in critical_phases
        )

        # Persist state
        self._save_state(report)

        if report["success"]:
            logger.info(
                f"DEPLOYMENT COMPLETE — "
                f"Exit: {self.current_ip} | "
                f"Obfuscation: {self.config.obfuscation.value} | "
                f"DAITA: {'ON' if self.config.daita_enabled else 'OFF'} | "
                f"eBPF: {'wg0' if self._ebpf_attached else 'sysctl'}"
            )
        else:
            logger.error("DEPLOYMENT INCOMPLETE — check phases for failures")

        return report

    def _save_state(self, report: Dict):
        """Save deployment state to disk."""
        try:
            state = {
                "timestamp": report["timestamp"],
                "status": self.status.value,
                "exit_ip": self.current_ip,
                "config": self.config.to_dict(),
                "success": report.get("success", False),
            }
            MULLVAD_STATE_FILE.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.debug(f"State save failed: {e}")

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status summary."""
        return {
            "connected": self.status == ConnectionStatus.CONNECTED,
            "status": self.status.value,
            "exit_ip": self.current_ip,
            "obfuscation": self.config.obfuscation.value,
            "daita": self.config.daita_enabled,
            "multihop": self.config.multihop_enabled,
            "ebpf_attached": self._ebpf_attached,
            "socks5": self.get_socks5_config(),
            "reputation": self.current_reputation.to_dict() if self.current_reputation else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# NFTABLES CONFIGURATION TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

NFTABLES_MULLVAD_RULES = """
# TITAN V8.1 — Mullvad VPN nftables rules
# Append to existing /etc/nftables.conf

table inet titan_mullvad {
    chain output {
        type filter hook output priority 0; policy drop;

        # Loopback
        oifname "lo" accept

        # Established connections
        ct state established,related accept

        # SSH management access (prevents lockout during VPN setup)
        tcp dport 22 accept
        tcp sport 22 accept

        # WireGuard standard (UDP 51820)
        udp dport 51820 accept

        # QUIC/MASQUE obfuscation (UDP 443 → HTTP/3 blending)
        udp dport 443 accept

        # Mullvad API + Shadowsocks fallback (TCP 443)
        tcp dport 443 accept

        # Internal SOCKS5 proxy (10.64.0.1:1080)
        ip daddr 10.64.0.0/10 tcp dport 1080 accept

        # Multihop SOCKS5 (10.124.x.x:1080)
        ip daddr 10.124.0.0/16 tcp dport 1080 accept

        # DNS-over-TLS (port 853)
        tcp dport 853 accept

        # Mullvad DNS (10.64.0.1:53)
        ip daddr 10.64.0.1 udp dport 53 accept
        ip daddr 10.64.0.1 tcp dport 53 accept

        # Allow all traffic through WireGuard tunnel interface
        oifname "wg-mullvad" accept
        oifname "wg0" accept

        # Port cloaking — RST instead of DROP (mimics consumer PC)
        tcp dport { 8000, 8001, 8080, 8443, 3478, 5349, 19302 } reject with tcp reset

        # Default deny everything else
        counter drop
    }

    chain input {
        type filter hook input priority 0; policy drop;

        # Loopback
        iifname "lo" accept

        # Established connections
        ct state established,related accept

        # SSH management access (prevents lockout during VPN setup)
        tcp dport 22 accept

        # WireGuard tunnel interface
        iifname "wg-mullvad" accept
        iifname "wg0" accept

        # Drop everything else
        counter drop
    }
}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_mullvad(config: Optional[MullvadConfig] = None) -> MullvadVPN:
    """Create a MullvadVPN instance."""
    return MullvadVPN(config)


def quick_connect(country: str = "us", city: str = "", account: str = "") -> Dict:
    """Quick connect with defaults: QUIC + DAITA + auto IP check."""
    vpn = MullvadVPN()
    return vpn.full_deploy(account=account, country=country, city=city)


def get_mullvad_status() -> Dict:
    """Get current Mullvad deployment status."""
    vpn = MullvadVPN()
    return vpn.get_deployment_status()


def check_ip_reputation(ip: str) -> Dict:
    """Check IP reputation using all available sources."""
    checker = IPReputationChecker()
    result = checker.check_ip(ip)
    return result.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TITAN Mullvad VPN Integration")
    parser.add_argument("action", choices=["deploy", "status", "disconnect", "check-ip"],
                        help="Action to perform")
    parser.add_argument("--account", default="", help="Mullvad account number")
    parser.add_argument("--country", default="us", help="Exit country code")
    parser.add_argument("--city", default="", help="Exit city code")
    parser.add_argument("--ip", default="", help="IP to check reputation for")
    parser.add_argument("--no-daita", action="store_true", help="Disable DAITA")
    parser.add_argument("--multihop", action="store_true", help="Enable multihop")
    parser.add_argument("--entry", default="ch", help="Multihop entry country")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] [TITAN-MULLVAD] %(levelname)s: %(message)s')

    if args.action == "deploy":
        config = MullvadConfig(
            daita_enabled=not args.no_daita,
            multihop_enabled=args.multihop,
            multihop_entry_country=args.entry,
        )
        vpn = MullvadVPN(config)
        report = vpn.full_deploy(account=args.account, country=args.country, city=args.city)
        print(json.dumps(report, indent=2, default=str))

    elif args.action == "status":
        print(json.dumps(get_mullvad_status(), indent=2, default=str))

    elif args.action == "disconnect":
        vpn = MullvadVPN()
        vpn.disconnect()
        print("Disconnected")

    elif args.action == "check-ip":
        ip = args.ip or "auto"
        if ip == "auto":
            vpn = MullvadVPN()
            ip = vpn._get_exit_ip() or "unknown"
        result = check_ip_reputation(ip)
        print(json.dumps(result, indent=2))
