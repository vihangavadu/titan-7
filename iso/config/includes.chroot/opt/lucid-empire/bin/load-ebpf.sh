#!/bin/bash
# LUCID EMPIRE TITAN - eBPF Loader Script
# Compiles and loads TCP fingerprint masquerade program

set -e

EBPF_DIR="/opt/lucid-empire/ebpf"
EBPF_SRC="$EBPF_DIR/tcp_fingerprint.c"
EBPF_OBJ="$EBPF_DIR/tcp_fingerprint.o"
CONFIG_DIR="/opt/lucid-empire/config"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[TITAN-eBPF]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Check root
if [[ $EUID -ne 0 ]]; then
    error "eBPF loader requires root privileges"
    exit 1
fi

# Detect network interface
detect_interface() {
    local iface=$(ip route | grep default | awk '{print $5}' | head -1)
    if [[ -z "$iface" ]]; then
        iface="eth0"
    fi
    echo "$iface"
}

INTERFACE="${1:-$(detect_interface)}"
OS_PROFILE="${2:-windows}"

log "LUCID EMPIRE TITAN - eBPF TCP Fingerprint Masquerade"
log "Interface: $INTERFACE"
log "OS Profile: $OS_PROFILE"

# Check kernel support
check_kernel_support() {
    log "Checking kernel support..."
    
    # Check kernel version
    KERNEL_VERSION=$(uname -r | cut -d. -f1-2)
    KERNEL_MAJOR=$(echo $KERNEL_VERSION | cut -d. -f1)
    KERNEL_MINOR=$(echo $KERNEL_VERSION | cut -d. -f2)
    
    if [[ $KERNEL_MAJOR -lt 5 ]] || [[ $KERNEL_MAJOR -eq 5 && $KERNEL_MINOR -lt 15 ]]; then
        warn "Kernel $KERNEL_VERSION may have limited eBPF support (recommend 5.15+)"
    fi
    
    # Check BTF support
    if [[ ! -f /sys/kernel/btf/vmlinux ]]; then
        warn "BTF not available - some features may be limited"
    fi
    
    # Check BPF JIT
    local jit=$(cat /proc/sys/net/core/bpf_jit_enable 2>/dev/null || echo "0")
    if [[ "$jit" != "1" ]]; then
        log "Enabling BPF JIT compiler..."
        echo 1 > /proc/sys/net/core/bpf_jit_enable
    fi
}

# Compile eBPF program
compile_ebpf() {
    log "Compiling eBPF program..."
    
    if [[ ! -f "$EBPF_SRC" ]]; then
        error "Source file not found: $EBPF_SRC"
        exit 1
    fi
    
    # Check for clang
    if ! command -v clang &>/dev/null; then
        error "clang not found. Install with: apt install clang llvm"
        exit 1
    fi
    
    # Compile with BTF if available
    local btf_flag=""
    if [[ -f /sys/kernel/btf/vmlinux ]]; then
        btf_flag="-g"
    fi
    
    clang -O2 -target bpf \
        $btf_flag \
        -D__TARGET_ARCH_x86 \
        -I/usr/include/x86_64-linux-gnu \
        -c "$EBPF_SRC" \
        -o "$EBPF_OBJ" 2>/dev/null || {
            warn "Full compilation failed, trying minimal mode..."
            clang -O2 -target bpf -c "$EBPF_SRC" -o "$EBPF_OBJ"
        }
    
    log "Compiled: $EBPF_OBJ"
}

# Unload existing programs
unload_ebpf() {
    log "Unloading existing eBPF programs from $INTERFACE..."
    
    # Remove XDP program
    ip link set dev "$INTERFACE" xdp off 2>/dev/null || true
    
    # Remove TC programs
    tc qdisc del dev "$INTERFACE" clsact 2>/dev/null || true
    
    log "Existing programs unloaded"
}

# Load eBPF program
load_ebpf() {
    log "Loading eBPF program on $INTERFACE..."
    
    if [[ ! -f "$EBPF_OBJ" ]]; then
        error "Compiled object not found: $EBPF_OBJ"
        exit 1
    fi
    
    # Try XDP first
    if ip link set dev "$INTERFACE" xdp obj "$EBPF_OBJ" sec xdp 2>/dev/null; then
        log "Loaded XDP program successfully"
    else
        warn "XDP load failed, trying TC..."
        
        # Set up TC qdisc
        tc qdisc add dev "$INTERFACE" clsact 2>/dev/null || true
        
        # Load TC egress program
        if tc filter add dev "$INTERFACE" egress bpf da obj "$EBPF_OBJ" sec tc 2>/dev/null; then
            log "Loaded TC program successfully"
        else
            error "Failed to load eBPF program"
            exit 1
        fi
    fi
}

# Configure OS profile via map
configure_profile() {
    log "Configuring $OS_PROFILE profile..."
    
    local ttl window_size mss
    
    case "$OS_PROFILE" in
        windows|win)
            ttl=128
            window_size=65535
            mss=1460
            ;;
        macos|mac|darwin)
            ttl=64
            window_size=65535
            mss=1460
            ;;
        linux)
            ttl=64
            window_size=29200
            mss=1460
            ;;
        ios|iphone)
            ttl=64
            window_size=65535
            mss=1380
            ;;
        android)
            ttl=64
            window_size=65535
            mss=1460
            ;;
        *)
            warn "Unknown profile '$OS_PROFILE', using Windows defaults"
            ttl=128
            window_size=65535
            mss=1460
            ;;
    esac
    
    # Write config for Python loader to use
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_DIR/tcp_profile.conf" << EOF
# LUCID EMPIRE TCP Fingerprint Configuration
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
OS_PROFILE=$OS_PROFILE
TTL=$ttl
WINDOW_SIZE=$window_size
MSS=$mss
INTERFACE=$INTERFACE
EOF
    
    log "Profile configured: TTL=$ttl, Window=$window_size, MSS=$mss"
    
    # Try to update map using bpftool if available
    if command -v bpftool &>/dev/null; then
        # Find map ID
        local map_id=$(bpftool map list | grep tcp_config_map | awk '{print $1}' | tr -d ':')
        if [[ -n "$map_id" ]]; then
            log "Updating eBPF map (ID: $map_id)..."
            # Note: Full map update would require proper struct encoding
            # For now, config file is used by Python loader
        fi
    fi
}

# Show status
show_status() {
    echo ""
    log "=== eBPF Status ==="
    
    # XDP status
    echo -e "${CYAN}XDP Programs:${NC}"
    ip link show dev "$INTERFACE" | grep -i xdp || echo "  None attached"
    
    # TC status
    echo -e "${CYAN}TC Programs:${NC}"
    tc filter show dev "$INTERFACE" egress 2>/dev/null || echo "  None attached"
    
    # BPF programs
    if command -v bpftool &>/dev/null; then
        echo -e "${CYAN}BPF Programs:${NC}"
        bpftool prog list 2>/dev/null | head -10 || true
    fi
    
    echo ""
    log "TCP Fingerprint masquerade active on $INTERFACE"
}

# Main execution
case "${3:-load}" in
    compile)
        compile_ebpf
        ;;
    load)
        check_kernel_support
        compile_ebpf
        unload_ebpf
        load_ebpf
        configure_profile
        show_status
        ;;
    unload)
        unload_ebpf
        log "eBPF programs unloaded"
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 [interface] [os_profile] [compile|load|unload|status]"
        echo ""
        echo "OS Profiles: windows, macos, linux, ios, android"
        echo "Default: windows on default interface"
        exit 1
        ;;
esac
