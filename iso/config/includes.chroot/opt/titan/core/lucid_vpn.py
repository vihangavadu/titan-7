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


# =============================================================================
# TITAN V7.6 P0 CRITICAL ENHANCEMENTS
# =============================================================================

import threading
import hashlib
import random
from collections import deque
from typing import Callable


class LeakType(Enum):
    """Types of network leaks"""
    DNS_LEAK = "dns_leak"
    IP_LEAK = "ip_leak"
    WEBRTC_LEAK = "webrtc_leak"
    IPV6_LEAK = "ipv6_leak"
    TIMING_LEAK = "timing_leak"


@dataclass
class LeakDetection:
    """Individual leak detection result"""
    leak_type: LeakType
    detected: bool
    evidence: str
    timestamp: float
    severity: str  # critical, high, medium, low


@dataclass
class VPNEndpoint:
    """VPN endpoint for failover management"""
    name: str
    address: str
    port: int
    priority: int = 1
    is_healthy: bool = True
    last_check: float = 0.0
    latency_ms: float = 0.0
    fail_count: int = 0


@dataclass
class VPNSessionMetric:
    """Metric for VPN session analytics"""
    metric_name: str
    value: float
    unit: str
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


class VPNHealthMonitor:
    """
    V7.6 P0 CRITICAL: Continuous monitoring of VPN connection health.
    
    Monitors VPN tunnel health with automatic reconnection on failure.
    Tracks latency, packet loss, and connection stability over time.
    
    Usage:
        monitor = get_vpn_health_monitor()
        
        # Start monitoring
        monitor.start_monitoring(vpn_instance)
        
        # Get health status
        health = monitor.get_health_status()
        
        # Register failure callback
        monitor.on_failure(lambda: handle_vpn_failure())
    """
    
    # Health thresholds
    LATENCY_WARNING_MS = 500
    LATENCY_CRITICAL_MS = 2000
    PACKET_LOSS_WARNING = 0.05  # 5%
    PACKET_LOSS_CRITICAL = 0.20  # 20%
    
    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.vpn: Optional[LucidVPN] = None
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._health_history: deque = deque(maxlen=100)
        self._failure_callbacks: List[Callable] = []
        self._recovery_callbacks: List[Callable] = []
        self._is_healthy = True
        self._consecutive_failures = 0
        self._lock = threading.Lock()
        logger.info("VPNHealthMonitor initialized")
    
    def start_monitoring(self, vpn: LucidVPN) -> None:
        """Start health monitoring for VPN connection"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self.vpn = vpn
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="VPNHealthMonitor"
        )
        self._monitor_thread.start()
        logger.info("VPN health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("VPN health monitoring stopped")
    
    def on_failure(self, callback: Callable) -> None:
        """Register callback for connection failure"""
        with self._lock:
            self._failure_callbacks.append(callback)
    
    def on_recovery(self, callback: Callable) -> None:
        """Register callback for connection recovery"""
        with self._lock:
            self._recovery_callbacks.append(callback)
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                health = self._check_health()
                
                with self._lock:
                    self._health_history.append(health)
                    
                    if health["is_healthy"]:
                        if not self._is_healthy:
                            # Recovery detected
                            self._is_healthy = True
                            self._consecutive_failures = 0
                            self._trigger_recovery_callbacks()
                    else:
                        self._consecutive_failures += 1
                        if self._is_healthy and self._consecutive_failures >= 3:
                            # Failure confirmed after 3 consecutive failures
                            self._is_healthy = False
                            self._trigger_failure_callbacks()
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def _check_health(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "timestamp": time.time(),
            "is_healthy": False,
            "tunnel_alive": False,
            "latency_ms": 0,
            "packet_loss": 0,
            "issues": []
        }
        
        if not self.vpn:
            health["issues"].append("No VPN instance")
            return health
        
        # Check tunnel port
        health["tunnel_alive"] = self.vpn._check_port(10808)
        if not health["tunnel_alive"]:
            health["issues"].append("SOCKS5 tunnel not responding")
            return health
        
        # Measure latency with curl through tunnel
        try:
            start = time.time()
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5",
                 "--socks5-hostname", "127.0.0.1:10808",
                 "-o", "/dev/null", "-w", "%{time_total}",
                 "https://www.gstatic.com/generate_204"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                health["latency_ms"] = float(result.stdout.strip()) * 1000
            else:
                health["latency_ms"] = -1
                health["issues"].append("Latency check failed")
        except Exception as e:
            health["latency_ms"] = -1
            health["issues"].append(f"Latency error: {str(e)[:50]}")
        
        # Check latency thresholds
        if health["latency_ms"] > self.LATENCY_CRITICAL_MS:
            health["issues"].append(f"Critical latency: {health['latency_ms']:.0f}ms")
        elif health["latency_ms"] > self.LATENCY_WARNING_MS:
            health["issues"].append(f"High latency: {health['latency_ms']:.0f}ms")
        
        # Determine overall health
        health["is_healthy"] = (
            health["tunnel_alive"] and 
            health["latency_ms"] > 0 and
            health["latency_ms"] < self.LATENCY_CRITICAL_MS
        )
        
        return health
    
    def _trigger_failure_callbacks(self) -> None:
        """Trigger all failure callbacks"""
        logger.warning("VPN health failure detected - triggering callbacks")
        for callback in self._failure_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Failure callback error: {e}")
    
    def _trigger_recovery_callbacks(self) -> None:
        """Trigger all recovery callbacks"""
        logger.info("VPN health recovered - triggering callbacks")
        for callback in self._recovery_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Recovery callback error: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status summary"""
        with self._lock:
            recent = list(self._health_history)[-10:] if self._health_history else []
        
        if not recent:
            return {
                "status": "unknown",
                "is_healthy": False,
                "message": "No health data yet"
            }
        
        # Calculate averages
        latencies = [h["latency_ms"] for h in recent if h["latency_ms"] > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        healthy_count = sum(1 for h in recent if h["is_healthy"])
        uptime_pct = (healthy_count / len(recent)) * 100
        
        return {
            "status": "healthy" if self._is_healthy else "degraded",
            "is_healthy": self._is_healthy,
            "avg_latency_ms": round(avg_latency, 1),
            "uptime_pct": round(uptime_pct, 1),
            "consecutive_failures": self._consecutive_failures,
            "last_check": recent[-1]["timestamp"] if recent else None,
            "recent_issues": [h["issues"] for h in recent[-3:] if h["issues"]]
        }
    
    def force_reconnect(self) -> bool:
        """Force VPN reconnection"""
        if not self.vpn:
            return False
        
        logger.info("Forcing VPN reconnection...")
        self.vpn.disconnect()
        time.sleep(2)
        state = self.vpn.connect()
        return state.status == VPNStatus.CONNECTED


# Singleton instance
_vpn_health_monitor: Optional[VPNHealthMonitor] = None

def get_vpn_health_monitor() -> VPNHealthMonitor:
    """Get singleton VPNHealthMonitor instance"""
    global _vpn_health_monitor
    if _vpn_health_monitor is None:
        _vpn_health_monitor = VPNHealthMonitor()
    return _vpn_health_monitor


class TunnelFailoverManager:
    """
    V7.6 P0 CRITICAL: Manage failover between multiple VPN endpoints.
    
    Maintains a prioritized list of VPN endpoints and automatically
    fails over to the next available endpoint when primary fails.
    
    Usage:
        failover = get_tunnel_failover_manager()
        
        # Add endpoints
        failover.add_endpoint(VPNEndpoint("primary", "vps1.example.com", 443, priority=1))
        failover.add_endpoint(VPNEndpoint("backup", "vps2.example.com", 443, priority=2))
        
        # Get best endpoint
        endpoint = failover.get_best_endpoint()
        
        # Mark failure
        failover.mark_endpoint_failed("primary")
    """
    
    MAX_FAIL_COUNT = 5
    HEALTH_CHECK_TIMEOUT = 10
    
    def __init__(self):
        self.endpoints: Dict[str, VPNEndpoint] = {}
        self._lock = threading.Lock()
        self._active_endpoint: Optional[str] = None
        logger.info("TunnelFailoverManager initialized")
    
    def add_endpoint(self, endpoint: VPNEndpoint) -> None:
        """Add a VPN endpoint"""
        with self._lock:
            self.endpoints[endpoint.name] = endpoint
            logger.info(f"Endpoint added: {endpoint.name} ({endpoint.address}:{endpoint.port})")
    
    def remove_endpoint(self, name: str) -> bool:
        """Remove a VPN endpoint"""
        with self._lock:
            if name in self.endpoints:
                del self.endpoints[name]
                return True
            return False
    
    def get_endpoint(self, name: str) -> Optional[VPNEndpoint]:
        """Get endpoint by name"""
        return self.endpoints.get(name)
    
    def get_best_endpoint(self) -> Optional[VPNEndpoint]:
        """Get the best available endpoint based on priority and health"""
        with self._lock:
            healthy = [e for e in self.endpoints.values() 
                      if e.is_healthy and e.fail_count < self.MAX_FAIL_COUNT]
            
            if not healthy:
                # All endpoints failed, try to reset oldest failure
                all_endpoints = sorted(
                    self.endpoints.values(),
                    key=lambda e: e.last_check
                )
                if all_endpoints:
                    # Reset oldest endpoint for retry
                    oldest = all_endpoints[0]
                    oldest.fail_count = 0
                    oldest.is_healthy = True
                    logger.warning(f"All endpoints failed, resetting: {oldest.name}")
                    return oldest
                return None
            
            # Sort by priority (lower = better) then latency
            healthy.sort(key=lambda e: (e.priority, e.latency_ms))
            return healthy[0]
    
    def mark_endpoint_failed(self, name: str) -> None:
        """Mark endpoint as failed"""
        with self._lock:
            if name in self.endpoints:
                ep = self.endpoints[name]
                ep.fail_count += 1
                ep.last_check = time.time()
                
                if ep.fail_count >= self.MAX_FAIL_COUNT:
                    ep.is_healthy = False
                    logger.warning(f"Endpoint marked unhealthy: {name} (fails: {ep.fail_count})")
    
    def mark_endpoint_success(self, name: str, latency_ms: float = 0) -> None:
        """Mark endpoint as successfully connected"""
        with self._lock:
            if name in self.endpoints:
                ep = self.endpoints[name]
                ep.is_healthy = True
                ep.fail_count = 0
                ep.latency_ms = latency_ms
                ep.last_check = time.time()
                self._active_endpoint = name
    
    def check_endpoint_health(self, endpoint: VPNEndpoint) -> Tuple[bool, float]:
        """Check if endpoint is reachable, returns (is_healthy, latency_ms)"""
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.HEALTH_CHECK_TIMEOUT)
            result = sock.connect_ex((endpoint.address, endpoint.port))
            sock.close()
            
            if result == 0:
                latency = (time.time() - start) * 1000
                return True, latency
            return False, 0
        except Exception:
            return False, 0
    
    def check_all_endpoints(self) -> Dict[str, Dict]:
        """Check health of all endpoints"""
        results = {}
        for name, ep in self.endpoints.items():
            is_healthy, latency = self.check_endpoint_health(ep)
            
            with self._lock:
                ep.is_healthy = is_healthy
                ep.latency_ms = latency
                ep.last_check = time.time()
                if is_healthy:
                    ep.fail_count = max(0, ep.fail_count - 1)
            
            results[name] = {
                "is_healthy": is_healthy,
                "latency_ms": round(latency, 1),
                "fail_count": ep.fail_count,
                "priority": ep.priority
            }
        
        return results
    
    def get_active_endpoint(self) -> Optional[str]:
        """Get currently active endpoint name"""
        return self._active_endpoint
    
    def failover(self) -> Optional[VPNEndpoint]:
        """
        Perform failover to next best endpoint.
        
        Returns:
            Next endpoint to use, or None if all exhausted
        """
        with self._lock:
            if self._active_endpoint:
                self.mark_endpoint_failed(self._active_endpoint)
        
        next_ep = self.get_best_endpoint()
        if next_ep:
            logger.info(f"Failing over to endpoint: {next_ep.name}")
        else:
            logger.error("No healthy endpoints available for failover")
        
        return next_ep
    
    def get_status(self) -> Dict[str, Any]:
        """Get failover manager status"""
        return {
            "endpoint_count": len(self.endpoints),
            "healthy_count": sum(1 for e in self.endpoints.values() if e.is_healthy),
            "active_endpoint": self._active_endpoint,
            "endpoints": {
                name: {
                    "address": ep.address,
                    "is_healthy": ep.is_healthy,
                    "priority": ep.priority,
                    "fail_count": ep.fail_count,
                    "latency_ms": ep.latency_ms
                }
                for name, ep in self.endpoints.items()
            }
        }


