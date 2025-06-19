#!/bin/bash

# FIM System Cleanup Script
# =========================
# Bu script FIM s# Veri dosyalarını da silmek isteyip istemediğini sor
echo ""
read -p "🗑️  Veri dosyalarını da silmek istiyor musunuz? (database, logs) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Veri dosyaları siliniyor..."
    if [ "$PRODUCTION_MODE" = true ]; then
        sudo rm -rf /opt/fim/data/*.db* /opt/fim/logs/*.log 2>/dev/null || true
    else
        cd "$PROJECT_DIR"
        rm -rf ./data/*.db* ./logs/*.log 2>/dev/null || true
    fi
    log_success "Veri dosyaları silindi"
elseen temizler.

set -e

# Production mode detection
PRODUCTION_MODE=false
COMPOSE_FILE="docker-compose.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_DIR/docker"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --production|--prod|-p)
            PRODUCTION_MODE=true
            COMPOSE_FILE="docker-compose.prod.yml"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--production|--prod|-p]"
            exit 1
            ;;
    esac
done

# Set full compose file path
COMPOSE_PATH="$DOCKER_DIR/$COMPOSE_FILE"

# Renkli output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo -e "${YELLOW}"
echo "================================================================"
echo "🧹 FIM System Cleanup"
if [ "$PRODUCTION_MODE" = true ]; then
    echo "🏭 Production Mode"
else
    echo "🔧 Development Mode"
fi
echo "================================================================"
echo -e "${NC}"

# Container'ları durdur ve kaldır
log_info "FIM container'ları durduruluyor ($COMPOSE_FILE)..."
cd "$PROJECT_DIR"
docker-compose -f "$COMPOSE_PATH" down --remove-orphans 2>/dev/null || true

# Docker imajlarını kaldır (sadece FIM ile ilgili olanları)
log_info "FIM Docker imajları kaldırılıyor..."
docker rmi $(docker images "*fim*" -q) 2>/dev/null || true
docker rmi $(docker images "*basicfim*" -q) 2>/dev/null || true

# Network'ü kaldır
log_info "FIM network'ü kaldırılıyor..."
docker network rm fim-network 2>/dev/null || true

# Build cache'i temizle
log_info "Docker build cache temizleniyor..."
docker builder prune -f 2>/dev/null || true

# Dangling imajları ve container'ları temizle
log_info "Kullanılmayan Docker kaynaklarını temizleniyor..."
docker system prune -f 2>/dev/null || true

# Veri dosyalarını da silmek isteyip istemediğini sor
echo ""
read -p "🗑️  Veri dosyalarını da silmek istiyor musunuz? (database, logs) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Veri dosyları siliniyor..."
    if [ "$PRODUCTION_MODE" = true ]; then
        sudo rm -rf /opt/fim/data/* /opt/fim/logs/* 2>/dev/null || true
    else
        cd "$PROJECT_DIR"
        rm -rf ./data/* ./logs/* 2>/dev/null || true
    fi
    log_success "Veri dosyları silindi"
else
    log_info "Veri dosyları korundu"
fi

log_success "FIM sistemi tamamen temizlendi!"
echo ""
echo "Sistemi yeniden başlatmak için: $PROJECT_DIR/fim start"
