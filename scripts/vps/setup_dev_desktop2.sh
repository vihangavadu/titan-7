#!/bin/bash
# VPS Dev Desktop Setup — Windsurf + VS Code + Cursor + Chrome only
set -e
CURSOR_DEB="https://downloads.cursor.com/production/7d96c2a03bb088ad367615e9da1a3fe20fbbc6ae/linux/x64/deb/amd64/deb/cursor_2.5.26_amd64.deb"

echo "[1/7] Installing Cursor IDE (deb)..."
curl -sL "$CURSOR_DEB" -o /tmp/cursor.deb
dpkg -i /tmp/cursor.deb 2>&1 || apt-get install -f -y
rm -f /tmp/cursor.deb
echo "   Cursor: $(which cursor || echo 'installed')"

echo "[2/7] Disabling unnecessary services..."
for svc in avahi-daemon avahi-daemon.socket lightdm colord rtkit-daemon bluetooth cups cups-browsed ModemManager; do
    systemctl disable --now "$svc" 2>/dev/null || true
done
echo "   Done."

echo "[3/7] Configuring XRDP — 24bpp, XFCE session..."
sed -i 's/^max_bpp=.*/max_bpp=24/' /etc/xrdp/xrdp.ini
cat > /etc/xrdp/startwm.sh << 'EOF'
#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR
exec /usr/bin/xfce4-session
EOF
chmod +x /etc/xrdp/startwm.sh
systemctl restart xrdp xrdp-sesman
echo "   XRDP ready on :3389"

echo "[4/7] Writing XFCE dev desktop config..."
CFG="/root/.config"
mkdir -p "$CFG/xfce4/xfconf/xfce-perchannel-xml" "$CFG/autostart"

# Panel: bottom bar, 48px, 5 launchers (Windsurf, Code, Cursor, Chrome, Terminal) + clock + systray
cat > "$CFG/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml" << 'PANELEOF'
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
PANELEOF

# Desktop: dark background, no desktop icons
cat > "$CFG/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml" << 'DESKEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVirtual-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.114"/>
            <value type="double" value="0.122"/>
            <value type="double" value="0.153"/>
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
DESKEOF

# Session: no save/restore, no prompts
cat > "$CFG/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml" << 'SESSEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-session" version="1.0">
  <property name="general" type="empty">
    <property name="SaveOnExit"     type="bool" value="false"/>
    <property name="AutoSave"       type="bool" value="false"/>
    <property name="PromptOnLogout" type="bool" value="false"/>
  </property>
  <property name="startup" type="empty">
    <property name="ssh-agent" type="bool" value="false"/>
    <property name="gpg-agent" type="bool" value="false"/>
  </property>
</channel>
SESSEOF

# Window manager: dark theme, compositing OFF (faster RDP)
cat > "$CFG/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml" << 'WMEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme"            type="string" value="Greybird-dark"/>
    <property name="use_compositing"  type="bool"   value="false"/>
    <property name="frame_opacity"    type="int"     value="100"/>
  </property>
</channel>
WMEOF
echo "   XFCE config written."

echo "[5/7] Hiding non-dev apps from application menu..."
HIDE=(
    thunar thunar-bulk-rename thunar-settings
    mousepad gedit xed
    gimp shotwell
    vlc totem
    libreoffice-base libreoffice-calc libreoffice-draw libreoffice-impress libreoffice-writer
    xfce4-about xfce4-appfinder xfce4-screenshooter
    nm-connection-editor
    xfce4-power-manager-settings xfce4-taskmanager
    xfce4-display-settings xfce4-keyboard-settings xfce4-mouse-settings
    xfce4-settings-editor xfce4-settings-manager
    firefox-esr firefox
    xfburn
    xfce4-mail-reader
    xfce4-mixer
)
for app in "${HIDE[@]}"; do
    D="/usr/share/applications/${app}.desktop"
    [ -f "$D" ] || continue
    grep -q "^NoDisplay=" "$D" \
        && sed -i 's/^NoDisplay=.*/NoDisplay=true/' "$D" \
        || echo "NoDisplay=true" >> "$D"
done
echo "   Menu cleaned."

echo "[6/7] Right-click menu — dev tools only..."
mkdir -p /root/.config/menus
cat > /root/.config/menus/xfce-applications.menu << 'MENUEOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
  "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd">
<Menu>
  <Name>Xfce</Name>
  <Menu>
    <Name>Development IDEs</Name>
    <Include>
      <Filename>windsurf.desktop</Filename>
      <Filename>code.desktop</Filename>
      <Filename>cursor.desktop</Filename>
    </Include>
  </Menu>
  <Menu>
    <Name>Browser</Name>
    <Include>
      <Filename>google-chrome.desktop</Filename>
    </Include>
  </Menu>
  <Menu>
    <Name>Terminal</Name>
    <Include>
      <Filename>xfce4-terminal-emulator.desktop</Filename>
    </Include>
  </Menu>
</Menu>
MENUEOF

echo "[7/7] Chrome GPU/sandbox flags for VPS..."
# Patch Chrome desktop entry for VPS (no sandbox, software GPU)
sed -i '/^Exec=/ s|google-chrome-stable %U|google-chrome-stable --no-sandbox --disable-gpu --disable-dev-shm-usage %U|' \
    /usr/share/applications/google-chrome.desktop 2>/dev/null || true
sed -i '/^Exec=/ s|google-chrome-stable$|google-chrome-stable --no-sandbox --disable-gpu --disable-dev-shm-usage|' \
    /usr/share/applications/google-chrome.desktop 2>/dev/null || true

# Also patch Windsurf/Code to not sandbox (needed on VPS)
for de in /usr/share/applications/windsurf.desktop /usr/share/applications/code.desktop; do
    [ -f "$de" ] && sed -i '/^Exec=/ { /no-sandbox/! s/ %[FfUu]/ --no-sandbox &/ }' "$de" || true
done

echo ""
echo "========================================"
echo "  VPS Dev Desktop — COMPLETE"
echo "========================================"
echo "  Windsurf : $(which windsurf)"
echo "  VS Code  : $(which code)"
echo "  Cursor   : $(which cursor)"
echo "  Chrome   : $(which google-chrome)"
echo "  RDP      : 187.77.186.252:3389"
echo "  Desktop  : XFCE4 dark, bottom panel"
echo "  Panel    : Windsurf | Code | Cursor | Chrome | Terminal"
echo "========================================"
