#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LUCID EMPIRE v7.0.0-TITAN :: TLS MASQUERADING MODULE                        ║
║  NSS/BoringSSL Chrome Impersonation for JA4 Bypass                           ║
║  Authority: Dva.12 | Classification: ZERO DETECT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Implements TLS fingerprint masquerading to match Chrome 120+ signatures.
Defeats JA4/JA3 fingerprinting by Cloudflare, Akamai, and similar CDNs.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TLSFingerprint:
    """TLS Fingerprint configuration for browser impersonation"""
    
    # Target browser to impersonate
    browser_name: str = "Chrome"
    browser_version: str = "120"
    
    # JA4 components: a_b_c format
    # a = TLS version + SNI + ALPN
    # b = cipher suites (sorted)
    # c = extensions (sorted)
    
    # TLS version (1.2 = 0x0303, 1.3 = 0x0304)
    tls_version: str = "0x0304"
    
    # Cipher suites in Chrome 120 order (NOT sorted - exact order matters for JA3)
    cipher_suites: List[str] = None
    
    # TLS extensions in Chrome order
    extensions: List[str] = None
    
    # GREASE values (Generate Random Extensions And Sustain Extensibility)
    # Chrome uses these to prevent protocol ossification
    grease_values: List[str] = None
    
    # Elliptic curves
    supported_groups: List[str] = None
    
    # Signature algorithms
    signature_algorithms: List[str] = None
    
    # ALPN protocols
    alpn_protocols: List[str] = None
    
    def __post_init__(self):
        """Initialize default Chrome 120 fingerprint"""
        if self.cipher_suites is None:
            self.cipher_suites = self._chrome_131_ciphers()
        if self.extensions is None:
            self.extensions = self._chrome_131_extensions()
        if self.grease_values is None:
            self.grease_values = self._generate_grease()
        if self.supported_groups is None:
            self.supported_groups = self._chrome_131_curves()
        if self.signature_algorithms is None:
            self.signature_algorithms = self._chrome_131_signatures()
        if self.alpn_protocols is None:
            self.alpn_protocols = ["h2", "http/1.1"]
    
    def _chrome_131_ciphers(self) -> List[str]:
        """Chrome 131 cipher suite order (exact order for JA3 match)"""
        return [
            # TLS 1.3 ciphers first
            "TLS_AES_128_GCM_SHA256",           # 0x1301
            "TLS_AES_256_GCM_SHA384",           # 0x1302
            "TLS_CHACHA20_POLY1305_SHA256",     # 0x1303
            
            # TLS 1.2 ciphers
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",  # 0xc02b
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",    # 0xc02f
            "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",  # 0xc02c
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",    # 0xc030
            "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",  # 0xcca9
            "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",    # 0xcca8
            "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",       # 0xc013
            "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",       # 0xc014
            "TLS_RSA_WITH_AES_128_GCM_SHA256",          # 0x009c
            "TLS_RSA_WITH_AES_256_GCM_SHA384",          # 0x009d
            "TLS_RSA_WITH_AES_128_CBC_SHA",             # 0x002f
            "TLS_RSA_WITH_AES_256_CBC_SHA",             # 0x0035
        ]
    
    def _chrome_131_extensions(self) -> List[str]:
        """Chrome 131 TLS extension order"""
        return [
            "server_name",                    # 0
            "extended_master_secret",         # 23
            "renegotiation_info",             # 65281
            "supported_groups",               # 10
            "ec_point_formats",               # 11
            "session_ticket",                 # 35
            "application_layer_protocol_negotiation",  # 16
            "status_request",                 # 5
            "delegated_credentials",          # 34
            "key_share",                      # 51
            "supported_versions",             # 43
            "signature_algorithms",           # 13
            "psk_key_exchange_modes",         # 45
            "record_size_limit",              # 28
            "padding",                        # 21
            "compress_certificate",           # 27
            "application_settings",           # 17513
        ]
    
    def _generate_grease(self) -> List[str]:
        """Generate GREASE values (random from valid set)"""
        # Valid GREASE values per RFC 8701
        valid_grease = [
            "0x0a0a", "0x1a1a", "0x2a2a", "0x3a3a",
            "0x4a4a", "0x5a5a", "0x6a6a", "0x7a7a",
            "0x8a8a", "0x9a9a", "0xaaaa", "0xbaba",
            "0xcaca", "0xdada", "0xeaea", "0xfafa"
        ]
        # Chrome typically uses 2-3 GREASE values
        return random.sample(valid_grease, 3)
    
    def _chrome_131_curves(self) -> List[str]:
        """Chrome 131 supported elliptic curves"""
        return [
            "x25519",           # 29
            "secp256r1",        # 23 (P-256)
            "secp384r1",        # 24 (P-384)
        ]
    
    def _chrome_131_signatures(self) -> List[str]:
        """Chrome 131 signature algorithms"""
        return [
            "ecdsa_secp256r1_sha256",
            "rsa_pss_rsae_sha256",
            "rsa_pkcs1_sha256",
            "ecdsa_secp384r1_sha384",
            "rsa_pss_rsae_sha384",
            "rsa_pkcs1_sha384",
            "rsa_pss_rsae_sha512",
            "rsa_pkcs1_sha512",
        ]
    
    def get_ja3_string(self) -> str:
        """
        Generate JA3 fingerprint string
        Format: TLSVersion,Ciphers,Extensions,EllipticCurves,EllipticCurvePointFormats
        """
        # Convert cipher names to hex codes
        cipher_codes = self._ciphers_to_codes()
        extension_codes = self._extensions_to_codes()
        curve_codes = self._curves_to_codes()
        
        return f"771,{cipher_codes},{extension_codes},{curve_codes},0"
    
    def get_ja4_string(self) -> str:
        """
        Generate JA4 fingerprint string
        Format: a_b_c where:
        - a: protocol version info
        - b: sorted cipher hash
        - c: sorted extension hash  
        """
        # JA4 uses sorted values (unlike JA3)
        cipher_codes = sorted(self._ciphers_to_codes().split('-'))
        ext_codes = sorted(self._extensions_to_codes().split('-'))
        
        # Calculate truncated hashes
        import hashlib
        cipher_hash = hashlib.sha256('-'.join(cipher_codes).encode()).hexdigest()[:12]
        ext_hash = hashlib.sha256('-'.join(ext_codes).encode()).hexdigest()[:12]
        
        # a component: t13d1516h2 (tls1.3, domain, 15 ciphers, 16 extensions, h2 alpn)
        a = f"t13d{len(cipher_codes):02d}{len(ext_codes):02d}h2"
        
        return f"{a}_{cipher_hash}_{ext_hash}"
    
    def _ciphers_to_codes(self) -> str:
        """Convert cipher suite names to hex codes"""
        cipher_map = {
            "TLS_AES_128_GCM_SHA256": "1301",
            "TLS_AES_256_GCM_SHA384": "1302",
            "TLS_CHACHA20_POLY1305_SHA256": "1303",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256": "c02b",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256": "c02f",
            "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384": "c02c",
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384": "c030",
            "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256": "cca9",
            "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256": "cca8",
            "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA": "c013",
            "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA": "c014",
            "TLS_RSA_WITH_AES_128_GCM_SHA256": "009c",
            "TLS_RSA_WITH_AES_256_GCM_SHA384": "009d",
            "TLS_RSA_WITH_AES_128_CBC_SHA": "002f",
            "TLS_RSA_WITH_AES_256_CBC_SHA": "0035",
        }
        codes = [cipher_map.get(c, "0000") for c in self.cipher_suites]
        return "-".join(codes)
    
    def _extensions_to_codes(self) -> str:
        """Convert extension names to decimal codes"""
        ext_map = {
            "server_name": "0",
            "status_request": "5",
            "supported_groups": "10",
            "ec_point_formats": "11",
            "signature_algorithms": "13",
            "application_layer_protocol_negotiation": "16",
            "padding": "21",
            "extended_master_secret": "23",
            "compress_certificate": "27",
            "record_size_limit": "28",
            "delegated_credentials": "34",
            "session_ticket": "35",
            "supported_versions": "43",
            "psk_key_exchange_modes": "45",
            "key_share": "51",
            "renegotiation_info": "65281",
            "application_settings": "17513",
        }
        codes = [ext_map.get(e, "0") for e in self.extensions]
        return "-".join(codes)
    
    def _curves_to_codes(self) -> str:
        """Convert curve names to codes"""
        curve_map = {
            "x25519": "29",
            "secp256r1": "23",
            "secp384r1": "24",
            "secp521r1": "25",
        }
        codes = [curve_map.get(c, "0") for c in self.supported_groups]
        return "-".join(codes)
    
    def to_dict(self) -> Dict:
        """Export as dictionary"""
        return asdict(self)
    
    def to_json(self, path: Path = None) -> str:
        """Export as JSON"""
        data = self.to_dict()
        data['ja3'] = self.get_ja3_string()
        data['ja4'] = self.get_ja4_string()
        
        if path:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        
        return json.dumps(data, indent=2)


