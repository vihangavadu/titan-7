#!/usr/bin/env python3
"""
TITAN OS - Full Repo-to-VPS Sync
Compares local repo tree against VPS /opt/titan and uploads ALL missing files.
Nothing is skipped - every script, config, doc, ISO file, etc.
"""

import json
import os
import sys
import time
from pathlib import Path, PurePosixPath

import paramiko

VPS_IP = "72.62.72.48"
VPS_USER = "root"
VPS_PASS = "Chilaw@123@llm"
VPS_ROOT = "/opt/titan"
LOCAL_ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = Path.home() / ".ssh" / "id_ed25519"

# Skip these local dirs (not deployable or internal-only)
SKIP_DIRS = {".git", ".idea", ".venv", ".windsurf", "__pycache__", "node_modules"}
SKIP_SUFFIXES = (".pyc", ".pyo")


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


def list_local_files():
    """List every file in the local repo (relative paths)."""
    files = {}
    for root, dirs, filenames in os.walk(LOCAL_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(SKIP_SUFFIXES):
                continue
            full = Path(root) / f
            rel = full.relative_to(LOCAL_ROOT).as_posix()
            try:
                size = full.stat().st_size
            except OSError:
                size = 0
            files[rel] = {"size": size, "local_path": str(full)}
    return files


def list_remote_files(ssh):
    """List every file on VPS under /opt/titan (relative paths)."""
    rc, out, err = ssh_run(ssh, f"find {VPS_ROOT} -type f -printf '%P\\t%s\\n'", timeout=180)
    files = {}
    if rc != 0 or not out:
        return files
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            rel_path = parts[0].strip()
            try:
                size = int(parts[1].strip())
            except ValueError:
                size = -1
            files[rel_path] = {"size": size}
    return files


def sftp_mkdir_p(sftp, remote_dir):
    """Recursively create remote directories."""
    dirs_to_create = []
    current = remote_dir
    while current and current != "/":
        try:
            sftp.stat(current)
            break
        except FileNotFoundError:
            dirs_to_create.append(current)
            current = str(PurePosixPath(current).parent)
    
    for d in reversed(dirs_to_create):
        try:
            sftp.mkdir(d)
        except IOError:
            pass


def upload_files(ssh, missing_files, local_files):
    """Upload all missing files to VPS."""
    sftp = ssh.open_sftp()
    uploaded = 0
    failed = []
    total = len(missing_files)
    total_bytes = 0

    for i, rel_path in enumerate(sorted(missing_files), 1):
        info = local_files[rel_path]
        local_path = info["local_path"]
        remote_path = f"{VPS_ROOT}/{rel_path}"
        remote_dir = str(PurePosixPath(remote_path).parent)

        try:
            sftp_mkdir_p(sftp, remote_dir)
            sftp.put(local_path, remote_path)
            uploaded += 1
            total_bytes += info["size"]
            if i % 50 == 0 or i == total:
                pct = (i / total) * 100
                print(f"  [{i}/{total}] {pct:.0f}% uploaded ({uploaded} ok, {len(failed)} fail)")
        except Exception as e:
            failed.append((rel_path, str(e)[:100]))

    sftp.close()
    return uploaded, failed, total_bytes


def main():
    print("=" * 72)
    print("TITAN OS - Full Repo-to-VPS Sync")
    print("=" * 72)
    print(f"Local:  {LOCAL_ROOT}")
    print(f"Remote: {VPS_USER}@{VPS_IP}:{VPS_ROOT}")
    print()

    # Phase 1: Scan local repo
    print("[Phase 1] Scanning local repo tree...")
    t0 = time.time()
    local_files = list_local_files()
    print(f"  Local files: {len(local_files):,}")
    print(f"  Scan time: {time.time()-t0:.1f}s")

    # Phase 2: Connect and scan VPS
    print("\n[Phase 2] Connecting to VPS and scanning remote tree...")
    ssh = get_ssh()
    t0 = time.time()
    remote_files = list_remote_files(ssh)
    print(f"  Remote files: {len(remote_files):,}")
    print(f"  Scan time: {time.time()-t0:.1f}s")

    # Phase 3: Compute diff
    print("\n[Phase 3] Computing diff...")
    local_set = set(local_files.keys())
    remote_set = set(remote_files.keys())

    missing_on_vps = local_set - remote_set
    extra_on_vps = remote_set - local_set
    common = local_set & remote_set

    # Check size mismatches in common files
    size_mismatch = []
    for rel in common:
        local_size = local_files[rel]["size"]
        remote_size = remote_files[rel]["size"]
        if local_size != remote_size:
            size_mismatch.append(rel)

    print(f"  Files in local repo:    {len(local_set):,}")
    print(f"  Files on VPS:           {len(remote_set):,}")
    print(f"  Common (both):          {len(common):,}")
    print(f"  MISSING on VPS:         {len(missing_on_vps):,}")
    print(f"  Extra on VPS only:      {len(extra_on_vps):,}")
    print(f"  Size mismatch (stale):  {len(size_mismatch):,}")

    # Group missing files by top-level directory
    print("\n  Missing files by folder:")
    folder_counts = {}
    for rel in missing_on_vps:
        top = rel.split("/")[0] if "/" in rel else "(root)"
        folder_counts[top] = folder_counts.get(top, 0) + 1
    for folder, count in sorted(folder_counts.items(), key=lambda x: -x[1]):
        print(f"    {folder:<30} {count:>5} files missing")

    # Group size mismatches by folder
    if size_mismatch:
        print(f"\n  Stale/outdated files by folder:")
        stale_folders = {}
        for rel in size_mismatch:
            top = rel.split("/")[0] if "/" in rel else "(root)"
            stale_folders[top] = stale_folders.get(top, 0) + 1
        for folder, count in sorted(stale_folders.items(), key=lambda x: -x[1]):
            print(f"    {folder:<30} {count:>5} files outdated")

    # Combine: missing + stale = need upload
    need_upload = missing_on_vps | set(size_mismatch)
    total_upload_size = sum(local_files[r]["size"] for r in need_upload)

    print(f"\n  TOTAL files to upload: {len(need_upload):,}")
    print(f"  TOTAL upload size:     {total_upload_size / (1024*1024):.1f} MB")

    if not need_upload:
        print("\n  VPS is already in sync with repo!")
        ssh.close()
        return

    # Phase 4: Upload
    print(f"\n[Phase 4] Uploading {len(need_upload):,} files to VPS...")
    t0 = time.time()
    uploaded, failed, total_bytes = upload_files(ssh, need_upload, local_files)
    elapsed = time.time() - t0
    print(f"\n  Uploaded: {uploaded:,} files ({total_bytes/(1024*1024):.1f} MB)")
    print(f"  Failed:   {len(failed):,}")
    print(f"  Time:     {elapsed:.1f}s")

    if failed:
        print("\n  Failed files:")
        for path, err in failed[:20]:
            print(f"    {path}: {err}")
        if len(failed) > 20:
            print(f"    ... and {len(failed)-20} more")

    # Phase 5: Set permissions
    print("\n[Phase 5] Setting permissions...")
    ssh_run(ssh, f"find {VPS_ROOT} -name '*.sh' -exec chmod +x {{}} \\;")
    ssh_run(ssh, f"find {VPS_ROOT} -name '*.py' -exec chmod +x {{}} \\;")
    ssh_run(ssh, f"find {VPS_ROOT}/src/bin -type f -exec chmod +x {{}} \\; 2>/dev/null")
    print("  [+] Permissions set")

    # Phase 6: Re-verify
    print("\n[Phase 6] Re-verifying...")
    remote_files_after = list_remote_files(ssh)
    local_set_2 = set(local_files.keys())
    remote_set_2 = set(remote_files_after.keys())
    still_missing = local_set_2 - remote_set_2

    print(f"  Local files:   {len(local_set_2):,}")
    print(f"  Remote files:  {len(remote_set_2):,}")
    print(f"  Still missing: {len(still_missing):,}")

    if still_missing:
        print("\n  Still missing files (sample):")
        for rel in sorted(still_missing)[:15]:
            print(f"    {rel}")

    # Save report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "local_root": str(LOCAL_ROOT),
        "remote_root": VPS_ROOT,
        "local_file_count": len(local_files),
        "remote_file_count_before": len(remote_files),
        "remote_file_count_after": len(remote_files_after),
        "missing_before_upload": len(missing_on_vps),
        "stale_before_upload": len(size_mismatch),
        "total_uploaded": uploaded,
        "total_failed": len(failed),
        "still_missing": len(still_missing),
        "missing_by_folder": folder_counts,
        "failed_files": [{"path": p, "error": e} for p, e in failed],
        "still_missing_files": sorted(still_missing)[:50],
    }
    report_path = LOCAL_ROOT / "vps_sync_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  Report saved: {report_path}")

    ssh.close()

    print("\n" + "=" * 72)
    if len(still_missing) == 0:
        print("SUCCESS: VPS now matches repo tree completely!")
    else:
        print(f"PARTIAL: {len(still_missing)} files still missing (check report)")
    print("=" * 72)


if __name__ == "__main__":
    main()
