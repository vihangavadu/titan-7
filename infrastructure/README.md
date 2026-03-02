# AI Infrastructure Orchestrator

This repository provides a Python-based automation framework for managing
remote servers, configuring OS environments, and deploying AI workloads.

## Features

* Remote provisioning via SSH and Ansible
* OS configuration (GPU drivers, Docker, etc.)
* Containerised AI deployments
* GPU telemetry and REST reporting
* Health checks and automated debugging

## Structure

```
infrastructure/
├── ansible/
│   └── setup_host.yml       # initial playbook for GPU hosts
├── modules/
│   ├── ai_deploy.py
│   ├── doctor.py
│   ├── monitor.py
│   └── provision.py
├── deploy.py               # core orchestrator
├── requirements.txt        # Python dependencies
└── README.md
```

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Create `config.yml` describing your hosts.
3. Run `python deploy.py` to provision and deploy.

Modify the Ansible playbook and modules according to your needs.
