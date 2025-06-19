#!/bin/bash

# FIM (File Integrity Monitoring) Docker Startup Script
# =====================================================
# Bu script FIM sisteminin tüm bileşenlerini Docker içerisinde başlatır.

set -e  # Hata durumunda script'i durdur

# Renkli output için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${PURPLE}"
echo "================================================================"
echo "🔒 FIM (File Integrity Monitoring) System"
echo "================================================================"
echo -e "${NC}"

# Fonksiyonlar
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Gerekli dizinleri oluştur
log_info "Gerekli dizinler kontrol ediliyor..."
mkdir -p ./data ./logs

# Config dosyasının varlığını kontrol et
if [ ! -f "./config/config.yaml" ]; then
    log_warning "Config dosyası bulunamadı! ./config/config.yaml dosyasını oluşturun."
    log_info "Örnek config dosyası için dokumentasyona bakın."
fi

# Docker ve Docker Compose kontrolü
if ! command -v docker &> /dev/null; then
    log_error "Docker kurulu değil! Lütfen Docker'ı kurun."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose kurulu değil! Lütfen Docker Compose'u kurun."
    exit 1
fi

# Docker servisinin çalışıp çalışmadığını kontrol et
if ! docker info &> /dev/null; then
    log_error "Docker servisi çalışmıyor! Lütfen Docker'ı başlatın."
    exit 1
fi

log_success "Docker kurulu ve çalışıyor ✓"

# Mevcut container'ları temizle (opsiyonel)
if [ "$1" = "--clean" ]; then
    log_warning "Mevcut FIM container'ları temizleniyor..."
    docker-compose down --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
    log_success "Temizlik tamamlandı"
fi

# Database başlatma
log_info "Database başlatılıyor..."
docker-compose run --rm fim-db-init

if [ $? -eq 0 ]; then
    log_success "Database başarıyla kuruldu ✓"
else
    log_error "Database kurulumunda hata oluştu!"
    exit 1
fi

# Ana servisleri başlat
log_info "FIM servisleri başlatılıyor..."
docker-compose up -d fim-api fim-frontend

# Servislerin başlamasını bekle
log_info "Servisler başlatılıyor, lütfen bekleyin..."
sleep 10

# Health check
log_info "Servis durumları kontrol ediliyor..."

# API Health Check
if curl -s -f http://localhost:8000/health &>/dev/null; then
    log_success "FIM API servisi çalışıyor ✓ (http://localhost:8000)"
else
    log_warning "FIM API servisi henüz hazır değil, biraz daha bekleyin..."
fi

# Frontend Health Check
if curl -s -f http://localhost:3000/health.html &>/dev/null; then
    log_success "FIM Frontend servisi çalışıyor ✓ (http://localhost:3000)"
else
    log_warning "FIM Frontend servisi henüz hazır değil, biraz daha bekleyin..."
fi

# Sonuç
echo -e "${GREEN}"
echo "================================================================"
echo "🎉 FIM Sistemi Başarıyla Başlatıldı!"
echo "================================================================"
echo -e "${NC}"
echo "📋 Servis URL'leri:"
echo "   • Web UI:     http://localhost:3000"
echo "   • API:        http://localhost:8000"
echo "   • Health:     http://localhost:8000/health"
echo "   • API Docs:   http://localhost:8000/docs"
echo ""
echo "📁 Veri Dizinleri:"
echo "   • Database:   ./data/"
echo "   • Logs:       ./logs/"
echo ""
echo "🔧 Yararlı Komutlar:"
echo "   • Logları görmek için:     docker-compose logs -f"
echo "   • Durumu kontrol etmek:    docker-compose ps"
echo "   • Durdurmak için:          docker-compose down"
echo "   • Yeniden başlatmak:       $0 --clean"
echo ""

# Container durumlarını göster
log_info "Container durumları:"
docker-compose ps

log_success "FIM sistemi hazır! Web tarayıcınızda http://localhost:3000 adresini ziyaret edin."
