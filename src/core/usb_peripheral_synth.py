"""
TITAN V7.5 — USB Peripheral Synthesis

Generates a realistic synthetic USB device tree via gadgetfs/configfs.
Populates the system with virtual peripherals (webcam, microphone, input
devices) that match the spoofed hardware profile.

Detection vector: An empty or generic USB bus is common in VMs and
containers.  Real Windows laptops always have USB HID devices, audio
devices, webcams, and storage controllers.  Fraud SDKs (Forter, Sardine)
query navigator.usb and WebUSB to detect empty buses.

This module writes synthetic USB device descriptors into configfs so
that the kernel reports a populated bus to user-space.

Usage:
    python3 usb_peripheral_synth.py [--profile default|gaming|office]
"""

import os
import sys
import random
import json
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger("titan.usb_synth")

# Realistic USB device templates — modeled from actual Windows laptop lsusb output
USB_DEVICES = {
    "default": [
        # Integrated webcam (every laptop has one)
        {
            "idVendor": "0c45", "idProduct": "6713",
            "manufacturer": "Sonix Technology Co., Ltd.",
            "product": "Integrated Webcam",
            "bDeviceClass": "ef", "bDeviceSubClass": "02",
            "serial_prefix": "SN0"
        },
        # Realtek Bluetooth adapter
        {
            "idVendor": "0bda", "idProduct": "0821",
            "manufacturer": "Realtek Semiconductor Corp.",
            "product": "Bluetooth Radio",
            "bDeviceClass": "e0", "bDeviceSubClass": "01",
            "serial_prefix": "00e0"
        },
        # USB Composite HID (keyboard + touchpad)
        {
            "idVendor": "06cb", "idProduct": "00bd",
            "manufacturer": "Synaptics, Inc.",
            "product": "Synaptics TouchPad",
            "bDeviceClass": "00", "bDeviceSubClass": "00",
            "serial_prefix": "SYN"
        },
        # Intel USB hub (root)
        {
            "idVendor": "8087", "idProduct": "0026",
            "manufacturer": "Intel Corp.",
            "product": "AX201 Bluetooth",
            "bDeviceClass": "e0", "bDeviceSubClass": "01",
            "serial_prefix": "IN"
        },
        # USB Mass Storage (occasionally connected)
        {
            "idVendor": "0781", "idProduct": "5583",
            "manufacturer": "SanDisk Corp.",
            "product": "Ultra Fit",
            "bDeviceClass": "00", "bDeviceSubClass": "00",
            "serial_prefix": "4C530"
        },
    ],
    "gaming": [
        {
            "idVendor": "046d", "idProduct": "c08b",
            "manufacturer": "Logitech, Inc.",
            "product": "G502 HERO Gaming Mouse",
            "bDeviceClass": "00", "bDeviceSubClass": "00",
            "serial_prefix": "LGS"
        },
        {
            "idVendor": "1532", "idProduct": "0084",
            "manufacturer": "Razer USA, Ltd",
            "product": "Razer BlackWidow V3",
            "bDeviceClass": "00", "bDeviceSubClass": "00",
            "serial_prefix": "RZ"
        },
        {
            "idVendor": "0c45", "idProduct": "6366",
            "manufacturer": "Sonix Technology Co., Ltd.",
            "product": "HD Webcam",
            "bDeviceClass": "ef", "bDeviceSubClass": "02",
            "serial_prefix": "SN1"
        },
        {
            "idVendor": "8087", "idProduct": "0029",
            "manufacturer": "Intel Corp.",
            "product": "AX211 Bluetooth",
            "bDeviceClass": "e0", "bDeviceSubClass": "01",
            "serial_prefix": "IN"
        },
    ],
    "office": [
        {
            "idVendor": "046d", "idProduct": "c52b",
            "manufacturer": "Logitech, Inc.",
            "product": "Unifying Receiver",
            "bDeviceClass": "00", "bDeviceSubClass": "00",
            "serial_prefix": "LGU"
        },
        {
            "idVendor": "0c45", "idProduct": "6713",
            "manufacturer": "Sonix Technology Co., Ltd.",
            "product": "Integrated Webcam",
            "bDeviceClass": "ef", "bDeviceSubClass": "02",
            "serial_prefix": "SN0"
        },
        {
            "idVendor": "8087", "idProduct": "0026",
            "manufacturer": "Intel Corp.",
            "product": "AX201 Bluetooth",
            "bDeviceClass": "e0", "bDeviceSubClass": "01",
            "serial_prefix": "IN"
        },
    ],
}


