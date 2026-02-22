"""
LUCID EMPIRE v8.1-TITAN - Handover Protocol
============================================
The "Prepare -> Handover -> Execute" model.

Phase 1 (Genesis): Playwright runs headless, builds trust signals
Phase 2 (Freeze): Automation terminates, navigator.webdriver is naturally false
Phase 3 (Handover): Standard Firefox opens with grafted "Golden Profile"

AUTHORITY: Dva.12 | TITAN V8.1 FINAL
"""

import asyncio
import json
import os
import random
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class ProfileSpec:
    """Specification for a Golden Profile."""
    name: str
    timezone: str = "America/New_York"
    locale: str = "en_US.UTF-8"
    language: str = "en-US"
    
    # Hardware spoofing (for Hardware Shield)
    gpu_vendor: str = "Google Inc. (NVIDIA)"
    gpu_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    cpu_cores: int = 16
    cpu_model: str = "13th Gen Intel(R) Core(TM) i9-13900K"
    ram_gb: int = 64
    
    # Screen (consistent with common Windows configs)
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0
    
    # Location (for geo-consistency)
    geo_city: str = "New York"
    geo_state: str = "NY"
    geo_zip: str = "10001"
    geo_country: str = "US"
    geo_lat: float = 40.7128
    geo_lon: float = -74.0060
    
    # Aging
    aging_days: int = 90
    
    # Trust building
    warmup_sites: List[str] = field(default_factory=lambda: [
        "https://www.google.com",
        "https://www.youtube.com",
        "https://www.amazon.com",
        "https://www.facebook.com",
        "https://www.cnn.com",
        "https://weather.com",
        "https://www.reddit.com",
        "https://www.bing.com",
    ])


