"""
TITAN V8.0 MAXIMUM LEVEL — Service Orchestrator
Auto-starts and manages all background services:
  - Transaction Monitor (24/7 capture on port 7443)
  - Daily Auto-Discovery (finds new easy targets once per day)
  - Operational Feedback Loop (TX decline data improves site ratings)
  - Health Watchdog (monitors service status)

Usage:
    from titan_services import TitanServiceManager
    
    mgr = TitanServiceManager()
    mgr.start_all()          # Start all services
    mgr.get_status()         # Get status of all services
    mgr.stop_all()           # Graceful shutdown
"""

import os
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

# Load titan.env config
try:
    from titan_env import get_config, is_configured
except ImportError:
    def get_config(key, default=""): return os.environ.get(key, default)
    def is_configured(key): return bool(os.environ.get(key, ""))

logger = logging.getLogger("TITAN-V7-SERVICES")

# ═══════════════════════════════════════════════════════════════════════════
# DAILY AUTO-DISCOVERY SCHEDULER
# Runs target discovery once per day at a configurable hour
# ═══════════════════════════════════════════════════════════════════════════

class DailyDiscoveryScheduler:
    """
    Runs auto-discovery once per day to find new easy/2D/Shopify targets.
    Results are auto-added to the TargetDiscovery database.
    """
    
    STATE_FILE = Path("/opt/titan/data/services/discovery_scheduler.json")
    
    def __init__(self, run_hour: int = 3):
        self.run_hour = run_hour  # Hour of day to run (0-23, default 3 AM)
        self._thread = None
        self._running = False
        self._last_run = None
        self._last_result = None
        self._load_state()
    
    def _load_state(self):
        if self.STATE_FILE.exists():
            try:
                data = json.loads(self.STATE_FILE.read_text())
                self._last_run = data.get("last_run")
                self._last_result = data.get("last_result")
            except Exception:
                pass
    
    def _save_state(self):
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_run": self._last_run,
                "last_result": self._last_result,
                "run_hour": self.run_hour,
            }
            self.STATE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save scheduler state: {e}")
    
    def _should_run_now(self) -> bool:
        now = datetime.now(timezone.utc)
        if self._last_run:
            try:
                last = datetime.fromisoformat(self._last_run.replace("Z", ""))
                if (now - last).total_seconds() < 82800:  # 23 hours
                    return False
            except Exception:
                pass
        return True
    
    def run_discovery(self) -> Dict:
        """Execute one discovery run"""
        logger.info("Daily Auto-Discovery starting...")
        try:
            from target_discovery import TargetDiscovery
            td = TargetDiscovery()
            result = td.auto_discover_new(max_sites=50, engine="google")
            
            self._last_run = datetime.now(timezone.utc).isoformat()
            self._last_result = {
                "timestamp": self._last_run,
                "total_searched": result.get("total_searched", 0),
                "easy_2d_found": result.get("easy_2d_found", 0),
                "bypassable_found": result.get("bypassable_found", 0),
                "auto_added": result.get("auto_added_to_db", 0),
            }
            self._save_state()
            
            logger.info(
                f"Discovery complete: {result.get('total_searched', 0)} searched, "
                f"{result.get('easy_2d_found', 0)} easy 2D, "
                f"{result.get('auto_added_to_db', 0)} added to DB"
            )
            return result
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return {"error": str(e)}
    
    def start(self):
        """Start the daily scheduler loop"""
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info(f"Daily Discovery Scheduler started (run hour: {self.run_hour}:00 UTC)")
        
        # Run immediately if never run or stale
        if self._should_run_now():
            threading.Thread(target=self.run_discovery, daemon=True).start()
    
    def stop(self):
        self._running = False
    
    def _scheduler_loop(self):
        while self._running:
            now = datetime.now(timezone.utc)
            if now.hour == self.run_hour and self._should_run_now():
                self.run_discovery()
            time.sleep(300)  # Check every 5 minutes
    
    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "run_hour": f"{self.run_hour}:00 UTC",
            "last_run": self._last_run or "never",
            "last_result": self._last_result,
        }


# ═══════════════════════════════════════════════════════════════════════════
# OPERATIONAL FEEDBACK LOOP
# TX Monitor decline data feeds back into site ratings and BIN scoring
# ═══════════════════════════════════════════════════════════════════════════

