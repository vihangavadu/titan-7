# Titan-7 Migration Package Preparation
# Creates comprehensive zip with codebase, projects, and memories

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "Titan-7 Migration Package Creator"
Write-Host "=========================================="
Write-Host ""

$baseDir = "C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7"
$outputDir = "C:\Users\Administrator\Downloads\titan-7\titan-7"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Create output directory
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Write-Host "[1/5] Zipping Titan-7 codebase..."
$titan7Zip = "$outputDir\titan-7-complete-$timestamp.zip"

# Compress entire titan-7 directory
Compress-Archive -Path $baseDir -DestinationPath $titan7Zip -CompressionLevel Optimal -Force

$titan7Size = (Get-Item $titan7Zip).Length / 1MB
Write-Host "  ✓ Titan-7 archive created: $([math]::Round($titan7Size, 2)) MB"

# Create memories export
Write-Host "[2/5] Exporting Windsurf memories and context..."
$memoriesDir = "$outputDir\windsurf-memories-$timestamp"
New-Item -ItemType Directory -Force -Path $memoriesDir | Out-Null

# Export current conversation context
$contextFile = "$memoriesDir\conversation-context.txt"
$contextContent = @"
Titan-7 Project Migration Context
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Source: Windows Local Development
Target: VPS 187.77.186.252 (Debian 12)

Project Summary:
Titan OS V9.1+ Full Stack with 110+ Core Python modules, 17+ GUI applications,
AI training pipeline V9.0, Android/Waydroid integration, complete operational playbook,
research documentation, ISO build system, and VPS deployment scripts.

Key Components:
Core: /opt/titan/core (110+ modules)
Apps: /opt/titan/apps (17 apps)
Scripts: /opt/titan/scripts
Training: /opt/titan/training (V9.0 pipeline)
Docs: /opt/titan/docs
Android: /opt/titan/android

Services Required:
Redis (session management), Ollama (AI models), Xray (network proxy),
ntfy (notifications), Titan Dev Hub (port 8877)

VPS Configuration:
Previous VPS: 72.62.72.48 (Hostinger KVM 8)
New VPS: 187.77.186.252 (Fresh Debian 12)
SSH: root@187.77.186.252 (password: Chilaw@123@llm)
XRDP: Port 3389

Migration Checklist:
XRDP + XFCE installed and optimized
Windsurf IDE installed with desktop shortcut
Titan-7 codebase extracted to /root/workspace/titan-7
Python 3.11+ environment configured
All services installed (Redis, Ollama, Xray, ntfy)
AI models deployed (titan-fast, titan-analyst, titan-strategist)
Titan API verified (59 endpoints)
Integration bridge verified (69 subsystems)
GUI apps verified (17 apps, 38 tabs)
Dev Hub deployed and accessible

Important Notes:
Mullvad VPN account: 3018159629819615
Never run mullvad connect over SSH (kills connection)
Use XRDP for GUI access, SSH for deployment
All paths use /opt/titan/ prefix on VPS
PYTHONPATH must include /opt/titan:/opt/titan/core:/opt/titan/apps
"@
$contextContent | Out-File -FilePath $contextFile -Encoding UTF8

Write-Host "  ✓ Context exported"

# Create deployment instructions
Write-Host "[3/5] Creating deployment instructions..."
$deployFile = "$memoriesDir\DEPLOYMENT_INSTRUCTIONS.md"
@"
# Titan-7 VPS Deployment Guide

## Target VPS
- **IP**: 187.77.186.252
- **OS**: Debian 12 (fresh install)
- **User**: root
- **Password**: Chilaw@123@llm
- **XRDP Port**: 3389

## Step 1: Upload Setup Script
``````powershell
scp C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\scripts\vps\setup_optimized_xrdp_windsurf.sh root@187.77.186.252:/tmp/
``````

## Step 2: Run XRDP + Windsurf Setup
``````powershell
ssh root@187.77.186.252 "bash /tmp/setup_optimized_xrdp_windsurf.sh"
``````

This will:
- Install XFCE desktop (lightweight, low latency)
- Configure XRDP with performance optimizations
- Install Windsurf IDE
- Create desktop shortcut
- Set up workspace directories
- Install Python development tools

## Step 3: Upload Titan-7 Codebase
``````powershell
scp titan-7-complete-*.zip root@187.77.186.252:/root/workspace/
``````

## Step 4: Connect via XRDP
1. Open Remote Desktop Connection (mstsc.exe)
2. Computer: 187.77.186.252:3389
3. Username: root
4. Password: Chilaw@123@llm
5. Click "Connect"

## Step 5: Extract and Deploy (via XRDP session)
``````bash
cd /root/workspace
unzip titan-7-complete-*.zip
cd titan-7

