# SAV Insight Studio

SPSS (.sav) dosyalarını analiz etmek, veri kalitesini ölçmek ve dijital ikiz uygunluğunu değerlendirmek için kapsamlı bir web uygulaması.

## 🚀 Özellikler

- 📊 **SAV Dosyası Analizi** - SPSS dosyalarını yükleyin ve otomatik analiz edin
- 📈 **Veri Kalitesi Raporu** - Tamlık, geçerlilik ve tutarlılık skorları
- 🚦 **Dijital İkiz Değerlendirmesi** - Yeşil/Sarı/Kırmızı ışık sistemi ile uygunluk raporu
- 🔍 **Değişken Keşfi** - Her değişken için detaylı frekans ve istatistik analizi
- 🤖 **AI Destekli Akıllı Filtreler** - Gemini AI ile segmentasyon önerileri
- 📥 **Kapsamlı Export** - Excel özet raporu, ham veri, JSON metadata
- 💾 **PostgreSQL Entegrasyonu** - Önceki analizleri saklama ve geri çağırma
- 🕐 **Analiz Geçmişi** - Tüm önceki analizlere tek tıkla erişim

## 📋 Gereksinimler

### Lokal Çalıştırma
- Node.js 18+ 
- Python 3.11+
- PostgreSQL 14+ (opsiyonel ama önerilir)
- npm veya yarn

### Docker ile Çalıştırma
- Docker
- Docker Compose

## 🛠️ Kurulum ve Çalıştırma

### 1. PostgreSQL Veritabanı Oluşturma

PostgreSQL'de yeni bir veritabanı oluşturun:

```sql
CREATE DATABASE sav_insight;
```

### 2. Backend Yapılandırması

Backend dizininde `.env` dosyası oluşturun:

```bash
cd sav-insight-studio/backend
```

`.env` dosyası içeriği:
```env
# PostgreSQL Bağlantısı
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/sav_insight

# Gemini API Key (Akıllı Filtreler için)
GEMINI_API_KEY=your_gemini_api_key_here

# Upload Dizini
UPLOAD_DIR=./uploads

# Debug Modu
DEBUG=true
```

### 3. Backend'i Başlat

**Windows:**
```powershell
cd sav-insight-studio\backend
pip install -r requirements.txt
python main.py
```

**Linux/Mac:**
```bash
cd sav-insight-studio/backend
pip install -r requirements.txt
python main.py
```

Backend `http://localhost:8000` adresinde çalışacak.

### 4. Frontend'i Başlat

Yeni bir terminal penceresinde:

```bash
cd sav-insight-studio
npm install
npm run dev
```

Frontend `http://localhost:3000` adresinde çalışacak.

### 5. Gemini API Key (Opsiyonel)

Akıllı filtre önerileri için Gemini API key gereklidir:

1. https://makersuite.google.com/app/apikey adresinden API key alın
2. **Backend için:** `backend/.env` dosyasına `GEMINI_API_KEY=...` ekleyin
3. **Frontend için:** Ana dizinde `.env.local` dosyası oluşturun:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## 🐳 Docker ile Çalıştırma

### Tüm Uygulamayı Başlat

```bash
cd sav-insight-studio
docker-compose up --build
```

Bu komut:
- Backend'i `http://localhost:8000` adresinde başlatır
- Frontend'i `http://localhost:3000` adresinde başlatır

### PostgreSQL ile Docker

`docker-compose.yml` dosyasına PostgreSQL ekleyebilirsiniz:

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: sav_insight
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

## ☁️ AWS Docker Entegrasyonu

### AWS'deki Mevcut Docker Container'ına Entegrasyon

AWS'de çalışan bir Docker container'ınız varsa ve bu projeyi entegre etmek istiyorsanız:

#### 1. Veritabanı Bağlantısı (RDS veya Mevcut PostgreSQL)

**Seçenek A: AWS RDS PostgreSQL**

AWS RDS PostgreSQL veritabanınıza bağlanmak için:

```env
# backend/.env dosyası
DATABASE_URL=postgresql://username:password@your-rds-endpoint.region.rds.amazonaws.com:5432/sav_insight
```

**Örnek:**
```env
DATABASE_URL=postgresql://admin:MySecurePassword123@sav-insight-db.abc123.us-east-1.rds.amazonaws.com:5432/sav_insight
```

**Seçenek B: Mevcut Docker Container'daki PostgreSQL**

Eğer AWS'de zaten çalışan bir PostgreSQL container'ınız varsa:

