# Migration Integrity Verifier

## Overview

The **migration_integrity_verifier.py** script performs comprehensive verification of a Titan V7.0.3 deployment on Debian 12 (and other Linux systems).

It validates:
- ✅ Titan installation paths and critical files
- ✅ System dependencies
- ✅ Configuration readiness
- ✅ Kernel hardening parameters
- ✅ Network security (firewall, dangerous services)
- ✅ Kernel modules (eBPF, hardware shield)
- ✅ Cross-platform compatibility

## Usage

### Basic Verification (with full root access)
```bash
sudo python3 scripts/migration_integrity_verifier.py
```

### Verification without root (limited checks)
```bash
python3 scripts/migration_integrity_verifier.py
```

### Custom Titan installation path
```bash
TITAN_ROOT=/opt/custom-titan python3 scripts/migration_integrity_verifier.py
```

### Capture output to file
```bash
sudo python3 scripts/migration_integrity_verifier.py | tee verification_report.log
```

## Features

### 1. Environment Detection
- Detects OS type (Linux, macOS, Windows)
- Identifies if running with root/admin privileges
- Gracefully degrades on non-Linux systems

### 2. Path Verification
- Confirms Titan installation at expected location
- Validates critical Python modules present
- Checks configuration file exists

### 3. Dependency Verification
- Validates system packages installed
- OS-specific package lists (Linux, macOS)
- Provides installation commands for missing packages

### 4. Configuration Validation
- Checks for required configuration sections
- Detects dangerous placeholders (REPLACE_WITH_, YOUR_API_KEY, etc.)
- Validates critical settings are configured

### 5. Kernel Hardening Audit (Linux + root)
- Verifies 10+ security-critical kernel parameters
- Checks:
  - ICMP echo ignore
  - Redirect handling
  - IP forwarding disabled
  - IPv6 disabled
  - dmesg restrict
  - Namespace cloning restrictions
  - Pointer dereference restrict
  - ptrace restrictions

### 6. Network Security Check (Linux + root)
- Verifies firewall configuration (nftables)
- Detects dangerous services:
  - RPC binding
  - Telnet
  - FTP
- Confirms SSH service (if needed)

### 7. Module Loading Verification (Linux + root)
- Checks if kernel modules loaded:
  - `titan_hw` (hardware spoofing)
  - `ebpf_shields` (network rewriting)
- Warns if critical modules missing

## Output Format

### Color-Coded Results
```
[PASS] - Test passed (green)
[FAIL] - Test failed (red)
[WARN] - Test passed with warnings (yellow)
[*]    - Informational message (blue)
```

### Summary Report
```
MIGRATION VERIFICATION SUMMARY
======================================================================
Total Tests:  24
Passed:       22
Warnings:     2
Failed:       0
======================================================================
[✓] MIGRATION VERIFICATION PASSED
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Verification passed (all critical checks OK) |
| 1 | Verification failed (1+ critical checks failed) |
| 2 | Fatal error (script execution error) |
| 130 | User interrupted (Ctrl+C) |

## Remediation Guide

### Missing Dependencies
```bash
# Install all missing packages
sudo apt-get install -y git python3 iptables jq
```

### Kernel Parameters Need Hardening
```bash
# Apply hardening
sudo sysctl -w net.ipv4.icmp_echo_ignore_all=1
sudo sysctl -w net.ipv4.conf.all.accept_redirects=0
# ... (apply others as needed)

# OR apply all at once via titan.env
```

### Dangerous Services Detected
```bash
# Stop and disable RPC
sudo systemctl stop rpcbind
sudo systemctl disable rpcbind

# Stop and disable other dangerous services
sudo systemctl stop telnetd  # if present
sudo systemctl disable telnetd
```

### Kernel Modules Not Loaded
```bash
# Load hardware shield module
sudo modprobe titan_hw

# Load eBPF shields
sudo insmod /path/to/ebpf_shields.ko

# OR check if they're in dkms queue
sudo dkms status
```

### Configuration Issues
Edit `/opt/titan/config/titan.env`:
```bash
sudo nano /opt/titan/config/titan.env

# Ensure proxy credentials are set:
TITAN_PROXY_USERNAME=<username>
TITAN_PROXY_PASSWORD=<password>

# Remove any REPLACE_WITH_ placeholders
```

## Running on Deployment Systems

### Pre-Migration Check (on fresh Debian 12)
```bash
# Before running Titan deployment
python3 scripts/migration_integrity_verifier.py
# Should show: "Titan Core NOT found" - OK (not yet deployed)
```

### Post-Migration Check (after deployment)
```bash
# After Titan deployed
sudo python3 scripts/migration_integrity_verifier.py
# Should show: 22+ tests passed, 0 failures
```

### Continuous Verification
```bash
# Add to crontab for periodic checks
crontab -e
# Add line:
0 2 * * * /usr/bin/python3 /opt/titan/scripts/migration_integrity_verifier.py >> /var/log/titan_verification.log 2>&1
```

## Troubleshooting

### "ss command not found"
```bash
sudo apt-get install -y iproute2
```

### "nft command not found"
```bash
sudo apt-get install -y nftables
```

### "Permission denied" on Linux
Ensure running with sudo:
```bash
sudo python3 scripts/migration_integrity_verifier.py
```

### "Module not found" errors
Check if modules were built:
```bash
ls -la /opt/titan/kernel_modules/
dkms status
```

## Example: Full Deployment Verification Workflow

```bash
#!/bin/bash
# Full deployment verification workflow

echo "=== PRE-BUILD VERIFICATION ==="
python3 scripts/migration_integrity_verifier.py

echo ""
echo "=== BUILDING TITAN ISO ==="
./build_final.sh

echo ""
echo "=== BOOTING SYSTEM ==="
sudo reboot

# (After boot)

echo ""
echo "=== POST-BOOT VERIFICATION ==="
sudo python3 scripts/migration_integrity_verifier.py

echo ""
echo "=== CHECKING OPERATIONAL STATUS ==="
curl http://localhost:7443/health  # Transaction monitor
python3 /opt/titan/apps/app_unified.py --verify
```

## Exit Requirements

The system is considered ready for operations when:
- ✅ All required packages installed
- ✅ Titan installation verified
- ✅ Configuration file exists and has no `REPLACE_WITH_` placeholders
- ✅ All kernel hardening parameters at expected values (Linux + root)
- ✅ No dangerous services listening
- ✅ Firewall active (nftables or iptables)
- ✅ Critical kernel modules loaded

## Integration with CI/CD

```yaml
# GitHub Actions example
- name: Verify Migration
  run: |
    sudo python3 scripts/migration_integrity_verifier.py
    if [ $? -ne 0 ]; then exit 1; fi
```

---

**Script Location:** `scripts/migration_integrity_verifier.py`  
**Requires:** Python 3.6+  
**Tested On:** Debian 12, Ubuntu 22.04, Ubuntu 24.04  
**Authority:** Dva.12 | **Status:** SINGULARITY
