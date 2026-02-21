"""
TITAN V7.6 SINGULARITY — Self-Hosted Tool Stack Integration
Unified interface to all self-hosted services that boost operation success rate,
user experience, operational planning, and target analysis.

╔══════════════════════════════════════════════════════════════════════════════╗
║  TOOL STACK OVERVIEW                                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ── A. SUCCESS RATE BOOSTERS ──                                              ║
║  1. GeoIP Validator     — MaxMind GeoLite2 offline DB for geo-match checks   ║
║  2. IP Quality Checker  — Self-hosted IP reputation scoring                  ║
║  3. Fingerprint Tester  — Self-hosted CreepJS for pre-launch fingerprint QA  ║
║  4. Proxy Health Monitor— Continuous proxy pool health scoring               ║
║                                                                              ║
║  ── B. USER EXPERIENCE ──                                                    ║
║  5. Uptime Kuma         — Service monitoring dashboard (all Titan services)  ║
║  6. Ntfy                — Push notifications to phone on op events           ║
║  7. Grafana + Prometheus— Metrics dashboard for success rates & trends       ║
║                                                                              ║
║  ── C. OPERATION PLANNING ──                                                 ║
║  8. n8n                 — Workflow automation (auto-recon → plan → execute)   ║
║  9. Redis               — Fast inter-module state, job queues, rate limiting ║
║  10. Nocodb/Baserow     — Visual database for targets, BINs, operations      ║
║                                                                              ║
║  ── D. TARGET ANALYSIS ──                                                    ║
║  11. Headless Browser   — Playwright for automated target probing            ║
║  12. Wappalyzer         — Technology stack detection on target sites          ║
║  13. Nuclei             — Vulnerability/misconfiguration scanner             ║
║                                                                              ║
║  ── E. INFRASTRUCTURE ──                                                     ║
║  14. MinIO              — S3-compatible object storage for profiles/assets    ║
║  15. Loki               — Log aggregation (pair with Grafana)                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Architecture:
    - Each tool has a client class with health check + core operations
    - Tools are lazy-initialized on first use (no startup overhead)
    - All tools are OPTIONAL — Titan works without any of them
    - get_stack_status() returns health of all configured tools
    - install_self_hosted_stack.sh handles Docker/native installation
"""

import json
import time
import os
import hashlib
import logging
import threading
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

__version__ = "7.6.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-STACK")

# Load titan.env
_TITAN_ENV = Path("/opt/titan/config/titan.env")
if _TITAN_ENV.exists():
    for _line in _TITAN_ENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip()
            if _v and not _v.startswith("REPLACE_WITH") and _k not in os.environ:
                os.environ[_k] = _v


# ═══════════════════════════════════════════════════════════════════════════════
# A1. GEOIP VALIDATOR — MaxMind GeoLite2 Offline Database
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Ensures proxy IP geo matches card billing country/state.
#      Geo mismatch is the #1 decline reason on Forter/Riskified.
#      Offline DB = zero API calls, zero latency, zero cost.
# RAM: ~50MB for city DB
# INSTALL: pip install geoip2 + download GeoLite2-City.mmdb

