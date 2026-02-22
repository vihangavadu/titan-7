"""
TITAN V8.1 SINGULARITY — Environment Configuration Loader

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
import logging
from pathlib import Path

logger = logging.getLogger("TITAN-ENV")

TITAN_ENV_PATH = Path("/opt/titan/config/titan.env")
_loaded = False


def load_env(force: bool = False):
    """Load titan.env into os.environ. Safe to call multiple times."""
    global _loaded
    if _loaded and not force:
        return
    
    if not TITAN_ENV_PATH.exists():
        return
    
    count = 0
    for line in TITAN_ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # V7.5 FIX: Handle 'export' prefix common in shell env files
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # V7.5 FIX: Strip surrounding quotes from values
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if not value or value.startswith("REPLACE_WITH"):
            continue
        # V7.5 FIX: Force reload updates existing values
        if force or key not in os.environ:
            os.environ[key] = value
            count += 1
    
    logger.debug(f"Loaded {count} variables from {TITAN_ENV_PATH}")
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


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced Configuration Management
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field


@dataclass
class ConfigValidationResult:
    """Configuration validation result"""
    valid: bool
    missing_required: List[str]
    missing_optional: List[str]
    placeholder_values: List[str]
    warnings: List[str]


@dataclass
class ConfigChange:
    """Configuration change record"""
    timestamp: float
    key: str
    old_value: str
    new_value: str
    source: str


class ConfigValidator:
    """
    V7.6 P0: Validate configuration completeness.
    
    Features:
    - Required vs optional config separation
    - Service dependency validation
    - Configuration scoring
    - Remediation guidance
    """
    
    REQUIRED_CONFIGS = {
        "core": [
            "TITAN_DATA_DIR",
            "TITAN_LOG_LEVEL",
        ],
        "cloud_brain": [
            "TITAN_CLOUD_URL",
            "TITAN_API_KEY",
        ],
        "proxy": [
            "TITAN_PROXY_PROVIDER",
        ],
        "vpn": [
            "TITAN_VPN_SERVER_IP",
            "TITAN_VPN_UUID",
        ],
    }
    
    OPTIONAL_CONFIGS = {
        "payment_stripe": [
            "TITAN_STRIPE_SECRET_KEY",
            "TITAN_STRIPE_PUBLISHABLE_KEY",
        ],
        "payment_paypal": [
            "TITAN_PAYPAL_CLIENT_ID",
            "TITAN_PAYPAL_CLIENT_SECRET",
        ],
        "payment_braintree": [
            "TITAN_BRAINTREE_MERCHANT_ID",
            "TITAN_BRAINTREE_PUBLIC_KEY",
            "TITAN_BRAINTREE_PRIVATE_KEY",
        ],
        "features": [
            "TITAN_EBPF_ENABLED",
            "TITAN_HW_SHIELD_ENABLED",
            "TITAN_TX_MONITOR_AUTOSTART",
            "TITAN_DISCOVERY_AUTOSTART",
            "TITAN_FEEDBACK_AUTOSTART",
        ],
    }
    
    def __init__(self):
        self._last_validation: Optional[ConfigValidationResult] = None
        self._validation_history: List[Dict] = []
        self.logger = logging.getLogger("TITAN-CONFIG-VALIDATOR")
    
    def validate(self, services: List[str] = None) -> ConfigValidationResult:
        """Validate configuration completeness"""
        load_env()
        
        missing_required = []
        missing_optional = []
        placeholder_values = []
        warnings = []
        
        # Check required configs
        services_to_check = services or list(self.REQUIRED_CONFIGS.keys())
        for service in services_to_check:
            for key in self.REQUIRED_CONFIGS.get(service, []):
                value = os.environ.get(key, "")
                if not value:
                    missing_required.append(key)
                elif value.startswith("REPLACE_WITH"):
                    placeholder_values.append(key)
        
        # Check optional configs
        for service in self.OPTIONAL_CONFIGS:
            for key in self.OPTIONAL_CONFIGS[service]:
                value = os.environ.get(key, "")
                if not value:
                    missing_optional.append(key)
                elif value.startswith("REPLACE_WITH"):
                    placeholder_values.append(key)
        
        # Generate warnings
        if placeholder_values:
            warnings.append(f"{len(placeholder_values)} config values need to be replaced")
        
        if "TITAN_API_KEY" in missing_required or "TITAN_API_KEY" in placeholder_values:
            warnings.append("Cloud brain connection will not work without API key")
        
        if "TITAN_PROXY_PROVIDER" in missing_required:
            warnings.append("No proxy provider configured - operations will use direct connection")
        
        result = ConfigValidationResult(
            valid=len(missing_required) == 0 and len(placeholder_values) == 0,
            missing_required=missing_required,
            missing_optional=missing_optional,
            placeholder_values=placeholder_values,
            warnings=warnings,
        )
        
        self._last_validation = result
        self._validation_history.append({
            "timestamp": time.time(),
            "valid": result.valid,
            "missing_count": len(missing_required),
            "placeholder_count": len(placeholder_values),
        })
        
        return result
    
    def get_completion_score(self) -> float:
        """Calculate configuration completion percentage"""
        load_env()
        
        total = 0
        configured = 0
        
        for configs in self.REQUIRED_CONFIGS.values():
            total += len(configs)
            for key in configs:
                if is_configured(key):
                    configured += 1
        
        for configs in self.OPTIONAL_CONFIGS.values():
            total += len(configs)
            for key in configs:
                if is_configured(key):
                    configured += 1
        
        return round(configured / max(1, total), 3)
    
    def get_remediation(self) -> List[str]:
        """Get remediation steps for missing config"""
        if not self._last_validation:
            self.validate()
        
        steps = []
        
        if self._last_validation.missing_required:
            steps.append(f"Configure {len(self._last_validation.missing_required)} required settings in titan.env")
            for key in self._last_validation.missing_required[:5]:
                steps.append(f"  - Add: {key}=<value>")
        
        if self._last_validation.placeholder_values:
            steps.append(f"Replace {len(self._last_validation.placeholder_values)} placeholder values")
            for key in self._last_validation.placeholder_values[:5]:
                steps.append(f"  - Update: {key}")
        
        return steps


class ConfigMonitor:
    """
    V7.6 P0: Monitor config changes.
    
    Features:
    - Real-time config change detection
    - Change history tracking
    - Notification on changes
    - Rollback support
    """
    
    POLL_INTERVAL_SECONDS = 60
    
    def __init__(self):
        self._monitoring = False
        self._thread: Optional[threading.Thread] = None
        self._last_state: Dict[str, str] = {}
        self._changes: List[ConfigChange] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-CONFIG-MONITOR")
    
    def start(self):
        """Start config monitoring"""
        if self._monitoring:
            return
        
        self._take_snapshot()
        self._monitoring = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("Config monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self._monitoring = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                self._check_changes()
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
            
            time.sleep(self.POLL_INTERVAL_SECONDS)
    
    def _take_snapshot(self):
        """Take snapshot of current config"""
        load_env(force=True)
        with self._lock:
            self._last_state = {k: v for k, v in os.environ.items() if k.startswith("TITAN_")}
    
    def _check_changes(self):
        """Check for config changes"""
        load_env(force=True)
        current = {k: v for k, v in os.environ.items() if k.startswith("TITAN_")}
        
        with self._lock:
            # Check for changed/new values
            for key, value in current.items():
                old_value = self._last_state.get(key)
                if old_value != value:
                    change = ConfigChange(
                        timestamp=time.time(),
                        key=key,
                        old_value=old_value or "",
                        new_value=value,
                        source="titan.env",
                    )
                    self._changes.append(change)
                    self.logger.info(f"Config changed: {key}")
            
            # Check for removed values
            for key in self._last_state:
                if key not in current:
                    change = ConfigChange(
                        timestamp=time.time(),
                        key=key,
                        old_value=self._last_state[key],
                        new_value="",
                        source="removed",
                    )
                    self._changes.append(change)
            
            self._last_state = current
    
    def get_changes(self, since_hours: float = 24) -> List[Dict]:
        """Get recent config changes"""
        cutoff = time.time() - (since_hours * 3600)
        
        with self._lock:
            return [
                {
                    "timestamp": c.timestamp,
                    "key": c.key,
                    "old_value": "***" if "SECRET" in c.key or "KEY" in c.key else c.old_value,
                    "new_value": "***" if "SECRET" in c.key or "KEY" in c.key else c.new_value,
                    "source": c.source,
                }
                for c in self._changes
                if c.timestamp > cutoff
            ]
    
    def get_status(self) -> Dict:
        """Get monitor status"""
        with self._lock:
            return {
                "monitoring": self._monitoring,
                "config_count": len(self._last_state),
                "total_changes": len(self._changes),
            }


class SecureConfigManager:
    """
    V7.6 P0: Secure sensitive config values.
    
    Features:
    - Sensitive value masking
    - Access logging
    - Config encryption helpers
    - Secure storage
    """
    
    SENSITIVE_PATTERNS = [
        "KEY", "SECRET", "PASSWORD", "TOKEN", "UUID",
        "PRIVATE", "CREDENTIAL", "API_KEY",
    ]
    
    def __init__(self):
        self._access_log: List[Dict] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-SECURE-CONFIG")
    
    def is_sensitive(self, key: str) -> bool:
        """Check if a key is sensitive"""
        key_upper = key.upper()
        return any(pattern in key_upper for pattern in self.SENSITIVE_PATTERNS)
    
    def get_secure(self, key: str, default: str = "", log_access: bool = True) -> str:
        """Get a config value with access logging"""
        value = get_config(key, default)
        
        if log_access and self.is_sensitive(key):
            with self._lock:
                self._access_log.append({
                    "timestamp": time.time(),
                    "key": key,
                    "accessed": True,
                })
                if len(self._access_log) > 1000:
                    self._access_log = self._access_log[-1000:]
        
        return value
    
    def mask_value(self, value: str, visible_chars: int = 4) -> str:
        """Mask a sensitive value"""
        if len(value) <= visible_chars:
            return "*" * len(value)
        return "*" * (len(value) - visible_chars) + value[-visible_chars:]
    
    def get_masked_config(self) -> Dict[str, str]:
        """Get all config with sensitive values masked"""
        all_config = get_all_config()
        masked = {}
        
        for key, value in all_config.items():
            if self.is_sensitive(key):
                masked[key] = self.mask_value(value)
            else:
                masked[key] = value
        
        return masked
    
    def compute_config_hash(self) -> str:
        """Compute hash of current config for integrity checking"""
        all_config = get_all_config()
        config_str = json.dumps(all_config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def get_access_log(self, limit: int = 50) -> List[Dict]:
        """Get access log for sensitive configs"""
        with self._lock:
            return self._access_log[-limit:]


class ConfigMigrator:
    """
    V7.6 P0: Migrate config between versions.
    
    Features:
    - Config version tracking
    - Migration rules
    - Backup/restore
    - Validation after migration
    """
    
    MIGRATIONS = {
        "7.5": {
            "renames": {
                "TITAN_CLOUD_API_KEY": "TITAN_API_KEY",
                "TITAN_PROXY_URL": "TITAN_PROXY_PROVIDER",
            },
            "defaults": {
                "TITAN_LOG_LEVEL": "INFO",
            },
        },
        "7.6": {
            "renames": {},
            "defaults": {
                "TITAN_TX_MONITOR_AUTOSTART": "1",
                "TITAN_DISCOVERY_AUTOSTART": "1",
                "TITAN_FEEDBACK_AUTOSTART": "1",
            },
        },
    }
    
    def __init__(self):
        self._backups: Dict[str, Dict[str, str]] = {}
        self._migration_history: List[Dict] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-CONFIG-MIGRATOR")
    
    def backup(self, label: str = None) -> str:
        """Backup current config"""
        if label is None:
            label = f"backup_{int(time.time())}"
        
        all_config = get_all_config()
        
        with self._lock:
            self._backups[label] = all_config
        
        self.logger.info(f"Config backed up: {label} ({len(all_config)} values)")
        return label
    
    def restore(self, label: str) -> bool:
        """Restore config from backup"""
        with self._lock:
            backup = self._backups.get(label)
            if not backup:
                return False
            
            for key, value in backup.items():
                os.environ[key] = value
        
        self.logger.info(f"Config restored from: {label}")
        return True
    
    def migrate(self, from_version: str, to_version: str) -> Dict:
        """Migrate config between versions"""
        result = {
            "from": from_version,
            "to": to_version,
            "renames": [],
            "defaults_applied": [],
            "success": True,
        }
        
        # Create backup first
        backup_label = self.backup(f"pre_migration_{from_version}_{to_version}")
        
        try:
            # Apply migrations for versions between from and to
            for version, rules in self.MIGRATIONS.items():
                if version > from_version and version <= to_version:
                    # Apply renames
                    for old_key, new_key in rules.get("renames", {}).items():
                        old_value = os.environ.get(old_key)
                        if old_value and not os.environ.get(new_key):
                            os.environ[new_key] = old_value
                            result["renames"].append(f"{old_key} -> {new_key}")
                    
                    # Apply defaults
                    for key, default in rules.get("defaults", {}).items():
                        if not os.environ.get(key):
                            os.environ[key] = default
                            result["defaults_applied"].append(key)
            
            self._migration_history.append({
                "timestamp": time.time(),
                **result,
            })
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            self.restore(backup_label)
        
        return result
    
    def get_history(self) -> List[Dict]:
        """Get migration history"""
        with self._lock:
            return list(self._migration_history)


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_config_validator: Optional[ConfigValidator] = None
_config_monitor: Optional[ConfigMonitor] = None
_secure_config_manager: Optional[SecureConfigManager] = None
_config_migrator: Optional[ConfigMigrator] = None


def get_config_validator() -> ConfigValidator:
    """Get global config validator"""
    global _config_validator
    if _config_validator is None:
        _config_validator = ConfigValidator()
    return _config_validator


def get_config_monitor() -> ConfigMonitor:
    """Get global config monitor"""
    global _config_monitor
    if _config_monitor is None:
        _config_monitor = ConfigMonitor()
    return _config_monitor


def get_secure_config_manager() -> SecureConfigManager:
    """Get global secure config manager"""
    global _secure_config_manager
    if _secure_config_manager is None:
        _secure_config_manager = SecureConfigManager()
    return _secure_config_manager


def get_config_migrator() -> ConfigMigrator:
    """Get global config migrator"""
    global _config_migrator
    if _config_migrator is None:
        _config_migrator = ConfigMigrator()
    return _config_migrator
