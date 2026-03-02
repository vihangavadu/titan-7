#!/bin/bash
# TITAN X — xrdp Performance + Branding + Mobile Optimization
set -e

echo "[TITAN X] Configuring xrdp..."

XRDP_INI="/etc/xrdp/xrdp.ini"
STARTWM="/etc/xrdp/startwm.sh"

# 1. Performance tuning
echo "  [1/5] Performance tuning..."
sed -i 's/^max_bpp=.*/max_bpp=24/' "$XRDP_INI"
sed -i 's/^#*tcp_nodelay=.*/tcp_nodelay=true/' "$XRDP_INI"
sed -i 's/^#*tcp_keepalive=.*/tcp_keepalive=true/' "$XRDP_INI"
sed -i 's/^#*bulk_compression=.*/bulk_compression=true/' "$XRDP_INI"
sed -i 's/^#*bitmap_compression=.*/bitmap_compression=true/' "$XRDP_INI"
sed -i 's/^#*bitmap_cache=.*/bitmap_cache=true/' "$XRDP_INI"
sed -i 's/^crypt_level=.*/crypt_level=low/' "$XRDP_INI"
echo "  [+] max_bpp=24, compression on, crypt=low"

# 2. xrdp Login Screen Branding
echo "  [2/5] Login screen branding..."
sed -i 's|^#*ls_title=.*|ls_title=TITAN X V10.0|' "$XRDP_INI"
sed -i 's|^ls_logo_filename=.*|ls_logo_filename=/opt/titan/branding/xrdp/titan_xrdp_logo.bmp|' "$XRDP_INI"
# Set login background color to dark
sed -i 's|^#*ls_top_window_bg_color=.*|ls_top_window_bg_color=0a0e17|' "$XRDP_INI"
sed -i 's|^#*ls_bg_color=.*|ls_bg_color=0a0e17|' "$XRDP_INI"
sed -i 's|^#*ls_btn_ok_color=.*|ls_btn_ok_color=00d4ff|' "$XRDP_INI"
echo "  [+] Login screen: Titan X logo + dark theme"

# 3. Xorg session bpp
echo "  [3/5] Xorg session config..."
if ! grep -q "xserverbpp" "$XRDP_INI"; then
    sed -i '/^\[Xorg\]/,/^\[/ { /^ip=/ a\xserverbpp=24' "$XRDP_INI" 2>/dev/null || true
fi

# 4. startwm.sh with auto-resize and Titan X env
echo "  [4/5] Session startup script..."
cat > "$STARTWM" << 'WMEOF'
#!/bin/bash
# TITAN X — Session Startup
# Auto-detects resolution and configures environment

if [ -r /etc/default/locale ]; then
    . /etc/default/locale
    export LANG LANGUAGE
fi

export PYTHONPATH=/opt/titan:/opt/titan/src/core:/opt/titan/src/apps
export TITAN_ROOT=/opt/titan
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough

unset DBUS_SESSION_BUS_ADDRESS
unset SESSION_MANAGER

# Auto-resize to client resolution
if command -v xrandr &>/dev/null; then
    sleep 1
    # Get connected output
    OUTPUT=$(xrandr --current 2>/dev/null | grep " connected" | head -1 | awk '{print $1}')
    if [ -n "$OUTPUT" ]; then
        # xrdp will set the resolution from client, just ensure it's applied
        xrandr --output "$OUTPUT" --auto 2>/dev/null || true
    fi
fi

# Set DPI for better readability on mobile
xrdb -merge <<XRDB
Xft.dpi: 108
Xft.antialias: true
Xft.hinting: true
Xft.hintstyle: hintslight
Xft.rgba: rgb
XRDB

exec startxfce4
WMEOF
chmod +x "$STARTWM"
echo "  [+] startwm.sh updated with auto-resize + DPI"

# 5. Install xdotool for touch support
echo "  [5/5] Touch/mobile tools..."
apt-get install -y xdotool xclip 2>/dev/null | tail -1 || true
echo "  [+] xdotool + xclip installed"

# Restart xrdp
systemctl restart xrdp
echo ""
echo "[DONE] xrdp configured. Restart your RDP session to see changes."
