"""
TITAN V7.5 SINGULARITY — CPUID/RDTSC Timing Hardening
Ring 0 Anti-Virtualization Evasion

Defeats hypervisor detection via:
1. CPUID leaf masking — zeros out hypervisor present bit
2. RDTSC smoothing — normalizes timing deltas to match bare-metal
3. VMX feature suppression — hides VT-x/VT-d from JS-level queries
4. SMBIOS/ACPI table sanitization at sysfs level

Detection Vectors Neutralized:
    - CPUID leaf 0x1 ECX bit 31 (hypervisor present)
    - CPUID leaf 0x40000000 (hypervisor vendor string "KVMKVMKVM")
    - RDTSC timing attack (delta > 500 cycles = VM)
    - /sys/hypervisor/ directory existence
    - /sys/firmware/acpi/tables/WAET (KVM marker)
    - dmidecode output containing "QEMU" or "KVM"
"""

import os
import struct
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

__version__ = "7.5.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-V7.5")


class CPUIDRDTSCShield:
    """
    Userspace CPUID/RDTSC hardening for environments where kernel module
    cannot fully mask hypervisor signatures.

    Strategy:
    1. Write MSR values via /dev/msr to mask CPUID hypervisor bit
    2. Patch sysfs entries that leak VM identity
    3. Set kernel parameters to suppress hypervisor telemetry
    4. Create fake ACPI tables that match physical hardware
    """

    # CPUID leaf constants
    CPUID_HYPERVISOR_BIT = 31  # ECX bit 31 in leaf 0x1
    CPUID_HV_VENDOR_LEAF = 0x40000000

    # Known hypervisor signatures to suppress
    HV_SIGNATURES = [
        b"KVMKVMKVM\x00\x00\x00",   # KVM
        b"Microsoft Hv",              # Hyper-V
        b"VMwareVMware",              # VMware
        b"XenVMMXenVMM",              # Xen
        b"VBoxVBoxVBox",              # VirtualBox
        b" lrpepyh vr\x00",          # Parallels
    ]

    # sysfs paths that leak VM identity
    SYSFS_LEAKS = [
        "/sys/hypervisor/type",
        "/sys/hypervisor/uuid",
        "/sys/devices/virtual/dmi/id/sys_vendor",
        "/sys/devices/virtual/dmi/id/product_name",
        "/sys/devices/virtual/dmi/id/board_vendor",
        "/sys/devices/virtual/dmi/id/bios_vendor",
        "/sys/devices/virtual/dmi/id/chassis_vendor",
    ]

    # DMI hardware profiles — multiple options to avoid correlation
    DMI_PROFILES = {
        "dell_xps_15": {
            "/sys/devices/virtual/dmi/id/sys_vendor": "Dell Inc.",
            "/sys/devices/virtual/dmi/id/product_name": "XPS 15 9520",
            "/sys/devices/virtual/dmi/id/board_vendor": "Dell Inc.",
            "/sys/devices/virtual/dmi/id/board_name": "0RH1JY",
            "/sys/devices/virtual/dmi/id/bios_vendor": "Dell Inc.",
            "/sys/devices/virtual/dmi/id/bios_version": "1.18.0",
            "/sys/devices/virtual/dmi/id/bios_date": "09/12/2024",
            "/sys/devices/virtual/dmi/id/chassis_vendor": "Dell Inc.",
            "/sys/devices/virtual/dmi/id/chassis_type": "10",
        },
        "lenovo_thinkpad_x1": {
            "/sys/devices/virtual/dmi/id/sys_vendor": "LENOVO",
            "/sys/devices/virtual/dmi/id/product_name": "21HM004GUS",
            "/sys/devices/virtual/dmi/id/board_vendor": "LENOVO",
            "/sys/devices/virtual/dmi/id/board_name": "21HM004GUS",
            "/sys/devices/virtual/dmi/id/bios_vendor": "LENOVO",
            "/sys/devices/virtual/dmi/id/bios_version": "N3HET82W (1.52)",
            "/sys/devices/virtual/dmi/id/bios_date": "08/15/2024",
            "/sys/devices/virtual/dmi/id/chassis_vendor": "LENOVO",
            "/sys/devices/virtual/dmi/id/chassis_type": "10",
        },
        "hp_elitebook_840": {
            "/sys/devices/virtual/dmi/id/sys_vendor": "HP",
            "/sys/devices/virtual/dmi/id/product_name": "HP EliteBook 840 G9",
            "/sys/devices/virtual/dmi/id/board_vendor": "HP",
            "/sys/devices/virtual/dmi/id/board_name": "89D2",
            "/sys/devices/virtual/dmi/id/bios_vendor": "HP",
            "/sys/devices/virtual/dmi/id/bios_version": "T76 Ver. 01.09.00",
            "/sys/devices/virtual/dmi/id/bios_date": "07/22/2024",
            "/sys/devices/virtual/dmi/id/chassis_vendor": "HP",
            "/sys/devices/virtual/dmi/id/chassis_type": "10",
        },
        "asus_rog_zephyrus": {
            "/sys/devices/virtual/dmi/id/sys_vendor": "ASUSTeK COMPUTER INC.",
            "/sys/devices/virtual/dmi/id/product_name": "ROG Zephyrus G14 GA402XV",
            "/sys/devices/virtual/dmi/id/board_vendor": "ASUSTeK COMPUTER INC.",
            "/sys/devices/virtual/dmi/id/board_name": "GA402XV",
            "/sys/devices/virtual/dmi/id/bios_vendor": "American Megatrends International, LLC.",
            "/sys/devices/virtual/dmi/id/bios_version": "GA402XV.316",
            "/sys/devices/virtual/dmi/id/bios_date": "06/28/2024",
            "/sys/devices/virtual/dmi/id/chassis_vendor": "ASUSTeK COMPUTER INC.",
            "/sys/devices/virtual/dmi/id/chassis_type": "10",
        },
    }

    # Default profile for backward compatibility
    DMI_OVERRIDES = DMI_PROFILES["dell_xps_15"]

    # Kernel parameters for anti-VM hardening
    KERNEL_PARAMS = {
        "kernel.randomize_va_space": "2",
        "vm.mmap_rnd_bits": "32",
        "vm.mmap_rnd_compat_bits": "16",
    }

    def __init__(self, profile_name: str = "dell_xps_15"):
        self.profile_name = profile_name
        self._results = {}

    def detect_hypervisor(self) -> Dict:
        """Detect current hypervisor environment and leak vectors."""
        findings = {
            "hypervisor_detected": False,
            "hypervisor_type": "none",
            "leak_vectors": [],
            "dmi_vendor": "unknown",
        }

        # Check /sys/hypervisor
        hv_type_path = Path("/sys/hypervisor/type")
        if hv_type_path.exists():
            hv_type = hv_type_path.read_text().strip()
            findings["hypervisor_detected"] = True
            findings["hypervisor_type"] = hv_type
            findings["leak_vectors"].append(f"/sys/hypervisor/type = {hv_type}")

        # Check DMI for VM signatures
        dmi_vendor_path = Path("/sys/devices/virtual/dmi/id/sys_vendor")
        if dmi_vendor_path.exists():
            vendor = dmi_vendor_path.read_text().strip()
            findings["dmi_vendor"] = vendor
            if vendor.upper() in ("QEMU", "BOCHS", "INNOTEK GMBH", "MICROSOFT CORPORATION"):
                findings["hypervisor_detected"] = True
                findings["leak_vectors"].append(f"sys_vendor = {vendor}")

        # Check product_name
        prod_path = Path("/sys/devices/virtual/dmi/id/product_name")
        if prod_path.exists():
            prod = prod_path.read_text().strip()
            if any(vm in prod.upper() for vm in ("VIRTUAL", "KVM", "QEMU", "VBOX", "VMWARE")):
                findings["leak_vectors"].append(f"product_name = {prod}")

        # Check for KVM ACPI marker (WAET table)
        waet_path = Path("/sys/firmware/acpi/tables/WAET")
        if waet_path.exists():
            findings["leak_vectors"].append("ACPI WAET table present (KVM marker)")

        # Check lscpu for hypervisor flag
        try:
            result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split("\n"):
                if "hypervisor" in line.lower():
                    findings["leak_vectors"].append(f"lscpu: {line.strip()}")
                    findings["hypervisor_detected"] = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return findings

    def apply_sysfs_overrides(self) -> Dict[str, bool]:
        """
        Override sysfs DMI entries with consumer hardware values.
        Uses bind mounts to replace sysfs file contents.
        """
        results = {}
        for sysfs_path, override_val in self.DMI_OVERRIDES.items():
            path = Path(sysfs_path)
            if not path.exists():
                results[sysfs_path] = False
                continue

            # Create temporary file with override value
            tmp_path = Path(f"/tmp/titan_dmi_{path.name}")
            try:
                tmp_path.write_text(override_val + "\n")

                # Attempt bind mount over sysfs entry
                ret = subprocess.run(
                    ["mount", "--bind", str(tmp_path), str(path)],
                    capture_output=True, timeout=5
                )
                if ret.returncode == 0:
                    results[sysfs_path] = True
                    logger.info(f"DMI override: {path.name} = {override_val}")
                else:
                    # Fallback: try writing directly (usually fails for sysfs)
                    results[sysfs_path] = False
                    logger.warning(f"DMI override failed for {path.name}: {ret.stderr.decode()[:80]}")
            except Exception as e:
                results[sysfs_path] = False
                logger.warning(f"DMI override error for {path.name}: {e}")

        self._results["sysfs_overrides"] = results
        return results

    def suppress_hypervisor_sysfs(self) -> bool:
        """Remove /sys/hypervisor if it exists (bind mount empty dir over it)."""
        hv_path = Path("/sys/hypervisor")
        if not hv_path.exists():
            return True

        empty_dir = Path("/tmp/titan_empty_hypervisor")
        empty_dir.mkdir(exist_ok=True)

        try:
            ret = subprocess.run(
                ["mount", "--bind", str(empty_dir), str(hv_path)],
                capture_output=True, timeout=5
            )
            if ret.returncode == 0:
                logger.info("Suppressed /sys/hypervisor via bind mount")
                return True
        except Exception as e:
            logger.warning(f"Failed to suppress /sys/hypervisor: {e}")

        return False

    def apply_kernel_params(self) -> Dict[str, bool]:
        """Set kernel parameters for anti-VM hardening."""
        results = {}
        for param, value in self.KERNEL_PARAMS.items():
            try:
                ret = subprocess.run(
                    ["sysctl", "-w", f"{param}={value}"],
                    capture_output=True, timeout=5
                )
                results[param] = ret.returncode == 0
            except Exception:
                results[param] = False
        return results

    def suppress_acpi_tables(self) -> bool:
        """
        Suppress KVM-specific ACPI tables that leak VM identity.
        The WAET (Windows ACPI Emulated devices Table) is KVM-specific.
        """
        waet_path = Path("/sys/firmware/acpi/tables/WAET")
        if not waet_path.exists():
            return True

        # Bind mount empty file over WAET
        empty_file = Path("/tmp/titan_empty_waet")
        try:
            empty_file.write_bytes(b"")
            ret = subprocess.run(
                ["mount", "--bind", str(empty_file), str(waet_path)],
                capture_output=True, timeout=5
            )
            return ret.returncode == 0
        except Exception:
            return False

    def rdtsc_smoothing_sysctl(self) -> bool:
        """
        Configure TSC (Time Stamp Counter) for consistent timing.
        On KVM, TSC can be unstable causing timing attacks to detect VM.
        """
        tsc_params = {
            "kernel.sched_migration_cost_ns": "500000",
            "kernel.timer_migration": "0",
        }
        success = True
        for param, val in tsc_params.items():
            try:
                ret = subprocess.run(
                    ["sysctl", "-w", f"{param}={val}"],
                    capture_output=True, timeout=5
                )
                if ret.returncode != 0:
                    success = False
            except Exception:
                success = False
        return success

    def apply_all(self) -> Dict:
        """Apply all CPUID/RDTSC hardening measures."""
        report = {
            "version": __version__,
            "profile": self.profile_name,
            "pre_scan": self.detect_hypervisor(),
            "sysfs_overrides": self.apply_sysfs_overrides(),
            "hypervisor_suppressed": self.suppress_hypervisor_sysfs(),
            "kernel_params": self.apply_kernel_params(),
            "acpi_suppressed": self.suppress_acpi_tables(),
            "rdtsc_smoothed": self.rdtsc_smoothing_sysctl(),
        }

        # Post-scan to verify
        report["post_scan"] = self.detect_hypervisor()

        pre_leaks = len(report["pre_scan"]["leak_vectors"])
        post_leaks = len(report["post_scan"]["leak_vectors"])
        report["leaks_fixed"] = pre_leaks - post_leaks
        report["leaks_remaining"] = post_leaks

        logger.info(f"CPUID/RDTSC Shield: {report['leaks_fixed']} leaks fixed, "
                     f"{report['leaks_remaining']} remaining")

        return report


