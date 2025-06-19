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
        --clean)
            CLEAN_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--production|--prod|-p] [--clean]"
            exit 1
            ;;
    esac
done

# Set full compose file path
COMPOSE_PATH="$DOCKER_DIR/$COMPOSE_FILE"

# Banner
echo -e "${PURPLE}"
echo "================================================================"
echo "🔒 FIM (File Integrity Monitoring) System"
if [ "$PRODUCTION_MODE" = true ]; then
    echo "🏭 Production Mode"
else
    echo "🔧 Development Mode"
fi
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
cd "$PROJECT_DIR"
if [ "$PRODUCTION_MODE" = true ]; then
    # Production mode: system directories
    sudo mkdir -p /opt/fim/data /opt/fim/logs
    sudo chown $USER:$USER /opt/fim/data /opt/fim/logs
    log_info "Production dizinleri oluşturuldu: /opt/fim/"
else
    # Development mode: local directories
    mkdir -p ./data ./logs
    log_info "Development dizinleri oluşturuldu: ./data ./logs"
fi

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
if [ "$CLEAN_MODE" = true ]; then
    log_warning "Mevcut FIM container'ları temizleniyor..."
    docker-compose -f "$COMPOSE_PATH" down --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
    log_success "Temizlik tamamlandı"
fi

# Database başlatma
log_info "Database başlatılıyor ($COMPOSE_FILE)..."
docker-compose -f "$COMPOSE_PATH" run --rm fim-db-init

if [ $? -eq 0 ]; then
    log_success "Database başarıyla kuruldu ✓"
else
    log_error "Database kurulumunda hata oluştu!"
    exit 1
fi

# Ana servisleri başlat
log_info "FIM servisleri başlatılıyor ($COMPOSE_FILE)..."
docker-compose -f "$COMPOSE_PATH" up -d fim-api fim-frontend

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
docker-compose -f "$COMPOSE_PATH" ps

if [ "$PRODUCTION_MODE" = true ]; then
    log_success "🏭 FIM Production sistemi hazır! Web tarayıcınızda http://localhost:3000 adresini ziyaret edin."
    log_info "Production verileri: /opt/fim/ dizininde saklanmaktadır."
else
    log_success "🔧 FIM Development sistemi hazır! Web tarayıcınızda http://localhost:3000 adresini ziyaret edin."
    log_info "Development verileri: ./data ve ./logs dizinlerinde saklanmaktadır."
fi
