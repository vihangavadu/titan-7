"""
TITAN V7.5 — Reusable Branded Splash Screen
Used by all GUI apps for consistent branding.

Usage:
    from titan_splash import show_titan_splash
    app = QApplication(sys.argv)
    splash = show_titan_splash(app, "GENESIS ENGINE", "#ff6b35")
    window = MyMainWindow()
    window.show()
    if splash: splash.finish(window)
"""

from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen
from PyQt6.QtCore import Qt


def show_titan_splash(app: QApplication, subtitle: str = "OPERATION CENTER",
                      accent_hex: str = "#00d4ff") -> QSplashScreen:
    """
    Show a branded Titan splash screen.

    Args:
        app: QApplication instance
        subtitle: App subtitle text (e.g. "GENESIS ENGINE")
        accent_hex: Accent color hex string (e.g. "#ff6b35")

    Returns:
        QSplashScreen instance (call .finish(window) after main window shows)
    """
    try:
        accent = QColor(accent_hex)
        accent_dim = QColor(accent_hex)
        accent_dim.setAlpha(150)

        W, H = 580, 360
        pix = QPixmap(W, H)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background — Enterprise Slate
        grad = QLinearGradient(0, 0, W, H)
        grad.setColorAt(0, QColor(21, 26, 33))   # #151A21 Slate UI
        grad.setColorAt(1, QColor(28, 35, 48))    # #1C2330 Panel BG
        p.fillRect(0, 0, W, H, grad)

        # Double border
        p.setPen(QPen(QColor(accent_hex + "28"), 1))
        p.drawRect(2, 2, W - 4, H - 4)
        p.setPen(QPen(QColor(accent_hex + "10"), 1))
        p.drawRect(8, 8, W - 16, H - 16)

        # Corner accents
        p.setPen(QPen(accent, 1.5))
        corners = [(0, 0, 1, 1), (W - 1, 0, -1, 1), (0, H - 1, 1, -1), (W - 1, H - 1, -1, -1)]
        for cx, cy, dx, dy in corners:
            p.drawLine(cx, cy, cx + dx * 45, cy)
            p.drawLine(cx, cy, cx, cy + dy * 45)

        # Primary accent dot at top center
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(58, 117, 196))  # #3A75C4 Corporate Trust Blue
        p.drawEllipse(W // 2 - 6, 52, 12, 12)

        # TITAN title
        p.setPen(accent)
        p.setFont(QFont("Inter", 30, QFont.Weight.Bold))
        p.drawText(0, 70, W, 55, Qt.AlignmentFlag.AlignCenter, "TITAN")

        # Version
        p.setFont(QFont("Inter", 10))
        p.setPen(accent_dim)
        p.drawText(0, 125, W, 25, Qt.AlignmentFlag.AlignCenter, "V8.0  MAXIMUM LEVEL")

        # Subtitle (app name)
        p.setFont(QFont("Inter", 9))
        p.setPen(QColor(148, 163, 184))  # #94A3B8 Text Secondary
        p.drawText(0, 160, W, 22, Qt.AlignmentFlag.AlignCenter, subtitle)

        # Decorative line
        p.setPen(QPen(QColor(accent_hex + "30"), 1))
        p.drawLine(W // 2 - 80, 192, W // 2 + 80, 192)

        # Loading bar bg
        p.setPen(Qt.PenStyle.NoPen)
        bar_y = 245
        p.setBrush(QColor(42, 52, 68, 120))  # Surface color
        p.drawRoundedRect(140, bar_y, 300, 5, 2.5, 2.5)
        # Loading bar fill
        p.setBrush(accent)
        p.drawRoundedRect(140, bar_y, 180, 5, 2.5, 2.5)

        # Status
        p.setPen(QColor(100, 116, 139))  # #64748B Text Muted
        p.setFont(QFont("Inter", 8))
        p.drawText(0, bar_y + 14, W, 18, Qt.AlignmentFlag.AlignCenter, "Initializing modules...")

        # Footer
        p.setPen(QColor(71, 85, 105))  # #475569 Text Disabled
        p.setFont(QFont("Inter", 7))
        p.drawText(0, H - 30, W, 18, Qt.AlignmentFlag.AlignCenter,
                   "AUTHORITY: Dva.12  |  CODENAME: MAXIMUM LEVEL  |  BUILD: 8.0.0")

        # Scan lines
        p.setPen(QColor(0, 0, 0, 7))
        for y in range(0, H, 3):
            p.drawLine(0, y, W, y)

        p.end()

        splash = QSplashScreen(pix)
        splash.show()
        app.processEvents()
        return splash

    except Exception:
        return None
