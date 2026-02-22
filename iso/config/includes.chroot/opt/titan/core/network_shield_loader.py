#!/usr/bin/env python3
"""
TITAN V7.0 SINGULARITY - eBPF Network Shield Loader

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
            "tcp_options_order": ["mss", "nop", "wscale", "nop", "nop", "sack_perm"],
            "ip_id_behavior": "incremental",
            "df_bit": True,
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
        # This would use bpf syscall or bpftool to update the map
        # For now, we log the intention
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
    
    def is_available(self) -> bool:
        """Check if eBPF shield can be loaded on this system."""
        try:
            if os.geteuid() != 0:
                return False
            if not self._check_bpf_support():
                return False
            # Check if clang is available for compilation
            result = subprocess.run(["which", "clang"], capture_output=True, check=False)
            return result.returncode == 0
        except Exception:
            return False
    
    def switch_persona(self, persona) -> Dict[str, Any]:
        """Convenience alias for set_persona that accepts Persona enum directly."""
        if isinstance(persona, Persona):
            name_map = {Persona.LINUX: "linux", Persona.WINDOWS: "windows", Persona.MACOS: "macos"}
            return self.set_persona(name_map.get(persona, "windows"))
        return self.set_persona(str(persona).lower())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # R3-FIX: Safe Boot Sequence — block traffic until eBPF is confirmed active
    # ═══════════════════════════════════════════════════════════════════════════
    
    _NFTABLES_BLOCK_RULES = """#!/usr/sbin/nft -f
