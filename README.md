# ATLAS - Autonomous AI Partner System

7/24 calisan otonom AI is ortagi sistemi. Sunucu izleme, kod yonetimi, guvenlik kontrolu ve otomatik mudahale yeteneklerine sahip.

## Mimari

```
atlas/
├── app/
│   ├── main.py              # FastAPI uygulamasi
│   ├── config.py             # Yapilandirma (Pydantic Settings)
│   ├── agents/               # Agent modulleri
│   │   └── base_agent.py     # Temel agent sinifi
│   ├── core/                 # Cekirdek moduller
│   │   ├── master_agent.py   # Ana koordinator agent
│   │   └── decision_matrix.py # Karar matrisi
│   ├── tools/                # Araclar
│   │   └── telegram_bot.py   # Telegram entegrasyonu
│   ├── monitors/             # Izleme modulleri
│   ├── models/               # Veri modelleri
│   ├── services/             # Servis katmani
│   └── utils/                # Yardimci moduller
├── tests/                    # Testler
├── logs/                     # Log dosyalari
├── pyproject.toml            # Proje bagimliliklari
└── .env.example              # Ortam degiskenleri sablonu
```

## Kurulum

### Gereksinimler

- Python 3.11+
- Redis
- PostgreSQL

### Adimlar

```bash
# 1. Repoyu klonla
git clone <repo-url>
cd atlas

# 2. Sanal ortam olustur
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# 3. Bagimliliklari yukle
pip install -e ".[dev]"

# 4. Ortam degiskenlerini ayarla
cp .env.example .env
# .env dosyasini duzenle: API anahtarlari, veritabani bilgileri vb.
```

## Calistirma

```bash
# Gelistirme modu
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Uretim modu
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoint'leri

| Endpoint    | Metod | Aciklama              |
| ----------- | ----- | --------------------- |
| `/health`   | GET   | Saglik kontrolu       |
| `/status`   | GET   | Detayli sistem durumu |
| `/tasks`    | POST  | Yeni gorev olustur    |

## Karar Matrisi

| Risk    | Aciliyet | Aksiyon          |
| ------- | -------- | ---------------- |
| Dusuk   | Dusuk    | Kaydet           |
| Dusuk   | Orta     | Kaydet           |
| Dusuk   | Yuksek   | Bildir           |
| Orta    | Dusuk    | Bildir           |
| Orta    | Orta     | Bildir           |
| Orta    | Yuksek   | Otomatik Duzelt  |
| Yuksek  | Dusuk    | Bildir           |
| Yuksek  | Orta     | Otomatik Duzelt  |
| Yuksek  | Yuksek   | Hemen Mudahale   |

## Testler

```bash
pytest
```

## Lisans

Ozel proje - Tum haklari saklidir.
