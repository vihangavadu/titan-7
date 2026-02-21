#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V7.6 — Self-Hosted Tool Stack Installer
# One-shot installer for all self-hosted services
# ═══════════════════════════════════════════════════════════════════════════
#
# Tools installed:
#   A. Success Rate:  GeoIP, IP Quality, CreepJS, Proxy Monitor
#   B. UX:            Uptime Kuma, Ntfy, Grafana+Prometheus
#   C. Planning:      n8n, Redis, NocoDB
#   D. Analysis:      Playwright, Wappalyzer, Nuclei
#   E. Infra:         MinIO, Loki
#
# Usage: bash install_self_hosted_stack.sh [all|minimal|analysis|monitoring]
#   all      — Install everything
#   minimal  — GeoIP + Redis + Ntfy + Playwright (recommended start)
#   analysis — Playwright + Wappalyzer + Nuclei + CreepJS
#   monitoring — Uptime Kuma + Grafana + Prometheus + Loki
#
# VPS Requirements: Debian 12, 32GB RAM, 400GB SSD
# ═══════════════════════════════════════════════════════════════════════════

set -e

INSTALL_MODE="${1:-minimal}"
TITAN_DATA="/opt/titan/data"
TITAN_TOOLS="/opt/titan/tools"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.6 — Self-Hosted Tool Stack Installer              ║"
echo "║  Mode: $INSTALL_MODE                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Prerequisites ──
echo "── [0/7] Prerequisites ──"
apt-get update -qq
apt-get install -y -qq curl wget gnupg2 apt-transport-https ca-certificates > /dev/null 2>&1
echo "[✓] System packages updated"

PYTHON=$(command -v python3 || command -v python)
echo "[✓] Python: $($PYTHON --version)"

# Create directories
mkdir -p $TITAN_DATA/{geoip,redis,minio,grafana,prometheus,loki,vector_db,web_intel_cache}
mkdir -p $TITAN_TOOLS/{creepjs,nuclei}
echo "[✓] Directories created"