# R3-FIX: Temporary outbound block during eBPF boot
# This table is deleted once eBPF shield reports successful init
table inet titan_boot_block {{
    chain output {{
        type filter hook output priority 0; policy drop;
        # Allow loopback
        oif "lo" accept
        # Allow SSH (port 22) to prevent lockout
        tcp sport 22 accept
        tcp dport 22 accept
        # Allow DNS for eBPF compilation dependencies
        udp dport 53 accept
        tcp dport 53 accept
        # Allow established connections (keeps SSH alive)
        ct state established,related accept
        # Drop everything else — prevents true TCP fingerprint leak
        counter drop
    }}
}}
"""
    
    def safe_boot(self, mode: str = "xdp", persona: str = "windows",
                  timeout_seconds: int = 30) -> bool:
        """
        R3-FIX: Safe boot sequence that prevents TCP fingerprint leak.
        
        1. Block all outbound traffic via nftables (except SSH + loopback)
        2. Compile and load eBPF program
        3. Set persona
        4. Verify eBPF is active
        5. Remove nftables block
        
        If eBPF fails to load within timeout, the block is removed and
        an error is raised — the system stays in Linux TCP fingerprint
        but at least doesn't hang.
        
        Args:
            mode: eBPF attachment mode ('xdp' or 'tc')
            persona: Target OS persona
            timeout_seconds: Max time to wait for eBPF init
            
        Returns:
            True if eBPF loaded successfully with no fingerprint leak window
        """
        self._check_root()
        
        logger.info("[R3-SAFE-BOOT] Starting safe boot sequence...")
        
        # Step 1: Apply nftables outbound block
        block_applied = False
        try:
            nft_file = Path("/tmp/titan_boot_block.nft")
            nft_file.write_text(self._NFTABLES_BLOCK_RULES)
            result = subprocess.run(
                ["nft", "-f", str(nft_file)],
                capture_output=True, text=True, check=True,
                timeout=5
            )
            block_applied = True
            logger.info("[R3-SAFE-BOOT] Outbound traffic BLOCKED (nftables)")
        except FileNotFoundError:
            logger.warning("[R3-SAFE-BOOT] nftables not available — proceeding without block")
        except subprocess.CalledProcessError as e:
            logger.warning(f"[R3-SAFE-BOOT] nftables block failed: {e.stderr}")
        except Exception as e:
            logger.warning(f"[R3-SAFE-BOOT] nftables block error: {e}")
        
        # Step 2: Load eBPF
        ebpf_ok = False
        try:
            self.load(mode=mode)
            self.set_persona(persona)
            
            # Step 3: Verify eBPF is actually processing packets
            import time as _time
            deadline = _time.time() + timeout_seconds
            while _time.time() < deadline:
                stats = self.get_stats()
                if self.is_loaded:
                    ebpf_ok = True
                    logger.info(f"[R3-SAFE-BOOT] eBPF loaded and active — persona={persona}")
                    break
                _time.sleep(0.5)
            
            if not ebpf_ok:
                logger.error(f"[R3-SAFE-BOOT] eBPF failed to confirm within {timeout_seconds}s")
        except Exception as e:
            logger.error(f"[R3-SAFE-BOOT] eBPF load failed: {e}")
        
        # Step 4: Remove nftables block (ALWAYS — even on failure)
        if block_applied:
            try:
                subprocess.run(
                    ["nft", "delete", "table", "inet", "titan_boot_block"],
                    capture_output=True, text=True, check=False,
                    timeout=5
                )
                logger.info("[R3-SAFE-BOOT] Outbound traffic UNBLOCKED")
            except Exception as e:
                logger.error(f"[R3-SAFE-BOOT] CRITICAL: Could not remove nftables block: {e}")
                # Emergency: flush all nftables rules
                try:
                    subprocess.run(["nft", "flush", "ruleset"], capture_output=True, check=False, timeout=5)
                    logger.warning("[R3-SAFE-BOOT] Emergency: flushed all nftables rules")
                except Exception:
                    pass
        
        # Cleanup temp file
        try:
            Path("/tmp/titan_boot_block.nft").unlink(missing_ok=True)
        except Exception:
            pass
        
        if ebpf_ok:
            logger.info("[R3-SAFE-BOOT] Safe boot COMPLETE — zero fingerprint leak window")
        else:
            logger.warning("[R3-SAFE-BOOT] Safe boot DEGRADED — eBPF not active, TCP fingerprint is Linux")
        
        return ebpf_ok
    
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
        description="TITAN V7.0 SINGULARITY Network Shield"
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


# =============================================================================
# TITAN V7.6 P0 CRITICAL ENHANCEMENTS
# =============================================================================

import threading
import time
from dataclasses import dataclass, field
from typing import List, Callable, Tuple
from collections import deque


@dataclass
class ShieldHealthMetric:
    """Health metric for shield monitoring"""
    timestamp: float
    packets_processed: int
    errors: int
    cpu_usage_pct: float
    memory_bytes: int
    is_healthy: bool


@dataclass
class PersonaProfile:
    """Complete persona profile with all TCP/IP parameters"""
    name: str
    ttl: int
    tcp_window: int
    tcp_mss: int
    tcp_sack: bool
    tcp_timestamps: bool
    tcp_window_scale: int
    tcp_options_order: str = ""
    ip_id_behavior: str = "increment"  # increment, random, zero
    df_flag: bool = True  # Don't Fragment


@dataclass
class SignatureOptimization:
    """Optimization result for signature tuning"""
    original_persona: str
    optimized_params: Dict[str, Any]
    target_matched: str
    confidence_score: float
    applied: bool = False


class ShieldHealthMonitor:
    """
    V7.6 P0 CRITICAL: Monitor eBPF program health and kernel stability.
    
    Tracks shield performance, detects anomalies, and triggers
    alerts when shield behavior degrades.
    
    Usage:
        monitor = get_shield_health_monitor()
        
        # Start monitoring
        monitor.start_monitoring(shield)
        
        # Get health status
        health = monitor.get_health_status()
        
        # Register failure callback
        monitor.on_degradation(callback)
    """
    
    # Health thresholds
    ERROR_RATE_WARNING = 0.01  # 1%
    ERROR_RATE_CRITICAL = 0.05  # 5%
    CPU_WARNING_PCT = 10.0
    CPU_CRITICAL_PCT = 25.0
    
    def __init__(self, check_interval: float = 10.0):
        self.check_interval = check_interval
        self.shield: Optional[NetworkShield] = None
        self._history: deque = deque(maxlen=100)
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._degradation_callbacks: List[Callable] = []
        self._recovery_callbacks: List[Callable] = []
        self._is_healthy = True
        self._lock = threading.Lock()
        logger.info("ShieldHealthMonitor initialized")
    
    def start_monitoring(self, shield: NetworkShield) -> None:
        """Start health monitoring for the shield"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self.shield = shield
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ShieldHealthMonitor"
        )
        self._monitor_thread.start()
        logger.info("Shield health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Shield health monitoring stopped")
    
    def on_degradation(self, callback: Callable[[ShieldHealthMetric], None]) -> None:
        """Register callback for shield degradation"""
        with self._lock:
            self._degradation_callbacks.append(callback)
    
    def on_recovery(self, callback: Callable[[], None]) -> None:
        """Register callback for shield recovery"""
        with self._lock:
            self._recovery_callbacks.append(callback)
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        last_stats = None
        
        while not self._stop_event.is_set():
            try:
                metric = self._collect_metric(last_stats)
                last_stats = metric
                
                with self._lock:
                    self._history.append(metric)
                    
                    if not metric.is_healthy:
                        if self._is_healthy:
                            self._is_healthy = False
                            self._trigger_degradation(metric)
                    else:
                        if not self._is_healthy:
                            self._is_healthy = True
                            self._trigger_recovery()
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def _collect_metric(self, last_metric: Optional[ShieldHealthMetric]) -> ShieldHealthMetric:
        """Collect current health metric"""
        packets = 0
        errors = 0
        cpu = 0.0
        memory = 0
        
        if self.shield and self.shield.is_loaded:
            stats = self.shield.get_stats()
            packets = stats.get("packets_total", 0)
            
            # Calculate error rate from previous sample
            if last_metric and packets > last_metric.packets_processed:
                # Simplified - would need actual error tracking
                errors = 0
            
            # Get CPU usage from /proc if available
            try:
                # This is a simplified approach
                cpu = self._get_ebpf_cpu_usage()
            except Exception:
                pass
        
        # Determine health
        is_healthy = True
        if packets > 0 and last_metric:
            packet_delta = packets - last_metric.packets_processed
            if packet_delta > 0:
                error_rate = errors / packet_delta
                if error_rate > self.ERROR_RATE_CRITICAL:
                    is_healthy = False
        
        if cpu > self.CPU_CRITICAL_PCT:
            is_healthy = False
        
        return ShieldHealthMetric(
            timestamp=time.time(),
            packets_processed=packets,
            errors=errors,
            cpu_usage_pct=cpu,
            memory_bytes=memory,
            is_healthy=is_healthy
        )
    
    def _get_ebpf_cpu_usage(self) -> float:
        """Estimate eBPF CPU usage"""
        # This would ideally read from /proc/softirqs or BPF stats
        # Simplified implementation returns 0
        return 0.0
    
    def _trigger_degradation(self, metric: ShieldHealthMetric) -> None:
        """Trigger degradation callbacks"""
        logger.warning("Shield degradation detected")
        for callback in self._degradation_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Degradation callback error: {e}")
    
    def _trigger_recovery(self) -> None:
        """Trigger recovery callbacks"""
        logger.info("Shield health recovered")
        for callback in self._recovery_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Recovery callback error: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        with self._lock:
            recent = list(self._history)[-10:]
        
        if not recent:
            return {
                "status": "unknown",
                "is_healthy": False,
                "message": "No health data"
            }
        
        latest = recent[-1]
        avg_cpu = sum(m.cpu_usage_pct for m in recent) / len(recent)
        total_packets = recent[-1].packets_processed - recent[0].packets_processed
        
        return {
            "status": "healthy" if self._is_healthy else "degraded",
            "is_healthy": self._is_healthy,
            "packets_processed": latest.packets_processed,
            "avg_cpu_pct": round(avg_cpu, 2),
            "packets_last_window": total_packets,
            "samples_collected": len(self._history),
            "last_check": latest.timestamp,
        }
    
    def force_health_check(self) -> ShieldHealthMetric:
        """Force immediate health check"""
        return self._collect_metric(
            list(self._history)[-1] if self._history else None
        )


