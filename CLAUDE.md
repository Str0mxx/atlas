# ATLAS - Otonom AI İş Ortağı Sistemi

## Proje Hakkında

ATLAS, Fatih için 7/24 çalışan otonom bir AI iş ortağı sistemidir. Sadece komut beklemez, proaktif olarak sorunları tespit eder, fırsatları yakalar ve kritik olmayan işleri otomatik halleder.

## Fatih'in İşleri

- **Mapa Health**: Medikal turizm (saç ekimi, diş, estetik)
- **FTRK Store**: Kozmetik üretimi (parfüm, krem, oda kokusu)
- **E-ticaret**: Trendyol satışları
- **Yazılım**: Web ve mobil geliştirme

## Teknoloji Stack

```
Backend:        Python 3.11+
Framework:      FastAPI
AI:             LangChain + Anthropic Claude API
Database:       PostgreSQL (ana) + Redis (cache/queue)
Vector DB:      Qdrant (semantik hafıza)
Task Queue:     Celery + Redis
Telegram:       python-telegram-bot
Voice:          Whisper (STT) + ElevenLabs (TTS)
Google Ads:     google-ads-python
SSH:            Paramiko + Fabric
```

## Proje Yapısı

```
atlas/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Ayarlar ve env variables
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── master_agent.py     # Ana koordinatör beyin
│   │   ├── decision_matrix.py  # Risk/aciliyet karar matrisi
│   │   ├── task_manager.py     # Görev yönetimi
│   │   └── memory/
│   │       ├── __init__.py
│   │       ├── short_term.py   # Redis - kısa süreli
│   │       ├── long_term.py    # PostgreSQL - uzun süreli
│   │       └── semantic.py     # Qdrant - vektör hafıza
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py       # Temel agent sınıfı
│   │   ├── research_agent.py   # Araştırma (web, tedarikçi)
│   │   ├── analysis_agent.py   # İş analizi, fizibilite
│   │   ├── communication_agent.py  # E-posta yönetimi
│   │   ├── security_agent.py   # Sunucu güvenliği
│   │   ├── coding_agent.py     # Kod yazma/düzeltme
│   │   ├── marketing_agent.py  # Google Ads, SEO
│   │   ├── creative_agent.py   # Ürün geliştirme, içerik
│   │   └── voice_agent.py      # Sesli asistan
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py     # Telegram entegrasyonu
│   │   ├── email_client.py     # Gmail/SMTP
│   │   ├── web_scraper.py      # Playwright scraping
│   │   ├── ssh_manager.py      # Sunucu bağlantısı
│   │   ├── google_ads.py       # Google Ads API
│   │   ├── image_generator.py  # AI görsel üretimi
│   │   └── file_handler.py     # PDF/Excel oluşturma
│   │
│   ├── monitors/
│   │   ├── __init__.py
│   │   ├── server_monitor.py   # Sunucu izleme
│   │   ├── ads_monitor.py      # Reklam performansı
│   │   ├── security_monitor.py # Güvenlik taraması
│   │   └── opportunity_monitor.py  # Fırsat taraması
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints
│   │   └── webhooks.py         # Telegram/diğer webhooks
│   │
│   └── models/
│       ├── __init__.py
│       ├── task.py             # Görev modeli
│       ├── agent_response.py   # Agent yanıt modeli
│       └── notification.py     # Bildirim modeli
│
├── tests/
│   └── ...
│
├── scripts/
│   ├── setup_db.py             # Veritabanı kurulumu
│   └── seed_data.py            # Başlangıç verileri
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Karar Matrisi

```
                    ACİLİYET
                 Düşük    Yüksek
              ┌─────────┬─────────┐
      Düşük   │ Kaydet  │ Bildir  │
RİSK          │ & İzle  │ & Öner  │
              ├─────────┼─────────┤
      Yüksek  │ Otomatik│ Hemen   │
              │ Düzelt  │ Müdahale│
              └─────────┴─────────┘
```

### Otonom Aksiyon Kuralları

**Otomatik (onay gerektirmez):**
- Log temizliği (30+ gün)
- Başarısız giriş IP engelleme
- Cache temizliği
- SSL otomatik yenileme
- Çöken servisleri restart
- Basit reklam metni düzeltmeleri

**Bildirim + opsiyonel onay:**
- Majör güncellemeler
- Firewall değişiklikleri
- Google Ads teklif değişiklikleri (<%20)
- Kod optimizasyonları

**Mutlaka onay gerektirir:**
- Sunucu restart
- Veritabanı değişiklikleri
- Kampanya durdurma/başlatma
- Büyük bütçe değişiklikleri (>%30)
- Production deployment
- Tedarikçilere mail gönderme

## Kod Standartları

- **Dil**: Türkçe yorumlar, İngilizce kod
- **Docstring**: Her fonksiyona Google style docstring
- **Type hints**: Tüm fonksiyonlarda zorunlu
- **Async**: I/O işlemleri için async/await kullan
- **Error handling**: Try-except ile hataları yakala, logla
- **Logging**: Her önemli işlem loglanmalı

## Örnek Kod Stili

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def analyze_supplier(
    supplier_url: str,
    criteria: dict[str, any]
) -> Optional[dict]:
    """
    Tedarikçi web sitesini analiz eder ve puanlar.
    
    Args:
        supplier_url: Tedarikçi web sitesi URL'i
        criteria: Değerlendirme kriterleri
        
    Returns:
        Tedarikçi analiz sonucu veya None (hata durumunda)
        
    Raises:
        ConnectionError: Site erişilemezse
    """
    try:
        # Analiz işlemleri...
        logger.info(f"Tedarikçi analiz edildi: {supplier_url}")
        return result
    except Exception as e:
        logger.error(f"Tedarikçi analiz hatası: {e}")
        return None
```

## Önemli Notlar

1. **Güvenlik**: API key'ler her zaman .env'de, asla kod içinde değil
2. **Hafıza**: Her önemli karar ve sonuç veritabanına kaydedilmeli
3. **Bildirim**: Kritik olaylar her zaman Telegram'a bildirilmeli
4. **Modülerlik**: Her agent bağımsız çalışabilmeli
5. **Test**: Kritik fonksiyonlar için test yazılmalı

## Geliştirme Sırası

1. ✅ Proje yapısı ve temel config
2. 🔲 Master Agent + Karar Matrisi
3. 🔲 Hafıza sistemi (Redis + PostgreSQL)
4. 🔲 Telegram entegrasyonu
5. 🔲 Güvenlik Agent'ı
6. 🔲 Araştırma Agent'ı
7. 🔲 Diğer agent'lar...
