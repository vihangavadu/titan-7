"""
TITAN V7.5 SINGULARITY — IndexedDB Sharding Synthesis (LSNG)
Local Storage Next Generation with fragmented multi-bucket IndexedDB

Problem:
    Modern anti-fingerprint systems detect synthetic profiles through:
    1. Storage latency timing attacks (empty vs. populated databases)
    2. Cross-site database schema analysis
    3. LSNG (localStorage Next Gen) entropy measurement
    4. IndexedDB quota behavior fingerprinting
    5. Database creation timestamp clustering

Solution:
    Pre-seeded fragmented IndexedDB stores that:
    1. Mirror realistic web application storage patterns
    2. Introduce deterministic-yet-unique shard distribution
    3. Simulate historical accumulation over time
    4. Match quota consumption to target persona
    5. Prevent timing-based empty-database detection
"""

import hashlib
import json
import os
import random
import sqlite3
import struct
import threading
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set

__version__ = "7.5.0"
__author__ = "Dva.12"


class StoragePersona(Enum):
    """Persona archetypes for storage patterns"""
    CASUAL_USER = "casual"           # Few apps, minimal storage
    POWER_USER = "power"             # Many apps, moderate storage
    DEVELOPER = "developer"          # Dev tools, large storage
    BUSINESS = "business"            # Productivity apps, structured data
    GAMER = "gamer"                  # Gaming platforms, saves
    TRADER = "trader"                # Financial apps, market data


class StorageTarget(Enum):
    """Target storage systems"""
    INDEXED_DB = "indexeddb"
    LOCAL_STORAGE = "localstorage"
    SESSION_STORAGE = "sessionstorage"
    CACHE_STORAGE = "cache"


@dataclass
class StorageShard:
    """Individual storage shard"""
    origin: str              # https://example.com
    database_name: str       # App-specific database name
    store_name: str          # Object store name
    records: int             # Number of records
    size_bytes: int          # Approximate size
    created_at: float        # Unix timestamp
    last_modified: float     # Unix timestamp
    version: int             # Database version
    schema_hash: str         # Schema fingerprint


@dataclass
class LSNGProfile:
    """Complete LSNG profile for a persona"""
    persona: StoragePersona
    shards: List[StorageShard] = field(default_factory=list)
    total_origins: int = 0
    total_size_mb: float = 0.0
    age_days: int = 90       # How old the storage appears


# ═══════════════════════════════════════════════════════════════════════════════
# COMMON WEB APP STORAGE PATTERNS - Real-world captured schemas
# ═══════════════════════════════════════════════════════════════════════════════

