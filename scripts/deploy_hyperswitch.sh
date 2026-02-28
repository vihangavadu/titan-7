#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TITAN OS — Hyperswitch Deployment Script
# ═══════════════════════════════════════════════════════════════════════════════
# Deploys Hyperswitch payment orchestrator on VPS via Docker Compose.
#
# Components:
#   - Hyperswitch App Server (port 8080)
#   - Hyperswitch Control Center (port 9000)
#   - PostgreSQL 15 (port 5432)
#   - Redis 7 (uses existing or port 6380)
#
# Usage:
#   ./deploy_hyperswitch.sh [--with-control-center] [--test-mode]
#
# Prerequisites:
#   - Docker & Docker Compose installed
#   - At least 4GB RAM available
#   - Ports 8080, 9000 available
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TITAN_ROOT="${SCRIPT_DIR}/.."
DEPLOY_DIR="/opt/titan/hyperswitch"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
ENV_FILE="/opt/titan/config/titan.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[HYPERSWITCH]${NC} $*"; }
warn() { echo -e "${YELLOW}[HYPERSWITCH]${NC} $*"; }
err()  { echo -e "${RED}[HYPERSWITCH]${NC} $*"; }

# ── Parse args ────────────────────────────────────────────────────────────────
WITH_CC=false
TEST_MODE=false

for arg in "$@"; do
    case "$arg" in
        --with-control-center) WITH_CC=true ;;
        --test-mode) TEST_MODE=true ;;
        *) warn "Unknown arg: $arg" ;;
    esac
done

# ── Pre-flight checks ────────────────────────────────────────────────────────

log "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    err "Docker not found. Install with: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v docker compose &>/dev/null && ! command -v docker-compose &>/dev/null; then
    err "Docker Compose not found."
    exit 1
fi

COMPOSE_CMD="docker compose"
if ! docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
fi

log "Docker: $(docker --version | head -1)"
log "Compose: $($COMPOSE_CMD version 2>/dev/null | head -1 || echo 'available')"

# ── Create deployment directory ───────────────────────────────────────────────

log "Creating deployment directory: ${DEPLOY_DIR}"
sudo mkdir -p "${DEPLOY_DIR}"
sudo chown "$(whoami)" "${DEPLOY_DIR}"

# ── Generate secrets ──────────────────────────────────────────────────────────

DB_PASS=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p | head -c 32)
ADMIN_KEY="admin_$(openssl rand -hex 24 2>/dev/null || head -c 48 /dev/urandom | xxd -p | head -c 48)"
API_KEY="api_$(openssl rand -hex 24 2>/dev/null || head -c 48 /dev/urandom | xxd -p | head -c 48)"
PK_KEY="pk_$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p | head -c 32)"

# ── Write Docker Compose ──────────────────────────────────────────────────────

log "Writing Docker Compose configuration..."

cat > "${COMPOSE_FILE}" << COMPOSE_EOF
version: "3.8"

services:
  hyperswitch-server:
    image: juspaydotin/hyperswitch-router:latest
    container_name: hyperswitch-server
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - ROUTER__SERVER__HOST=0.0.0.0
      - ROUTER__SERVER__PORT=8080
      - ROUTER__MASTER_DATABASE__USERNAME=hyperswitch
      - ROUTER__MASTER_DATABASE__PASSWORD=${DB_PASS}
      - ROUTER__MASTER_DATABASE__HOST=hyperswitch-db
      - ROUTER__MASTER_DATABASE__PORT=5432
      - ROUTER__MASTER_DATABASE__DBNAME=hyperswitch_db
      - ROUTER__REDIS__HOST=hyperswitch-redis
      - ROUTER__REDIS__PORT=6379
      - ROUTER__SECRETS__ADMIN_API_KEY=${ADMIN_KEY}
      - ROUTER__SECRETS__JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || echo "titan_jwt_secret_$(date +%s)")
      - ROUTER__LOCKER__LOCKER_ENABLED=false
      - RUN_ENV=sandbox
    depends_on:
      hyperswitch-db:
        condition: service_healthy
      hyperswitch-redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    networks:
      - hyperswitch-net

  hyperswitch-db:
    image: postgres:15
    container_name: hyperswitch-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=hyperswitch
      - POSTGRES_PASSWORD=${DB_PASS}
      - POSTGRES_DB=hyperswitch_db
    volumes:
      - hyperswitch-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hyperswitch -d hyperswitch_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - hyperswitch-net

  hyperswitch-redis:
    image: redis:7-alpine
    container_name: hyperswitch-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - hyperswitch-redis-data:/data
    networks:
      - hyperswitch-net

COMPOSE_EOF

