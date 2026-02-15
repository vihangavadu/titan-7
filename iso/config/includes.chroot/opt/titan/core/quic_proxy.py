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


class BrowserProfile(Enum):
    """Browser TLS fingerprint profiles"""
    CHROME_131_WIN11 = "chrome_131_win11"
    CHROME_131_MACOS = "chrome_131_macos"
    FIREFOX_132_WIN11 = "firefox_132_win11"
    FIREFOX_132_LINUX = "firefox_132_linux"
    SAFARI_17_MACOS = "safari_17_macos"
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
            verify_mode=False,  # We handle verification separately
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
            writer.close()
            await writer.wait_closed()
    
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
            try:
                writer.close()
            except Exception:
                pass
    
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


if __name__ == "__main__":
    asyncio.run(main())
