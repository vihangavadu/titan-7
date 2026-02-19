#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V7.0.3 SINGULARITY — Pre-Build Environment Check
# ═══════════════════════════════════════════════════════════════════════════
# PURPOSE: Verify all required environment variables and API keys are present
#          before allowing ISO build to proceed.
#
# USAGE: ./scripts/pre_build_env_check.sh [--strict]
#        --strict: Exit with error if any placeholder values remain
#
# EXIT CODES:
#   0 = All checks passed
#   1 = Missing required environment variables
#   2 = Placeholder values detected (strict mode)
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

STRICT_MODE=0
if [[ "$1" == "--strict" ]]; then
    STRICT_MODE=1
fi

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  TITAN V7.0.3 SINGULARITY — PRE-BUILD ENVIRONMENT CHECK${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"

# Locate the titan.env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$REPO_ROOT/iso/config/includes.chroot/opt/titan/config/titan.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}[FATAL] titan.env not found at: $ENV_FILE${NC}"
    exit 1
fi

echo -e "\n${CYAN}[1] Checking titan.env location...${NC}"
echo -e "  ${GREEN}[OK]${NC} Found: $ENV_FILE"
((PASS_COUNT++))

# Required environment variables (must be present)
REQUIRED_VARS=(
    "TITAN_PROXY_POOL_FILE"
    "TITAN_PROFILES_DIR"
    "TITAN_STATE_DIR"
)

# Optional but recommended (warn if placeholder)
OPTIONAL_VARS=(
    "TITAN_CLOUD_URL"
    "TITAN_API_KEY"
    "TITAN_MODEL"
    "TITAN_PROXY_PROVIDER"
    "TITAN_PROXY_USERNAME"
    "TITAN_PROXY_PASSWORD"
    "TITAN_VPN_SERVER_IP"
    "TITAN_VPN_UUID"
    "TITAN_VPN_PUBLIC_KEY"
    "TITAN_VPN_PRIVATE_KEY"
    "TITAN_TAILSCALE_AUTH_KEY"
)

# Placeholder patterns
PLACEHOLDER_PATTERNS=(
    "REPLACE_WITH"
    "demo-key"
    "demo-user"
    "demo-pass"
    "12345678-1234"
    "demo-public"
    "demo-private"
    "demo-short"
    "sk-demo"
    "tskey-auth-demo"
)

echo -e "\n${CYAN}[2] Checking required environment variables...${NC}"
for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" "$ENV_FILE"; then
        echo -e "  ${GREEN}[OK]${NC} $var defined"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}[FAIL]${NC} $var NOT FOUND"
        ((FAIL_COUNT++))
    fi
done

echo -e "\n${CYAN}[3] Checking optional environment variables...${NC}"
for var in "${OPTIONAL_VARS[@]}"; do
    if grep -q "^${var}=" "$ENV_FILE"; then
        # Get the value
        value=$(grep "^${var}=" "$ENV_FILE" | cut -d'=' -f2-)
        is_placeholder=0
        
        for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
            if [[ "$value" == *"$pattern"* ]]; then
                is_placeholder=1
                break
            fi
        done
        
        if [[ $is_placeholder -eq 1 ]]; then
            echo -e "  ${YELLOW}[WARN]${NC} $var = placeholder (operator must configure)"
            ((WARN_COUNT++))
        else
            echo -e "  ${GREEN}[OK]${NC} $var configured"
            ((PASS_COUNT++))
        fi
    else
        echo -e "  ${YELLOW}[WARN]${NC} $var not defined (feature may be disabled)"
        ((WARN_COUNT++))
    fi
done

echo -e "\n${CYAN}[4] Checking core configuration files...${NC}"

# Check nftables.conf
NFTABLES="$REPO_ROOT/iso/config/includes.chroot/etc/nftables.conf"
if [[ -f "$NFTABLES" ]]; then
    if grep -q "policy drop" "$NFTABLES"; then
        echo -e "  ${GREEN}[OK]${NC} nftables.conf: default-deny policy"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}[FAIL]${NC} nftables.conf: missing policy drop"
        ((FAIL_COUNT++))
    fi
else
    echo -e "  ${RED}[FAIL]${NC} nftables.conf not found"
    ((FAIL_COUNT++))
fi

# Check sysctl hardening
SYSCTL="$REPO_ROOT/iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf"
if [[ -f "$SYSCTL" ]]; then
    if grep -q "ip_default_ttl = 128" "$SYSCTL"; then
        echo -e "  ${GREEN}[OK]${NC} sysctl: Windows TTL masquerade enabled"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}[FAIL]${NC} sysctl: TTL masquerade not configured"
        ((FAIL_COUNT++))
    fi
else
    echo -e "  ${RED}[FAIL]${NC} 99-titan-hardening.conf not found"
    ((FAIL_COUNT++))
fi

echo -e "\n${CYAN}[5] Checking systemd services...${NC}"
SYSTEMD_DIR="$REPO_ROOT/iso/config/includes.chroot/etc/systemd/system"
REQUIRED_SERVICES=(
    "lucid-titan.service"
    "lucid-console.service"
    "lucid-ebpf.service"
    "titan-first-boot.service"
    "titan-dns.service"
)

for svc in "${REQUIRED_SERVICES[@]}"; do
    if [[ -f "$SYSTEMD_DIR/$svc" ]]; then
        echo -e "  ${GREEN}[OK]${NC} $svc"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}[FAIL]${NC} $svc NOT FOUND"
        ((FAIL_COUNT++))
    fi
done

# Summary
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
TOTAL=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
echo -e "  ${GREEN}PASS: $PASS_COUNT${NC}  |  ${YELLOW}WARN: $WARN_COUNT${NC}  |  ${RED}FAIL: $FAIL_COUNT${NC}  |  TOTAL: $TOTAL"

if [[ $FAIL_COUNT -gt 0 ]]; then
    echo -e "\n  ${RED}>>> PRE-BUILD CHECK: FAILED <<<${NC}"
    echo -e "  ${RED}$FAIL_COUNT critical issue(s) must be resolved before build.${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    exit 1
fi

if [[ $STRICT_MODE -eq 1 && $WARN_COUNT -gt 0 ]]; then
    echo -e "\n  ${YELLOW}>>> PRE-BUILD CHECK: WARNINGS (strict mode) <<<${NC}"
    echo -e "  ${YELLOW}$WARN_COUNT placeholder(s) detected. Configure before deployment.${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    exit 2
fi

echo -e "\n  ${GREEN}>>> PRE-BUILD CHECK: PASSED <<<${NC}"
if [[ $WARN_COUNT -gt 0 ]]; then
    echo -e "  ${YELLOW}Note: $WARN_COUNT placeholder(s) require operator configuration.${NC}"
fi
echo -e "  ${GREEN}System is ready for ISO build.${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
echo ""
exit 0
