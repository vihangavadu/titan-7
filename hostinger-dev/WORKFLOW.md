# Titan OS Development Workflow on Hostinger VPS

## Prerequisites
- Hostinger VPS (KVM, Debian 12 recommended)
- API token from https://hpanel.hostinger.com/profile/api
- Windsurf IDE with MCP configured (see MCP_SETUP.md)

---

## Workflow 1: Initial VPS Setup

```
1. Purchase VPS via hPanel or API
2. Setup VPS with Debian 12 template
3. Attach SSH key for passwordless access
4. Configure firewall (allow SSH 22, RDP 3389, Titan API 7700)
5. Set hostname to "titan-vps"
6. Create initial snapshot
```

### Via MCP (ask Cascade):
```
"List available OS templates"
"Setup my VPS with Debian 12 and hostname titan-vps"
"Attach my SSH key to the VPS"
"Create a firewall with rules for SSH, RDP, and port 7700"
"Create a snapshot"
```

### Via Python Client:
```python
from titan_vps_client import TitanVPSClient
client = TitanVPSClient()
client.print_status()
```

---

## Workflow 2: Deploy Titan OS to VPS

```
1. SSH into VPS
2. Clone titan-7 repo
3. Run install scripts
4. Start services
5. Verify deployment
```

### SSH Commands:
```bash
ssh root@<VPS_IP>

# Clone repo
git clone https://github.com/malithwishwa02-dot/titan-7.git /opt/titan
cd /opt/titan

# Install dependencies
apt update && apt install -y python3-pip python3-venv xrdp xfce4
pip3 install -r src/apps/requirements.txt

# Start services
python3 src/core/titan_services.py start

# Verify
python3 src/core/titan_master_verify.py
```

---

## Workflow 3: Development Cycle

```
1. Make code changes locally in Windsurf
2. Git push to GitHub
3. SSH into VPS and git pull
4. Restart affected services
5. Test via RDP or API
```

### Quick Sync (via MCP):
```
"Restart my VPS to apply changes"
"Create a snapshot before I make changes"
```

### Quick Sync (manual):
```bash
# On VPS:
cd /opt/titan && git pull origin main
systemctl restart titan-services  # or manual restart
```

---

## Workflow 4: Emergency Recovery

If SSH breaks (e.g., after eBPF lockout):

### Via MCP:
```
"Start recovery mode on my VPS"
```

### Via Python:
```python
client = TitanVPSClient()
vm = client.find_titan_vm()
client.emergency_recovery(vm["id"], "YourRecoveryPassword123!")
```

### Via hPanel:
1. Go to https://hpanel.hostinger.com
2. Select your VPS
3. Click "Recovery Mode" → Start
4. SSH in with recovery credentials
5. Fix the issue
6. Stop recovery mode

---

## Workflow 5: Backup & Restore

### Before risky changes:
```
"Create a snapshot of my VPS"
```

### If something breaks:
```
"Restore the last snapshot on my VPS"
```

### Automatic backups:
Hostinger creates automatic backups. List them:
```
"List backups for my VPS"
```

---

## Workflow 6: Firewall Management

### Titan requires these ports open:
| Port | Service | Direction |
|------|---------|-----------|
| 22 | SSH | Inbound |
| 3389 | RDP (xrdp) | Inbound |
| 7700 | Titan API | Inbound |
| 51820 | WireGuard VPN | Inbound |
| 443 | HTTPS (outbound) | Outbound |
| 80 | HTTP (outbound) | Outbound |

### Create Titan firewall via MCP:
```
"Create a firewall called titan-fw with rules for ports 22, 3389, 7700, and 51820"
"Activate the titan-fw firewall on my VPS"
```

---

## Workflow 7: Post-Install Script

Create an automated setup script that runs after VPS recreation:

```bash
#!/bin/bash
# Titan OS V8.1 Post-Install Script
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git xrdp xfce4 \
    wireguard nftables libfaketime fonts-liberation
pip3 install PyQt6 requests playwright chromadb sentence-transformers
playwright install firefox
git clone https://github.com/malithwishwa02-dot/titan-7.git /opt/titan
cd /opt/titan && pip3 install -r src/apps/requirements.txt
systemctl enable xrdp
echo "Titan OS V8.1 installed successfully" > /root/titan-install.log
```

### Register via API:
```python
client = TitanVPSClient()
client.create_post_install_script(
    name="titan-v81-setup",
    content=open("post_install.sh").read()
)
```

---

## Key API Endpoints for Daily Use

| What | Endpoint | MCP Command |
|------|----------|-------------|
| Check VPS status | `GET /api/vps/v1/virtual-machines` | "List my VPS" |
| Restart VPS | `POST .../restart` | "Restart my VPS" |
| Create snapshot | `POST .../snapshot` | "Snapshot my VPS" |
| Recovery mode | `POST .../recovery` | "Start recovery" |
| View actions | `GET .../actions` | "Show VPS actions" |
| Firewall rules | `GET /api/vps/v1/firewall` | "Show firewall" |
