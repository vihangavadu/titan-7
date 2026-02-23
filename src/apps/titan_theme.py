"""
TITAN V8.11 SINGULARITY — Unified Theme System
Single source of truth for all colors, fonts, and stylesheets.

Usage:
    from titan_theme import THEME, apply_titan_theme, make_group_style, make_tab_style
"""

from PyQt6.QtGui import QFont, QColor, QPalette


class TitanTheme:
    """Central theme constants for all Titan apps."""

    # Backgrounds
    BG = "#0a0e17"
    BG_CARD = "#111827"
    BG_CARD2 = "#1e293b"
    BG_INPUT = "#0f172a"
    BG_HOVER = "#1a2332"

    # Text
    TEXT = "#e2e8f0"
    TEXT_DIM = "#64748b"
    TEXT_BRIGHT = "#f8fafc"

    # Accent colors (each app picks one as primary)
    CYAN = "#00d4ff"
    GREEN = "#22c55e"
    YELLOW = "#eab308"
    RED = "#ef4444"
    ORANGE = "#f97316"
    PURPLE = "#a855f7"
    AMBER = "#f59e0b"
    INDIGO = "#6366f1"

    # Borders
    BORDER = "#1e293b"
    BORDER_FOCUS = "#334155"

    # Fonts
    FONT_TITLE = "Inter"
    FONT_MONO = "JetBrains Mono"
    FONT_BODY = "Inter"

    # Sizes
    TITLE_SIZE = 18
    BODY_SIZE = 12
    MONO_SIZE = 11
    TAB_SIZE = 12


THEME = TitanTheme()


def apply_titan_theme(window, accent: str = THEME.CYAN):
    """Apply the standard dark theme to any QMainWindow."""
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(THEME.BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(THEME.TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(THEME.BG_CARD))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(THEME.BG_CARD2))
    pal.setColor(QPalette.ColorRole.Text, QColor(THEME.TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(THEME.BG_CARD))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(THEME.TEXT))
    window.setPalette(pal)
    window.setStyleSheet(f"""
        QMainWindow {{ background: {THEME.BG}; }}
        QGroupBox {{
            background: {THEME.BG_CARD}; border: 1px solid {THEME.BORDER};
            border-radius: 10px; margin-top: 16px; padding-top: 20px;
            color: {THEME.TEXT}; font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; left: 12px; padding: 0 6px;
            color: {accent};
        }}
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background: {THEME.BG_CARD2}; color: {THEME.TEXT};
            border: 1px solid {THEME.BORDER_FOCUS}; border-radius: 6px;
            padding: 8px; font-size: {THEME.BODY_SIZE}px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 1px solid {accent};
        }}
        QTextEdit, QPlainTextEdit {{
            background: {THEME.BG_INPUT}; color: {THEME.TEXT};
            border: 1px solid {THEME.BORDER}; border-radius: 6px;
        }}
        QTableWidget {{
            background: {THEME.BG_INPUT}; color: {THEME.TEXT};
            gridline-color: {THEME.BORDER}; border: none;
        }}
        QHeaderView::section {{
            background: {THEME.BG_CARD}; color: {accent};
            padding: 6px; border: none; font-weight: bold;
        }}
        QLabel {{ background: transparent; }}
        QScrollArea {{ border: none; }}
        QProgressBar {{
            background: {THEME.BG_CARD2}; border: none; border-radius: 4px;
            text-align: center; color: {THEME.TEXT};
        }}
        QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
        QCheckBox {{ color: {THEME.TEXT}; }}
        QSlider::groove:horizontal {{
            background: {THEME.BG_CARD2}; height: 6px; border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {accent}; width: 16px; height: 16px;
            margin: -5px 0; border-radius: 8px;
        }}
    """)


def make_tab_style(accent: str = THEME.CYAN) -> str:
    """Return QTabWidget stylesheet string."""
    return f"""
        QTabBar::tab {{
            padding: 10px 24px; min-width: 140px;
            background: {THEME.BG_CARD}; color: {THEME.TEXT_DIM};
            border: none; border-bottom: 2px solid transparent;
            font-weight: bold; font-size: {THEME.TAB_SIZE}px;
        }}
        QTabBar::tab:selected {{
            color: {accent}; border-bottom: 2px solid {accent};
        }}
        QTabBar::tab:hover {{ color: {THEME.TEXT}; }}
        QTabWidget::pane {{ border: none; }}
    """


def make_btn(text: str, color: str, fg: str = "white", bold: bool = True) -> str:
    """Return QPushButton stylesheet string."""
    weight = "bold" if bold else "normal"
    return f"background: {color}; color: {fg}; padding: 8px 16px; border-radius: 6px; font-weight: {weight};"


def make_mono_display() -> str:
    """Return stylesheet for monospace read-only displays."""
    return f"font-family: '{THEME.FONT_MONO}'; font-size: {THEME.MONO_SIZE}px; background: {THEME.BG_INPUT}; color: {THEME.TEXT}; border: 1px solid {THEME.BORDER}; border-radius: 6px;"


def status_dot(available: bool) -> str:
    """Return colored dot for module status indicators."""
    color = THEME.GREEN if available else THEME.RED
    return f"color: {color}; font-size: 10px;"
