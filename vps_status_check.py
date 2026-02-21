#!/usr/bin/env python3
"""
TITAN V7.5 SINGULARITY — VPS Status Check
Quick status check of TITAN OS deployment on VPS.
"""

import subprocess
import json
from datetime import datetime

def run_ssh_command(command):
    """Run command on VPS via SSH."""
    try:
        result = subprocess.run([
            "ssh", "root@72.62.72.48", command
        ], capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def check_vps_status():
    """Check VPS deployment status."""
    print("🔍 TITAN V7.5 VPS Status Check")
    print("="*50)
    
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "connection": False,
        "system": {},
        "titan_files": {},
        "services": {},
        "llm_bridge": False,
        "forensic_monitor": False
    }
    
    # Check connection
    print("📡 Checking SSH connection...")
    stdout, stderr, code = run_ssh_command("echo 'Connected'; whoami; hostname")
    if code == 0:
        print("✅ SSH connection successful")
        status["connection"] = True
        lines = stdout.split('\n')
        print(f"   User: {lines[1] if len(lines) > 1 else 'unknown'}")
        print(f"   Host: {lines[2] if len(lines) > 2 else 'unknown'}")
    else:
        print("❌ SSH connection failed")
        print(f"   Error: {stderr}")
        return status
    
    # Check system info
    print("\n🖥️ System information...")
    stdout, stderr, code = run_ssh_command("uname -a; df -h / | tail -1; free -h | grep Mem")
    if code == 0:
        lines = stdout.split('\n')
        status["system"]["kernel"] = lines[0] if lines else "unknown"
        status["system"]["disk"] = lines[1] if len(lines) > 1 else "unknown"
        status["system"]["memory"] = lines[2] if len(lines) > 2 else "unknown"
        print(f"   Kernel: {status['system']['kernel']}")
        print(f"   Disk: {status['system']['disk']}")
        print(f"   Memory: {status['system']['memory']}")
    
    # Check Titan directory
    print("\n📁 TITAN installation...")
    stdout, stderr, code = run_ssh_command("ls -la /opt/titan/ 2>/dev/null || echo 'Not found'")
    if code == 0 and "Not found" not in stdout:
        print("✅ TITAN directory exists")
        # Count files in subdirectories
        for subdir in ["core", "apps", "config"]:
            stdout_count, _, code_count = run_ssh_command(f"find /opt/titan/{subdir} -name '*.py' 2>/dev/null | wc -l")
            if code_count == 0:
                file_count = stdout_count.strip()
                status["titan_files"][subdir] = file_count
                print(f"   {subdir}/: {file_count} Python files")
    else:
        print("❌ TITAN directory not found")
    
    # Check services
    print("\n⚙️ Services status...")
    services = ["titan-backend", "titan-frontend", "titan-monitor", "nginx", "postgresql"]
    for service in services:
        stdout, stderr, code = run_ssh_command(f"systemctl is-active {service} 2>/dev/null || echo 'inactive'")
        service_status = stdout.strip()
        status["services"][service] = service_status
        status_icon = "🟢" if service_status == "active" else "🔴"
        print(f"   {status_icon} {service}: {service_status}")
    
    # Check LLM bridge
    print("\n🧠 LLM Bridge...")
    stdout, stderr, code = run_ssh_command("cd /opt/titan && python3 -c 'import sys; sys.path.insert(0, \"core\"); from ollama_bridge import is_ollama_available; print(f\"Available: {is_ollama_available()}\")' 2>/dev/null")
    if code == 0:
        status["llm_bridge"] = True
        print(f"   ✅ LLM Bridge: {stdout}")
    else:
        print("   ❌ LLM Bridge: Not available")
    
    # Check forensic monitor
    print("\n🔍 Forensic Monitor...")
    stdout, stderr, code = run_ssh_command("cd /opt/titan && python3 -c 'import sys; sys.path.insert(0, \"core\"); from forensic_monitor import ForensicMonitor; print(\"Available\")' 2>/dev/null")
    if code == 0:
        status["forensic_monitor"] = True
        print("   ✅ Forensic Monitor: Available")
    else:
        print("   ❌ Forensic Monitor: Not available")
    
    # Check recent logs
    print("\n📋 Recent activity...")
    stdout, stderr, code = run_ssh_command("journalctl -u titan-backend --no-pager -n 3 --output=cat 2>/dev/null || echo 'No logs'")
    if code == 0 and stdout:
        print("   Recent backend logs:")
        for line in stdout.split('\n')[:3]:
            if line.strip():
                print(f"     {line}")
    
    # Summary
    print("\n📊 Status Summary:")
    connection_ok = status["connection"]
    titan_installed = bool(status["titan_files"])
    services_active = sum(1 for s in status["services"].values() if s == "active")
    llm_working = status["llm_bridge"]
    forensic_working = status["forensic_monitor"]
    
    print(f"   Connection: {'✅' if connection_ok else '❌'}")
    print(f"   TITAN Installed: {'✅' if titan_installed else '❌'}")
    print(f"   Active Services: {services_active}/{len(services)}")
    print(f"   LLM Bridge: {'✅' if llm_working else '❌'}")
    print(f"   Forensic Monitor: {'✅' if forensic_working else '❌'}")
    
    # Overall health
    health_score = sum([connection_ok, titan_installed, llm_working, forensic_working])
    if health_score >= 3:
        health = "🟢 EXCELLENT"
    elif health_score >= 2:
        health = "🟡 GOOD"
    else:
        health = "🔴 NEEDS ATTENTION"
    
    print(f"\n🏥 Overall Health: {health}")
    
    return status

def main():
    """Main function."""
    try:
        status = check_vps_status()
        
        # Save status report
        with open("vps_status_report.json", "w") as f:
            json.dump(status, f, indent=2, default=str)
        
        print(f"\n📄 Status report saved to: vps_status_report.json")
        return 0
    except KeyboardInterrupt:
        print("\n⚠️ Status check cancelled")
        return 1
    except Exception as e:
        print(f"\n❌ Status check error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
