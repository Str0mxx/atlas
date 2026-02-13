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
│   ├── celery_app.py           # Celery uygulama ve beat zamanlama
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
│   │   ├── learning/           # Pekiştirmeli öğrenme sistemi
│   │   │   ├── __init__.py
│   │   │   ├── q_learning.py   # Q-learning algoritması
│   │   │   ├── policy.py       # Politika yönetimi
│   │   │   ├── adaptation.py   # Adaptif öğrenme (drift tespiti)
│   │   │   ├── experience_buffer.py  # Deneyim tekrar tamponu
│   │   │   └── reward_system.py     # Ödül hesaplama
│   │   │
│   │   ├── resilience/         # Offline-first dayanıklılık sistemi
│   │   │   ├── __init__.py
│   │   │   ├── offline_mode.py        # Çevrimdışı yönetim (bağlantı izleme, sync kuyruğu)
│   │   │   ├── local_inference.py     # Yerel AI çıkarım (Ollama/kural tabanlı/cache)
│   │   │   ├── state_persistence.py   # Durum kalıcılığı (SQLite snapshot, kurtarma noktası)
│   │   │   ├── failover.py            # Circuit breaker + failover yönetimi
│   │   │   └── autonomous_fallback.py # Otonom fallback (acil durum protokolleri)
│   │   │
│   │   ├── planning/           # Stratejik planlama sistemi
│   │   │   ├── __init__.py
│   │   │   ├── goal_tree.py           # Hiyerarşik hedef ağacı (AND/OR decomposition)
│   │   │   ├── htplanner.py           # HTN planlama (task decomposition, metot seçimi)
│   │   │   ├── temporal.py            # Zamansal planlama (CPM, PERT, kritik yol)
│   │   │   ├── contingency.py         # Olasılık planlaması (Plan B/C/D, otomatik geçiş)
│   │   │   ├── resource.py            # Kaynak planlaması (tahsis, çatışma, optimizasyon)
│   │   │   └── strategy.py            # Strateji motoru (senaryo, KPI, adaptif strateji)
│   │   │
│   │   ├── collaboration/      # Multi-agent işbirliği sistemi
│   │   │   ├── __init__.py
│   │   │   ├── protocol.py            # Mesaj geçişi (öncelik kuyruğu, pub/sub, istek-yanıt)
│   │   │   ├── negotiation.py         # Contract Net Protocol (CFP, teklif, değerlendirme)
│   │   │   ├── coordination.py        # Koordinasyon (Blackboard, SyncBarrier, MutexLock)
│   │   │   ├── team.py               # Takım yönetimi (oluşturma, yetenek eşleme, iş yükü)
│   │   │   ├── consensus.py           # Konsensüs (çoğunluk, oybirliği, ağırlıklı, quorum)
│   │   │   └── workflow.py            # İş akışı orkestrasyon (seri, paralel, koşullu, merge)
│   │   │
│   │   ├── plugins/            # Plugin/Extension sistemi
│   │   │   ├── __init__.py
│   │   │   ├── hooks.py               # Hook/event sistemi (async pub/sub, hata izolasyonu)
│   │   │   ├── validator.py           # Plugin doğrulama (BaseAgent/BaseMonitor uyum kontrolü)
│   │   │   ├── registry.py            # Plugin kayıt defteri (durum takibi, CRUD, filtreleme)
│   │   │   ├── manifest.py            # Manifest yükleme (plugin.json parse, keşif)
│   │   │   ├── loader.py              # Plugin yükleyici (importlib, sınıf çözümleme)
│   │   │   └── manager.py             # Plugin yöneticisi (facade: yaşam döngüsü orkestrasyon)
│   │   │
│   │   ├── bootstrap/          # Self-bootstrapping ve auto-provisioning
│   │   │   ├── __init__.py
│   │   │   ├── environment_detector.py  # OS/yazılım/kaynak/ağ tespiti
│   │   │   ├── package_manager.py       # Birleşik paket yönetimi (pip/npm/apt/brew/choco/docker)
│   │   │   ├── service_provisioner.py   # Servis kontrolü (DB/SSL/port/health)
│   │   │   ├── dependency_resolver.py   # Bağımlılık grafı (topolojik sort, döngü tespiti)
│   │   │   ├── task_analyzer.py         # Görev analizi (araç tespiti, skill gap)
│   │   │   ├── auto_installer.py        # Orkestratör (plan/execute/rollback/verify)
│   │   │   ├── self_upgrade.py          # Sürüm kontrolü (migrasyon, hot-reload)
│   │   │   └── capability_builder.py    # Yetenek oluşturucu (agent/tool/plugin scaffold)
│   │   │
│   │   ├── selfcode/            # Self-coding agent sistemi
│   │   │   ├── __init__.py
│   │   │   ├── code_analyzer.py         # AST analiz (bağımlılık, karmaşıklık, güvenlik)
│   │   │   ├── code_generator.py        # Kod üretimi (şablon, LLM, stil zorlama)
│   │   │   ├── test_generator.py        # Test üretimi (birim test, edge case, mock)
│   │   │   ├── debugger.py              # Otomatik hata ayıklama (parse, analiz, fix)
│   │   │   ├── refactorer.py            # Yeniden düzenleme (dead code, simplify, extract)
│   │   │   ├── code_executor.py         # Güvenli çalıştırma (sandbox, kaynak limiti)
│   │   │   ├── agent_factory.py         # Agent fabrikası (şablon, scaffold, kayıt)
│   │   │   └── api_integrator.py        # API entegrasyonu (OpenAPI parse, istemci üretimi)
│   │   │
│   │   ├── memory_palace/       # Memory Palace insansı hafıza sistemi
│   │   │   ├── __init__.py
│   │   │   ├── episodic_memory.py       # Olay hafızası (ne, nerede, ne zaman, kim)
│   │   │   ├── procedural_memory.py     # İşlem hafızası (beceri, alışkanlık, otomatiklik)
│   │   │   ├── emotional_memory.py      # Duygusal hafıza (etiketleme, tercih, kaçınma)
│   │   │   ├── forgetting_curve.py      # Ebbinghaus unutma eğrisi (R=e^(-t/S))
│   │   │   ├── associative_network.py   # Çağrışım ağı (kavram, yayılan aktivasyon)
│   │   │   ├── working_memory.py        # Çalışma belleği (7±2 kapasite, gruplama)
│   │   │   ├── memory_consolidator.py   # Hafıza pekiştirme (uyku-benzeri konsolidasyon)
│   │   │   ├── autobiographical.py      # Özyaşam hafızası (bölümler, kimlik, anlatı)
│   │   │   └── memory_palace_manager.py # Orkestratör (kodlama, yönlendirme, arama)
│   │   │
│   │   ├── business/            # Autonomous Business Runner sistemi
│   │   │   ├── __init__.py
│   │   │   ├── opportunity_detector.py  # Fırsat tespiti (pazar tarama, trend, rakip, boşluk, lead scoring)
│   │   │   ├── strategy_generator.py    # Strateji üretici (hedef ayrıştırma, aksiyon planı, ROI)
│   │   │   ├── execution_engine.py      # Uygulama motoru (zamanlama, delegasyon, checkpoint, rollback)
│   │   │   ├── performance_analyzer.py  # Performans analizi (KPI, trend, anomali, rapor)
│   │   │   ├── optimizer.py             # İş optimizasyonu (A/B test, parametre, maliyet azaltma)
│   │   │   ├── feedback_loop.py         # Geri bildirim döngüsü (öğrenme, strateji düzeltme)
│   │   │   ├── autonomous_cycle.py      # 7/24 döngü (Detect→Plan→Execute→Measure→Optimize)
│   │   │   └── business_memory.py       # İş hafızası (başarı, başarısızlık, pazar, müşteri, rakip)
│   │   │
│   │   └── nlp_engine/          # Natural Language Programming Engine
│   │       ├── __init__.py
│   │       ├── intent_parser.py         # Niyet analizi (komut sınıflandırma, varlık çıkarma, belirsizlik)
│   │       ├── task_decomposer.py       # Görev ayrıştırma (alt görev, karmaşıklık, bağımlılık, doğrulama)
│   │       ├── requirement_extractor.py # Gereksinim çıkarma (fonksiyonel, NFR, kısıt, varsayım, MoSCoW)
│   │       ├── spec_generator.py        # Spesifikasyon üretici (API tasarımı, veri modeli, mimari, dokümantasyon)
│   │       ├── code_planner.py          # Kod planlayıcı (dosya yapısı, bağımlılık, arayüz, test stratejisi)
│   │       ├── execution_translator.py  # Komut çevirici (agent/DB/shell/API, güvenlik doğrulama)
│   │       ├── feedback_interpreter.py  # Geri bildirim (hata açıklama, başarı onay, ilerleme, öneri)
│   │       ├── conversation_manager.py  # Diyalog yönetimi (bağlam, referans çözümleme, konu takibi)
│   │       └── nlp_orchestrator.py      # Orkestratör (pipeline: Parse→Decompose→Spec→Plan→Translate→Feedback)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py            # Temel agent sınıfı (execute/analyze/report)
│   │   ├── coding_meta_agent.py     # Self-coding pipeline orkestratörü
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
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── monitor_tasks.py    # Celery periyodik monitor görevleri (4 task)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints (görev CRUD, agent, metrik, arama)
│   │   ├── webhooks.py         # Webhook'lar (Telegram, Google Ads, Gmail, Alert)
│   │   └── plugin_routes.py    # Plugin API (list, detail, enable, disable, reload)
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
│       ├── learning.py         # Öğrenme/RL modeli
│       ├── planning.py         # Stratejik planlama modeli
│       ├── collaboration.py    # Multi-agent işbirliği modeli
│       ├── plugin.py           # Plugin sistemi modeli
│       ├── bootstrap.py       # Self-bootstrapping modeli
│       ├── selfcode.py        # Self-coding agent modeli
│       ├── memory_palace.py   # Memory Palace hafıza modeli
│       ├── business.py        # Autonomous Business Runner modeli
│       └── nlp_engine.py      # NLP Engine modeli
│
│
│   ├── plugins/                # Plugin dizini (kullanıcı plugin'leri)
│   │   ├── __init__.py
│   │   └── _example/           # Örnek plugin (InventoryAgent)
│   │       ├── plugin.json
│   │       ├── agent.py
│   │       └── hooks.py
│
├── tests/                      # 102 test dosyası, 4176 test
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
├── docs/
│   └── DEPLOYMENT.md           # Production deployment rehberi
│
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline (lint, type-check, test, docker-build)
│       └── security.yml        # Güvenlik taraması (pip-audit, CodeQL)
│
├── docker-compose.yml          # 6 servis (postgres, redis, qdrant, app, celery)
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

