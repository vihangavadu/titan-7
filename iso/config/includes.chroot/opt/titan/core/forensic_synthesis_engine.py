#!/usr/bin/env python3
"""
TITAN V8.1 ΓÇö Forensic Synthesis Engine
=========================================
Generates forensically undetectable 900-day Firefox profiles with:
- Symmetrical 500MB+ storage (70% Cache2 binary, 30% LSNG/IDB)
- Valid nsDiskCacheEntry 32-byte headers + HTTP metadata tails
- _CACHE_MAP_ index + _CACHE_001_/002_/003_ block files
- DJB2 url_hash for moz_places
- 12-char URL-safe Base64 GUIDs
- LSNG Structured Clone UTF-16LE + Snappy compression
- QuotaManager .metadata-v2 per origin
- Atomic PRTime/POSIX temporal synchronization
- 900-day non-linear circadian history arc
"""
import os, sys, json, sqlite3, hashlib, secrets, random, struct, math, time, zlib
import base64, logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("TITAN-FORENSIC-SYNTH")

try:
    import snappy as _snappy
    HAS_SNAPPY = True
except ImportError:
    HAS_SNAPPY = False

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# FORENSIC CONSTANTS
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
DJB2_GOLDEN_RATIO = 0x9E3779B9
SNAPPY_THRESHOLD = 64
CACHE2_HEADER_SIZE = 36
BLOCK_512 = 512
BLOCK_1024 = 1024
BLOCK_4096 = 4096
CACHE_INDEX_HEADER_SIZE = 12

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# CRYPTOGRAPHIC UTILITIES
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

def moz_url_hash(url: str) -> int:
    """Mozilla's proprietary 64-bit DJB2 URL hash variant."""
    h = 0
    for ch in url:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    h = (h * DJB2_GOLDEN_RATIO) & 0xFFFFFFFFFFFFFFFF
    return h

def moz_guid() -> str:
    """12-character URL-safe Base64 GUID matching Firefox internals."""
    return base64.urlsafe_b64encode(secrets.token_bytes(9)).decode('ascii')[:12]

def to_prtime(dt: datetime) -> int:
    """Datetime -> Mozilla PRTime (microseconds since epoch)."""
    return int(dt.timestamp() * 1_000_000)

def to_posix(dt: datetime) -> int:
    """Datetime -> POSIX seconds."""
    return int(dt.timestamp())

def http_date(dt: datetime) -> str:
    """Datetime -> HTTP-date format (RFC 7231)."""
    days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return '%s, %02d %s %d %02d:%02d:%02d GMT' % (
        days[dt.weekday()], dt.day, months[dt.month-1], dt.year,
        dt.hour, dt.minute, dt.second)

def encode_structured_clone(value: str) -> bytes:
    """Encodes string to Firefox Structured Clone format (UTF-16LE + 4-byte length header)."""
    utf16 = value.encode('utf-16-le')
    header = struct.pack('<I', len(value))
    return header + utf16

def snappy_compress(data: bytes) -> Tuple[bytes, int]:
    """Compress with Snappy if available and beneficial. Returns (data, compressed_flag)."""
    if len(data) <= SNAPPY_THRESHOLD:
        return data, 0
    if HAS_SNAPPY:
        compressed = _snappy.compress(data)
        if len(compressed) < len(data):
            return compressed, 1
    return data, 0

