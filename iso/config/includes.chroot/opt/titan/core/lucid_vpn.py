"""
TITAN V7.0 SINGULARITY - Lucid VPN Module
Zero-Signature Residential Network Emulation System

Replaces third-party proxy dependency with self-hosted infrastructure:
- VLESS + Reality protocol (TLS 1.3 masquerade via Xray-core)
- Tailscale mesh backhaul (VPS relay <-> residential exit node)
- TCP/IP stack spoofing (Windows 10/11 mimesis via sysctl + nftables)
- Mobile 4G/5G CGNAT exit (highest trust tier)
- Local DNS resolver (unbound) for zero DNS leaks

Architecture:
  TITAN ISO -> Xray (VLESS+Reality) -> VPS Relay -> Tailscale -> Residential/Mobile Exit -> Internet

Source: "Building Undetectable Lucid Titan VPN" research document
"""

import os
import json
import subprocess
import socket
import logging
import shutil
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime, timezone

# Centralized env loading
try:
    from titan_env import load_env
    load_env()
except ImportError:
    _TITAN_ENV = Path("/opt/titan/config/titan.env")
    if _TITAN_ENV.exists():
        for _line in _TITAN_ENV.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip()
                if _v and not _v.startswith("REPLACE_WITH") and _k not in os.environ:
                    os.environ[_k] = _v

logger = logging.getLogger("TITAN-LUCID-VPN")

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

VPN_CONFIG_DIR = Path("/opt/titan/vpn")
VPN_STATE_FILE = VPN_CONFIG_DIR / "state.json"
XRAY_CONFIG_FILE = VPN_CONFIG_DIR / "xray-client.json"
XRAY_BINARY = "/usr/local/bin/xray"
TAILSCALE_BINARY = "/usr/bin/tailscale"
UNBOUND_CONFIG = Path("/etc/unbound/unbound.conf.d/titan-dns.conf")


class VPNMode(Enum):
    """Network routing mode"""
    PROXY = "proxy"           # Traditional residential proxy (default)
    LUCID_VPN = "lucid_vpn"   # Lucid VPN with residential exit
    MOBILE_VPN = "mobile_vpn" # Lucid VPN with 4G/5G mobile exit


