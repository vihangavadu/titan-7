#!/usr/bin/env python3
"""Search Vast.ai for H100/A100 GPU offers."""
import requests, json, sys

API_KEY = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
BASE = "https://console.vast.ai/api/v0"
headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

body = {
    "verified": {"eq": True},
    "rentable": {"eq": True},
    "rented": {"eq": False},
    "gpu_name": {"in": ["H100_SXM", "H100_PCIE", "H100", "A100_SXM", "A100_PCIE", "A100"]},
    "num_gpus": {"eq": 1},
    "gpu_ram": {"gte": 40000},
    "disk_space": {"gte": 50},
    "reliability": {"gte": 0.90},
    "order": [["dph_total", "asc"]],
    "limit": 15,
    "type": "ondemand"
}

r = requests.post(BASE + "/bundles/", headers=headers, json=body)
data = r.json()
offers = data.get("offers", [])
print("Found %d H100/A100 offers:" % len(offers))
print("-" * 100)
for o in offers[:15]:
    gpu = o.get("gpu_name", "?")
    cost = o.get("dph_total", 0)
    vram = o.get("gpu_ram", 0)
    oid = o.get("id", 0)
    driver = o.get("driver_version", "?")
    cuda = o.get("cuda_max_good", "?")
    cpu_cores = o.get("cpu_cores_effective", 0)
    ram = o.get("cpu_ram", 0)
    loc = o.get("geolocation", "?")
    print("  ID:%-10s  %-12s  $%.3f/hr  %5dMB VRAM  drv:%-7s  cuda:%-4s  %dcpu  %5dMB RAM  %s" % (
        oid, gpu, cost, vram, driver, cuda, cpu_cores, ram, loc))

# Also check for RTX 4090 (good price-perf)
body2 = dict(body)
body2["gpu_name"] = {"in": ["RTX_4090"]}
body2["gpu_ram"] = {"gte": 23000}
r2 = requests.post(BASE + "/bundles/", headers=headers, json=body2)
data2 = r2.json()
offers2 = data2.get("offers", [])
print("\nFound %d RTX 4090 offers:" % len(offers2))
for o in offers2[:5]:
    gpu = o.get("gpu_name", "?")
    cost = o.get("dph_total", 0)
    vram = o.get("gpu_ram", 0)
    oid = o.get("id", 0)
    driver = o.get("driver_version", "?")
    cuda = o.get("cuda_max_good", "?")
    loc = o.get("geolocation", "?")
    print("  ID:%-10s  %-12s  $%.3f/hr  %5dMB VRAM  drv:%-7s  cuda:%-4s  %s" % (
        oid, gpu, cost, vram, driver, cuda, loc))
