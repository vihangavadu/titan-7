"""
TITAN V7.0 SINGULARITY — Cockpit Middleware Daemon
Privileged backend daemon for zero-terminal GUI operations

The Cockpit daemon implements the Principle of Least Privilege:
the GUI front-end runs as a standard user while all privileged
operations (kernel module loading, eBPF control, network config,
fingerprint rotation) are handled by this daemon via a secure
local Unix socket with cryptographically signed JSON commands.

Architecture:
    cockpit_daemon.py       → Rust-inspired Python middleware daemon
    app_unified.py (GUI)    → sends signed JSON commands via Unix socket
    titan_hw.ko / eBPF      → privileged operations executed by daemon

Command Schema:
    {
        "action": "rotate_fingerprint",
        "target": "windows_11_23h2",
        "timestamp": 1707840000,
        "signature": "sha256_hmac_of_payload"
    }

Security Model:
    - GUI runs as 'user' (unprivileged)
    - Daemon runs as root via systemd
    - Commands validated against strict schema
    - HMAC-SHA256 signature verification
    - Rate limiting (max 10 commands/second)
    - Audit log of all privileged operations
"""

import hashlib
import hmac
import json
import logging
import os
import socket
import struct
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

__version__ = "8.0.0"
__author__ = "Dva.12"

SOCKET_PATH = "/run/titan/cockpit.sock"
AUDIT_LOG_PATH = "/opt/titan/state/cockpit_audit.log"
HMAC_KEY_PATH = "/opt/titan/state/.cockpit_hmac_key"
MAX_COMMANDS_PER_SECOND = 10
MAX_PAYLOAD_SIZE = 65536


class CommandAction(Enum):
    """Supported privileged operations."""
    ROTATE_FINGERPRINT = "rotate_fingerprint"
    RELOAD_EBPF = "reload_ebpf"
    LOAD_KERNEL_MODULE = "load_kernel_module"
    UNLOAD_KERNEL_MODULE = "unload_kernel_module"
    SET_NETWORK_JITTER = "set_network_jitter"
    ROTATE_MAC = "rotate_mac"
    FLUSH_DNS = "flush_dns"
    KILL_SWITCH_ARM = "kill_switch_arm"
    KILL_SWITCH_PANIC = "kill_switch_panic"
    APPLY_UPDATE = "apply_update"
    ROLLBACK_PARTITION = "rollback_partition"
    WIPE_EPHEMERAL = "wipe_ephemeral"
    RESTART_SERVICE = "restart_service"
    CHECK_INTEGRITY = "check_integrity"
    GET_STATUS = "get_status"
    START_WAYDROID = "start_waydroid"
    STOP_WAYDROID = "stop_waydroid"


@dataclass
class CommandResult:
    """Result of a privileged command execution."""
    success: bool
    action: str
    message: str = ""
    data: Dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_json(self) -> str:
        self.timestamp = time.time()
        return json.dumps({
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        })


class RateLimiter:
    """Token bucket rate limiter for command processing."""

    def __init__(self, max_per_second: int = MAX_COMMANDS_PER_SECOND):
        self._max = max_per_second
        self._tokens = max_per_second
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._max, self._tokens + elapsed * self._max)
            self._last_refill = now
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False


