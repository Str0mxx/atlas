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
│   │   ├── master_agent.py     # Ana koordinatör beyin (akıllı yönlendirme, eskalasyon, denetim izi)
│   │   ├── decision_matrix.py  # Risk/aciliyet karar matrisi (olasılıksal destek)
│   │   ├── task_manager.py     # Görev yönetimi (önceliklendirme, bağımlılık, tekrar deneme)
│   │   ├── database.py         # Async SQLAlchemy veritabanı bağlantısı
│   │   │
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── short_term.py   # Redis - kısa süreli hafıza
│   │   │   ├── long_term.py    # PostgreSQL - uzun süreli hafıza
│   │   │   └── semantic.py     # Qdrant - vektör/semantik hafıza
│   │   │
│   │   ├── autonomy/           # BDI Otonomi sistemi
│   │   │   ├── __init__.py
│   │   │   ├── bdi_agent.py    # Belief-Desire-Intention agent (Sense-Plan-Act)
│   │   │   ├── beliefs.py      # İnanç yönetimi (güven takibi)
│   │   │   ├── desires.py      # Hedef/istek yönetimi
│   │   │   ├── intentions.py   # Niyet seçimi ve planlama
│   │   │   ├── decision_theory.py  # Karar-teorik muhakeme
│   │   │   ├── probability.py  # Bayesci ağlar, olasılıksal muhakeme
│   │   │   ├── monte_carlo.py  # Monte Carlo simülasyonu
│   │   │   └── uncertainty.py  # Belirsizlik yönetimi
│   │   │
│   │   └── learning/           # Pekiştirmeli öğrenme sistemi
│   │       ├── __init__.py
│   │       ├── q_learning.py   # Q-learning algoritması
│   │       ├── policy.py       # Politika yönetimi
│   │       ├── adaptation.py   # Adaptif öğrenme (drift tespiti)
│   │       ├── experience_buffer.py  # Deneyim tekrar tamponu
│   │       └── reward_system.py     # Ödül hesaplama
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py            # Temel agent sınıfı (execute/analyze/report)
│   │   ├── server_monitor_agent.py  # Sunucu sağlık izleme
│   │   ├── security_agent.py        # Güvenlik taraması (auth log, fail2ban, SSL, port)
│   │   ├── research_agent.py        # Araştırma (web arama, tedarikçi, şirket)
│   │   ├── analysis_agent.py        # İş analizi (fizibilite, finansal, pazar, rakip)
│   │   ├── communication_agent.py   # E-posta yönetimi (Gmail API, şablonlar, toplu)
│   │   ├── coding_agent.py          # Kod analizi (güvenlik tarama, kalite, üretim)
│   │   ├── marketing_agent.py       # Google Ads (kampanya, anahtar kelime, bütçe)
│   │   ├── creative_agent.py        # İçerik üretimi (ürün fikri, reklam, marka)
│   │   └── voice_agent.py           # Sesli asistan (Whisper STT, ElevenLabs TTS)
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py     # Telegram (komutlar, callback, onay iş akışı)
│   │   ├── email_client.py     # Gmail API entegrasyonu
│   │   ├── web_scraper.py      # Playwright tabanlı web scraping
│   │   ├── ssh_manager.py      # Paramiko async SSH yönetimi
│   │   ├── google_ads.py       # Google Ads API entegrasyonu
│   │   ├── image_generator.py  # AI görsel üretimi
│   │   └── file_handler.py     # PDF/Excel oluşturma
│   │
│   ├── monitors/
│   │   ├── __init__.py
│   │   ├── base_monitor.py        # Temel monitor sınıfı (zamanlama, yaşam döngüsü)
│   │   ├── server_monitor.py      # Sunucu sağlık izleme
│   │   ├── security_monitor.py    # Güvenlik tehdit izleme
│   │   ├── ads_monitor.py         # Reklam performans izleme
│   │   └── opportunity_monitor.py # İş fırsatı taraması
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints (görev CRUD, agent, metrik, arama)
│   │   └── webhooks.py         # Webhook'lar (Telegram, Google Ads, Gmail, Alert)
│   │
│   └── models/
│       ├── __init__.py
│       ├── task.py             # Görev modeli
│       ├── agent_response.py   # Agent yanıt modeli
│       ├── agent_log.py        # Agent log modeli
│       ├── notification.py     # Bildirim modeli
│       ├── decision.py         # Karar kayıt (denetim izi, onay, eskalasyon)
│       ├── server.py           # Sunucu metrik modeli
│       ├── security.py         # Güvenlik tarama modeli
│       ├── research.py         # Araştırma sonuç modeli
│       ├── marketing.py        # Pazarlama/kampanya modeli
│       ├── coding.py           # Kod analiz modeli
│       ├── communication.py    # İletişim/e-posta modeli
│       ├── analysis.py         # İş analiz modeli
│       ├── creative.py         # Yaratıcı içerik modeli
│       ├── voice.py            # Ses işleme modeli
│       ├── autonomy.py         # BDI otonomi modeli
│       ├── probability.py      # Olasılıksal karar modeli
│       └── learning.py         # Öğrenme/RL modeli
│
├── tests/                      # 51 test dosyası, 2107 test
│   └── ...
│
├── scripts/
│   ├── setup_db.py             # Veritabanı kurulumu
│   └── seed_data.py            # Başlangıç verileri
│
├── alembic/                    # Veritabanı migrasyonları
│   ├── env.py
│   └── versions/
│
├── docker/
│   └── Dockerfile              # Multi-stage build
│
├── .env.example
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

