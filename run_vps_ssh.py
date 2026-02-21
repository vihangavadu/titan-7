#!/usr/bin/env python3
import subprocess
import sys
import os

VPS_HOST = "72.62.72.48"
VPS_USER = "root"
VPS_PASS = "Xt7mKp9wRv3n.Jq2026"
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "vps_verify_real.sh")

def run_ssh_command(command):
    """Run SSH command using various methods"""
    ssh_clients = [
        r"C:\Program Files\Git\usr\bin\ssh.exe",
        r"C:\Windows\System32\OpenSSH\ssh.exe",
        "ssh"
    ]
    
    for ssh_path in ssh_clients:
        if os.path.exists(ssh_path) or ssh_path == "ssh":
            try:
                # Try using sshpass if available
                cmd = [ssh_path, "-o", "StrictHostKeyChecking=no", 
                       "-o", "PasswordAuthentication=yes",
                       "-o", "PubkeyAuthentication=no",
                       f"{VPS_USER}@{VPS_HOST}", command]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    return True, result.stdout
                else:
                    print(f"Failed with {ssh_path}: {result.stderr}")
            except Exception as e:
                print(f"Error with {ssh_path}: {e}")
                continue
    
    return False, "All SSH methods failed"

def main():
    print("TITAN V7.5 - VPS Script Runner")
    print("=" * 50)
    
    # Test connection
    print("Testing SSH connection...")
    success, output = run_ssh_command("echo 'Connected' && whoami && pwd")
    if not success:
        print("❌ SSH connection failed")
        print("Output:", output)
        return 1
    
    print("✅ SSH connection successful")
    print("User:", output.strip().split('\n')[1] if '\n' in output else 'Unknown')
    print()
    
    # Read and run the verification script
    if not os.path.exists(SCRIPT_PATH):
        print(f"❌ Script not found: {SCRIPT_PATH}")
        return 1
    
    with open(SCRIPT_PATH, 'r') as f:
        script_content = f.read()
    
    print("Running verification script...")
    print("-" * 50)
    
    success, output = run_ssh_command(script_content)
    
    print("-" * 50)
    if success:
        print("✅ Script executed successfully")
    else:
        print("❌ Script execution failed")
    
    print("\nOutput:")
    print(output)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
