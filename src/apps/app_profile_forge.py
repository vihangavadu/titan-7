#!/usr/bin/env python3
"""
TITAN V8.2 PROFILE FORGE — Identity + Chrome Profile Building
==============================================================
Focused app for persona creation and browser profile forging.

3 tabs:
  1. IDENTITY — Name, email, phone, address, card details
  2. FORGE — Genesis engine, purchase history, IndexedDB, realism scoring
  3. PROFILES — Browse/manage generated profiles
"""

import sys
import os
import json
import random
import hashlib
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QFrame, QComboBox, QProgressBar, QMessageBox,
    QScrollArea, QPlainTextEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

ACCENT = "#00d4ff"
BG = "#0a0e17"
BG_CARD = "#111827"
TEXT = "#e2e8f0"
TEXT2 = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
ORANGE = "#f97316"

try:
    from titan_theme import apply_titan_theme, make_tab_style
    THEME_OK = True
except ImportError:
    THEME_OK = False

# Core imports (graceful)
try:
    from genesis_core import GenesisEngine, ProfileConfig
    GENESIS_OK = True
except ImportError:
    GENESIS_OK = False

try:
    from purchase_history_engine import PurchaseHistoryEngine, CardHolderData
    PURCHASE_OK = True
except ImportError:
    PURCHASE_OK = False

try:
    from advanced_profile_generator import AdvancedProfileGenerator
    APG_OK = True
except ImportError:
    APG_OK = False

try:
    from persona_enrichment_engine import PersonaEnrichmentEngine
    PERSONA_OK = True
except ImportError:
    PERSONA_OK = False

try:
    from indexeddb_lsng_synthesis import IndexedDBShardSynthesizer
    IDB_OK = True
except ImportError:
    IDB_OK = False

try:
    from first_session_bias_eliminator import FirstSessionBiasEliminator
    FSB_OK = True
except ImportError:
    FSB_OK = False

try:
    from forensic_synthesis_engine import Cache2Synthesizer
    CACHE_OK = True
except ImportError:
    CACHE_OK = False

try:
    from font_sanitizer import FontSanitizer
    FONT_OK = True
except ImportError:
    FONT_OK = False

try:
    from audio_hardener import AudioHardener
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

try:
    from profile_realism_engine import ProfileRealismEngine
    REALISM_OK = True
except ImportError:
    REALISM_OK = False

try:
    from chromium_commerce_injector import inject_golden_chain
    CHROME_COMMERCE_OK = True
except ImportError:
    CHROME_COMMERCE_OK = False

try:
    from titan_session import get_session, update_session
    SESSION_OK = True
except ImportError:
    SESSION_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN PERSONA GENERATOR (works without core modules)
# ═══════════════════════════════════════════════════════════════════════════════
_FIRST_NAMES_M = ["James","Robert","John","Michael","David","William","Richard","Joseph","Thomas","Christopher",
    "Daniel","Matthew","Anthony","Mark","Steven","Andrew","Paul","Joshua","Kenneth","Kevin"]
_FIRST_NAMES_F = ["Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan","Jessica","Sarah","Karen",
    "Lisa","Nancy","Betty","Margaret","Sandra","Ashley","Dorothy","Kimberly","Emily","Donna"]
_LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
    "Anderson","Taylor","Thomas","Moore","Jackson","Martin","Lee","Thompson","White","Harris",
    "Clark","Lewis","Robinson","Walker","Young","Allen","King","Wright","Scott","Hill"]
_STREETS = ["Oak","Maple","Cedar","Pine","Elm","Washington","Park","Lake","Hill","Forest",
    "River","Spring","Valley","Sunset","Highland","Meadow","Cherry","Willow","Birch","Walnut"]
_STREET_TYPES = ["St","Ave","Dr","Ln","Blvd","Ct","Way","Rd","Pl","Cir"]
_CITIES_STATES_ZIPS = [
    ("New York","NY","10001"),("Los Angeles","CA","90001"),("Chicago","IL","60601"),
    ("Houston","TX","77001"),("Phoenix","AZ","85001"),("Philadelphia","PA","19101"),
    ("San Antonio","TX","78201"),("San Diego","CA","92101"),("Dallas","TX","75201"),
    ("Austin","TX","78701"),("Jacksonville","FL","32099"),("Columbus","OH","43085"),
    ("Charlotte","NC","28201"),("Indianapolis","IN","46201"),("Denver","CO","80201"),
    ("Seattle","WA","98101"),("Nashville","TN","37201"),("Portland","OR","97201"),
    ("Las Vegas","NV","89101"),("Atlanta","GA","30301"),("Miami","FL","33101"),
    ("Tampa","FL","33601"),("Minneapolis","MN","55401"),("Raleigh","NC","27601"),
]
_EMAIL_DOMAINS = ["gmail.com","yahoo.com","outlook.com","icloud.com","protonmail.com","hotmail.com"]
_CARD_BINS = {
    "visa": ["4532","4556","4916","4929","4485","4716"],
    "mastercard": ["5425","5399","5168","5495","5307","5211"],
    "amex": ["3782","3714","3787","3400","3700"],
    "discover": ["6011","6445","6500","6559"],
}

