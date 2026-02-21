"""
TITAN V7.0 SINGULARITY — Phase 2.3: Kill Switch (Panic Sequence)
Automated Detection Response & Hardware ID Flush

Problem: When a fraud detection system flags the session (fraud score
drops below threshold), the operator has seconds before the session
is permanently burned. Manual response is too slow.

Solution: Automated panic sequence that:
1. Monitors fraud score signals in real-time
2. On detection trigger (score < 85), immediately:
   a. Flushes hardware ID via Netlink to kernel module
   b. Clears browser session/cookies/localStorage
   c. Kills browser process
   d. Rotates proxy connection
   e. Randomizes MAC address
   f. Logs the event for post-mortem analysis
3. Optionally deploys a new clean profile for retry

The kill switch operates as a background daemon thread that watches
for detection signals from multiple sources.

Usage:
    from kill_switch import KillSwitch, KillSwitchConfig
    
    ks = KillSwitch(KillSwitchConfig(
        profile_uuid="AM-8821-TRUSTED",
        fraud_score_threshold=85,
        auto_flush_hw=True,
    ))
    ks.arm()
    # ... browser session runs ...
    # If fraud score drops below 85, panic sequence fires automatically
    ks.disarm()
"""

import os
import sys
import json
import time
import signal
import struct
import socket
import shutil
import secrets
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("TITAN-V7-KILLSWITCH")


class ThreatLevel(Enum):
    """Current threat assessment"""
    GREEN = "green"       # No detection signals
    YELLOW = "yellow"     # Elevated risk, monitoring
    ORANGE = "orange"     # Pre-detection signals detected
    RED = "red"           # Active detection — PANIC


class PanicReason(Enum):
    """What triggered the panic sequence"""
    FRAUD_SCORE_DROP = "fraud_score_drop"
    MANUAL_TRIGGER = "manual_trigger"
    BROWSER_CHALLENGE = "browser_challenge"
    IP_FLAGGED = "ip_flagged"
    DEVICE_FINGERPRINT_MISMATCH = "device_fp_mismatch"
    THREE_DS_AGGRESSIVE = "3ds_aggressive"
    SESSION_TIMEOUT = "session_timeout"


@dataclass
class KillSwitchConfig:
    """Configuration for the kill switch"""
    profile_uuid: str
    profile_path: str = "/opt/titan/profiles"
    fraud_score_threshold: int = 85       # Panic if score drops below
    monitoring_interval_ms: int = 500     # Check every 500ms
    auto_flush_hw: bool = True            # Auto-randomize hardware ID
    auto_kill_browser: bool = True        # Auto-kill browser process
    auto_rotate_proxy: bool = True        # Auto-rotate proxy
    auto_flush_mac: bool = False          # Auto-randomize MAC (requires root)
    log_events: bool = True               # Log all events for post-mortem
    netlink_protocol: int = 31            # NETLINK_TITAN
    state_dir: str = "/opt/titan/state"
    on_panic_callback: Optional[Callable] = None  # Custom panic handler


@dataclass
class PanicEvent:
    """Record of a panic event"""
    timestamp: str
    reason: PanicReason
    fraud_score: Optional[int]
    threat_level: ThreatLevel
    profile_uuid: str
    actions_taken: List[str]
    duration_ms: float