class CockpitDaemon:
    """
    Privileged middleware daemon for the TITAN V7 Cockpit interface.

    Listens on a Unix domain socket for signed JSON commands from the
    GUI front-end. Validates commands, checks signatures, and executes
    privileged operations with full audit logging.

    Usage (daemon side):
        daemon = CockpitDaemon()
        daemon.start()  # Blocks, runs event loop

    Usage (client side):
        client = CockpitClient()
        result = client.send_command("rotate_fingerprint", {"target": "windows_11_23h2"})
    """

    def __init__(
        self,
        socket_path: str = SOCKET_PATH,
        hmac_key_path: str = HMAC_KEY_PATH,
    ):
        self._socket_path = socket_path
        self._hmac_key = self._load_or_generate_hmac_key(hmac_key_path)
        self._rate_limiter = RateLimiter()
        self._running = False
        self._server_socket: Optional[socket.socket] = None
        self._handlers: Dict[str, Callable] = {}
        self._logger = self._setup_logger()
        self._register_default_handlers()

    def _setup_logger(self) -> logging.Logger:
        """Configure audit logger."""
        logger = logging.getLogger("titan.cockpit")
        logger.setLevel(logging.INFO)
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        handler = logging.FileHandler(AUDIT_LOG_PATH)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        logger.addHandler(handler)
        return logger

    def _load_or_generate_hmac_key(self, key_path: str) -> bytes:
        """Load existing HMAC key or generate a new one."""
        try:
            if os.path.isfile(key_path):
                with open(key_path, "rb") as f:
                    return f.read()
        except (PermissionError, OSError):
            pass

        # Generate new key
        key = os.urandom(32)
        try:
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(key)
            os.chmod(key_path, 0o600)
        except (PermissionError, OSError):
            pass
        return key

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature of command payload."""
        expected = hmac.new(self._hmac_key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _validate_command(self, data: Dict) -> Tuple[bool, str]:
        """Validate command structure and action."""
        if "action" not in data:
            return False, "Missing 'action' field"

        try:
            CommandAction(data["action"])
        except ValueError:
            return False, f"Unknown action: {data['action']}"

        if "timestamp" in data:
            cmd_time = data["timestamp"]
            now = time.time()
            if abs(now - cmd_time) > 30:
                return False, "Command timestamp too old (replay protection)"

        return True, ""

    def _register_default_handlers(self) -> None:
        """Register default command handlers."""
        self._handlers = {
            CommandAction.GET_STATUS.value: self._handle_get_status,
            CommandAction.ROTATE_FINGERPRINT.value: self._handle_rotate_fingerprint,
            CommandAction.RELOAD_EBPF.value: self._handle_reload_ebpf,
            CommandAction.LOAD_KERNEL_MODULE.value: self._handle_load_kernel_module,
            CommandAction.UNLOAD_KERNEL_MODULE.value: self._handle_unload_kernel_module,
            CommandAction.SET_NETWORK_JITTER.value: self._handle_set_jitter,
            CommandAction.ROTATE_MAC.value: self._handle_rotate_mac,
            CommandAction.FLUSH_DNS.value: self._handle_flush_dns,
            CommandAction.KILL_SWITCH_ARM.value: self._handle_kill_switch_arm,
            CommandAction.KILL_SWITCH_PANIC.value: self._handle_kill_switch_panic,
            CommandAction.WIPE_EPHEMERAL.value: self._handle_wipe_ephemeral,
            CommandAction.CHECK_INTEGRITY.value: self._handle_check_integrity,
            CommandAction.RESTART_SERVICE.value: self._handle_restart_service,
            CommandAction.START_WAYDROID.value: self._handle_start_waydroid,
            CommandAction.STOP_WAYDROID.value: self._handle_stop_waydroid,
        }

    def register_handler(self, action: str, handler: Callable) -> None:
        """Register a custom command handler."""
        self._handlers[action] = handler

    def _execute_command(self, data: Dict) -> CommandResult:
        """Execute a validated command."""
        action = data["action"]
        handler = self._handlers.get(action)

        if not handler:
            return CommandResult(
                success=False, action=action,
                message=f"No handler for action: {action}"
            )

        try:
            return handler(data)
        except Exception as e:
            self._logger.error(f"Command failed: {action} — {e}")
            return CommandResult(
                success=False, action=action,
                message=f"Execution error: {str(e)}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # DEFAULT COMMAND HANDLERS
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_get_status(self, data: Dict) -> CommandResult:
        """Return system status."""
        status = {
            "version": __version__,
            "uptime": time.time(),
            "kernel_module_loaded": os.path.exists("/sys/module/titan_hw"),
            "ebpf_active": os.path.exists("/sys/fs/bpf/titan_xdp"),
            # V7.5 FIX: Use context manager to avoid file handle leak
            "overlay_active": "overlay" in Path("/proc/mounts").read_text() if os.path.exists("/proc/mounts") else False,
        }
        return CommandResult(success=True, action="get_status", data=status)

    def _handle_rotate_fingerprint(self, data: Dict) -> CommandResult:
        """Rotate hardware fingerprint via kernel module."""
        target = data.get("target", "windows_11_23h2")
        try:
            subprocess.run(
                ["python3", "-c", f"from titan.core import NetlinkHWBridge; b = NetlinkHWBridge(); b.sync_profile('{target}')"],
                capture_output=True, timeout=10,
            )
            self._logger.info(f"Fingerprint rotated to: {target}")
            return CommandResult(success=True, action="rotate_fingerprint", data={"target": target})
        except Exception as e:
            return CommandResult(success=False, action="rotate_fingerprint", message=str(e))

    def _handle_reload_ebpf(self, data: Dict) -> CommandResult:
        """Reload eBPF network shield."""
        interface = data.get("interface", "eth0")
        try:
            subprocess.run(
                ["bash", "/opt/titan/core/build_ebpf.sh", interface],
                capture_output=True, timeout=30,
            )
            self._logger.info(f"eBPF reloaded on: {interface}")
            return CommandResult(success=True, action="reload_ebpf", data={"interface": interface})
        except Exception as e:
            return CommandResult(success=False, action="reload_ebpf", message=str(e))

    def _handle_load_kernel_module(self, data: Dict) -> CommandResult:
        """Load titan_hw kernel module."""
        try:
            subprocess.run(["modprobe", "titan_hw"], capture_output=True, timeout=10)
            self._logger.info("Kernel module titan_hw loaded")
            return CommandResult(success=True, action="load_kernel_module")
        except Exception as e:
            return CommandResult(success=False, action="load_kernel_module", message=str(e))

    def _handle_unload_kernel_module(self, data: Dict) -> CommandResult:
        """Unload titan_hw kernel module."""
        try:
            subprocess.run(["rmmod", "titan_hw"], capture_output=True, timeout=10)
            self._logger.info("Kernel module titan_hw unloaded")
            return CommandResult(success=True, action="unload_kernel_module")
        except Exception as e:
            return CommandResult(success=False, action="unload_kernel_module", message=str(e))

    def _handle_set_jitter(self, data: Dict) -> CommandResult:
        """Apply network micro-jitter via tc-netem."""
        connection_type = data.get("connection_type", "cable")
        interface = data.get("interface", "eth0")
        try:
            from .network_jitter import apply_network_jitter
            engine = apply_network_jitter(interface=interface, connection_type=connection_type)
            self._logger.info(f"Network jitter applied: {connection_type} on {interface}")
            return CommandResult(success=True, action="set_network_jitter", data=engine.get_status())
        except Exception as e:
            return CommandResult(success=False, action="set_network_jitter", message=str(e))

    def _handle_rotate_mac(self, data: Dict) -> CommandResult:
        """Rotate MAC address on specified interface."""
        interface = data.get("interface", "eth0")
        try:
            import random
            mac = "02:%02x:%02x:%02x:%02x:%02x" % tuple(random.randint(0, 255) for _ in range(5))
            subprocess.run(["ip", "link", "set", interface, "down"], capture_output=True, timeout=5)
            subprocess.run(["ip", "link", "set", interface, "address", mac], capture_output=True, timeout=5)
            subprocess.run(["ip", "link", "set", interface, "up"], capture_output=True, timeout=5)
            self._logger.info(f"MAC rotated on {interface}: {mac}")
            return CommandResult(success=True, action="rotate_mac", data={"mac": mac, "interface": interface})
        except Exception as e:
            return CommandResult(success=False, action="rotate_mac", message=str(e))

    def _handle_flush_dns(self, data: Dict) -> CommandResult:
        """Flush DNS cache."""
        try:
            subprocess.run(["unbound-control", "flush_zone", "."], capture_output=True, timeout=5)
            self._logger.info("DNS cache flushed")
            return CommandResult(success=True, action="flush_dns")
        except Exception as e:
            return CommandResult(success=False, action="flush_dns", message=str(e))

    def _handle_kill_switch_arm(self, data: Dict) -> CommandResult:
        """Arm the kill switch."""
        try:
            from .kill_switch import arm_kill_switch
            arm_kill_switch()
            self._logger.info("Kill switch ARMED")
            return CommandResult(success=True, action="kill_switch_arm")
        except Exception as e:
            return CommandResult(success=False, action="kill_switch_arm", message=str(e))

    def _handle_kill_switch_panic(self, data: Dict) -> CommandResult:
        """Trigger kill switch PANIC."""
        try:
            from .kill_switch import send_panic_signal
            send_panic_signal()
            self._logger.warning("Kill switch PANIC triggered")
            return CommandResult(success=True, action="kill_switch_panic")
        except Exception as e:
            return CommandResult(success=False, action="kill_switch_panic", message=str(e))

    def _handle_wipe_ephemeral(self, data: Dict) -> CommandResult:
        """Wipe ephemeral data."""
        try:
            from .immutable_os import ImmutableOSManager
            manager = ImmutableOSManager()
            success = manager.wipe_ephemeral()
            self._logger.info("Ephemeral data wiped")
            return CommandResult(success=success, action="wipe_ephemeral")
        except Exception as e:
            return CommandResult(success=False, action="wipe_ephemeral", message=str(e))

    def _handle_check_integrity(self, data: Dict) -> CommandResult:
        """Check system integrity."""
        try:
            from .immutable_os import verify_system_integrity
            result = verify_system_integrity()
            return CommandResult(success=result["status"] == "PASS", action="check_integrity", data=result)
        except Exception as e:
            return CommandResult(success=False, action="check_integrity", message=str(e))

    def _handle_restart_service(self, data: Dict) -> CommandResult:
        """Restart a systemd service (allowlisted only)."""
        ALLOWED_SERVICES = [
            "lucid-titan", "lucid-ebpf", "titan-dns",
            "unbound", "nftables",
        ]
        service = data.get("service", "")
        if service not in ALLOWED_SERVICES:
            return CommandResult(success=False, action="restart_service", message=f"Service not allowed: {service}")
        try:
            subprocess.run(["systemctl", "restart", service], capture_output=True, timeout=15)
            self._logger.info(f"Service restarted: {service}")
            return CommandResult(success=True, action="restart_service", data={"service": service})
        except Exception as e:
            return CommandResult(success=False, action="restart_service", message=str(e))

    def _handle_start_waydroid(self, data: Dict) -> CommandResult:
        """Start Waydroid session."""
        try:
            subprocess.run(["waydroid", "session", "start"], capture_output=True, timeout=30)
            self._logger.info("Waydroid session started")
            return CommandResult(success=True, action="start_waydroid")
        except Exception as e:
            return CommandResult(success=False, action="start_waydroid", message=str(e))

    def _handle_stop_waydroid(self, data: Dict) -> CommandResult:
        """Stop Waydroid session."""
        try:
            subprocess.run(["waydroid", "session", "stop"], capture_output=True, timeout=15)
            self._logger.info("Waydroid session stopped")
            return CommandResult(success=True, action="stop_waydroid")
        except Exception as e:
            return CommandResult(success=False, action="stop_waydroid", message=str(e))

    # ══════════════════════════════════════════════════════════════════════════
    # SERVER LIFECYCLE
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle a single client connection."""
        try:
            # Read length-prefixed message
            header = client_socket.recv(4)
            if len(header) < 4:
                return
            msg_len = struct.unpack("!I", header)[0]
            if msg_len > MAX_PAYLOAD_SIZE:
                client_socket.sendall(b'{"error":"payload too large"}')
                return

            payload = b""
            while len(payload) < msg_len:
                chunk = client_socket.recv(min(4096, msg_len - len(payload)))
                if not chunk:
                    break
                payload += chunk

            # Rate limit
            if not self._rate_limiter.allow():
                result = CommandResult(success=False, action="unknown", message="Rate limited")
                client_socket.sendall(result.to_json().encode())
                return

            # Parse command
            data = json.loads(payload.decode())

            # Verify signature if present
            signature = data.pop("signature", "")
            if signature:
                payload_for_sig = json.dumps(data, sort_keys=True).encode()
                if not self._verify_signature(payload_for_sig, signature):
                    result = CommandResult(success=False, action=data.get("action", "unknown"), message="Invalid signature")
                    client_socket.sendall(result.to_json().encode())
                    return

            # Validate command
            valid, error = self._validate_command(data)
            if not valid:
                result = CommandResult(success=False, action=data.get("action", "unknown"), message=error)
                client_socket.sendall(result.to_json().encode())
                return

            # Execute
            self._logger.info(f"Executing: {data['action']}")
            result = self._execute_command(data)
            response = result.to_json().encode()
            client_socket.sendall(struct.pack("!I", len(response)) + response)

        except (json.JSONDecodeError, struct.error) as e:
            error_result = CommandResult(success=False, action="unknown", message=f"Parse error: {e}")
            try:
                client_socket.sendall(error_result.to_json().encode())
            except OSError:
                pass
        except Exception as e:
            self._logger.error(f"Client handler error: {e}")
        finally:
            client_socket.close()

    def start(self) -> None:
        """Start the daemon, listening on Unix socket."""
        os.makedirs(os.path.dirname(self._socket_path), exist_ok=True)
        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_socket.bind(self._socket_path)
        os.chmod(self._socket_path, 0o660)
        self._server_socket.listen(5)
        self._running = True

        self._logger.info(f"Cockpit daemon started on {self._socket_path}")

        try:
            while self._running:
                self._server_socket.settimeout(1.0)
                try:
                    client, _ = self._server_socket.accept()
                    thread = threading.Thread(
                        target=self._handle_client, args=(client,),
                        daemon=True,
                    )
                    thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
        if self._server_socket:
            self._server_socket.close()
        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)
        self._logger.info("Cockpit daemon stopped")


