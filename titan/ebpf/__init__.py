"""
TITAN V7.0 SINGULARITY - eBPF Network Shield Module

This module provides kernel-level packet manipulation capabilities
using eBPF (Extended Berkeley Packet Filter) and XDP (eXpress Data Path).

Components:
- network_shield.c: eBPF C program for packet modification
- network_shield_loader.py: Python interface for loading and controlling the shield

Source: Unified Agent [cite: 1, 14, 16]
"""

from .network_shield_loader import (
    NetworkShield,
    NetworkShieldError,
    Persona,
)

__all__ = [
    "NetworkShield",
    "NetworkShieldError",
    "Persona",
]
