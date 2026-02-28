#!/bin/bash
# VPS Dev Desktop Setup — Windsurf + VS Code + Cursor + Chrome only
# Run as root on the VPS
set -e

echo "[1/7] Installing Cursor IDE..."
CURSOR_URL="https://downloader.cursor.sh/linux/appImage/x64"
CURSOR_DIR="/opt/cursor"
mkdir -p "$CURSOR_DIR"
if [ ! -f "$CURSOR_DIR/cursor.AppImage" ]; then
    wget -qO "$CURSOR_DIR/cursor.AppImage" "$CURSOR_URL"
    chmod +x "$CURSOR_DIR/cursor.AppImage"
fi
# Extract AppImage so it runs without FUSE (common in VPS environments)
cd "$CURSOR_DIR"
if [ ! -f "$CURSOR_DIR/AppRun" ]; then
    "$CURSOR_DIR/cursor.AppImage" --appimage-extract >/dev/null 2>&1 || true
    if [ -d "$CURSOR_DIR/squashfs-root" ]; then
        ln -sf "$CURSOR_DIR/squashfs-root/AppRun" /usr/local/bin/cursor
    else
        # Fallback: create wrapper script
        cat > /usr/local/bin/cursor << 'EOF'
#!/bin/bash
exec /opt/cursor/cursor.AppImage --no-sandbox "$@"
EOF
        chmod +x /usr/local/bin/cursor
    fi
else
    ln -sf "$CURSOR_DIR/AppRun" /usr/local/bin/cursor
fi

# Create Cursor desktop entry
cat > /usr/share/applications/cursor.desktop << 'EOF'
[Desktop Entry]
Name=Cursor
Comment=AI-first code editor
Exec=/usr/local/bin/cursor --no-sandbox %F
Icon=/opt/cursor/squashfs-root/cursor.png
Type=Application
Categories=Development;IDE;
StartupWMClass=Cursor
EOF
echo "   Cursor installed."

echo "[2/7] Disabling unnecessary services..."
DISABLE_SERVICES=(
    avahi-daemon
    avahi-daemon.socket
    lightdm
    colord
    rtkit-daemon
    upower
    bluetooth
    cups
    cups-browsed
    ModemManager
)
for svc in "${DISABLE_SERVICES[@]}"; do
    systemctl disable --now "$svc" 2>/dev/null || true
done
echo "   Services disabled."

echo "[3/7] Configuring XRDP for 24-bit color and XFCE session..."
# Improve XRDP color depth
sed -i 's/max_bpp=16/max_bpp=24/' /etc/xrdp/xrdp.ini
sed -i 's/max_bpp=32/max_bpp=24/' /etc/xrdp/xrdp.ini
# Ensure XRDP uses XFCE
cat > /etc/xrdp/startwm.sh << 'EOF'
#!/bin/sh
# XRDP Session Starter — Dev Desktop
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
exec /usr/bin/xfce4-session
EOF
chmod +x /etc/xrdp/startwm.sh
systemctl restart xrdp xrdp-sesman
echo "   XRDP configured."

echo "[4/7] Building clean XFCE dev desktop configuration..."
XFCE_CONFIG="/root/.config"
mkdir -p "$XFCE_CONFIG/xfce4/xfconf/xfce-perchannel-xml"
mkdir -p "$XFCE_CONFIG/autostart"

# --- Panel config: single bottom panel with only dev app launchers ---
cat > "$XFCE_CONFIG/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=8;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="size" type="uint" value="48"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
        <value type="int" value="7"/>
        <value type="int" value="8"/>
      </property>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="launcher">
      <property name="items" type="array">
        <value type="string" value="windsurf.desktop"/>
      </property>
    </property>
    <property name="plugin-2" type="string" value="launcher">
      <property name="items" type="array">
        <value type="string" value="code.desktop"/>
      </property>
    </property>
    <property name="plugin-3" type="string" value="launcher">
      <property name="items" type="array">
        <value type="string" value="cursor.desktop"/>
      </property>
    </property>
    <property name="plugin-4" type="string" value="launcher">
      <property name="items" type="array">
        <value type="string" value="google-chrome.desktop"/>
      </property>
    </property>
    <property name="plugin-5" type="string" value="launcher">
      <property name="items" type="array">
        <value type="string" value="xfce4-terminal-emulator.desktop"/>
      </property>
    </property>
    <property name="plugin-6" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
    </property>
    <property name="plugin-7" type="string" value="clock"/>
    <property name="plugin-8" type="string" value="systray"/>
  </property>
</channel>
EOF