1. **Network Yapılandırması:**
   ```yaml
   # docker-compose.yml
   services:
     backend:
       networks:
         - your_existing_network
     db:
       image: postgres:15
       networks:
         - your_existing_network
   networks:
     your_existing_network:
       external: true
   ```

2. **Veritabanı URL:**
   ```env
   # Container adı veya service adı kullanın
   DATABASE_URL=postgresql://postgres:password@db_container_name:5432/sav_insight
   ```

**Seçenek C: EC2'de Çalışan PostgreSQL**

EC2 instance'ınızda PostgreSQL çalışıyorsa:

```env
# Public IP veya Private IP kullanın
DATABASE_URL=postgresql://postgres:password@ec2-xx-xx-xx-xx.compute-1.amazonaws.com:5432/sav_insight
# veya
DATABASE_URL=postgresql://postgres:password@10.0.1.5:5432/sav_insight
```

#### 2. Docker Compose ile AWS Entegrasyonu

**Tam Yapılandırma Örneği:**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: sav-insight-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - sav_uploads:/tmp/sav_uploads
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_URL=${DATABASE_URL}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - UPLOAD_DIR=/tmp/sav_uploads
      - DEBUG=false
    networks:
      - sav_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: sav-insight-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - sav_network
    restart: unless-stopped

volumes:
  sav_uploads:

networks:
  sav_network:
    driver: bridge
```

#### 3. Environment Variables (.env)

AWS'de çalıştırırken `backend/.env` dosyası:

```env
# AWS RDS veya Mevcut PostgreSQL Bağlantısı
DATABASE_URL=postgresql://username:password@your-database-endpoint:5432/sav_insight

# Gemini API Key (Opsiyonel)
GEMINI_API_KEY=your_gemini_api_key_here

# Upload Dizini (Container içinde)
UPLOAD_DIR=/tmp/sav_uploads

# Debug Modu (Production'da false)
DEBUG=false

# Max Upload Size (100MB)
MAX_UPLOAD_SIZE=104857600
```

#### 4. AWS Security Group Yapılandırması

PostgreSQL bağlantısı için Security Group kuralları:

**Inbound Rules:**
- Type: PostgreSQL
- Port: 5432
- Source: Backend container'ın bulunduğu Security Group veya VPC CIDR

**Örnek:**
```
Type: PostgreSQL (TCP)
Port: 5432
Source: sg-xxxxxxxxx (Backend Security Group)
```

#### 5. Veritabanı Oluşturma

AWS'deki PostgreSQL'de veritabanı oluşturun:

```sql
-- psql veya pgAdmin ile bağlanın
CREATE DATABASE sav_insight;

-- Kullanıcı oluşturma (opsiyonel)
CREATE USER sav_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE sav_insight TO sav_user;
```

#### 6. Container'ı Başlatma

```bash
# Environment variables ile
docker-compose up -d

# veya manuel olarak
docker run -d \
  --name sav-insight-backend \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/sav_insight" \
  -e GEMINI_API_KEY="your_key" \
  -v $(pwd)/uploads:/tmp/sav_uploads \
  sav-insight-backend
```

#### 7. Bağlantı Testi

```bash
# Health check
curl http://localhost:8000/health

# Config check
curl http://localhost:8000/api/config

# Database connection test
curl http://localhost:8000/api/datasets
```

#### 8. Troubleshooting AWS Bağlantı Sorunları

**Problem: "Connection refused" veya "Timeout"**

1. **Security Group Kontrolü:**
   ```bash
   # RDS Security Group'da backend'in IP'sine izin verildiğinden emin olun
   ```

2. **Network Connectivity:**
   ```bash
   # Container'dan RDS'e ping atın
   docker exec sav-insight-backend ping your-rds-endpoint
   ```

3. **DNS Resolution:**
   ```bash
   # RDS endpoint'in resolve edildiğinden emin olun
   docker exec sav-insight-backend nslookup your-rds-endpoint
   ```

4. **Connection Pool Ayarları:**
   ```python
   # database.py'de zaten optimize edilmiş:
   # - pool_pre_ping=True (bağlantı kontrolü)
   # - pool_recycle=3600 (1 saatte bir yenile)
   # - keepalive ayarları
   ```

**Problem: "Authentication failed"**

1. Kullanıcı adı ve şifrenin doğru olduğundan emin olun
2. RDS'de kullanıcının gerekli yetkilere sahip olduğundan emin olun
3. SSL bağlantısı gerekiyorsa:
   ```env
   DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/sav_insight?sslmode=require
   ```

#### 9. Production Best Practices

1. **Environment Variables:**
   - AWS Secrets Manager veya Parameter Store kullanın
   - `.env` dosyasını Git'e commit etmeyin

2. **Database Connection:**
   - Connection pooling aktif (zaten yapılandırılmış)
   - Keepalive ayarları aktif
   - Connection timeout ayarları

3. **Security:**
   - RDS'de SSL/TLS kullanın
   - Security Group'ları sıkı tutun
   - IAM authentication kullanabilirsiniz (RDS için)

4. **Monitoring:**
   - CloudWatch ile logları izleyin
   - Health check endpoint'ini kullanın
   - Database connection pool metriklerini izleyin

#### 10. Örnek AWS Deployment Script

```bash
#!/bin/bash
# deploy-aws.sh