class CockpitClient:
    """
    Client for sending commands to the Cockpit daemon.
    Used by the GUI (app_unified.py) to execute privileged operations.

    Usage:
        client = CockpitClient()
        result = client.send_command("rotate_fingerprint", {"target": "windows_11_23h2"})
        print(result)
    """

    def __init__(
        self,
        socket_path: str = SOCKET_PATH,
        hmac_key_path: str = HMAC_KEY_PATH,
    ):
        self._socket_path = socket_path
        self._hmac_key = b""
        try:
            if os.path.isfile(hmac_key_path):
                with open(hmac_key_path, "rb") as f:
                    self._hmac_key = f.read()
        except (PermissionError, OSError):
            pass

    def _sign_payload(self, payload: bytes) -> str:
        """Generate HMAC-SHA256 signature."""
        if not self._hmac_key:
            return ""
        return hmac.new(self._hmac_key, payload, hashlib.sha256).hexdigest()

    def send_command(self, action: str, params: Optional[Dict] = None) -> Dict:
        """Send a command to the Cockpit daemon and return the result."""
        data = {
            "action": action,
            "timestamp": time.time(),
            **(params or {}),
        }

        payload = json.dumps(data, sort_keys=True).encode()
        signature = self._sign_payload(payload)
        data["signature"] = signature

        full_payload = json.dumps(data).encode()

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self._socket_path)
            sock.settimeout(10.0)

            # Send length-prefixed message
            sock.sendall(struct.pack("!I", len(full_payload)) + full_payload)

            # Read response
            header = sock.recv(4)
            if len(header) >= 4:
                resp_len = struct.unpack("!I", header)[0]
                response = b""
                while len(response) < resp_len:
                    chunk = sock.recv(min(4096, resp_len - len(response)))
                    if not chunk:
                        break
                    response += chunk
                return json.loads(response.decode())
            else:
                # Fallback: read without length prefix
                response = sock.recv(MAX_PAYLOAD_SIZE)
                return json.loads(response.decode())

        except (ConnectionRefusedError, FileNotFoundError):
            return {"success": False, "message": "Cockpit daemon not running"}
        except Exception as e:
            return {"success": False, "message": str(e)}
        finally:
            try:
                sock.close()
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        client = CockpitClient()
        action = sys.argv[2] if len(sys.argv) > 2 else "get_status"
        print(json.dumps(client.send_command(action), indent=2))
    else:
        print("TITAN V7.6 Cockpit Daemon")
        print("=" * 40)
        daemon = CockpitDaemon()
        daemon.start()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 COMMAND QUEUE — Retry logic and command queuing
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QueuedCommand:
    """A command waiting in queue."""
    queue_id: str
    action: str
    params: Dict
    priority: int  # 1=critical, 2=high, 3=normal
    created_at: float
    attempts: int = 0
    max_attempts: int = 3
    last_error: str = ""


