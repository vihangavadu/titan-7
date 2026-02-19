# TITAN Hardware Shield - Kernel Module

> **Note:** This directory is a legacy placeholder. The production kernel module
> source lives at:
>
> **`/opt/titan/core/hardware_shield_v6.c`**
>
> with its Makefile at `/opt/titan/core/Makefile`.

## V6.2 Implementation (ACTIVE)

The production hardware shield (`hardware_shield_v6.c`) implements:

1. **Dynamic Netlink Injection** — Runtime profile switching via `NETLINK_TITAN` (protocol 31)
2. **procfs Handler Replacement** — Custom `proc_ops` for `/proc/cpuinfo` and `/proc/meminfo`
3. **DKOM Module Hiding** — `list_del(&THIS_MODULE->list)` + `kobject_del` hides from `lsmod`/`/sys/module`
4. **DMI/SMBIOS Spoofing** — Board vendor, serial, BIOS, UUID via sysfs attribute override
5. **Kernel 6.1+ Compatible** — Targets Debian 12 Bookworm

### Netlink Message Types

| ID | Constant | Description |
|----|----------|-------------|
| 1 | `TITAN_MSG_SET_PROFILE` | Load hardware profile (CPU, RAM, GPU, serial) |
| 2 | `TITAN_MSG_GET_PROFILE` | Query current active profile |
| 3 | `TITAN_MSG_HIDE_MODULE` | Hide module from lsmod/procfs |
| 4 | `TITAN_MSG_SHOW_MODULE` | Restore module visibility |
| 5 | `TITAN_MSG_GET_STATUS` | Get shield status string |
| 6 | `TITAN_MSG_SET_DMI` | Override DMI/SMBIOS fields |
| 7 | `TITAN_MSG_SET_CACHE` | Set CPU cache topology |
| 8 | `TITAN_MSG_SET_VERSION` | Set kernel version string |

### Build

```bash
cd /opt/titan/core
make            # Builds titan_hw.ko
sudo insmod titan_hw.ko
```

### Legacy Profile Format

This directory's profile format (`cpuinfo`, `dmi_*`, `hardware.conf`) is still
read by the legacy `generate-hw-profile.py` script. V6.2 profiles are sent via
Netlink instead.

## Status

- ✅ Kernel module source implemented (`hardware_shield_v6.c`)
- ✅ Netlink dynamic profile switching
- ✅ DKOM module hiding
- ✅ procfs hooks (cpuinfo, meminfo)
- ✅ DMI/SMBIOS override
- ✅ Makefile + build hooks integration
- ✅ Boot-time panic flush service (`kill_switch.py`)
