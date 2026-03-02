"""Telemetry and status reporting."""
import subprocess
import requests


def report(host):
    # sample GPU query
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader"])
        data = out.decode().strip()
    except Exception:
        data = "n/a"
    payload = {"ip": host["ip"], "gpu": data}
    # pretend to POST to REST API
    print("Reporting:", payload)
    # requests.post("https://example.com/telemetry", json=payload)
