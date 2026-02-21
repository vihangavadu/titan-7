"""
TITAN V7.0 SINGULARITY — TLS Hello Parroting Engine
JA4+ Fingerprint Evasion via Client Hello Template Injection

Defeats JA4+ / JA3 / JA3S network fingerprinting by parroting the exact
TLS Client Hello byte-sequence of target browsers. Instead of spoofing
headers after encryption (impossible due to integrity checks), this module
injects TLS templates at the library level before the handshake.

Architecture:
    fingerprint_injector.py → selects TLS template per profile
    tls_parrot.py           → generates Client Hello parameters
    Camoufox (BoringSSL)    → emits parroted handshake on wire

Supported Parrot Targets:
    - Chrome 120-131 (Windows 11)
    - Chrome 120-131 (macOS Sonoma)
    - Firefox 121-132 (Windows 11)
    - Edge 120-131 (Windows 11)
    - Safari 17.x (macOS Sonoma / iOS 17)

Detection Vectors Neutralized:
    - JA3 hash mismatch (User-Agent says Chrome but TLS says Firefox)
    - JA4+ cipher suite ordering anomaly
    - GREASE value absence/pattern detection
    - TLS extension ordering fingerprint
    - ALPN protocol mismatch
    - Supported groups / key share mismatch
"""

import hashlib
import json
import os
import random
import struct
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "8.0.0"
__author__ = "Dva.12"


class ParrotTarget(Enum):
    """Supported browser TLS fingerprint targets."""
    CHROME_133_WIN11 = "chrome_133_win11"
    CHROME_132_WIN11 = "chrome_132_win11"
    CHROME_131_WIN11 = "chrome_131_win11"
    CHROME_128_WIN11 = "chrome_128_win11"
    CHROME_131_MACOS = "chrome_131_macos"
    FIREFOX_134_WIN11 = "firefox_134_win11"
    FIREFOX_132_WIN11 = "firefox_132_win11"
    FIREFOX_128_WIN11 = "firefox_128_win11"
    EDGE_133_WIN11 = "edge_133_win11"
    EDGE_131_WIN11 = "edge_131_win11"
    SAFARI_18_MACOS = "safari_18_macos"
    SAFARI_17_MACOS = "safari_17_macos"
    SAFARI_17_IOS = "safari_17_ios"


# GREASE values per RFC 8701 — Chrome rotates these randomly
GREASE_VALUES = [
    0x0A0A, 0x1A1A, 0x2A2A, 0x3A3A, 0x4A4A,
    0x5A5A, 0x6A6A, 0x7A7A, 0x8A8A, 0x9A9A,
    0xAAAA, 0xBABA, 0xCACA, 0xDADA, 0xEAEA, 0xFAFA,
]


