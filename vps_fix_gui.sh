#!/bin/bash
# TITAN V8.0 — Fix RDP Desktop, GUI Theme, App Shortcuts
set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.0 — Desktop & GUI Fix                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Install missing packages ────────────────────────────────────
echo "[1/7] Checking packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    adwaita-icon-theme-full \
    papirus-icon-theme \
    fonts-jetbrains-mono \
    dbus-x11 \
    xfce4-terminal \
    xfce4-taskmanager \
    thunar \
    mousepad \
    2>/dev/null || true
echo "  ✓ Packages OK"

# ── 2. Create Desktop directory ────────────────────────────────────
echo "[2/7] Creating desktop shortcuts..."
mkdir -p /root/Desktop

# Dev Hub launcher
cat > /root/Desktop/titan-dev-hub.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=TITAN Dev Hub
Comment=V8.0 AI-Powered Development IDE
Exec=python3 /opt/titan/apps/titan_dev_hub.py
Icon=utilities-terminal
Terminal=false
Categories=Development;IDE;
StartupNotify=true
EOF
chmod +x /root/Desktop/titan-dev-hub.desktop

# Unified Operations Dashboard
cat > /root/Desktop/titan-unified.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=TITAN Operations
Comment=V8.0 Unified Operations Dashboard
Exec=python3 /opt/titan/apps/app_unified.py
Icon=preferences-system
Terminal=false
Categories=System;
StartupNotify=true
EOF
chmod +x /root/Desktop/titan-unified.desktop

# Genesis Profile Forge
cat > /root/Desktop/titan-genesis.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=TITAN Genesis
Comment=V8.0 Profile Generation Engine
Exec=python3 /opt/titan/apps/app_genesis.py
Icon=contact-new
Terminal=false
Categories=System;
StartupNotify=true
EOF
chmod +x /root/Desktop/titan-genesis.desktop

# Cerberus Validation
cat > /root/Desktop/titan-cerberus.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=TITAN Cerberus
Comment=V8.0 Asset Validation Engine
Exec=python3 /opt/titan/apps/app_cerberus.py
Icon=dialog-password
Terminal=false
Categories=System;
StartupNotify=true
EOF
chmod +x /root/Desktop/titan-cerberus.desktop

# KYC Module
cat > /root/Desktop/titan-kyc.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=TITAN KYC
Comment=V8.0 KYC Compliance Module
Exec=python3 /opt/titan/apps/app_kyc.py
Icon=security-medium
Terminal=false
Categories=System;
StartupNotify=true
EOF
chmod +x /root/Desktop/titan-kyc.desktop

# Bug Reporter
cat > /root/Desktop/titan-reporter.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=TITAN Reporter
Comment=V8.0 Diagnostic Bug Reporter
Exec=python3 /opt/titan/apps/app_bug_reporter.py
Icon=dialog-warning
Terminal=false
Categories=Development;
StartupNotify=true
EOF
chmod +x /root/Desktop/titan-reporter.desktop

# Terminal shortcut
cat > /root/Desktop/terminal.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Terminal
Comment=XFCE Terminal
Exec=xfce4-terminal
Icon=utilities-terminal
Terminal=false
Categories=System;
EOF
chmod +x /root/Desktop/terminal.desktop

echo "  ✓ 7 desktop shortcuts created"