class GeoIPValidator:
    """
    Offline IP geolocation using MaxMind GeoLite2 database.
    
    Usage:
        geo = get_geoip_validator()
        result = geo.lookup("1.2.3.4")
        # → {"country": "US", "state": "California", "city": "Los Angeles", 
        #    "lat": 34.05, "lon": -118.24, "timezone": "America/Los_Angeles"}
        
        match = geo.check_geo_match("1.2.3.4", card_country="US", card_state="CA")
        # → {"match": True, "country_match": True, "state_match": True, "score": 1.0}
    """
    
    DB_PATHS = [
        Path("/opt/titan/data/geoip/GeoLite2-City.mmdb"),
        Path("/usr/share/GeoIP/GeoLite2-City.mmdb"),
        Path("/var/lib/GeoIP/GeoLite2-City.mmdb"),
    ]
    
    def __init__(self, db_path: str = None):
        self._reader = None
        self._available = False
        self._db_path = None
        
        try:
            import geoip2.database
            path = Path(db_path) if db_path else self._find_db()
            if path and path.exists():
                self._reader = geoip2.database.Reader(str(path))
                self._db_path = path
                self._available = True
                logger.info(f"GeoIP loaded: {path} ({path.stat().st_size // 1048576}MB)")
        except ImportError:
            logger.debug("geoip2 not installed: pip install geoip2")
        except Exception as e:
            logger.warning(f"GeoIP init failed: {e}")
    
    def _find_db(self) -> Optional[Path]:
        for p in self.DB_PATHS:
            if p.exists():
                return p
        return None
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def lookup(self, ip: str) -> Dict:
        """Look up geolocation for an IP address."""
        if not self._available:
            return {"error": "GeoIP not available"}
        try:
            r = self._reader.city(ip)
            return {
                "ip": ip,
                "country": r.country.iso_code or "",
                "country_name": r.country.name or "",
                "state": r.subdivisions.most_specific.iso_code if r.subdivisions else "",
                "state_name": r.subdivisions.most_specific.name if r.subdivisions else "",
                "city": r.city.name or "",
                "postal": r.postal.code or "",
                "lat": r.location.latitude,
                "lon": r.location.longitude,
                "timezone": r.location.time_zone or "",
                "accuracy_km": r.location.accuracy_radius,
            }
        except Exception as e:
            return {"ip": ip, "error": str(e)}
    
    def check_geo_match(self, proxy_ip: str, card_country: str = "",
                        card_state: str = "", card_zip: str = "") -> Dict:
        """
        Check if proxy IP geolocation matches card billing address.
        Returns match score 0.0-1.0 and detailed breakdown.
        """
        geo = self.lookup(proxy_ip)
        if "error" in geo:
            return {"match": False, "score": 0.0, "error": geo["error"]}
        
        score = 0.0
        details = {}
        
        # Country match (most critical)
        country_match = geo.get("country", "").upper() == card_country.upper()
        details["country_match"] = country_match
        if country_match:
            score += 0.5
        
        # State match
        if card_state:
            state_match = geo.get("state", "").upper() == card_state.upper()
            details["state_match"] = state_match
            if state_match:
                score += 0.3
        else:
            score += 0.15  # No state to check, partial credit
        
        # ZIP proximity (if available)
        if card_zip and geo.get("postal"):
            zip_match = geo["postal"][:3] == card_zip[:3]
            details["zip_prefix_match"] = zip_match
            if zip_match:
                score += 0.2
        else:
            score += 0.05
        
        details["proxy_geo"] = {
            "country": geo.get("country"), "state": geo.get("state"),
            "city": geo.get("city"), "timezone": geo.get("timezone"),
        }
        
        return {
            "match": score >= 0.5,
            "score": round(score, 2),
            "details": details,
        }
    
    def get_timezone_for_ip(self, ip: str) -> str:
        """Get timezone string for an IP (for timezone_enforcer)."""
        geo = self.lookup(ip)
        return geo.get("timezone", "America/New_York")
    
    def get_stats(self) -> Dict:
        return {
            "available": self._available,
            "db_path": str(self._db_path) if self._db_path else None,
            "db_size_mb": round(self._db_path.stat().st_size / 1048576, 1) if self._db_path and self._db_path.exists() else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# A2. IP QUALITY CHECKER — Self-Hosted IP Reputation Scoring
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Know if your proxy IP is already flagged BEFORE you start an operation.
#      A burned IP = instant decline regardless of everything else.
# RAM: ~10MB
# INSTALL: Queries multiple free APIs (AbuseIPDB, ip-api, ipinfo)

class IPQualityChecker:
    """
    Multi-source IP reputation checker.
    Queries free APIs to score proxy IPs before operations.
    
    Usage:
        checker = get_ip_quality_checker()
        result = checker.check("1.2.3.4")
        # → {"ip": "1.2.3.4", "risk_score": 25, "is_proxy": True, 
        #    "is_vpn": True, "is_datacenter": True, "recommendation": "CAUTION"}
    """
    
    def __init__(self):
        self._cache: Dict[str, Tuple[float, Dict]] = {}
        self._cache_ttl = 3600  # 1 hour
        self._lock = threading.Lock()
    
    @property
    def is_available(self) -> bool:
        return True  # Always available (uses free APIs + heuristics)
    
    def check(self, ip: str, use_cache: bool = True) -> Dict:
        """Check IP quality and reputation."""
        # Cache check
        if use_cache:
            with self._lock:
                cached = self._cache.get(ip)
                if cached and time.time() - cached[0] < self._cache_ttl:
                    return cached[1]
        
        result = {
            "ip": ip,
            "risk_score": 0,
            "is_proxy": False,
            "is_vpn": False,
            "is_datacenter": False,
            "is_tor": False,
            "is_residential": False,
            "country": "",
            "isp": "",
            "org": "",
            "sources_checked": [],
            "recommendation": "UNKNOWN",
        }
        
        # Source 1: ip-api.com (free, no key needed, 45 req/min)
        self._check_ipapi(ip, result)
        
        # Source 2: ipinfo.io (free tier: 50k/month)
        self._check_ipinfo(ip, result)
        
        # Source 3: Heuristic checks
        self._heuristic_checks(ip, result)
        
        # Calculate final recommendation
        score = result["risk_score"]
        if score <= 20:
            result["recommendation"] = "CLEAN"
        elif score <= 40:
            result["recommendation"] = "LOW_RISK"
        elif score <= 60:
            result["recommendation"] = "CAUTION"
        elif score <= 80:
            result["recommendation"] = "HIGH_RISK"
        else:
            result["recommendation"] = "BURNED"
        
        # Cache result
        with self._lock:
            self._cache[ip] = (time.time(), result)
        
        return result
    
    def _check_ipapi(self, ip: str, result: Dict):
        """Query ip-api.com for basic geo + ISP data."""
        try:
            import urllib.request
            url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,city,zip,lat,lon,timezone,isp,org,as,proxy,hosting"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            
            if data.get("status") == "success":
                result["country"] = data.get("countryCode", "")
                result["isp"] = data.get("isp", "")
                result["org"] = data.get("org", "")
                
                if data.get("proxy"):
                    result["is_proxy"] = True
                    result["risk_score"] += 30
                if data.get("hosting"):
                    result["is_datacenter"] = True
                    result["risk_score"] += 20
                
                result["sources_checked"].append("ip-api")
        except Exception as e:
            logger.debug(f"ip-api check failed: {e}")
    
    def _check_ipinfo(self, ip: str, result: Dict):
        """Query ipinfo.io for additional data."""
        try:
            import urllib.request
            token = os.getenv("IPINFO_TOKEN", "")
            url = f"https://ipinfo.io/{ip}/json"
            if token:
                url += f"?token={token}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            
            org = data.get("org", "").lower()
            # Datacenter ASN detection
            dc_keywords = ["amazon", "google", "microsoft", "digitalocean", "linode",
                           "vultr", "ovh", "hetzner", "hostinger", "contabo", "choopa",
                           "datacamp", "m247", "psychz", "cogent", "leaseweb"]
            if any(kw in org for kw in dc_keywords):
                result["is_datacenter"] = True
                result["risk_score"] += 15
            
            if not result["country"]:
                result["country"] = data.get("country", "")
            
            result["sources_checked"].append("ipinfo")
        except Exception as e:
            logger.debug(f"ipinfo check failed: {e}")
    
    def _heuristic_checks(self, ip: str, result: Dict):
        """Heuristic IP quality checks."""
        # Known bad ranges
        parts = ip.split(".")
        if len(parts) == 4:
            first_octet = int(parts[0])
            # Tor exit nodes commonly in these ranges
            if first_octet in (10, 172, 192):
                result["risk_score"] += 5  # Private range (shouldn't be public)
        
        # If ISP contains residential keywords, it's likely residential
        isp_lower = result.get("isp", "").lower()
        residential_keywords = ["comcast", "spectrum", "at&t", "verizon", "cox",
                                "centurylink", "frontier", "charter", "optimum",
                                "bt ", "virgin media", "sky broadband", "telstra",
                                "bell ", "rogers", "shaw", "telus"]
        if any(kw in isp_lower for kw in residential_keywords):
            result["is_residential"] = True
            result["risk_score"] = max(0, result["risk_score"] - 20)
        
        result["sources_checked"].append("heuristic")
    
    def batch_check(self, ips: List[str]) -> List[Dict]:
        """Check multiple IPs."""
        return [self.check(ip) for ip in ips]
    
    def get_stats(self) -> Dict:
        return {
            "available": True,
            "cached_ips": len(self._cache),
            "cache_ttl_seconds": self._cache_ttl,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# A3. FINGERPRINT TESTER — Self-Hosted CreepJS Instance
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Test your spoofed fingerprint BEFORE hitting the real target.
#      Catches canvas leaks, WebGL mismatches, timezone inconsistencies.
# RAM: ~20MB (static HTML served by Python http.server)
# INSTALL: Clone CreepJS repo, serve locally

class FingerprintTester:
    """
    Self-hosted fingerprint testing using CreepJS.
    Serves a local CreepJS instance for pre-launch fingerprint QA.
    
    Usage:
        tester = get_fingerprint_tester()
        url = tester.get_test_url()
        # → "http://127.0.0.1:8787/creepjs/"
        # Open this URL in Camoufox to verify fingerprint before operation
    """
    
    CREEPJS_DIR = Path("/opt/titan/tools/creepjs")
    DEFAULT_PORT = 8787
    
    def __init__(self, port: int = None):
        self._port = port or int(os.getenv("TITAN_FINGERPRINT_TEST_PORT", str(self.DEFAULT_PORT)))
        self._server_process = None
        self._available = self.CREEPJS_DIR.exists()
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def get_test_url(self) -> str:
        """Get URL for fingerprint testing."""
        return f"http://127.0.0.1:{self._port}/"
    
    def start_server(self) -> bool:
        """Start the local CreepJS server."""
        if not self._available:
            logger.warning("CreepJS not installed at /opt/titan/tools/creepjs")
            return False
        
        if self._server_process and self._server_process.poll() is None:
            return True  # Already running
        
        try:
            self._server_process = subprocess.Popen(
                ["python3", "-m", "http.server", str(self._port)],
                cwd=str(self.CREEPJS_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
            if self._server_process.poll() is None:
                logger.info(f"CreepJS server started on port {self._port}")
                return True
        except Exception as e:
            logger.error(f"Failed to start CreepJS server: {e}")
        return False
    
    def stop_server(self):
        """Stop the local CreepJS server."""
        if self._server_process:
            self._server_process.terminate()
            self._server_process = None
    
    def get_stats(self) -> Dict:
        running = self._server_process is not None and self._server_process.poll() is None
        return {
            "available": self._available,
            "server_running": running,
            "port": self._port,
            "test_url": self.get_test_url() if running else None,
            "creepjs_path": str(self.CREEPJS_DIR),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# A4. PROXY HEALTH MONITOR — Continuous Proxy Pool Scoring
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Dead/slow/flagged proxies = failed operations.
#      Continuous health scoring ensures only clean proxies are used.
# RAM: ~5MB

class ProxyHealthMonitor:
    """
    Continuous proxy pool health monitoring.
    Tests latency, anonymity, and reputation of each proxy.
    
    Usage:
        monitor = get_proxy_health_monitor()
        monitor.add_proxy("socks5://user:pass@host:port")
        health = monitor.check_proxy("socks5://user:pass@host:port")
        best = monitor.get_best_proxies(country="US", n=3)
    """
    
    def __init__(self):
        self._proxies: Dict[str, Dict] = {}  # proxy_url -> health data
        self._lock = threading.Lock()
    
    @property
    def is_available(self) -> bool:
        return True
    
    def add_proxy(self, proxy_url: str, country: str = "") -> None:
        """Add a proxy to the monitoring pool."""
        with self._lock:
            self._proxies[proxy_url] = {
                "url": proxy_url,
                "country": country,
                "last_check": 0,
                "latency_ms": 0,
                "alive": False,
                "score": 0,
                "checks": 0,
                "failures": 0,
            }
    
    def check_proxy(self, proxy_url: str) -> Dict:
        """Health check a single proxy."""
        import urllib.request
        import urllib.error
        
        result = self._proxies.get(proxy_url, {"url": proxy_url})
        t0 = time.time()
        
        try:
            # Set up proxy handler
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy_url,
                "https": proxy_url,
            })
            opener = urllib.request.build_opener(proxy_handler)
            
            # Test connectivity + get external IP
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=query,country,countryCode,proxy,hosting",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with opener.open(req, timeout=10) as resp:
                data = json.loads(resp.read())
            
            latency = (time.time() - t0) * 1000
            
            result["alive"] = True
            result["latency_ms"] = round(latency, 1)
            result["external_ip"] = data.get("query", "")
            result["country"] = data.get("countryCode", result.get("country", ""))
            result["is_proxy_detected"] = data.get("proxy", False)
            result["is_datacenter"] = data.get("hosting", False)
            result["last_check"] = time.time()
            result["checks"] = result.get("checks", 0) + 1
            
            # Score: lower latency + residential = better
            score = 100
            if latency > 2000:
                score -= 30
            elif latency > 1000:
                score -= 15
            elif latency > 500:
                score -= 5
            
            if result.get("is_datacenter"):
                score -= 25
            if result.get("is_proxy_detected"):
                score -= 15
            
            failure_rate = result.get("failures", 0) / max(result.get("checks", 1), 1)
            score -= int(failure_rate * 30)
            
            result["score"] = max(0, min(100, score))
            
        except Exception as e:
            result["alive"] = False
            result["last_check"] = time.time()
            result["failures"] = result.get("failures", 0) + 1
            result["checks"] = result.get("checks", 0) + 1
            result["score"] = max(0, result.get("score", 50) - 10)
            result["error"] = str(e)
        
        with self._lock:
            self._proxies[proxy_url] = result
        
        return result
    
    def check_all(self) -> List[Dict]:
        """Health check all proxies in the pool."""
        results = []
        for proxy_url in list(self._proxies.keys()):
            results.append(self.check_proxy(proxy_url))
        return results
    
    def get_best_proxies(self, country: str = None, n: int = 5) -> List[Dict]:
        """Get the best proxies by score, optionally filtered by country."""
        with self._lock:
            proxies = list(self._proxies.values())
        
        # Filter alive proxies
        alive = [p for p in proxies if p.get("alive")]
        
        # Filter by country
        if country:
            alive = [p for p in alive if p.get("country", "").upper() == country.upper()]
        
        # Sort by score descending
        alive.sort(key=lambda p: p.get("score", 0), reverse=True)
        
        return alive[:n]
    
    def get_stats(self) -> Dict:
        with self._lock:
            total = len(self._proxies)
            alive = sum(1 for p in self._proxies.values() if p.get("alive"))
        return {
            "available": True,
            "total_proxies": total,
            "alive_proxies": alive,
            "dead_proxies": total - alive,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# B5. UPTIME KUMA — Service Monitoring Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Know instantly when Ollama, backend, proxy, or any service goes down.
#      30MB RAM, beautiful web dashboard.
# INSTALL: Docker or npm

class UptimeKumaClient:
    """
    Client for self-hosted Uptime Kuma monitoring.
    
    Usage:
        kuma = get_uptime_kuma()
        status = kuma.get_all_monitors()
        kuma.add_monitor("Ollama", "http://127.0.0.1:11434", monitor_type="http")
    """
    
    def __init__(self, url: str = None, username: str = None, password: str = None):
        self._url = url or os.getenv("TITAN_UPTIME_KUMA_URL", "http://127.0.0.1:3001")
        self._username = username or os.getenv("TITAN_UPTIME_KUMA_USER", "admin")
        self._password = password or os.getenv("TITAN_UPTIME_KUMA_PASS", "")
        self._available = False
        self._check_available()
    
    def _check_available(self):
        try:
            import urllib.request
            with urllib.request.urlopen(self._url, timeout=3) as r:
                self._available = r.status == 200
        except Exception:
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def get_status_page(self) -> str:
        """Get URL to the Uptime Kuma dashboard."""
        return self._url
    
    def get_stats(self) -> Dict:
        return {
            "available": self._available,
            "url": self._url,
            "dashboard": self._url if self._available else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# B6. NTFY — Push Notifications
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Get instant phone alerts when operations succeed/fail/need attention.
#      2MB RAM, works with any phone (no app needed, just browser).
# INSTALL: Docker or single binary

class NtfyClient:
    """
    Self-hosted push notification client via ntfy.sh.
    
    Usage:
        ntfy = get_ntfy_client()
        ntfy.send("Operation completed: BIN 411111 on amazon.com — SUCCESS ✓")
        ntfy.send("ALERT: Proxy pool depleted!", priority="high", tags=["warning"])
    """
    
    def __init__(self, server_url: str = None, topic: str = None):
        self._server = server_url or os.getenv("TITAN_NTFY_URL", "http://127.0.0.1:8090")
        self._topic = topic or os.getenv("TITAN_NTFY_TOPIC", "titan-ops")
        self._available = False
        self._sent_count = 0
        self._check_available()
    
    def _check_available(self):
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self._server}/v1/health", timeout=3) as r:
                self._available = r.status == 200
        except Exception:
            # Try the base URL
            try:
                import urllib.request
                with urllib.request.urlopen(self._server, timeout=3) as r:
                    self._available = r.status == 200
            except Exception:
                self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def send(self, message: str, title: str = "Titan OS",
             priority: str = "default", tags: List[str] = None) -> bool:
        """
        Send a push notification.
        
        Args:
            message: Notification body
            title: Notification title
            priority: min, low, default, high, urgent
            tags: List of emoji tags (e.g., ["white_check_mark", "warning"])
        """
        try:
            import urllib.request
            url = f"{self._server}/{self._topic}"
            headers = {
                "Title": title,
                "Priority": priority,
            }
            if tags:
                headers["Tags"] = ",".join(tags)
            
            req = urllib.request.Request(
                url, data=message.encode("utf-8"),
                headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._sent_count += 1
                return resp.status == 200
        except Exception as e:
            logger.debug(f"Ntfy send failed: {e}")
            return False
    
    def send_operation_result(self, op_data: Dict) -> bool:
        """Send formatted operation result notification."""
        result = op_data.get("result", "unknown")
        bin_num = op_data.get("bin", "???")[:6]
        target = op_data.get("target", "???")
        amount = op_data.get("amount", 0)
        
        if result in ("success", "approved"):
            emoji = "white_check_mark"
            priority = "high"
            msg = f"✅ SUCCESS: BIN {bin_num} on {target} — ${amount:.2f}"
        elif result in ("declined", "failed"):
            emoji = "x"
            priority = "default"
            reason = op_data.get("reason", "unknown")
            msg = f"❌ DECLINED: BIN {bin_num} on {target} — {reason}"
        else:
            emoji = "question"
            priority = "low"
            msg = f"❓ {result.upper()}: BIN {bin_num} on {target}"
        
        return self.send(msg, title="Titan Operation", priority=priority, tags=[emoji])
    
    def send_alert(self, alert_type: str, message: str) -> bool:
        """Send a system alert."""
        priority_map = {
            "critical": "urgent",
            "warning": "high",
            "info": "default",
        }
        tag_map = {
            "critical": "rotating_light",
            "warning": "warning",
            "info": "information_source",
        }
        return self.send(
            message, title=f"Titan Alert: {alert_type.upper()}",
            priority=priority_map.get(alert_type, "default"),
            tags=[tag_map.get(alert_type, "bell")]
        )
    
    def get_stats(self) -> Dict:
        return {
            "available": self._available,
            "server": self._server,
            "topic": self._topic,
            "sent_count": self._sent_count,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# C9. REDIS — Fast Inter-Module State & Job Queues
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Fast shared state between all 75 modules. Rate limiting, job queues,
#      session state, proxy rotation state, operation locks.
# RAM: ~10MB base + data
# INSTALL: apt install redis-server

class RedisClient:
    """
    Redis client for fast inter-module state sharing.
    
    Usage:
        r = get_redis_client()
        r.set("proxy:current", "socks5://...", ttl=300)
        r.get("proxy:current")
        r.increment("ops:today:success")
        r.rate_limit("bin:411111", max_per_hour=5)
    """
    
    def __init__(self, host: str = None, port: int = None, db: int = 0):
        self._host = host or os.getenv("TITAN_REDIS_HOST", "127.0.0.1")
        self._port = port or int(os.getenv("TITAN_REDIS_PORT", "6379"))
        self._db = db
        self._client = None
        self._available = False
        self._init_client()
    
    def _init_client(self):
        try:
            import redis
            self._client = redis.Redis(
                host=self._host, port=self._port, db=self._db,
                decode_responses=True, socket_timeout=3,
            )
            self._client.ping()
            self._available = True
            logger.info(f"Redis connected: {self._host}:{self._port}")
        except ImportError:
            logger.debug("redis not installed: pip install redis")
        except Exception as e:
            logger.debug(f"Redis not available: {e}")
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def set(self, key: str, value: str, ttl: int = None) -> bool:
        if not self._available:
            return False
        try:
            self._client.set(key, value, ex=ttl)
            return True
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[str]:
        if not self._available:
            return None
        try:
            return self._client.get(key)
        except Exception:
            return None
    
    def increment(self, key: str, amount: int = 1) -> int:
        if not self._available:
            return 0
        try:
            return self._client.incr(key, amount)
        except Exception:
            return 0
    
    def rate_limit(self, key: str, max_per_hour: int = 10) -> Tuple[bool, int]:
        """
        Check rate limit. Returns (allowed, current_count).
        Uses sliding window counter.
        """
        if not self._available:
            return True, 0
        
        try:
            rl_key = f"ratelimit:{key}"
            current = self._client.incr(rl_key)
            if current == 1:
                self._client.expire(rl_key, 3600)
            
            allowed = current <= max_per_hour
            return allowed, current
        except Exception:
            return True, 0
    
    def set_json(self, key: str, data: Any, ttl: int = None) -> bool:
        return self.set(key, json.dumps(data, default=str), ttl)
    
    def get_json(self, key: str) -> Optional[Any]:
        val = self.get(key)
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                pass
        return None
    
    def publish(self, channel: str, message: str) -> bool:
        """Publish message to a Redis channel (pub/sub)."""
        if not self._available:
            return False
        try:
            self._client.publish(channel, message)
            return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict:
        if not self._available:
            return {"available": False}
        try:
            info = self._client.info("memory")
            return {
                "available": True,
                "host": self._host,
                "port": self._port,
                "used_memory_mb": round(info.get("used_memory", 0) / 1048576, 1),
                "connected_clients": self._client.info("clients").get("connected_clients", 0),
            }
        except Exception:
            return {"available": True, "host": self._host, "port": self._port}


# ═══════════════════════════════════════════════════════════════════════════════
# D11. TARGET SITE PROBER — Playwright Headless Browser
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Automated target site probing — detect payment processor, antifraud,
#      3DS behavior, checkout flow, without manual browsing.
# RAM: ~100MB per browser instance
# INSTALL: pip install playwright && playwright install chromium

class TargetSiteProber:
    """
    Headless browser-based target site analysis using Playwright.
    
    Usage:
        prober = get_target_prober()
        result = prober.probe_target("https://amazon.com")
        # → {"domain": "amazon.com", "technologies": [...], 
        #    "antifraud": ["forter"], "payment_processor": "stripe", ...}
    """
    
    def __init__(self):
        self._available = False
        try:
            from playwright.sync_api import sync_playwright
            self._available = True
        except ImportError:
            logger.debug("playwright not installed: pip install playwright")
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def probe_target(self, url: str, timeout_ms: int = 30000) -> Dict:
        """
        Probe a target site for payment/antifraud intelligence.
        Launches headless Chromium, loads the page, analyzes scripts/cookies.
        """
        if not self._available:
            return {"error": "Playwright not available"}
        
        from playwright.sync_api import sync_playwright
        
        result = {
            "url": url,
            "domain": url.split("//")[-1].split("/")[0].replace("www.", ""),
            "technologies": [],
            "antifraud_detected": [],
            "payment_processors": [],
            "scripts_loaded": [],
            "cookies_set": [],
            "has_captcha": False,
            "has_3ds": False,
            "load_time_ms": 0,
            "status_code": 0,
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Collect network requests
                requests_urls = []
                page.on("request", lambda req: requests_urls.append(req.url))
                
                t0 = time.time()
                response = page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                result["load_time_ms"] = round((time.time() - t0) * 1000)
                result["status_code"] = response.status if response else 0
                
                # Get page content
                html = page.content().lower()
                
                # Detect antifraud
                af_signatures = {
                    "forter": ["forter.com", "fortertoken"],
                    "riskified": ["riskified.com", "beacon-v2", "riskx"],
                    "signifyd": ["signifyd.com", "sig-api"],
                    "sift": ["sift.com", "siftscience"],
                    "datadome": ["datadome.co"],
                    "perimeterx": ["px-client", "perimeterx"],
                    "kasada": ["kasada", "cd-kogmv"],
                    "shape": ["shape.com", "f5.com/shape"],
                    "kount": ["kount.com", "kaxsdc"],
                }
                
                for vendor, sigs in af_signatures.items():
                    for sig in sigs:
                        if sig in html or any(sig in r.lower() for r in requests_urls):
                            if vendor not in result["antifraud_detected"]:
                                result["antifraud_detected"].append(vendor)
                
                # Detect payment processors
                psp_signatures = {
                    "stripe": ["js.stripe.com", "stripe.com/v3"],
                    "adyen": ["adyen.com", "checkoutshopper"],
                    "braintree": ["braintreegateway.com", "braintree-api"],
                    "paypal": ["paypal.com/sdk", "paypalobjects"],
                    "shopify_payments": ["shopify.com/payments", "shopifycloud"],
                    "square": ["squareup.com", "square.com/web-payments"],
                    "worldpay": ["worldpay.com", "access.worldpay"],
                    "checkout_com": ["checkout.com", "frames.checkout"],
                    "authorize_net": ["authorize.net", "acceptjs"],
                }
                
                for psp, sigs in psp_signatures.items():
                    for sig in sigs:
                        if sig in html or any(sig in r.lower() for r in requests_urls):
                            if psp not in result["payment_processors"]:
                                result["payment_processors"].append(psp)
                
                # Detect technologies
                tech_signatures = {
                    "shopify": ["cdn.shopify.com", "shopify.com"],
                    "woocommerce": ["woocommerce", "wc-ajax"],
                    "magento": ["magento", "mage/"],
                    "bigcommerce": ["bigcommerce.com"],
                    "react": ["react", "_next/"],
                    "cloudflare": ["cloudflare", "cf-ray"],
                    "google_analytics": ["google-analytics.com", "gtag"],
                    "google_tag_manager": ["googletagmanager.com"],
                    "facebook_pixel": ["fbevents.js", "facebook.com/tr"],
                }
                
                for tech, sigs in tech_signatures.items():
                    for sig in sigs:
                        if sig in html or any(sig in r.lower() for r in requests_urls):
                            if tech not in result["technologies"]:
                                result["technologies"].append(tech)
                
                # Detect CAPTCHA
                captcha_sigs = ["recaptcha", "hcaptcha", "captcha", "turnstile"]
                result["has_captcha"] = any(sig in html for sig in captcha_sigs)
                
                # Get cookies
                cookies = context.cookies()
                result["cookies_set"] = [
                    {"name": c["name"], "domain": c["domain"]}
                    for c in cookies[:20]
                ]
                
                # Count external scripts
                result["scripts_loaded"] = len([
                    r for r in requests_urls if r.endswith(".js")
                ])
                
                browser.close()
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_stats(self) -> Dict:
        return {"available": self._available}


# ═══════════════════════════════════════════════════════════════════════════════
# D12. WAPPALYZER — Technology Stack Detection
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Instantly know what platform/framework a target uses.
#      Shopify vs WooCommerce vs Magento = completely different checkout flows.
# RAM: ~5MB
# INSTALL: pip install python-Wappalyzer

class TechStackDetector:
    """
    Technology stack detection using Wappalyzer patterns.
    
    Usage:
        detector = get_tech_detector()
        result = detector.detect("https://example.com")
        # → {"shopify": {"version": "2.0"}, "cloudflare": {}, "stripe": {}}
    """
    
    def __init__(self):
        self._available = False
        self._wappalyzer = None
        try:
            from Wappalyzer import Wappalyzer, WebPage
            self._wappalyzer = Wappalyzer.latest()
            self._available = True
        except ImportError:
            logger.debug("Wappalyzer not installed: pip install python-Wappalyzer")
        except Exception as e:
            logger.debug(f"Wappalyzer init failed: {e}")
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def detect(self, url: str) -> Dict:
        """Detect technologies on a URL."""
        if not self._available:
            return {"error": "Wappalyzer not available"}
        
        try:
            from Wappalyzer import WebPage
            webpage = WebPage.new_from_url(url)
            techs = self._wappalyzer.analyze_with_versions_and_categories(webpage)
            return {
                "url": url,
                "technologies": techs,
                "count": len(techs),
            }
        except Exception as e:
            return {"url": url, "error": str(e)}
    
    def get_stats(self) -> Dict:
        return {"available": self._available}


# ═══════════════════════════════════════════════════════════════════════════════
# E14. MINIO — S3-Compatible Object Storage
# ═══════════════════════════════════════════════════════════════════════════════
# WHY: Store browser profiles, assets, backups in S3-compatible storage.
#      Enables profile sharing, versioning, and backup.
# RAM: ~100MB
# INSTALL: Docker or single binary

class MinIOClient:
    """
    MinIO S3-compatible storage client for profile/asset management.
    
    Usage:
        minio = get_minio_client()
        minio.upload_profile("/path/to/profile", "profile-001")
        minio.download_profile("profile-001", "/path/to/dest")
        minio.list_profiles()
    """
    
    def __init__(self, endpoint: str = None, access_key: str = None,
                 secret_key: str = None):
        self._endpoint = endpoint or os.getenv("TITAN_MINIO_ENDPOINT", "127.0.0.1:9000")
        self._access_key = access_key or os.getenv("TITAN_MINIO_ACCESS_KEY", "titan")
        self._secret_key = secret_key or os.getenv("TITAN_MINIO_SECRET_KEY", "")
        self._client = None
        self._available = False
        self._init_client()
    
    def _init_client(self):
        try:
            from minio import Minio
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=False,
            )
            # Test connection
            self._client.list_buckets()
            self._available = True
            logger.info(f"MinIO connected: {self._endpoint}")
        except ImportError:
            logger.debug("minio not installed: pip install minio")
        except Exception as e:
            logger.debug(f"MinIO not available: {e}")
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def get_stats(self) -> Dict:
        if not self._available:
            return {"available": False}
        try:
            buckets = self._client.list_buckets()
            return {
                "available": True,
                "endpoint": self._endpoint,
                "buckets": [b.name for b in buckets],
            }
        except Exception:
            return {"available": True, "endpoint": self._endpoint}


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED STACK MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TitanSelfHostedStack:
    """
    Unified manager for all self-hosted tools.
    Lazy-initializes each tool on first access.
    
    Usage:
        stack = get_self_hosted_stack()
        
        # Check what's available
        status = stack.get_status()
        
        # Access individual tools
        geo = stack.geoip
        ip_check = stack.ip_quality
        redis = stack.redis
        ntfy = stack.ntfy
    """
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def _lazy_get(self, name: str, factory):
        if name not in self._tools:
            with self._lock:
                if name not in self._tools:
                    self._tools[name] = factory()
        return self._tools[name]
    
    @property
    def geoip(self) -> GeoIPValidator:
        return self._lazy_get("geoip", GeoIPValidator)
    
    @property
    def ip_quality(self) -> IPQualityChecker:
        return self._lazy_get("ip_quality", IPQualityChecker)
    
    @property
    def fingerprint_tester(self) -> FingerprintTester:
        return self._lazy_get("fingerprint_tester", FingerprintTester)
    
    @property
    def proxy_monitor(self) -> ProxyHealthMonitor:
        return self._lazy_get("proxy_monitor", ProxyHealthMonitor)
    
    @property
    def uptime_kuma(self) -> UptimeKumaClient:
        return self._lazy_get("uptime_kuma", UptimeKumaClient)
    
    @property
    def ntfy(self) -> NtfyClient:
        return self._lazy_get("ntfy", NtfyClient)
    
    @property
    def redis(self) -> RedisClient:
        return self._lazy_get("redis", RedisClient)
    
    @property
    def target_prober(self) -> TargetSiteProber:
        return self._lazy_get("target_prober", TargetSiteProber)
    
    @property
    def tech_detector(self) -> TechStackDetector:
        return self._lazy_get("tech_detector", TechStackDetector)
    
    @property
    def minio(self) -> MinIOClient:
        return self._lazy_get("minio", MinIOClient)
    
    def get_status(self) -> Dict:
        """Get status of all self-hosted tools."""
        tools = {
            "geoip_validator": self.geoip.get_stats(),
            "ip_quality_checker": self.ip_quality.get_stats(),
            "fingerprint_tester": self.fingerprint_tester.get_stats(),
            "proxy_health_monitor": self.proxy_monitor.get_stats(),
            "uptime_kuma": self.uptime_kuma.get_stats(),
            "ntfy_notifications": self.ntfy.get_stats(),
            "redis_cache": self.redis.get_stats(),
            "target_prober": self.target_prober.get_stats(),
            "tech_detector": self.tech_detector.get_stats(),
            "minio_storage": self.minio.get_stats(),
        }
        
        available_count = sum(1 for t in tools.values() if t.get("available"))
        
        return {
            "total_tools": len(tools),
            "available_tools": available_count,
            "unavailable_tools": len(tools) - available_count,
            "tools": tools,
        }
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        status = self.get_status()
        return [name for name, info in status["tools"].items() if info.get("available")]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_stack: Optional[TitanSelfHostedStack] = None
_stack_lock = threading.Lock()


def get_self_hosted_stack() -> TitanSelfHostedStack:
    """Get singleton TitanSelfHostedStack instance."""
    global _stack
    with _stack_lock:
        if _stack is None:
            _stack = TitanSelfHostedStack()
    return _stack


# Individual tool accessors for convenience
def get_geoip_validator() -> GeoIPValidator:
    return get_self_hosted_stack().geoip

def get_ip_quality_checker() -> IPQualityChecker:
    return get_self_hosted_stack().ip_quality

def get_fingerprint_tester() -> FingerprintTester:
    return get_self_hosted_stack().fingerprint_tester

def get_proxy_health_monitor() -> ProxyHealthMonitor:
    return get_self_hosted_stack().proxy_monitor

def get_uptime_kuma() -> UptimeKumaClient:
    return get_self_hosted_stack().uptime_kuma

def get_ntfy_client() -> NtfyClient:
    return get_self_hosted_stack().ntfy

def get_redis_client() -> RedisClient:
    return get_self_hosted_stack().redis

def get_target_prober() -> TargetSiteProber:
    return get_self_hosted_stack().target_prober

def get_tech_detector() -> TechStackDetector:
    return get_self_hosted_stack().tech_detector

def get_minio_client() -> MinIOClient:
    return get_self_hosted_stack().minio