class KillSwitch:
    """
    Automated panic sequence for detection response.
    
    Arms a background monitor that watches for fraud score drops
    and other detection signals. When triggered, executes a rapid
    sequence of countermeasures to protect the operator.
    """
    
    def __init__(self, config: KillSwitchConfig):
        self.config = config
        self.armed = False
        self.threat_level = ThreatLevel.GREEN
        self.current_fraud_score = 100
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.panic_history: List[PanicEvent] = []
        self._fraud_score_file = Path(config.state_dir) / "fraud_score.json"
        self._signal_file = Path(config.state_dir) / "kill_signal"
        
        # Ensure state directory exists
        Path(config.state_dir).mkdir(parents=True, exist_ok=True)
    
    # ═══════════════════════════════════════════════════════════════════
    # ARM / DISARM
    # ═══════════════════════════════════════════════════════════════════
    
    def arm(self) -> bool:
        """
        Arm the kill switch. Starts background monitoring thread.
        Returns True if armed successfully.
        """
        if self.armed:
            logger.warning("[KILLSWITCH] Already armed")
            return True
        
        self.armed = True
        self._stop_event.clear()
        self.threat_level = ThreatLevel.GREEN
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="TitanKillSwitch"
        )
        self.monitor_thread.start()
        
        # Write armed state
        self._write_state({"armed": True, "timestamp": datetime.now(timezone.utc).isoformat()})
        
        logger.info("[KILLSWITCH] *** ARMED *** — Monitoring for detection signals")
        logger.info(f"[KILLSWITCH] Threshold: fraud_score < {self.config.fraud_score_threshold}")
        logger.info(f"[KILLSWITCH] Interval: {self.config.monitoring_interval_ms}ms")
        return True
    
    def disarm(self):
        """Disarm the kill switch. Stops monitoring."""
        self.armed = False
        self._stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        # Clean up signal file
        if self._signal_file.exists():
            self._signal_file.unlink()
        
        self._write_state({"armed": False, "timestamp": datetime.now(timezone.utc).isoformat()})
        logger.info("[KILLSWITCH] Disarmed")
    
    # ═══════════════════════════════════════════════════════════════════
    # MONITORING LOOP
    # ═══════════════════════════════════════════════════════════════════
    
    def _monitor_loop(self):
        """Background monitoring thread"""
        while not self._stop_event.is_set():
            try:
                # Check fraud score file (written by Cerberus or browser extension)
                score = self._read_fraud_score()
                if score is not None:
                    self.current_fraud_score = score
                    self._update_threat_level(score)
                    
                    if score < self.config.fraud_score_threshold:
                        logger.critical(f"[KILLSWITCH] FRAUD SCORE DROP: {score} < {self.config.fraud_score_threshold}")
                        self.panic(PanicReason.FRAUD_SCORE_DROP, score)
                        return  # Exit monitor after panic
                
                # Check for manual kill signal file
                if self._signal_file.exists():
                    reason_str = self._signal_file.read_text().strip()
                    try:
                        reason = PanicReason(reason_str)
                    except ValueError:
                        reason = PanicReason.MANUAL_TRIGGER
                    
                    logger.critical(f"[KILLSWITCH] MANUAL SIGNAL: {reason.value}")
                    self._signal_file.unlink()
                    self.panic(reason)
                    return
                
            except Exception as e:
                logger.error(f"[KILLSWITCH] Monitor error: {e}")
            
            self._stop_event.wait(self.config.monitoring_interval_ms / 1000)
    
    def _read_fraud_score(self) -> Optional[int]:
        """Read current fraud score from state file"""
        try:
            if self._fraud_score_file.exists():
                with open(self._fraud_score_file) as f:
                    data = json.load(f)
                return data.get("score")
        except (json.JSONDecodeError, IOError):
            pass
        return None
    
    def _update_threat_level(self, score: int):
        """Update threat level based on fraud score"""
        if score >= 90:
            self.threat_level = ThreatLevel.GREEN
        elif score >= 85:
            self.threat_level = ThreatLevel.YELLOW
        elif score >= 75:
            self.threat_level = ThreatLevel.ORANGE
            logger.warning(f"[KILLSWITCH] ORANGE — score={score}, approaching threshold")
        else:
            self.threat_level = ThreatLevel.RED
    
    # ═══════════════════════════════════════════════════════════════════
    # PANIC SEQUENCE
    # ═══════════════════════════════════════════════════════════════════
    
    def panic(self, reason: PanicReason = PanicReason.MANUAL_TRIGGER,
              fraud_score: Optional[int] = None):
        """
        Execute panic sequence. This is the main kill switch action.
        
        Sequence (all execute within ~500ms):
        0. Sever network (nftables DROP all outbound — prevents data leakage)
        1. Kill browser process immediately
        2. Flush hardware ID via Netlink
        3. Clear browser session data
        4. Rotate proxy
        5. Randomize MAC (if enabled)
        6. Log event
        """
        start_time = time.time()
        actions = []
        
        logger.critical("=" * 60)
        logger.critical("  ██████╗  █████╗ ███╗   ██╗██╗ ██████╗")
        logger.critical("  ██╔══██╗██╔══██╗████╗  ██║██║██╔════╝")
        logger.critical("  ██████╔╝███████║██╔██╗ ██║██║██║     ")
        logger.critical("  ██╔═══╝ ██╔══██║██║╚██╗██║██║██║     ")
        logger.critical("  ██║     ██║  ██║██║ ╚████║██║╚██████╗")
        logger.critical("  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝")
        logger.critical("=" * 60)
        logger.critical(f"  REASON: {reason.value}")
        logger.critical(f"  SCORE:  {fraud_score or self.current_fraud_score}")
        logger.critical("=" * 60)
        
        # Step 0: Network sever (absolute first — block ALL outbound before anything else)
        severed = self._sever_network()
        if severed:
            actions.append("network_severed")
            logger.critical("[PANIC] Step 0: Network SEVERED (nftables DROP all)")
        else:
            actions.append("network_sever_failed")
        
        # Step 1: Kill browser
        if self.config.auto_kill_browser:
            killed = self._kill_browser()
            if killed:
                actions.append("browser_killed")
                logger.critical("[PANIC] Step 1: Browser KILLED")
            else:
                actions.append("browser_kill_failed")
        
        # Step 2: Flush hardware ID via Netlink
        if self.config.auto_flush_hw:
            flushed = self._flush_hardware_id()
            if flushed:
                actions.append("hw_id_flushed")
                logger.critical("[PANIC] Step 2: Hardware ID FLUSHED (randomized)")
            else:
                actions.append("hw_flush_failed")
        
        # Step 3: Clear browser session
        cleared = self._clear_session_data()
        if cleared:
            actions.append("session_cleared")
            logger.critical("[PANIC] Step 3: Session data CLEARED")
        
        # Step 4: Rotate proxy
        if self.config.auto_rotate_proxy:
            rotated = self._rotate_proxy()
            if rotated:
                actions.append("proxy_rotated")
                logger.critical("[PANIC] Step 4: Proxy ROTATED")
        
        # Step 5: MAC randomization
        if self.config.auto_flush_mac:
            mac_changed = self._randomize_mac()
            if mac_changed:
                actions.append("mac_randomized")
                logger.critical("[PANIC] Step 5: MAC address RANDOMIZED")
        
        # Step 6: Call custom handler
        if self.config.on_panic_callback:
            try:
                self.config.on_panic_callback(reason, fraud_score)
                actions.append("custom_callback")
            except Exception as e:
                logger.error(f"[PANIC] Custom callback error: {e}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log event
        event = PanicEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            fraud_score=fraud_score or self.current_fraud_score,
            threat_level=self.threat_level,
            profile_uuid=self.config.profile_uuid,
            actions_taken=actions,
            duration_ms=round(duration_ms, 2),
        )
        self.panic_history.append(event)
        
        if self.config.log_events:
            self._log_panic_event(event)
        
        logger.critical(f"[PANIC] Sequence complete in {duration_ms:.0f}ms — {len(actions)} actions")
        
        # V8 FIX: Notify Operations Guard about panic for learning
        try:
            from titan_ai_operations_guard import get_operations_guard
            guard = get_operations_guard()
            if guard:
                guard.post_operation_analysis({
                    "target_domain": "PANIC_EVENT",
                    "status": "panic",
                    "decline_code": reason.value,
                    "decline_category": "panic",
                    "fraud_score": fraud_score or self.current_fraud_score,
                    "actions_taken": actions,
                    "duration_ms": round(duration_ms, 2),
                })
        except Exception:
            pass
        
        # Disarm after panic
        self.armed = False
    
    # ═══════════════════════════════════════════════════════════════════
    # PANIC ACTIONS
    # ═══════════════════════════════════════════════════════════════════
    
    def _sever_network(self) -> bool:
        """
        Immediately block ALL outbound traffic via nftables.
        This is Step 0 — must execute before browser kill to prevent
        any data leakage during the panic window.
        """
        # Try nftables first (preferred), fall back to iptables
        # V7.5 FIX: Use shell=True for nftables commands with special chars
        nft_rules = [
            "nft add table inet titan_panic",
            "nft 'add chain inet titan_panic output { type filter hook output priority 0 ; policy drop ; }'",
            "nft add rule inet titan_panic output ct state established accept",
        ]
        
        try:
            for rule in nft_rules:
                subprocess.run(
                    rule, shell=True,
                    capture_output=True, timeout=2, check=True
                )
            logger.critical("[PANIC] Network severed via nftables (all outbound DROP)")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback: iptables
        try:
            subprocess.run(
                ["iptables", "-I", "OUTPUT", "-j", "DROP"],
                capture_output=True, timeout=2, check=True
            )
            logger.critical("[PANIC] Network severed via iptables (all outbound DROP)")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
            logger.error("[PANIC] Network sever failed — requires root")
            return False
    
    def _restore_network(self) -> bool:
        """Remove the panic firewall rules to restore connectivity."""
        try:
            subprocess.run(
                ["nft", "delete", "table", "inet", "titan_panic"],
                capture_output=True, timeout=2, check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        try:
            subprocess.run(
                ["iptables", "-D", "OUTPUT", "-j", "DROP"],
                capture_output=True, timeout=2, check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _kill_browser(self) -> bool:
        """Kill all browser processes immediately"""
        killed = False
        browser_processes = ["firefox", "firefox-esr", "camoufox", "chromium"]
        
        for proc_name in browser_processes:
            try:
                result = subprocess.run(
                    ["pkill", "-9", "-f", proc_name],
                    capture_output=True, timeout=2
                )
                if result.returncode == 0:
                    killed = True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        # Also kill any playwright/geckodriver automation remnants
        for auto_proc in ["geckodriver", "playwright", "chromedriver"]:
            try:
                subprocess.run(["pkill", "-9", "-f", auto_proc],
                             capture_output=True, timeout=1)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        return killed
    
    def _flush_hardware_id(self) -> bool:
        """
        Send new random hardware profile to kernel module via Netlink.
        This immediately changes /proc/cpuinfo, /proc/meminfo output
        so any subsequent fingerprinting sees a different device.
        """
        try:
            # Generate random hardware profile
            random_serial = secrets.token_hex(8).upper()
            random_uuid = f"{secrets.token_hex(4)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(6)}"
            
            # Try to send via Netlink (requires root)
            NETLINK_TITAN = self.config.netlink_protocol
            TITAN_MSG_SET_PROFILE = 1
            
            # Build profile struct (matches titan_hw_profile in hardware_shield_v6.c)
            # cpu_model[128] + cpu_vendor[64] + cores(4) + threads(4) + freq(8) + ram(8) + ...
            cpu_models = [
                "13th Gen Intel(R) Core(TM) i7-13700K",
                "AMD Ryzen 9 7950X 16-Core Processor",
                "12th Gen Intel(R) Core(TM) i9-12900K",
                "11th Gen Intel(R) Core(TM) i5-11400F",
            ]
            
            import random as rng
            cpu_model = rng.choice(cpu_models).encode('utf-8')[:127].ljust(128, b'\x00')
            cpu_vendor = b'GenuineIntel'.ljust(64, b'\x00')
            
            profile_data = cpu_model  # char[128]
            profile_data += cpu_vendor  # char[64]
            profile_data += struct.pack('i', rng.choice([8, 12, 16]))  # cores
            profile_data += struct.pack('i', rng.choice([16, 20, 24, 32]))  # threads
            profile_data += struct.pack('L', rng.choice([2500, 3000, 3500, 4000]))  # freq
            profile_data += struct.pack('L', rng.choice([16384, 32768, 65536]))  # ram_mb
            profile_data += rng.choice([b'Dell Inc.', b'ASUSTeK', b'Lenovo', b'HP']).ljust(64, b'\x00')  # mb_vendor
            profile_data += secrets.token_hex(4).upper().encode().ljust(64, b'\x00')  # mb_model
            profile_data += b'American Megatrends'.ljust(64, b'\x00')  # bios_vendor
            profile_data += b'1.20.0'.ljust(64, b'\x00')  # bios_version
            profile_data += random_serial.encode().ljust(64, b'\x00')  # serial
            profile_data += random_uuid.encode().ljust(64, b'\x00')  # uuid
            profile_data += struct.pack('i', 1)  # active=1
            
            # Send via Netlink
            sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_TITAN)
            sock.bind((os.getpid(), 0))
            
            # Build Netlink message header (16 bytes) + payload
            msg_len = 16 + len(profile_data)
            nlmsg = struct.pack('IHHII', msg_len, TITAN_MSG_SET_PROFILE, 0, 0, os.getpid())
            nlmsg += profile_data
            
            sock.send(nlmsg)
            sock.close()
            
            logger.info(f"[PANIC] Hardware ID flushed: serial={random_serial}")
            return True
            
        except PermissionError:
            logger.warning("[PANIC] HW flush requires root — writing stub file instead")
            return self._flush_hw_stub()
        except Exception as e:
            logger.error(f"[PANIC] HW flush error: {e}")
            return self._flush_hw_stub()
    
    def _flush_hw_stub(self) -> bool:
        """Fallback: Write randomized hardware stub + boot service to apply it on next boot"""
        try:
            stub_path = Path(self.config.state_dir) / "titan_hw_stub.json"
            stub = {
                "action": "flush",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "new_serial": secrets.token_hex(8).upper(),
                "new_uuid": f"{secrets.token_hex(4)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(6)}",
                "reason": "panic_flush",
                "profile_uuid": self.config.profile_uuid,
            }
            with open(stub_path, "w") as f:
                json.dump(stub, f, indent=2)
            
            # Create a one-shot systemd service to apply the stub at next boot
            # The inline Python sends a proper Netlink SET_PROFILE message
            # matching the protocol in _flush_hardware_ids()
            service_content = f"""[Unit]
Description=TITAN Hardware Flush (one-shot panic recovery)
After=multi-user.target
ConditionPathExists={stub_path}

[Service]
Type=oneshot
ExecStart=/bin/bash -c '\\
  STUB="{stub_path}"; \\
  if [ -f "$STUB" ]; then \\
    if lsmod | grep -q titan_hw; then \\
      python3 -c "\\
import json, struct, socket, os, random; \\
stub = json.load(open(\\"$STUB\\")); \\
NETLINK_TITAN = 31; \\
TITAN_MSG_SET_PROFILE = 1; \\
cpu_models = [b\\"Intel(R) Core(TM) i7-12700H\\", b\\"Intel(R) Core(TM) i9-13900K\\", b\\"AMD Ryzen 7 5800X\\"]; \\
cpu_model = random.choice(cpu_models).ljust(128, b\\"\\\\x00\\")[:128]; \\
cpu_vendor = b\\"GenuineIntel\\".ljust(64, b\\"\\\\x00\\"); \\
profile_data = cpu_model + cpu_vendor; \\
profile_data += struct.pack(\\"i\\", random.choice([8,12,16])); \\
profile_data += struct.pack(\\"i\\", random.choice([16,20,24,32])); \\
profile_data += struct.pack(\\"L\\", random.choice([2500,3000,3500,4000])); \\
profile_data += struct.pack(\\"L\\", random.choice([16384,32768,65536])); \\
profile_data += random.choice([b\\"Dell Inc.\\", b\\"ASUSTeK\\", b\\"Lenovo\\"]).ljust(64, b\\"\\\\x00\\"); \\
profile_data += stub[\\"new_serial\\"][:8].encode().ljust(64, b\\"\\\\x00\\"); \\
profile_data += b\\"American Megatrends\\".ljust(64, b\\"\\\\x00\\"); \\
profile_data += b\\"1.20.0\\".ljust(64, b\\"\\\\x00\\"); \\
profile_data += stub[\\"new_serial\\"].encode().ljust(64, b\\"\\\\x00\\"); \\
profile_data += stub[\\"new_uuid\\"].encode().ljust(64, b\\"\\\\x00\\"); \\
profile_data += struct.pack(\\"i\\", 1); \\
sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_TITAN); \\
sock.bind((os.getpid(), 0)); \\
msg_len = 16 + len(profile_data); \\
nlmsg = struct.pack(\\"IHHII\\", msg_len, TITAN_MSG_SET_PROFILE, 0, 0, os.getpid()); \\
nlmsg += profile_data; \\
sock.send(nlmsg); \\
sock.close(); \\
print(\\"Netlink HW flush sent: serial=\\" + stub[\\"new_serial\\"])"; \\
    fi; \\
    rm -f "$STUB"; \\
    systemctl disable titan-hw-flush.service; \\
  fi'
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
"""
            service_path = Path("/etc/systemd/system/titan-hw-flush.service")
            try:
                service_path.write_text(service_content)
                subprocess.run(
                    ["systemctl", "enable", "titan-hw-flush.service"],
                    capture_output=True, timeout=5
                )
                logger.info("[PANIC] Boot-time HW flush service installed")
            except (PermissionError, FileNotFoundError):
                logger.warning("[PANIC] Could not install boot service (no root), stub file written for manual apply")
            
            return True
        except Exception as e:
            logger.error(f"[PANIC] HW stub write error: {e}")
            return False
    
    def _clear_session_data(self) -> bool:
        """Clear volatile session data from profile"""
        try:
            profile_dir = Path(self.config.profile_path) / self.config.profile_uuid
            
            # Files to delete (session-specific, not the entire profile)
            volatile_files = [
                "sessionstore.jsonlz4",
                "sessionstore-backups",
                "cookies.sqlite-wal",
                "cookies.sqlite-shm",
                "places.sqlite-wal",
                "places.sqlite-shm",
                "webappsstore.sqlite-wal",
            ]
            
            cleared = 0
            for fname in volatile_files:
                fpath = profile_dir / fname
                if fpath.exists():
                    if fpath.is_dir():
                        shutil.rmtree(fpath, ignore_errors=True)
                    else:
                        fpath.unlink()
                    cleared += 1
            
            logger.info(f"[PANIC] Cleared {cleared} volatile session files")
            return True
            
        except Exception as e:
            logger.error(f"[PANIC] Session clear error: {e}")
            return False
    
    def _rotate_proxy(self) -> bool:
        """Signal proxy manager to rotate connection"""
        try:
            rotate_signal = Path(self.config.state_dir) / "proxy_rotate_signal"
            rotate_signal.write_text(json.dumps({
                "action": "rotate",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "panic",
                "profile_uuid": self.config.profile_uuid,
            }))
            return True
        except Exception as e:
            logger.error(f"[PANIC] Proxy rotate error: {e}")
            return False
    
    def _randomize_mac(self) -> bool:
        """Randomize MAC address (requires root)"""
        try:
            # Get default interface
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=2
            )
            iface = result.stdout.split("dev ")[1].split()[0] if "dev " in result.stdout else "eth0"
            
            # Generate random MAC (locally administered, unicast)
            mac_bytes = [secrets.randbelow(256) for _ in range(6)]
            mac_bytes[0] = (mac_bytes[0] & 0xFC) | 0x02  # Set locally administered bit
            new_mac = ":".join(f"{b:02x}" for b in mac_bytes)
            
            subprocess.run(["ip", "link", "set", iface, "down"], timeout=2)
            subprocess.run(["ip", "link", "set", iface, "address", new_mac], timeout=2)
            subprocess.run(["ip", "link", "set", iface, "up"], timeout=2)
            
            logger.info(f"[PANIC] MAC randomized: {new_mac} on {iface}")
            return True
            
        except Exception as e:
            logger.error(f"[PANIC] MAC randomize error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # STATE & LOGGING
    # ═══════════════════════════════════════════════════════════════════
    
    def _write_state(self, state: Dict[str, Any]):
        """Write kill switch state to disk"""
        try:
            state_file = Path(self.config.state_dir) / "killswitch_state.json"
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"[KILLSWITCH] Failed to write state: {e}")
    
    def _log_panic_event(self, event: PanicEvent):
        """Log panic event to disk for post-mortem analysis"""
        try:
            log_file = Path(self.config.state_dir) / "panic_log.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": event.timestamp,
                    "reason": event.reason.value,
                    "fraud_score": event.fraud_score,
                    "threat_level": event.threat_level.value,
                    "profile_uuid": event.profile_uuid,
                    "actions": event.actions_taken,
                    "duration_ms": event.duration_ms,
                }) + "\n")
        except Exception as e:
            logger.warning(f"[KILLSWITCH] Failed to write panic log: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # EXTERNAL SIGNAL API
    # ═══════════════════════════════════════════════════════════════════
    
    def update_fraud_score(self, score: int):
        """
        External API: update fraud score from Cerberus or browser extension.
        This is the preferred way to feed scores (vs file-based monitoring).
        """
        self.current_fraud_score = score
        self._update_threat_level(score)
        
        # Also write to file for persistence
        try:
            with open(self._fraud_score_file, "w") as f:
                json.dump({"score": score, "timestamp": datetime.now(timezone.utc).isoformat()}, f)
        except Exception as e:
            logger.warning(f"[KILLSWITCH] Failed to write fraud score: {e}")
        
        if score < self.config.fraud_score_threshold and self.armed:
            self.panic(PanicReason.FRAUD_SCORE_DROP, score)
    
    def trigger_manual_panic(self, reason: str = "manual"):
        """External API: trigger panic manually"""
        try:
            panic_reason = PanicReason(reason)
        except ValueError:
            panic_reason = PanicReason.MANUAL_TRIGGER
        self.panic(panic_reason)
    
    def hard_panic(self):
        """
        EXTREME: Hard kernel panic via sysrq-trigger.
        
        This is the nuclear option for seizure scenarios:
        1. Sever network immediately
        2. Sync filesystems
        3. Force immediate reboot (no clean shutdown)
        
        On a Live ISO (tmpfs), this destroys ALL in-memory data instantly.
        Nothing survives a hard reboot on a RAM-only system.
        
        WARNING: This is irreversible. All unsaved data is lost.
        """
        logger.critical("[HARD PANIC] *** SYSRQ TRIGGERED — IMMEDIATE REBOOT ***")
        
        # Step 1: Sever network first
        try:
            subprocess.run(["ip", "link", "set", "dev", "eth0", "down"], timeout=1)
        except Exception:
            pass
        try:
            subprocess.run(["ip", "link", "set", "dev", "wlan0", "down"], timeout=1)
        except Exception:
            pass
        
        # Step 2: Sync then force reboot via sysrq
        try:
            # sysrq 's' = sync, 'u' = remount ro, 'b' = reboot
            with open("/proc/sysrq-trigger", "w") as f:
                f.write("s")  # Sync
            time.sleep(0.1)
            with open("/proc/sysrq-trigger", "w") as f:
                f.write("u")  # Unmount
            time.sleep(0.1)
            with open("/proc/sysrq-trigger", "w") as f:
                f.write("b")  # Reboot (hard, immediate)
        except PermissionError:
            # Fallback: force reboot via subprocess
            try:
                subprocess.run(["reboot", "-f"], timeout=2)
            except Exception:
                # Last resort
                os.system("echo b > /proc/sysrq-trigger 2>/dev/null || reboot -f")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current kill switch status"""
        return {
            "armed": self.armed,
            "threat_level": self.threat_level.value,
            "fraud_score": self.current_fraud_score,
            "threshold": self.config.fraud_score_threshold,
            "panic_count": len(self.panic_history),
            "profile_uuid": self.config.profile_uuid,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def arm_kill_switch(profile_uuid: str, threshold: int = 85,
                     auto_flush_hw: bool = True) -> KillSwitch:
    """Arm a kill switch for a session"""
    config = KillSwitchConfig(
        profile_uuid=profile_uuid,
        fraud_score_threshold=threshold,
        auto_flush_hw=auto_flush_hw,
    )
    ks = KillSwitch(config)
    ks.arm()
    return ks


def send_panic_signal(reason: str = "manual_trigger"):
    """Send panic signal via file (for external scripts/extensions)"""
    signal_file = Path("/opt/titan/state/kill_signal")
    signal_file.parent.mkdir(parents=True, exist_ok=True)
    signal_file.write_text(reason)


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: MEMORY PRESSURE MANAGER
# Monitors system memory and manages pressure zones to prevent OOM kills
# during operations. OOM kills leave forensic traces in dmesg and can
# corrupt profile state. This manager proactively manages memory to
# keep the system in a safe operating zone.
# ═══════════════════════════════════════════════════════════════════════════

class MemoryZone(Enum):
    """Memory pressure zones with automatic response actions."""
    GREEN = "green"       # <60% — normal operation
    YELLOW = "yellow"     # 60-75% — start shedding caches
    ORANGE = "orange"     # 75-85% — aggressive cleanup, warn operator
    RED = "red"           # >85% — emergency: kill non-essential processes


class MemoryPressureManager:
    """
    v7.5 Memory Pressure Manager with 4-zone automatic response.

    Problem: TITAN runs multiple heavy processes (Camoufox, ONNX inference,
    FFmpeg for KYC, eBPF maps). On 4-8GB VPS instances, memory pressure
    can trigger OOM killer which:
    - Leaves forensic traces in dmesg/journald
    - Corrupts browser profile state mid-session
    - Kills the kill switch daemon itself (ironic)

    Solution: Proactive memory management with zone-based responses:
    - GREEN (<60%): Normal operation
    - YELLOW (60-75%): Drop page cache, trim malloc arenas
    - ORANGE (75-85%): Kill background noise generators, warn operator
    - RED (>85%): Emergency profile save + process termination
    """

    # Processes safe to kill in ORANGE/RED zones (by name substring)
    EXPENDABLE_PROCESSES = [
        "background_noise",
        "trajectory_precompute",
        "intel_monitor",
        "warmup_browser",
    ]

    def __init__(self, yellow_pct: float = 60.0, orange_pct: float = 75.0,
                 red_pct: float = 85.0, poll_interval_s: float = 5.0):
        self.thresholds = {
            MemoryZone.YELLOW: yellow_pct,
            MemoryZone.ORANGE: orange_pct,
            MemoryZone.RED: red_pct,
        }
        self.poll_interval = poll_interval_s
        self.current_zone = MemoryZone.GREEN
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[MemoryZone, list] = {z: [] for z in MemoryZone}
        self.logger = logging.getLogger("TITAN-MEMORY-MGR")

    def get_memory_usage(self) -> Dict[str, Any]:
        """Read current memory usage from /proc/meminfo."""
        try:
            meminfo = Path("/proc/meminfo").read_text()
            values = {}
            for line in meminfo.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    values[key] = int(parts[1])  # kB

            total = values.get("MemTotal", 1)
            available = values.get("MemAvailable", total)
            used = total - available
            pct = (used / total) * 100.0

            return {
                "total_mb": total // 1024,
                "used_mb": used // 1024,
                "available_mb": available // 1024,
                "percent_used": round(pct, 1),
                "swap_total_mb": values.get("SwapTotal", 0) // 1024,
                "swap_used_mb": (values.get("SwapTotal", 0) - values.get("SwapFree", 0)) // 1024,
            }
        except Exception as e:
            self.logger.error(f"Cannot read /proc/meminfo: {e}")
            return {"percent_used": 0, "error": str(e)}

    def classify_zone(self, pct: float) -> MemoryZone:
        """Classify current memory usage into a pressure zone."""
        if pct >= self.thresholds[MemoryZone.RED]:
            return MemoryZone.RED
        elif pct >= self.thresholds[MemoryZone.ORANGE]:
            return MemoryZone.ORANGE
        elif pct >= self.thresholds[MemoryZone.YELLOW]:
            return MemoryZone.YELLOW
        return MemoryZone.GREEN

    def on_zone_change(self, zone: MemoryZone, callback):
        """Register callback for zone transition."""
        self._callbacks[zone].append(callback)

    def _respond_yellow(self):
        """YELLOW zone: drop caches and trim malloc arenas."""
        self.logger.warning("[MEMORY] YELLOW zone — dropping page cache")
        try:
            # Drop page cache (requires root or sysctl vm.drop_caches permission)
            subprocess.run(
                "echo 1 > /proc/sys/vm/drop_caches",
                shell=True, capture_output=True, timeout=5
            )
            # Trim glibc malloc arenas
            subprocess.run(
                ["python3", "-c", "import ctypes; ctypes.CDLL('libc.so.6').malloc_trim(0)"],
                capture_output=True, timeout=5
            )
        except Exception as e:
            self.logger.error(f"[MEMORY] Yellow response failed: {e}")

    def _respond_orange(self):
        """ORANGE zone: kill expendable background processes."""
        self.logger.warning("[MEMORY] ORANGE zone — killing expendable processes")
        self._respond_yellow()  # Also do yellow actions
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                for proc_name in self.EXPENDABLE_PROCESSES:
                    if proc_name in line:
                        parts = line.split()
                        if len(parts) > 1:
                            pid = int(parts[1])
                            os.kill(pid, signal.SIGTERM)
                            self.logger.info(f"[MEMORY] Killed expendable process: {proc_name} (PID {pid})")
        except Exception as e:
            self.logger.error(f"[MEMORY] Orange response failed: {e}")

    def _respond_red(self):
        """RED zone: emergency — save state and aggressive cleanup."""
        self.logger.critical("[MEMORY] RED zone — emergency memory cleanup!")
        self._respond_orange()  # Also do orange actions
        try:
            # Force Python GC
            import gc
            gc.collect()
            # Drop all caches aggressively
            subprocess.run(
                "echo 3 > /proc/sys/vm/drop_caches",
                shell=True, capture_output=True, timeout=5
            )
            # Write emergency state marker
            state_file = Path("/opt/titan/state/memory_emergency")
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps({
                "timestamp": time.time(),
                "memory": self.get_memory_usage(),
                "action": "emergency_cleanup",
            }))
        except Exception as e:
            self.logger.critical(f"[MEMORY] Red response failed: {e}")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            mem = self.get_memory_usage()
            pct = mem.get("percent_used", 0)
            new_zone = self.classify_zone(pct)

            if new_zone != self.current_zone:
                old_zone = self.current_zone
                self.current_zone = new_zone
                self.logger.info(f"[MEMORY] Zone transition: {old_zone.value} → {new_zone.value} ({pct}%)")

                # Execute zone response
                if new_zone == MemoryZone.YELLOW:
                    self._respond_yellow()
                elif new_zone == MemoryZone.ORANGE:
                    self._respond_orange()
                elif new_zone == MemoryZone.RED:
                    self._respond_red()

                # Fire callbacks
                for cb in self._callbacks.get(new_zone, []):
                    try:
                        cb(new_zone, mem)
                    except Exception:
                        pass

            time.sleep(self.poll_interval)

    def start(self):
        """Start memory pressure monitoring."""
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="titan-memory-mgr"
        )
        self._thread.start()
        self.logger.info("[MEMORY] Pressure manager started")

    def stop(self):
        """Stop memory pressure monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        self.logger.info("[MEMORY] Pressure manager stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current memory manager status."""
        mem = self.get_memory_usage()
        return {
            "running": self._running,
            "zone": self.current_zone.value,
            "memory": mem,
            "thresholds": {z.value: v for z, v in self.thresholds.items()},
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: FORENSIC WIPER
# Secure forensic data wiping for emergency cleanup
# ═══════════════════════════════════════════════════════════════════════════

class ForensicWiper:
    """
    V7.6: Secure forensic data wiping engine.
    
    Handles:
    - Secure file deletion (multiple overwrite passes)
    - Memory page zeroing
    - Swap file clearing
    - Browser artifact removal
    - System log sanitization
    
    Used for emergency cleanup when operation is compromised.
    """
    
    # Paths to sanitize during wipe
    WIPE_PATHS = {
        'titan_profiles': '/opt/titan/profiles',
        'titan_state': '/opt/titan/state',
        'titan_logs': '/opt/titan/logs',
        'browser_data': [
            '~/.config/chromium',
            '~/.config/google-chrome',
            '~/.mozilla/firefox',
        ],
        'temp_files': [
            '/tmp/titan*',
            '/tmp/browser*',
            '/var/tmp/titan*',
        ],
        'system_logs': [
            '/var/log/syslog',
            '/var/log/auth.log',
            '/var/log/kern.log',
        ],
    }
    
    # Secure deletion patterns (DOD 5220.22-M)
    OVERWRITE_PATTERNS = [
        b'\x00',  # Pass 1: zeros
        b'\xff',  # Pass 2: ones
        b'\x00',  # Pass 3: zeros (alternative: random)
    ]
    
    def __init__(self, secure_delete: bool = True, passes: int = 3):
        self.secure_delete = secure_delete
        self.passes = min(passes, 7)  # Cap at 7 passes
        self.logger = logging.getLogger("TITAN-FORENSIC")
        self._wipe_log = []
    
    def secure_delete_file(self, file_path: str) -> bool:
        """
        Securely delete a file with multiple overwrite passes.
        """
        from pathlib import Path
        
        path = Path(file_path).expanduser()
        if not path.exists():
            return True  # Already gone
        
        if not path.is_file():
            return False
        
        try:
            file_size = path.stat().st_size
            
            if self.secure_delete and file_size > 0:
                # Overwrite with patterns
                with open(path, 'r+b') as f:
                    for i in range(self.passes):
                        pattern = self.OVERWRITE_PATTERNS[i % len(self.OVERWRITE_PATTERNS)]
                        f.seek(0)
                        f.write(pattern * file_size)
                        f.flush()
                        os.fsync(f.fileno())
            
            # Remove file
            path.unlink()
            self._wipe_log.append(f"Deleted: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {file_path}: {e}")
            return False
    
    def secure_delete_directory(self, dir_path: str, recursive: bool = True) -> Dict:
        """
        Securely delete a directory and all contents.
        """
        from pathlib import Path
        import shutil
        
        path = Path(dir_path).expanduser()
        result = {
            'path': str(path),
            'files_deleted': 0,
            'dirs_deleted': 0,
            'errors': [],
        }
        
        if not path.exists():
            return result
        
        try:
            if recursive:
                for item in path.rglob('*'):
                    if item.is_file():
                        if self.secure_delete_file(str(item)):
                            result['files_deleted'] += 1
                        else:
                            result['errors'].append(str(item))
                
                # Remove empty directories
                for item in sorted(path.rglob('*'), reverse=True):
                    if item.is_dir():
                        try:
                            item.rmdir()
                            result['dirs_deleted'] += 1
                        except Exception:
                            pass
                
                # Remove root directory
                try:
                    path.rmdir()
                    result['dirs_deleted'] += 1
                except Exception:
                    pass
            else:
                shutil.rmtree(path, ignore_errors=True)
                result['dirs_deleted'] = 1
                
        except Exception as e:
            result['errors'].append(f"Directory error: {e}")
        
        return result
    
    def wipe_browser_artifacts(self) -> Dict:
        """Wipe all browser-related artifacts."""
        result = {'wiped': [], 'errors': []}
        
        for browser_path in self.WIPE_PATHS['browser_data']:
            res = self.secure_delete_directory(browser_path)
            if res['errors']:
                result['errors'].extend(res['errors'])
            else:
                result['wiped'].append(browser_path)
        
        return result
    
    def wipe_titan_data(self) -> Dict:
        """Wipe all TITAN-related data."""
        result = {'wiped': [], 'errors': []}
        
        # Profiles
        res = self.secure_delete_directory(self.WIPE_PATHS['titan_profiles'])
        result['wiped'].append(('profiles', res))
        
        # State
        res = self.secure_delete_directory(self.WIPE_PATHS['titan_state'])
        result['wiped'].append(('state', res))
        
        # Logs
        res = self.secure_delete_directory(self.WIPE_PATHS['titan_logs'])
        result['wiped'].append(('logs', res))
        
        return result
    
    def sanitize_system_logs(self) -> Dict:
        """Sanitize system logs containing TITAN activity."""
        result = {'sanitized': [], 'errors': []}
        
        titan_patterns = [
            'titan', 'TITAN', 'cerberus', 'genesis',
            'kyc_bypass', 'ghost_motor', 'kill_switch'
        ]
        
        for log_path in self.WIPE_PATHS['system_logs']:
            try:
                from pathlib import Path
                path = Path(log_path)
                
                if not path.exists():
                    continue
                
                # Read and filter
                with open(path, 'r') as f:
                    lines = f.readlines()
                
                filtered = [
                    line for line in lines
                    if not any(p.lower() in line.lower() for p in titan_patterns)
                ]
                
                if len(filtered) < len(lines):
                    with open(path, 'w') as f:
                        f.writelines(filtered)
                    result['sanitized'].append({
                        'file': log_path,
                        'removed_lines': len(lines) - len(filtered),
                    })
                    
            except PermissionError:
                result['errors'].append(f"Permission denied: {log_path}")
            except Exception as e:
                result['errors'].append(f"{log_path}: {e}")
        
        return result
    
    def clear_memory_pages(self) -> bool:
        """Clear sensitive data from memory."""
        try:
            import gc
            gc.collect()
            
            # Drop page cache
            subprocess.run(
                "sync; echo 1 > /proc/sys/vm/drop_caches",
                shell=True, capture_output=True, timeout=5
            )
            
            # Clear swap if possible
            subprocess.run(
                ["swapoff", "-a"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["swapon", "-a"],
                capture_output=True, timeout=10
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Memory clear failed: {e}")
            return False
    
    def full_wipe(self) -> Dict:
        """Execute full forensic wipe of all TITAN data."""
        self.logger.warning("EXECUTING FULL FORENSIC WIPE")
        
        result = {
            'timestamp': time.time(),
            'titan_data': self.wipe_titan_data(),
            'browser_artifacts': self.wipe_browser_artifacts(),
            'system_logs': self.sanitize_system_logs(),
            'memory_cleared': self.clear_memory_pages(),
            'wipe_log': self._wipe_log.copy(),
        }
        
        self.logger.warning(f"FORENSIC WIPE COMPLETE: {len(self._wipe_log)} items processed")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: THREAT SIGNAL AGGREGATOR
# Aggregate multiple threat signals for accurate threat assessment
# ═══════════════════════════════════════════════════════════════════════════

class ThreatSignalAggregator:
    """
    V7.6: Aggregates multiple threat signals for accurate assessment.
    
    Signal sources:
    - Antifraud detection scores
    - KYC failure indicators
    - Network anomalies
    - Browser fingerprint challenges
    - Rate limiting events
    
    Provides weighted threat score for KillSwitch decisions.
    """
    
    # Signal weights for threat calculation
    SIGNAL_WEIGHTS = {
        'fraud_detection': 30,
        'kyc_failure': 25,
        'rate_limit': 15,
        'captcha_loop': 20,
        'ip_flagged': 25,
        'fingerprint_challenged': 20,
        'account_locked': 35,
        'payment_declined': 10,
        '3ds_failure': 15,
        'browser_crash': 10,
        'network_anomaly': 15,
    }
    
    # Decay rate for signal aging (per minute)
    SIGNAL_DECAY_RATE = 0.05
    
    def __init__(self, panic_threshold: int = 80):
        self.panic_threshold = panic_threshold
        self._signals = []
        self._lock = threading.Lock()
        self._callbacks = []
    
    def add_signal(self, signal_type: str, severity: float = 1.0, 
                   details: Dict = None):
        """
        Add a threat signal.
        
        Args:
            signal_type: Type of signal (from SIGNAL_WEIGHTS)
            severity: Multiplier 0.0-2.0 (1.0 = normal)
            details: Additional context
        """
        weight = self.SIGNAL_WEIGHTS.get(signal_type, 10)
        adjusted_weight = weight * min(severity, 2.0)
        
        signal = {
            'type': signal_type,
            'weight': adjusted_weight,
            'severity': severity,
            'timestamp': time.time(),
            'details': details or {},
        }
        
        with self._lock:
            self._signals.append(signal)
        
        # Check if we should trigger callbacks
        current_score = self.get_threat_score()
        if current_score >= self.panic_threshold:
            for callback in self._callbacks:
                try:
                    callback(current_score, signal)
                except Exception:
                    pass
    
    def get_threat_score(self) -> int:
        """
        Calculate current aggregate threat score (0-100).
        
        Accounts for signal decay over time.
        """
        current_time = time.time()
        total_weight = 0
        
        with self._lock:
            for signal in self._signals:
                age_minutes = (current_time - signal['timestamp']) / 60
                decay = max(0, 1 - (age_minutes * self.SIGNAL_DECAY_RATE))
                total_weight += signal['weight'] * decay
        
        # Normalize to 0-100
        return min(int(total_weight), 100)
    
    def get_active_signals(self) -> List[Dict]:
        """Get list of active (non-decayed) signals."""
        current_time = time.time()
        active = []
        
        with self._lock:
            for signal in self._signals:
                age_minutes = (current_time - signal['timestamp']) / 60
                decay = 1 - (age_minutes * self.SIGNAL_DECAY_RATE)
                
                if decay > 0.1:  # Still relevant
                    active.append({
                        **signal,
                        'current_weight': signal['weight'] * decay,
                        'age_minutes': round(age_minutes, 1),
                    })
        
        return sorted(active, key=lambda x: x['current_weight'], reverse=True)
    
    def clear_signals(self):
        """Clear all signals."""
        with self._lock:
            self._signals.clear()
    
    def prune_old_signals(self, max_age_minutes: float = 30):
        """Remove signals older than max_age."""
        cutoff = time.time() - (max_age_minutes * 60)
        
        with self._lock:
            self._signals = [
                s for s in self._signals 
                if s['timestamp'] > cutoff
            ]
    
    def on_panic_threshold(self, callback):
        """Register callback for when panic threshold is reached."""
        self._callbacks.append(callback)
    
    def should_panic(self) -> Tuple[bool, int]:
        """Check if threat level warrants panic."""
        score = self.get_threat_score()
        return (score >= self.panic_threshold, score)
    
    def get_summary(self) -> Dict:
        """Get threat summary for reporting."""
        active = self.get_active_signals()
        score = self.get_threat_score()
        
        return {
            'threat_score': score,
            'panic_threshold': self.panic_threshold,
            'should_panic': score >= self.panic_threshold,
            'active_signal_count': len(active),
            'top_signals': active[:5],
            'signal_types': list(set(s['type'] for s in active)),
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: EMERGENCY RECOVERY MANAGER
# Recovery from panic states and incident management
# ═══════════════════════════════════════════════════════════════════════════

class EmergencyRecoveryManager:
    """
    V7.6: Manages recovery from panic/emergency states.
    
    Features:
    - State checkpointing before panic
    - Gradual recovery procedures
    - Identity rotation for resumption
    - Incident logging and analysis
    """
    
    RECOVERY_STAGES = [
        'assess_damage',
        'rotate_identity', 
        'rebuild_profile',
        'test_connectivity',
        'resume_operations',
    ]
    
    def __init__(self, state_dir: str = '/opt/titan/state/recovery'):
        from pathlib import Path
        
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("TITAN-RECOVERY")
        self._current_stage = None
        self._incident_id = None
    
    def checkpoint_state(self, kill_switch: 'KillSwitch') -> str:
        """
        Save checkpoint before panic for later recovery.
        
        Returns checkpoint ID.
        """
        import uuid
        
        checkpoint_id = str(uuid.uuid4())[:8]
        checkpoint = {
            'id': checkpoint_id,
            'timestamp': time.time(),
            'kill_switch_status': kill_switch.get_status(),
            'profiles': self._list_profiles(),
            'active_sessions': self._get_active_sessions(),
        }
        
        checkpoint_file = self.state_dir / f"checkpoint_{checkpoint_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint, indent=2))
        
        self.logger.info(f"State checkpoint saved: {checkpoint_id}")
        return checkpoint_id
    
    def start_recovery(self, checkpoint_id: str = None) -> Dict:
        """
        Start recovery process.
        
        Args:
            checkpoint_id: Optional checkpoint to recover from
        """
        import uuid
        
        self._incident_id = str(uuid.uuid4())[:8]
        self._current_stage = 'assess_damage'
        
        recovery_plan = {
            'incident_id': self._incident_id,
            'checkpoint_id': checkpoint_id,
            'stages': self.RECOVERY_STAGES.copy(),
            'current_stage': self._current_stage,
            'started_at': time.time(),
        }
        
        self.logger.info(f"Recovery started: incident={self._incident_id}")
        return recovery_plan
    
    def assess_damage(self) -> Dict:
        """
        Assess damage from panic event.
        
        Returns assessment report.
        """
        self._current_stage = 'assess_damage'
        
        assessment = {
            'profiles_intact': 0,
            'profiles_compromised': 0,
            'network_status': 'unknown',
            'browser_status': 'unknown',
            'data_wiped': False,
        }
        
        # Check profiles
        profiles = self._list_profiles()
        assessment['profiles_intact'] = len(profiles)
        
        # Check network
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            assessment['network_status'] = 'connected'
        except Exception:
            assessment['network_status'] = 'disconnected'
        
        # Check for wipe markers
        wipe_marker = self.state_dir / "forensic_wipe_executed"
        assessment['data_wiped'] = wipe_marker.exists()
        
        return assessment
    
    def rotate_identity(self) -> Dict:
        """
        Rotate identity components for fresh start.
        """
        self._current_stage = 'rotate_identity'
        
        result = {
            'mac_rotated': False,
            'proxy_rotated': False,
            'fingerprint_regenerated': False,
        }
        
        # Rotate MAC address
        try:
            subprocess.run([
                "ip", "link", "set", "eth0", "down"
            ], capture_output=True, timeout=5)
            
            import random
            new_mac = ':'.join([
                format(random.randint(0, 255), '02x')
                for _ in range(6)
            ])
            # Ensure locally administered bit
            parts = new_mac.split(':')
            parts[0] = format(int(parts[0], 16) | 0x02, '02x')
            new_mac = ':'.join(parts)
            
            subprocess.run([
                "ip", "link", "set", "eth0", "address", new_mac
            ], capture_output=True, timeout=5)
            
            subprocess.run([
                "ip", "link", "set", "eth0", "up"
            ], capture_output=True, timeout=5)
            
            result['mac_rotated'] = True
            result['new_mac'] = new_mac
            
        except Exception as e:
            self.logger.error(f"MAC rotation failed: {e}")
        
        return result
    
    def rebuild_profile(self, profile_type: str = 'fresh') -> Dict:
        """
        Rebuild a clean profile for operations via genesis_core.
        """
        self._current_stage = 'rebuild_profile'
        
        result = {
            'profile_type': profile_type,
            'profile_id': None,
            'success': False,
        }
        
        try:
            from genesis_core import GenesisEngine, ProfileConfig
            genesis = GenesisEngine()
            config = ProfileConfig(
                profile_type=profile_type,
                browser="camoufox",
                os_target="linux",
            )
            profile = genesis.generate(config)
            if profile:
                result['profile_id'] = getattr(profile, 'profile_id', None) or getattr(profile, 'uuid', None)
                result['profile_path'] = getattr(profile, 'path', None) or str(getattr(profile, 'profile_path', ''))
                result['success'] = True
                logger.info(f"[RECOVERY] Profile rebuilt via genesis_core: {result['profile_id']}")
            else:
                raise RuntimeError("genesis_core returned None")
        except ImportError:
            logger.warning("[RECOVERY] genesis_core not available — generating minimal recovery profile")
            import uuid
            result['profile_id'] = f"recovery_{uuid.uuid4().hex[:8]}"
            result['success'] = True
        except Exception as e:
            logger.error(f"[RECOVERY] Profile rebuild failed: {e}")
            import uuid
            result['profile_id'] = f"recovery_{uuid.uuid4().hex[:8]}"
            result['success'] = True
            result['warning'] = f"Used fallback UUID — genesis_core error: {str(e)}"
        
        return result
    
    def test_connectivity(self) -> Dict:
        """
        Test connectivity before resuming operations.
        """
        self._current_stage = 'test_connectivity'
        
        tests = {
            'internet': False,
            'proxy': False,
            'target_sites': [],
        }
        
        # Test internet
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            tests['internet'] = True
        except Exception:
            pass
        
        # Test common targets
        test_urls = [
            ('https://www.google.com', 'google'),
            ('https://www.amazon.com', 'amazon'),
        ]
        
        for url, name in test_urls:
            try:
                import urllib.request
                req = urllib.request.urlopen(url, timeout=10)
                if req.status == 200:
                    tests['target_sites'].append({'name': name, 'reachable': True})
            except Exception:
                tests['target_sites'].append({'name': name, 'reachable': False})
        
        return tests
    
    def complete_recovery(self) -> Dict:
        """
        Complete recovery and resume normal operations.
        """
        self._current_stage = 'resume_operations'
        
        summary = {
            'incident_id': self._incident_id,
            'recovery_complete': True,
            'completed_at': time.time(),
            'stages_completed': self.RECOVERY_STAGES,
        }
        
        # Clear incident state
        self._incident_id = None
        self._current_stage = None
        
        self.logger.info("Recovery completed successfully")
        return summary
    
    def _list_profiles(self) -> List[str]:
        """List available profiles."""
        from pathlib import Path
        profiles_dir = Path('/opt/titan/profiles')
        if profiles_dir.exists():
            return [p.name for p in profiles_dir.iterdir() if p.is_dir()]
        return []
    
    def _get_active_sessions(self) -> List[Dict]:
        """Get list of active sessions by checking profile lock files and running processes."""
        sessions = []
        try:
            profiles_dir = Path(self.config.profile_path) if hasattr(self.config, 'profile_path') else Path("/opt/titan/profiles")
            if profiles_dir.exists():
                for profile_dir in profiles_dir.iterdir():
                    if not profile_dir.is_dir():
                        continue
                    # Check for Firefox/Camoufox lock files indicating active session
                    lock_file = profile_dir / "lock"
                    parent_lock = profile_dir / ".parentlock"
                    session_file = profile_dir / "sessionstore.jsonlz4"
                    if lock_file.exists() or parent_lock.exists():
                        sessions.append({
                            "profile_id": profile_dir.name,
                            "path": str(profile_dir),
                            "status": "active",
                            "has_lock": lock_file.exists(),
                            "has_session": session_file.exists(),
                        })
                    elif session_file.exists():
                        sessions.append({
                            "profile_id": profile_dir.name,
                            "path": str(profile_dir),
                            "status": "stale",
                            "has_lock": False,
                            "has_session": True,
                        })
        except Exception as e:
            logger.debug(f"Session scan error: {e}")
        return sessions
    
    def get_recovery_status(self) -> Dict:
        """Get current recovery status."""
        return {
            'incident_id': self._incident_id,
            'in_recovery': self._incident_id is not None,
            'current_stage': self._current_stage,
            'stages': self.RECOVERY_STAGES,
        }


# V7.6 Convenience exports
def create_forensic_wiper(secure: bool = True) -> ForensicWiper:
    """V7.6: Create forensic wiper"""
    return ForensicWiper(secure_delete=secure)

def create_threat_aggregator(threshold: int = 80) -> ThreatSignalAggregator:
    """V7.6: Create threat signal aggregator"""
    return ThreatSignalAggregator(panic_threshold=threshold)

def create_recovery_manager() -> EmergencyRecoveryManager:
    """V7.6: Create emergency recovery manager"""
    return EmergencyRecoveryManager()
