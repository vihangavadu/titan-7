"""
TITAN V8.1 — Programmatic Window Icon Generator
Generates a branded hex icon via QPainter — no external files needed.

Usage:
    from titan_icon import set_titan_icon
    set_titan_icon(window, "#00d4ff")  # cyan accent
"""

from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon, QPen, QBrush
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QMainWindow
import math


def create_titan_pixmap(size: int = 64, accent_hex: str = "#00d4ff") -> QPixmap:
    """Create a branded Titan hex icon pixmap."""
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))  # transparent background

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx, cy = size / 2, size / 2
    accent = QColor(accent_hex)
    bg = QColor(10, 14, 23)
    margin = 2

    # Draw filled hex background
    hex_r = size / 2 - margin
    hex_points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        hex_points.append(QPointF(cx + hex_r * math.cos(angle), cy + hex_r * math.sin(angle)))

    from PyQt6.QtGui import QPolygonF
    polygon = QPolygonF(hex_points)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(bg))
    p.drawPolygon(polygon)

    # Hex border
    p.setPen(QPen(accent, max(1, size / 32)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolygon(polygon)

    # Inner hex (subtle)
    inner_r = hex_r * 0.78
    inner_points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        inner_points.append(QPointF(cx + inner_r * math.cos(angle), cy + inner_r * math.sin(angle)))
    inner_poly = QPolygonF(inner_points)
    accent_dim = QColor(accent)
    accent_dim.setAlpha(40)
    p.setPen(QPen(accent_dim, max(1, size / 64)))
    p.drawPolygon(inner_poly)

    # T letterform
    t_bar_w = size * 0.45
    t_bar_h = size * 0.08
    t_stem_w = size * 0.1
    t_stem_h = size * 0.38
    t_top = cy - size * 0.22

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(accent))
    # Horizontal bar
    p.drawRoundedRect(
        int(cx - t_bar_w / 2), int(t_top),
        int(t_bar_w), int(t_bar_h),
        t_bar_h / 3, t_bar_h / 3
    )
    # Vertical stem
    p.drawRoundedRect(
        int(cx - t_stem_w / 2), int(t_top),
        int(t_stem_w), int(t_stem_h),
        t_stem_w / 3, t_stem_w / 3
    )

    # Orange accent dot
    dot_r = max(2, size * 0.04)
    p.setBrush(QBrush(QColor(255, 107, 53)))
    p.drawEllipse(QPointF(cx, t_top - dot_r * 2.5), dot_r, dot_r)

    p.end()
    return pix


def set_titan_icon(window: QMainWindow, accent_hex: str = "#00d4ff"):
    """Set the Titan branded icon on a QMainWindow."""
    try:
        icon = QIcon()
        for size in [16, 24, 32, 48, 64, 128]:
            icon.addPixmap(create_titan_pixmap(size, accent_hex))
        window.setWindowIcon(icon)
    except Exception:
        pass
