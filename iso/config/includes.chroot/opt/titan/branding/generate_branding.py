#!/usr/bin/env python3
"""
TITAN V7.0.3 SINGULARITY — Branding Asset Generator
Generates wallpapers, splash screens, and login backgrounds
using PIL/Pillow with cyberpunk aesthetic.

Usage:
    python3 generate_branding.py [--output-dir /opt/titan/branding]

Generates:
    wallpapers/titan_wallpaper_1920x1080.png
    wallpapers/titan_wallpaper_2560x1440.png
    wallpapers/titan_wallpaper_lock_1920x1080.png
    splash/titan_splash.png
    splash/titan_boot_splash.png
"""

import math
import random
import struct
import zlib
import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# PURE PYTHON PNG WRITER (no Pillow dependency)
# ═══════════════════════════════════════════════════════════════════

class PNGWriter:
    """Minimal PNG writer — no external dependencies."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = [[(0, 0, 0)] * width for _ in range(height)]

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = color

    def fill_rect(self, x, y, w, h, color):
        for py in range(max(0, y), min(self.height, y + h)):
            for px in range(max(0, x), min(self.width, x + w)):
                self.pixels[py][px] = color

    def blend_pixel(self, x, y, color, alpha):
        if 0 <= x < self.width and 0 <= y < self.height:
            bg = self.pixels[y][x]
            r = int(bg[0] * (1 - alpha) + color[0] * alpha)
            g = int(bg[1] * (1 - alpha) + color[1] * alpha)
            b = int(bg[2] * (1 - alpha) + color[2] * alpha)
            self.pixels[y][x] = (min(255, r), min(255, g), min(255, b))

    def draw_line(self, x0, y0, x1, y1, color, alpha=1.0, thickness=1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for t in range(-thickness // 2, thickness // 2 + 1):
                self.blend_pixel(x0 + t, y0, color, alpha)
                self.blend_pixel(x0, y0 + t, color, alpha)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def draw_circle(self, cx, cy, r, color, alpha=1.0, filled=False):
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                dist = math.sqrt(x * x + y * y)
                if filled:
                    if dist <= r:
                        a = alpha * max(0, 1 - max(0, dist - r + 1))
                        self.blend_pixel(cx + x, cy + y, color, a)
                else:
                    if abs(dist - r) < 1.5:
                        a = alpha * max(0, 1 - abs(dist - r))
                        self.blend_pixel(cx + x, cy + y, color, a)

    def draw_hex(self, cx, cy, size, color, alpha=0.3, thickness=1):
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            px = int(cx + size * math.cos(angle))
            py = int(cy + size * math.sin(angle))
            points.append((px, py))
        for i in range(6):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % 6]
            self.draw_line(x0, y0, x1, y1, color, alpha, thickness)

    def save(self, filepath):
        raw = b''
        for row in self.pixels:
            raw += b'\x00'  # filter byte
            for r, g, b in row:
                raw += struct.pack('BBB', r, g, b)

        def make_chunk(chunk_type, data):
            chunk = chunk_type + data
            return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)

        png = b'\x89PNG\r\n\x1a\n'
        png += make_chunk(b'IHDR', struct.pack('>IIBBBBB', self.width, self.height, 8, 2, 0, 0, 0))
        compressed = zlib.compress(raw, 9)
        png += make_chunk(b'IDAT', compressed)
        png += make_chunk(b'IEND', b'')

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(png)
        print(f"  [+] Saved: {filepath} ({os.path.getsize(filepath) // 1024}KB)")


# ═══════════════════════════════════════════════════════════════════
# COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════

COLORS = {
    "bg_deep":      (10, 14, 23),
    "bg_mid":       (13, 21, 37),
    "bg_light":     (18, 28, 48),
    "cyan":         (0, 212, 255),
    "cyan_dim":     (0, 100, 130),
    "cyan_dark":    (0, 50, 70),
    "orange":       (255, 107, 53),
    "orange_dim":   (130, 55, 25),
    "green":        (0, 255, 136),
    "purple":       (156, 39, 176),
    "white":        (220, 230, 240),
    "grid":         (20, 35, 55),
    "grid_bright":  (30, 50, 75),
}


# ═══════════════════════════════════════════════════════════════════
# WALLPAPER GENERATOR
# ═══════════════════════════════════════════════════════════════════

def generate_wallpaper(width, height, filepath, variant="main"):
    """Generate a cyberpunk wallpaper."""
    print(f"\n  Generating {width}x{height} wallpaper ({variant})...")
    img = PNGWriter(width, height)

    # Background gradient (radial from center)
    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
            t = min(1.0, dist)
            r = int(COLORS["bg_mid"][0] * (1 - t) + COLORS["bg_deep"][0] * t)
            g = int(COLORS["bg_mid"][1] * (1 - t) + COLORS["bg_deep"][1] * t)
            b = int(COLORS["bg_mid"][2] * (1 - t) + COLORS["bg_deep"][2] * t)
            img.pixels[y][x] = (r, g, b)

    # Grid pattern
    grid_spacing = 60
    for y in range(0, height, grid_spacing):
        for x in range(width):
            dist = abs(y - cy) / (height / 2)
            alpha = max(0.02, 0.08 * (1 - dist))
            img.blend_pixel(x, y, COLORS["grid_bright"], alpha)
    for x in range(0, width, grid_spacing):
        for y in range(height):
            dist = abs(x - cx) / (width / 2)
            alpha = max(0.02, 0.08 * (1 - dist))
            img.blend_pixel(x, y, COLORS["grid_bright"], alpha)

    # Hex grid pattern (background texture)
    hex_size = 45
    rng = random.Random(42)
    for row in range(-2, height // (hex_size * 2) + 3):
        for col in range(-2, width // (int(hex_size * 1.73)) + 3):
            hx = int(col * hex_size * 1.73 + (row % 2) * hex_size * 0.866)
            hy = int(row * hex_size * 1.5)
            dist = math.sqrt((hx - cx) ** 2 + (hy - cy) ** 2) / max_dist
            alpha = max(0.02, 0.12 * (1 - dist))
            if rng.random() < 0.7:
                img.draw_hex(hx, hy, hex_size, COLORS["cyan_dark"], alpha)

    # Central glow (radial gradient)
    glow_radius = min(width, height) // 3
    for y in range(max(0, cy - glow_radius), min(height, cy + glow_radius)):
        for x in range(max(0, cx - glow_radius), min(width, cx + glow_radius)):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < glow_radius:
                alpha = 0.06 * (1 - dist / glow_radius) ** 2
                img.blend_pixel(x, y, COLORS["cyan"], alpha)

    # Circuit traces
    rng2 = random.Random(7)
    for _ in range(25):
        sx = rng2.randint(0, width)
        sy = rng2.randint(0, height)
        length = rng2.randint(80, 300)
        direction = rng2.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
        dist = math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2) / max_dist
        alpha = max(0.05, 0.2 * (1 - dist))
        color = COLORS["cyan_dim"] if rng2.random() > 0.3 else COLORS["orange_dim"]
        ex = sx + direction[0] * length
        ey = sy + direction[1] * length
        img.draw_line(sx, sy, ex, ey, color, alpha)
        # Node at end
        img.draw_circle(ex, ey, 3, color, alpha * 1.5, filled=True)

    # Floating particles
    for _ in range(60):
        px = rng2.randint(0, width)
        py = rng2.randint(0, height)
        size = rng2.randint(1, 3)
        color = COLORS["cyan"] if rng2.random() > 0.2 else COLORS["orange"]
        alpha = rng2.uniform(0.1, 0.5)
        img.draw_circle(px, py, size, color, alpha, filled=True)

    # Large decorative hex rings
    img.draw_hex(cx, cy, min(width, height) // 4, COLORS["cyan"], 0.08, 2)
    img.draw_hex(cx, cy, min(width, height) // 3, COLORS["cyan"], 0.05, 1)

    # Corner accents
    corner_size = 80
    # Top-left
    img.draw_line(0, 0, corner_size, 0, COLORS["cyan"], 0.3)
    img.draw_line(0, 0, 0, corner_size, COLORS["cyan"], 0.3)
    # Top-right
    img.draw_line(width - 1, 0, width - corner_size, 0, COLORS["cyan"], 0.3)
    img.draw_line(width - 1, 0, width - 1, corner_size, COLORS["cyan"], 0.3)
    # Bottom-left
    img.draw_line(0, height - 1, corner_size, height - 1, COLORS["cyan"], 0.3)
    img.draw_line(0, height - 1, 0, height - corner_size, COLORS["cyan"], 0.3)
    # Bottom-right
    img.draw_line(width - 1, height - 1, width - corner_size, height - 1, COLORS["cyan"], 0.3)
    img.draw_line(width - 1, height - 1, width - 1, height - corner_size, COLORS["cyan"], 0.3)

    # Scan lines (subtle CRT effect)
    for y in range(0, height, 3):
        for x in range(width):
            img.blend_pixel(x, y, (0, 0, 0), 0.03)

    if variant == "lock":
        # Add darker overlay for lock screen
        for y in range(height):
            for x in range(width):
                img.blend_pixel(x, y, (0, 0, 0), 0.25)

    img.save(filepath)


# ═══════════════════════════════════════════════════════════════════
# SPLASH SCREEN GENERATOR
# ═══════════════════════════════════════════════════════════════════

def generate_splash(width, height, filepath):
    """Generate boot/app splash screen."""
    print(f"\n  Generating {width}x{height} splash screen...")
    img = PNGWriter(width, height)

    cx, cy = width // 2, height // 2

    # Dark background with subtle radial glow
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (max(width, height) / 2)
            t = min(1.0, dist)
            r = int(13 * (1 - t) + 6 * t)
            g = int(21 * (1 - t) + 8 * t)
            b = int(37 * (1 - t) + 14 * t)
            img.pixels[y][x] = (r, g, b)

    # Central hex
    img.draw_hex(cx, cy - 30, 80, COLORS["cyan"], 0.25, 2)
    img.draw_hex(cx, cy - 30, 60, COLORS["cyan"], 0.15, 1)

    # Central glow
    for y2 in range(max(0, cy - 100), min(height, cy + 70)):
        for x2 in range(max(0, cx - 100), min(width, cx + 100)):
            dist = math.sqrt((x2 - cx) ** 2 + (y2 - (cy - 30)) ** 2)
            if dist < 90:
                alpha = 0.08 * (1 - dist / 90) ** 2
                img.blend_pixel(x2, y2, COLORS["cyan"], alpha)

    # T letterform (centered)
    t_width = 100
    t_height = 16
    t_stem_w = 20
    t_stem_h = 90
    # Horizontal bar
    for y2 in range(cy - 60, cy - 60 + t_height):
        for x2 in range(cx - t_width // 2, cx + t_width // 2):
            img.blend_pixel(x2, y2, COLORS["cyan"], 0.9)
    # Vertical stem
    for y2 in range(cy - 60, cy - 60 + t_stem_h):
        for x2 in range(cx - t_stem_w // 2, cx + t_stem_w // 2):
            img.blend_pixel(x2, y2, COLORS["cyan"], 0.9)

    # Orange accent dot
    img.draw_circle(cx, cy - 72, 4, COLORS["orange"], 0.9, filled=True)

    # Loading bar area (bottom)
    bar_y = cy + 80
    bar_w = 200
    bar_h = 4
    # Bar background
    for y2 in range(bar_y, bar_y + bar_h):
        for x2 in range(cx - bar_w // 2, cx + bar_w // 2):
            img.blend_pixel(x2, y2, COLORS["cyan_dark"], 0.5)

    # Scan lines
    for y in range(0, height, 3):
        for x in range(width):
            img.blend_pixel(x, y, (0, 0, 0), 0.04)

    img.save(filepath)


# ═══════════════════════════════════════════════════════════════════
# GRUB THEME BACKGROUND
# ═══════════════════════════════════════════════════════════════════

def generate_grub_bg(filepath):
    """Generate GRUB boot menu background (1024x768)."""
    width, height = 1024, 768
    print(f"\n  Generating GRUB background {width}x{height}...")
    img = PNGWriter(width, height)

    cx, cy = width // 2, height // 2

    # Deep dark background
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (max(width, height) / 2)
            t = min(1.0, dist)
            r = int(10 * (1 - t) + 5 * t)
            g = int(16 * (1 - t) + 8 * t)
            b = int(28 * (1 - t) + 12 * t)
            img.pixels[y][x] = (r, g, b)

    # Subtle grid
    for y in range(0, height, 40):
        for x in range(width):
            img.blend_pixel(x, y, COLORS["grid"], 0.1)
    for x in range(0, width, 40):
        for y in range(height):
            img.blend_pixel(x, y, COLORS["grid"], 0.1)

    # Hex pattern
    img.draw_hex(cx, cy - 80, 120, COLORS["cyan"], 0.1, 2)

    # Corner brackets
    for corner_x, corner_y, dx, dy in [(0, 0, 1, 1), (width-1, 0, -1, 1),
                                         (0, height-1, 1, -1), (width-1, height-1, -1, -1)]:
        for i in range(50):
            img.blend_pixel(corner_x + dx * i, corner_y, COLORS["cyan"], 0.25)
            img.blend_pixel(corner_x, corner_y + dy * i, COLORS["cyan"], 0.25)

    # Scan lines
    for y in range(0, height, 2):
        for x in range(width):
            img.blend_pixel(x, y, (0, 0, 0), 0.05)

    img.save(filepath)


# ═══════════════════════════════════════════════════════════════════
# APP ICON GENERATOR (simple colored hex icons per app)
# ═══════════════════════════════════════════════════════════════════

def generate_app_icon(size, filepath, accent_color, letter):
    """Generate a hex-shaped app icon with a letter."""
    print(f"  Generating app icon: {filepath}")
    img = PNGWriter(size, size)
    cx, cy = size // 2, size // 2

    # Background
    for y in range(size):
        for x in range(size):
            img.pixels[y][x] = COLORS["bg_deep"]

    # Hex shape
    hex_r = size // 2 - 4
    img.draw_hex(cx, cy, hex_r, accent_color, 0.6, 2)
    img.draw_hex(cx, cy, hex_r - 6, accent_color, 0.2, 1)

    # Inner glow
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < hex_r - 8:
                alpha = 0.05 * (1 - dist / (hex_r - 8))
                img.blend_pixel(x, y, accent_color, alpha)

    img.save(filepath)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent

    print("=" * 60)
    print("  TITAN V7.0.3 SINGULARITY — Branding Asset Generator")
    print("=" * 60)

    # Wallpapers
    generate_wallpaper(1920, 1080, str(output_dir / "wallpapers" / "titan_wallpaper_1920x1080.png"))
    generate_wallpaper(2560, 1440, str(output_dir / "wallpapers" / "titan_wallpaper_2560x1440.png"))
    generate_wallpaper(1920, 1080, str(output_dir / "wallpapers" / "titan_lockscreen_1920x1080.png"), variant="lock")

    # Splash screens
    generate_splash(600, 400, str(output_dir / "splash" / "titan_splash.png"))
    generate_splash(1920, 1080, str(output_dir / "splash" / "titan_boot_splash.png"))

    # GRUB background
    generate_grub_bg(str(output_dir / "grub" / "titan_grub_bg.png"))

    # App icons (48x48)
    icons = [
        ("titan_unified.png", COLORS["cyan"], "U"),
        ("titan_genesis.png", COLORS["orange"], "G"),
        ("titan_cerberus.png", (0, 188, 212), "C"),
        ("titan_kyc.png", COLORS["purple"], "K"),
        ("titan_bug_reporter.png", (85, 136, 255), "B"),
        ("titan_mission_control.png", COLORS["cyan"], "M"),
        ("titan_browser.png", COLORS["green"], "W"),
    ]
    for fname, color, letter in icons:
        generate_app_icon(48, str(output_dir / "icons" / fname), color, letter)
        generate_app_icon(128, str(output_dir / "icons" / fname.replace(".png", "_128.png")), color, letter)

    print("\n" + "=" * 60)
    print("  BRANDING GENERATION COMPLETE")
    print(f"  Output: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