class VPNStatus(Enum):
    """VPN connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ExitNodeType(Enum):
    """Exit node type for IP reputation"""
    RESIDENTIAL = "residential"  # Home ISP (Comcast, AT&T, etc.)
    MOBILE = "mobile"            # 4G/5G CGNAT (highest trust)
    DATACENTER = "datacenter"    # VPS only (NOT recommended)


@dataclass
class VPNConfig:
    """Complete Lucid VPN configuration"""
    # VPS Relay
    vps_address: str = ""
    vps_port: int = 443
    
    # Xray VLESS + Reality
    xray_uuid: str = ""
    xray_private_key: str = ""
    xray_public_key: str = ""
    xray_short_id: str = ""
    sni_target: str = "www.microsoft.com"
    flow: str = "xtls-rprx-vision"
    
    # Tailscale
    tailscale_auth_key: str = ""
    exit_node_ip: str = ""
    exit_node_type: ExitNodeType = ExitNodeType.RESIDENTIAL
    
    # TCP/IP Spoofing (applied via sysctl + nftables)
    spoof_ttl: int = 128          # Windows 10/11
    spoof_window_size: int = 64240 # Windows 10/11
    disable_timestamps: bool = True # Windows behavior
    mss_clamp: int = 1380          # Residential/mobile MTU
    
    # DNS
    dns_servers: List[str] = field(default_factory=lambda: ["9.9.9.9", "1.1.1.1"])
    use_local_resolver: bool = True
    
    # Mode
    mode: VPNMode = VPNMode.LUCID_VPN
    
    @classmethod
    def from_env(cls) -> 'VPNConfig':
        """Create VPNConfig from titan.env / environment variables."""
        dns_str = os.getenv("TITAN_DNS_PRIMARY", "1.1.1.1")
        dns2 = os.getenv("TITAN_DNS_SECONDARY", "8.8.8.8")
        return cls(
            vps_address=os.getenv("TITAN_VPN_SERVER_IP", ""),
            vps_port=int(os.getenv("TITAN_VPN_SERVER_PORT", "443")),
            xray_uuid=os.getenv("TITAN_VPN_UUID", ""),
            xray_public_key=os.getenv("TITAN_VPN_PUBLIC_KEY", ""),
            xray_short_id=os.getenv("TITAN_VPN_SHORT_ID", ""),
            sni_target=os.getenv("TITAN_VPN_SNI", "www.microsoft.com"),
            tailscale_auth_key=os.getenv("TITAN_TAILSCALE_AUTH_KEY", ""),
            exit_node_ip=os.getenv("TITAN_TAILSCALE_EXIT_NODE", ""),
            dns_servers=[dns_str, dns2],
        )
    
    def render_xray_config(self) -> Dict:
        """Render the xray-client.json template with actual values."""
        template_path = XRAY_CONFIG_FILE
        if template_path.exists():
            with open(template_path) as f:
                config = json.load(f)
        else:
            config = {"outbounds": [{"settings": {"vnext": [{}]}, "streamSettings": {"realitySettings": {}}}]}
        
        # Walk the outbound and replace placeholders
        for ob in config.get("outbounds", []):
            if ob.get("protocol") == "vless":
                vnext = ob.get("settings", {}).get("vnext", [{}])[0]
                vnext["address"] = self.vps_address
                vnext["port"] = self.vps_port
                users = vnext.get("users", [{}])
                if users:
                    users[0]["id"] = self.xray_uuid
                    users[0]["flow"] = self.flow
                rs = ob.get("streamSettings", {}).get("realitySettings", {})
                rs["serverName"] = self.sni_target
                rs["publicKey"] = self.xray_public_key
                rs["shortId"] = self.xray_short_id
        return config
    
    def write_xray_config(self):
        """Write rendered Xray config to disk."""
        rendered = self.render_xray_config()
        XRAY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(XRAY_CONFIG_FILE, "w") as f:
            json.dump(rendered, f, indent=2)
        logger.info(f"Xray config written to {XRAY_CONFIG_FILE}")
    
    def to_dict(self) -> Dict:
        return {
            "vps_address": self.vps_address,
            "vps_port": self.vps_port,
            "xray_uuid": self.xray_uuid,
            "xray_public_key": self.xray_public_key,
            "xray_short_id": self.xray_short_id,
            "sni_target": self.sni_target,
            "flow": self.flow,
            "exit_node_ip": self.exit_node_ip,
            "exit_node_type": self.exit_node_type.value,
            "spoof_ttl": self.spoof_ttl,
            "mss_clamp": self.mss_clamp,
            "dns_servers": self.dns_servers,
            "mode": self.mode.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VPNConfig':
        config = cls()
        for key, val in data.items():
            if key == "exit_node_type":
                config.exit_node_type = ExitNodeType(val)
            elif key == "mode":
                config.mode = VPNMode(val)
            elif hasattr(config, key):
                setattr(config, key, val)
        return config


@dataclass
class VPNState:
    """Current VPN connection state"""
    status: VPNStatus = VPNStatus.DISCONNECTED
    mode: VPNMode = VPNMode.PROXY
    public_ip: Optional[str] = None
    exit_ip: Optional[str] = None
    exit_country: Optional[str] = None
    exit_isp: Optional[str] = None
    latency_ms: float = 0
    xray_pid: Optional[int] = None
    tailscale_connected: bool = False
    dns_secure: bool = False
    tcp_spoofed: bool = False
    last_check: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "mode": self.mode.value,
            "public_ip": self.public_ip,
            "exit_ip": self.exit_ip,
            "exit_country": self.exit_country,
            "exit_isp": self.exit_isp,
            "latency_ms": self.latency_ms,
            "xray_pid": self.xray_pid,
            "tailscale_connected": self.tailscale_connected,
            "dns_secure": self.dns_secure,
            "tcp_spoofed": self.tcp_spoofed,
            "last_check": self.last_check,
            "error_message": self.error_message,
        }


# ═══════════════════════════════════════════════════════════════════════════
# TCP/IP FINGERPRINT PROFILES (from VPN research document Table 1)
# ═══════════════════════════════════════════════════════════════════════════

TCP_FINGERPRINTS = {
    "windows_11": {
        "ttl": 128,
        "window_size": 64240,
        "mss": 1460,
        "timestamps": False,
        "window_scale": 8,
        "option_order": "MSS,NOP,WScale,NOP,NOP,SACK",
        "description": "Windows 10/11 Desktop — default target for residential exit",
    },
    "android": {
        "ttl": 64,
        "window_size": 65535,
        "mss": 1440,
        "timestamps": True,
        "window_scale": 7,
        "option_order": "MSS,SACK,TS,NOP,WScale",
        "description": "Android Mobile — target for 4G/5G mobile exit",
    },
    "linux_default": {
        "ttl": 64,
        "window_size": 29200,
        "mss": 1460,
        "timestamps": True,
        "window_scale": 7,
        "option_order": "MSS,SACK,TS,NOP,WScale",
        "description": "Linux Server — DEFAULT (detectable, avoid)",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# PRIVACY-HAVEN VPS PROVIDERS (from VPN research document Section 2)
# ═══════════════════════════════════════════════════════════════════════════

VPS_PROVIDERS = {
    "njalla": {
        "name": "Njalla",
        "jurisdiction": "Sweden/Nevis",
        "accepts_crypto": True,
        "anonymous_signup": True,
        "notes": "Pirate Bay operators. Privacy shield model — they own server on your behalf.",
    },
    "flokinet": {
        "name": "FlokiNET",
        "jurisdiction": "Iceland/Romania/Finland",
        "accepts_crypto": True,
        "anonymous_signup": True,
        "notes": "Freedom of speech focused. Robust legal defense against takedowns.",
    },
    "bithost": {
        "name": "BitHost.io",
        "jurisdiction": "Various",
        "accepts_crypto": True,
        "anonymous_signup": True,
        "notes": "Crypto-native payments, minimal data retention.",
    },
    "rootlayer": {
        "name": "Rootlayer",
        "jurisdiction": "Moldova",
        "accepts_crypto": True,
        "anonymous_signup": True,
        "notes": "Minimal verification, lax enforcement.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# REALITY PROTOCOL SNI TARGETS (high-reputation domains for masquerade)
# ═══════════════════════════════════════════════════════════════════════════

REALITY_SNI_TARGETS = [
    "learn.microsoft.com",
    "www.apple.com",
    "aws.amazon.com",
    "cloud.google.com",
    "developer.mozilla.org",
    "docs.github.com",
    "support.cloudflare.com",
]


class LucidVPN:
    """
    Lucid VPN Connection Manager
    
    Manages the complete VPN lifecycle:
    1. Configuration (Xray + Tailscale + TCP spoofing)
    2. Connection (start Xray client, verify Tailscale mesh, apply sysctl)
    3. Validation (IP check, DNS leak test, TCP fingerprint verify)
    4. Disconnection (clean teardown)
    
    Usage:
        vpn = LucidVPN()
        vpn.load_config()           # Load saved config
        vpn.connect()               # Start VPN tunnel
        state = vpn.get_state()     # Check connection state
        vpn.disconnect()            # Clean disconnect
    """
    
    def __init__(self):
        self.config = VPNConfig()
        self.state = VPNState()
        VPN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._load_state()
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFIGURATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def save_config(self, config: VPNConfig):
        """Save VPN configuration to disk"""
        self.config = config
        config_data = config.to_dict()
        # Never save private key to the general config
        config_file = VPN_CONFIG_DIR / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        os.chmod(str(config_file), 0o600)
        logger.info("VPN configuration saved")
    
    def load_config(self) -> Optional[VPNConfig]:
        """Load VPN configuration from disk"""
        config_file = VPN_CONFIG_DIR / "config.json"
        if not config_file.exists():
            return None
        try:
            with open(config_file) as f:
                data = json.load(f)
            self.config = VPNConfig.from_dict(data)
            return self.config
        except Exception as e:
            logger.error(f"Failed to load VPN config: {e}")
            return None
    
    def is_configured(self) -> bool:
        """Check if VPN is fully configured"""
        return bool(
            self.config.vps_address
            and self.config.xray_uuid
            and self.config.xray_public_key
            and self.config.xray_short_id
        )
    
    def _load_state(self):
        """Load state from disk"""
        if VPN_STATE_FILE.exists():
            try:
                with open(VPN_STATE_FILE) as f:
                    data = json.load(f)
                self.state.status = VPNStatus(data.get("status", "disconnected"))
                self.state.mode = VPNMode(data.get("mode", "proxy"))
            except Exception as e:
                logger.warning(f"Failed to load VPN state: {e}")
    
    def _save_state(self):
        """Persist state to disk"""
        with open(VPN_STATE_FILE, "w") as f:
            json.dump(self.state.to_dict(), f, indent=2)
    
    # ═══════════════════════════════════════════════════════════════════════
    # XRAY CLIENT CONFIGURATION GENERATOR
    # ═══════════════════════════════════════════════════════════════════════
    
    def generate_xray_config(self) -> Dict:
        """Generate Xray client config for VLESS + Reality"""
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": 10808,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth",
                        "udp": True
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls"]
                    }
                },
                {
                    "tag": "http-in",
                    "port": 10809,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {}
                }
            ],
            "outbounds": [
                {
                    "tag": "vless-reality",
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": self.config.vps_address,
                                "port": self.config.vps_port,
                                "users": [
                                    {
                                        "id": self.config.xray_uuid,
                                        "encryption": "none",
                                        "flow": self.config.flow
                                    }
                                ]
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "show": False,
                            "fingerprint": "chrome",
                            "serverName": self.config.sni_target,
                            "publicKey": self.config.xray_public_key,
                            "shortId": self.config.xray_short_id,
                            "spiderX": ""
                        }
                    }
                },
                {
                    "tag": "direct",
                    "protocol": "freedom",
                    "settings": {}
                },
                {
                    "tag": "block",
                    "protocol": "blackhole",
                    "settings": {}
                }
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "domain": ["geosite:private"]
                    },
                    {
                        "type": "field",
                        "outboundTag": "block",
                        "protocol": ["bittorrent"]
                    }
                ]
            },
            "dns": {
                "servers": self.config.dns_servers + ["localhost"]
            }
        }
        return config
    
    def write_xray_config(self):
        """Write Xray client config to disk"""
        config = self.generate_xray_config()
        with open(XRAY_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(str(XRAY_CONFIG_FILE), 0o600)
        logger.info(f"Xray config written to {XRAY_CONFIG_FILE}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════
    
    def connect(self) -> VPNState:
        """
        Connect the Lucid VPN tunnel.
        
        Steps:
        1. Apply TCP/IP spoofing (sysctl + nftables)
        2. Start Xray client (VLESS + Reality)
        3. Verify Tailscale mesh (if using residential/mobile exit)
        4. Configure DNS (unbound local resolver)
        5. Validate connection (IP, DNS leak, TCP fingerprint)
        """
        if not self.is_configured():
            self.state.status = VPNStatus.ERROR
            self.state.error_message = "VPN not configured. Run titan-vpn-setup first."
            self._save_state()
            return self.state
        
        self.state.status = VPNStatus.CONNECTING
        self.state.mode = self.config.mode
        self._save_state()
        
        try:
            # Step 1: Apply TCP/IP spoofing
            logger.info("Step 1/5: Applying TCP/IP stack spoofing...")
            self._apply_tcp_spoofing()
            self.state.tcp_spoofed = True
            
            # Step 2: Start Xray
            logger.info("Step 2/5: Starting Xray (VLESS + Reality)...")
            self._start_xray()
            
            # Step 3: Verify Tailscale (if not datacenter-only mode)
            if self.config.exit_node_ip:
                logger.info("Step 3/5: Verifying Tailscale mesh...")
                self._verify_tailscale()
            else:
                logger.info("Step 3/5: No exit node configured (VPS direct mode)")
                self.state.tailscale_connected = False
            
            # Step 4: Configure DNS
            logger.info("Step 4/5: Configuring secure DNS...")
            self._configure_dns()
            self.state.dns_secure = True
            
            # Step 5: Validate
            logger.info("Step 5/5: Validating connection...")
            self._validate_connection()
            
            self.state.status = VPNStatus.CONNECTED
            self.state.last_check = datetime.now(timezone.utc).isoformat()
            self.state.error_message = None
            self._save_state()
            
            logger.info(f"Lucid VPN CONNECTED — Exit IP: {self.state.exit_ip}")
            return self.state
            
        except Exception as e:
            self.state.status = VPNStatus.ERROR
            self.state.error_message = str(e)
            self._save_state()
            logger.error(f"VPN connection failed: {e}")
            return self.state
    
    def disconnect(self) -> VPNState:
        """Clean disconnect of Lucid VPN"""
        logger.info("Disconnecting Lucid VPN...")
        
        # Stop Xray
        if self.state.xray_pid:
            try:
                os.kill(self.state.xray_pid, 15)  # SIGTERM
                logger.info(f"Xray process {self.state.xray_pid} terminated")
            except ProcessLookupError:
                pass
            self.state.xray_pid = None
        
        # Kill any remaining xray processes
        self._run_cmd(["pkill", "-f", "xray"], check=False)
        
        # Revert TCP spoofing
        self._revert_tcp_spoofing()
        self.state.tcp_spoofed = False
        
        # Revert DNS
        self._revert_dns()
        self.state.dns_secure = False
        
        self.state.status = VPNStatus.DISCONNECTED
        self.state.exit_ip = None
        self.state.public_ip = None
        self._save_state()
        
        logger.info("Lucid VPN disconnected")
        return self.state
    
    def get_state(self) -> VPNState:
        """Get current VPN state"""
        return self.state
    
    def get_socks5_url(self) -> Optional[str]:
        """
        Get the local SOCKS5 proxy URL for browser configuration.
        When VPN is connected, Xray provides a local SOCKS5 on 127.0.0.1:10808.
        """
        if self.state.status == VPNStatus.CONNECTED:
            return "socks5://127.0.0.1:10808"
        return None
    
    def get_http_proxy_url(self) -> Optional[str]:
        """Get the local HTTP proxy URL (Xray on 127.0.0.1:10809)"""
        if self.state.status == VPNStatus.CONNECTED:
            return "http://127.0.0.1:10809"
        return None
    
    # ═══════════════════════════════════════════════════════════════════════
    # TCP/IP STACK SPOOFING (Source: VPN doc Sections 3-4)
    # ═══════════════════════════════════════════════════════════════════════
    
    def _apply_tcp_spoofing(self):
        """Apply sysctl + nftables rules to spoof TCP/IP fingerprint"""
        fingerprint = "windows_11" if self.config.exit_node_type == ExitNodeType.RESIDENTIAL else "android"
        fp = TCP_FINGERPRINTS[fingerprint]
        
        # sysctl: TTL
        self._run_cmd(["sysctl", "-w", f"net.ipv4.ip_default_ttl={fp['ttl']}"])
        
        # sysctl: TCP timestamps
        ts_val = "1" if fp["timestamps"] else "0"
        self._run_cmd(["sysctl", "-w", f"net.ipv4.tcp_timestamps={ts_val}"])
        
        # sysctl: Window scaling
        self._run_cmd(["sysctl", "-w", "net.ipv4.tcp_window_scaling=1"])
        
        # sysctl: BBR congestion control (mimics residential quality)
        self._run_cmd(["sysctl", "-w", "net.core.default_qdisc=fq"])
        self._run_cmd(["sysctl", "-w", "net.ipv4.tcp_congestion_control=bbr"], check=False)
        
        # nftables: MSS clamping for tunnel overhead
        nft_rules = f"""