class HandoverProtocol:
    """
    Implements the Genesis -> Freeze -> Handover workflow.
    """
    
    LUCID_ROOT = Path("/opt/lucid-empire")
    PROFILES_DIR = LUCID_ROOT / "profiles"
    
    def __init__(self, profile_spec: ProfileSpec):
        self.spec = profile_spec
        self.profile_dir = self.PROFILES_DIR / profile_spec.name
        self.firefox_profile = self.profile_dir / "firefox_profile"
        self.chromium_profile = self.profile_dir / "chromium_profile"
        
    async def execute_genesis(
        self,
        warmup_duration_seconds: int = 180,
        headless: bool = True,
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Phase 1: THE GENESIS (The "Oven")
        
        Runs Playwright headless to:
        1. Visit high-trust sites
        2. Accept cookies
        3. Generate behavioral hash
        4. Build trust signals
        
        Returns trust metrics and profile path.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install firefox")
        
        def progress(msg: str, pct: int):
            if on_progress:
                on_progress(msg, pct)
            else:
                print(f"[GENESIS] {msg} ({pct}%)")
        
        progress("Initializing profile structure", 5)
        
        # Create profile directories
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.firefox_profile.mkdir(exist_ok=True)
        self.chromium_profile.mkdir(exist_ok=True)
        
        # Generate hardware config for Hardware Shield
        self._create_hardware_config()
        progress("Hardware configuration generated", 10)
        
        # Generate fake /proc files
        self._create_fake_proc_files()
        progress("System emulation files created", 15)
        
        # Set timezone and locale
        self._create_environment_files()
        progress("Environment configured", 20)
        
        # Run Playwright to build trust
        async with async_playwright() as p:
            progress("Launching headless Firefox", 25)
            
            browser = await p.firefox.launch(
                headless=headless,
            )
            
            # Create context with our profile settings
            context = await browser.new_context(
                viewport={"width": self.spec.screen_width, "height": self.spec.screen_height},
                locale=self.spec.language,
                timezone_id=self.spec.timezone,
                geolocation={"latitude": self.spec.geo_lat, "longitude": self.spec.geo_lon},
                permissions=["geolocation"],
                user_agent=self._generate_user_agent(),
            )
            
            page = await context.new_page()
            
            # Calculate time per site
            sites = self.spec.warmup_sites
            time_per_site = warmup_duration_seconds // len(sites)
            
            trust_metrics = {
                "sites_visited": [],
                "cookies_acquired": 0,
                "localStorage_entries": 0,
                "total_duration": 0,
            }
            
            # Visit each site
            start_time = time.time()
            for i, site in enumerate(sites):
                pct = 30 + int((i / len(sites)) * 60)
                progress(f"Building trust: {site}", pct)
                
                try:
                    await page.goto(site, timeout=30000)
                    
                    # Simulate human behavior
                    await self._simulate_human_behavior(page)
                    
                    # Accept cookies if dialog appears
                    await self._accept_cookies(page)
                    
                    # Dwell time
                    await asyncio.sleep(random.uniform(time_per_site * 0.8, time_per_site * 1.2))
                    
                    trust_metrics["sites_visited"].append({
                        "url": site,
                        "timestamp": datetime.now().isoformat(),
                    })
                    
                except Exception as e:
                    progress(f"Warning: {site} - {str(e)[:50]}", pct)
            
            trust_metrics["total_duration"] = time.time() - start_time
            
            # Get cookies
            cookies = await context.cookies()
            trust_metrics["cookies_acquired"] = len(cookies)
            
            progress("Extracting profile data", 92)
            
            # Save cookies to Firefox format
            await self._save_firefox_profile(context, cookies)
            
            progress("Profile grafted to Firefox format", 95)
            
            # Close browser - THIS IS THE FREEZE PHASE
            await browser.close()
            
        progress("Genesis complete. Navigator.webdriver is now FALSE.", 100)
        
        # Calculate trust score
        trust_score = self._calculate_trust_score(trust_metrics)
        trust_metrics["trust_score"] = trust_score
        
        # Save metrics
        metrics_path = self.profile_dir / "genesis_metrics.json"
        metrics_path.write_text(json.dumps(trust_metrics, indent=2))
        
        # Mark as active profile
        self._set_as_active()
        
        return trust_metrics
    
    def _create_hardware_config(self) -> None:
        """Create hardware.conf for the Hardware Shield."""
        config = f"""# LUCID Hardware Shield Configuration
# Generated: {datetime.now().isoformat()}
GPU_VENDOR={self.spec.gpu_vendor}
GPU_RENDERER={self.spec.gpu_renderer}
CPU_CORES={self.spec.cpu_cores}
CPU_MODEL={self.spec.cpu_model}
RAM_GB={self.spec.ram_gb}
SCREEN_WIDTH={self.spec.screen_width}
SCREEN_HEIGHT={self.spec.screen_height}
COLOR_DEPTH={self.spec.color_depth}
PIXEL_RATIO={self.spec.pixel_ratio}
"""
        (self.profile_dir / "hardware.conf").write_text(config)
    
    def _create_fake_proc_files(self) -> None:
        """Create fake /proc/cpuinfo and /proc/meminfo."""
        
        # Fake cpuinfo (Intel i9-13900K style)
        cpuinfo_lines = []
        for i in range(self.spec.cpu_cores):
            cpuinfo_lines.extend([
                f"processor\t: {i}",
                "vendor_id\t: GenuineIntel",
                "cpu family\t: 6",
                "model\t\t: 183",
                f"model name\t: {self.spec.cpu_model}",
                "stepping\t: 1",
                "microcode\t: 0x11e",
                "cpu MHz\t\t: 5800.000",
                "cache size\t: 36864 KB",
                "physical id\t: 0",
                f"siblings\t: {self.spec.cpu_cores}",
                f"core id\t\t: {i % (self.spec.cpu_cores // 2)}",
                f"cpu cores\t: {self.spec.cpu_cores // 2}",
                "apicid\t\t: 0",
                "initial apicid\t: 0",
                "fpu\t\t: yes",
                "fpu_exception\t: yes",
                "cpuid level\t: 32",
                "wp\t\t: yes",
                "flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf tsc_known_freq pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb invpcid_single ssbd ibrs ibpb stibp ibrs_enhanced tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid rdseed adx smap clflushopt clwb intel_pt sha_ni xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp hwp_pkg_req avx_vnni umip pks gfni vaes vpclmulqdq rdpid movdiri movdir64b fsrm md_clear serialize pconfig arch_lbr amx_bf16 avx512f avx512dq avx512_ifma avx512cd avx512bw avx512vl avx512_bf16 avx512vbmi avx512_vbmi2 avx512_vnni avx512_bitalg avx512_vpopcntdq cldemote flush_l1d arch_capabilities",
                "vmx flags\t: vnmi preemption_timer posted_intr invvpid ept_x_only ept_ad ept_1gb flexpriority apicv tsc_offset vtpr mtf vapic ept vpid unrestricted_guest vapic_reg vid ple shadow_vmcs ept_mode_based_exec tsc_scaling usr_wait_pause",
                "bugs\t\t:",
                "bogomips\t: 11600.00",
                "clflush size\t: 64",
                "cache_alignment\t: 64",
                "address sizes\t: 46 bits physical, 48 bits virtual",
                "power management:",
                "",
            ])
        (self.profile_dir / "cpuinfo").write_text("\n".join(cpuinfo_lines))
        
        # Fake meminfo
        ram_kb = self.spec.ram_gb * 1024 * 1024
        meminfo = f"""MemTotal:       {ram_kb} kB
MemFree:        {ram_kb // 3} kB
MemAvailable:   {int(ram_kb * 0.8)} kB
Buffers:        {ram_kb // 20} kB
Cached:         {ram_kb // 4} kB
SwapCached:     0 kB
Active:         {ram_kb // 3} kB
Inactive:       {ram_kb // 4} kB
Active(anon):   {ram_kb // 5} kB
Inactive(anon): {ram_kb // 10} kB
Active(file):   {ram_kb // 8} kB
Inactive(file): {ram_kb // 8} kB
Unevictable:    0 kB
Mlocked:        0 kB
SwapTotal:      0 kB
SwapFree:       0 kB
Dirty:          0 kB
Writeback:      0 kB
AnonPages:      {ram_kb // 4} kB
Mapped:         {ram_kb // 10} kB
Shmem:          {ram_kb // 40} kB
KReclaimable:   {ram_kb // 16} kB
Slab:           {ram_kb // 12} kB
SReclaimable:   {ram_kb // 16} kB
SUnreclaim:     {ram_kb // 24} kB
KernelStack:    16384 kB
PageTables:     {ram_kb // 200} kB
NFS_Unstable:   0 kB
Bounce:         0 kB
WritebackTmp:   0 kB
CommitLimit:    {ram_kb // 2} kB
Committed_AS:   {ram_kb // 3} kB
VmallocTotal:   34359738367 kB
VmallocUsed:    {ram_kb // 100} kB
VmallocChunk:   0 kB
Percpu:         8192 kB
HardwareCorrupted: 0 kB
AnonHugePages:  0 kB
ShmemHugePages: 0 kB
ShmemPmdMapped: 0 kB
FileHugePages:  0 kB
FilePmdMapped:  0 kB
HugePages_Total: 0
HugePages_Free: 0
HugePages_Rsvd: 0
HugePages_Surp: 0
Hugepagesize:   2048 kB
Hugetlb:        0 kB
DirectMap4k:    {ram_kb // 20} kB
DirectMap2M:    {ram_kb // 2} kB
DirectMap1G:    {ram_kb // 2} kB
"""
        (self.profile_dir / "meminfo").write_text(meminfo)
    
    def _create_environment_files(self) -> None:
        """Create timezone, locale, and language files."""
        (self.profile_dir / "timezone").write_text(self.spec.timezone)
        (self.profile_dir / "locale").write_text(self.spec.locale)
        (self.profile_dir / "language").write_text(self.spec.language)
        
        # Geo data for consistency checking
        geo_data = {
            "city": self.spec.geo_city,
            "state": self.spec.geo_state,
            "zip": self.spec.geo_zip,
            "country": self.spec.geo_country,
            "lat": self.spec.geo_lat,
            "lon": self.spec.geo_lon,
        }
        (self.profile_dir / "geolocation.json").write_text(json.dumps(geo_data, indent=2))
    
    def _generate_user_agent(self) -> str:
        """Generate a realistic Windows user agent."""
        # Firefox ESR on Windows 11 (most common)
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
    
    async def _simulate_human_behavior(self, page: Page) -> None:
        """Simulate human-like behavior on page."""
        try:
            # Random scrolling
            for _ in range(random.randint(2, 5)):
                await page.mouse.wheel(0, random.randint(100, 500))
                await asyncio.sleep(random.uniform(0.3, 1.5))
            
            # Random mouse movements
            for _ in range(random.randint(3, 8)):
                x = random.randint(100, self.spec.screen_width - 100)
                y = random.randint(100, self.spec.screen_height - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
        except Exception:
            pass  # Ignore interaction errors
    
    async def _accept_cookies(self, page: Page) -> None:
        """Try to accept cookie consent dialogs."""
        accept_selectors = [
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('Accept Cookies')",
            "button:has-text('I Accept')",
            "button:has-text('OK')",
            "button:has-text('Agree')",
            "[data-testid='accept-cookies']",
            "#accept-cookies",
            ".accept-cookies",
            "[class*='cookie'] button",
        ]
        
        for selector in accept_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                continue
    
    async def _save_firefox_profile(self, context: BrowserContext, cookies: List[Dict]) -> None:
        """Convert Playwright session to Firefox profile format."""
        
        # Create Firefox profile structure
        (self.firefox_profile / "prefs.js").write_text(self._generate_prefs_js())
        
        # Create places.sqlite (history)
        await self._create_places_db()
        
        # Create cookies.sqlite
        self._create_cookies_db(cookies)
        
        # Create formhistory.sqlite (for autofill trust)
        self._create_formhistory_db()
        
        # Create times.json (profile aging)
        self._create_times_json()
    
    def _generate_prefs_js(self) -> str:
        """Generate Firefox prefs.js with hardened settings."""
        prefs = f'''// LUCID EMPIRE Generated Profile
// DO NOT EDIT - Managed by Genesis Engine

user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.page", 1);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
user_pref("privacy.trackingprotection.enabled", false);
user_pref("network.cookie.cookieBehavior", 0);
user_pref("dom.webnotifications.enabled", false);
user_pref("geo.enabled", true);
user_pref("intl.accept_languages", "{self.spec.language}");
user_pref("javascript.options.wasm", true);
user_pref("webgl.disabled", false);
user_pref("media.peerconnection.enabled", false);
user_pref("dom.battery.enabled", false);
user_pref("device.sensors.enabled", false);
user_pref("privacy.resistFingerprinting", false);
user_pref("general.smoothScroll", true);
'''
        return prefs
    
    async def _create_places_db(self) -> None:
        """Create Firefox places.sqlite with aged history."""
        from .genesis_engine import GenesisEngine
        
        # Use existing GenesisEngine for history generation
        engine = GenesisEngine(self.firefox_profile)
        history = engine.generate_history(
            aging_days=self.spec.aging_days,
            entries_count=500,
        )
        
        db_path = self.firefox_profile / "places.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS moz_places (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                rev_host TEXT,
                visit_count INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0,
                typed INTEGER DEFAULT 0,
                frecency INTEGER DEFAULT -1,
                last_visit_date INTEGER,
                guid TEXT
            );
            CREATE TABLE IF NOT EXISTS moz_historyvisits (
                id INTEGER PRIMARY KEY,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER
            );
            CREATE INDEX IF NOT EXISTS moz_places_url_index ON moz_places(url);
            CREATE INDEX IF NOT EXISTS moz_historyvisits_placeid ON moz_historyvisits(place_id);
        """)
        
        for i, entry in enumerate(history):
            url = entry["url"]
            domain = entry["domain"]
            rev_host = ".".join(reversed(domain.split("."))) + "."
            
            cursor.execute("""
                INSERT INTO moz_places (id, url, title, rev_host, visit_count, typed, frecency, last_visit_date, guid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i + 1,
                url,
                entry["title"],
                rev_host,
                entry["visit_count"],
                entry["typed"],
                random.randint(100, 10000),
                entry["visit_time_unix"],
                f"genesis_{i:08d}"
            ))
            
            cursor.execute("""
                INSERT INTO moz_historyvisits (place_id, visit_date, visit_type, session)
                VALUES (?, ?, ?, ?)
            """, (
                i + 1,
                entry["visit_time_unix"],
                1,
                random.randint(1, 100)
            ))
        
        conn.commit()
        conn.close()
    
    def _create_cookies_db(self, playwright_cookies: List[Dict]) -> None:
        """Create Firefox cookies.sqlite from Playwright cookies."""
        from .genesis_engine import GenesisEngine
        
        # Get additional aged cookies from GenesisEngine
        engine = GenesisEngine(self.firefox_profile)
        aged_cookies = engine.generate_cookies(aging_days=self.spec.aging_days)
        
        db_path = self.firefox_profile / "cookies.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_cookies (
                id INTEGER PRIMARY KEY,
                originAttributes TEXT NOT NULL DEFAULT '',
                name TEXT,
                value TEXT,
                host TEXT,
                path TEXT,
                expiry INTEGER,
                lastAccessed INTEGER,
                creationTime INTEGER,
                isSecure INTEGER,
                isHttpOnly INTEGER,
                inBrowserElement INTEGER DEFAULT 0,
                sameSite INTEGER DEFAULT 0,
                rawSameSite INTEGER DEFAULT 0,
                schemeMap INTEGER DEFAULT 0
            )
        """)
        
        cookie_id = 1
        
        # Insert Playwright cookies (fresh from warmup)
        for cookie in playwright_cookies:
            cursor.execute("""
                INSERT INTO moz_cookies (id, name, value, host, path, expiry, lastAccessed, creationTime, isSecure, isHttpOnly)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cookie_id,
                cookie.get("name", ""),
                cookie.get("value", ""),
                cookie.get("domain", ""),
                cookie.get("path", "/"),
                int(cookie.get("expires", 0)),
                int(time.time() * 1000000),
                int(time.time() * 1000000),
                1 if cookie.get("secure", False) else 0,
                1 if cookie.get("httpOnly", False) else 0,
            ))
            cookie_id += 1
        
        # Insert aged cookies
        for cookie in aged_cookies:
            cursor.execute("""
                INSERT INTO moz_cookies (id, name, value, host, path, expiry, lastAccessed, creationTime, isSecure, isHttpOnly)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cookie_id,
                cookie["name"],
                cookie["value"],
                cookie["host"],
                cookie["path"],
                cookie["expiry"],
                cookie["last_access"],
                cookie["creation_time"],
                1 if cookie["secure"] else 0,
                1 if cookie["http_only"] else 0,
            ))
            cookie_id += 1
        
        conn.commit()
        conn.close()
    
    def _create_formhistory_db(self) -> None:
        """Create formhistory.sqlite for autofill trust."""
        db_path = self.firefox_profile / "formhistory.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_formhistory (
                id INTEGER PRIMARY KEY,
                fieldname TEXT NOT NULL,
                value TEXT NOT NULL,
                timesUsed INTEGER,
                firstUsed INTEGER,
                lastUsed INTEGER,
                guid TEXT
            )
        """)
        
        # Common form fields with aging
        base_time = int(time.time() * 1000000)
        aging_us = self.spec.aging_days * 24 * 60 * 60 * 1000000
        
        common_fields = [
            ("searchbar-history", "amazon product reviews"),
            ("searchbar-history", "best buy laptop deals"),
            ("searchbar-history", "weather forecast"),
        ]
        
        for i, (field, value) in enumerate(common_fields):
            cursor.execute("""
                INSERT INTO moz_formhistory (id, fieldname, value, timesUsed, firstUsed, lastUsed, guid)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                i + 1,
                field,
                value,
                random.randint(1, 10),
                base_time - aging_us + random.randint(0, aging_us),
                base_time - random.randint(0, aging_us // 4),
                f"form_{i:08d}"
            ))
        
        conn.commit()
        conn.close()
    
    def _create_times_json(self) -> None:
        """Create times.json for profile creation timestamp."""
        creation_time = datetime.now() - timedelta(days=self.spec.aging_days)
        times = {
            "created": int(creation_time.timestamp() * 1000),
            "firstUse": int(creation_time.timestamp() * 1000),
        }
        (self.firefox_profile / "times.json").write_text(json.dumps(times))
    
    def _calculate_trust_score(self, metrics: Dict) -> int:
        """Calculate a 0-100 trust score based on metrics."""
        score = 0
        
        # Sites visited (max 30 points)
        sites_count = len(metrics.get("sites_visited", []))
        score += min(30, sites_count * 4)
        
        # Cookies acquired (max 30 points)
        cookies = metrics.get("cookies_acquired", 0)
        score += min(30, cookies // 2)
        
        # Duration (max 20 points)
        duration = metrics.get("total_duration", 0)
        score += min(20, int(duration / 10))
        
        # Profile aging (max 20 points)
        score += min(20, self.spec.aging_days // 5)
        
        return min(100, score)
    
    def _set_as_active(self) -> None:
        """Set this profile as the active profile."""
        active_link = self.PROFILES_DIR / "active"
        if active_link.is_symlink():
            active_link.unlink()
        elif active_link.exists():
            shutil.rmtree(active_link)
        active_link.symlink_to(self.profile_dir)
    
    def launch_browser(self, browser: str = "firefox", url: str = "") -> subprocess.Popen:
        """
        Phase 3: THE HANDOVER
        
        Launch the standard browser with the grafted profile.
        Navigator.webdriver is naturally FALSE because we're not using automation.
        """
        if browser == "firefox":
            cmd = ["/opt/lucid-empire/bin/lucid-firefox", "-p", self.spec.name]
        elif browser == "chromium":
            cmd = ["/opt/lucid-empire/bin/lucid-chromium", "-p", self.spec.name]
        else:
            raise ValueError(f"Unknown browser: {browser}")
        
        if url:
            cmd.append(url)
        
        return subprocess.Popen(cmd)


async def run_genesis(profile_spec: ProfileSpec, **kwargs) -> Dict[str, Any]:
    """Convenience function to run the Genesis phase."""
    protocol = HandoverProtocol(profile_spec)
    return await protocol.execute_genesis(**kwargs)


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID Genesis Engine - Profile Handover Protocol")
    parser.add_argument("--name", required=True, help="Profile name")
    parser.add_argument("--timezone", default="America/New_York", help="Timezone")
    parser.add_argument("--locale", default="en_US.UTF-8", help="Locale")
    parser.add_argument("--city", default="New York", help="Geo city")
    parser.add_argument("--zip", default="10001", help="Zip code")
    parser.add_argument("--aging-days", type=int, default=90, help="Profile age in days")
    parser.add_argument("--warmup-time", type=int, default=180, help="Warmup duration in seconds")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--visible", action="store_true", help="Show browser during warmup")
    
    args = parser.parse_args()
    
    spec = ProfileSpec(
        name=args.name,
        timezone=args.timezone,
        locale=args.locale,
        geo_city=args.city,
        geo_zip=args.zip,
        aging_days=args.aging_days,
    )
    
    metrics = asyncio.run(run_genesis(
        spec,
        warmup_duration_seconds=args.warmup_time,
        headless=not args.visible,
    ))
    
    print(f"\n[GENESIS COMPLETE]")
    print(f"  Trust Score: {metrics['trust_score']}/100")
    print(f"  Sites Visited: {len(metrics['sites_visited'])}")
    print(f"  Cookies Acquired: {metrics['cookies_acquired']}")
    print(f"\nLaunch browser: lucid-firefox -p {args.name}")
