# ATLAS Production Deployment Guide

## Gereksinimler

| Bilesken | Minimum | Onerilen |
|----------|---------|----------|
| CPU | 2 core | 4 core |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB SSD | 50 GB SSD |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| Docker | 24.0+ | En guncel |
| Docker Compose | v2.20+ | En guncel |

## 1. Sunucu Hazirlik

```bash
# Sistem guncellemesi
sudo apt update && sudo apt upgrade -y

# Docker kurulumu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose (v2 dahili gelir)
docker compose version
```

## 2. Proje Kurulumu

```bash
# Repoyu klonla
git clone https://github.com/Str0mxx/atlas.git
cd atlas

# .env dosyasini olustur
cp .env.example .env
```

## 3. Ortam Degiskenleri (.env)

`.env` dosyasini duzenle — asagidaki degiskenleri **mutlaka** guncelle:

### Zorunlu

```bash
# Anthropic API (AI islemleri icin)
ANTHROPIC_API_KEY=sk-ant-gercek-anahtar

# Telegram Bot (bildirimler icin)
TELEGRAM_BOT_TOKEN=gercek-bot-token
TELEGRAM_ADMIN_CHAT_ID=gercek-chat-id

# Uygulama
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<rastgele-uzun-string>  # openssl rand -hex 32

# Webhook guvenligi
WEBHOOK_SECRET=<rastgele-string>       # openssl rand -hex 32
```

### Veritabani (docker-compose varsayilanlari ile calisir)

```bash
# Docker Compose icinde override edilir, degistirmeye gerek yok:
# DATABASE_URL, REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
# QDRANT_HOST, QDRANT_PORT
```

### Opsiyonel (kullanilan servislere gore)

```bash
# SSH sunucu yonetimi
SSH_DEFAULT_HOST=sunucu.ornegi.com
SSH_DEFAULT_USER=root

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...

# Sesli asistan
OPENAI_API_KEY=sk-...          # Whisper STT
ELEVENLABS_API_KEY=...         # ElevenLabs TTS
```

## 4. Production docker-compose Override (Opsiyonel)

Guclu sifre ve kaynak limitleri icin `docker-compose.prod.yml` olustur:

```yaml
# docker-compose.prod.yml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-guclu-sifre-buraya}
    deploy:
      resources:
        limits:
          memory: 1G

  redis:
    command: redis-server --requirepass ${REDIS_PASSWORD:-guclu-sifre}
    deploy:
      resources:
        limits:
          memory: 512M

  atlas-app:
    environment:
      DATABASE_URL: postgresql+asyncpg://atlas:${POSTGRES_PASSWORD:-guclu-sifre-buraya}@postgres:5432/atlas_db
    deploy:
      resources:
        limits:
          memory: 2G

  celery-worker:
    environment:
      DATABASE_URL: postgresql+asyncpg://atlas:${POSTGRES_PASSWORD:-guclu-sifre-buraya}@postgres:5432/atlas_db
    deploy:
      resources:
        limits:
          memory: 1G

  celery-beat:
    deploy:
      resources:
        limits:
          memory: 256M
```

Kullanim:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 5. Deployment

### Ilk Kurulum

```bash
# Image'lari build et
docker compose build

# Altyapi servislerini baslat ve saglik kontrolu bekle
docker compose up -d postgres redis qdrant

# Saglik kontrolu (30 saniye bekle)
sleep 30
docker compose ps

# Tum servisleri baslat (migration otomatik calisir)
docker compose up -d
```

### Guncelleme (Zero-downtime)

```bash
# Guncel kodu cek
git pull origin master

# Image'lari yeniden build et
docker compose build

# Servisleri tek tek guncelle
docker compose up -d --no-deps atlas-app
docker compose up -d --no-deps celery-worker
docker compose up -d --no-deps celery-beat
```

## 6. Dogrulama

```bash
# Tum servislerin durumu
docker compose ps

# Beklenen cikti: 6 servis, hepsi "Up" ve "healthy"

# Saglik kontrolu
curl http://localhost:8000/health
# {"status":"ok","service":"atlas"}

# Detayli durum
curl http://localhost:8000/status

# Loglari kontrol et
docker compose logs atlas-app --tail=50
docker compose logs celery-worker --tail=20
docker compose logs celery-beat --tail=20
```

