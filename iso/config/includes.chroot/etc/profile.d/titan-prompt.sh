#!/bin/bash
# Titan OS V7.0.3 — Custom Terminal Prompt & Environment
# Loaded for all users via /etc/profile.d/

# ─── Custom PS1 Prompt ──────────────────────────────────────
# Cyan hostname, green path, clean arrow
if [ "$EUID" -eq 0 ]; then
    # Root: red indicator
    PS1='\[\e[38;5;196m\]\u\[\e[38;5;240m\]@\[\e[38;5;39m\]\h \[\e[38;5;245m\]\w \[\e[38;5;196m\]#\[\e[0m\] '
else
    # User: cyan indicator
    PS1='\[\e[38;5;39m\]\u\[\e[38;5;240m\]@\[\e[38;5;45m\]titan \[\e[38;5;245m\]\w \[\e[38;5;39m\]>\[\e[0m\] '
fi

# ─── Aliases ────────────────────────────────────────────────
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias cls='clear'

# Titan shortcuts
alias ops='python3 /opt/titan/apps/app_unified.py &'
alias genesis='python3 /opt/titan/apps/app_genesis.py &'
alias cerberus='python3 /opt/titan/apps/app_cerberus.py &'
alias kyc='python3 /opt/titan/apps/app_kyc.py &'
alias browser='bash /opt/titan/bin/titan-browser &'
alias status='cat /opt/titan/state/.first-boot-complete 2>/dev/null || echo "First boot not complete"'
alias shields='python3 -c "import sys; sys.path.insert(0,\"/opt/titan/core\"); from titan_master_verify import main; main()" 2>/dev/null'

# ─── Environment ────────────────────────────────────────────
export TITAN_ROOT="/opt/titan"
export EDITOR=nano
export VISUAL=nano
export TERM=xterm-256color

# ─── MOTD on first terminal open ────────────────────────────
if [ -z "$TITAN_MOTD_SHOWN" ] && [ -t 1 ]; then
    export TITAN_MOTD_SHOWN=1
    echo ""
    echo -e "  \e[38;5;39m╔══════════════════════════════════════╗\e[0m"
    echo -e "  \e[38;5;39m║\e[0m   \e[1;38;5;39mTitan OS\e[0m V7.0.3 Singularity     \e[38;5;39m║\e[0m"
    echo -e "  \e[38;5;39m║\e[0m   Type \e[38;5;45mops\e[0m to launch Operation Center \e[38;5;39m║\e[0m"
    echo -e "  \e[38;5;39m╚══════════════════════════════════════╝\e[0m"
    echo ""
fi
