# TITAN V7.0 SINGULARITY - Troubleshooting Guide

## Common Issues and Solutions

**Version:** 7.0.2 | **Authority:** Dva.12

---

## Table of Contents

1. [Installation Issues](#1-installation-issues)
2. [Kernel Module Issues](#2-kernel-module-issues)
3. [Browser Launch Issues](#3-browser-launch-issues)
4. [Profile Issues](#4-profile-issues)
5. [Card Validation Issues](#5-card-validation-issues)
6. [Proxy Issues](#6-proxy-issues)
7. [Pre-Flight Failures](#7-pre-flight-failures)
8. [Detection Issues](#8-detection-issues)
9. [Performance Issues](#9-performance-issues)
10. [Debug Mode](#10-debug-mode)

---

## 1. Installation Issues

### Camoufox Not Found

**Symptom:**
```
ImportError: No module named 'camoufox'
```

**Solution:**
```bash
# Install Camoufox with GeoIP support
pip install camoufox[geoip]

# Fetch browser binaries
python -m camoufox fetch

# Verify installation
python -c "from camoufox.sync_api import Camoufox; print('OK')"
```

### Playwright Not Installed

**Symptom:**
```
ImportError: No module named 'playwright'
```

**Solution:**
```bash
pip install playwright
python -m playwright install firefox
```

### Missing Dependencies

**Symptom:**
```
ModuleNotFoundError: No module named 'aiohttp'
```

**Solution:**
```bash
pip install -r /opt/lucid-empire/requirements.txt
```

### Clone & Configure (C&C) Migration Failures

**Symptom:**
`titan-migrate` fails with "Tor is not ready".

**Solution:**
Ensure Tor is installed and running:
```bash
sudo systemctl restart tor
# Wait 30 seconds for circuit establishment
```

**Symptom:**
`proxychains4 git clone` fails.

**Solution:**
Check if your VPS provider blocks Tor or if you have a firewall issue. You can try a direct clone (less stealthy):
```bash
sudo git clone https://github.com/YOUR_REPO/titan-main.git /opt/titan-build
```

### Python Version Too Old

**Symptom:**
```
SyntaxError: invalid syntax (dataclass features)
```

**Solution:**
```bash
# Check Python version (need 3.11+)
python3 --version

# Install Python 3.11 if needed
sudo apt install python3.11 python3.11-venv
```

---

## 2. Kernel Module Issues

### Module Not Loaded

**Symptom:**
```
[WARN] Kernel module not loaded (userspace fallback active)
```

**Solution:**
```bash
# Check if module exists
ls /lib/modules/$(uname -r)/extra/titan_hw.ko

# Load module
sudo modprobe titan_hw

# Verify
lsmod | grep titan_hw

# Check dmesg for errors
dmesg | tail -20 | grep titan
```

### Module Build Failed

**Symptom:**
```
make: *** No rule to make target 'titan_hw.ko'
```

**Solution:**
```bash
# Install kernel headers
sudo apt install linux-headers-$(uname -r)

# Rebuild
cd /opt/titan/hardware_shield
make clean
make
sudo make install
```

### DKMS Issues

**Symptom:**
```
Error! Bad return status for module build
```

**Solution:**
```bash
# Check DKMS status
sudo dkms status

# Remove and reinstall
sudo dkms remove titan_hw/6.0.0 --all
sudo dkms install titan_hw/6.0.0

# Check build log
cat /var/lib/dkms/titan_hw/6.0.0/build/make.log
```

### Module Version Mismatch

**Symptom:**
```
titan_hw: version magic mismatch
```

**Solution:**
```bash
# Rebuild for current kernel
cd /opt/titan/hardware_shield
make clean
make
sudo make install
sudo depmod -a
sudo modprobe titan_hw
```

---

## 3. Browser Launch Issues

### Camoufox Launch Failed

**Symptom:**
```
[ERROR] Browser launch failed: Executable doesn't exist
```

**Solution:**
```bash
# Re-fetch Camoufox
python -m camoufox fetch

# Check executable
ls ~/.camoufox/
```

### Firefox Not Found

**Symptom:**
```
[ERROR] No compatible browser found
```

**Solution:**
```bash
# Install Firefox ESR
sudo apt install firefox-esr

# Or standard Firefox
sudo apt install firefox
```

### Profile Not Found

**Symptom:**
```
[ERROR] Profile not found: titan_abc123
```

**Solution:**
```bash
# List available profiles
ls /opt/titan/profiles/

# Use correct profile name
titan-browser -p <correct_profile_name>
```

### WebDriver Detected

**Symptom:**
Browser shows "WebDriver detected" or CAPTCHA appears immediately.

**Solution:**
1. Ensure using Camoufox (not standard Firefox)
2. Check Hardware Shield is active
3. Verify Ghost Motor extension loaded
4. Use `titan-browser` launcher (not direct browser)

---

## 4. Profile Issues

### Profile Directory Not Found

**Symptom:**
```
FileNotFoundError: /opt/titan/profiles/
```

**Solution:**
```bash
# Create directory
sudo mkdir -p /opt/titan/profiles
sudo chmod 755 /opt/titan/profiles
```

### Profile Metadata Missing

**Symptom:**
```
[WARN] Profile metadata not found
```

**Solution:**
```bash
# Regenerate profile
titan-genesis --target amazon_us --persona "John Smith" --age 90
```

### History Database Corrupted

**Symptom:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
```bash
# Delete and regenerate profile
rm -rf /opt/titan/profiles/titan_abc123
titan-genesis --target amazon_us --persona "John Smith" --age 90
```

### Profile Too Young

**Symptom:**
High decline rate, frequent CAPTCHAs.

**Solution:**
- Use `--age 90` or higher when forging
- Profiles under 30 days have lower trust

---

## 5. Card Validation Issues

### No Merchant Keys

**Symptom:**
```
ValidationResult: status=UNKNOWN, message="No API keys available"
```

**Solution:**
```python
from titan.core import CerberusValidator, MerchantKey

validator = CerberusValidator()
validator.add_key(MerchantKey(
    provider="stripe",
    public_key="pk_live_xxx",
    secret_key="sk_live_xxx"
))
```

### Card Declined

**Symptom:**
```
ValidationResult: status=DEAD
```

**Causes:**
- Invalid card number (Luhn check failed)
- Expired card
- Insufficient funds
- Card blocked by issuer

**Solution:**
- Verify card details
- Try different card
- Check BIN in database

### High Risk Score

**Symptom:**
```
ValidationResult: risk_score=80
```

**Cause:** Card BIN is in high-risk database (prepaid, virtual, etc.)

**Solution:**
- Use different card with lower risk BIN
- Check `CerberusValidator.HIGH_RISK_BINS`

### 3DS Required

**Symptom:**
```
ValidationResult: risk_score=40, message="3DS required"
```

**Solution:**
- Have SMS/app access ready
- Or use non-3DS card (risk_score=20)
- See Operator Guide for 3DS strategies

---

## 6. Proxy Issues

### Proxy Connection Failed

**Symptom:**
```
aiohttp.ClientConnectorError: Cannot connect to proxy
```

**Solution:**
```bash
# Test proxy manually
curl -x http://user:pass@proxy:port https://api.ipify.org

# Check proxy is running
nc -zv proxy.example.com 8080
```

### Proxy Authentication Failed

**Symptom:**
```
407 Proxy Authentication Required
```

**Solution:**
- Verify username/password
- Check proxy subscription is active
- Ensure correct auth format in URL

### Datacenter IP Detected

**Symptom:**
Immediate blocks, CAPTCHAs, or "suspicious activity" messages.

**Solution:**
- Use residential proxies (not datacenter)
- Check IP at: https://whoer.net
- Verify proxy type with provider

### Geographic Mismatch

**Symptom:**
AVS failures, "billing address doesn't match" errors.

**Solution:**
```python
from titan.core import GeoTarget, ResidentialProxyManager

manager = ResidentialProxyManager()
target = GeoTarget.from_billing_address({
    "city": "New York",
    "state": "NY",
    "country": "US"
})
proxy = manager.get_proxy_for_geo(target)
```

### Proxy Pool Empty

**Symptom:**
```
[ERROR] No proxy available for geo target
```

**Solution:**
```python
# Add proxies to pool
manager.add_proxy(ProxyEndpoint(...))

# Or load from file
manager.load_pool("/path/to/proxies.json")
```

---

## 7. Pre-Flight Failures

### IP Reputation Failed

**Symptom:**
```
Pre-flight check failed: IP reputation
```

**Solution:**
- Switch to different residential proxy
- Avoid recently used IPs
- Check IP at: https://www.ipqualityscore.com/

### Canvas Hash Inconsistent

**Symptom:**
```
Pre-flight check failed: Canvas hash mismatch
```

**Solution:**
- Ensure using same profile UUID
- Regenerate fingerprint config:
```python
from titan.core import create_injector
injector = create_injector("titan_abc123")
injector.write_to_profile(Path("/opt/titan/profiles/titan_abc123"))
```

### Timezone Mismatch

**Symptom:**
```
Pre-flight check failed: Timezone doesn't match IP location
```

**Solution:**
- Use Integration Bridge for auto-alignment:
```python
bridge = create_bridge(
    profile_uuid="titan_abc123",
    billing_address={"city": "New York", "country": "US"}
)
config = bridge.align_location_to_billing(billing_address)
```

### WebRTC Leak Detected

**Symptom:**
```
Pre-flight check failed: WebRTC leak
```

**Solution:**
- Use Camoufox with `block_webrtc=True`
- Or disable WebRTC in Firefox:
  - `media.peerconnection.enabled` = false

### DNS Leak Detected

**Symptom:**
```
Pre-flight check failed: DNS leak
```

**Solution:**
- Configure proxy to handle DNS
- Use SOCKS5 with remote DNS resolution
- Or configure system DNS to match proxy location

---

## 8. Detection Issues

### Bot Detection Triggered

**Symptom:**
- CAPTCHA appears
- "Unusual activity detected"
- Account locked

**Causes:**
1. Timing too fast
2. Mouse movements unnatural
3. Fingerprint inconsistent
4. Direct URL navigation

**Solutions:**
1. Follow timing guide (45-90s per page)
2. Ensure Ghost Motor active
3. Use deterministic fingerprints
4. Use referrer warmup

### Fingerprint Flagged

**Symptom:**
Repeated blocks on same site despite new cards.

**Solution:**
- Create new profile with new UUID
- Change hardware profile
- Use different GPU in WebGL config

### Velocity Limit Hit

**Symptom:**
```
Decline code: velocity_exceeded
```

**Solution:**
- Wait 24-48 hours before retrying
- Use different profile
- Reduce operation frequency

### Account Flagged

**Symptom:**
All operations fail on specific account.

**Solution:**
- Create new account with new profile
- Use different email domain
- Change persona details

---

## 9. Performance Issues

### Slow Profile Generation

**Symptom:**
Profile forging takes >30 seconds.

**Solution:**
- Reduce history size: `history_size=100`
- Use SSD storage for profiles
- Check disk space

### High Memory Usage

**Symptom:**
System runs out of memory during operation.

**Solution:**
- Close unnecessary applications
- Use headless mode for testing
- Increase swap space

### Browser Slow/Freezing

**Symptom:**
Browser becomes unresponsive.

**Solution:**
- Reduce extensions
- Clear browser cache
- Use fresh profile

---

## 10. Debug Mode

### Enable Debug Logging

```bash
# Environment variable
export TITAN_DEBUG=1

# Command line
titan-browser -d -p my_profile https://amazon.com
```

### View Logs

```bash
# Real-time logs
tail -f /opt/titan/logs/titan.log

# Last 100 lines
tail -100 /opt/titan/logs/titan.log
```

### Python Debug

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from titan.core import create_bridge
# Now all operations will log debug info
```

### Check Component Status

```bash
# All systems
titan-status

# Specific components
titan-status --hardware
titan-status --network
titan-status --profiles
titan-status --proxies
```

### Network Debug

```bash
# Check eBPF programs
sudo bpftool prog list | grep titan

# Check network interfaces
ip link show

# Test connectivity through proxy
curl -x socks5://user:pass@proxy:1080 https://api.ipify.org
```

### Profile Debug

```bash
# List profile contents
ls -la /opt/titan/profiles/titan_abc123/

# Check metadata
cat /opt/titan/profiles/titan_abc123/profile_metadata.json | jq .

# Check fingerprint config
cat /opt/titan/profiles/titan_abc123/fingerprint_config.json | jq .
```

---

## Getting Help

### Log Collection

When reporting issues, collect:

```bash
# System info
uname -a
python3 --version
pip list | grep -E "camoufox|playwright|aiohttp"

# TITAN status
titan-status 2>&1

# Recent logs
tail -200 /opt/titan/logs/titan.log

# Kernel module status
lsmod | grep titan
dmesg | grep titan
```

### Common Log Locations

| Component | Log Location |
|-----------|--------------|
| TITAN Core | `/opt/titan/logs/titan.log` |
| Kernel Module | `dmesg` / `/var/log/kern.log` |
| Browser | `~/.camoufox/logs/` |
| System | `/var/log/syslog` |

---

*TITAN V7.0.3 SOVEREIGN - Troubleshooting Guide*
*Authority: Dva.12 | When things go wrong*