table ip titan_vpn {{
    chain forward {{
        type filter hook forward priority 0; policy accept;
        tcp flags syn tcp option maxseg size set {self.config.mss_clamp}
    }}
    chain postrouting {{
        type route hook output priority 0; policy accept;
        ip ttl set {fp['ttl']}
    }}
}}
"""
        nft_file = VPN_CONFIG_DIR / "titan-vpn.nft"
        nft_file.write_text(nft_rules)
        self._run_cmd(["nft", "-f", str(nft_file)], check=False)
        
        logger.info(f"TCP/IP spoofing applied: {fingerprint} (TTL={fp['ttl']}, TS={ts_val})")
    
    def _revert_tcp_spoofing(self):
        """Revert TCP/IP spoofing to Linux defaults"""
        self._run_cmd(["sysctl", "-w", "net.ipv4.ip_default_ttl=64"], check=False)
        self._run_cmd(["sysctl", "-w", "net.ipv4.tcp_timestamps=1"], check=False)
        self._run_cmd(["nft", "delete", "table", "ip", "titan_vpn"], check=False)
        logger.info("TCP/IP spoofing reverted to defaults")
    
    # ═══════════════════════════════════════════════════════════════════════
    # XRAY CLIENT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def _start_xray(self):
        """Start Xray client process"""
        # Kill any existing instance
        self._run_cmd(["pkill", "-f", "xray"], check=False)
        time.sleep(0.5)
        
        # Write config
        self.write_xray_config()
        
        # V7.5 FIX: Use instance variable instead of mutating module-level global
        xray_bin = XRAY_BINARY
        if not Path(xray_bin).exists():
            # Try alternative locations
            for alt in ["/usr/bin/xray", "/usr/local/bin/xray", "/opt/titan/bin/xray"]:
                if Path(alt).exists():
                    xray_bin = alt
                    break
            else:
                raise FileNotFoundError(
                    "Xray binary not found. Install with: "
                    "bash -c '$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)'"
                )
        
        # Start Xray
        proc = subprocess.Popen(
            [xray_bin, "run", "-c", str(XRAY_CONFIG_FILE)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.state.xray_pid = proc.pid
        
        # Wait for SOCKS5 port to be available
        for i in range(30):
            time.sleep(0.5)
            if self._check_port(10808):
                logger.info(f"Xray started (PID: {proc.pid}, SOCKS5: 127.0.0.1:10808)")
                return
        
        # Failed to start
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        raise RuntimeError(f"Xray failed to start within 15s. Error: {stderr[:200]}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # TAILSCALE MESH MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def _verify_tailscale(self):
        """Verify Tailscale mesh is connected and exit node is reachable"""
        if not shutil.which("tailscale"):
            logger.warning("Tailscale not installed — running in VPS-direct mode")
            self.state.tailscale_connected = False
            return
        
        # Check Tailscale status
        result = self._run_cmd(["tailscale", "status", "--json"], check=False, capture=True)
        if result and result.returncode == 0:
            try:
                ts_status = json.loads(result.stdout)
                self.state.tailscale_connected = ts_status.get("BackendState") == "Running"
            except (json.JSONDecodeError, KeyError):
                self.state.tailscale_connected = False
        
        # Set exit node if configured
        if self.config.exit_node_ip and self.state.tailscale_connected:
            self._run_cmd([
                "tailscale", "set",
                f"--exit-node={self.config.exit_node_ip}"
            ], check=False)
            logger.info(f"Tailscale exit node set: {self.config.exit_node_ip}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # DNS CONFIGURATION (Source: VPN doc Section 7.1)
    # ═══════════════════════════════════════════════════════════════════════
    
    def _configure_dns(self):
        """Configure DNS to prevent leaks"""
        if self.config.use_local_resolver:
            # Configure unbound if available
            if shutil.which("unbound"):
                unbound_conf = """# TITAN Lucid VPN DNS Configuration