# Database schemas from popular web applications
WEB_APP_SCHEMAS: Dict[str, Dict] = {
    "google_account": {
        "origin": "https://accounts.google.com",
        "databases": [
            {"name": "user-state-db", "stores": ["state", "preferences", "sessions"], "avg_records": 50},
            {"name": "IdentityService", "stores": ["tokens", "users"], "avg_records": 10},
        ],
        "typical_size_kb": 128,
    },
    "youtube": {
        "origin": "https://www.youtube.com",
        "databases": [
            {"name": "yt-player-local-media", "stores": ["downloads", "cache", "metadata"], "avg_records": 200},
            {"name": "yt-idb", "stores": ["videos", "playlists", "history"], "avg_records": 1000},
        ],
        "typical_size_kb": 5120,
    },
    "facebook": {
        "origin": "https://www.facebook.com",
        "databases": [
            {"name": "MessengerStore", "stores": ["messages", "threads", "contacts"], "avg_records": 500},
            {"name": "fb_idb", "stores": ["feed", "notifications", "settings"], "avg_records": 300},
        ],
        "typical_size_kb": 4096,
    },
    "twitter": {
        "origin": "https://x.com",
        "databases": [
            {"name": "async-local-storage", "stores": ["data"], "avg_records": 100},
            {"name": "localforageDriver", "stores": ["cache", "media"], "avg_records": 500},
        ],
        "typical_size_kb": 2048,
    },
    "amazon": {
        "origin": "https://www.amazon.com",
        "databases": [
            {"name": "OPF-IDBStore", "stores": ["cart", "recommendations"], "avg_records": 50},
            {"name": "amzn-idb", "stores": ["search", "browse_history"], "avg_records": 200},
        ],
        "typical_size_kb": 1024,
    },
    "linkedin": {
        "origin": "https://www.linkedin.com",
        "databases": [
            {"name": "flagship-next-runtime-cache", "stores": ["profiles", "jobs", "feed"], "avg_records": 150},
        ],
        "typical_size_kb": 512,
    },
    "reddit": {
        "origin": "https://www.reddit.com",
        "databases": [
            {"name": "localforage", "stores": ["data"], "avg_records": 100},
            {"name": "reddit-idb", "stores": ["posts", "comments", "votes"], "avg_records": 800},
        ],
        "typical_size_kb": 1536,
    },
    "netflix": {
        "origin": "https://www.netflix.com",
        "databases": [
            {"name": "nf-idb", "stores": ["titles", "playback", "profiles"], "avg_records": 300},
            {"name": "cache-v1", "stores": ["images", "metadata"], "avg_records": 500},
        ],
        "typical_size_kb": 3072,
    },
    "github": {
        "origin": "https://github.com",
        "databases": [
            {"name": "sw-cache", "stores": ["assets", "api-cache"], "avg_records": 200},
            {"name": "github-idb", "stores": ["repos", "issues", "notifications"], "avg_records": 150},
        ],
        "typical_size_kb": 768,
    },
    "twitch": {
        "origin": "https://www.twitch.tv",
        "databases": [
            {"name": "keyval-store", "stores": ["data"], "avg_records": 50},
            {"name": "player-idb", "stores": ["quality", "volume", "history"], "avg_records": 100},
        ],
        "typical_size_kb": 512,
    },
    "spotify": {
        "origin": "https://open.spotify.com",
        "databases": [
            {"name": "sp-idb", "stores": ["tracks", "playlists", "queue", "recently_played"], "avg_records": 600},
            {"name": "sp-cache", "stores": ["images", "audio_previews"], "avg_records": 200},
        ],
        "typical_size_kb": 2048,
    },
    "instagram": {
        "origin": "https://www.instagram.com",
        "databases": [
            {"name": "ig-idb", "stores": ["feed", "stories", "reels", "direct"], "avg_records": 400},
            {"name": "sw-toolbox", "stores": ["precache", "runtime"], "avg_records": 150},
        ],
        "typical_size_kb": 1536,
    },
    "discord": {
        "origin": "https://discord.com",
        "databases": [
            {"name": "keyval-store", "stores": ["data"], "avg_records": 80},
            {"name": "discord-idb", "stores": ["messages", "guilds", "channels", "users"], "avg_records": 500},
        ],
        "typical_size_kb": 2560,
    },
    "ebay": {
        "origin": "https://www.ebay.com",
        "databases": [
            {"name": "ebay-idb", "stores": ["search", "watched", "bids"], "avg_records": 100},
        ],
        "typical_size_kb": 256,
    },
}

# Persona-specific app distributions
PERSONA_APP_WEIGHTS: Dict[StoragePersona, Dict[str, float]] = {
    StoragePersona.CASUAL_USER: {
        "google_account": 0.95, "youtube": 0.80, "facebook": 0.70,
        "twitter": 0.40, "amazon": 0.50, "netflix": 0.30,
    },
    StoragePersona.POWER_USER: {
        "google_account": 0.99, "youtube": 0.95, "twitter": 0.80,
        "reddit": 0.75, "github": 0.60, "amazon": 0.70,
        "linkedin": 0.50, "twitch": 0.40, "netflix": 0.60,
    },
    StoragePersona.DEVELOPER: {
        "google_account": 0.99, "github": 0.95, "youtube": 0.70,
        "reddit": 0.80, "twitter": 0.60, "linkedin": 0.70,
        "amazon": 0.40, "twitch": 0.30,
    },
    StoragePersona.BUSINESS: {
        "google_account": 0.99, "linkedin": 0.90, "amazon": 0.60,
        "youtube": 0.50, "twitter": 0.40,
    },
    StoragePersona.GAMER: {
        "youtube": 0.90, "twitch": 0.85, "reddit": 0.70,
        "twitter": 0.60, "amazon": 0.50, "google_account": 0.95,
    },
    StoragePersona.TRADER: {
        "google_account": 0.99, "twitter": 0.80, "reddit": 0.70,
        "youtube": 0.60, "linkedin": 0.50, "amazon": 0.40,
    },
}


