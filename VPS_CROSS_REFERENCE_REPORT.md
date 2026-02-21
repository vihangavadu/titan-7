# TITAN V7.5 VPS Cross-Reference Report
**Generated**: 2026-02-21T03:55:00Z  
**VPS**: 72.62.72.48 (srv1400969.hstgr.cloud)  
**Plan**: KVM 8 (8 CPU, 32GB RAM, 400GB disk)  
**Template**: Debian 12  

---

## 🔍 Current VPS Status (Based on System Memories)

### ✅ **Confirmed Working**
- **SSH Access**: `root@72.62.72.48` ✅
- **OS**: Debian 12 with BIOS boot (fixed from EFI issue) ✅
- **Network**: Static IP 72.62.72.48/24 ✅
- **Titan OS**: Base installation at `/opt/titan/` ✅
- **Backend API**: Port 8000 (titan-backend.service) ✅

### ⚠️ **Known Issues**
- **eBPF/XDP**: Disabled due to kernel 6.1.0 verifier failures
- **titan_hw.ko**: Not auto-loading after reboot (needs manual insmod)
- **DMI**: Shows QEMU (needs manual spoof activation on KVM)

---

## 📁 Local vs VPS Codebase Comparison

### **New Components (Need Deployment)**
These components were created recently and likely need deployment to VPS:

#### **LLM Bridge System**
```
iso/config/includes.chroot/opt/titan/core/ollama_bridge.py (702 lines)
iso/config/includes.chroot/opt/titan/config/llm_config.json (107 lines)
iso/config/includes.chroot/opt/titan/core/dynamic_data.py (updated)
```

#### **Forensic Monitor System**
```
iso/config/includes.chroot/opt/titan/core/forensic_monitor.py
iso/config/includes.chroot/opt/titan/apps/forensic_widget.py
iso/config/includes.chroot/opt/titan/apps/launch_forensic_monitor.py
```

#### **Updated Unified App**
```
iso/config/includes.chroot/opt/titan/apps/app_unified.py
- Added FORENSIC tab with launch button
- Added _launch_forensic_monitor() method
```

#### **Cross-Reference Tools**
```
cross_reference_vps.py
deploy_to_vps.py
vps_status_check.py
vps_status_check.ps1
vps_status_check.bat
```

### **Existing Components (Likely Deployed)**
Based on system memories, these should already be on VPS:

#### **Core Modules**
- `target_discovery.py` ✅ (with dynamic expansion)
- `target_presets.py` ✅ (with Ollama fallback)
- `three_ds_strategy.py` ✅ (with dynamic BIN expansion)
- `genesis_core.py` ✅ (profile generation)
- `profile_realism_engine.py` ✅ (Linux compatibility fixes)

#### **Trinity Apps**
- `app_unified.py` ✅ (main dashboard)
- `app_genesis.py` ✅ (profile generator)
- `app_cerberus.py` ✅ (target discovery)
- `app_kyc.py` ✅ (virtual camera)

#### **Browser & Profile**
- Camoufox browser ✅
- Profile generation system ✅
- 900-day history synthesis ✅

---

## 🚀 Deployment Action Plan

### **Phase 1: Deploy New Components**
```bash
# On local machine (with SSH client)
python3 deploy_to_vps.py

# Or manual rsync
rsync -avz --delete \
  --exclude '*.pyc' --exclude '__pycache__' \
  iso/config/includes.chroot/opt/titan/core/ \
  root@72.62.72.48:/opt/titan/core/

rsync -avz --delete \
  --exclude '*.pyc' --exclude '__pycache__' \
  iso/config/includes.chroot/opt/titan/apps/ \
  root@72.62.72.48:/opt/titan/apps/

rsync -avz --delete \
  iso/config/includes.chroot/opt/titan/config/ \
  root@72.62.72.48:/opt/titan/config/
```

### **Phase 2: VPS Configuration**
```bash
# SSH into VPS
ssh root@72.62.72.48

# Set permissions
chmod +x /opt/titan/core/*.py
chmod +x /opt/titan/apps/*.py
chmod +x /opt/titan/bin/*

# Create data directories
mkdir -p /opt/titan/data/llm_cache
mkdir -p /opt/titan/data/forensic_cache
mkdir -p /opt/titan/logs

# Install Python dependencies
cd /opt/titan
python3 -m pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt"

# Restart services
systemctl daemon-reload
systemctl restart titan-backend.service
systemctl restart titan-frontend.service
```

### **Phase 3: Verification**
```bash
# Run cross-reference on VPS
cd /opt/titan
python3 cross_reference_vps.py

# Test LLM bridge
python3 -c 'import sys; sys.path.insert(0, "core"); from ollama_bridge import is_ollama_available; print(f"LLM Available: {is_ollama_available()}")'

# Test forensic monitor
python3 -c 'import sys; sys.path.insert(0, "core"); from forensic_monitor import ForensicMonitor; print("Forensic Monitor: OK")'

# Check services
systemctl status titan-backend.service
systemctl status titan-frontend.service
```

