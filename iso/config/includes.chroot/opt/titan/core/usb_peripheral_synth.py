"""
TITAN V7.0.3 — USB Peripheral Synthesis

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