class TLSMasqueradeManager:
    """
    Manages TLS fingerprint configurations for different browser targets.
    
    Generates configurations that can be applied to:
    - Camoufox (via NSS patches)
    - curl-impersonate
    - Custom HTTP clients
    """
    
    BROWSER_PROFILES = {
        "chrome_131": TLSFingerprint(browser_name="Chrome", browser_version="131"),
        "chrome_131": TLSFingerprint(browser_name="Chrome", browser_version="132"),
        "chrome_122": TLSFingerprint(browser_name="Chrome", browser_version="122"),
        "firefox_132": TLSFingerprint(
            browser_name="Firefox",
            browser_version="132",
            cipher_suites=[
                "TLS_AES_128_GCM_SHA256",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
                "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
                "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
                "TLS_RSA_WITH_AES_128_GCM_SHA256",
                "TLS_RSA_WITH_AES_256_GCM_SHA384",
                "TLS_RSA_WITH_AES_128_CBC_SHA",
                "TLS_RSA_WITH_AES_256_CBC_SHA",
            ],
            extensions=[
                "server_name",
                "extended_master_secret",
                "renegotiation_info",
                "supported_groups",
                "ec_point_formats",
                "session_ticket",
                "application_layer_protocol_negotiation",
                "status_request",
                "delegated_credentials",
                "key_share",
                "supported_versions",
                "signature_algorithms",
                "psk_key_exchange_modes",
                "record_size_limit",
            ]
        ),
    }
    
    def __init__(self, profile_dir: Path = None):
        self.profile_dir = profile_dir or Path("./lucid_profile_data")
    
    def get_profile(self, browser: str = "chrome_131") -> TLSFingerprint:
        """Get TLS fingerprint profile for specified browser"""
        return self.BROWSER_PROFILES.get(browser, self.BROWSER_PROFILES["chrome_131"])
    
    def generate_config(self, profile_name: str, browser: str = "chrome_131") -> Path:
        """Generate TLS configuration file for a profile"""
        fingerprint = self.get_profile(browser)
        
        config_dir = self.profile_dir / profile_name
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = config_dir / "tls_config.json"
        fingerprint.to_json(config_path)
        
        return config_path
    
    def generate_curl_impersonate_args(self, browser: str = "chrome_131") -> List[str]:
        """Generate curl-impersonate command arguments"""
        fp = self.get_profile(browser)
        
        args = [
            "--ciphers", ",".join(fp.cipher_suites),
            "--tls13-ciphers", "TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256",
            "-H", f"sec-ch-ua: \"Chromium\";v=\"{fp.browser_version}\", \"Google Chrome\";v=\"{fp.browser_version}\"",
            "-H", "sec-ch-ua-mobile: ?0",
            "-H", "sec-ch-ua-platform: \"Windows\"",
        ]
        
        return args
    
    def validate_fingerprint(self, captured_ja3: str, target_browser: str = "chrome_131") -> Tuple[bool, str]:
        """
        Validate a captured JA3 fingerprint against target
        
        Returns:
            (matches, message)
        """
        target_fp = self.get_profile(target_browser)
        expected_ja3 = target_fp.get_ja3_string()
        
        if captured_ja3 == expected_ja3:
            return True, "JA3 fingerprint matches target browser"
        else:
            return False, f"JA3 mismatch!\nExpected: {expected_ja3}\nGot: {captured_ja3}"


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP/2 FINGERPRINT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HTTP2Fingerprint:
    """HTTP/2 fingerprint configuration for browser impersonation"""
    
    browser_name: str = "Chrome"
    browser_version: str = "120"
    
    # SETTINGS frame parameters
    header_table_size: int = 65536
    enable_push: int = 0  # Chrome disables server push
    max_concurrent_streams: int = 1000
    initial_window_size: int = 6291456
    max_frame_size: int = 16384
    max_header_list_size: int = 262144
    
    # WINDOW_UPDATE behavior
    connection_window_size: int = 15728640
    
    # Header ordering (pseudo-headers first)
    header_order: List[str] = None
    
    # Priority frames
    use_priority_frames: bool = False  # Chrome 120+ doesn't use PRIORITY
    
    def __post_init__(self):
        if self.header_order is None:
            self.header_order = self._chrome_header_order()
    
    def _chrome_header_order(self) -> List[str]:
        """Chrome's HTTP/2 pseudo-header order"""
        return [
            ":method",
            ":authority", 
            ":scheme",
            ":path",
        ]
    
    def get_settings_frame(self) -> Dict[str, int]:
        """Get SETTINGS frame parameters"""
        return {
            "HEADER_TABLE_SIZE": self.header_table_size,
            "ENABLE_PUSH": self.enable_push,
            "MAX_CONCURRENT_STREAMS": self.max_concurrent_streams,
            "INITIAL_WINDOW_SIZE": self.initial_window_size,
            "MAX_FRAME_SIZE": self.max_frame_size,
            "MAX_HEADER_LIST_SIZE": self.max_header_list_size,
        }
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self, path: Path = None) -> str:
        data = self.to_dict()
        data['settings_frame'] = self.get_settings_frame()
        
        if path:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        
        return json.dumps(data, indent=2)


