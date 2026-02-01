#!/bin/bash

# ============================================
# Zivv Agent Deployment Script
# ============================================
# Usage: ./deploy.sh [options]
#   --force       Force pull and restart even if no changes
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Parse arguments
FORCE=false

for arg in "$@"; do
    case $arg in
        --force) FORCE=true ;;
    esac
done

# 1. Load .env file
if [ -f .env ]; then
    log_info "Loading .env file..."
    set -a
    source .env
    set +a
else
    log_warn ".env file not found. Make sure environment variables are set."
fi

# 2. Validate required environment variables
REQUIRED_VARS=("CR_PAT")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_error "Required environment variable $var is not set (GitHub Personal Access Token for GHCR)."
        exit 1
    fi
done
log_success "Environment variables validated"

# 3. Login to GitHub Container Registry
log_info "Logging in to GitHub Container Registry..."
echo "$CR_PAT" | docker login ghcr.io -u holdlijun --password-stdin > /dev/null 2>&1
log_success "Logged in to GHCR"

# 4. Pull latest images
log_info "Pulling latest images..."
docker compose pull zivv-agent

# 5. Restart containers
log_info "Restarting zivv-agent container..."
docker compose up -d --force-recreate zivv-agent
log_success "Container restarted"

# 6. Cleanup old images
log_info "Cleaning up old Docker images..."
docker image prune -f > /dev/null 2>&1
log_success "Old images removed"

# 7. Show status
echo ""
echo "============================================"
echo -e "${GREEN}🚀 Zivv Agent Deployment Complete!${NC}"
echo "============================================"
echo ""
echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "zivv-agent|NAMES"
echo ""
log_info "View logs: docker compose logs -f zivv-agent"
