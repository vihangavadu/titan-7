#!/usr/bin/env python3
"""
TITAN V7.6 MASTER AUTOMATION
=============================
Complete end-to-end automation system with research feedback loop.

This is the master entry point that integrates:
  - titan_automation_orchestrator.py → E2E operation automation
  - titan_operation_logger.py → Comprehensive logging
  - titan_detection_analyzer.py → 2-day detection research
  - titan_auto_patcher.py → Auto-patching feedback loop

The Complete Flow:
  ┌──────────────────────────────────────────────────────────────────┐
  │                    TITAN AUTOMATION LOOP                         │
  └──────────────────────────────────────────────────────────────────┘
                          │
                          ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  ORCHESTRATOR → Runs operations automatically                    │
  │  - Card validation, profile generation, network setup            │
  │  - Browser launch, checkout, 3DS handling, KYC bypass            │
  │  - Logs every step with detailed metrics                         │
  └──────────────────────────────────────────────────────────────────┘
                          │
                          ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  LOGGER → Records everything for analysis                        │
  │  - Operation results, phase timings, detection signals           │
  │  - SQLite database for analytics queries                         │
  │  - Success rates by target, time, configuration                  │
  └──────────────────────────────────────────────────────────────────┘
                          │
                          ▼ (after 2 days)
  ┌──────────────────────────────────────────────────────────────────┐
  │  ANALYZER → Researches detection patterns                        │
  │  - Identifies detection signatures (IP, fingerprint, behavior)   │
  │  - Root cause analysis for failures                              │
  │  - Generates patch recommendations                               │
  └──────────────────────────────────────────────────────────────────┘
                          │
                          ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  PATCHER → Applies fixes automatically                           │
  │  - Adjusts module parameters                                     │
  │  - Validates patch effectiveness                                 │
  │  - Rolls back ineffective patches                                │
  └──────────────────────────────────────────────────────────────────┘
                          │
                          └──────────────► (back to orchestrator)

Usage:
    # Run a single test operation
    python titan_master_automation.py --test
    
    # Run batch of operations
    python titan_master_automation.py --batch batch_config.json
    
    # Run detection research (after 2 days of operations)
    python titan_master_automation.py --research --days 2
    
    # Run auto-patch cycle
    python titan_master_automation.py --patch-cycle
    
    # Start the full automation loop (daemon mode)
    python titan_master_automation.py --daemon
"""

import os
import sys
import json
import time
import signal
import argparse
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("TITAN-MASTER")


