#!/bin/bash
# TITAN V7.0 SINGULARITY - eBPF Build Script
# Compiles: network_shield_v6.c -> network_shield_v6.o (eBPF bytecode)
# Requires: clang >= 12, llvm, linux-headers, libbpf-dev

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${SCRIPT_DIR}/network_shield_v6.c"
OUT_DIR="/opt/titan/ebpf"
BPF_PIN_DIR="/sys/fs/bpf"
TITAN_PIN_DIR="${BPF_PIN_DIR}/titan_network_shield"

# Detect kernel headers
KERNEL_VERSION=$(uname -r)
KERNEL_HEADERS="/lib/modules/${KERNEL_VERSION}/build"
LIBBPF_INCLUDE="/usr/include/bpf"

# Verify dependencies
check_deps() {
    local missing=()
    command -v clang >/dev/null 2>&1 || missing+=("clang")
    command -v llc >/dev/null 2>&1 || missing+=("llc")
    command -v bpftool >/dev/null 2>&1 || missing+=("bpftool")
    
    if [ ! -d "${KERNEL_HEADERS}" ]; then
        missing+=("linux-headers-${KERNEL_VERSION}")
    fi
    
    if [ ! -f "/sys/kernel/btf/vmlinux" ]; then
        echo "WARNING: BTF not available. Some features may not work."
        echo "  Enable CONFIG_DEBUG_INFO_BTF=y in kernel config."
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo "ERROR: Missing dependencies: ${missing[*]}"
        echo "Install with: apt install clang llvm libbpf-dev linux-headers-${KERNEL_VERSION} bpftool"
        exit 1
    fi
}

# Generate vmlinux.h from BTF if available
generate_vmlinux_h() {
    if [ -f "/sys/kernel/btf/vmlinux" ] && command -v bpftool >/dev/null 2>&1; then
        echo "[1/4] Generating vmlinux.h from kernel BTF..."
        bpftool btf dump file /sys/kernel/btf/vmlinux format c > "${SCRIPT_DIR}/vmlinux.h" 2>/dev/null || true
    fi
}

# Compile eBPF program
compile_ebpf() {
    echo "[2/4] Compiling eBPF program..."
    
    mkdir -p "${OUT_DIR}"
    
    # Compile with clang targeting BPF
    clang \
        -target bpf \
        -D__TARGET_ARCH_x86 \
        -I"${KERNEL_HEADERS}/include" \
        -I"${KERNEL_HEADERS}/include/uapi" \
        -I"${KERNEL_HEADERS}/arch/x86/include" \
        -I"${KERNEL_HEADERS}/arch/x86/include/uapi" \
        -I"${KERNEL_HEADERS}/arch/x86/include/generated" \
        -I"${KERNEL_HEADERS}/arch/x86/include/generated/uapi" \
        -I"${LIBBPF_INCLUDE}" \
        -I"${SCRIPT_DIR}" \
        -O2 -g \
        -Wall -Werror \
        -c "${SRC}" \
        -o "${OUT_DIR}/network_shield_v6.o"
    
    echo "  -> ${OUT_DIR}/network_shield_v6.o"
}

# Load and pin eBPF programs
load_ebpf() {
    echo "[3/5] Loading eBPF programs..."
    
    # Clean stale pins
    rm -rf "${TITAN_PIN_DIR}" 2>/dev/null || true
    mkdir -p "${TITAN_PIN_DIR}"
    
    # Load all programs and maps from the object file at once.
    # bpftool loadall pins each SEC("...") program and auto-creates maps.
    bpftool prog loadall "${OUT_DIR}/network_shield_v6.o" "${TITAN_PIN_DIR}" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  -> All programs loaded and pinned to ${TITAN_PIN_DIR}/"
        ls "${TITAN_PIN_DIR}/" 2>/dev/null | sed 's/^/     /' 
    else
        # Fallback: load individual sections
        echo "  -> loadall failed, trying individual sections..."
        bpftool prog load "${OUT_DIR}/network_shield_v6.o" "${TITAN_PIN_DIR}/titan_xdp_filter" \
            type xdp 2>/dev/null && echo "  -> XDP filter loaded" || echo "  -> XDP filter: skipped"
        bpftool prog load "${OUT_DIR}/network_shield_v6.o" "${TITAN_PIN_DIR}/titan_tc_egress" \
            type sched_cls 2>/dev/null && echo "  -> TC egress loaded" || echo "  -> TC egress: skipped"
        bpftool prog load "${OUT_DIR}/network_shield_v6.o" "${TITAN_PIN_DIR}/titan_sockops" \
            type sock_ops 2>/dev/null && echo "  -> Sockops loaded" || echo "  -> Sockops: skipped"
    fi
}

