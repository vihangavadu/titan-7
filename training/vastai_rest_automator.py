#!/usr/bin/env python3
# VASTAI REST AUTOMATOR v2 — rebuilt from official API docs
# Endpoints referenced:
#   POST /api/v0/bundles/              (search offers)
#   PUT  /api/v0/asks/{id}/            (create instance)
#   GET  /api/v0/instances/            (list instances)
#   POST /api/v0/instances/{id}/ssh/   (attach ssh key)
#   DELETE /api/v0/instances/{id}/     (destroy instance)
# Auth: Authorization: Bearer <API_KEY>

import sys
import json
import time
import shlex
import subprocess
import argparse
from pathlib import Path

try:
    import requests
except ImportError:
    print("[!] ERROR: 'requests' module missing. Run: pip3 install requests")
    sys.exit(1)

# ── CONFIG ──────────────────────────────────────────────────────────
API_KEY   = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
BASE_URL  = "https://console.vast.ai/api/v0"
IMAGE     = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"
VPS_IP    = "72.62.72.48"
HTTP_PORT = 8888
SSH_KEY   = "/root/.ssh/id_rsa"
OUTPUT_DIR = Path("/opt/titan/training/vastai_output")

# ── API LAYER ───────────────────────────────────────────────────────
def api(method, endpoint, payload=None):
    """Send an authenticated request to the Vast.ai REST API."""
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        r = {
            "GET":    lambda: requests.get(url, headers=headers, timeout=30),
            "POST":   lambda: requests.post(url, headers=headers, json=payload, timeout=30),
            "PUT":    lambda: requests.put(url, headers=headers, json=payload, timeout=30),
            "DELETE": lambda: requests.delete(url, headers=headers, timeout=30),
        }[method]()
        if r.status_code in (200, 201):
            return r.json()
        print(f"[-] API {r.status_code} on {method} {endpoint}: {r.text[:300]}")
        return None
    except Exception as e:
        print(f"[!] Exception {method} {endpoint}: {e}")
        return None

# ── SEARCH ──────────────────────────────────────────────────────────
def search_offers():
    """POST /api/v0/bundles/ — find cheapest suitable GPU."""
    print("[*] Searching Vast.ai for GPU offers...")
    body = {
        "verified":    {"eq": True},
        "rentable":    {"eq": True},
        "rented":      {"eq": False},
        "gpu_name":    {"in": ["RTX_3090", "RTX_4090", "A40"]},
        "num_gpus":    {"eq": 1},
        "gpu_ram":     {"gte": 23000},
        "disk_space":  {"gte": 50},
        "reliability": {"gte": 0.95},
        "order":       [["dph_total", "asc"]],
        "limit":       20,
        "type":        "ondemand",
    }
    resp = api("POST", "bundles/", payload=body)
    if not resp or "offers" not in resp or not resp["offers"]:
        print("[-] No offers found. Check API key / filters.")
        return None
    best = resp["offers"][0]
    print(f"[+] Best offer: {best.get('gpu_name')} @ ${best.get('dph_total', 0):.4f}/hr  "
          f"(ID {best['id']}, {best.get('gpu_ram',0)}MB VRAM, "
          f"{best.get('cpu_cores',0)} vCPU, {best.get('cpu_ram',0)}MB RAM)")
    return best["id"]

# ── CREATE ──────────────────────────────────────────────────────────
def create_instance(offer_id):
    """PUT /api/v0/asks/{id}/ — accept an offer and create instance."""
    print(f"[*] Creating instance from offer {offer_id}...")
    body = {
        "image":   IMAGE,
        "disk":    50,
        "runtype": "ssh",
    }
    resp = api("PUT", f"asks/{offer_id}/", payload=body)
    if resp and resp.get("success"):
        cid = resp["new_contract"]
        print(f"[+] Instance created. Contract ID: {cid}")
        return cid
    print(f"[-] Instance creation failed: {resp}")
    return None