class IndexedDBShardSynthesizer:
    """
    Synthesizes realistic IndexedDB shards for anti-fingerprint evasion.
    
    Creates fragmented multi-bucket storage that mirrors authentic
    browser accumulation patterns.
    """
    
    def __init__(self, profile_uuid: str, seed: Optional[int] = None):
        self.profile_uuid = profile_uuid
        self._rng = random.Random(seed or hash(profile_uuid))
        self._shards: List[StorageShard] = []
        self._lock = threading.Lock()
    
    def _generate_age_timestamp(self, age_days: int, jitter_days: int = 30) -> float:
        """Generate a realistic creation timestamp"""
        base_age = age_days + self._rng.randint(-jitter_days, jitter_days)
        base_age = max(1, base_age)  # At least 1 day old
        return time.time() - (base_age * 86400) + self._rng.randint(0, 86400)
    
    def _generate_record_data(self, store_name: str, size_bytes: int) -> bytes:
        """Generate synthetic record data for a store"""
        # Create realistic-looking data based on store type
        if "message" in store_name.lower():
            return self._generate_message_data(size_bytes)
        elif "cache" in store_name.lower():
            return self._generate_cache_data(size_bytes)
        elif "history" in store_name.lower():
            return self._generate_history_data(size_bytes)
        else:
            return self._generate_generic_data(size_bytes)
    
    def _generate_message_data(self, size_bytes: int) -> bytes:
        """Generate message-like data"""
        words = ["hello", "thanks", "see", "you", "later", "ok", "great", "yes", "no", "maybe"]
        messages = []
        current_size = 0
        
        while current_size < size_bytes:
            msg = {
                "id": hashlib.md5(str(self._rng.random()).encode()).hexdigest()[:16],
                "text": " ".join(self._rng.choices(words, k=self._rng.randint(3, 15))),
                "ts": int(time.time() - self._rng.randint(0, 86400 * 30)),
            }
            data = json.dumps(msg).encode()
            messages.append(data)
            current_size += len(data)
        
        return b"\n".join(messages)
    
    def _generate_cache_data(self, size_bytes: int) -> bytes:
        """Generate cache-like data (compressed placeholder content)"""
        # Simulate compressed cached resources
        placeholder = b"CACHED_RESOURCE_" * (size_bytes // 16)
        return zlib.compress(placeholder[:size_bytes])
    
    def _generate_history_data(self, size_bytes: int) -> bytes:
        """Generate browsing history data"""
        entries = []
        current_size = 0
        
        domains = ["google.com", "youtube.com", "amazon.com", "facebook.com", "twitter.com"]
        
        while current_size < size_bytes:
            entry = {
                "url": f"https://{self._rng.choice(domains)}/{hashlib.md5(str(self._rng.random()).encode()).hexdigest()[:8]}",
                "title": f"Page {self._rng.randint(1000, 9999)}",
                "visited": int(time.time() - self._rng.randint(0, 86400 * 90)),
                "count": self._rng.randint(1, 50),
            }
            data = json.dumps(entry).encode()
            entries.append(data)
            current_size += len(data)
        
        return b"\n".join(entries)
    
    def _generate_generic_data(self, size_bytes: int) -> bytes:
        """Generate generic key-value data"""
        data = {}
        current_size = 0
        
        while current_size < size_bytes:
            key = f"key_{self._rng.randint(1, 99999)}"
            value = hashlib.sha256(str(self._rng.random()).encode()).hexdigest()
            data[key] = value
            current_size = len(json.dumps(data))
        
        return json.dumps(data).encode()
    
    def _select_apps_for_persona(self, persona: StoragePersona) -> List[str]:
        """Select which apps this persona would have"""
        weights = PERSONA_APP_WEIGHTS.get(persona, PERSONA_APP_WEIGHTS[StoragePersona.CASUAL_USER])
        
        selected = []
        for app, probability in weights.items():
            if self._rng.random() < probability:
                selected.append(app)
        
        return selected
    
    def synthesize_profile(
        self,
        persona: StoragePersona,
        age_days: int = 90,
        size_multiplier: float = 1.0,
    ) -> LSNGProfile:
        """
        Synthesize a complete LSNG profile for a persona.
        
        Creates IndexedDB shards matching realistic usage patterns.
        """
        apps = self._select_apps_for_persona(persona)
        shards = []
        total_size = 0
        
        for app_name in apps:
            schema = WEB_APP_SCHEMAS.get(app_name)
            if not schema:
                continue
            
            origin = schema["origin"]
            base_size_kb = schema["typical_size_kb"] * size_multiplier
            
            # Add some randomness to size
            actual_size_kb = base_size_kb * (0.5 + self._rng.random())
            
            for db_info in schema["databases"]:
                db_name = db_info["name"]
                
                # Version increases over time
                version = self._rng.randint(1, 5)
                
                # Creation timestamp
                created = self._generate_age_timestamp(age_days, jitter_days=age_days // 2)
                
                # Last modified is more recent
                modified = created + self._rng.randint(0, int(time.time() - created))
                
                for store_name in db_info["stores"]:
                    records = int(db_info["avg_records"] * (0.3 + self._rng.random() * 1.4))
                    store_size = int(actual_size_kb * 1024 / len(db_info["stores"]))
                    
                    shard = StorageShard(
                        origin=origin,
                        database_name=db_name,
                        store_name=store_name,
                        records=records,
                        size_bytes=store_size,
                        created_at=created,
                        last_modified=modified,
                        version=version,
                        schema_hash=hashlib.md5(f"{origin}_{db_name}_{store_name}_{version}".encode()).hexdigest()[:16],
                    )
                    shards.append(shard)
                    total_size += store_size
        
        with self._lock:
            self._shards = shards
        
        return LSNGProfile(
            persona=persona,
            shards=shards,
            total_origins=len(set(s.origin for s in shards)),
            total_size_mb=round(total_size / (1024 * 1024), 2),
            age_days=age_days,
        )
    
    def export_to_sqlite(self, profile: LSNGProfile, output_dir: Path) -> Dict[str, Path]:
        """
        Export LSNG profile to SQLite databases (Firefox/Chrome IndexedDB format).
        
        Returns mapping of origin -> database file path.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported = {}
        
        # Group shards by origin
        by_origin: Dict[str, List[StorageShard]] = {}
        for shard in profile.shards:
            if shard.origin not in by_origin:
                by_origin[shard.origin] = []
            by_origin[shard.origin].append(shard)
        
        for origin, shards in by_origin.items():
            # Create origin-specific database file
            origin_hash = hashlib.md5(origin.encode()).hexdigest()[:16]
            db_path = output_dir / f"indexeddb_{origin_hash}.sqlite"
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create tables mimicking IndexedDB structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS database_info (
                    id INTEGER PRIMARY KEY,
                    origin TEXT,
                    name TEXT,
                    version INTEGER,
                    created_at REAL,
                    last_modified REAL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS object_stores (
                    id INTEGER PRIMARY KEY,
                    database_id INTEGER,
                    name TEXT,
                    key_path TEXT,
                    auto_increment INTEGER
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY,
                    store_id INTEGER,
                    key BLOB,
                    value BLOB
                )
            """)
            
            # Group by database within origin
            by_db: Dict[str, List[StorageShard]] = {}
            for shard in shards:
                if shard.database_name not in by_db:
                    by_db[shard.database_name] = []
                by_db[shard.database_name].append(shard)
            
            for db_name, db_shards in by_db.items():
                sample_shard = db_shards[0]
                
                cursor.execute("""
                    INSERT INTO database_info (origin, name, version, created_at, last_modified)
                    VALUES (?, ?, ?, ?, ?)
                """, (origin, db_name, sample_shard.version, sample_shard.created_at, sample_shard.last_modified))
                
                db_id = cursor.lastrowid
                
                for shard in db_shards:
                    cursor.execute("""
                        INSERT INTO object_stores (database_id, name, key_path, auto_increment)
                        VALUES (?, ?, ?, ?)
                    """, (db_id, shard.store_name, "id", 1))
                    
                    store_id = cursor.lastrowid
                    
                    # Generate synthetic records
                    record_data = self._generate_record_data(shard.store_name, shard.size_bytes)
                    
                    # Split into individual records
                    chunk_size = max(100, shard.size_bytes // shard.records)
                    for i in range(shard.records):
                        key = struct.pack(">Q", i + 1)
                        start = i * chunk_size
                        value = record_data[start:start + chunk_size] if start < len(record_data) else b""
                        
                        cursor.execute("""
                            INSERT INTO records (store_id, key, value)
                            VALUES (?, ?, ?)
                        """, (store_id, key, value))
            
            conn.commit()
            conn.close()
            
            exported[origin] = db_path
        
        return exported
    
    def inject_timing_noise(self, profile: LSNGProfile) -> Dict[str, float]:
        """
        Generate timing characteristics to defeat latency-based detection.
        
        Returns expected access latencies per origin.
        """
        timing = {}
        
        for shard in profile.shards:
            origin = shard.origin
            
            if origin not in timing:
                timing[origin] = 0.0
            
            # Base latency increases with size
            base_ms = 0.5 + (shard.size_bytes / 1024 / 1024) * 2.0
            
            # Add jitter
            jitter = self._rng.uniform(-0.3, 0.3) * base_ms
            
            timing[origin] = max(0.1, timing[origin] + base_ms + jitter)
        
        return timing
    
    def get_quota_profile(self, profile: LSNGProfile) -> Dict:
        """Get storage quota profile matching persona"""
        # Real Chrome quota is ~60% of available disk
        # Personas have different usage patterns
        
        usage_ratios = {
            StoragePersona.CASUAL_USER: 0.02,     # 2% of quota
            StoragePersona.POWER_USER: 0.08,      # 8% of quota
            StoragePersona.DEVELOPER: 0.15,       # 15% of quota
            StoragePersona.BUSINESS: 0.05,        # 5% of quota
            StoragePersona.GAMER: 0.10,           # 10% of quota
            StoragePersona.TRADER: 0.06,          # 6% of quota
        }
        
        ratio = usage_ratios.get(profile.persona, 0.05)
        
        # Simulate 100GB available
        available_bytes = 100 * 1024 * 1024 * 1024
        quota_bytes = int(available_bytes * 0.6)
        usage_bytes = int(profile.total_size_mb * 1024 * 1024)
        
        return {
            "quota_bytes": quota_bytes,
            "usage_bytes": usage_bytes,
            "usage_ratio": round(usage_bytes / quota_bytes * 100, 4),
            "expected_ratio": round(ratio * 100, 2),
            "persona": profile.persona.value,
        }


class LocalStorageSynthesizer:
    """Synthesize realistic localStorage entries"""
    
    def __init__(self, profile_uuid: str, seed: Optional[int] = None):
        self.profile_uuid = profile_uuid
        self._rng = random.Random(seed or hash(profile_uuid))
    
    def generate(self, origins: List[str]) -> Dict[str, Dict[str, str]]:
        """Generate localStorage entries for origins"""
        result = {}
        
        for origin in origins:
            entries = {}
            
            # Common localStorage keys
            common_keys = [
                ("theme", ["light", "dark", "auto"]),
                ("language", ["en", "en-US", "en-GB"]),
                ("consent", ["true", "false", "accepted"]),
                ("__cf_bm", [self._generate_token()]),
                ("_ga", [f"GA1.2.{self._rng.randint(100000, 999999)}.{int(time.time()) - self._rng.randint(0, 86400*90)}"]),
                ("_gid", [f"GA1.2.{self._rng.randint(100000, 999999)}.{int(time.time()) - self._rng.randint(0, 86400)}"]),
            ]
            
            for key, values in common_keys:
                if self._rng.random() < 0.7:  # 70% chance for each key
                    entries[key] = self._rng.choice(values)
            
            # Add random site-specific entries
            for i in range(self._rng.randint(3, 15)):
                key = f"pref_{self._rng.randint(1, 9999)}"
                entries[key] = self._generate_token(self._rng.randint(16, 128))
            
            result[origin] = entries
        
        return result
    
    def _generate_token(self, length: int = 32) -> str:
        """Generate a random token"""
        chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(self._rng.choice(chars) for _ in range(length))


class StorageTimingNormalizer:
    """
    Normalizes storage access timing to prevent empty-database detection.
    
    Injects artificial latency to match populated-database behavior.
    """
    
    def __init__(self):
        self._baseline_latency_ms = 0.5
        self._lock = threading.Lock()
    
    def get_latency_for_size(self, size_bytes: int) -> float:
        """Calculate expected latency for storage size"""
        # Empty databases have ~0.1ms latency
        # Populated databases scale with size
        
        if size_bytes < 1024:
            return 0.1
        
        # Logarithmic scaling
        import math
        return self._baseline_latency_ms + math.log10(size_bytes / 1024) * 0.5
    
    def inject_latency(self, expected_size_bytes: int) -> None:
        """Inject latency to match expected database size behavior"""
        latency = self.get_latency_for_size(expected_size_bytes)
        time.sleep(latency / 1000.0)


# ═══════════════════════════════════════════════════════════════════════════════
# V7.5 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_indexeddb_synthesizer: Optional[IndexedDBShardSynthesizer] = None
_localstorage_synthesizer: Optional[LocalStorageSynthesizer] = None
_timing_normalizer: Optional[StorageTimingNormalizer] = None


def get_indexeddb_synthesizer(profile_uuid: str = "") -> IndexedDBShardSynthesizer:
    """Get IndexedDB shard synthesizer"""
    global _indexeddb_synthesizer
    if _indexeddb_synthesizer is None or profile_uuid:
        _indexeddb_synthesizer = IndexedDBShardSynthesizer(profile_uuid or "default")
    return _indexeddb_synthesizer


def get_localstorage_synthesizer(profile_uuid: str = "") -> LocalStorageSynthesizer:
    """Get localStorage synthesizer"""
    global _localstorage_synthesizer
    if _localstorage_synthesizer is None or profile_uuid:
        _localstorage_synthesizer = LocalStorageSynthesizer(profile_uuid or "default")
    return _localstorage_synthesizer


def get_timing_normalizer() -> StorageTimingNormalizer:
    """Get timing normalizer"""
    global _timing_normalizer
    if _timing_normalizer is None:
        _timing_normalizer = StorageTimingNormalizer()
    return _timing_normalizer


def synthesize_storage_profile(
    profile_uuid: str,
    persona: str = "casual",
    age_days: int = 90,
) -> Dict:
    """Convenience function: synthesize complete storage profile"""
    synthesizer = get_indexeddb_synthesizer(profile_uuid)
    
    try:
        persona_enum = StoragePersona(persona)
    except ValueError:
        persona_enum = StoragePersona.CASUAL_USER
    
    profile = synthesizer.synthesize_profile(persona_enum, age_days)
    
    return {
        "persona": profile.persona.value,
        "total_origins": profile.total_origins,
        "total_shards": len(profile.shards),
        "total_size_mb": profile.total_size_mb,
        "age_days": profile.age_days,
        "origins": list(set(s.origin for s in profile.shards)),
        "timing_profile": synthesizer.inject_timing_noise(profile),
        "quota_profile": synthesizer.get_quota_profile(profile),
    }


if __name__ == "__main__":
    print("TITAN V7.5 IndexedDB Sharding Synthesis (LSNG)")
    print("=" * 50)
    
    synthesizer = IndexedDBShardSynthesizer("test_profile")
    
    # Generate profiles for different personas
    for persona in StoragePersona:
        profile = synthesizer.synthesize_profile(persona, age_days=90)
        print(f"\n{persona.value.upper()}:")
        print(f"  Origins: {profile.total_origins}")
        print(f"  Shards: {len(profile.shards)}")
        print(f"  Size: {profile.total_size_mb:.2f} MB")
        print(f"  Quota: {synthesizer.get_quota_profile(profile)['usage_ratio']:.4f}%")