# Add Control Center if requested
if [ "$WITH_CC" = true ]; then
    cat >> "${COMPOSE_FILE}" << CC_EOF
  hyperswitch-control-center:
    image: juspaydotin/hyperswitch-control-center:latest
    container_name: hyperswitch-control-center
    restart: unless-stopped
    ports:
      - "9000:9000"
    environment:
      - HYPERSWITCH_SERVER_URL=http://hyperswitch-server:8080
    depends_on:
      - hyperswitch-server
    networks:
      - hyperswitch-net

CC_EOF
fi

# Add volumes and networks
cat >> "${COMPOSE_FILE}" << FOOTER_EOF

volumes:
  hyperswitch-pgdata:
  hyperswitch-redis-data:

networks:
  hyperswitch-net:
    driver: bridge
FOOTER_EOF

log "Docker Compose written to ${COMPOSE_FILE}"

# ── Deploy ────────────────────────────────────────────────────────────────────

log "Pulling images (this may take a few minutes)..."
cd "${DEPLOY_DIR}"
$COMPOSE_CMD pull

log "Starting Hyperswitch stack..."
$COMPOSE_CMD up -d

# ── Wait for health ───────────────────────────────────────────────────────────

log "Waiting for Hyperswitch to become healthy..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
        log "Hyperswitch is healthy!"
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    warn "Hyperswitch did not become healthy within ${MAX_WAIT}s"
    warn "Check logs: cd ${DEPLOY_DIR} && $COMPOSE_CMD logs -f"
else
    log "Hyperswitch API: http://127.0.0.1:8080"
    [ "$WITH_CC" = true ] && log "Control Center: http://127.0.0.1:9000"
fi

# ── Update titan.env ──────────────────────────────────────────────────────────

log "Updating titan.env with Hyperswitch configuration..."

update_env_var() {
    local key="$1"
    local value="$2"
    local file="$3"
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

if [ -f "$ENV_FILE" ]; then
    update_env_var "TITAN_HYPERSWITCH_URL" "http://127.0.0.1:8080" "$ENV_FILE"
    update_env_var "TITAN_HYPERSWITCH_API_KEY" "${API_KEY}" "$ENV_FILE"
    update_env_var "TITAN_HYPERSWITCH_PUBLISHABLE_KEY" "${PK_KEY}" "$ENV_FILE"
    update_env_var "TITAN_HYPERSWITCH_ADMIN_KEY" "${ADMIN_KEY}" "$ENV_FILE"
    update_env_var "TITAN_HYPERSWITCH_CONTROL_CENTER_URL" "http://127.0.0.1:9000" "$ENV_FILE"
    update_env_var "TITAN_HYPERSWITCH_ENABLED" "1" "$ENV_FILE"
    log "titan.env updated"
else
    warn "titan.env not found at ${ENV_FILE} — create it manually"
fi

# ── Save credentials ──────────────────────────────────────────────────────────

CREDS_FILE="${DEPLOY_DIR}/credentials.txt"
cat > "${CREDS_FILE}" << CREDS_EOF
# Hyperswitch Credentials — Generated $(date -Iseconds)
# KEEP THIS FILE SECURE

ADMIN_KEY=${ADMIN_KEY}
API_KEY=${API_KEY}
PUBLISHABLE_KEY=${PK_KEY}
DB_PASSWORD=${DB_PASS}

HYPERSWITCH_URL=http://127.0.0.1:8080
CONTROL_CENTER_URL=http://127.0.0.1:9000
CREDS_EOF
chmod 600 "${CREDS_FILE}"
log "Credentials saved to ${CREDS_FILE}"

# ── Smoke test ────────────────────────────────────────────────────────────────

if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
    HEALTH=$(curl -sf http://127.0.0.1:8080/health)
    log "Health check: ${HEALTH}"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  HYPERSWITCH DEPLOYED SUCCESSFULLY${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  API:            ${CYAN}http://127.0.0.1:8080${NC}"
    [ "$WITH_CC" = true ] && echo -e "  Control Center: ${CYAN}http://127.0.0.1:9000${NC}"
    echo -e "  Admin Key:      ${YELLOW}${ADMIN_KEY:0:12}...${NC}"
    echo -e "  API Key:        ${YELLOW}${API_KEY:0:12}...${NC}"
    echo -e "  Credentials:    ${DEPLOY_DIR}/credentials.txt"
    echo -e "  Logs:           cd ${DEPLOY_DIR} && $COMPOSE_CMD logs -f"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
else
    err "Hyperswitch health check failed — check Docker logs"
    cd "${DEPLOY_DIR}" && $COMPOSE_CMD logs --tail=50
    exit 1
fi