def _luhn_checksum(partial):
    digits = [int(d) for d in partial]
    odd_sum = sum(digits[-1::-2])
    even_sum = sum(sum(divmod(2 * d, 10)) for d in digits[-2::-2])
    return (odd_sum + even_sum) % 10

def _generate_card_number(network="visa"):
    bins = _CARD_BINS.get(network, _CARD_BINS["visa"])
    prefix = random.choice(bins)
    length = 15 if network == "amex" else 16
    body = prefix + "".join(str(random.randint(0, 9)) for _ in range(length - len(prefix) - 1))
    check = (10 - _luhn_checksum(body + "0")) % 10
    return body + str(check)

def generate_persona():
    gender = random.choice(["M", "F"])
    first = random.choice(_FIRST_NAMES_M if gender == "M" else _FIRST_NAMES_F)
    last = random.choice(_LAST_NAMES)
    city, state, zipcode = random.choice(_CITIES_STATES_ZIPS)
    street_num = random.randint(100, 9999)
    street = f"{street_num} {random.choice(_STREETS)} {random.choice(_STREET_TYPES)}"
    email_user = f"{first.lower()}.{last.lower()}{random.randint(1,99)}"
    email = f"{email_user}@{random.choice(_EMAIL_DOMAINS)}"
    phone = f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
    network = random.choice(["visa", "mastercard"])
    card = _generate_card_number(network)
    exp_month = random.randint(1, 12)
    exp_year = random.randint(26, 29)
    return {
        "name": f"{first} {last}", "email": email, "phone": phone,
        "street": street, "city": city, "state": state, "zip": zipcode,
        "card_number": card, "card_last4": card[-4:], "card_network": network,
        "card_exp": f"{exp_month:02d}/{exp_year}", "card_cvv": str(random.randint(100, 999)),
        "gender": gender,
    }

# V8.3: AI detection vector sanitization
try:
    from ai_intelligence_engine import (
        validate_fingerprint_coherence, validate_identity_graph,
        plan_session_rhythm, generate_navigation_path, audit_profile,
    )
    AI_V83_OK = True
except ImportError:
    AI_V83_OK = False

try:
    from chromium_cookie_engine import OblivionForgeEngine, BrowserType, ChromeCryptoEngine, HybridInjector, LevelDBForger, CacheSurgeon
    COOKIE_ENGINE_OK = True
except ImportError:
    COOKIE_ENGINE_OK = False

try:
    from leveldb_writer import LevelDBWriter
    LEVELDB_OK = True
except ImportError:
    LEVELDB_OK = False


class ForgeWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop_flag = __import__('threading').Event()

    def stop(self):
        """V8.3 FIX #2: Signal worker to stop cleanly."""
        self._stop_flag.set()

    def _fallback_forge(self):
        """Built-in forge when GenesisEngine is not available. Creates a real local profile directory."""
        self.progress.emit(5, "Fallback forge: creating local profile...")
        profile_id = str(uuid.uuid4())[:12]
        profile_dir = Path("/opt/titan/profiles") / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "Default").mkdir(exist_ok=True)

        self.progress.emit(15, "Generating persona metadata...")
        target = self.config.get("target", "amazon.com")
        age_days = self.config.get("age_days", 90)
        name = self.config.get("name", "") or generate_persona()["name"]

        self.progress.emit(30, "Building browser fingerprint...")
        ua_templates = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12{v}.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12{v}.0.0.0 Safari/537.36",
        ]
        chrome_ver = random.randint(0, 5)
        user_agent = random.choice(ua_templates).replace("{v}", str(chrome_ver))
        screen_res = random.choice(["1920x1080", "2560x1440", "1680x1050", "1440x900", "3840x2160"])
        platform = random.choice(["Win32", "MacIntel"])
        tz = random.choice(["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"])
        webgl = random.choice(["ANGLE (NVIDIA GeForce RTX 3070)", "ANGLE (AMD Radeon RX 6800)", "ANGLE (Intel Iris Xe)", "Apple GPU"])
        hw_conc = random.choice([8, 12, 16, 24])
        langs = random.choice(["en-US,en", "en-US", "en-GB,en"])

        if self._stop_flag.is_set():
            self.finished.emit({"success": False, "error": "Cancelled"})
            return

        self.progress.emit(45, "Generating browsing history artifacts...")
        now = datetime.now()
        history = []
        for i in range(random.randint(30, 80)):
            days_ago = random.randint(0, age_days)
            ts = (now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()
            sites = [target, "google.com", "youtube.com", "reddit.com", "wikipedia.org",
                     "stackoverflow.com", "github.com", "amazon.com", "twitter.com", "linkedin.com"]
            site = random.choice(sites)
            history.append({"url": f"https://www.{site}/{''.join(random.choices('abcdefghijklmnop', k=8))}", "ts": ts, "title": f"Page on {site}"})

        self.progress.emit(60, "Building cookie jar...")
        cookies = []
        for site in set(h["url"].split("/")[2] for h in history[:20]):
            cookies.append({"domain": site, "name": "_ga", "value": f"GA1.2.{random.randint(100000,999999)}.{int(now.timestamp()) - random.randint(0, age_days*86400)}", "httpOnly": False, "secure": True})
            cookies.append({"domain": site, "name": "_gid", "value": f"GA1.2.{random.randint(100000,999999)}.{int(now.timestamp())}", "httpOnly": False, "secure": True})

        self.progress.emit(75, "Writing profile artifacts...")
        # Compute quality score based on completeness
        fields_filled = sum(1 for k in ["name","email","phone","street","city","state","zip","card_last4"] if self.config.get(k))
        quality_score = min(95, 40 + fields_filled * 5 + min(len(history), 50) // 2 + len(cookies) // 2)

        meta = {
            "profile_id": profile_id,
            "target": target,
            "persona": {
                "name": name,
                "email": self.config.get("email", ""),
                "phone": self.config.get("phone", ""),
                "address": {
                    "street": self.config.get("street", ""),
                    "city": self.config.get("city", ""),
                    "state": self.config.get("state", ""),
                    "zip": self.config.get("zip", ""),
                },
                "card_network": self.config.get("card_network", "visa"),
                "card_last4": self.config.get("card_last4", ""),
                "card_exp": self.config.get("card_exp", ""),
            },
            "fingerprint": {
                "user_agent": user_agent,
                "screen_resolution": screen_res,
                "platform": platform,
                "timezone": tz,
                "webgl_renderer": webgl,
                "hardware_concurrency": hw_conc,
                "languages": langs,
            },
            "age_days": age_days,
            "quality_score": quality_score,
            "history_count": len(history),
            "cookie_count": len(cookies),
            "created": now.isoformat(),
            "forge_engine": "builtin-v8.3",
        }

        (profile_dir / "titan_meta.json").write_text(json.dumps(meta, indent=2))
        (profile_dir / "Default" / "history.json").write_text(json.dumps(history, indent=2))
        (profile_dir / "Default" / "cookies.json").write_text(json.dumps(cookies, indent=2))
        (profile_dir / "Default" / "fingerprint.json").write_text(json.dumps(meta["fingerprint"], indent=2))

        self.progress.emit(95, f"Profile forged locally — Quality: {quality_score}/100")
        self.progress.emit(100, "Done")
        return {
            "success": True,
            "profile_path": str(profile_dir),
            "profile_id": profile_id,
            "quality_score": quality_score,
            "layers_applied": 4,
            "v83_fp_coherence": None,
            "v83_fp_issues": [],
            "v83_id_plausible": None,
            "v83_id_anomalies": [],
        }

    def run(self):
        result = {"success": False, "error": "Genesis not available"}
        if not GENESIS_OK:
            result = self._fallback_forge()
            if result:
                self.finished.emit(result)
            else:
                self.finished.emit({"success": False, "error": "Fallback forge failed"})
            return
        try:
            self.progress.emit(5, "Initializing Genesis Engine...")
            engine = GenesisEngine()

            self.progress.emit(10, "Building profile config...")
            pc = ProfileConfig(
                target=self.config.get("target", "amazon.com"),
                persona_name=self.config.get("name", ""),
                persona_email=self.config.get("email", ""),
                age_days=self.config.get("age_days", 90),
            )

            self.progress.emit(20, "Forging browser profile...")
            profile = engine.generate(pc)
            profile_path = str(getattr(profile, 'path', ''))

            self.progress.emit(35, "Injecting purchase history...")
            if PURCHASE_OK and self.config.get("name"):
                try:
                    name_parts = self.config["name"].split()
                    ch = CardHolderData(
                        full_name=self.config.get("name", ""),
                        first_name=name_parts[0] if name_parts else "",
                        last_name=name_parts[-1] if len(name_parts) > 1 else "",
                        card_last_four=self.config.get("card_last4", "0000"),
                        card_network=self.config.get("card_network", "visa"),
                        card_exp_display=self.config.get("card_exp", "12/27"),
                        billing_address=self.config.get("street", ""),
                        billing_city=self.config.get("city", ""),
                        billing_state=self.config.get("state", ""),
                        billing_zip=self.config.get("zip", ""),
                        email=self.config.get("email", ""),
                        phone=self.config.get("phone", ""),
                    )
                    phe = PurchaseHistoryEngine()
                    phe.inject(profile_path, ch, num_purchases=random.randint(5, 12),
                               age_days=self.config.get("age_days", 90))
                except Exception as e:
                    self.progress.emit(37, f"Purchase history: {e}")

            if self._stop_flag.is_set():
                self.finished.emit({"success": False, "error": "Cancelled"})
                return

            self.progress.emit(45, "Synthesizing IndexedDB shards...")
            if IDB_OK:
                try:
                    idb = IndexedDBShardSynthesizer()
                    idb.synthesize(profile_path, target=self.config.get("target", ""), age_days=self.config.get("age_days", 90))
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"IDB synthesis failed: {e}", exc_info=True)

            if self._stop_flag.is_set():
                self.finished.emit({"success": False, "error": "Cancelled"})
                return

            self.progress.emit(55, "Eliminating first-session bias...")
            if FSB_OK:
                try:
                    FirstSessionBiasEliminator().eliminate(profile_path)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"FSB elimination failed: {e}", exc_info=True)

            self.progress.emit(60, "Injecting Chrome commerce funnel...")
            if CHROME_COMMERCE_OK and profile_path:
                try:
                    history_db = os.path.join(profile_path, "Default", "History")
                    if os.path.exists(history_db):
                        target = self.config.get("target", "amazon.com")
                        inject_golden_chain(history_db, f"https://{target}", f"ORD-{random.randint(10000, 99999)}")
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Commerce injection failed: {e}", exc_info=True)

            self.progress.emit(68, "Generating forensic cache mass...")
            if CACHE_OK:
                try:
                    Cache2Synthesizer().synthesize(profile_path, target_mb=self.config.get("storage_mb", 500))
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Cache synthesis failed: {e}", exc_info=True)

            self.progress.emit(78, "Applying fingerprint hardening...")
            if FONT_OK:
                try:
                    FontSanitizer().sanitize(profile_path)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Font sanitizer failed: {e}", exc_info=True)
            if AUDIO_OK:
                try:
                    AudioHardener().harden(profile_path)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Audio hardener failed: {e}", exc_info=True)

            self.progress.emit(88, "Running realism analysis...")
            quality_score = 0
            if REALISM_OK:
                try:
                    score_result = ProfileRealismEngine().score(profile_path)
                    quality_score = getattr(score_result, 'score', 0) if hasattr(score_result, 'score') else 75
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Realism scoring failed: {e}", exc_info=True)
                    quality_score = 70

            # V8.3: AI fingerprint coherence + identity graph validation
            fp_coherence = None
            id_graph = None
            if AI_V83_OK:
                try:
                    self.progress.emit(90, "V8.3: Validating fingerprint coherence...")
                    fp_config = {
                        "user_agent": self.config.get("user_agent", ""),
                        "webgl_renderer": self.config.get("webgl_renderer", ""),
                        "hardware_concurrency": self.config.get("hw_concurrency", 16),
                        "screen_resolution": self.config.get("screen_res", "1920x1080"),
                        "timezone": self.config.get("timezone", ""),
                        "locale": self.config.get("locale", "en-US"),
                        "platform": self.config.get("platform", "Win32"),
                    }
                    fp_coherence = validate_fingerprint_coherence(fp_config)
                    if fp_coherence and fp_coherence.ai_powered:
                        quality_score = int(quality_score * 0.6 + fp_coherence.score * 0.4)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"FP coherence check failed: {e}", exc_info=True)

                try:
                    self.progress.emit(93, "V8.3: Validating identity graph...")
                    persona = {
                        "name": self.config.get("name", ""),
                        "email": self.config.get("email", ""),
                        "phone": self.config.get("phone", ""),
                        "street": self.config.get("street", ""),
                        "city": self.config.get("city", ""),
                        "state": self.config.get("state", ""),
                        "zip": self.config.get("zip", ""),
                        "card_bin": self.config.get("card_bin", ""),
                        "card_network": self.config.get("card_network", ""),
                    }
                    id_graph = validate_identity_graph(persona)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Identity graph check failed: {e}", exc_info=True)

            self.progress.emit(97, "Finalizing...")
            result = {
                "success": True,
                "profile_path": profile_path,
                "profile_id": str(getattr(profile, 'uuid', '')),
                "quality_score": quality_score,
                "layers_applied": sum([PURCHASE_OK, IDB_OK, FSB_OK, CHROME_COMMERCE_OK, CACHE_OK, FONT_OK, AUDIO_OK, REALISM_OK]),
                "v83_fp_coherence": fp_coherence.score if fp_coherence and fp_coherence.ai_powered else None,
                "v83_fp_issues": fp_coherence.mismatches if fp_coherence and fp_coherence.ai_powered else [],
                "v83_id_plausible": id_graph.plausible if id_graph and id_graph.ai_powered else None,
                "v83_id_anomalies": id_graph.anomalies if id_graph and id_graph.ai_powered else [],
            }
            self.progress.emit(100, f"Profile forged — Quality: {quality_score}/100")
        except Exception as e:
            result = {"success": False, "error": str(e)}
        self.finished.emit(result)