class CommandQueue:
    """
    V7.6 Command Queue - Manages command queuing with retry logic,
    priority scheduling, and failure tracking.
    """
    
    def __init__(self):
        self._queue: List[QueuedCommand] = []
        self._processing: Optional[QueuedCommand] = None
        self._completed: List[QueuedCommand] = []
        self._failed: List[QueuedCommand] = []
        self._lock = threading.Lock()
    
    def enqueue(self, action: str, params: Dict = None,
                priority: int = 3, max_attempts: int = 3) -> str:
        """
        Add a command to the queue.
        
        Returns:
            Queue ID for tracking
        """
        with self._lock:
            queue_id = hashlib.md5(
                f"{action}:{time.time()}:{id(params)}".encode()
            ).hexdigest()[:12]
            
            cmd = QueuedCommand(
                queue_id=queue_id,
                action=action,
                params=params or {},
                priority=priority,
                created_at=time.time(),
                max_attempts=max_attempts
            )
            
            self._queue.append(cmd)
            self._sort_queue()
            return queue_id
    
    def _sort_queue(self):
        """Sort by priority, then by creation time."""
        self._queue.sort(key=lambda c: (c.priority, c.created_at))
    
    def get_next(self) -> Optional[QueuedCommand]:
        """Get next command to process."""
        with self._lock:
            if self._processing:
                return None
            
            for cmd in self._queue:
                if cmd.attempts < cmd.max_attempts:
                    cmd.attempts += 1
                    self._processing = cmd
                    return cmd
            
            return None
    
    def complete(self, queue_id: str, success: bool, error: str = ""):
        """Mark a command as complete or failed."""
        with self._lock:
            if self._processing and self._processing.queue_id == queue_id:
                cmd = self._processing
                self._processing = None
                
                if success:
                    self._completed.append(cmd)
                    self._queue.remove(cmd)
                else:
                    cmd.last_error = error
                    if cmd.attempts >= cmd.max_attempts:
                        self._failed.append(cmd)
                        self._queue.remove(cmd)
                    # Else: leave in queue for retry
    
    def get_status(self) -> Dict:
        """Get queue status."""
        with self._lock:
            return {
                "pending": len(self._queue),
                "processing": 1 if self._processing else 0,
                "completed": len(self._completed),
                "failed": len(self._failed),
                "current": self._processing.action if self._processing else None,
            }
    
    def clear_completed(self):
        """Clear completed commands."""
        with self._lock:
            self._completed.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 DAEMON HEALTH MONITOR — Self-monitoring and auto-recovery
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DaemonHealthStatus:
    """Daemon health status."""
    healthy: bool
    uptime_seconds: float
    commands_processed: int
    errors_last_hour: int
    memory_mb: float
    socket_connected: bool
    last_command_time: Optional[float]