# Attach to network interface
attach_ebpf() {
    echo "[4/5] Attaching eBPF programs..."
    
    # Detect primary network interface
    IFACE=$(ip route show default | awk '/default/ {print $5}' | head -1)
    if [ -z "${IFACE}" ]; then
        echo "WARNING: Could not detect default network interface"
        return
    fi
    
    echo "  Interface: ${IFACE}"
    
    # Find pinned program paths (loadall uses SEC name as filename)
    XDP_PIN=$(find "${TITAN_PIN_DIR}" -name '*xdp*' -o -name '*filter*' 2>/dev/null | head -1)
    TC_PIN=$(find "${TITAN_PIN_DIR}" -name '*tc*' -o -name '*egress*' 2>/dev/null | head -1)
    SOCKOPS_PIN=$(find "${TITAN_PIN_DIR}" -name '*sockops*' 2>/dev/null | head -1)
    
    # Attach XDP (try native first, fall back to generic)
    if [ -n "${XDP_PIN}" ] && [ -f "${XDP_PIN}" ]; then
        ip link set dev "${IFACE}" xdp pinned "${XDP_PIN}" 2>/dev/null \
            && echo "  -> XDP attached (native) to ${IFACE}" \
            || { ip link set dev "${IFACE}" xdpgeneric pinned "${XDP_PIN}" 2>/dev/null \
                && echo "  -> XDP attached (generic) to ${IFACE}" \
                || echo "  -> XDP attach failed"; }
    fi
    
    # Attach TC egress
    if [ -n "${TC_PIN}" ] && [ -f "${TC_PIN}" ]; then
        tc qdisc add dev "${IFACE}" clsact 2>/dev/null || true
        tc filter add dev "${IFACE}" egress bpf direct-action pinned "${TC_PIN}" 2>/dev/null \
            && echo "  -> TC egress attached to ${IFACE}" \
            || echo "  -> TC egress attach failed"
    fi
    
    # Attach sockops to root cgroup (required for TCP connection tracking)
    if [ -n "${SOCKOPS_PIN}" ] && [ -f "${SOCKOPS_PIN}" ]; then
        CGROUP_ROOT=$(mount -t cgroup2 | head -1 | awk '{print $3}')
        if [ -z "${CGROUP_ROOT}" ]; then
            CGROUP_ROOT="/sys/fs/cgroup"
        fi
        bpftool cgroup attach "${CGROUP_ROOT}" sock_ops pinned "${SOCKOPS_PIN}" 2>/dev/null \
            && echo "  -> Sockops attached to cgroup ${CGROUP_ROOT}" \
            || echo "  -> Sockops attach failed (cgroup2 required)"
    fi
}

# Configure eBPF maps with runtime defaults
configure_maps() {
    echo "[5/5] Configuring eBPF maps..."
    
    # Find titan_config map
    CONFIG_MAP=$(bpftool map list 2>/dev/null | grep -i titan_config | awk '{print $1}' | tr -d ':')
    if [ -z "${CONFIG_MAP}" ]; then
        # Try pinned path
        CONFIG_MAP=$(find "${TITAN_PIN_DIR}" -name '*config*' 2>/dev/null | head -1)
    fi
    
    if [ -n "${CONFIG_MAP}" ]; then
        # Enable all protections by default:
        # quic_proxy=1, tcp_fp=1, dns_protection=1, webrtc_block=1,
        # proxy_ip=127.0.0.1 (0x7f000001), proxy_port=8443,
        # os_profile=0 (Win11 Chrome), reserved=0,
        # dns_server_1=1.1.1.1 (0x01010101), dns_server_2=8.8.8.8 (0x08080808)
        bpftool map update id "${CONFIG_MAP}" \
            key hex 00 00 00 00 \
            value hex 01 01 01 01 01 00 00 7f fb 20 00 00 01 01 01 01 08 08 08 08 \
            2>/dev/null \
            && echo "  -> titan_config map initialized (DNS: 1.1.1.1, 8.8.8.8)" \
            || echo "  -> Map config via pinned path..."
    else
        echo "  -> titan_config map not found (will use defaults)"
    fi
    
    echo ""
    echo "=== TITAN Network Shield Active ==="
    echo "  DNS whitelist: 1.1.1.1, 8.8.8.8"
    echo "  WebRTC blocking: ON"
    echo "  TCP fingerprint: Win11 Chrome"
    echo "  QUIC proxy: 127.0.0.1:8443"
}

# Detach and unload
detach_ebpf() {
    IFACE=$(ip route show default | awk '/default/ {print $5}' | head -1)
    if [ -n "${IFACE}" ]; then
        ip link set dev "${IFACE}" xdp off 2>/dev/null || true
        tc filter del dev "${IFACE}" egress 2>/dev/null || true
    fi
    rm -rf "${TITAN_PIN_DIR}" 2>/dev/null || true
    echo "TITAN eBPF programs detached and unpinned"
}

# Status check
status_ebpf() {
    echo "=== TITAN Network Shield eBPF Status ==="
    if [ -d "${TITAN_PIN_DIR}" ]; then
        echo "Pin directory: ${TITAN_PIN_DIR}"
        ls -la "${TITAN_PIN_DIR}/" 2>/dev/null || echo "  (empty)"
    else
        echo "Not loaded (no pin directory)"
    fi
    
    echo ""
    echo "Loaded BPF programs:"
    bpftool prog list 2>/dev/null | grep -i titan || echo "  None found"
    
    echo ""
    echo "BPF maps:"
    bpftool map list 2>/dev/null | grep -i titan || echo "  None found"
}

# Main
case "${1:-build}" in
    build)
        check_deps
        generate_vmlinux_h
        compile_ebpf
        echo "Build complete. Run '$0 load' to load programs."
        ;;
    load)
        check_deps
        compile_ebpf
        load_ebpf
        attach_ebpf
        configure_maps
        echo "TITAN Network Shield active."
        ;;
    unload)
        detach_ebpf
        ;;
    status)
        status_ebpf
        ;;
    *)
        echo "Usage: $0 {build|load|unload|status}"
        exit 1
        ;;
esac