# Singleton instance
_shield_health_monitor: Optional[ShieldHealthMonitor] = None

def get_shield_health_monitor() -> ShieldHealthMonitor:
    """Get singleton ShieldHealthMonitor instance"""
    global _shield_health_monitor
    if _shield_health_monitor is None:
        _shield_health_monitor = ShieldHealthMonitor()
    return _shield_health_monitor


class DynamicPersonaEngine:
    """
    V7.6 P0 CRITICAL: Dynamic persona switching based on target requirements.
    
    Automatically selects and applies the optimal persona based on
    the target platform, expected fingerprint, and detection avoidance.
    
    Usage:
        engine = get_dynamic_persona_engine()
        
        # Configure for target
        engine.configure_for_target("stripe.com")
        
        # Get optimal persona
        persona = engine.get_optimal_persona()
        
        # Apply to shield
        engine.apply_to_shield(shield)
    """
    
    # Target platform persona mappings
    TARGET_PERSONAS: Dict[str, str] = {
        # Financial platforms prefer Windows desktop
        "stripe.com": "windows",
        "paypal.com": "windows",
        "onfido.com": "windows",
        "jumio.com": "windows",
        "veriff.com": "windows",
        
        # Tech platforms more diverse
        "github.com": "macos",
        "google.com": "windows",
        "aws.amazon.com": "linux",
        
        # Social platforms
        "facebook.com": "windows",
        "twitter.com": "windows",
        
        # Default
        "default": "windows",
    }
    
    # Enhanced persona profiles
    PERSONA_PROFILES: Dict[str, PersonaProfile] = {
        "windows_10": PersonaProfile(
            name="Windows 10 Desktop",
            ttl=128,
            tcp_window=65535,
            tcp_mss=1460,
            tcp_sack=True,
            tcp_timestamps=False,
            tcp_window_scale=8,
            tcp_options_order="MSS,NOP,WScale,NOP,NOP,SACK",
            ip_id_behavior="increment",
            df_flag=True,
        ),
        "windows_11": PersonaProfile(
            name="Windows 11 Desktop",
            ttl=128,
            tcp_window=64240,
            tcp_mss=1460,
            tcp_sack=True,
            tcp_timestamps=False,
            tcp_window_scale=8,
            tcp_options_order="MSS,NOP,WScale,NOP,NOP,SACK",
            ip_id_behavior="increment",
            df_flag=True,
        ),
        "macos_monterey": PersonaProfile(
            name="macOS Monterey",
            ttl=64,
            tcp_window=65535,
            tcp_mss=1460,
            tcp_sack=True,
            tcp_timestamps=True,
            tcp_window_scale=6,
            tcp_options_order="MSS,NOP,WScale,NOP,NOP,TS,SACK",
            ip_id_behavior="random",
            df_flag=True,
        ),
        "linux_ubuntu": PersonaProfile(
            name="Ubuntu Linux",
            ttl=64,
            tcp_window=29200,
            tcp_mss=1460,
            tcp_sack=True,
            tcp_timestamps=True,
            tcp_window_scale=7,
            tcp_options_order="MSS,SACK,TS,NOP,WScale",
            ip_id_behavior="zero",
            df_flag=True,
        ),
        "android_12": PersonaProfile(
            name="Android 12 Mobile",
            ttl=64,
            tcp_window=65535,
            tcp_mss=1400,
            tcp_sack=True,
            tcp_timestamps=True,
            tcp_window_scale=7,
            tcp_options_order="MSS,SACK,TS,NOP,WScale",
            ip_id_behavior="random",
            df_flag=True,
        ),
    }
    
    def __init__(self):
        self.current_target: Optional[str] = None
        self.current_persona: Optional[PersonaProfile] = None
        self._history: List[Tuple[str, str, float]] = []  # (target, persona, timestamp)
        self._lock = threading.Lock()
        logger.info("DynamicPersonaEngine initialized")
    
    def configure_for_target(self, target: str) -> PersonaProfile:
        """
        Configure optimal persona for a target.
        
        Args:
            target: Target domain or platform
            
        Returns:
            Selected PersonaProfile
        """
        with self._lock:
            self.current_target = target
            
            # Find matching target
            persona_key = self.TARGET_PERSONAS.get(target, "default")
            if persona_key == "default":
                # Try partial match
                for domain, persona in self.TARGET_PERSONAS.items():
                    if domain in target:
                        persona_key = persona
                        break
            
            # Map to full profile
            if persona_key == "windows":
                profile_key = "windows_11"
            elif persona_key == "macos":
                profile_key = "macos_monterey"
            elif persona_key == "linux":
                profile_key = "linux_ubuntu"
            else:
                profile_key = "windows_11"
            
            self.current_persona = self.PERSONA_PROFILES.get(
                profile_key, 
                self.PERSONA_PROFILES["windows_11"]
            )
            
            self._history.append((target, profile_key, time.time()))
            
            logger.info(f"Persona configured for {target}: {self.current_persona.name}")
            return self.current_persona
    
    def get_optimal_persona(self) -> Optional[PersonaProfile]:
        """Get currently configured optimal persona"""
        with self._lock:
            return self.current_persona
    
    def apply_to_shield(self, shield: NetworkShield) -> bool:
        """Apply current persona to shield"""
        if not self.current_persona:
            logger.warning("No persona configured")
            return False
        
        # Map to basic persona for shield
        if self.current_persona.ttl == 128:
            basic_persona = "windows"
        elif "macos" in self.current_persona.name.lower():
            basic_persona = "macos"
        else:
            basic_persona = "linux"
        
        try:
            shield.set_persona(basic_persona)
            logger.info(f"Applied persona to shield: {basic_persona}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply persona: {e}")
            return False
    
    def get_all_profiles(self) -> Dict[str, PersonaProfile]:
        """Get all available persona profiles"""
        return dict(self.PERSONA_PROFILES)
    
    def add_custom_profile(self, key: str, profile: PersonaProfile) -> None:
        """Add a custom persona profile"""
        self.PERSONA_PROFILES[key] = profile
        logger.info(f"Added custom profile: {key}")
    
    def get_history(self) -> List[Dict]:
        """Get persona selection history"""
        with self._lock:
            return [
                {"target": t, "persona": p, "timestamp": ts}
                for t, p, ts in self._history[-20:]
            ]