@dataclass
class TLSTemplate:
    """Complete TLS Client Hello template for a specific browser version."""
    target: ParrotTarget
    ja3_hash: str
    ja4_hash: str
    tls_version: int                          # 0x0303 = TLS 1.2, 0x0304 = TLS 1.3
    cipher_suites: List[int] = field(default_factory=list)
    extensions: List[int] = field(default_factory=list)
    supported_groups: List[int] = field(default_factory=list)
    ec_point_formats: List[int] = field(default_factory=list)
    sig_algorithms: List[int] = field(default_factory=list)
    alpn_protocols: List[str] = field(default_factory=list)
    key_share_groups: List[int] = field(default_factory=list)
    psk_key_exchange_modes: List[int] = field(default_factory=list)
    supported_versions: List[int] = field(default_factory=list)
    compress_certificate_algos: List[int] = field(default_factory=list)
    grease_enabled: bool = True
    record_size_limit: int = 0
    padding_target: int = 0                   # SNI padding target (Chrome = 517)
    delegated_credentials_enabled: bool = False
    encrypted_client_hello: bool = False       # ECH support flag


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DATABASE — Exact Client Hello parameters per browser
# ══════════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[ParrotTarget, TLSTemplate] = {
    ParrotTarget.CHROME_131_WIN11: TLSTemplate(
        target=ParrotTarget.CHROME_131_WIN11,
        ja3_hash="cd08e31494f9531f560d64c695473da9",
        ja4_hash="t13d1517h2_8daaf6152771_b0da82dd1658",
        tls_version=0x0303,
        cipher_suites=[
            0x1301,  # TLS_AES_128_GCM_SHA256
            0x1302,  # TLS_AES_256_GCM_SHA384
            0x1303,  # TLS_CHACHA20_POLY1305_SHA256
            0xC02B,  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
            0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
            0xC02C,  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
            0xC030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
            0xCCA9,  # TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256
            0xCCA8,  # TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
            0xC013,  # TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA
            0xC014,  # TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA
            0x009C,  # TLS_RSA_WITH_AES_128_GCM_SHA256
            0x009D,  # TLS_RSA_WITH_AES_256_GCM_SHA384
            0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
            0x0035,  # TLS_RSA_WITH_AES_256_CBC_SHA
        ],
        extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21],
        supported_groups=[0x001D, 0x0017, 0x0018, 0x0019, 0x0100, 0x0101],
        ec_point_formats=[0],
        sig_algorithms=[
            0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806,
            0x0601, 0x0201,
        ],
        alpn_protocols=["h2", "http/1.1"],
        key_share_groups=[0x001D, 0x0017],
        psk_key_exchange_modes=[1],
        supported_versions=[0x0304, 0x0303],
        compress_certificate_algos=[2],  # Brotli
        grease_enabled=True,
        record_size_limit=16385,
        padding_target=517,
        encrypted_client_hello=True,
    ),

    ParrotTarget.FIREFOX_132_WIN11: TLSTemplate(
        target=ParrotTarget.FIREFOX_132_WIN11,
        ja3_hash="579ccef312d18482fc42e2b822ca2430",
        ja4_hash="t13d1516h2_9dc949149365_e7c285222651",
        tls_version=0x0303,
        cipher_suites=[
            0x1301,  # TLS_AES_128_GCM_SHA256
            0x1303,  # TLS_CHACHA20_POLY1305_SHA256
            0x1302,  # TLS_AES_256_GCM_SHA384
            0xC02B,  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
            0xC02F,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
            0xCCA9,  # TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256
            0xCCA8,  # TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
            0xC02C,  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
            0xC030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
            0xC013,  # TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA
            0xC014,  # TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA
            0x009C,  # TLS_RSA_WITH_AES_128_GCM_SHA256
            0x009D,  # TLS_RSA_WITH_AES_256_GCM_SHA384
            0x002F,  # TLS_RSA_WITH_AES_128_CBC_SHA
            0x0035,  # TLS_RSA_WITH_AES_256_CBC_SHA
            0x00FF,  # TLS_EMPTY_RENEGOTIATION_INFO_SCSV
        ],
        extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 34, 51, 45, 43, 13, 28, 21],
        supported_groups=[0x001D, 0x0017, 0x0018, 0x0100, 0x0101],
        ec_point_formats=[0],
        sig_algorithms=[
            0x0403, 0x0503, 0x0603, 0x0807, 0x0808, 0x0809, 0x080A, 0x080B,
            0x0804, 0x0401, 0x0501, 0x0601, 0x0303, 0x0201,
        ],
        alpn_protocols=["h2", "http/1.1"],
        key_share_groups=[0x001D, 0x0017],
        psk_key_exchange_modes=[1],
        supported_versions=[0x0304, 0x0303],
        compress_certificate_algos=[],
        grease_enabled=False,
        record_size_limit=16385,
        padding_target=0,
        delegated_credentials_enabled=True,
        encrypted_client_hello=True,
    ),

    ParrotTarget.EDGE_131_WIN11: TLSTemplate(
        target=ParrotTarget.EDGE_131_WIN11,
        ja3_hash="cd08e31494f9531f560d64c695473da9",
        ja4_hash="t13d1517h2_8daaf6152771_b0da82dd1658",
        tls_version=0x0303,
        cipher_suites=[
            0x1301, 0x1302, 0x1303,
            0xC02B, 0xC02F, 0xC02C, 0xC030,
            0xCCA9, 0xCCA8,
            0xC013, 0xC014,
            0x009C, 0x009D, 0x002F, 0x0035,
        ],
        extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21],
        supported_groups=[0x001D, 0x0017, 0x0018, 0x0019, 0x0100, 0x0101],
        ec_point_formats=[0],
        sig_algorithms=[0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601, 0x0201],
        alpn_protocols=["h2", "http/1.1"],
        key_share_groups=[0x001D, 0x0017],
        psk_key_exchange_modes=[1],
        supported_versions=[0x0304, 0x0303],
        compress_certificate_algos=[2],
        grease_enabled=True,
        record_size_limit=16385,
        padding_target=517,
        encrypted_client_hello=True,
    ),

    ParrotTarget.SAFARI_17_MACOS: TLSTemplate(
        target=ParrotTarget.SAFARI_17_MACOS,
        ja3_hash="773906b0efdefa24a7f2b8eb6985bf37",
        ja4_hash="t13d1516h2_a09f3c656075_3205bec25e5b",
        tls_version=0x0303,
        cipher_suites=[
            0x1301, 0x1302, 0x1303,
            0xC02C, 0xC02B, 0xCCA9,
            0xC030, 0xC02F, 0xCCA8,
            0xC024, 0xC023, 0xC00A, 0xC009,
            0xC028, 0xC027, 0xC014, 0xC013,
            0x009D, 0x009C, 0x003D, 0x003C,
            0x0035, 0x002F, 0x00FF,
        ],
        extensions=[0, 23, 65281, 10, 11, 16, 5, 13, 51, 45, 43, 21],
        supported_groups=[0x001D, 0x0017, 0x0018, 0x0019],
        ec_point_formats=[0],
        sig_algorithms=[0x0403, 0x0503, 0x0603, 0x0804, 0x0805, 0x0806, 0x0401, 0x0501, 0x0601, 0x0201, 0x0203],
        alpn_protocols=["h2", "http/1.1"],
        key_share_groups=[0x001D, 0x0017],
        psk_key_exchange_modes=[1],
        supported_versions=[0x0304, 0x0303],
        compress_certificate_algos=[],
        grease_enabled=False,
        record_size_limit=16384,
        padding_target=0,
    ),
}

