#!/usr/bin/env python3
"""
TITAN V7.5 SINGULARITY — VPS Deployment Script
Deploys local codebase to VPS with proper permissions and service management.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

class VPSDeployer:
    """Deploy TITAN codebase to VPS."""
    
    def __init__(self, vps_host="72.62.72.48", vps_user="root"):
        self.vps_host = vps_host
        self.vps_user = vps_user
        self.local_root = Path(__file__).parent
        self.vps_root = "/opt/titan"
        
    def check_ssh_connection(self):
        """Check SSH connection to VPS."""
        print("🔍 Checking SSH connection...")
        try:
            result = subprocess.run([
                "ssh", f"{self.vps_user}@{self.vps_host}",
                "echo 'SSH connection successful'; whoami; hostname"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ SSH connection successful")
                print(f"   Host: {result.stdout.strip().split(chr(10))[2]}")
                return True
            else:
                print(f"❌ SSH connection failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ SSH connection error: {e}")
            return False
    
    def create_deployment_commands(self):
        """Generate deployment commands for VPS."""
        commands = [
            # Create backup
            f"mkdir -p /tmp/titan_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            f"cp -r {self.vps_root}/* /tmp/titan_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}/ 2>/dev/null || true",
            
            # Ensure directories exist
            f"mkdir -p {self.vps_root}/core",
            f"mkdir -p {self.vps_root}/apps", 
            f"mkdir -p {self.vps_root}/config",
            f"mkdir -p {self.vps_root}/bin",
            f"mkdir -p {self.vps_root}/lib",
            f"mkdir -p {self.vps_root}/data",
            f"mkdir -p {self.vps_root}/logs",
            
            # Set permissions
            f"chmod 755 {self.vps_root}",
            f"chmod 755 {self.vps_root}/core",
            f"chmod 755 {self.vps_root}/apps",
            f"chmod 755 {self.vps_root}/config",
            f"chmod 755 {self.vps_root}/bin",
            f"chmod 755 {self.vps_root}/lib",
            f"chmod 755 {self.vps_root}/data",
            
            # Stop services before deployment
            "systemctl stop titan-backend.service 2>/dev/null || true",
            "systemctl stop titan-frontend.service 2>/dev/null || true",
            "systemctl stop titan-monitor.service 2>/dev/null || true",
        ]
        
        return commands
    
    def sync_files(self):
        """Sync files to VPS using rsync."""
        print("📦 Syncing files to VPS...")
        
        # Source directories
        source_dirs = [
            f"{self.local_root}/iso/config/includes.chroot/opt/titan/core/",
            f"{self.local_root}/iso/config/includes.chroot/opt/titan/apps/",
            f"{self.local_root}/iso/config/includes.chroot/opt/titan/config/",
            f"{self.local_root}/iso/config/includes.chroot/opt/titan/bin/",
            f"{self.local_root}/iso/config/includes.chroot/opt/titan/lib/",
        ]
        
        for source_dir in source_dirs:
            if Path(source_dir).exists():
                dest_dir = source_dir.replace(f"{self.local_root}/iso/config/includes.chroot/opt/titan/", f"{self.vps_user}@{self.vps_host}:{self.vps_root}/")
                
                print(f"   Syncing {source_dir} → {dest_dir}")
                
                try:
                    result = subprocess.run([
                        "rsync", "-avz", "--delete",
                        "--exclude", "*.pyc",
                        "--exclude", "__pycache__",
                        "--exclude", ".git",
                        "--exclude", "*.log",
                        source_dir, dest_dir
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print(f"   ✅ Synced successfully")
                    else:
                        print(f"   ❌ Sync failed: {result.stderr}")
                        return False
                except Exception as e:
                    print(f"   ❌ Sync error: {e}")
                    return False
            else:
                print(f"   ⚠️ Source directory not found: {source_dir}")
        
        return True
    
    def post_deployment_commands(self):
        """Commands to run after deployment."""
        commands = [
            # Set Python executable permissions
            f"find {self.vps_root} -name '*.py' -exec chmod +x {{}} \\;",
            
            # Set executable permissions for scripts
            f"chmod +x {self.vps_root}/bin/* 2>/dev/null || true",
            
            # Create data directories
            f"mkdir -p {self.vps_root}/data/llm_cache",
            f"mkdir -p {self.vps_root}/data/forensic_cache",
            f"mkdir -p {self.vps_root}/logs",
            
            # Set ownership
            f"chown -R root:root {self.vps_root}",
            
            # Install Python dependencies if needed
            f"cd {self.vps_root} && python3 -m pip install -r requirements.txt 2>/dev/null || echo 'No requirements.txt found'",
            
            # Restart services
            "systemctl daemon-reload",
            "systemctl start titan-backend.service 2>/dev/null || echo 'titan-backend service not found'",
            "systemctl start titan-frontend.service 2>/dev/null || echo 'titan-frontend service not found'",
            "systemctl start titan-monitor.service 2>/dev/null || echo 'titan-monitor service not found'",
            
            # Check service status
            "systemctl status titan-backend.service --no-pager 2>/dev/null || echo 'Service not found'",
            "systemctl status titan-frontend.service --no-pager 2>/dev/null || echo 'Service not found'",
        ]
        
        return commands
    
    def run_remote_commands(self, commands):
        """Execute commands on VPS."""
        print("🔧 Running remote commands...")
        
        for i, command in enumerate(commands, 1):
            print(f"   [{i}/{len(commands)}] {command[:80]}...")
            
            try:
                result = subprocess.run([
                    "ssh", f"{self.vps_user}@{self.vps_host}",
                    command
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"      ✅ Success")
                else:
                    print(f"      ⚠️ Warning: {result.stderr.strip()}")
            except Exception as e:
                print(f"      ❌ Error: {e}")
    
    def verify_deployment(self):
        """Verify deployment was successful."""
        print("✅ Verifying deployment...")
        
        verification_commands = [
            f"ls -la {self.vps_root}/",
            f"ls -la {self.vps_root}/core/",
            f"ls -la {self.vps_root}/apps/",
            f"python3 -c 'import sys; sys.path.insert(0, \"{self.vps_root}/core\"); from ollama_bridge import is_ollama_available; print(f\"LLM Available: {{is_ollama_available()}}\")'",
            f"python3 -c 'import sys; sys.path.insert(0, \"{self.vps_root}/core\"); from forensic_monitor import ForensicMonitor; print(\"Forensic Monitor: OK\")'",
        ]
        
        self.run_remote_commands(verification_commands)
    
    def deploy(self):
        """Run full deployment process."""
        print("🚀 Starting TITAN V7.5 VPS Deployment...")
        print(f"🎯 Target: {self.vps_user}@{self.vps_host}:{self.vps_root}")
        
        # Check SSH connection
        if not self.check_ssh_connection():
            return False
        
        # Run pre-deployment commands
        pre_commands = self.create_deployment_commands()
        self.run_remote_commands(pre_commands)
        
        # Sync files
        if not self.sync_files():
            return False
        
        # Run post-deployment commands
        post_commands = self.post_deployment_commands()
        self.run_remote_commands(post_commands)
        
        # Verify deployment
        self.verify_deployment()
        
        print("✅ Deployment completed!")
        return True

def main():
    """Main function."""
    print("🔍 TITAN V7.5 VPS Deployment Tool")
    print("="*50)
    
    # Check if rsync is available
    try:
        subprocess.run(["rsync", "--version"], capture_output=True, timeout=5)
    except FileNotFoundError:
        print("❌ rsync not found. Please install rsync:")
        print("   Windows: WSL or Git Bash")
        print("   Linux: sudo apt-get install rsync")
        return 1
    
    deployer = VPSDeployer()
    
    try:
        success = deployer.deploy()
        if success:
            print("\n🎉 Deployment successful!")
            print("💡 Next steps:")
            print("   1. SSH into VPS: ssh root@72.62.72.48")
            print("   2. Run cross-reference: python3 /opt/titan/cross_reference_vps.py")
            print("   3. Check services: systemctl status titan-*.service")
            return 0
        else:
            print("\n❌ Deployment failed!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️ Deployment cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Deployment error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
