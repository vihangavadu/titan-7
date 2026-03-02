#!/usr/bin/env python3
"""
TITAN X — Branding Asset Generator
Generates wallpapers, icons, xrdp login bitmaps, all programmatically.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Colors
BG_DARK = (10, 14, 23)        # #0a0e17
BG_CARD = (17, 24, 39)        # #111827
ACCENT = (0, 212, 255)        # #00d4ff
ACCENT_DIM = (0, 106, 128)    # dimmed cyan
ORANGE = (255, 107, 53)       # #ff6b35
TEXT_PRIMARY = (226, 232, 240) # #e2e8f0
TEXT_SECONDARY = (100, 116, 139)
GREEN = (34, 197, 94)
GRID_LINE = (20, 30, 50)


def get_font(size, bold=False):
    """Get best available font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]
    for f in candidates:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def get_mono_font(size):
    """Get monospace font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for f in candidates:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def draw_hex_grid(draw, w, h, spacing=80, color=GRID_LINE):
    """Draw subtle hexagonal grid pattern."""
    for y in range(-spacing, h + spacing, spacing):
        for x in range(-spacing, w + spacing, spacing):
            offset_x = (spacing // 2) if (y // spacing) % 2 else 0
            cx, cy = x + offset_x, y
            size = spacing // 3
            points = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                px = cx + size * math.cos(angle)
                py = cy + size * math.sin(angle)
                points.append((px, py))
            draw.polygon(points, outline=color)


def draw_circuit_lines(draw, w, h):
    """Draw subtle circuit board traces."""
    import random
    random.seed(42)
    for _ in range(30):
        x = random.randint(0, w)
        y = random.randint(0, h)
        length = random.randint(40, 200)
        if random.random() > 0.5:
            draw.line([(x, y), (x + length, y)], fill=(15, 25, 45), width=1)
            draw.ellipse([x + length - 2, y - 2, x + length + 2, y + 2], fill=ACCENT_DIM)
        else:
            draw.line([(x, y), (x, y + length)], fill=(15, 25, 45), width=1)
            draw.ellipse([x - 2, y + length - 2, x + 2, y + length + 2], fill=ACCENT_DIM)


def draw_titan_t(draw, cx, cy, size, color=ACCENT):
    """Draw the iconic T letterform."""
    bar_w = size
    bar_h = size // 8
    stem_w = size // 5
    stem_h = size * 3 // 4
    # Horizontal bar
    draw.rounded_rectangle(
        [cx - bar_w // 2, cy - stem_h // 2, cx + bar_w // 2, cy - stem_h // 2 + bar_h],
        radius=4, fill=color
    )
    # Vertical stem
    draw.rounded_rectangle(
        [cx - stem_w // 2, cy - stem_h // 2, cx + stem_w // 2, cy + stem_h // 2],
        radius=4, fill=color
    )


def generate_wallpaper(width, height, output_path):
    """Generate Titan X desktop wallpaper."""
    img = Image.new("RGB", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Gradient overlay (darker at edges)
    for y in range(height):
        for x in range(0, width, 4):
            dist_center = math.sqrt((x - width/2)**2 + (y - height/2)**2)
            max_dist = math.sqrt((width/2)**2 + (height/2)**2)
            factor = min(dist_center / max_dist, 1.0)
            darken = int(factor * 8)
            r = max(BG_DARK[0] - darken, 0)
            g = max(BG_DARK[1] - darken, 0)
            b = max(BG_DARK[2] - darken, 0)
            draw.rectangle([x, y, x + 3, y], fill=(r, g, b))

    # Hex grid
    draw_hex_grid(draw, width, height, spacing=120, color=(15, 22, 35))

    # Circuit traces
    draw_circuit_lines(draw, width, height)

    # Central T icon
    draw_titan_t(draw, width // 2, height // 2 - 40, 200)

    # Glow effect around T
    glow = Image.new("RGB", (width, height), (0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    draw_titan_t(glow_draw, width // 2, height // 2 - 40, 200, color=(0, 100, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=30))
    img = Image.composite(img, Image.new("RGB", (width, height), BG_DARK),
                          glow.convert("L"))
    draw = ImageDraw.Draw(img)

    # Redraw T on top of glow
    draw_titan_t(draw, width // 2, height // 2 - 40, 200)

    # Title text
    font_title = get_font(72, bold=True)
    font_sub = get_font(22)
    font_mono = get_mono_font(16)

    # "TITAN X" text
    draw.text((width // 2, height // 2 + 100), "TITAN X", fill=ACCENT,
              font=font_title, anchor="mm")

    # Subtitle
    draw.text((width // 2, height // 2 + 150), "V10.0  SINGULARITY",
              fill=TEXT_SECONDARY, font=font_sub, anchor="mm")

    # Bottom bar
    bar_y = height - 50
    draw.line([(50, bar_y), (width - 50, bar_y)], fill=(20, 30, 45), width=1)
    draw.text((60, bar_y + 10), "117 MODULES", fill=TEXT_SECONDARY, font=font_mono)
    draw.text((width // 2, bar_y + 10), "11 APPS", fill=TEXT_SECONDARY,
              font=font_mono, anchor="mt")
    draw.text((width - 60, bar_y + 10), "ZERO ORPHANS", fill=TEXT_SECONDARY,
              font=font_mono, anchor="rt")

    # Corner accents
    corner_size = 40
    for cx, cy in [(30, 30), (width - 30, 30), (30, height - 30), (width - 30, height - 30)]:
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=ACCENT_DIM)

    img.save(output_path, "PNG", quality=95)
    print(f"  [+] Wallpaper: {output_path} ({width}x{height})")


def generate_icon(size, output_path):
    """Generate Titan X app icon at given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    margin = size // 16
    draw.ellipse([margin, margin, size - margin, size - margin], fill=BG_DARK,
                 outline=ACCENT, width=max(1, size // 64))

    # Shield hex shape
    cx, cy = size // 2, size // 2
    hex_size = int(size * 0.35)
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 90)
        px = cx + hex_size * math.cos(angle)
        py = cy + hex_size * math.sin(angle)
        points.append((px, py))
    draw.polygon(points, outline=ACCENT, fill=None, width=max(1, size // 48))

    # T letterform
    t_size = int(size * 0.4)
    draw_titan_t(draw, cx, cy, t_size)

    img.save(output_path, "PNG")
    print(f"  [+] Icon: {output_path} ({size}x{size})")


def generate_xrdp_logo(output_path):
    """Generate xrdp login screen logo (240x140 BMP)."""
    w, h = 240, 140
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # T icon
    draw_titan_t(draw, 60, h // 2, 60)

    # Text
    font_title = get_font(28, bold=True)
    font_sub = get_font(12)
    draw.text((110, h // 2 - 20), "TITAN X", fill=ACCENT, font=font_title)
    draw.text((110, h // 2 + 15), "V10.0 SINGULARITY", fill=TEXT_SECONDARY, font=font_sub)

    img.save(output_path, "BMP")
    print(f"  [+] xrdp logo: {output_path}")


def generate_xrdp_background(output_path):
    """Generate xrdp login background (BMP)."""
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Subtle gradient from center
    for y in range(h):
        for x in range(0, w, 8):
            dist = math.sqrt((x - w/2)**2 + (y - h/2)**2)
            max_dist = math.sqrt((w/2)**2 + (h/2)**2)
            factor = min(dist / max_dist, 1.0)
            darken = int(factor * 6)
            r = max(BG_DARK[0] - darken, 0)
            g = max(BG_DARK[1] - darken, 0)
            b = max(BG_DARK[2] - darken, 0)
            draw.rectangle([x, y, x + 7, y], fill=(r, g, b))

    # Hex grid
    draw_hex_grid(draw, w, h, spacing=150, color=(13, 20, 32))

    # Circuit lines
    draw_circuit_lines(draw, w, h)

    img.save(output_path, "BMP")
    print(f"  [+] xrdp background: {output_path}")


def main():
    base = "/opt/titan/branding"
    os.makedirs(f"{base}/wallpapers", exist_ok=True)
    os.makedirs(f"{base}/icons", exist_ok=True)
    os.makedirs(f"{base}/xrdp", exist_ok=True)

    print("[TITAN X] Generating branding assets...")
    print()

    # Wallpapers
    print("[1/4] Wallpapers")
    generate_wallpaper(1920, 1080, f"{base}/wallpapers/titan_wallpaper_1080.png")
    generate_wallpaper(2560, 1440, f"{base}/wallpapers/titan_wallpaper_1440.png")

    # Icons (multi-size)
    print("\n[2/4] Icons")
    for size in [16, 32, 48, 128, 256]:
        generate_icon(size, f"{base}/icons/titan-x-{size}.png")

    # xrdp login assets
    print("\n[3/4] xrdp login")
    generate_xrdp_logo(f"{base}/xrdp/titan_xrdp_logo.bmp")
    generate_xrdp_background(f"{base}/xrdp/titan_xrdp_bg.bmp")

    # Copy main icon for system use
    print("\n[4/4] System icon")
    icon_48 = f"{base}/icons/titan-x-48.png"
    targets = [
        "/usr/share/pixmaps/titan-x.png",
        "/usr/share/icons/hicolor/48x48/apps/titan-x.png",
    ]
    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        try:
            import shutil
            shutil.copy2(icon_48, t)
            print(f"  [+] Installed: {t}")
        except Exception as e:
            print(f"  [!] Failed: {t} -> {e}")

    # Also install multi-size icons
    size_map = {16: "16x16", 32: "32x32", 48: "48x48", 128: "128x128", 256: "256x256"}
    for size, dirname in size_map.items():
        target = f"/usr/share/icons/hicolor/{dirname}/apps/titan-x.png"
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            import shutil
            shutil.copy2(f"{base}/icons/titan-x-{size}.png", target)
        except Exception:
            pass

    print("\n[DONE] All branding assets generated.")


if __name__ == "__main__":
    main()
