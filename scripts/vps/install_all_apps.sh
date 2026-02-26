#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "========================================"
echo "  TITAN VPS APP INSTALLER"
echo "========================================"

# Prerequisites
echo ""
echo "=== [1/7] Prerequisites ==="
apt-get update -qq
apt-get install -y -qq wget curl gnupg2 apt-transport-https software-properties-common python3-pip python3-venv ca-certificates > /dev/null 2>&1
echo "Done"

# Windsurf IDE
echo ""
echo "=== [2/7] Windsurf IDE ==="
if command -v windsurf &>/dev/null; then
    echo "Already installed: $(windsurf --version 2>/dev/null || echo 'yes')"
else
    # Method 1: Try apt repo
    curl -fsSL https://windsurf-stable.codeiumdata.com/wVxQEIHkbUBqRFCalECu/windsurf.gpg 2>/dev/null | gpg --dearmor -o /usr/share/keyrings/windsurf-stable-archive-keyring.gpg 2>/dev/null || true
    echo "deb [signed-by=/usr/share/keyrings/windsurf-stable-archive-keyring.gpg arch=amd64] https://windsurf-stable.codeiumdata.com/wVxQEIHkbUBqRFCalECu/apt stable main" > /etc/apt/sources.list.d/windsurf.list 2>/dev/null || true
    apt-get update -qq 2>/dev/null
    if apt-get install -y -qq windsurf 2>/dev/null; then
        echo "Installed via apt"
    else
        # Method 2: Download .deb directly from releases page
        echo "Apt repo failed, downloading .deb..."
        rm -f /tmp/windsurf.deb
        # Try multiple known URLs
        for URL in \
            "https://github.com/nicedoc/windsurf-releases/releases/latest/download/Windsurf-linux-x64.deb" \
            "https://windsurf-stable.codeiumdata.com/linux-deb-x64/stable/Windsurf-linux-x64-latest.deb" \
            ; do
            echo "Trying: $URL"
            curl -fsSL "$URL" -o /tmp/windsurf.deb 2>/dev/null && \
                file /tmp/windsurf.deb | grep -q "Debian" && break
            rm -f /tmp/windsurf.deb
        done

        if [ -f /tmp/windsurf.deb ] && file /tmp/windsurf.deb | grep -q "Debian"; then
            dpkg -i /tmp/windsurf.deb 2>/dev/null || apt-get install -f -y -qq 2>/dev/null
            echo "Installed via .deb"
        else
            # Method 3: Download tar.gz and extract
            echo "Deb failed, trying tar.gz..."
            mkdir -p /opt/windsurf
            curl -fsSL "https://windsurf-stable.codeiumdata.com/linux-x64/stable/Windsurf-linux-x64-latest.tar.gz" -o /tmp/windsurf.tar.gz 2>/dev/null || true
            if [ -f /tmp/windsurf.tar.gz ] && file /tmp/windsurf.tar.gz | grep -q "gzip"; then
                tar xzf /tmp/windsurf.tar.gz -C /opt/windsurf --strip-components=1
                ln -sf /opt/windsurf/bin/windsurf /usr/local/bin/windsurf
                echo "Installed via tar.gz to /opt/windsurf"
            else
                # Method 4: Install VS Code as fallback + Windsurf extension
                echo "All Windsurf download methods failed."
                echo "Installing VS Code as base IDE..."
                wget -qO /tmp/vscode.deb 'https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64' 2>/dev/null || \
                wget -qO /tmp/vscode.deb 'https://update.code.visualstudio.com/latest/linux-deb-x64/stable' 2>/dev/null
                if [ -f /tmp/vscode.deb ] && file /tmp/vscode.deb | grep -q "Debian"; then
                    dpkg -i /tmp/vscode.deb 2>/dev/null || apt-get install -f -y -qq 2>/dev/null
                    echo "VS Code installed as fallback IDE"
                else
                    echo "WARN: Could not install any IDE via download. Will try snap."
                    apt-get install -y -qq snapd 2>/dev/null || true
                    snap install code --classic 2>/dev/null || echo "snap also failed"
                fi
            fi
        fi
    fi
