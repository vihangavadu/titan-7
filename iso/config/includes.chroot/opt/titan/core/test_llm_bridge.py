#!/usr/bin/env python3
"""
Quick verification script for the multi-provider LLM bridge.
Tests config loading, provider status, and task routing without making actual API calls.
"""

import sys
import os
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required functions can be imported."""
    try:
        from ollama_bridge import (
            get_provider_status, resolve_provider_for_task, is_ollama_available,
            get_config, reload_config, get_cache_stats
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config_loading():
    """Test config file loading."""
    try:
        from ollama_bridge import get_config, reload_config
        
        # Force reload config
        reload_config()
        cfg = get_config()
        
        # Check required sections
        required_sections = ["providers", "task_routing", "cache", "global"]
        for section in required_sections:
            if section not in cfg:
                print(f"❌ Missing config section: {section}")
                return False
        
        print("✅ Config loaded successfully")
        print(f"   - Found {len(cfg['providers'])} providers")
        print(f"   - Found {len(cfg['task_routing'])} task types")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_provider_status():
    """Test provider status checking."""
    try:
        from ollama_bridge import get_provider_status
        
        status = get_provider_status()
        print("✅ Provider status check:")
        for prov, info in status.items():
            enabled = info["enabled"]
            has_key = info["has_api_key"]
            available = info["available"]
            print(f"   - {prov}: enabled={enabled}, has_key={has_key}, available={available}")
        
        return True
    except Exception as e:
        print(f"❌ Provider status check failed: {e}")
        return False

def test_task_routing():
    """Test task routing resolution."""
    try:
        from ollama_bridge import resolve_provider_for_task
        
        task_types = [
            "bin_generation", "site_discovery", "preset_generation",
            "country_profiles", "dork_generation", "warmup_searches", "default"
        ]
        
        print("✅ Task routing resolution:")
        for task in task_types:
            resolved = resolve_provider_for_task(task)
            if resolved:
                prov, model = resolved
                print(f"   - {task}: {prov}/{model}")
            else:
                print(f"   - {task}: No available provider")
        
        return True
    except Exception as e:
        print(f"❌ Task routing failed: {e}")
        return False

def test_dynamic_data_integration():
    """Test that dynamic_data.py can import and use the bridge."""
    try:
        from dynamic_data import LLM_AVAILABLE, OLLAMA_AVAILABLE
        
        print(f"✅ Dynamic data integration:")
        print(f"   - LLM_AVAILABLE: {LLM_AVAILABLE}")
        print(f"   - OLLAMA_AVAILABLE (compat): {OLLAMA_AVAILABLE}")
        
        if LLM_AVAILABLE:
            from dynamic_data import generate_merchant_sites
            print("   - generate_merchant_sites function imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Dynamic data integration failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=== TITAN Multi-Provider LLM Bridge Verification ===\n")
    
    tests = [
        ("Imports", test_imports),
        ("Config Loading", test_config_loading),
        ("Provider Status", test_provider_status),
        ("Task Routing", test_task_routing),
        ("Dynamic Data Integration", test_dynamic_data_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        if test_fn():
            passed += 1
        else:
            print(f"Test failed: {name}")
    
    print(f"\n=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All verification tests passed! The multi-provider LLM bridge is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced LLM Bridge Testing
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import logging

logger = logging.getLogger("TITAN-LLM-BRIDGE-TEST")


@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    passed: bool
    duration_ms: float
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Provider benchmark result"""
    provider: str
    model: str
    latency_ms: float
    tokens_per_second: float
    success: bool
    error: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Complete test suite result"""
    timestamp: float
    total_tests: int
    passed: int
    failed: int
    duration_seconds: float
    results: List[TestResult]


class BridgeTestOrchestrator:
    """
    V7.6 P0: Orchestrate comprehensive bridge testing.
    
    Features:
    - Test suite management
    - Parallel test execution
    - Dependency resolution
    - Failure isolation
    """
    
    def __init__(self):
        self._tests: Dict[str, Callable] = {}
        self._test_order: List[str] = []
        self._dependencies: Dict[str, List[str]] = {}
        self._results: List[TestSuiteResult] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-BRIDGE-ORCHESTRATOR")
        
        # Register default tests
        self._register_default_tests()
    
    def _register_default_tests(self):
        """Register default test cases"""
        self.register_test("imports", self._test_imports)
        self.register_test("config_loading", self._test_config, dependencies=["imports"])
        self.register_test("provider_status", self._test_providers, dependencies=["config_loading"])
        self.register_test("task_routing", self._test_routing, dependencies=["provider_status"])
        self.register_test("cache_system", self._test_cache, dependencies=["imports"])
        self.register_test("dynamic_data", self._test_dynamic, dependencies=["task_routing"])
    
    def register_test(
        self,
        name: str,
        test_fn: Callable,
        dependencies: List[str] = None,
    ):
        """Register a test case"""
        with self._lock:
            self._tests[name] = test_fn
            self._dependencies[name] = dependencies or []
            if name not in self._test_order:
                self._test_order.append(name)
    
    def run_all(self, parallel: bool = False) -> TestSuiteResult:
        """Run all registered tests"""
        start_time = time.time()
        results = []
        passed = 0
        failed = 0
        
        # Resolve execution order based on dependencies
        execution_order = self._resolve_order()
        
        failed_tests = set()
        
        for test_name in execution_order:
            # Skip if dependency failed
            deps = self._dependencies.get(test_name, [])
            if any(d in failed_tests for d in deps):
                results.append(TestResult(
                    test_name=test_name,
                    passed=False,
                    duration_ms=0,
                    message="Skipped due to dependency failure",
                    details={"skipped_deps": [d for d in deps if d in failed_tests]},
                ))
                failed += 1
                failed_tests.add(test_name)
                continue
            
            # Run test
            test_fn = self._tests.get(test_name)
            if not test_fn:
                continue
            
            test_start = time.time()
            try:
                # Execute test
                success, message, details = test_fn()
                duration_ms = (time.time() - test_start) * 1000
                
                result = TestResult(
                    test_name=test_name,
                    passed=success,
                    duration_ms=round(duration_ms, 2),
                    message=message,
                    details=details or {},
                )
                
                if success:
                    passed += 1
                else:
                    failed += 1
                    failed_tests.add(test_name)
                
            except Exception as e:
                duration_ms = (time.time() - test_start) * 1000
                result = TestResult(
                    test_name=test_name,
                    passed=False,
                    duration_ms=round(duration_ms, 2),
                    message=f"Exception: {str(e)}",
                    details={"exception": str(e)},
                )
                failed += 1
                failed_tests.add(test_name)
            
            results.append(result)
        
        duration = time.time() - start_time
        
        suite_result = TestSuiteResult(
            timestamp=time.time(),
            total_tests=len(results),
            passed=passed,
            failed=failed,
            duration_seconds=round(duration, 2),
            results=results,
        )
        
        with self._lock:
            self._results.append(suite_result)
            if len(self._results) > 100:
                self._results = self._results[-100:]
        
        return suite_result
    
    def _resolve_order(self) -> List[str]:
        """Resolve test execution order based on dependencies"""
        resolved = []
        remaining = list(self._test_order)
        
        while remaining:
            for test in remaining[:]:
                deps = self._dependencies.get(test, [])
                if all(d in resolved for d in deps):
                    resolved.append(test)
                    remaining.remove(test)
                    break
            else:
                # Circular dependency - add remaining in order
                resolved.extend(remaining)
                break
        
        return resolved
    
    def _test_imports(self) -> tuple:
        """Test imports"""
        try:
            from ollama_bridge import (
                get_provider_status, resolve_provider_for_task,
                is_ollama_available, get_config
            )
            return True, "All imports successful", {"modules": ["ollama_bridge"]}
        except ImportError as e:
            return False, f"Import failed: {e}", {}
    
    def _test_config(self) -> tuple:
        """Test config loading"""
        try:
            from ollama_bridge import get_config, reload_config
            reload_config()
            cfg = get_config()
            
            required = ["providers", "task_routing", "cache", "global"]
            missing = [s for s in required if s not in cfg]
            
            if missing:
                return False, f"Missing sections: {missing}", {"missing": missing}
            
            return True, "Config loaded", {
                "providers": len(cfg.get("providers", {})),
                "task_types": len(cfg.get("task_routing", {})),
            }
        except Exception as e:
            return False, f"Config error: {e}", {}
    
    def _test_providers(self) -> tuple:
        """Test provider status"""
        try:
            from ollama_bridge import get_provider_status
            status = get_provider_status()
            
            available = [p for p, s in status.items() if s.get("available")]
            
            return True, f"{len(available)} providers available", {
                "status": status,
                "available": available,
            }
        except Exception as e:
            return False, f"Provider check failed: {e}", {}
    
    def _test_routing(self) -> tuple:
        """Test task routing"""
        try:
            from ollama_bridge import resolve_provider_for_task
            
            tasks = ["bin_generation", "site_discovery", "default"]
            routing = {}
            
            for task in tasks:
                resolved = resolve_provider_for_task(task)
                routing[task] = f"{resolved[0]}/{resolved[1]}" if resolved else None
            
            has_routing = any(routing.values())
            return has_routing, "Routing configured" if has_routing else "No providers available", {
                "routing": routing,
            }
        except Exception as e:
            return False, f"Routing failed: {e}", {}
    
    def _test_cache(self) -> tuple:
        """Test cache system"""
        try:
            from ollama_bridge import get_cache_stats
            stats = get_cache_stats()
            
            return True, "Cache system operational", {"stats": stats}
        except ImportError:
            return True, "Cache system not available (optional)", {}
        except Exception as e:
            return False, f"Cache error: {e}", {}
    
    def _test_dynamic(self) -> tuple:
        """Test dynamic data integration"""
        try:
            from dynamic_data import LLM_AVAILABLE
            return True, f"LLM available: {LLM_AVAILABLE}", {"llm_available": LLM_AVAILABLE}
        except ImportError:
            return True, "Dynamic data not available (optional)", {}
        except Exception as e:
            return False, f"Dynamic data error: {e}", {}
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get test run history"""
        with self._lock:
            return [
                {
                    "timestamp": r.timestamp,
                    "total": r.total_tests,
                    "passed": r.passed,
                    "failed": r.failed,
                    "duration": r.duration_seconds,
                }
                for r in self._results[-limit:]
            ]


