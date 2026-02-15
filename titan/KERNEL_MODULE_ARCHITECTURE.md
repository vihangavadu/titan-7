# TITAN Hardware Shield - Kernel Module Architecture

## Overview
Migration from Ring-3 (LD_PRELOAD) to Ring-0 (Kernel Module) for hardware fingerprint masking.

## Critical Security Requirements

### Problem with Current LD_PRELOAD Approach
1. **Environment Detection**: `LD_PRELOAD` variable visible in process environment
2. **Memory Maps**: Library appears in `/proc/self/maps`
3. **Static Binary Bypass**: Statically-linked executables (Go/Rust) completely bypass hooks
4. **Trivial Detection**: Any sophisticated anti-cheat can detect this method

### Kernel Module Advantages
1. **Zero Userspace Footprint**: No environment variables, no memory map entries
2. **Universal Coverage**: Works with static binaries, dynamic binaries, all languages
3. **Transparent Operation**: Applications cannot detect the interception
4. **True Ring-0**: Operates at kernel privilege level

## Implementation Strategy

### Target Files for Interception
```
/proc/cpuinfo              - CPU model, features, core count
/sys/class/dmi/id/product_name - System manufacturer
/sys/class/dmi/id/product_uuid - Hardware UUID
/sys/class/dmi/id/board_vendor - Motherboard vendor
/sys/class/net/*/address   - MAC addresses (future)
```

### Interception Method

The kernel module will use one of two approaches based on kernel version:

#### Option A: Kprobes (Kernel 5.x - 6.x)
- Hook `vfs_read` or `__vfs_read`
- Inspect file descriptor path
- Return modified buffer for targeted paths
- Limitations: May be restricted on some kernels

#### Option B: Filesystem Overlay (Preferred for Kernel 6.x+)
- Create custom proc_ops/file_operations structures
- Replace original handlers for specific files
- More stable across kernel versions
- Better performance

### Configuration Files

Hardware profiles stored in: `/opt/lucid-empire/profiles/<profile_name>/`

Required files:
- `cpuinfo` - Full /proc/cpuinfo replacement content
- `dmi_product_name` - System product name
- `dmi_product_uuid` - Hardware UUID
- `dmi_board_vendor` - Board manufacturer
- `hardware.conf` - Additional metadata

### Build Integration

1. **Package Dependencies**:
   - `linux-headers-$(uname -r)` - Already in package list
   - `build-essential` - Already available

2. **Build Hook** (`060-kernel-module.hook.chroot`):
   - Compile module during ISO build
   - Install to `/opt/lucid-empire/kernel-modules/`
   - Enable systemd service

3. **Systemd Service** (`lucid-titan.service`):
   - Load module early in boot sequence
   - Before display manager starts
   - Ensures protection active before any applications run

### Module Loading Sequence

```
Boot → Kernel → Systemd → lucid-titan.service → insmod titan_hw.ko → Display Manager → Applications
```

### Testing Requirements

1. **LD_PRELOAD Verification**:
   ```bash
   # Should be empty
   cat /proc/$$/environ | grep LD_PRELOAD
   ```

2. **Static Binary Test**:
   ```bash
   # Create static Go binary that reads /proc/cpuinfo
   # Should see spoofed CPU, not real hardware
   ```

3. **Memory Map Test**:
   ```bash
   # Should NOT contain hardware_shield.so
   cat /proc/$$/maps | grep hardware
   ```

4. **Stealth Test** (Optional):
   ```bash
   # Module can optionally hide itself
   lsmod | grep titan_hw  # May return nothing if stealth enabled
   ```

## Migration Checklist

- [ ] Create kernel module source (`titan/hardware_shield/titan_hw.c`)
- [ ] Create module Makefile
- [ ] Add build hook for ISO compilation
- [ ] Create systemd service file
- [ ] Generate default hardware profiles
- [ ] Update launch-titan.sh to REMOVE LD_PRELOAD references
- [ ] Create test suite for static binaries
- [ ] Document module parameters
- [ ] Security audit with CodeQL

## Implementation Notes

### Kernel Version Compatibility
Target: Debian 12 Bookworm (Kernel 6.1.x)
- Use modern kprobe API
- Handle BTF (BPF Type Format) if available
- Graceful fallback if certain features unavailable

### Security Considerations
- Module signed with kernel signing key (future)
- Verify profile data integrity before loading
- Rate limit hook operations to prevent DoS
- Audit log all interceptions (debug mode only)

### Performance Impact
- Hooks only trigger on specific file paths
- Zero overhead for non-targeted operations
- Cached profile data in kernel memory
- Mutex-protected shared data structures

## Current Status

**Phase**: COMPLETE ✓

### Implemented Components
- ✓ Kernel module (`titan_hw.c` - 301 lines)
- ✓ Procfs handler replacement for /proc/cpuinfo
- ✓ Sysfs attribute override for DMI data
- ✓ Profile-based configuration loading
- ✓ DKMS integration
- ✓ Systemd service
- ✓ Build script integration
- ✓ Documentation complete

### Key Features Delivered
- Ring 0 execution (kernel privilege)
- Zero userspace footprint
- Works with static binaries (Go/Rust)
- Invisible to /proc/self/maps inspection
- Profile hot-swapping support
- Optional DKOM module hiding

## Files

| File | Location | Lines |
|------|----------|-------|
| Kernel Module | `titan/hardware_shield/titan_hw.c` | 301 |
| Makefile | `titan/hardware_shield/Makefile` | 8 |
| Service | `/etc/systemd/system/lucid-titan.service` | 24 |
| Build Script | `scripts/build-titan-final.sh` | 84 |

## Next Steps (Production Hardening)

1. Secure Boot signing for kernel module
2. TPM-based profile encryption
3. Audit logging for compliance
4. Performance optimization for high-frequency reads

**Status:** OPERATIONAL | **Authority:** Dva.12
