# Network & Hardware Shield — Kernel-Level Identity Spoofing

## Core Modules: `hardware_shield_v6.c`, `network_shield_v6.c`, `network_jitter.py`, `proxy_manager.py`, `lucid_vpn.py`, `quic_proxy.py`, `tls_parrot.py`

These modules operate at the kernel and network level — the deepest layers of evasion that no browser extension or userspace tool can replicate.

---

## 1. Hardware Shield (`hardware_shield_v6.c` — Kernel Module)

### The Problem

Every VPS/cloud server has identifiable hardware:
- `/proc/cpuinfo` shows "AMD EPYC" or "Intel Xeon" (server CPUs, never in consumer desktops)
- `/sys/class/dmi/id/sys_vendor` shows "QEMU", "KVM", "VMware", "Xen"
- `/proc/meminfo` shows server-class RAM configurations
- USB bus is empty (no keyboard, mouse, webcam)

Fraud SDKs (ThreatMetrix, Iovation) read these through JavaScript → WebAssembly → system calls. Even Camoufox can't hide what the kernel reports.

### The Solution: Kernel Module Hooks

`hardware_shield_v6.c` is a loadable kernel module (`.ko`) that:

1. **Hooks `/proc/cpuinfo`**: Replaces AMD EPYC with consumer Intel i7/i9
2. **Hooks `/proc/meminfo`**: Reports consumer RAM configuration
3. **Hooks `/sys/class/dmi/id/*`**: Replaces QEMU with Dell/HP/Lenovo
4. **Receives profiles via Netlink**: Userspace Python sends hardware profiles through Netlink socket (protocol 31)

```c
// Kernel module initialization
static int __init titan_hw_init(void) {
    // Register Netlink handler for receiving hardware profiles
    cfg.input = titan_nl_recv_msg;
    titan_nl_sock = netlink_kernel_create(&init_net, NETLINK_TITAN, &cfg);
    
    // Hook procfs file operations
    hook_proc_cpuinfo();
    hook_proc_meminfo();
    hook_sysfs_dmi();
    
    // Set default profile (consumer desktop)
    set_default_profile();
    
    printk(KERN_INFO "TITAN-HW-V7: Hardware Shield active\n");
    return 0;
}
```

### Hardware Profiles

The module supports multiple hardware profiles sent from userspace:

| Profile | CPU | RAM | Motherboard | Use Case |
|---------|-----|-----|-------------|----------|
| **Dell XPS 8960** | i7-13700K | 32GB DDR5 | Dell Inc. | High-end desktop |
| **HP Pavilion** | i5-12400 | 16GB DDR4 | HP Inc. | Mid-range desktop |
| **Lenovo ThinkPad** | i7-1365U | 16GB DDR5 | Lenovo | Business laptop |
| **Custom Gaming** | i9-12900K | 64GB DDR5 | ASUS ROG | Gaming desktop |

### Netlink Communication

Userspace Python sends profiles to the kernel module:

```python
import struct, socket, os

NETLINK_TITAN = 31
TITAN_MSG_SET_PROFILE = 1

# Build profile data
cpu_model = b'13th Gen Intel(R) Core(TM) i7-13700K'.ljust(128, b'\x00')
cpu_vendor = b'GenuineIntel'.ljust(64, b'\x00')
mb_vendor = b'Dell Inc.'.ljust(64, b'\x00')
mb_model = b'XPS 8960'.ljust(64, b'\x00')
# ... pack all fields

# Send via Netlink
sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_TITAN)
sock.bind((os.getpid(), 0))
nlmsg = struct.pack('IHHII', msg_len, TITAN_MSG_SET_PROFILE, 0, 0, os.getpid())
nlmsg += profile_data
sock.send(nlmsg)
```

### Auto-Start on Boot

The `titan-hw-shield.service` systemd unit ensures the module loads on every boot:

```ini
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'cd /opt/titan/core && make -s; insmod hardware_shield_v6.ko'
RemainAfterExit=yes
```

---

## 2. Network Shield (`network_shield_v6.c` — eBPF/XDP)

### The Problem

Network-level fingerprinting reveals the OS through:
- **TTL (Time To Live)**: Linux default = 64, Windows default = 128
- **TCP window size**: Linux and Windows use different defaults
- **TCP options order**: The order of SACK, timestamps, window scale differs
- **IP ID generation**: Linux uses incremental, Windows uses random
- **DNS resolver**: Datacenter DNS servers reveal hosting provider

### The Solution: eBPF Packet Manipulation

`network_shield_v6.c` is an eBPF/XDP program that modifies packets at the kernel level before they leave the network interface:

```c
// XDP program attached to network interface
SEC("xdp")
int titan_xdp_shield(struct xdp_md *ctx) {
    // Parse packet headers
    struct iphdr *iph = parse_ip_header(ctx);
    struct tcphdr *tcph = parse_tcp_header(ctx);
    
    // Spoof TTL to Windows value
    iph->ttl = 128;
    
    // Modify TCP window size to match Windows
    tcph->window = htons(WINDOWS_TCP_WINDOW);
    
    // Reorder TCP options to match Windows stack
    reorder_tcp_options(tcph, WINDOWS_TCP_OPTION_ORDER);
    
    // Recalculate checksums
    update_checksums(iph, tcph);
    
    return XDP_PASS;
}
```

### Current Status on VPS

The eBPF program requires `asm/bitsperlong.h` header which is missing on the VPS kernel. As a workaround, TTL and TCP parameters are set via sysctl:

```bash
# /etc/sysctl.d/99-titan.conf
net.ipv4.ip_default_ttl=128          # Windows TTL
net.ipv4.tcp_timestamps=1            # Enable timestamps (Windows does)
net.ipv4.tcp_window_scaling=1        # Enable window scaling
net.ipv4.tcp_sack=1                  # Enable SACK
net.ipv4.tcp_fin_timeout=30          # Windows default
net.ipv4.tcp_tw_reuse=1              # Reuse TIME_WAIT sockets
kernel.randomize_va_space=2          # Full ASLR
kernel.core_pattern=|/bin/false      # Disable core dumps (forensic protection)
```

---

## 3. Network Micro-Jitter (`network_jitter.py`)

### The Problem

Datacenter networks have unnaturally low and consistent latency. A residential connection has:
- Variable latency (±5-20ms jitter)
- Occasional packet loss (0.1-0.5%)
- Bandwidth fluctuation

A datacenter connection has:
- Near-zero jitter (<1ms)
- Zero packet loss
- Constant bandwidth

Sophisticated antifraud systems (Arkose Labs) measure network characteristics to detect datacenter connections.

### The Solution: tc-netem Jitter Injection

```python
class NetworkJitter:
    """
    Injects realistic residential network characteristics using tc-netem.
    
    Applied to the outbound network interface to simulate:
    - Latency jitter: ±5-15ms (normal distribution)
    - Packet loss: 0.1-0.3% (random)
    - Bandwidth variation: ±10% of base
    - Occasional latency spikes: 50-200ms (every 30-60 seconds)
    """
    
    def apply_residential_profile(self, interface="eth0"):
        commands = [
            f"tc qdisc add dev {interface} root netem "
            f"delay 10ms 5ms distribution normal "
            f"loss 0.1% 25% "
            f"duplicate 0.01% "
            f"reorder 0.1% 50%"
        ]
```

---

## 4. Proxy Management (`proxy_manager.py`)

### Why Residential Proxies Are Essential

The single most important factor in avoiding detection is IP reputation. Datacenter IPs are in public databases and are instantly flagged by every antifraud system.

**Residential proxies** route traffic through real home internet connections, giving you an IP that belongs to a real ISP (Comcast, AT&T, Verizon) in a real city.

### Proxy Manager Features

```python
class ResidentialProxyManager:
    """
    Manages residential proxy connections with:
    
    1. Geo-targeting: Select proxy in specific city/state/country
    2. Sticky sessions: Same IP for entire operation (critical for checkout)
    3. Rotation: Automatic IP rotation between operations
    4. Health checking: Verify proxy is alive and not blacklisted
    5. Failover: Automatic switch to backup proxy on failure
    6. Speed testing: Measure latency to ensure acceptable performance
    """
    
    def get_proxy(self, geo: GeoTarget) -> ProxyEndpoint:
        """
        Get a residential proxy matching the target geography.
        
        The proxy's city/state should match the billing address
        to avoid geographic anomaly detection.
        """
```

### Geo-Matching Strategy

```
Billing address: 123 Main St, Austin, TX 78701
→ Proxy target: Austin, TX (or at minimum, Texas)
→ Timezone: America/Chicago (CST)
→ Browser locale: en-US
→ GPS coordinates: 30.2672° N, 97.7431° W

All must be consistent. A Texas billing address with a New York IP
is a strong fraud signal.
```

---

## 5. DNS Protection

### The Problem

DNS queries reveal your real location and hosting provider:
- Default DNS on Hostinger VPS: `153.92.2.6` (Hostinger's DNS)
- This immediately identifies you as a Hostinger VPS user

### The Solution

```bash
# /etc/resolv.conf (immutable — cannot be changed by DHCP)
nameserver 127.0.0.1    # Local DNS-over-HTTPS resolver
nameserver 1.1.1.1      # Cloudflare (used by millions of real users)
nameserver 8.8.8.8      # Google (backup)
```

The file is made immutable with `chattr +i` so DHCP renewals cannot overwrite it.

Additionally, Camoufox is configured to use DNS-over-HTTPS (DoH) which encrypts DNS queries, preventing the proxy provider from seeing which domains you visit.

---

## 6. QUIC Proxy (`quic_proxy.py`)

### Why QUIC Matters

Modern websites (Google, YouTube, Facebook) use HTTP/3 over QUIC protocol. QUIC has its own fingerprinting vectors:
- QUIC transport parameters
- Connection ID format
- Initial packet size
- Congestion control algorithm

### TITAN's QUIC Proxy

```python
class TitanQUICProxy:
    """
    HTTP/3 QUIC proxy that:
    1. Tunnels QUIC traffic through residential proxy
    2. Normalizes QUIC transport parameters to match Chrome
    3. Handles connection migration (IP change during session)
    4. Supports 0-RTT resumption for faster connections
    """
```

---

## 7. USB Peripheral Synthesis (`usb_peripheral_synth.py`)

### The Problem

A real desktop computer has USB devices: keyboard, mouse, webcam, maybe a printer. A VPS has an empty USB bus. Some fraud SDKs check the USB device tree.

### The Solution

```python
USB_DEVICES = [
    {"vendor": "046d", "product": "c52b", "name": "Logitech Unifying Receiver"},
    {"vendor": "046d", "product": "c077", "name": "Logitech M105 Mouse"},
    {"vendor": "04f2", "product": "b604", "name": "Chicony Integrated Camera"},
    {"vendor": "8087", "product": "0029", "name": "Intel Bluetooth Adapter"},
]
```

Uses Linux's `configfs/gadgetfs` to create virtual USB devices that appear in the device tree, making the system look like it has real peripherals connected.
