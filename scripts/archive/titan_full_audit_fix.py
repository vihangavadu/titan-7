#!/usr/bin/env python3
"""
TITAN OS — Full Audit & Fix
Cross-references the ENTIRE repo tree against the VPS.
Finds every missing apt pkg, pip pkg, systemd unit, config file,
desktop entry, binary, and installs/deploys/activates ALL of them.
"""

import json
import os
import sys
import time
import socket
from pathlib import Path, PurePosixPath

import paramiko

VPS_IP = "72.62.72.48"
VPS_USER = "root"
VPS_PASS = "Chilaw@123@llm"
VPS_ROOT = "/opt/titan"
LOCAL_ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = Path.home() / ".ssh" / "id_ed25519"
INCLUDES = LOCAL_ROOT / "iso" / "config" / "includes.chroot"

# ═══════════════════════════════════════════════════════════════════
# EXPECTED APT PACKAGES — extracted from all 3 package-lists
# Excludes: live-boot, live-config, live-config-systemd, task-xfce-desktop
# (VPS uses tigervnc for headless GUI instead of full desktop)
# ═══════════════════════════════════════════════════════════════════
EXPECTED_APT_PACKAGES = [
    # Core system (custom.list.chroot)
    "xfce4-terminal", "lightdm", "lightdm-gtk-greeter", "network-manager",
    "openssh-server", "rofi",
    # Dev tools
    "build-essential", "gcc", "git", "vim", "curl", "wget", "clang", "llvm",
    "cmake", "pkg-config", "libssl-dev", "libffi-dev", "libgl-dev",
    "mesa-common-dev", "libx11-dev",
    # eBPF
    "linux-headers-amd64", "bpfcc-tools", "libbpf-dev", "bpftrace", "iproute2",
    # Python
    "python3", "python3-pip", "python3-venv", "python3-dev",
    # Network
    "tcpdump", "wireshark", "nmap", "netcat-openbsd", "dnsutils",
    "iptables", "nftables",
    # Time
    "libfaketime",
    # Browsers (headless)
    "firefox-esr", "chromium",
    "libgtk-3-0", "libdbus-glib-1-2", "libasound2", "libx11-xcb1", "libxtst6",
    # Isolation
    "cgroup-tools", "systemd-container",
    # Utilities
    "jq", "sqlite3", "tree", "htop", "tmux", "unzip", "p7zip-full",
    # Python system pkgs
    "python3-pyqt6", "python3-dotenv", "python3-snappy",
    "python3-cryptography", "python3-nacl",
    "python3-requests", "python3-httpx", "python3-aiohttp",
    "python3-flask", "python3-jinja2",
    "python3-numpy", "python3-pil", "python3-psutil", "python3-yaml",
    "python3-dateutil", "python3-pydantic", "python3-tk",
    # DB/Storage
    "libsnappy-dev", "libsodium-dev",
    # Fonts
    "fontconfig", "fonts-liberation", "fonts-dejavu", "fonts-noto", "fonts-cantarell",
    # HW ID
    "dmidecode", "lshw", "pciutils", "usbutils",
    # Audio/Video
    "libpulse0", "libopengl0", "libglx-mesa0", "mesa-utils", "ffmpeg",
    "v4l2loopback-dkms",
    # Proxy
    "proxychains4", "torsocks",
    # Security
    "apparmor", "firejail",
    # Firmware
    "firmware-linux", "firmware-linux-nonfree", "firmware-misc-nonfree",
    # eBPF extras
    "libelf-dev", "zlib1g-dev",
    # Sysinfo
    "inxi", "neofetch", "lsb-release",
    # Compression
    "zstd", "lz4",
    # Desktop integration
    "zenity", "xdg-utils", "desktop-file-utils",
    # Node
    "nodejs", "npm",
    # Camoufox deps
    "libgbm1", "libdrm2", "libxt6", "xvfb",
    # Waydroid deps (custom.list + waydroid.list)
    "lxc", "python3-lxc", "dnsmasq-base", "dkms", "libgles2-mesa", "bridge-utils",
    # USB
    "usb-modeswitch",
    # dbus
    "dbus-x11",
    # DNS privacy
    "unbound", "unbound-anchor",
    # Desktop UX (V7.0.3)
    "tint2", "conky-all", "feh", "picom", "dunst",
    "plymouth", "plymouth-themes",
    "papirus-icon-theme", "arc-theme",
    "pcmanfm",
    # VPS
    "acpid", "ifupdown", "e2fsprogs",
    # KYC module (kyc_module.list.chroot)
    "v4l2loopback-utils",
    "gstreamer1.0-tools", "gstreamer1.0-plugins-good", "gstreamer1.0-plugins-bad",
    "python3-opencv", "python3-scipy", "vainfo",
    # VPS-specific (from build_vps_image.sh)
    "tigervnc-standalone-server", "tigervnc-common",
    # Cert
    "ca-certificates", "ssl-cert",
    # Redis
    "redis-server",
]