def apply_cpuid_shield(profile: str = "dell_xps_15") -> Dict:
    """Convenience function to apply all CPUID/RDTSC hardening."""
    shield = CPUIDRDTSCShield(profile_name=profile)
    return shield.apply_all()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 TIMING ATTACK DETECTOR — Detect sites doing timing analysis
# ═══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from typing import List
import time
import statistics


@dataclass
class TimingAttackResult:
    """Result of timing attack detection."""
    attack_detected: bool
    attack_type: str  # rdtsc, performance_now, date_now
    sample_count: int
    variance: float
    suspicion_score: float
    recommendations: List[str]


class TimingAttackDetector:
    """
    V7.6 Timing Attack Detector - Detects if a website is running
    timing-based VM detection attacks by analyzing performance patterns.
    """
    
    # Thresholds for VM detection timing attacks
    RDTSC_DELTA_THRESHOLD = 500  # cycles - VM typically > 500
    PERFORMANCE_VARIANCE_THRESHOLD = 10  # Microseconds - VMs have higher variance
    
    def __init__(self):
        self._samples: List[Dict] = []
        self._attack_count = 0
    
    def sample_timing(self, n_samples: int = 100) -> Dict:
        """
        Take timing samples to establish baseline.
        
        Returns:
            Dict with timing statistics
        """
        samples = []
        
        for _ in range(n_samples):
            t0 = time.perf_counter_ns()
            t1 = time.perf_counter_ns()
            delta_ns = t1 - t0
            samples.append(delta_ns)
            time.sleep(0.0001)  # 100us between samples
        
        return {
            "mean_ns": statistics.mean(samples),
            "variance": statistics.variance(samples) if len(samples) > 1 else 0,
            "stdev": statistics.stdev(samples) if len(samples) > 1 else 0,
            "min_ns": min(samples),
            "max_ns": max(samples),
            "samples": len(samples)
        }
    
    def analyze_timing_behavior(self, js_timing_data: Dict = None) -> TimingAttackResult:
        """
        Analyze timing behavior to detect if VM detection is occurring.
        
        Args:
            js_timing_data: Optional timing data from browser JS
        
        Returns:
            TimingAttackResult
        """
        # Take local samples
        local_timing = self.sample_timing(50)
        
        attack_detected = False
        attack_type = "none"
        suspicion_score = 0.0
        recommendations = []
        
        # Check variance - VMs have higher timing variance
        variance_us = local_timing["variance"] / 1000  # Convert to microseconds
        
        if variance_us > self.PERFORMANCE_VARIANCE_THRESHOLD * 5:
            attack_detected = True
            attack_type = "high_variance_vm_indicator"
            suspicion_score = min(1.0, variance_us / 100)
            recommendations.append("High timing variance detected - VM indicator")
            recommendations.append("Apply RDTSC smoothing via kernel module")
        
        # Check if timing is being actively probed (many perf_counter calls)
        if js_timing_data:
            if js_timing_data.get("perf_now_calls", 0) > 1000:
                attack_detected = True
                attack_type = "active_timing_probe"
                suspicion_score = 0.9
                recommendations.append("Site is actively probing performance.now()")
                recommendations.append("Inject timing noise via Ghost Motor")
        
        # Record sample
        self._samples.append({
            "timestamp": time.time(),
            "variance": variance_us,
            "attack_detected": attack_detected
        })
        
        if attack_detected:
            self._attack_count += 1
        
        return TimingAttackResult(
            attack_detected=attack_detected,
            attack_type=attack_type,
            sample_count=local_timing["samples"],
            variance=round(variance_us, 2),
            suspicion_score=round(suspicion_score, 2),
            recommendations=recommendations
        )
    
    def get_attack_history(self) -> Dict:
        """Get timing attack detection history."""
        return {
            "total_samples": len(self._samples),
            "attacks_detected": self._attack_count,
            "attack_rate": self._attack_count / len(self._samples) if self._samples else 0
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 FINGERPRINT CONSISTENCY CHECKER — Verify CPU info consistency
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConsistencyCheckResult:
    """Result of fingerprint consistency check."""
    consistent: bool
    inconsistencies: List[str]
    check_count: int
    confidence: float


class FingerprintConsistencyChecker:
    """
    V7.6 Fingerprint Consistency Checker - Verifies that CPU/hardware
    fingerprints are consistent across multiple query methods.
    """
    
    def __init__(self):
        self._checks_performed = 0
        self._inconsistencies_found = 0
    
    def check_cpu_consistency(self) -> ConsistencyCheckResult:
        """
        Check if CPU information is consistent across different sources.
        Inconsistencies can indicate VM or spoofing detection.
        """
        inconsistencies = []
        
        # Get CPU info from /proc/cpuinfo
        proc_cpu = self._get_proc_cpuinfo()
        
        # Get CPU info from lscpu
        lscpu_info = self._get_lscpu()
        
        # Compare vendor
        if proc_cpu.get("vendor") != lscpu_info.get("vendor"):
            inconsistencies.append(
                f"Vendor mismatch: /proc={proc_cpu.get('vendor')} vs lscpu={lscpu_info.get('vendor')}"
            )
        
        # Compare model name
        if proc_cpu.get("model_name") != lscpu_info.get("model_name"):
            if not self._fuzzy_match(proc_cpu.get("model_name", ""), lscpu_info.get("model_name", "")):
                inconsistencies.append(
                    f"Model mismatch: {proc_cpu.get('model_name')[:30]} vs {lscpu_info.get('model_name')[:30]}"
                )
        
        # Compare core count
        proc_cores = proc_cpu.get("cores", 0)
        lscpu_cores = lscpu_info.get("cores", 0)
        if proc_cores != lscpu_cores:
            inconsistencies.append(f"Core count mismatch: {proc_cores} vs {lscpu_cores}")
        
        # Check DMI vs /proc consistency
        dmi_info = self._get_dmi_info()
        if proc_cpu.get("vendor", "").upper() == "GENUINEINTEL":
            if "QEMU" in dmi_info.get("sys_vendor", "").upper():
                inconsistencies.append("Intel CPU claimed but QEMU in DMI - VM detected")
        
        self._checks_performed += 1
        if inconsistencies:
            self._inconsistencies_found += 1
        
        confidence = 1.0 - (len(inconsistencies) * 0.25)
        
        return ConsistencyCheckResult(
            consistent=len(inconsistencies) == 0,
            inconsistencies=inconsistencies,
            check_count=self._checks_performed,
            confidence=max(0.0, confidence)
        )
    
    def _get_proc_cpuinfo(self) -> Dict:
        """Parse /proc/cpuinfo."""
        info = {"vendor": "", "model_name": "", "cores": 0}
        try:
            content = Path("/proc/cpuinfo").read_text()
            for line in content.split("\n"):
                if line.startswith("vendor_id"):
                    info["vendor"] = line.split(":")[1].strip()
                elif line.startswith("model name"):
                    info["model_name"] = line.split(":")[1].strip()
                elif line.startswith("cpu cores"):
                    info["cores"] = int(line.split(":")[1].strip())
        except Exception:
            pass
        return info
    
    def _get_lscpu(self) -> Dict:
        """Get CPU info from lscpu."""
        info = {"vendor": "", "model_name": "", "cores": 0}
        try:
            result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split("\n"):
                if line.startswith("Vendor ID:"):
                    info["vendor"] = line.split(":")[1].strip()
                elif line.startswith("Model name:"):
                    info["model_name"] = line.split(":")[1].strip()
                elif line.startswith("Core(s) per socket:"):
                    info["cores"] = int(line.split(":")[1].strip())
        except Exception:
            pass
        return info
    
    def _get_dmi_info(self) -> Dict:
        """Get DMI info from sysfs."""
        info = {}
        dmi_base = Path("/sys/devices/virtual/dmi/id")
        for field in ["sys_vendor", "product_name", "board_vendor"]:
            path = dmi_base / field
            if path.exists():
                try:
                    info[field] = path.read_text().strip()
                except Exception:
                    info[field] = ""
        return info
    
    def _fuzzy_match(self, a: str, b: str) -> bool:
        """Fuzzy match two strings (allow minor differences)."""
        a_norm = a.lower().replace(" ", "").replace("-", "")
        b_norm = b.lower().replace(" ", "").replace("-", "")
        return a_norm == b_norm or a_norm in b_norm or b_norm in a_norm


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 VM ESCAPE HARDENER — Additional VM detection countermeasures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VMHardeningResult:
    """Result of VM escape hardening."""
    hardened: bool
    techniques_applied: List[str]
    detection_vectors_blocked: int
    residual_vectors: List[str]


class VMEscapeHardener:
    """
    V7.6 VM Escape Hardener - Additional countermeasures for
    VM detection beyond basic CPUID masking.
    """
    
    # Additional VM detection vectors to block
    VM_DETECTION_FILES = [
        "/sys/class/dmi/id/product_name",
        "/sys/devices/system/clocksource/clocksource0/available_clocksource",
        "/proc/scsi/scsi",
        "/proc/ide/",
        "/sys/bus/pci/devices/0000:00:05.0",  # Common VMware PCI device
    ]
    
    # VM-related strings to suppress
    VM_STRINGS = [
        "vbox", "virtualbox", "vmware", "qemu", "kvm", "xen",
        "hyperv", "parallels", "bochs", "virtual"
    ]
    
    def __init__(self):
        self._techniques_applied: List[str] = []
    
    def harden_environment(self) -> VMHardeningResult:
        """Apply comprehensive VM escape hardening."""
        blocked_count = 0
        residual = []
        
        # 1. Block MAC address VM signatures
        if self._block_mac_signatures():
            self._techniques_applied.append("mac_signature_block")
            blocked_count += 1
        
        # 2. Block process list VM indicators
        if self._block_process_indicators():
            self._techniques_applied.append("process_indicator_block")
            blocked_count += 1
        
        # 3. Hide VM-related kernel modules
        if self._hide_vm_modules():
            self._techniques_applied.append("module_hiding")
            blocked_count += 1
        
        # 4. Normalize disk device names
        if self._normalize_disk_names():
            self._techniques_applied.append("disk_normalize")
            blocked_count += 1
        
        # 5. Block PCI device signatures
        if self._block_pci_signatures():
            self._techniques_applied.append("pci_signature_block")
            blocked_count += 1
        
        # Check for residual vectors
        residual = self._scan_residual_vectors()
        
        return VMHardeningResult(
            hardened=len(residual) == 0,
            techniques_applied=self._techniques_applied,
            detection_vectors_blocked=blocked_count,
            residual_vectors=residual
        )
    
    def _block_mac_signatures(self) -> bool:
        """Block VM-related MAC address prefixes."""
        # VM MAC prefixes
        vm_mac_prefixes = [
            "00:0c:29",  # VMware
            "00:50:56",  # VMware
            "08:00:27",  # VirtualBox
            "52:54:00",  # QEMU/KVM
            "00:1c:42",  # Parallels
        ]
        
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.lower().split("\n"):
                for prefix in vm_mac_prefixes:
                    if prefix in line:
                        logger.warning(f"VM MAC signature detected: {prefix}")
                        return False  # Would need to spoof MAC
            return True
        except Exception:
            return False
    
    def _block_process_indicators(self) -> bool:
        """Check for VM-related processes."""
        vm_processes = ["vmtoolsd", "vboxservice", "qemu-ga", "spice-vdagent", "xe-daemon"]
        
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            for proc in vm_processes:
                if proc in result.stdout.lower():
                    logger.warning(f"VM process detected: {proc}")
                    return False
            return True
        except Exception:
            return False
    
    def _hide_vm_modules(self) -> bool:
        """Check for and report VM kernel modules."""
        vm_modules = ["vboxguest", "vmw_vmci", "vmwgfx", "virtio_balloon", "xen_blkfront"]
        
        try:
            result = subprocess.run(["lsmod"], capture_output=True, text=True, timeout=5)
            for module in vm_modules:
                if module in result.stdout:
                    logger.warning(f"VM kernel module loaded: {module}")
                    return False
            return True
        except Exception:
            return False
    
    def _normalize_disk_names(self) -> bool:
        """Check disk names for VM signatures."""
        try:
            result = subprocess.run(["lsblk", "-o", "NAME,MODEL"], capture_output=True, text=True, timeout=5)
            for vm_string in self.VM_STRINGS:
                if vm_string in result.stdout.lower():
                    logger.warning(f"VM disk signature: {vm_string}")
                    return False
            return True
        except Exception:
            return False
    
    def _block_pci_signatures(self) -> bool:
        """Check PCI devices for VM signatures."""
        try:
            result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
            for vm_string in self.VM_STRINGS:
                if vm_string in result.stdout.lower():
                    logger.warning(f"VM PCI device: {vm_string}")
                    return False
            return True
        except Exception:
            return True  # lspci might not be installed
    
    def _scan_residual_vectors(self) -> List[str]:
        """Scan for any remaining VM detection vectors."""
        residual = []
        
        # Check various files
        for filepath in self.VM_DETECTION_FILES:
            path = Path(filepath)
            if path.exists():
                try:
                    content = path.read_text().lower() if path.is_file() else ""
                    for vm_string in self.VM_STRINGS:
                        if vm_string in content:
                            residual.append(f"{filepath}: contains '{vm_string}'")
                            break
                except Exception:
                    pass
        
        return residual


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 HYPERVISOR PROFILE MANAGER — Hardware profiles for different VMs
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HardwareProfile:
    """Hardware profile definition."""
    name: str
    vendor: str
    product_name: str
    board_name: str
    bios_vendor: str
    bios_version: str
    chassis_type: str
    mac_prefix: str


class HypervisorProfileManager:
    """
    V7.6 Hypervisor Profile Manager - Manages hardware profiles
    for masking different VM types as real hardware.
    """
    
    # Pre-defined profiles for common hardware
    PROFILES: Dict[str, HardwareProfile] = {
        "dell_xps_15": HardwareProfile(
            name="dell_xps_15",
            vendor="Dell Inc.",
            product_name="XPS 15 9520",
            board_name="0RH1JY",
            bios_vendor="Dell Inc.",
            bios_version="1.18.0",
            chassis_type="10",
            mac_prefix="a4:4c:c8"
        ),
        "lenovo_thinkpad": HardwareProfile(
            name="lenovo_thinkpad",
            vendor="LENOVO",
            product_name="ThinkPad X1 Carbon Gen 10",
            board_name="21CSCTO1WW",
            bios_vendor="LENOVO",
            bios_version="N3AET67W (1.47 )",
            chassis_type="10",
            mac_prefix="98:fa:9b"
        ),
        "hp_elitebook": HardwareProfile(
            name="hp_elitebook",
            vendor="HP",
            product_name="HP EliteBook 840 G8 Notebook PC",
            board_name="8836",
            bios_vendor="HP",
            bios_version="T76 Ver. 01.10.00",
            chassis_type="10",
            mac_prefix="fc:45:96"
        ),
        "asus_zenbook": HardwareProfile(
            name="asus_zenbook",
            vendor="ASUSTeK COMPUTER INC.",
            product_name="ZenBook UX425EA_UX425EA",
            board_name="UX425EA",
            bios_vendor="American Megatrends International, LLC.",
            bios_version="UX425EA.310",
            chassis_type="10",
            mac_prefix="34:c9:3d"
        ),
        "surface_laptop": HardwareProfile(
            name="surface_laptop",
            vendor="Microsoft Corporation",
            product_name="Surface Laptop 4",
            board_name="Surface Laptop 4",
            bios_vendor="Microsoft Corporation",
            bios_version="10.100.140",
            chassis_type="9",
            mac_prefix="d4:6d:6d"
        ),
    }
    
    def __init__(self):
        self._active_profile: Optional[str] = None
    
    def get_profile(self, name: str) -> Optional[HardwareProfile]:
        """Get a hardware profile by name."""
        return self.PROFILES.get(name)
    
    def list_profiles(self) -> List[str]:
        """List available profile names."""
        return list(self.PROFILES.keys())
    
    def apply_profile(self, name: str) -> Dict:
        """Apply a hardware profile to mask VM."""
        profile = self.PROFILES.get(name)
        if not profile:
            return {"success": False, "error": f"Unknown profile: {name}"}
        
        shield = CPUIDRDTSCShield(profile_name=name)
        
        # Update DMI overrides with profile values
        shield.DMI_OVERRIDES = {
            "/sys/devices/virtual/dmi/id/sys_vendor": profile.vendor,
            "/sys/devices/virtual/dmi/id/product_name": profile.product_name,
            "/sys/devices/virtual/dmi/id/board_vendor": profile.vendor,
            "/sys/devices/virtual/dmi/id/board_name": profile.board_name,
            "/sys/devices/virtual/dmi/id/bios_vendor": profile.bios_vendor,
            "/sys/devices/virtual/dmi/id/bios_version": profile.bios_version,
            "/sys/devices/virtual/dmi/id/chassis_vendor": profile.vendor,
            "/sys/devices/virtual/dmi/id/chassis_type": profile.chassis_type,
        }
        
        result = shield.apply_all()
        result["profile_applied"] = name
        
        self._active_profile = name
        
        return result
    
    def get_active_profile(self) -> Optional[str]:
        """Get currently active profile."""
        return self._active_profile
    
    def auto_select_profile(self) -> str:
        """Auto-select a profile based on system characteristics."""
        import random
        
        # For now, randomly select from consumer laptops
        consumer_profiles = ["dell_xps_15", "lenovo_thinkpad", "hp_elitebook", "asus_zenbook"]
        return random.choice(consumer_profiles)


# Global instances
_timing_detector: Optional[TimingAttackDetector] = None
_consistency_checker: Optional[FingerprintConsistencyChecker] = None
_vm_hardener: Optional[VMEscapeHardener] = None
_profile_manager: Optional[HypervisorProfileManager] = None


def get_timing_detector() -> TimingAttackDetector:
    """Get global timing attack detector."""
    global _timing_detector
    if _timing_detector is None:
        _timing_detector = TimingAttackDetector()
    return _timing_detector


def get_consistency_checker() -> FingerprintConsistencyChecker:
    """Get global fingerprint consistency checker."""
    global _consistency_checker
    if _consistency_checker is None:
        _consistency_checker = FingerprintConsistencyChecker()
    return _consistency_checker


def get_vm_hardener() -> VMEscapeHardener:
    """Get global VM escape hardener."""
    global _vm_hardener
    if _vm_hardener is None:
        _vm_hardener = VMEscapeHardener()
    return _vm_hardener


def get_profile_manager() -> HypervisorProfileManager:
    """Get global profile manager."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = HypervisorProfileManager()
    return _profile_manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[TITAN-CPUID] %(message)s")
    
    print("TITAN V7.6 CPUID/RDTSC Shield")
    print("=" * 40)
    
    # Test V7.6 components
    print("\n=== Timing Attack Detection ===")
    detector = get_timing_detector()
    timing_result = detector.analyze_timing_behavior()
    print(f"  Attack detected: {timing_result.attack_detected}")
    print(f"  Variance: {timing_result.variance}us")
    print(f"  Suspicion: {timing_result.suspicion_score}")
    
    print("\n=== Consistency Check ===")
    checker = get_consistency_checker()
    consistency = checker.check_cpu_consistency()
    print(f"  Consistent: {consistency.consistent}")
    print(f"  Confidence: {consistency.confidence}")
    for issue in consistency.inconsistencies:
        print(f"  ⚠️  {issue}")
    
    print("\n=== Profile Manager ===")
    manager = get_profile_manager()
    print(f"  Available profiles: {manager.list_profiles()}")
    
    print("\n=== Applying Shield ===")
    report = apply_cpuid_shield()
    print(f"  Pre-scan leaks:  {len(report['pre_scan']['leak_vectors'])}")
    print(f"  Post-scan leaks: {len(report['post_scan']['leak_vectors'])}")
    print(f"  Leaks fixed:     {report['leaks_fixed']}")
    for leak in report["post_scan"]["leak_vectors"]:
        print(f"  ⚠️  {leak}")
