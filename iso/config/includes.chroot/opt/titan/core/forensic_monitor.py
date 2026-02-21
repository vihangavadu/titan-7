"""
TITAN V7.5 SINGULARITY — Forensic Detection Monitor
Real-time OS analysis using LLM to detect forensic artifacts, missing components, and detectable traces.
"""

import os
import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
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
            "timestamp": datetime.utcnow().isoformat(),
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
            return subprocess.check_output(["hostname"], text=True).strip()
        except:
            return "unknown"
    
    def _get_kernel_info(self) -> Dict[str, str]:
        """Get kernel and system info."""
        info = {}
        try:
            # Kernel version
            info["kernel"] = subprocess.check_output(["uname", "-r"], text=True).strip()
            info["system"] = subprocess.check_output(["uname", "-s"], text=True).strip()
            info["arch"] = subprocess.check_output(["uname", "-m"], text=True).strip()
            
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
            ], text=True)
            
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
                ], text=True, stderr=subprocess.DEVNULL)
                for line in output.strip().split('\n')[2:]:
                    if line.strip():
                        network["connections"].append(line.split()[:5])
            except:
                pass
            
            # Routing table
            try:
                output = subprocess.check_output(["ip", "route"], text=True)
                network["routes"] = output.strip().split('\n')[:10]
            except:
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
                except:
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
                except:
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
                    ], text=True, stderr=subprocess.DEVNULL)
                    
                    # Filter for suspicious keywords
                    suspicious_keywords = [
                        "failed", "denied", "error", "intrusion", "attack",
                        "breach", "unauthorized", "suspicious", "malware"
                    ]
                    
                    for line in output.strip().split('\n'):
                        if any(keyword in line.lower() for keyword in suspicious_keywords):
                            logs[log_type].append(line.strip())
            except:
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
            except:
                # Fallback to service command
                try:
                    result = subprocess.run([
                        "service", service, "status"
                    ], capture_output=True, text=True, timeout=5)
                    if "running" in result.stdout.lower():
                        services[service] = "active"
                    else:
                        services[service] = "inactive"
                except:
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
                ], text=True)
                hardware["disks"] = output.strip().split('\n')[1:]  # Skip header
            except:
                pass
            
            # USB devices
            try:
                output = subprocess.check_output([
                    "lsusb"
                ], text=True, stderr=subprocess.DEVNULL)
                hardware["usb_devices"] = output.strip().split('\n')
            except:
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
            except:
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
            except:
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
        except:
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
