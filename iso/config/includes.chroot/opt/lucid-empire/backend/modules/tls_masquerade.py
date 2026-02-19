"""
LUCID EMPIRE v7.0-TITAN - TLS Masquerade Manager
=================================================
TLS/JA4 fingerprint management for browser impersonation.
Configures TLS Client Hello to match target browser profiles.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TLSProfile:
    """TLS fingerprint profile for a specific browser."""
    name: str
    ja3_fingerprint: str
    ja4_fingerprint: str
    cipher_suites: List[int]
    extensions: List[int]
    supported_groups: List[int]
    signature_algorithms: List[int]
    alpn_protocols: List[str]
    tls_versions: List[int]
    
    # Additional characteristics
    grease_enabled: bool = True
    compress_certificate: bool = False
    psk_modes: List[int] = field(default_factory=list)


class TLSMasqueradeManager:
    """
    Manages TLS fingerprint profiles for browser impersonation.
    
    Provides configuration for various browsers and versions
    to ensure TLS fingerprints match the spoofed user agent.
    """
    
    # TLS cipher suite constants
    TLS_CIPHERS = {
        "TLS_AES_128_GCM_SHA256": 0x1301,
        "TLS_AES_256_GCM_SHA384": 0x1302,
        "TLS_CHACHA20_POLY1305_SHA256": 0x1303,
        "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256": 0xc02b,
        "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256": 0xc02f,
        "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384": 0xc02c,
        "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384": 0xc030,
        "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256": 0xcca9,
        "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256": 0xcca8,
    }
    
    # Pre-defined browser TLS profiles
    PROFILES: Dict[str, TLSProfile] = {}
    
    @classmethod
    def _init_profiles(cls):
        """Initialize browser TLS profiles."""
        if cls.PROFILES:
            return
        
        # Chrome 120 on Windows
        cls.PROFILES["chrome_131"] = TLSProfile(
            name="Chrome 120 Windows",
            ja3_fingerprint="769,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0",
            ja4_fingerprint="t13d1517h2_8daaf6152771_b0da82dd1658",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,  # TLS 1.3
                0xc02b, 0xc02f, 0xc02c, 0xc030,  # ECDHE
                0xcca9, 0xcca8,  # ChaCha20
                0xc013, 0xc014, 0x009c, 0x009d, 0x002f, 0x0035,
            ],
            extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21],
            supported_groups=[29, 23, 24, 25],
            signature_algorithms=[
                0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501,
                0x0806, 0x0601, 0x0201
            ],
            alpn_protocols=["h2", "http/1.1"],
            tls_versions=[0x0304, 0x0303],  # TLS 1.3, 1.2
            grease_enabled=True,
        )
        
        # Chrome 121 on Windows
        cls.PROFILES["chrome_132"] = TLSProfile(
            name="Chrome 121 Windows",
            ja3_fingerprint="769,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0",
            ja4_fingerprint="t13d1517h2_8daaf6152771_b0da82dd1658",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,
                0xc02b, 0xc02f, 0xc02c, 0xc030,
                0xcca9, 0xcca8,
                0xc013, 0xc014, 0x009c, 0x009d, 0x002f, 0x0035,
            ],
            extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21],
            supported_groups=[29, 23, 24, 25],
            signature_algorithms=[0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601, 0x0201],
            alpn_protocols=["h2", "http/1.1"],
            tls_versions=[0x0304, 0x0303],
            grease_enabled=True,
        )
        
        # Firefox 121 on Windows
        cls.PROFILES["firefox_132"] = TLSProfile(
            name="Firefox 121 Windows",
            ja3_fingerprint="771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21,29-23-24-25-256-257,0",
            ja4_fingerprint="t13d1516h2_8daaf6152771_e5627efa2ab1",
            cipher_suites=[
                0x1301, 0x1303, 0x1302,
                0xc02b, 0xc02f, 0xcca9, 0xcca8,
                0xc02c, 0xc030, 0xc00a, 0xc009,
                0xc013, 0xc014, 0x009c, 0x009d, 0x002f, 0x0035,
            ],
            extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 34, 51, 43, 13, 45, 28, 21],
            supported_groups=[29, 23, 24, 25, 256, 257],
            signature_algorithms=[0x0403, 0x0503, 0x0603, 0x0807, 0x0808, 0x0809, 0x080a, 0x080b, 0x0804, 0x0805, 0x0806, 0x0401, 0x0501, 0x0601, 0x0303, 0x0203, 0x0301, 0x0201],
            alpn_protocols=["h2", "http/1.1"],
            tls_versions=[0x0304, 0x0303],
            grease_enabled=False,
        )
        
        # Safari 17 on macOS
        cls.PROFILES["safari_17"] = TLSProfile(
            name="Safari 17 macOS",
            ja3_fingerprint="771,4865-4866-4867-49196-49195-52393-49200-49199-52392-49162-49161-49172-49171-157-156-53-47-49160-49170-10,0-23-65281-10-11-16-5-13-18-51-45-43-27,29-23-24-25,0",
            ja4_fingerprint="t13d1715h2_5b57614c22b0_3d5424432f57",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,
                0xc02c, 0xc02b, 0xcca9,
                0xc030, 0xc02f, 0xcca8,
                0xc00a, 0xc009, 0xc014, 0xc013,
                0x009d, 0x009c, 0x0035, 0x002f,
                0xc008, 0xc012, 0x000a,
            ],
            extensions=[0, 23, 65281, 10, 11, 16, 5, 13, 18, 51, 45, 43, 27],
            supported_groups=[29, 23, 24, 25],
            signature_algorithms=[0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601],
            alpn_protocols=["h2", "http/1.1"],
            tls_versions=[0x0304, 0x0303, 0x0302],
            grease_enabled=False,
        )
        
        # Chrome Mobile on Android
        cls.PROFILES["chrome_mobile_120"] = TLSProfile(
            name="Chrome 120 Android",
            ja3_fingerprint="769,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0",
            ja4_fingerprint="t13d1517h2_8daaf6152771_02713d6af862",
            cipher_suites=[
                0x1301, 0x1302, 0x1303,
                0xc02b, 0xc02f, 0xc02c, 0xc030,
                0xcca9, 0xcca8,
                0xc013, 0xc014, 0x009c, 0x009d, 0x002f, 0x0035,
            ],
            extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21],
            supported_groups=[29, 23, 24],
            signature_algorithms=[0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601, 0x0201],
            alpn_protocols=["h2", "http/1.1"],
            tls_versions=[0x0304, 0x0303],
            grease_enabled=True,
        )
    
    def __init__(self):
        self._init_profiles()
        self._active_profile: Optional[TLSProfile] = None
    
    def get_profile(self, name: str) -> Optional[TLSProfile]:
        """Get a TLS profile by name."""
        return self.PROFILES.get(name)
    
    def list_profiles(self) -> List[str]:
        """List available profile names."""
        return list(self.PROFILES.keys())
    
    def set_active_profile(self, name: str) -> bool:
        """Set the active TLS profile."""
        profile = self.get_profile(name)
        if profile:
            self._active_profile = profile
            return True
        return False
    
    def get_active_profile(self) -> Optional[TLSProfile]:
        """Get the currently active profile."""
        return self._active_profile
    
    def get_curl_flags(self, profile_name: Optional[str] = None) -> List[str]:
        """
        Get curl flags to mimic the TLS profile.
        
        Args:
            profile_name: Profile name, or use active profile if None
        
        Returns:
            List of curl command-line flags
        """
        profile = self.get_profile(profile_name) if profile_name else self._active_profile
        if not profile:
            return []
        
        flags = []
        
        # TLS version
        if 0x0304 in profile.tls_versions:
            flags.extend(["--tlsv1.3"])
        
        # Ciphers (simplified)
        cipher_names = []
        for cipher in profile.cipher_suites[:6]:
            if cipher == 0x1301:
                cipher_names.append("TLS_AES_128_GCM_SHA256")
            elif cipher == 0x1302:
                cipher_names.append("TLS_AES_256_GCM_SHA384")
            elif cipher == 0x1303:
                cipher_names.append("TLS_CHACHA20_POLY1305_SHA256")
        
        if cipher_names:
            flags.extend(["--ciphers", ":".join(cipher_names)])
        
        # ALPN
        if profile.alpn_protocols:
            flags.extend(["--alpn", ",".join(profile.alpn_protocols)])
        
        return flags
    
    def get_ja4_fingerprint(self, profile_name: Optional[str] = None) -> str:
        """Get JA4 fingerprint for a profile."""
        profile = self.get_profile(profile_name) if profile_name else self._active_profile
        return profile.ja4_fingerprint if profile else ""
    
    def match_user_agent_to_profile(self, user_agent: str) -> Optional[str]:
        """
        Find best TLS profile match for a user agent.
        
        Args:
            user_agent: Browser user agent string
        
        Returns:
            Profile name or None
        """
        ua_lower = user_agent.lower()
        
        if "chrome" in ua_lower:
            if "mobile" in ua_lower or "android" in ua_lower:
                return "chrome_mobile_120"
            # Extract version
            import re
            match = re.search(r'chrome/(\d+)', ua_lower)
            if match:
                version = int(match.group(1))
                if version >= 121:
                    return "chrome_131"
            return "chrome_131"
        
        elif "firefox" in ua_lower:
            return "firefox_132"
        
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            return "safari_17"
        
        # Default to Chrome
        return "chrome_131"
    
    def export_ebpf_tcp_profile(self, profile_name: Optional[str] = None) -> Dict:
        """
        Export TCP fingerprint parameters for the eBPF network_shield_v6
        os_tcp_profile struct. This bridges TLS profile data to the kernel.
        
        Args:
            profile_name: Profile name, or use active profile if None
            
        Returns:
            Dict matching the os_tcp_profile struct fields for bpftool map update
        """
        profile = self.get_profile(profile_name) if profile_name else self._active_profile
        if not profile:
            return {}
        
        # Map browser profiles to real OS TCP stack parameters (p0f signatures)
        tcp_params = {
            "chrome_131": {"ttl": 128, "window_size": 65535, "window_scale": 8, "mss": 1460,
                           "sack_ok": 1, "timestamps": 1, "nop_count": 2,
                           "opt_order": [2, 1, 3, 1, 1, 4, 0, 0], "opt_count": 6},
            "chrome_132": {"ttl": 128, "window_size": 65535, "window_scale": 8, "mss": 1460,
                           "sack_ok": 1, "timestamps": 1, "nop_count": 2,
                           "opt_order": [2, 1, 3, 1, 1, 4, 0, 0], "opt_count": 6},
            "firefox_132": {"ttl": 128, "window_size": 65535, "window_scale": 8, "mss": 1460,
                            "sack_ok": 1, "timestamps": 1, "nop_count": 1,
                            "opt_order": [2, 4, 8, 1, 3, 0, 0, 0], "opt_count": 5},
            "safari_17": {"ttl": 64, "window_size": 65535, "window_scale": 6, "mss": 1460,
                          "sack_ok": 1, "timestamps": 1, "nop_count": 2,
                          "opt_order": [2, 1, 3, 1, 1, 8, 4, 0], "opt_count": 7},
            "chrome_mobile_120": {"ttl": 64, "window_size": 65535, "window_scale": 7, "mss": 1460,
                                  "sack_ok": 1, "timestamps": 1, "nop_count": 1,
                                  "opt_order": [2, 4, 8, 1, 3, 0, 0, 0], "opt_count": 5},
        }
        
        name = profile_name or (self._active_profile.name if self._active_profile else "")
        # Find matching key
        for key in tcp_params:
            if key in name.lower().replace(" ", "_"):
                return tcp_params[key]
        
        # Default: Windows Chrome
        return tcp_params["chrome_131"]
    
    def export_bpftool_commands(self, profile_name: Optional[str] = None, map_name: str = "titan_os_profiles", map_index: int = 0) -> List[str]:
        """
        Generate bpftool commands to load this profile into the eBPF map.
        
        Returns:
            List of shell commands to execute
        """
        params = self.export_ebpf_tcp_profile(profile_name)
        if not params:
            return []
        
        import struct
        # Pack os_tcp_profile struct: u8 ttl, u16 window_size, u8 window_scale, u16 mss,
        #   u8 sack_ok, u8 timestamps, u8 nop_count, u8[8] opt_order, u8 opt_count
        opt_bytes = bytes(params["opt_order"])
        value_hex = struct.pack('<BHBHBBBs8sB',
            params["ttl"], params["window_size"], params["window_scale"],
            params["mss"], params["sack_ok"], params["timestamps"],
            params["nop_count"], b'', opt_bytes, params["opt_count"]
        ).hex()
        
        key_hex = struct.pack('<I', map_index).hex()
        
        return [
            f"bpftool map update pinned /sys/fs/bpf/{map_name} key hex {key_hex} value hex {value_hex}",
        ]