# ── WAIT ────────────────────────────────────────────────────────────
def wait_for_instance(instance_id, timeout=600):
    """Poll GET /api/v0/instances/ until SSH is ready."""
    print(f"[*] Waiting for instance {instance_id} to become ready...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        resp = api("GET", "instances/")
        if resp and "instances" in resp:
            for inst in resp["instances"]:
                if inst.get("id") == instance_id:
                    status = inst.get("actual_status", "unknown")
                    ssh_host = inst.get("ssh_host")
                    ssh_port = inst.get("ssh_port")
                    if status == "running" and ssh_host and ssh_port:
                        print(f"[+] ACTIVE — SSH: {ssh_host}:{ssh_port}")
                        return {"host": ssh_host, "port": ssh_port}
                    print(f"    status={status}  ssh={ssh_host}:{ssh_port}")
                    break
        time.sleep(15)
    print("[-] Timeout waiting for instance.")
    return None

# ── ACCOUNT SSH KEY ─────────────────────────────────────────────────
def ensure_ssh_key():
    """Ensure VPS public key is registered on the Vast.ai account.
    GET  /api/v0/ssh/  — list account keys
    POST /api/v0/ssh/  — create account key (auto-applies to all instances)
    """
    pub = Path(f"{SSH_KEY}.pub").read_text().strip()
    pub_short = pub[:40]
    print("[*] Checking account SSH keys...")
    existing = api("GET", "ssh/")
    if isinstance(existing, list):
        for k in existing:
            if k.get("key", "").startswith(pub_short) or k.get("public_key", "").startswith(pub_short):
                print(f"[+] SSH key already on account (id={k.get('id')}).")
                return
    print("[*] Adding SSH key to Vast.ai account...")
    resp = api("POST", "ssh/", payload={"ssh_key": pub})
    if resp and resp.get("success"):
        print(f"[+] SSH key added to account (id={resp.get('key',{}).get('id')}).")
    else:
        print(f"[!] SSH key add result: {resp}")

# ── SSH / SCP HELPERS ───────────────────────────────────────────────
SSH_OPTS = f"-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -i {SSH_KEY}"

def ssh(target, command, timeout=600):
    """Run a command on the instance via SSH."""
    cmd = f'ssh {SSH_OPTS} -p {target["port"]} root@{target["host"]} {shlex.quote(command)}'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() + "\n" + r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1

def scp_download(target, remote_path, local_path):
    """Download a file from the instance via SCP."""
    cmd = f'scp {SSH_OPTS} -P {target["port"]} root@{target["host"]}:{remote_path} {local_path}'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode == 0

# ── DESTROY ─────────────────────────────────────────────────────────
def destroy_instance(instance_id):
    """DELETE /api/v0/instances/{id}/ — permanently destroy."""
    print(f"[*] Destroying instance {instance_id}...")
    resp = api("DELETE", f"instances/{instance_id}/")
    if resp and resp.get("success"):
        print("[+] Instance destroyed. Billing stopped.")
    else:
        print(f"[-] Destroy result: {resp}")

# ── FULL PIPELINE ───────────────────────────────────────────────────
def run_pipeline():
    print("=" * 60)
    print(" TITAN V8.3 — Automated GPU Training Pipeline")
    print("=" * 60)

    # 0. Ensure SSH key is on the account
    ensure_ssh_key()

    # 1. Find GPU
    offer_id = search_offers()
    if not offer_id:
        return

    # 2. Create instance
    instance_id = create_instance(offer_id)
    if not instance_id:
        return

    try:
        # 3. Wait for boot
        target = wait_for_instance(instance_id)
        if not target:
            raise Exception("Instance failed to boot within timeout.")

        # 4. Wait for SSH daemon
        print("[*] Waiting 30s for SSH daemon...")
        time.sleep(30)

        for attempt in range(8):
            out, rc = ssh(target, "echo SSH_OK && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
            if "SSH_OK" in out:
                print(f"[+] SSH verified. GPU: {out.split(chr(10))[1].strip() if chr(10) in out else 'detected'}")
                break
            print(f"    SSH attempt {attempt+1}/8 failed, waiting 15s...")
            time.sleep(15)
        else:
            raise Exception("SSH connection failed after 8 attempts.")

        # 5. Install dependencies
        print("[*] Installing ML dependencies (2-3 min)...")
        out, rc = ssh(target,
            "pip install -q transformers==4.48.0 peft==0.14.0 datasets==3.3.0 "
            "accelerate==1.3.0 bitsandbytes scipy sentencepiece && echo DEPS_OK",
            timeout=300)
        if "DEPS_OK" not in out:
            raise Exception(f"Dependency install failed:\n{out[-500:]}")
        print("[+] Dependencies installed.")

        # 6. Download training data + script from VPS HTTP server
        print("[*] Downloading training package from VPS...")
        out, rc = ssh(target,
            f"mkdir -p /workspace && cd /workspace && "
            f"wget -q http://{VPS_IP}:{HTTP_PORT}/titan_training_package.tar.gz && "
            f"tar -xzf titan_training_package.tar.gz && "
            f"echo FILES=$(ls data_v2/*.jsonl 2>/dev/null | wc -l)")
        print(f"    {out.strip().split(chr(10))[-1] if out.strip() else 'downloaded'}")

        out, rc = ssh(target,
            f"cd /workspace && "
            f"wget -q http://{VPS_IP}:{HTTP_PORT}/phase3/gpu_train.py -O gpu_train.py && "
            f"wc -l gpu_train.py")
        print(f"    gpu_train.py: {out.strip().split(chr(10))[-1] if out.strip() else 'downloaded'}")

        # 7. Verify files before training
        print("[*] Verifying workspace files...")
        out, rc = ssh(target, "ls -lh /workspace/gpu_train.py /workspace/data_v2/ 2>&1 && echo FILES_OK")
        print(f"    {out}")
        if "FILES_OK" not in out:
            raise Exception(f"Missing workspace files: {out}")

        # 8. Launch training
        print("[*] Launching GPU training...")
        out, rc = ssh(target,
            'cd /workspace && nohup python3 -u gpu_train.py > training.log 2>&1 & echo "PID=$!"')
        print(f"    Launch output: {out}")
        pid_line = [l for l in out.split("\n") if "PID=" in l]
        pid = pid_line[0].split("PID=")[1].strip() if pid_line else ""
        print(f"[+] Training launched. PID={pid}")

        # 9. Wait 15s then check it didn't crash immediately
        time.sleep(15)
        out, rc = ssh(target, "pgrep -f gpu_train.py || echo NO_PROCESS")
        if "NO_PROCESS" in out:
            log_out, _ = ssh(target, "cat /workspace/training.log 2>/dev/null || echo NO_LOG")
            print(f"[!] Training crashed immediately. Log:\n{log_out[-2000:]}")
            raise Exception("Training crashed on startup.")
        # Use pgrep result as the PID if we didn't get one earlier
        if not pid or pid == "unknown":
            pid = out.strip().split("\n")[0]
        print(f"[+] Training process confirmed alive. PID={pid}")

        # 9. Monitor loop
        print("[*] Monitoring training (checking every 60s)...")
        prev_log_len = 0
        stale_count = 0

        while True:
            time.sleep(60)
            out, rc = ssh(target, f"ps -p {pid} > /dev/null 2>&1 && echo ALIVE || echo DEAD")
            log_out, _ = ssh(target, "tail -80 /workspace/training.log")
            cur_len = len(log_out)

            if "DEAD" in out:
                print("[*] Training process finished.")
                print(f"    Last output:\n{log_out[-1500:]}")
                break

            if cur_len > prev_log_len:
                # Extract last meaningful line
                lines = [l.strip() for l in log_out.split("\n") if l.strip()]
                last = lines[-1] if lines else ""
                print(f"[*] Training running... ({last[:120]})")
                prev_log_len = cur_len
                stale_count = 0
            else:
                stale_count += 1
                if stale_count >= 5:
                    print(f"[!] No log progress for {stale_count} min")

            if any(m in log_out for m in ["ALL TRAINING COMPLETE", "Training complete", "=== DONE ==="]):
                print("[+] Training completed successfully!")
                break

        # 10. Download trained models
        print("[*] Downloading trained models...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ssh(target, "cd /workspace && tar -czf /workspace/trained_models.tar.gz output/ 2>/dev/null || true")
        ok = scp_download(target, "/workspace/trained_models.tar.gz", str(OUTPUT_DIR / "trained_models.tar.gz"))
        if ok:
            subprocess.run(f"cd {OUTPUT_DIR} && tar -xzf trained_models.tar.gz", shell=True)
            print(f"[+] Models saved to {OUTPUT_DIR}")
        else:
            print("[!] SCP download failed — try manual download later.")
            # Also grab log
            ssh(target, "cat /workspace/training.log > /workspace/training_final.log")
            scp_download(target, "/workspace/training_final.log", str(OUTPUT_DIR / "training.log"))

    except Exception as e:
        print(f"[!] Pipeline error: {e}")
    finally:
        # 11. Destroy instance (stop billing)
        destroy_instance(instance_id)

    print("=" * 60)
    print(" Pipeline complete.")
    print("=" * 60)

# ── CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vast.ai REST Training Automator v2")
    parser.add_argument("--action", choices=["full", "search", "destroy"], default="full")
    parser.add_argument("--id", type=int, help="Instance ID (for destroy)")
    args = parser.parse_args()

    if args.action == "full":
        run_pipeline()
    elif args.action == "search":
        search_offers()
    elif args.action == "destroy":
        if args.id:
            destroy_instance(args.id)
        else:
            print("[!] Provide --id for destroy.")