class TitanMasterAutomation:
    """
    Master automation controller for TITAN.
    
    Integrates orchestrator, logger, analyzer, and patcher
    into a unified automation system.
    """
    
    def __init__(self, log_dir: Optional[Path] = None,
                 config_dir: Optional[Path] = None):
        """
        Initialize master automation.
        
        Args:
            log_dir: Directory for logs
            config_dir: Directory for configs
        """
        self.log_dir = log_dir or Path("/opt/titan/logs")
        self.config_dir = config_dir or Path("/opt/titan/config")
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Component instances (lazy loaded)
        self._orchestrator = None
        self._logger = None
        self._analyzer = None
        self._patcher = None
        
        # Daemon state
        self._running = False
        
        logger.info("TITAN Master Automation initialized")
    
    @property
    def orchestrator(self):
        """Get or create orchestrator."""
        if self._orchestrator is None:
            from titan_automation_orchestrator import TitanOrchestrator
            self._orchestrator = TitanOrchestrator(self.log_dir)
        return self._orchestrator
    
    @property
    def op_logger(self):
        """Get or create operation logger."""
        if self._logger is None:
            from titan_operation_logger import TitanOperationLogger
            self._logger = TitanOperationLogger(self.log_dir)
        return self._logger
    
    @property
    def analyzer(self):
        """Get or create detection analyzer."""
        if self._analyzer is None:
            from titan_detection_analyzer import DetectionAnalyzer
            self._analyzer = DetectionAnalyzer(self.log_dir)
        return self._analyzer
    
    @property
    def patcher(self):
        """Get or create auto-patcher."""
        if self._patcher is None:
            from titan_auto_patcher import AutoPatcher
            self._patcher = AutoPatcher(self.config_dir)
        return self._patcher
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OPERATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_test_operation(self) -> Dict:
        """Run a test operation to verify system."""
        from titan_automation_orchestrator import (
            OperationConfig, BillingAddress, PersonaConfig
        )
        
        # Create test config
        config = OperationConfig(
            card_number="4111111111111111",
            card_exp="12/25",
            card_cvv="123",
            billing_address=BillingAddress(
                first_name="John",
                last_name="Doe",
                street="123 Test Street",
                city="New York",
                state="NY",
                zip_code="10001",
                country="US"
            ),
            persona=PersonaConfig(
                first_name="John",
                last_name="Doe",
                dob="1990-01-15"
            ),
            target_url="https://example.com/checkout",
            target_domain="example.com"
        )
        
        # Run operation
        result = self.orchestrator.run_operation(config)
        return result.to_dict()
    
    def run_operation(self, config_dict: Dict) -> Dict:
        """
        Run operation from config dictionary.
        
        Args:
            config_dict: Operation configuration
            
        Returns:
            Operation result
        """
        from titan_automation_orchestrator import (
            OperationConfig, BillingAddress, PersonaConfig
        )
        
        config = OperationConfig(
            card_number=config_dict["card"]["number"],
            card_exp=config_dict["card"]["exp"],
            card_cvv=config_dict["card"]["cvv"],
            billing_address=BillingAddress(**config_dict["billing"]),
            persona=PersonaConfig(**config_dict.get("persona", {
                "first_name": "John",
                "last_name": "Doe",
                "dob": "1990-01-01"
            })),
            target_url=config_dict["target"]["url"],
            target_domain=config_dict["target"].get("domain", "")
        )
        
        result = self.orchestrator.run_operation(config)
        return result.to_dict()
    
    def run_batch(self, batch_config: Dict) -> Dict:
        """
        Run batch of operations.
        
        Args:
            batch_config: Batch configuration with operations list
            
        Returns:
            Batch summary
        """
        from titan_automation_orchestrator import (
            BatchAutomation, OperationConfig, BillingAddress, PersonaConfig
        )
        
        batch = BatchAutomation(self.orchestrator)
        
        configs = []
        for op in batch_config["operations"]:
            config = OperationConfig(
                card_number=op["card"]["number"],
                card_exp=op["card"]["exp"],
                card_cvv=op["card"]["cvv"],
                billing_address=BillingAddress(**op["billing"]),
                persona=PersonaConfig(**op.get("persona", {
                    "first_name": "John",
                    "last_name": "Doe",
                    "dob": "1990-01-01"
                })),
                target_url=op["target"]["url"]
            )
            configs.append(config)
        
        delay = batch_config.get("delay_between", 5.0)
        summary = batch.run_batch(configs, delay_between=delay)
        
        return summary
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_detection_research(self, days: int = 2) -> Dict:
        """
        Run detection research analysis.
        
        Args:
            days: Days of data to analyze
            
        Returns:
            Research report
        """
        report = self.analyzer.run_research_cycle(days)
        return report.to_dict()
    
    def get_success_stats(self, days: int = 7) -> Dict:
        """Get success rate statistics."""
        return self.op_logger.get_success_rate(days)
    
    def get_detection_patterns(self, days: int = 2) -> Dict:
        """Get detection patterns."""
        return self.op_logger.get_detection_patterns(days)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PATCHING METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_patch_cycle(self, days: int = 2) -> Dict:
        """
        Run auto-patch cycle.
        
        Args:
            days: Days of data for analysis
            
        Returns:
            Patch cycle results
        """
        return self.patcher.run_auto_patch_cycle(days)
    
    def get_patch_effectiveness(self) -> Dict:
        """Get patch effectiveness report."""
        return self.patcher.get_effectiveness_report()
    
    def get_current_configs(self) -> Dict:
        """Get current module configurations."""
        return self.patcher.get_all_configs()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON MODE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_daemon(self, patch_interval_hours: int = 24,
                    research_days: int = 2):
        """
        Start daemon mode with automatic research and patching.
        
        Args:
            patch_interval_hours: Hours between patch cycles
            research_days: Days of data per research cycle
        """
        from titan_auto_patcher import FeedbackLoopManager
        
        logger.info("=" * 60)
        logger.info("  TITAN MASTER AUTOMATION - DAEMON MODE")
        logger.info("=" * 60)
        logger.info(f"  Patch interval: {patch_interval_hours} hours")
        logger.info(f"  Research window: {research_days} days")
        logger.info("=" * 60)
        
        # Setup signal handlers
        self._running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start feedback loop
        feedback = FeedbackLoopManager()
        feedback.enable(patch_interval_hours, research_days)
        
        logger.info("Daemon started. Press Ctrl+C to stop.")
        
        # Keep running
        while self._running:
            time.sleep(1)
        
        feedback.disable()
        logger.info("Daemon stopped.")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received...")
        self._running = False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS AND REPORTING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_system_status(self) -> Dict:
        """Get overall system status."""
        # Success stats
        try:
            stats = self.op_logger.get_success_rate(7)
        except Exception:
            stats = {"success_rate": 0, "total_operations": 0}
        
        # Patch status
        try:
            patch_status = self.patcher.get_effectiveness_report()
        except Exception:
            patch_status = {"total_patches": 0}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "success_rate_7d": stats.get("success_rate", 0),
            "total_operations_7d": stats.get("total_operations", 0),
            "patches_applied": patch_status.get("total_patches", 0),
            "patches_validated": patch_status.get("validated", 0),
            "avg_improvement": patch_status.get("avg_improvement", 0),
            "log_dir": str(self.log_dir),
            "config_dir": str(self.config_dir)
        }
    
    def generate_full_report(self, days: int = 7) -> Dict:
        """Generate full automation report."""
        return {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "success_stats": self.get_success_stats(days),
            "detection_patterns": self.get_detection_patterns(min(days, 2)),
            "patch_effectiveness": self.get_patch_effectiveness(),
            "current_configs": self.get_current_configs()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TITAN Master Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run test operation
  python titan_master_automation.py --test

  # Run batch operations
  python titan_master_automation.py --batch operations.json

  # Run detection research
  python titan_master_automation.py --research --days 2

  # Run auto-patch cycle
  python titan_master_automation.py --patch-cycle

  # Start daemon mode
  python titan_master_automation.py --daemon

  # Get system status
  python titan_master_automation.py --status

  # Generate full report
  python titan_master_automation.py --report
        """
    )
    
    # Commands
    parser.add_argument("--test", action="store_true",
                       help="Run test operation")
    parser.add_argument("--operation", metavar="FILE",
                       help="Run single operation from JSON file")
    parser.add_argument("--batch", metavar="FILE",
                       help="Run batch operations from JSON file")
    parser.add_argument("--research", action="store_true",
                       help="Run detection research")
    parser.add_argument("--patch-cycle", action="store_true",
                       help="Run auto-patch cycle")
    parser.add_argument("--daemon", action="store_true",
                       help="Start daemon mode")
    parser.add_argument("--status", action="store_true",
                       help="Show system status")
    parser.add_argument("--report", action="store_true",
                       help="Generate full report")
    
    # Options
    parser.add_argument("--days", type=int, default=2,
                       help="Days for analysis (default: 2)")
    parser.add_argument("--interval", type=int, default=24,
                       help="Patch interval in hours (daemon mode, default: 24)")
    parser.add_argument("--log-dir", metavar="DIR",
                       help="Log directory")
    parser.add_argument("--config-dir", metavar="DIR",
                       help="Config directory")
    
    args = parser.parse_args()
    
    # Initialize
    log_dir = Path(args.log_dir) if args.log_dir else None
    config_dir = Path(args.config_dir) if args.config_dir else None
    master = TitanMasterAutomation(log_dir, config_dir)
    
    # Execute command
    if args.test:
        print("\n=== RUNNING TEST OPERATION ===\n")
        result = master.run_test_operation()
        print(json.dumps(result, indent=2))
        
    elif args.operation:
        print(f"\n=== RUNNING OPERATION: {args.operation} ===\n")
        with open(args.operation) as f:
            config = json.load(f)
        result = master.run_operation(config)
        print(json.dumps(result, indent=2))
        
    elif args.batch:
        print(f"\n=== RUNNING BATCH: {args.batch} ===\n")
        with open(args.batch) as f:
            batch_config = json.load(f)
        result = master.run_batch(batch_config)
        print(json.dumps(result, indent=2))
        
    elif args.research:
        print(f"\n=== RUNNING DETECTION RESEARCH ({args.days} days) ===\n")
        result = master.run_detection_research(args.days)
        print(result.get("executive_summary", ""))
        print(f"\nFull report saved to: {master.log_dir}/research/")
        
    elif args.patch_cycle:
        print(f"\n=== RUNNING AUTO-PATCH CYCLE ({args.days} days) ===\n")
        result = master.run_patch_cycle(args.days)
        print(json.dumps(result, indent=2))
        
    elif args.daemon:
        print("\n=== STARTING DAEMON MODE ===\n")
        master.start_daemon(args.interval, args.days)
        
    elif args.status:
        print("\n=== SYSTEM STATUS ===\n")
        status = master.get_system_status()
        print(json.dumps(status, indent=2))
        
    elif args.report:
        print(f"\n=== GENERATING FULL REPORT ({args.days} days) ===\n")
        report = master.generate_full_report(args.days)
        
        # Save to file
        report_file = master.log_dir / f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved: {report_file}")
        print(f"\nSummary:")
        print(f"  Success Rate (7d): {report['success_stats'].get('success_rate', 0)*100:.1f}%")
        print(f"  Total Operations: {report['success_stats'].get('total_operations', 0)}")
        print(f"  Patches Applied: {report['patch_effectiveness'].get('total_patches', 0)}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