## 7. Izleme ve Bakim

### Log Yonetimi

```bash
# Canli loglar
docker compose logs -f atlas-app

# Belirli bir servisin loglari
docker compose logs -f celery-worker

# Tum servislerin loglari
docker compose logs -f
```

### Veritabani Yedekleme

```bash
# Manuel yedek
docker compose exec postgres pg_dump -U atlas atlas_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Geri yukleme
docker compose exec -T postgres psql -U atlas atlas_db < backup_dosyasi.sql
```

### Otomatik Yedek (cron)

```bash
# crontab -e ile ekle:
0 3 * * * cd /path/to/atlas && docker compose exec -T postgres pg_dump -U atlas atlas_db | gzip > /backups/atlas_$(date +\%Y\%m\%d).sql.gz
```

### Disk Temizligi

```bash
# Kullanilmayan Docker kaynaklari
docker system prune -f

# Eski image'lari temizle
docker image prune -a --filter "until=168h"
```

## 8. Sorun Giderme

### Servis baslamiyor

```bash
# Loglari incele
docker compose logs <servis-adi> --tail=100

# Servisi yeniden baslat
docker compose restart <servis-adi>

# Tamamen yeniden olustur
docker compose up -d --force-recreate <servis-adi>
```

### Veritabani baglantisi basarisiz

```bash
# PostgreSQL saglik kontrolu
docker compose exec postgres pg_isready -U atlas -d atlas_db

# Baglanti testi
docker compose exec atlas-app python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
print('Baglanti basarili')
"
```

### Migration hatasi

```bash
# Mevcut migration durumu
docker compose exec atlas-app alembic current

# Migration gecmisi
docker compose exec atlas-app alembic history

# Migration'i tekrar calistir
docker compose exec atlas-app alembic upgrade head
```

### Redis baglantisi

```bash
# Redis ping
docker compose exec redis redis-cli ping

# Celery kuyruk durumu
docker compose exec celery-worker celery -A app.main:celery_app inspect active
```

## 9. Guvenlik Kontrol Listesi

- [ ] `APP_ENV=production` ve `APP_DEBUG=false` ayarli
- [ ] `APP_SECRET_KEY` ve `WEBHOOK_SECRET` rastgele uzun degerlerle degistirildi
- [ ] PostgreSQL sifresi varsayilandan (`password`) degistirildi
- [ ] Redis sifresi ayarlandi (opsiyonel, ic ag ise)
- [ ] `.env` dosyasi `.gitignore`'da (repodan haric)
- [ ] Sunucu firewall'u aktif (sadece 8000, 22 portlari acik)
- [ ] SSH key-based authentication etkin
- [ ] Docker portlari disariya gereksiz acilmamis (sadece atlas-app:8000)
- [ ] Duzenli yedekleme cron'u kurulmus
- [ ] GitHub Actions CI/CD pipeline'i aktif

## 10. Port Haritasi

| Servis | Ic Port | Dis Port | Aciklama |
|--------|---------|----------|----------|
| atlas-app | 8000 | 8000 | FastAPI uygulamasi |
| postgres | 5432 | 5432* | PostgreSQL |
| redis | 6379 | 6379* | Redis cache/broker |
| qdrant | 6333/6334 | 6333*/6334* | Vektor veritabani |

> *Production'da sadece `atlas-app:8000` disariya acilmali. Diger portlari `docker-compose.prod.yml` ile kapatabilirsiniz:
>
> ```yaml
> postgres:
>   ports: []  # Dis erisim kapatildi
> redis:
>   ports: []
> qdrant:
>   ports: []
> ```

## 11. Reverse Proxy (Nginx)

Production'da Nginx arkasinda calistirmayi oneririz:

```nginx
server {
    listen 80;
    server_name atlas.ornegi.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name atlas.ornegi.com;

    ssl_certificate /etc/letsencrypt/live/atlas.ornegi.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/atlas.ornegi.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

```bash
# Let's Encrypt SSL sertifikasi
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d atlas.ornegi.com
```
