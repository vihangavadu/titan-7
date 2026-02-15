# LUCID EMPIRE :: PROFILE STORE
# Factory pattern for deterministic, hardware-consistent identity generation

import json
import os
import uuid
import time
import shutil
from hashlib import sha256

class ProfileFactory:
    """Generates hardware-consistent profiles using deterministic factory pattern."""
    
    def __init__(self, seed=None, golden_template_path="./assets/templates/golden_template.json"):
        self.seed = seed or str(uuid.uuid4())
        self.golden_template_path = golden_template_path
        self.profile_db = "./lucid_profiles.json"
        self._load_database()
    
    def create(self, identifier=None):
        """Create a new profile deterministically from seed."""
        identifier = identifier or self.seed
        
        # Deterministic hash-based generation
        profile_hash = sha256(f"{identifier}{self.seed}".encode()).hexdigest()
        
        profile = {
            "id": identifier,
            "seed": self.seed,
            "hash": profile_hash[:16],
            "created_at": time.time(),
            "hardware": self._generate_hardware_fingerprint(profile_hash),
            "network": self._generate_network_fingerprint(profile_hash),
        }
        
        # Validate hardware consistency
        if not self._validate_hardware_consistency(profile):
            raise ValueError(f"Hardware consistency check failed for {identifier}")
        
        return profile
    
    def _generate_hardware_fingerprint(self, seed_hash):
        """Generate hardware fingerprint deterministically."""
        # Convert hex to integers for deterministic values
        n1 = int(seed_hash[:8], 16)
        n2 = int(seed_hash[8:16], 16)
        n3 = int(seed_hash[16:24], 16)
        n4 = int(seed_hash[24:32], 16)
        
        return {
            "cpu_cores": (n1 % 8) + 4,  # 4-12 cores
            "memory_gb": ((n2 % 64) // 8 + 1) * 8,  # 8, 16, 32, 64 GB
            "gpu": f"GPU_{n3 % 100}",
            "screen_res": f"{1920 + (n4 % 960)}x{1080 + (n4 % 540)}",
        }
    
    def _generate_network_fingerprint(self, seed_hash):
        """Generate network fingerprint deterministically."""
        octets = [int(seed_hash[i:i+2], 16) % 256 for i in range(0, 8, 2)]
        return {"ipv4_octet_base": octets,}
    
    def _validate_hardware_consistency(self, profile):
        """Validate that hardware fingerprint is consistent across calls."""
        # Regenerate from same seed and compare
        regenerated = self.create(profile["id"])
        return regenerated["hardware"] == profile["hardware"]
    
    def _load_database(self):
        """Load profile database from disk."""
        if os.path.exists(self.profile_db):
            with open(self.profile_db, 'r') as f:
                self.database = json.load(f)
        else:
            self.database = {}
    
    def save_profile(self, profile):
        """Save profile to database."""
        self.database[profile["id"]] = profile
        with open(self.profile_db, 'w') as f:
            json.dump(self.database, f, indent=2)

class ProfileStore:
    """Manages profile lifecycle and access."""
    
    def __init__(self, store_dir="./lucid_profile_data"):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
    
    def create_profile_directory(self, profile_id):
        """Create profile directory structure."""
        profile_path = os.path.join(self.store_dir, profile_id)
        os.makedirs(profile_path, exist_ok=True)
        return profile_path
    
    def list_profiles(self):
        """List all stored profiles."""
        return [d for d in os.listdir(self.store_dir) if os.path.isdir(os.path.join(self.store_dir, d))]
    
    def delete_profile(self, profile_id):
        """Delete a profile and its directory."""
        profile_path = os.path.join(self.store_dir, profile_id)
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path)
