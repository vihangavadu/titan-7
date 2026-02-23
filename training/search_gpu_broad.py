#!/usr/bin/env python3
"""Broad search for all high-end GPUs on Vast.ai."""
import requests, json

API_KEY = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
BASE = "https://console.vast.ai/api/v0"
headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}

# Search 1: Any GPU with 40GB+ VRAM (catches H100, A100, A6000, etc.)
body = {
    "verified": {"eq": True},
    "rentable": {"eq": True},
    "rented": {"eq": False},
    "num_gpus": {"eq": 1},
    "gpu_ram": {"gte": 40000},
    "disk_space": {"gte": 50},
    "reliability": {"gte": 0.85},
    "order": [["dph_total", "asc"]],
    "limit": 20,
    "type": "ondemand"
}
r = requests.post(BASE + "/bundles/", headers=headers, json=body)
data = r.json()
offers = data.get("offers", [])
print("=== HIGH VRAM (40GB+) - %d offers ===" % len(offers))
for o in offers[:20]:
    print("  ID:%-10s  %-15s  $%.3f/hr  %5dMB  drv:%-7s  cuda:%-4s  %s" % (
        o.get("id", 0), o.get("gpu_name", "?"), o.get("dph_total", 0),
        o.get("gpu_ram", 0), o.get("driver_version", "?"),
        o.get("cuda_max_good", "?"), o.get("geolocation", "?")))

# Search 2: Any GPU with 24GB VRAM but faster than 3090 (4090, 3090Ti, A5000)
body2 = {
    "verified": {"eq": True},
    "rentable": {"eq": True},
    "rented": {"eq": False},
    "num_gpus": {"eq": 1},
    "gpu_ram": {"gte": 23000, "lte": 39999},
    "disk_space": {"gte": 50},
    "reliability": {"gte": 0.85},
    "order": [["dph_total", "asc"]],
    "limit": 20,
    "type": "ondemand"
}
r2 = requests.post(BASE + "/bundles/", headers=headers, json=body2)
data2 = r2.json()
offers2 = data2.get("offers", [])
print("\n=== MID VRAM (24-40GB) - %d offers ===" % len(offers2))
for o in offers2[:20]:
    print("  ID:%-10s  %-15s  $%.3f/hr  %5dMB  drv:%-7s  cuda:%-4s  %s" % (
        o.get("id", 0), o.get("gpu_name", "?"), o.get("dph_total", 0),
        o.get("gpu_ram", 0), o.get("driver_version", "?"),
        o.get("cuda_max_good", "?"), o.get("geolocation", "?")))

# Search 3: Multi-GPU (2x) for parallel training
body3 = {
    "verified": {"eq": True},
    "rentable": {"eq": True},
    "rented": {"eq": False},
    "num_gpus": {"gte": 2},
    "gpu_ram": {"gte": 23000},
    "disk_space": {"gte": 50},
    "reliability": {"gte": 0.85},
    "order": [["dph_total", "asc"]],
    "limit": 10,
    "type": "ondemand"
}
r3 = requests.post(BASE + "/bundles/", headers=headers, json=body3)
data3 = r3.json()
offers3 = data3.get("offers", [])
print("\n=== MULTI-GPU (2+) - %d offers ===" % len(offers3))
for o in offers3[:10]:
    print("  ID:%-10s  %dx %-12s  $%.3f/hr  %5dMB/gpu  drv:%-7s  %s" % (
        o.get("id", 0), o.get("num_gpus", 1), o.get("gpu_name", "?"),
        o.get("dph_total", 0), o.get("gpu_ram", 0),
        o.get("driver_version", "?"), o.get("geolocation", "?")))