class OperationalFeedbackLoop:
    """
    Connects Transaction Monitor data to Target Discovery and BIN scoring.
    - Decline patterns update site success rates
    - Successful BINs get scored higher
    - Sites with high decline rates get flagged
    """
    
    FEEDBACK_FILE = Path("/opt/titan/data/services/feedback_state.json")
    
    def __init__(self):
        self._thread = None
        self._running = False
        self._feedback_data = {"site_scores": {}, "bin_scores": {}, "last_update": None}
        self._load_state()
    
    def _load_state(self):
        if self.FEEDBACK_FILE.exists():
            try:
                self._feedback_data = json.loads(self.FEEDBACK_FILE.read_text())
            except Exception:
                pass
    
    def _save_state(self):
        try:
            self.FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.FEEDBACK_FILE.write_text(json.dumps(self._feedback_data, indent=2))
        except Exception:
            pass
    
    def update_from_tx_history(self) -> Dict:
        """Pull recent TX data and update site/BIN scores"""
        try:
            from transaction_monitor import TransactionMonitor
            monitor = TransactionMonitor()
            stats = monitor.get_stats(hours=168)  # Last 7 days
            
            updated_sites = 0
            updated_bins = 0
            
            # Update site scores
            for domain, data in stats.get("by_site", {}).items():
                total = data.get("total", 0)
                if total >= 3:  # Need at least 3 transactions for meaningful data
                    rate = data.get("rate", 0) / 100.0
                    self._feedback_data["site_scores"][domain] = {
                        "success_rate": rate,
                        "total_tx": total,
                        "approved": data.get("approved", 0),
                        "updated": datetime.now(timezone.utc).isoformat(),
                    }
                    updated_sites += 1
            
            # Update BIN scores
            for bin_prefix, data in stats.get("by_bin", {}).items():
                total = data.get("total", 0)
                if total >= 2:
                    rate = data.get("rate", 0) / 100.0
                    self._feedback_data["bin_scores"][bin_prefix] = {
                        "success_rate": rate,
                        "total_tx": total,
                        "approved": data.get("approved", 0),
                        "updated": datetime.now(timezone.utc).isoformat(),
                    }
                    updated_bins += 1
            
            self._feedback_data["last_update"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            
            return {
                "updated_sites": updated_sites,
                "updated_bins": updated_bins,
                "total_site_scores": len(self._feedback_data["site_scores"]),
                "total_bin_scores": len(self._feedback_data["bin_scores"]),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_site_score(self, domain: str) -> Optional[Dict]:
        return self._feedback_data["site_scores"].get(domain)
    
    def get_bin_score(self, bin_prefix: str) -> Optional[Dict]:
        return self._feedback_data["bin_scores"].get(bin_prefix)
    
    def get_best_sites(self, min_rate: float = 0.7, min_tx: int = 3) -> List[Dict]:
        results = []
        for domain, data in self._feedback_data["site_scores"].items():
            if data["success_rate"] >= min_rate and data["total_tx"] >= min_tx:
                results.append({"domain": domain, **data})
        results.sort(key=lambda x: x["success_rate"], reverse=True)
        return results
    
    def get_best_bins(self, min_rate: float = 0.7, min_tx: int = 2) -> List[Dict]:
        results = []
        for bin_prefix, data in self._feedback_data["bin_scores"].items():
            if data["success_rate"] >= min_rate and data["total_tx"] >= min_tx:
                results.append({"bin": bin_prefix, **data})
        results.sort(key=lambda x: x["success_rate"], reverse=True)
        return results
    
    def start(self):
        """Start the feedback loop — updates every 30 minutes"""
        self._running = True
        self._thread = threading.Thread(target=self._feedback_loop, daemon=True)
        self._thread.start()
        logger.info("Operational Feedback Loop started (30-min interval)")
    
    def stop(self):
        self._running = False
    
    def _feedback_loop(self):
        time.sleep(60)  # Wait 1 min for TX monitor to be ready
        while self._running:
            self.update_from_tx_history()
            time.sleep(1800)  # Every 30 minutes
    
    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "tracked_sites": len(self._feedback_data["site_scores"]),
            "tracked_bins": len(self._feedback_data["bin_scores"]),
            "last_update": self._feedback_data.get("last_update", "never"),
        }


# ═══════════════════════════════════════════════════════════════════════════
# GAP-8: MEMORY PRESSURE MANAGER
# On 8GB systems with eBPF shield + 3D Reenactment Engine active,
# GUI lag creates a "janky browser" signature detectable by behavioral AI.
# This manager monitors RAM and throttles non-critical subsystems to
# guarantee the browser always has enough headroom for smooth operation.
# ═══════════════════════════════════════════════════════════════════════════

class MemoryPressureManager:
    """
    Monitors system RAM and throttles non-critical Titan subsystems
    when available memory drops below safe thresholds.

    Priority tiers (highest = protected, never throttled):
      P0 — Browser (Camoufox) + Ghost Motor extension
      P1 — eBPF/XDP network shield (kernel-space, low overhead)
      P2 — Transaction Monitor
      P3 — 3D Reenactment Engine (KYC) — throttled first
      P4 — Daily Discovery Scheduler — suspended under pressure
      P5 — Operational Feedback Loop — suspended under pressure

    Thresholds (configurable):
      GREEN  > 2500 MB free  — all systems nominal
      YELLOW  800–2500 MB   — suspend P4/P5, reduce 3D engine FPS
      RED    < 800 MB        — suspend P3/P4/P5, drop eBPF sampling rate
      CRITICAL < 400 MB      — emergency: kill all non-browser processes
    """

    THRESHOLD_GREEN_MB   = 2500
    THRESHOLD_YELLOW_MB  = 800
    THRESHOLD_RED_MB     = 400

    CHECK_INTERVAL_S = 10   # Check every 10 seconds

    def __init__(self, service_manager: "TitanServiceManager" = None):
        self._service_manager = service_manager
        self._thread = None
        self._running = False
        self._current_tier = "GREEN"
        self._actions_taken: list = []

    def _get_free_mb(self) -> float:
        """Read available RAM from /proc/meminfo (MemAvailable)"""
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / 1024.0
        except Exception:
            pass
        return 9999.0  # Assume plenty if unreadable

    def _get_tier(self, free_mb: float) -> str:
        if free_mb >= self.THRESHOLD_GREEN_MB:
            return "GREEN"
        elif free_mb >= self.THRESHOLD_YELLOW_MB:
            return "YELLOW"
        elif free_mb >= self.THRESHOLD_RED_MB:
            return "RED"
        else:
            return "CRITICAL"

    def _apply_tier(self, tier: str, free_mb: float):
        if tier == self._current_tier:
            return  # No change

        prev = self._current_tier
        self._current_tier = tier
        logger.info(f"[MEM-PRESSURE] {prev} → {tier} ({free_mb:.0f} MB free)")

        if tier == "GREEN":
            self._restore_all()

        elif tier == "YELLOW":
            # Suspend low-priority schedulers, reduce 3D engine FPS
            self._suspend_discovery()
            self._suspend_feedback()
            self._throttle_reenactment_engine(fps=10)
            logger.warning(
                f"[MEM-PRESSURE] YELLOW: suspended discovery+feedback, "
                f"3D engine throttled to 10fps ({free_mb:.0f} MB free)"
            )

        elif tier == "RED":
            # Suspend P3/P4/P5, reduce eBPF sampling
            self._suspend_discovery()
            self._suspend_feedback()
            self._suspend_reenactment_engine()
            self._reduce_ebpf_sampling()
            logger.error(
                f"[MEM-PRESSURE] RED: 3D engine suspended, eBPF sampling reduced "
                f"({free_mb:.0f} MB free)"
            )

        elif tier == "CRITICAL":
            # Emergency: kill everything except browser + eBPF
            self._suspend_discovery()
            self._suspend_feedback()
            self._suspend_reenactment_engine()
            self._emergency_kill_nonessential()
            logger.critical(
                f"[MEM-PRESSURE] CRITICAL: emergency throttle active "
                f"({free_mb:.0f} MB free) — browser protected"
            )

    def _suspend_discovery(self):
        try:
            if self._service_manager and self._service_manager.discovery_scheduler:
                self._service_manager.discovery_scheduler.stop()
                self._actions_taken.append("discovery_suspended")
        except Exception:
            pass

    def _suspend_feedback(self):
        try:
            if self._service_manager and self._service_manager.feedback_loop:
                self._service_manager.feedback_loop.stop()
                self._actions_taken.append("feedback_suspended")
        except Exception:
            pass

    def _throttle_reenactment_engine(self, fps: int = 10):
        """Reduce 3D reenactment engine frame rate to lower GPU/CPU pressure"""
        try:
            import subprocess
            # Signal the reenactment engine via its control socket
            subprocess.run(
                ["pkill", "-USR1", "-f", "reenactment_engine"],
                capture_output=True, timeout=3
            )
            # Write throttle config for engine to read on next cycle
            throttle_file = Path("/opt/titan/state/reenactment_throttle.json")
            throttle_file.parent.mkdir(parents=True, exist_ok=True)
            throttle_file.write_text(
                f'{{"fps": {fps}, "resolution_scale": 0.75, "reason": "memory_pressure"}}'
            )
            self._actions_taken.append(f"reenactment_throttled_{fps}fps")
        except Exception:
            pass

    def _suspend_reenactment_engine(self):
        """Fully suspend the 3D reenactment engine"""
        try:
            import subprocess
            subprocess.run(
                ["pkill", "-STOP", "-f", "reenactment_engine"],
                capture_output=True, timeout=3
            )
            self._actions_taken.append("reenactment_suspended")
        except Exception:
            pass

    def _reduce_ebpf_sampling(self):
        """Reduce eBPF perf event sampling rate to lower kernel overhead"""
        try:
            # Write reduced sampling config — network_shield_loader reads this
            cfg_file = Path("/opt/titan/state/ebpf_sampling.json")
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text('{"sample_rate": 16, "reason": "memory_pressure"}')
            self._actions_taken.append("ebpf_sampling_reduced")
        except Exception:
            pass

    def _emergency_kill_nonessential(self):
        """Kill all non-essential processes to protect browser headroom"""
        import subprocess
        nonessential = ["ollama", "titan-patch-bridge", "titan-discovery"]
        for proc in nonessential:
            try:
                subprocess.run(
                    ["pkill", "-9", "-f", proc],
                    capture_output=True, timeout=3
                )
            except Exception:
                pass
        self._actions_taken.append("emergency_kill")

    def _restore_all(self):
        """Restore all throttled subsystems when memory pressure clears"""
        try:
            import subprocess
            # Resume reenactment engine if stopped
            subprocess.run(
                ["pkill", "-CONT", "-f", "reenactment_engine"],
                capture_output=True, timeout=3
            )
            # Remove throttle files
            for f in [
                Path("/opt/titan/state/reenactment_throttle.json"),
                Path("/opt/titan/state/ebpf_sampling.json"),
            ]:
                if f.exists():
                    f.unlink()

            # Restart suspended services
            if self._service_manager:
                if "discovery_suspended" in self._actions_taken:
                    try:
                        self._service_manager.discovery_scheduler.start()
                    except Exception:
                        pass
                if "feedback_suspended" in self._actions_taken:
                    try:
                        self._service_manager.feedback_loop.start()
                    except Exception:
                        pass

            self._actions_taken.clear()
            logger.info("[MEM-PRESSURE] GREEN: all subsystems restored")
        except Exception:
            pass

    def get_status(self) -> dict:
        free_mb = self._get_free_mb()
        return {
            "running": self._running,
            "tier": self._current_tier,
            "free_mb": round(free_mb, 1),
            "actions_taken": list(self._actions_taken),
        }

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("[MEM-PRESSURE] Memory Pressure Manager started")

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            free_mb = self._get_free_mb()
            tier = self._get_tier(free_mb)
            self._apply_tier(tier, free_mb)
            time.sleep(self.CHECK_INTERVAL_S)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN SERVICE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class TitanServiceManager:
    """
    Master service orchestrator — starts and manages all background services.
    
    Usage:
        mgr = TitanServiceManager()
        mgr.start_all()
        status = mgr.get_status()
        mgr.stop_all()
    """
    
    def __init__(self):
        self.tx_monitor = None
        self.discovery_scheduler = None
        self.feedback_loop = None
        self.memory_pressure = None
        self.autonomous_engine = None
        self._started = False
    
    def start_all(self, tx_port: int = None, discovery_hour: int = None) -> Dict:
        """Start all background services using titan.env configuration"""
        # Read config from titan.env (falls back to sensible defaults)
        if tx_port is None:
            tx_port = int(get_config("TITAN_TX_MONITOR_PORT", "7443"))
        if discovery_hour is None:
            discovery_hour = int(get_config("TITAN_DISCOVERY_RUN_HOUR", "3"))
        
        results = {}
        
        # 1. Transaction Monitor
        if get_config("TITAN_TX_MONITOR_AUTOSTART", "1") == "1":
            try:
                from transaction_monitor import TransactionMonitor
                self.tx_monitor = TransactionMonitor()
                self.tx_monitor.start(tx_port)
                results["tx_monitor"] = {"status": "started", "port": tx_port}
                logger.info(f"TX Monitor started on port {tx_port}")
            except Exception as e:
                results["tx_monitor"] = {"status": "error", "error": str(e)}
                logger.error(f"TX Monitor failed: {e}")
        else:
            results["tx_monitor"] = {"status": "disabled_by_config"}
        
        # 2. Daily Discovery Scheduler
        if get_config("TITAN_DISCOVERY_AUTOSTART", "1") == "1":
            try:
                self.discovery_scheduler = DailyDiscoveryScheduler(run_hour=discovery_hour)
                self.discovery_scheduler.start()
                results["discovery_scheduler"] = {"status": "started", "run_hour": discovery_hour}
            except Exception as e:
                results["discovery_scheduler"] = {"status": "error", "error": str(e)}
                logger.error(f"Discovery Scheduler failed: {e}")
        else:
            results["discovery_scheduler"] = {"status": "disabled_by_config"}
        
        # 3. Operational Feedback Loop
        if get_config("TITAN_FEEDBACK_AUTOSTART", "1") == "1":
            try:
                self.feedback_loop = OperationalFeedbackLoop()
                self.feedback_loop.start()
                results["feedback_loop"] = {"status": "started"}
            except Exception as e:
                results["feedback_loop"] = {"status": "error", "error": str(e)}
                logger.error(f"Feedback Loop failed: {e}")
        else:
            results["feedback_loop"] = {"status": "disabled_by_config"}
        
        # 4. Memory Pressure Manager (GAP-8: prevents janky browser on 8GB systems)
        try:
            self.memory_pressure = MemoryPressureManager(service_manager=self)
            self.memory_pressure.start()
            results["memory_pressure"] = {"status": "started"}
        except Exception as e:
            results["memory_pressure"] = {"status": "error", "error": str(e)}
            logger.error(f"Memory Pressure Manager failed: {e}")

        # 5. V8.0 Autonomous Self-Improving Engine (24/7)
        if get_config("TITAN_AUTONOMOUS_AUTOSTART", "0") == "1":
            try:
                from titan_autonomous_engine import AutonomousEngine
                self.autonomous_engine = AutonomousEngine()
                self.autonomous_engine.load_tasks()
                self.autonomous_engine.start()
                results["autonomous_engine"] = {"status": "started", "tasks": self.autonomous_engine.task_queue.pending_count()}
            except Exception as e:
                results["autonomous_engine"] = {"status": "error", "error": str(e)}
                logger.error(f"Autonomous Engine failed: {e}")
        else:
            results["autonomous_engine"] = {"status": "disabled_by_config"}

        self._started = True
        logger.info("All TITAN services started")
        return results
    
    def stop_all(self):
        if self.tx_monitor:
            self.tx_monitor.stop()
        if self.discovery_scheduler:
            self.discovery_scheduler.stop()
        if self.feedback_loop:
            self.feedback_loop.stop()
        if self.memory_pressure:
            self.memory_pressure.stop()
        if self.autonomous_engine:
            self.autonomous_engine.stop()
        self._started = False
        logger.info("All TITAN services stopped")
    
    def get_status(self) -> Dict:
        return {
            "started": self._started,
            "tx_monitor": self.tx_monitor.get_stats() if self.tx_monitor else {"status": "not started"},
            "discovery_scheduler": self.discovery_scheduler.get_status() if self.discovery_scheduler else {"status": "not started"},
            "feedback_loop": self.feedback_loop.get_status() if self.feedback_loop else {"status": "not started"},
            "memory_pressure": self.memory_pressure.get_status() if self.memory_pressure else {"status": "not started"},
            "autonomous_engine": self.autonomous_engine.get_status() if self.autonomous_engine else {"status": "not started"},
        }
    
    def run_discovery_now(self) -> Dict:
        """Force an immediate discovery run"""
        if self.discovery_scheduler:
            return self.discovery_scheduler.run_discovery()
        sched = DailyDiscoveryScheduler()
        return sched.run_discovery()
    
    def update_feedback_now(self) -> Dict:
        """Force an immediate feedback update"""
        if self.feedback_loop:
            return self.feedback_loop.update_from_tx_history()
        fb = OperationalFeedbackLoop()
        return fb.update_from_tx_history()
    
    def get_best_sites(self) -> List[Dict]:
        """Get sites with highest real success rates from TX data"""
        if self.feedback_loop:
            return self.feedback_loop.get_best_sites()
        return OperationalFeedbackLoop().get_best_sites()
    
    def get_best_bins(self) -> List[Dict]:
        """Get BINs with highest real success rates from TX data"""
        if self.feedback_loop:
            return self.feedback_loop.get_best_bins()
        return OperationalFeedbackLoop().get_best_bins()


# Singleton
_service_manager = None

def get_service_manager() -> TitanServiceManager:
    global _service_manager
    if _service_manager is None:
        _service_manager = TitanServiceManager()
    return _service_manager

def start_all_services(**kwargs) -> Dict:
    return get_service_manager().start_all(**kwargs)

def stop_all_services():
    get_service_manager().stop_all()

def get_services_status() -> Dict:
    return get_service_manager().get_status()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════════════════

class ServiceHealthWatchdog:
    """
    V7.6 P0: Monitor service health and auto-restart failed services.
    
    Continuously monitors all TITAN services for health issues and
    automatically restarts failed services with exponential backoff.
    """
    
    _instance = None
    
    def __init__(self, service_manager: TitanServiceManager = None):
        self.service_manager = service_manager or get_service_manager()
        self.health_checks: Dict[str, Dict] = {}
        self.restart_counts: Dict[str, int] = {}
        self.max_restarts = 5
        self.base_backoff_seconds = 30
        self._thread = None
        self._running = False
        self.check_interval = 30
        self.logger = logging.getLogger("TITAN-WATCHDOG")
        
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks for all services."""
        self.register_health_check(
            "tx_monitor",
            check_fn=self._check_tx_monitor,
            restart_fn=self._restart_tx_monitor,
            critical=True
        )
        self.register_health_check(
            "discovery_scheduler",
            check_fn=self._check_discovery_scheduler,
            restart_fn=self._restart_discovery_scheduler,
            critical=False
        )
        self.register_health_check(
            "feedback_loop",
            check_fn=self._check_feedback_loop,
            restart_fn=self._restart_feedback_loop,
            critical=False
        )
        self.register_health_check(
            "memory_pressure",
            check_fn=self._check_memory_pressure,
            restart_fn=self._restart_memory_pressure,
            critical=True
        )
    
    def register_health_check(
        self,
        service_name: str,
        check_fn,
        restart_fn,
        critical: bool = False,
        interval_override: int = None
    ):
        """Register a health check for a service."""
        self.health_checks[service_name] = {
            "check_fn": check_fn,
            "restart_fn": restart_fn,
            "critical": critical,
            "interval": interval_override or self.check_interval,
            "last_check": None,
            "last_status": None,
            "consecutive_failures": 0
        }
        self.restart_counts[service_name] = 0
    
    def _check_tx_monitor(self) -> Dict:
        """Check transaction monitor health."""
        if not self.service_manager.tx_monitor:
            return {"healthy": False, "reason": "not_initialized"}
        try:
            stats = self.service_manager.tx_monitor.get_stats()
            is_running = stats.get("running", False) or stats.get("status") == "running"
            return {"healthy": is_running, "stats": stats}
        except Exception as e:
            return {"healthy": False, "reason": str(e)}
    
    def _restart_tx_monitor(self) -> bool:
        """Restart transaction monitor."""
        try:
            if self.service_manager.tx_monitor:
                self.service_manager.tx_monitor.stop()
            port = int(get_config("TITAN_TX_MONITOR_PORT", "7443"))
            from transaction_monitor import TransactionMonitor
            self.service_manager.tx_monitor = TransactionMonitor()
            self.service_manager.tx_monitor.start(port)
            return True
        except Exception as e:
            self.logger.error(f"TX Monitor restart failed: {e}")
            return False
    
    def _check_discovery_scheduler(self) -> Dict:
        """Check discovery scheduler health."""
        if not self.service_manager.discovery_scheduler:
            return {"healthy": False, "reason": "not_initialized"}
        status = self.service_manager.discovery_scheduler.get_status()
        return {"healthy": status.get("running", False), "status": status}
    
    def _restart_discovery_scheduler(self) -> bool:
        """Restart discovery scheduler."""
        try:
            if self.service_manager.discovery_scheduler:
                self.service_manager.discovery_scheduler.stop()
            hour = int(get_config("TITAN_DISCOVERY_RUN_HOUR", "3"))
            self.service_manager.discovery_scheduler = DailyDiscoveryScheduler(run_hour=hour)
            self.service_manager.discovery_scheduler.start()
            return True
        except Exception as e:
            self.logger.error(f"Discovery scheduler restart failed: {e}")
            return False
    
    def _check_feedback_loop(self) -> Dict:
        """Check feedback loop health."""
        if not self.service_manager.feedback_loop:
            return {"healthy": False, "reason": "not_initialized"}
        status = self.service_manager.feedback_loop.get_status()
        return {"healthy": status.get("running", False), "status": status}
    
    def _restart_feedback_loop(self) -> bool:
        """Restart feedback loop."""
        try:
            if self.service_manager.feedback_loop:
                self.service_manager.feedback_loop.stop()
            self.service_manager.feedback_loop = OperationalFeedbackLoop()
            self.service_manager.feedback_loop.start()
            return True
        except Exception as e:
            self.logger.error(f"Feedback loop restart failed: {e}")
            return False
    
    def _check_memory_pressure(self) -> Dict:
        """Check memory pressure manager health."""
        if not self.service_manager.memory_pressure:
            return {"healthy": False, "reason": "not_initialized"}
        status = self.service_manager.memory_pressure.get_status()
        return {"healthy": status.get("running", False), "status": status}
    
    def _restart_memory_pressure(self) -> bool:
        """Restart memory pressure manager."""
        try:
            if self.service_manager.memory_pressure:
                self.service_manager.memory_pressure.stop()
            self.service_manager.memory_pressure = MemoryPressureManager(
                service_manager=self.service_manager
            )
            self.service_manager.memory_pressure.start()
            return True
        except Exception as e:
            self.logger.error(f"Memory pressure manager restart failed: {e}")
            return False
    
    def _get_backoff(self, service_name: str) -> int:
        """Calculate exponential backoff for service restarts."""
        count = self.restart_counts.get(service_name, 0)
        return min(self.base_backoff_seconds * (2 ** count), 600)  # Max 10 minutes
    
    def _watchdog_loop(self):
        """Main watchdog monitoring loop."""
        while self._running:
            for service_name, check_info in self.health_checks.items():
                try:
                    result = check_info["check_fn"]()
                    check_info["last_check"] = datetime.now(timezone.utc).isoformat()
                    check_info["last_status"] = result
                    
                    if result.get("healthy", False):
                        check_info["consecutive_failures"] = 0
                        self.restart_counts[service_name] = 0
                    else:
                        check_info["consecutive_failures"] += 1
                        
                        if check_info["consecutive_failures"] >= 3:
                            if self.restart_counts[service_name] < self.max_restarts:
                                self.logger.warning(
                                    f"Service {service_name} unhealthy, attempting restart "
                                    f"({self.restart_counts[service_name]+1}/{self.max_restarts})"
                                )
                                if check_info["restart_fn"]():
                                    self.restart_counts[service_name] += 1
                                    check_info["consecutive_failures"] = 0
                                    self.logger.info(f"Service {service_name} restarted successfully")
                                else:
                                    self.restart_counts[service_name] += 1
                            else:
                                self.logger.error(
                                    f"Service {service_name} exceeded max restarts ({self.max_restarts})"
                                )
                except Exception as e:
                    self.logger.error(f"Health check failed for {service_name}: {e}")
            
            time.sleep(self.check_interval)
    
    def start(self):
        """Start the watchdog."""
        self._running = True
        self._thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._thread.start()
        self.logger.info("Service Health Watchdog started")
    
    def stop(self):
        """Stop the watchdog."""
        self._running = False
    
    def get_status(self) -> Dict:
        """Get watchdog status."""
        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "services": {
                name: {
                    "last_check": info.get("last_check"),
                    "healthy": info.get("last_status", {}).get("healthy"),
                    "consecutive_failures": info.get("consecutive_failures", 0),
                    "restart_count": self.restart_counts.get(name, 0)
                }
                for name, info in self.health_checks.items()
            }
        }


class ServiceDependencyManager:
    """
    V7.6 P0: Manage service dependencies and startup order.
    
    Ensures services start in correct order respecting dependencies,
    with proper wait times for dependent services.
    """
    
    _instance = None
    
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = {}
        self.startup_order: List[str] = []
        self.service_status: Dict[str, str] = {}
        self.logger = logging.getLogger("TITAN-DEPS")
        
        self._register_default_dependencies()
    
    def _register_default_dependencies(self):
        """Register default service dependencies."""
        # Memory pressure has no deps, must start first
        self.register_dependency("memory_pressure", [])
        
        # TX monitor depends on memory pressure
        self.register_dependency("tx_monitor", ["memory_pressure"])
        
        # Feedback loop depends on TX monitor
        self.register_dependency("feedback_loop", ["tx_monitor"])
        
        # Discovery scheduler is independent
        self.register_dependency("discovery_scheduler", ["memory_pressure"])
        
        # Watchdog monitors all, starts last
        self.register_dependency("watchdog", [
            "memory_pressure", "tx_monitor", "feedback_loop", "discovery_scheduler"
        ])
    
    def register_dependency(self, service: str, depends_on: List[str]):
        """Register service dependencies."""
        self.dependencies[service] = depends_on
        self._recalculate_order()
    
    def _recalculate_order(self):
        """Calculate topological startup order."""
        in_degree = {s: 0 for s in self.dependencies}
        for service, deps in self.dependencies.items():
            in_degree[service] = len(deps)
        
        queue = [s for s, d in in_degree.items() if d == 0]
        order = []
        
        while queue:
            service = queue.pop(0)
            order.append(service)
            
            for other, deps in self.dependencies.items():
                if service in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0 and other not in order:
                        queue.append(other)
        
        self.startup_order = order
    
    def get_startup_order(self) -> List[str]:
        """Get services in dependency-ordered startup sequence."""
        return list(self.startup_order)
    
    def can_start(self, service: str) -> Tuple[bool, List[str]]:
        """Check if a service can start (all dependencies ready)."""
        deps = self.dependencies.get(service, [])
        pending = [d for d in deps if self.service_status.get(d) != "running"]
        return len(pending) == 0, pending
    
    def mark_started(self, service: str):
        """Mark a service as started."""
        self.service_status[service] = "running"
    
    def mark_stopped(self, service: str):
        """Mark a service as stopped."""
        self.service_status[service] = "stopped"
    
    def get_dependents(self, service: str) -> List[str]:
        """Get services that depend on the given service."""
        return [s for s, deps in self.dependencies.items() if service in deps]
    
    def get_shutdown_order(self) -> List[str]:
        """Get services in reverse dependency order for shutdown."""
        return list(reversed(self.startup_order))


class ServiceMetricsCollector:
    """
    V7.6 P0: Collect and export service metrics.
    
    Aggregates metrics from all services for monitoring dashboards,
    alerting, and operational insights.
    """
    
    _instance = None
    
    def __init__(self):
        self.metrics: Dict[str, Dict] = {}
        self.metric_history: Dict[str, List] = {}
        self.max_history = 1000
        self._thread = None
        self._running = False
        self.collection_interval = 60
        self.logger = logging.getLogger("TITAN-METRICS")
    
    def collect_metrics(self) -> Dict:
        """Collect current metrics from all services."""
        mgr = get_service_manager()
        now = datetime.now(timezone.utc).isoformat()
        
        metrics = {
            "timestamp": now,
            "services": {}
        }
        
        # TX Monitor metrics
        if mgr.tx_monitor:
            try:
                stats = mgr.tx_monitor.get_stats()
                metrics["services"]["tx_monitor"] = {
                    "running": stats.get("running", False),
                    "total_tx": stats.get("total_transactions", 0),
                    "approved": stats.get("approved", 0),
                    "declined": stats.get("declined", 0),
                    "success_rate": stats.get("success_rate", 0)
                }
            except Exception:
                metrics["services"]["tx_monitor"] = {"error": "unavailable"}
        
        # Discovery scheduler metrics
        if mgr.discovery_scheduler:
            try:
                status = mgr.discovery_scheduler.get_status()
                metrics["services"]["discovery_scheduler"] = {
                    "running": status.get("running", False),
                    "last_run": status.get("last_run"),
                    "last_result": status.get("last_result")
                }
            except Exception:
                metrics["services"]["discovery_scheduler"] = {"error": "unavailable"}
        
        # Feedback loop metrics
        if mgr.feedback_loop:
            try:
                status = mgr.feedback_loop.get_status()
                metrics["services"]["feedback_loop"] = {
                    "running": status.get("running", False),
                    "tracked_sites": status.get("tracked_sites", 0),
                    "tracked_bins": status.get("tracked_bins", 0)
                }
            except Exception:
                metrics["services"]["feedback_loop"] = {"error": "unavailable"}
        
        # Memory pressure metrics
        if mgr.memory_pressure:
            try:
                status = mgr.memory_pressure.get_status()
                metrics["services"]["memory_pressure"] = {
                    "running": status.get("running", False),
                    "tier": status.get("tier", "unknown"),
                    "free_mb": status.get("free_mb", 0)
                }
            except Exception:
                metrics["services"]["memory_pressure"] = {"error": "unavailable"}
        
        # Store in history
        for service, data in metrics["services"].items():
            if service not in self.metric_history:
                self.metric_history[service] = []
            self.metric_history[service].append({
                "timestamp": now,
                "data": data
            })
            # Trim history
            if len(self.metric_history[service]) > self.max_history:
                self.metric_history[service] = self.metric_history[service][-self.max_history:]
        
        self.metrics = metrics
        return metrics
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        return self.metrics
    
    def get_metric_history(self, service: str, limit: int = 100) -> List:
        """Get metric history for a service."""
        history = self.metric_history.get(service, [])
        return history[-limit:]
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        for service, data in self.metrics.get("services", {}).items():
            prefix = f"titan_{service}"
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        lines.append(f"{prefix}_{key} {value}")
                    elif isinstance(value, bool):
                        lines.append(f'{prefix}_{key} {1 if value else 0}')
        return "\n".join(lines)
    
    def _collection_loop(self):
        """Metrics collection loop."""
        while self._running:
            try:
                self.collect_metrics()
            except Exception as e:
                self.logger.error(f"Metrics collection failed: {e}")
            time.sleep(self.collection_interval)
    
    def start(self):
        """Start metrics collection."""
        self._running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        self.logger.info("Service Metrics Collector started")
    
    def stop(self):
        """Stop metrics collection."""
        self._running = False


class ServiceConfigManager:
    """
    V7.6 P0: Centralized service configuration management.
    
    Provides unified configuration access for all services with
    validation, defaults, and hot-reload capability.
    """
    
    _instance = None
    CONFIG_FILE = Path("/opt/titan/data/services/service_config.json")
    
    def __init__(self):
        self.config: Dict = {}
        self.defaults: Dict = {}
        self.validators: Dict[str, callable] = {}
        self.change_callbacks: List[callable] = []
        self.logger = logging.getLogger("TITAN-CONFIG")
        
        self._register_defaults()
        self._load_config()
    
    def _register_defaults(self):
        """Register default configuration values."""
        self.defaults = {
            "tx_monitor": {
                "port": 7443,
                "autostart": True,
                "log_level": "INFO"
            },
            "discovery_scheduler": {
                "run_hour": 3,
                "autostart": True,
                "max_sites": 50
            },
            "feedback_loop": {
                "autostart": True,
                "update_interval_minutes": 30
            },
            "memory_pressure": {
                "autostart": True,
                "green_threshold_mb": 2500,
                "yellow_threshold_mb": 800,
                "red_threshold_mb": 400
            },
            "watchdog": {
                "autostart": True,
                "check_interval_seconds": 30,
                "max_restarts": 5
            }
        }
    
    def _load_config(self):
        """Load configuration from disk."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE) as f:
                    self.config = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                self.config = {}
        else:
            self.config = {}
    
    def _save_config(self):
        """Save configuration to disk."""
        try:
            self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def get(self, service: str, key: str, default=None):
        """Get a configuration value."""
        service_config = self.config.get(service, {})
        if key in service_config:
            return service_config[key]
        
        service_defaults = self.defaults.get(service, {})
        if key in service_defaults:
            return service_defaults[key]
        
        return default
    
    def set(self, service: str, key: str, value):
        """Set a configuration value."""
        if service not in self.config:
            self.config[service] = {}
        
        # Validate if validator registered
        validator_key = f"{service}.{key}"
        if validator_key in self.validators:
            if not self.validators[validator_key](value):
                raise ValueError(f"Invalid value for {validator_key}: {value}")
        
        old_value = self.config[service].get(key)
        self.config[service][key] = value
        self._save_config()
        
        # Notify callbacks
        for callback in self.change_callbacks:
            try:
                callback(service, key, old_value, value)
            except Exception:
                pass
    
    def get_service_config(self, service: str) -> Dict:
        """Get all configuration for a service."""
        defaults = self.defaults.get(service, {}).copy()
        overrides = self.config.get(service, {})
        defaults.update(overrides)
        return defaults
    
    def register_validator(self, service: str, key: str, validator: callable):
        """Register a validator for a config key."""
        self.validators[f"{service}.{key}"] = validator
    
    def register_change_callback(self, callback: callable):
        """Register a callback for config changes."""
        self.change_callbacks.append(callback)
    
    def export_config(self) -> Dict:
        """Export full configuration with defaults merged."""
        result = {}
        for service in set(list(self.defaults.keys()) + list(self.config.keys())):
            result[service] = self.get_service_config(service)
        return result
    
    def reset_to_defaults(self, service: str = None):
        """Reset configuration to defaults."""
        if service:
            if service in self.config:
                del self.config[service]
        else:
            self.config = {}
        self._save_config()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON GETTERS
# ═══════════════════════════════════════════════════════════════════════════

def get_service_health_watchdog() -> ServiceHealthWatchdog:
    """Get singleton ServiceHealthWatchdog instance."""
    if ServiceHealthWatchdog._instance is None:
        ServiceHealthWatchdog._instance = ServiceHealthWatchdog()
    return ServiceHealthWatchdog._instance


def get_service_dependency_manager() -> ServiceDependencyManager:
    """Get singleton ServiceDependencyManager instance."""
    if ServiceDependencyManager._instance is None:
        ServiceDependencyManager._instance = ServiceDependencyManager()
    return ServiceDependencyManager._instance


def get_service_metrics_collector() -> ServiceMetricsCollector:
    """Get singleton ServiceMetricsCollector instance."""
    if ServiceMetricsCollector._instance is None:
        ServiceMetricsCollector._instance = ServiceMetricsCollector()
    return ServiceMetricsCollector._instance


def get_service_config_manager() -> ServiceConfigManager:
    """Get singleton ServiceConfigManager instance."""
    if ServiceConfigManager._instance is None:
        ServiceConfigManager._instance = ServiceConfigManager()
    return ServiceConfigManager._instance
