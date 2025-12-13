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

Mevcut AWS Docker container'ınıza entegre etmek için:

1. `docker-compose.yml` dosyasını AWS'e kopyalayın
2. Environment variables ayarlayın:
   ```env
   DATABASE_URL=postgresql://user:pass@your-rds-endpoint:5432/sav_insight
   GEMINI_API_KEY=your_key
   ```
3. Port 8000'i expose edin
4. Volume mount: `sav_uploads:/tmp/sav_uploads`

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
