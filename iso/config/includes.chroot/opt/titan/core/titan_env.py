"""
TITAN V7.0 SINGULARITY — Environment Configuration Loader

Loads /opt/titan/config/titan.env into os.environ.
Import this module early to ensure all TITAN_* variables are available.

Usage:
    from titan_env import get_config, is_configured
    
    # Check if a specific service is configured (not placeholder)
    if is_configured("TITAN_CLOUD_URL"):
        ...
    
    # Get a value with default
    url = get_config("TITAN_CLOUD_URL", "http://localhost:8000/v1")
"""

import os
from pathlib import Path

TITAN_ENV_PATH = Path("/opt/titan/config/titan.env")
_loaded = False


def load_env(force: bool = False):
    """Load titan.env into os.environ. Safe to call multiple times."""
    global _loaded
    if _loaded and not force:
        return
    
    if not TITAN_ENV_PATH.exists():
        return
    
    for line in TITAN_ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not value or value.startswith("REPLACE_WITH"):
            continue
        if key not in os.environ:
            os.environ[key] = value
    
    _loaded = True


def get_config(key: str, default: str = "") -> str:
    """Get a config value, loading titan.env if needed."""
    load_env()
    return os.environ.get(key, default)


def is_configured(key: str) -> bool:
    """Check if a key is set to a real value (not a placeholder)."""
    load_env()
    val = os.environ.get(key, "")
    return bool(val) and not val.startswith("REPLACE_WITH")


def get_all_config() -> dict:
    """Get all TITAN_ config values as a dict."""
    load_env()
    return {k: v for k, v in os.environ.items() if k.startswith("TITAN_")}


def get_config_status() -> dict:
    """Get configuration status for all required services."""
    return {
        "cloud_brain": is_configured("TITAN_CLOUD_URL") and is_configured("TITAN_API_KEY"),
        "proxy": is_configured("TITAN_PROXY_PROVIDER"),
        "vpn": is_configured("TITAN_VPN_SERVER_IP") and is_configured("TITAN_VPN_UUID"),
        "stripe": is_configured("TITAN_STRIPE_SECRET_KEY"),
        "paypal": is_configured("TITAN_PAYPAL_CLIENT_ID"),
        "braintree": is_configured("TITAN_BRAINTREE_MERCHANT_ID"),
        "ebpf": is_configured("TITAN_EBPF_ENABLED"),
        "hw_shield": is_configured("TITAN_HW_SHIELD_ENABLED"),
        "tx_monitor": get_config("TITAN_TX_MONITOR_AUTOSTART", "1") == "1",
        "auto_discovery": get_config("TITAN_DISCOVERY_AUTOSTART", "1") == "1",
        "feedback_loop": get_config("TITAN_FEEDBACK_AUTOSTART", "1") == "1",
    }


# Auto-load on import
load_env()
