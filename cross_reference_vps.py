#!/usr/bin/env python3
"""
TITAN V7.5 SINGULARITY — VPS Codebase Cross-Reference Tool
Compares local codebase with deployed VPS installation.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set

class VPSCrossReference:
    """Cross-reference local codebase with VPS deployment."""
    
    def __init__(self):
        self.local_root = Path(__file__).parent
        self.vps_root = Path("/opt/titan")
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "local_files": {},
            "vps_files": {},
            "missing_on_vps": [],
            "extra_on_vps": [],
            "differences": [],
            "services": {},
            "config_diffs": {},
            "permissions": {},
            "summary": {}
        }
    
    def scan_local_codebase(self) -> Dict[str, Dict]:
        """Scan local codebase and collect file info."""
        print("🔍 Scanning local codebase...")
        
        local_files = {}
        
        # Core directories to scan
        scan_dirs = [
            "iso/config/includes.chroot/opt/titan/core",
            "iso/config/includes.chroot/opt/titan/apps", 
            "iso/config/includes.chroot/opt/titan/config",
            "iso/config/includes.chroot/opt/titan/bin",
            "iso/config/includes.chroot/opt/titan/lib",
            "iso/config/includes.chroot/opt/titan/data"
        ]
        
        for scan_dir in scan_dirs:
            dir_path = self.local_root / scan_dir
            if dir_path.exists():
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        # Calculate relative path from /opt/titan
                        rel_path = str(file_path).replace(str(self.local_root / "iso/config/includes.chroot/opt/titan"), "")
                        rel_path = rel_path.lstrip("/")
                        
                        if rel_path:
                            local_files[rel_path] = {
                                "size": file_path.stat().st_size,
                                "hash": self._file_hash(file_path),
                                "modified": file_path.stat().st_mtime,
                                "local_path": str(file_path)
                            }
        
        self.results["local_files"] = local_files
        print(f"✅ Found {len(local_files)} local files")
        return local_files
    
    def scan_vps_deployment(self) -> Dict[str, Dict]:
        """Scan VPS deployment and collect file info."""
        print("🔍 Scanning VPS deployment...")
        
        vps_files = {}
        
        if not self.vps_root.exists():
            print(f"❌ VPS root not found: {self.vps_root}")
            return vps_files
        
        for file_path in self.vps_root.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path).replace(str(self.vps_root), "")
                rel_path = rel_path.lstrip("/")
                
                vps_files[rel_path] = {
                    "size": file_path.stat().st_size,
                    "hash": self._file_hash(file_path),
                    "modified": file_path.stat().st_mtime,
                    "vps_path": str(file_path),
                    "permissions": oct(file_path.stat().st_mode)[-3:]
                }
        
        self.results["vps_files"] = vps_files
        print(f"✅ Found {len(vps_files)} VPS files")
        return vps_files
    
    def _file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return "unknown"
    
    def compare_deployments(self):
        """Compare local and VPS deployments."""
        print("🔍 Comparing deployments...")
        
        local_files = self.results["local_files"]
        vps_files = self.results["vps_files"]
        
        local_set = set(local_files.keys())
        vps_set = set(vps_files.keys())
        
        # Find missing files on VPS
        missing_on_vps = list(local_set - vps_set)
        self.results["missing_on_vps"] = sorted(missing_on_vps)
        
        # Find extra files on VPS
        extra_on_vps = list(vps_set - local_set)
        self.results["extra_on_vps"] = sorted(extra_on_vps)
        
        # Find differences in common files
        common_files = local_set & vps_set
        differences = []
        
        for file_path in common_files:
            local_info = local_files[file_path]
            vps_info = vps_files[file_path]
            
            if local_info["hash"] != vps_info["hash"]:
                differences.append({
                    "file": file_path,
                    "local_hash": local_info["hash"],
                    "vps_hash": vps_info["hash"],
                    "local_size": local_info["size"],
                    "vps_size": vps_info["size"],
                    "status": "different"
                })
        
        self.results["differences"] = sorted(differences, key=lambda x: x["file"])
        
        print(f"📊 Comparison complete:")
        print(f"   - Missing on VPS: {len(missing_on_vps)} files")
        print(f"   - Extra on VPS: {len(extra_on_vps)} files") 
        print(f"   - Different files: {len(differences)} files")
    
    def check_services(self):
        """Check Titan services status on VPS."""
        print("🔍 Checking Titan services...")
        
        services = {}
        
        # Service list to check
        service_list = [
            "titan-backend.service",
            "titan-frontend.service", 
            "titan-monitor.service",
            "titan-firewall.service",
            "titan-vpn.service",
            "nginx.service",
            "postgresql.service"
        ]
        
        for service in service_list:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True, text=True, timeout=5
                )
                services[service] = {
                    "status": result.stdout.strip() or "inactive",
                    "enabled": self._is_service_enabled(service)
                }
            except:
                services[service] = {"status": "unknown", "enabled": False}
        
        self.results["services"] = services
        
        active_count = sum(1 for s in services.values() if s["status"] == "active")
        print(f"✅ Services checked: {active_count}/{len(services)} active")
    
    def _is_service_enabled(self, service: str) -> bool:
        """Check if service is enabled."""
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", service],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "enabled"
        except:
            return False
    
    def check_configurations(self):
        """Check critical configuration files."""
        print("🔍 Checking configurations...")
        
        config_files = [
            "/opt/titan/config/llm_config.json",
            "/opt/titan/config/titan.conf",
            "/opt/titan/config/database.conf",
            "/etc/nginx/sites-available/titan",
            "/etc/systemd/system/titan-backend.service"
        ]
        
        config_diffs = {}
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                    
                    config_diffs[config_file] = {
                        "exists": True,
                        "size": len(content),
                        "hash": hashlib.md5(content.encode()).hexdigest(),
                        "preview": content[:500] + "..." if len(content) > 500 else content
                    }
                except Exception as e:
                    config_diffs[config_file] = {"exists": True, "error": str(e)}
            else:
                config_diffs[config_file] = {"exists": False}
        
        self.results["config_diffs"] = config_diffs
        print(f"✅ Checked {len(config_files)} configuration files")
    
    def check_permissions(self):
        """Check file permissions on critical directories."""
        print("🔍 Checking permissions...")
        
        critical_dirs = [
            "/opt/titan",
            "/opt/titan/core",
            "/opt/titan/apps", 
            "/opt/titan/config",
            "/opt/titan/data",
            "/var/log/titan"
        ]
        
        permissions = {}
        
        for dir_path in critical_dirs:
            path = Path(dir_path)
            if path.exists():
                stat = path.stat()
                permissions[dir_path] = {
                    "mode": oct(stat.st_mode),
                    "owner": stat.st_uid,
                    "group": stat.st_gid,
                    "writable": os.access(path, os.W_OK)
                }
            else:
                permissions[dir_path] = {"exists": False}
        
        self.results["permissions"] = permissions
        print(f"✅ Checked permissions for {len(critical_dirs)} directories")
    
    def generate_summary(self):
        """Generate deployment summary."""
        print("📊 Generating summary...")
        
        summary = {
            "total_local_files": len(self.results["local_files"]),
            "total_vps_files": len(self.results["vps_files"]),
            "missing_files": len(self.results["missing_on_vps"]),
            "extra_files": len(self.results["extra_on_vps"]),
            "different_files": len(self.results["differences"]),
            "active_services": sum(1 for s in self.results["services"].values() if s.get("status") == "active"),
            "total_services": len(self.results["services"]),
            "deployment_health": "unknown"
        }
        
        # Calculate deployment health
        if summary["missing_files"] == 0 and summary["different_files"] == 0:
            summary["deployment_health"] = "perfect"
        elif summary["missing_files"] < 5 and summary["different_files"] < 10:
            summary["deployment_health"] = "good"
        elif summary["missing_files"] < 20 and summary["different_files"] < 50:
            summary["deployment_health"] = "fair"
        else:
            summary["deployment_health"] = "poor"
        
        self.results["summary"] = summary
        
        print(f"📈 Deployment Health: {summary['deployment_health'].upper()}")
        print(f"   - Files: {summary['total_local_files']} local vs {summary['total_vps_files']} VPS")
        print(f"   - Services: {summary['active_services']}/{summary['total_services']} active")
    
    def save_report(self, output_path: str = None):
        """Save cross-reference report to file."""
        if output_path is None:
            output_path = f"vps_cross_reference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📄 Report saved to: {output_path}")
        return output_path
    
    def print_summary(self):
        """Print summary to console."""
        summary = self.results["summary"]
        
        print("\n" + "="*80)
        print("🔍 TITAN V7.5 VPS CROSS-REFERENCE SUMMARY")
        print("="*80)
        print(f"📅 Analysis: {self.results['timestamp']}")
        print(f"🏥 Deployment Health: {summary['deployment_health'].upper()}")
        print(f"📁 Files: {summary['total_local_files']} local → {summary['total_vps_files']} VPS")
        print(f"❌ Missing: {summary['missing_files']} files")
        print(f"➕ Extra: {summary['extra_files']} files") 
        print(f"🔄 Different: {summary['different_files']} files")
        print(f"⚙️ Services: {summary['active_services']}/{summary['total_services']} active")
        
        if self.results["missing_on_vps"]:
            print(f"\n❌ MISSING FILES ({len(self.results['missing_on_vps'])}):")
            for file in self.results["missing_on_vps"][:10]:
                print(f"   - {file}")
            if len(self.results["missing_on_vps"]) > 10:
                print(f"   ... and {len(self.results['missing_on_vps']) - 10} more")
        
        if self.results["differences"]:
            print(f"\n🔄 MODIFIED FILES ({len(self.results['differences'])}):")
            for diff in self.results["differences"][:10]:
                print(f"   - {diff['file']} (hash mismatch)")
            if len(self.results["differences"]) > 10:
                print(f"   ... and {len(self.results['differences']) - 10} more")
        
        print("\n" + "="*80)
    
    def run_full_analysis(self):
        """Run complete cross-reference analysis."""
        print("🚀 Starting VPS cross-reference analysis...")
        
        self.scan_local_codebase()
        self.scan_vps_deployment()
        self.compare_deployments()
        self.check_services()
        self.check_configurations()
        self.check_permissions()
        self.generate_summary()
        self.print_summary()
        
        # Save report
        report_path = self.save_report()
        return report_path

def main():
    """Main function."""
    if os.geteuid() != 0:
        print("❌ This script must be run as root on the VPS")
        print("💡 Usage: sudo python3 cross_reference_vps.py")
        return 1
    
    analyzer = VPSCrossReference()
    try:
        report_path = analyzer.run_full_analysis()
        print(f"\n✅ Analysis complete! Report saved to: {report_path}")
        return 0
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
