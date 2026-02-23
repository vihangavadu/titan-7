"""
LevelDB writer helper.
Writes a simple key-value snapshot into the profile's Local Storage leveldb
folder. Tries to use `plyvel` (if available) to write actual LevelDB records; otherwise
falls back to writing `local_storage_simulated.json` and `.txt`.
"""
import os
import json


def write_local_storage(leveldb_dir, data):
    """Attempt to write `data` dict into LevelDB located at `leveldb_dir`.
    Returns True on success, False otherwise.
    """
    # Try plyvel first
    try:
        import plyvel
    except Exception:
        plyvel = None

    if plyvel:
        try:
            db = plyvel.DB(leveldb_dir, create_if_missing=True)
            # For simplicity, write keys as plain bytes prefixed with 'ls:' to avoid colliding
            # with other keys that Chrome might expect. Real Chrome uses a complex encoding.
            with db.write_batch() as b:
                for k, v in data.items():
                    key = f"ls:{k}".encode('utf-8')
                    b.put(key, v.encode('utf-8'))
            db.close()
            return True
        except Exception:
            # fall back to simple snapshot
            pass

    # Fallback: write JSON + text snapshot for deterministic tests
    try:
        os.makedirs(leveldb_dir, exist_ok=True)
        snap = os.path.join(leveldb_dir, 'local_storage_simulated.json')
        with open(snap, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        txt = os.path.join(leveldb_dir, 'local_storage_simulated.txt')
        with open(txt, 'w', encoding='utf-8') as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")
        return True
    except Exception:
        return False
