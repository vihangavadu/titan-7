"""
TITAN V7.0 SINGULARITY — Immutable OS Manager & A/B Partition Controller
Implements read-only root with OverlayFS and atomic A/B partition updates

V7 Architecture: The Debian Live foundation is hardened into a pseudo-immutable
system where the core filesystem (SquashFS) is mounted read-only. All runtime
writes are directed to a temporary tmpfs overlay using OverlayFS. Changes are
discarded on reboot, returning the system to its pristine, verified state.

Architecture:
    immutable_os.py         → userspace A/B partition manager + integrity checker
    095-os-harden.hook.chroot → build-time OverlayFS configuration
    build_iso.sh            → A/B partition scheme in ISO layout

Detection Vectors Neutralized:
    - Configuration drift (unique system state as fingerprint)
    - Persistence vulnerabilities (malware surviving reboot)
    - Forensic residue (operation traces on disk)
    - State corruption (accumulated "drift" from previous ops)
"""

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "7.0.0"
__author__ = "Dva.12"


class PartitionSlot(Enum):
    """A/B partition slot identifiers."""
    SLOT_A = "a"
    SLOT_B = "b"


class BootState(Enum):
    """System boot state."""
    PRISTINE = "pristine"       # Fresh boot, no modifications
    OPERATIONAL = "operational"  # During operation, overlay active
    UPDATING = "updating"       # A/B update in progress
    ROLLBACK = "rollback"       # Rolled back to previous slot
    CORRUPTED = "corrupted"     # Integrity check failed


class OverlayState(Enum):
    """OverlayFS state."""
    MOUNTED = "mounted"
    UNMOUNTED = "unmounted"
    ERROR = "error"


@dataclass
class PartitionInfo:
    """Information about a partition slot."""
    slot: PartitionSlot
    device: str                    # e.g., /dev/sda2 or /dev/sda3
    mount_point: str
    squashfs_hash: str = ""        # SHA-256 of SquashFS image
    version: str = ""              # TITAN version string
    boot_count: int = 0
    last_boot: str = ""
    status: str = "active"         # active, standby, failed
    verified: bool = False


@dataclass
class ImmutableConfig:
    """Immutable OS configuration."""
    overlay_tmpfs_size: str = "4G"          # tmpfs size for OverlayFS upper
    persistent_dirs: List[str] = field(default_factory=lambda: [
        "/opt/titan/state",                  # Runtime state (profiles, certs)
        "/opt/titan/config",                 # Operator configuration
        "/home/user",                        # User home (encrypted)
    ])
    ephemeral_dirs: List[str] = field(default_factory=lambda: [
        "/tmp", "/var/tmp", "/var/log",
        "/var/cache", "/var/run",
    ])
    integrity_check_on_boot: bool = True
    auto_rollback_on_failure: bool = True
    update_server_url: str = ""
    update_check_interval: int = 3600       # seconds


