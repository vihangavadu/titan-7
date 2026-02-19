# LUCID EMPIRE TITAN Class - eBPF Network Shield Makefile
# Purpose: Compile XDP program and loader for kernel-level OS masquerading

CC = gcc
CLANG = clang
LLVM_STRIP = llvm-strip
CFLAGS = -Wall -O2 -g
LDFLAGS = -lbpf -lelf -lz

# eBPF compilation flags
EBPF_CFLAGS = -O2 -target bpf -D__TARGET_ARCH_x86 -D__KERNEL__ -D__BPF_TRACING__
EBPF_INCLUDES = -I/usr/include/x86_64-linux-gnu -I/usr/include

# Source files
XDP_SOURCE = xdp_outbound.c
LOADER_SOURCE = xdp_loader.c

# Output files
XDP_OBJECT = xdp_outbound.o
LOADER_BINARY = xdp_loader

# Default target
all: $(XDP_OBJECT) $(LOADER_BINARY)

# Compile eBPF XDP program
$(XDP_OBJECT): $(XDP_SOURCE)
	@echo "[*] Compiling eBPF XDP program..."
	$(CLANG) $(EBPF_CFLAGS) $(EBPF_INCLUDES) -c $< -o $@
	$(LLVM_STRIP) -g $@
	@echo "[+] XDP object compiled: $@"

# Compile loader program
$(LOADER_BINARY): $(LOADER_SOURCE)
	@echo "[*] Compiling XDP loader..."
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)
	@echo "[+] Loader compiled: $@"

# Install system dependencies
install-deps:
	@echo "[*] Installing eBPF dependencies..."
	sudo apt-get update
	sudo apt-get install -y \
		libbpf-dev \
		libelf-dev \
		linux-headers-$(shell uname -r) \
		clang \
		llvm \
		llvm-dev \
		pkg-config
	@echo "[+] Dependencies installed"

# Set capabilities for non-root operation (alternative to sudo)
set-cap:
	@echo "[*] Setting capabilities for XDP loader..."
	sudo setcap cap_net_admin+ep $(LOADER_BINARY)
	@echo "[+] Capabilities set - can run without sudo"

# Deploy XDP program
deploy: all
	@echo "[*] Deploying XDP network shield..."
	sudo ./$(LOADER_BINARY) -i eth0

# Clean build artifacts
clean:
	rm -f $(XDP_OBJECT) $(LOADER_BINARY)
	@echo "[*] Build artifacts cleaned"

# Verify kernel version
check-kernel:
	@echo "[*] Checking kernel compatibility..."
	@uname -r | grep -E "^[5-9]\.|^[1-9][0-9]\." && \
		echo "[+] Kernel version compatible with XDP" || \
		echo "[-] Warning: Kernel may not support XDP (requires 5.8+)"

# Verify interface exists
check-interface:
	@echo "[*] Checking network interface..."
	@if ip link show eth0 >/dev/null 2>&1; then \
		echo "[+] Interface eth0 found"; \
	else \
		echo "[-] Interface eth0 not found"; \
		echo "Available interfaces:"; \
		ip link show | grep -E "^[0-9]+:" | cut -d: -f2 | sed 's/^ /  /'; \
	fi

# Full system check
check: check-kernel check-interface
	@echo "[*] System check complete"

# Development build with debug symbols
debug: CFLAGS += -DDEBUG -g3
debug: EBPF_CFLAGS += -DDEBUG
debug: all

# Production build (optimized)
release: CFLAGS += -DNDEBUG -O3
release: EBPF_CFLAGS += -DNDEBUG -O3
release: all

# Install as system service
install-service: $(LOADER_BINARY)
	@echo "[*] Installing XDP shield as system service..."
	sudo cp $(LOADER_BINARY) /usr/local/bin/
	sudo cp lucid-xdp.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable lucid-xdp
	@echo "[+] Service installed. Start with: sudo systemctl start lucid-xdp"

# Uninstall service
uninstall-service:
	@echo "[*] Removing XDP shield service..."
	sudo systemctl stop lucid-xdp || true
	sudo systemctl disable lucid-xdp || true
	sudo rm -f /etc/systemd/system/lucid-xdp.service
	sudo systemctl daemon-reload
	sudo rm -f /usr/local/bin/$(LOADER_BINARY)
	@echo "[+] Service removed"

# Help target
help:
	@echo "LUCID EMPIRE TITAN Class - Build System"
	@echo "======================================"
	@echo ""
	@echo "Targets:"
	@echo "  all           - Build XDP program and loader"
	@echo "  install-deps  - Install required system dependencies"
	@echo "  set-cap       - Set capabilities for non-root operation"
	@echo "  deploy        - Build and deploy XDP shield"
	@echo "  clean         - Remove build artifacts"
	@echo "  check         - Verify system compatibility"
	@echo "  debug         - Build with debug symbols"
	@echo "  release       - Build optimized production version"
	@echo "  install-service - Install as systemd service"
	@echo "  uninstall-service - Remove systemd service"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Iron Rules Compliance:"
	@echo "  - Requires root or CAP_NET_ADMIN capability"
	@echo "  - Kernel 5.8+ required for XDP support"
	@echo "  - Interface binding mandatory"

.PHONY: all clean install-deps set-cap deploy check-kernel check-interface check debug release install-service uninstall-service help