class TitanProfileForge(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()

    def apply_theme(self):
        if THEME_OK:
            apply_titan_theme(self, ACCENT)
            self.tabs.setStyleSheet(make_tab_style(ACCENT))
        else:
            self.setStyleSheet(f"background: {BG}; color: {TEXT};")

    def init_ui(self):
        self.setWindowTitle("TITAN V8.2 — Profile Forge")
        self.setMinimumSize(1000, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        hdr = QLabel("PROFILE FORGE")
        hdr.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(hdr)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_identity_tab()
        self._build_forge_tab()
        self._build_profiles_tab()
        self._build_advanced_tab()

    def _build_identity_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Auto-fill button row
        auto_row = QHBoxLayout()
        auto_btn = QPushButton("GENERATE RANDOM PERSONA")
        auto_btn.setStyleSheet(f"background: {GREEN}; color: white; padding: 12px 28px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        auto_btn.clicked.connect(self._auto_fill_persona)
        auto_row.addWidget(auto_btn)
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(f"background: {RED}; color: white; padding: 12px 18px; border-radius: 8px;")
        clear_btn.clicked.connect(self._clear_identity)
        auto_row.addWidget(clear_btn)
        auto_row.addStretch()
        layout.addLayout(auto_row)

        # Persona
        pgrp = QGroupBox("Persona Identity")
        pf = QFormLayout(pgrp)
        self.id_name = QLineEdit()
        self.id_name.setPlaceholderText("Full name")
        pf.addRow("Name:", self.id_name)
        self.id_email = QLineEdit()
        self.id_email.setPlaceholderText("email@provider.com")
        pf.addRow("Email:", self.id_email)
        self.id_phone = QLineEdit()
        self.id_phone.setPlaceholderText("+1-555-000-0000")
        pf.addRow("Phone:", self.id_phone)
        layout.addWidget(pgrp)

        # Address
        agrp = QGroupBox("Billing Address")
        af = QFormLayout(agrp)
        self.id_street = QLineEdit()
        self.id_street.setPlaceholderText("123 Main St")
        af.addRow("Street:", self.id_street)
        self.id_city = QLineEdit()
        af.addRow("City:", self.id_city)
        self.id_state = QLineEdit()
        self.id_state.setPlaceholderText("e.g., NY, CA, TX")
        af.addRow("State:", self.id_state)
        self.id_zip = QLineEdit()
        af.addRow("ZIP:", self.id_zip)
        layout.addWidget(agrp)

        # Card
        cgrp = QGroupBox("Card Details")
        cf = QFormLayout(cgrp)
        self.id_card_last4 = QLineEdit()
        self.id_card_last4.setPlaceholderText("Last 4 digits")
        self.id_card_last4.setMaxLength(4)
        cf.addRow("Last 4:", self.id_card_last4)
        self.id_card_network = QComboBox()
        self.id_card_network.addItems(["visa", "mastercard", "amex", "discover"])
        cf.addRow("Network:", self.id_card_network)
        self.id_card_exp = QLineEdit()
        self.id_card_exp.setPlaceholderText("MM/YY")
        self.id_card_exp.setMaxLength(5)
        cf.addRow("Expiry:", self.id_card_exp)
        layout.addWidget(cgrp)

        # Target
        tgrp = QGroupBox("Target Configuration")
        tf = QFormLayout(tgrp)
        self.id_target = QComboBox()
        self.id_target.setEditable(True)
        self.id_target.addItems(["amazon.com", "ebay.com", "walmart.com", "bestbuy.com", "target.com", "shopify.com", "stripe.com"])
        tf.addRow("Target:", self.id_target)
        self.id_age = QSpinBox()
        self.id_age.setRange(7, 365)
        self.id_age.setValue(90)
        self.id_age.setSuffix(" days")
        tf.addRow("Profile Age:", self.id_age)
        self.id_storage = QSpinBox()
        self.id_storage.setRange(50, 5000)
        self.id_storage.setValue(500)
        self.id_storage.setSuffix(" MB")
        tf.addRow("Cache Size:", self.id_storage)
        layout.addWidget(tgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "IDENTITY")

    def _auto_fill_persona(self):
        p = generate_persona()
        self.id_name.setText(p["name"])
        self.id_email.setText(p["email"])
        self.id_phone.setText(p["phone"])
        self.id_street.setText(p["street"])
        self.id_city.setText(p["city"])
        self.id_state.setText(p["state"])
        self.id_zip.setText(p["zip"])
        self.id_card_last4.setText(p["card_last4"])
        idx = self.id_card_network.findText(p["card_network"])
        if idx >= 0:
            self.id_card_network.setCurrentIndex(idx)
        self.id_card_exp.setText(p["card_exp"])

    def _clear_identity(self):
        for w in [self.id_name, self.id_email, self.id_phone, self.id_street,
                  self.id_city, self.id_state, self.id_zip, self.id_card_last4, self.id_card_exp]:
            w.clear()

    def _build_forge_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Pipeline status
        grp = QGroupBox("Forge Pipeline (9 Stages)")
        gf = QVBoxLayout(grp)
        layers = [
            ("Genesis Engine", GENESIS_OK),
            ("Purchase History", PURCHASE_OK),
            ("IndexedDB/LSNG", IDB_OK),
            ("First-Session Bias", FSB_OK),
            ("Chrome Commerce", CHROME_COMMERCE_OK),
            ("Forensic Cache", CACHE_OK),
            ("Font Sanitizer", FONT_OK),
            ("Audio Hardener", AUDIO_OK),
            ("Realism Scoring", REALISM_OK),
        ]
        for name, ok in layers:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 10px;")
            dot.setFixedWidth(14)
            row.addWidget(dot)
            row.addWidget(QLabel(name))
            row.addStretch()
            gf.addLayout(row)
        layout.addWidget(grp)

        # Progress
        self.forge_progress = QProgressBar()
        self.forge_progress.setValue(0)
        layout.addWidget(self.forge_progress)

        self.forge_status = QLabel("Ready to forge")
        self.forge_status.setStyleSheet(f"color: {TEXT2};")
        layout.addWidget(self.forge_status)

        # Forge button
        btn_row = QHBoxLayout()
        self.forge_btn = QPushButton("FORGE PROFILE")
        self.forge_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 14px 32px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.forge_btn.clicked.connect(self._start_forge)
        btn_row.addWidget(self.forge_btn)

        quick_btn = QPushButton("QUICK FORGE (Auto-Generate + Forge)")
        quick_btn.setStyleSheet(f"background: {GREEN}; color: white; padding: 14px 24px; border-radius: 8px; font-weight: bold; font-size: 12px;")
        quick_btn.clicked.connect(self._quick_forge)
        btn_row.addWidget(quick_btn)
        layout.addLayout(btn_row)

        # Output
        self.forge_output = QPlainTextEdit()
        self.forge_output.setReadOnly(True)
        self.forge_output.setMinimumHeight(200)
        self.forge_output.setPlaceholderText("Forge output will appear here...")
        layout.addWidget(self.forge_output)

        layout.addStretch()
        self.tabs.addTab(scroll, "FORGE")

    def _build_profiles_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Generated Profiles")
        gf = QVBoxLayout(grp)

        self.profiles_table = QTableWidget()
        self.profiles_table.setColumnCount(5)
        self.profiles_table.setHorizontalHeaderLabels(["ID", "Target", "Age", "Quality", "Created"])
        self.profiles_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.profiles_table.setMinimumHeight(400)
        gf.addWidget(self.profiles_table)

        btn_row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 8px 16px; border: 1px solid #334155; border-radius: 6px;")
        refresh.clicked.connect(self._refresh_profiles)
        btn_row.addWidget(refresh)
        btn_row.addStretch()
        gf.addLayout(btn_row)

        layout.addWidget(grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "PROFILES")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4: ADVANCED (wires: chromium_cookie_engine, leveldb_writer)
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_advanced_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Module status
        stat_grp = QGroupBox("Advanced Forge Modules")
        sl = QVBoxLayout(stat_grp)
        mods = [
            ("chromium_cookie_engine", COOKIE_ENGINE_OK, "OblivionForgeEngine, ChromeCryptoEngine, HybridInjector, LevelDBForger, CacheSurgeon"),
            ("leveldb_writer", LEVELDB_OK, "LevelDBWriter — Chrome Local Storage LevelDB injection"),
            ("genesis_core", GENESIS_OK, "GenesisEngine — Primary profile forge engine"),
            ("forensic_synthesis_engine", CACHE_OK, "Cache2Synthesizer — Chrome disk cache synthesis"),
            ("chromium_commerce_injector", CHROME_COMMERCE_OK, "inject_golden_chain — Commerce trust anchors"),
        ]
        for name, ok, desc in mods:
            color = GREEN if ok else RED
            sl.addWidget(QLabel(f"<span style='color:{color};'>{'●' if ok else '○'}</span> <b>{name}</b>: {desc}"))
        layout.addWidget(stat_grp)

        # Cookie Engine panel
        ck_grp = QGroupBox("Chromium Cookie Engine")
        cl = QVBoxLayout(ck_grp)
        cl.addWidget(QLabel("Forge encrypted cookies, LevelDB data, and disk cache for Chrome profiles"))
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Profile Path:"))
        self.adv_profile_path = QLineEdit("/opt/titan/profiles/")
        self.adv_profile_path.setPlaceholderText("/opt/titan/profiles/<profile_id>")
        row1.addWidget(self.adv_profile_path)
        cl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Browser:"))
        self.adv_browser = QComboBox()
        self.adv_browser.addItems(["chrome", "chromium", "edge", "brave", "firefox"])
        row2.addWidget(self.adv_browser)
        row2.addWidget(QLabel("Target Origin:"))
        self.adv_origin = QLineEdit("https://www.amazon.com")
        row2.addWidget(self.adv_origin)
        cl.addLayout(row2)

        btn_row = QHBoxLayout()
        btn_forge_cookies = QPushButton("Forge Cookies")
        btn_forge_cookies.setStyleSheet(f"background: {ACCENT}; color: #0a0e17; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        btn_forge_cookies.clicked.connect(self._forge_cookies)
        btn_row.addWidget(btn_forge_cookies)

        btn_cache = QPushButton("Synthesize Cache")
        btn_cache.setStyleSheet(f"background: {ORANGE}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        btn_cache.clicked.connect(self._synthesize_cache)
        btn_row.addWidget(btn_cache)

        btn_leveldb = QPushButton("Write LevelDB Data")
        btn_leveldb.setStyleSheet(f"background: {GREEN}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        btn_leveldb.clicked.connect(self._write_leveldb)
        btn_row.addWidget(btn_leveldb)
        btn_row.addStretch()
        cl.addLayout(btn_row)
        layout.addWidget(ck_grp)

        # LevelDB key-value editor
        ldb_grp = QGroupBox("LevelDB Key-Value Injection")
        ll = QVBoxLayout(ldb_grp)
        ll.addWidget(QLabel("Inject localStorage data into Chrome LevelDB (origin-keyed)"))
        kv_row = QHBoxLayout()
        kv_row.addWidget(QLabel("Key:"))
        self.adv_ldb_key = QLineEdit()
        self.adv_ldb_key.setPlaceholderText("e.g. csm-hit, session-id, ubid-main")
        kv_row.addWidget(self.adv_ldb_key)
        kv_row.addWidget(QLabel("Value:"))
        self.adv_ldb_value = QLineEdit()
        self.adv_ldb_value.setPlaceholderText("Value to inject")
        kv_row.addWidget(self.adv_ldb_value)
        ll.addLayout(kv_row)
        layout.addWidget(ldb_grp)

        # Output
        self.adv_output = QPlainTextEdit()
        self.adv_output.setReadOnly(True)
        self.adv_output.setMaximumHeight(250)
        self.adv_output.setStyleSheet("font-family: 'JetBrains Mono'; font-size: 11px;")
        self.adv_output.setPlainText("Advanced forge panel ready.\nModules loaded: cookie_engine=" + str(COOKIE_ENGINE_OK) + " leveldb=" + str(LEVELDB_OK))
        layout.addWidget(self.adv_output)

        layout.addStretch()
        self.tabs.addTab(scroll, "ADVANCED")

    def _forge_cookies(self):
        profile_path = self.adv_profile_path.text().strip()
        origin = self.adv_origin.text().strip() or "https://www.amazon.com"
        browser = self.adv_browser.currentText()
        if not COOKIE_ENGINE_OK:
            self.adv_output.setPlainText("chromium_cookie_engine not available — cannot forge cookies.\nInstall with: pip install plyvel cryptography")
            return
        try:
            bt = BrowserType(browser) if hasattr(BrowserType, browser.upper()) else BrowserType.CHROME
            engine = OblivionForgeEngine(profile_path, bt)
            result = engine.forge(origin) if hasattr(engine, 'forge') else engine.inject_cookies(origin) if hasattr(engine, 'inject_cookies') else str(engine)
            self.adv_output.setPlainText(f"Cookie forge complete for {origin}\n\nProfile: {profile_path}\nBrowser: {browser}\n\n{json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result)}")
        except Exception as e:
            self.adv_output.setPlainText(f"Cookie forge error: {e}")

    def _synthesize_cache(self):
        profile_path = self.adv_profile_path.text().strip()
        if not CACHE_OK:
            self.adv_output.setPlainText("forensic_synthesis_engine not available — cannot synthesize cache.")
            return
        try:
            synth = Cache2Synthesizer()
            result = synth.synthesize(profile_path) if hasattr(synth, 'synthesize') else synth.generate(profile_path) if hasattr(synth, 'generate') else str(synth)
            self.adv_output.setPlainText(f"Cache synthesis complete\n\n{json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result)}")
        except Exception as e:
            self.adv_output.setPlainText(f"Cache synthesis error: {e}")

    def _write_leveldb(self):
        profile_path = self.adv_profile_path.text().strip()
        origin = self.adv_origin.text().strip() or "https://www.amazon.com"
        key = self.adv_ldb_key.text().strip()
        value = self.adv_ldb_value.text().strip()
        if not LEVELDB_OK:
            self.adv_output.setPlainText("leveldb_writer not available — cannot write LevelDB.\nInstall with: pip install plyvel && apt install libleveldb-dev")
            return
        if not key:
            self.adv_output.setPlainText("Enter a key to inject into LevelDB.")
            return
        try:
            ldb_dir = os.path.join(profile_path, "Default", "Local Storage", "leveldb")
            writer = LevelDBWriter(ldb_dir)
            if writer.open():
                ok = writer.write_origin_data(origin, {key: value})
                writer.close()
                self.adv_output.setPlainText(f"LevelDB write {'OK' if ok else 'FAILED'}\n\nOrigin: {origin}\nKey: {key}\nValue: {value[:100]}\nDB: {ldb_dir}")
            else:
                self.adv_output.setPlainText("Failed to open LevelDB database")
        except Exception as e:
            self.adv_output.setPlainText(f"LevelDB write error: {e}")

    def _start_forge(self):
        config = {
            "target": self.id_target.currentText(),
            "name": self.id_name.text().strip(),
            "email": self.id_email.text().strip(),
            "phone": self.id_phone.text().strip(),
            "street": self.id_street.text().strip(),
            "city": self.id_city.text().strip(),
            "state": self.id_state.text().strip(),
            "zip": self.id_zip.text().strip(),
            "card_last4": self.id_card_last4.text().strip(),
            "card_network": self.id_card_network.currentText(),
            "card_exp": self.id_card_exp.text().strip(),
            "age_days": self.id_age.value(),
            "storage_mb": self.id_storage.value(),
        }
        self.forge_btn.setEnabled(False)
        self.forge_progress.setValue(0)
        self.forge_output.clear()
        self.worker = ForgeWorker(config)
        self.worker.progress.connect(self._on_forge_progress)
        self.worker.finished.connect(self._on_forge_done)
        self.worker.start()

    def _on_forge_progress(self, pct, msg):
        self.forge_progress.setValue(pct)
        self.forge_status.setText(msg)
        self.forge_output.appendPlainText(f"[{pct}%] {msg}")

    def _quick_forge(self):
        self._auto_fill_persona()
        self._start_forge()

    def _on_forge_done(self, result):
        self.forge_btn.setEnabled(True)
        if result.get("success"):
            self.forge_output.appendPlainText(f"\nSUCCESS — Quality: {result.get('quality_score', 0)}/100")
            self.forge_output.appendPlainText(f"Path: {result.get('profile_path', 'N/A')}")
            self.forge_output.appendPlainText(f"Layers: {result.get('layers_applied', 0)}")
            if result.get("v83_fp_coherence") is not None:
                self.forge_output.appendPlainText(f"FP Coherence: {result['v83_fp_coherence']}/100")
            if result.get("v83_id_plausible") is not None:
                self.forge_output.appendPlainText(f"ID Plausible: {result['v83_id_plausible']}")
            if SESSION_OK:
                try:
                    update_session(
                        last_profile_path=result.get("profile_path", ""),
                        last_profile_id=result.get("profile_id", ""),
                        last_forge_quality=result.get("quality_score", 0),
                    )
                except Exception:
                    pass
            self._refresh_profiles()
        else:
            self.forge_output.appendPlainText(f"\nFAILED: {result.get('error', 'Unknown')}")

    def _refresh_profiles(self):
        profiles_dir = Path("/opt/titan/profiles")
        profiles_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_table.setRowCount(0)
        for d in sorted(profiles_dir.iterdir(), reverse=True):
            if d.is_dir():
                row = self.profiles_table.rowCount()
                self.profiles_table.insertRow(row)
                self.profiles_table.setItem(row, 0, QTableWidgetItem(d.name[:16]))
                meta_file = d / "titan_meta.json"
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text())
                        self.profiles_table.setItem(row, 1, QTableWidgetItem(meta.get("target", "")))
                        self.profiles_table.setItem(row, 2, QTableWidgetItem(f"{meta.get('age_days', '?')}d"))
                        self.profiles_table.setItem(row, 3, QTableWidgetItem(str(meta.get("quality_score", "?"))))
                        self.profiles_table.setItem(row, 4, QTableWidgetItem(meta.get("created", "")))
                    except Exception:
                        pass

    def _export_profile(self, profile_dir):
        if not profile_dir or not Path(profile_dir).exists():
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Export Profile", f"{Path(profile_dir).name}.json", "JSON (*.json)")
        if dest:
            meta_file = Path(profile_dir) / "titan_meta.json"
            if meta_file.exists():
                shutil.copy2(str(meta_file), dest)
                QMessageBox.information(self, "Export", f"Profile exported to {dest}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TitanProfileForge()
    win.show()
    sys.exit(app.exec())
