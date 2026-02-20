"""
TITAN V7.5 SINGULARITY — Enterprise HRUX Theme System
Centralized High-Reliability UX (HRUX) theme for all GUI applications.

Replaces the legacy "Premium Cyberpunk Glassmorphism" aesthetic with
an enterprise-grade, WCAG-compliant design system optimized for:
- Prolonged operational monitoring (reduced eye strain)
- Situational awareness under stress (semantic color hierarchy)
- Cognitive load reduction (dual typography, progressive disclosure)
- Professional authority projection (elevated neutrals)

Color Philosophy:
    Legacy cyberpunk (#0a0e17 midnight + neon) → Enterprise HRUX (#151A21 slate + semantic)
    Glassmorphism overlays → Solid opaque panels (WCAG contrast compliance)
    Arbitrary neon app colors → Intent-driven semantic color system

Typography Philosophy:
    All-monospace → Dual system: Inter (UI) + JetBrains Mono (data-dense only)
"""

from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication


# ═══════════════════════════════════════════════════════════════════════════
# ENTERPRISE COLOR PALETTE — "Elevated Neutrals + Semantic Intent"
# ═══════════════════════════════════════════════════════════════════════════

class Colors:
    """HRUX Enterprise color constants."""

    # ── Foundation ──────────────────────────────────────────────────────
    BASE_BG = "#151A21"           # Slate UI — softer dark, reduces glare
    PANEL_BG = "#1C2330"          # Deep Navy — solid opaque panels
    PANEL_ELEVATED = "#232B3A"    # Elevated panel (cards, modals)
    SURFACE = "#2A3444"           # Input fields, interactive surfaces
    SURFACE_HOVER = "#313D4F"     # Hover state for surfaces

    # ── Text Hierarchy ─────────────────────────────────────────────────
    TEXT_PRIMARY = "#E2E8F0"      # Primary text — high contrast
    TEXT_SECONDARY = "#94A3B8"    # Secondary text — labels, descriptions
    TEXT_MUTED = "#64748B"        # Muted text — placeholders, hints
    TEXT_DISABLED = "#475569"     # Disabled state

    # ── Primary Action (Corporate Trust Blue) ──────────────────────────
    PRIMARY = "#3A75C4"           # Primary interactive elements
    PRIMARY_HOVER = "#4A8AD8"     # Primary hover
    PRIMARY_PRESSED = "#2D5F9E"   # Primary pressed
    PRIMARY_SUBTLE = "#1A2D4A"    # Primary background tint

    # ── Data Focus (Electric Cyan — Neon Anchor) ──────────────────────
    ACCENT = "#40E0FF"            # Critical data highlights, active routes
    ACCENT_DIM = "#2A8A9E"        # Dimmed accent for borders
    ACCENT_SUBTLE = "#152830"     # Accent background tint

    # ── Semantic: Success / Validation ─────────────────────────────────
    SUCCESS = "#2E7D32"           # Secure Green — verified, loaded, pass
    SUCCESS_TEXT = "#4CAF50"      # Success text
    SUCCESS_SUBTLE = "#1A2E1C"   # Success background tint

    # ── Semantic: Warning / Caution ────────────────────────────────────
    WARNING = "#E6A817"           # Amber — caution, degraded state
    WARNING_TEXT = "#FFB74D"      # Warning text
    WARNING_SUBTLE = "#2E2510"   # Warning background tint

    # ── Semantic: Critical / Alert ─────────────────────────────────────
    CRITICAL = "#D32F2F"          # Action Red — alerts, kill switch, leaks
    CRITICAL_TEXT = "#EF5350"     # Critical text
    CRITICAL_SUBTLE = "#2E1515"  # Critical background tint

    # ── Borders & Dividers ─────────────────────────────────────────────
    BORDER = "#2A3444"            # Default border
    BORDER_FOCUS = "#3A75C4"      # Focused input border
    BORDER_SUBTLE = "#1E2736"     # Subtle divider

    # ── Selection ──────────────────────────────────────────────────────
    SELECTION_BG = "#3A75C4"      # Selection background
    SELECTION_TEXT = "#FFFFFF"     # Selection text

    # ── Legacy Compatibility Aliases ───────────────────────────────────
    # Module-specific accents (used sparingly for module identity)
    MODULE_GENESIS = "#3A75C4"    # Was #ff6b35 (Genesis Orange)
    MODULE_CERBERUS = "#3A75C4"   # Was #00d4ff (Cerberus Cyan)
    MODULE_KYC = "#3A75C4"        # Was #9c27b0 (KYC Purple)
    MODULE_GHOST = "#3A75C4"      # Was #00ff88 (Ghost Green)