fi
echo "Windsurf step complete"

# Google Chrome
echo ""
echo "=== [3/7] Google Chrome ==="
if command -v google-chrome &>/dev/null || command -v google-chrome-stable &>/dev/null; then
    echo "Already installed"
else
    wget -qO /tmp/chrome.deb 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
    dpkg -i /tmp/chrome.deb 2>/dev/null || apt-get install -f -y -qq 2>/dev/null
    echo "Chrome installed"
fi

# Firefox ESR
echo ""
echo "=== [4/7] Firefox ESR ==="
if command -v firefox-esr &>/dev/null || command -v firefox &>/dev/null; then
    echo "Already installed"
else
    apt-get install -y -qq firefox-esr > /dev/null 2>&1
    echo "Firefox ESR installed"
fi

# Camoufox
echo ""
echo "=== [5/7] Camoufox ==="
if python3 -c "import camoufox" 2>/dev/null; then
    echo "Already installed"
else
    pip3 install --break-system-packages camoufox 2>/dev/null || pip3 install camoufox 2>/dev/null
    python3 -m camoufox fetch 2>/dev/null || true
    echo "Camoufox installed"
fi

# Multilogin X + Multilogin 6 Luna
echo ""
echo "=== [6/7] Multilogin X + Luna ==="
mkdir -p /opt/multilogin
cat > /opt/multilogin/README.md << 'MLREADME'
# Multilogin Setup

## Multilogin X (Browser-based)
- Access: https://app.multilogin.com
- Or: https://multilogin.com/download
- Desktop shortcut created for web access

## Multilogin 6 Luna (Legacy Desktop App)
- Download: https://multilogin.com/download
- Or manually: https://app.multiloginapp.com

Both require a paid subscription and login credentials.
MLREADME

# Try to download Multilogin X agent
echo "Downloading Multilogin X agent..."
curl -fsSL "https://app.multilogin.com/download/linux/x64" -o /tmp/multilogin-x.deb 2>/dev/null || true
if [ -f /tmp/multilogin-x.deb ] && file /tmp/multilogin-x.deb | grep -qi "debian\|archive"; then
    dpkg -i /tmp/multilogin-x.deb 2>/dev/null || apt-get install -f -y -qq 2>/dev/null
    echo "Multilogin X agent installed"
else
    echo "Multilogin X agent not directly downloadable - web shortcut created"
fi

# Try Multilogin 6 (Luna)
echo "Setting up Multilogin 6 Luna..."
curl -fsSL "https://app.multiloginapp.com/download/linux/x64" -o /tmp/multilogin6.deb 2>/dev/null || true
if [ -f /tmp/multilogin6.deb ] && file /tmp/multilogin6.deb | grep -qi "debian\|archive"; then
    dpkg -i /tmp/multilogin6.deb 2>/dev/null || apt-get install -f -y -qq 2>/dev/null
    echo "Multilogin 6 Luna installed"
else
    echo "Multilogin 6 Luna not directly downloadable - web shortcut created"
fi
echo "Multilogin step complete"

# Desktop shortcuts
echo ""
echo "=== [7/7] Desktop Shortcuts ==="
DESKTOP_DIR="/root/Desktop"
mkdir -p "$DESKTOP_DIR"

# Windsurf / VS Code shortcut
if command -v windsurf &>/dev/null; then
    cat > "$DESKTOP_DIR/windsurf.desktop" << 'DESK'
[Desktop Entry]
Name=Windsurf IDE
Exec=windsurf --no-sandbox --unity-launch %F
Terminal=false
Type=Application
Icon=windsurf
Categories=Development;IDE;
DESK
elif command -v code &>/dev/null; then
    cat > "$DESKTOP_DIR/vscode.desktop" << 'DESK'
