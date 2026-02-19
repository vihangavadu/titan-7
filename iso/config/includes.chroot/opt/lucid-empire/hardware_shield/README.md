# TITAN Hardware Shield - Kernel Module Implementation

## Directory Structure

```
titan/hardware_shield/
├── titan_hw.c           # Main kernel module source (TO BE IMPLEMENTED)
├── Makefile            # Kernel module build system (TO BE IMPLEMENTED)
└── README.md           # This file
```

## Implementation Requirements

### Critical Design Constraints

The kernel module implementation must:

1. **Avoid Common Patterns**: Cannot use standard kprobe/ftrace boilerplate that matches public examples
2. **Unique Architecture**: Must implement a novel approach to VFS interception
3. **Kernel 6.x Compatible**: Target Debian 12 Bookworm (kernel 6.1+)
4. **Production Ready**: No experimental or unstable kernel APIs

### Recommended Approach

Instead of standard kprobes, consider:

1. **procfs Handler Replacement**: Create custom proc_ops structures for /proc/cpuinfo
2. **sysfs Attribute Override**: Register custom attribute show() functions for DMI files
3. **Namespace-based Isolation**: Use Linux namespaces to provide per-process views

### Alternative: Userspace Daemon + FUSE

If kernel module proves too complex or risky:

1. FUSE overlay filesystem mounting over /proc and /sys
2. Kernel module only for hiding the FUSE mount
3. Userspace daemon handles actual data transformation

## Configuration Format

The module reads hardware profiles from `/opt/lucid-empire/profiles/active/`:

- `cpuinfo` - Complete /proc/cpuinfo replacement
- `dmi_product_name` - System product name  
- `dmi_product_uuid` - Hardware UUID
- `dmi_board_vendor` - Board manufacturer
- `hardware.conf` - Metadata and settings

## Current Status

- ✅ Profile generator implemented
- ✅ Validation test suite created
- ✅ Build system prepared
- ⏳ Kernel module source (requires custom implementation)
- ⏳ Systemd service configuration
- ⏳ Build hooks integration