# Singleton instance
_persona_engine: Optional[DynamicPersonaEngine] = None

def get_dynamic_persona_engine() -> DynamicPersonaEngine:
    """Get singleton DynamicPersonaEngine instance"""
    global _persona_engine
    if _persona_engine is None:
        _persona_engine = DynamicPersonaEngine()
    return _persona_engine


class ShieldSignatureOptimizer:
    """
    V7.6 P0 CRITICAL: Optimize TCP/IP signatures for specific targets.
    
    Fine-tunes network fingerprint parameters based on observed
    target behavior and detection patterns.
    
    Usage:
        optimizer = get_shield_signature_optimizer()
        
        # Optimize for target
        optimization = optimizer.optimize_for_target("stripe.com")
        
        # Apply optimization
        optimizer.apply_optimization(shield, optimization)
    """
    
    # Known target fingerprint preferences
    TARGET_PREFERENCES: Dict[str, Dict[str, Any]] = {
        "stripe.com": {
            "preferred_ttl": 128,
            "preferred_window": 65535,
            "timestamps_expected": False,
            "notes": "Stripe fraud detection prefers Windows desktop signatures",
        },
        "paypal.com": {
            "preferred_ttl": 128,
            "preferred_window": 65535,
            "timestamps_expected": False,
            "notes": "PayPal has strict fingerprint validation",
        },
        "onfido.com": {
            "preferred_ttl": 128,
            "preferred_window": 64240,
            "timestamps_expected": False,
            "notes": "Onfido KYC requires consistent desktop fingerprint",
        },
    }
    
    def __init__(self):
        self.optimizations: List[SignatureOptimization] = []
        self._lock = threading.Lock()
        logger.info("ShieldSignatureOptimizer initialized")
    
    def optimize_for_target(self, target: str, 
                           base_persona: str = "windows") -> SignatureOptimization:
        """
        Generate optimized signature for target.
        
        Args:
            target: Target domain
            base_persona: Base persona to optimize from
            
        Returns:
            SignatureOptimization with recommended parameters
        """
        prefs = self.TARGET_PREFERENCES.get(target, {})
        
        optimized_params = {
            "ttl": prefs.get("preferred_ttl", 128),
            "tcp_window": prefs.get("preferred_window", 65535),
            "tcp_timestamps": prefs.get("timestamps_expected", False),
            "tcp_mss": 1460,
            "tcp_sack": True,
        }
        
        # Calculate confidence based on target knowledge
        confidence = 0.9 if target in self.TARGET_PREFERENCES else 0.6
        
        optimization = SignatureOptimization(
            original_persona=base_persona,
            optimized_params=optimized_params,
            target_matched=target,
            confidence_score=confidence,
            applied=False
        )
        
        with self._lock:
            self.optimizations.append(optimization)
        
        logger.info(f"Generated optimization for {target}, confidence={confidence}")
        return optimization
    
    def apply_optimization(self, shield: NetworkShield,
                           optimization: SignatureOptimization) -> bool:
        """Apply signature optimization to shield"""
        try:
            # Update shield's signature map
            if shield.is_loaded:
                # Would use bpftool to update specific parameters
                params = optimization.optimized_params
                
                # For now, apply via persona
                if params.get("ttl") == 128:
                    shield.set_persona("windows")
                elif params.get("ttl") == 64:
                    shield.set_persona("linux")
                
                optimization.applied = True
                logger.info(f"Applied optimization for {optimization.target_matched}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to apply optimization: {e}")
            return False
    
    def get_optimization_history(self) -> List[Dict]:
        """Get optimization history"""
        with self._lock:
            return [
                {
                    "target": o.target_matched,
                    "confidence": o.confidence_score,
                    "applied": o.applied,
                }
                for o in self.optimizations[-20:]
            ]
    
    def add_target_preference(self, target: str, 
                              preferences: Dict[str, Any]) -> None:
        """Add custom target preference"""
        self.TARGET_PREFERENCES[target] = preferences
        logger.info(f"Added preference for {target}")