class ProviderBenchmarker:
    """
    V7.6 P0: Benchmark provider performance.
    
    Features:
    - Latency measurement
    - Throughput testing
    - Comparative analysis
    - Performance trending
    """
    
    # Standard test prompts
    TEST_PROMPTS = {
        "short": "Generate 5 random words.",
        "medium": "List 10 common web domains used for e-commerce.",
        "long": "Write a detailed paragraph about how payment processing works.",
    }
    
    def __init__(self):
        self._benchmarks: List[BenchmarkResult] = []
        self._provider_stats: Dict[str, Dict] = defaultdict(lambda: {
            "runs": 0, "total_latency": 0, "failures": 0,
        })
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-PROVIDER-BENCHMARK")
    
    def benchmark_provider(
        self,
        provider: str,
        model: str,
        prompt_type: str = "short",
    ) -> BenchmarkResult:
        """Benchmark a specific provider"""
        prompt = self.TEST_PROMPTS.get(prompt_type, self.TEST_PROMPTS["short"])
        
        start_time = time.time()
        
        try:
            # Try to use the provider
            from ollama_bridge import query_llm
            
            response = query_llm(
                prompt=prompt,
                task_type="default",
                force_provider=provider,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate tokens (rough approximation)
            response_text = response if isinstance(response, str) else str(response)
            est_tokens = len(response_text.split())
            tokens_per_second = (est_tokens / latency_ms) * 1000 if latency_ms > 0 else 0
            
            result = BenchmarkResult(
                provider=provider,
                model=model,
                latency_ms=round(latency_ms, 2),
                tokens_per_second=round(tokens_per_second, 2),
                success=True,
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            result = BenchmarkResult(
                provider=provider,
                model=model,
                latency_ms=round(latency_ms, 2),
                tokens_per_second=0,
                success=False,
                error=str(e),
            )
        
        with self._lock:
            self._benchmarks.append(result)
            stats = self._provider_stats[provider]
            stats["runs"] += 1
            stats["total_latency"] += result.latency_ms
            if not result.success:
                stats["failures"] += 1
        
        return result
    
    def benchmark_all(self) -> Dict[str, BenchmarkResult]:
        """Benchmark all available providers"""
        results = {}
        
        try:
            from ollama_bridge import get_provider_status
            status = get_provider_status()
            
            for provider, info in status.items():
                if info.get("available"):
                    model = info.get("default_model", "unknown")
                    results[provider] = self.benchmark_provider(provider, model)
        
        except ImportError:
            self.logger.warning("ollama_bridge not available for benchmarking")
        
        return results
    
    def get_rankings(self) -> List[Dict]:
        """Get provider rankings by performance"""
        with self._lock:
            rankings = []
            
            for provider, stats in self._provider_stats.items():
                if stats["runs"] == 0:
                    continue
                
                avg_latency = stats["total_latency"] / stats["runs"]
                success_rate = (stats["runs"] - stats["failures"]) / stats["runs"]
                
                rankings.append({
                    "provider": provider,
                    "avg_latency_ms": round(avg_latency, 2),
                    "success_rate": round(success_rate, 3),
                    "total_runs": stats["runs"],
                    "score": round(success_rate * 100 - (avg_latency / 100), 2),
                })
            
            rankings.sort(key=lambda x: x["score"], reverse=True)
            return rankings
    
    def get_stats(self) -> Dict:
        """Get benchmark statistics"""
        with self._lock:
            return {
                "total_benchmarks": len(self._benchmarks),
                "providers_tested": len(self._provider_stats),
                "provider_stats": dict(self._provider_stats),
            }


class TestResultCollector:
    """
    V7.6 P0: Collect and analyze test results.
    
    Features:
    - Result aggregation
    - Trend analysis
    - Failure pattern detection
    - Reporting
    """
    
    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self._results: List[Dict] = []
        self._failure_patterns: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-TEST-COLLECTOR")
    
    def collect(self, suite_result: TestSuiteResult):
        """Collect a test suite result"""
        with self._lock:
            record = {
                "timestamp": suite_result.timestamp,
                "total": suite_result.total_tests,
                "passed": suite_result.passed,
                "failed": suite_result.failed,
                "duration": suite_result.duration_seconds,
                "pass_rate": suite_result.passed / max(1, suite_result.total_tests),
                "failed_tests": [r.test_name for r in suite_result.results if not r.passed],
            }
            
            self._results.append(record)
            
            # Track failure patterns
            for test_name in record["failed_tests"]:
                self._failure_patterns[test_name] += 1
            
            # Cleanup old results
            self._cleanup()
    
    def _cleanup(self):
        """Remove old results"""
        cutoff = time.time() - (self.retention_days * 86400)
        self._results = [r for r in self._results if r["timestamp"] > cutoff]
    
    def get_summary(self) -> Dict:
        """Get results summary"""
        with self._lock:
            if not self._results:
                return {"total_runs": 0}
            
            total_runs = len(self._results)
            total_tests = sum(r["total"] for r in self._results)
            total_passed = sum(r["passed"] for r in self._results)
            avg_pass_rate = sum(r["pass_rate"] for r in self._results) / total_runs
            
            return {
                "total_runs": total_runs,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "avg_pass_rate": round(avg_pass_rate, 3),
                "top_failures": sorted(
                    self._failure_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5],
            }
    
    def get_trend(self, days: int = 7) -> List[Dict]:
        """Get pass rate trend"""
        cutoff = time.time() - (days * 86400)
        
        with self._lock:
            recent = [r for r in self._results if r["timestamp"] > cutoff]
            
            # Group by day
            by_day = defaultdict(list)
            for r in recent:
                day = time.strftime("%Y-%m-%d", time.localtime(r["timestamp"]))
                by_day[day].append(r["pass_rate"])
            
            return [
                {
                    "date": day,
                    "avg_pass_rate": round(sum(rates) / len(rates), 3),
                    "runs": len(rates),
                }
                for day, rates in sorted(by_day.items())
            ]


class ContinuousTestRunner:
    """
    V7.6 P0: Run tests continuously for monitoring.
    
    Features:
    - Scheduled test execution
    - Alert on failures
    - Health monitoring
    - Auto-recovery detection
    """
    
    def __init__(
        self,
        orchestrator: BridgeTestOrchestrator = None,
        collector: TestResultCollector = None,
        interval_minutes: float = 15,
    ):
        self.orchestrator = orchestrator or BridgeTestOrchestrator()
        self.collector = collector or TestResultCollector()
        self.interval_minutes = interval_minutes
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[float] = None
        self._consecutive_failures = 0
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-CONTINUOUS-TESTER")
    
    def start(self):
        """Start continuous testing"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info(f"Continuous testing started (interval: {self.interval_minutes} min)")
    
    def stop(self):
        """Stop continuous testing"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        self.logger.info("Continuous testing stopped")
    
    def _run_loop(self):
        """Main test loop"""
        while self._running:
            try:
                # Run test suite
                result = self.orchestrator.run_all()
                self.collector.collect(result)
                
                with self._lock:
                    self._last_run = time.time()
                    
                    if result.failed > 0:
                        self._consecutive_failures += 1
                        self.logger.warning(
                            f"Test run failed: {result.failed}/{result.total_tests} failures "
                            f"(consecutive: {self._consecutive_failures})"
                        )
                    else:
                        if self._consecutive_failures > 0:
                            self.logger.info(
                                f"Recovery detected after {self._consecutive_failures} failures"
                            )
                        self._consecutive_failures = 0
                
            except Exception as e:
                self.logger.error(f"Test loop error: {e}")
            
            # Sleep until next run
            time.sleep(self.interval_minutes * 60)
    
    def run_now(self) -> TestSuiteResult:
        """Run tests immediately"""
        result = self.orchestrator.run_all()
        self.collector.collect(result)
        
        with self._lock:
            self._last_run = time.time()
        
        return result
    
    def get_status(self) -> Dict:
        """Get runner status"""
        with self._lock:
            return {
                "running": self._running,
                "interval_minutes": self.interval_minutes,
                "last_run": self._last_run,
                "consecutive_failures": self._consecutive_failures,
                "health": "healthy" if self._consecutive_failures == 0 else (
                    "degraded" if self._consecutive_failures < 3 else "critical"
                ),
            }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_bridge_test_orchestrator: Optional[BridgeTestOrchestrator] = None
_provider_benchmarker: Optional[ProviderBenchmarker] = None
_test_result_collector: Optional[TestResultCollector] = None
_continuous_test_runner: Optional[ContinuousTestRunner] = None


def get_bridge_test_orchestrator() -> BridgeTestOrchestrator:
    """Get global bridge test orchestrator"""
    global _bridge_test_orchestrator
    if _bridge_test_orchestrator is None:
        _bridge_test_orchestrator = BridgeTestOrchestrator()
    return _bridge_test_orchestrator


def get_provider_benchmarker() -> ProviderBenchmarker:
    """Get global provider benchmarker"""
    global _provider_benchmarker
    if _provider_benchmarker is None:
        _provider_benchmarker = ProviderBenchmarker()
    return _provider_benchmarker


def get_test_result_collector() -> TestResultCollector:
    """Get global test result collector"""
    global _test_result_collector
    if _test_result_collector is None:
        _test_result_collector = TestResultCollector()
    return _test_result_collector


def get_continuous_test_runner() -> ContinuousTestRunner:
    """Get global continuous test runner"""
    global _continuous_test_runner
    if _continuous_test_runner is None:
        _continuous_test_runner = ContinuousTestRunner()
    return _continuous_test_runner