# ═══════════════════════════════════════════════════════════════════
# EXPECTED PIP PACKAGES — from hooks + requirements.txt files
# ═══════════════════════════════════════════════════════════════════
EXPECTED_PIP_PACKAGES = [
    # Hook 080 (Cognitive Core)
    "openai", "onnxruntime", "scipy",
    # Hook 070 (Camoufox)
    "camoufox", "browserforge", "playwright",
    # Hook 99 (Phase 3)
    "aioquic", "pytz", "lz4", "stripe", "cryptography",
    "fastapi", "uvicorn", "insightface",
    "httpx", "pydantic", "aiohttp",
    # apps/requirements.txt
    "gitpython", "black", "flake8", "pylint", "orjson", "structlog",
    "watchdog", "pyyaml", "python-dotenv", "jedi", "websockets",
    "python-dateutil", "jsonschema", "tqdm", "nltk",
    "chromadb", "sentence-transformers",
    "langchain", "langchain-core", "langchain-ollama", "langchain-community",
    "duckduckgo-search", "geoip2", "redis", "minio",
    # core/requirements_oblivion.txt
    "pycryptodome", "websocket-client", "selenium",
    # tests
    "pytest", "pytest-cov", "pytest-asyncio", "pytest-mock",
    "pytest-html", "pytest-timeout", "faker", "coverage",
    # Additional
    "prometheus-client", "flask-cors", "gunicorn",
    "requests", "numpy", "pandas",
    "python-socks", "urllib3", "certifi",
]

# ═══════════════════════════════════════════════════════════════════
# EXPECTED CLI TOOLS — must be in PATH
# ═══════════════════════════════════════════════════════════════════
EXPECTED_TOOLS = [
    "python3", "pip3", "git", "gcc", "clang", "cmake",
    "curl", "wget", "vim", "tmux", "htop", "tree", "jq",
    "nmap", "tcpdump", "ffmpeg", "node", "npm",
    "redis-cli", "ollama", "xray",
    "sqlite3", "unzip", "7z",
    "xvfb-run", "Xvfb",
    "neofetch", "inxi",
    "unbound", "nft",
    "firejail",
]

# ═══════════════════════════════════════════════════════════════════
# EXPECTED SYSTEMD SERVICES — from includes.chroot + hooks
# ═══════════════════════════════════════════════════════════════════
EXPECTED_SERVICES = {
    # From includes.chroot/etc/systemd/system/
    "titan-dev-hub":     {"unit_file": "/etc/systemd/system/titan-dev-hub.service",     "enable": True, "start": True},
    "titan-dns":         {"unit_file": "/etc/systemd/system/titan-dns.service",         "enable": True, "start": True},
    "titan-first-boot":  {"unit_file": "/etc/systemd/system/titan-first-boot.service",  "enable": True, "start": False},
    "titan-patch-bridge": {"unit_file": "/etc/systemd/system/titan-patch-bridge.service","enable": True, "start": True},
    "lucid-titan":       {"unit_file": "/etc/systemd/system/lucid-titan.service",       "enable": True, "start": False},
    "lucid-ebpf":        {"unit_file": "/etc/systemd/system/lucid-ebpf.service",        "enable": True, "start": False},
    "lucid-console":     {"unit_file": "/etc/systemd/system/lucid-console.service",     "enable": False, "start": False},
    # From master installer / hooks
    "titan-api":         {"unit_file": "/etc/systemd/system/titan-api.service",         "enable": True, "start": True},
    "ollama":            {"unit_file": "/etc/systemd/system/ollama.service",            "enable": True, "start": True},
    "redis-server":      {"unit_file": None,                                            "enable": True, "start": True},
    "xray":              {"unit_file": None,                                            "enable": True, "start": True},
    "nftables":          {"unit_file": None,                                            "enable": True, "start": False},
    "unbound":           {"unit_file": None,                                            "enable": True, "start": True},
}

# ═══════════════════════════════════════════════════════════════════
# EXPECTED CONFIG FILES — from includes.chroot/etc/
# Map: VPS path -> local source path relative to includes.chroot
# ═══════════════════════════════════════════════════════════════════
EXPECTED_CONFIGS = {
    "/etc/os-release": "etc/os-release",
    "/etc/issue": "etc/issue",
    "/etc/issue.net": "etc/issue.net",
    "/etc/hosts": "etc/hosts",
    "/etc/lsb-release": "etc/lsb-release",
    "/etc/nftables.conf": "etc/nftables.conf",
    "/etc/fonts/local.conf": "etc/fonts/local.conf",
    "/etc/pulse/daemon.conf": "etc/pulse/daemon.conf",
    "/etc/conky/titan.conf": "etc/conky/titan.conf",
    "/etc/neofetch/config.conf": "etc/neofetch/config.conf",
    "/etc/profile.d/titan-prompt.sh": "etc/profile.d/titan-prompt.sh",
    "/etc/security/limits.d/disable-cores.conf": "etc/security/limits.d/disable-cores.conf",
    "/etc/sudoers.d/titan-ops": "etc/sudoers.d/titan-ops",
    "/etc/sysctl.d/99-titan-hardening.conf": "etc/sysctl.d/99-titan-hardening.conf",
    "/etc/sysctl.d/99-titan-stealth.conf": "etc/sysctl.d/99-titan-stealth.conf",
    "/etc/NetworkManager/conf.d/10-titan-privacy.conf": "etc/NetworkManager/conf.d/10-titan-privacy.conf",
    "/etc/apt/preferences.d/00-titan-pin-stable": "etc/apt/preferences.d/00-titan-pin-stable",
    "/etc/default/grub.d/titan-branding.cfg": "etc/default/grub.d/titan-branding.cfg",
    "/etc/udev/rules.d/99-titan-usb.rules": "etc/udev/rules.d/99-titan-usb.rules",
    "/etc/unbound/unbound.conf": "etc/unbound/unbound.conf",
    "/etc/unbound/unbound.conf.d/titan-dns.conf": "etc/unbound/unbound.conf.d/titan-dns.conf",
    "/etc/polkit-1/localauthority/50-local.d/10-titan-nopasswd.pkla": "etc/polkit-1/localauthority/50-local.d/10-titan-nopasswd.pkla",
    "/etc/systemd/coredump.conf.d/titan-no-coredump.conf": "etc/systemd/coredump.conf.d/titan-no-coredump.conf",
    "/etc/systemd/journald.conf.d/titan-privacy.conf": "etc/systemd/journald.conf.d/titan-privacy.conf",
    "/etc/xdg/dunst/dunstrc": "etc/xdg/dunst/dunstrc",
    "/etc/xdg/openbox/autostart": "etc/xdg/openbox/autostart",
    "/etc/lightdm/lightdm.conf": "etc/lightdm/lightdm.conf",
    "/etc/lightdm/lightdm-gtk-greeter.conf": "etc/lightdm/lightdm-gtk-greeter.conf",
    "/root/.bashrc": "etc/skel/.bashrc",
}

