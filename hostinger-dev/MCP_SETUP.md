# Hostinger MCP Server Setup for Windsurf IDE

## What is MCP?

Model Context Protocol (MCP) allows Windsurf/Cascade to directly interact with external APIs.
Hostinger's official MCP server gives Cascade the ability to manage your VPS, DNS, domains,
and billing — all from within the IDE.

## Official MCP Server

**Repository:** https://github.com/hostinger/api-mcp-server

## Step 1: Get API Token

1. Login to https://hpanel.hostinger.com
2. Go to **Profile** → **API** (https://hpanel.hostinger.com/profile/api)
3. Click **Create Token**
4. Set permissions: same as your user account
5. Set expiry: recommended 90 days (or no expiry for dev)
6. **Copy the token immediately** — it won't be shown again

## Step 2: Configure Windsurf MCP

Create or edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "hostinger": {
      "command": "npx",
      "args": ["-y", "@hostinger/mcp-server"],
      "env": {
        "HOSTINGER_API_TOKEN": "YOUR_API_TOKEN_HERE"
      }
    }
  }
}
```

**On Windows**, the path is:
```
C:\Users\<username>\.codeium\windsurf\mcp_config.json
```

## Step 3: Restart Windsurf

After saving `mcp_config.json`, restart Windsurf IDE completely.
The MCP server will start automatically when Cascade needs it.

## Step 4: Verify

Ask Cascade: "List my Hostinger VPS instances"

If configured correctly, Cascade will call the Hostinger MCP server and return your VPS list.

## Available MCP Tools

Once configured, Cascade can use these tools directly:

### VPS Management
- `vps_list_virtual_machines` — List all VPS instances
- `vps_get_virtual_machine` — Get details of a specific VPS
- `vps_start_virtual_machine` — Start a VPS
- `vps_stop_virtual_machine` — Stop a VPS
- `vps_restart_virtual_machine` — Restart a VPS
- `vps_recreate_virtual_machine` — Reinstall OS on VPS
- `vps_setup_virtual_machine` — Setup a newly purchased VPS
- `vps_set_hostname` — Set VPS hostname
- `vps_set_nameservers` — Set DNS resolvers
- `vps_get_metrics` — Get CPU/RAM/disk/network metrics

### VPS Firewall
- `vps_list_firewalls` — List firewall configs
- `vps_create_firewall` — Create new firewall
- `vps_activate_firewall` — Apply firewall to VPS
- `vps_deactivate_firewall` — Remove firewall from VPS
- `vps_create_firewall_rule` — Add firewall rule
- `vps_delete_firewall_rule` — Remove firewall rule

### VPS SSH Keys
- `vps_list_public_keys` — List SSH keys
- `vps_create_public_key` — Add new SSH key
- `vps_attach_public_key` — Attach key to VPS
- `vps_delete_public_key` — Remove SSH key

### VPS Backups & Snapshots
- `vps_list_backups` — List available backups
- `vps_restore_backup` — Restore from backup
- `vps_get_snapshot` — Get current snapshot info
- `vps_create_snapshot` — Create new snapshot
- `vps_restore_snapshot` — Restore from snapshot
- `vps_delete_snapshot` — Delete snapshot

### VPS Docker Manager
- `vps_list_docker_projects` — List Docker Compose projects
- `vps_get_docker_project` — Get project details
- `vps_create_docker_project` — Deploy new compose project
- `vps_restart_docker_project` — Restart project
- `vps_update_docker_project` — Pull latest images & recreate
- `vps_delete_docker_project` — Remove project
- `vps_get_docker_logs` — Get project logs

### VPS Recovery & Templates
- `vps_start_recovery_mode` — Boot into rescue mode
- `vps_stop_recovery_mode` — Exit rescue mode
- `vps_list_templates` — List available OS templates
- `vps_get_actions` — View operation history

### VPS Post-install Scripts
- `vps_list_post_install_scripts` — List automation scripts
- `vps_create_post_install_script` — Create new script
- `vps_update_post_install_script` — Update script
- `vps_delete_post_install_script` — Remove script

### DNS Management
- `dns_list_zones` — List DNS records
- `dns_update_records` — Update DNS records
- `dns_delete_records` — Delete DNS records
- `dns_validate_records` — Validate before applying
- `dns_list_snapshots` — List DNS snapshots

### Domains
- `domains_list_portfolio` — List domains
- `domains_purchase_domain` — Buy new domain
- `domains_enable_domain_lock` — Lock domain transfers
- `domains_enable_privacy_protection` — Enable WHOIS privacy

### Billing
- `billing_list_subscriptions` — List active subscriptions
- `billing_get_catalog` — View available plans & pricing
- `billing_list_payment_methods` — List payment methods

## Titan-Specific Workflows

### Deploy Titan to VPS
```
Ask Cascade: "Deploy Titan OS to my VPS <vmId>"
```
This will:
1. Create a snapshot (backup current state)
2. SSH into VPS
3. Clone titan-7 repo
4. Run install scripts
5. Verify deployment

### Emergency Recovery
```
Ask Cascade: "Start recovery mode on my VPS"
```
This boots the VPS into rescue mode if SSH is broken (e.g., after eBPF lockout).

### Quick Snapshot Before Changes
```
Ask Cascade: "Create a snapshot of my VPS before I make changes"
```

## Security Notes

- API token has **same permissions as your user account**
- Token is stored in local MCP config — not committed to git
- The `.gitignore` excludes `mcp_config.json` with real tokens
- Rate limit: don't exceed API limits or your IP gets temporarily blocked
