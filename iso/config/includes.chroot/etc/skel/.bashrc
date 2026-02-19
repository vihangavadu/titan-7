# TITAN V7.0 SINGULARITY — Shell Environment

# PATH
export PATH="/opt/titan/bin:/opt/lucid-empire/bin:$PATH"

# History
HISTSIZE=1000
HISTFILESIZE=2000
HISTCONTROL=ignoredups:ignorespace

# Aliases
alias titan-status='python3 /opt/titan/core/titan_env.py --status 2>/dev/null || echo "Run titan-configure first"'
alias titan-console='python3 /opt/lucid-empire/backend/server.py'
alias titan-browser='/opt/titan/bin/titan-browser'
alias titan-vpn='/opt/titan/bin/titan-vpn'
alias titan-configure='/opt/titan/bin/titan-configure'
alias titan-killswitch='python3 -c "from core.kill_switch import send_panic_signal; send_panic_signal()"'
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'

# Colored prompt
PS1='\[\033[01;32m\]titan\[\033[00m\]@\[\033[01;34m\]singularity\[\033[00m\]:\[\033[01;33m\]\w\[\033[00m\]\$ '

# MOTD
if [ -z "$TITAN_MOTD_SHOWN" ]; then
    echo ""
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║  TITAN V7.0 SINGULARITY — READY         ║"
    echo "  ║  Type 'titan-configure' to begin setup   ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo ""
    export TITAN_MOTD_SHOWN=1
fi
