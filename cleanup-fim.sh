#!/bin/bash

# FIM System Cleanup Script
# =========================
# Bu script FIM sistemini tamamen temizler.

set -e

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
echo "================================================================"
echo -e "${NC}"

# Container'ları durdur ve kaldır
log_info "FIM container'ları durduruluyor..."
docker-compose down --remove-orphans 2>/dev/null || true

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
    rm -rf ./data/* 2>/dev/null || true
    rm -rf ./logs/* 2>/dev/null || true
    log_success "Veri dosyları silindi"
else
    log_info "Veri dosyları korundu"
fi

log_success "FIM sistemi tamamen temizlendi!"
echo ""
echo "Sistemi yeniden başlatmak için: ./start-fim.sh"