[Desktop Entry]
Name=VS Code
Exec=code --no-sandbox --unity-launch %F
Terminal=false
Type=Application
Icon=vscode
Categories=Development;IDE;
DESK
fi

# Chrome
cat > "$DESKTOP_DIR/google-chrome.desktop" << 'DESK'
[Desktop Entry]
Name=Google Chrome
Exec=google-chrome-stable --no-sandbox %U
Terminal=false
Type=Application
Icon=google-chrome
Categories=Network;WebBrowser;
DESK

# Firefox
cat > "$DESKTOP_DIR/firefox.desktop" << 'DESK'
[Desktop Entry]
Name=Firefox
Exec=firefox-esr %U
Terminal=false
Type=Application
Icon=firefox-esr
Categories=Network;WebBrowser;
DESK

# Camoufox launcher
cat > /usr/local/bin/camoufox-launch << 'SCRIPT'
#!/bin/bash
python3 -c "
from camoufox.sync_api import Camoufox
with Camoufox(headless=False) as browser:
    page = browser.new_page()
    page.goto('https://browserleaks.com/canvas')
    input('Press Enter to close...')
"
SCRIPT
chmod +x /usr/local/bin/camoufox-launch

cat > "$DESKTOP_DIR/camoufox.desktop" << 'DESK'
[Desktop Entry]
Name=Camoufox
Exec=camoufox-launch
Terminal=true
Type=Application
Icon=firefox
Categories=Network;WebBrowser;
DESK

# Multilogin X
cat > "$DESKTOP_DIR/multilogin-x.desktop" << 'DESK'
[Desktop Entry]
Name=Multilogin X
Exec=google-chrome-stable --no-sandbox --app=https://app.multilogin.com %U
Terminal=false
Type=Application
Icon=web-browser
Categories=Network;WebBrowser;
DESK

# Multilogin 6 Luna
cat > "$DESKTOP_DIR/multilogin-luna.desktop" << 'DESK'
[Desktop Entry]
Name=Multilogin 6 Luna
Exec=google-chrome-stable --no-sandbox --app=https://app.multiloginapp.com %U
Terminal=false
Type=Application
Icon=web-browser
Categories=Network;WebBrowser;
DESK

# Terminal
cat > "$DESKTOP_DIR/terminal.desktop" << 'DESK'
[Desktop Entry]
Name=Terminal
Exec=xfce4-terminal
Terminal=false
Type=Application
Icon=utilities-terminal
Categories=System;TerminalEmulator;
DESK

# Make all executable and trusted
chmod +x "$DESKTOP_DIR"/*.desktop
# Mark as trusted for XFCE
for f in "$DESKTOP_DIR"/*.desktop; do
    gio set "$f" metadata::xfce-exe-checksum "$(sha256sum "$f" | cut -d' ' -f1)" 2>/dev/null || true
done

echo "Desktop shortcuts created"

echo ""
echo "========================================"
echo "  INSTALLATION COMPLETE"
echo "========================================"
echo ""
echo "Installed:"
command -v windsurf && echo "  - Windsurf: $(windsurf --version 2>/dev/null || echo 'installed')"
command -v code && echo "  - VS Code: $(code --version 2>/dev/null | head -1 || echo 'installed')"
command -v google-chrome-stable && echo "  - Chrome: $(google-chrome-stable --version 2>/dev/null)"
command -v firefox-esr && echo "  - Firefox: $(firefox-esr --version 2>/dev/null)"
python3 -c "import camoufox; print('  - Camoufox: installed')" 2>/dev/null || echo "  - Camoufox: not found"
echo "  - Multilogin X: web shortcut"
echo "  - Multilogin 6 Luna: web shortcut"
echo ""
echo "Desktop shortcuts in: $DESKTOP_DIR"
ls -1 "$DESKTOP_DIR"/*.desktop 2>/dev/null
echo ""
echo "Connect via RDP: 187.77.186.252:3389"