# ── 3. Mark .desktop files as trusted (XFCE security) ─────────────
echo "[3/7] Trusting desktop shortcuts..."
# XFCE requires dbus to trust .desktop files, let's also set the metadata
for f in /root/Desktop/*.desktop; do
    # Remove the untrusted flag via gio if possible
    gio set "$f" metadata::trusted true 2>/dev/null || true
    # Also set executable bit
    chmod +x "$f"
done
echo "  ✓ Desktop files trusted"

# ── 4. Set XFCE Dark Theme ────────────────────────────────────────
echo "[4/7] Applying V8.0 dark theme..."
mkdir -p /root/.config/xfce4/xfconf/xfce-perchannel-xml

# GTK Theme + Icon Theme
cat > /root/.config/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Adwaita-dark"/>
    <property name="IconThemeName" type="string" value="Papirus-Dark"/>
    <property name="CursorThemeName" type="string" value="Adwaita"/>
    <property name="CursorSize" type="int" value="24"/>
    <property name="EnableEventSounds" type="bool" value="false"/>
    <property name="EnableInputFeedbackSounds" type="bool" value="false"/>
    <property name="SoundThemeName" type="string" value="default"/>
  </property>
  <property name="Xft" type="empty">
    <property name="Antialias" type="int" value="1"/>
    <property name="Hinting" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintmedium"/>
    <property name="RGBA" type="string" value="rgb"/>
    <property name="DPI" type="int" value="96"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="FontName" type="string" value="JetBrains Mono 10"/>
    <property name="MonospaceFontName" type="string" value="JetBrains Mono 10"/>
    <property name="CursorThemeName" type="string" value="Adwaita"/>
    <property name="CursorThemeSize" type="int" value="24"/>
    <property name="DecorationLayout" type="string" value="menu:minimize,maximize,close"/>
  </property>
</channel>
EOF

# Window Manager Theme
cat > /root/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Adwaita-dark"/>
    <property name="title_font" type="string" value="JetBrains Mono Bold 10"/>
    <property name="use_compositing" type="bool" value="false"/>
    <property name="placement_ratio" type="int" value="20"/>
    <property name="cycle_tabwin_mode" type="int" value="0"/>
  </property>
</channel>
EOF

# Disable compositing for RDP performance
cat > /root/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorrdp0" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.058824"/>
            <value type="double" value="0.066667"/>
            <value type="double" value="0.109804"/>
            <value type="double" value="1.000000"/>
          </property>
          <property name="image-style" type="int" value="0"/>
          <property name="last-image" type="string" value=""/>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.058824"/>
            <value type="double" value="0.066667"/>
            <value type="double" value="0.109804"/>
            <value type="double" value="1.000000"/>
          </property>
          <property name="image-style" type="int" value="0"/>
          <property name="last-image" type="string" value=""/>
        </property>
      </property>
    </property>
  </property>
  <property name="desktop-icons" type="empty">
    <property name="style" type="int" value="2"/>
    <property name="file-icons" type="empty">
      <property name="show-home" type="bool" value="false"/>
      <property name="show-filesystem" type="bool" value="false"/>
      <property name="show-removable" type="bool" value="false"/>
      <property name="show-trash" type="bool" value="false"/>
    </property>
    <property name="icon-size" type="uint" value="48"/>
    <property name="font-size" type="double" value="10.000000"/>
    <property name="tooltip-size" type="double" value="48.000000"/>
  </property>
</channel>
EOF

echo "  ✓ Adwaita-dark theme + Papirus icons + JetBrains Mono font"

# ── 5. XFCE Panel Config ──────────────────────────────────────────
echo "[5/7] Configuring XFCE panel..."
cat > /root/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="dark-mode" type="bool" value="true"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=8;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="icon-size" type="uint" value="22"/>
      <property name="size" type="uint" value="32"/>
      <property name="background-style" type="uint" value="1"/>
      <property name="background-rgba" type="array">
        <value type="double" value="0.058824"/>
        <value type="double" value="0.066667"/>
        <value type="double" value="0.109804"/>
        <value type="double" value="0.950000"/>
      </property>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
      </property>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu">
      <property name="button-title" type="string" value="TITAN"/>
      <property name="show-button-title" type="bool" value="true"/>
    </property>
    <property name="plugin-2" type="string" value="tasklist">
      <property name="flat-buttons" type="bool" value="true"/>
      <property name="show-labels" type="bool" value="true"/>
    </property>
    <property name="plugin-3" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-4" type="string" value="systray"/>
    <property name="plugin-5" type="string" value="clock">
      <property name="digital-format" type="string" value="%H:%M  |  %b %d"/>
    </property>
    <property name="plugin-6" type="string" value="actions"/>
  </property>
</channel>
EOF
echo "  ✓ Panel: TITAN menu + dark background"

# ── 6. Terminal dark config ────────────────────────────────────────
echo "[6/7] Configuring terminal..."
mkdir -p /root/.config/xfce4/terminal
cat > /root/.config/xfce4/terminal/terminalrc << 'EOF'
[Configuration]
FontName=JetBrains Mono 11
MiscAlwaysShowTabs=FALSE
MiscBell=FALSE
MiscBellUrgent=FALSE
MiscBordersDefault=TRUE
MiscCursorBlinks=TRUE
MiscCursorShape=TERMINAL_CURSOR_SHAPE_BLOCK
MiscDefaultGeometry=120x35
MiscInheritGeometry=FALSE
MiscMenubarDefault=FALSE
MiscMouseAutohide=FALSE
MiscMouseWheelZoom=TRUE
MiscToolbarDefault=FALSE
MiscConfirmClose=TRUE
MiscCycleTabs=TRUE
MiscTabCloseButtons=TRUE
MiscTabCloseMiddleClick=TRUE
MiscTabPosition=GTK_POS_TOP
MiscHighlightUrls=TRUE
MiscMiddleClickOpensUri=FALSE
MiscCopyOnSelect=FALSE
MiscShowRelaunchDialog=TRUE
MiscRewrapOnResize=TRUE
MiscUseShiftArrowsToScroll=FALSE
MiscSlimTabs=FALSE
MiscNewTabAdjacent=FALSE
MiscSearchDialogOpacity=100
MiscShowUnsafePasteDialog=FALSE
ScrollingUnlimited=TRUE
BackgroundMode=TERMINAL_BACKGROUND_TRANSPARENT
BackgroundDarkness=0.920000
ColorForeground=#00ffcc
ColorBackground=#0f111c
ColorCursor=#00d4ff
ColorSelection=#1a1d2e
ColorSelectionUseDefault=FALSE
ColorPalette=#1a1d2e;#ff3366;#00ff88;#ffcc00;#00d4ff;#cc66ff;#00ffcc;#c8ccd4;#3d4059;#ff5577;#33ff99;#ffdd33;#33ddff;#dd88ff;#33ffdd;#e8ecf4
TabActivityColor=#00d4ff
EOF
echo "  ✓ Terminal: cyberpunk dark theme"

# ── 7. Quick-launch scripts in PATH ───────────────────────────────
echo "[7/7] Creating quick-launch commands..."

cat > /usr/local/bin/devhub << 'EOF'
#!/bin/bash
cd /opt/titan/apps && python3 titan_dev_hub.py &
EOF
chmod +x /usr/local/bin/devhub

cat > /usr/local/bin/ops << 'EOF'
#!/bin/bash
cd /opt/titan/apps && python3 app_unified.py &
EOF
chmod +x /usr/local/bin/ops

cat > /usr/local/bin/genesis << 'EOF'
#!/bin/bash
cd /opt/titan/apps && python3 app_genesis.py &
EOF
chmod +x /usr/local/bin/genesis

cat > /usr/local/bin/cerberus << 'EOF'
#!/bin/bash
cd /opt/titan/apps && python3 app_cerberus.py &
EOF
chmod +x /usr/local/bin/cerberus

cat > /usr/local/bin/kyc << 'EOF'
#!/bin/bash
cd /opt/titan/apps && python3 app_kyc.py &
EOF
chmod +x /usr/local/bin/kyc

cat > /usr/local/bin/reporter << 'EOF'
#!/bin/bash
cd /opt/titan/apps && python3 app_bug_reporter.py &
EOF
chmod +x /usr/local/bin/reporter

echo "  ✓ Commands: devhub, ops, genesis, cerberus, kyc, reporter"

# ── Kill existing XFCE sessions so changes apply on next login ─────
echo ""
echo "[*] Resetting XFCE session cache..."
rm -rf /root/.cache/sessions/* 2>/dev/null || true
rm -f /root/.cache/xfce4-session-* 2>/dev/null || true

# Restart xrdp-sesman to pick up changes
echo "[*] Restarting xrdp-sesman..."
systemctl restart xrdp-sesman 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  DESKTOP FIX COMPLETE                                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  ✅ 7 desktop shortcuts (Dev Hub, Ops, Genesis, Cerberus,   ║"
echo "║     KYC, Reporter, Terminal)                                 ║"
echo "║  ✅ Adwaita-dark theme + Papirus-Dark icons                  ║"
echo "║  ✅ JetBrains Mono font                                      ║"
echo "║  ✅ Cyberpunk terminal colors (#0f111c bg, #00ffcc fg)       ║"
echo "║  ✅ TITAN menu in panel                                      ║"
echo "║  ✅ Quick commands: devhub, ops, genesis, cerberus, kyc      ║"
echo "║                                                              ║"
echo "║  👉 DISCONNECT RDP and RECONNECT to see changes              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
