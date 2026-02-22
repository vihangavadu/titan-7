# Manual VPS Deployment Instructions

## 🚀 Quick Deploy (Manual Steps)

### **Step 1: Connect to VPS**
```bash
# Using SSH client (Git Bash, WSL, or PowerShell)
ssh root@72.62.72.48
# Password: Xt7mKp9wRv3n.Jq2026
```

### **Step 2: Create Backup**
```bash
# On VPS
mkdir -p /tmp/titan_backup_$(date +%Y%m%d_%H%M%S)
cp -r /opt/titan/* /tmp/titan_backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || echo "Backup created"
```

### **Step 3: Stop Services**
```bash
# On VPS
systemctl stop titan-backend.service 2>/dev/null || true
systemctl stop titan-frontend.service 2>/dev/null || true
systemctl stop titan-monitor.service 2>/dev/null || true
```

### **Step 4: Copy Files (from local machine)**
```bash
# From local machine (in Git Bash or WSL)
rsync -avz --delete \
  --exclude '*.pyc' --exclude '__pycache__' --exclude '.git' \
  iso/config/includes.chroot/opt/titan/core/ \
  root@72.62.72.48:/opt/titan/core/

rsync -avz --delete \
  --exclude '*.pyc' --exclude '__pycache__' --exclude '.git' \
  iso/config/includes.chroot/opt/titan/apps/ \
  root@72.62.72.48:/opt/titan/apps/

rsync -avz --delete \
  --exclude '*.pyc' --exclude '__pycache__' --exclude '.git' \
  iso/config/includes.chroot/opt/titan/config/ \
  root@72.62.72.48:/opt/titan/config/

# Copy cross-reference tools
rsync -avz cross_reference_vps.py root@72.62.72.48:/opt/titan/
```

### **Step 5: Setup VPS (back on VPS)**
```bash
# Set permissions
chmod +x /opt/titan/core/*.py
chmod +x /opt/titan/apps/*.py
chmod +x /opt/titan/cross_reference_vps.py

# Create directories
mkdir -p /opt/titan/data/llm_cache
mkdir -p /opt/titan/data/forensic_cache
mkdir -p /opt/titan/logs

# Set ownership
chown -R root:root /opt/titan
```

### **Step 6: Install Dependencies**
```bash
# Install Python packages
cd /opt/titan
python3 -m pip install requests psutil PyQt6 2>/dev/null || echo "Some packages may already exist"
```

### **Step 7: Restart Services**
```bash
# Reload systemd
systemctl daemon-reload

# Start services
systemctl start titan-backend.service
systemctl start titan-frontend.service 2>/dev/null || echo "Frontend service not found"
systemctl start titan-monitor.service 2>/dev/null || echo "Monitor service not found"
```

### **Step 8: Verify Deployment**
```bash
# Test LLM bridge
python3 -c 'import sys; sys.path.insert(0, "core"); from ollama_bridge import is_ollama_available; print(f"LLM Available: {is_ollama_available()}")'

# Test forensic monitor
python3 -c 'import sys; sys.path.insert(0, "core"); from forensic_monitor import ForensicMonitor; print("Forensic Monitor: OK")'

# Check services
systemctl status titan-backend.service --no-pager
systemctl status titan-frontend.service --no-pager

# Check API
curl -s http://localhost:8000/health || echo "API check failed"
```

### **Step 9: Run Cross-Reference**
```bash
# Run comprehensive analysis
cd /opt/titan
python3 cross_reference_vps.py

# View report
cat vps_cross_reference_*.json | python3 -m json.tool | head -50
```

---

## 🔍 What Gets Deployed

### **New Components**
- ✅ `ollama_bridge.py` - Multi-provider LLM system
- ✅ `llm_config.json` - LLM configuration
- ✅ `forensic_monitor.py` - 24/7 forensic detection
- ✅ `forensic_widget.py` - PyQt6 dashboard
- ✅ `launch_forensic_monitor.py` - Standalone launcher
- ✅ Updated `app_unified.py` - With FORENSIC tab
- ✅ Updated `dynamic_data.py` - Task routing support

### **Updated Components**
- ✅ `dynamic_data.py` - Now uses task-specific LLM routing
- ✅ `app_unified.py` - Added forensic monitor integration

---

## 📊 Expected Results

### **After Deployment**
```
/opt/titan/
├── core/
│   ├── ollama_bridge.py          # NEW - 702 lines
│   ├── forensic_monitor.py       # NEW - Comprehensive analysis
│   ├── dynamic_data.py           # UPDATED - Task routing
│   └── [existing files...]
├── apps/
│   ├── app_unified.py            # UPDATED - Forensic tab
│   ├── forensic_widget.py        # NEW - PyQt6 dashboard
│   ├── launch_forensic_monitor.py # NEW - Launcher
│   └── [existing apps...]
├── config/
│   ├── llm_config.json          # NEW - Multi-provider config
│   └── [existing configs...]
├── data/
│   ├── llm_cache/                # NEW - LLM responses
│   └── forensic_cache/           # NEW - Analysis results
└── cross_reference_vps.py        # NEW - Analysis tool
```

### **Service Status**
```
titan-backend.service    ✅ Active (API port 8000)
titan-frontend.service   ✅ Active (if configured)
nginx.service           ✅ Active (reverse proxy)
postgresql.service      ✅ Active (database)
```

---

## 🛠️ Troubleshooting

### **If LLM Bridge Fails**
```bash
# Check Python path
python3 -c 'import sys; print(sys.path)'

# Test imports manually
python3 -c 'import requests; import json; print("Basic imports OK")'

# Check config file
cat /opt/titan/config/llm_config.json
```

### **If Forensic Monitor Fails**
```bash
# Check imports
python3 -c 'from core.forensic_monitor import ForensicMonitor; print("Import OK")'

# Check cache directory
ls -la /opt/titan/data/forensic_cache/

# Test basic functionality
python3 -c 'from core.forensic_monitor import ForensicMonitor; m = ForensicMonitor(); print("Monitor created")'
```

### **If Services Won't Start**
```bash
# Check logs
journalctl -u titan-backend.service -n 20

# Check Python errors
cd /opt/titan
python3 -m core.backend_server

# Check permissions
ls -la /opt/titan/core/*.py
```

---

## 🎯 Success Indicators

### **Deployment Success**
- [ ] All files copied without errors
- [ ] Services start successfully
- [ ] API responds on port 8000
- [ ] No import errors in Python modules

### **Functional Success**
- [ ] LLM bridge can check provider availability
- [ ] Forensic monitor can scan system state
- [ ] Unified app shows new FORENSIC tab
- [ ] Cross-reference runs without errors

### **Performance Success**
- [ ] API response time < 2 seconds
- [ ] Memory usage reasonable (< 1GB total)
- [ ] Cache directories populate correctly

---

## 📞 Next Steps After Deployment

1. **Launch Forensic Monitor**: Open unified app → FORENSIC tab → Launch
2. **Configure LLM Keys**: Edit `/opt/titan/config/llm_config.json` with API keys
3. **Test Task Routing**: Verify different tasks use appropriate models
4. **Monitor Performance**: Watch memory usage and response times
5. **Review Reports**: Check forensic analysis results

---

## 🔄 Rollback Plan

If deployment causes issues:
```bash
# Stop services
systemctl stop titan-*.service

# Restore from backup
cp -r /tmp/titan_backup_*/opt/titan/* /opt/titan/

# Restart services
systemctl start titan-backend.service
systemctl start titan-frontend.service

# Verify
systemctl status titan-*.service
```

---

*Deploy TITAN V7.5 with new LLM bridge and forensic monitoring capabilities!*
