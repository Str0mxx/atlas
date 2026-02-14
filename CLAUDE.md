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
│   │   ├── nlp_engine/          # Natural Language Programming Engine
│   │   │   ├── __init__.py
│   │   │   ├── intent_parser.py         # Niyet analizi (komut sınıflandırma, varlık çıkarma, belirsizlik)
│   │   │   ├── task_decomposer.py       # Görev ayrıştırma (alt görev, karmaşıklık, bağımlılık, doğrulama)
│   │   │   ├── requirement_extractor.py # Gereksinim çıkarma (fonksiyonel, NFR, kısıt, varsayım, MoSCoW)
│   │   │   ├── spec_generator.py        # Spesifikasyon üretici (API tasarımı, veri modeli, mimari, dokümantasyon)
│   │   │   ├── code_planner.py          # Kod planlayıcı (dosya yapısı, bağımlılık, arayüz, test stratejisi)
│   │   │   ├── execution_translator.py  # Komut çevirici (agent/DB/shell/API, güvenlik doğrulama)
│   │   │   ├── feedback_interpreter.py  # Geri bildirim (hata açıklama, başarı onay, ilerleme, öneri)
│   │   │   ├── conversation_manager.py  # Diyalog yönetimi (bağlam, referans çözümleme, konu takibi)
│   │   │   └── nlp_orchestrator.py      # Orkestratör (pipeline: Parse→Decompose→Spec→Plan→Translate→Feedback)
│   │   │
│   │   ├── predictive/          # Predictive Intelligence sistemi
│   │   │   ├── __init__.py
│   │   │   ├── pattern_recognizer.py    # Örüntü tanıma (zaman serisi, davranışsal, anomali, dönesel, trend)
│   │   │   ├── trend_analyzer.py        # Trend analizi (hareketli ortalama, üstel düzleştirme, mevsimsellik)
│   │   │   ├── forecaster.py            # Tahmin motoru (regresyon, ensemble, güven aralığı, senaryo)
│   │   │   ├── risk_predictor.py        # Risk tahmini (başarısızlık olasılığı, erken uyarı, azaltma)
│   │   │   ├── demand_predictor.py      # Talep tahmini (satış, kaynak, kapasite, envanter optimizasyonu)
│   │   │   ├── behavior_predictor.py    # Davranış tahmini (satın alma, churn, LTV, sonraki aksiyon)
│   │   │   ├── event_predictor.py       # Olay tahmini (olasılık, zamanlama, zincirleme etki, önleme)
│   │   │   ├── model_manager.py         # Model yönetimi (eğitim, değerlendirme, seçim, versiyonlama)
│   │   │   └── prediction_engine.py     # Orkestratör (multi-model ensemble, güven puanlama, açıklama)
│   │   │
│   │   ├── knowledge/            # Knowledge Graph sistemi
│   │   │   ├── __init__.py
│   │   │   ├── entity_extractor.py      # Varlık çıkarma (NER, tiplendirme, bağlama, coreference)
│   │   │   ├── relation_extractor.py    # İlişki çıkarma (kalıp eşleme, güç puanlama, zamansal/nedensel)
│   │   │   ├── graph_builder.py         # Graf oluşturma (düğüm/kenar CRUD, birleştirme, tekrar tespiti)
│   │   │   ├── graph_store.py           # Depolama (indeksleme, versiyonlama, JSON persistence)
│   │   │   ├── query_engine.py          # Sorgulama (BFS yol bulma, alt graf, örüntü, doğal dil)
│   │   │   ├── inference_engine.py      # Çıkarım (geçişken kapanma, miras, ters ilişki, kural tabanlı)
│   │   │   ├── knowledge_fusion.py      # Bilgi birleştirme (çatışma çözümü, güven, kalite)
│   │   │   ├── ontology_manager.py      # Ontoloji (hiyerarşi, kısıtlama, doğrulama, şema evrimi)
│   │   │   └── knowledge_graph_manager.py # Orkestratör (pipeline, sorgu, analitik, import/export)
│   │   │
│   │   ├── jit/                  # Just-in-Time Capability sistemi
│   │   │   ├── __init__.py
│   │   │   ├── capability_checker.py    # Yetenek kontrolü (mevcut/benzer arama, efor tahmini, fizibilite)
│   │   │   ├── requirement_analyzer.py  # İhtiyaç analizi (niyet tespiti, API çıkarma, güvenlik, kısıtlar)
│   │   │   ├── api_discoverer.py        # API keşfi (katalog, endpoint arama, auth, rate limit, döküman)
│   │   │   ├── rapid_builder.py         # Hızlı inşa (client/agent/model/test üretimi, bağlantı)
│   │   │   ├── live_integrator.py       # Canlı entegrasyon (hot-load, kayıt, routing, rollback)
│   │   │   ├── credential_manager.py    # Kimlik yönetimi (API key, OAuth, rotasyon, güvenli depolama)
│   │   │   ├── sandbox_tester.py        # Sandbox test (izole çalıştırma, güvenlik tarama, performans)
│   │   │   ├── user_communicator.py     # Kullanıcı iletişimi (ilerleme, onay, hata/başarı bildirimi)
│   │   │   └── jit_orchestrator.py      # Orkestratör (pipeline, timeout, cache, öğrenme, rollback)
│   │   │
│   │   ├── evolution/            # Self-Evolution sistemi
│   │   │   ├── __init__.py
│   │   │   ├── performance_monitor.py   # Performans izleme (başarı oranı, yanıt süresi, hata kalıbı, trend)
│   │   │   ├── weakness_detector.py     # Zayıflık tespiti (başarısızlık, eksik yetenek, yavaş işlem, şikâyet)
│   │   │   ├── improvement_planner.py   # İyileştirme planlama (önceliklendirme, efor, risk, bağımlılık)
│   │   │   ├── code_evolver.py          # Kod evrimi (değişiklik üretimi, versiyon, diff, rollback)
│   │   │   ├── safety_guardian.py       # Güvenlik koruyucu (sınıflandırma, zararlı kod, kaynak limit)
│   │   │   ├── experiment_runner.py     # Deney yönetimi (sandbox, A/B test, benchmark, istatistik)
│   │   │   ├── approval_manager.py      # Onay yönetimi (kuyruk, Telegram, timeout, toplu onay, denetim)
│   │   │   ├── knowledge_learner.py     # Bilgi öğrenici (kalıp, best practice, agent paylaşımı)
│   │   │   └── evolution_controller.py  # Orkestratör (Observe→Analyze→Plan→Implement→Test→Deploy)
│   │   │
│   │   ├── emotional/            # Emotional Intelligence sistemi
│   │   │   ├── __init__.py
│   │   │   ├── sentiment_analyzer.py    # Duygu analizi (polarite, sınıflandırma, yoğunluk, alaycılık)
│   │   │   ├── empathy_engine.py        # Empati motoru (durum takibi, frustrasyon, kutlama, destek)
│   │   │   ├── mood_tracker.py          # Ruh hali takibi (kayıt, kalıp, tahmin, proaktif destek)
│   │   │   ├── communication_styler.py  # İletişim stili (ton adaptasyonu, resmiyet, mizah, aciliyet)
│   │   │   ├── conflict_resolver.py     # Çatışma çözümü (değerlendirme, de-eskalasyon, insan eskalasyonu)
│   │   │   ├── motivation_engine.py     # Motivasyon motoru (teşvik, kutlama, ilerleme, hedef)
│   │   │   ├── personality_adapter.py   # Kişilik adaptörü (tercih öğrenme, sabır, detay, mizah stili)
│   │   │   ├── emotional_memory.py      # Duygusal hafıza (ilişki kalitesi, önemli olay, tercih evrimi)
│   │   │   └── eq_orchestrator.py       # Orkestratör (pipeline: Analiz→Empati→Mood→Stil→Çatışma→Motivasyon)
│   │   │
│   │   ├── simulation/            # Simulation & Scenario Testing sistemi
│   │   │   ├── __init__.py
│   │   │   ├── world_modeler.py         # Dünya modelleyici (snapshot, varlık, kaynak, kısıtlama, varsayım)
│   │   │   ├── action_simulator.py      # Aksiyon simülatörü (sonuç, yan etki, kaynak, süre, zincir)
│   │   │   ├── scenario_generator.py    # Senaryo üretici (best/worst/likely/edge case, random)
│   │   │   ├── outcome_predictor.py     # Sonuç tahmincisi (başarı olasılığı, başarısızlık modları, zincirleme)
│   │   │   ├── risk_simulator.py        # Risk simülatörü (enjeksiyon, yayılım, kurtarma, stres testi)
│   │   │   ├── rollback_planner.py      # Geri alma planlayıcı (checkpoint, adımlar, veri kurtarma, doğrulama)
│   │   │   ├── what_if_engine.py        # Ne olur analizi (hassasiyet, eşik, devrilme noktası, optimizasyon)
│   │   │   ├── dry_run_executor.py      # Kuru çalıştırma (yan etkisiz, ön koşul, izin, kaynak kontrolü)
│   │   │   └── simulation_engine.py     # Orkestratör (pipeline, karşılaştırma, öneri, güven, rapor)
│   │   │
│   │   ├── github_integrator/     # GitHub Project Integrator sistemi
│   │   │   ├── __init__.py
│   │   │   ├── repo_discoverer.py       # Repo keşfi (arama, değerlendirme, filtreleme, sıralama, trending)
│   │   │   ├── repo_analyzer.py         # Repo analizi (tech stack, bağımlılık, kalite, API tespit)
│   │   │   ├── compatibility_checker.py # Uyumluluk kontrolü (Python, OS, lisans, bağımlılık çatışması)
│   │   │   ├── repo_cloner.py           # Repo klonlama (branch, sparse checkout, submodule, versiyon sabitleme)
│   │   │   ├── auto_installer.py        # Otomatik kurulum (yöntem tespit, onay, komut, rollback)
│   │   │   ├── agent_wrapper.py         # Agent sarmalama (agent/tool wrap, kayıt, kod üretimi)
│   │   │   ├── tool_adapter.py          # Araç adaptörü (CLI/library/API sarmalama, fonksiyon çıkarma)
│   │   │   ├── security_scanner.py      # Güvenlik tarayıcı (kalıp, malware, ağ/dosya erişim, sandbox)
│   │   │   └── github_orchestrator.py   # Orkestratör (Search→Analyze→Check→Clone→Install→Wrap→Register)
│   │   │
│   │   ├── hierarchy/             # Hierarchical Agent Controller sistemi
│   │       ├── __init__.py
│   │       ├── agent_hierarchy.py       # Agent hiyerarşisi (parent-child, yetki, delegasyon kuralları)
│   │       ├── cluster_manager.py       # Küme yönetimi (oluşturma, atama, sağlık, yük dengeleme)
│   │       ├── delegation_engine.py     # Yetki devri (görev ayrıştırma, yetenek eşleme, iş yükü dağıtımı)
│   │       ├── supervision_controller.py # Denetim kontrolü (izleme, ilerleme, müdahale, eskalasyon)
│   │       ├── reporting_system.py      # Raporlama (durum toplama, ilerleme, günlük/haftalık özet)
│   │       ├── command_chain.py         # Komut zinciri (direktif, yayın, hedefli, acil, geri bildirim)
│   │       ├── autonomy_controller.py   # Otonomi kontrolü (seviye, bağımsız hareket, dinamik ayarlama)
│   │       ├── conflict_arbiter.py      # Çatışma hakemi (kaynak, öncelik, kilitlenme, çözüm stratejisi)
│   │       └── hierarchy_orchestrator.py # Orkestratör (tam hiyerarşi, yeniden yapılandırma, optimizasyon)
│   │   │
│   │   ├── spawner/               # Agent Spawner sistemi
│   │   │   ├── __init__.py
│   │   │   ├── agent_template.py        # Agent şablonları (predefined tipler, preset, kaynak profili)
│   │   │   ├── spawn_engine.py          # Oluşturma motoru (template, scratch, clone, hybrid, batch)
│   │   │   ├── lifecycle_manager.py     # Yaşam döngüsü (durum geçişleri, sağlık, auto-restart)
│   │   │   ├── resource_allocator.py    # Kaynak tahsisi (memory, CPU, API kota, dinamik yeniden dağıtım)
│   │   │   ├── capability_injector.py   # Yetenek enjeksiyonu (add, remove, upgrade, hot-swap, bağımlılık)
│   │   │   ├── agent_pool.py            # Agent havuzu (fixed/elastic/on-demand, hızlı atama)
│   │   │   ├── termination_handler.py   # Sonlandırma (graceful, force, timeout, idle, durum koruma)
│   │   │   ├── agent_registry.py        # Agent kaydı (yetenek indeksi, etiket, arama, istatistik)
│   │   │   └── spawner_orchestrator.py  # Orkestratör (tam yaşam döngüsü, auto-scale, havuz yönetimi)
│   │   │
│   │   ├── swarm/                 # Swarm Intelligence sistemi
│   │   │   ├── __init__.py
│   │   │   ├── swarm_coordinator.py     # Sürü koordinatörü (oluşturma, katılım, lider seçimi, hedef dağıtımı)
│   │   │   ├── pheromone_system.py      # Feromon sistemi (stigmerji, iz bırakma, bozunma, çekim puanı)
│   │   │   ├── collective_memory.py     # Kolektif hafıza (güven puanlı bilgi, birleştirme, oylama)
│   │   │   ├── voting_system.py         # Oylama sistemi (çoğunluk, oybirliği, ağırlıklı, veto, quorum)
│   │   │   ├── task_auction.py          # Görev açık artırma (teklif, yetenek eşleme, adillik bonusu)
│   │   │   ├── emergent_behavior.py     # Ortaya çıkan davranış (yakınsama, örüntü, sinerji tespiti)
│   │   │   ├── load_balancer.py         # Yük dengeleyici (least-loaded, round-robin, iş çalma, Jain indeksi)
│   │   │   ├── fault_tolerance.py       # Hata toleransı (yedekleme, yeniden atama, iyileştirme, eskalasyon)
│   │   │   └── swarm_orchestrator.py    # Orkestratör (misyon, oylama, bilgi paylaşımı, optimizasyon)
│   │   │
│   │   ├── mission/               # Mission Control sistemi
│   │       ├── __init__.py
│   │       ├── mission_definer.py       # Görev tanımlayıcı (hedef, başarı kriteri, kısıtlama, bütçe, şablon)
│   │       ├── mission_planner.py       # Görev planlayıcı (faz, kilometre taşı, kritik yol, bağımlılık, risk)
│   │       ├── phase_controller.py      # Faz kontrolcü (geçiş, geçit inceleme, git/gitme, geri alma, paralel)
│   │       ├── resource_commander.py    # Kaynak komutanı (agent/araç atama, bütçe, çatışma, yeniden dağıtım)
│   │       ├── progress_tracker.py      # İlerleme takipçi (gerçek zamanlı, ETA, burndown, engelleyici)
│   │       ├── situation_room.py        # Durum odası (dashboard, uyarı, karar desteği, ne-olur analizi)
│   │       ├── contingency_manager.py   # Olasılık yöneticisi (Plan B, kurtarma, iptal, kademeli düşüşme)
│   │       ├── mission_reporter.py      # Görev raporlayıcı (durum, yönetici özeti, detaylı, görev-sonrası)
│   │       └── mission_control.py       # Orkestratör (tam yaşam döngüsü, çoklu görev, eskalasyon)
│   │   │
│   │   ├── bridge/                # Inter-System Bridge sistemi
│   │       ├── __init__.py
│   │       ├── system_registry.py     # Sistem kaydı (yetenek indeksleme, bağımlılık grafı, durum takibi)
│   │       ├── message_bus.py         # Mesaj yolu (pub/sub, doğrudan, broadcast, istek-yanıt, dead letter)
│   │       ├── event_router.py        # Olay yönlendirici (filtre, dönüştürücü, replay, retention)
│   │       ├── api_gateway.py         # API geçidi (route, rate limit, circuit breaker, middleware)
│   │       ├── data_transformer.py    # Veri dönüştürücü (format, şema eşleme, zenginleştirme, pipeline)
│   │       ├── workflow_connector.py  # İş akışı bağlayıcı (adım, telafi, saga pattern, rollback)
│   │       ├── health_aggregator.py   # Sağlık birleştirici (kontrol, rapor, uyarı, otomatik iyileştirme)
│   │       ├── config_sync.py         # Konfig senkronizasyonu (paylaşım, yayılım, snapshot, geri alma)
│   │       └── bridge_orchestrator.py # Orkestratör (kayıt, aktivasyon, mesaj, API, iş akışı, sorun giderme)
│   │   │
│   │   ├── goal_pursuit/          # Autonomous Goal Pursuit sistemi
│   │   │   ├── __init__.py
│   │   │   ├── goal_generator.py      # Hedef üretici (fırsat tespit, aday, önceliklendirme, fizibilite, hizalama)
│   │   │   ├── value_estimator.py     # Değer tahmincisi (fayda, maliyet, ROI, risk ayarlı, zaman değeri)
│   │   │   ├── goal_selector.py       # Hedef seçici (çoklu kriter, kaynak, çatışma, tercih, stratejik uyum)
│   │   │   ├── initiative_launcher.py # Girişim başlatıcı (görev dönüşümü, kaynak, zaman, metrik, izleme)
│   │   │   ├── progress_evaluator.py  # İlerleme değerlendirici (takip, kilometre taşı, rota, terk, başarı)
│   │   │   ├── learning_extractor.py  # Öğrenme çıkarıcı (başarı kalıbı, başarısızlık, strateji, best practice)
│   │   │   ├── proactive_scanner.py   # Proaktif tarayıcı (çevre izleme, fırsat, tehdit, trend, öneri)
│   │   │   ├── user_aligner.py        # Kullanıcı hizalayıcı (tercih, öneri, onay, sınır, geri bildirim)
│   │   │   └── goal_pursuit_engine.py # Orkestratör (otonom yaşam döngüsü, çoklu hedef, eskalasyon, 7/24)
│   │   │
│   │   ├── unified/              # Unified Intelligence Core sistemi
│   │   │   ├── __init__.py
│   │   │   ├── consciousness.py       # Bilinç katmanı (öz-farkındalık, durum, hedef, yetenek, kısıtlama)
│   │   │   ├── reasoning_engine.py    # Akıl yürütme (mantıksal, analojik, nedensel, abduktif, meta)
│   │   │   ├── attention_manager.py   # Dikkat yönetimi (odak, kapasite, arka plan, kesme, bağlam geçişi)
│   │   │   ├── world_model.py         # Dünya modeli (varlık, ilişki, durum tahmini, karşı-olgusal, simülasyon)
│   │   │   ├── decision_integrator.py # Karar entegrasyonu (BDI+Olasılık+RL+Duygusal+Kural+Konsensüs sentezi)
│   │   │   ├── action_coordinator.py  # Aksiyon koordinasyonu (oluşturma, yürütme, plan, kaynak, geri bildirim)
│   │   │   ├── reflection_module.py   # Yansıma modülü (öz-değerlendirme, performans, önyargı, iyileştirme)
│   │   │   ├── persona_manager.py     # Kişilik yöneticisi (özellik, değer, stil, tutarlılık, adaptasyon)
│   │   │   └── atlas_core.py          # Orkestratör (algıla→düşün→karar→eylem→yansı döngüsü, birleşik API)
│   │   │
│   │   ├── assistant/            # Context-Aware Assistant sistemi
│   │   │   ├── __init__.py
│   │   │   ├── context_builder.py     # Bağlam oluşturucu (profil, konuşma, görev, çevre, zaman farkındalığı)
│   │   │   ├── intent_predictor.py    # Niyet tahmincisi (sonraki istek, proaktif öneri, kalıp, davranış modeli)
│   │   │   ├── smart_responder.py     # Akıllı yanıtlayıcı (bağlam duyarlı, ton, detay, format, çoklu-modal)
│   │   │   ├── task_inferrer.py       # Görev çıkarıcı (örtülü tespit, belirsizlik, takip, tamamlama, sonraki adım)
│   │   │   ├── preference_learner.py  # Tercih öğrenici (stil, iletişim, araç, zaman, geri bildirim)
│   │   │   ├── proactive_helper.py    # Proaktif yardımcı (öneri, hatırlatma, deadline, fırsat, sorun önleme)
│   │   │   ├── conversation_memory.py # Konuşma hafızası (uzun süreli, konu takibi, referans, bağlam restorasyon)
│   │   │   ├── multi_channel_handler.py # Çoklu kanal (Telegram, email, ses, bağlam sync, kanal formatlama)
│   │   │   └── assistant_orchestrator.py # Orkestratör (tam deneyim, entegrasyon, sürekli öğrenme, kişilik)
│   │   │
│   │   ├── diagnostic/           # Self-Diagnostic & Auto-Repair sistemi
│   │   │   ├── __init__.py
│   │   │   ├── health_scanner.py      # Sağlık tarayıcı (bileşen kaydı, eşik, anomali, baseline)
│   │   │   ├── error_analyzer.py      # Hata analizci (kayıt, frekans, kök neden, korelasyon, etki)
│   │   │   ├── bottleneck_detector.py # Darboğaz tespit (profilleme, CPU, bellek, I/O, ağ)
│   │   │   ├── dependency_checker.py  # Bağımlılık kontrolü (eksik, çatışma, döngüsel, güvenlik açığı)
│   │   │   ├── auto_fixer.py          # Otomatik düzeltici (bilinen fix, güvenli/onaylı, cache/config/restart)
│   │   │   ├── recovery_manager.py    # Kurtarma yöneticisi (yedek, checkpoint, rollback, veri bütünlüğü)
│   │   │   ├── preventive_care.py     # Önleyici bakım (zamanlama, temizlik, optimizasyon, trend, tahmin)
│   │   │   ├── diagnostic_reporter.py # Teşhis raporlayıcı (sağlık raporu, uyarı, öneri, trend raporu)
│   │   │   └── diagnostic_orchestrator.py # Orkestratör (tam teşhis, hata raporlama, kurtarma, bakım)
│   │   │
│   │   └── integration/          # External Integration Hub sistemi
│   │       ├── __init__.py
│   │       ├── api_connector.py       # API bağlayıcı (REST, GraphQL, SOAP, WebSocket, gRPC)
│   │       ├── auth_handler.py        # Kimlik doğrulama (API key, OAuth2, JWT, Basic, token yenileme)
│   │       ├── webhook_manager.py     # Webhook yönetimi (gelen/giden, imza doğrulama, yönlendirme)
│   │       ├── data_sync.py           # Veri senkronizasyonu (full, delta, çift yönlü, çatışma çözümü)
│   │       ├── service_registry.py    # Servis kaydı (keşif, sağlık, failover, circuit breaker)
│   │       ├── rate_limiter.py        # Hız sınırlayıcı (kota, backoff, kuyruk, öncelik)
│   │       ├── response_cache.py      # Yanıt önbelleği (TTL, geçersiz kılma, ısındırma, hit rate)
│   │       ├── error_handler.py       # Hata yönetimi (sınıflandırma, yeniden deneme, yedek yanıt)
│   │       └── integration_hub.py     # Orkestratör (merkezi entegrasyon, servis orkestrasyon, izleme)
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
│       ├── nlp_engine.py      # NLP Engine modeli
│       ├── predictive.py      # Predictive Intelligence modeli
│       ├── knowledge.py       # Knowledge Graph modeli
│       ├── jit.py             # JIT Capability modeli
│       ├── evolution.py       # Self-Evolution modeli
│       ├── emotional.py       # Emotional Intelligence modeli
│       ├── simulation.py     # Simulation & Scenario Testing modeli
│       ├── github_integrator.py # GitHub Project Integrator modeli
│       ├── hierarchy.py    # Hierarchical Agent Controller modeli
│       ├── spawner.py     # Agent Spawner modeli
│       ├── swarm.py       # Swarm Intelligence modeli
│       ├── mission.py     # Mission Control modeli
│       ├── bridge.py      # Inter-System Bridge modeli
│       ├── goal_pursuit.py # Autonomous Goal Pursuit modeli
│       ├── unified.py     # Unified Intelligence Core modeli
│       ├── assistant.py   # Context-Aware Assistant modeli
│       ├── diagnostic.py  # Self-Diagnostic & Auto-Repair modeli
│       └── integration.py # External Integration Hub modeli
│
│
│   ├── plugins/                # Plugin dizini (kullanıcı plugin'leri)
│   │   ├── __init__.py
│   │   └── _example/           # Örnek plugin (InventoryAgent)
│   │       ├── plugin.json
│   │       ├── agent.py
│   │       └── hooks.py
│
├── tests/                      # 120 test dosyası, 6800 test
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

