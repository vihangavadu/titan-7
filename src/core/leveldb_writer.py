"""
TITAN V8.11 — LevelDB Writer
Writes key-value data into Chrome/Chromium Local Storage LevelDB databases.
Supports real plyvel-based writes and JSON fallback for testing environments.

Used by:
  - genesis_core.py (profile forge localStorage injection)
  - chromium_commerce_injector.py (commerce trust anchor injection)
  - oblivion_forge.py (Chrome profile localStorage population)
  - form_autofill_injector.py (pre-fill localStorage data)
"""
import os
import json
import struct
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("TITAN-LEVELDB")

try:
    import plyvel
    PLYVEL_OK = True
except ImportError:
    plyvel = None
    PLYVEL_OK = False


class LevelDBWriter:
    """
    Writes key-value data into Chrome Local Storage LevelDB format.
    
    Chrome stores localStorage in LevelDB at:
      <profile>/Local Storage/leveldb/
    
    Keys are encoded as: META:<origin> or _<origin>\\x00<key>
    Values are stored as UTF-16LE encoded strings.
    """
    
    def __init__(self, leveldb_dir: str, create: bool = True):
        self.leveldb_dir = Path(leveldb_dir)
        self.create = create
        self._db = None
        self._write_count = 0
        
        if create:
            self.leveldb_dir.mkdir(parents=True, exist_ok=True)
    
    def open(self) -> bool:
        """Open the LevelDB database."""
        if not PLYVEL_OK:
            logger.warning("plyvel not available — using JSON fallback")
            return True
        try:
            self._db = plyvel.DB(str(self.leveldb_dir), create_if_missing=self.create)
            return True
        except Exception as e:
            logger.error(f"LevelDB open error: {e}")
            return False
    
    def close(self):
        """Close the LevelDB database."""
        if self._db:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None
    
    def write_origin_data(self, origin: str, data: Dict[str, str]) -> bool:
        """
        Write localStorage data for a specific origin.
        
        Args:
            origin: The origin URL (e.g., 'https://www.amazon.com')
            data: Dict of key-value pairs to write
            
        Returns:
            True on success
        """
        if self._db and PLYVEL_OK:
            return self._write_plyvel(origin, data)
        else:
            return self._write_fallback(origin, data)
    
    def _write_plyvel(self, origin: str, data: Dict[str, str]) -> bool:
        """Write using real LevelDB via plyvel."""
        try:
            with self._db.write_batch() as batch:
                # Write META key for origin
                meta_key = f"META:{origin}".encode('utf-8')
                meta_val = struct.pack('<I', len(data))
                batch.put(meta_key, meta_val)
                
                # Write each key-value pair
                for key, value in data.items():
                    # Chrome key format: _<origin>\x00<key>
                    ls_key = f"_{origin}\x00{key}".encode('utf-8')
                    # Chrome stores values as UTF-16LE
                    ls_val = b'\x01' + value.encode('utf-16-le')
                    batch.put(ls_key, ls_val)
                    self._write_count += 1
            
            return True
        except Exception as e:
            logger.error(f"plyvel write error: {e}")
            return self._write_fallback(origin, data)
    
    def _write_fallback(self, origin: str, data: Dict[str, str]) -> bool:
        """Fallback: write JSON snapshot when plyvel is unavailable."""
        try:
            self.leveldb_dir.mkdir(parents=True, exist_ok=True)
            
            # Load existing data if present
            snap_path = self.leveldb_dir / 'local_storage_simulated.json'
            existing = {}
            if snap_path.exists():
                try:
                    existing = json.loads(snap_path.read_text(encoding='utf-8'))
                except Exception:
                    pass
            
            # Merge new data under origin key
            if origin not in existing:
                existing[origin] = {}
            existing[origin].update(data)
            
            # Write JSON
            snap_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            # Write text format for debugging
            txt_path = self.leveldb_dir / 'local_storage_simulated.txt'
            with open(txt_path, 'a', encoding='utf-8') as f:
                for k, v in data.items():
                    f.write(f"{origin}|{k}={v}\n")
            
            self._write_count += len(data)
            return True
        except Exception as e:
            logger.error(f"Fallback write error: {e}")
            return False
    
    def write_commerce_anchors(self, origin: str, platform: str = "generic") -> bool:
        """
        Write platform-specific commerce trust anchors to localStorage.
        These simulate a returning customer with purchase history.
        """
        anchors = {
            "shopify": {
                "cart_ts": str(int(time.time() * 1000)),
                "checkout_step": "contact_information",
                "shopify_pay_redirect": "pending",
                "_tracking_consent": '{"con":{"CMP":{"a":"","m":"","p":"","s":""}}}',
            },
            "stripe": {
                "__stripe_mid": hashlib.md5(os.urandom(16)).hexdigest(),
                "__stripe_sid": hashlib.md5(os.urandom(16)).hexdigest(),
            },
            "amazon": {
                "csm-hit": f"tb:{hashlib.md5(os.urandom(8)).hexdigest()[:20]}+s-{hashlib.md5(os.urandom(8)).hexdigest()[:20]}",
                "session-id": f"{int(time.time())}-{os.urandom(4).hex()}",
            },
            "generic": {
                "user_session": hashlib.sha256(os.urandom(32)).hexdigest()[:32],
                "returning_visitor": "true",
                "visit_count": str(3 + (hash(origin) % 12)),
            },
        }
        
        data = anchors.get(platform, anchors["generic"])
        return self.write_origin_data(origin, data)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Return write statistics."""
        return {
            "leveldb_dir": str(self.leveldb_dir),
            "plyvel_available": PLYVEL_OK,
            "write_count": self._write_count,
            "using_fallback": not PLYVEL_OK or self._db is None,
        }
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()


def write_local_storage(leveldb_dir: str, data: Dict[str, str]) -> bool:
    """
    Legacy function interface — write data dict into LevelDB.
    Returns True on success, False otherwise.
    """
    writer = LevelDBWriter(leveldb_dir)
    writer.open()
    try:
        return writer.write_origin_data("https://localhost", data)
    finally:
        writer.close()
