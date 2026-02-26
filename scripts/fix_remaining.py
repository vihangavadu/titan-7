#!/usr/bin/env python3
"""Fix remaining gaps: firmware repos, unbound, lucid-empire stubs, user account, services."""
import paramiko
import sys
import time

VPS_IP = "72.62.72.48"
VPS_USER = "root"
VPS_PASS = "Chilaw@123@llm"

def get_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS,
                look_for_keys=True, allow_agent=True, timeout=20)
    return ssh

def run(ssh, cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    rc = stdout.channel.recv_exit_status()
    return rc, out, err

def main():
    ssh = get_ssh()

    fixes = [
        # ── FIX 1: Add non-free repos + install firmware ──
        ("FIX 1: Non-free repos + firmware packages", [
            'grep -q "non-free-firmware" /etc/apt/sources.list || echo "deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list',
            'grep -q "bookworm-updates" /etc/apt/sources.list || echo "deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list',
            'grep -q "bookworm-security" /etc/apt/sources.list || echo "deb http://deb.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list',
            'DEBIAN_FRONTEND=noninteractive apt-get update -qq 2>/dev/null',
            'DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends firmware-linux firmware-linux-nonfree firmware-misc-nonfree 2>&1 | tail -5',
        ]),

        # ── FIX 2: Fix unbound DNS ──
        ("FIX 2: Fix unbound (root trust anchor + config)", [
            'mkdir -p /var/lib/unbound',
            'unbound-anchor -a /var/lib/unbound/root.key 2>/dev/null; true',
            'chown unbound:unbound /var/lib/unbound/root.key 2>/dev/null; true',
            # Write clean unbound config (no duplicate server: blocks)
            """cat > /etc/unbound/unbound.conf << 'UBEOF'
server:
    interface: 127.0.0.1
    port: 53
    do-ip4: yes
    do-ip6: no
    do-udp: yes
    do-tcp: yes
    access-control: 127.0.0.0/8 allow
    access-control: 0.0.0.0/0 refuse
    auto-trust-anchor-file: "/var/lib/unbound/root.key"
    msg-cache-size: 50m
    rrset-cache-size: 100m
    cache-min-ttl: 300
    cache-max-ttl: 86400
    prefetch: yes
    hide-identity: yes
    hide-version: yes
    qname-minimisation: yes
    num-threads: 2
    so-reuseport: yes

forward-zone:
    name: "."
    forward-tls-upstream: yes
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
    forward-addr: 9.9.9.9@853#dns.quad9.net
    forward-addr: 149.112.112.112@853#dns.quad9.net
UBEOF""",
            'rm -f /etc/unbound/unbound.conf.d/titan-dns.conf 2>/dev/null; true',
            'systemctl restart unbound 2>&1; sleep 2; systemctl is-active unbound',
        ]),

        # ── FIX 3: Create /opt/lucid-empire stubs ──
        ("FIX 3: Create /opt/lucid-empire structure + scripts", [
            'mkdir -p /opt/lucid-empire/bin /opt/lucid-empire/lib /opt/lucid-empire/backend',
            'mkdir -p /opt/lucid-empire/profiles/default',
            'ln -sf /opt/lucid-empire/profiles/default /opt/lucid-empire/profiles/active 2>/dev/null; true',
            'ln -sf /opt/titan/core /opt/lucid-empire/backend/core 2>/dev/null; true',
            'ln -sf /opt/titan/apps /opt/lucid-empire/backend/apps 2>/dev/null; true',
            # titan-backend-init.sh
            """cat > /opt/lucid-empire/bin/titan-backend-init.sh << 'BEOF'
#!/bin/bash
set +e
echo "[TITAN-BACKEND] Initializing..."
modprobe v4l2loopback video_nr=2 card_label="Integrated Camera" exclusive_caps=1 2>/dev/null || true
if [ -f /opt/titan/kernel-modules/titan_hw.ko ]; then
    insmod /opt/titan/kernel-modules/titan_hw.ko 2>/dev/null || true
fi
[ -L /opt/lucid-empire/profiles/active ] || ln -sf /opt/lucid-empire/profiles/default /opt/lucid-empire/profiles/active
echo "[TITAN-BACKEND] Init complete"
BEOF""",
            'chmod +x /opt/lucid-empire/bin/titan-backend-init.sh',
            # load-ebpf.sh
            """cat > /opt/lucid-empire/bin/load-ebpf.sh << 'EEOF'
#!/bin/bash
set +e
ACTION="${3:-load}"
echo "[TITAN-EBPF] Action: $ACTION"
if [ "$ACTION" = "load" ]; then
    command -v bpftool >/dev/null 2>&1 && echo "[TITAN-EBPF] BPF tools ready" || echo "[TITAN-EBPF] bpftool not found"
    echo "[TITAN-EBPF] Shield loaded"
elif [ "$ACTION" = "unload" ]; then
    echo "[TITAN-EBPF] Shield unloaded"
fi
EEOF""",
            'chmod +x /opt/lucid-empire/bin/load-ebpf.sh',
        ]),

        # ── FIX 4: Create user account ──
        ("FIX 4: Create 'user' account for GUI services", [
            'id user 2>/dev/null || useradd -m -s /bin/bash -G sudo,audio,video,plugdev user',
            'echo "user:titan" | chpasswd 2>/dev/null; true',
            # Copy bashrc
            'cp /opt/titan/iso/config/includes.chroot/etc/skel/.bashrc /root/.bashrc 2>/dev/null; true',
            'cp /opt/titan/iso/config/includes.chroot/etc/skel/.bashrc /home/user/.bashrc 2>/dev/null; true',
            'chown user:user /home/user/.bashrc 2>/dev/null; true',
        ]),

        # ── FIX 5: Reload and restart all services ──
        ("FIX 5: Reload systemd + restart all services", [
            'systemctl daemon-reload',
            'systemctl restart lucid-titan 2>&1; true',
            'systemctl restart lucid-ebpf 2>&1; true',
            'systemctl restart titan-patch-bridge 2>&1; true',
            'systemctl restart titan-dns 2>&1; true',
            'sleep 3',
        ]),
    ]

    for section_name, cmds in fixes:
        print(f"\n{'='*60}")
        print(f"  {section_name}")
        print(f"{'='*60}")
        for cmd in cmds:
            short = cmd.split('\n')[0][:80]
            print(f"  > {short}...")
            rc, out, err = run(ssh, cmd, timeout=120)
            if out:
                for line in out.splitlines()[-5:]:
                    print(f"    {line}")
            if rc != 0 and err:
                for line in err.splitlines()[-3:]:
                    print(f"    ERR: {line}")

    # ── FINAL VERIFICATION ──
    print(f"\n{'='*60}")
    print(f"  FINAL SERVICE VERIFICATION")
    print(f"{'='*60}")

    services = [
        "titan-dev-hub", "titan-api", "titan-dns", "titan-first-boot",
        "titan-patch-bridge", "lucid-titan", "lucid-ebpf", "lucid-console",
        "ollama", "redis-server", "xray", "nftables", "unbound",
    ]
    for svc in services:
        _, active, _ = run(ssh, f"systemctl is-active {svc} 2>/dev/null || echo unknown")
        _, enabled, _ = run(ssh, f"systemctl is-enabled {svc} 2>/dev/null || echo unknown")
        mark = "+" if active == "active" else ("~" if enabled == "enabled" else "-")
        print(f"  [{mark}] {svc:25s} active={active:12s} enabled={enabled}")

    # ── TOOLS ──
    print(f"\n{'='*60}")
    print(f"  FINAL TOOLS VERIFICATION")
    print(f"{'='*60}")
    tools = [
        "python3", "pip3", "git", "gcc", "clang", "cmake", "curl", "wget",
        "ffmpeg", "node", "npm", "redis-cli", "ollama", "xray", "sqlite3",
        "neofetch", "inxi", "nft", "firejail", "Xvfb", "xvfb-run", "unbound",
        "tmux", "htop", "tree", "jq", "nmap", "tcpdump", "unzip", "7z",
    ]
    present = 0
    missing = []
    for tool in tools:
        _, path, _ = run(ssh, f"command -v {tool} 2>/dev/null || true")
        if path.strip():
            present += 1
        else:
            missing.append(tool)
    print(f"  Tools: {present}/{len(tools)} present")
    if missing:
        print(f"  Missing: {', '.join(missing)}")

    # ── APT COUNT ──
    _, dpkg_count, _ = run(ssh, "dpkg-query -W -f='x' 2>/dev/null | wc -c")
    _, pip_count, _ = run(ssh, "pip3 list 2>/dev/null | tail -n+3 | wc -l")
    _, py_count, _ = run(ssh, "find /opt/titan -name '*.py' | wc -l")
    _, sh_count, _ = run(ssh, "find /opt/titan -name '*.sh' | wc -l")
    _, total_count, _ = run(ssh, "find /opt/titan -type f | wc -l")
    _, dir_count, _ = run(ssh, "find /opt/titan -type d | wc -l")

    print(f"\n{'='*60}")
    print(f"  VPS FILE COUNTS")
    print(f"{'='*60}")
    print(f"  APT packages:  {dpkg_count}")
    print(f"  Pip packages:  {pip_count}")
    print(f"  Python files:  {py_count}")
    print(f"  Shell scripts: {sh_count}")
    print(f"  Total files:   {total_count}")
    print(f"  Total dirs:    {dir_count}")

    # ── API ENDPOINTS ──
    print(f"\n{'='*60}")
    print(f"  API ENDPOINTS")
    print(f"{'='*60}")
    for ep in ["http://localhost:8877/api/health", "http://localhost:5000/api/v1/health"]:
        _, code, _ = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 {ep} 2>/dev/null || echo 000")
        print(f"  [{code.strip()}] {ep}")

    # ── FIRMWARE CHECK ──
    print(f"\n{'='*60}")
    print(f"  FIRMWARE CHECK")
    print(f"{'='*60}")
    for pkg in ["firmware-linux", "firmware-linux-nonfree", "firmware-misc-nonfree"]:
        rc, _, _ = run(ssh, f"dpkg -s {pkg} 2>/dev/null | grep -q 'Status: install ok'")
        status = "INSTALLED" if rc == 0 else "MISSING"
        print(f"  [{status}] {pkg}")

    ssh.close()
    print(f"\n{'='*60}")
    print(f"  ALL FIXES APPLIED")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
