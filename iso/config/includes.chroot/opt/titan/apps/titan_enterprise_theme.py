"""
TITAN V7.5 SINGULARITY — Cyberpunk Glassmorphism Theme System
Premium per-module accent colors, neon glow effects, rgba glassmorphism panels,
and deep midnight base for prolonged operational use.

Color Philosophy:
    Deep midnight base (#0a0e17) + per-module neon accent colors
    Glassmorphism overlays via rgba() semi-transparent panels
    Neon green (#00ff88) for success/active states
    Unique accent per module: Genesis Orange, Cerberus Cyan, KYC Purple, etc.

Typography:
    JetBrains Mono / Consolas monospace — developer aesthetic throughout
"""

from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication


# ═══════════════════════════════════════════════════════════════════════════
# CYBERPUNK COLOR PALETTE — Deep Midnight + Neon Accents
# ═══════════════════════════════════════════════════════════════════════════

def _hex_to_rgb(hex_color: str):
    """Convert #RRGGBB to (r, g, b) tuple."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgba(hex_color: str, alpha: float) -> str:
    """Convert hex color + alpha to CSS rgba() string."""
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


class Colors:
    """Cyberpunk Glassmorphism color constants."""

    # ── Foundation — Deep Midnight Background ───────────────────────────
    BASE_BG = "#0a0e17"           # Deep midnight — primary background
    PANEL_BG = "#0d1117"          # Glassmorphism panel base
    PANEL_ELEVATED = "#111827"    # Elevated panel (cards, modals)
    SURFACE = "#1a2035"           # Input fields, interactive surfaces
    SURFACE_HOVER = "#1e2a45"     # Hover state for surfaces

    # ── Text Hierarchy ─────────────────────────────────────────────────
    TEXT_PRIMARY = "#c8d2dc"      # Soft white — primary text
    TEXT_SECONDARY = "#94A3B8"    # Secondary labels, descriptions
    TEXT_MUTED = "#64748B"        # Placeholders, hints
    TEXT_DISABLED = "#475569"     # Disabled state

    # ── Default Neon Cyan (Unified / fallback) ──────────────────────────
    PRIMARY = "#00d4ff"           # Neon cyan — default primary
    PRIMARY_HOVER = "#33ddff"     # Lighter neon on hover
    PRIMARY_PRESSED = "#0099bb"   # Pressed state
    PRIMARY_SUBTLE = "#001822"    # Background tint

    # ── Neon Green — Success / Active ───────────────────────────────────
    SUCCESS = "#00ff88"           # Neon green — verified, loaded, active
    SUCCESS_TEXT = "#00ff88"      # Neon green text
    SUCCESS_SUBTLE = "#001a0d"    # Success background tint

    # ── Warning / Caution ───────────────────────────────────────────────
    WARNING = "#E6A817"           # Amber — caution, degraded state
    WARNING_TEXT = "#FFB74D"      # Warning text
    WARNING_SUBTLE = "#2E2510"    # Warning background tint

    # ── Critical / Alert ────────────────────────────────────────────────
    CRITICAL = "#ff3355"          # Hot red — alerts, kill switch, leaks
    CRITICAL_TEXT = "#ff4466"     # Critical text
    CRITICAL_SUBTLE = "#1a0008"   # Critical background tint

    # ── Borders & Dividers ─────────────────────────────────────────────
    BORDER = "#1a2535"            # Default border
    BORDER_FOCUS = "#00d4ff"      # Focused input border (neon)
    BORDER_SUBTLE = "#0d1520"     # Subtle divider

    # ── Selection ──────────────────────────────────────────────────────
    SELECTION_BG = "#00d4ff"      # Selection background
    SELECTION_TEXT = "#000000"    # Selection text (black on neon)

    # ── Per-Module Accent Colors (Unique cyberpunk identity per app) ─────
    MODULE_GENESIS = "#ff6b35"    # Genesis Orange — profile forge
    MODULE_CERBERUS = "#00bcd4"   # Cerberus Cyan — card validation
    MODULE_KYC = "#9c27b0"        # KYC Purple — identity verification
    MODULE_GHOST = "#00ff88"      # Ghost Motor Green — biometric
    MODULE_UNIFIED = "#00d4ff"    # Unified Neon Cyan — command center
    MODULE_REPORTER = "#5588ff"   # Bug Reporter Blue — diagnostics
    MODULE_MISSION = "#00d4ff"    # Mission Control — infrastructure

    # ── Legacy Compatibility ────────────────────────────────────────────
    ACCENT = "#00d4ff"
    ACCENT_DIM = "#006688"
    ACCENT_SUBTLE = "#001822"


# ═══════════════════════════════════════════════════════════════════════════
# CYBERPUNK TYPOGRAPHY — JetBrains Mono Throughout
# ═══════════════════════════════════════════════════════════════════════════

class Fonts:
    """Cyberpunk typography — monospace developer aesthetic."""

    # Monospace for all UI elements (cyberpunk aesthetic)
    UI_FAMILY = "'JetBrains Mono', 'Consolas', 'Courier New', monospace"
    UI_FAMILY_PLAIN = "JetBrains Mono"

    DATA_FAMILY = "'JetBrains Mono', 'Consolas', 'Courier New', monospace"
    DATA_FAMILY_PLAIN = "JetBrains Mono"

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
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        return QFont(Fonts.UI_FAMILY_PLAIN, size, weight)

    @staticmethod
    def data(size: int = 10, bold: bool = False) -> QFont:
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        return QFont(Fonts.DATA_FAMILY_PLAIN, size, weight)

    @staticmethod
    def heading(size: int = 16) -> QFont:
        return QFont(Fonts.UI_FAMILY_PLAIN, size, QFont.Weight.Bold)


# ═══════════════════════════════════════════════════════════════════════════
# NOMENCLATURE — Module Identity Labels
# ═══════════════════════════════════════════════════════════════════════════

class Nomenclature:
    """Cyberpunk module identity labels."""

    APP_UNIFIED = "TITAN V8.0 — Unified Operation Center"
    APP_GENESIS = "TITAN V8.0 — Genesis Profile Forge"
    APP_CERBERUS = "TITAN V8.0 — Cerberus Card Intelligence"
    APP_KYC = "TITAN V8.0 — KYC Bypass & Identity Compliance"
    APP_BUG_REPORTER = "TITAN V8.0 — Diagnostic Reporter"
    APP_MISSION_CONTROL = "System Control Panel"

    MOD_GENESIS = "Genesis — The Forge"
    MOD_CERBERUS = "Cerberus Guard"
    MOD_KYC = "KYC Bypass"
    MOD_GHOST = "Ghost Motor"
    MOD_KILL = "Kill Switch"
    MOD_TLS = "TLS Parrot"
    MOD_NETWORK = "Network Shield"
    MOD_FINGERPRINT = "Fingerprint Spoofing"

    ACT_FORGE = "Forge"
    ACT_VALIDATE = "Validate"
    ACT_LAUNCH = "Launch Browser"
    STATUS_ARMED = "ARMED"
    STATUS_DISARMED = "DISARMED"
    STATUS_PANIC = "PANIC"
    STATUS_READY = "READY"


# ═══════════════════════════════════════════════════════════════════════════
# CYBERPUNK GLASSMORPHISM STYLESHEET GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_cyberpunk_stylesheet(accent: str = "#00d4ff") -> str:
    """
    Generate a cyberpunk glassmorphism QSS stylesheet with the given module accent color.
    Each module passes its own unique accent for visual identity differentiation.

    Args:
        accent: Hex color string for module accent (#ff6b35, #00bcd4, #9c27b0, etc.)
    """
    r, g, b = _hex_to_rgb(accent)
    panel_glass = f"rgba(13, 17, 35, 0.85)"
    panel_border = f"rgba({r}, {g}, {b}, 0.35)"
    panel_title_bg = f"rgba({r}, {g}, {b}, 0.12)"
    input_glass = f"rgba(26, 32, 53, 0.9)"
    input_border = f"rgba({r}, {g}, {b}, 0.3)"
    btn_bg = f"rgba({r}, {g}, {b}, 0.15)"
    btn_hover = f"rgba({r}, {g}, {b}, 0.85)"
    tab_selected_bg = f"rgba({r}, {g}, {b}, 0.15)"

    return f"""
    /* ═══════════════════════════════════════════════════════════════════
       TITAN V8.0 — Cyberpunk Glassmorphism Theme
       Deep Midnight Base + Neon Accent: {accent}
       ═══════════════════════════════════════════════════════════════════ */

    QMainWindow, QDialog {{
        background-color: {Colors.BASE_BG};
    }}

    /* ── Glassmorphism Group Boxes (Panels) ──────────────────────── */
    QGroupBox {{
        font-family: {Fonts.UI_FAMILY};
        font-weight: bold;
        font-size: {Fonts.SIZE_SM}pt;
        color: {accent};
        border: 1px solid {panel_border};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 16px;
        background-color: {panel_glass};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 10px;
        color: {accent};
        background-color: {panel_title_bg};
        border-radius: 3px;
    }}

    /* ── Labels ────────────────────────────────────────────────────── */
    QLabel {{
        font-family: {Fonts.UI_FAMILY};
        color: {Colors.TEXT_PRIMARY};
    }}

    /* ── Glassmorphism Input Fields ────────────────────────────────── */
    QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
        font-family: {Fonts.UI_FAMILY};
        font-size: {Fonts.SIZE_SM}pt;
        background-color: {input_glass};
        border: 1px solid {input_border};
        border-radius: 6px;
        padding: 7px 10px;
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: {accent};
        selection-color: #000000;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {accent};
        background-color: rgba(26, 32, 53, 0.95);
    }}

    QComboBox::drop-down {{
        border: none;
        background: transparent;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: rgba(13, 17, 35, 0.97);
        border: 1px solid {accent};
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: {accent};
        selection-color: #000000;
    }}

    /* ── Cyberpunk Buttons with Gradient ───────────────────────────── */
    QPushButton {{
        font-family: {Fonts.UI_FAMILY};
        font-weight: bold;
        font-size: {Fonts.SIZE_SM}pt;
        background-color: {btn_bg};
        border: 1px solid {accent};
        border-radius: 6px;
        padding: 8px 18px;
        color: {accent};
    }}
    QPushButton:hover {{
        background-color: {btn_hover};
        border: 1px solid {accent};
        color: #000000;
    }}
    QPushButton:pressed {{
        background-color: rgba({r}, {g}, {b}, 1.0);
        color: #000000;
    }}
    QPushButton:disabled {{
        background-color: rgba(26, 32, 53, 0.5);
        border: 1px solid rgba(100, 116, 139, 0.3);
        color: {Colors.TEXT_DISABLED};
    }}

    /* ── Tabs ──────────────────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {panel_border};
        border-radius: 6px;
        background-color: {Colors.BASE_BG};
    }}
    QTabBar::tab {{
        font-family: {Fonts.UI_FAMILY};
        font-weight: bold;
        background: rgba(13, 17, 35, 0.7);
        color: {Colors.TEXT_MUTED};
        padding: 10px 22px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        border: 1px solid transparent;
    }}
    QTabBar::tab:selected {{
        background: {tab_selected_bg};
        color: {accent};
        border-bottom: 2px solid {accent};
    }}
    QTabBar::tab:hover {{
        background: rgba(26, 32, 53, 0.8);
        color: {Colors.TEXT_PRIMARY};
    }}

    /* ── Gradient Progress Bars (Cyan → Neon Green) ────────────────── */
    QProgressBar {{
        border: 1px solid {panel_border};
        border-radius: 4px;
        background-color: rgba(26, 32, 53, 0.8);
        text-align: center;
        color: {Colors.TEXT_SECONDARY};
        font-family: {Fonts.UI_FAMILY};
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {accent}, stop:1 {Colors.SUCCESS});
        border-radius: 3px;
    }}

    /* ── Checkboxes ────────────────────────────────────────────────── */
    QCheckBox {{
        font-family: {Fonts.UI_FAMILY};
        color: {Colors.TEXT_PRIMARY};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {input_border};
        border-radius: 3px;
        background-color: {input_glass};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border: 1px solid {accent};
        border-radius: 3px;
    }}

    /* ── Styled Scrollbars ─────────────────────────────────────────── */
    QScrollBar:vertical {{
        background: rgba(10, 14, 23, 0.6);
        width: 8px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba({r}, {g}, {b}, 0.4);
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba({r}, {g}, {b}, 0.7);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: rgba(10, 14, 23, 0.6);
        height: 8px;
        border: none;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba({r}, {g}, {b}, 0.4);
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba({r}, {g}, {b}, 0.7);
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Tables ────────────────────────────────────────────────────── */
    QTableWidget {{
        background-color: rgba(13, 17, 35, 0.85);
        gridline-color: {panel_border};
        color: {Colors.TEXT_PRIMARY};
        font-family: {Fonts.UI_FAMILY};
        border: 1px solid {panel_border};
        border-radius: 6px;
    }}
    QHeaderView::section {{
        background-color: rgba({r}, {g}, {b}, 0.2);
        color: {accent};
        font-family: {Fonts.UI_FAMILY};
        font-weight: bold;
        padding: 6px;
        border: none;
        border-bottom: 1px solid {accent};
    }}
    QTableWidget::item:selected {{
        background-color: {tab_selected_bg};
        color: {accent};
    }}
    QTableWidget::item:alternate {{
        background-color: rgba(26, 32, 53, 0.5);
    }}

    /* ── List Widgets ──────────────────────────────────────────────── */
    QListWidget {{
        background-color: rgba(13, 17, 35, 0.85);
        border: 1px solid {panel_border};
        border-radius: 6px;
        color: {Colors.TEXT_PRIMARY};
        font-family: {Fonts.UI_FAMILY};
    }}
    QListWidget::item:selected {{
        background-color: {tab_selected_bg};
        color: {accent};
    }}
    QListWidget::item:hover {{
        background-color: rgba(26, 32, 53, 0.8);
    }}

    /* ── Sliders with Radial Gradient Handle ───────────────────────── */
    QSlider::groove:horizontal {{
        height: 4px;
        background: rgba(26, 32, 53, 0.9);
        border: 1px solid {panel_border};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {accent}, stop:1 {Colors.SUCCESS});
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
            fx:0.5, fy:0.5,
            stop:0 #ffffff,
            stop:0.4 {accent},
            stop:1 rgba({r}, {g}, {b}, 0.6));
        border: 1px solid {accent};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
            fx:0.5, fy:0.5,
            stop:0 #ffffff,
            stop:0.3 {accent},
            stop:1 rgba({r}, {g}, {b}, 0.9));
    }}

    /* ── Frames ────────────────────────────────────────────────────── */
    QFrame {{
        border: none;
    }}

    /* ── Cyberpunk Tooltips with Neon Border ────────────────────────── */
    QToolTip {{
        font-family: {Fonts.UI_FAMILY};
        font-size: {Fonts.SIZE_XS}pt;
        background-color: rgba(10, 14, 23, 0.95);
        color: {accent};
        border: 1px solid {accent};
        padding: 6px 10px;
        border-radius: 4px;
    }}

    /* ── Status Bar ────────────────────────────────────────────────── */
    QStatusBar {{
        background-color: rgba(13, 17, 35, 0.9);
        color: {Colors.TEXT_SECONDARY};
        font-family: {Fonts.UI_FAMILY};
        border-top: 1px solid {panel_border};
    }}