class ImmutableOSManager:
    """
    Immutable OS Manager — controls OverlayFS, A/B partitions, and
    cryptographic integrity verification.

    Boot Sequence:
        1. GRUB loads kernel + initramfs
        2. SquashFS root is mounted read-only
        3. OverlayFS mounts tmpfs as upper layer
        4. Persistent encrypted partition mounted for /opt/titan/state
        5. Integrity check verifies SquashFS hash
        6. System reports PRISTINE state

    Usage:
        manager = ImmutableOSManager()
        status = manager.get_system_status()
        if manager.verify_integrity():
            print("System integrity: VERIFIED")
    """

    SLOT_CONFIG_PATH = "/opt/titan/state/partition_config.json"
    INTEGRITY_HASH_PATH = "/opt/titan/state/squashfs_hashes.json"

    def __init__(self, config: Optional[ImmutableConfig] = None):
        self._config = config or ImmutableConfig()
        self._boot_state = BootState.PRISTINE
        self._overlay_state = OverlayState.UNMOUNTED
        self._active_slot: Optional[PartitionSlot] = None
        self._partitions: Dict[PartitionSlot, PartitionInfo] = {}

    def _detect_active_slot(self) -> Optional[PartitionSlot]:
        """Detect which A/B slot is currently booted."""
        try:
            # Check kernel command line for slot indicator
            with open("/proc/cmdline", "r") as f:
                cmdline = f.read()
            if "titan_slot=b" in cmdline:
                return PartitionSlot.SLOT_B
            return PartitionSlot.SLOT_A
        except (FileNotFoundError, PermissionError):
            return PartitionSlot.SLOT_A

    def _check_overlay_status(self) -> OverlayState:
        """Check if OverlayFS is currently mounted."""
        try:
            with open("/proc/mounts", "r") as f:
                mounts = f.read()
            if "overlay" in mounts and "upperdir" in mounts:
                return OverlayState.MOUNTED
            return OverlayState.UNMOUNTED
        except (FileNotFoundError, PermissionError):
            return OverlayState.ERROR

    def _hash_file(self, filepath: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (FileNotFoundError, PermissionError):
            return ""

    def initialize(self) -> bool:
        """
        Initialize the immutable OS manager.
        Detects current slot, checks overlay, and loads partition config.
        """
        self._active_slot = self._detect_active_slot()
        self._overlay_state = self._check_overlay_status()

        # Load partition config if exists
        if os.path.isfile(self.SLOT_CONFIG_PATH):
            try:
                with open(self.SLOT_CONFIG_PATH, "r") as f:
                    data = json.load(f)
                for slot_data in data.get("partitions", []):
                    slot = PartitionSlot(slot_data["slot"])
                    self._partitions[slot] = PartitionInfo(
                        slot=slot,
                        device=slot_data.get("device", ""),
                        mount_point=slot_data.get("mount_point", ""),
                        squashfs_hash=slot_data.get("squashfs_hash", ""),
                        version=slot_data.get("version", ""),
                        boot_count=slot_data.get("boot_count", 0),
                        last_boot=slot_data.get("last_boot", ""),
                        status=slot_data.get("status", "active"),
                        verified=slot_data.get("verified", False),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        if self._overlay_state == OverlayState.MOUNTED:
            self._boot_state = BootState.PRISTINE
        else:
            self._boot_state = BootState.OPERATIONAL

        return True

    def verify_integrity(self) -> Dict:
        """
        Verify system integrity by checking SquashFS hashes against
        known-good values stored at build time.

        Returns a dict with verification results.
        """
        results = {
            "status": "PASS",
            "checks": {},
            "active_slot": self._active_slot.value if self._active_slot else "unknown",
        }

        # Check SquashFS image integrity
        squashfs_paths = [
            "/lib/live/mount/medium/live/filesystem.squashfs",
            "/run/live/medium/live/filesystem.squashfs",
        ]

        for path in squashfs_paths:
            if os.path.exists(path):
                current_hash = self._hash_file(path)
                results["checks"]["squashfs_hash"] = current_hash

                # Compare against stored hash
                if os.path.isfile(self.INTEGRITY_HASH_PATH):
                    try:
                        with open(self.INTEGRITY_HASH_PATH, "r") as f:
                            known_hashes = json.load(f)
                        expected = known_hashes.get("squashfs", "")
                        if expected and current_hash != expected:
                            results["status"] = "FAIL"
                            results["checks"]["hash_match"] = False
                        else:
                            results["checks"]["hash_match"] = True
                    except (json.JSONDecodeError, KeyError):
                        results["checks"]["hash_match"] = "unknown"
                break

        # Check overlay is properly mounted (ephemeral writes only)
        results["checks"]["overlay_active"] = (
            self._overlay_state == OverlayState.MOUNTED
        )

        # Check that root is read-only
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] == "/":
                        results["checks"]["root_readonly"] = "ro" in parts[3].split(",")
                        break
        except (FileNotFoundError, PermissionError):
            results["checks"]["root_readonly"] = "unknown"

        # Check persistent dirs exist and are writable
        for pdir in self._config.persistent_dirs:
            if os.path.isdir(pdir):
                results["checks"][f"persistent_{pdir}"] = os.access(pdir, os.W_OK)

        if not all(
            v for k, v in results["checks"].items()
            if isinstance(v, bool)
        ):
            results["status"] = "FAIL"

        return results

    def prepare_update(self, update_image_path: str) -> Dict:
        """
        Prepare an A/B partition update.
        Stages the update to the inactive slot without affecting the running system.
        """
        if not self._active_slot:
            return {"status": "error", "message": "Active slot not detected"}

        # Determine standby slot
        standby = (
            PartitionSlot.SLOT_B
            if self._active_slot == PartitionSlot.SLOT_A
            else PartitionSlot.SLOT_A
        )

        self._boot_state = BootState.UPDATING

        result = {
            "status": "staged",
            "active_slot": self._active_slot.value,
            "target_slot": standby.value,
            "update_image": update_image_path,
            "image_hash": self._hash_file(update_image_path),
        }

        return result

    def apply_update(self, target_slot: PartitionSlot) -> bool:
        """
        Apply staged update by switching the bootloader to target slot.
        The actual switch happens on next reboot.
        """
        try:
            # Update GRUB default to boot from target slot
            slot_flag = f"titan_slot={target_slot.value}"
            grub_default = f"/etc/default/grub.d/titan-slot.cfg"

            os.makedirs(os.path.dirname(grub_default), exist_ok=True)
            with open(grub_default, "w") as f:
                f.write(f'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {slot_flag}"\n')

            subprocess.run(["update-grub"], capture_output=True, timeout=30)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError, PermissionError):
            return False

    def rollback(self) -> bool:
        """
        Rollback to the previous partition slot.
        Used when a boot from the new slot fails verification.
        """
        if not self._active_slot:
            return False

        previous = (
            PartitionSlot.SLOT_A
            if self._active_slot == PartitionSlot.SLOT_B
            else PartitionSlot.SLOT_B
        )

        self._boot_state = BootState.ROLLBACK
        return self.apply_update(previous)

    def wipe_ephemeral(self, secure: bool = True) -> bool:
        """
        Wipe all ephemeral data from the OverlayFS upper layer.
        Equivalent to a "soft reboot" — clears all session artifacts.
        
        Args:
            secure: If True, overwrite files before deletion to prevent forensic recovery
        """
        try:
            for edir in self._config.ephemeral_dirs:
                if os.path.isdir(edir):
                    for item in os.listdir(edir):
                        item_path = os.path.join(edir, item)
                        try:
                            if os.path.isdir(item_path):
                                if secure:
                                    self._secure_rmtree(item_path)
                                else:
                                    shutil.rmtree(item_path)
                            else:
                                if secure:
                                    self._secure_delete(item_path)
                                else:
                                    os.remove(item_path)
                        except (PermissionError, OSError):
                            continue
            return True
        except Exception:
            return False

    @staticmethod
    def _secure_delete(filepath: str) -> None:
        """Overwrite file with random data before deletion to prevent forensic recovery."""
        try:
            size = os.path.getsize(filepath)
            with open(filepath, 'wb') as f:
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
            os.remove(filepath)
        except (OSError, PermissionError):
            try:
                os.remove(filepath)
            except OSError:
                pass

    @staticmethod
    def _secure_rmtree(dirpath: str) -> None:
        """Securely wipe directory tree — overwrite all files before removal."""
        for root, dirs, files in os.walk(dirpath, topdown=False):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    with open(fpath, 'wb') as f:
                        f.write(os.urandom(min(size, 1024 * 1024)))
                        f.flush()
                        os.fsync(f.fileno())
                    os.remove(fpath)
                except (OSError, PermissionError):
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
            for dname in dirs:
                try:
                    os.rmdir(os.path.join(root, dname))
                except OSError:
                    pass
        try:
            os.rmdir(dirpath)
        except OSError:
            pass

    def get_system_status(self) -> Dict:
        """Get comprehensive immutable OS status."""
        return {
            "boot_state": self._boot_state.value,
            "overlay_state": self._overlay_state.value,
            "active_slot": self._active_slot.value if self._active_slot else "unknown",
            "partitions": {
                slot.value: {
                    "device": info.device,
                    "version": info.version,
                    "status": info.status,
                    "verified": info.verified,
                    "boot_count": info.boot_count,
                }
                for slot, info in self._partitions.items()
            },
            "config": {
                "overlay_size": self._config.overlay_tmpfs_size,
                "persistent_dirs": self._config.persistent_dirs,
                "integrity_check": self._config.integrity_check_on_boot,
                "auto_rollback": self._config.auto_rollback_on_failure,
            },
        }