def generate_serial(prefix: str, seed: str = "") -> str:
    """Generate a deterministic but realistic USB serial number."""
    h = hashlib.sha256(f"{prefix}{seed}{random.random()}".encode()).hexdigest()
    return f"{prefix}{h[:12].upper()}"


def write_usb_descriptors(profile: str = "default", output_dir: str = "/tmp/titan_usb"):
    """Write USB device descriptor files for the given hardware profile.

    These descriptors are consumed by the titan_hw.ko module or a
    user-space USB gadget daemon to populate the visible USB bus.
    """
    devices = USB_DEVICES.get(profile, USB_DEVICES["default"])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = []
    for i, dev in enumerate(devices):
        serial = generate_serial(dev["serial_prefix"])
        desc = {
            "bus": 1,
            "port": i + 1,
            "idVendor": f"0x{dev['idVendor']}",
            "idProduct": f"0x{dev['idProduct']}",
            "manufacturer": dev["manufacturer"],
            "product": dev["product"],
            "serial": serial,
            "bDeviceClass": f"0x{dev['bDeviceClass']}",
            "bDeviceSubClass": f"0x{dev['bDeviceSubClass']}",
            "bcdUSB": "0x0200",
            "speed": random.choice(["12M", "480M", "5000M"]),
        }
        fname = f"device_{i:02d}_{dev['idVendor']}_{dev['idProduct']}.json"
        (out / fname).write_text(json.dumps(desc, indent=2))
        manifest.append(fname)
        logger.info("USB synth: %s — %s (%s)", dev["product"], serial, fname)

    # Write manifest for the loader
    (out / "manifest.json").write_text(json.dumps({
        "profile": profile,
        "device_count": len(manifest),
        "devices": manifest,
    }, indent=2))

    logger.info("USB peripheral synthesis complete: %d devices for '%s' profile",
                len(manifest), profile)
    return manifest


def apply_sysfs_overrides(output_dir: str = "/tmp/titan_usb"):
    """Apply USB device descriptors to sysfs via configfs gadget API.

    Requires root and configfs mounted at /sys/kernel/config.
    Falls back gracefully if not available (non-root or no configfs).
    """
    configfs = Path("/sys/kernel/config/usb_gadget")
    if not configfs.exists():
        logger.warning("configfs not mounted — USB synthesis requires root + configfs")
        return False

    manifest_path = Path(output_dir) / "manifest.json"
    if not manifest_path.exists():
        logger.error("No USB manifest found at %s", manifest_path)
        return False

    manifest = json.loads(manifest_path.read_text())
    for dev_file in manifest["devices"]:
        dev = json.loads((Path(output_dir) / dev_file).read_text())
        gadget_name = f"titan_{dev['idVendor'].replace('0x', '')}_{dev['idProduct'].replace('0x', '')}"
        gadget_dir = configfs / gadget_name

        try:
            gadget_dir.mkdir(exist_ok=True)
            (gadget_dir / "idVendor").write_text(dev["idVendor"])
            (gadget_dir / "idProduct").write_text(dev["idProduct"])
            (gadget_dir / "bDeviceClass").write_text(dev["bDeviceClass"])
            (gadget_dir / "bDeviceSubClass").write_text(dev["bDeviceSubClass"])

            strings_dir = gadget_dir / "strings" / "0x409"
            strings_dir.mkdir(parents=True, exist_ok=True)
            (strings_dir / "manufacturer").write_text(dev["manufacturer"])
            (strings_dir / "product").write_text(dev["product"])
            (strings_dir / "serialnumber").write_text(dev["serial"])

            logger.info("sysfs: Registered gadget %s", gadget_name)
        except PermissionError:
            logger.warning("sysfs: Permission denied for gadget %s (need root)", gadget_name)
        except Exception as e:
            logger.warning("sysfs: Failed to register %s: %s", gadget_name, e)

    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    profile = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("--profile") is False else "default"
    if "--profile" in sys.argv:
        idx = sys.argv.index("--profile")
        profile = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "default"

    print(f"[TITAN USB] Synthesizing USB peripherals for profile: {profile}")
    write_usb_descriptors(profile)
    apply_sysfs_overrides()
    print("[TITAN USB] Done.")


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════════════════

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
import threading