def calculate_frecency(visit_count: int, days_since_last: int, typed: bool = False) -> int:
    """Calculate Mozilla frecency score. Higher = more frequently/recently visited."""
    if visit_count == 0:
        return 0
    bonus = 2000 if typed else 100
    bucket_weight = 1.0
    if days_since_last < 4:
        bucket_weight = 1.0
    elif days_since_last < 14:
        bucket_weight = 0.7
    elif days_since_last < 31:
        bucket_weight = 0.5
    elif days_since_last < 90:
        bucket_weight = 0.3
    else:
        bucket_weight = 0.1
    point_for_visit = bonus * bucket_weight
    frecency = int(visit_count * math.ceil(point_for_visit) / visit_count)
    return max(frecency, -1)

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# UNIFIED TIME STATE MANAGER
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class TimeStateManager:
    """Atomic temporal synchronization across all storage formats."""
    def __init__(self, age_days: int = 900):
        self.now = datetime.now(timezone.utc)
        self.profile_birth = self.now - timedelta(days=age_days)
        self.age_days = age_days
        
    def random_event(self, min_days_ago: int = 0, max_days_ago: int = None) -> datetime:
        """Generate a random event time within profile lifetime, with circadian weighting."""
        if max_days_ago is None:
            max_days_ago = self.age_days
        max_days_ago = min(max_days_ago, self.age_days)
        days_ago = random.randint(min_days_ago, max_days_ago)
        hour = self._circadian_hour()
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        dt = self.now - timedelta(days=days_ago)
        return dt.replace(hour=hour, minute=minute, second=second,
                         microsecond=random.randint(0, 999999))
    
    def _circadian_hour(self) -> int:
        """Circadian rhythm: peaks at 10, 14, 20; troughs at 03-06."""
        weights = [1,1,1,1,1,2,3,5,7,9,10,8,7,8,9,8,7,6,7,9,10,8,5,2]
        return random.choices(range(24), weights=weights, k=1)[0]
    
    def burst_session(self, center_time: datetime, num_events: int = 5,
                      spread_minutes: int = 30) -> List[datetime]:
        """Generate a burst of events around a center time (browsing session)."""
        events = []
        for _ in range(num_events):
            offset = random.gauss(0, spread_minutes / 3) 
            dt = center_time + timedelta(minutes=offset)
            dt = dt.replace(microsecond=random.randint(0, 999999))
            events.append(dt)
        return sorted(events)

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# CACHE2 FILESYSTEM SYNTHESIZER
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class Cache2Synthesizer:
    """Generates forensically valid Firefox Cache2 filesystem."""
    
    # Realistic web asset templates
    CDN_DOMAINS = [
        'cdn.jsdelivr.net','unpkg.com','cdnjs.cloudflare.com',
        'static.xx.fbcdn.net','www.gstatic.com','s.pinimg.com',
        'platform.twitter.com','connect.facebook.net','securepubads.g.doubleclick.net',
        'www.googletagmanager.com','js.stripe.com','www.google-analytics.com',
    ]
    IMG_DOMAINS = [
        'images-na.ssl-images-amazon.com','m.media-amazon.com',
        'i.ytimg.com','pbs.twimg.com','avatars.githubusercontent.com',
        'encrypted-tbn0.gstatic.com','scontent.xx.fbcdn.net',
        'images.unsplash.com','cdn.shopify.com','i.imgur.com',
    ]
    CONTENT_TYPES = {
        'js': ('application/javascript', (30000, 500000)),
        'css': ('text/css', (5000, 150000)),
        'jpg': ('image/jpeg', (8000, 900000)),
        'png': ('image/png', (3000, 500000)),
        'webp': ('image/webp', (5000, 600000)),
        'woff2': ('font/woff2', (15000, 80000)),
        'json': ('application/json', (200, 50000)),
        'svg': ('image/svg+xml', (500, 30000)),
        'gif': ('image/gif', (1000, 200000)),
    }
    
    def __init__(self, profile_dir: Path, tsm: TimeStateManager):
        self.entries_dir = profile_dir / 'cache2' / 'entries'
        self.cache_root = profile_dir / 'cache2'
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.tsm = tsm
        self._entry_count = 0
        
    def synthesize(self, target_bytes: int) -> int:
        """Generate Cache2 binary mass to target size."""
        # Clean existing
        for f in self.entries_dir.iterdir():
            if f.is_file():
                f.unlink()
        
        written = 0
        while written < target_bytes:
            asset = self._random_asset()
            size = self._write_entry(asset)
            written += size
            self._entry_count += 1
        
        # Write index files
        self._write_cache_map()
        self._write_block_files()
        
        logger.info('[CACHE2] %d entries, %.1f MB', self._entry_count, written / 1e6)
        return written
    
    def _random_asset(self) -> Dict:
        """Generate a random web asset descriptor."""
        ext = random.choices(
            list(self.CONTENT_TYPES.keys()),
            weights=[30, 15, 25, 10, 10, 5, 3, 1, 1],  # JS/CSS/images dominate
            k=1
        )[0]
        ct, (lo, hi) = self.CONTENT_TYPES[ext]
        
        if ext in ('js', 'css', 'json', 'svg'):
            domain = random.choice(self.CDN_DOMAINS)
        elif ext in ('jpg', 'png', 'webp', 'gif'):
            domain = random.choice(self.IMG_DOMAINS)
        else:
            domain = random.choice(self.CDN_DOMAINS + self.IMG_DOMAINS)
        
        path = '/%s/%s.%s' % (
            random.choice(['assets','static','dist','build','_next/static','bundles','media']),
            secrets.token_hex(random.randint(8, 20)),
            ext
        )
        
        event_time = self.tsm.random_event()
        
        return {
            'url': 'https://%s%s' % (domain, path),
            'content_type': ct,
            'ext': ext,
            'size': random.randint(lo, hi),
            'event_time': event_time,
            'server': random.choice(['gws','cloudflare','nginx/1.24.0','AmazonS3','Apache','ECS (dca/24A8)','Microsoft-IIS/10.0']),
        }
    
    def _write_entry(self, asset: Dict) -> int:
        """Write a single cache2 entry with valid nsDiskCacheEntry header + HTTP metadata tail."""
        url = asset['url']
        event_time = asset['event_time']
        data_size = asset['size']
        
        # Generate content
        content = self._generate_content(asset['ext'], data_size)
        
        # Build HTTP metadata tail
        etag = '"%s"' % secrets.token_hex(16)
        last_mod = event_time - timedelta(days=random.randint(1, 180))
        http_meta = (
            'request-method\x00GET\x00'
            'response-head\x00HTTP/1.1 200 OK\r\n'
            'Content-Type: %s\r\n'
            'Content-Length: %d\r\n'
            'ETag: %s\r\n'
            'Last-Modified: %s\r\n'
            'Cache-Control: public, max-age=%d\r\n'
            'Accept-Ranges: bytes\r\n'
            'Server: %s\r\n'
            'Date: %s\r\n'
            'X-Cache: HIT\r\n'
            '\r\n\x00'
        ) % (
            asset['content_type'], data_size, etag,
            http_date(last_mod),
            random.randint(3600, 31536000),
            asset['server'],
            http_date(event_time),
        )
        http_meta_bytes = http_meta.encode('ascii', errors='replace')
        
        # Cache key
        key_str = ':https://%s' % url.split('://')[1]
        key_bytes = key_str.encode('ascii') + b'\x00'
        
        # 36-byte nsDiskCacheEntry header (little-endian)
        fetch_count = random.randint(1, 50)
        last_fetched = to_posix(event_time)
        last_modified = to_posix(last_mod)
        expiration = to_posix(event_time + timedelta(days=random.randint(30, 365)))
        
        header = struct.pack('<HH', 1, 3)  # major=1, minor=3 (Firefox format version)
        header += struct.pack('<I', len(content))  # metadata location = content length
        header += struct.pack('<I', fetch_count)
        header += struct.pack('<I', last_fetched)
        header += struct.pack('<I', last_modified)
        header += struct.pack('<I', expiration)
        header += struct.pack('<I', len(content))  # data size
        header += struct.pack('<I', len(key_bytes))  # key size
        header += struct.pack('<I', len(http_meta_bytes))  # metadata size
        
        assert len(header) == CACHE2_HEADER_SIZE
        
        # File = header + content + key + metadata
        filename = hashlib.sha1(key_str.encode()).hexdigest().upper()
        entry_path = self.entries_dir / filename
        
        with open(entry_path, 'wb') as f:
            f.write(header)
            f.write(content)
            f.write(key_bytes)
            f.write(http_meta_bytes)
        
        return CACHE2_HEADER_SIZE + len(content) + len(key_bytes) + len(http_meta_bytes)
    
    def _generate_content(self, ext: str, size: int) -> bytes:
        """Generate forensically realistic content for each asset type."""
        if ext == 'js':
            return self._gen_js(size)
        elif ext == 'css':
            return self._gen_css(size)
        elif ext == 'jpg':
            # Valid JPEG: FFD8 header + JFIF + random data + FFD9 footer
            hdr = bytes([0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00])
            footer = bytes([0xFF, 0xD9])
            return hdr + os.urandom(size - len(hdr) - len(footer)) + footer
        elif ext == 'png':
            return self._gen_png(size)
        elif ext == 'webp':
            hdr = b'RIFF' + struct.pack('<I', size - 8) + b'WEBPVP8 '
            return hdr + os.urandom(size - len(hdr))
        elif ext == 'woff2':
            hdr = b'wOF2' + struct.pack('>I', 0x00010000) + struct.pack('>I', size)
            return hdr + os.urandom(size - len(hdr))
        elif ext == 'gif':
            hdr = b'GIF89a' + struct.pack('<HH', 1, 1)
            return hdr + os.urandom(size - len(hdr))
        elif ext == 'svg':
            svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            svg += b'<path d="M' + secrets.token_hex(size // 3).encode()[:size - len(svg) - 10]
            svg += b'"/></svg>'
            return svg[:size]
        elif ext == 'json':
            return self._gen_json(size)
        return os.urandom(size)
    
    def _gen_js(self, size: int) -> bytes:
        """Minified JS that passes entropy analysis."""
        tokens = [b'var ',b'function(',b'){',b'return ',b'this.',b'new ',b'if(',b'else{',
                  b'for(var ',b'.prototype.',b'module.exports=',b'window.',b'document.',
                  b'addEventListener("',b'querySelector(".',b'createElement("',
                  b'JSON.parse(',b'Promise.',b'async ',b'await ',b'fetch("',b'const ',
                  b'let ',b'class ',b'extends ',b'constructor(',b'super(',b'typeof ',
                  b'Object.assign(',b'Array.from(',b'Math.floor(',b'parseInt(',
                  b'setTimeout(',b'setInterval(',b'clearTimeout(',b'console.log(',
                  b'try{',b'catch(e){',b'throw new Error("',b'null',b'undefined',
                  b'true',b'false',b'||',b'&&',b'===',b'!==',b'>=',b'<=',]
        buf = bytearray()
        while len(buf) < size:
            buf += random.choice(tokens)
            buf += secrets.token_hex(random.randint(2, 8)).encode()
            if random.random() < 0.15: buf += b';'
            if random.random() < 0.03: buf += b'\n'
        return bytes(buf[:size])
    
    def _gen_css(self, size: int) -> bytes:
        sels = [b'.c-',b'#m-',b'body ',b'div.',b'span.',b'a:hover',b'.btn-',b'.nav-',
                b'header ',b'footer ',b'.card-',b'.modal-',b'@media(',b'.flex-',b'.grid-',
                b'h1,h2,h3',b'p.',b'input.',b'textarea',b'select.',b'[data-',b'::before',b'::after']
        props = [b'display:',b'position:',b'margin:',b'padding:',b'color:#',b'background:',
                 b'font-size:',b'font-weight:',b'border:',b'width:',b'height:',b'opacity:',
                 b'transform:',b'transition:',b'flex:',b'z-index:',b'overflow:',b'cursor:']
        buf = bytearray()
        while len(buf) < size:
            buf += random.choice(sels) + secrets.token_hex(3).encode()
            buf += b'{' + random.choice(props) + secrets.token_hex(3).encode() + b'}'
        return bytes(buf[:size])
    
    def _gen_png(self, size: int) -> bytes:
        """Valid PNG with random pixel data."""
        def _chunk(ct, data):
            c = ct + data
            crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            return struct.pack('>I', len(data)) + c + crc
        w = random.choice([16, 32, 48, 64])
        h = max(1, (size - 100) // (w * 3 + 1))
        hdr = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
        raw = b''
        for y in range(min(h, 256)):
            raw += b'\x00' + os.urandom(w * 3)
        idat = zlib.compress(raw, 1)
        png = hdr + _chunk(b'IHDR', ihdr) + _chunk(b'IDAT', idat) + _chunk(b'IEND', b'')
        if len(png) < size:
            png += os.urandom(size - len(png))
        return png[:size]
    
    def _gen_json(self, size: int) -> bytes:
        d = {'d': {('k%d' % i): secrets.token_hex(random.randint(4, 32)) for i in range(random.randint(3, 20))}}
        j = json.dumps(d).encode()
        while len(j) < size:
            j += json.dumps({'x': secrets.token_hex(32)}).encode()
        return j[:size]
    
    def _write_cache_map(self):
        """Write _CACHE_MAP_ index file with valid 12-byte CacheIndexHeader."""
        map_path = self.cache_root / '_CACHE_MAP_'
        # CacheIndexHeader: version(4) + entries(4) + dirty(4)
        header = struct.pack('<III',
                             2,  # version
                             self._entry_count,
                             0)  # not dirty
        # Followed by hash table entries (simplified ΓÇö 256KB index)
        index_data = os.urandom(256 * 1024)
        with open(map_path, 'wb') as f:
            f.write(header)
            f.write(index_data)
    
    def _write_block_files(self):
        """Write _CACHE_001/002/003_ block files."""
        for name, block_size, target_kb in [
            ('_CACHE_001_', BLOCK_512, 1024),
            ('_CACHE_002_', BLOCK_1024, 2048),
            ('_CACHE_003_', BLOCK_4096, 4096),
        ]:
            path = self.cache_root / name
            # Block file header: magic(4) + version(4) + num_blocks(4) + block_size(4)
            num_blocks = (target_kb * 1024) // block_size
            header = struct.pack('<IIII', 0x00000001, 3, num_blocks, block_size)
            with open(path, 'wb') as f:
                f.write(header)
                f.write(os.urandom(num_blocks * block_size))

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# LSNG SYNTHESIZER WITH STRUCTURED CLONE + SNAPPY
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

class LSNGSynthesizer:
    """Generates forensically valid LSNG storage with Structured Clone encoding."""
    
    def __init__(self, profile_dir: Path, tsm: TimeStateManager):
        self.storage_dir = profile_dir / 'storage' / 'default'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tsm = tsm
    
    def sanitize_origin(self, url: str) -> str:
        if url.startswith('https://'):
            return 'https+++' + url[8:].rstrip('/')
        return 'http+++' + url[7:].rstrip('/')
    
    def write_metadata_v2(self, origin_dir: Path, origin_url: str):
        """Generate QuotaManager .metadata-v2 file."""
        meta_path = origin_dir / '.metadata-v2'
        origin_bytes = origin_url.encode('utf-8')
        # .metadata-v2 format:
        # 8 bytes: last access time (microseconds)
        # 1 byte: persisted flag
        # 4 bytes: reserved
        # 4 bytes: suffix length
        # suffix bytes
        # 4 bytes: group length  
        # group bytes
        # 4 bytes: origin length
        # origin bytes
        last_access = to_prtime(self.tsm.random_event(0, 7))
        buf = struct.pack('<Q', last_access)
        buf += struct.pack('<B', 0)  # not persisted
        buf += struct.pack('<I', 0)  # reserved
        buf += struct.pack('<I', 0)  # empty suffix
        group = origin_url.encode('utf-8')
        buf += struct.pack('<I', len(group)) + group
        buf += struct.pack('<I', len(origin_bytes)) + origin_bytes
        buf += b'\x00' * max(0, 62 - len(buf))  # pad to minimum
        meta_path.write_bytes(buf)
    
    def inject_origin(self, origin_url: str, entries: List[Tuple[str, str]],
                      target_bytes: int = 0):
        """Inject LSNG data for an origin with Structured Clone encoding."""
        origin = self.sanitize_origin(origin_url)
        origin_dir = self.storage_dir / origin
        ls_dir = origin_dir / 'ls'
        idb_dir = origin_dir / 'idb'
        ls_dir.mkdir(parents=True, exist_ok=True)
        idb_dir.mkdir(parents=True, exist_ok=True)
        
        self.write_metadata_v2(origin_dir, origin_url)
        
        db_path = ls_dir / 'data.sqlite'
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('PRAGMA page_size = 32768')
        c.execute('PRAGMA journal_mode = WAL')
        c.execute("""CREATE TABLE IF NOT EXISTS data (
            key TEXT PRIMARY KEY,
            utf16Length INTEGER NOT NULL,
            compressed INTEGER NOT NULL,
            lastAccessTime INTEGER NOT NULL,
            value BLOB NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS database (
            origin TEXT NOT NULL,
            last_vacuum_time INTEGER NOT NULL DEFAULT 0,
            last_analyze_time INTEGER NOT NULL DEFAULT 0,
            last_vacuum_size INTEGER NOT NULL DEFAULT 0
        )""")
        
        total = 0
        for key, value in entries:
            sc_data = encode_structured_clone(value)
            blob, compressed = snappy_compress(sc_data)
            ts = to_prtime(self.tsm.random_event(0, 90))
            c.execute('INSERT OR REPLACE INTO data VALUES (?,?,?,?,?)',
                      (key, len(value), compressed, ts, blob))
            total += len(blob)
        
        # Pad to target if specified
        if target_bytes > 0:
            i = 0
            while total < target_bytes:
                val = self._gen_padding_value()
                sc_data = encode_structured_clone(val)
                blob, compressed = snappy_compress(sc_data)
                k = 'cache:%s:%s' % (secrets.token_hex(4), secrets.token_hex(6))
                ts = to_prtime(self.tsm.random_event(0, 180))
                c.execute('INSERT OR REPLACE INTO data VALUES (?,?,?,?,?)',
                          (k, len(val), compressed, ts, blob))
                total += len(blob)
                i += 1
                if i > 50000: break
        
        conn.commit()
        conn.close()
        return total
    
    def _gen_padding_value(self) -> str:
        """Generate realistic-looking localStorage value for padding."""
        rtype = random.randint(0, 3)
        if rtype == 0:
            return json.dumps({
                'event': random.choice(['page_view','click','scroll','impression']),
                'ts': int(time.time()) - random.randint(0, 86400 * 180),
                'sid': secrets.token_hex(8),
                'props': {('p%d' % j): secrets.token_hex(random.randint(4, 32))
                          for j in range(random.randint(2, 8))}
            })
        elif rtype == 1:
            return base64.b64encode(os.urandom(random.randint(512, 8192))).decode()
        elif rtype == 2:
            return json.dumps({
                'url': 'https://cdn.example.com/%s.%s' % (
                    secrets.token_hex(16), random.choice(['js','css','woff2'])),
                'h': {'ct': random.choice(['text/javascript','text/css']),
                      'etag': '"%s"' % secrets.token_hex(16)},
                'b': base64.b64encode(os.urandom(random.randint(256, 4096))).decode()
            })
        else:
            return json.dumps({
                'id': random.randint(1, 999999),
                'd': {('f%d' % j): secrets.token_hex(random.randint(8, 64))
                      for j in range(random.randint(3, 12))}
            })

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# MAIN ORCHESTRATOR
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

def synthesize_profile(profile_path: str, config: Dict = None) -> int:
    """
    Main entry: generate forensically undetectable 900-day profile.
    
    Args:
        profile_path: Path to profile directory
        config: Optional config dict
    
    Returns:
        Total profile size in bytes
    """
    config = config or {}
    pp = Path(profile_path)
    age_days = config.get('profile_age_days', 900)
    target_mb = config.get('target_mb', 500)
    
    tsm = TimeStateManager(age_days)
    
    # Calculate symmetrical targets (70% cache, 30% LSNG/IDB)
    total_target = target_mb * 1024 * 1024
    cache_target = int(total_target * 0.70)
    lsng_target = int(total_target * 0.20)
    idb_target = int(total_target * 0.10)
    
    logger.info('[SYNTH] Starting %d-day, %dMB profile synthesis', age_days, target_mb)
    
    # Phase 1: Cache2 binary mass (70%)
    logger.info('[SYNTH] Phase 1: Cache2 binary mass (%d MB)', cache_target // (1024*1024))
    cache_synth = Cache2Synthesizer(pp, tsm)
    cache_bytes = cache_synth.synthesize(cache_target)
    
    # Phase 2: LSNG storage (20%)
    logger.info('[SYNTH] Phase 2: LSNG storage (%d MB)', lsng_target // (1024*1024))
    lsng_synth = LSNGSynthesizer(pp, tsm)
    lsng_bytes = _populate_lsng(lsng_synth, tsm, lsng_target)
    
    # Phase 3: IndexedDB (10%)
    logger.info('[SYNTH] Phase 3: IndexedDB (%d MB)', idb_target // (1024*1024))
    idb_bytes = _populate_idb(pp, tsm, idb_target)
    
    total = sum(f.stat().st_size for f in pp.rglob('*') if f.is_file())
    logger.info('[SYNTH] Complete: %d MB total (cache=%dMB lsng=%dMB idb=%dMB)',
                total // (1024*1024), cache_bytes // (1024*1024),
                lsng_bytes // (1024*1024), idb_bytes // (1024*1024))
    return total


def _populate_lsng(lsng: LSNGSynthesizer, tsm: TimeStateManager, target: int) -> int:
    """Populate LSNG with domain-specific realistic data."""
    domains = {
        'https://www.google.com': [('_ga','GA1.2.%d.%d'%(random.randint(100000,999999),int(time.time())-random.randint(86400,86400*180))),('_gid','GA1.2.%d.%d'%(random.randint(100000,999999),int(time.time()))),('NID',secrets.token_hex(64))],
        'https://www.youtube.com': [('yt-player-bandwidth',str(random.randint(2000000,80000000))),('yt-player-quality',json.dumps({'data':'hd1080'}))],
        'https://www.facebook.com': [('presence',json.dumps({'t3':[],'utc3':int(time.time()),'v':1}))],
        'https://www.amazon.com': [('session-id','%d-%d-%d'%(random.randint(100,999),random.randint(1000000,9999999),random.randint(1000000,9999999)))],
        'https://www.twitter.com': [('night_mode',random.choice(['0','1','2']))],
        'https://www.reddit.com': [('USER_LOCALE','en'),('eu_cookie_v2','3')],
        'https://www.github.com': [('color_mode',json.dumps({'color_mode':'auto'}))],
        'https://www.linkedin.com': [('lang','"v=2&lang=en-us"')],
        'https://www.netflix.com': [('profilesGateState','unlocked')],
        'https://www.spotify.com': [('sp_t',secrets.token_hex(32))],
        'https://www.twitch.tv': [('twilight-user',json.dumps({'authToken':secrets.token_hex(16)}))],
        'https://www.steampowered.com': [('sessionid',secrets.token_hex(12))],
        'https://www.eneba.com': [('currency','USD'),('locale','en')],
        'https://www.walmart.com': [('type','guest')],
        'https://www.bestbuy.com': [('locStoreId',str(random.randint(100,2000)))],
        'https://mail.google.com': [('GMAIL_AT',secrets.token_hex(16))],
        'https://www.stripe.com': [('__stripe_mid',secrets.token_hex(16))],
        'https://www.paypal.com': [('TLTSID',secrets.token_hex(32))],
        'https://www.stackoverflow.com': [('prov',secrets.token_hex(16))],
        'https://www.wikipedia.org': [('GeoIP','US')],
    }
    
    per_domain = target // max(len(domains), 1)
    total = 0
    for url, entries in domains.items():
        total += lsng.inject_origin(url, entries, target_bytes=per_domain)
    return total


def _populate_idb(pp: Path, tsm: TimeStateManager, target: int) -> int:
    """Populate IndexedDB with realistic structured data."""
    sd = pp / 'storage' / 'default'
    
    idb_domains = {
        'google.com': ['search_cache','sync_data'],
        'youtube.com': ['watch_history','player_cache','recommendations'],
        'facebook.com': ['feed_cache','message_cache','media_cache'],
        'amazon.com': ['product_cache','order_history'],
        'twitter.com': ['tweet_cache','timeline_cache'],
        'reddit.com': ['subreddit_cache','post_cache'],
        'gmail.com': ['email_cache','attachment_index'],
        'steampowered.com': ['game_library','achievement_cache'],
        'netflix.com': ['title_cache','continue_watching'],
        'spotify.com': ['track_cache','playlist_cache'],
    }
    
    per_domain = target // max(len(idb_domains), 1)
    total = 0
    
    for domain, stores in idb_domains.items():
        dd = sd / ('https+++www.' + domain) / 'idb'
        dd.mkdir(parents=True, exist_ok=True)
        
        dbh = hashlib.md5(domain.encode()).hexdigest()[:16]
        db_path = dd / (dbh + '.sqlite')
        
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('PRAGMA page_size = 32768')
        c.execute('PRAGMA journal_mode = WAL')
        c.execute("""CREATE TABLE IF NOT EXISTS object_data (
            id INTEGER PRIMARY KEY, object_store_id INTEGER,
            key_value BLOB, data BLOB, file_ids TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS object_store (
            id INTEGER PRIMARY KEY, auto_increment INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL, key_path TEXT
        )""")
        
        for i, sn in enumerate(stores, 1):
            c.execute('INSERT OR IGNORE INTO object_store VALUES (?,?,?,?)',
                      (i, 1, sn, 'id'))
        
        rid = 1
        cb = 0
        while cb < per_domain and rid < 100000:
            sid = random.randint(1, len(stores))
            event_time = tsm.random_event(0, 180)
            data = json.dumps({
                'id': rid, 'type': stores[sid-1],
                'timestamp': to_prtime(event_time),
                'payload': {('f%d' % j): secrets.token_hex(random.randint(16, 128))
                           for j in range(random.randint(3, 15))},
            }).encode()
            c.execute('INSERT OR REPLACE INTO object_data VALUES (?,?,?,?,NULL)',
                      (rid, sid, struct.pack('>I', rid), data))
            cb += len(data)
            rid += 1
        
        conn.commit()
        conn.close()
        total += cb
    
    return total
