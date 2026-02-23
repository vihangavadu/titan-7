#!/usr/bin/env python3
"""
CORTEX AGENT: Autonomous Pre-Init Logic for PROMETHEUS-CORE Pipeline
=====================================================================

This is a standalone wrapper script that runs BEFORE main_v5.py or any core 
pipeline modules execute. It performs autonomous pre-flight checks including:

1. MCP Server Health Probes (IP scoring, proxy health, MLA status)
2. LLM-based Context-Aware Configuration (dynamic entropy/aging parameters)
3. Environment Pre-checks and Validation
4. Error Resilience Mesh with graceful fallback

If all agentic checks pass, this script invokes main_v5.py with dynamic config.
If agentic checks fail, it aborts or falls back to static/safe configuration.

CRITICAL: This is a WRAPPER. Legacy code in core/* remains UNTOUCHED.
No refactoring, no monkey-patching - only orchestration.

Usage:
    python cortex_agent.py [--proxy PROXY] [--zip ZIP] [--age AGE] [options]
    
    Options from main_v5.py are passed through automatically after pre-flight.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [CORTEX AGENT] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/cortex_agent.log', mode='a')
    ]
)
logger = logging.getLogger("CortexAgent")

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)


# ============================================================================
# CORTEX AGENT CLASS
# ============================================================================

class CortexAgent:
    """
    Autonomous Pre-Flight Orchestrator for PROMETHEUS-CORE Pipeline.
    
    This class serves as a front-controller that:
    - Validates environment and dependencies
    - Probes external services (MCP servers, MLA API, proxies)
    - Queries LLM for intelligent configuration recommendations
    - Launches main_v5.py with optimized parameters
    - Handles all error conditions gracefully
    """
    
    def __init__(self, args: argparse.Namespace):
        """
        Initialize Cortex Agent with command-line arguments.
        
        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self.logger = logger
        self.status = {
            "timestamp": str(datetime.now()),
            "environment": {},
            "mcp_health": {},
            "mla_health": {},
            "proxy_health": {},
            "llm_analysis": {},
            "errors": [],
            "warnings": []
        }
        
        # Dynamic configuration derived from agentic logic
        self.dynamic_config = {
            "proxy": args.proxy,
            "zip_code": args.zip,
            "age_days": args.age,
            "config_source": "user_input"
        }
        
        self.logger.info("=" * 80)
        self.logger.info("CORTEX AGENT INITIALIZED - Autonomous Pre-Init Protocol")
        self.logger.info("=" * 80)
    
    async def run_preflight_checks(self) -> bool:
        """
        Execute all pre-flight checks in sequence.
        
        Returns:
            True if all critical checks pass, False otherwise
        """
        self.logger.info("[PHASE 0] PREFLIGHT CHECKS - Starting Autonomous Reconnaissance")
        
        checks = [
            ("Environment Validation", self._check_environment),
            ("MCP Infrastructure Probe", self._probe_mcp_servers),
            ("MLA API Health Check", self._check_mla_api),
            ("Proxy Health Validation", self._check_proxy_health),
            ("LLM Configuration Analysis", self._query_llm_for_config)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            self.logger.info(f"  > Running: {check_name}")
            try:
                result = await check_func()
                if result:
                    self.logger.info(f"    ✓ PASS: {check_name}")
                else:
                    self.logger.warning(f"    ⚠ PARTIAL: {check_name} (non-critical)")
                    self.status["warnings"].append(f"{check_name} returned partial success")
            except Exception as e:
                self.logger.error(f"    ✗ FAIL: {check_name} - {e}")
                self.status["errors"].append(f"{check_name}: {str(e)}")
                # Only mark as failed if it's a critical check
                if check_name in ["Environment Validation"]:
                    all_passed = False
        
        return all_passed
    
    async def _check_environment(self) -> bool:
        """
        Validate environment prerequisites.
        
        Returns:
            True if environment is valid
        """
        env_status = {}
        
        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        env_status["python_version"] = python_version
        self.logger.info(f"    Python Version: {python_version}")
        
        # Check critical directories
        critical_dirs = ["logs", "profiles", "config", "core"]
        for dir_name in critical_dirs:
            dir_path = Path(dir_name)
            exists = dir_path.exists()
            env_status[f"dir_{dir_name}"] = exists
            if not exists and dir_name in ["logs", "profiles"]:
                os.makedirs(dir_name, exist_ok=True)
                self.logger.info(f"    Created directory: {dir_name}")
        
        # Check for core modules
        try:
            from core.mcp_interface import MCPClient
            from core.intelligence import IntelligenceCore
            env_status["core_modules"] = True
            self.logger.info("    Core modules available: ✓")
        except ImportError as e:
            env_status["core_modules"] = False
            self.logger.warning(f"    Core modules check: {e}")
        
        # Check environment variables
        openai_key = os.getenv("OPENAI_API_KEY")
        env_status["openai_api_key"] = bool(openai_key)
        if openai_key:
            self.logger.info("    OPENAI_API_KEY: Set (LLM analysis enabled)")
        else:
            self.logger.info("    OPENAI_API_KEY: Not set (fallback mode)")
        
        self.status["environment"] = env_status
        return True
    
    async def _probe_mcp_servers(self) -> bool:
        """
        Probe MCP (Model Context Protocol) servers for health status.
        
        Returns:
            True if MCP infrastructure is available
        """
        try:
            from core.mcp_interface import MCPClient
            
            mcp = MCPClient(self.logger)
            is_healthy = await mcp.health_check()
            
            # Safely get servers list
            servers = list(mcp.servers.keys()) if hasattr(mcp, 'servers') and mcp.servers else []
            
            self.status["mcp_health"] = {
                "available": is_healthy,
                "servers": servers
            }
            
            if is_healthy:
                self.logger.info("    MCP Infrastructure: ONLINE")
                # Try a simple fetch test
                try:
                    test_result = await asyncio.wait_for(
                        mcp.fetch_url("https://www.wikipedia.org"),
                        timeout=10.0
                    )
                    if test_result:
                        self.logger.info(f"    MCP Test Fetch: SUCCESS ({len(test_result)} bytes)")
                        self.status["mcp_health"]["test_fetch"] = "success"
                    else:
                        self.logger.warning("    MCP Test Fetch: FAILED (but infrastructure available)")
                        self.status["mcp_health"]["test_fetch"] = "failed"
                except asyncio.TimeoutError:
                    self.logger.warning("    MCP Test Fetch: TIMEOUT")
                    self.status["mcp_health"]["test_fetch"] = "timeout"
            else:
                self.logger.warning("    MCP Infrastructure: OFFLINE (will use TLS fallback)")
            
            return is_healthy
        
        except ImportError:
            self.logger.warning("    MCP modules not available - skipping")
            self.status["mcp_health"] = {"available": False, "reason": "import_error"}
            return False
        except Exception as e:
            self.logger.error(f"    MCP probe failed: {e}")
            self.status["mcp_health"] = {"available": False, "error": str(e)}
            return False
    
    async def _check_mla_api(self) -> bool:
        """
        Check Multilogin Agent (MLA) API availability.
        
        Returns:
            True if MLA API is reachable
        """
        try:
            import requests
            
            # Common MLA API endpoints
            mla_ports = [35000, 45000, 35001]
            mla_endpoints = ["/api/v1/profile/active", "/api/v2/profile", "/"]
            
            for port in mla_ports:
                for endpoint in mla_endpoints:
                    url = f"http://localhost:{port}{endpoint}"
                    try:
                        response = requests.get(url, timeout=2)
                        if response.status_code in [200, 404, 401]:  # Any response means API is alive
                            self.logger.info(f"    MLA API found at port {port}: {response.status_code}")
                            self.status["mla_health"] = {
                                "available": True,
                                "port": port,
                                "endpoint": endpoint,
                                "status_code": response.status_code
                            }
                            return True
                    except requests.exceptions.RequestException:
                        continue
            
            # No MLA API found
            self.logger.warning("    MLA API: NOT REACHABLE (manual profile export may be required)")
            self.status["mla_health"] = {
                "available": False,
                "reason": "no_response_on_common_ports"
            }
            return False
        
        except ImportError:
            self.logger.warning("    requests library not available - skipping MLA check")
            self.status["mla_health"] = {"available": False, "reason": "import_error"}
            return False
        except Exception as e:
            self.logger.error(f"    MLA API check failed: {e}")
            self.status["mla_health"] = {"available": False, "error": str(e)}
            return False
    
    async def _check_proxy_health(self) -> bool:
        """
        Validate proxy configuration and health.
        
        Returns:
            True if proxy is valid and healthy
        """
        if not self.args.proxy:
            self.logger.info("    Proxy: Not configured (direct connection mode)")
            self.status["proxy_health"] = {
                "configured": False,
                "mode": "direct"
            }
            return True
        
        try:
            # Parse proxy URL
            proxy_url = self.args.proxy
            self.logger.info(f"    Proxy configured: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")
            
            # Try to validate proxy with a simple request
            try:
                from core.tls_mimic import TLSMimic
                
                tls = TLSMimic(proxy_url=proxy_url)
                ip_info = tls.check_ip_trust()
                
                if ip_info:
                    self.logger.info(f"    Proxy IP Trust Check: SUCCESS")
                    self.logger.info(f"      IP: {ip_info.get('ip', 'unknown')}")
                    self.logger.info(f"      Location: {ip_info.get('city', 'unknown')}, {ip_info.get('country', 'unknown')}")
                    self.status["proxy_health"] = {
                        "configured": True,
                        "healthy": True,
                        "ip_info": ip_info
                    }
                    return True
                else:
                    self.logger.warning("    Proxy IP Trust Check: FAILED (proxy may be invalid)")
                    self.status["proxy_health"] = {
                        "configured": True,
                        "healthy": False,
                        "reason": "trust_check_failed"
                    }
                    return False
            except ImportError:
                self.logger.warning("    TLS Mimic module not available - basic proxy validation only")
                self.status["proxy_health"] = {
                    "configured": True,
                    "healthy": "unknown",
                    "reason": "tls_mimic_unavailable"
                }
                return True
        
        except Exception as e:
            self.logger.error(f"    Proxy validation failed: {e}")
            self.status["proxy_health"] = {
                "configured": True,
                "healthy": False,
                "error": str(e)
            }
            return False
    
    async def _query_llm_for_config(self) -> bool:
        """
        Query LLM (via Intelligence Core) for context-aware configuration.
        
        Returns:
            True if LLM analysis completed (or fallback used)
        """
        try:
            from core.intelligence import IntelligenceCore
            
            brain = IntelligenceCore(self.logger)
            
            # Select a target URL for analysis (use first trust anchor from config)
            try:
                from config.settings import SETTINGS
                target_url = SETTINGS.get("trust_anchors", ["https://www.wikipedia.org"])[0]
            except ImportError:
                target_url = "https://www.wikipedia.org"
            
            self.logger.info(f"    Analyzing target: {target_url}")
            
            # Fetch target data (try MCP first, then fallback to TLS)
            raw_data = ""
            try:
                from core.mcp_interface import MCPClient
                mcp = MCPClient(self.logger)
                if self.status.get("mcp_health", {}).get("available"):
                    raw_data = await asyncio.wait_for(
                        mcp.fetch_url(target_url),
                        timeout=10.0
                    ) or ""
            except Exception:
                pass
            
            # Fallback to TLS if MCP failed
            if not raw_data:
                try:
                    from core.tls_mimic import TLSMimic
                    tls = TLSMimic(proxy_url=self.args.proxy)
                    resp = tls.get(target_url)
                    if resp and resp.status_code == 200:
                        raw_data = resp.text
                except Exception:
                    pass
            
            # Perform LLM analysis
            strategy = await brain.analyze_target(target_url, raw_data)
            
            self.logger.info("    LLM Analysis Complete:")
            self.logger.info(f"      Trust Level: {strategy.get('trust_level', 'unknown')}")
            self.logger.info(f"      Risk Assessment: {strategy.get('risk_assessment', 'unknown')}")
            self.logger.info(f"      Recommended Age: {strategy.get('recommended_age_days', self.args.age)} days")
            self.logger.info(f"      Strategy Notes: {strategy.get('strategy_notes', 'N/A')}")
            
            # Store LLM analysis
            self.status["llm_analysis"] = strategy
            
            # Update dynamic config if user didn't explicitly set age
            if not self._is_age_explicitly_set():
                old_age = self.dynamic_config["age_days"]
                self.dynamic_config["age_days"] = strategy.get("recommended_age_days", old_age)
                self.dynamic_config["config_source"] = "llm_analysis"
                if old_age != self.dynamic_config["age_days"]:
                    self.logger.info(f"    Age parameter ADJUSTED: {old_age} -> {self.dynamic_config['age_days']} days")
            else:
                self.logger.info(f"    Age parameter LOCKED (user override): {self.dynamic_config['age_days']} days")
            
            return True
        
        except ImportError:
            self.logger.warning("    Intelligence Core not available - using static config")
            self.status["llm_analysis"] = {"available": False, "reason": "import_error"}
            return True  # Non-critical failure
        except Exception as e:
            self.logger.error(f"    LLM analysis failed: {e}")
            self.status["llm_analysis"] = {"available": False, "error": str(e)}
            return True  # Non-critical failure
    
    def _is_age_explicitly_set(self) -> bool:
        """
        Check if age parameter was explicitly set by user.
        
        Returns:
            True if user provided --age argument
        """
        # Check if age was in sys.argv
        return "--age" in sys.argv
    
    def _save_status_report(self) -> str:
        """
        Save pre-flight status report to file.
        
        Returns:
            Path to the saved report
        """
        report_path = f"logs/cortex_agent_status_{int(datetime.now().timestamp())}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.status, f, indent=2, default=str)
        
        self.logger.info(f"  Status report saved: {report_path}")
        return report_path
    
    async def launch_main_v5(self) -> int:
        """
        Launch main_v5.py with dynamic configuration.
        
        Returns:
            Exit code from main_v5.py
        """
        self.logger.info("[PHASE 1] LAUNCHING PROMETHEUS-CORE PIPELINE")
        self.logger.info("  Target: main_v5.py")
        self.logger.info(f"  Dynamic Config: {json.dumps(self.dynamic_config, indent=4)}")
        
        # Construct command for main_v5.py
        cmd = [sys.executable, "main_v5.py"]
        
        if self.dynamic_config["proxy"]:
            cmd.extend(["--proxy", self.dynamic_config["proxy"]])
        if self.dynamic_config["zip_code"]:
            cmd.extend(["--zip", self.dynamic_config["zip_code"]])
        cmd.extend(["--age", str(self.dynamic_config["age_days"])])
        
        self.logger.info(f"  Command: {' '.join(cmd)}")
        
        try:
            # Execute main_v5.py
            result = subprocess.run(cmd, cwd=os.getcwd(), timeout=300)
            return result.returncode
        except Exception as e:
            self.logger.error(f"  Failed to launch main_v5.py: {e}")
            return 1
    
    async def execute(self) -> int:
        """
        Execute the full Cortex Agent workflow.
        
        Returns:
            Exit code (0 for success)
        """
        try:
            # Phase 0: Pre-flight checks
            preflight_passed = await self.run_preflight_checks()
            
            # Save status report
            report_path = self._save_status_report()
            
            # Decision logic
            if preflight_passed:
                self.logger.info("")
                self.logger.info("=" * 80)
                self.logger.info("PREFLIGHT CHECKS: ALL CRITICAL CHECKS PASSED")
                self.logger.info("=" * 80)
                self.logger.info("")
                
                # Launch main_v5.py
                return await self.launch_main_v5()
            else:
                self.logger.error("")
                self.logger.error("=" * 80)
                self.logger.error("PREFLIGHT CHECKS: CRITICAL FAILURES DETECTED")
                self.logger.error("=" * 80)
                self.logger.error(f"Errors: {len(self.status['errors'])}")
                for error in self.status["errors"]:
                    self.logger.error(f"  - {error}")
                self.logger.error("")
                
                # Fallback decision
                if self.args.force:
                    self.logger.warning("FORCE MODE ENABLED - Launching despite failures")
                    return await self.launch_main_v5()
                else:
                    self.logger.error("ABORTING - Use --force to override")
                    return 1
        
        except KeyboardInterrupt:
            self.logger.warning("Operation cancelled by user")
            return 130
        except Exception as e:
            self.logger.error(f"Fatal error in Cortex Agent: {e}", exc_info=True)
            return 1


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Cortex Agent: Autonomous Pre-Init Wrapper for PROMETHEUS-CORE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full autonomous mode with proxy
  python cortex_agent.py --proxy user:pass@host:port --zip 10001

  # Manual age override
  python cortex_agent.py --age 150 --zip 10001

  # Force launch even if pre-flight fails
  python cortex_agent.py --force --zip 10001

  # Dry-run mode (pre-flight only, no launch)
  python cortex_agent.py --dry-run
        """
    )
    
    # Arguments passed through to main_v5.py
    parser.add_argument("--proxy", help="Proxy URL (user:pass@host:port)", default=None)
    parser.add_argument("--zip", help="Zip code for profile", default="10001")
    parser.add_argument("--age", type=int, default=90, help="Profile age in days (default: 90)")
    
    # Cortex Agent specific arguments
    parser.add_argument("--force", action="store_true", help="Force launch even if pre-flight fails")
    parser.add_argument("--dry-run", action="store_true", help="Run pre-flight only, don't launch main_v5.py")
    
    return parser.parse_args()


async def main() -> int:
    """
    Main entry point for Cortex Agent.
    
    Returns:
        Exit code
    """
    args = parse_arguments()
    
    # Initialize Cortex Agent
    agent = CortexAgent(args)
    
    # Dry-run mode
    if args.dry_run:
        logger.info("DRY-RUN MODE: Pre-flight checks only")
        await agent.run_preflight_checks()
        agent._save_status_report()
        logger.info("Dry-run complete. Exiting without launching main_v5.py")
        return 0
    
    # Full execution
    return await agent.execute()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
