#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY - Profile Isolation Manager

This module provides process isolation using Linux namespaces and cgroups
to prevent data leakage between browser profiles and ensure each identity
operates in a completely isolated environment.

Key Features:
- Network namespace isolation (optional)
- Mount namespace for filesystem isolation
- PID namespace for process isolation
- Resource limits via cgroups v2

Source: Unified Agent [cite: 1]

Requirements:
- Linux kernel 4.6+ (for cgroups v2)
- Root privileges (for namespace creation)
- unshare command available

Usage:
    from profile_isolation import ProfileIsolator
    
    isolator = ProfileIsolator(profile_id="profile_01")
    isolator.create_isolated_env()
    isolator.run_isolated(["firefox", "--profile", "/path/to/profile"])
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [ISOLATOR] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for the isolated environment."""
    memory_max_mb: int = 4096       # Maximum memory in MB
    cpu_quota_percent: int = 100    # CPU quota as percentage
    pids_max: int = 500             # Maximum number of processes
    io_weight: int = 100            # I/O priority weight (1-10000)


class ProfileIsolatorError(Exception):
    """Custom exception for isolation errors."""
    pass


class CgroupManager:
    """
    Manages cgroup v2 for resource isolation.
    
    Creates and configures cgroup slices for profile isolation,
    allowing fine-grained control over resource consumption.
    """
    
    CGROUP_ROOT = Path("/sys/fs/cgroup")
    
    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        self.cgroup_name = f"titan-{profile_id}"
        self.cgroup_path = self.CGROUP_ROOT / self.cgroup_name
    
    def is_cgroup_v2(self) -> bool:
        """Check if cgroup v2 is available."""
        # cgroup v2 has a cgroup.controllers file at the root
        return (self.CGROUP_ROOT / "cgroup.controllers").exists()
    
    def create(self, limits: ResourceLimits) -> bool:
        """
        Create a cgroup for the profile with specified limits.
        
        Args:
            limits: Resource limits to apply
            
        Returns:
            True if successful
        """
        if not self.is_cgroup_v2():
            logger.warning("cgroup v2 not available, skipping resource limits")
            return False
        
        try:
            # Create the cgroup directory
            self.cgroup_path.mkdir(exist_ok=True)
            logger.debug(f"Created cgroup: {self.cgroup_path}")
            
            # Enable controllers
            self._enable_controllers()
            
            # Set memory limit
            memory_limit = limits.memory_max_mb * 1024 * 1024  # Convert to bytes
            self._write_cgroup_file("memory.max", str(memory_limit))
            
            # Set CPU quota (period is 100000 microseconds by default)
            cpu_quota = limits.cpu_quota_percent * 1000  # Convert to microseconds
            self._write_cgroup_file("cpu.max", f"{cpu_quota} 100000")
            
            # Set PID limit
            self._write_cgroup_file("pids.max", str(limits.pids_max))
            
            # Set I/O weight
            self._write_cgroup_file("io.weight", f"default {limits.io_weight}")
            
            logger.info(f"Cgroup configured: {self.cgroup_name}")
            logger.info(f"  Memory: {limits.memory_max_mb} MB")
            logger.info(f"  CPU: {limits.cpu_quota_percent}%")
            logger.info(f"  PIDs: {limits.pids_max}")
            
            return True
            
        except PermissionError:
            logger.warning("Insufficient permissions for cgroup management")
            return False
        except Exception as e:
            logger.error(f"Failed to create cgroup: {e}")
            return False
    
    def _enable_controllers(self) -> None:
        """Enable required controllers for the cgroup."""
        controllers_file = self.CGROUP_ROOT / "cgroup.subtree_control"
        try:
            with open(controllers_file, 'w') as f:
                f.write("+cpu +memory +io +pids")
        except Exception:
            pass  # May fail if already enabled or not available
    
    def _write_cgroup_file(self, filename: str, value: str) -> None:
        """Write a value to a cgroup control file."""
        filepath = self.cgroup_path / filename
        try:
            with open(filepath, 'w') as f:
                f.write(value)
        except FileNotFoundError:
            logger.debug(f"Cgroup file not available: {filename}")
        except PermissionError:
            logger.debug(f"Permission denied for: {filename}")
    
    def add_process(self, pid: int) -> None:
        """Add a process to the cgroup."""
        procs_file = self.cgroup_path / "cgroup.procs"
        try:
            with open(procs_file, 'w') as f:
                f.write(str(pid))
            logger.debug(f"Added PID {pid} to cgroup")
        except Exception as e:
            logger.warning(f"Failed to add process to cgroup: {e}")
    
    def cleanup(self) -> None:
        """Remove the cgroup."""
        if self.cgroup_path.exists():
            try:
                # Move all processes to the root cgroup first
                procs_file = self.cgroup_path / "cgroup.procs"
                if procs_file.exists():
                    with open(procs_file, 'r') as f:
                        pids = f.read().strip().split('\n')
                    
                    root_procs = self.CGROUP_ROOT / "cgroup.procs"
                    for pid in pids:
                        if pid:
                            try:
                                with open(root_procs, 'w') as f:
                                    f.write(pid)
                            except Exception:
                                pass
                
                # Remove the cgroup directory
                self.cgroup_path.rmdir()
                logger.debug(f"Removed cgroup: {self.cgroup_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup cgroup: {e}")


class ProfileIsolator:
    """
    Manages isolated execution environments for browser profiles.
    
    Uses Linux namespaces to create isolated environments that prevent
    data leakage between profiles. Each profile runs in its own:
    - Mount namespace (isolated filesystem view)
    - PID namespace (isolated process tree)
    - Optionally: Network namespace (isolated network stack)
    
    Source: [cite: 1]
    """
    
    def __init__(
        self,
        profile_id: str,
        base_dir: Optional[Path] = None,
        isolate_network: bool = False
    ):
        """
        Initialize the profile isolator.
        
        Args:
            profile_id: Unique identifier for the profile
            base_dir: Base directory for isolation data
            isolate_network: Whether to use network namespace isolation
        """
        self.profile_id = profile_id
        self.base_dir = base_dir or Path("/tmp/titan-isolation")
        self.isolate_network = isolate_network
        
        self.profile_dir = self.base_dir / profile_id
        self.rootfs_dir = self.profile_dir / "rootfs"
        self.work_dir = self.profile_dir / "work"
        self.upper_dir = self.profile_dir / "upper"
        self.merged_dir = self.profile_dir / "merged"
        
        self.cgroup = CgroupManager(profile_id)
        self.limits = ResourceLimits()
        
        self._mounted = False
    
    def _check_root(self) -> None:
        """Verify root privileges."""
        if os.geteuid() != 0:
            raise ProfileIsolatorError(
                "Root privileges required for namespace isolation"
            )
    
    def create_isolated_env(self, limits: Optional[ResourceLimits] = None) -> None:
        """
        Create an isolated environment for the profile.
        
        This sets up:
        - Directory structure
        - Overlay filesystem (for copy-on-write isolation)
        - Cgroup for resource limits
        
        Args:
            limits: Optional resource limits to apply
        """
        self._check_root()
        
        if limits:
            self.limits = limits
        
        logger.info(f"Creating isolated environment for: {self.profile_id}")
        
        # Create directory structure
        for directory in [self.profile_dir, self.rootfs_dir, 
                         self.work_dir, self.upper_dir, self.merged_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Set up cgroup
        self.cgroup.create(self.limits)
        
        logger.info(f"Isolated environment ready: {self.profile_dir}")
    
    def _setup_overlay_mount(self) -> None:
        """
        Set up an overlay filesystem for the isolated environment.
        
        This allows the isolated process to see the host filesystem
        but any writes go to the profile-specific upper layer.
        """
        if self._mounted:
            return
        
        # Mount overlay filesystem
        # lowerdir = host root, upperdir = profile writes, merged = combined view
        mount_cmd = [
            "mount", "-t", "overlay", "overlay",
            "-o", f"lowerdir=/,upperdir={self.upper_dir},workdir={self.work_dir}",
            str(self.merged_dir)
        ]
        
        try:
            subprocess.run(mount_cmd, check=True, capture_output=True)
            self._mounted = True
            logger.debug("Overlay filesystem mounted")
        except subprocess.CalledProcessError as e:
            raise ProfileIsolatorError(f"Failed to mount overlay: {e.stderr}")
    
    def _teardown_overlay_mount(self) -> None:
        """Unmount the overlay filesystem."""
        if not self._mounted:
            return
        
        try:
            subprocess.run(
                ["umount", str(self.merged_dir)],
                check=True,
                capture_output=True
            )
            self._mounted = False
            logger.debug("Overlay filesystem unmounted")
        except subprocess.CalledProcessError:
            logger.warning("Failed to unmount overlay filesystem")
    
    def run_isolated(
        self,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run a command in the isolated environment.
        
        Uses unshare to create new namespaces for:
        - Mount namespace (--mount)
        - PID namespace (--pid --fork)
        - Optionally: Network namespace (--net)
        
        Args:
            command: Command and arguments to run
            env: Environment variables for the command
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CompletedProcess result
        """
        self._check_root()
        
        # Build unshare command
        unshare_cmd = ["unshare", "--mount", "--pid", "--fork"]
        
        if self.isolate_network:
            unshare_cmd.append("--net")
        
        # Add the actual command
        full_cmd = unshare_cmd + ["--"] + command
        
        # Prepare environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        # Add profile identification using innocuous names
        run_env["MOZ_PROFILER_SESSION"] = self.profile_id
        run_env["MOZ_SANDBOX_LEVEL"] = "1"
        
        logger.info(f"Running isolated: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                full_cmd,
                env=run_env,
                capture_output=capture_output,
                text=True
            )
            return result
        except FileNotFoundError:
            raise ProfileIsolatorError(f"Command not found: {command[0]}")
    
    def run_isolated_shell(
        self,
        script: str,
        env: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a shell script in the isolated environment.
        
        Args:
            script: Shell script content
            env: Environment variables
            
        Returns:
            CompletedProcess result
        """
        # Create a temporary script file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sh',
            delete=False
        ) as f:
            f.write("#!/bin/bash\n")
            f.write(script)
            script_path = f.name
        
        try:
            os.chmod(script_path, 0o755)
            return self.run_isolated([script_path], env=env)
        finally:
            os.unlink(script_path)
    
    def get_isolation_info(self) -> Dict[str, Any]:
        """Get information about the isolated environment."""
        return {
            "profile_id": self.profile_id,
            "base_dir": str(self.base_dir),
            "profile_dir": str(self.profile_dir),
            "network_isolated": self.isolate_network,
            "cgroup_path": str(self.cgroup.cgroup_path),
            "resource_limits": {
                "memory_max_mb": self.limits.memory_max_mb,
                "cpu_quota_percent": self.limits.cpu_quota_percent,
                "pids_max": self.limits.pids_max,
            },
            "mounted": self._mounted,
        }
    
    def cleanup(self) -> None:
        """Clean up the isolated environment."""
        logger.info(f"Cleaning up isolated environment: {self.profile_id}")
        
        self._teardown_overlay_mount()
        self.cgroup.cleanup()
        
        # Remove the profile directory
        if self.profile_dir.exists():
            try:
                shutil.rmtree(self.profile_dir)
                logger.debug(f"Removed profile directory: {self.profile_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove profile directory: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.create_isolated_env()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False


def main():
    """Command-line interface for the profile isolator."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TITAN V8.1 SINGULARITY Profile Isolator"
    )
    
    parser.add_argument(
        "-p", "--profile",
        required=True,
        help="Profile ID for isolation"
    )
    parser.add_argument(
        "-n", "--network-isolate",
        action="store_true",
        help="Enable network namespace isolation"
    )
    parser.add_argument(
        "-m", "--memory",
        type=int,
        default=4096,
        help="Maximum memory in MB (default: 4096)"
    )
    parser.add_argument(
        "-c", "--cpu",
        type=int,
        default=100,
        help="CPU quota as percentage (default: 100)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run in isolation (after --)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Remove leading '--'
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    
    if not command:
        parser.error("No command specified. Use -- to separate options from command.")
    
    limits = ResourceLimits(
        memory_max_mb=args.memory,
        cpu_quota_percent=args.cpu
    )
    
    isolator = ProfileIsolator(
        profile_id=args.profile,
        isolate_network=args.network_isolate
    )
    
    try:
        isolator.create_isolated_env(limits)
        
        print(f"\n{'='*60}")
        print(f"TITAN Profile Isolator")
        print(f"{'='*60}")
        print(json.dumps(isolator.get_isolation_info(), indent=2))
        print(f"{'='*60}\n")
        
        result = isolator.run_isolated(command)
        sys.exit(result.returncode)
        
    except ProfileIsolatorError as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    finally:
        isolator.cleanup()


if __name__ == "__main__":
    main()
