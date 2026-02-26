#!/usr/bin/env python3
"""
TITAN OS - V9.4 Comprehensive VPS Verifier

Purpose:
- Analyze the local codebase folder-by-folder (.github -> training)
- Verify the VPS has the same Titan codebase structure
- Verify runtime stack (services, tools, API, Waydroid, GUI/XRDP, training files)
- Generate machine-readable and human-readable reports

Usage:
  python scripts/verify_vps_everything.py \
    --host 72.62.72.48 --user root --password "$env:TITAN_VPS_PASSWORD"

  # Key-based auth (recommended after first run)
  python scripts/verify_vps_everything.py --host 72.62.72.48 --user root
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import paramiko
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "paramiko is required. Install with: pip install paramiko"
    ) from exc


IGNORE_DIRS = {
    ".git",
    ".idea",
    ".venv",
    ".windsurf",
    "__pycache__",
    "node_modules",
}
IGNORE_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".swp",
)

# User asked for full scan "from github to training"
DEFAULT_MIRROR_DIRS = [
    ".github",
    "config",
    "docs",
    "hostinger-dev",
    "iso",
    "modelfiles",
    "plans",
    "scripts",
    "src",
    "tests",
    "training",
]

CRITICAL_REMOTE_FILES = [
    "core/titan_api.py",
    "core/integration_bridge.py",
    "core/titan_session.py",
    "core/kyc_core.py",
    "core/kyc_enhanced.py",
    "core/kyc_voice_engine.py",
    "core/waydroid_sync.py",
    "core/cockpit_daemon.py",
    "apps/titan_dev_hub.py",
    "apps/app_kyc.py",
    "apps/titan_launcher.py",
    "apps/app_unified.py",
    "apps/app_genesis.py",
    "apps/app_cerberus.py",
    "scripts/setup_waydroid_android.sh",
    "scripts/deploy_android_vm.sh",
]

IMPORT_SMOKE_MODULES = [
    "integration_bridge",
    "titan_session",
    "titan_api",
    "kyc_core",
    "kyc_enhanced",
    "kyc_voice_engine",
    "waydroid_sync",
    "cockpit_daemon",
]

REQUIRED_SERVICES = [
    "redis-server",
    "ollama",
    "xray",
    "ntfy",
    "titan-dev-hub",
    "titan-api",
    "xrdp",
]

OPTIONAL_SERVICES = [
    "lightdm",
    "lucid-console",
    "lucid-ebpf",
    "lucid-titan",
    "titan-dns",
    "titan-first-boot",
    "titan-patch-bridge",
    "waydroid-container",
    "titan-waydroid",
]

SERVICES_TO_CHECK = REQUIRED_SERVICES + OPTIONAL_SERVICES

TOOLS_TO_CHECK = [
    "python3",
    "pip3",
    "git",
    "curl",
    "ffmpeg",
    "node",
    "npm",
    "redis-cli",
    "ollama",
    "waydroid",
    "xrdp",
    "Xvnc",
]

API_ENDPOINTS = [
    "http://127.0.0.1:5000/api/v1/health",
    "http://127.0.0.1:5000/api/v1/modules",
    "http://127.0.0.1:5000/api/v1/android/status",
    "http://127.0.0.1:8877/api/health",
]


class SSHRunner:
    def __init__(
        self,
        host: str,
        user: str,
        password: str | None,
        key_file: str | None,
        timeout: int,
    ) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.key_file = key_file
        self.timeout = timeout
        self.client: paramiko.SSHClient | None = None

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {
            "hostname": self.host,
            "username": self.user,
            "timeout": self.timeout,
            "look_for_keys": True,
            "allow_agent": True,
        }

        if self.key_file and Path(self.key_file).exists():
            kwargs["key_filename"] = self.key_file

        if self.password:
            kwargs["password"] = self.password

        client.connect(**kwargs)
        self.client = client

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None

    def run(self, cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
        if not self.client:
            raise RuntimeError("SSH client not connected")
        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        rc = stdout.channel.recv_exit_status()
        return rc, out, err


def count_local_files(path: Path) -> int:
    if not path.exists():
        return -1
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file_name in files:
            if file_name.endswith(IGNORE_SUFFIXES):
                continue
            total += 1
    return total


def count_remote_files(ssh: SSHRunner, remote_path: str) -> int:
    q = shlex.quote(remote_path)
    cmd = f"if [ -d {q} ]; then find {q} -type f | wc -l; else echo -1; fi"
    rc, out, _ = ssh.run(cmd)
    if rc != 0:
        return -1
    try:
        return int(out.strip())
    except ValueError:
        return -1


def check_remote_exists(ssh: SSHRunner, remote_path: str) -> bool:
    q = shlex.quote(remote_path)
    rc, _, _ = ssh.run(f"test -e {q}")
    return rc == 0


def remote_service_state(
    ssh: SSHRunner,
    service: str,
    *,
    required: bool,
) -> Dict[str, object]:
    q = shlex.quote(service)
    _, active, _ = ssh.run(f"systemctl is-active {q} 2>/dev/null || true")
    _, enabled, _ = ssh.run(f"systemctl is-enabled {q} 2>/dev/null || true")
    return {
        "service": service,
        "required": required,
        "active": active.strip() or "unknown",
        "enabled": enabled.strip() or "unknown",
    }


def remote_tool_state(ssh: SSHRunner, tool: str) -> Dict[str, str]:
    q = shlex.quote(tool)
    rc, out, _ = ssh.run(f"command -v {q} 2>/dev/null || true")
    return {
        "tool": tool,
        "present": bool(out.strip()) and rc == 0,
        "path": out.strip() if out.strip() else "",
    }


def run_remote_python_syntax_check(ssh: SSHRunner, remote_root: str) -> Dict[str, object]:
    root_repr = repr(remote_root)
    script = f"""