"""


# Default stylesheet (Unified Neon Cyan accent)
ENTERPRISE_STYLESHEET = generate_cyberpunk_stylesheet(Colors.MODULE_UNIFIED)


# ═══════════════════════════════════════════════════════════════════════════
# THEME APPLICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def build_enterprise_palette(accent: str = "#00d4ff") -> QPalette:
    """Build the cyberpunk QPalette for PyQt6 applications."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BASE_BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.PANEL_BG))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.PANEL_ELEVATED))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(accent))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.BASE_BG))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(accent))
    return palette


def apply_enterprise_theme(widget, accent_color: str = None):
    """
    Apply cyberpunk glassmorphism theme to a QMainWindow or QWidget.
    Each module passes its unique accent color for visual identity.

    Usage:
        from titan_enterprise_theme import apply_enterprise_theme
        apply_enterprise_theme(self, "#ff6b35")   # Genesis Orange
        apply_enterprise_theme(self, "#00bcd4")   # Cerberus Cyan
        apply_enterprise_theme(self, "#9c27b0")   # KYC Purple
        apply_enterprise_theme(self, "#5588ff")   # Bug Reporter Blue
        apply_enterprise_theme(self)              # Default: Unified Cyan
    """
    accent = accent_color or Colors.MODULE_UNIFIED
    widget.setPalette(build_enterprise_palette(accent))
    widget.setStyleSheet(generate_cyberpunk_stylesheet(accent))


