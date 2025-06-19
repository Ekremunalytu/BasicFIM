# 🔒 FIM (File Integrity Monitoring) System

Modern, containerized dosya bütünlüğü izleme sistemi. Tam Docker destekli, ana makinenizi kirletmeden çalışır.

## 🌟 Özellikler

- **🐳 Tam Docker Destekli**: Ana makinenizi kirletmeden çalışır
- **🎯 Profil Tabanlı İzleme**: Light, Balanced, Paranoid profilleri
- **🌐 Web Arayüzü**: Modern, responsive dashboard
- **🔄 REST API**: Programatik erişim için tam API
- **📊 Gerçek Zamanlı İzleme**: Dosya değişikliklerini anında yakalama
- **🗃️ SQLite Database**: Hafif ve hızlı veri saklama
- **📱 Health Monitoring**: Sistem durumu izleme
- **🔧 Kolay Kurulum**: Tek komutla başlatma

## 📁 Proje Yapısı

```
FIM/
├── services/                    # Mikro servisler
│   ├── fim-api/                 # Backend API servisi
│   │   ├── fim_scanner/         # Ana FIM modülleri
│   │   │   ├── database/        # Database yönetimi
│   │   │   ├── settings/        # Konfigürasyon
│   │   │   ├── core/            # Core monitoring logic
│   │   │   ├── models/          # Data models
│   │   │   └── main.py         # Ana uygulama
│   │   ├── Dockerfile          # API container tanımı
│   │   ├── requirements.txt    # Python dependencies
│   │   └── .dockerignore       # Docker ignore rules
│   └── frontend/               # Frontend servisi
│       ├── static/             # Web arayüzü dosyaları
│       │   ├── index.html      # Ana sayfa
│       │   └── health.html     # Health check sayfası
│       ├── Dockerfile          # Frontend container tanımı
│       ├── nginx.conf          # Nginx konfigürasyonu
│       └── .dockerignore       # Docker ignore rules
├── docker/                     # Docker konfigürasyonları
│   ├── docker-compose.yml      # Development ortamı
│   └── docker-compose.prod.yml # Production ortamı
├── scripts/                    # Yardımcı scriptler
│   ├── start-fim.sh            # Başlatma scripti
│   └── cleanup-fim.sh          # Temizlik scripti
├── config/
│   └── config.yaml            # Ana konfigürasyon
├── data/                      # Database dosyaları (host'ta saklanır)
├── logs/                      # Log dosyaları (host'ta saklanır)
├── fim                        # Ana kontrol scripti
└── README.md                  # Bu dosya
```

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM
- 1GB disk alanı

### Kurulum ve Başlatma

**🎯 Kolay Kullanım (Önerilen):**
```bash
# Development ortamı
./fim start

# Production ortamı  
./fim start --production

# Temiz başlatma
./fim start --clean

# Durumu görme
./fim status

# Sistem durdurma
./fim stop

# Temizlik
./fim clean
```

**🔧 Manuel Kullanım:**
1. **Development ortamı için FIM sistemini başlatın:**
   ```bash
   ./scripts/start-fim.sh
   ```

2. **Production ortamı için FIM sistemini başlatın:**
   ```bash
   ./scripts/start-fim.sh --production
   ```

3. **Web arayüzüne erişin:**
   - Dashboard: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### 🔧 Manuel Docker Komutları

**Development:**
```bash
# Database kurulumu
docker-compose -f docker/docker-compose.yml run --rm fim-db-init

# Servisleri başlat
docker-compose -f docker/docker-compose.yml up -d
```

**Production:**
```bash
# Database kurulumu
docker-compose -f docker/docker-compose.prod.yml run --rm fim-db-init

# Servisleri başlat
docker-compose -f docker/docker-compose.prod.yml up -d
```

## 🎛️ Kullanım

### Web Dashboard

Dashboard üzerinden:
- ✅ Sistem durumunu izleyin
- 📊 İzlenen dosya sayısını görün
- ⚡ Son değişiklikleri takip edin
- 🎯 Aktif profili kontrol edin

### REST API Endpoints

```bash
# Sistem durumu
curl http://localhost:8000/api/v1/status

# İzlenen dosyalar
curl http://localhost:8000/api/v1/files

# Son olaylar
curl http://localhost:8000/api/v1/events

# Health check
curl http://localhost:8000/health
```

## 🧹 Temizlik

```bash
# Development temizliği
./fim clean

# Production temizliği
./fim clean --production

# Manuel temizlik
./scripts/cleanup-fim.sh
```

```bash
docker-compose down
```

## 📋 Güvenlik Profilleri

### Light Profile
- Minimal performans etkisi
- Sadece kritik sistem dosyaları

### Balanced Profile (Önerilen)
- Dengeli güvenlik/performans
- Çoğu üretim ortamı için ideal

### Paranoid Profile
- Maksimum güvenlik
- Geniş dosya izleme

---

**🔒 FIM - Dosyalarınızı güvende tutun!**