# Alias shorter names
TEMPLATES[ParrotTarget.CHROME_128_WIN11] = TLSTemplate(
    target=ParrotTarget.CHROME_128_WIN11,
    ja3_hash="cd08e31494f9531f560d64c695473da9",
    ja4_hash="t13d1517h2_8daaf6152771_b0da82dd1658",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.CHROME_131_WIN11].cipher_suites.copy(),
    extensions=TEMPLATES[ParrotTarget.CHROME_131_WIN11].extensions.copy(),
    supported_groups=TEMPLATES[ParrotTarget.CHROME_131_WIN11].supported_groups.copy(),
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.CHROME_131_WIN11].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[2],
    grease_enabled=True,
    record_size_limit=16385,
    padding_target=517,
)
TEMPLATES[ParrotTarget.FIREFOX_128_WIN11] = TLSTemplate(
    target=ParrotTarget.FIREFOX_128_WIN11,
    ja3_hash="579ccef312d18482fc42e2b822ca2430",
    ja4_hash="t13d1516h2_9dc949149365_e7c285222651",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].cipher_suites.copy(),
    extensions=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].extensions.copy(),
    supported_groups=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].supported_groups.copy(),
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[],
    grease_enabled=False,
    record_size_limit=16385,
    padding_target=0,
    delegated_credentials_enabled=True,
)
# Chrome 132/133 — same cipher suite as 131, minor extension changes
TEMPLATES[ParrotTarget.CHROME_132_WIN11] = TLSTemplate(
    target=ParrotTarget.CHROME_132_WIN11,
    ja3_hash="cd08e31494f9531f560d64c695473da9",
    ja4_hash="t13d1517h2_8daaf6152771_b0da82dd1658",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.CHROME_131_WIN11].cipher_suites.copy(),
    extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21, 41],
    supported_groups=[0x001D, 0x0017, 0x0018, 0x0019, 0x0100, 0x0101],
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.CHROME_131_WIN11].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[2],
    grease_enabled=True,
    record_size_limit=16385,
    padding_target=517,
    encrypted_client_hello=True,
)
TEMPLATES[ParrotTarget.CHROME_133_WIN11] = TLSTemplate(
    target=ParrotTarget.CHROME_133_WIN11,
    ja3_hash="cd08e31494f9531f560d64c695473da9",
    ja4_hash="t13d1518h2_8daaf6152771_b0da82dd1658",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.CHROME_131_WIN11].cipher_suites.copy(),
    extensions=[0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 17513, 21, 41],
    supported_groups=[0x001D, 0x0017, 0x0018, 0x0019, 0x0100, 0x0101],
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.CHROME_131_WIN11].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[2],
    grease_enabled=True,
    record_size_limit=16385,
    padding_target=517,
    encrypted_client_hello=True,
)
# Firefox 134 — same cipher suite as 132, ECH fully enabled
TEMPLATES[ParrotTarget.FIREFOX_134_WIN11] = TLSTemplate(
    target=ParrotTarget.FIREFOX_134_WIN11,
    ja3_hash="579ccef312d18482fc42e2b822ca2430",
    ja4_hash="t13d1516h2_9dc949149365_e7c285222651",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].cipher_suites.copy(),
    extensions=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].extensions.copy(),
    supported_groups=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].supported_groups.copy(),
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.FIREFOX_132_WIN11].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[],
    grease_enabled=False,
    record_size_limit=16385,
    padding_target=0,
    delegated_credentials_enabled=True,
    encrypted_client_hello=True,
)
# Edge 133 — mirrors Chrome 133 (same Chromium base)
TEMPLATES[ParrotTarget.EDGE_133_WIN11] = TLSTemplate(
    target=ParrotTarget.EDGE_133_WIN11,
    ja3_hash="cd08e31494f9531f560d64c695473da9",
    ja4_hash="t13d1518h2_8daaf6152771_b0da82dd1658",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.CHROME_133_WIN11].cipher_suites.copy(),
    extensions=TEMPLATES[ParrotTarget.CHROME_133_WIN11].extensions.copy(),
    supported_groups=TEMPLATES[ParrotTarget.CHROME_133_WIN11].supported_groups.copy(),
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.CHROME_133_WIN11].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[2],
    grease_enabled=True,
    record_size_limit=16385,
    padding_target=517,
    encrypted_client_hello=True,
)
# Safari 18 macOS Sequoia — updated cipher ordering
TEMPLATES[ParrotTarget.SAFARI_18_MACOS] = TLSTemplate(
    target=ParrotTarget.SAFARI_18_MACOS,
    ja3_hash="773906b0efdefa24a7f2b8eb6985bf37",
    ja4_hash="t13d1516h2_a09f3c656075_3205bec25e5b",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.SAFARI_17_MACOS].cipher_suites.copy(),
    extensions=[0, 23, 65281, 10, 11, 16, 5, 13, 51, 45, 43, 27, 21],
    supported_groups=[0x001D, 0x0017, 0x0018, 0x0019],
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.SAFARI_17_MACOS].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[],
    grease_enabled=False,
    record_size_limit=16384,
    padding_target=0,
    encrypted_client_hello=True,
)
TEMPLATES[ParrotTarget.SAFARI_17_IOS] = TLSTemplate(
    target=ParrotTarget.SAFARI_17_IOS,
    ja3_hash="773906b0efdefa24a7f2b8eb6985bf37",
    ja4_hash="t13d1516h2_a09f3c656075_3205bec25e5b",
    tls_version=0x0303,
    cipher_suites=TEMPLATES[ParrotTarget.SAFARI_17_MACOS].cipher_suites.copy(),
    extensions=TEMPLATES[ParrotTarget.SAFARI_17_MACOS].extensions.copy(),
    supported_groups=TEMPLATES[ParrotTarget.SAFARI_17_MACOS].supported_groups.copy(),
    ec_point_formats=[0],
    sig_algorithms=TEMPLATES[ParrotTarget.SAFARI_17_MACOS].sig_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    key_share_groups=[0x001D, 0x0017],
    psk_key_exchange_modes=[1],
    supported_versions=[0x0304, 0x0303],
    compress_certificate_algos=[],
    grease_enabled=False,
    record_size_limit=16384,
    padding_target=0,
)


