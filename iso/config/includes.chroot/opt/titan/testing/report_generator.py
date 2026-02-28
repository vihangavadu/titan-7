#!/usr/bin/env python3
"""
TITAN V8.1 Report Generator

Generates comprehensive failure analysis reports with:
- Root cause identification
- Remediation recommendations
- Success rate projections
- Detailed signal breakdowns
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FailureCategory(Enum):
    """Categories of test failures"""
    FINGERPRINT = "fingerprint"
    BEHAVIORAL = "behavioral"
    NETWORK = "network"
    DEVICE = "device"
    VELOCITY = "velocity"
    PSP_DECLINE = "psp_decline"
    CARD_ISSUE = "card_issue"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class FailureAnalysis:
    """Detailed analysis of a test failure"""
    test_name: str
    category: FailureCategory
    root_cause: str
    severity: str
    impact: str
    signals: List[Dict[str, Any]]
    remediation_steps: List[str]
    affected_components: List[str]
    estimated_fix_time: str
    priority: int  # 1 = highest
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "category": self.category.value,
            "root_cause": self.root_cause,
            "severity": self.severity,
            "impact": self.impact,
            "signals": self.signals,
            "remediation_steps": self.remediation_steps,
            "affected_components": self.affected_components,
            "estimated_fix_time": self.estimated_fix_time,
            "priority": self.priority,
        }


@dataclass
class ComponentHealth:
    """Health status of a system component"""
    name: str
    status: str  # healthy, degraded, failing
    pass_rate: float
    failure_count: int
    common_issues: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "pass_rate": self.pass_rate,
            "failure_count": self.failure_count,
            "common_issues": self.common_issues,
        }


@dataclass
class TestReport:
    """Complete test report with analysis"""
    title: str
    generated_at: str
    summary: Dict[str, Any]
    success_rate: float
    projected_success_rate: float
    failure_analyses: List[FailureAnalysis]
    component_health: List[ComponentHealth]
    recommendations: List[str]
    detailed_results: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "success_rate": self.success_rate,
            "projected_success_rate": self.projected_success_rate,
            "failure_analyses": [fa.to_dict() for fa in self.failure_analyses],
            "component_health": [ch.to_dict() for ch in self.component_health],
            "recommendations": self.recommendations,
            "detailed_results": self.detailed_results,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = []
        
        # Header
        lines.append(f"# {self.title}")
        lines.append(f"\n**Generated:** {self.generated_at}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Tests | {self.summary.get('total_tests', 0)} |")
        lines.append(f"| Passed | {self.summary.get('passed', 0)} |")
        lines.append(f"| Failed | {self.summary.get('failed', 0)} |")
        lines.append(f"| Current Success Rate | {self.success_rate:.1f}% |")
        lines.append(f"| Projected Success Rate (after fixes) | {self.projected_success_rate:.1f}% |")
        lines.append("")
        
        # Component Health
        lines.append("## Component Health")
        lines.append("")
        lines.append("| Component | Status | Pass Rate | Issues |")
        lines.append("|-----------|--------|-----------|--------|")
        for ch in self.component_health:
            status_emoji = "✅" if ch.status == "healthy" else "⚠️" if ch.status == "degraded" else "❌"
            lines.append(f"| {ch.name} | {status_emoji} {ch.status} | {ch.pass_rate:.0f}% | {ch.failure_count} |")
        lines.append("")
        
        # Failure Analysis
        if self.failure_analyses:
            lines.append("## Failure Analysis")
            lines.append("")
            
            # Group by category
            by_category: Dict[str, List[FailureAnalysis]] = {}
            for fa in self.failure_analyses:
                cat = fa.category.value
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(fa)
            
            for category, analyses in sorted(by_category.items()):
                lines.append(f"### {category.upper()} Issues ({len(analyses)})")
                lines.append("")
                
                for fa in sorted(analyses, key=lambda x: x.priority):
                    priority_label = ["🔴 CRITICAL", "🟠 HIGH", "🟡 MEDIUM", "🟢 LOW"][min(fa.priority - 1, 3)]
                    lines.append(f"#### {fa.test_name}")
                    lines.append(f"**Priority:** {priority_label}")
                    lines.append(f"**Root Cause:** {fa.root_cause}")
                    lines.append(f"**Impact:** {fa.impact}")
                    lines.append("")
                    lines.append("**Remediation Steps:**")
                    for i, step in enumerate(fa.remediation_steps, 1):
                        lines.append(f"{i}. {step}")
                    lines.append("")
                    
                    if fa.signals:
                        lines.append("**Detected Signals:**")
                        for signal in fa.signals[:5]:
                            lines.append(f"- `{signal.get('name', 'unknown')}`: {signal.get('description', '')}")
                        lines.append("")
        
        # Top Recommendations
        lines.append("## Top Recommendations")
        lines.append("")
        for i, rec in enumerate(self.recommendations[:10], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("*Report generated by TITAN V8.1 Testing Environment*")
        
        return "\n".join(lines)
    
    def save(self, output_dir: Path, formats: List[str] = None):
        """Save report in multiple formats"""
        formats = formats or ["json", "md"]
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"titan_test_report_{timestamp}"
        
        saved_files = []
        
        if "json" in formats:
            json_path = output_dir / f"{base_name}.json"
            with open(json_path, "w") as f:
                f.write(self.to_json())
            saved_files.append(json_path)
        
        if "md" in formats:
            md_path = output_dir / f"{base_name}.md"
            with open(md_path, "w") as f:
                f.write(self.to_markdown())
            saved_files.append(md_path)
        
        if "html" in formats:
            html_path = output_dir / f"{base_name}.html"
            with open(html_path, "w") as f:
                f.write(self._to_html())
            saved_files.append(html_path)
        
        return saved_files
    
    def _to_html(self) -> str:
        """Generate HTML report"""
        md_content = self.to_markdown()
        
        # Simple markdown to HTML conversion
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }}
        h2 {{ color: #16213e; margin-top: 30px; }}
        h3 {{ color: #0f3460; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #16213e; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .summary-box {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .summary-box h2 {{ color: white; margin-top: 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; }}
        .metric-label {{ font-size: 0.9em; opacity: 0.8; }}
    </style>
</head>
<body>
    <h1>{self.title}</h1>
    <p><strong>Generated:</strong> {self.generated_at}</p>
    
    <div class="summary-box">
        <h2>Executive Summary</h2>
        <div class="metric">
            <div class="metric-value">{self.summary.get('total_tests', 0)}</div>
            <div class="metric-label">Total Tests</div>
        </div>
        <div class="metric">
            <div class="metric-value success">{self.summary.get('passed', 0)}</div>
            <div class="metric-label">Passed</div>
        </div>
        <div class="metric">
            <div class="metric-value danger">{self.summary.get('failed', 0)}</div>
            <div class="metric-label">Failed</div>
        </div>
        <div class="metric">
            <div class="metric-value">{self.success_rate:.1f}%</div>
            <div class="metric-label">Current Rate</div>
        </div>
        <div class="metric">
            <div class="metric-value success">{self.projected_success_rate:.1f}%</div>
            <div class="metric-label">Projected Rate</div>
        </div>
    </div>
    
    <h2>Component Health</h2>
    <table>
        <tr><th>Component</th><th>Status</th><th>Pass Rate</th><th>Issues</th></tr>
        {"".join(f'<tr><td>{ch.name}</td><td class="{self._status_class(ch.status)}">{ch.status}</td><td>{ch.pass_rate:.0f}%</td><td>{ch.failure_count}</td></tr>' for ch in self.component_health)}
    </table>
    
    <h2>Top Recommendations</h2>
    <ol>
        {"".join(f'<li>{rec}</li>' for rec in self.recommendations[:10])}
    </ol>
    
    <hr>
    <p><em>Report generated by TITAN V8.1 Testing Environment</em></p>
</body>
</html>"""
        return html
    
    def _status_class(self, status: str) -> str:
        if status == "healthy":
            return "success"
        elif status == "degraded":
            return "warning"
        return "danger"