# ═══════════════════════════════════════════════════════════════════════════
# ENTERPRISE TYPOGRAPHY — Dual System
# ═══════════════════════════════════════════════════════════════════════════

class Fonts:
    """HRUX Enterprise typography constants."""

    # UI font: legible sans-serif for headers, labels, buttons, prose
    UI_FAMILY = "'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif"
    UI_FAMILY_PLAIN = "Inter"  # For QFont constructor

    # Data font: monospace for UUIDs, hashes, IPs, logs, hex values
    DATA_FAMILY = "'JetBrains Mono', 'Consolas', 'Courier New', monospace"
    DATA_FAMILY_PLAIN = "JetBrains Mono"  # For QFont constructor

    # Size scale
    SIZE_XS = 9
    SIZE_SM = 10
    SIZE_BASE = 11
    SIZE_LG = 13
    SIZE_XL = 16
    SIZE_2XL = 20
    SIZE_3XL = 26

    @staticmethod
    def ui(size: int = 11, bold: bool = False) -> QFont:
        """Create a UI font (sans-serif)."""
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        return QFont(Fonts.UI_FAMILY_PLAIN, size, weight)

    @staticmethod
    def data(size: int = 10, bold: bool = False) -> QFont:
        """Create a data font (monospace) — for hashes, IPs, logs."""
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        return QFont(Fonts.DATA_FAMILY_PLAIN, size, weight)

    @staticmethod
    def heading(size: int = 16) -> QFont:
        """Create a heading font."""
        return QFont(Fonts.UI_FAMILY_PLAIN, size, QFont.Weight.Bold)


# ═══════════════════════════════════════════════════════════════════════════
# ENTERPRISE NAMING CONVENTIONS — Semantic Recalibration
# ═══════════════════════════════════════════════════════════════════════════

class Nomenclature:
    """
    Enterprise terminology mapping.
    Maps legacy offensive terms to enterprise-grade equivalents.
    """

    # Application titles
    APP_UNIFIED = "TITAN — Unified Operations Dashboard"
    APP_GENESIS = "TITAN — Identity Synthesis Engine"
    APP_CERBERUS = "TITAN — Asset Validation & Risk Assessment"
    APP_KYC = "TITAN — Verification Compliance Module"
    APP_BUG_REPORTER = "TITAN — Diagnostic Reporter"
    APP_MISSION_CONTROL = "TITAN — Infrastructure Control Panel"

    # Module names (for tabs, headers, sidebar)
    MOD_GENESIS = "Identity Synthesis"       # Was "Genesis — The Forge"
    MOD_CERBERUS = "Asset Validation"        # Was "Cerberus Guard"
    MOD_KYC = "Verification Compliance"      # Was "KYC Bypass"
    MOD_GHOST = "Biometric Normalization"    # Was "Ghost Motor"
    MOD_KILL = "Isolation Protocol"          # Was "Kill Switch"
    MOD_TLS = "TLS Compliance Engine"        # Was "TLS Parrot"
    MOD_NETWORK = "Network Integrity Shield" # Was "Network Shield"
    MOD_FINGERPRINT = "Environment Emulation" # Was "Fingerprint Spoofing"

    # Action verbs
    ACT_FORGE = "Synthesize"                 # Was "Forge"
    ACT_SPOOF = "Emulate"                    # Was "Spoof"
    ACT_KILL = "Isolate"                     # Was "Kill / Panic"
    ACT_BYPASS = "Mitigate"                  # Was "Bypass / Evade"
    ACT_INJECT = "Apply"                     # Was "Inject"
    ACT_VALIDATE = "Validate"                # Was "Check / Audit"
    ACT_LAUNCH = "Initiate Session"          # Was "Launch Browser"

    # Status labels
    STATUS_ARMED = "Active"                  # Was "Armed"
    STATUS_DISARMED = "Standby"              # Was "Disarmed"
    STATUS_PANIC = "Isolation Triggered"     # Was "PANIC"
    STATUS_READY = "Operational"             # Was "Ready"
    STATUS_FORGING = "Synthesizing..."       # Was "Forging..."

    # Section headers
    SEC_TARGET = "Infrastructure Assessment" # Was "Target Discovery"
    SEC_PROXY = "Network Configuration"      # Was "Proxy Setup"
    SEC_CARD = "Asset Authorization"         # Was "Card Validation"
    SEC_PROFILE = "Identity Configuration"   # Was "Profile / Persona"
    SEC_PREFLIGHT = "Integrity Verification" # Was "Preflight Checks"
    SEC_HANDOVER = "Operational Handover"    # Was "Handover Protocol"


