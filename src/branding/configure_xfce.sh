#!/bin/bash
# TITAN X — XFCE Desktop Branding & Configuration
set -e

echo "[TITAN X] Configuring XFCE desktop..."

# Install dark theme if not present
echo "  [1/7] Installing dark GTK theme..."
apt-get install -y arc-theme adwaita-icon-theme-full 2>/dev/null | tail -1 || true
echo "  [+] Arc theme installed"

# 2. Configure for all users (root + user)
for USERHOME in /root /home/user; do
    [ -d "$USERHOME" ] || continue
    USERNAME=$(basename "$USERHOME")
    [ "$USERNAME" = "root" ] && USERNAME="root"
    echo "  [2/7] Configuring XFCE for $USERHOME..."

    XFCE_CONF="$USERHOME/.config/xfce4/xfconf/xfce-perchannel-xml"
    mkdir -p "$XFCE_CONF"
    mkdir -p "$USERHOME/.config/xfce4/panel"
    mkdir -p "$USERHOME/.config/autostart"

    # Desktop wallpaper + settings
    cat > "$XFCE_CONF/xfce4-desktop.xml" << 'DESKEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorVNC-0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/opt/titan/branding/wallpapers/titan_wallpaper_1080.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.039216"/>
            <value type="double" value="0.054902"/>
            <value type="double" value="0.090196"/>
            <value type="double" value="1.000000"/>
          </property>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/opt/titan/branding/wallpapers/titan_wallpaper_1080.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.039216"/>
            <value type="double" value="0.054902"/>
            <value type="double" value="0.090196"/>
            <value type="double" value="1.000000"/>
          </property>
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
    <property name="font-size" type="double" value="11.000000"/>
  </property>
</channel>
DESKEOF

    # Dark GTK theme (xsettings)
    cat > "$XFCE_CONF/xsettings.xml" << 'XSEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Arc-Dark"/>
    <property name="IconThemeName" type="string" value="Adwaita"/>
    <property name="CursorThemeName" type="string" value="Adwaita"/>
    <property name="CursorSize" type="int" value="24"/>
    <property name="EnableEventSounds" type="bool" value="false"/>
    <property name="EnableInputFeedbackSounds" type="bool" value="false"/>
    <property name="SoundThemeName" type="string" value=""/>
  </property>
  <property name="Xft" type="empty">
    <property name="DPI" type="int" value="108"/>
    <property name="Antialias" type="int" value="1"/>
    <property name="Hinting" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintslight"/>
    <property name="RGBA" type="string" value="rgb"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="FontName" type="string" value="Noto Sans 10"/>
    <property name="MonospaceFontName" type="string" value="DejaVu Sans Mono 10"/>
    <property name="CursorThemeSize" type="int" value="24"/>
    <property name="CanChangeAccels" type="bool" value="false"/>
    <property name="ColorPalette" type="string" value="black:dark red:dark green:dark yellow:dark blue:dark magenta:dark cyan:light gray:dark gray:red:green:yellow:blue:magenta:cyan:white"/>
    <property name="ButtonImages" type="bool" value="true"/>
    <property name="MenuImages" type="bool" value="true"/>
    <property name="TitlebarMiddleClick" type="string" value="lower"/>
  </property>
</channel>
XSEOF

    # Window manager dark theme
    cat > "$XFCE_CONF/xfwm4.xml" << 'WMEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Arc-Dark"/>
    <property name="title_font" type="string" value="Noto Sans Bold 10"/>
    <property name="title_alignment" type="string" value="center"/>
    <property name="button_layout" type="string" value="O|HMC"/>
    <property name="cycle_draw_frame" type="bool" value="true"/>
    <property name="cycle_raise" type="bool" value="true"/>
    <property name="focus_delay" type="int" value="141"/>
    <property name="raise_on_click" type="bool" value="true"/>
    <property name="snap_to_border" type="bool" value="true"/>
    <property name="snap_to_windows" type="bool" value="true"/>
    <property name="tile_on_move" type="bool" value="true"/>
    <property name="use_compositing" type="bool" value="true"/>
    <property name="placement_ratio" type="int" value="20"/>
    <property name="shadow_delta_height" type="int" value="2"/>
    <property name="shadow_delta_width" type="int" value="0"/>
    <property name="shadow_delta_x" type="int" value="0"/>
    <property name="shadow_delta_y" type="int" value="-3"/>
    <property name="shadow_opacity" type="int" value="50"/>
  </property>
