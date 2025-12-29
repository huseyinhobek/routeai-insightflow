# 🚀 AWS Ubuntu Sunucuya Deployment Rehberi

Bu rehber, Aletheia projesini AWS Ubuntu sunucusuna kurmak için adım adım talimatlar içerir.

## 📋 Ön Gereksinimler

- AWS Ubuntu sunucusu (20.04 veya 22.04)
- SSH erişimi
- Docker ve Docker Compose kurulu
- Git kurulu
- En az 4GB RAM
- En az 20GB disk alanı

---

## 🔧 1. Sunucu Hazırlığı

### SSH ile bağlan
```bash
ssh -i your-key.pem ubuntu@your-server-ip
```

### Güncellemeleri yükle
```bash
sudo apt update && sudo apt upgrade -y
```

### Docker ve Docker Compose kurulumu
```bash
# Docker kurulumu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Docker Compose kurulumu
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout/login yap veya:
newgrp docker
```

### Git kurulumu
```bash
sudo apt install git -y
```

---

## 📥 2. Projeyi Clone Et

```bash
cd ~
git clone https://github.com/huseyinhobek/aletheia.git
cd aletheia/sav-insight-studio
```

---

## 🔐 3. Environment Variables Ayarla

`.env` dosyası oluştur:

```bash
nano .env
```

Aşağıdaki içeriği ekle (değerleri kendi değerlerinle değiştir):

```env
# Database
POSTGRES_USER=aletheia_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=aletheia_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Backend
SECRET_KEY=your_secret_key_here_min_32_chars
OPENAI_API_KEY=your_openai_api_key_here
APP_BASE_URL=https://your-domain.com

# Frontend
VITE_API_BASE_URL=http://localhost:8000

# Email (opsiyonel)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=Aletheia <noreply@your-domain.com>
```

**Önemli:** `SECRET_KEY` için güçlü bir key oluştur:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 💾 4. Lokal Veritabanını Export Et

### Lokal makinede (şu anki bilgisayarında):

```bash
# PostgreSQL dump al
docker exec sav-postgres pg_dump -U aletheia_user aletheia_db > aletheia_backup.sql

# Veya eğer lokal PostgreSQL kullanıyorsan:
pg_dump -U aletheia_user -h localhost aletheia_db > aletheia_backup.sql
```

### Upload edilmiş dosyaları hazırla

```bash
# Lokal makinede
cd ~/Downloads/native-data-transformation-dashboard/sav-insight-studio/backend/uploads
tar -czf uploads_backup.tar.gz *
```

---

## 📤 5. Dosyaları Sunucuya Transfer Et

### SCP ile transfer:

```bash
# Lokal makinede çalıştır
scp -i your-key.pem aletheia_backup.sql ubuntu@your-server-ip:~/
scp -i your-key.pem uploads_backup.tar.gz ubuntu@your-server-ip:~/
```

---

## 🗄️ 6. Veritabanını Import Et

### Sunucuda:

```bash
# Docker Compose ile servisleri başlat (sadece postgres için)
cd ~/aletheia/sav-insight-studio
docker-compose up -d postgres redis

# Postgres'in hazır olmasını bekle (10-15 saniye)
sleep 15

# Veritabanını import et
docker exec -i sav-postgres psql -U aletheia_user -d aletheia_db < ~/aletheia_backup.sql
```

---

## 📁 7. Upload Dosyalarını Yerleştir

```bash
# Uploads klasörünü oluştur
mkdir -p ~/aletheia/sav-insight-studio/backend/uploads

# Dosyaları extract et
cd ~/aletheia/sav-insight-studio/backend/uploads
tar -xzf ~/uploads_backup.tar.gz

# İzinleri ayarla
chmod -R 755 ~/aletheia/sav-insight-studio/backend/uploads
```

---

## 🐳 8. Docker Compose ile Servisleri Başlat

```bash
cd ~/aletheia/sav-insight-studio

# Tüm servisleri build et ve başlat
docker-compose build
docker-compose up -d

# Logları kontrol et
docker-compose logs -f
```

**Not:** İlk build uzun sürebilir (10-15 dakika).

---

## ✅ 9. Servisleri Kontrol Et

```bash
# Container'ların durumunu kontrol et
docker-compose ps

# Backend loglarını kontrol et
docker-compose logs backend

# Frontend loglarını kontrol et
docker-compose logs frontend
```

---

## 🌐 10. Nginx Reverse Proxy Kurulumu (Opsiyonel)

Eğer domain kullanacaksan:

```bash
sudo apt install nginx -y
```

Nginx config dosyası oluştur:

```bash
sudo nano /etc/nginx/sites-available/aletheia
```

İçeriği:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Aktif et:

```bash
sudo ln -s /etc/nginx/sites-available/aletheia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 11. SSL Sertifikası (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## 🔄 12. Otomatik Backup Script (Opsiyonel)

```bash
nano ~/backup_aletheia.sh
```

İçeriği:

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
docker exec sav-postgres pg_dump -U aletheia_user aletheia_db > $BACKUP_DIR/db_$DATE.sql

# Uploads backup
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C ~/aletheia/sav-insight-studio/backend/uploads .

# Eski backup'ları sil (7 günden eski)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Cron job ekle:

```bash
chmod +x ~/backup_aletheia.sh
crontab -e
```

Şunu ekle (her gün saat 02:00'de):

```
0 2 * * * /home/ubuntu/backup_aletheia.sh
```

---

## 🐛 Sorun Giderme

### Port çakışması
```bash
# Port kullanımını kontrol et
sudo netstat -tulpn | grep -E '3000|8000|5432|6379'

# Eğer port kullanılıyorsa, docker-compose.yml'de port numaralarını değiştir
```

### Veritabanı bağlantı hatası
```bash
# Postgres loglarını kontrol et
docker-compose logs postgres

# Container'ı yeniden başlat
docker-compose restart postgres
```

### Disk alanı
```bash
# Disk kullanımını kontrol et
df -h

# Eski Docker image'larını temizle
docker system prune -a
```

### Memory hatası
```bash
# Memory kullanımını kontrol et
free -h

# Swap ekle (gerekirse)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 13. Monitoring (Opsiyonel)

### Docker stats
```bash
docker stats
```

### Log monitoring
```bash
# Tüm logları takip et
docker-compose logs -f

# Sadece backend
docker-compose logs -f backend
```

---

## 🔄 14. Güncelleme İşlemi

Yeni değişiklikleri çekmek için:

```bash
cd ~/aletheia/sav-insight-studio
git pull origin main
docker-compose build
docker-compose up -d
```

---

## 📝 Notlar

- **Güvenlik:** `.env` dosyasını asla commit etme
- **Backup:** Düzenli backup al
- **Monitoring:** Logları düzenli kontrol et
- **Updates:** Güvenlik güncellemelerini takip et

---

## 🆘 Destek

Sorun yaşarsan:
1. Logları kontrol et: `docker-compose logs`
2. Container durumunu kontrol et: `docker-compose ps`
3. Disk ve memory kullanımını kontrol et

