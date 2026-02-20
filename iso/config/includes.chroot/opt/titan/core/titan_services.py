"""
TITAN V7.5 SINGULARITY — Service Orchestrator
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
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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
        now = datetime.utcnow()
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
            
            self._last_run = datetime.utcnow().isoformat() + "Z"
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
            now = datetime.utcnow()
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
                        "updated": datetime.utcnow().isoformat() + "Z",
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
                        "updated": datetime.utcnow().isoformat() + "Z",
                    }
                    updated_bins += 1
            
            self._feedback_data["last_update"] = datetime.utcnow().isoformat() + "Z"
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
        self._started = False
        logger.info("All TITAN services stopped")
    
    def get_status(self) -> Dict:
        return {
            "started": self._started,
            "tx_monitor": self.tx_monitor.get_stats() if self.tx_monitor else {"status": "not started"},
            "discovery_scheduler": self.discovery_scheduler.get_status() if self.discovery_scheduler else {"status": "not started"},
            "feedback_loop": self.feedback_loop.get_status() if self.feedback_loop else {"status": "not started"},
            "memory_pressure": self.memory_pressure.get_status() if self.memory_pressure else {"status": "not started"},
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