</channel>
WMEOF

    # Panel config — dark, 48px, with Titan X branding
    cat > "$XFCE_CONF/xfce4-panel.xml" << 'PANEOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="dark-mode" type="bool" value="true"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=6;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="icon-size" type="uint" value="22"/>
      <property name="size" type="uint" value="40"/>
      <property name="background-style" type="uint" value="1"/>
      <property name="background-rgba" type="array">
        <value type="double" value="0.039216"/>
        <value type="double" value="0.054902"/>
        <value type="double" value="0.090196"/>
        <value type="double" value="0.950000"/>
      </property>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
        <value type="int" value="7"/>
      </property>
      <property name="enter-opacity" type="uint" value="100"/>
      <property name="leave-opacity" type="uint" value="95"/>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu">
      <property name="button-title" type="string" value="TITAN X"/>
      <property name="button-icon" type="string" value="titan-x"/>
      <property name="show-button-title" type="bool" value="true"/>
      <property name="small" type="bool" value="false"/>
    </property>
    <property name="plugin-2" type="string" value="separator">
      <property name="expand" type="bool" value="false"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-3" type="string" value="tasklist">
      <property name="flat-buttons" type="bool" value="true"/>
      <property name="show-labels" type="bool" value="true"/>
      <property name="show-handle" type="bool" value="false"/>
      <property name="grouping" type="uint" value="1"/>
    </property>
    <property name="plugin-4" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-5" type="string" value="systray">
      <property name="square-icons" type="bool" value="true"/>
      <property name="icon-size" type="int" value="22"/>
    </property>
    <property name="plugin-6" type="string" value="clock">
      <property name="digital-format" type="string" value="%H:%M  %d %b"/>
      <property name="mode" type="uint" value="2"/>
    </property>
    <property name="plugin-7" type="string" value="actions">
      <property name="appearance" type="uint" value="0"/>
    </property>
  </property>
</channel>
PANEOF

    # Terminal dark theme
    mkdir -p "$USERHOME/.config/xfce4/terminal"
    cat > "$USERHOME/.config/xfce4/terminal/terminalrc" << 'TERMEOF'
[Configuration]
BackgroundMode=TERMINAL_BACKGROUND_TRANSPARENT
BackgroundDarkness=0.92
ColorForeground=#e2e8f0
ColorBackground=#0a0e17
ColorCursor=#00d4ff
ColorCursorUseDefault=FALSE
ColorPalette=#073642;#ef4444;#22c55e;#eab308;#268bd2;#a855f7;#2aa198;#eee8d5;#586e75;#cb4b16;#4ade80;#facc15;#839496;#6c71c4;#93a1a1;#fdf6e3
FontName=DejaVu Sans Mono 11
MiscAlwaysShowTabs=FALSE
MiscBordersDefault=TRUE
MiscMenubarDefault=FALSE
MiscShowUnsafePasteDialog=FALSE
MiscDefaultGeometry=120x35
ScrollingBar=TERMINAL_SCROLLBAR_NONE
TERMEOF

    # Fix ownership
    if [ "$USERHOME" = "/home/user" ]; then
        chown -R user:user "$USERHOME/.config" 2>/dev/null || true
    fi
done
echo "  [+] XFCE configured for all users"

# 3. Desktop shortcuts for all 11 apps
echo "  [3/7] Creating desktop shortcuts..."
APPS_DESKTOP="/usr/share/applications"
ICON="titan-x"

declare -A APPS
APPS=(
    ["titan-operations"]="Titan X Operations|Start operations - target to checkout pipeline|titan_operations.py"
    ["titan-intelligence"]="Titan X Intelligence|AI analysis, 3DS strategy, detection lab|titan_intelligence.py"
    ["titan-network"]="Titan X Network|VPN, proxy, eBPF shields, forensic monitor|titan_network.py"
    ["titan-kyc"]="Titan X KYC Studio|Camera, documents, voice, identity verification|app_kyc.py"
    ["titan-admin"]="Titan X Admin|System management, services, automation|titan_admin.py"
    ["titan-settings"]="Titan X Settings|Configure VPN, AI, browser, API keys|app_settings.py"
    ["titan-profile-forge"]="Titan X Profile Forge|Identity forge, persona, chrome profiles|app_profile_forge.py"
    ["titan-card-validator"]="Titan X Card Validator|BIN check, AVS, card quality grading|app_card_validator.py"
    ["titan-browser-launch"]="Titan X Browser Launch|Preflight, launch, TX monitor|app_browser_launch.py"
    ["titan-genesis"]="Titan X Genesis AppX|ML6 browser, profile management|../../../tools/multilogin6/genesis_appx/launch_genesis_appx.sh"
    ["titan-bug-reporter"]="Titan X Bug Reporter|Report, patch, track decline patterns|app_bug_reporter.py"
)

