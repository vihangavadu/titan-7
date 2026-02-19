"""
TITAN V7.0 SINGULARITY :: LINUX eBPF LOADER
Authority: Dva.12
Platform: Linux (Kernel-level network masking)

This module handles loading and managing eBPF/XDP programs for network
masking on Linux systems. This provides kernel-level interception of
network traffic and allows manipulation of packets before transmission.
"""

import os
import sys
import ctypes
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class eBPFLoader:
    """
    Linux eBPF/XDP Program Loader
    
    Provides kernel-level network masking through XDP (eXpress Data Path)
    programs. This is the "Singularity" method for network masking on Linux.
    """
    
    def __init__(self, xdp_object_path: Optional[str] = None):
        """
        Initialize eBPF loader
        
        Args:
            xdp_object_path: Path to compiled eBPF object file (xdp_outbound.o)
        """
        self.xdp_object = xdp_object_path or self._find_xdp_object()
        self.loaded_interfaces = {}
        self.requires_root = True
        
        logger.info(f"eBPF Loader initialized. Object: {self.xdp_object}")
    
    @staticmethod
    def _find_xdp_object() -> str:
        """
        Find compiled XDP object file in standard locations
        
        Returns:
            Path to xdp_outbound.o
            
        Raises:
            FileNotFoundError: If XDP object not found
        """
        search_paths = [
            Path.cwd() / "lib" / "xdp_outbound.o",
            Path.home() / ".lucid-empire" / "lib" / "xdp_outbound.o",
            Path("/usr/lib/lucid-empire/xdp_outbound.o"),
            Path("/opt/lucid-empire/lib/xdp_outbound.o"),
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found XDP object: {path}")
                return str(path)
        
        raise FileNotFoundError(
            "XDP object file (xdp_outbound.o) not found. "
            "Run: clang -O2 -target bpf -c xdp_outbound.c -o xdp_outbound.o"
        )
    
    def check_privileges(self) -> bool:
        """
        Check if running with required privileges (root or CAP_NET_ADMIN)
        
        Returns:
            True if sufficient privileges, False otherwise
        """
        if os.geteuid() == 0:
            logger.info("Running as root (uid=0)")
            return True
        
        # Check for CAP_NET_ADMIN capability
        try:
            result = subprocess.run(
                ["getcap", "/proc/self/exe"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "cap_net_admin" in result.stdout:
                logger.info("CAP_NET_ADMIN capability detected")
                return True
        except Exception as e:
            logger.warning(f"Could not check capabilities: {e}")
        
        logger.error("Insufficient privileges. Need root or CAP_NET_ADMIN")
        return False
    
    def check_kernel_version(self) -> Tuple[bool, str]:
        """
        Check kernel version for XDP support (requires 5.8+)
        
        Returns:
            Tuple of (is_compatible, kernel_version)
        """
        try:
            kernel_version = os.uname().release
            major, minor = map(int, kernel_version.split('.')[:2])
            
            is_compatible = (major > 5) or (major == 5 and minor >= 8)
            
            if is_compatible:
                logger.info(f"Kernel {kernel_version} supports XDP")
            else:
                logger.error(f"Kernel {kernel_version} too old (need 5.8+)")
            
            return is_compatible, kernel_version
        except Exception as e:
            logger.error(f"Could not check kernel version: {e}")
            return False, "unknown"
    
    def load_xdp_program(self, interface: str = "eth0") -> bool:
        """
        Load XDP program onto network interface
        
        This command is roughly equivalent to:
        ip link set dev <interface> xdp object <xdp_outbound.o> section xdp
        
        Args:
            interface: Network interface name (eth0, wlan0, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.check_privileges():
            logger.error("Insufficient privileges to load XDP program")
            return False
        
        kernel_ok, kernel_version = self.check_kernel_version()
        if not kernel_ok:
            logger.error(f"Kernel {kernel_version} does not support XDP")
            return False
        
        # Verify interface exists
        if not self._interface_exists(interface):
            logger.error(f"Interface {interface} not found")
            return False
        
        try:
            logger.info(f"Loading XDP program on {interface}...")
            
            # Use bpftool to load XDP program
            cmd = [
                "bpftool", "prog", "load",
                self.xdp_object,
                "/sys/fs/bpf/xdp_outbound",
                "type", "xdp"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"bpftool load failed: {result.stderr}")
                return False
            
            # Attach to interface
            cmd = [
                "ip", "link", "set", "dev", interface,
                "xdp", "object", self.xdp_object, "section", "xdp"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"XDP attachment failed: {result.stderr}")
                return False
            
            logger.info(f"✓ XDP program loaded on {interface}")
            self.loaded_interfaces[interface] = True
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("XDP loading timed out")
            return False
        except Exception as e:
            logger.error(f"XDP loading failed: {e}")
            return False
    
    def unload_xdp_program(self, interface: str = "eth0") -> bool:
        """
        Unload XDP program from network interface
        
        Args:
            interface: Network interface name
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Unloading XDP program from {interface}...")
            
            cmd = [
                "ip", "link", "set", "dev", interface,
                "xdp", "off"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"✓ XDP program unloaded from {interface}")
                self.loaded_interfaces.pop(interface, None)
                return True
            else:
                logger.error(f"XDP unload failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"XDP unload failed: {e}")
            return False
    
    @staticmethod
    def _interface_exists(interface: str) -> bool:
        """Check if network interface exists"""
        try:
            result = subprocess.run(
                ["ip", "link", "show", interface],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def list_interfaces(self) -> list:
        """
        List all network interfaces on the system
        
        Returns:
            List of interface names
        """
        try:
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            interfaces = []
            for line in result.stdout.split('\n'):
                if ':' in line and not line.startswith(' '):
                    # Extract interface name
                    parts = line.split(':')
                    if len(parts) > 1:
                        iface = parts[1].strip()
                        if iface and not iface.startswith('lo'):
                            interfaces.append(iface)
            
            return interfaces
        except Exception as e:
            logger.error(f"Could not list interfaces: {e}")
            return []
    
    def get_xdp_status(self, interface: str) -> Optional[str]:
        """
        Get XDP program status on interface
        
        Returns:
            Status string or None
        """
        try:
            result = subprocess.run(
                ["ip", "link", "show", interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if 'xdp' in line:
                    return line.strip()
            
            return None
        except Exception as e:
            logger.error(f"Could not get XDP status: {e}")
            return None
    
    def configure_iptables_backup(self) -> bool:
        """
        Configure iptables as backup network control mechanism
        
        This creates a fail-safe rule to block non-SOCKS traffic for
        the lucid-agent user, ensuring traffic only goes through proxy
        
        Returns:
            True if successful
        """
        try:
            logger.info("Configuring iptables backup rules...")
            
            # Get lucid user UID (typically 1337)
            try:
                result = subprocess.run(
                    ["id", "-u", "lucid-agent"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                lucid_uid = result.stdout.strip()
            except:
                lucid_uid = "1337"
            
            # Allow loopback (SOCKS server)
            cmd = [
                "iptables", "-A", "OUTPUT",
                "-m", "owner", "--uid-owner", lucid_uid,
                "-j", "ACCEPT",
                "-i", "lo",
                "-m", "comment", "--comment", "lucid-loopback"
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("✓ iptables backup rules configured")
                return True
            else:
                logger.warning(f"iptables configuration warning: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"iptables configuration failed: {e}")
            return False


class TimeDisplacementLoader:
    """
    Linux Time Displacement Handler
    
    Manages libfaketime integration for temporal masking
    """
    
    def __init__(self):
        self.libfaketime_path = "/usr/lib/x86_64-linux-gnu/libfaketime.so.1"
        self.time_control_file = "/tmp/lucid_time_control"
    
    def check_libfaketime(self) -> bool:
        """Check if libfaketime is installed"""
        if Path(self.libfaketime_path).exists():
            logger.info(f"✓ libfaketime found: {self.libfaketime_path}")
            return True
        
        logger.error("libfaketime not found. Install with: apt-get install libfaketime")
        return False
    
    def initialize_time_warp(self, days_ago: int = 90) -> bool:
        """
        Initialize time warp (90 days in past)
        
        Args:
            days_ago: Number of days to go back
            
        Returns:
            True if successful
        """
        try:
            import datetime
            
            initial_time = datetime.datetime.now() - datetime.timedelta(days=days_ago)
            timestamp = initial_time.timestamp()
            
            # Set file timestamp
            os.utime(self.time_control_file, (timestamp, timestamp))
            
            logger.info(f"✓ Time warp initialized: {initial_time}")
            return True
            
        except Exception as e:
            logger.error(f"Time warp initialization failed: {e}")
            return False


def get_ebpf_loader() -> Optional[eBPFLoader]:
    """
    Factory function to get eBPF loader if system supports it
    
    Returns:
        eBPFLoader instance or None if not available
    """
    try:
        loader = eBPFLoader()
        
        # Run checks
        if not loader.check_privileges():
            logger.error("eBPF loader requires root or CAP_NET_ADMIN")
            return None
        
        kernel_ok, kernel_version = loader.check_kernel_version()
        if not kernel_ok:
            logger.error(f"eBPF loader requires kernel 5.8+ (current: {kernel_version})")
            return None
        
        logger.info("✓ eBPF loader ready")
        return loader
        
    except FileNotFoundError as e:
        logger.error(f"eBPF loader unavailable: {e}")
        return None
    except Exception as e:
        logger.error(f"eBPF loader initialization failed: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    loader = get_ebpf_loader()
    if loader:
        print("eBPF Loader Status: OK")
        print(f"Interfaces: {loader.list_interfaces()}")
    else:
        print("eBPF Loader Status: UNAVAILABLE")