# ═══════════════════════════════════════════════════════════════════════════
# ENTERPRISE STYLESHEET — Complete QSS
# ═══════════════════════════════════════════════════════════════════════════

ENTERPRISE_STYLESHEET = f"""
    /* ═══════════════════════════════════════════════════════════════════
       TITAN V7.5 — Enterprise HRUX Theme
       High-Reliability UX: Elevated Neutrals + Semantic Color System
       ═══════════════════════════════════════════════════════════════════ */

    QMainWindow {{
        background-color: {Colors.BASE_BG};
    }}

    /* ── Group Boxes (Panels) ──────────────────────────────────────── */
    QGroupBox {{
        font-family: {Fonts.UI_FAMILY};
        font-weight: bold;
        font-size: {Fonts.SIZE_SM}pt;
        color: {Colors.TEXT_SECONDARY};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 16px;
        background-color: {Colors.PANEL_BG};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 10px;
        color: {Colors.PRIMARY};
    }}

    /* ── Labels ────────────────────────────────────────────────────── */
    QLabel {{
        font-family: {Fonts.UI_FAMILY};
        color: {Colors.TEXT_PRIMARY};
    }}

    /* ── Input Fields ──────────────────────────────────────────────── */
    QLineEdit, QComboBox, QSpinBox, QTextEdit {{
        font-family: {Fonts.UI_FAMILY};
        font-size: {Fonts.SIZE_SM}pt;
        background-color: {Colors.SURFACE};
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 7px 10px;
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: {Colors.SELECTION_BG};
        selection-color: {Colors.SELECTION_TEXT};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {Colors.BORDER_FOCUS};
        background-color: {Colors.SURFACE};
    }}

    QComboBox::drop-down {{
        border: none;
        background: transparent;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.PANEL_ELEVATED};
        border: 1px solid {Colors.BORDER_FOCUS};
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: {Colors.SELECTION_BG};
        selection-color: {Colors.SELECTION_TEXT};
    }}

    /* ── Buttons ───────────────────────────────────────────────────── */
    QPushButton {{
        font-family: {Fonts.UI_FAMILY};
        font-weight: 600;
        font-size: {Fonts.SIZE_SM}pt;
        background-color: {Colors.PRIMARY_SUBTLE};
        border: 1px solid {Colors.PRIMARY};
        border-radius: 6px;
        padding: 8px 18px;
        color: {Colors.PRIMARY_HOVER};
    }}
    QPushButton:hover {{
        background-color: {Colors.PRIMARY};
        border: 1px solid {Colors.PRIMARY_HOVER};
        color: {Colors.SELECTION_TEXT};
    }}
    QPushButton:pressed {{
        background-color: {Colors.PRIMARY_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {Colors.SURFACE};
        border: 1px solid {Colors.BORDER_SUBTLE};
        color: {Colors.TEXT_DISABLED};
    }}

    /* ── Tabs ──────────────────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        background-color: {Colors.BASE_BG};
    }}
    QTabBar::tab {{
        font-family: {Fonts.UI_FAMILY};
        font-weight: 600;
        background: {Colors.PANEL_BG};
        color: {Colors.TEXT_MUTED};
        padding: 10px 22px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background: {Colors.PRIMARY_SUBTLE};
        color: {Colors.PRIMARY_HOVER};
        border-bottom: 2px solid {Colors.PRIMARY};
    }}
    QTabBar::tab:hover {{
        background: {Colors.SURFACE};
        color: {Colors.TEXT_PRIMARY};
    }}

    /* ── Progress Bars ─────────────────────────────────────────────── */
    QProgressBar {{
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        background-color: {Colors.SURFACE};
        text-align: center;
        color: {Colors.TEXT_SECONDARY};
        font-family: {Fonts.UI_FAMILY};
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {Colors.PRIMARY}, stop:1 {Colors.PRIMARY_HOVER});
        border-radius: 3px;
    }}

    /* ── Checkboxes ────────────────────────────────────────────────── */
    QCheckBox {{
        font-family: {Fonts.UI_FAMILY};
        color: {Colors.TEXT_PRIMARY};
        spacing: 8px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {Colors.PRIMARY};
        border: 1px solid {Colors.PRIMARY};
        border-radius: 3px;
    }}

    /* ── Scrollbars ────────────────────────────────────────────────── */
    QScrollBar:vertical {{
        background: {Colors.BASE_BG};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {Colors.SURFACE_HOVER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Colors.TEXT_MUTED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ── Frames ────────────────────────────────────────────────────── */
    QFrame {{
        border: none;
    }}

    /* ── Tooltips ──────────────────────────────────────────────────── */
    QToolTip {{
        font-family: {Fonts.UI_FAMILY};
        background-color: {Colors.PANEL_ELEVATED};
        color: {Colors.TEXT_PRIMARY};
        border: 1px solid {Colors.BORDER};
        padding: 6px 10px;
        border-radius: 4px;
    }}
"""