class HTTP2FingerprintManager:
    """Manages HTTP/2 fingerprint configurations"""
    
    BROWSER_PROFILES = {
        "chrome_131": HTTP2Fingerprint(
            browser_name="Chrome",
            browser_version="131",
            header_table_size=65536,
            enable_push=0,
            max_concurrent_streams=1000,
            initial_window_size=6291456,
            max_frame_size=16384,
            max_header_list_size=262144,
        ),
        "firefox_132": HTTP2Fingerprint(
            browser_name="Firefox",
            browser_version="132",
            header_table_size=65536,
            enable_push=1,
            max_concurrent_streams=100,
            initial_window_size=131072,
            max_frame_size=16384,
            max_header_list_size=65536,
            header_order=[":method", ":path", ":authority", ":scheme"],
        ),
    }
    
    def __init__(self, profile_dir: Path = None):
        self.profile_dir = profile_dir or Path("./lucid_profile_data")
    
    def get_profile(self, browser: str = "chrome_131") -> HTTP2Fingerprint:
        return self.BROWSER_PROFILES.get(browser, self.BROWSER_PROFILES["chrome_131"])
    
    def generate_config(self, profile_name: str, browser: str = "chrome_131") -> Path:
        fingerprint = self.get_profile(browser)
        
        config_dir = self.profile_dir / profile_name
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = config_dir / "http2_config.json"
        fingerprint.to_json(config_path)
        
        return config_path


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED NETWORK FINGERPRINT
# ═══════════════════════════════════════════════════════════════════════════════