class ReportGenerator:
    """
    Generates comprehensive test reports with failure analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Remediation database
        self.remediation_db = {
            "missing_canvas": [
                "Enable canvas fingerprint in FingerprintInjector",
                "Use Camoufox with canvas noise injection enabled",
                "Verify fingerprint_config.json exists in profile",
            ],
            "missing_webgl": [
                "Configure WebGL vendor/renderer in FingerprintInjector",
                "Use realistic GPU strings (NVIDIA, AMD, Intel)",
                "Avoid VM-like renderers (llvmpipe, SwiftShader)",
            ],
            "headless_browser": [
                "Use Camoufox instead of headless Chrome",
                "Remove HeadlessChrome from user agent",
                "Use titan-browser launcher for proper configuration",
            ],
            "webdriver_detected": [
                "Use Camoufox which removes WebDriver indicators",
                "Avoid Selenium/Puppeteer automation",
                "Use manual operation with Ghost Motor",
            ],
            "low_mouse_entropy": [
                "Enable Ghost Motor DMTG for mouse trajectories",
                "Increase mouse movement variability",
                "Add micro-tremors and natural curves",
            ],
            "fast_form_fill": [
                "Slow down form filling to 30-60 seconds",
                "Add natural pauses between fields",
                "Use human-like keystroke timing",
            ],
            "no_referrer": [
                "Use ReferrerWarmup to create navigation path",
                "Start from Google search, not direct URL",
                "Browse through site naturally before checkout",
            ],
            "datacenter_ip": [
                "Use residential proxy instead of datacenter",
                "Configure ResidentialProxyManager with geo targeting",
                "Verify proxy is not on blacklists",
            ],
            "country_mismatch": [
                "Use proxy in same country as billing address",
                "Configure Integration Bridge with billing alignment",
                "Verify timezone matches proxy location",
            ],
            "velocity_exceeded": [
                "Wait 1-24 hours before retrying",
                "Use different card/IP combination",
                "Reduce transaction frequency",
            ],
        }
    
    def generate_report(self, test_summary) -> TestReport:
        """Generate comprehensive report from test summary"""
        
        # Analyze failures
        failure_analyses = self._analyze_failures(test_summary.results)
        
        # Calculate component health
        component_health = self._calculate_component_health(test_summary.results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(failure_analyses, component_health)
        
        # Calculate projected success rate
        projected_rate = self._calculate_projected_rate(
            test_summary.success_rate,
            failure_analyses
        )
        
        return TestReport(
            title="TITAN V8.1 Test Environment Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary={
                "total_tests": test_summary.total_tests,
                "passed": test_summary.passed,
                "failed": test_summary.failed,
                "errors": test_summary.errors,
                "skipped": test_summary.skipped,
                "execution_time_ms": test_summary.total_time_ms,
            },
            success_rate=test_summary.success_rate,
            projected_success_rate=projected_rate,
            failure_analyses=failure_analyses,
            component_health=component_health,
            recommendations=recommendations,
            detailed_results=[r.to_dict() for r in test_summary.results],
        )
    
    def _analyze_failures(self, results: List) -> List[FailureAnalysis]:
        """Analyze each failure and determine root cause"""
        analyses = []
        
        for result in results:
            if result.status.value != "failed":
                continue
            
            # Determine category from signals
            category = self._categorize_failure(result)
            
            # Find root cause
            root_cause = self._identify_root_cause(result)
            
            # Get remediation steps
            remediation = self._get_remediation_steps(result)
            
            # Determine severity and priority
            severity, priority = self._assess_severity(result)
            
            analyses.append(FailureAnalysis(
                test_name=result.test_case.name,
                category=category,
                root_cause=root_cause,
                severity=severity,
                impact=self._assess_impact(category),
                signals=[s.to_dict() for s in result.risk_signals],
                remediation_steps=remediation,
                affected_components=self._get_affected_components(result),
                estimated_fix_time=self._estimate_fix_time(category),
                priority=priority,
            ))
        
        return sorted(analyses, key=lambda x: x.priority)
    
    def _categorize_failure(self, result) -> FailureCategory:
        """Categorize failure based on signals"""
        signal_names = [s.name for s in result.risk_signals]
        
        # Check for fingerprint issues
        fingerprint_signals = ["missing_canvas", "missing_webgl", "headless_browser", "webdriver_detected"]
        if any(s in signal_names for s in fingerprint_signals):
            return FailureCategory.FINGERPRINT
        
        # Check for behavioral issues
        behavioral_signals = ["low_mouse_entropy", "fast_form_fill", "no_referrer", "short_session"]
        if any(s in signal_names for s in behavioral_signals):
            return FailureCategory.BEHAVIORAL
        
        # Check for network issues
        network_signals = ["datacenter_ip", "vpn_ip", "country_mismatch", "low_ip_reputation"]
        if any(s in signal_names for s in network_signals):
            return FailureCategory.NETWORK
        
        # Check for velocity issues
        if any("velocity" in s for s in signal_names):
            return FailureCategory.VELOCITY
        
        # Check for PSP declines
        if result.psp_response and not result.psp_response.success:
            if result.psp_response.requires_3ds:
                return FailureCategory.AUTHENTICATION
            return FailureCategory.PSP_DECLINE
        
        return FailureCategory.UNKNOWN
    
    def _identify_root_cause(self, result) -> str:
        """Identify the primary root cause"""
        if not result.risk_signals:
            if result.psp_response:
                return result.psp_response.decline_message or "PSP declined transaction"
            return "Unknown failure - no signals detected"
        
        # Find highest severity signal
        critical_signals = [s for s in result.risk_signals if s.severity.value == "critical"]
        if critical_signals:
            return critical_signals[0].description
        
        high_signals = [s for s in result.risk_signals if s.severity.value == "high"]
        if high_signals:
            return high_signals[0].description
        
        return result.risk_signals[0].description
    
    def _get_remediation_steps(self, result) -> List[str]:
        """Get remediation steps for the failure"""
        steps = []
        
        for signal in result.risk_signals:
            # Check remediation database
            if signal.name in self.remediation_db:
                steps.extend(self.remediation_db[signal.name])
            elif signal.remediation:
                steps.append(signal.remediation)
        
        # Deduplicate while preserving order
        seen = set()
        unique_steps = []
        for step in steps:
            if step not in seen:
                seen.add(step)
                unique_steps.append(step)
        
        return unique_steps[:5]  # Top 5 steps
    
    def _assess_severity(self, result) -> tuple:
        """Assess severity and priority"""
        max_score = max((s.score for s in result.risk_signals), default=0)
        
        if max_score >= 40:
            return "critical", 1
        elif max_score >= 25:
            return "high", 2
        elif max_score >= 15:
            return "medium", 3
        return "low", 4
    
    def _assess_impact(self, category: FailureCategory) -> str:
        """Assess business impact of failure category"""
        impacts = {
            FailureCategory.FINGERPRINT: "High - Immediate bot detection and blocking",
            FailureCategory.BEHAVIORAL: "High - Triggers fraud review and manual verification",
            FailureCategory.NETWORK: "Critical - Instant decline from IP reputation",
            FailureCategory.VELOCITY: "Medium - Temporary blocking, recoverable with time",
            FailureCategory.PSP_DECLINE: "High - Transaction failure, potential account flag",
            FailureCategory.AUTHENTICATION: "Medium - Requires 3DS handling strategy",
            FailureCategory.DEVICE: "Medium - May trigger additional verification",
            FailureCategory.CARD_ISSUE: "Low - Card-specific, try different card",
            FailureCategory.CONFIGURATION: "Low - Fixable with proper setup",
            FailureCategory.UNKNOWN: "Unknown - Requires investigation",
        }
        return impacts.get(category, "Unknown impact")
    
    def _get_affected_components(self, result) -> List[str]:
        """Get list of affected system components"""
        components = set()
        
        for signal in result.risk_signals:
            category = signal.category
            if category == "fingerprint":
                components.add("FingerprintInjector")
                components.add("Camoufox")
            elif category == "behavioral":
                components.add("GhostMotor")
                components.add("ReferrerWarmup")
            elif category == "network":
                components.add("ProxyManager")
                components.add("NetworkShield")
            elif category == "device":
                components.add("HardwareShield")
            elif category == "velocity":
                components.add("VelocityTracker")
            elif category == "psp":
                components.add("CerberusValidator")
        
        return list(components)
    
    def _estimate_fix_time(self, category: FailureCategory) -> str:
        """Estimate time to fix the issue"""
        estimates = {
            FailureCategory.FINGERPRINT: "5-15 minutes",
            FailureCategory.BEHAVIORAL: "10-30 minutes",
            FailureCategory.NETWORK: "5-10 minutes",
            FailureCategory.VELOCITY: "1-24 hours (wait time)",
            FailureCategory.PSP_DECLINE: "Varies by issue",
            FailureCategory.AUTHENTICATION: "Requires 3DS access",
            FailureCategory.DEVICE: "10-20 minutes",
            FailureCategory.CARD_ISSUE: "Try different card",
            FailureCategory.CONFIGURATION: "5-10 minutes",
            FailureCategory.UNKNOWN: "Requires investigation",
        }
        return estimates.get(category, "Unknown")
    
    def _calculate_component_health(self, results: List) -> List[ComponentHealth]:
        """Calculate health status for each component"""
        components = {
            "Fingerprint": {"tests": 0, "passed": 0, "issues": []},
            "Behavioral": {"tests": 0, "passed": 0, "issues": []},
            "Network": {"tests": 0, "passed": 0, "issues": []},
            "Device": {"tests": 0, "passed": 0, "issues": []},
            "Velocity": {"tests": 0, "passed": 0, "issues": []},
            "PSP Integration": {"tests": 0, "passed": 0, "issues": []},
        }
        
        for result in results:
            # Categorize by test category
            category = result.test_case.category
            
            if category in ["fingerprint", "detection"]:
                components["Fingerprint"]["tests"] += 1
                if result.passed:
                    components["Fingerprint"]["passed"] += 1
                else:
                    for s in result.risk_signals:
                        if s.category == "fingerprint":
                            components["Fingerprint"]["issues"].append(s.name)
            
            if category in ["behavioral", "detection"]:
                components["Behavioral"]["tests"] += 1
                if result.passed:
                    components["Behavioral"]["passed"] += 1
                else:
                    for s in result.risk_signals:
                        if s.category == "behavioral":
                            components["Behavioral"]["issues"].append(s.name)
            
            if category in ["network"]:
                components["Network"]["tests"] += 1
                if result.passed:
                    components["Network"]["passed"] += 1
                else:
                    for s in result.risk_signals:
                        if s.category == "network":
                            components["Network"]["issues"].append(s.name)
            
            if category in ["psp"]:
                components["PSP Integration"]["tests"] += 1
                if result.passed:
                    components["PSP Integration"]["passed"] += 1
        
        health_list = []
        for name, data in components.items():
            if data["tests"] == 0:
                continue
            
            pass_rate = (data["passed"] / data["tests"]) * 100
            failure_count = data["tests"] - data["passed"]
            
            if pass_rate >= 90:
                status = "healthy"
            elif pass_rate >= 70:
                status = "degraded"
            else:
                status = "failing"
            
            # Get unique issues
            unique_issues = list(set(data["issues"]))[:5]
            
            health_list.append(ComponentHealth(
                name=name,
                status=status,
                pass_rate=pass_rate,
                failure_count=failure_count,
                common_issues=unique_issues,
            ))
        
        return health_list
    
    def _generate_recommendations(
        self,
        analyses: List[FailureAnalysis],
        health: List[ComponentHealth]
    ) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Priority 1: Critical failures
        critical = [a for a in analyses if a.priority == 1]
        if critical:
            recommendations.append(
                f"🔴 CRITICAL: Fix {len(critical)} critical issues immediately - "
                f"{', '.join(set(a.category.value for a in critical))}"
            )
        
        # Priority 2: Failing components
        failing = [h for h in health if h.status == "failing"]
        for component in failing:
            recommendations.append(
                f"❌ {component.name} is failing ({component.pass_rate:.0f}% pass rate) - "
                f"Address: {', '.join(component.common_issues[:3])}"
            )
        
        # Priority 3: Common issues
        all_issues = []
        for a in analyses:
            all_issues.extend([s.get("name", "") for s in a.signals])
        
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for issue, count in top_issues:
            if issue and count > 1:
                recommendations.append(
                    f"⚠️ '{issue}' appeared {count} times - prioritize fixing this"
                )
        
        # Priority 4: Component-specific recommendations
        for component in health:
            if component.status == "degraded":
                recommendations.append(
                    f"🟡 {component.name} is degraded - review configuration"
                )
        
        # Priority 5: General best practices
        recommendations.extend([
            "✅ Run pre-flight checks before every operation",
            "✅ Use Integration Bridge for unified configuration",
            "✅ Follow timing guidelines in Operator Guide",
        ])
        
        return recommendations[:15]
    
    def _calculate_projected_rate(
        self,
        current_rate: float,
        analyses: List[FailureAnalysis]
    ) -> float:
        """Calculate projected success rate after fixes"""
        if not analyses:
            return current_rate
        
        # Estimate improvement per fix
        improvements = {
            FailureCategory.FINGERPRINT: 15,
            FailureCategory.BEHAVIORAL: 12,
            FailureCategory.NETWORK: 18,
            FailureCategory.DEVICE: 8,
            FailureCategory.VELOCITY: 5,
            FailureCategory.PSP_DECLINE: 10,
            FailureCategory.AUTHENTICATION: 8,
            FailureCategory.CONFIGURATION: 5,
        }
        
        # Calculate potential improvement
        categories_found = set(a.category for a in analyses)
        total_improvement = sum(
            improvements.get(cat, 5) for cat in categories_found
        )
        
        # Cap at 95%
        projected = min(95, current_rate + total_improvement)
        
        return projected


def generate_report(test_summary, output_dir: Optional[Path] = None) -> TestReport:
    """Convenience function to generate and optionally save a report"""
    generator = ReportGenerator()
    report = generator.generate_report(test_summary)
    
    if output_dir:
        report.save(output_dir, formats=["json", "md", "html"])
    
    return report


if __name__ == "__main__":
    # Demo with mock data
    from dataclasses import dataclass
    
    @dataclass
    class MockSummary:
        total_tests: int = 10
        passed: int = 6
        failed: int = 3
        errors: int = 1
        skipped: int = 0
        success_rate: float = 60.0
        total_time_ms: float = 1500.0
        results: list = None
    
    summary = MockSummary(results=[])
    generator = ReportGenerator()
    report = generator.generate_report(summary)
    
    print(report.to_markdown())