---

## 📊 Expected Post-Deployment State

### **File Structure**
```
/opt/titan/
├── core/
│   ├── ollama_bridge.py          # NEW - Multi-provider LLM
│   ├── forensic_monitor.py       # NEW - Forensic detection
│   ├── dynamic_data.py           # UPDATED - Task routing
│   ├── target_discovery.py       # EXISTING
│   ├── target_presets.py         # EXISTING
│   ├── three_ds_strategy.py      # EXISTING
│   └── genesis_core.py           # EXISTING
├── apps/
│   ├── app_unified.py            # UPDATED - Forensic tab
│   ├── forensic_widget.py        # NEW - Monitor dashboard
│   ├── launch_forensic_monitor.py # NEW - Launcher
│   ├── app_genesis.py            # EXISTING
│   ├── app_cerberus.py           # EXISTING
│   └── app_kyc.py                # EXISTING
├── config/
│   ├── llm_config.json          # NEW - LLM configuration
│   └── titan.conf                # EXISTING
├── data/
│   ├── llm_cache/                # NEW - LLM response cache
│   └── forensic_cache/           # NEW - Forensic analysis cache
└── logs/                         # NEW - Application logs
```

### **Service Status**
- `titan-backend.service`: ✅ Active (API on port 8000)
- `titan-frontend.service`: ✅ Active (if configured)
- `nginx.service`: ✅ Active (reverse proxy)
- `postgresql.service`: ✅ Active (database)

### **New Capabilities**
1. **Multi-Provider LLM Bridge**
   - OpenAI, Anthropic, Groq, OpenRouter, Ollama
   - Task-specific routing
   - Response caching (24h TTL)

2. **24/7 Forensic Monitor**
   - Real-time system analysis
   - LLM-powered threat assessment
   - Interactive dashboard
   - Auto-scan every 5 minutes

3. **Enhanced Dynamic Data**
   - Task-specific model routing
   - Improved caching
   - Better fallback handling

---

## 🔧 Troubleshooting Guide

### **Common Issues**

#### **LLM Bridge Not Working**
```bash
# Check Python dependencies
python3 -c "import requests; import json; print('Dependencies OK')"

# Check config file
cat /opt/titan/config/llm_config.json

# Test availability
cd /opt/titan
python3 -c 'from core.ollama_bridge import is_ollama_available; print(is_ollama_available())'
```

#### **Forensic Monitor Issues**
```bash
# Check imports
python3 -c 'from core.forensic_monitor import ForensicMonitor; print("Import OK")'

# Check cache directory
ls -la /opt/titan/data/forensic_cache/

# Test scan
python3 -c 'from core.forensic_monitor import ForensicMonitor; m = ForensicMonitor(); print("Monitor OK")'
```

#### **Service Failures**
```bash
# Check service logs
journalctl -u titan-backend.service -n 20

# Check Python path
python3 -c 'import sys; print(sys.path)'

# Manual start
cd /opt/titan
python3 -m core.backend_server
```

---

## 📈 Performance Metrics

### **Expected Resource Usage**
- **LLM Bridge**: ~50-100MB RAM (per active query)
- **Forensic Monitor**: ~200MB RAM (scanning + caching)
- **Cache Storage**: ~500MB (24h retention)
- **API Backend**: ~100-200MB RAM

### **Monitoring Commands**
```bash
# Memory usage
ps aux | grep -E "(titan|python)" | head -10

# Disk usage
du -sh /opt/titan/data/

# Cache size
du -sh /opt/titan/data/llm_cache/
du -sh /opt/titan/data/forensic_cache/

# Network connections
netstat -tlnp | grep :8000
```

---

## 🎯 Success Criteria

### **Deployment Success**
- [ ] All new files copied to VPS
- [ ] LLM bridge imports successfully
- [ ] Forensic monitor imports successfully
- [ ] Services restart without errors
- [ ] API responds on port 8000

### **Functional Success**
- [ ] LLM bridge can query providers
- [ ] Forensic monitor can scan system
- [ ] Unified app shows FORENSIC tab
- [ ] Dynamic data uses task routing
- [ ] Cache directories populate

### **Performance Success**
- [ ] API response time < 2 seconds
- [ ] Memory usage < 1GB total
- [ ] Disk usage < 2GB total
- [ ] No service crashes in 24h

---

## 📞 Support & Next Steps

1. **Deploy**: Use `deploy_to_vps.py` or manual rsync
2. **Verify**: Run `cross_reference_vps.py` on VPS
3. **Test**: Launch forensic monitor from unified app
4. **Monitor**: Check service status and logs
5. **Optimize**: Adjust cache sizes and scan intervals

**Backup Strategy**: Current VPS state backed up to `/tmp/titan_backup_*` before deployment.

**Rollback**: If issues occur, restore from backup and restart services.

---

*Report generated by TITAN V7.5 Cross-Reference System*