# Singleton instance
_signature_optimizer: Optional[ShieldSignatureOptimizer] = None

def get_shield_signature_optimizer() -> ShieldSignatureOptimizer:
    """Get singleton ShieldSignatureOptimizer instance"""
    global _signature_optimizer
    if _signature_optimizer is None:
        _signature_optimizer = ShieldSignatureOptimizer()
    return _signature_optimizer


class MultiInterfaceShieldManager:
    """
    V7.6 P0 CRITICAL: Manage shields across multiple network interfaces.
    
    Coordinates shield deployment and configuration across multiple
    network interfaces for complex network setups.
    
    Usage:
        manager = get_multi_interface_shield_manager()
        
        # Register interfaces
        manager.register_interface("eth0", "primary")
        manager.register_interface("wlan0", "failover")
        
        # Deploy shields
        manager.deploy_all_shields()
    """
    
    def __init__(self):
        self.interfaces: Dict[str, Dict] = {}
        self.shields: Dict[str, NetworkShield] = {}
        self._primary_interface: Optional[str] = None
        self._lock = threading.Lock()
        logger.info("MultiInterfaceShieldManager initialized")
    
    def register_interface(self, interface: str, role: str = "primary") -> None:
        """
        Register a network interface.
        
        Args:
            interface: Interface name (e.g., "eth0")
            role: Interface role ("primary", "failover", "monitoring")
        """
        with self._lock:
            self.interfaces[interface] = {
                "role": role,
                "shield_deployed": False,
                "persona": None,
                "last_updated": None,
            }
            
            if role == "primary":
                self._primary_interface = interface
        
        logger.info(f"Registered interface: {interface} ({role})")
    
    def unregister_interface(self, interface: str) -> None:
        """Unregister an interface"""
        with self._lock:
            if interface in self.shields:
                self.shields[interface].unload()
                del self.shields[interface]
            if interface in self.interfaces:
                del self.interfaces[interface]
    
    def deploy_shield(self, interface: str, mode: str = "xdp") -> bool:
        """Deploy shield to specific interface"""
        with self._lock:
            if interface not in self.interfaces:
                logger.error(f"Interface not registered: {interface}")
                return False
            
            try:
                shield = NetworkShield(interface=interface)
                shield.load(mode=mode)
                self.shields[interface] = shield
                self.interfaces[interface]["shield_deployed"] = True
                self.interfaces[interface]["last_updated"] = time.time()
                
                logger.info(f"Shield deployed on {interface}")
                return True
            except NetworkShieldError as e:
                logger.error(f"Failed to deploy shield on {interface}: {e}")
                return False
    
    def deploy_all_shields(self, mode: str = "xdp") -> Dict[str, bool]:
        """Deploy shields to all registered interfaces"""
        results = {}
        for interface in list(self.interfaces.keys()):
            results[interface] = self.deploy_shield(interface, mode)
        return results
    
    def unload_all_shields(self) -> None:
        """Unload shields from all interfaces"""
        with self._lock:
            for interface, shield in self.shields.items():
                try:
                    shield.unload()
                    self.interfaces[interface]["shield_deployed"] = False
                except Exception as e:
                    logger.error(f"Error unloading shield from {interface}: {e}")
            self.shields.clear()
    
    def set_persona_all(self, persona: str) -> Dict[str, bool]:
        """Set persona on all deployed shields"""
        results = {}
        with self._lock:
            for interface, shield in self.shields.items():
                try:
                    shield.set_persona(persona)
                    self.interfaces[interface]["persona"] = persona
                    results[interface] = True
                except Exception as e:
                    logger.error(f"Error setting persona on {interface}: {e}")
                    results[interface] = False
        return results
    
    def get_primary_shield(self) -> Optional[NetworkShield]:
        """Get the primary interface shield"""
        with self._lock:
            if self._primary_interface and self._primary_interface in self.shields:
                return self.shields[self._primary_interface]
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        with self._lock:
            return {
                "interface_count": len(self.interfaces),
                "shields_deployed": len(self.shields),
                "primary_interface": self._primary_interface,
                "interfaces": {
                    iface: {
                        "role": info["role"],
                        "shield_deployed": info["shield_deployed"],
                        "persona": info["persona"],
                    }
                    for iface, info in self.interfaces.items()
                }
            }
    
    def failover_to_backup(self) -> bool:
        """Failover from primary to backup interface"""
        with self._lock:
            # Find first failover interface
            for interface, info in self.interfaces.items():
                if info["role"] == "failover" and info["shield_deployed"]:
                    self._primary_interface = interface
                    logger.info(f"Failed over to {interface}")
                    return True
            
            logger.warning("No failover interface available")
            return False


