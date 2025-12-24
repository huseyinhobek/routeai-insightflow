# Smart Filters Veritabanı Migration Rehberi

## Yapılan Değişiklikler
- `Dataset` modeline `smart_filters` JSON kolonu eklendi
- Backend'e yeni API endpoint'leri eklendi (GET ve PUT `/api/smart-filters/{dataset_id}`)
- Frontend localStorage yerine API kullanımına geçti

## Docker Deployment Adımları

### 1. Frontend Rebuild (GEREKLİ)
Frontend kod değişiklikleri var, rebuild gerekiyor:

```bash
cd /home/ubuntu/python-spss-parser/app/domain/sav-insight-studio/sav-insight-studio
docker-compose build frontend
docker-compose up -d frontend
```

### 2. Backend Restart (GEREKLİ)
Backend volume mount olduğu için rebuild gerekmez, sadece restart yeterli:

```bash
docker-compose restart backend
```

Veya eğer docker-compose kullanmıyorsanız:
```bash
docker restart sav-insight-backend
```

### 3. Veritabanı Migration (GEREKLİ)
Yeni `smart_filters` kolonunu eklemek için:

#### Seçenek A: SQLAlchemy ile Otomatik (Yeni Tablolar İçin)
Backend başlatıldığında `init_db()` çağrılırsa yeni tablolar için otomatik eklenir.

#### Seçenek B: Manuel SQL Migration (Mevcut Tablolar İçin)
Eğer `datasets` tablosu zaten varsa, manuel olarak kolonu ekleyin:

```sql
-- PostgreSQL için
ALTER TABLE datasets ADD COLUMN smart_filters JSON;

-- Veya NULL değerlerle başlatmak için
ALTER TABLE datasets ADD COLUMN smart_filters JSON DEFAULT '[]'::json;
```

#### Seçenek C: Python Script ile Migration
Backend container'ına girip migration script'i çalıştırın:

```bash
docker exec -it sav-insight-backend python -c "
from database import init_database, engine, DATABASE_AVAILABLE
from sqlalchemy import text
init_database()
if DATABASE_AVAILABLE:
    with engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE datasets ADD COLUMN smart_filters JSON'))
            conn.commit()
            print('Migration başarılı: smart_filters kolonu eklendi')
        except Exception as e:
            if 'already exists' in str(e) or 'duplicate' in str(e).lower():
                print('Kolon zaten mevcut')
            else:
                print(f'Hata: {e}')
"
```

### 4. Kontrol
Migration'ın başarılı olduğunu kontrol edin:

```bash
docker exec -it sav-insight-backend python -c "
from database import init_database, engine, DATABASE_AVAILABLE
from sqlalchemy import inspect
init_database()
if DATABASE_AVAILABLE:
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('datasets')]
    if 'smart_filters' in columns:
        print('✓ smart_filters kolonu mevcut')
    else:
        print('✗ smart_filters kolonu bulunamadı')
"
```

## Hızlı Komutlar (Tümünü Birden)

```bash
# Frontend rebuild
docker-compose build frontend && docker-compose up -d frontend

# Backend restart
docker-compose restart backend

# Database migration (PostgreSQL container'ına bağlanarak)
docker exec -it postgres-sav psql -U sav_user -d sav_insight -c "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS smart_filters JSON DEFAULT '[]'::json;"
```

## Notlar
- Frontend rebuild zorunludur (kod değişiklikleri var)
- Backend restart yeterlidir (volume mount + reload var)
- Database migration zorunludur (yeni kolon eklendi)
- Mevcut veriler korunur, sadece yeni kolon eklenir

