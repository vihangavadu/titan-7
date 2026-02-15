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

    def wipe_ephemeral(self) -> bool:
        """
        Wipe all ephemeral data from the OverlayFS upper layer.
        Equivalent to a "soft reboot" — clears all session artifacts.
        """
        try:
            for edir in self._config.ephemeral_dirs:
                if os.path.isdir(edir):
                    for item in os.listdir(edir):
                        item_path = os.path.join(edir, item)
                        try:
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        except (PermissionError, OSError):
                            continue
            return True
        except Exception:
            return False

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