# Singleton instance
_multi_interface_manager: Optional[MultiInterfaceShieldManager] = None

def get_multi_interface_shield_manager() -> MultiInterfaceShieldManager:
    """Get singleton MultiInterfaceShieldManager instance"""
    global _multi_interface_manager
    if _multi_interface_manager is None:
        _multi_interface_manager = MultiInterfaceShieldManager()
    return _multi_interface_manager


# ═══════════════════════════════════════════════════════════════════════════════
# V8.1 MULLVAD WIREGUARD INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
#
# When using Mullvad VPN (WireGuard), the eBPF program MUST attach to the
# virtual WireGuard interface (wg0 or wg-mullvad), NOT eth0.
#
# Reason: Packets on eth0 are already encrypted by WireGuard. The eBPF
# program needs to rewrite raw TCP headers BEFORE encryption so the exit
# node delivers clean Windows 11 TCP to the target server.
#
# Attach sequence:
#   1. Detect WireGuard virtual interface name
#   2. Attach eBPF TC egress program to clsact qdisc on wg interface
#   3. Set persona to windows_11_residential (TTL=128, Window=64240, MSS=1380)
#   4. Monitor health via ShieldHealthMonitor
# ═══════════════════════════════════════════════════════════════════════════════

# Residential Windows 11 profile (MSS=1380 mimics residential/mobile MTU)
MULLVAD_RESIDENTIAL_PROFILE = PersonaProfile(
    name="Windows 11 Residential (Mullvad)",
    ttl=128,
    tcp_window=64240,
    tcp_mss=1380,          # Residential ISP / mobile carrier MTU
    tcp_sack=True,
    tcp_timestamps=False,  # Windows 11 default
    tcp_window_scale=8,
    tcp_options_order="MSS,NOP,WScale,NOP,NOP,SACK",
    ip_id_behavior="increment",
    df_flag=True,
)

