# 06 — App: Network Center

## Overview

**File:** `src/apps/titan_network.py`
**Color Theme:** Green (#22c55e)
**Tabs:** 4
**Modules Wired:** 18 (4 previously orphaned, now connected)
**Purpose:** VPN management, kernel-level network masquerade, forensic monitoring, and proxy configuration.

The Network Center manages everything between the browser and the internet. It ensures that every network packet leaving the system looks like it came from a Windows desktop on a residential connection.

---

## Tab 1: MULLVAD VPN — Connect, DAITA, IP Reputation

### What This Tab Does
Manages Mullvad VPN connections with advanced obfuscation and IP reputation monitoring.

### Features

**VPN Connection Controls**
- Country dropdown (40+ countries with Mullvad servers)
- City selector for sub-country targeting
- Obfuscation mode: Auto / DAITA / QUIC / None
  - **DAITA** — Defence Against AI-guided Traffic Analysis: pads packets to prevent ML-based traffic classification
  - **QUIC** — tunnels VPN through QUIC protocol, appears as regular HTTPS
- "Connect" button triggers `VPNConnectWorker` background thread
- "Disconnect" button for clean VPN teardown

**Connection Status**
- Real-time status: Connected / Connecting / Disconnected
- Exit IP address display
- Connection duration timer
- Server load indicator

**IP Reputation Check**
- `check_ip_reputation(ip)` runs after connection
- Queries multiple reputation services
- Displays: clean/suspicious/blacklisted rating
- Warns if exit IP has poor reputation (high fraud score)

**Lucid VPN Fallback**
- `LucidVPN` integration for self-hosted VLESS+Reality VPN
- Toggle between Mullvad and Lucid
- Lucid provides dedicated residential IP (not shared)

**Network Shield Auto-Attach**
- After VPN connects, "Attach Shield" button available
- `ShieldAttachWorker` detects WireGuard interface automatically
- Attaches eBPF TCP masquerade to VPN tunnel interface
- Status shows: interface detected, persona applied, mode active

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Country | VPN exit country | "United States" |
| City | VPN exit city (optional) | "Miami" |
| Obfuscation | Obfuscation mode | "DAITA" |
| Persona | TCP personality to mimic | "windows" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Connection Status | Connected with exit IP |
| IP Reputation | Clean/suspicious/blacklisted |
| Shield Status | eBPF attached to WireGuard interface |
| Latency | Connection round-trip time |

---

## Tab 2: NETWORK SHIELD — eBPF TCP Mimesis

### What This Tab Does
Configures and monitors the kernel-level eBPF network shield that rewrites TCP/IP headers to match a Windows machine.

### Features

**eBPF Shield Control**
- `NetworkShield` / `NetworkShieldLegacy` management
- Interface selector (eth0, wg0, etc.)
- Persona selector: Windows 11 / Windows 10 / macOS Sonoma
- Mode selector: TC (traffic control) / XDP (express data path)
  - **TC mode** — works everywhere, slightly higher latency
  - **XDP mode** — fastest, requires driver support

**Shield Status Dashboard**
- Packets processed counter (real-time)
- Headers rewritten counter
- Current TTL value (should show 128 for Windows)
- TCP window size in use
- TCP options order

**QUIC Proxy**
- `QUICProxy` start/stop controls
- Port configuration
- Connection count display
- QUIC fingerprint status

**CPUID/RDTSC Shield**
- `CPUIDRDTSCShield` status
- Hypervisor bit status (should show "masked")
- RDTSC calibration status
- `performance.now()` timing test result

**Network Jitter**
- `NetworkJitterEngine` configuration
- Connection type selector (DSL / Cable / Fiber / Mobile)
- Current jitter pattern display
- Latency statistics (min/avg/max/jitter)

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Interface | Network interface to protect | "wg0" (WireGuard) |
| Persona | OS to mimic at TCP level | "Windows 11" |
| Mode | eBPF attachment mode | "TC" |
| Jitter Type | Residential connection type | "Cable" |
| QUIC Port | Port for QUIC proxy | 8443 |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Shield Active | Green indicator + packet counters |
| TCP Profile | Current TTL, window size, options order |
| QUIC Status | Proxy running with connection count |
| CPUID Status | Hypervisor bit masked confirmation |
| Jitter Stats | Current latency pattern statistics |

---

## Tab 3: FORENSIC — Detection Monitor & Emergency Wipe

### What This Tab Does
Real-time monitoring for forensic artifacts and emergency data destruction controls.

### Features

**Forensic Monitor**
- `ForensicMonitor` runs every 5 seconds (auto-refresh timer)
- Scans for: Titan-specific file patterns, suspicious processes, network connections
- Real-time alerts if detectable traces found
- History log of all forensic events

**Forensic Cleaner**
- `ForensicCleaner` / `EmergencyWiper` integration
- "Clean" button removes Titan artifacts from filesystem
- Selective cleaning: profiles only, logs only, everything
- Secure deletion (overwrite before unlink)

**Kill Switch**
- `KillSwitch` emergency wipe control
- "ARM" button puts kill switch in ready state
- "PANIC" button triggers immediate data destruction
- Confirmation dialog prevents accidental activation
- Destroys: profiles, logs, state, free space overwrite, tmpfs clear

**OS Integrity**
- `ImmutableOS` verification
- Displays checksums of core system files
- Alerts if any file has been modified
- "Verify" button runs full integrity check
- Auto-restore option for modified files

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Clean Scope | What to clean | "All artifacts" |
| Kill Switch | Arm/disarm emergency wipe | ARM → PANIC |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Forensic Status | Green (clean) / Red (traces detected) |
| Alert Log | History of detected artifacts |
| Integrity Report | System file verification results |
| Kill Switch State | Armed / Disarmed / Triggered |

---

## Tab 4: PROXY/DNS — Proxy Management & Self-Hosted Tools

### What This Tab Does
Manages residential proxy pools, geographic spoofing, self-hosted validation tools, and referrer warmup.

### Features

**Proxy Pool Management**
- `ResidentialProxyManager` integration
- Provider configuration (BrightData, Oxylabs, SmartProxy, IPRoyal)
- Pool health dashboard: total proxies, alive, dead, response time
- Geographic filtering: country/state/city
- Session proxy assignment with rotation controls
- Exit IP monitoring (checks every 30 seconds)

**GeoIP & IP Quality**
- `GeoIPValidator` — validates proxy GeoIP matches billing address
- `IPQualityChecker` — checks IP against fraud databases
- `FingerprintTester` — browser fingerprint consistency test
- Self-hosted tools from `titan_self_hosted_stack.py`

**Location Spoofing**
- `LocationSpoofer` / `LocationSpooferLinux` configuration
- GPS coordinates input with map preview
- Jitter radius setting (±50m default)
- "Auto from billing" button derives coordinates from address

**Referrer Warmup**
- `ReferrerWarmupEngine` configuration
- Warmup chain type: Google search / Social media / Email link / Direct
- Chain length setting (number of intermediate sites)
- "Preview chain" shows the planned referrer path
- "Execute warmup" runs the chain before target navigation

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Proxy Provider | Which proxy service | "BrightData" |
| Proxy Country | Geographic filter | "US" |
| Proxy City | City-level filter | "New York" |
| GPS Latitude | Spoofed latitude | 40.7128 |
| GPS Longitude | Spoofed longitude | -74.0060 |
| Warmup Type | Referrer chain type | "Google search" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Proxy Status | Connected proxy IP + health metrics |
| GeoIP Match | Whether proxy location matches billing |
| IP Quality | Fraud score from quality checker |
| Warmup Complete | Referrer chain executed successfully |

---

## Module Wiring Summary

| Tab | Modules Used |
|-----|-------------|
| MULLVAD VPN | mullvad_vpn, lucid_vpn, network_shield_loader |
| NETWORK SHIELD | network_shield, network_jitter, quic_proxy, cpuid_rdtsc_shield |
| FORENSIC | forensic_monitor, forensic_cleaner, kill_switch, immutable_os |
| PROXY/DNS | proxy_manager, titan_self_hosted_stack, location_spoofer, location_spoofer_linux, referrer_warmup |

**Total: 18 modules wired into Network Center**

---

*Next: [07 — App: KYC Studio](07_APP_KYC_STUDIO.md)*