## Proje İstatistikleri

- **Python modülleri**: ~80 kaynak + ~50 test dosyası
- **Toplam LOC**: ~52,500
- **Test sayısı**: 2,107
- **Agent sayısı**: 10 (1 base + 9 uzman)
- **API endpoint**: 10
- **Webhook endpoint**: 4

## Geliştirme Durumu

### Tamamlanan (✅)

1. ✅ Proje yapısı ve temel config
2. ✅ Master Agent + Karar Matrisi (akıllı agent seçimi, eskalasyon, denetim izi, onay iş akışı)
3. ✅ Hafıza sistemi (Redis + PostgreSQL + Qdrant)
4. ✅ Telegram entegrasyonu (komutlar, callback, bildirim, onay iş akışı)
5. ✅ Tüm Agent'lar (Security, Research, Analysis, Communication, Coding, Marketing, Creative, Voice, ServerMonitor)
6. ✅ Tüm Araçlar (SSH, Email, Web Scraper, Google Ads, Image Generator, File Handler)
7. ✅ Tüm Monitörler (Server, Security, Ads, Opportunity)
8. ✅ API Endpoints (10 endpoint: CRUD görevler, agent bilgisi, metrikler, semantik arama)
9. ✅ Webhook sistemi (Telegram, Google Ads, Gmail, Alert - HMAC-SHA256 doğrulama)
10. ✅ BDI Otonomi sistemi (Belief-Desire-Intention, Sense-Plan-Act döngüsü)
11. ✅ Olasılıksal karar sistemi (Bayesci ağlar, Monte Carlo simülasyonu, belirsizlik yönetimi)
12. ✅ Pekiştirmeli öğrenme (Q-learning, politika yönetimi, adaptif öğrenme, deneyim tamponu)
13. ✅ Veritabanı migrasyonları (Alembic) ve seed verileri
14. ✅ Docker (Dockerfile)

### Yapılacak (🔲)

15. 🔲 docker-compose.yml (PostgreSQL, Redis, Qdrant, ATLAS app orkestrasyonu)
16. 🔲 Celery worker modülleri (arkaplan görev işleme, periyodik taramalar)
17. 🔲 CI/CD pipeline (GitHub Actions)
18. 🔲 Production deployment rehberi
