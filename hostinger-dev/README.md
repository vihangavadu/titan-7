# Hostinger VPS Development — Titan OS V8.1

## Overview

This folder contains everything needed to develop and deploy Titan OS on Hostinger VPS
using the Hostinger Developer API, integrated with Windsurf IDE via MCP (Model Context Protocol).

## Setup Steps

### 1. Get Your API Token
1. Go to https://hpanel.hostinger.com/profile/api
2. Create a new API token
3. Copy the token — you'll need it for step 2

### 2. Configure Windsurf MCP
Hostinger provides an **official MCP server**: https://github.com/hostinger/api-mcp-server

Add this to your Windsurf MCP config (`~/.codeium/windsurf/mcp_config.json`):

```json
{
  "mcpServers": {
    "hostinger": {
      "command": "npx",
      "args": ["-y", "@hostinger/mcp-server"],
      "env": {
        "HOSTINGER_API_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### 3. Install Python SDK (optional, for scripts)
```bash
pip install hostinger_api
```

### 4. Install CLI Tool (optional)
```bash
# Via npm
npm install -g @hostinger/api-cli

# Usage
hapi vps vm list
hapi vps vm get <vmId>
```

## Files in This Folder

| File | Purpose |
|------|---------|
| `README.md` | This file — setup guide |
| `API_REFERENCE.md` | Complete Hostinger API endpoint reference for Titan development |
| `MCP_SETUP.md` | Detailed MCP server configuration for Windsurf IDE |
| `titan_vps_client.py` | Python client wrapping all VPS API endpoints for Titan operations |
| `deploy_titan.py` | One-shot Titan OS deployment script via API |
| `mcp_config.json` | Template MCP config for Windsurf |
| `WORKFLOW.md` | Step-by-step development workflow |

## Architecture

```
Windsurf IDE (your machine)
    │
    ├── MCP Server (@hostinger/mcp-server)
    │   └── Hostinger API Token (Bearer auth)
    │
    └── Hostinger Developer API (https://developers.hostinger.com)
        ├── VPS: Virtual Machine — start/stop/restart/recreate/setup
        ├── VPS: Firewall — create rules, activate/deactivate
        ├── VPS: SSH Keys — attach/create public keys
        ├── VPS: Backups — list/restore backups
        ├── VPS: Snapshots — create/restore/delete snapshots
        ├── VPS: Docker — manage compose projects
        ├── VPS: Recovery — start/stop recovery mode
        ├── VPS: Post-install Scripts — automate setup
        ├── VPS: PTR Records — reverse DNS
        ├── VPS: OS Templates — available OS images
        ├── DNS: Zones — manage DNS records
        ├── Domains: Portfolio — domain management
        └── Billing: Subscriptions — account management
```

## Quick Commands (after MCP setup)

Once the MCP server is configured, you can ask Cascade directly:
- "List my VPS instances"
- "Restart my VPS"
- "Create a snapshot of my VPS"
- "Show firewall rules"
- "Deploy Titan to my VPS"
