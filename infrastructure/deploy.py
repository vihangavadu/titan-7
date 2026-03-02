#!/usr/bin/env python3
"""Core orchestrator for remote infrastructure and AI deployments."""
import os
import sys
import yaml
from modules import provision, monitor, doctor, ai_deploy


def load_config(path="config.yml"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file {path} not found")
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()
    # iterate through hosts defined in config
    for host in cfg.get("hosts", []):
        ip = host["ip"]
        user = host.get("user", "root")
        key = host.get("ssh_key")

        print(f"Provisioning {ip}...")
        provision.run_ansible_playbook(host, "ansible/setup_host.yml")

        print(f"Checking health on {ip}...")
        doctor.run_checks(host)

        print(f"Gathering telemetry from {ip}...")
        monitor.report(host)

        print(f"Deploying AI workloads to {ip}...")
        ai_deploy.deploy_containers(host)


if __name__ == "__main__":
    main()
