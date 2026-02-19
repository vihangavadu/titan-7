#!/usr/bin/env python3
"""
Lucid Empire V7.0-TITAN - eBPF Network Shield Loader

This module provides a Python interface for loading and controlling
the eBPF network shield program. It handles:
- Compilation of the eBPF C code
- Loading the program into the kernel
- Attaching to network interfaces (XDP/TC hooks)
- Runtime persona switching
- Statistics monitoring

Source: Unified Agent [cite: 1, 14, 16]

Requirements:
- Linux kernel 5.x+ with eBPF support
- bcc (BPF Compiler Collection) or libbpf
- Root privileges

Usage:
    from network_shield_loader import NetworkShield
    
    shield = NetworkShield(interface="eth0")
    shield.load()
    shield.set_persona("windows")
    shield.get_stats()
    shield.unload()
"""

import os
import sys
import subprocess
import ctypes
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from enum import IntEnum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [TITAN-SHIELD] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class Persona(IntEnum):
    """Operating system personas for network fingerprint masquerading."""
    LINUX = 0
    WINDOWS = 1
    MACOS = 2


class NetworkShieldError(Exception):
    """Custom exception for Network Shield errors."""
    pass


class NetworkShield:
    """
    eBPF Network Shield Manager
    
    Provides a high-level interface for managing the kernel-level
    network packet manipulation program.
    
    Attributes:
        interface: Network interface to attach the shield to
        ebpf_dir: Directory containing eBPF source and compiled programs
        persona: Currently active OS persona for fingerprint masquerading
    """
    
    # OS Signature definitions (mirrors the eBPF code)
    OS_SIGNATURES = {
        Persona.LINUX: {
            "ttl": 64,
            "tcp_window": 29200,
            "tcp_mss": 1460,
            "tcp_sack": True,
            "tcp_timestamps": True,
            "tcp_window_scale": 7,
        },
        Persona.WINDOWS: {
            "ttl": 128,
            "tcp_window": 65535,
            "tcp_mss": 1460,
            "tcp_sack": True,
            "tcp_timestamps": False,
            "tcp_window_scale": 8,
        },
        Persona.MACOS: {
            "ttl": 64,
            "tcp_window": 65535,
            "tcp_mss": 1460,
            "tcp_sack": True,
            "tcp_timestamps": True,
            "tcp_window_scale": 6,
        },
    }
    
    def __init__(self, interface: str = "eth0", ebpf_dir: Optional[Path] = None):
        """
        Initialize the Network Shield.
        
        Args:
            interface: Network interface name to attach the shield to
            ebpf_dir: Path to directory containing eBPF source files
        """
        self.interface = interface
        self.ebpf_dir = ebpf_dir or Path(__file__).parent
        self.source_file = self.ebpf_dir / "network_shield.c"
        self.object_file = self.ebpf_dir / "network_shield.o"
        self.persona = Persona.LINUX
        self.is_loaded = False
        self._bpf_map_fd = None
        
        logger.info(f"NetworkShield initialized for interface: {interface}")
    
    def _check_root(self) -> None:
        """Verify root privileges are available."""
        if os.geteuid() != 0:
            raise NetworkShieldError(
                "Root privileges required. Run with sudo."
            )
    
    def _check_interface(self) -> None:
        """Verify the network interface exists."""
        try:
            result = subprocess.run(
                ["ip", "link", "show", self.interface],
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"Interface {self.interface} found")
        except subprocess.CalledProcessError:
            raise NetworkShieldError(
                f"Network interface '{self.interface}' not found"
            )
    
    def _check_bpf_support(self) -> bool:
        """Check if the kernel supports eBPF/XDP."""
        checks = [
            # Check for BPF filesystem
            Path("/sys/fs/bpf").exists(),
            # Check for BPF syscall
            Path("/proc/kallsyms").exists(),
        ]
        
        # Check kernel config for BPF
        try:
            result = subprocess.run(
                ["cat", "/proc/config.gz"],
                capture_output=True,
                check=False
            )
            if result.returncode == 0:
                import gzip
                config = gzip.decompress(result.stdout).decode()
                checks.append("CONFIG_BPF=y" in config)
                checks.append("CONFIG_BPF_SYSCALL=y" in config)
        except Exception:
            pass
        
        return all(checks[:2])  # At minimum, need bpf filesystem
    
    def compile(self, force: bool = False) -> Path:
        """
        Compile the eBPF C source code to BPF bytecode.
        
        Args:
            force: Recompile even if object file exists
            
        Returns:
            Path to the compiled object file
        """
        if not self.source_file.exists():
            raise NetworkShieldError(
                f"eBPF source file not found: {self.source_file}"
            )
        
        # Check if recompilation is needed
        if not force and self.object_file.exists():
            src_mtime = self.source_file.stat().st_mtime
            obj_mtime = self.object_file.stat().st_mtime
            if obj_mtime > src_mtime:
                logger.info("Using cached compiled eBPF program")
                return self.object_file
        
        logger.info("Compiling eBPF network shield...")
        
        # Compile with clang
        compile_cmd = [
            "clang",
            "-O2",
            "-g",
            "-target", "bpf",
            "-D__TARGET_ARCH_x86",
            "-I/usr/include",
            "-I/usr/include/x86_64-linux-gnu",
            "-c", str(self.source_file),
            "-o", str(self.object_file)
        ]
        
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Compilation successful: {self.object_file}")
            return self.object_file
        except subprocess.CalledProcessError as e:
            raise NetworkShieldError(
                f"eBPF compilation failed:\n{e.stderr}"
            )
    
    def load(self, mode: str = "xdp") -> None:
        """
        Load the eBPF program and attach it to the network interface.
        
        Args:
            mode: Attachment mode - 'xdp' for XDP hook, 'tc' for TC hook
        """
        self._check_root()
        self._check_interface()
        
        if not self._check_bpf_support():
            raise NetworkShieldError(
                "Kernel does not support eBPF. Ensure CONFIG_BPF is enabled."
            )
        
        # Compile if needed
        self.compile()
        
        if mode == "xdp":
            self._attach_xdp()
        elif mode == "tc":
            self._attach_tc()
        else:
            raise NetworkShieldError(f"Unknown mode: {mode}")
        
        self.is_loaded = True
        logger.info(f"Network Shield loaded in {mode.upper()} mode")
    
    def _attach_xdp(self) -> None:
        """Attach the eBPF program using XDP hook."""
        logger.info(f"Attaching XDP program to {self.interface}...")
        
        try:
            # First, detach any existing XDP program
            subprocess.run(
                ["ip", "link", "set", "dev", self.interface, "xdp", "off"],
                capture_output=True,
                check=False  # Ignore errors if no program was attached
            )
            
            # Attach the new XDP program
            result = subprocess.run(
                [
                    "ip", "link", "set", "dev", self.interface,
                    "xdp", "obj", str(self.object_file),
                    "sec", "xdp"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("XDP program attached successfully")
        except subprocess.CalledProcessError as e:
            raise NetworkShieldError(
                f"Failed to attach XDP program:\n{e.stderr}"
            )
    
    def _attach_tc(self) -> None:
        """Attach the eBPF program using TC (Traffic Control) hook."""
        logger.info(f"Attaching TC program to {self.interface}...")
        
        try:
            # Create a clsact qdisc if it doesn't exist
            subprocess.run(
                ["tc", "qdisc", "add", "dev", self.interface, "clsact"],
                capture_output=True,
                check=False  # Ignore if already exists
            )
            
            # Attach to egress
            result = subprocess.run(
                [
                    "tc", "filter", "add", "dev", self.interface,
                    "egress", "bpf", "da", "obj", str(self.object_file),
                    "sec", "tc"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("TC program attached successfully")
        except subprocess.CalledProcessError as e:
            raise NetworkShieldError(
                f"Failed to attach TC program:\n{e.stderr}"
            )
    
    def unload(self) -> None:
        """Detach and unload the eBPF program."""
        if not self.is_loaded:
            logger.warning("Network Shield is not loaded")
            return
        
        self._check_root()
        
        logger.info(f"Unloading Network Shield from {self.interface}...")
        
        # Detach XDP
        subprocess.run(
            ["ip", "link", "set", "dev", self.interface, "xdp", "off"],
            capture_output=True,
            check=False
        )
        
        # Detach TC
        subprocess.run(
            ["tc", "filter", "del", "dev", self.interface, "egress"],
            capture_output=True,
            check=False
        )
        
        self.is_loaded = False
        logger.info("Network Shield unloaded")
    
    def set_persona(self, persona: str) -> Dict[str, Any]:
        """
        Switch the active OS persona for fingerprint masquerading.
        
        Args:
            persona: Target persona name ('linux', 'windows', 'macos')
            
        Returns:
            Dictionary containing the active signature configuration
        """
        persona_map = {
            "linux": Persona.LINUX,
            "windows": Persona.WINDOWS,
            "macos": Persona.MACOS,
        }
        
        persona_lower = persona.lower()
        if persona_lower not in persona_map:
            raise NetworkShieldError(
                f"Unknown persona: {persona}. "
                f"Valid options: {list(persona_map.keys())}"
            )
        
        self.persona = persona_map[persona_lower]
        signature = self.OS_SIGNATURES[self.persona]
        
        logger.info(f"Persona switched to: {persona.upper()}")
        logger.info(f"  TTL: {signature['ttl']}")
        logger.info(f"  TCP Window: {signature['tcp_window']}")
        logger.info(f"  TCP MSS: {signature['tcp_mss']}")
        
        # Update the BPF map with the new persona
        if self.is_loaded:
            self._update_persona_map()
        
        return signature
    
    def _update_persona_map(self) -> None:
        """Update the eBPF map with the current persona value."""
        # Update BPF map via bpftool with the current persona value
        logger.debug(f"Updating BPF persona_config map to: {self.persona}")
        
        try:
            # Use bpftool to update the map
            result = subprocess.run(
                [
                    "bpftool", "map", "update",
                    "name", "persona_config",
                    "key", "0", "0", "0", "0",
                    "value", str(self.persona), "0", "0", "0"
                ],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                logger.debug("BPF map updated successfully")
            else:
                logger.warning(f"Could not update BPF map: {result.stderr}")
        except FileNotFoundError:
            logger.warning("bpftool not found, map update skipped")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Retrieve packet processing statistics from the eBPF program.
        
        Returns:
            Dictionary with packet counts
        """
        stats = {
            "packets_total": 0,
            "packets_modified": 0,
            "packets_tcp": 0,
            "packets_udp": 0,
        }
        
        if not self.is_loaded:
            return stats
        
        try:
            # Use bpftool to read the stats map
            result = subprocess.run(
                ["bpftool", "map", "dump", "name", "stats", "-j"],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            stat_keys = ["packets_total", "packets_modified", 
                        "packets_tcp", "packets_udp"]
            
            for entry in data:
                key_idx = entry.get("key", [0])[0]
                if key_idx < len(stat_keys):
                    # Sum values from all CPUs (PERCPU_ARRAY)
                    values = entry.get("value", [0])
                    if isinstance(values, list):
                        stats[stat_keys[key_idx]] = sum(values)
                    else:
                        stats[stat_keys[key_idx]] = values
                        
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            logger.debug(f"Could not read stats: {e}")
        
        return stats
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Network Shield.
        
        Returns:
            Dictionary with status information
        """
        return {
            "loaded": self.is_loaded,
            "interface": self.interface,
            "persona": self.persona.name,
            "signature": self.OS_SIGNATURES[self.persona],
            "stats": self.get_stats(),
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        if self.is_loaded:
            self.unload()
        return False


def main():
    """Command-line interface for the Network Shield."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Lucid Empire V7.0-TITAN Network Shield"
    )
    parser.add_argument(
        "-i", "--interface",
        default="eth0",
        help="Network interface to attach to"
    )
    parser.add_argument(
        "-p", "--persona",
        choices=["linux", "windows", "macos"],
        default="windows",
        help="OS persona for fingerprint masquerading"
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["xdp", "tc"],
        default="xdp",
        help="eBPF attachment mode"
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Only compile the eBPF program, don't load"
    )
    parser.add_argument(
        "--unload",
        action="store_true",
        help="Unload any attached eBPF programs"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    shield = NetworkShield(interface=args.interface)
    
    try:
        if args.compile_only:
            shield.compile(force=True)
            print(f"Compiled: {shield.object_file}")
            return
        
        if args.unload:
            shield.is_loaded = True  # Assume loaded to force unload
            shield.unload()
            return
        
        # Load and configure
        shield.load(mode=args.mode)
        shield.set_persona(args.persona)
        
        print("\n" + "=" * 60)
        print("TITAN Network Shield Active")
        print("=" * 60)
        print(json.dumps(shield.get_status(), indent=2))
        print("\nPress Ctrl+C to stop...")
        
        # Keep running until interrupted
        import time
        while True:
            time.sleep(5)
            stats = shield.get_stats()
            logger.info(f"Stats: {stats}")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except NetworkShieldError as e:
        logger.error(str(e))
        sys.exit(1)
    finally:
        if shield.is_loaded:
            shield.unload()


if __name__ == "__main__":
    main()