# Alias for module-specific entry
apply_module_theme = apply_enterprise_theme


def apply_enterprise_theme_to_app(app: QApplication, accent_color: str = None):
    """Apply cyberpunk theme globally to the QApplication instance."""
    accent = accent_color or Colors.MODULE_UNIFIED
    app.setPalette(build_enterprise_palette(accent))
    app.setStyleSheet(generate_cyberpunk_stylesheet(accent))


# ═══════════════════════════════════════════════════════════════════════════
# SEMANTIC STATUS STYLES — For inline setStyleSheet() calls
# ═══════════════════════════════════════════════════════════════════════════

class StatusStyles:
    """Pre-built stylesheet strings for status labels."""

    SUCCESS = f"color: {Colors.SUCCESS_TEXT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    WARNING = f"color: {Colors.WARNING_TEXT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    CRITICAL = f"color: {Colors.CRITICAL_TEXT}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    INFO = f"color: {Colors.PRIMARY}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"
    MUTED = f"color: {Colors.TEXT_MUTED}; font-family: {Fonts.UI_FAMILY};"
    PRIMARY = f"color: {Colors.PRIMARY_HOVER}; font-family: {Fonts.UI_FAMILY}; font-weight: bold;"

    DATA = f"color: {Colors.PRIMARY}; font-family: {Fonts.DATA_FAMILY};"
    DATA_SUCCESS = f"color: {Colors.SUCCESS_TEXT}; font-family: {Fonts.DATA_FAMILY};"
    DATA_CRITICAL = f"color: {Colors.CRITICAL_TEXT}; font-family: {Fonts.DATA_FAMILY};"


# ═══════════════════════════════════════════════════════════════════════════
# MISSION CONTROL (tkinter) THEME — Neon Midnight Cyberpunk
# ═══════════════════════════════════════════════════════════════════════════

MISSION_CONTROL_COLORS = {
    "bg": Colors.BASE_BG,           # #0a0e17 deep midnight
    "fg": Colors.MODULE_MISSION,    # #00d4ff neon cyan
    "fg_dim": Colors.TEXT_MUTED,
    "accent": Colors.PANEL_BG,
    "accent_hover": Colors.PANEL_ELEVATED,
    "green": Colors.SUCCESS_TEXT,   # #00ff88 neon green
    "orange": Colors.WARNING_TEXT,
    "alert": Colors.CRITICAL_TEXT,
    "warn": Colors.WARNING_TEXT,
    "panel": Colors.PANEL_BG,
    "border": Colors.BORDER,
    "highlight": Colors.MODULE_MISSION,
    "text": Colors.TEXT_PRIMARY,
}
