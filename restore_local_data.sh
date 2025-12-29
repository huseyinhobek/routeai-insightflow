#!/bin/bash

# Aletheia Local Data Restore Script
# Bu script lokal veritabanından alınan backup'ı sunucuya restore eder

echo "🔄 Aletheia Restore Başlatılıyor..."

# Backup dosyasını bul
DB_BACKUP=$(ls -t ~/aletheia_db_*.sql.gz 2>/dev/null | head -1)
UPLOAD_BACKUP=$(ls -t ~/uploads_*.tar.gz 2>/dev/null | head -1)

if [ -z "$DB_BACKUP" ]; then
    echo "❌ Veritabanı backup dosyası bulunamadı!"
    echo "   ~/ dizininde aletheia_db_*.sql.gz dosyası olmalı"
    exit 1
fi

echo "📦 Bulunan backup: $DB_BACKUP"

# 1. Veritabanını restore et
echo "📥 Veritabanı restore ediliyor..."

# Backup'ı aç
gunzip -c $DB_BACKUP > /tmp/aletheia_restore.sql

# Mevcut veritabanını temizle ve restore et
docker exec -i sav-postgres psql -U insightflow -d insightflow << 'SQL'
-- Tüm tabloları DROP et
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO insightflow;
GRANT ALL ON SCHEMA public TO public;
SQL

# Backup'ı restore et (kullanıcı adlarını değiştir)
echo "📥 Veritabanı içeriği restore ediliyor..."
gunzip -c $DB_BACKUP | sed 's/aletheia_user/insightflow/g' | sed 's/aletheia_db/insightflow/g' | docker exec -i sav-postgres psql -U insightflow -d insightflow

if [ $? -eq 0 ]; then
    echo "✅ Veritabanı restore tamamlandı!"
else
    echo "❌ Veritabanı restore hatası!"
    exit 1
fi

# 2. Upload dosyalarını restore et (varsa)
if [ -n "$UPLOAD_BACKUP" ]; then
    echo "📁 Upload dosyaları restore ediliyor..."
    mkdir -p /opt/aletheia/sav-insight-studio/backend/uploads
    tar -xzf $UPLOAD_BACKUP -C /opt/aletheia/sav-insight-studio/backend/uploads
    if [ $? -eq 0 ]; then
        echo "✅ Upload dosyaları restore tamamlandı!"
        chmod -R 755 /opt/aletheia/sav-insight-studio/backend/uploads
    else
        echo "❌ Upload dosyaları restore hatası!"
    fi
else
    echo "⚠️  Upload backup dosyası bulunamadı, atlanıyor..."
fi

# 3. Veritabanı tablolarını kontrol et
echo ""
echo "📊 Veritabanı Tabloları:"
docker exec sav-postgres psql -U insightflow -d insightflow -c "\dt" | head -30

echo ""
echo "✅ Restore tamamlandı!"