# --- Desktop settings: clean dark background, no icons ---
cat > "$XFCE_CONFIG/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVirtual-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.113725"/>
            <value type="double" value="0.121569"/>
            <value type="double" value="0.152941"/>
            <value type="double" value="1"/>
          </property>
          <property name="image-style" type="int" value="0"/>
        </property>
      </property>
    </property>
  </property>
  <property name="desktop-icons" type="empty">
    <property name="style" type="int" value="0"/>
  </property>
</channel>
EOF

# --- Window manager: clean theme ---
cat > "$XFCE_CONFIG/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Greybird-dark"/>
    <property name="title_font" type="string" value="Sans Bold 9"/>
    <property name="use_compositing" type="bool" value="false"/>
  </property>
</channel>
EOF

# --- Session: do not restore previous windows ---
cat > "$XFCE_CONFIG/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="general" type="empty">
    <property name="SaveOnExit" type="bool" value="false"/>
    <property name="AutoSave" type="bool" value="false"/>
    <property name="PromptOnLogout" type="bool" value="false"/>
  </property>
  <property name="startup" type="empty">
    <property name="ssh-agent" type="bool" value="false"/>
    <property name="gpg-agent" type="bool" value="false"/>
  </property>
</channel>
EOF
echo "   XFCE config written."

echo "[5/7] Hiding non-dev apps from application menu..."
# NoDisplay=true on apps that shouldn't appear in the menu
HIDE_APPS=(
    thunar thunar-bulk-rename thunar-settings
    mousepad gedit
    gimp
    vlc
    libreoffice-base libreoffice-calc libreoffice-draw libreoffice-impress libreoffice-writer
    xfce4-about xfce4-appfinder
    xfce4-screenshooter
    nm-connection-editor
    xfce4-power-manager-settings
    xfce4-taskmanager
    xfce-ui-settings
    xfce4-display-settings
    xfce4-keyboard-settings
    xfce4-mouse-settings
    xfce4-settings-editor
    xfce4-settings-manager
    firefox-esr
    xfburn
)
for app in "${HIDE_APPS[@]}"; do
    DESKTOP="/usr/share/applications/${app}.desktop"
    if [ -f "$DESKTOP" ]; then
        # Only add NoDisplay if not already there
        grep -q "^NoDisplay=" "$DESKTOP" \
            && sed -i 's/^NoDisplay=.*/NoDisplay=true/' "$DESKTOP" \
            || echo "NoDisplay=true" >> "$DESKTOP"
    fi
done
echo "   App menu cleaned."

echo "[6/7] Creating right-click desktop menu with dev tools only..."
mkdir -p /root/.config/menus
cat > /root/.config/menus/xfce-applications.menu << 'EOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
  "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd">
<Menu>
  <Name>Xfce</Name>
  <Menu>
    <Name>Development</Name>
    <Directory>xfce-development.directory</Directory>
    <Include>
      <Filename>windsurf.desktop</Filename>
      <Filename>code.desktop</Filename>
      <Filename>cursor.desktop</Filename>
    </Include>
  </Menu>
  <Menu>
    <Name>Internet</Name>
    <Directory>xfce-internet.directory</Directory>
    <Include>
      <Filename>google-chrome.desktop</Filename>
    </Include>
  </Menu>
  <Menu>
    <Name>System</Name>
    <Directory>xfce-system.directory</Directory>
    <Include>
      <Filename>xfce4-terminal-emulator.desktop</Filename>
    </Include>
  </Menu>
</Menu>
EOF

echo "[7/7] Setting Chrome flags for VPS (no sandbox + GPU disable)..."
mkdir -p /root/.config/google-chrome
cat > /root/.config/google-chrome/chrome-flags.conf << 'EOF'
--no-sandbox
--disable-gpu
--disable-dev-shm-usage
EOF
# Also patch Chrome desktop entry
sed -i 's|Exec=/usr/bin/google-chrome-stable|Exec=/usr/bin/google-chrome-stable --no-sandbox --disable-gpu --disable-dev-shm-usage|' \
    /usr/share/applications/google-chrome.desktop 2>/dev/null || true

echo ""
echo "============================================"
echo "  VPS Dev Desktop Setup Complete!"
echo "============================================"
echo "  IDEs available:"
echo "    - Windsurf  : $(which windsurf)"
echo "    - VS Code   : $(which code)"
echo "    - Cursor    : $(which cursor 2>/dev/null || echo 'check /opt/cursor')"
echo "  Browser:"
echo "    - Chrome    : $(which google-chrome)"
echo "  RDP Port      : 3389"
echo "  Color Depth   : 24-bit"
echo "  Desktop       : XFCE4 (clean dev layout)"
echo ""
echo "  Connect with any RDP client:"
echo "    Host: 187.77.186.252:3389"
echo "    User: root"
echo "============================================"