- **Python modülleri**: ~168 kaynak + ~103 test dosyası
- **Toplam LOC**: ~92,500
- **Test sayısı**: 4,313+
- **Agent sayısı**: 11 (1 base + 9 uzman + 1 meta)
- **API endpoint**: 15 (10 core + 5 plugin)
- **Webhook endpoint**: 4

## Geliştirme Durumu (27/27 Tamamlandı ✅)

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
15. ✅ docker-compose.yml (PostgreSQL, Redis, Qdrant, ATLAS app, Celery worker/beat)
16. ✅ Celery worker modülleri (periyodik monitor görevleri, sonuç işleme, Telegram bildirimi)
17. ✅ CI/CD pipeline (GitHub Actions: lint, type-check, test, docker-build, güvenlik taraması)
18. ✅ Production deployment rehberi (docs/DEPLOYMENT.md)
19. ✅ Offline-first resilience sistemi (OfflineManager, LocalLLM, StatePersistence, CircuitBreaker, FailoverManager, AutonomousFallback)
20. ✅ Strategic Planning sistemi (GoalTree, HTNPlanner, TemporalPlanner, ContingencyPlanner, ResourcePlanner, StrategyEngine)
21. ✅ Multi-Agent Collaboration sistemi (MessageBus, NegotiationManager, Blackboard/SyncBarrier/MutexLock, TeamManager, ConsensusBuilder, WorkflowEngine)
22. ✅ Plugin/Extension sistemi (PluginManager, PluginLoader, PluginRegistry, PluginValidator, HookManager, manifest keşif, API endpoints)
23. ✅ Self-Bootstrapping sistemi (EnvironmentDetector, PackageManager, ServiceProvisioner, DependencyResolver, TaskAnalyzer, AutoInstaller, SelfUpgrade, CapabilityBuilder)
24. ✅ Self-Coding Agent sistemi (CodeAnalyzer, CodeGenerator, TestGenerator, AutoDebugger, CodeRefactorer, SafeExecutor, AgentFactory, APIIntegrator, CodingMetaAgent)
25. ✅ Memory Palace sistemi (EpisodicMemory, ProceduralMemory, EmotionalMemory, ForgettingCurve, AssociativeNetwork, WorkingMemory, MemoryConsolidator, AutobiographicalMemory, MemoryPalaceManager)
26. ✅ Autonomous Business Runner sistemi (OpportunityDetector, StrategyGenerator, ExecutionEngine, PerformanceAnalyzer, BusinessOptimizer, FeedbackLoop, AutonomousCycle, BusinessMemory)
27. ✅ NLP Engine sistemi (IntentParser, TaskDecomposer, RequirementExtractor, SpecGenerator, CodePlanner, ExecutionTranslator, FeedbackInterpreter, ConversationManager, NLPOrchestrator)