def verify_system_integrity() -> Dict:
    """Convenience function: quick system integrity check."""
    manager = ImmutableOSManager()
    manager.initialize()
    return manager.verify_integrity()


def get_boot_status() -> Dict:
    """Convenience function: get current boot status."""
    manager = ImmutableOSManager()
    manager.initialize()
    return manager.get_system_status()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 INTEGRITY MONITOR — Continuous runtime integrity monitoring
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from typing import Callable, Set
from collections import defaultdict


class IntegrityViolation(Enum):
    """Types of integrity violations."""
    HASH_MISMATCH = "hash_mismatch"
    UNAUTHORIZED_WRITE = "unauthorized_write"
    OVERLAY_CORRUPTION = "overlay_corruption"
    PERSISTENT_TAMPERING = "persistent_tampering"
    BOOT_PARAMETER_CHANGE = "boot_parameter_change"


@dataclass
class IntegrityEvent:
    """An integrity violation event."""
    violation_type: IntegrityViolation
    path: str
    expected: str
    actual: str
    timestamp: float
    severity: str  # "critical", "high", "medium", "low"


class IntegrityMonitor:
    """
    V7.6 Integrity Monitor - Continuous runtime monitoring
    of system integrity with real-time alerts.
    """
    
    # Critical system paths to monitor
    CRITICAL_PATHS = [
        "/opt/titan/core",
        "/opt/titan/drivers",
        "/etc/titan",
        "/usr/local/bin/titan-*",
    ]
    
    # Allowed write paths (everything else should be read-only)
    ALLOWED_WRITE_PATHS = [
        "/opt/titan/state",
        "/opt/titan/config",
        "/home/user",
        "/tmp",
        "/var/tmp",
        "/var/log",
        "/var/cache",
    ]
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize integrity monitor.
        
        Args:
            check_interval: Seconds between integrity checks
        """
        self.check_interval = check_interval
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._events: List[IntegrityEvent] = []
        self._callbacks: List[Callable[[IntegrityEvent], None]] = []
        self._baseline_hashes: Dict[str, str] = {}
        self._last_check_time: float = 0
    
    def establish_baseline(self, paths: Optional[List[str]] = None):
        """
        Establish baseline hashes for critical files.
        
        Args:
            paths: Paths to hash (uses CRITICAL_PATHS if None)
        """
        paths = paths or self.CRITICAL_PATHS
        
        for path_pattern in paths:
            path = Path(path_pattern.replace("*", ""))
            if path.exists():
                if path.is_file():
                    self._baseline_hashes[str(path)] = self._hash_file(str(path))
                elif path.is_dir():
                    for child in path.rglob("*"):
                        if child.is_file():
                            self._baseline_hashes[str(child)] = self._hash_file(str(child))
    
    def _hash_file(self, filepath: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (FileNotFoundError, PermissionError):
            return ""
    
    def _check_overlay_integrity(self) -> List[IntegrityEvent]:
        """Check OverlayFS integrity."""
        events = []
        
        try:
            with open("/proc/mounts", "r") as f:
                mounts = f.read()
            
            if "overlay" not in mounts:
                events.append(IntegrityEvent(
                    violation_type=IntegrityViolation.OVERLAY_CORRUPTION,
                    path="/",
                    expected="overlay mounted",
                    actual="overlay not found",
                    timestamp=time.time(),
                    severity="critical"
                ))
        except Exception:
            pass
        
        return events
    
    def _check_file_integrity(self) -> List[IntegrityEvent]:
        """Check file integrity against baseline."""
        events = []
        
        for filepath, expected_hash in self._baseline_hashes.items():
            current_hash = self._hash_file(filepath)
            
            if current_hash and current_hash != expected_hash:
                events.append(IntegrityEvent(
                    violation_type=IntegrityViolation.HASH_MISMATCH,
                    path=filepath,
                    expected=expected_hash[:16] + "...",
                    actual=current_hash[:16] + "...",
                    timestamp=time.time(),
                    severity="high" if "/core/" in filepath else "medium"
                ))
        
        return events
    
    def _check_unauthorized_writes(self) -> List[IntegrityEvent]:
        """Check for unauthorized write attempts."""
        events = []
        
        # Check if overlay upper directory has unexpected writes
        overlay_upper_paths = [
            "/run/live/rootfs/overlay/upper",
            "/lib/live/mount/overlay/rw",
        ]
        
        for upper_path in overlay_upper_paths:
            if os.path.exists(upper_path):
                for item in os.listdir(upper_path):
                    full_path = os.path.join(upper_path, item)
                    # Check if this path should be writable
                    is_allowed = any(
                        full_path.replace(upper_path, "").startswith(allowed)
                        for allowed in self.ALLOWED_WRITE_PATHS
                    )
                    
                    if not is_allowed:
                        events.append(IntegrityEvent(
                            violation_type=IntegrityViolation.UNAUTHORIZED_WRITE,
                            path=full_path,
                            expected="no writes",
                            actual="unexpected write detected",
                            timestamp=time.time(),
                            severity="medium"
                        ))
        
        return events
    
    def run_check(self) -> List[IntegrityEvent]:
        """Run a complete integrity check."""
        all_events = []
        
        all_events.extend(self._check_overlay_integrity())
        all_events.extend(self._check_file_integrity())
        all_events.extend(self._check_unauthorized_writes())
        
        # Store events
        self._events.extend(all_events)
        self._last_check_time = time.time()
        
        # Trigger callbacks
        for event in all_events:
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception:
                    pass
        
        return all_events
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            self.run_check()
            time.sleep(self.check_interval)
    
    def start(self):
        """Start background monitoring."""
        if not self._running:
            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self._monitor_thread.start()
    
    def stop(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def register_callback(self, callback: Callable[[IntegrityEvent], None]):
        """Register a callback for integrity events."""
        self._callbacks.append(callback)
    
    def get_events(self, severity: Optional[str] = None) -> List[IntegrityEvent]:
        """Get recorded integrity events."""
        if severity:
            return [e for e in self._events if e.severity == severity]
        return self._events
    
    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            "running": self._running,
            "last_check": self._last_check_time,
            "baseline_files": len(self._baseline_hashes),
            "events_total": len(self._events),
            "events_critical": len([e for e in self._events if e.severity == "critical"]),
            "events_high": len([e for e in self._events if e.severity == "high"]),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 SECURE BOOT MANAGER — Secure boot chain verification
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BootChainEntry:
    """An entry in the verified boot chain."""
    component: str
    hash: str
    signature: Optional[str]
    verified: bool
    timestamp: float


class SecureBootManager:
    """
    V7.6 Secure Boot Manager - Verifies the entire boot chain
    from bootloader to kernel to initramfs to TITAN components.
    """
    
    # Boot chain components to verify
    BOOT_CHAIN = [
        {"name": "grub", "paths": ["/boot/grub/grub.cfg"]},
        {"name": "kernel", "paths": ["/boot/vmlinuz-*"]},
        {"name": "initramfs", "paths": ["/boot/initrd.img-*"]},
        {"name": "squashfs", "paths": [
            "/lib/live/mount/medium/live/filesystem.squashfs",
            "/run/live/medium/live/filesystem.squashfs"
        ]},
        {"name": "titan_core", "paths": ["/opt/titan/core/__init__.py"]},
    ]
    
    def __init__(self, signature_key_path: Optional[str] = None):
        """
        Initialize secure boot manager.
        
        Args:
            signature_key_path: Path to public key for signature verification
        """
        self.signature_key_path = signature_key_path
        self._chain_entries: List[BootChainEntry] = []
        self._verified = False
        self._known_hashes: Dict[str, str] = {}
    
    def load_known_hashes(self, hash_file: str = "/opt/titan/state/boot_hashes.json"):
        """Load known-good hashes from file."""
        try:
            with open(hash_file, "r") as f:
                self._known_hashes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._known_hashes = {}
    
    def _hash_file(self, filepath: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (FileNotFoundError, PermissionError):
            return ""
    
    def _find_matching_path(self, patterns: List[str]) -> Optional[str]:
        """Find first existing path matching patterns."""
        for pattern in patterns:
            if "*" in pattern:
                import glob
                matches = glob.glob(pattern)
                if matches:
                    return matches[0]
            elif os.path.exists(pattern):
                return pattern
        return None
    
    def verify_chain(self) -> Dict:
        """
        Verify the entire boot chain.
        
        Returns:
            Verification result with status and details
        """
        self._chain_entries = []
        all_verified = True
        
        for component in self.BOOT_CHAIN:
            name = component["name"]
            path = self._find_matching_path(component["paths"])
            
            if path:
                current_hash = self._hash_file(path)
                expected_hash = self._known_hashes.get(name, "")
                
                verified = True
                if expected_hash and current_hash != expected_hash:
                    verified = False
                    all_verified = False
                
                entry = BootChainEntry(
                    component=name,
                    hash=current_hash,
                    signature=None,  # Signature verification if available
                    verified=verified,
                    timestamp=time.time()
                )
            else:
                entry = BootChainEntry(
                    component=name,
                    hash="",
                    signature=None,
                    verified=False,
                    timestamp=time.time()
                )
                all_verified = False
            
            self._chain_entries.append(entry)
        
        self._verified = all_verified
        
        return {
            "verified": all_verified,
            "chain": [
                {
                    "component": e.component,
                    "hash": e.hash[:16] + "..." if e.hash else "missing",
                    "verified": e.verified
                }
                for e in self._chain_entries
            ]
        }
    
    def save_current_hashes(self, output_file: str = "/opt/titan/state/boot_hashes.json"):
        """Save current hashes as known-good baseline."""
        hashes = {}
        
        for component in self.BOOT_CHAIN:
            name = component["name"]
            path = self._find_matching_path(component["paths"])
            if path:
                hashes[name] = self._hash_file(path)
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(hashes, f, indent=2)
        
        self._known_hashes = hashes
    
    def get_verification_status(self) -> Dict:
        """Get current verification status."""
        return {
            "verified": self._verified,
            "components_checked": len(self._chain_entries),
            "components_verified": sum(1 for e in self._chain_entries if e.verified),
            "chain_entries": [
                {"component": e.component, "verified": e.verified}
                for e in self._chain_entries
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 ATOMIC UPDATE CONTROLLER — Atomic update with rollback protection
# ═══════════════════════════════════════════════════════════════════════════════

class UpdateState(Enum):
    """Update state machine states."""
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    STAGING = "staging"
    APPLYING = "applying"
    PENDING_REBOOT = "pending_reboot"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


@dataclass
class UpdatePackage:
    """Information about an update package."""
    version: str
    download_url: str
    size_bytes: int
    sha256: str
    changelog: str
    release_date: str
    min_version: str  # Minimum current version required


class AtomicUpdateController:
    """
    V7.6 Atomic Update Controller - Manages atomic A/B updates
    with automatic rollback protection.
    """
    
    UPDATE_STAGING_DIR = "/opt/titan/updates/staging"
    UPDATE_HISTORY_FILE = "/opt/titan/state/update_history.json"
    BOOT_ATTEMPTS_FILE = "/opt/titan/state/boot_attempts"
    MAX_BOOT_ATTEMPTS = 3
    
    def __init__(self, os_manager: Optional[ImmutableOSManager] = None):
        """
        Initialize update controller.
        
        Args:
            os_manager: ImmutableOSManager instance
        """
        self.os_manager = os_manager or ImmutableOSManager()
        self._state = UpdateState.IDLE
        self._current_package: Optional[UpdatePackage] = None
        self._progress: float = 0
        self._error: Optional[str] = None
    
    def check_for_updates(self, update_url: str) -> Optional[UpdatePackage]:
        """
        Check for available updates.
        
        Args:
            update_url: URL to check for updates
        
        Returns:
            UpdatePackage if available, None otherwise
        """
        self._state = UpdateState.CHECKING
        
        try:
            # In real implementation, fetch from update_url
            # For now, return None (no updates)
            self._state = UpdateState.IDLE
            return None
        except Exception as e:
            self._error = str(e)
            self._state = UpdateState.FAILED
            return None
    
    def download_update(self, package: UpdatePackage) -> bool:
        """
        Download an update package.
        
        Args:
            package: Update package to download
        
        Returns:
            True if download successful
        """
        self._state = UpdateState.DOWNLOADING
        self._current_package = package
        self._progress = 0
        
        try:
            os.makedirs(self.UPDATE_STAGING_DIR, exist_ok=True)
            
            # In real implementation, download from package.download_url
            # with progress tracking
            
            self._progress = 100
            return True
            
        except Exception as e:
            self._error = str(e)
            self._state = UpdateState.FAILED
            return False
    
    def verify_update(self) -> bool:
        """Verify downloaded update integrity."""
        self._state = UpdateState.VERIFYING
        
        if not self._current_package:
            self._error = "No package to verify"
            self._state = UpdateState.FAILED
            return False
        
        # Verify hash of downloaded package
        staged_path = os.path.join(
            self.UPDATE_STAGING_DIR, 
            f"titan-{self._current_package.version}.squashfs"
        )
        
        if not os.path.exists(staged_path):
            self._error = "Staged update not found"
            self._state = UpdateState.FAILED
            return False
        
        # Hash verification
        sha256 = hashlib.sha256()
        try:
            with open(staged_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            
            if sha256.hexdigest() != self._current_package.sha256:
                self._error = "Hash mismatch"
                self._state = UpdateState.FAILED
                return False
                
        except Exception as e:
            self._error = str(e)
            self._state = UpdateState.FAILED
            return False
        
        return True
    
    def stage_update(self) -> bool:
        """Stage update to inactive partition slot."""
        self._state = UpdateState.STAGING
        
        if not self._current_package:
            self._error = "No package to stage"
            self._state = UpdateState.FAILED
            return False
        
        staged_path = os.path.join(
            self.UPDATE_STAGING_DIR,
            f"titan-{self._current_package.version}.squashfs"
        )
        
        # Prepare update on inactive slot
        self.os_manager.initialize()
        result = self.os_manager.prepare_update(staged_path)
        
        if result.get("status") == "staged":
            return True
        
        self._error = result.get("message", "Staging failed")
        self._state = UpdateState.FAILED
        return False
    
    def apply_update(self) -> bool:
        """Apply staged update (takes effect on next reboot)."""
        self._state = UpdateState.APPLYING
        
        # Get target slot from staging state
        active_slot = self.os_manager._active_slot
        if not active_slot:
            self._error = "Cannot determine active slot"
            self._state = UpdateState.FAILED
            return False
        
        target_slot = (
            PartitionSlot.SLOT_B if active_slot == PartitionSlot.SLOT_A
            else PartitionSlot.SLOT_A
        )
        
        # Reset boot attempt counter for target slot
        try:
            os.makedirs(os.path.dirname(self.BOOT_ATTEMPTS_FILE), exist_ok=True)
            with open(self.BOOT_ATTEMPTS_FILE, "w") as f:
                f.write("0")
        except Exception:
            pass
        
        if self.os_manager.apply_update(target_slot):
            self._state = UpdateState.PENDING_REBOOT
            self._record_update()
            return True
        
        self._error = "Failed to apply update"
        self._state = UpdateState.FAILED
        return False
    
    def _record_update(self):
        """Record update in history."""
        history = []
        
        try:
            if os.path.exists(self.UPDATE_HISTORY_FILE):
                with open(self.UPDATE_HISTORY_FILE, "r") as f:
                    history = json.load(f)
        except Exception:
            pass
        
        if self._current_package:
            history.append({
                "version": self._current_package.version,
                "applied_at": time.time(),
                "status": "pending_reboot"
            })
        
        try:
            with open(self.UPDATE_HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass
    
    def check_boot_health(self) -> bool:
        """
        Check if current boot is healthy (call after reboot).
        If not healthy, triggers automatic rollback.
        
        Returns:
            True if boot is healthy
        """
        # Increment boot attempt counter
        attempts = 0
        try:
            if os.path.exists(self.BOOT_ATTEMPTS_FILE):
                with open(self.BOOT_ATTEMPTS_FILE, "r") as f:
                    attempts = int(f.read().strip())
        except Exception:
            pass
        
        attempts += 1
        
        try:
            with open(self.BOOT_ATTEMPTS_FILE, "w") as f:
                f.write(str(attempts))
        except Exception:
            pass
        
        if attempts > self.MAX_BOOT_ATTEMPTS:
            # Too many failed boot attempts, trigger rollback
            self.trigger_rollback()
            return False
        
        # Run integrity verification
        integrity_result = self.os_manager.verify_integrity()
        
        if integrity_result.get("status") != "PASS":
            self.trigger_rollback()
            return False
        
        # Boot is healthy, reset counter
        try:
            with open(self.BOOT_ATTEMPTS_FILE, "w") as f:
                f.write("0")
        except Exception:
            pass
        
        return True
    
    def trigger_rollback(self) -> bool:
        """Trigger rollback to previous slot."""
        self._state = UpdateState.ROLLING_BACK
        
        if self.os_manager.rollback():
            return True
        
        self._error = "Rollback failed"
        self._state = UpdateState.FAILED
        return False
    
    def get_status(self) -> Dict:
        """Get update controller status."""
        return {
            "state": self._state.value,
            "progress": self._progress,
            "error": self._error,
            "current_package": {
                "version": self._current_package.version,
                "size": self._current_package.size_bytes
            } if self._current_package else None
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 SYSTEM SNAPSHOT MANAGER — Snapshot and restore system states
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SystemSnapshot:
    """A system state snapshot."""
    snapshot_id: str
    name: str
    created_at: float
    size_bytes: int
    paths_included: List[str]
    hash: str
    compressed: bool


class SystemSnapshotManager:
    """
    V7.6 System Snapshot Manager - Creates and manages snapshots
    of critical system state for quick restore.
    """
    
    SNAPSHOT_DIR = "/opt/titan/snapshots"
    SNAPSHOT_INDEX = "/opt/titan/state/snapshots.json"
    
    DEFAULT_PATHS = [
        "/opt/titan/config",
        "/opt/titan/state/profiles",
        "/home/user/.config/titan",
    ]
    
    def __init__(self, max_snapshots: int = 5):
        """
        Initialize snapshot manager.
        
        Args:
            max_snapshots: Maximum number of snapshots to retain
        """
        self.max_snapshots = max_snapshots
        self._snapshots: List[SystemSnapshot] = []
        self._load_index()
    
    def _load_index(self):
        """Load snapshot index from disk."""
        try:
            if os.path.exists(self.SNAPSHOT_INDEX):
                with open(self.SNAPSHOT_INDEX, "r") as f:
                    data = json.load(f)
                self._snapshots = [
                    SystemSnapshot(**s) for s in data.get("snapshots", [])
                ]
        except Exception:
            self._snapshots = []
    
    def _save_index(self):
        """Save snapshot index to disk."""
        try:
            os.makedirs(os.path.dirname(self.SNAPSHOT_INDEX), exist_ok=True)
            with open(self.SNAPSHOT_INDEX, "w") as f:
                json.dump({
                    "snapshots": [
                        {
                            "snapshot_id": s.snapshot_id,
                            "name": s.name,
                            "created_at": s.created_at,
                            "size_bytes": s.size_bytes,
                            "paths_included": s.paths_included,
                            "hash": s.hash,
                            "compressed": s.compressed
                        }
                        for s in self._snapshots
                    ]
                }, f, indent=2)
        except Exception:
            pass
    
    def create_snapshot(self, name: str, 
                       paths: Optional[List[str]] = None,
                       compress: bool = True) -> Optional[SystemSnapshot]:
        """
        Create a new system snapshot.
        
        Args:
            name: Human-readable snapshot name
            paths: Paths to include (uses DEFAULT_PATHS if None)
            compress: Whether to compress the snapshot
        
        Returns:
            Created snapshot or None on failure
        """
        paths = paths or self.DEFAULT_PATHS
        
        # Generate snapshot ID
        snapshot_id = hashlib.md5(
            f"{name}{time.time()}".encode()
        ).hexdigest()[:12]
        
        snapshot_path = os.path.join(self.SNAPSHOT_DIR, f"{snapshot_id}.tar")
        if compress:
            snapshot_path += ".gz"
        
        try:
            os.makedirs(self.SNAPSHOT_DIR, exist_ok=True)
            
            # Create tarball of paths
            import tarfile
            mode = "w:gz" if compress else "w"
            
            total_size = 0
            with tarfile.open(snapshot_path, mode) as tar:
                for path in paths:
                    if os.path.exists(path):
                        tar.add(path)
                        if os.path.isfile(path):
                            total_size += os.path.getsize(path)
                        elif os.path.isdir(path):
                            for root, _, files in os.walk(path):
                                for f in files:
                                    total_size += os.path.getsize(os.path.join(root, f))
            
            # Calculate hash of snapshot
            sha256 = hashlib.sha256()
            with open(snapshot_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            
            snapshot = SystemSnapshot(
                snapshot_id=snapshot_id,
                name=name,
                created_at=time.time(),
                size_bytes=os.path.getsize(snapshot_path),
                paths_included=paths,
                hash=sha256.hexdigest(),
                compressed=compress
            )
            
            self._snapshots.append(snapshot)
            self._enforce_retention()
            self._save_index()
            
            return snapshot
            
        except Exception:
            return None
    
    def restore_snapshot(self, snapshot_id: str, 
                        target_dir: Optional[str] = None) -> bool:
        """
        Restore a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            target_dir: Target directory (uses / if None)
        
        Returns:
            True if restore successful
        """
        snapshot = next(
            (s for s in self._snapshots if s.snapshot_id == snapshot_id),
            None
        )
        
        if not snapshot:
            return False
        
        snapshot_path = os.path.join(self.SNAPSHOT_DIR, f"{snapshot_id}.tar")
        if snapshot.compressed:
            snapshot_path += ".gz"
        
        if not os.path.exists(snapshot_path):
            return False
        
        try:
            import tarfile
            mode = "r:gz" if snapshot.compressed else "r"
            
            target = target_dir or "/"
            with tarfile.open(snapshot_path, mode) as tar:
                tar.extractall(path=target)
            
            return True
            
        except Exception:
            return False
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        snapshot = next(
            (s for s in self._snapshots if s.snapshot_id == snapshot_id),
            None
        )
        
        if not snapshot:
            return False
        
        # Remove file
        snapshot_path = os.path.join(self.SNAPSHOT_DIR, f"{snapshot_id}.tar")
        if snapshot.compressed:
            snapshot_path += ".gz"
        
        try:
            if os.path.exists(snapshot_path):
                os.remove(snapshot_path)
        except Exception:
            pass
        
        # Remove from index
        self._snapshots = [s for s in self._snapshots if s.snapshot_id != snapshot_id]
        self._save_index()
        
        return True
    
    def _enforce_retention(self):
        """Enforce maximum snapshot retention."""
        while len(self._snapshots) > self.max_snapshots:
            # Remove oldest snapshot
            oldest = min(self._snapshots, key=lambda s: s.created_at)
            self.delete_snapshot(oldest.snapshot_id)
    
    def list_snapshots(self) -> List[Dict]:
        """List all snapshots."""
        return [
            {
                "id": s.snapshot_id,
                "name": s.name,
                "created_at": s.created_at,
                "size_mb": round(s.size_bytes / (1024 * 1024), 2),
                "paths": s.paths_included
            }
            for s in sorted(self._snapshots, key=lambda x: x.created_at, reverse=True)
        ]
    
    def get_snapshot(self, snapshot_id: str) -> Optional[SystemSnapshot]:
        """Get snapshot by ID."""
        return next(
            (s for s in self._snapshots if s.snapshot_id == snapshot_id),
            None
        )


# Global instances
_integrity_monitor: Optional[IntegrityMonitor] = None
_secure_boot_manager: Optional[SecureBootManager] = None
_update_controller: Optional[AtomicUpdateController] = None
_snapshot_manager: Optional[SystemSnapshotManager] = None


def get_integrity_monitor() -> IntegrityMonitor:
    """Get global integrity monitor."""
    global _integrity_monitor
    if _integrity_monitor is None:
        _integrity_monitor = IntegrityMonitor()
    return _integrity_monitor


def get_secure_boot_manager() -> SecureBootManager:
    """Get global secure boot manager."""
    global _secure_boot_manager
    if _secure_boot_manager is None:
        _secure_boot_manager = SecureBootManager()
    return _secure_boot_manager


def get_update_controller() -> AtomicUpdateController:
    """Get global update controller."""
    global _update_controller
    if _update_controller is None:
        _update_controller = AtomicUpdateController()
    return _update_controller


def get_snapshot_manager() -> SystemSnapshotManager:
    """Get global snapshot manager."""
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = SystemSnapshotManager()
    return _snapshot_manager