- **Python modülleri**: ~354 kaynak + ~120 test dosyası
- **Toplam LOC**: ~162,500
- **Test sayısı**: 6,800+
- **Agent sayısı**: 11 (1 base + 9 uzman + 1 meta)
- **API endpoint**: 15 (10 core + 5 plugin)
- **Webhook endpoint**: 4

## Geliştirme Durumu (44/44 Tamamlandı ✅)

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
28. ✅ Predictive Intelligence sistemi (PatternRecognizer, TrendAnalyzer, Forecaster, RiskPredictor, DemandPredictor, BehaviorPredictor, EventPredictor, ModelManager, PredictionEngine)
29. ✅ Knowledge Graph sistemi (EntityExtractor, RelationExtractor, GraphBuilder, GraphStore, QueryEngine, InferenceEngine, KnowledgeFusion, OntologyManager, KnowledgeGraphManager)
30. ✅ JIT Capability sistemi (CapabilityChecker, RequirementAnalyzer, APIDiscoverer, RapidBuilder, LiveIntegrator, CredentialManager, SandboxTester, UserCommunicator, JITOrchestrator)
31. ✅ Self-Evolution sistemi (PerformanceMonitor, WeaknessDetector, ImprovementPlanner, CodeEvolver, SafetyGuardian, ExperimentRunner, ApprovalManager, KnowledgeLearner, EvolutionController)
32. ✅ Emotional Intelligence sistemi (SentimentAnalyzer, EmpathyEngine, MoodTracker, CommunicationStyler, ConflictResolver, MotivationEngine, PersonalityAdapter, EmotionalMemoryManager, EQOrchestrator)
33. ✅ Simulation & Scenario Testing sistemi (WorldModeler, ActionSimulator, ScenarioGenerator, OutcomePredictor, RiskSimulator, RollbackPlanner, WhatIfEngine, DryRunExecutor, SimulationEngine)
34. ✅ GitHub Project Integrator sistemi (RepoDiscoverer, RepoAnalyzer, CompatibilityChecker, RepoCloner, AutoInstaller, AgentWrapper, ToolAdapter, SecurityScanner, GitHubOrchestrator)
35. ✅ Hierarchical Agent Controller sistemi (AgentHierarchy, ClusterManager, DelegationEngine, SupervisionController, ReportingSystem, CommandChain, AutonomyController, ConflictArbiter, HierarchyOrchestrator)
36. ✅ Agent Spawner sistemi (AgentTemplateManager, SpawnEngine, LifecycleManager, ResourceAllocator, CapabilityInjector, AgentPool, TerminationHandler, AgentRegistry, SpawnerOrchestrator)
37. ✅ Swarm Intelligence sistemi (SwarmCoordinator, PheromoneSystem, CollectiveMemory, VotingSystem, TaskAuction, EmergentBehavior, SwarmLoadBalancer, SwarmFaultTolerance, SwarmOrchestrator)
38. ✅ Mission Control sistemi (MissionDefiner, MissionPlanner, PhaseController, ResourceCommander, ProgressTracker, SituationRoom, ContingencyManager, MissionReporter, MissionControl)
39. ✅ Inter-System Bridge sistemi (SystemRegistry, MessageBus, EventRouter, APIGateway, DataTransformer, WorkflowConnector, HealthAggregator, ConfigSync, BridgeOrchestrator)
40. ✅ Autonomous Goal Pursuit sistemi (GoalGenerator, ValueEstimator, GoalSelector, InitiativeLauncher, ProgressEvaluator, LearningExtractor, ProactiveScanner, UserAligner, GoalPursuitEngine)
41. ✅ Unified Intelligence Core sistemi (Consciousness, ReasoningEngine, AttentionManager, WorldModel, DecisionIntegrator, ActionCoordinator, ReflectionModule, PersonaManager, ATLASCore)
42. ✅ Context-Aware Assistant sistemi (ContextBuilder, IntentPredictor, SmartResponder, TaskInferrer, PreferenceLearner, ProactiveHelper, ConversationMemory, MultiChannelHandler, AssistantOrchestrator)
43. ✅ Self-Diagnostic & Auto-Repair sistemi (HealthScanner, ErrorAnalyzer, BottleneckDetector, DependencyChecker, AutoFixer, RecoveryManager, PreventiveCare, DiagnosticReporter, DiagnosticOrchestrator)
44. ✅ External Integration Hub sistemi (APIConnector, AuthHandler, WebhookManager, DataSync, ExternalServiceRegistry, RateLimiter, ResponseCache, IntegrationErrorHandler, IntegrationHub)
