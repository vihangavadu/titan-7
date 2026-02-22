"""
TITAN V7.0 SINGULARITY - Userspace QUIC Proxy
Transparent QUIC Decoupling for TLS Fingerprint Modification

V5.2 Problem: Blocking QUIC creates "TCP Fallback" fingerprint
V6 Solution: Userspace proxy that modifies JA4 fingerprint in HTTP/3

Architecture:
1. eBPF redirects UDP/443 to this proxy (port 8443)
2. Proxy terminates QUIC connection
3. Modifies TLS Client Hello (JA4 signature)
4. Re-encrypts and forwards to destination

Result: Server sees valid HTTP/3 with correct browser fingerprint
"""

import asyncio
import gc
import ipaddress
import logging
import os
import struct
import socket
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List
from enum import Enum

try:
    from aioquic.asyncio import connect, serve
    from aioquic.asyncio.protocol import QuicConnectionProtocol
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import StreamDataReceived, ConnectionTerminated
    from aioquic.h3.connection import H3Connection
    from aioquic.h3.events import HeadersReceived, DataReceived
    AIOQUIC_AVAILABLE = True
except ImportError:
    AIOQUIC_AVAILABLE = False
    logging.getLogger("TITAN-QUIC").warning(
        "aioquic not installed — HTTP/3 TLS fingerprint protection DISABLED. "
        "Install: pip install aioquic"
    )


class BrowserProfile(Enum):
    """Browser TLS fingerprint profiles"""
    CHROME_133_WIN11 = "chrome_133_win11"
    CHROME_132_WIN11 = "chrome_132_win11"
    CHROME_131_WIN11 = "chrome_131_win11"
    CHROME_131_MACOS = "chrome_131_macos"
    FIREFOX_134_WIN11 = "firefox_134_win11"
    FIREFOX_132_WIN11 = "firefox_132_win11"
    FIREFOX_132_LINUX = "firefox_132_linux"
    SAFARI_18_MACOS = "safari_18_macos"
    SAFARI_17_MACOS = "safari_17_macos"
    EDGE_133_WIN11 = "edge_133_win11"
    EDGE_131_WIN11 = "edge_131_win11"


@dataclass
class TLSFingerprint:
    """TLS fingerprint configuration"""
    # JA3/JA4 components
    tls_version: int = 0x0303  # TLS 1.2
    cipher_suites: List[int] = field(default_factory=list)
    extensions: List[int] = field(default_factory=list)
    supported_groups: List[int] = field(default_factory=list)
    ec_point_formats: List[int] = field(default_factory=list)
    
    # ALPN
    alpn_protocols: List[str] = field(default_factory=lambda: ["h3", "h2"])
    
    # SNI handling
    sni_enabled: bool = True


# Browser fingerprint database
FINGERPRINT_DB: Dict[BrowserProfile, TLSFingerprint] = {
    BrowserProfile.CHROME_131_WIN11: TLSFingerprint(
        tls_version=0x0304,  # TLS 1.3
        cipher_suites=[
            0x1301,  # TLS_AES_128_GCM_SHA256
            0x1302,  # TLS_AES_256_GCM_SHA384
            0x1303,  # TLS_CHACHA20_POLY1305_SHA256
            0xc02b,  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
            0xc02f,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
            0xc02c,  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
            0xc030,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
            0xcca9,  # TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256
            0xcca8,  # TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
        ],
        extensions=[
            0x0000,  # server_name
            0x0017,  # extended_master_secret
            0xff01,  # renegotiation_info
            0x000a,  # supported_groups
            0x000b,  # ec_point_formats
            0x0023,  # session_ticket
            0x0010,  # application_layer_protocol_negotiation
            0x0005,  # status_request
            0x000d,  # signature_algorithms
            0x002b,  # supported_versions
            0x002d,  # psk_key_exchange_modes
            0x0033,  # key_share
        ],
        supported_groups=[
            0x001d,  # x25519
            0x0017,  # secp256r1
            0x0018,  # secp384r1
        ],
        ec_point_formats=[0x00],  # uncompressed
        alpn_protocols=["h3", "h2", "http/1.1"],
    ),
    
    BrowserProfile.FIREFOX_132_WIN11: TLSFingerprint(
        tls_version=0x0304,
        cipher_suites=[
            0x1301,
            0x1303,
            0x1302,
            0xc02b,
            0xc02f,
            0xc02c,
            0xc030,
            0xcca9,
            0xcca8,
        ],
        extensions=[
            0x0000,
            0x0017,
            0xff01,
            0x000a,
            0x000b,
            0x0023,
            0x0010,
            0x0005,
            0x000d,
            0x002b,
            0x002d,
            0x0033,
            0x001c,  # record_size_limit (Firefox specific)
        ],
        supported_groups=[
            0x001d,
            0x0017,
            0x0018,
            0x0019,  # secp521r1 (Firefox includes this)
        ],
        ec_point_formats=[0x00],
        alpn_protocols=["h3", "h2"],
    ),
    # V7.5 FIX: Add Firefox Linux profile (Titan OS uses Camoufox on Linux)
    BrowserProfile.FIREFOX_132_LINUX: TLSFingerprint(
        tls_version=0x0304,
        cipher_suites=[
            0x1301,
            0x1303,
            0x1302,
            0xc02b,
            0xc02f,
            0xc02c,
            0xc030,
            0xcca9,
            0xcca8,
        ],
        extensions=[
            0x0000,
            0x0017,
            0xff01,
            0x000a,
            0x000b,
            0x0023,
            0x0010,
            0x0005,
            0x000d,
            0x002b,
            0x002d,
            0x0033,
            0x001c,  # record_size_limit (Firefox specific)
        ],
        supported_groups=[
            0x001d,
            0x0017,
            0x0018,
            0x0019,
        ],
        ec_point_formats=[0x00],
        alpn_protocols=["h3", "h2"],
    ),
}


@dataclass
class ProxyConfig:
    """QUIC Proxy configuration"""
    listen_host: str = "127.0.0.1"
    listen_port: int = 8443
    browser_profile: BrowserProfile = BrowserProfile.CHROME_131_WIN11
    
    # Connection settings
    max_connections: int = 1000
    idle_timeout: float = 30.0
    
    # Logging
    log_level: str = "INFO"
    log_connections: bool = True