# ═══════════════════════════════════════════════════════════════════════════
# A1. GeoIP — MaxMind GeoLite2 Offline Database
# ═══════════════════════════════════════════════════════════════════════════
install_geoip() {
    echo ""
    echo "── [A1] GeoIP — MaxMind GeoLite2 ──"
    $PYTHON -m pip install --quiet geoip2 2>&1 | tail -1

    GEOIP_DIR="$TITAN_DATA/geoip"
    MMDB="$GEOIP_DIR/GeoLite2-City.mmdb"

    if [ -f "$MMDB" ]; then
        echo "[✓] GeoLite2-City.mmdb already exists ($(du -h $MMDB | cut -f1))"
        return
    fi

    # MaxMind requires a license key for download
    MAXMIND_KEY="${MAXMIND_LICENSE_KEY:-}"
    if [ -n "$MAXMIND_KEY" ]; then
        echo "[*] Downloading GeoLite2-City.mmdb..."
        wget -q "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=${MAXMIND_KEY}&suffix=tar.gz" -O /tmp/geolite2.tar.gz
        tar -xzf /tmp/geolite2.tar.gz -C /tmp/
        find /tmp/ -name "GeoLite2-City.mmdb" -exec mv {} "$MMDB" \;
        rm -f /tmp/geolite2.tar.gz
        echo "[✓] GeoLite2-City.mmdb downloaded ($(du -h $MMDB | cut -f1))"
    else
        # Try DB-IP free alternative (no key needed)
        echo "[*] No MAXMIND_LICENSE_KEY set. Trying DB-IP free alternative..."
        MONTH=$(date +%Y-%m)
        wget -q "https://download.db-ip.com/free/dbip-city-lite-${MONTH}.mmdb.gz" -O /tmp/dbip.mmdb.gz 2>/dev/null || true
        if [ -f /tmp/dbip.mmdb.gz ]; then
            gunzip -f /tmp/dbip.mmdb.gz
            mv /tmp/dbip.mmdb "$MMDB" 2>/dev/null || true
            echo "[✓] DB-IP City Lite downloaded as fallback"
        else
            echo "[!] GeoIP DB not downloaded. Set MAXMIND_LICENSE_KEY or download manually."
            echo "    Get free key: https://www.maxmind.com/en/geolite2/signup"
            echo "    Place at: $MMDB"
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# A3. CreepJS — Self-Hosted Fingerprint Testing
# ═══════════════════════════════════════════════════════════════════════════
install_creepjs() {
    echo ""
    echo "── [A3] CreepJS — Fingerprint Tester ──"
    CREEPJS_DIR="$TITAN_TOOLS/creepjs"

    if [ -d "$CREEPJS_DIR/.git" ]; then
        echo "[✓] CreepJS already cloned"
        cd "$CREEPJS_DIR" && git pull --quiet 2>/dev/null || true
        return
    fi

    git clone --quiet --depth 1 https://github.com/nicedoc/creepjs.git "$CREEPJS_DIR" 2>/dev/null || \
    git clone --quiet --depth 1 https://github.com/nicedoc/nicedoc.io.git "$CREEPJS_DIR" 2>/dev/null || {
        # Fallback: create a minimal fingerprint test page
        mkdir -p "$CREEPJS_DIR"
        cat > "$CREEPJS_DIR/index.html" << 'FPHTML'
<!DOCTYPE html>
<html><head><title>Titan Fingerprint Test</title>
<style>body{font-family:monospace;background:#1a1a2e;color:#0f0;padding:20px}
table{border-collapse:collapse}td{border:1px solid #333;padding:4px 8px}
.warn{color:#ff0}.fail{color:#f00}.pass{color:#0f0}</style></head>
<body><h2>TITAN Fingerprint QA</h2><div id="results">Testing...</div>
<script>
const r=[];
function add(k,v,s){r.push({key:k,value:v,status:s})}
add('User-Agent',navigator.userAgent,'info');
add('Platform',navigator.platform,'info');
add('Languages',JSON.stringify(navigator.languages),'info');
add('Timezone',Intl.DateTimeFormat().resolvedOptions().timeZone,'info');
add('Screen',screen.width+'x'+screen.height,'info');
add('Color Depth',screen.colorDepth+'bit','info');
add('Device Memory',(navigator.deviceMemory||'N/A')+'GB','info');
add('Hardware Concurrency',navigator.hardwareConcurrency||'N/A','info');
add('WebGL Vendor',function(){try{var c=document.createElement('canvas'),g=c.getContext('webgl');var d=g.getExtension('WEBGL_debug_renderer_info');return g.getParameter(d.UNMASKED_VENDOR_WEBGL)}catch(e){return'N/A'}}(),'info');
add('WebGL Renderer',function(){try{var c=document.createElement('canvas'),g=c.getContext('webgl');var d=g.getExtension('WEBGL_debug_renderer_info');return g.getParameter(d.UNMASKED_RENDERER_WEBGL)}catch(e){return'N/A'}}(),'info');
add('Canvas Hash',function(){try{var c=document.createElement('canvas');c.width=200;c.height=50;var x=c.getContext('2d');x.textBaseline='top';x.font='14px Arial';x.fillStyle='#f60';x.fillRect(0,0,200,50);x.fillStyle='#069';x.fillText('Titan FP Test 🎭',2,15);return c.toDataURL().slice(-32)}catch(e){return'N/A'}}(),'info');
add('Do Not Track',navigator.doNotTrack||'unset','info');
add('Cookies Enabled',navigator.cookieEnabled,'info');
add('Touch Support','ontouchstart' in window?'YES':'NO','info');
var h='<table><tr><th>Property</th><th>Value</th></tr>';
r.forEach(function(i){h+='<tr><td>'+i.key+'</td><td>'+i.value+'</td></tr>'});
h+='</table>';
document.getElementById('results').innerHTML=h;
</script></body></html>
FPHTML
        echo "[✓] Created minimal fingerprint test page"
    }
    echo "[✓] CreepJS ready at $CREEPJS_DIR"
}

# ═══════════════════════════════════════════════════════════════════════════
# B5. Uptime Kuma — Service Monitoring
# ═══════════════════════════════════════════════════════════════════════════
install_uptime_kuma() {
    echo ""
    echo "── [B5] Uptime Kuma — Service Monitoring ──"

    if command -v docker &>/dev/null; then
        if docker ps -a --format '{{.Names}}' | grep -q uptime-kuma; then
            echo "[✓] Uptime Kuma container already exists"
            docker start uptime-kuma 2>/dev/null || true
            return
        fi
        docker run -d \
            --name uptime-kuma \
            --restart unless-stopped \
            -p 3001:3001 \
            -v $TITAN_DATA/uptime-kuma:/app/data \
            louislam/uptime-kuma:1 2>/dev/null
        echo "[✓] Uptime Kuma started on port 3001"
    else
        echo "[!] Docker not installed. Install Docker first or use npm:"
        echo "    npm install -g uptime-kuma && uptime-kuma"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# B6. Ntfy — Push Notifications
# ═══════════════════════════════════════════════════════════════════════════
install_ntfy() {
    echo ""
    echo "── [B6] Ntfy — Push Notifications ──"

    if command -v ntfy &>/dev/null; then
        echo "[✓] Ntfy already installed"
        return
    fi

    # Install via apt (Debian/Ubuntu)
    if [ -f /etc/debian_version ]; then
        curl -sSf https://archive.heckel.io/apt/pubkey.txt | apt-key add - 2>/dev/null
        echo "deb https://archive.heckel.io/apt debian main" > /etc/apt/sources.list.d/ntfy.list
        apt-get update -qq 2>/dev/null
        apt-get install -y -qq ntfy 2>/dev/null && {
            # Configure
            mkdir -p /etc/ntfy
            cat > /etc/ntfy/server.yml << 'EOF'
base-url: "http://127.0.0.1:8090"
listen-http: ":8090"
cache-file: "/var/cache/ntfy/cache.db"
behind-proxy: false
EOF
            systemctl enable ntfy 2>/dev/null
            systemctl start ntfy 2>/dev/null
            echo "[✓] Ntfy installed and started on port 8090"
            return
        }
    fi

    # Fallback: Docker
    if command -v docker &>/dev/null; then
        docker run -d \
            --name ntfy \
            --restart unless-stopped \
            -p 8090:80 \
            -v $TITAN_DATA/ntfy:/var/cache/ntfy \
            binwiederhier/ntfy serve 2>/dev/null
        echo "[✓] Ntfy started via Docker on port 8090"
    else
        echo "[!] Could not install Ntfy. Install Docker or download binary from https://ntfy.sh"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# C9. Redis — Fast Cache & State
# ═══════════════════════════════════════════════════════════════════════════
install_redis() {
    echo ""
    echo "── [C9] Redis — Fast Cache & State ──"

    if command -v redis-server &>/dev/null; then
        echo "[✓] Redis already installed"
        systemctl enable redis-server 2>/dev/null || true
        systemctl start redis-server 2>/dev/null || true
        return
    fi

    apt-get install -y -qq redis-server 2>/dev/null && {
        # Optimize for Titan
        cat >> /etc/redis/redis.conf << 'EOF'

# Titan OS optimizations
maxmemory 512mb
maxmemory-policy allkeys-lru
save ""
appendonly no
EOF
        systemctl enable redis-server
        systemctl restart redis-server
        echo "[✓] Redis installed and optimized (512MB max, LRU eviction)"
    } || echo "[!] Redis installation failed"

    $PYTHON -m pip install --quiet redis 2>&1 | tail -1
}

# ═══════════════════════════════════════════════════════════════════════════
# D11. Playwright — Headless Browser for Target Probing
# ═══════════════════════════════════════════════════════════════════════════
install_playwright() {
    echo ""
    echo "── [D11] Playwright — Target Site Prober ──"

    $PYTHON -m pip install --quiet playwright 2>&1 | tail -1
    $PYTHON -m playwright install chromium --with-deps 2>&1 | tail -3
    echo "[✓] Playwright + Chromium installed"
}

# ═══════════════════════════════════════════════════════════════════════════
# D12. Wappalyzer — Technology Detection
# ═══════════════════════════════════════════════════════════════════════════
install_wappalyzer() {
    echo ""
    echo "── [D12] Wappalyzer — Tech Stack Detection ──"
    $PYTHON -m pip install --quiet python-Wappalyzer 2>&1 | tail -1
    echo "[✓] Wappalyzer installed"
}

# ═══════════════════════════════════════════════════════════════════════════
# D13. Nuclei — Vulnerability Scanner
# ═══════════════════════════════════════════════════════════════════════════
install_nuclei() {
    echo ""
    echo "── [D13] Nuclei — Vulnerability Scanner ──"

    if command -v nuclei &>/dev/null; then
        echo "[✓] Nuclei already installed"
        return
    fi

    # Install via Go binary
    NUCLEI_VERSION="3.3.7"
    wget -q "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" -O /tmp/nuclei.zip 2>/dev/null && {
        unzip -o -q /tmp/nuclei.zip -d /usr/local/bin/ nuclei
        chmod +x /usr/local/bin/nuclei
        rm /tmp/nuclei.zip
        nuclei -update-templates -silent 2>/dev/null || true
        echo "[✓] Nuclei ${NUCLEI_VERSION} installed"
    } || echo "[!] Nuclei download failed"
}

# ═══════════════════════════════════════════════════════════════════════════
# B7. Grafana + Prometheus — Metrics Dashboard
# ═══════════════════════════════════════════════════════════════════════════
install_grafana_prometheus() {
    echo ""
    echo "── [B7] Grafana + Prometheus — Metrics Dashboard ──"

    if ! command -v docker &>/dev/null; then
        echo "[!] Docker required for Grafana+Prometheus. Skipping."
        return
    fi

    # Prometheus
    if ! docker ps -a --format '{{.Names}}' | grep -q titan-prometheus; then
        mkdir -p $TITAN_DATA/prometheus
        cat > $TITAN_DATA/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'titan-backend'
    static_configs:
      - targets: ['host.docker.internal:8000']
  - job_name: 'node'
    static_configs:
      - targets: ['host.docker.internal:9100']
EOF
        docker run -d \
            --name titan-prometheus \
            --restart unless-stopped \
            -p 9090:9090 \
            -v $TITAN_DATA/prometheus:/etc/prometheus \
            prom/prometheus 2>/dev/null
        echo "[✓] Prometheus started on port 9090"
    else
        echo "[✓] Prometheus already exists"
    fi

    # Grafana
    if ! docker ps -a --format '{{.Names}}' | grep -q titan-grafana; then
        docker run -d \
            --name titan-grafana \
            --restart unless-stopped \
            -p 3000:3000 \
            -v $TITAN_DATA/grafana:/var/lib/grafana \
            -e GF_SECURITY_ADMIN_PASSWORD=titan \
            grafana/grafana-oss 2>/dev/null
        echo "[✓] Grafana started on port 3000 (admin/titan)"
    else
        echo "[✓] Grafana already exists"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# C8. n8n — Workflow Automation
# ═══════════════════════════════════════════════════════════════════════════
install_n8n() {
    echo ""
    echo "── [C8] n8n — Workflow Automation ──"

    if ! command -v docker &>/dev/null; then
        echo "[!] Docker required for n8n. Skipping."
        return
    fi

    if ! docker ps -a --format '{{.Names}}' | grep -q titan-n8n; then
        docker run -d \
            --name titan-n8n \
            --restart unless-stopped \
            -p 5678:5678 \
            -v $TITAN_DATA/n8n:/home/node/.n8n \
            -e N8N_BASIC_AUTH_ACTIVE=true \
            -e N8N_BASIC_AUTH_USER=titan \
            -e N8N_BASIC_AUTH_PASSWORD=titan \
            n8nio/n8n 2>/dev/null
        echo "[✓] n8n started on port 5678 (titan/titan)"
    else
        echo "[✓] n8n already exists"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# Python dependencies for all tools
# ═══════════════════════════════════════════════════════════════════════════
install_python_deps() {
    echo ""
    echo "── Python Dependencies ──"
    $PYTHON -m pip install --quiet \
        geoip2 \
        redis \
        minio \
        python-Wappalyzer \
        playwright \
        2>&1 | tail -1
    echo "[✓] Python packages installed"
}

# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

case "$INSTALL_MODE" in
    minimal)
        echo "Installing MINIMAL stack (GeoIP + Redis + Ntfy + Playwright)..."
        install_geoip
        install_redis
        install_ntfy
        install_playwright
        install_python_deps
        ;;
    analysis)
        echo "Installing ANALYSIS stack (Playwright + Wappalyzer + Nuclei + CreepJS)..."
        install_playwright
        install_wappalyzer
        install_nuclei
        install_creepjs
        install_python_deps
        ;;
    monitoring)
        echo "Installing MONITORING stack (Uptime Kuma + Grafana + Prometheus)..."
        install_uptime_kuma
        install_grafana_prometheus
        install_ntfy
        ;;
    all)
        echo "Installing ALL tools..."
        install_geoip
        install_redis
        install_ntfy
        install_creepjs
        install_uptime_kuma
        install_grafana_prometheus
        install_n8n
        install_playwright
        install_wappalyzer
        install_nuclei
        install_python_deps
        ;;
    *)
        echo "Unknown mode: $INSTALL_MODE"
        echo "Usage: $0 [all|minimal|analysis|monitoring]"
        exit 1
        ;;
esac

# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════
echo ""
echo "── Verification ──"
cd /opt/titan/core 2>/dev/null || true

$PYTHON -c "
from titan_self_hosted_stack import get_self_hosted_stack
stack = get_self_hosted_stack()
status = stack.get_status()
print(f'Available: {status[\"available_tools\"]}/{status[\"total_tools\"]} tools')
for name, info in status['tools'].items():
    icon = '✓' if info.get('available') else '✗'
    print(f'  [{icon}] {name}')
" 2>/dev/null || echo "[!] Verification script failed (non-critical)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Installation Complete!                                      ║"
echo "║                                                              ║"
echo "║  Service Ports:                                              ║"
echo "║    Uptime Kuma:  http://localhost:3001                       ║"
echo "║    Grafana:      http://localhost:3000 (admin/titan)         ║"
echo "║    Prometheus:   http://localhost:9090                       ║"
echo "║    n8n:          http://localhost:5678 (titan/titan)         ║"
echo "║    Ntfy:         http://localhost:8090                       ║"
echo "║    Redis:        localhost:6379                              ║"
echo "║    CreepJS:      http://localhost:8787 (start manually)      ║"
echo "║                                                              ║"
echo "║  Next: systemctl restart titan-backend                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
