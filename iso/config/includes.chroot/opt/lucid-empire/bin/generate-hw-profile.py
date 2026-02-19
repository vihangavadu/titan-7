#!/usr/bin/env python3
"""
LUCID EMPIRE :: Hardware Profile Generator
Generates fake hardware configuration data for kernel module consumption
"""

import json
import os
import sys
import random
import uuid
from pathlib import Path

class HardwareProfileBuilder:
    """Builds realistic hardware profiles for anti-fingerprinting"""
    
    def __init__(self, profile_name, base_path="/opt/lucid-empire/profiles"):
        self.profile_name = profile_name
        self.profile_dir = Path(base_path) / profile_name
        self.config = {}
        
    def generate_intel_cpu_signature(self, model="i7-12700K", cores=12):
        """Generate Intel CPU info block"""
        cpu_lines = []
        for proc_id in range(cores):
            block = {
                "processor": str(proc_id),
                "vendor_id": "GenuineIntel",
                "cpu family": "6",
                "model": "154",
                "model name": f"12th Gen Intel(R) Core(TM) {model}",
                "stepping": "3",
                "cpu MHz": "3600.000",
                "cache size": "25600 KB",
                "physical id": "0",
                "siblings": str(cores),
                "core id": str(proc_id),
                "cpu cores": str(cores),
            }
            cpu_lines.append(block)
        return cpu_lines
    
    def generate_amd_cpu_signature(self, model="Ryzen 9 5950X", cores=16):
        """Generate AMD CPU info block"""
        cpu_lines = []
        for proc_id in range(cores):
            block = {
                "processor": str(proc_id),
                "vendor_id": "AuthenticAMD",
                "cpu family": "25",
                "model": "33",
                "model name": f"AMD {model} 16-Core Processor",
                "stepping": "0",
                "cpu MHz": "3400.000",
                "cache size": "512 KB",
                "physical id": "0",
                "siblings": str(cores),
                "core id": str(proc_id),
                "cpu cores": str(cores),
            }
            cpu_lines.append(block)
        return cpu_lines
    
    def write_cpuinfo_file(self, cpu_blocks):
        """Write /proc/cpuinfo format file"""
        output_path = self.profile_dir / "cpuinfo"
        with open(output_path, 'w') as f:
            for block in cpu_blocks:
                for key, value in block.items():
                    f.write(f"{key}\t: {value}\n")
                f.write("\n")
        print(f"Generated: {output_path}")
    
    def generate_dmi_identifiers(self):
        """Generate DMI/SMBIOS identifiers"""
        # Realistic manufacturer/product combinations
        hardware_combos = [
            {"vendor": "Dell Inc.", "product": "OptiPlex 7090"},
            {"vendor": "Dell Inc.", "product": "Precision 5560"},
            {"vendor": "HP", "product": "EliteDesk 800 G8"},
            {"vendor": "HP", "product": "ZBook Studio G8"},
            {"vendor": "Lenovo", "product": "ThinkCentre M90q"},
            {"vendor": "Lenovo", "product": "ThinkStation P340"},
            {"vendor": "ASUS", "product": "ROG Strix G15"},
            {"vendor": "ASUS", "product": "ProArt StudioBook"},
            {"vendor": "MSI", "product": "Prestige 15"},
            {"vendor": "MSI", "product": "Creator Z16"},
        ]
        
        selected = random.choice(hardware_combos)
        generated_uuid = str(uuid.uuid4())
        
        dmi_data = {
            "product_name": selected["product"],
            "product_uuid": generated_uuid,
            "board_vendor": selected["vendor"],
            "sys_vendor": selected["vendor"],
        }
        
        for key, value in dmi_data.items():
            output_path = self.profile_dir / f"dmi_{key}"
            with open(output_path, 'w') as f:
                f.write(value + "\n")
            print(f"Generated: {output_path}")
        
        return dmi_data
    
    def write_config_metadata(self, cpu_type, cores, dmi_data):
        """Write profile metadata"""
        metadata = {
            "profile_name": self.profile_name,
            "cpu_type": cpu_type,
            "cpu_cores": cores,
            "dmi": dmi_data,
            "generated_at": "build-time"
        }
        
        config_path = self.profile_dir / "hardware.conf"
        with open(config_path, 'w') as f:
            f.write(f"CPU_CORES={cores}\n")
            f.write(f"CPU_TYPE={cpu_type}\n")
            for key, value in dmi_data.items():
                f.write(f"DMI_{key.upper()}={value}\n")
        print(f"Generated: {config_path}")
        
        meta_path = self.profile_dir / "profile.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"Generated: {meta_path}")
    
    def build_profile(self, cpu_vendor="intel", cpu_model=None, cores=12):
        """Build complete hardware profile"""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== Building Hardware Profile: {self.profile_name} ===")
        
        if cpu_vendor.lower() == "intel":
            model = cpu_model or "i7-12700K"
            cpu_blocks = self.generate_intel_cpu_signature(model, cores)
        else:
            model = cpu_model or "Ryzen 9 5950X"
            cpu_blocks = self.generate_amd_cpu_signature(model, cores)
        
        self.write_cpuinfo_file(cpu_blocks)
        dmi_data = self.generate_dmi_identifiers()
        self.write_config_metadata(cpu_vendor, cores, dmi_data)
        
        print(f"\n✓ Profile '{self.profile_name}' created successfully")
        return self.profile_dir


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_hw_profile.py <profile_name> [cpu_vendor] [cores]")
        print("Example: generate_hw_profile.py gaming_pc intel 16")
        sys.exit(1)
    
    profile_name = sys.argv[1]
    cpu_vendor = sys.argv[2] if len(sys.argv) > 2 else "intel"
    cores = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    
    builder = HardwareProfileBuilder(profile_name)
    builder.build_profile(cpu_vendor=cpu_vendor, cores=cores)


if __name__ == "__main__":
    main()