import json
import os
import py_compile

root = {root_repr}
ignore_dirs = {sorted(IGNORE_DIRS)!r}
ignore_suffixes = {IGNORE_SUFFIXES!r}

checked = 0
failed = []

for base, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for name in files:
        if not name.endswith('.py'):
            continue
        if name.endswith(ignore_suffixes):
            continue
        path = os.path.join(base, name)
        checked += 1
        try:
            py_compile.compile(path, doraise=True)
        except Exception as exc:
            failed.append({{'file': path, 'error': str(exc)[:200]}})

print(json.dumps({{'checked': checked, 'failed': failed}}))
"""
    cmd = f"python3 - <<'PY'\n{script}\nPY"
    rc, out, err = ssh.run(cmd, timeout=300)
    if rc != 0 or not out:
        return {"checked": 0, "failed": [{"file": "<runner>", "error": err or "syntax check failed"}]}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"checked": 0, "failed": [{"file": "<decode>", "error": out[:200]}]}


def run_remote_import_smoke(ssh: SSHRunner, remote_root: str) -> Dict[str, object]:
    root_repr = repr(remote_root)
    modules_repr = repr(IMPORT_SMOKE_MODULES)
    script = f"""
import importlib
import json
import os
import sys

root = {root_repr}
mods = {modules_repr}

sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'core'))
sys.path.insert(0, os.path.join(root, 'apps'))
sys.path.insert(0, os.path.join(root, 'src', 'core'))
sys.path.insert(0, os.path.join(root, 'src', 'apps'))

results = []
for name in mods:
    try:
        importlib.import_module(name)
        results.append({{'module': name, 'ok': True, 'error': ''}})
    except Exception as exc:
        results.append({{'module': name, 'ok': False, 'error': str(exc)[:220]}})