class NetworkFingerprintManager:
    """
    Combined TLS + HTTP/2 fingerprint manager
    
    Generates complete network-level browser impersonation configs
    """
    
    def __init__(self, profile_dir: Path = None):
        self.profile_dir = profile_dir or Path("./lucid_profile_data")
        self.tls_manager = TLSMasqueradeManager(profile_dir)
        self.http2_manager = HTTP2FingerprintManager(profile_dir)
    
    def generate_full_config(
        self, 
        profile_name: str, 
        target_browser: str = "chrome_131"
    ) -> Dict[str, Path]:
        """Generate complete network fingerprint configuration"""
        
        tls_path = self.tls_manager.generate_config(profile_name, target_browser)
        http2_path = self.http2_manager.generate_config(profile_name, target_browser)
        
        # Generate combined config
        combined = {
            "profile_name": profile_name,
            "target_browser": target_browser,
            "tls": self.tls_manager.get_profile(target_browser).to_dict(),
            "http2": self.http2_manager.get_profile(target_browser).to_dict(),
            "ja3": self.tls_manager.get_profile(target_browser).get_ja3_string(),
            "ja4": self.tls_manager.get_profile(target_browser).get_ja4_string(),
        }
        
        combined_path = self.profile_dir / profile_name / "network_fingerprint.json"
        with open(combined_path, 'w') as f:
            json.dump(combined, f, indent=2)
        
        return {
            "tls": tls_path,
            "http2": http2_path,
            "combined": combined_path,
        }
    
    def get_browser_list(self) -> List[str]:
        """Get list of supported browser profiles"""
        return list(self.tls_manager.BROWSER_PROFILES.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("LUCID EMPIRE - TLS MASQUERADING MODULE TEST")
    print("=" * 60)
    
    # Test TLS fingerprint
    fp = TLSFingerprint()
    print("\n[Chrome 120 TLS Fingerprint]")
    print(f"JA3: {fp.get_ja3_string()}")
    print(f"JA4: {fp.get_ja4_string()}")
    
    # Test HTTP/2 fingerprint
    http2 = HTTP2Fingerprint()
    print("\n[Chrome 120 HTTP/2 Fingerprint]")
    print(f"Settings: {http2.get_settings_frame()}")
    print(f"Header Order: {http2.header_order}")
    
    # Test combined config generation
    manager = NetworkFingerprintManager()
    paths = manager.generate_full_config("test_profile", "chrome_131")
    print(f"\n[Generated Configs]")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    
    print("\n" + "=" * 60)
    print("TLS MASQUERADING MODULE: OPERATIONAL")
    print("=" * 60)
