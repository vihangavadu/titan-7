# Hostinger Developer API — Complete Reference for Titan Development

**Base URL:** `https://developers.hostinger.com`
**Auth:** `Authorization: Bearer YOUR_API_TOKEN`
**Content-Type:** `application/json`
**Pagination:** 50 items/page, `?page=N`
**Rate Limit:** 429 on excess, IP blocked on repeat violations

---

## VPS: Virtual Machine (CRITICAL for Titan)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/virtual-machines` | List all VPS instances |
| GET | `/api/vps/v1/virtual-machines/{vmId}` | Get VPS details (IP, state, OS, specs) |
| POST | `/api/vps/v1/virtual-machines` | Purchase new VPS |
| POST | `/api/vps/v1/virtual-machines/{vmId}/setup` | Setup newly purchased VPS |
| POST | `/api/vps/v1/virtual-machines/{vmId}/start` | Start VPS |
| POST | `/api/vps/v1/virtual-machines/{vmId}/stop` | Stop VPS |
| POST | `/api/vps/v1/virtual-machines/{vmId}/restart` | Restart VPS |
| POST | `/api/vps/v1/virtual-machines/{vmId}/recreate` | Reinstall OS (destructive) |
| PUT | `/api/vps/v1/virtual-machines/{vmId}/hostname` | Set hostname |
| DELETE | `/api/vps/v1/virtual-machines/{vmId}/hostname` | Reset hostname |
| PUT | `/api/vps/v1/virtual-machines/{vmId}/nameservers` | Set DNS resolvers |
| PUT | `/api/vps/v1/virtual-machines/{vmId}/panel-password` | Reset panel password |
| PUT | `/api/vps/v1/virtual-machines/{vmId}/root-password` | Reset root password |

## VPS: Firewall

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/firewall` | List all firewalls |
| POST | `/api/vps/v1/firewall` | Create new firewall |
| GET | `/api/vps/v1/firewall/{fwId}` | Get firewall details |
| PUT | `/api/vps/v1/firewall/{fwId}` | Update firewall |
| DELETE | `/api/vps/v1/firewall/{fwId}` | Delete firewall |
| POST | `/api/vps/v1/firewall/{fwId}/activate/{vmId}` | Activate on VPS |
| POST | `/api/vps/v1/firewall/{fwId}/deactivate/{vmId}` | Deactivate from VPS |
| POST | `/api/vps/v1/firewall/{fwId}/rules` | Create firewall rule |
| PUT | `/api/vps/v1/firewall/{fwId}/rules/{ruleId}` | Update rule |
| DELETE | `/api/vps/v1/firewall/{fwId}/rules/{ruleId}` | Delete rule |
| POST | `/api/vps/v1/firewall/{fwId}/sync/{vmId}` | Sync rules to VPS |

## VPS: SSH Keys

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/public-keys` | List SSH keys |
| POST | `/api/vps/v1/public-keys` | Create SSH key |
| DELETE | `/api/vps/v1/public-keys/{keyId}` | Delete SSH key |
| POST | `/api/vps/v1/public-keys/attach/{vmId}` | Attach key to VPS |

## VPS: Backups & Snapshots

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/virtual-machines/{vmId}/backups` | List backups |
| POST | `/api/vps/v1/virtual-machines/{vmId}/backups/{backupId}/restore` | Restore backup |
| GET | `/api/vps/v1/virtual-machines/{vmId}/snapshot` | Get snapshot |
| POST | `/api/vps/v1/virtual-machines/{vmId}/snapshot` | Create snapshot |
| POST | `/api/vps/v1/virtual-machines/{vmId}/snapshot/restore` | Restore snapshot |
| DELETE | `/api/vps/v1/virtual-machines/{vmId}/snapshot` | Delete snapshot |

## VPS: Docker Manager (experimental)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/virtual-machines/{vmId}/docker` | List compose projects |
| POST | `/api/vps/v1/virtual-machines/{vmId}/docker` | Create compose project |
| GET | `/api/vps/v1/virtual-machines/{vmId}/docker/{project}` | Get project |
| PUT | `/api/vps/v1/virtual-machines/{vmId}/docker/{project}` | Update project |
| DELETE | `/api/vps/v1/virtual-machines/{vmId}/docker/{project}/down` | Delete project |
| POST | `/api/vps/v1/virtual-machines/{vmId}/docker/{project}/restart` | Restart project |
| GET | `/api/vps/v1/virtual-machines/{vmId}/docker/{project}/containers` | List containers |
| GET | `/api/vps/v1/virtual-machines/{vmId}/docker/{project}/logs` | Get logs |

## VPS: Recovery & Actions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vps/v1/virtual-machines/{vmId}/recovery` | Start recovery mode |
| DELETE | `/api/vps/v1/virtual-machines/{vmId}/recovery` | Stop recovery mode |
| GET | `/api/vps/v1/virtual-machines/{vmId}/actions` | List actions history |
| GET | `/api/vps/v1/virtual-machines/{vmId}/actions/{actionId}` | Get action detail |

## VPS: PTR Records & OS Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vps/v1/virtual-machines/{vmId}/ptr/{ipId}` | Create PTR record |
| DELETE | `/api/vps/v1/virtual-machines/{vmId}/ptr/{ipId}` | Delete PTR record |
| GET | `/api/vps/v1/templates` | List OS templates |

## VPS: Post-Install Scripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/post-install-scripts` | List scripts |
| POST | `/api/vps/v1/post-install-scripts` | Create script |
| GET | `/api/vps/v1/post-install-scripts/{id}` | Get script |
| PUT | `/api/vps/v1/post-install-scripts/{id}` | Update script |
| DELETE | `/api/vps/v1/post-install-scripts/{id}` | Delete script |

## VPS: Malware Scanner (Monarx)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vps/v1/virtual-machines/{vmId}/monarx` | Get scan metrics |
| POST | `/api/vps/v1/virtual-machines/{vmId}/monarx` | Install Monarx |
| DELETE | `/api/vps/v1/virtual-machines/{vmId}/monarx` | Uninstall Monarx |

## DNS: Zone Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dns/v1/zones/{domain}` | Get DNS records |
| PUT | `/api/dns/v1/zones/{domain}` | Update DNS records |
| DELETE | `/api/dns/v1/zones/{domain}` | Delete DNS records |
| POST | `/api/dns/v1/zones/{domain}/reset` | Reset DNS to default |
| POST | `/api/dns/v1/zones/{domain}/validate` | Validate DNS changes |
| GET | `/api/dns/v1/snapshots/{domain}` | List DNS snapshots |
| GET | `/api/dns/v1/snapshots/{domain}/{snapId}` | Get DNS snapshot |

## Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/billing/v1/catalog` | Get catalog (plans & pricing) |
| GET | `/api/billing/v1/subscriptions` | List subscriptions |
| GET | `/api/billing/v1/payment-methods` | List payment methods |

## SDKs & Tools

| Tool | Install | Repo |
|------|---------|------|
| **MCP Server** | `npx @hostinger/mcp-server` | https://github.com/hostinger/api-mcp-server |
| **Python SDK** | `pip install hostinger_api` | https://github.com/hostinger/api-python-sdk |
| **CLI** | `npm i -g @hostinger/api-cli` | https://github.com/hostinger/api-cli |
| **Ansible** | collection install | https://github.com/hostinger/ansible-collection-hostinger |
| **Terraform** | provider config | https://github.com/hostinger/terraform-provider-hostinger |
| **TypeScript** | `npm i hostinger-api-sdk` | https://github.com/hostinger/api-typescript-sdk |
