#!/bin/bash

# Aletheia Local Data Backup Script
# Bu script lokal veritabanını ve upload dosyalarını backup alır

echo "🔄 Aletheia Backup Başlatılıyor..."

# Tarih damgası
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR

# 1. PostgreSQL Database Backup
echo "📦 Veritabanı backup alınıyor..."
docker exec sav-postgres pg_dump -U aletheia_user aletheia_db > $BACKUP_DIR/aletheia_db_$DATE.sql

if [ $? -eq 0 ]; then
    echo "✅ Veritabanı backup tamamlandı: $BACKUP_DIR/aletheia_db_$DATE.sql"
    # SQL dosyasını sıkıştır
    gzip $BACKUP_DIR/aletheia_db_$DATE.sql
    echo "✅ Veritabanı backup sıkıştırıldı: $BACKUP_DIR/aletheia_db_$DATE.sql.gz"
else
    echo "❌ Veritabanı backup hatası!"
    exit 1
fi

# 2. Upload Dosyaları Backup
echo "📁 Upload dosyaları backup alınıyor..."
if [ -d "sav-insight-studio/backend/uploads" ]; then
    tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C sav-insight-studio/backend/uploads .
    if [ $? -eq 0 ]; then
        echo "✅ Upload dosyaları backup tamamlandı: $BACKUP_DIR/uploads_$DATE.tar.gz"
    else
        echo "❌ Upload dosyaları backup hatası!"
        exit 1
    fi
else
    echo "⚠️  Upload klasörü bulunamadı, atlanıyor..."
fi

# 3. Backup boyutlarını göster
echo ""
echo "📊 Backup Özeti:"
du -h $BACKUP_DIR/*$DATE*

echo ""
echo "✅ Backup tamamlandı!"
echo "📤 Sunucuya transfer için:"
echo "   scp -i your-key.pem $BACKUP_DIR/aletheia_db_$DATE.sql.gz ubuntu@your-server-ip:~/"
echo "   scp -i your-key.pem $BACKUP_DIR/uploads_$DATE.tar.gz ubuntu@your-server-ip:~/"