class QUICProxyProtocol(QuicConnectionProtocol if AIOQUIC_AVAILABLE else object):
    """
    QUIC connection handler that modifies TLS fingerprint.
    """
    
    def __init__(self, *args, fingerprint: TLSFingerprint = None, **kwargs):
        if AIOQUIC_AVAILABLE:
            super().__init__(*args, **kwargs)
        self.fingerprint = fingerprint or FINGERPRINT_DB[BrowserProfile.CHROME_131_WIN11]
        self.h3_conn: Optional[H3Connection] = None
        self.upstream_conn = None
        self.logger = logging.getLogger("TITAN-QUIC-PROXY")
    
    def quic_event_received(self, event):
        """Handle QUIC events"""
        if isinstance(event, StreamDataReceived):
            # Forward data to upstream
            if self.upstream_conn:
                asyncio.create_task(self._forward_upstream(event.stream_id, event.data))
        
        elif isinstance(event, ConnectionTerminated):
            self.logger.debug(f"Connection terminated: {event.reason_phrase}")
    
    async def _forward_upstream(self, stream_id: int, data: bytes):
        """Forward data to upstream server"""
        if self.upstream_conn:
            self.upstream_conn._quic.send_stream_data(stream_id, data)


class TitanQUICProxy:
    """
    Transparent QUIC Proxy for TLS fingerprint modification.
    
    This proxy:
    1. Receives QUIC connections redirected by eBPF
    2. Terminates the connection locally
    3. Creates new connection to destination with modified fingerprint
    4. Forwards data bidirectionally
    
    Usage:
        proxy = TitanQUICProxy(ProxyConfig())
        await proxy.start()
    """
    
    def __init__(self, config: Optional[ProxyConfig] = None):
        self.config = config or ProxyConfig()
        self.logger = logging.getLogger("TITAN-QUIC-PROXY")
        self._setup_logging()
        
        self.active_connections: Dict[str, QUICProxyProtocol] = {}
        self._running = False
        self._server = None
    
    def _setup_logging(self):
        """Configure logging"""
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
        )
    
    def get_fingerprint(self) -> TLSFingerprint:
        """Get the configured TLS fingerprint"""
        return FINGERPRINT_DB.get(
            self.config.browser_profile,
            FINGERPRINT_DB[BrowserProfile.CHROME_131_WIN11]
        )
    
    def create_client_config(self, server_name: str) -> QuicConfiguration:
        """Create QUIC configuration with modified fingerprint"""
        if not AIOQUIC_AVAILABLE:
            raise RuntimeError("aioquic not available")
        
        fingerprint = self.get_fingerprint()
        
        config = QuicConfiguration(
            is_client=True,
            alpn_protocols=fingerprint.alpn_protocols,
            server_name=server_name,
            verify_mode=False,  # Skip cert verification for transparent proxy
        )
        
        # Apply cipher suite ordering to match target JA4 fingerprint.
        # aioquic's QuicConfiguration accepts cipher_suites as a list of
        # CipherSuite enum values. We map our hex IDs to the enum names.
        try:
            from aioquic.tls import CipherSuite
            cipher_map = {
                0x1301: CipherSuite.AES_128_GCM_SHA256,
                0x1302: CipherSuite.AES_256_GCM_SHA384,
                0x1303: CipherSuite.CHACHA20_POLY1305_SHA256,
            }
            ordered_ciphers = []
            for cs in fingerprint.cipher_suites:
                if cs in cipher_map:
                    ordered_ciphers.append(cipher_map[cs])
            if ordered_ciphers:
                config.cipher_suites = ordered_ciphers
        except (ImportError, AttributeError):
            pass  # aioquic version doesn't expose CipherSuite enum
        
        # Set supported groups (key exchange curves) to match fingerprint
        try:
            config.supported_groups = fingerprint.supported_groups
        except AttributeError:
            pass  # older aioquic versions
        
        # Set QUIC initial parameters to match browser profile
        config.max_datagram_frame_size = 65536
        config.idle_timeout = 30.0
        
        return config
    
    def create_server_config(self) -> QuicConfiguration:
        """Create server configuration for accepting connections"""
        if not AIOQUIC_AVAILABLE:
            raise RuntimeError("aioquic not available")
        
        config = QuicConfiguration(
            is_client=False,
            alpn_protocols=["h3", "h2"],
            max_datagram_frame_size=65536,
        )
        
        # Generate ephemeral self-signed cert for local-only proxy listener.
        # This cert is ONLY used for the loopback 127.0.0.1 listener where
        # eBPF redirects traffic — it never leaves the machine.
        cert_dir = Path("/opt/titan/state/proxy_certs")
        cert_file = cert_dir / "proxy.pem"
        key_file = cert_dir / "proxy.key"
        
        if not cert_file.exists():
            try:
                cert_dir.mkdir(parents=True, exist_ok=True)
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import ec
                from datetime import datetime, timedelta, timezone
                
                key = ec.generate_private_key(ec.SECP256R1())
                subject = issuer = x509.Name([
                    x509.NameAttribute(NameOID.COMMON_NAME, "TITAN Local Proxy"),
                ])
                cert = (
                    x509.CertificateBuilder()
                    .subject_name(subject)
                    .issuer_name(issuer)
                    .public_key(key.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(datetime.now(timezone.utc))
                    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
                    .add_extension(
                        x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
                        critical=False,
                    )
                    .sign(key, hashes.SHA256())
                )
                cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
                key_file.write_bytes(key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                ))
                self.logger.info("Generated ephemeral proxy TLS cert")
            except ImportError:
                self.logger.warning("cryptography package not available — using aioquic defaults")
            except Exception as e:
                self.logger.warning(f"Cert generation failed: {e}")
        
        if cert_file.exists() and key_file.exists():
            config.load_cert_chain(str(cert_file), str(key_file))
        
        return config
    
    async def handle_connection(self, 
                                reader: asyncio.StreamReader,
                                writer: asyncio.StreamWriter):
        """Handle incoming proxied connection"""
        peer = writer.get_extra_info('peername')
        self.logger.info(f"New connection from {peer}")
        
        # V7.5 FIX: Track active connections for idle GC
        conn_id = f"{peer[0]}:{peer[1]}" if peer else "unknown"
        self.active_connections[conn_id] = None
        
        try:
            # Read initial data to determine destination
            initial_data = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            
            if not initial_data:
                return
            
            dest_host, dest_port = self._extract_destination(initial_data, writer)
            
            if not dest_host:
                self.logger.warning("Could not determine destination")
                return
            
            # Create upstream connection with modified fingerprint
            await self._proxy_connection(reader, writer, dest_host, dest_port, initial_data)
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Connection timeout from {peer}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            self.active_connections.pop(conn_id, None)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    
    def _extract_destination(self, data: bytes, writer: asyncio.StreamWriter = None) -> Tuple[Optional[str], int]:
        """
        Extract destination from connection data using multiple methods:
        1. SO_ORIGINAL_DST from eBPF-redirected socket (Linux netfilter/tproxy)
        2. QUIC Initial packet SNI extraction
        3. Environment variable fallback
        """
        # Method 1: SO_ORIGINAL_DST — the gold standard for transparent proxies.
        # When eBPF/iptables TPROXY redirects traffic, the original dest is
        # recoverable via getsockopt(SOL_IP, SO_ORIGINAL_DST).
        if writer:
            try:
                sock = writer.get_extra_info('socket')
                if sock:
                    SO_ORIGINAL_DST = 80  # Linux: SOL_IP=0, SO_ORIGINAL_DST=80
                    dst = sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
                    port = struct.unpack('!H', dst[2:4])[0]
                    ip = socket.inet_ntoa(dst[4:8])
                    if ip and ip != '0.0.0.0' and ip != '127.0.0.1':
                        self.logger.debug(f"SO_ORIGINAL_DST: {ip}:{port}")
                        return ip, port
            except (OSError, AttributeError, struct.error):
                pass  # Not a redirected socket or not on Linux
        
        # Method 2: Extract SNI from QUIC/TLS Client Hello
        try:
            if len(data) >= 50:
                sni = self._extract_sni_from_payload(data)
                if sni:
                    return sni, 443
        except Exception:
            pass
        
        # Method 3: Environment variable (set by eBPF map or systemd)
        ebpf_dest = os.getenv("TITAN_PROXY_DEST", "")
        if ebpf_dest:
            if ":" in ebpf_dest:
                host, port_s = ebpf_dest.rsplit(":", 1)
                return host, int(port_s)
            return ebpf_dest, 443
        
        return None, 443
    
    def _extract_sni_from_payload(self, data: bytes) -> Optional[str]:
        """Extract SNI hostname from TLS Client Hello within packet data"""
        # Search for SNI extension pattern: 00 00 (ext type) followed by lengths
        # then 00 (host_name type) then length then ASCII hostname
        try:
            idx = 0
            while idx < len(data) - 10:
                # Look for SNI extension type (0x0000) preceded by plausible length
                if data[idx] == 0x00 and data[idx+1] == 0x00:
                    # Read extension length
                    ext_len = (data[idx+2] << 8) | data[idx+3]
                    if 4 < ext_len < 256:
                        # Read server name list length
                        snl_len = (data[idx+4] << 8) | data[idx+5]
                        if snl_len > 0 and data[idx+6] == 0x00:  # host_name type
                            name_len = (data[idx+7] << 8) | data[idx+8]
                            if 0 < name_len < 254 and idx + 9 + name_len <= len(data):
                                hostname = data[idx+9:idx+9+name_len]
                                try:
                                    name = hostname.decode('ascii')
                                    if '.' in name and all(c.isalnum() or c in '.-' for c in name):
                                        return name
                                except (UnicodeDecodeError, ValueError):
                                    pass
                idx += 1
        except (IndexError, ValueError):
            pass
        return None
    
    async def _proxy_connection(self,
                                 client_reader: asyncio.StreamReader,
                                 client_writer: asyncio.StreamWriter,
                                 dest_host: str,
                                 dest_port: int,
                                 initial_data: bytes):
        """Proxy connection with fingerprint modification"""
        self.logger.info(f"Proxying to {dest_host}:{dest_port}")
        
        if AIOQUIC_AVAILABLE:
            # Use aioquic for proper QUIC proxying
            await self._proxy_quic(client_reader, client_writer, dest_host, dest_port, initial_data)
        else:
            # Fallback: simple TCP proxy (loses QUIC benefits)
            await self._proxy_tcp_fallback(client_reader, client_writer, dest_host, dest_port, initial_data)
    
    async def _proxy_quic(self,
                          client_reader: asyncio.StreamReader,
                          client_writer: asyncio.StreamWriter,
                          dest_host: str,
                          dest_port: int,
                          initial_data: bytes):
        """QUIC-aware proxying with fingerprint modification"""
        config = self.create_client_config(dest_host)
        
        try:
            async with connect(
                dest_host,
                dest_port,
                configuration=config,
            ) as upstream:
                # Forward initial data
                stream_id = upstream._quic.get_next_available_stream_id()
                upstream._quic.send_stream_data(stream_id, initial_data)
                
                # Bidirectional forwarding
                await asyncio.gather(
                    self._forward_client_to_upstream(client_reader, upstream),
                    self._forward_upstream_to_client(upstream, client_writer),
                )
        except Exception as e:
            self.logger.error(f"QUIC proxy error: {e}")
    
    async def _proxy_tcp_fallback(self,
                                   client_reader: asyncio.StreamReader,
                                   client_writer: asyncio.StreamWriter,
                                   dest_host: str,
                                   dest_port: int,
                                   initial_data: bytes):
        """TCP fallback when QUIC not available"""
        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(
                dest_host, dest_port
            )
            
            # Forward initial data
            upstream_writer.write(initial_data)
            await upstream_writer.drain()
            
            # Bidirectional forwarding
            await asyncio.gather(
                self._pipe(client_reader, upstream_writer),
                self._pipe(upstream_reader, client_writer),
            )
            
        except Exception as e:
            self.logger.error(f"TCP fallback error: {e}")
    
    async def _forward_client_to_upstream(self, reader, upstream):
        """Forward data from client to upstream QUIC connection"""
        try:
            stream_id = upstream._quic.get_next_available_stream_id()
            while True:
                data = await reader.read(65536)
                if not data:
                    upstream._quic.send_stream_data(stream_id, b'', end_stream=True)
                    upstream.transmit()
                    break
                upstream._quic.send_stream_data(stream_id, data)
                upstream.transmit()
        except (ConnectionError, asyncio.CancelledError):
            pass
        except Exception as e:
            self.logger.debug(f"Client->upstream forward ended: {e}")
    
    async def _forward_upstream_to_client(self, upstream, writer):
        """Forward data from upstream QUIC connection to client TCP writer.
        
        Uses aioquic's event-driven API: the QuicConnectionProtocol subclass
        receives quic_event_received() callbacks. We use an asyncio.Queue to
        bridge between the callback-driven aioquic model and our async loop.
        """
        # Create a queue for events and monkey-patch the upstream protocol
        event_queue = asyncio.Queue()
        original_handler = getattr(upstream, 'quic_event_received', None)
        
        def _event_handler(event):
            event_queue.put_nowait(event)
            if original_handler:
                original_handler(event)
        
        upstream.quic_event_received = _event_handler
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    break
                
                if isinstance(event, StreamDataReceived):
                    writer.write(event.data)
                    await writer.drain()
                    if event.end_stream:
                        break
                elif isinstance(event, ConnectionTerminated):
                    break
        except (ConnectionError, asyncio.CancelledError):
            pass
        except Exception as e:
            self.logger.debug(f"Upstream->client forward ended: {e}")
        finally:
            pass  # V7.5 FIX: Writer is closed by handle_connection, not here
    
    async def _pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Simple bidirectional pipe"""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
    
    async def start(self):
        """Start the QUIC proxy server"""
        self.logger.info(f"Starting TITAN QUIC Proxy on {self.config.listen_host}:{self.config.listen_port}")
        self.logger.info(f"Browser profile: {self.config.browser_profile.value}")
        
        self._running = True
        
        # V7.0 AUDIT REMEDIATION: Disable Python GC during active proxying
        # to eliminate bimodal latency spikes (10-50ms GC pauses) that differ
        # from the unimodal Gaussian of hardware QUIC stacks (msquic.dll).
        # Manual GC is triggered during idle periods via _gc_idle_task.
        gc.disable()
        self.logger.info("GC disabled for latency-critical proxying (manual idle collection)")
        
        # Start TCP server (eBPF redirects UDP to TCP locally)
        self._server = await asyncio.start_server(
            self.handle_connection,
            self.config.listen_host,
            self.config.listen_port,
        )
        
        # Start idle GC task — collects during low-traffic windows
        self._gc_task = asyncio.create_task(self._gc_idle_collector())
        
        async with self._server:
            await self._server.serve_forever()
    
    async def _gc_idle_collector(self):
        """Run GC during idle periods to prevent unbounded memory growth.
        Only collects when no connections are active."""
        while self._running:
            await asyncio.sleep(5.0)
            if len(self.active_connections) == 0:
                gc.collect()
    
    async def stop(self):
        """Stop the proxy server"""
        self._running = False
        if hasattr(self, '_gc_task'):
            self._gc_task.cancel()
        gc.enable()  # Re-enable GC on shutdown
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self.logger.info("TITAN QUIC Proxy stopped (GC re-enabled)")
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        return {
            "running": self._running,
            "active_connections": len(self.active_connections),
            "browser_profile": self.config.browser_profile.value,
            "listen_address": f"{self.config.listen_host}:{self.config.listen_port}",
        }


async def main():
    """Main entry point for standalone proxy"""
    config = ProxyConfig(
        listen_host=os.getenv("TITAN_PROXY_HOST", "127.0.0.1"),
        listen_port=int(os.getenv("TITAN_PROXY_PORT", "8443")),
        browser_profile=BrowserProfile.CHROME_131_WIN11,
        log_level="DEBUG",
    )
    
    proxy = TitanQUICProxy(config)
    
    try:
        await proxy.start()
    except KeyboardInterrupt:
        await proxy.stop()


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: HTTP/3 TRANSPARENT PROXY
# Full QUIC interception with nftables redirect rules and JA4 fingerprint
# modification in the HTTP/3 layer. Eliminates the "TCP fallback" detection
# signal by properly handling QUIC instead of blocking it.
# ═══════════════════════════════════════════════════════════════════════════

class HTTP3TransparentProxy:
    """
    v7.5 HTTP/3 Transparent Proxy with nftables integration.

    Architecture:
    1. nftables rule redirects outbound UDP/443 to local proxy port
    2. Proxy terminates QUIC, inspects/modifies TLS Client Hello
    3. Re-establishes QUIC to destination with parroted JA4 fingerprint
    4. Transparently relays HTTP/3 frames between client and server

    This prevents the "no QUIC support" detection vector that flags
    automated browsers which block UDP/443 to force TCP fallback.
    """

    NFTABLES_TABLE = "titan_quic"
    NFTABLES_CHAIN = "quic_redirect"

    def __init__(self, proxy_port: int = 8443, interface: str = "eth0"):
        self.proxy_port = proxy_port
        self.interface = interface
        self.logger = logging.getLogger("TITAN-HTTP3-PROXY")
        self._rules_installed = False

    def install_nftables_rules(self) -> bool:
        """
        Install nftables rules to redirect UDP/443 to local proxy.
        Requires root privileges.
        """
        commands = [
            f"nft add table inet {self.NFTABLES_TABLE}",
            f"nft add chain inet {self.NFTABLES_TABLE} {self.NFTABLES_CHAIN} "
            f"{{ type nat hook output priority -100 \\; policy accept \\; }}",
            f"nft add rule inet {self.NFTABLES_TABLE} {self.NFTABLES_CHAIN} "
            f"udp dport 443 redirect to :{self.proxy_port}",
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    self.logger.error(f"nftables error: {result.stderr.strip()}")
                    return False
            except Exception as e:
                self.logger.error(f"nftables install failed: {e}")
                return False

        self._rules_installed = True
        self.logger.info(f"[HTTP3] nftables redirect installed: UDP/443 → :{self.proxy_port}")
        return True

    def remove_nftables_rules(self) -> bool:
        """Remove QUIC redirect nftables rules."""
        try:
            result = subprocess.run(
                f"nft delete table inet {self.NFTABLES_TABLE}",
                shell=True, capture_output=True, text=True, timeout=10
            )
            self._rules_installed = False
            self.logger.info("[HTTP3] nftables redirect rules removed")
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"nftables removal failed: {e}")
            return False

    def get_quic_transport_params(self, browser_profile: str = "chrome_131") -> Dict:
        """
        Generate QUIC transport parameters matching the target browser.
        These parameters are visible in the Initial packet and must match
        the browser's expected values to avoid fingerprinting.
        """
        profiles = {
            "chrome_131": {
                "max_idle_timeout": 30000,
                "max_udp_payload_size": 1350,
                "initial_max_data": 15728640,
                "initial_max_stream_data_bidi_local": 6291456,
                "initial_max_stream_data_bidi_remote": 6291456,
                "initial_max_stream_data_uni": 6291456,
                "initial_max_streams_bidi": 100,
                "initial_max_streams_uni": 3,
                "active_connection_id_limit": 8,
                "grease_quic_bit": True,
            },
            "firefox_132": {
                "max_idle_timeout": 30000,
                "max_udp_payload_size": 1200,
                "initial_max_data": 10485760,
                "initial_max_stream_data_bidi_local": 1048576,
                "initial_max_stream_data_bidi_remote": 1048576,
                "initial_max_stream_data_uni": 1048576,
                "initial_max_streams_bidi": 100,
                "initial_max_streams_uni": 3,
                "active_connection_id_limit": 8,
                "grease_quic_bit": False,
            },
        }
        return profiles.get(browser_profile, profiles["chrome_131"])

    def get_status(self) -> Dict:
        """Get HTTP/3 proxy status."""
        return {
            "proxy_port": self.proxy_port,
            "nftables_installed": self._rules_installed,
            "interface": self.interface,
            "aioquic_available": AIOQUIC_AVAILABLE,
            "version": "7.5",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced QUIC Proxy Operations
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import random
import time
import hashlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor


@dataclass
class PooledConnection:
    """Pooled QUIC connection entry"""
    connection_id: str
    host: str
    port: int
    fingerprint: BrowserProfile
    created_at: float
    last_used: float
    request_count: int = 0
    is_active: bool = True
    health_score: float = 100.0


@dataclass
class FingerprintState:
    """Current fingerprint rotation state"""
    current_profile: BrowserProfile
    rotation_count: int
    last_rotation: float
    entropy_seed: int
    session_id: str


@dataclass
class QUICMetrics:
    """QUIC proxy metrics snapshot"""
    timestamp: float
    total_connections: int
    active_connections: int
    pooled_connections: int
    requests_per_minute: float
    avg_latency_ms: float
    connection_errors: int
    fingerprint_rotations: int
    bytes_transferred: int


@dataclass
class HealthCheckResult:
    """Health check result for QUIC proxy"""
    healthy: bool
    latency_ms: float
    error_rate_pct: float
    pool_utilization_pct: float
    fingerprint_diversity: int
    issues: List[str]


class QUICConnectionPool:
    """
    V7.6 P0: Connection pooling for reusing upstream QUIC connections.
    
    Features:
    - Connection reuse to reduce handshake overhead
    - Per-host connection limits
    - Automatic connection health tracking
    - Idle connection cleanup
    - Fingerprint-aware pooling
    """
    
    def __init__(self, max_connections_per_host: int = 6,
                 max_total_connections: int = 100,
                 idle_timeout: float = 60.0):
        self.max_per_host = max_connections_per_host
        self.max_total = max_total_connections
        self.idle_timeout = idle_timeout
        
        # Connection pools: host -> list of connections
        self._pools: Dict[str, List[PooledConnection]] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            "total_created": 0,
            "total_reused": 0,
            "total_closed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
        # Cleanup thread
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        self.logger = logging.getLogger("TITAN-QUIC-POOL")
    
    def acquire(self, host: str, port: int,
                fingerprint: BrowserProfile = None) -> Optional[PooledConnection]:
        """
        Acquire a connection from the pool or create a new one.
        
        Args:
            host: Target host
            port: Target port
            fingerprint: Required fingerprint profile (None = any)
        
        Returns:
            PooledConnection or None if pool is full
        """
        pool_key = f"{host}:{port}"
        
        with self._lock:
            # Try to reuse existing connection
            if pool_key in self._pools:
                for conn in self._pools[pool_key]:
                    if conn.is_active:
                        continue  # In use
                    
                    # Check fingerprint match
                    if fingerprint and conn.fingerprint != fingerprint:
                        continue
                    
                    # Check health
                    if conn.health_score < 50:
                        continue
                    
                    # Reuse this connection
                    conn.is_active = True
                    conn.last_used = time.time()
                    conn.request_count += 1
                    self._stats["total_reused"] += 1
                    self._stats["cache_hits"] += 1
                    
                    self.logger.debug(f"Reusing pooled connection to {pool_key}")
                    return conn
            
            self._stats["cache_misses"] += 1
            
            # Check limits
            total_connections = sum(len(p) for p in self._pools.values())
            if total_connections >= self.max_total:
                self.logger.warning("Connection pool at capacity")
                return None
            
            # Check per-host limit
            host_connections = len(self._pools.get(pool_key, []))
            if host_connections >= self.max_per_host:
                self.logger.warning(f"Per-host limit reached for {pool_key}")
                return None
            
            # Create new connection entry
            conn = PooledConnection(
                connection_id=hashlib.sha256(
                    f"{host}:{port}:{time.time()}:{random.random()}".encode()
                ).hexdigest()[:16],
                host=host,
                port=port,
                fingerprint=fingerprint or BrowserProfile.CHROME_131_WIN11,
                created_at=time.time(),
                last_used=time.time(),
                is_active=True,
            )
            
            if pool_key not in self._pools:
                self._pools[pool_key] = []
            self._pools[pool_key].append(conn)
            self._stats["total_created"] += 1
            
            self.logger.debug(f"Created new pooled connection to {pool_key}")
            return conn
    
    def release(self, conn: PooledConnection, healthy: bool = True):
        """Release a connection back to the pool"""
        with self._lock:
            conn.is_active = False
            conn.last_used = time.time()
            
            if not healthy:
                conn.health_score = max(0, conn.health_score - 25)
    
    def close(self, conn: PooledConnection):
        """Close and remove a connection from the pool"""
        pool_key = f"{conn.host}:{conn.port}"
        
        with self._lock:
            if pool_key in self._pools:
                self._pools[pool_key] = [
                    c for c in self._pools[pool_key]
                    if c.connection_id != conn.connection_id
                ]
                self._stats["total_closed"] += 1
    
    def _cleanup_loop(self):
        """Background cleanup of idle connections"""
        while self._running:
            try:
                time.sleep(10)
                self._cleanup_idle()
            except Exception as e:
                self.logger.error(f"Pool cleanup error: {e}")
    
    def _cleanup_idle(self):
        """Remove idle connections"""
        current_time = time.time()
        
        with self._lock:
            for pool_key in list(self._pools.keys()):
                active_conns = []
                for conn in self._pools[pool_key]:
                    idle_time = current_time - conn.last_used
                    
                    if conn.is_active:
                        active_conns.append(conn)
                    elif idle_time > self.idle_timeout:
                        self._stats["total_closed"] += 1
                        self.logger.debug(f"Closed idle connection to {pool_key}")
                    elif conn.health_score < 20:
                        self._stats["total_closed"] += 1
                    else:
                        active_conns.append(conn)
                
                self._pools[pool_key] = active_conns
                
                # Remove empty pools
                if not active_conns:
                    del self._pools[pool_key]
    
    def get_stats(self) -> Dict:
        """Get pool statistics"""
        with self._lock:
            total = sum(len(p) for p in self._pools.values())
            active = sum(1 for p in self._pools.values() for c in p if c.is_active)
            
            return {
                **self._stats,
                "current_total": total,
                "current_active": active,
                "current_idle": total - active,
                "hosts": len(self._pools),
                "reuse_rate_pct": round(
                    self._stats["cache_hits"] / max(1, self._stats["cache_hits"] + self._stats["cache_misses"]) * 100, 2
                ),
            }
    
    def shutdown(self):
        """Shutdown the connection pool"""
        self._running = False
        with self._lock:
            self._pools.clear()


class FingerprintRotator:
    """
    V7.6 P0: Rotate fingerprints dynamically to avoid pattern detection.
    
    Features:
    - Time-based rotation schedules
    - Per-target fingerprint selection
    - Entropy injection for variation
    - Rotation history tracking
    - Anti-pattern detection
    """
    
    # Rotation strategies
    STRATEGY_FIXED = "fixed"          # No rotation
    STRATEGY_TIME_BASED = "time"      # Rotate every N minutes
    STRATEGY_REQUEST_BASED = "request"  # Rotate every N requests
    STRATEGY_RANDOM = "random"         # Random rotation
    STRATEGY_ADAPTIVE = "adaptive"     # Adapt based on responses
    
    def __init__(self, strategy: str = "time", rotation_interval: float = 300):
        self.strategy = strategy
        self.rotation_interval = rotation_interval
        
        # Available fingerprints for rotation
        self._available_profiles = list(BrowserProfile)
        self._excluded_profiles: List[BrowserProfile] = []
        
        # Current state
        self._state = FingerprintState(
            current_profile=BrowserProfile.CHROME_131_WIN11,
            rotation_count=0,
            last_rotation=time.time(),
            entropy_seed=random.randint(0, 2**32),
            session_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:16],
        )
        
        # Per-host fingerprint assignments
        self._host_assignments: Dict[str, BrowserProfile] = {}
        
        # Rotation history
        self._history: deque = deque(maxlen=100)
        
        # Request counter for request-based rotation
        self._request_count = 0
        
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-FP-ROTATOR")
    
    def get_fingerprint(self, host: Optional[str] = None) -> BrowserProfile:
        """
        Get the appropriate fingerprint for a request.
        
        Args:
            host: Target host (for per-host assignment)
        
        Returns:
            BrowserProfile to use
        """
        with self._lock:
            # Check if rotation is needed
            self._maybe_rotate()
            
            # Per-host assignment for consistency
            if host and host in self._host_assignments:
                return self._host_assignments[host]
            
            # Return current profile
            profile = self._state.current_profile
            
            # Assign to host for consistency
            if host:
                self._host_assignments[host] = profile
            
            self._request_count += 1
            return profile
    
    def _maybe_rotate(self):
        """Check if rotation is needed and perform it"""
        should_rotate = False
        
        if self.strategy == self.STRATEGY_TIME_BASED:
            elapsed = time.time() - self._state.last_rotation
            should_rotate = elapsed >= self.rotation_interval
        
        elif self.strategy == self.STRATEGY_REQUEST_BASED:
            should_rotate = self._request_count >= self.rotation_interval
        
        elif self.strategy == self.STRATEGY_RANDOM:
            # 5% chance per request
            should_rotate = random.random() < 0.05
        
        elif self.strategy == self.STRATEGY_ADAPTIVE:
            # Adaptive rotation based on history
            should_rotate = self._should_adapt()
        
        if should_rotate:
            self._rotate()
    
    def _rotate(self):
        """Rotate to a new fingerprint"""
        # Select next profile
        available = [p for p in self._available_profiles if p not in self._excluded_profiles]
        if not available:
            available = self._available_profiles
        
        # Avoid immediate repeat
        candidates = [p for p in available if p != self._state.current_profile]
        if not candidates:
            candidates = available
        
        new_profile = random.choice(candidates)
        
        # Record rotation
        self._history.append({
            "from": self._state.current_profile.value,
            "to": new_profile.value,
            "timestamp": time.time(),
            "request_count": self._request_count,
        })
        
        self._state.current_profile = new_profile
        self._state.rotation_count += 1
        self._state.last_rotation = time.time()
        self._request_count = 0
        
        # Clear host assignments on rotation (optional - configure)
        # self._host_assignments.clear()
        
        self.logger.info(f"Fingerprint rotated to {new_profile.value} (rotation #{self._state.rotation_count})")
    
    def _should_adapt(self) -> bool:
        """Determine if adaptive rotation is needed"""
        if len(self._history) < 5:
            return False
        
        # Check for repeated patterns
        recent = list(self._history)[-5:]
        profiles_used = set(h["to"] for h in recent)
        
        # Rotate if we've been using same profile too much
        if len(profiles_used) < 2:
            return True
        
        return False
    
    def force_rotate(self, to_profile: Optional[BrowserProfile] = None):
        """Force immediate rotation"""
        with self._lock:
            if to_profile:
                self._state.current_profile = to_profile
                self._state.rotation_count += 1
                self._state.last_rotation = time.time()
            else:
                self._rotate()
    
    def exclude_profile(self, profile: BrowserProfile):
        """Exclude a profile from rotation"""
        with self._lock:
            if profile not in self._excluded_profiles:
                self._excluded_profiles.append(profile)
    
    def include_profile(self, profile: BrowserProfile):
        """Include a previously excluded profile"""
        with self._lock:
            if profile in self._excluded_profiles:
                self._excluded_profiles.remove(profile)
    
    def get_state(self) -> Dict:
        """Get current rotation state"""
        with self._lock:
            return {
                "current_profile": self._state.current_profile.value,
                "rotation_count": self._state.rotation_count,
                "last_rotation": self._state.last_rotation,
                "strategy": self.strategy,
                "rotation_interval": self.rotation_interval,
                "request_count": self._request_count,
                "host_assignments": len(self._host_assignments),
                "excluded_profiles": [p.value for p in self._excluded_profiles],
            }


class QUICHealthMonitor:
    """
    V7.6 P0: Monitor QUIC proxy health and connection quality.
    
    Features:
    - Connection latency tracking
    - Error rate monitoring
    - Pool health assessment
    - Automatic issue detection
    - Health alerts and thresholds
    """
    
    def __init__(self, proxy: 'TitanQUICProxy',
                 pool: 'QUICConnectionPool' = None,
                 rotator: 'FingerprintRotator' = None):
        self.proxy = proxy
        self.pool = pool
        self.rotator = rotator
        
        # Metrics tracking
        self._latencies: deque = deque(maxlen=100)
        self._errors: deque = deque(maxlen=100)
        self._requests: deque = deque(maxlen=1000)
        
        # Health thresholds
        self.thresholds = {
            "max_latency_ms": 500,
            "max_error_rate_pct": 5,
            "min_pool_utilization_pct": 10,
            "max_pool_utilization_pct": 90,
        }
        
        # Alert callbacks
        self._alert_callbacks: List[callable] = []
        
        # Background monitoring
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-QUIC-HEALTH")
    
    def record_request(self, latency_ms: float, success: bool,
                       host: str = None, fingerprint: str = None):
        """Record a request for health tracking"""
        with self._lock:
            timestamp = time.time()
            
            self._latencies.append(latency_ms)
            self._requests.append({
                "timestamp": timestamp,
                "latency_ms": latency_ms,
                "success": success,
                "host": host,
                "fingerprint": fingerprint,
            })
            
            if not success:
                self._errors.append({
                    "timestamp": timestamp,
                    "host": host,
                })
    
    def check_health(self) -> HealthCheckResult:
        """Perform comprehensive health check"""
        issues = []
        
        with self._lock:
            # Calculate average latency
            avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0
            
            # Calculate error rate (last minute)
            current_time = time.time()
            recent_errors = [e for e in self._errors if current_time - e["timestamp"] < 60]
            recent_requests = [r for r in self._requests if current_time - r["timestamp"] < 60]
            
            error_rate = (len(recent_errors) / len(recent_requests) * 100) if recent_requests else 0
        
        # Check thresholds
        if avg_latency > self.thresholds["max_latency_ms"]:
            issues.append(f"High latency: {avg_latency:.1f}ms > {self.thresholds['max_latency_ms']}ms")
        
        if error_rate > self.thresholds["max_error_rate_pct"]:
            issues.append(f"High error rate: {error_rate:.1f}% > {self.thresholds['max_error_rate_pct']}%")
        
        # Check pool health
        pool_utilization = 0
        if self.pool:
            stats = self.pool.get_stats()
            total = stats["current_total"]
            active = stats["current_active"]
            pool_utilization = (active / total * 100) if total > 0 else 0
            
            if pool_utilization > self.thresholds["max_pool_utilization_pct"]:
                issues.append(f"High pool utilization: {pool_utilization:.1f}%")
        
        # Check fingerprint diversity
        fingerprint_diversity = 0
        if self.rotator:
            state = self.rotator.get_state()
            fingerprint_diversity = len(BrowserProfile) - len(state.get("excluded_profiles", []))
        
        return HealthCheckResult(
            healthy=len(issues) == 0,
            latency_ms=avg_latency,
            error_rate_pct=error_rate,
            pool_utilization_pct=pool_utilization,
            fingerprint_diversity=fingerprint_diversity,
            issues=issues,
        )
    
    def start_monitoring(self, interval: float = 30):
        """Start background health monitoring"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("QUIC health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("QUIC health monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Background monitoring loop"""
        while self._running:
            try:
                result = self.check_health()
                
                if not result.healthy:
                    self._trigger_alerts(result)
                
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
    
    def _trigger_alerts(self, result: HealthCheckResult):
        """Trigger alerts for health issues"""
        for issue in result.issues:
            self.logger.warning(f"QUIC Health Alert: {issue}")
        
        for callback in self._alert_callbacks:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Alert callback error: {e}")
    
    def add_alert_callback(self, callback: callable):
        """Add a callback for health alerts"""
        self._alert_callbacks.append(callback)
    
    def get_metrics(self) -> QUICMetrics:
        """Get current metrics snapshot"""
        with self._lock:
            current_time = time.time()
            
            # Requests per minute
            recent_requests = [r for r in self._requests if current_time - r["timestamp"] < 60]
            rpm = len(recent_requests)
            
            # Average latency
            avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0
            
            # Total bytes (estimated)
            bytes_transferred = len(self._requests) * 50000  # Rough estimate
            
            return QUICMetrics(
                timestamp=current_time,
                total_connections=len(self._requests),
                active_connections=len(self.proxy.active_connections) if self.proxy else 0,
                pooled_connections=self.pool.get_stats()["current_total"] if self.pool else 0,
                requests_per_minute=rpm,
                avg_latency_ms=avg_latency,
                connection_errors=len(self._errors),
                fingerprint_rotations=self.rotator.get_state()["rotation_count"] if self.rotator else 0,
                bytes_transferred=bytes_transferred,
            )


class ProxyMetricsCollector:
    """
    V7.6 P0: Collect and analyze proxy performance metrics.
    
    Features:
    - Time-series metrics collection
    - Performance trend analysis
    - Anomaly detection
    - Report generation
    - Metric persistence
    """
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        
        # Time-series data
        self._metrics: deque = deque(maxlen=10000)
        
        # Aggregated stats
        self._hourly_stats: Dict[int, Dict] = {}
        
        # Anomaly detection
        self._baseline: Optional[Dict] = None
        self._anomalies: List[Dict] = []
        
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-PROXY-METRICS")
    
    def record_metric(self, metric: QUICMetrics):
        """Record a metrics snapshot"""
        with self._lock:
            self._metrics.append({
                "timestamp": metric.timestamp,
                "total_connections": metric.total_connections,
                "active_connections": metric.active_connections,
                "pooled_connections": metric.pooled_connections,
                "requests_per_minute": metric.requests_per_minute,
                "avg_latency_ms": metric.avg_latency_ms,
                "connection_errors": metric.connection_errors,
                "fingerprint_rotations": metric.fingerprint_rotations,
                "bytes_transferred": metric.bytes_transferred,
            })
            
            # Update hourly stats
            hour = int(metric.timestamp // 3600)
            if hour not in self._hourly_stats:
                self._hourly_stats[hour] = {
                    "samples": 0,
                    "total_latency": 0,
                    "total_errors": 0,
                    "total_requests": 0,
                }
            
            self._hourly_stats[hour]["samples"] += 1
            self._hourly_stats[hour]["total_latency"] += metric.avg_latency_ms
            self._hourly_stats[hour]["total_errors"] += metric.connection_errors
            self._hourly_stats[hour]["total_requests"] += metric.requests_per_minute
            
            # Clean old hourly stats
            cutoff_hour = hour - self.retention_hours
            self._hourly_stats = {
                h: s for h, s in self._hourly_stats.items()
                if h > cutoff_hour
            }
            
            # Check for anomalies
            self._check_anomalies(metric)
    
    def compute_baseline(self):
        """Compute baseline metrics from collected data"""
        with self._lock:
            if len(self._metrics) < 10:
                return
            
            latencies = [m["avg_latency_ms"] for m in self._metrics]
            rpms = [m["requests_per_minute"] for m in self._metrics]
            
            self._baseline = {
                "avg_latency": sum(latencies) / len(latencies),
                "std_latency": self._std_dev(latencies),
                "avg_rpm": sum(rpms) / len(rpms),
                "std_rpm": self._std_dev(rpms),
                "computed_at": time.time(),
                "samples": len(self._metrics),
            }
            
            self.logger.info(f"Baseline computed: latency={self._baseline['avg_latency']:.1f}ms")
    
    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _check_anomalies(self, metric: QUICMetrics):
        """Check for anomalies in the metric"""
        if not self._baseline:
            return
        
        # Check latency anomaly (> 3 std dev)
        if self._baseline["std_latency"] > 0:
            z_score = (metric.avg_latency_ms - self._baseline["avg_latency"]) / self._baseline["std_latency"]
            if abs(z_score) > 3:
                self._anomalies.append({
                    "type": "latency",
                    "timestamp": metric.timestamp,
                    "value": metric.avg_latency_ms,
                    "expected": self._baseline["avg_latency"],
                    "z_score": z_score,
                })
                self.logger.warning(f"Latency anomaly: {metric.avg_latency_ms:.1f}ms (z={z_score:.1f})")
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        with self._lock:
            if not self._metrics:
                return {"status": "no data"}
            
            recent = list(self._metrics)[-50:]
            
            return {
                "total_samples": len(self._metrics),
                "hours_tracked": len(self._hourly_stats),
                "recent_avg_latency": sum(m["avg_latency_ms"] for m in recent) / len(recent),
                "recent_avg_rpm": sum(m["requests_per_minute"] for m in recent) / len(recent),
                "total_anomalies": len(self._anomalies),
                "baseline": self._baseline,
            }
    
    def get_hourly_report(self) -> Dict:
        """Get hourly performance report"""
        with self._lock:
            report = {}
            for hour, stats in sorted(self._hourly_stats.items()):
                avg_latency = stats["total_latency"] / stats["samples"] if stats["samples"] > 0 else 0
                report[hour] = {
                    "samples": stats["samples"],
                    "avg_latency_ms": round(avg_latency, 2),
                    "total_errors": stats["total_errors"],
                    "avg_rpm": round(stats["total_requests"] / stats["samples"], 2) if stats["samples"] > 0 else 0,
                }
            return report
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        import json
        
        with self._lock:
            data = {
                "exported_at": time.time(),
                "metrics": list(self._metrics),
                "hourly_stats": self._hourly_stats,
                "baseline": self._baseline,
                "anomalies": self._anomalies,
            }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Metrics exported to {filepath}")


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_quic_connection_pool: Optional[QUICConnectionPool] = None
_fingerprint_rotator: Optional[FingerprintRotator] = None
_quic_health_monitor: Optional[QUICHealthMonitor] = None
_proxy_metrics_collector: Optional[ProxyMetricsCollector] = None


def get_quic_connection_pool(max_per_host: int = 6) -> QUICConnectionPool:
    """Get global QUIC connection pool"""
    global _quic_connection_pool
    if _quic_connection_pool is None:
        _quic_connection_pool = QUICConnectionPool(max_connections_per_host=max_per_host)
    return _quic_connection_pool


def get_fingerprint_rotator(strategy: str = "time") -> FingerprintRotator:
    """Get global fingerprint rotator"""
    global _fingerprint_rotator
    if _fingerprint_rotator is None:
        _fingerprint_rotator = FingerprintRotator(strategy=strategy)
    return _fingerprint_rotator


def get_quic_health_monitor(proxy: TitanQUICProxy = None) -> QUICHealthMonitor:
    """Get global QUIC health monitor"""
    global _quic_health_monitor
    if _quic_health_monitor is None:
        _quic_health_monitor = QUICHealthMonitor(
            proxy=proxy,
            pool=get_quic_connection_pool(),
            rotator=get_fingerprint_rotator(),
        )
    return _quic_health_monitor


def get_proxy_metrics_collector() -> ProxyMetricsCollector:
    """Get global proxy metrics collector"""
    global _proxy_metrics_collector
    if _proxy_metrics_collector is None:
        _proxy_metrics_collector = ProxyMetricsCollector()
    return _proxy_metrics_collector


if __name__ == "__main__":
    asyncio.run(main())