print(json.dumps(results))
"""
    cmd = f"python3 - <<'PY'\n{script}\nPY"
    rc, out, err = ssh.run(cmd, timeout=180)
    if rc != 0 or not out:
        return {"results": [], "error": err or "import smoke failed"}
    try:
        return {"results": json.loads(out), "error": ""}
    except json.JSONDecodeError:
        return {"results": [], "error": out[:220]}


def run_api_checks(ssh: SSHRunner) -> List[Dict[str, object]]:
    checks = []
    for endpoint in API_ENDPOINTS:
        q = shlex.quote(endpoint)
        cmd = (
            "curl -sS -o /tmp/titan_verify_api.out -w '%{http_code}' "
            f"--max-time 6 {q} || true"
        )
        _, code, _ = ssh.run(cmd)
        _, body, _ = ssh.run("head -c 220 /tmp/titan_verify_api.out 2>/dev/null || true")
        code = (code or "").strip()
        checks.append(
            {
                "endpoint": endpoint,
                "http_code": code,
                "ok": code.startswith("2"),
                "sample": body,
            }
        )
    return checks


def run_waydroid_checks(ssh: SSHRunner) -> Dict[str, object]:
    result: Dict[str, object] = {}

    _, waydroid_bin, _ = ssh.run("command -v waydroid 2>/dev/null || true")
    result["installed"] = bool(waydroid_bin.strip())
    result["binary"] = waydroid_bin.strip()

    _, binder_list, _ = ssh.run("ls /dev/*binder* 2>/dev/null || true")
    result["binder_nodes"] = [line.strip() for line in binder_list.splitlines() if line.strip()]

    _, status, _ = ssh.run("waydroid status 2>/dev/null || true")
    result["status"] = status

    image_paths = [
        "/var/lib/waydroid/images/system.img",
        "/var/lib/waydroid/images/vendor.img",
    ]
    image_state = {}
    for path in image_paths:
        image_state[path] = check_remote_exists(ssh, path)
    result["images"] = image_state

    return result


def run_gui_checks(ssh: SSHRunner) -> Dict[str, object]:
    result: Dict[str, object] = {}

    _, xrdp_bin, _ = ssh.run("command -v xrdp 2>/dev/null || true")
    result["xrdp_installed"] = bool(xrdp_bin.strip())
    result["xrdp_binary"] = xrdp_bin.strip()

    result["xrdp_startwm_exists"] = check_remote_exists(ssh, "/etc/xrdp/startwm.sh")
    _, xfce_marker, _ = ssh.run(
        "grep -q 'startxfce4' /etc/xrdp/startwm.sh 2>/dev/null && echo yes || echo no"
    )
    result["xrdp_startwm_xfce"] = xfce_marker.strip() == "yes"

    _, user_exists, _ = ssh.run("id -u user >/dev/null 2>&1 && echo yes || echo no")
    result["desktop_user_present"] = user_exists.strip() == "yes"

    _, listeners, _ = ssh.run("ss -ltn 2>/dev/null | grep -c ':3389' || true")
    try:
        listener_count = int((listeners or "0").strip())
    except ValueError:
        listener_count = 0
    result["xrdp_listener_count"] = listener_count
    result["xrdp_port_listening"] = listener_count > 0

    return result


def scan_folder_parity(
    ssh: SSHRunner,
    local_root: Path,
    remote_root: str,
    mirror_dirs: List[str],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    for rel in mirror_dirs:
        local_path = local_root / rel
        remote_path = f"{remote_root.rstrip('/')}/{rel}"

        local_count = count_local_files(local_path)
        remote_count = count_remote_files(ssh, remote_path)

        if local_count < 0:
            status = "skip"
            note = "local missing"
        elif remote_count < 0:
            status = "fail"
            note = "remote missing"
        elif local_count == remote_count:
            status = "pass"
            note = "exact match"
        elif local_count > 0 and remote_count >= int(local_count * 0.8):
            status = "warn"
            note = "count drift (>=80% mirrored)"
        else:
            status = "fail"
            note = "count drift (<80% mirrored)"

        rows.append(
            {
                "folder": rel,
                "local_files": local_count,
                "remote_files": remote_count,
                "status": status,
                "note": note,
            }
        )

    return rows


def summarize_status(report: Dict[str, object]) -> Dict[str, int]:
    pass_count = 0
    warn_count = 0
    fail_count = 0

    for row in report["folder_parity"]:
        if row["status"] == "pass":
            pass_count += 1
        elif row["status"] == "warn":
            warn_count += 1
        elif row["status"] == "fail":
            fail_count += 1

    for row in report["critical_files"]:
        if row["present"]:
            pass_count += 1
        else:
            fail_count += 1

    syntax_failed = len(report["python_syntax"].get("failed", []))
    if syntax_failed == 0:
        pass_count += 1
    else:
        fail_count += 1

    imports = report["imports"].get("results", [])
    import_fails = sum(1 for item in imports if not item.get("ok"))
    if import_fails == 0:
        pass_count += 1
    else:
        fail_count += 1

    for service in report["services"]:
        is_required = bool(service.get("required", True))
        if service["active"] == "active":
            pass_count += 1
        elif is_required:
            if service["active"] in {"inactive", "failed", "unknown"}:
                fail_count += 1
            else:
                warn_count += 1
        else:
            warn_count += 1

    for tool in report["tools"]:
        if tool["present"]:
            pass_count += 1
        else:
            fail_count += 1

    for api in report["api"]:
        if api["ok"]:
            pass_count += 1
        elif api["http_code"] in {"000", "", "curl_error"}:
            warn_count += 1
        else:
            fail_count += 1

    waydroid = report["waydroid"]
    if waydroid.get("installed"):
        pass_count += 1
    else:
        fail_count += 1

    images = waydroid.get("images", {})
    if images and all(images.values()):
        pass_count += 1
    else:
        warn_count += 1

    gui = report.get("gui", {})
    if gui.get("xrdp_installed"):
        pass_count += 1
    else:
        fail_count += 1

    if gui.get("xrdp_startwm_exists") and gui.get("xrdp_startwm_xfce"):
        pass_count += 1
    else:
        fail_count += 1

    if gui.get("desktop_user_present"):
        pass_count += 1
    else:
        warn_count += 1

    if gui.get("xrdp_port_listening"):
        pass_count += 1
    else:
        warn_count += 1

    return {"pass": pass_count, "warn": warn_count, "fail": fail_count}


def to_markdown(report: Dict[str, object]) -> str:
    summary = report["summary"]
    lines = []
    lines.append("# TITAN VPS Comprehensive Verification Report")
    lines.append("")
    lines.append(f"- Timestamp: `{report['meta']['timestamp']}`")
    lines.append(f"- Host: `{report['meta']['host']}`")
    lines.append(f"- Remote root: `{report['meta']['remote_root']}`")
    lines.append(f"- Result: **PASS={summary['pass']} WARN={summary['warn']} FAIL={summary['fail']}**")
    lines.append("")

    lines.append("## Folder parity (.github -> training)")
    lines.append("")
    lines.append("| Folder | Local Files | Remote Files | Status | Note |")
    lines.append("|---|---:|---:|---|---|")
    for row in report["folder_parity"]:
        lines.append(
            f"| `{row['folder']}` | {row['local_files']} | {row['remote_files']} | {row['status'].upper()} | {row['note']} |"
        )

    lines.append("")
    lines.append("## Critical files")
    lines.append("")
    for row in report["critical_files"]:
        mark = "OK" if row["present"] else "MISSING"
        lines.append(f"- [{mark}] `{row['path']}`")

    lines.append("")
    lines.append("## Python syntax")
    lines.append("")
    lines.append(f"- Checked: `{report['python_syntax'].get('checked', 0)}`")
    lines.append(f"- Failed: `{len(report['python_syntax'].get('failed', []))}`")

    lines.append("")
    lines.append("## Services")
    lines.append("")
    for svc in report["services"]:
        required = "required" if svc.get("required", True) else "optional"
        lines.append(
            f"- `{svc['service']}` ({required}): active=`{svc['active']}` enabled=`{svc['enabled']}`"
        )

    lines.append("")
    lines.append("## Tools")
    lines.append("")
    for tool in report["tools"]:
        mark = "OK" if tool["present"] else "MISSING"
        lines.append(f"- [{mark}] `{tool['tool']}` {tool['path']}")

    lines.append("")
    lines.append("## Waydroid")
    lines.append("")
    lines.append(f"- Installed: `{report['waydroid'].get('installed')}`")
    lines.append(f"- Binder nodes: `{', '.join(report['waydroid'].get('binder_nodes', []))}`")
    for img_path, present in report["waydroid"].get("images", {}).items():
        lines.append(f"- `{img_path}`: `{present}`")

    lines.append("")
    lines.append("## GUI + XRDP")
    lines.append("")
    lines.append(f"- XRDP binary installed: `{report['gui'].get('xrdp_installed')}`")
    lines.append(f"- XRDP startwm exists: `{report['gui'].get('xrdp_startwm_exists')}`")
    lines.append(f"- XRDP XFCE wiring: `{report['gui'].get('xrdp_startwm_xfce')}`")
    lines.append(f"- Desktop user present (`user`): `{report['gui'].get('desktop_user_present')}`")
    lines.append(f"- XRDP listener count (:3389): `{report['gui'].get('xrdp_listener_count')}`")

    lines.append("")
    lines.append("## API checks")
    lines.append("")
    for api in report["api"]:
        lines.append(f"- `{api['endpoint']}` -> `{api['http_code']}`")

    return "\n".join(lines) + "\n"


def print_console_summary(report: Dict[str, object]) -> None:
    print("=" * 72)
    print("TITAN V9.4 - COMPREHENSIVE VPS VERIFIER")
    print("=" * 72)
    print(f"Host: {report['meta']['host']}")
    print(f"Remote root: {report['meta']['remote_root']}")
    print(f"Timestamp: {report['meta']['timestamp']}")
    print("-" * 72)

    print("Folder parity:")
    for row in report["folder_parity"]:
        print(
            f"  [{row['status'].upper():4}] {row['folder']:<12} "
            f"local={row['local_files']:<6} remote={row['remote_files']:<6} {row['note']}"
        )

    missing = [row["path"] for row in report["critical_files"] if not row["present"]]
    print("-" * 72)
    print(f"Critical files missing: {len(missing)}")
    if missing:
        for path in missing[:12]:
            print(f"  - {path}")

    syntax_failed = report["python_syntax"].get("failed", [])
    print("-" * 72)
    print(f"Python syntax checked: {report['python_syntax'].get('checked', 0)}")
    print(f"Python syntax failures: {len(syntax_failed)}")

    import_results = report["imports"].get("results", [])
    import_fail = [m for m in import_results if not m.get("ok")]
    print(f"Import smoke failures: {len(import_fail)}")

    gui = report.get("gui", {})
    print(f"XRDP installed: {gui.get('xrdp_installed')}  listening(:3389): {gui.get('xrdp_port_listening')}")

    summary = report["summary"]
    print("-" * 72)
    print(
        f"FINAL: PASS={summary['pass']} WARN={summary['warn']} FAIL={summary['fail']}"
    )
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TITAN codebase + VPS comprehensive verifier"
    )
    parser.add_argument("--host", default="72.62.72.48")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=os.environ.get("TITAN_VPS_PASSWORD", ""))
    parser.add_argument("--key-file", default=str(Path.home() / ".ssh" / "id_ed25519"))
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--local-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--remote-root", default="/opt/titan")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on WARN/FAIL")
    parser.add_argument("--report-json", default="")
    parser.add_argument("--report-md", default="")
    args = parser.parse_args()

    local_root = Path(args.local_root).resolve()
    if not local_root.exists():
        print(f"Local root not found: {local_root}", file=sys.stderr)
        return 2

    timestamp = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    report_json = args.report_json or str(local_root / f"vps_verify_report_{timestamp}.json")
    report_md = args.report_md or str(local_root / f"vps_verify_report_{timestamp}.md")

    ssh = SSHRunner(
        host=args.host,
        user=args.user,
        password=args.password,
        key_file=args.key_file,
        timeout=args.timeout,
    )

    try:
        ssh.connect()
    except Exception as exc:
        print(f"SSH connection failed: {exc}", file=sys.stderr)
        return 2

    try:
        folder_parity = scan_folder_parity(
            ssh,
            local_root=local_root,
            remote_root=args.remote_root,
            mirror_dirs=DEFAULT_MIRROR_DIRS,
        )

        critical_files = []
        for rel in CRITICAL_REMOTE_FILES:
            remote_path = f"{args.remote_root.rstrip('/')}/{rel}"
            critical_files.append(
                {
                    "path": remote_path,
                    "present": check_remote_exists(ssh, remote_path),
                }
            )

        syntax = run_remote_python_syntax_check(ssh, args.remote_root)
        imports = run_remote_import_smoke(ssh, args.remote_root)

        services = [
            *[remote_service_state(ssh, svc, required=True) for svc in REQUIRED_SERVICES],
            *[remote_service_state(ssh, svc, required=False) for svc in OPTIONAL_SERVICES],
        ]
        tools = [remote_tool_state(ssh, tool) for tool in TOOLS_TO_CHECK]
        api = run_api_checks(ssh)
        waydroid = run_waydroid_checks(ssh)
        gui = run_gui_checks(ssh)

        report = {
            "meta": {
                "timestamp": timestamp,
                "host": args.host,
                "user": args.user,
                "remote_root": args.remote_root,
                "local_root": str(local_root),
            },
            "folder_parity": folder_parity,
            "critical_files": critical_files,
            "python_syntax": syntax,
            "imports": imports,
            "services": services,
            "tools": tools,
            "api": api,
            "waydroid": waydroid,
            "gui": gui,
        }
        report["summary"] = summarize_status(report)

        Path(report_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        Path(report_md).write_text(to_markdown(report), encoding="utf-8")

        print_console_summary(report)
        print(f"JSON report: {report_json}")
        print(f"MD report:   {report_md}")

        if args.strict:
            if report["summary"]["fail"] > 0 or report["summary"]["warn"] > 0:
                return 1

        return 0 if report["summary"]["fail"] == 0 else 1

    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