# ═══════════════════════════════════════════════════════════════════════════
# THEME APPLICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def build_enterprise_palette() -> QPalette:
    """Build the enterprise QPalette for PyQt6 applications."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BASE_BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.PANEL_BG))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.PANEL_ELEVATED))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.SELECTION_BG))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.SELECTION_TEXT))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.PANEL_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Colors.TEXT_PRIMARY))
    return palette


def apply_enterprise_theme(widget):
    """
    Apply the full enterprise HRUX theme to a QMainWindow or QWidget.
    Replaces the legacy apply_dark_theme() method in all apps.

    Usage:
        from titan_enterprise_theme import apply_enterprise_theme
        # In __init__ or setup:
        apply_enterprise_theme(self)
    """
    widget.setPalette(build_enterprise_palette())
    widget.setStyleSheet(ENTERPRISE_STYLESHEET)


def apply_enterprise_theme_to_app(app: QApplication):
    """Apply enterprise theme globally to the QApplication instance."""
    app.setPalette(build_enterprise_palette())
    app.setStyleSheet(ENTERPRISE_STYLESHEET)


# ═══════════════════════════════════════════════════════════════════════════
# SEMANTIC STATUS STYLES — For inline setStyleSheet() calls
# ═══════════════════════════════════════════════════════════════════════════

class StatusStyles:
    """Pre-built stylesheet strings for status labels."""

    SUCCESS = f"color: {Colors.SUCCESS_TEXT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    WARNING = f"color: {Colors.WARNING_TEXT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    CRITICAL = f"color: {Colors.CRITICAL_TEXT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    INFO = f"color: {Colors.ACCENT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    MUTED = f"color: {Colors.TEXT_MUTED}; font-family: {Fonts.UI_FAMILY};"
    PRIMARY = f"color: {Colors.PRIMARY_HOVER}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"

    # Data-dense contexts (monospace)
    DATA = f"color: {Colors.ACCENT}; font-family: {Fonts.DATA_FAMILY};"
    DATA_SUCCESS = f"color: {Colors.SUCCESS_TEXT}; font-family: {Fonts.DATA_FAMILY};"
    DATA_CRITICAL = f"color: {Colors.CRITICAL_TEXT}; font-family: {Fonts.DATA_FAMILY};"


# ═══════════════════════════════════════════════════════════════════════════
# MISSION CONTROL (tkinter) THEME — For titan_mission_control.py
# ═══════════════════════════════════════════════════════════════════════════

MISSION_CONTROL_COLORS = {
    "bg": Colors.BASE_BG,
    "fg": Colors.PRIMARY_HOVER,
    "fg_dim": Colors.TEXT_MUTED,
    "accent": Colors.PANEL_BG,
    "accent_hover": Colors.PANEL_ELEVATED,
    "green": Colors.SUCCESS_TEXT,
    "orange": Colors.WARNING_TEXT,
    "alert": Colors.CRITICAL_TEXT,
    "warn": Colors.WARNING_TEXT,
    "panel": Colors.PANEL_BG,
    "border": Colors.BORDER,
    "highlight": Colors.PRIMARY,
    "text": Colors.TEXT_PRIMARY,
}
