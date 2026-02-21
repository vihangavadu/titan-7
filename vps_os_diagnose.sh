#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN OS — OLLAMA SYSTEM DIAGNOSTIC                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# ─── Gather raw system data ───────────────────────────────────────────────────
OS_INFO=$(cat /etc/os-release 2>/dev/null | head -5)
KERNEL=$(uname -a)
UPTIME=$(uptime)
DISK=$(df -h 2>/dev/null)
MEM=$(free -h 2>/dev/null)
CPU=$(lscpu 2>/dev/null | grep -E "Model name|CPU\(s\)|MHz|Architecture" | head -6)
SERVICES=$(systemctl list-units --state=failed --no-pager 2>/dev/null | head -20)
SERVICES_ACTIVE=$(systemctl list-units --type=service --state=active --no-pager 2>/dev/null | grep -E "titan|ollama|nginx|postgres|xrdp" | head -20)
ERRORS=$(journalctl -p err -n 30 --no-pager 2>/dev/null | tail -30)
NETWORK=$(ip addr show 2>/dev/null | grep -E "inet |state")
PORTS=$(ss -tulpn 2>/dev/null | head -30)
PROCESSES=$(ps aux --sort=-%cpu 2>/dev/null | head -20)
TITAN_FILES=$(find /opt/titan -name "*.py" 2>/dev/null | wc -l)
TITAN_CORE=$(ls /opt/titan/core/ 2>/dev/null)
TITAN_APPS=$(ls /opt/titan/apps/ 2>/dev/null)
OLLAMA_STATUS=$(systemctl is-active ollama 2>/dev/null || echo "not a service")
OLLAMA_MODELS=$(ollama list 2>/dev/null || echo "ollama CLI not in PATH")
PYTHON_VER=$(python3 --version 2>/dev/null)
PYQT=$(python3 -c "import PyQt6; print('PyQt6 OK')" 2>/dev/null || echo "PyQt6 missing")
DISK_INODES=$(df -i 2>/dev/null | head -5)
LOAD=$(cat /proc/loadavg 2>/dev/null)
DMESG_ERRORS=$(dmesg 2>/dev/null | grep -iE "error|fail|warn|oom" | tail -15)

echo "═══ SYSTEM SNAPSHOT ═══"
echo "Kernel: $KERNEL"
echo "Uptime: $UPTIME"
echo "Load: $LOAD"
echo "Python: $PYTHON_VER | PyQt6: $PYQT"
echo "Titan .py files: $TITAN_FILES"
echo "Ollama service: $OLLAMA_STATUS"
echo ""
echo "Memory:"
echo "$MEM"
echo ""
echo "Disk:"
echo "$DISK"
echo ""
echo "Failed services:"
echo "${SERVICES:-none}"
echo ""
echo "Active Titan/key services:"
echo "${SERVICES_ACTIVE:-none found}"
echo ""
echo "Open ports:"
echo "$PORTS"
echo ""
echo "Top processes:"
echo "$PROCESSES"
echo ""

# ─── Build the Ollama prompt with all system data ─────────────────────────────
python3 - <<PYEOF
import sys, json, urllib.request, urllib.error

sys.path.insert(0, "core")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# Collect all system data
system_data = """
=== OS INFO ===
$(echo "$OS_INFO")

=== KERNEL ===
$(echo "$KERNEL")

=== UPTIME / LOAD ===
$(echo "$UPTIME")
Load avg: $(echo "$LOAD")

=== MEMORY ===
$(echo "$MEM")

=== DISK ===
$(echo "$DISK")

=== DISK INODES ===
$(echo "$DISK_INODES")

=== CPU ===
$(echo "$CPU")

=== NETWORK ===
$(echo "$NETWORK")

=== OPEN PORTS ===
$(echo "$PORTS")

=== FAILED SYSTEMD SERVICES ===
$(echo "$SERVICES")

=== ACTIVE TITAN/KEY SERVICES ===
$(echo "$SERVICES_ACTIVE")

=== TOP PROCESSES (by CPU) ===
$(echo "$PROCESSES")

=== RECENT SYSTEM ERRORS (journalctl) ===
$(echo "$ERRORS")

=== DMESG ERRORS/WARNINGS ===
$(echo "$DMESG_ERRORS")

=== TITAN INSTALLATION ===
Python files: $(echo "$TITAN_FILES")
Core modules: $(echo "$TITAN_CORE")
Apps: $(echo "$TITAN_APPS")
Ollama service: $(echo "$OLLAMA_STATUS")
Ollama models: $(echo "$OLLAMA_MODELS")
Python: $(echo "$PYTHON_VER")
PyQt6: $(echo "$PYQT")
"""

prompt = f"""You are a senior Linux system administrator and security expert analyzing a production server running TITAN OS V7.5 SINGULARITY — a specialized operational platform.

Below is a full system diagnostic snapshot. Analyze it thoroughly and identify:

1. CRITICAL ISSUES — things that are broken or will cause failures
2. WARNINGS — things that are degraded or suboptimal
3. SECURITY CONCERNS — misconfigurations, exposed services, risks
4. PERFORMANCE ISSUES — resource bottlenecks, memory pressure, high load
5. MISSING/FAILED SERVICES — services that should be running but aren't
6. RECOMMENDATIONS — specific actionable fixes for each issue found

Be specific. Reference exact service names, port numbers, error messages, and file paths from the data. Do not give generic advice.

SYSTEM DATA:
{system_data}

Provide your analysis in this format:
CRITICAL: [list each critical issue]
WARNING: [list each warning]  
SECURITY: [list each security concern]
PERFORMANCE: [list each performance issue]
MISSING_SERVICES: [list missing/failed services]
RECOMMENDATIONS: [numbered list of specific fixes]
OVERALL_HEALTH: [score 0-100 and one-line summary]
"""

print("═══ SENDING TO OLLAMA FOR ANALYSIS ═══")
print(f"Prompt size: {len(prompt)} chars")
print()

try:
    payload = json.dumps({
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2000
        }
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode())
        response_text = result.get("response", "")
        
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  OLLAMA SYSTEM ANALYSIS REPORT                                       ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        print()
        print(response_text)
        print()
        print(f"[Tokens used: {result.get('eval_count', '?')} | Time: {result.get('eval_duration', 0)//1000000000:.1f}s]")

except urllib.error.URLError as e:
    print(f"❌ Ollama connection failed: {e}")
    print("   Is Ollama running? Check: systemctl status ollama")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  DIAGNOSTIC COMPLETE                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