# ═══════════════════════════════════════════════════════════════════
# EXPECTED DESKTOP ENTRIES
# ═══════════════════════════════════════════════════════════════════
EXPECTED_DESKTOP_ENTRIES = {
    "/usr/share/applications/titan-unified.desktop": "usr/share/applications/titan-unified.desktop",
    "/usr/share/applications/titan-browser.desktop": "usr/share/applications/titan-browser.desktop",
    "/usr/share/applications/titan-bug-reporter.desktop": "usr/share/applications/titan-bug-reporter.desktop",
    "/usr/share/applications/titan-cerberus.desktop": "usr/share/applications/titan-cerberus.desktop",
    "/usr/share/applications/titan-genesis.desktop": "usr/share/applications/titan-genesis.desktop",
    "/usr/share/applications/titan-kyc.desktop": "usr/share/applications/titan-kyc.desktop",
    "/usr/share/applications/titan-configure.desktop": "usr/share/applications/titan-configure.desktop",
    "/usr/share/applications/titan-files.desktop": "usr/share/applications/titan-files.desktop",
    "/usr/share/applications/titan-install.desktop": "usr/share/applications/titan-install.desktop",
    "/usr/share/applications/titan-terminal.desktop": "usr/share/applications/titan-terminal.desktop",
}

# ═══════════════════════════════════════════════════════════════════
# EXPECTED SYSTEMD UNIT FILES — from includes.chroot
# ═══════════════════════════════════════════════════════════════════
EXPECTED_UNIT_FILES = {
    "/etc/systemd/system/titan-dev-hub.service": "etc/systemd/system/titan-dev-hub.service",
    "/etc/systemd/system/titan-dns.service": "etc/systemd/system/titan-dns.service",
    "/etc/systemd/system/titan-first-boot.service": "etc/systemd/system/titan-first-boot.service",
    "/etc/systemd/system/titan-patch-bridge.service": "etc/systemd/system/titan-patch-bridge.service",
    "/etc/systemd/system/lucid-titan.service": "etc/systemd/system/lucid-titan.service",
    "/etc/systemd/system/lucid-ebpf.service": "etc/systemd/system/lucid-ebpf.service",
    "/etc/systemd/system/lucid-console.service": "etc/systemd/system/lucid-console.service",
}

# ═══════════════════════════════════════════════════════════════════
# EXPECTED THEME/BRANDING ARTIFACTS — from hook 060
# ═══════════════════════════════════════════════════════════════════
EXPECTED_THEME_FILES = [
    "/etc/gtk-3.0/settings.ini",
    "/etc/environment.d/50-titan-qt.conf",
    "/usr/share/themes/TitanDark/openbox-3/themerc",
    "/etc/dpkg/origins/titanos",
    "/etc/modprobe.d/titan-camera.conf",
    "/etc/modprobe.d/titan-blacklist.conf",
    "/etc/profile.d/titan-env.sh",
    "/etc/environment.d/50-titan.conf",
]


def get_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {"hostname": VPS_IP, "username": VPS_USER, "timeout": 20,
              "look_for_keys": True, "allow_agent": True}
    if KEY_FILE.exists():
        kwargs["key_filename"] = str(KEY_FILE)
    if VPS_PASS:
        kwargs["password"] = VPS_PASS
    ssh.connect(**kwargs)
    return ssh