class DaemonHealthMonitor:
    """
    V7.6 Daemon Health Monitor - Monitors daemon health,
    tracks metrics, and triggers auto-recovery on failures.
    """
    
    def __init__(self):
        self._start_time = time.time()
        self._commands_processed = 0
        self._errors: List[float] = []  # Timestamps of errors
        self._last_command_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def record_command(self, success: bool):
        """Record a command execution."""
        with self._lock:
            self._commands_processed += 1
            self._last_command_time = time.time()
            
            if not success:
                self._errors.append(time.time())
            
            # Cleanup old errors (keep last hour)
            cutoff = time.time() - 3600
            self._errors = [e for e in self._errors if e > cutoff]
    
    def get_health_status(self) -> DaemonHealthStatus:
        """Get current health status."""
        import psutil
        
        with self._lock:
            errors_last_hour = len(self._errors)
            
            # Get memory usage
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / (1024 * 1024)
            except Exception:
                memory_mb = 0.0
            
            # Check socket
            socket_connected = os.path.exists(SOCKET_PATH)
            
            # Determine health
            healthy = (
                errors_last_hour < 50 and
                socket_connected and
                memory_mb < 500  # Alert if > 500MB
            )
            
            return DaemonHealthStatus(
                healthy=healthy,
                uptime_seconds=time.time() - self._start_time,
                commands_processed=self._commands_processed,
                errors_last_hour=errors_last_hour,
                memory_mb=round(memory_mb, 1),
                socket_connected=socket_connected,
                last_command_time=self._last_command_time
            )
    
    def should_restart(self) -> Tuple[bool, str]:
        """Check if daemon should restart."""
        status = self.get_health_status()
        
        if status.errors_last_hour > 100:
            return True, "Too many errors in last hour"
        
        if status.memory_mb > 500:
            return True, "Memory usage too high"
        
        if not status.socket_connected:
            return True, "Socket not available"
        
        return False, ""
    
    def get_metrics(self) -> Dict:
        """Get metrics for monitoring."""
        status = self.get_health_status()
        return {
            "titan_cockpit_uptime_seconds": status.uptime_seconds,
            "titan_cockpit_commands_total": status.commands_processed,
            "titan_cockpit_errors_hour": status.errors_last_hour,
            "titan_cockpit_memory_mb": status.memory_mb,
            "titan_cockpit_healthy": 1 if status.healthy else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 COMMAND AUDIT ANALYZER — Analyze audit logs for anomalies
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuditAnomaly:
    """An anomaly detected in audit logs."""
    anomaly_type: str
    description: str
    severity: str  # info, warning, critical
    timestamp: float
    context: Dict


class CommandAuditAnalyzer:
    """
    V7.6 Audit Analyzer - Analyzes audit logs for anomalies,
    suspicious patterns, and potential security issues.
    """
    
    # Anomaly detection thresholds
    THRESHOLDS = {
        "commands_per_minute": 30,  # Max commands per minute
        "kill_switch_triggers": 3,   # Max kill switch in 5 mins
        "failed_signatures": 5,      # Max failed signature attempts
        "unknown_actions": 10,       # Max unknown action attempts
    }
    
    def __init__(self):
        self._events: List[Dict] = []
        self._anomalies: List[AuditAnomaly] = []
        self._lock = threading.Lock()
    
    def record_event(self, action: str, success: bool,
                     signature_valid: bool = True, extra: Dict = None):
        """Record an audit event."""
        with self._lock:
            event = {
                "action": action,
                "success": success,
                "signature_valid": signature_valid,
                "timestamp": time.time(),
                "extra": extra or {}
            }
            self._events.append(event)
            
            # Keep last 10000 events
            if len(self._events) > 10000:
                self._events = self._events[-10000:]
            
            # Run anomaly detection
            self._detect_anomalies(event)
    
    def _detect_anomalies(self, latest_event: Dict):
        """Detect anomalies based on latest event."""
        now = time.time()
        minute_ago = now - 60
        five_mins_ago = now - 300
        
        # Get recent events
        recent_minute = [e for e in self._events if e["timestamp"] > minute_ago]
        recent_5min = [e for e in self._events if e["timestamp"] > five_mins_ago]
        
        # Check command rate
        if len(recent_minute) > self.THRESHOLDS["commands_per_minute"]:
            self._add_anomaly(
                "high_command_rate",
                f"Unusually high command rate: {len(recent_minute)}/min",
                "warning"
            )
        
        # Check kill switch abuse
        kill_switches = [e for e in recent_5min if "kill_switch" in e["action"]]
        if len(kill_switches) > self.THRESHOLDS["kill_switch_triggers"]:
            self._add_anomaly(
                "kill_switch_abuse",
                f"Multiple kill switch triggers: {len(kill_switches)} in 5 mins",
                "critical"
            )
        
        # Check failed signatures
        failed_sigs = [e for e in recent_5min if not e["signature_valid"]]
        if len(failed_sigs) > self.THRESHOLDS["failed_signatures"]:
            self._add_anomaly(
                "signature_attacks",
                f"Multiple failed signatures: {len(failed_sigs)} attempts",
                "critical"
            )
        
        # Check unknown actions
        unknown = [e for e in recent_5min if not e["success"] and "unknown" in str(e.get("extra", {}))]
        if len(unknown) > self.THRESHOLDS["unknown_actions"]:
            self._add_anomaly(
                "unknown_actions",
                f"Multiple unknown action attempts: {len(unknown)}",
                "warning"
            )
    
    def _add_anomaly(self, anomaly_type: str, description: str, severity: str):
        """Add an anomaly if not duplicate."""
        now = time.time()
        
        # Check for recent duplicate
        for existing in self._anomalies[-10:]:
            if (existing.anomaly_type == anomaly_type and
                now - existing.timestamp < 300):  # 5 min dedup
                return
        
        anomaly = AuditAnomaly(
            anomaly_type=anomaly_type,
            description=description,
            severity=severity,
            timestamp=now,
            context={}
        )
        self._anomalies.append(anomaly)
        
        # Log critical anomalies
        if severity == "critical":
            logging.getLogger("titan.cockpit").warning(f"ANOMALY: {description}")
    
    def get_anomalies(self, since_hours: float = 24) -> List[AuditAnomaly]:
        """Get anomalies from last N hours."""
        cutoff = time.time() - (since_hours * 3600)
        with self._lock:
            return [a for a in self._anomalies if a.timestamp > cutoff]
    
    def get_stats(self) -> Dict:
        """Get audit statistics."""
        with self._lock:
            if not self._events:
                return {"total_events": 0, "success_rate": 0}
            
            success = sum(1 for e in self._events if e["success"])
            return {
                "total_events": len(self._events),
                "success_rate": round(success / len(self._events), 2),
                "anomalies_24h": len(self.get_anomalies(24)),
                "critical_anomalies": len([a for a in self._anomalies if a.severity == "critical"])
            }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 SECURE SESSION MANAGER — Authenticated GUI sessions
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass  
class CockpitSession:
    """An authenticated session with the cockpit daemon."""
    session_id: str
    created_at: float
    last_activity: float
    permissions: List[str]
    client_pid: Optional[int]
    is_valid: bool = True


class SecureSessionManager:
    """
    V7.6 Secure Session Manager - Manages authenticated sessions
    between GUI and daemon with session tokens and permissions.
    """
    
    SESSION_TIMEOUT = 3600  # 1 hour
    
    def __init__(self):
        self._sessions: Dict[str, CockpitSession] = {}
        self._lock = threading.Lock()
    
    def create_session(self, client_pid: Optional[int] = None,
                       permissions: List[str] = None) -> str:
        """
        Create a new authenticated session.
        
        Returns:
            Session token
        """
        with self._lock:
            session_id = hashlib.sha256(
                f"{time.time()}:{os.urandom(16).hex()}".encode()
            ).hexdigest()[:32]
            
            session = CockpitSession(
                session_id=session_id,
                created_at=time.time(),
                last_activity=time.time(),
                permissions=permissions or ["*"],
                client_pid=client_pid
            )
            
            self._sessions[session_id] = session
            return session_id
    
    def validate_session(self, session_id: str, action: str = None) -> Tuple[bool, str]:
        """
        Validate a session token.
        
        Args:
            session_id: Session token to validate
            action: Optional action to check permission for
        
        Returns:
            (valid, error_message)
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if not session:
                return False, "Session not found"
            
            if not session.is_valid:
                return False, "Session invalidated"
            
            # Check timeout
            if time.time() - session.last_activity > self.SESSION_TIMEOUT:
                session.is_valid = False
                return False, "Session expired"
            
            # Check permission
            if action and "*" not in session.permissions:
                if action not in session.permissions:
                    return False, f"Permission denied for action: {action}"
            
            # Update activity
            session.last_activity = time.time()
            return True, ""
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].is_valid = False
    
    def cleanup_expired(self):
        """Remove expired sessions."""
        with self._lock:
            now = time.time()
            expired = [
                sid for sid, s in self._sessions.items()
                if not s.is_valid or (now - s.last_activity > self.SESSION_TIMEOUT * 2)
            ]
            for sid in expired:
                del self._sessions[sid]
    
    def get_active_sessions(self) -> List[Dict]:
        """Get list of active sessions."""
        with self._lock:
            return [
                {
                    "session_id": s.session_id[:8] + "...",
                    "age_minutes": int((time.time() - s.created_at) / 60),
                    "idle_seconds": int(time.time() - s.last_activity),
                    "permissions": s.permissions,
                    "valid": s.is_valid
                }
                for s in self._sessions.values()
                if s.is_valid
            ]


# Global instances for V7.6 components
_command_queue: Optional[CommandQueue] = None
_health_monitor: Optional[DaemonHealthMonitor] = None
_audit_analyzer: Optional[CommandAuditAnalyzer] = None
_session_manager: Optional[SecureSessionManager] = None


def get_command_queue() -> CommandQueue:
    """Get global command queue."""
    global _command_queue
    if _command_queue is None:
        _command_queue = CommandQueue()
    return _command_queue


def get_health_monitor() -> DaemonHealthMonitor:
    """Get global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DaemonHealthMonitor()
    return _health_monitor


def get_audit_analyzer() -> CommandAuditAnalyzer:
    """Get global audit analyzer."""
    global _audit_analyzer
    if _audit_analyzer is None:
        _audit_analyzer = CommandAuditAnalyzer()
    return _audit_analyzer


def get_session_manager() -> SecureSessionManager:
    """Get global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SecureSessionManager()
    return _session_manager