# Run master installer
bash scripts/vps/deploy_full_titan_stack.sh
``````

## Step 6: Verify Installation
``````bash
cd /root/workspace/titan-7
python3 scripts/verify_vps_everything.py
``````

## XRDP Performance Tips
- Disable desktop compositing (already configured)
- Use 24-bit color depth (not 32-bit)
- Disable wallpaper for faster rendering
- Close unused applications
- Use wired connection if possible

## Windsurf IDE Setup
1. Double-click Windsurf icon on desktop
2. Open folder: /root/workspace/titan-7
3. Install recommended extensions
4. Configure Python interpreter: /usr/bin/python3
5. Set PYTHONPATH in settings

## Troubleshooting
- **XRDP won't connect**: Check firewall (ufw status)
- **Black screen**: Restart xrdp (systemctl restart xrdp)
- **Windsurf won't start**: Check logs (/var/log/windsurf/)
- **Slow performance**: Reduce color depth, disable effects
"@ | Out-File -FilePath $deployFile -Encoding UTF8

Write-Host "  ✓ Deployment instructions created"

# Create quick reference
Write-Host "[4/5] Creating quick reference..."
$quickRef = "$memoriesDir\QUICK_REFERENCE.md"
@"
# Titan-7 Quick Reference

## VPS Access
``````
XRDP: 187.77.186.252:3389 (root / Chilaw@123@llm)
SSH:  ssh root@187.77.186.252
``````

## Key Directories
``````
/root/workspace/titan-7          - Main codebase
/opt/titan/core                  - Core modules (110+)
/opt/titan/apps                  - GUI apps (17)
/opt/titan/scripts               - Deployment scripts
/opt/titan/training              - AI training pipeline
/opt/titan/docs                  - Documentation
``````

## Essential Commands
``````bash
# Verify installation
python3 scripts/verify_vps_everything.py

# Start services
systemctl start redis-server ollama xray ntfy titan-dev-hub

# Check service status
systemctl status redis-server ollama xray ntfy

# Launch Titan API
python3 /opt/titan/core/titan_api.py

# Launch Dev Hub
python3 /opt/titan/apps/titan_dev_hub.py --host 0.0.0.0 --port 8877
``````

## AI Models
``````bash
# List models
ollama list

# Pull models
ollama pull mistral:7b
ollama pull qwen2.5:7b
ollama pull deepseek-r1:8b

# Create custom models
ollama create titan-fast -f /opt/titan/training/phase1/titan-fast-v9.modelfile
ollama create titan-analyst -f /opt/titan/training/phase1/titan-analyst-v9.modelfile
ollama create titan-strategist -f /opt/titan/training/phase1/titan-strategist-v9.modelfile
``````

## Important Files
- `/opt/titan/config/titan.env` - Environment variables
- `/opt/titan/config/llm_config.json` - AI routing config
- `/opt/titan/core/integration_bridge.py` - Core integration
- `/opt/titan/core/titan_api.py` - REST API (59 endpoints)

## Mullvad VPN
- Account: 3018159629819615
- **NEVER** run `mullvad connect` over SSH!
- Configure via XRDP GUI only

## Ports
- 3389: XRDP
- 6379: Redis
- 11434: Ollama
- 8877: Titan Dev Hub
- 5000: Titan API (default)
"@ | Out-File -FilePath $quickRef -Encoding UTF8

Write-Host "  ✓ Quick reference created"

# Zip memories package
Write-Host "[5/5] Creating memories archive..."
$memoriesZip = "$outputDir\windsurf-memories-$timestamp.zip"
Compress-Archive -Path $memoriesDir -DestinationPath $memoriesZip -Force
Remove-Item -Recurse -Force $memoriesDir

$memoriesSize = (Get-Item $memoriesZip).Length / 1KB
Write-Host "  ✓ Memories archive created: $([math]::Round($memoriesSize, 2)) KB"

Write-Host ""
Write-Host "=========================================="
Write-Host "✓ Migration Package Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Created files:"
Write-Host "  1. $titan7Zip"
Write-Host "     Size: $([math]::Round($titan7Size, 2)) MB"
Write-Host ""
Write-Host "  2. $memoriesZip"
Write-Host "     Contains: Context, deployment guide, quick reference"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run setup script on VPS:"
Write-Host "     scp scripts\vps\setup_optimized_xrdp_windsurf.sh root@187.77.186.252:/tmp/"
Write-Host "     ssh root@187.77.186.252 'bash /tmp/setup_optimized_xrdp_windsurf.sh'"
Write-Host ""
Write-Host "  2. Upload codebase:"
Write-Host "     scp $titan7Zip root@187.77.186.252:/root/workspace/"
Write-Host ""
Write-Host "  3. Connect via XRDP to 187.77.186.252:3389"
Write-Host "=========================================="
