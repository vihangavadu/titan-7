"""
TITAN V8.1 SINGULARITY — Forensic Detection Monitor
Real-time OS analysis using LLM to detect forensic artifacts, missing components, and detectable traces.
"""

import os
import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import hashlib

logger = logging.getLogger("TITAN-FORENSIC-MONITOR")

# Import LLM bridge for intelligent analysis
try:
    from ollama_bridge import query_llm_json, resolve_provider_for_task, is_ollama_available
    LLM_AVAILABLE = is_ollama_available()
except ImportError:
    LLM_AVAILABLE = False
    def query_llm_json(*args, **kwargs):
        return None

class ForensicMonitor:
    """Real-time forensic detection and analysis system."""
    
    def __init__(self):
        self.last_scan = None
        self.scan_interval = 300  # 5 minutes between scans
        self.cache_dir = Path("/opt/titan/data/forensic_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def scan_system_state(self) -> Dict[str, Any]:
        """Collect comprehensive system state for forensic analysis."""
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": self._get_hostname(),
            "kernel": self._get_kernel_info(),
            "processes": self._get_process_list(),
            "network": self._get_network_state(),
            "filesystem": self._scan_filesystem_artifacts(),
            "logs": self._scan_log_artifacts(),
            "memory": self._get_memory_state(),
            "services": self._get_service_state(),
            "hardware": self._get_hardware_info(),
            "temp_files": self._scan_temp_files(),
            "browser_artifacts": self._scan_browser_artifacts(),
            "titan_modules": self._scan_titan_modules(),
        }
        return state
    
    def _get_hostname(self) -> str:
        """Get system hostname."""
        try:
            return subprocess.check_output(["hostname"], text=True, timeout=5).strip()
        except Exception:
            return "unknown"
    
    def _get_kernel_info(self) -> Dict[str, str]:
        """Get kernel and system info."""
        info = {}
        try:
            # Kernel version
            info["kernel"] = subprocess.check_output(["uname", "-r"], text=True, timeout=5).strip()
            info["system"] = subprocess.check_output(["uname", "-s"], text=True, timeout=5).strip()
            info["arch"] = subprocess.check_output(["uname", "-m"], text=True, timeout=5).strip()
            
            # DMI info (hardware identifiers)
            if Path("/sys/class/dmi/id/product_name").exists():
                info["product_name"] = Path("/sys/class/dmi/id/product_name").read_text().strip()
            if Path("/sys/class/dmi/id/sys_vendor").exists():
                info["sys_vendor"] = Path("/sys/class/dmi/id/sys_vendor").read_text().strip()
        except Exception as e:
            logger.debug(f"Failed to get kernel info: {e}")
        return info
    
    def _get_process_list(self) -> List[Dict[str, str]]:
        """Get running processes with forensic relevance."""
        processes = []
        try:
            # Get process list with ps
            output = subprocess.check_output([
                "ps", "aux", "--sort=-%cpu", "--no-headers"
            ], text=True, timeout=10)
            
            for line in output.strip().split('\n')[:50]:  # Top 50 processes
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    processes.append({
                        "user": parts[0],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "pid": parts[1],
                        "command": parts[10][:200]  # Truncate long commands
                    })
        except Exception as e:
            logger.debug(f"Failed to get process list: {e}")
        return processes
    
    def _get_network_state(self) -> Dict[str, Any]:
        """Get network state and connections."""
        network = {"interfaces": [], "connections": [], "routes": []}
        
        try:
            # Network interfaces
            if Path("/proc/net/dev").exists():
                for line in Path("/proc/net/dev").read_text().split('\n')[2:]:
                    if ':' in line:
                        iface = line.split(':')[0].strip()
                        if iface not in ['lo']:
                            network["interfaces"].append(iface)
            
            # Active connections
            try:
                output = subprocess.check_output([
                    "netstat", "-tn", "--established"
                ], text=True, stderr=subprocess.DEVNULL, timeout=10)
                for line in output.strip().split('\n')[2:]:
                    if line.strip():
                        network["connections"].append(line.split()[:5])
            except Exception:
                pass
            
            # Routing table
            try:
                output = subprocess.check_output(["ip", "route"], text=True, timeout=5)
                network["routes"] = output.strip().split('\n')[:10]
            except Exception:
                pass
                
        except Exception as e:
            logger.debug(f"Failed to get network state: {e}")
        return network
    
    def _scan_filesystem_artifacts(self) -> Dict[str, Any]:
        """Scan filesystem for suspicious artifacts."""
        artifacts = {
            "suspicious_files": [],
            "titan_files": [],
            "large_files": [],
            "recent_files": []
        }
        
        try:
            # Scan common locations for forensic artifacts
            suspicious_paths = [
                "/tmp", "/var/tmp", "/dev/shm", "/var/crash",
                "/var/log", "/root/.bash_history", "/home/*/.bash_history"
            ]
            
            for path_pattern in suspicious_paths:
                try:
                    if '*' in path_pattern:
                        # Handle glob patterns
                        from glob import glob
                        for path in glob(path_pattern):
                            if Path(path).exists():
                                self._scan_directory(path, artifacts)
                    else:
                        if Path(path).exists():
                            self._scan_directory(path, artifacts)
                except Exception:
                    pass
            
            # Check for Titan-specific files
            titan_paths = [
                "/opt/titan", "/etc/titan", "/var/lib/titan", "/tmp/titan"
            ]
            for path in titan_paths:
                if Path(path).exists():
                    self._scan_titan_directory(path, artifacts)
                    
        except Exception as e:
            logger.debug(f"Filesystem scan failed: {e}")
        
        return artifacts
    
    def _scan_directory(self, path: str, artifacts: Dict[str, Any]):
        """Scan a directory for artifacts."""
        try:
            path_obj = Path(path)
            if not path_obj.is_dir():
                return
                
            # Scan recent files (last 24 hours)
            cutoff = time.time() - 86400  # 24 hours ago
            for item in path_obj.iterdir():
                try:
                    stat = item.stat()
                    if stat.st_mtime > cutoff:
                        artifacts["recent_files"].append({
                            "path": str(item),
                            "size": stat.st_size,
                            "mtime": stat.st_mtime
                        })
                    
                    # Check for suspicious file names
                    suspicious_names = [
                        "core", "dump", "crash", "panic", "oops",
                        "forensics", "evidence", "capture", "trace"
                    ]
                    if any(name in item.name.lower() for name in suspicious_names):
                        artifacts["suspicious_files"].append(str(item))
                        
                    # Large files (>100MB)
                    if stat.st_size > 100 * 1024 * 1024:
                        artifacts["large_files"].append({
                            "path": str(item),
                            "size_mb": stat.st_size // (1024 * 1024)
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Failed to scan directory {path}: {e}")
    
    def _scan_titan_directory(self, path: str, artifacts: Dict[str, Any]):
        """Scan Titan-specific directories."""
        try:
            path_obj = Path(path)
            for item in path_obj.rglob("*"):
                if item.is_file():
                    artifacts["titan_files"].append({
                        "path": str(item),
                        "size": item.stat().st_size,
                        "hash": self._quick_hash(item)
                    })
        except Exception as e:
            logger.debug(f"Failed to scan Titan directory {path}: {e}")
    
    def _quick_hash(self, file_path: Path) -> str:
        """Generate quick hash of file for change detection."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read(1024)).hexdigest()[:16]
        except:
            return "unknown"
    
    def _scan_log_artifacts(self) -> Dict[str, List[str]]:
        """Scan system logs for suspicious entries."""
        logs = {"auth": [], "syslog": [], "kernel": [], "titan": []}
        
        log_files = {
            "/var/log/auth.log": "auth",
            "/var/log/secure": "auth", 
            "/var/log/syslog": "syslog",
            "/var/log/messages": "syslog",
            "/var/log/kern.log": "kernel",
            "/var/log/dmesg": "kernel"
        }
        
        for log_file, log_type in log_files.items():
            try:
                if Path(log_file).exists():
                    # Get last 50 lines
                    output = subprocess.check_output([
                        "tail", "-50", log_file
                    ], text=True, stderr=subprocess.DEVNULL, timeout=10)
                    
                    # Filter for suspicious keywords
                    suspicious_keywords = [
                        "failed", "denied", "error", "intrusion", "attack",
                        "breach", "unauthorized", "suspicious", "malware"
                    ]
                    
                    for line in output.strip().split('\n'):
                        if any(keyword in line.lower() for keyword in suspicious_keywords):
                            logs[log_type].append(line.strip())
            except Exception:
                pass
        
        return logs
    
    def _get_memory_state(self) -> Dict[str, Any]:
        """Get memory usage and swap information."""
        memory = {}
        try:
            if Path("/proc/meminfo").exists():
                meminfo = Path("/proc/meminfo").read_text()
                for line in meminfo.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().split()[0]
                        memory[key] = value
        except Exception as e:
            logger.debug(f"Failed to get memory state: {e}")
        return memory
    
    def _get_service_state(self) -> Dict[str, str]:
        """Get system service states."""
        services = {}
        
        critical_services = [
            "ssh", "sshd", "network", "firewall", "ufw", "iptables",
            "xrdp", "vnc", "titan", "cockpit", "docker"
        ]
        
        for service in critical_services:
            try:
                # Try systemctl first
                result = subprocess.run([
                    "systemctl", "is-active", service
                ], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    services[service] = result.stdout.strip()
                else:
                    services[service] = "inactive"
            except Exception:
                # Fallback to service command
                try:
                    result = subprocess.run([
                        "service", service, "status"
                    ], capture_output=True, text=True, timeout=5)
                    if "running" in result.stdout.lower():
                        services[service] = "active"
                    else:
                        services[service] = "inactive"
                except Exception:
                    services[service] = "unknown"
        
        return services
    
    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information for forensic analysis."""
        hardware = {}
        
        try:
            # CPU info
            if Path("/proc/cpuinfo").exists():
                cpuinfo = Path("/proc/cpuinfo").read_text()
                hardware["cpu_model"] = "unknown"
                for line in cpuinfo.split('\n'):
                    if line.startswith("model name"):
                        hardware["cpu_model"] = line.split(':', 1)[1].strip()
                        break
            
            # Disk info
            try:
                output = subprocess.check_output([
                    "df", "-h", "--output=source,size,used,target"
                ], text=True, timeout=10)
                hardware["disks"] = output.strip().split('\n')[1:]  # Skip header
            except Exception:
                pass
            
            # USB devices
            try:
                output = subprocess.check_output([
                    "lsusb"
                ], text=True, stderr=subprocess.DEVNULL, timeout=10)
                hardware["usb_devices"] = output.strip().split('\n')
            except Exception:
                hardware["usb_devices"] = []
                
        except Exception as e:
            logger.debug(f"Failed to get hardware info: {e}")
        
        return hardware
    
    def _scan_temp_files(self) -> List[Dict[str, str]]:
        """Scan temporary files and directories."""
        temp_files = []
        
        temp_dirs = ["/tmp", "/var/tmp", "/dev/shm"]
        for temp_dir in temp_dirs:
            try:
                if Path(temp_dir).exists():
                    for item in Path(temp_dir).iterdir():
                        if item.is_file():
                            temp_files.append({
                                "path": str(item),
                                "size": item.stat().st_size,
                                "mtime": item.stat().st_mtime
                            })
            except Exception:
                pass
        
        return temp_files[:100]  # Limit to 100 most recent
    
    def _scan_browser_artifacts(self) -> Dict[str, List[str]]:
        """Scan for browser artifacts and profiles."""
        artifacts = {"profiles": [], "cookies": [], "history": [], "cache": []}
        
        # Common browser locations
        browser_paths = [
            "/root/.mozilla", "/home/*/.mozilla",
            "/root/.config/google-chrome", "/home/*/.config/google-chrome",
            "/root/.config/firefox", "/home/*/.config/firefox"
        ]
        
        for path_pattern in browser_paths:
            try:
                from glob import glob
                for path in glob(path_pattern):
                    if Path(path).exists():
                        self._scan_browser_directory(path, artifacts)
            except Exception:
                pass
        
        return artifacts
    
    def _scan_browser_directory(self, path: str, artifacts: Dict[str, Any]):
        """Scan a browser directory for artifacts."""
        try:
            path_obj = Path(path)
            for item in path_obj.rglob("*"):
                if item.is_file():
                    name = item.name.lower()
                    if "profile" in name:
                        artifacts["profiles"].append(str(item))
                    elif "cookie" in name:
                        artifacts["cookies"].append(str(item))
                    elif "history" in name or "places" in name:
                        artifacts["history"].append(str(item))
                    elif "cache" in name:
                        artifacts["cache"].append(str(item))
        except Exception:
            pass
    
    def _scan_titan_modules(self) -> Dict[str, Any]:
        """Scan Titan-specific modules and their status."""
        titan_info = {
            "modules": [],
            "configs": [],
            "logs": [],
            "processes": []
        }
        
        try:
            # Check for Titan kernel modules
            if Path("/proc/modules").exists():
                modules = Path("/proc/modules").read_text()
                for line in modules.split('\n'):
                    if "titan" in line.lower():
                        titan_info["modules"].append(line.split()[0])
            
            # Titan config files
            titan_configs = [
                "/etc/titan", "/opt/titan/config", "/opt/titan/etc"
            ]
            for config_dir in titan_configs:
                if Path(config_dir).exists():
                    for item in Path(config_dir).rglob("*"):
                        if item.is_file():
                            titan_info["configs"].append(str(item))
            
            # Titan processes
            for proc_info in self._get_process_list():
                if "titan" in proc_info["command"].lower():
                    titan_info["processes"].append(proc_info)
                    
        except Exception as e:
            logger.debug(f"Failed to scan Titan modules: {e}")
        
        return titan_info
    
    def analyze_with_llm(self, system_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze system state for forensic issues."""
        if not LLM_AVAILABLE:
            return self._fallback_analysis(system_state)
        
        prompt = self._build_analysis_prompt(system_state)
        
        try:
            analysis = query_llm_json(
                prompt=prompt,
                task_type="preset_generation",  # Use detailed analysis model
                temperature=0.2,
                max_tokens=4096,
                timeout=120
            )
            
            if analysis:
                return analysis
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
        
        return self._fallback_analysis(system_state)
    
    def _build_analysis_prompt(self, system_state: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt for LLM."""
        # Create summary of system state
        summary = {
            "hostname": system_state.get("hostname"),
            "kernel": system_state.get("kernel", {}),
            "process_count": len(system_state.get("processes", [])),
            "network_interfaces": len(system_state.get("network", {}).get("interfaces", [])),
            "suspicious_files": len(system_state.get("filesystem", {}).get("suspicious_files", [])),
            "titan_files": len(system_state.get("filesystem", {}).get("titan_files", [])),
            "recent_files": len(system_state.get("filesystem", {}).get("recent_files", [])),
            "log_entries": {k: len(v) for k, v in system_state.get("logs", {}).items()},
            "services": system_state.get("services", {}),
            "titan_modules": system_state.get("titan_modules", {}),
        }
        
        prompt = f"""You are a digital forensics expert analyzing a TITAN OS system for security issues and detectable artifacts.

SYSTEM SUMMARY:
{json.dumps(summary, indent=2)}

TASK: Analyze this system state and provide a security assessment. Focus on:
1. Missing security components or misconfigurations
2. Detectable forensic artifacts that could reveal system usage
3. Suspicious processes or network activity
4. Titan-specific security issues
5. Recommendations for hardening

Return a JSON object with this exact structure:
{{
  "risk_level": "low|medium|high|critical",
  "issues": [
    {{
      "category": "forensics|security|titan|network|system",
      "severity": "info|warning|danger|critical",
      "title": "Brief issue title",
      "description": "Detailed description of the issue",
      "evidence": "Specific evidence from the system state",
      "recommendation": "How to fix or mitigate"
    }}
  ],
  "missing_components": [
    {{
      "component": "Component name",
      "importance": "critical|important|optional",
      "impact": "What happens without this component"
    }}
  ],
  "detectable_artifacts": [
    {{
      "type": "logs|cache|temp|history|metadata",
      "artifact": "Description of artifact",
      "risk": "low|medium|high",
      "cleanup": "How to remove or obscure"
    }}
  ],
  "recommendations": [
    "Actionable recommendation 1",
    "Actionable recommendation 2"
  ],
  "summary": "Overall security assessment summary"
}}

Be thorough but focus on actionable findings. If everything looks good, say so in the summary."""
        
        return prompt
    
    def _fallback_analysis(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis without LLM."""
        issues = []
        missing_components = []
        detectable_artifacts = []
        
        # Basic rule-based analysis
        services = system_state.get("services", {})
        
        # Check for missing security services
        if services.get("firewall") != "active":
            issues.append({
                "category": "security",
                "severity": "warning",
                "title": "Firewall not active",
                "description": "No firewall service is running",
                "evidence": f"Firewall status: {services.get('firewall', 'unknown')}",
                "recommendation": "Enable and configure firewall (ufw/iptables)"
            })
        
        # Check for suspicious files
        suspicious_count = len(system_state.get("filesystem", {}).get("suspicious_files", []))
        if suspicious_count > 0:
            issues.append({
                "category": "forensics",
                "severity": "warning",
                "title": f"Suspicious files detected",
                "description": f"Found {suspicious_count} files with suspicious names",
                "evidence": "Files with names containing 'core', 'dump', 'crash', etc.",
                "recommendation": "Review and clean suspicious files"
            })
        
        # Check for Titan modules
        titan_modules = system_state.get("titan_modules", {}).get("modules", [])
        if not titan_modules:
            missing_components.append({
                "component": "Titan kernel modules",
                "importance": "critical",
                "impact": "Missing stealth and anti-forensics capabilities"
            })
        
        return {
            "risk_level": "medium" if issues else "low",
            "issues": issues,
            "missing_components": missing_components,
            "detectable_artifacts": detectable_artifacts,
            "recommendations": ["Enable firewall", "Review suspicious files"],
            "summary": "Basic analysis completed. Enable LLM for detailed assessment."
        }
    
    def get_monitoring_instructions(self) -> str:
        """Get real-time monitoring instructions for display."""
        instructions = """
🔍 TITAN FORENSIC MONITOR — 24/7 SYSTEM ANALYSIS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REAL-TIME THREAT DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ CONTINUOUS MONITORING:
• Process analysis — Detect suspicious or unexpected processes
• Network monitoring — Track connections and data exfiltration attempts  
• File system surveillance — Identify new artifacts and suspicious files
• Log analysis — Detect intrusion attempts and security events
• Service integrity — Monitor critical security services
• Titan module status — Ensure stealth components are active

🎯 AUTOMATIC THREAT CLASSIFICATION:
• CRITICAL — Active attacks, rootkits, data exfiltration
• HIGH — Suspicious processes, unauthorized access attempts
• MEDIUM — Missing security components, detectable artifacts
• LOW — Configuration issues, non-critical warnings

🛡️ FORENSIC COUNTERMEASURES:
• Artifact cleanup — Automatically remove detectable traces
• Log sanitization — Obscure system activity logs
• Process hiding — Conceal sensitive operations
• Network cloaking — Mask communication patterns
• Metadata scrubbing — Remove file timestamps and attributes

📊 DASHBOARD ALERTS:
• Red — Immediate action required (critical threats)
• Yellow — Investigation recommended (suspicious activity)  
• Blue — Informational (system status updates)
• Green — All systems operational

⚙️ CONFIGURATION:
• Scan interval: Every 5 minutes
• LLM analysis: Intelligent threat assessment
• Cache retention: 24 hours of historical data
• Alert threshold: Medium severity and above

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATUS: ACTIVE MONITORING
LAST SCAN: Running comprehensive system analysis...
THREAT LEVEL: Assessing current security posture...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return instructions


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 THREAT CORRELATION ENGINE — Correlate threats across multiple sources
# ═══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Set, Tuple
import threading


@dataclass
class CorrelatedThreat:
    """A correlated threat combining multiple indicators."""
    threat_id: str
    severity: str  # "critical", "high", "medium", "low"
    indicators: List[Dict[str, Any]]
    sources: List[str]
    first_seen: float
    last_seen: float
    correlation_score: float  # 0.0-1.0
    recommended_actions: List[str]


class ThreatCorrelationEngine:
    """
    V7.6 Threat Correlation Engine - Correlates threats across
    multiple sources to identify complex attack patterns.
    """
    
    # Correlation rules (indicator combinations that indicate higher severity)
    CORRELATION_RULES = {
        "active_intrusion": {
            "indicators": ["failed_login", "port_scan", "process_injection"],
            "min_matches": 2,
            "severity_boost": "critical",
            "actions": ["Enable lockdown mode", "Block source IPs", "Alert operator"]
        },
        "data_exfiltration": {
            "indicators": ["suspicious_outbound", "large_file_access", "encryption_activity"],
            "min_matches": 2,
            "severity_boost": "critical",
            "actions": ["Kill suspicious processes", "Block network", "Forensic capture"]
        },
        "persistence_attempt": {
            "indicators": ["cron_modification", "systemd_modification", "init_modification"],
            "min_matches": 1,
            "severity_boost": "high",
            "actions": ["Review scheduled tasks", "Check service files", "Audit startup"]
        },
        "forensic_analysis": {
            "indicators": ["forensic_tool_detected", "log_collection", "memory_dump"],
            "min_matches": 1,
            "severity_boost": "critical",
            "actions": ["Activate kill switch", "Wipe artifacts", "Self-destruct option"]
        },
    }
    
    # Indicator extraction patterns
    INDICATOR_PATTERNS = {
        "failed_login": ["authentication failure", "failed password", "invalid user"],
        "port_scan": ["connection refused", "syn flood", "nmap", "masscan"],
        "process_injection": ["ptrace", "ld_preload", "debugger attached"],
        "suspicious_outbound": ["unusual_port", "high_bandwidth", "encrypted_tunnel"],
        "forensic_tool_detected": ["volatility", "sleuthkit", "autopsy", "foremost"],
        "cron_modification": ["/etc/crontab", "/var/spool/cron"],
        "systemd_modification": ["/etc/systemd", ".service"],
        "log_collection": ["rsyslog", "syslog-ng", "journald export"],
    }
    
    def __init__(self):
        self._active_threats: Dict[str, CorrelatedThreat] = {}
        self._indicator_history: List[Tuple[float, str, Dict]] = []  # (timestamp, indicator_type, data)
        self._correlation_lock = threading.Lock()
        self._threat_counter = 0
        
    def add_indicator(self, indicator_type: str, data: Dict[str, Any], source: str = "unknown"):
        """
        Add a threat indicator for correlation.
        
        Args:
            indicator_type: Type of indicator (e.g., "failed_login")
            data: Associated data
            source: Source of the indicator
        """
        now = time.time()
        
        with self._correlation_lock:
            self._indicator_history.append((now, indicator_type, data, source))
            
            # Prune old indicators (keep last 30 minutes)
            cutoff = now - 1800
            self._indicator_history = [
                (t, i, d, s) for t, i, d, s in self._indicator_history if t > cutoff
            ]
            
            # Run correlation
            self._correlate_indicators()
    
    def _correlate_indicators(self):
        """Run correlation rules against current indicators."""
        now = time.time()
        recent_indicators = defaultdict(list)
        
        # Group recent indicators by type
        for timestamp, indicator_type, data, source in self._indicator_history:
            recent_indicators[indicator_type].append({
                "timestamp": timestamp,
                "data": data,
                "source": source
            })
        
        # Check each correlation rule
        for rule_name, rule in self.CORRELATION_RULES.items():
            matches = []
            sources = set()
            
            for required_indicator in rule["indicators"]:
                if required_indicator in recent_indicators:
                    matches.extend(recent_indicators[required_indicator])
                    for m in recent_indicators[required_indicator]:
                        sources.add(m["source"])
            
            if len(matches) >= rule["min_matches"]:
                # Create or update correlated threat
                threat_key = f"correlated_{rule_name}"
                
                if threat_key not in self._active_threats:
                    self._threat_counter += 1
                    threat = CorrelatedThreat(
                        threat_id=f"THREAT-{self._threat_counter:04d}",
                        severity=rule["severity_boost"],
                        indicators=matches,
                        sources=list(sources),
                        first_seen=min(m["timestamp"] for m in matches),
                        last_seen=max(m["timestamp"] for m in matches),
                        correlation_score=min(1.0, len(matches) / (rule["min_matches"] * 2)),
                        recommended_actions=rule["actions"]
                    )
                    self._active_threats[threat_key] = threat
                    logger.warning(f"[V7.6] Correlated threat detected: {threat.threat_id} - {rule_name}")
                else:
                    # Update existing threat
                    threat = self._active_threats[threat_key]
                    threat.indicators = matches
                    threat.sources = list(sources)
                    threat.last_seen = now
                    threat.correlation_score = min(1.0, len(matches) / (rule["min_matches"] * 2))
    
    def extract_indicators_from_state(self, system_state: Dict[str, Any]) -> List[Tuple[str, Dict]]:
        """Extract threat indicators from system state."""
        indicators = []
        
        # Extract from logs
        logs = system_state.get("logs", {})
        for log_type, entries in logs.items():
            for entry in entries:
                for indicator_type, patterns in self.INDICATOR_PATTERNS.items():
                    if any(pattern.lower() in entry.lower() for pattern in patterns):
                        indicators.append((indicator_type, {"log_type": log_type, "entry": entry[:200]}))
        
        # Extract from processes
        for proc in system_state.get("processes", []):
            command = proc.get("command", "").lower()
            for indicator_type, patterns in self.INDICATOR_PATTERNS.items():
                if any(pattern.lower() in command for pattern in patterns):
                    indicators.append((indicator_type, {"process": proc}))
        
        return indicators
    
    def get_active_threats(self) -> List[CorrelatedThreat]:
        """Get all active correlated threats."""
        with self._correlation_lock:
            return list(self._active_threats.values())
    
    def get_threat_summary(self) -> Dict[str, Any]:
        """Get summary of current threat status."""
        threats = self.get_active_threats()
        
        severity_counts = defaultdict(int)
        for t in threats:
            severity_counts[t.severity] += 1
        
        overall_level = "low"
        if severity_counts["critical"] > 0:
            overall_level = "critical"
        elif severity_counts["high"] > 0:
            overall_level = "high"
        elif severity_counts["medium"] > 0:
            overall_level = "medium"
        
        return {
            "overall_level": overall_level,
            "active_threats": len(threats),
            "by_severity": dict(severity_counts),
            "threats": [
                {
                    "id": t.threat_id,
                    "severity": t.severity,
                    "score": t.correlation_score,
                    "actions": t.recommended_actions
                }
                for t in threats
            ]
        }
    
    def clear_threat(self, threat_id: str):
        """Clear a threat after it has been addressed."""
        with self._correlation_lock:
            for key, threat in list(self._active_threats.items()):
                if threat.threat_id == threat_id:
                    del self._active_threats[key]
                    logger.info(f"[V7.6] Threat cleared: {threat_id}")
                    break


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 ARTIFACT CLEANUP MANAGER — Automated cleanup of forensic artifacts
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CleanupResult:
    """Result of artifact cleanup operation."""
    success: bool
    files_removed: int
    logs_sanitized: int
    caches_cleared: int
    errors: List[str]
    timestamp: float


class ArtifactCleanupManager:
    """
    V7.6 Artifact Cleanup Manager - Automated cleanup of forensic
    artifacts including logs, caches, temp files, and metadata.
    """
    
    # Cleanup targets by category
    CLEANUP_TARGETS = {
        "temp_files": [
            "/tmp/*titan*", "/tmp/*TITAN*", "/var/tmp/*titan*",
            "/dev/shm/*titan*", "/tmp/core.*", "/var/crash/*"
        ],
        "logs": [
            "/var/log/titan*", "/var/log/auth.log", "/var/log/secure",
            "/var/log/syslog", "/var/log/messages", "/var/log/dmesg"
        ],
        "bash_history": [
            "/root/.bash_history", "/home/*/.bash_history",
            "/root/.zsh_history", "/home/*/.zsh_history"
        ],
        "browser_cache": [
            "/root/.cache/mozilla", "/home/*/.cache/mozilla",
            "/root/.cache/google-chrome", "/home/*/.cache/google-chrome"
        ],
        "system_cache": [
            "/var/cache/apt/archives/*.deb", "/var/cache/fontconfig"
        ]
    }
    
    # Log sanitization patterns (strings to remove from logs)
    LOG_SANITIZE_PATTERNS = [
        r"titan", r"TITAN", r"lucid", r"LUCID",
        r"camoufox", r"ghost.?motor", r"cerberus",
        r"proxy.*socks", r"vpn.*connect"
    ]
    
    def __init__(self):
        self._cleanup_history: List[CleanupResult] = []
        self._total_cleaned = 0
    
    def cleanup_temp_files(self) -> Tuple[int, List[str]]:
        """Remove temporary files."""
        from glob import glob
        removed = 0
        errors = []
        
        for pattern in self.CLEANUP_TARGETS["temp_files"]:
            try:
                for filepath in glob(pattern):
                    try:
                        path = Path(filepath)
                        if path.is_file():
                            path.unlink()
                            removed += 1
                        elif path.is_dir():
                            import shutil
                            shutil.rmtree(path)
                            removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove {filepath}: {e}")
            except Exception as e:
                errors.append(f"Pattern {pattern} error: {e}")
        
        return removed, errors
    
    def sanitize_logs(self) -> Tuple[int, List[str]]:
        """Sanitize system logs by removing sensitive entries."""
        import re
        sanitized = 0
        errors = []
        
        pattern = re.compile("|".join(self.LOG_SANITIZE_PATTERNS), re.IGNORECASE)
        
        for log_pattern in self.CLEANUP_TARGETS["logs"]:
            try:
                from glob import glob
                for log_file in glob(log_pattern):
                    try:
                        path = Path(log_file)
                        if not path.exists() or not path.is_file():
                            continue
                        
                        content = path.read_text(errors='ignore')
                        lines = content.split('\n')
                        
                        # Remove lines matching sensitive patterns
                        clean_lines = [
                            line for line in lines 
                            if not pattern.search(line)
                        ]
                        
                        if len(clean_lines) < len(lines):
                            path.write_text('\n'.join(clean_lines))
                            sanitized += len(lines) - len(clean_lines)
                            
                    except PermissionError:
                        errors.append(f"Permission denied: {log_file}")
                    except Exception as e:
                        errors.append(f"Failed to sanitize {log_file}: {e}")
            except Exception as e:
                errors.append(f"Pattern error: {e}")
        
        return sanitized, errors
    
    def clear_bash_history(self) -> Tuple[int, List[str]]:
        """Clear bash/zsh history files."""
        from glob import glob
        cleared = 0
        errors = []
        
        for pattern in self.CLEANUP_TARGETS["bash_history"]:
            try:
                for hist_file in glob(pattern):
                    try:
                        Path(hist_file).write_text("")
                        cleared += 1
                    except Exception as e:
                        errors.append(f"Failed to clear {hist_file}: {e}")
            except Exception as e:
                errors.append(f"Pattern error: {e}")
        
        return cleared, errors
    
    def clear_browser_caches(self) -> Tuple[int, List[str]]:
        """Clear browser cache directories."""
        from glob import glob
        import shutil
        cleared = 0
        errors = []
        
        for pattern in self.CLEANUP_TARGETS["browser_cache"]:
            try:
                for cache_dir in glob(pattern):
                    try:
                        if Path(cache_dir).is_dir():
                            shutil.rmtree(cache_dir)
                            cleared += 1
                    except Exception as e:
                        errors.append(f"Failed to clear {cache_dir}: {e}")
            except Exception as e:
                errors.append(f"Pattern error: {e}")
        
        return cleared, errors
    
    def secure_delete(self, filepath: str, passes: int = 3) -> bool:
        """
        Securely delete a file by overwriting with random data.
        
        Args:
            filepath: Path to file
            passes: Number of overwrite passes
        
        Returns:
            True if successful
        """
        import random
        
        try:
            path = Path(filepath)
            if not path.exists():
                return False
            
            file_size = path.stat().st_size
            
            with open(path, 'wb') as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(random.randbytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            path.unlink()
            return True
            
        except Exception as e:
            logger.error(f"[V7.6] Secure delete failed for {filepath}: {e}")
            return False
    
    def full_cleanup(self) -> CleanupResult:
        """Perform full artifact cleanup."""
        all_errors = []
        
        files_removed, errs = self.cleanup_temp_files()
        all_errors.extend(errs)
        
        logs_sanitized, errs = self.sanitize_logs()
        all_errors.extend(errs)
        
        hist_cleared, errs = self.clear_bash_history()
        all_errors.extend(errs)
        
        caches_cleared, errs = self.clear_browser_caches()
        all_errors.extend(errs)
        
        result = CleanupResult(
            success=len(all_errors) == 0,
            files_removed=files_removed,
            logs_sanitized=logs_sanitized,
            caches_cleared=caches_cleared + hist_cleared,
            errors=all_errors[:20],  # Limit errors
            timestamp=time.time()
        )
        
        self._cleanup_history.append(result)
        self._total_cleaned += files_removed + logs_sanitized + caches_cleared + hist_cleared
        
        logger.info(f"[V7.6] Cleanup complete: {files_removed} files, {logs_sanitized} log entries, {caches_cleared} caches")
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        return {
            "total_cleaned": self._total_cleaned,
            "cleanup_operations": len(self._cleanup_history),
            "last_cleanup": self._cleanup_history[-1].timestamp if self._cleanup_history else None
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 REAL-TIME ALERT SYSTEM — Real-time alert generation and notification
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An alert generated by the monitoring system."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: float
    acknowledged: bool = False
    actions_taken: List[str] = field(default_factory=list)


class RealTimeAlertSystem:
    """
    V7.6 Real-Time Alert System - Generates and manages alerts
    for security events and anomalies.
    """
    
    # Alert thresholds
    THRESHOLDS = {
        "failed_logins": {"count": 5, "window": 300, "severity": AlertSeverity.DANGER},
        "process_cpu": {"threshold": 90, "severity": AlertSeverity.WARNING},
        "disk_usage": {"threshold": 90, "severity": AlertSeverity.WARNING},
        "memory_usage": {"threshold": 95, "severity": AlertSeverity.DANGER},
        "suspicious_files": {"count": 3, "severity": AlertSeverity.WARNING},
        "network_anomaly": {"severity": AlertSeverity.DANGER},
    }
    
    def __init__(self, max_alerts: int = 1000):
        self._alerts: List[Alert] = []
        self._alert_counter = 0
        self._max_alerts = max_alerts
        self._notification_callbacks: List[callable] = []
        self._alert_lock = threading.Lock()
    
    def generate_alert(self, severity: AlertSeverity, title: str, 
                      message: str, source: str = "forensic_monitor") -> Alert:
        """Generate a new alert."""
        with self._alert_lock:
            self._alert_counter += 1
            
            alert = Alert(
                alert_id=f"ALERT-{self._alert_counter:06d}",
                severity=severity,
                title=title,
                message=message,
                source=source,
                timestamp=time.time()
            )
            
            self._alerts.append(alert)
            
            # Prune old alerts if needed
            if len(self._alerts) > self._max_alerts:
                self._alerts = self._alerts[-self._max_alerts:]
            
            # Call notification callbacks
            for callback in self._notification_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.debug(f"Alert callback failed: {e}")
            
            logger.warning(f"[V7.6] Alert generated: [{severity.value.upper()}] {title}")
            return alert
    
    def check_system_state(self, system_state: Dict[str, Any]) -> List[Alert]:
        """Check system state and generate alerts as needed."""
        alerts = []
        
        # Check memory usage
        memory = system_state.get("memory", {})
        if memory:
            try:
                total = int(memory.get("MemTotal", 0))
                free = int(memory.get("MemFree", 0)) + int(memory.get("Cached", 0))
                if total > 0:
                    usage_pct = (total - free) / total * 100
                    if usage_pct > self.THRESHOLDS["memory_usage"]["threshold"]:
                        alerts.append(self.generate_alert(
                            self.THRESHOLDS["memory_usage"]["severity"],
                            "High Memory Usage",
                            f"Memory usage at {usage_pct:.1f}%",
                            "memory_monitor"
                        ))
            except (ValueError, TypeError):
                pass
        
        # Check suspicious files
        suspicious = system_state.get("filesystem", {}).get("suspicious_files", [])
        if len(suspicious) >= self.THRESHOLDS["suspicious_files"]["count"]:
            alerts.append(self.generate_alert(
                self.THRESHOLDS["suspicious_files"]["severity"],
                "Suspicious Files Detected",
                f"Found {len(suspicious)} suspicious files in the system",
                "filesystem_monitor"
            ))
        
        # Check for forensic tools in processes
        for proc in system_state.get("processes", []):
            command = proc.get("command", "").lower()
            forensic_tools = ["volatility", "sleuthkit", "autopsy", "foremost", "tcpdump"]
            if any(tool in command for tool in forensic_tools):
                alerts.append(self.generate_alert(
                    AlertSeverity.CRITICAL,
                    "Forensic Tool Detected",
                    f"Potential forensic analysis tool running: {command[:100]}",
                    "process_monitor"
                ))
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        with self._alert_lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None,
                         unacknowledged_only: bool = False) -> List[Alert]:
        """Get active alerts, optionally filtered."""
        with self._alert_lock:
            alerts = self._alerts.copy()
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alert status."""
        alerts = self.get_active_alerts()
        
        by_severity = defaultdict(int)
        unacknowledged = 0
        
        for alert in alerts:
            by_severity[alert.severity.value] += 1
            if not alert.acknowledged:
                unacknowledged += 1
        
        return {
            "total_alerts": len(alerts),
            "unacknowledged": unacknowledged,
            "by_severity": dict(by_severity),
            "recent": [
                {
                    "id": a.alert_id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "time": a.timestamp
                }
                for a in sorted(alerts, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }
    
    def register_callback(self, callback: callable):
        """Register a callback for new alerts."""
        self._notification_callbacks.append(callback)
    
    def clear_old_alerts(self, max_age_hours: int = 24) -> int:
        """Clear alerts older than specified hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        
        with self._alert_lock:
            original_count = len(self._alerts)
            self._alerts = [a for a in self._alerts if a.timestamp > cutoff]
            cleared = original_count - len(self._alerts)
        
        return cleared


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 FORENSIC DASHBOARD — Dashboard data aggregation and status tracking
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DashboardStatus:
    """Current dashboard status."""
    overall_health: str  # "healthy", "warning", "critical"
    threat_level: str
    active_alerts: int
    last_scan: float
    uptime_hours: float
    modules_active: int
    components: Dict[str, str]


class ForensicDashboard:
    """
    V7.6 Forensic Dashboard - Aggregates monitoring data for
    display and provides unified status tracking.
    """
    
    def __init__(self):
        self._start_time = time.time()
        self._scan_history: List[Dict] = []
        self._component_status: Dict[str, str] = {}
        self._metrics: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # metric -> [(timestamp, value)]
    
    def record_scan(self, scan_result: Dict[str, Any], analysis: Optional[Dict] = None):
        """Record a scan result."""
        entry = {
            "timestamp": time.time(),
            "result": scan_result,
            "analysis": analysis
        }
        
        self._scan_history.append(entry)
        
        # Prune old scans (keep last 100)
        if len(self._scan_history) > 100:
            self._scan_history = self._scan_history[-100:]
    
    def update_component_status(self, component: str, status: str):
        """Update status of a monitoring component."""
        self._component_status[component] = status
    
    def record_metric(self, metric_name: str, value: float):
        """Record a metric value."""
        now = time.time()
        self._metrics[metric_name].append((now, value))
        
        # Prune old metrics (keep last hour)
        cutoff = now - 3600
        self._metrics[metric_name] = [
            (t, v) for t, v in self._metrics[metric_name] if t > cutoff
        ]
    
    def get_status(self, threat_engine: Optional[ThreatCorrelationEngine] = None,
                  alert_system: Optional[RealTimeAlertSystem] = None) -> DashboardStatus:
        """Get current dashboard status."""
        now = time.time()
        
        # Calculate overall health
        health = "healthy"
        threat_level = "low"
        active_alerts = 0
        
        if threat_engine:
            summary = threat_engine.get_threat_summary()
            threat_level = summary["overall_level"]
            if threat_level in ("critical", "high"):
                health = "critical"
            elif threat_level == "medium":
                health = "warning"
        
        if alert_system:
            alert_summary = alert_system.get_alert_summary()
            active_alerts = alert_summary["unacknowledged"]
            if alert_summary["by_severity"].get("critical", 0) > 0:
                health = "critical"
            elif alert_summary["by_severity"].get("danger", 0) > 0 and health != "critical":
                health = "warning"
        
        last_scan = self._scan_history[-1]["timestamp"] if self._scan_history else self._start_time
        
        return DashboardStatus(
            overall_health=health,
            threat_level=threat_level,
            active_alerts=active_alerts,
            last_scan=last_scan,
            uptime_hours=round((now - self._start_time) / 3600, 1),
            modules_active=len([s for s in self._component_status.values() if s == "active"]),
            components=self._component_status.copy()
        )
    
    def get_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of recorded metrics."""
        summary = {}
        
        for metric_name, values in self._metrics.items():
            if values:
                vals = [v for _, v in values]
                summary[metric_name] = {
                    "current": vals[-1],
                    "min": min(vals),
                    "max": max(vals),
                    "avg": sum(vals) / len(vals),
                    "samples": len(vals)
                }
        
        return summary
    
    def get_scan_trend(self, hours: int = 24) -> List[Dict]:
        """Get scan results trend for specified hours."""
        cutoff = time.time() - (hours * 3600)
        return [s for s in self._scan_history if s["timestamp"] > cutoff]
    
    def export_report(self) -> Dict[str, Any]:
        """Export full dashboard report."""
        status = self.get_status()
        
        return {
            "generated_at": time.time(),
            "status": {
                "health": status.overall_health,
                "threat_level": status.threat_level,
                "active_alerts": status.active_alerts,
                "uptime_hours": status.uptime_hours
            },
            "components": status.components,
            "metrics": self.get_metrics_summary(),
            "recent_scans": len(self._scan_history),
            "scan_trend": self.get_scan_trend(1)  # Last hour
        }


# Global instances
_threat_engine: Optional[ThreatCorrelationEngine] = None
_cleanup_manager: Optional[ArtifactCleanupManager] = None
_alert_system: Optional[RealTimeAlertSystem] = None
_dashboard: Optional[ForensicDashboard] = None


def get_threat_engine() -> ThreatCorrelationEngine:
    """Get global threat correlation engine."""
    global _threat_engine
    if _threat_engine is None:
        _threat_engine = ThreatCorrelationEngine()
    return _threat_engine


def get_cleanup_manager() -> ArtifactCleanupManager:
    """Get global artifact cleanup manager."""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = ArtifactCleanupManager()
    return _cleanup_manager


def get_alert_system() -> RealTimeAlertSystem:
    """Get global alert system."""
    global _alert_system
    if _alert_system is None:
        _alert_system = RealTimeAlertSystem()
    return _alert_system


def get_dashboard() -> ForensicDashboard:
    """Get global forensic dashboard."""
    global _dashboard
    if _dashboard is None:
        _dashboard = ForensicDashboard()
    return _dashboard