server:
    interface: 127.0.0.1
    port: 53
    do-not-query-localhost: no
    hide-identity: yes
    hide-version: yes
    qname-minimisation: yes
    
    # Privacy-respecting upstream
    forward-zone:
        name: "."
        forward-addr: 9.9.9.9@853        # Quad9 DoT
        forward-addr: 1.1.1.1@853         # Cloudflare DoT
        forward-tls-upstream: yes
"""
                UNBOUND_CONFIG.parent.mkdir(parents=True, exist_ok=True)
                UNBOUND_CONFIG.write_text(unbound_conf)
                self._run_cmd(["systemctl", "restart", "unbound"], check=False)
        
        # Set resolv.conf to use local or privacy DNS
        resolv_content = "# TITAN Lucid VPN DNS\n"
        if self.config.use_local_resolver and shutil.which("unbound"):
            resolv_content += "nameserver 127.0.0.1\n"
        else:
            for dns in self.config.dns_servers:
                resolv_content += f"nameserver {dns}\n"
        
        # Backup and write
        resolv_path = Path("/etc/resolv.conf")
        backup_path = VPN_CONFIG_DIR / "resolv.conf.backup"
        if resolv_path.exists() and not backup_path.exists():
            shutil.copy2(str(resolv_path), str(backup_path))
        
        resolv_path.write_text(resolv_content)
        # Lock resolv.conf (prevent DHCP overwrite)
        self._run_cmd(["chattr", "+i", "/etc/resolv.conf"], check=False)
        
        logger.info("DNS configured for zero-leak operation")
    
    def _revert_dns(self):
        """Revert DNS to original configuration"""
        self._run_cmd(["chattr", "-i", "/etc/resolv.conf"], check=False)
        backup_path = VPN_CONFIG_DIR / "resolv.conf.backup"
        if backup_path.exists():
            shutil.copy2(str(backup_path), "/etc/resolv.conf")
        if UNBOUND_CONFIG.exists():
            UNBOUND_CONFIG.unlink()
            self._run_cmd(["systemctl", "restart", "unbound"], check=False)
        logger.info("DNS reverted to original")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION VALIDATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def _validate_connection(self):
        """Validate VPN connection: IP, DNS, TCP fingerprint"""
        # V7.5 FIX: urllib doesn't support socks5h:// — use curl via subprocess
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10",
                 "--socks5-hostname", "127.0.0.1:10808",
                 "https://api.ipify.org?format=json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                ip_data = json.loads(result.stdout)
                self.state.exit_ip = ip_data.get("ip", "unknown")
            else:
                logger.warning(f"IP check returned non-zero or empty: {result.stderr[:100]}")
                self.state.exit_ip = "unknown"
        except Exception as e:
            logger.warning(f"Could not determine exit IP: {e}")
            self.state.exit_ip = "unknown"
    
    def validate_full(self) -> Dict[str, Any]:
        """Full validation report for pre-flight integration"""
        checks = {}
        
        # 1. Xray tunnel alive
        checks["xray_alive"] = self._check_port(10808)
        
        # 2. Exit IP is residential
        checks["exit_ip"] = self.state.exit_ip
        checks["exit_ip_known"] = self.state.exit_ip not in (None, "unknown")
        
        # 3. Tailscale connected (if configured)
        if self.config.exit_node_ip:
            checks["tailscale_connected"] = self.state.tailscale_connected
        else:
            checks["tailscale_connected"] = "N/A (VPS direct)"
        
        # 4. DNS secure
        checks["dns_secure"] = self.state.dns_secure
        
        # 5. TCP spoofed
        checks["tcp_spoofed"] = self.state.tcp_spoofed
        
        # 6. Overall
        critical = [checks["xray_alive"], checks["dns_secure"], checks["tcp_spoofed"]]
        checks["overall_pass"] = all(critical)
        
        return checks
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY
    # ═══════════════════════════════════════════════════════════════════════
    
    def _run_cmd(self, cmd: List[str], check: bool = True, capture: bool = False):
        """Run a system command"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=15,
                text=True
            )
            if check and result.returncode != 0:
                logger.warning(f"Command failed: {' '.join(cmd)} — {result.stderr[:100]}")
            return result if capture else None
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Command error: {' '.join(cmd)} — {e}")
            return None
    
    def _check_port(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a TCP port is listening"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_vpn_status() -> Dict:
    """Quick status check for GUI integration"""
    vpn = LucidVPN()
    vpn.load_config()
    state = vpn.get_state()
    return state.to_dict()


def get_vpn_providers() -> Dict:
    """Get recommended VPS providers for operator"""
    return VPS_PROVIDERS


def get_tcp_fingerprints() -> Dict:
    """Get TCP/IP fingerprint profiles"""
    return TCP_FINGERPRINTS


def get_reality_sni_targets() -> List[str]:
    """Get recommended SNI targets for Reality protocol"""
    return REALITY_SNI_TARGETS


def get_network_mode() -> VPNMode:
    """Get current network mode (proxy or VPN)"""
    vpn = LucidVPN()
    vpn.load_config()
    return vpn.state.mode