def ssh_run(ssh, cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def ssh_stream(ssh, cmd, timeout=1800):
    """Run command and stream output live."""
    channel = ssh.get_transport().open_session()
    channel.settimeout(timeout)
    channel.exec_command(cmd)
    buf = ""
    while True:
        try:
            if channel.recv_ready():
                chunk = channel.recv(8192).decode("utf-8", errors="replace")
                sys.stdout.write(chunk)
                sys.stdout.flush()
                buf += chunk
            if channel.exit_status_ready():
                while channel.recv_ready():
                    chunk = channel.recv(8192).decode("utf-8", errors="replace")
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    buf += chunk
                break
        except socket.timeout:
            continue
        except Exception:
            break
        time.sleep(0.05)
    return channel.recv_exit_status(), buf


def upload_file(sftp, local_path, remote_path):
    """Upload a local file to VPS, creating parent dirs."""
    parent = str(PurePosixPath(remote_path).parent)
    try:
        sftp.stat(parent)
    except FileNotFoundError:
        # Create parent dirs recursively via exec
        pass
    try:
        sftp.put(str(local_path), remote_path)
        return True
    except Exception as e:
        print(f"    UPLOAD FAIL: {local_path} -> {remote_path}: {e}")
        return False


def main():
    print("=" * 72)
    print("  TITAN OS — FULL AUDIT & FIX")
    print("  Cross-references entire repo against VPS")
    print("=" * 72)
    print()

    ssh = get_ssh()
    sftp = ssh.open_sftp()

    report = {
        "apt_missing": [],
        "apt_installed": [],
        "pip_missing": [],
        "pip_installed": [],
        "tools_missing": [],
        "tools_present": [],
        "configs_missing": [],
        "configs_present": [],
        "units_missing": [],
        "units_present": [],
        "desktop_missing": [],
        "desktop_present": [],
        "theme_missing": [],
        "theme_present": [],
        "services_status": {},
    }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: AUDIT APT PACKAGES
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 1: Audit APT Packages ═══")
    rc, installed_raw, _ = ssh_run(ssh, "dpkg-query -W -f='${Package}\\n' 2>/dev/null", timeout=30)
    installed_apt = set(installed_raw.splitlines()) if rc == 0 else set()
    print(f"  VPS has {len(installed_apt)} apt packages installed.")

    for pkg in EXPECTED_APT_PACKAGES:
        if pkg in installed_apt:
            report["apt_installed"].append(pkg)
        else:
            report["apt_missing"].append(pkg)

    print(f"  Expected: {len(EXPECTED_APT_PACKAGES)}")
    print(f"  Present:  {len(report['apt_installed'])}")
    print(f"  MISSING:  {len(report['apt_missing'])}")
    if report["apt_missing"]:
        print(f"  Missing packages: {', '.join(report['apt_missing'][:30])}...")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: AUDIT PIP PACKAGES
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 2: Audit Pip Packages ═══")
    rc, pip_raw, _ = ssh_run(ssh, "pip3 list --format=columns 2>/dev/null | tail -n+3 | awk '{print tolower($1)}'", timeout=30)
    installed_pip = set(pip_raw.splitlines()) if rc == 0 else set()
    # Normalize: pip uses dashes/underscores interchangeably
    installed_pip_norm = set()
    for p in installed_pip:
        installed_pip_norm.add(p.lower().replace("-", "_").replace(".", "_"))
        installed_pip_norm.add(p.lower().replace("_", "-"))
        installed_pip_norm.add(p.lower())

    for pkg in EXPECTED_PIP_PACKAGES:
        norm = pkg.lower().replace("-", "_").replace(".", "_")
        norm2 = pkg.lower().replace("_", "-")
        if norm in installed_pip_norm or norm2 in installed_pip_norm or pkg.lower() in installed_pip_norm:
            report["pip_installed"].append(pkg)
        else:
            report["pip_missing"].append(pkg)

    print(f"  Expected: {len(EXPECTED_PIP_PACKAGES)}")
    print(f"  Present:  {len(report['pip_installed'])}")
    print(f"  MISSING:  {len(report['pip_missing'])}")
    if report["pip_missing"]:
        print(f"  Missing: {', '.join(report['pip_missing'][:30])}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: AUDIT CLI TOOLS
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 3: Audit CLI Tools ═══")
    for tool in EXPECTED_TOOLS:
        rc, path, _ = ssh_run(ssh, f"command -v {tool} 2>/dev/null || true", timeout=10)
        if path.strip():
            report["tools_present"].append(tool)
        else:
            report["tools_missing"].append(tool)
    print(f"  Expected: {len(EXPECTED_TOOLS)}")
    print(f"  Present:  {len(report['tools_present'])}")
    print(f"  MISSING:  {len(report['tools_missing'])}")
    if report["tools_missing"]:
        print(f"  Missing: {', '.join(report['tools_missing'])}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: AUDIT CONFIG FILES
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 4: Audit Config Files ═══")
    for vps_path, local_rel in EXPECTED_CONFIGS.items():
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc == 0:
            report["configs_present"].append(vps_path)
        else:
            report["configs_missing"].append((vps_path, local_rel))
    print(f"  Expected: {len(EXPECTED_CONFIGS)}")
    print(f"  Present:  {len(report['configs_present'])}")
    print(f"  MISSING:  {len(report['configs_missing'])}")
    if report["configs_missing"]:
        for vp, lr in report["configs_missing"]:
            print(f"    [-] {vp}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: AUDIT SYSTEMD UNIT FILES
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 5: Audit Systemd Unit Files ═══")
    for vps_path, local_rel in EXPECTED_UNIT_FILES.items():
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc == 0:
            report["units_present"].append(vps_path)
        else:
            report["units_missing"].append((vps_path, local_rel))
    print(f"  Expected: {len(EXPECTED_UNIT_FILES)}")
    print(f"  Present:  {len(report['units_present'])}")
    print(f"  MISSING:  {len(report['units_missing'])}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 6: AUDIT DESKTOP ENTRIES
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 6: Audit Desktop Entries ═══")
    for vps_path, local_rel in EXPECTED_DESKTOP_ENTRIES.items():
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc == 0:
            report["desktop_present"].append(vps_path)
        else:
            report["desktop_missing"].append((vps_path, local_rel))
    print(f"  Expected: {len(EXPECTED_DESKTOP_ENTRIES)}")
    print(f"  Present:  {len(report['desktop_present'])}")
    print(f"  MISSING:  {len(report['desktop_missing'])}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 7: AUDIT THEME/BRANDING FILES
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 7: Audit Theme/Branding ═══")
    for vps_path in EXPECTED_THEME_FILES:
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc == 0:
            report["theme_present"].append(vps_path)
        else:
            report["theme_missing"].append(vps_path)
    print(f"  Expected: {len(EXPECTED_THEME_FILES)}")
    print(f"  Present:  {len(report['theme_present'])}")
    print(f"  MISSING:  {len(report['theme_missing'])}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 8: AUDIT SERVICES STATUS
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ PHASE 8: Audit Service Status ═══")
    for svc, spec in EXPECTED_SERVICES.items():
        _, active, _ = ssh_run(ssh, f"systemctl is-active {svc} 2>/dev/null || echo unknown", timeout=10)
        _, enabled, _ = ssh_run(ssh, f"systemctl is-enabled {svc} 2>/dev/null || echo unknown", timeout=10)
        report["services_status"][svc] = {
            "active": active.strip(),
            "enabled": enabled.strip(),
            "want_enable": spec["enable"],
            "want_start": spec["start"],
        }
        status_mark = "+" if active.strip() == "active" else "-"
        print(f"  [{status_mark}] {svc}: active={active.strip()}, enabled={enabled.strip()}")

    # ═══════════════════════════════════════════════════════════════
    # GAP SUMMARY
    # ═══════════════════════════════════════════════════════════════
    total_missing = (
        len(report["apt_missing"]) + len(report["pip_missing"]) +
        len(report["tools_missing"]) + len(report["configs_missing"]) +
        len(report["units_missing"]) + len(report["desktop_missing"]) +
        len(report["theme_missing"])
    )
    print("\n" + "=" * 72)
    print(f"  GAP SUMMARY: {total_missing} items missing")
    print(f"    APT:     {len(report['apt_missing'])} missing")
    print(f"    Pip:     {len(report['pip_missing'])} missing")
    print(f"    Tools:   {len(report['tools_missing'])} missing")
    print(f"    Configs: {len(report['configs_missing'])} missing")
    print(f"    Units:   {len(report['units_missing'])} missing")
    print(f"    Desktop: {len(report['desktop_missing'])} missing")
    print(f"    Theme:   {len(report['theme_missing'])} missing")
    print("=" * 72)

    if total_missing == 0:
        print("\n  ALL CHECKS PASSED — Titan OS is fully installed!")
        ssh.close()
        return

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 1: INSTALL MISSING APT PACKAGES
    # ═══════════════════════════════════════════════════════════════
    if report["apt_missing"]:
        print(f"\n═══ FIX: Installing {len(report['apt_missing'])} missing APT packages ═══")
        pkgs = " ".join(report["apt_missing"])
        fix_script = f"""#!/bin/bash
set +e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends {pkgs} 2>&1 | tail -20
echo "APT_FIX_DONE"
"""
        rc, out = ssh_stream(ssh, f"bash -c '{fix_script.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'")
        # For packages that may not exist, try individually
        still_missing = []
        for pkg in report["apt_missing"]:
            rc2, _, _ = ssh_run(ssh, f"dpkg -s {pkg} 2>/dev/null | grep -q 'Status: install ok'", timeout=10)
            if rc2 != 0:
                still_missing.append(pkg)
        if still_missing:
            print(f"  Retrying {len(still_missing)} packages individually...")
            for pkg in still_missing:
                rc2, out2, _ = ssh_run(ssh, f"DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends {pkg} 2>&1 | tail -3", timeout=60)
                status = "OK" if rc2 == 0 else "UNAVAIL"
                print(f"    [{status}] {pkg}")

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 2: INSTALL MISSING PIP PACKAGES
    # ═══════════════════════════════════════════════════════════════
    if report["pip_missing"]:
        print(f"\n═══ FIX: Installing {len(report['pip_missing'])} missing pip packages ═══")
        pkgs = " ".join(report["pip_missing"])
        cmd = f"pip3 install --no-cache-dir --break-system-packages {pkgs} 2>&1 | tail -10"
        rc, out = ssh_stream(ssh, cmd)

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 3: DEPLOY MISSING CONFIG FILES
    # ═══════════════════════════════════════════════════════════════
    if report["configs_missing"]:
        print(f"\n═══ FIX: Deploying {len(report['configs_missing'])} missing config files ═══")
        for vps_path, local_rel in report["configs_missing"]:
            local_path = INCLUDES / local_rel.replace("/", os.sep)
            if local_path.exists():
                # Create remote parent dir
                parent = str(PurePosixPath(vps_path).parent)
                ssh_run(ssh, f"mkdir -p {parent}")
                upload_file(sftp, local_path, vps_path)
                print(f"    [DEPLOYED] {vps_path}")
            else:
                print(f"    [SKIP] {vps_path} (no local source at {local_path})")

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 4: DEPLOY MISSING SYSTEMD UNIT FILES
    # ═══════════════════════════════════════════════════════════════
    if report["units_missing"]:
        print(f"\n═══ FIX: Deploying {len(report['units_missing'])} missing systemd units ═══")
        for vps_path, local_rel in report["units_missing"]:
            local_path = INCLUDES / local_rel.replace("/", os.sep)
            if local_path.exists():
                ssh_run(ssh, f"mkdir -p {str(PurePosixPath(vps_path).parent)}")
                upload_file(sftp, local_path, vps_path)
                print(f"    [DEPLOYED] {vps_path}")
            else:
                print(f"    [SKIP] {vps_path}")

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 5: DEPLOY MISSING DESKTOP ENTRIES
    # ═══════════════════════════════════════════════════════════════
    if report["desktop_missing"]:
        print(f"\n═══ FIX: Deploying {len(report['desktop_missing'])} missing desktop entries ═══")
        for vps_path, local_rel in report["desktop_missing"]:
            local_path = INCLUDES / local_rel.replace("/", os.sep)
            if local_path.exists():
                ssh_run(ssh, f"mkdir -p {str(PurePosixPath(vps_path).parent)}")
                upload_file(sftp, local_path, vps_path)
                ssh_run(ssh, f"chmod 644 {vps_path}")
                print(f"    [DEPLOYED] {vps_path}")
            else:
                print(f"    [SKIP] {vps_path}")

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 6: CREATE MISSING THEME/BRANDING FILES
    # ═══════════════════════════════════════════════════════════════
    if report["theme_missing"]:
        print(f"\n═══ FIX: Creating {len(report['theme_missing'])} missing theme/branding files ═══")
        theme_script = r'''#!/bin/bash
set +e
# GTK theme
mkdir -p /etc/gtk-3.0
cat > /etc/gtk-3.0/settings.ini << 'GTKEOF'
[Settings]
gtk-theme-name=Arc-Dark
gtk-icon-theme-name=Papirus-Dark
gtk-font-name=Cantarell 10
gtk-cursor-theme-name=Adwaita
gtk-cursor-theme-size=24
gtk-application-prefer-dark-theme=1
gtk-xft-antialias=1
gtk-xft-hinting=1
gtk-xft-hintstyle=hintslight
gtk-xft-rgba=rgb
GTKEOF

# Qt theme
mkdir -p /etc/environment.d
cat > /etc/environment.d/50-titan-qt.conf << 'QTEOF'
QT_QPA_PLATFORMTHEME=gtk3
QT_STYLE_OVERRIDE=adwaita-dark
QTEOF

# Openbox theme
THEME_DIR="/usr/share/themes/TitanDark/openbox-3"
mkdir -p "$THEME_DIR"
cat > "$THEME_DIR/themerc" << 'OBEOF'
window.active.title.bg: flat solid
window.active.title.bg.color: #0e1420
window.active.label.text.color: #00d4ff
window.inactive.title.bg: flat solid
window.inactive.title.bg.color: #0a0e17
window.inactive.label.text.color: #556678
window.active.button.unpressed.bg: flat solid
window.active.button.unpressed.bg.color: #0e1420
window.active.button.unpressed.image.color: #00d4ff
border.width: 1
padding.width: 6
padding.height: 4
menu.title.bg: flat solid
menu.title.bg.color: #0e1420
menu.title.text.color: #00d4ff
menu.items.bg: flat solid
menu.items.bg.color: #0a0e17
menu.items.text.color: #c8d2dc
menu.items.active.bg: flat solid
menu.items.active.bg.color: #00d4ff20
menu.items.active.text.color: #00d4ff
OBEOF

# Vendor override
mkdir -p /etc/dpkg/origins
cat > /etc/dpkg/origins/titanos << 'VEOF'
Vendor: TitanOS
Vendor-URL: https://titan-os.io
Bugs: https://titan-os.io/bugs
Parent: Debian
VEOF
ln -sf /etc/dpkg/origins/titanos /etc/dpkg/origins/default 2>/dev/null

# Camera module config
cat > /etc/modprobe.d/titan-camera.conf << 'CAMEOF'
options v4l2loopback video_nr=2 card_label="Integrated Camera" exclusive_caps=1
CAMEOF

# Kernel blacklist
cat > /etc/modprobe.d/titan-blacklist.conf << 'BLEOF'
blacklist bluetooth
blacklist btusb
blacklist btrtl
blacklist btbcm
blacklist btintel
blacklist firewire-core
blacklist firewire-ohci
blacklist thunderbolt
blacklist nfc
blacklist cramfs
blacklist freevxfs
blacklist jffs2
blacklist hfs
blacklist hfsplus
blacklist udf
blacklist dccp
blacklist sctp
blacklist rds
blacklist tipc
BLEOF

# Titan env
cat > /etc/profile.d/titan-env.sh << 'ENVEOF'
#!/bin/bash
export TITAN_ROOT="/opt/titan"
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/src/core:/opt/titan/src/apps:$PYTHONPATH"
export PATH="/opt/titan/bin:$PATH"
ENVEOF
chmod +x /etc/profile.d/titan-env.sh

# Systemd env
cat > /etc/environment.d/50-titan.conf << 'SENVEOF'
TITAN_ROOT=/opt/titan
PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/src/core:/opt/titan/src/apps
PATH=/opt/titan/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SENVEOF

echo "THEME_FIX_DONE"
'''
        rc, out = ssh_stream(ssh, f"bash << 'FIXEOF'\n{theme_script}\nFIXEOF")

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 7: ENABLE & START SERVICES
    # ═══════════════════════════════════════════════════════════════
    print(f"\n═══ FIX: Enable & Start Services ═══")
    ssh_run(ssh, "systemctl daemon-reload")
    for svc, spec in EXPECTED_SERVICES.items():
        status = report["services_status"].get(svc, {})
        if spec["enable"] and status.get("enabled") != "enabled":
            rc, _, _ = ssh_run(ssh, f"systemctl enable {svc} 2>/dev/null")
            print(f"    [ENABLE] {svc}: {'OK' if rc == 0 else 'SKIP'}")
        if spec["start"] and status.get("active") != "active":
            rc, _, err = ssh_run(ssh, f"systemctl start {svc} 2>/dev/null")
            print(f"    [START]  {svc}: {'OK' if rc == 0 else 'FAIL'}")

    # ═══════════════════════════════════════════════════════════════
    # FIX PHASE 8: APPLY SYSCTL + PERMISSIONS
    # ═══════════════════════════════════════════════════════════════
    print(f"\n═══ FIX: Apply sysctl & permissions ═══")
    perms_script = r'''#!/bin/bash
set +e
# Apply sysctl
sysctl --system 2>/dev/null

# Set permissions on all scripts
find /opt/titan -name "*.py" -exec chmod +x {} \;
find /opt/titan -name "*.sh" -exec chmod +x {} \;
chmod +x /opt/titan/bin/* 2>/dev/null
chmod +x /opt/titan/apps/* 2>/dev/null
chmod +x /opt/titan/src/bin/* 2>/dev/null

# Protect sensitive
chmod 700 /opt/titan/config 2>/dev/null
chmod 700 /opt/titan/vpn 2>/dev/null
chmod 600 /opt/titan/config/titan.env 2>/dev/null
chmod 440 /etc/sudoers.d/titan-ops 2>/dev/null

# Config file perms
chmod 644 /etc/fonts/local.conf 2>/dev/null
chmod 644 /etc/pulse/daemon.conf 2>/dev/null
chmod 644 /etc/nftables.conf 2>/dev/null
chmod 644 /etc/sysctl.d/99-titan-hardening.conf 2>/dev/null
chmod 644 /etc/sysctl.d/99-titan-stealth.conf 2>/dev/null
chmod 644 /etc/udev/rules.d/99-titan-usb.rules 2>/dev/null
chmod +x /etc/profile.d/titan-prompt.sh 2>/dev/null
chmod +x /etc/profile.d/titan-env.sh 2>/dev/null
chmod +x /etc/xdg/openbox/autostart 2>/dev/null

# Desktop entries
chmod 644 /usr/share/applications/titan-*.desktop 2>/dev/null

# Reload
systemctl daemon-reload
udevadm control --reload-rules 2>/dev/null
udevadm trigger 2>/dev/null

echo "PERMS_FIX_DONE"
'''
    rc, out = ssh_stream(ssh, f"bash << 'PERMEOF'\n{perms_script}\nPERMEOF")

    # ═══════════════════════════════════════════════════════════════
    # RECHECK: FINAL AUDIT
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("  FINAL RE-AUDIT")
    print("=" * 72)

    # Re-check apt
    rc, installed_raw2, _ = ssh_run(ssh, "dpkg-query -W -f='${Package}\\n' 2>/dev/null", timeout=30)
    installed_apt2 = set(installed_raw2.splitlines()) if rc == 0 else set()
    apt_still_missing = [p for p in EXPECTED_APT_PACKAGES if p not in installed_apt2]

    # Re-check pip
    rc, pip_raw2, _ = ssh_run(ssh, "pip3 list --format=columns 2>/dev/null | tail -n+3 | awk '{print tolower($1)}'", timeout=30)
    installed_pip2 = set(pip_raw2.splitlines()) if rc == 0 else set()
    installed_pip2_norm = set()
    for p in installed_pip2:
        installed_pip2_norm.add(p.lower().replace("-", "_"))
        installed_pip2_norm.add(p.lower().replace("_", "-"))
        installed_pip2_norm.add(p.lower())
    pip_still_missing = []
    for pkg in EXPECTED_PIP_PACKAGES:
        n1 = pkg.lower().replace("-", "_")
        n2 = pkg.lower().replace("_", "-")
        if n1 not in installed_pip2_norm and n2 not in installed_pip2_norm and pkg.lower() not in installed_pip2_norm:
            pip_still_missing.append(pkg)

    # Re-check tools
    tools_still_missing = []
    for tool in EXPECTED_TOOLS:
        rc, path, _ = ssh_run(ssh, f"command -v {tool} 2>/dev/null || true", timeout=10)
        if not path.strip():
            tools_still_missing.append(tool)

    # Re-check configs
    configs_still_missing = []
    for vps_path in EXPECTED_CONFIGS:
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc != 0:
            configs_still_missing.append(vps_path)

    # Re-check units
    units_still_missing = []
    for vps_path in EXPECTED_UNIT_FILES:
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc != 0:
            units_still_missing.append(vps_path)

    # Re-check desktop
    desktop_still_missing = []
    for vps_path in EXPECTED_DESKTOP_ENTRIES:
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc != 0:
            desktop_still_missing.append(vps_path)

    # Re-check themes
    theme_still_missing = []
    for vps_path in EXPECTED_THEME_FILES:
        rc, _, _ = ssh_run(ssh, f"test -e {vps_path}", timeout=10)
        if rc != 0:
            theme_still_missing.append(vps_path)

    # Services final status
    print("\n  Service Status:")
    for svc in EXPECTED_SERVICES:
        _, active, _ = ssh_run(ssh, f"systemctl is-active {svc} 2>/dev/null || echo unknown", timeout=10)
        _, enabled, _ = ssh_run(ssh, f"systemctl is-enabled {svc} 2>/dev/null || echo unknown", timeout=10)
        mark = "+" if active.strip() == "active" else ("~" if enabled.strip() == "enabled" else "-")
        print(f"    [{mark}] {svc}: active={active.strip()}, enabled={enabled.strip()}")

    # Final counts
    total_apt = len(EXPECTED_APT_PACKAGES)
    total_pip = len(EXPECTED_PIP_PACKAGES)
    total_tools = len(EXPECTED_TOOLS)
    total_configs = len(EXPECTED_CONFIGS)
    total_units = len(EXPECTED_UNIT_FILES)
    total_desktop = len(EXPECTED_DESKTOP_ENTRIES)
    total_theme = len(EXPECTED_THEME_FILES)

    print(f"\n  FINAL SCOREBOARD:")
    print(f"    APT packages:    {total_apt - len(apt_still_missing)}/{total_apt}  (missing: {len(apt_still_missing)})")
    print(f"    Pip packages:    {total_pip - len(pip_still_missing)}/{total_pip}  (missing: {len(pip_still_missing)})")
    print(f"    CLI tools:       {total_tools - len(tools_still_missing)}/{total_tools}  (missing: {len(tools_still_missing)})")
    print(f"    Config files:    {total_configs - len(configs_still_missing)}/{total_configs}  (missing: {len(configs_still_missing)})")
    print(f"    Systemd units:   {total_units - len(units_still_missing)}/{total_units}  (missing: {len(units_still_missing)})")
    print(f"    Desktop entries: {total_desktop - len(desktop_still_missing)}/{total_desktop}  (missing: {len(desktop_still_missing)})")
    print(f"    Theme/branding:  {total_theme - len(theme_still_missing)}/{total_theme}  (missing: {len(theme_still_missing)})")

    if apt_still_missing:
        print(f"\n  Still missing APT: {', '.join(apt_still_missing[:20])}")
    if pip_still_missing:
        print(f"  Still missing Pip: {', '.join(pip_still_missing[:20])}")
    if tools_still_missing:
        print(f"  Still missing tools: {', '.join(tools_still_missing)}")
    if configs_still_missing:
        print(f"  Still missing configs: {', '.join(configs_still_missing)}")

    grand_total = total_apt + total_pip + total_tools + total_configs + total_units + total_desktop + total_theme
    grand_present = grand_total - len(apt_still_missing) - len(pip_still_missing) - len(tools_still_missing) - len(configs_still_missing) - len(units_still_missing) - len(desktop_still_missing) - len(theme_still_missing)
    pct = (grand_present / grand_total * 100) if grand_total > 0 else 0

    print(f"\n  ══════════════════════════════════════════")
    print(f"  TITAN OS COMPLETION: {grand_present}/{grand_total} ({pct:.1f}%)")
    print(f"  ══════════════════════════════════════════")

    # Save report
    report_path = LOCAL_ROOT / "titan_audit_report.json"
    final_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "apt": {"expected": total_apt, "present": total_apt - len(apt_still_missing), "missing": apt_still_missing},
        "pip": {"expected": total_pip, "present": total_pip - len(pip_still_missing), "missing": pip_still_missing},
        "tools": {"expected": total_tools, "present": total_tools - len(tools_still_missing), "missing": tools_still_missing},
        "configs": {"expected": total_configs, "present": total_configs - len(configs_still_missing), "missing": configs_still_missing},
        "units": {"expected": total_units, "present": total_units - len(units_still_missing), "missing": units_still_missing},
        "desktop": {"expected": total_desktop, "present": total_desktop - len(desktop_still_missing), "missing": desktop_still_missing},
        "theme": {"expected": total_theme, "present": total_theme - len(theme_still_missing), "missing": theme_still_missing},
        "completion": f"{pct:.1f}%",
    }
    with open(report_path, "w") as f:
        json.dump(final_report, f, indent=2)
    print(f"\n  Report saved: {report_path}")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
