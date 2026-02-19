"""
⚠️  DEPRECATED — V5 DEVELOPMENT CODE ⚠️

This directory (titan/) contains the original V5 development code.
It is NO LONGER the authoritative source for TITAN V7.0 SINGULARITY.

The V7.0 authoritative code lives in:
  iso/config/includes.chroot/opt/titan/core/   — 30 Python modules + 2 C modules
  iso/config/includes.chroot/opt/titan/apps/   — 4 Trinity GUI apps
  iso/config/includes.chroot/opt/titan/bin/    — Launchers and tools

The files in this directory are retained only for:
  - titan/ebpf/          — eBPF dev sources (deployed to iso/ via deploy_titan_v6.sh)
  - titan/hardware_shield/ — Kernel module dev sources (deployed via deploy_titan_v6.sh)
  - titan/mobile/        — Waydroid hardener (integrated into V7.0 ISO)

DO NOT EDIT titan_core.py or TITAN_CORE_v5.py — they are obsolete.
"""

from .titan_core import (
    TitanController,
    GenesisEngine,
    TemporalDisplacement,
    BrowserProfile,
    Persona,
    ProfilePhase,
)

__version__ = "7.0.0"
__codename__ = "SINGULARITY"
__author__ = "Dva.12"

__all__ = [
    "TitanController",
    "GenesisEngine",
    "TemporalDisplacement",
    "BrowserProfile",
    "Persona",
    "ProfilePhase",
]
