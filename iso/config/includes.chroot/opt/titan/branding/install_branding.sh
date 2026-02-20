#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# TITAN V7.5 SINGULARITY — Branding Installer
# Installs wallpapers, icons, desktop shortcuts, GRUB theme,
# login screen, and XFCE desktop configuration.
#
# Usage: sudo bash /opt/titan/branding/install_branding.sh
# ═══════════════════════════════════════════════════════════════════

set -e

BRAND_DIR="/opt/titan/branding"
CYAN='\033[96m'
GREEN='\033[92m'
ORANGE='\033[93m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║  TITAN V7.5 — BRANDING INSTALLER              ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Generate PNG assets ──────────────────────────────────
echo -e "${CYAN}[1/7]${NC} Generating branding assets..."
if command -v python3 &>/dev/null; then
    python3 "$BRAND_DIR/generate_branding.py" "$BRAND_DIR"
else
    echo "  [!] Python3 not found — skipping asset generation"
    echo "      Run manually: python3 $BRAND_DIR/generate_branding.py"
fi

# ── Step 2: Install wallpapers ───────────────────────────────────
echo -e "\n${CYAN}[2/7]${NC} Installing wallpapers..."
WALL_DIR="/usr/share/backgrounds/titan"
mkdir -p "$WALL_DIR"
if [ -d "$BRAND_DIR/wallpapers" ]; then
    cp -f "$BRAND_DIR/wallpapers"/*.png "$WALL_DIR/" 2>/dev/null && \
        echo -e "  ${GREEN}✓${NC} Wallpapers installed to $WALL_DIR" || \
        echo "  [!] No wallpaper PNGs found — run generate_branding.py first"
fi

# ── Step 3: Install desktop shortcuts ────────────────────────────
echo -e "\n${CYAN}[3/7]${NC} Installing desktop shortcuts..."
DESKTOP_DIR="/usr/share/applications"
HOME_DESKTOP="$HOME/Desktop"
mkdir -p "$DESKTOP_DIR" "$HOME_DESKTOP" 2>/dev/null

for f in "$BRAND_DIR/desktop"/*.desktop; do
    [ -f "$f" ] || continue
    cp -f "$f" "$DESKTOP_DIR/"
    cp -f "$f" "$HOME_DESKTOP/" 2>/dev/null
    chmod +x "$HOME_DESKTOP/$(basename "$f")" 2>/dev/null
    echo -e "  ${GREEN}✓${NC} $(basename "$f")"
done

# Also install for user 'user' if exists
if id "user" &>/dev/null; then
    USER_DESKTOP="/home/user/Desktop"
    mkdir -p "$USER_DESKTOP" 2>/dev/null
    for f in "$BRAND_DIR/desktop"/*.desktop; do
        [ -f "$f" ] || continue
        cp -f "$f" "$USER_DESKTOP/"
        chmod +x "$USER_DESKTOP/$(basename "$f")" 2>/dev/null
    done
    chown -R user:user "$USER_DESKTOP" 2>/dev/null
fi

# ── Step 4: Install GRUB theme ───────────────────────────────────
echo -e "\n${CYAN}[4/7]${NC} Installing GRUB theme..."
GRUB_THEME_DIR="/boot/grub/themes/titan"
if [ -d "/boot/grub" ]; then
    mkdir -p "$GRUB_THEME_DIR"
    cp -f "$BRAND_DIR/grub/theme.txt" "$GRUB_THEME_DIR/"
    [ -f "$BRAND_DIR/grub/titan_grub_bg.png" ] && \
        cp -f "$BRAND_DIR/grub/titan_grub_bg.png" "$GRUB_THEME_DIR/"

    # Update GRUB config
    GRUB_DEFAULT="/etc/default/grub"
    if [ -f "$GRUB_DEFAULT" ]; then
        if ! grep -q "GRUB_THEME" "$GRUB_DEFAULT"; then
            echo "GRUB_THEME=\"$GRUB_THEME_DIR/theme.txt\"" >> "$GRUB_DEFAULT"
        else
            sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$GRUB_THEME_DIR/theme.txt\"|" "$GRUB_DEFAULT"
        fi
        # Set background color
        if ! grep -q "GRUB_BACKGROUND" "$GRUB_DEFAULT"; then
            echo "GRUB_BACKGROUND=\"$GRUB_THEME_DIR/titan_grub_bg.png\"" >> "$GRUB_DEFAULT"
        fi
        update-grub 2>/dev/null && \
            echo -e "  ${GREEN}✓${NC} GRUB theme installed and updated" || \
            echo -e "  ${ORANGE}!${NC} GRUB config updated (run update-grub manually)"
    fi
else
    echo "  [!] /boot/grub not found — skipping GRUB theme"
fi

# ── Step 5: Configure XFCE desktop ──────────────────────────────
echo -e "\n${CYAN}[5/7]${NC} Configuring XFCE desktop..."

configure_xfce_for_user() {
    local user_home="$1"
    local xfce_dir="$user_home/.config/xfce4/xfconf/xfce-perchannel-xml"
    mkdir -p "$xfce_dir"

    # Set wallpaper
    cat > "$xfce_dir/xfce4-desktop.xml" << 'XFCE_DESKTOP'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVirtual-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/usr/share/backgrounds/titan/titan_wallpaper_1920x1080.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.039216"/>
            <value type="double" value="0.054902"/>
            <value type="double" value="0.090196"/>
            <value type="double" value="1.000000"/>
          </rgba1>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/usr/share/backgrounds/titan/titan_wallpaper_1920x1080.png"/>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
    </property>
  </property>
</channel>
XFCE_DESKTOP

    # Dark theme + panel styling
    cat > "$xfce_dir/xsettings.xml" << 'XFCE_SETTINGS'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Adwaita-dark"/>
    <property name="IconThemeName" type="string" value="Papirus-Dark"/>
    <property name="CursorThemeName" type="string" value="Adwaita"/>
    <property name="CursorSize" type="int" value="24"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="FontName" type="string" value="JetBrains Mono 10"/>
    <property name="MonospaceFontName" type="string" value="JetBrains Mono 10"/>
    <property name="CursorThemeName" type="string" value="Adwaita"/>
  </property>
  <property name="Xft" type="empty">
    <property name="Antialias" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintslight"/>
    <property name="RGBA" type="string" value="rgb"/>
    <property name="Lcdfilter" type="string" value="lcddefault"/>
  </property>
</channel>
XFCE_SETTINGS

    # Window manager theme
    cat > "$xfce_dir/xfwm4.xml" << 'XFCE_WM'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Adwaita-dark"/>
    <property name="title_font" type="string" value="JetBrains Mono Bold 10"/>
    <property name="use_compositing" type="bool" value="false"/>
    <property name="title_alignment" type="string" value="center"/>
  </property>
</channel>
XFCE_WM

    echo -e "  ${GREEN}✓${NC} XFCE configured for $(basename "$user_home")"
}

# Configure for root
configure_xfce_for_user "$HOME"

# Configure for 'user' if exists
if [ -d "/home/user" ]; then
    configure_xfce_for_user "/home/user"
    chown -R user:user /home/user/.config 2>/dev/null
fi

# ── Step 6: Configure LightDM/login screen ──────────────────────
echo -e "\n${CYAN}[6/7]${NC} Configuring login screen..."
LIGHTDM_CONF="/etc/lightdm/lightdm-gtk-greeter.conf"
if [ -d "/etc/lightdm" ]; then
    mkdir -p /etc/lightdm
    cat > "$LIGHTDM_CONF" << LIGHTDM
[greeter]
background=/usr/share/backgrounds/titan/titan_lockscreen_1920x1080.png
theme-name=Adwaita-dark
icon-theme-name=Papirus-Dark
font-name=JetBrains Mono 11
xft-antialias=true
xft-hintstyle=hintslight
position=50%,center 50%,center
panel-position=bottom
clock-format=%H:%M  |  %Y-%m-%d
indicators=~host;~spacer;~clock;~spacer;~session;~power
LIGHTDM
    echo -e "  ${GREEN}✓${NC} LightDM greeter configured"
else
    echo "  [!] LightDM not found — skipping login screen"
fi

# ── Step 7: Set GTK theme globally ───────────────────────────────
echo -e "\n${CYAN}[7/7]${NC} Setting global GTK dark theme..."
GTK3_SETTINGS="/etc/gtk-3.0/settings.ini"
mkdir -p /etc/gtk-3.0
cat > "$GTK3_SETTINGS" << GTK3
[Settings]
gtk-theme-name=Adwaita-dark
gtk-icon-theme-name=Papirus-Dark
gtk-font-name=JetBrains Mono 10
gtk-cursor-theme-name=Adwaita
gtk-cursor-theme-size=24
gtk-application-prefer-dark-theme=1
gtk-xft-antialias=1
gtk-xft-hinting=1
gtk-xft-hintstyle=hintslight
gtk-xft-rgba=rgb
GTK3
echo -e "  ${GREEN}✓${NC} GTK3 dark theme set globally"

# GTK2
GTK2_RC="/etc/gtk-2.0/gtkrc"
mkdir -p /etc/gtk-2.0
cat > "$GTK2_RC" << GTK2
gtk-theme-name="Adwaita-dark"
gtk-icon-theme-name="Papirus-Dark"
gtk-font-name="JetBrains Mono 10"
gtk-cursor-theme-name="Adwaita"
gtk-cursor-theme-size=24
GTK2
echo -e "  ${GREEN}✓${NC} GTK2 dark theme set globally"

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}  ╔══════════════════════════════════════════════════╗"
echo -e "  ║  BRANDING INSTALLATION COMPLETE                  ║"
echo -e "  ╠══════════════════════════════════════════════════╣"
echo -e "  ║                                                  ║"
echo -e "  ║  ✓ Wallpapers     → /usr/share/backgrounds/     ║"
echo -e "  ║  ✓ Desktop icons  → /usr/share/applications/    ║"
echo -e "  ║  ✓ GRUB theme     → /boot/grub/themes/titan/    ║"
echo -e "  ║  ✓ XFCE desktop   → Dark theme + wallpaper      ║"
echo -e "  ║  ✓ Login screen   → LightDM branded             ║"
echo -e "  ║  ✓ GTK theme      → Adwaita-dark globally       ║"
echo -e "  ║                                                  ║"
echo -e "  ║  Reboot or log out/in to see all changes.       ║"
echo -e "  ╚══════════════════════════════════════════════════╝${NC}"
echo ""