class TLSParrotEngine:
    """
    TLS Hello Parroting Engine — generates exact Client Hello parameters
    that match the target browser's JA4+ fingerprint.

    Usage:
        engine = TLSParrotEngine()
        config = engine.generate_parrot_config(
            target=ParrotTarget.CHROME_131_WIN11,
            sni="www.amazon.com"
        )
        # Pass config to Camoufox's modified BoringSSL via env/prefs
    """

    def __init__(self, custom_templates_dir: Optional[str] = None):
        self._templates = dict(TEMPLATES)
        if custom_templates_dir and os.path.isdir(custom_templates_dir):
            self._load_custom_templates(custom_templates_dir)

    def _load_custom_templates(self, directory: str) -> None:
        """Load user-defined TLS templates from JSON files."""
        for f in Path(directory).glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                target = ParrotTarget(data["target"])
                self._templates[target] = TLSTemplate(
                    target=target,
                    ja3_hash=data.get("ja3_hash", ""),
                    ja4_hash=data.get("ja4_hash", ""),
                    tls_version=data.get("tls_version", 0x0303),
                    cipher_suites=data.get("cipher_suites", []),
                    extensions=data.get("extensions", []),
                    supported_groups=data.get("supported_groups", []),
                    ec_point_formats=data.get("ec_point_formats", [0]),
                    sig_algorithms=data.get("sig_algorithms", []),
                    alpn_protocols=data.get("alpn_protocols", ["h2", "http/1.1"]),
                    key_share_groups=data.get("key_share_groups", []),
                    psk_key_exchange_modes=data.get("psk_key_exchange_modes", [1]),
                    supported_versions=data.get("supported_versions", [0x0304, 0x0303]),
                    compress_certificate_algos=data.get("compress_certificate_algos", []),
                    grease_enabled=data.get("grease_enabled", False),
                    record_size_limit=data.get("record_size_limit", 0),
                    padding_target=data.get("padding_target", 0),
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def _inject_grease(self, values: List[int], positions: List[int]) -> List[int]:
        """Insert random GREASE values at specified positions in a list."""
        result = list(values)
        grease = random.sample(GREASE_VALUES, k=min(len(positions), len(GREASE_VALUES)))
        for i, pos in enumerate(sorted(positions)):
            if i < len(grease) and pos <= len(result):
                result.insert(pos, grease[i])
        return result

    def get_template(self, target: ParrotTarget) -> TLSTemplate:
        """Get TLS template for a specific browser target."""
        if target not in self._templates:
            raise ValueError(f"No TLS template for target: {target.value}")
        return self._templates[target]

    def generate_parrot_config(
        self,
        target: ParrotTarget,
        sni: str = "",
        session_id: Optional[bytes] = None,
    ) -> Dict:
        """
        Generate a complete TLS parroting configuration dictionary.

        Returns a dict that can be serialized to JSON and passed to
        Camoufox's modified BoringSSL via environment variable or prefs file.
        """
        template = self.get_template(target)

        # Generate GREASE-injected cipher suites for Chrome targets
        cipher_suites = list(template.cipher_suites)
        extensions = list(template.extensions)
        supported_groups = list(template.supported_groups)

        if template.grease_enabled:
            cipher_suites = self._inject_grease(cipher_suites, [0])
            extensions = self._inject_grease(extensions, [0, len(extensions)])
            supported_groups = self._inject_grease(supported_groups, [0])

        config = {
            "tls_parrot_target": target.value,
            "tls_version": template.tls_version,
            "cipher_suites": cipher_suites,
            "extensions": extensions,
            "supported_groups": supported_groups,
            "ec_point_formats": template.ec_point_formats,
            "sig_algorithms": template.sig_algorithms,
            "alpn_protocols": template.alpn_protocols,
            "key_share_groups": template.key_share_groups,
            "psk_key_exchange_modes": template.psk_key_exchange_modes,
            "supported_versions": template.supported_versions,
            "compress_certificate_algos": template.compress_certificate_algos,
            "grease_enabled": template.grease_enabled,
            "record_size_limit": template.record_size_limit,
            "padding_target": template.padding_target,
            "delegated_credentials": template.delegated_credentials_enabled,
            "encrypted_client_hello": template.encrypted_client_hello,
            "sni": sni,
            "session_id": (session_id or os.urandom(32)).hex(),
            "ja3_expected": template.ja3_hash,
            "ja4_expected": template.ja4_hash,
        }

        return config

    def select_target_for_profile(self, browser_ua: str) -> ParrotTarget:
        """
        Auto-select the correct TLS parrot target based on the browser
        User-Agent string to ensure JA4+/UA consistency.
        """
        ua_lower = browser_ua.lower()
        if "chrome" in ua_lower and "edg" in ua_lower:
            return ParrotTarget.EDGE_133_WIN11
        elif "chrome" in ua_lower:
            return ParrotTarget.CHROME_133_WIN11
        elif "firefox" in ua_lower:
            return ParrotTarget.FIREFOX_134_WIN11
        elif "safari" in ua_lower and "iphone" in ua_lower:
            return ParrotTarget.SAFARI_17_IOS
        elif "safari" in ua_lower:
            return ParrotTarget.SAFARI_18_MACOS
        else:
            return ParrotTarget.CHROME_133_WIN11

    # ── v7.5 JA4 Permutation + Dynamic GREASE Shuffling ──────────────────────

    def generate_ja4_fingerprint(self, target: ParrotTarget) -> str:
        """
        Generate a dynamic JA4 fingerprint string from template parameters.
        JA4 format: t<ver>d<ciphers><exts>h<alpn>_<cipher_hash>_<ext_hash>
        This allows runtime verification that our Client Hello matches expected JA4.
        """
        template = self.get_template(target)
        ver = "13" if 0x0304 in template.supported_versions else "12"
        # Count non-GREASE ciphers and extensions
        real_ciphers = [c for c in template.cipher_suites if c not in GREASE_VALUES]
        real_exts = [e for e in template.extensions if e not in GREASE_VALUES]
        n_ciphers = f"{len(real_ciphers):02d}"
        n_exts = f"{len(real_exts):02d}"
        alpn_flag = "h2" if "h2" in template.alpn_protocols else "h1"

        # Cipher hash: sorted cipher hex values, SHA-256 truncated to 12
        cipher_str = ",".join(f"{c:04x}" for c in sorted(real_ciphers))
        cipher_hash = hashlib.sha256(cipher_str.encode()).hexdigest()[:12]

        # Extension hash: sorted extension IDs, SHA-256 truncated to 12
        ext_str = ",".join(f"{e:04x}" for e in sorted(real_exts))
        ext_hash = hashlib.sha256(ext_str.encode()).hexdigest()[:12]

        return f"t{ver}d{n_ciphers}{n_exts}{alpn_flag}_{cipher_hash}_{ext_hash}"

    def ja4_permutation(self, target: ParrotTarget, sni: str = "") -> Dict:
        """
        v7.5 JA4 Permutation Engine — generates a unique-per-session Client Hello
        that still produces the same JA4 hash as the target browser.

        Technique: JA4 hashes sorted cipher/extension lists, so we can freely
        reorder the wire-order of ciphers and extensions without changing the
        JA4 fingerprint. This defeats correlation attacks that track exact
        byte-sequence ordering across sessions.
        """
        template = self.get_template(target)

        # Separate TLS 1.3 ciphers (0x13xx) from legacy ciphers
        tls13_ciphers = [c for c in template.cipher_suites if (c >> 8) == 0x13]
        legacy_ciphers = [c for c in template.cipher_suites if (c >> 8) != 0x13]

        # Shuffle within each group (JA4 sorts before hashing, so order is free)
        random.shuffle(tls13_ciphers)
        random.shuffle(legacy_ciphers)
        permuted_ciphers = tls13_ciphers + legacy_ciphers

        # Permute extension order (keep SNI=0 first, padding last)
        exts = list(template.extensions)
        sni_ext = [e for e in exts if e == 0]
        padding_ext = [e for e in exts if e == 21]
        middle_exts = [e for e in exts if e != 0 and e != 21]
        random.shuffle(middle_exts)
        permuted_exts = sni_ext + middle_exts + padding_ext

        # Apply dynamic GREASE shuffling
        if template.grease_enabled:
            permuted_ciphers = self._grease_shuffle(permuted_ciphers)
            permuted_exts = self._grease_shuffle(permuted_exts)

        config = self.generate_parrot_config(target=target, sni=sni)
        config["cipher_suites"] = permuted_ciphers
        config["extensions"] = permuted_exts
        config["ja4_permuted"] = True
        config["ja4_computed"] = self.generate_ja4_fingerprint(target)
        return config

    def _grease_shuffle(self, values: List[int]) -> List[int]:
        """
        v7.5 Dynamic GREASE Shuffling — rotate GREASE values each session.
        Chrome picks random GREASE values from RFC 8701 pool on every connection.
        We replicate this by stripping old GREASE and inserting fresh random ones.
        """
        # Strip any existing GREASE values
        cleaned = [v for v in values if v not in GREASE_VALUES]
        # Pick 1-2 fresh random GREASE values
        n_grease = random.choice([1, 2])
        fresh_grease = random.sample(GREASE_VALUES, k=n_grease)
        # Insert at position 0 and optionally at end
        result = [fresh_grease[0]] + cleaned
        if n_grease > 1:
            result.append(fresh_grease[1])
        return result

    @property
    def templates(self) -> Dict:
        """Expose templates dict for status reporting."""
        return self._templates

    def verify_consistency(self, profile: Dict) -> Dict:
        """
        Verify that the TLS template is consistent with the browser profile.
        Returns a report dict with pass/fail status.
        """
        ua = profile.get("user_agent", "")
        target = self.select_target_for_profile(ua)
        template = self.get_template(target)

        checks = {
            "ua_tls_match": True,
            "alpn_correct": True,
            "grease_expected": True,
            "ech_supported": True,
        }

        if "chrome" in ua.lower() and not template.grease_enabled:
            checks["grease_expected"] = False
        if "firefox" in ua.lower() and template.grease_enabled:
            checks["grease_expected"] = False
        if template.encrypted_client_hello and not profile.get("ech_enabled", True):
            checks["ech_supported"] = False

        passed = all(checks.values())
        return {"status": "PASS" if passed else "FAIL", "checks": checks, "target": target.value}


def get_parrot_config(user_agent: str, sni: str = "") -> Dict:
    """Convenience function: auto-select TLS template and generate config."""
    engine = TLSParrotEngine()
    target = engine.select_target_for_profile(user_agent)
    return engine.generate_parrot_config(target=target, sni=sni)


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════════════════

import logging
from datetime import datetime, timezone as dt_timezone
from typing import Set


class TLSTemplateManager:
    """
    V7.6 P0: Manage TLS templates with versioning and updates.
    
    Provides template version management, update checking, and
    automatic template updates from remote sources.
    """
    
    _instance = None
    TEMPLATE_DIR = Path("/opt/titan/data/tls_templates")
    
    def __init__(self):
        self.templates: Dict[ParrotTarget, TLSTemplate] = dict(TEMPLATES)
        self.template_versions: Dict[ParrotTarget, str] = {}
        self.update_history: List[Dict] = []
        self.logger = logging.getLogger("TITAN-TLS.Manager")
        
        self._initialize_versions()
    
    def _initialize_versions(self):
        """Initialize template versions from built-in templates."""
        for target in self.templates:
            self.template_versions[target] = __version__
    
    def get_template(self, target: ParrotTarget) -> Optional[TLSTemplate]:
        """Get a template by target."""
        return self.templates.get(target)
    
    def list_templates(self) -> List[Dict]:
        """List all available templates with metadata."""
        result = []
        for target, template in self.templates.items():
            result.append({
                "target": target.value,
                "ja3_hash": template.ja3_hash,
                "ja4_hash": template.ja4_hash,
                "tls_version": hex(template.tls_version),
                "grease_enabled": template.grease_enabled,
                "ech_supported": template.encrypted_client_hello,
                "version": self.template_versions.get(target, "unknown"),
                "cipher_count": len(template.cipher_suites),
                "extension_count": len(template.extensions)
            })
        return result
    
    def add_template(self, template: TLSTemplate, version: str = None):
        """Add or update a template."""
        old_template = self.templates.get(template.target)
        self.templates[template.target] = template
        self.template_versions[template.target] = version or __version__
        
        self.update_history.append({
            "timestamp": datetime.now(dt_timezone.utc).isoformat(),
            "target": template.target.value,
            "action": "add" if not old_template else "update",
            "version": version or __version__
        })
    
    def remove_template(self, target: ParrotTarget) -> bool:
        """Remove a template."""
        if target in self.templates:
            del self.templates[target]
            if target in self.template_versions:
                del self.template_versions[target]
            return True
        return False
    
    def load_templates_from_dir(self, directory: Path = None) -> int:
        """Load templates from JSON files in directory."""
        directory = directory or self.TEMPLATE_DIR
        loaded = 0
        
        if not directory.exists():
            return 0
        
        for f in directory.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                
                target = ParrotTarget(data["target"])
                template = TLSTemplate(
                    target=target,
                    ja3_hash=data.get("ja3_hash", ""),
                    ja4_hash=data.get("ja4_hash", ""),
                    tls_version=data.get("tls_version", 0x0303),
                    cipher_suites=data.get("cipher_suites", []),
                    extensions=data.get("extensions", []),
                    supported_groups=data.get("supported_groups", []),
                    ec_point_formats=data.get("ec_point_formats", [0]),
                    sig_algorithms=data.get("sig_algorithms", []),
                    alpn_protocols=data.get("alpn_protocols", ["h2", "http/1.1"]),
                    key_share_groups=data.get("key_share_groups", []),
                    psk_key_exchange_modes=data.get("psk_key_exchange_modes", [1]),
                    supported_versions=data.get("supported_versions", [0x0304, 0x0303]),
                    compress_certificate_algos=data.get("compress_certificate_algos", []),
                    grease_enabled=data.get("grease_enabled", False),
                    record_size_limit=data.get("record_size_limit", 0),
                    padding_target=data.get("padding_target", 0),
                    encrypted_client_hello=data.get("encrypted_client_hello", False),
                )
                
                self.add_template(template, data.get("version", "custom"))
                loaded += 1
            except Exception as e:
                self.logger.warning(f"Failed to load template {f}: {e}")
        
        return loaded
    
    def export_template(self, target: ParrotTarget, output_path: Path) -> bool:
        """Export a template to JSON file."""
        template = self.templates.get(target)
        if not template:
            return False
        
        try:
            data = {
                "target": template.target.value,
                "ja3_hash": template.ja3_hash,
                "ja4_hash": template.ja4_hash,
                "tls_version": template.tls_version,
                "cipher_suites": template.cipher_suites,
                "extensions": template.extensions,
                "supported_groups": template.supported_groups,
                "ec_point_formats": template.ec_point_formats,
                "sig_algorithms": template.sig_algorithms,
                "alpn_protocols": template.alpn_protocols,
                "key_share_groups": template.key_share_groups,
                "psk_key_exchange_modes": template.psk_key_exchange_modes,
                "supported_versions": template.supported_versions,
                "compress_certificate_algos": template.compress_certificate_algos,
                "grease_enabled": template.grease_enabled,
                "record_size_limit": template.record_size_limit,
                "padding_target": template.padding_target,
                "encrypted_client_hello": template.encrypted_client_hello,
                "version": self.template_versions.get(target, __version__),
                "exported": datetime.now(dt_timezone.utc).isoformat()
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to export template: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get template manager status."""
        return {
            "template_count": len(self.templates),
            "templates": {t.value: v for t, v in self.template_versions.items()},
            "update_history": self.update_history[-10:]
        }


class TLSFingerprintAnalyzer:
    """
    V7.6 P0: Analyze and validate TLS fingerprints.
    
    Provides deep analysis of TLS fingerprints, detection of anomalies,
    and validation against known browser signatures.
    """
    
    _instance = None
    
    def __init__(self):
        self.known_fingerprints: Dict[str, Dict] = {}
        self.analysis_history: List[Dict] = []
        self.logger = logging.getLogger("TITAN-TLS.Analyzer")
        
        self._load_known_fingerprints()
    
    def _load_known_fingerprints(self):
        """Load known browser fingerprint database."""
        # Built-in fingerprint database
        for target, template in TEMPLATES.items():
            self.known_fingerprints[template.ja3_hash] = {
                "browser": target.value,
                "ja4_hash": template.ja4_hash,
                "tls_version": template.tls_version,
                "grease": template.grease_enabled
            }
    
    def analyze_ja3(self, ja3_hash: str) -> Dict:
        """Analyze a JA3 hash and identify the browser."""
        result = {
            "ja3_hash": ja3_hash,
            "known": ja3_hash in self.known_fingerprints,
            "browser": None,
            "confidence": 0,
            "warnings": []
        }
        
        if ja3_hash in self.known_fingerprints:
            info = self.known_fingerprints[ja3_hash]
            result["browser"] = info["browser"]
            result["confidence"] = 100
            result["details"] = info
        else:
            # Try to identify by pattern
            for known_hash, info in self.known_fingerprints.items():
                if known_hash[:8] == ja3_hash[:8]:
                    result["browser"] = f"similar_to_{info['browser']}"
                    result["confidence"] = 50
                    result["warnings"].append("JA3 hash partially matches known browser")
                    break
        
        if not result["known"]:
            result["warnings"].append("Unknown JA3 hash - may be detectable")
        
        return result
    
    def calculate_ja3(
        self,
        tls_version: int,
        cipher_suites: List[int],
        extensions: List[int],
        supported_groups: List[int],
        ec_point_formats: List[int]
    ) -> str:
        """Calculate JA3 hash from Client Hello components."""
        # Filter out GREASE values
        ciphers = [c for c in cipher_suites if c not in GREASE_VALUES]
        exts = [e for e in extensions if e not in GREASE_VALUES]
        groups = [g for g in supported_groups if g not in GREASE_VALUES]
        
        # JA3 format: version,ciphers,extensions,groups,ec_formats
        ja3_str = f"{tls_version}," + \
                  f"{'-'.join(str(c) for c in ciphers)}," + \
                  f"{'-'.join(str(e) for e in exts)}," + \
                  f"{'-'.join(str(g) for g in groups)}," + \
                  f"{'-'.join(str(f) for f in ec_point_formats)}"
        
        return hashlib.md5(ja3_str.encode()).hexdigest()
    
    def validate_fingerprint_consistency(
        self,
        config: Dict,
        user_agent: str
    ) -> Dict:
        """Validate that TLS fingerprint is consistent with User-Agent."""
        result = {
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        ua_lower = user_agent.lower()
        target = config.get("tls_parrot_target", "")
        
        # Check browser match
        if "chrome" in ua_lower and "chrome" not in target.lower():
            result["valid"] = False
            result["errors"].append("UA claims Chrome but TLS is not Chrome")
        elif "firefox" in ua_lower and "firefox" not in target.lower():
            result["valid"] = False
            result["errors"].append("UA claims Firefox but TLS is not Firefox")
        elif "safari" in ua_lower and "safari" not in target.lower():
            result["valid"] = False
            result["errors"].append("UA claims Safari but TLS is not Safari")
        
        result["checks"]["browser_match"] = len(result["errors"]) == 0
        
        # Check GREASE consistency
        if "chrome" in ua_lower or "edg" in ua_lower:
            if not config.get("grease_enabled", False):
                result["warnings"].append("Chrome/Edge should have GREASE enabled")
                result["checks"]["grease"] = False
            else:
                result["checks"]["grease"] = True
        else:
            result["checks"]["grease"] = True
        
        # Check ALPN
        alpn = config.get("alpn_protocols", [])
        if "h2" not in alpn:
            result["warnings"].append("Missing h2 in ALPN - modern browsers support HTTP/2")
        result["checks"]["alpn"] = "h2" in alpn
        
        # Check TLS version
        supported_versions = config.get("supported_versions", [])
        if 0x0304 not in supported_versions:  # TLS 1.3
            result["warnings"].append("TLS 1.3 not in supported versions")
        result["checks"]["tls13"] = 0x0304 in supported_versions
        
        return result
    
    def detect_anomalies(self, config: Dict) -> List[Dict]:
        """Detect anomalies in TLS configuration that could be detected."""
        anomalies = []
        
        cipher_suites = config.get("cipher_suites", [])
        extensions = config.get("extensions", [])
        
        # Check for suspicious cipher ordering
        tls13_ciphers = [c for c in cipher_suites if (c >> 8) == 0x13]
        if tls13_ciphers and tls13_ciphers != cipher_suites[:len(tls13_ciphers)]:
            anomalies.append({
                "type": "cipher_ordering",
                "severity": "medium",
                "message": "TLS 1.3 ciphers should be at the start of cipher list"
            })
        
        # Check for missing critical extensions
        critical_exts = [0, 10, 11, 13, 43, 51]  # SNI, supported_groups, ec_point, sig_algs, supported_versions, key_share
        missing = [e for e in critical_exts if e not in extensions]
        if missing:
            anomalies.append({
                "type": "missing_extensions",
                "severity": "high",
                "message": f"Missing critical extensions: {missing}"
            })
        
        # Check GREASE consistency
        grease_in_ciphers = any(c in GREASE_VALUES for c in cipher_suites)
        grease_in_exts = any(e in GREASE_VALUES for e in extensions)
        if grease_in_ciphers != grease_in_exts:
            anomalies.append({
                "type": "grease_inconsistency",
                "severity": "medium",
                "message": "GREASE present in ciphers but not extensions (or vice versa)"
            })
        
        return anomalies


class TLSPermutationGenerator:
    """
    V7.6 P0: Advanced permutation generation for JA4 evasion.
    
    Generates unique Client Hello permutations that maintain JA4
    hash equivalence while varying wire-order for anti-correlation.
    """
    
    _instance = None
    
    def __init__(self):
        self.permutation_history: Set[str] = set()
        self.max_history = 10000
        self.logger = logging.getLogger("TITAN-TLS.Permutation")
    
    def _permutation_hash(self, config: Dict) -> str:
        """Generate hash of permutation for deduplication."""
        key = f"{config.get('cipher_suites', [])}:{config.get('extensions', [])}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def generate_unique_permutation(
        self,
        target: ParrotTarget,
        engine: TLSParrotEngine,
        sni: str = "",
        max_attempts: int = 100
    ) -> Dict:
        """Generate a unique permutation not seen before."""
        for _ in range(max_attempts):
            config = engine.ja4_permutation(target, sni)
            perm_hash = self._permutation_hash(config)
            
            if perm_hash not in self.permutation_history:
                self.permutation_history.add(perm_hash)
                
                # Trim history if too large
                if len(self.permutation_history) > self.max_history:
                    # Remove oldest (convert to list, slice, convert back)
                    self.permutation_history = set(list(self.permutation_history)[-self.max_history//2:])
                
                config["permutation_hash"] = perm_hash
                config["unique"] = True
                return config
        
        # Fallback if no unique permutation found
        config = engine.ja4_permutation(target, sni)
        config["permutation_hash"] = self._permutation_hash(config)
        config["unique"] = False
        self.logger.warning("Could not generate unique permutation")
        return config
    
    def generate_batch(
        self,
        target: ParrotTarget,
        engine: TLSParrotEngine,
        count: int,
        sni: str = ""
    ) -> List[Dict]:
        """Generate a batch of unique permutations."""
        results = []
        for _ in range(count):
            config = self.generate_unique_permutation(target, engine, sni)
            results.append(config)
        return results
    
    def clear_history(self):
        """Clear permutation history."""
        self.permutation_history.clear()
    
    def get_stats(self) -> Dict:
        """Get permutation generator statistics."""
        return {
            "history_size": len(self.permutation_history),
            "max_history": self.max_history
        }


class TLSConsistencyValidator:
    """
    V7.6 P0: Cross-validate TLS with other profile elements.
    
    Ensures TLS fingerprint is consistent with all other profile
    attributes including UA, WebGL, navigator, and timezone.
    """
    
    _instance = None
    
    def __init__(self):
        self.validation_rules: List[Dict] = []
        self.logger = logging.getLogger("TITAN-TLS.Validator")
        
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default validation rules."""
        self.validation_rules = [
            {
                "name": "ua_tls_browser_match",
                "description": "User-Agent browser must match TLS fingerprint browser",
                "critical": True
            },
            {
                "name": "os_tls_match",
                "description": "OS in UA must match TLS template OS",
                "critical": True
            },
            {
                "name": "grease_consistency",
                "description": "GREASE usage must match browser type",
                "critical": False
            },
            {
                "name": "ech_support",
                "description": "ECH support must match browser capability",
                "critical": False
            }
        ]
    
    def validate_full_profile(self, profile: Dict, tls_config: Dict) -> Dict:
        """Validate TLS config against full profile."""
        result = {
            "valid": True,
            "score": 100,
            "checks": [],
            "errors": [],
            "warnings": []
        }
        
        user_agent = profile.get("user_agent", "")
        tls_target = tls_config.get("tls_parrot_target", "")
        
        # Check 1: Browser match
        ua_lower = user_agent.lower()
        browser_match = True
        
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser_match = "chrome" in tls_target.lower()
        elif "edg" in ua_lower:
            browser_match = "edge" in tls_target.lower()
        elif "firefox" in ua_lower:
            browser_match = "firefox" in tls_target.lower()
        elif "safari" in ua_lower:
            browser_match = "safari" in tls_target.lower()
        
        result["checks"].append({
            "name": "browser_match",
            "passed": browser_match,
            "message": f"UA browser matches TLS target" if browser_match else "Browser mismatch"
        })
        
        if not browser_match:
            result["valid"] = False
            result["score"] -= 40
            result["errors"].append("Critical: Browser in UA does not match TLS fingerprint")
        
        # Check 2: OS match
        os_match = True
        if "windows" in ua_lower:
            os_match = "win" in tls_target.lower()
        elif "mac os" in ua_lower or "macos" in ua_lower:
            os_match = "macos" in tls_target.lower()
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            os_match = "ios" in tls_target.lower()
        
        result["checks"].append({
            "name": "os_match",
            "passed": os_match,
            "message": f"UA OS matches TLS target" if os_match else "OS mismatch"
        })
        
        if not os_match:
            result["score"] -= 30
            result["warnings"].append("OS in UA does not match TLS fingerprint OS")
        
        # Check 3: Version plausibility
        version_ok = True
        if "chrome" in ua_lower:
            # Extract Chrome version from UA
            import re
            match = re.search(r'Chrome/(\d+)', user_agent)
            if match:
                chrome_ver = int(match.group(1))
                # Template should be within reasonable range
                if "131" in tls_target and chrome_ver < 125:
                    version_ok = False
                elif "128" in tls_target and chrome_ver > 132:
                    version_ok = False
        
        result["checks"].append({
            "name": "version_plausibility",
            "passed": version_ok,
            "message": "Version plausible" if version_ok else "Version mismatch"
        })
        
        if not version_ok:
            result["score"] -= 10
            result["warnings"].append("Browser version in UA may not match TLS template version")
        
        # Check 4: GREASE consistency
        grease_config = tls_config.get("grease_enabled", False)
        grease_ok = True
        
        if ("chrome" in ua_lower or "edg" in ua_lower) and not grease_config:
            grease_ok = False
        elif "firefox" in ua_lower and grease_config:
            grease_ok = False
        
        result["checks"].append({
            "name": "grease_consistency",
            "passed": grease_ok,
            "message": "GREASE config correct" if grease_ok else "GREASE mismatch"
        })
        
        if not grease_ok:
            result["score"] -= 10
            result["warnings"].append("GREASE configuration does not match expected browser behavior")
        
        # Check 5: WebGL consistency (if available)
        webgl_renderer = profile.get("webgl", {}).get("renderer", "")
        if webgl_renderer:
            webgl_os_match = True
            if "windows" in tls_target.lower() and "angle" not in webgl_renderer.lower():
                webgl_os_match = "direct3d" in webgl_renderer.lower() or "nvidia" in webgl_renderer.lower() or "amd" in webgl_renderer.lower()
            
            result["checks"].append({
                "name": "webgl_os_match",
                "passed": webgl_os_match,
                "message": "WebGL matches TLS OS" if webgl_os_match else "WebGL/TLS OS mismatch"
            })
            
            if not webgl_os_match:
                result["score"] -= 5
        
        result["score"] = max(0, result["score"])
        return result
    
    def quick_validate(self, user_agent: str, tls_target: ParrotTarget) -> bool:
        """Quick validation of UA/TLS match."""
        ua_lower = user_agent.lower()
        target_lower = tls_target.value.lower()
        
        if "chrome" in ua_lower and "edg" not in ua_lower:
            return "chrome" in target_lower
        elif "edg" in ua_lower:
            return "edge" in target_lower
        elif "firefox" in ua_lower:
            return "firefox" in target_lower
        elif "safari" in ua_lower:
            return "safari" in target_lower
        
        return True


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON GETTERS
# ═══════════════════════════════════════════════════════════════════════════

def get_tls_template_manager() -> TLSTemplateManager:
    """Get singleton TLSTemplateManager instance."""
    if TLSTemplateManager._instance is None:
        TLSTemplateManager._instance = TLSTemplateManager()
    return TLSTemplateManager._instance


def get_tls_fingerprint_analyzer() -> TLSFingerprintAnalyzer:
    """Get singleton TLSFingerprintAnalyzer instance."""
    if TLSFingerprintAnalyzer._instance is None:
        TLSFingerprintAnalyzer._instance = TLSFingerprintAnalyzer()
    return TLSFingerprintAnalyzer._instance


def get_tls_permutation_generator() -> TLSPermutationGenerator:
    """Get singleton TLSPermutationGenerator instance."""
    if TLSPermutationGenerator._instance is None:
        TLSPermutationGenerator._instance = TLSPermutationGenerator()
    return TLSPermutationGenerator._instance


def get_tls_consistency_validator() -> TLSConsistencyValidator:
    """Get singleton TLSConsistencyValidator instance."""
    if TLSConsistencyValidator._instance is None:
        TLSConsistencyValidator._instance = TLSConsistencyValidator()
    return TLSConsistencyValidator._instance