for name in "${!APPS[@]}"; do
    IFS='|' read -r title comment script <<< "${APPS[$name]}"

    if [[ "$script" == *".sh" ]]; then
        EXEC_LINE="Exec=bash /opt/titan/tools/multilogin6/genesis_appx/launch_genesis_appx.sh"
    else
        EXEC_LINE="Exec=bash -c 'export PYTHONPATH=/opt/titan:/opt/titan/src/core:/opt/titan/src/apps && python3 /opt/titan/src/apps/$script'"
    fi

    cat > "$APPS_DESKTOP/$name.desktop" << APPEOF
[Desktop Entry]
Name=$title
Comment=$comment
$EXEC_LINE
Icon=$ICON
Terminal=false
Type=Application
Categories=Titan;Utility;
StartupNotify=true
APPEOF
    chmod +x "$APPS_DESKTOP/$name.desktop"
done

# Launcher shortcut (primary)
cat > "$APPS_DESKTOP/titan-launcher.desktop" << 'LAUNCHEOF'
[Desktop Entry]
Name=Titan X Launcher
Comment=Main launcher - access all 11 apps
Exec=bash -c 'export PYTHONPATH=/opt/titan:/opt/titan/src/core:/opt/titan/src/apps && python3 /opt/titan/src/apps/titan_launcher.py'
Icon=titan-x
Terminal=false
Type=Application
Categories=Titan;Utility;
StartupNotify=true
LAUNCHEOF
chmod +x "$APPS_DESKTOP/titan-launcher.desktop"

echo "  [+] 12 desktop shortcuts created"

# 4. Copy to Desktop folder for root and user
echo "  [4/7] Placing shortcuts on desktops..."
for USERHOME in /root /home/user; do
    [ -d "$USERHOME" ] || continue
    DESK="$USERHOME/Desktop"
    mkdir -p "$DESK"

    # Only place the launcher on desktop (clean look)
    cp "$APPS_DESKTOP/titan-launcher.desktop" "$DESK/"
    chmod +x "$DESK/titan-launcher.desktop"

    if [ "$USERHOME" = "/home/user" ]; then
        chown -R user:user "$DESK" 2>/dev/null || true
    fi
done
echo "  [+] Launcher shortcut placed on desktops"

# 5. XFCE autostart — launch Titan X on login
echo "  [5/7] Setting up autostart..."
for USERHOME in /root /home/user; do
    [ -d "$USERHOME" ] || continue
    mkdir -p "$USERHOME/.config/autostart"
    cat > "$USERHOME/.config/autostart/titan-launcher.desktop" << 'AUTOEOF'
[Desktop Entry]
Type=Application
Name=Titan X Launcher
Exec=bash -c 'sleep 2 && export PYTHONPATH=/opt/titan:/opt/titan/src/core:/opt/titan/src/apps && python3 /opt/titan/src/apps/titan_launcher.py'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Auto-launch Titan X on login
AUTOEOF
    if [ "$USERHOME" = "/home/user" ]; then
        chown -R user:user "$USERHOME/.config/autostart" 2>/dev/null || true
    fi
done
echo "  [+] Titan X auto-launch on login configured"

# 6. XFCE file manager — single click
echo "  [6/7] File manager settings..."
for USERHOME in /root /home/user; do
    [ -d "$USERHOME" ] || continue
    XFCE_CONF="$USERHOME/.config/xfce4/xfconf/xfce-perchannel-xml"
    mkdir -p "$XFCE_CONF"
    cat > "$XFCE_CONF/thunar.xml" << 'THUNAREOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="thunar" version="1.0">
  <property name="last-view" type="string" value="ThunarIconView"/>
  <property name="misc-single-click" type="bool" value="true"/>
  <property name="misc-thumbnail-mode" type="string" value="THUNAR_THUMBNAIL_MODE_ALWAYS"/>
  <property name="misc-date-style" type="string" value="THUNAR_DATE_STYLE_SHORT"/>
  <property name="misc-text-beside-icons" type="bool" value="false"/>
  <property name="last-icon-view-zoom-level" type="string" value="THUNAR_ZOOM_LEVEL_100_PERCENT"/>
</channel>
THUNAREOF
    if [ "$USERHOME" = "/home/user" ]; then
        chown -R user:user "$XFCE_CONF" 2>/dev/null || true
    fi
done
echo "  [+] File manager: single-click, thumbnails enabled"

# 7. Update icon cache
echo "  [7/7] Updating icon cache..."
gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

echo ""
echo "[DONE] XFCE desktop fully branded. Log out and back in to apply."