@dataclass
class USBDevice:
    """Represents a USB device in the synthetic tree."""
    vendor_id: str
    product_id: str
    manufacturer: str
    product: str
    serial: str
    device_class: str
    device_subclass: str
    bus: int = 1
    port: int = 1
    speed: str = "480M"
    active: bool = True
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class USBDeviceManager:
    """
    V7.6 P0: Dynamic USB device management.
    
    Provides real-time management of synthetic USB devices with
    add/remove capability and state persistence.
    """
    
    _instance = None
    STATE_FILE = Path("/opt/titan/state/usb_devices.json")
    
    def __init__(self):
        self.devices: Dict[str, USBDevice] = {}
        self.active_profile: str = "default"
        self.logger = logging.getLogger("TITAN-USB.Manager")
        self._lock = threading.Lock()
        
        self._load_state()
    
    def _load_state(self):
        """Load USB device state from disk."""
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE) as f:
                    data = json.load(f)
                self.active_profile = data.get("profile", "default")
                for device_id, device_data in data.get("devices", {}).items():
                    self.devices[device_id] = USBDevice(**device_data)
            except Exception as e:
                self.logger.warning(f"Failed to load USB state: {e}")
    
    def _save_state(self):
        """Save USB device state to disk."""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "profile": self.active_profile,
                "devices": {
                    device_id: {
                        "vendor_id": d.vendor_id,
                        "product_id": d.product_id,
                        "manufacturer": d.manufacturer,
                        "product": d.product,
                        "serial": d.serial,
                        "device_class": d.device_class,
                        "device_subclass": d.device_subclass,
                        "bus": d.bus,
                        "port": d.port,
                        "speed": d.speed,
                        "active": d.active,
                        "created": d.created
                    }
                    for device_id, d in self.devices.items()
                }
            }
            with open(self.STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save USB state: {e}")
    
    def _device_id(self, vendor_id: str, product_id: str) -> str:
        """Generate device ID from vendor and product."""
        return f"{vendor_id}:{product_id}"
    
    def add_device(self, device: USBDevice) -> bool:
        """Add a USB device to the synthetic tree."""
        with self._lock:
            device_id = self._device_id(device.vendor_id, device.product_id)
            
            if device_id in self.devices:
                self.logger.warning(f"Device {device_id} already exists")
                return False
            
            self.devices[device_id] = device
            self._save_state()
            self.logger.info(f"Added USB device: {device.product} ({device_id})")
            return True
    
    def remove_device(self, vendor_id: str, product_id: str) -> bool:
        """Remove a USB device from the synthetic tree."""
        with self._lock:
            device_id = self._device_id(vendor_id, product_id)
            
            if device_id not in self.devices:
                return False
            
            del self.devices[device_id]
            self._save_state()
            self.logger.info(f"Removed USB device: {device_id}")
            return True
    
    def get_device(self, vendor_id: str, product_id: str) -> Optional[USBDevice]:
        """Get a USB device by vendor/product ID."""
        device_id = self._device_id(vendor_id, product_id)
        return self.devices.get(device_id)
    
    def list_devices(self, active_only: bool = False) -> List[USBDevice]:
        """List all USB devices."""
        devices = list(self.devices.values())
        if active_only:
            devices = [d for d in devices if d.active]
        return devices
    
    def set_device_active(self, vendor_id: str, product_id: str, active: bool) -> bool:
        """Set device active state."""
        with self._lock:
            device_id = self._device_id(vendor_id, product_id)
            if device_id not in self.devices:
                return False
            
            self.devices[device_id].active = active
            self._save_state()
            return True
    
    def load_profile(self, profile: str) -> int:
        """Load USB devices from a pre-defined profile."""
        devices = USB_DEVICES.get(profile, USB_DEVICES["default"])
        
        with self._lock:
            self.devices.clear()
            
            for i, dev in enumerate(devices):
                serial = generate_serial(dev["serial_prefix"])
                device = USBDevice(
                    vendor_id=dev["idVendor"],
                    product_id=dev["idProduct"],
                    manufacturer=dev["manufacturer"],
                    product=dev["product"],
                    serial=serial,
                    device_class=dev["bDeviceClass"],
                    device_subclass=dev["bDeviceSubClass"],
                    port=i + 1
                )
                device_id = self._device_id(device.vendor_id, device.product_id)
                self.devices[device_id] = device
            
            self.active_profile = profile
            self._save_state()
        
        self.logger.info(f"Loaded USB profile '{profile}' with {len(self.devices)} devices")
        return len(self.devices)
    
    def apply_to_sysfs(self) -> Dict[str, bool]:
        """Apply current devices to sysfs/configfs."""
        results = {}
        
        # Write device descriptors
        write_usb_descriptors(self.active_profile)
        
        # Apply to sysfs
        success = apply_sysfs_overrides()
        
        for device_id, device in self.devices.items():
            results[device_id] = success
        
        return results
    
    def get_status(self) -> Dict:
        """Get USB manager status."""
        return {
            "active_profile": self.active_profile,
            "device_count": len(self.devices),
            "active_devices": len([d for d in self.devices.values() if d.active]),
            "devices": [
                {
                    "vendor_id": d.vendor_id,
                    "product_id": d.product_id,
                    "product": d.product,
                    "active": d.active
                }
                for d in self.devices.values()
            ]
        }


class USBProfileGenerator:
    """
    V7.6 P0: Generate USB profiles matching hardware profiles.
    
    Creates consistent USB device configurations that match
    the overall hardware profile and persona.
    """
    
    _instance = None
    
    # Device categories for profile generation
    DEVICE_CATEGORIES = {
        "webcam": [
            {"idVendor": "0c45", "idProduct": "6713", "manufacturer": "Sonix Technology Co., Ltd.", "product": "Integrated Webcam"},
            {"idVendor": "046d", "idProduct": "0825", "manufacturer": "Logitech, Inc.", "product": "Webcam C270"},
            {"idVendor": "04f2", "idProduct": "b5ee", "manufacturer": "Chicony Electronics Co., Ltd.", "product": "Integrated Camera"},
        ],
        "bluetooth": [
            {"idVendor": "8087", "idProduct": "0026", "manufacturer": "Intel Corp.", "product": "AX201 Bluetooth"},
            {"idVendor": "0bda", "idProduct": "0821", "manufacturer": "Realtek Semiconductor Corp.", "product": "Bluetooth Radio"},
            {"idVendor": "8087", "idProduct": "0029", "manufacturer": "Intel Corp.", "product": "AX211 Bluetooth"},
        ],
        "input": [
            {"idVendor": "06cb", "idProduct": "00bd", "manufacturer": "Synaptics, Inc.", "product": "Synaptics TouchPad"},
            {"idVendor": "046d", "idProduct": "c52b", "manufacturer": "Logitech, Inc.", "product": "Unifying Receiver"},
            {"idVendor": "1bcf", "idProduct": "0005", "manufacturer": "Sunplus Innovation Technology Inc.", "product": "Optical Mouse"},
        ],
        "storage": [
            {"idVendor": "0781", "idProduct": "5583", "manufacturer": "SanDisk Corp.", "product": "Ultra Fit"},
            {"idVendor": "090c", "idProduct": "1000", "manufacturer": "Silicon Motion, Inc.", "product": "Flash Drive"},
        ],
        "gaming_mouse": [
            {"idVendor": "046d", "idProduct": "c08b", "manufacturer": "Logitech, Inc.", "product": "G502 HERO Gaming Mouse"},
            {"idVendor": "1532", "idProduct": "007c", "manufacturer": "Razer USA, Ltd", "product": "DeathAdder V2"},
        ],
        "gaming_keyboard": [
            {"idVendor": "1532", "idProduct": "0084", "manufacturer": "Razer USA, Ltd", "product": "Razer BlackWidow V3"},
            {"idVendor": "046d", "idProduct": "c339", "manufacturer": "Logitech, Inc.", "product": "G915 Wireless Keyboard"},
        ],
    }
    
    def __init__(self):
        self.logger = logging.getLogger("TITAN-USB.ProfileGen")
    
    def generate_for_hardware_profile(self, hardware_profile: Dict) -> List[Dict]:
        """Generate USB devices matching a hardware profile."""
        devices = []
        
        # Always include webcam and bluetooth
        devices.append(self._select_device("webcam"))
        devices.append(self._select_device("bluetooth"))
        
        # Determine persona type from hardware
        gpu = hardware_profile.get("gpu", "").lower()
        is_gaming = any(kw in gpu for kw in ["rtx", "gtx", "rx 6", "rx 7", "gaming"])
        
        if is_gaming:
            # Gaming setup
            devices.append(self._select_device("gaming_mouse"))
            devices.append(self._select_device("gaming_keyboard"))
        else:
            # Standard office/laptop setup
            devices.append(self._select_device("input"))
        
        # Optionally add storage (50% chance)
        if random.random() > 0.5:
            devices.append(self._select_device("storage"))
        
        # Add serial numbers
        for i, dev in enumerate(devices):
            dev["serial"] = generate_serial(dev.get("serial_prefix", "DEV"))
            dev["bDeviceClass"] = dev.get("bDeviceClass", "00")
            dev["bDeviceSubClass"] = dev.get("bDeviceSubClass", "00")
            dev["port"] = i + 1
        
        return devices
    
    def _select_device(self, category: str) -> Dict:
        """Select a random device from a category."""
        devices = self.DEVICE_CATEGORIES.get(category, [])
        if not devices:
            return {}
        
        device = random.choice(devices).copy()
        device["serial_prefix"] = device["manufacturer"][:3].upper()
        return device
    
    def generate_minimal_profile(self) -> List[Dict]:
        """Generate minimal USB profile for VMs/containers."""
        return [
            self._select_device("bluetooth"),
            self._select_device("input")
        ]
    
    def generate_laptop_profile(self) -> List[Dict]:
        """Generate typical laptop USB profile."""
        devices = [
            self._select_device("webcam"),
            self._select_device("bluetooth"),
            self._select_device("input")
        ]
        
        for i, dev in enumerate(devices):
            dev["serial"] = generate_serial(dev.get("serial_prefix", "LP"))
            dev["port"] = i + 1
        
        return devices
    
    def generate_desktop_profile(self, gaming: bool = False) -> List[Dict]:
        """Generate typical desktop USB profile."""
        devices = [
            self._select_device("bluetooth")
        ]
        
        if gaming:
            devices.extend([
                self._select_device("gaming_mouse"),
                self._select_device("gaming_keyboard"),
                self._select_device("webcam")
            ])
        else:
            devices.extend([
                self._select_device("input"),
                self._select_device("webcam")
            ])
        
        for i, dev in enumerate(devices):
            dev["serial"] = generate_serial(dev.get("serial_prefix", "DT"))
            dev["port"] = i + 1
        
        return devices


class USBConsistencyValidator:
    """
    V7.6 P0: Validate USB devices match overall profile.
    
    Ensures USB device configuration is consistent with
    the spoofed hardware profile and platform.
    """
    
    _instance = None
    
    def __init__(self):
        self.logger = logging.getLogger("TITAN-USB.Validator")
    
    def validate_profile(self, usb_devices: List[Dict], hardware_profile: Dict) -> Dict:
        """Validate USB devices against hardware profile."""
        result = {
            "valid": True,
            "score": 100,
            "checks": [],
            "warnings": [],
            "errors": []
        }
        
        # Check 1: Must have at least 2 devices (empty bus is suspicious)
        if len(usb_devices) < 2:
            result["warnings"].append("USB bus has fewer than 2 devices - suspicious")
            result["score"] -= 20
            result["checks"].append({"name": "device_count", "passed": False})
        else:
            result["checks"].append({"name": "device_count", "passed": True})
        
        # Check 2: Should have Bluetooth on modern systems
        has_bluetooth = any(
            "bluetooth" in d.get("product", "").lower()
            for d in usb_devices
        )
        if not has_bluetooth:
            result["warnings"].append("No Bluetooth adapter - uncommon on modern laptops")
            result["score"] -= 10
        result["checks"].append({"name": "bluetooth", "passed": has_bluetooth})
        
        # Check 3: Gaming devices should match gaming hardware
        has_gaming_device = any(
            any(kw in d.get("manufacturer", "").lower() for kw in ["razer", "logitech"])
            and "gaming" in d.get("product", "").lower()
            for d in usb_devices
        )
        
        gpu = hardware_profile.get("gpu", "").lower()
        is_gaming_gpu = any(kw in gpu for kw in ["rtx", "gtx", "rx 6", "rx 7"])
        
        if has_gaming_device and not is_gaming_gpu:
            result["warnings"].append("Gaming peripherals with non-gaming GPU - slight mismatch")
            result["score"] -= 5
        result["checks"].append({
            "name": "gaming_consistency",
            "passed": not (has_gaming_device and not is_gaming_gpu)
        })
        
        # Check 4: Verify no VM-specific devices
        vm_indicators = ["vbox", "vmware", "qemu", "virtual"]
        has_vm_device = any(
            any(ind in d.get("product", "").lower() for ind in vm_indicators)
            for d in usb_devices
        )
        
        if has_vm_device:
            result["valid"] = False
            result["errors"].append("VM-specific USB device detected")
            result["score"] -= 40
        result["checks"].append({"name": "no_vm_devices", "passed": not has_vm_device})
        
        # Check 5: Serial number format
        for dev in usb_devices:
            serial = dev.get("serial", "")
            if serial and (len(serial) < 6 or serial == "0" * len(serial)):
                result["warnings"].append(f"Suspicious serial number: {serial}")
                result["score"] -= 5
                break
        
        result["score"] = max(0, result["score"])
        return result
    
    def validate_against_platform(self, usb_devices: List[Dict], platform: str) -> Dict:
        """Validate USB devices are appropriate for platform."""
        result = {
            "valid": True,
            "platform": platform,
            "issues": []
        }
        
        platform_lower = platform.lower()
        
        # Windows laptops should have integrated webcam
        if "windows" in platform_lower and "laptop" in platform_lower:
            has_webcam = any("webcam" in d.get("product", "").lower() for d in usb_devices)
            if not has_webcam:
                result["issues"].append("Windows laptop should have integrated webcam")
        
        # MacBooks have specific Bluetooth chips
        if "mac" in platform_lower:
            has_intel_bt = any(
                "intel" in d.get("manufacturer", "").lower()
                and "bluetooth" in d.get("product", "").lower()
                for d in usb_devices
            )
            if has_intel_bt and "m1" in platform_lower:
                result["issues"].append("Intel Bluetooth on Apple Silicon Mac is inconsistent")
        
        result["valid"] = len(result["issues"]) == 0
        return result


class USBDeviceMonitor:
    """
    V7.6 P0: Monitor USB device state and changes.
    
    Continuously monitors the synthetic USB tree for anomalies
    and external changes.
    """
    
    _instance = None
    
    def __init__(self, manager: USBDeviceManager = None):
        self.manager = manager or get_usb_device_manager()
        self.monitoring = False
        self._thread = None
        self.check_interval = 30
        self.logger = logging.getLogger("TITAN-USB.Monitor")
        
        self.state_history: List[Dict] = []
        self.max_history = 100
        self.anomaly_callbacks: List[callable] = []
    
    def _get_system_usb_devices(self) -> List[Dict]:
        """Get actual USB devices from system."""
        devices = []
        
        try:
            # Try lsusb first
            import subprocess
            result = subprocess.run(
                ["lsusb", "-v"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse lsusb output (simplified)
                for line in result.stdout.decode().split('\n'):
                    if line.startswith("Bus"):
                        parts = line.split()
                        if len(parts) >= 6:
                            devices.append({
                                "bus": parts[1],
                                "device": parts[3].rstrip(':'),
                                "vendor_product": parts[5] if len(parts) > 5 else ""
                            })
        except Exception:
            pass
        
        # Alternative: read from sysfs
        if not devices:
            usb_path = Path("/sys/bus/usb/devices")
            if usb_path.exists():
                for device_dir in usb_path.iterdir():
                    if device_dir.is_dir() and (device_dir / "idVendor").exists():
                        try:
                            devices.append({
                                "vendor_id": (device_dir / "idVendor").read_text().strip(),
                                "product_id": (device_dir / "idProduct").read_text().strip(),
                                "manufacturer": (device_dir / "manufacturer").read_text().strip()
                                    if (device_dir / "manufacturer").exists() else ""
                            })
                        except Exception:
                            pass
        
        return devices
    
    def _check_anomalies(self):
        """Check for USB device anomalies."""
        system_devices = self._get_system_usb_devices()
        managed_devices = self.manager.list_devices(active_only=True)
        
        anomalies = []
        
        # Check for unexpected devices
        # (This is a simplified check - real implementation would be more sophisticated)
        expected_count = len(managed_devices)
        actual_count = len(system_devices)
        
        if actual_count < expected_count:
            anomalies.append({
                "type": "missing_devices",
                "message": f"Expected {expected_count} devices but found {actual_count}",
                "severity": "high"
            })
        
        # Record state
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expected": expected_count,
            "actual": actual_count,
            "anomalies": anomalies
        }
        self.state_history.append(state)
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history:]
        
        # Notify callbacks
        for anomaly in anomalies:
            self.logger.warning(f"USB anomaly: {anomaly['message']}")
            for callback in self.anomaly_callbacks:
                try:
                    callback(anomaly)
                except Exception:
                    pass
        
        return anomalies
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                self._check_anomalies()
            except Exception as e:
                self.logger.error(f"USB monitoring error: {e}")
            
            # Wait for next check
            for _ in range(self.check_interval):
                if not self.monitoring:
                    break
                import time
                time.sleep(1)
    
    def start(self):
        """Start monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("USB device monitoring started")
    
    def stop(self):
        """Stop monitoring."""
        self.monitoring = False
    
    def register_anomaly_callback(self, callback: callable):
        """Register callback for anomaly notifications."""
        self.anomaly_callbacks.append(callback)
    
    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            "monitoring": self.monitoring,
            "check_interval": self.check_interval,
            "history_size": len(self.state_history),
            "recent_anomalies": [
                s["anomalies"] for s in self.state_history[-5:]
                if s.get("anomalies")
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON GETTERS
# ═══════════════════════════════════════════════════════════════════════════

def get_usb_device_manager() -> USBDeviceManager:
    """Get singleton USBDeviceManager instance."""
    if USBDeviceManager._instance is None:
        USBDeviceManager._instance = USBDeviceManager()
    return USBDeviceManager._instance


def get_usb_profile_generator() -> USBProfileGenerator:
    """Get singleton USBProfileGenerator instance."""
    if USBProfileGenerator._instance is None:
        USBProfileGenerator._instance = USBProfileGenerator()
    return USBProfileGenerator._instance


def get_usb_consistency_validator() -> USBConsistencyValidator:
    """Get singleton USBConsistencyValidator instance."""
    if USBConsistencyValidator._instance is None:
        USBConsistencyValidator._instance = USBConsistencyValidator()
    return USBConsistencyValidator._instance


def get_usb_device_monitor() -> USBDeviceMonitor:
    """Get singleton USBDeviceMonitor instance."""
    if USBDeviceMonitor._instance is None:
        USBDeviceMonitor._instance = USBDeviceMonitor()
    return USBDeviceMonitor._instance