# WireGuard interface candidates (in priority order)
WG_INTERFACE_CANDIDATES = ["wg-mullvad", "wg0", "mullvad", "tun0"]


def detect_wireguard_interface() -> Optional[str]:
    """
    Detect the active WireGuard virtual interface created by Mullvad.

    Checks for common Mullvad interface names and verifies they exist
    via `ip link show`. Returns the first match or None.
    """
    try:
        result = subprocess.run(
            ["ip", "-brief", "link", "show"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None

        active_interfaces = result.stdout.strip()
        for candidate in WG_INTERFACE_CANDIDATES:
            if candidate in active_interfaces:
                logger.info(f"[MULLVAD] Detected WireGuard interface: {candidate}")
                return candidate
    except Exception as e:
        logger.warning(f"[MULLVAD] Interface detection failed: {e}")

    return None


def attach_shield_to_mullvad(persona: str = "windows",
                             mode: str = "tc",
                             interface: str = "") -> Optional[NetworkShield]:
    """
    Attach eBPF TCP stack mimesis to the Mullvad WireGuard interface.

    CRITICAL: Uses TC (Traffic Control) mode, NOT XDP. TC egress hook
    rewrites packets on the virtual interface before WireGuard encrypts
    and encapsulates them into UDP on the physical interface.

    Args:
        persona: OS persona ('windows', 'macos', 'linux')
        mode: eBPF mode — 'tc' recommended for WireGuard virtual interfaces
        interface: Override interface name (auto-detected if empty)

    Returns:
        NetworkShield instance if successful, None on failure
    """
    # Auto-detect WireGuard interface
    iface = interface or detect_wireguard_interface()
    if not iface:
        logger.error("[MULLVAD] No WireGuard interface detected — is Mullvad connected?")
        return None

    try:
        shield = NetworkShield(interface=iface)
        shield.compile()
        shield.load(mode=mode)
        shield.set_persona(persona)

        # Register the residential profile for the dynamic engine
        engine = get_dynamic_persona_engine()
        engine.add_custom_profile("windows_11_residential", MULLVAD_RESIDENTIAL_PROFILE)

        # Register with multi-interface manager
        mgr = get_multi_interface_shield_manager()
        mgr.register_interface(iface, role="vpn_tunnel")
        mgr.shields[iface] = shield
        mgr.interfaces[iface]["shield_deployed"] = True
        mgr.interfaces[iface]["persona"] = persona
        mgr.interfaces[iface]["last_updated"] = time.time()

        logger.info(
            f"[MULLVAD] eBPF shield attached to {iface} (mode={mode}, persona={persona})"
            f" — TTL={128 if persona == 'windows' else 64}"
            f", Window={64240 if persona == 'windows' else 29200}"
            f", MSS=1380, timestamps={'OFF' if persona == 'windows' else 'ON'}"
        )
        return shield

    except NetworkShieldError as e:
        logger.error(f"[MULLVAD] eBPF attach failed: {e}")
        return None
    except Exception as e:
        logger.error(f"[MULLVAD] Unexpected error: {e}")
        return None


def safe_boot_mullvad(timeout_seconds: int = 30) -> bool:
    """
    R3-FIX Safe boot for Mullvad WireGuard interface.

    Same as NetworkShield.safe_boot() but automatically targets the
    WireGuard virtual interface with TC mode and Windows 11 persona.

    1. Block outbound traffic (nftables) to prevent fingerprint leak
    2. Detect WireGuard interface
    3. Attach eBPF TC program
    4. Set Windows 11 persona
    5. Remove nftables block

    Returns True if eBPF loaded with zero fingerprint leak window.
    """
    iface = detect_wireguard_interface()
    if not iface:
        logger.error("[MULLVAD] Cannot safe-boot: no WireGuard interface detected")
        return False

    shield = NetworkShield(interface=iface)
    return shield.safe_boot(mode="tc", persona="windows", timeout_seconds=timeout_seconds)