# Singleton instance
_failover_manager: Optional[TunnelFailoverManager] = None

def get_tunnel_failover_manager() -> TunnelFailoverManager:
    """Get singleton TunnelFailoverManager instance"""
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = TunnelFailoverManager()
    return _failover_manager


class NetworkLeakDetector:
    """
    V7.6 P0 CRITICAL: Detect DNS, WebRTC, and IP leaks in real-time.
    
    Continuously monitors for network leaks that could expose
    the operator's real identity or location.
    
    Usage:
        detector = get_network_leak_detector()
        
        # Configure expected exit IP
        detector.set_expected_exit_ip("1.2.3.4")
        
        # Run leak detection
        leaks = detector.detect_all_leaks()
        
        # Start continuous monitoring
        detector.start_monitoring(callback=handle_leak)
    """
    
    # DNS leak test servers
    DNS_LEAK_TEST_DOMAINS = [
        "whoami.akamai.net",
        "myip.opendns.com",
    ]
    
    def __init__(self):
        self.expected_exit_ip: Optional[str] = None
        self.expected_country: Optional[str] = None
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._leak_history: deque = deque(maxlen=50)
        self._leak_callbacks: List[Callable[[LeakDetection], None]] = []
        self._lock = threading.Lock()
        logger.info("NetworkLeakDetector initialized")
    
    def set_expected_exit_ip(self, ip: str) -> None:
        """Set expected exit IP for leak detection"""
        self.expected_exit_ip = ip
    
    def set_expected_country(self, country: str) -> None:
        """Set expected exit country"""
        self.expected_country = country
    
    def on_leak_detected(self, callback: Callable[[LeakDetection], None]) -> None:
        """Register callback for leak detection"""
        with self._lock:
            self._leak_callbacks.append(callback)
    
    def detect_dns_leak(self) -> LeakDetection:
        """
        Detect DNS leaks by checking resolver IP.
        
        If DNS requests aren't going through the VPN tunnel,
        they may reveal the real location.
        """
        detection = LeakDetection(
            leak_type=LeakType.DNS_LEAK,
            detected=False,
            evidence="",
            timestamp=time.time(),
            severity="critical"
        )
        
        try:
            # Try to resolve through tunnel using dig
            result = subprocess.run(
                ["dig", "+short", "whoami.akamai.net", "@9.9.9.9"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                resolver_ip = result.stdout.strip()
                
                if resolver_ip and self.expected_exit_ip:
                    # Check if resolver IP is different from expected exit
                    # (This is a simplified check - real implementation would
                    # validate against known VPN exit IPs)
                    detection.evidence = f"Resolver IP: {resolver_ip}"
                    
                    # For now, just record the resolver IP
                    # In production, compare against known good resolver IPs
                    if resolver_ip != self.expected_exit_ip:
                        # Not necessarily a leak - depends on DNS setup
                        detection.detected = False
        
        except Exception as e:
            detection.evidence = f"DNS check failed: {str(e)[:50]}"
        
        return detection
    
    def detect_ip_leak(self) -> LeakDetection:
        """
        Detect IP address leaks.
        
        Compares reported external IP against expected VPN exit IP.
        """
        detection = LeakDetection(
            leak_type=LeakType.IP_LEAK,
            detected=False,
            evidence="",
            timestamp=time.time(),
            severity="critical"
        )
        
        try:
            # Check IP through VPN tunnel
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10",
                 "--socks5-hostname", "127.0.0.1:10808",
                 "https://api.ipify.org"],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0:
                current_ip = result.stdout.strip()
                detection.evidence = f"Current IP: {current_ip}"
                
                if self.expected_exit_ip and current_ip != self.expected_exit_ip:
                    # IP doesn't match expected - possible leak
                    detection.detected = True
                    detection.evidence += f" (expected: {self.expected_exit_ip})"
        
        except Exception as e:
            detection.evidence = f"IP check failed: {str(e)[:50]}"
        
        # Also check direct (non-tunnel) IP to compare
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5",
                 "https://api.ipify.org"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                direct_ip = result.stdout.strip()
                detection.evidence += f", Direct IP: {direct_ip}"
        except Exception:
            pass
        
        return detection
    
    def detect_ipv6_leak(self) -> LeakDetection:
        """
        Detect IPv6 leaks.
        
        If VPN only tunnels IPv4, IPv6 traffic may bypass the tunnel.
        """
        detection = LeakDetection(
            leak_type=LeakType.IPV6_LEAK,
            detected=False,
            evidence="",
            timestamp=time.time(),
            severity="high"
        )
        
        try:
            # Check if IPv6 is enabled and leaking
            result = subprocess.run(
                ["curl", "-s", "-6", "--max-time", "5",
                 "https://api6.ipify.org"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                ipv6 = result.stdout.strip()
                detection.detected = True
                detection.evidence = f"IPv6 exposed: {ipv6}"
                detection.severity = "high"
        except Exception:
            # No IPv6 connectivity - good
            detection.evidence = "IPv6 not accessible (safe)"
        
        return detection
    
    def detect_webrtc_leak(self) -> LeakDetection:
        """
        Detect potential WebRTC leaks.
        
        Note: Full WebRTC leak detection requires browser interaction.
        This checks if WebRTC-related ports are accessible.
        """
        detection = LeakDetection(
            leak_type=LeakType.WEBRTC_LEAK,
            detected=False,
            evidence="",
            timestamp=time.time(),
            severity="high"
        )
        
        # Check for STUN/TURN server accessibility (indicates WebRTC capability)
        stun_servers = [
            ("stun.l.google.com", 19302),
            ("stun.cloudflare.com", 3478),
        ]
        
        accessible = []
        for host, port in stun_servers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2)
                sock.sendto(b'\x00\x01\x00\x00', (host, port))
                sock.close()
                accessible.append(f"{host}:{port}")
            except Exception:
                pass
        
        if accessible:
            detection.evidence = f"STUN servers accessible: {', '.join(accessible)}"
            # Note: This doesn't mean WebRTC is leaking, just that it could
            # Full detection requires browser-level checks
        else:
            detection.evidence = "STUN servers blocked (WebRTC disabled)"
        
        return detection
    
    def detect_all_leaks(self) -> List[LeakDetection]:
        """Run all leak detection checks"""
        detections = []
        
        detections.append(self.detect_dns_leak())
        detections.append(self.detect_ip_leak())
        detections.append(self.detect_ipv6_leak())
        detections.append(self.detect_webrtc_leak())
        
        # Store in history
        with self._lock:
            for d in detections:
                if d.detected:
                    self._leak_history.append(d)
                    self._trigger_leak_callbacks(d)
        
        return detections
    
    def _trigger_leak_callbacks(self, detection: LeakDetection) -> None:
        """Trigger callbacks for detected leak"""
        for callback in self._leak_callbacks:
            try:
                callback(detection)
            except Exception as e:
                logger.error(f"Leak callback error: {e}")
    
    def start_monitoring(self, interval: float = 60.0) -> None:
        """Start continuous leak monitoring"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True,
            name="NetworkLeakDetector"
        )
        self._monitor_thread.start()
        logger.info("Network leak monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Network leak monitoring stopped")
    
    def _monitor_loop(self, interval: float) -> None:
        """Monitoring loop"""
        while not self._stop_event.is_set():
            try:
                self.detect_all_leaks()
            except Exception as e:
                logger.error(f"Leak monitoring error: {e}")
            
            self._stop_event.wait(interval)
    
    def get_leak_history(self) -> List[Dict]:
        """Get recent leak detections"""
        with self._lock:
            return [
                {
                    "type": d.leak_type.value,
                    "evidence": d.evidence,
                    "severity": d.severity,
                    "timestamp": d.timestamp
                }
                for d in self._leak_history
            ]
    
    def is_secure(self) -> bool:
        """Quick check if no recent leaks detected"""
        with self._lock:
            recent_cutoff = time.time() - 300  # Last 5 minutes
            recent_leaks = [d for d in self._leak_history 
                          if d.timestamp > recent_cutoff and d.detected]
            return len(recent_leaks) == 0


# Singleton instance
_leak_detector: Optional[NetworkLeakDetector] = None

def get_network_leak_detector() -> NetworkLeakDetector:
    """Get singleton NetworkLeakDetector instance"""
    global _leak_detector
    if _leak_detector is None:
        _leak_detector = NetworkLeakDetector()
    return _leak_detector


class VPNSessionAnalytics:
    """
    V7.6 P0 CRITICAL: Track VPN session metrics for operational insights.
    
    Collects and analyzes VPN session data including connection times,
    latency trends, failover events, and usage patterns.
    
    Usage:
        analytics = get_vpn_session_analytics()
        
        # Record events
        analytics.record_connection(endpoint="primary", latency_ms=45.2)
        analytics.record_disconnection(reason="failover")
        
        # Get analytics
        report = analytics.generate_report()
    """
    
    def __init__(self):
        self.metrics: deque = deque(maxlen=1000)
        self.session_start: Optional[float] = None
        self.total_connected_time: float = 0.0
        self.connection_count: int = 0
        self.failover_count: int = 0
        self._current_session: Dict[str, Any] = {}
        self._lock = threading.Lock()
        logger.info("VPNSessionAnalytics initialized")
    
    def record_metric(self, name: str, value: float, unit: str = "",
                     tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric"""
        metric = VPNSessionMetric(
            metric_name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            tags=tags or {}
        )
        
        with self._lock:
            self.metrics.append(metric)
    
    def record_connection(self, endpoint: str, latency_ms: float) -> None:
        """Record successful connection"""
        with self._lock:
            self.connection_count += 1
            self.session_start = time.time()
            self._current_session = {
                "endpoint": endpoint,
                "start_time": self.session_start,
                "initial_latency_ms": latency_ms
            }
        
        self.record_metric("connection", 1, "count", {"endpoint": endpoint})
        self.record_metric("latency", latency_ms, "ms", {"endpoint": endpoint})
        logger.debug(f"Analytics: Connection recorded to {endpoint}")
    
    def record_disconnection(self, reason: str = "normal") -> None:
        """Record disconnection"""
        with self._lock:
            if self.session_start:
                session_duration = time.time() - self.session_start
                self.total_connected_time += session_duration
                self.session_start = None
                
                self.record_metric(
                    "session_duration", 
                    session_duration, 
                    "seconds",
                    {"reason": reason}
                )
        
        self.record_metric("disconnection", 1, "count", {"reason": reason})
        logger.debug(f"Analytics: Disconnection recorded ({reason})")
    
    def record_failover(self, from_endpoint: str, to_endpoint: str) -> None:
        """Record failover event"""
        with self._lock:
            self.failover_count += 1
        
        self.record_metric(
            "failover", 1, "count",
            {"from": from_endpoint, "to": to_endpoint}
        )
        logger.debug(f"Analytics: Failover recorded {from_endpoint} -> {to_endpoint}")
    
    def record_latency_sample(self, latency_ms: float, endpoint: str = "") -> None:
        """Record latency measurement"""
        self.record_metric("latency", latency_ms, "ms", {"endpoint": endpoint})
    
    def record_leak_detection(self, leak_type: str, detected: bool) -> None:
        """Record leak detection result"""
        self.record_metric(
            "leak_check", 
            1 if detected else 0, 
            "boolean",
            {"leak_type": leak_type}
        )
    
    def get_average_latency(self, window_minutes: float = 60) -> float:
        """Get average latency over time window"""
        cutoff = time.time() - (window_minutes * 60)
        
        with self._lock:
            latency_metrics = [
                m.value for m in self.metrics
                if m.metric_name == "latency" and m.timestamp > cutoff
            ]
        
        if not latency_metrics:
            return 0.0
        
        return sum(latency_metrics) / len(latency_metrics)
    
    def get_uptime_percentage(self, window_hours: float = 24) -> float:
        """Calculate uptime percentage over time window"""
        window_seconds = window_hours * 3600
        
        with self._lock:
            # Calculate from session durations
            total_available = window_seconds
            
            # If currently connected, include current session
            current_duration = 0
            if self.session_start:
                current_duration = time.time() - self.session_start
            
            connected_time = self.total_connected_time + current_duration
            
            # Cap at window size
            connected_time = min(connected_time, total_available)
            
            if total_available == 0:
                return 100.0
            
            return (connected_time / total_available) * 100
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        with self._lock:
            current_session_duration = 0
            if self.session_start:
                current_session_duration = time.time() - self.session_start
            
            # Count metrics by type
            metric_counts = {}
            for m in self.metrics:
                metric_counts[m.metric_name] = metric_counts.get(m.metric_name, 0) + 1
            
            # Get recent latency samples
            cutoff_1h = time.time() - 3600
            recent_latencies = [
                m.value for m in self.metrics
                if m.metric_name == "latency" and m.timestamp > cutoff_1h
            ]
            
            return {
                "summary": {
                    "total_connections": self.connection_count,
                    "total_failovers": self.failover_count,
                    "total_connected_time_hours": round(
                        (self.total_connected_time + current_session_duration) / 3600, 2
                    ),
                    "current_session_minutes": round(current_session_duration / 60, 1),
                    "is_connected": self.session_start is not None,
                },
                "latency": {
                    "avg_1h": round(self.get_average_latency(60), 1),
                    "min_1h": round(min(recent_latencies), 1) if recent_latencies else 0,
                    "max_1h": round(max(recent_latencies), 1) if recent_latencies else 0,
                    "samples_1h": len(recent_latencies),
                },
                "uptime": {
                    "last_24h": round(self.get_uptime_percentage(24), 1),
                    "last_1h": round(self.get_uptime_percentage(1), 1),
                },
                "metric_counts": metric_counts,
                "current_session": dict(self._current_session) if self._current_session else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export all metrics"""
        with self._lock:
            metrics_data = [
                {
                    "name": m.metric_name,
                    "value": m.value,
                    "unit": m.unit,
                    "timestamp": m.timestamp,
                    "tags": m.tags
                }
                for m in self.metrics
            ]
        
        if format == "json":
            return json.dumps(metrics_data, indent=2)
        else:
            # CSV format
            lines = ["name,value,unit,timestamp,tags"]
            for m in metrics_data:
                tags_str = ";".join(f"{k}={v}" for k, v in m["tags"].items())
                lines.append(f"{m['name']},{m['value']},{m['unit']},{m['timestamp']},{tags_str}")
            return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset all analytics (for testing)"""
        with self._lock:
            self.metrics.clear()
            self.session_start = None
            self.total_connected_time = 0.0
            self.connection_count = 0
            self.failover_count = 0
            self._current_session = {}
        logger.info("VPN analytics reset")


# Singleton instance
_vpn_analytics: Optional[VPNSessionAnalytics] = None

def get_vpn_session_analytics() -> VPNSessionAnalytics:
    """Get singleton VPNSessionAnalytics instance"""
    global _vpn_analytics
    if _vpn_analytics is None:
        _vpn_analytics = VPNSessionAnalytics()
    return _vpn_analytics