# Environment variables
export DATABASE_URL="postgresql://admin:password@rds-endpoint:5432/sav_insight"
export GEMINI_API_KEY="your_key"

# Build and start
docker-compose -f docker-compose.yml up -d --build

# Wait for services
sleep 10

# Health check
curl http://localhost:8000/health
```

Bu script'i AWS CodeDeploy veya EC2 User Data ile kullanabilirsiniz.

## 📡 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/datasets/upload` | POST | SAV dosyası yükle |
| `/api/datasets` | GET | Tüm dataset'leri listele |
| `/api/datasets/{id}` | GET | Dataset metadata al |
| `/api/datasets/{id}` | DELETE | Dataset sil |
| `/api/datasets/{id}/quality` | GET | Kalite raporu al |
| `/api/datasets/{id}/variables/{var}` | GET | Değişken detayları |
| `/api/datasets/{id}/export/{type}` | GET | Export (summary, excel, json, report) |
| `/api/config` | GET | Yapılandırma durumu |
| `/health` | GET | Health check |

## 📊 Export Tipleri

- **summary** - Kapsamlı Excel özet raporu (veri kalitesi, değişken analizi, öneriler)
- **excel** - Ham veri + etiketli veri (iki sayfa)
- **json** - Tüm metadata JSON formatında
- **report** - Kalite raporu JSON formatında

## 🔧 Geliştirme

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
npm run dev
```

## ❗ Sorun Giderme

### Backend başlamıyor
- Python 3.11+ yüklü olduğundan emin olun
- PostgreSQL çalışıyor mu kontrol edin
- `DATABASE_URL` doğru mu kontrol edin
- Port 8000 kullanılabilir mi kontrol edin

### PostgreSQL bağlantı hatası
- PostgreSQL servisinin çalıştığından emin olun
- `sav_insight` veritabanının oluşturulduğundan emin olun
- Kullanıcı adı ve şifrenin doğru olduğundan emin olun

### Excel indirme çalışmıyor
- Backend'in çalıştığından emin olun
- Tarayıcı popup'larının engellenip engellenmediğini kontrol edin
- Console'da hata olup olmadığını kontrol edin

### Gemini API çalışmıyor
- API key'in doğru olduğundan emin olun
- API key'in aktif olduğundan emin olun
- `.env` ve `.env.local` dosyalarını kontrol edin

## 📁 Proje Yapısı

```
sav-insight-studio/
├── backend/
│   ├── main.py           # FastAPI ana uygulama
│   ├── config.py         # Yapılandırma
│   ├── database.py       # PostgreSQL bağlantısı
│   ├── models.py         # SQLAlchemy modelleri
│   ├── requirements.txt  # Python bağımlılıkları
│   └── services/
│       ├── quality_analyzer.py  # Veri kalitesi analizi
│       └── export_service.py    # Export işlemleri
├── pages/
│   ├── UploadPage.tsx         # Dosya yükleme
│   ├── DatasetOverview.tsx    # Genel bakış
│   ├── QualityReport.tsx      # Kalite raporu
│   ├── VariableExplorer.tsx   # Değişken keşfi
│   ├── SmartFilters.tsx       # AI filtreleri
│   ├── Exports.tsx            # Export sayfası
│   └── PreviousAnalyses.tsx   # Analiz geçmişi
├── services/
│   ├── apiService.ts     # API çağrıları
│   └── geminiService.ts  # Gemini AI entegrasyonu
├── components/
│   └── Layout.tsx        # Ana layout
├── App.tsx               # React router
├── types.ts              # TypeScript tipleri
├── constants.ts          # Sabitler
└── docker-compose.yml    # Docker yapılandırması
```

## 📜 Lisans

Bu proje özel bir projedir.
