# 08 — App: Admin Panel

## Overview

**File:** `src/apps/titan_admin.py`
**Color Theme:** Amber (#f59e0b)
**Tabs:** 5
**Modules Wired:** 18
**Purpose:** System administration, diagnostics, service management, automation control, and configuration.

The Admin Panel is where the operator manages the Titan OS system itself — starting/stopping services, monitoring health, running automation, and configuring the environment. It consolidates what was previously three separate apps (Mission Control, Dev Hub, Bug Reporter) into a single panel.

---

## Tab 1: SERVICES — Health Monitoring & Service Control

### What This Tab Does
Manages all background services and monitors system resource usage.

### Features

**Service Manager**
- `TitanServiceManager` integration via `get_service_manager()`
- Service list with status indicators: Running (green), Stopped (red), Error (yellow)
- Individual start/stop buttons per service
- "Start All" / "Stop All" bulk controls via `start_all_services()` / `stop_all_services()`
- Services managed: API server, TX Monitor, Intel Monitor, Forensic Monitor, Cockpit Daemon

**Health Check Dashboard**
- `HealthCheckWorker` runs comprehensive health scan in background thread
- **Module Count:** Total `.py` files in `src/core/`
- **Importability:** How many modules import successfully vs failures (with error messages)
- **RAM Usage:** Used/total GB and percentage (via `psutil`)
- **Disk Space:** Free GB remaining
- **AI Status:** Ollama availability and model status

**Memory Pressure Manager**
- `MemoryPressureManager` from `titan_services.py`
- Monitors RAM usage and triggers cleanup when threshold exceeded
- Configurable pressure threshold (default 80%)
- Auto-releases cached profiles and log buffers

**Service Status Table**
- `get_services_status()` returns status of all registered services
- Columns: service name, status, uptime, PID, memory usage
- Auto-refreshes periodically

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Service Action | Start/stop specific service | Start "API Server" |
| Bulk Action | Start all / Stop all | "Start All" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Health Report | Module count, importability, RAM, disk, AI status |
| Service Table | All services with status and resource usage |
| Memory Status | Current RAM pressure and cleanup status |

---

## Tab 2: TOOLS — Bug Reporter, Auto-Patcher, AI Config

### What This Tab Does
Development and maintenance tools for bug reporting, automated parameter tuning, and AI model configuration.

### Features

**Bug Patch Bridge**
- `BugPatchBridge` integration for structured bug reporting
- Bug description input with category selector
- Severity levels: Critical / High / Medium / Low
- Auto-captures system state at time of report
- Suggests patches based on similar past bugs

**Auto-Patcher Status**
- `TitanAutoPatcher` dashboard showing:
  - Last patch run timestamp
  - Parameters adjusted
  - Before/after performance comparison
  - Pending patch queue
- Manual "Run Patcher" button for immediate parameter tuning
- Patch history with rollback option

**AI Configuration**
- `OllamaBridge` configuration:
  - Model selection (mistral:7b, qwen2.5:7b, deepseek-r1:8b)
  - Temperature setting
  - Context window size
  - "Test Connection" button
- `ai_intelligence_engine` status: `is_ai_available()`, `get_ai_status()`
- Model download status if missing

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Bug Description | What went wrong | "Profile generation fails with >500 day age" |
| Bug Severity | Impact level | "High" |
| AI Model | Preferred model | "mistral:7b" |
| Temperature | AI creativity | 0.7 |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Bug Report ID | Tracked bug with system state snapshot |
| Patch Suggestion | Automated fix recommendation |
| AI Status | Model availability and health |

---

## Tab 3: SYSTEM — Module Health, Kill Switch, Forensics

### What This Tab Does
System-level diagnostics: module health, emergency controls, VPN status, and forensic monitoring.

### Features

**Module Health Matrix**
- Health check results from `HealthCheckWorker`
- Table of all core modules with import status
- Failed modules listed with specific error messages
- Percentage indicator: "87/90 modules importable"

**Kill Switch**
- `KillSwitch` controls from `kill_switch.py`
- ARM button (requires confirmation dialog)
- PANIC button (double confirmation: "Are you sure?" + "This cannot be undone")
- `arm_kill_switch()` — prepares for emergency wipe
- `send_panic_signal()` — triggers immediate data destruction
- Visual status: Disarmed (gray) / Armed (yellow) / Triggered (red)

**VPN Status**
- `LucidVPN` / `VPNStatus` display
- Connection state, exit IP, uptime
- Quick disconnect button

**Forensic Monitor**
- `ForensicMonitor` integration
- Real-time artifact detection status
- Last scan timestamp and result
- Alert count

**System Integrity**
- `verify_system_integrity()` — checks all core files
- `get_boot_status()` — boot verification state
- `MasterVerifier.verify()` — comprehensive integrity check
- Results table: file, expected hash, actual hash, status

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Kill Switch | Arm/Panic | ARM → confirm → PANIC |
| Integrity Check | Run verification | "Verify System" button |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Module Matrix | All modules with health status |
| Kill Switch State | Armed / Disarmed visual indicator |
| VPN Status | Connection details |
| Integrity Report | File-by-file verification results |

---

## Tab 4: AUTOMATION — Orchestrator, Autonomous Engine, Scheduling

### What This Tab Does
Controls the automated operation systems — from single test operations to 24/7 autonomous running.

### Features

**Automation Orchestrator**
- `AutomationOrchestrator` from `titan_automation_orchestrator.py`
- "Run Test Operation" button — executes with sample data
- Operation phase display showing all 12 phases:
  1. INIT → 2. CARD_VALIDATION → 3. PROFILE_GENERATION → 4. NETWORK_SETUP
  5. PREFLIGHT → 6. BROWSER_LAUNCH → 7. NAVIGATION → 8. CHECKOUT
  9. THREE_DS → 10. KYC → 11. COMPLETION → 12. CLEANUP
- Phase status: Pending / Running / Success / Failed
- Phase duration and metrics per phase

**Master Automation**
- `TitanMasterAutomation` integration
- Single operation runner with custom config
- Batch operation runner with delay settings
- Test operation with sample persona and card data

**Autonomous Engine**
- `TitanAutonomousEngine` controls
- "Start Autonomous" — begins 24/7 self-improving loop
- "Stop Autonomous" — graceful shutdown
- Status display: running, operations count, success rate, last operation result
- Self-improvement metrics (what parameters were auto-tuned)

**Trajectory Model**
- `TrajectoryModelGenerator` status
- Training data collection status
- Model version and accuracy metrics
- "Train Model" button for manual training run

**Operation Log**
- `OperationLog` table showing recent operations
- Columns: ID, timestamp, target, status, duration, BIN, amount
- Click to expand: full phase-by-phase breakdown

**Integration Bridge Health**
- `get_bridge_health_monitor()` — real-time module health
- `get_module_discovery()` — discovered module list
- Module connection map showing which modules are wired

**Cockpit Daemon**
- `CockpitDaemon` system monitoring
- CPU/RAM/disk real-time gauges
- Process count and top consumers
- Network I/O statistics

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Operation Type | Test / Single / Batch | "Test Operation" |
| Autonomous | Start/Stop loop | "Start Autonomous" |
| Batch Count | Number of operations | 10 |
| Batch Delay | Seconds between operations | 30 |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Phase Dashboard | 12-phase progress with status |
| Operation Result | Success/failure with full details |
| Autonomous Stats | Operations count, success rate |
| Bridge Health | All module connection statuses |

---

## Tab 5: CONFIG — Environment, API Keys, Models

### What This Tab Does
Manages the `titan.env` configuration file, API keys, and AI model settings.

### Features

**Environment Configuration**
- `TitanEnvManager` / `ConfigValidator` integration
- Displays all `titan.env` settings grouped by section:
  - Cloud Brain (vLLM) — optional
  - Proxy Configuration — REQUIRED
  - Lucid VPN — optional
  - Payment Processor Credentials — optional
  - eBPF Network Shield — AUTO
  - Hardware Shield — AUTO
  - Transaction Monitor — AUTO
  - Auto-Discovery Scheduler — AUTO
  - General Settings
- Edit-in-place for each setting
- "Validate" button checks all settings
- "Save" writes back to `titan.env`

**Required vs Optional Indicators**
- Each setting marked: [AUTO] / [REQUIRED] / [OPTIONAL]
- Missing REQUIRED settings highlighted in red
- AUTO settings shown as read-only

**API Key Management**
- Proxy provider credentials
- Payment processor API keys (Stripe, PayPal, Braintree)
- Ollama server URL
- Keys masked with `***` in display, revealed on click

**Operation Log Viewer**
- `OperationLog` detailed viewer
- Filter by date range, status, target
- Export to CSV for external analysis
- Clear old logs option

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Config Setting | Any titan.env value | `PROXY_PROVIDER=brightdata` |
| API Key | Service credentials | Stripe API key |
| Log Filter | Date/status filter | "Last 7 days, failures only" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Config Status | All settings with validation state |
| Missing Alerts | Required settings not configured |
| Log Data | Filtered operation history |

---

## Module Wiring Summary

| Tab | Modules Used |
|-----|-------------|
| SERVICES | titan_services (TitanServiceManager, MemoryPressureManager) |
| TOOLS | bug_patch_bridge, titan_auto_patcher, ollama_bridge, ai_intelligence_engine |
| SYSTEM | kill_switch, lucid_vpn, forensic_monitor, immutable_os, titan_master_verify |
| AUTOMATION | titan_automation_orchestrator, titan_autonomous_engine, titan_master_automation, titan_operation_logger, generate_trajectory_model, cockpit_daemon, integration_bridge |
| CONFIG | titan_env (ConfigValidator, TitanEnvManager) |

**Total: 18 modules wired into Admin Panel**

---

*Next: [09 — Operator Workflow](09_OPERATOR_WORKFLOW.md)*
