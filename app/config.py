"""ATLAS yapilandirma modulu.

Tum uygulama ayarlari Pydantic Settings uzerinden yonetilir.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Proje kok dizini
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Ana uygulama ayarlari."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Uygulama
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"
    app_secret_key: SecretStr = Field(default=SecretStr("change-this-secret-key"))

    # Anthropic
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))

    # Telegram
    telegram_bot_token: SecretStr = Field(default=SecretStr(""))
    telegram_admin_chat_id: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://atlas:password@localhost:5432/atlas_db"
    database_pool_size: int = 5

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10

    # Qdrant (Vektor Veritabani)
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: SecretStr | None = Field(default=None)
    qdrant_collection_prefix: str = "atlas"
    qdrant_embedding_model: str = "BAAI/bge-small-en-v1.5"
    qdrant_embedding_dimension: int = 384

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # SSH
    ssh_default_host: str = ""
    ssh_default_user: str = ""
    ssh_default_key_path: str = "~/.ssh/id_rsa"

    # Research
    tavily_api_key: SecretStr = Field(default=SecretStr(""))

    # Google Ads
    google_ads_developer_token: SecretStr = Field(default=SecretStr(""))
    google_ads_client_id: str = ""
    google_ads_client_secret: SecretStr = Field(default=SecretStr(""))
    google_ads_refresh_token: SecretStr = Field(default=SecretStr(""))
    google_ads_customer_id: str = ""

    # Gmail API
    gmail_client_id: str = ""
    gmail_client_secret: SecretStr = Field(default=SecretStr(""))
    gmail_refresh_token: SecretStr = Field(default=SecretStr(""))
    gmail_sender_email: str = ""
    gmail_sender_name: str = ""

    # Webhook
    webhook_secret: SecretStr = Field(default=SecretStr(""))

    # OpenAI (Whisper STT)
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    # ElevenLabs (TTS)
    elevenlabs_api_key: SecretStr = Field(default=SecretStr(""))

    # Master Agent
    master_agent_auto_mode: bool = False
    master_agent_max_retries: int = 3

    # TaskManager
    task_manager_max_concurrent: int = 5
    task_manager_retry_backoff_base: int = 5
    task_manager_retry_backoff_max: int = 300

    # Monitor Intervals (saniye)
    server_monitor_interval: int = 300
    security_monitor_interval: int = 3600
    ads_monitor_interval: int = 3600
    opportunity_monitor_interval: int = 86400

    # Plugin sistemi
    plugins_enabled: bool = True
    plugins_dir: str = "app/plugins"
    plugins_auto_load: bool = True

    # Bootstrap / Auto-Provisioning
    bootstrap_auto_install: bool = False
    bootstrap_allowed_installers: str = "pip,npm"
    bootstrap_sandbox_mode: bool = True
    bootstrap_require_approval: bool = True

    # Self-Coding
    selfcode_enabled: bool = False
    selfcode_max_generation_attempts: int = 3
    selfcode_sandbox_timeout: int = 30
    selfcode_auto_commit: bool = False
    selfcode_require_tests: bool = True

    # Memory Palace
    memory_palace_forgetting_rate: float = 0.1
    memory_palace_consolidation_interval: int = 3600
    memory_palace_emotional_weight: float = 0.3
    memory_palace_max_working_memory: int = 7

    # Business Runner
    business_cycle_interval: int = 60
    business_max_parallel_initiatives: int = 3
    business_risk_tolerance: float = 0.5
    business_human_approval_threshold: float = 0.8

    # NLP Engine
    nlp_clarification_threshold: float = 0.4
    nlp_max_context_turns: int = 50
    nlp_execution_confirmation: bool = True
    nlp_verbosity_level: str = "normal"

    # Predictive Intelligence
    predictive_forecast_horizon: int = 7
    predictive_confidence_threshold: float = 0.6
    predictive_model_update_frequency: str = "daily"
    predictive_ensemble_strategy: str = "weighted"

    # Knowledge Graph
    knowledge_max_nodes: int = 10000
    knowledge_inference_depth: int = 5
    knowledge_fusion_strategy: str = "trust_based"
    knowledge_persistence_path: str = ""

    # JIT Capability
    jit_enabled: bool = True
    jit_timeout_seconds: int = 120
    jit_sandbox_enabled: bool = True
    jit_auto_deploy: bool = False

    # Self-Evolution
    evolution_enabled: bool = True
    evolution_auto_approve_minor: bool = True
    evolution_require_approval_major: bool = True
    evolution_max_daily_auto_changes: int = 10
    evolution_cycle_hours: int = 24
    evolution_telegram_notifications: bool = True

    # Emotional Intelligence
    eq_enabled: bool = True
    eq_empathy_level: str = "medium"
    eq_humor_enabled: bool = True
    eq_formality_default: str = "neutral"
    eq_track_mood_history: bool = True

    # Simulation & Scenario Testing
    simulation_enabled: bool = True
    auto_simulate_risky: bool = True
    simulation_depth: int = 3
    require_simulation_approval: bool = False
    dry_run_default: bool = False

    # GitHub Project Integrator
    github_token: SecretStr = Field(default=SecretStr(""))
    github_auto_install_trusted: bool = False
    github_require_approval: bool = True
    github_min_stars: int = 10
    github_allowed_licenses: str = "mit,apache-2.0,bsd-2-clause,bsd-3-clause,isc,unlicense"
    github_sandbox_untrusted: bool = True

    # Hierarchical Agent Controller
    hierarchy_max_depth: int = 5
    hierarchy_default_autonomy: str = "medium"
    hierarchy_reporting_interval: int = 3600
    hierarchy_escalation_timeout: int = 300
    hierarchy_cluster_auto_balance: bool = True

    # Agent Spawner
    spawner_max_agents: int = 50
    spawner_pool_size: int = 5
    spawner_auto_scale: bool = True
    spawner_idle_timeout: int = 300
    spawner_spawn_timeout: int = 30

    # Swarm Intelligence
    swarm_enabled: bool = True
    swarm_min_size: int = 2
    swarm_max_size: int = 20
    swarm_voting_threshold: float = 0.5
    swarm_pheromone_decay_rate: float = 0.1

    # Mission Control
    mission_enabled: bool = True
    max_concurrent_missions: int = 5
    auto_abort_threshold: float = 0.3
    report_interval: int = 3600
    require_phase_approval: bool = False

    # Inter-System Bridge
    bridge_enabled: bool = True
    message_queue_size: int = 1000
    event_retention: int = 1000
    health_check_interval: int = 60
    auto_discovery: bool = True

    # Autonomous Goal Pursuit
    goal_pursuit_enabled: bool = True
    max_autonomous_goals: int = 5
    require_user_approval: bool = True
    proactive_scanning: bool = True
    value_threshold: float = 0.3

    # Unified Intelligence Core
    unified_enabled: bool = True
    consciousness_level: str = "medium"
    reasoning_depth: int = 10
    reflection_interval: int = 3600
    persona_consistency: float = 0.8

    # Context-Aware Assistant
    assistant_enabled: bool = True
    proactive_mode: bool = True
    learning_enabled: bool = True
    multi_channel: bool = True
    context_window: int = 50

    # Self-Diagnostic & Auto-Repair
    diagnostic_enabled: bool = True
    auto_repair: bool = False
    scan_interval: int = 300
    preventive_maintenance: bool = True
    alert_threshold: float = 0.5

    # External Integration Hub
    integration_enabled: bool = True
    default_timeout: int = 30
    max_retries: int = 3
    cache_enabled: bool = True
    rate_limit_default: int = 100

    # Resource Management
    resource_monitoring: bool = True
    cpu_threshold: float = 0.8
    memory_threshold: float = 0.8
    storage_threshold: float = 0.8
    cost_budget: float = 1000.0

    # Adaptive Learning Engine
    adaptive_enabled: bool = True
    learning_rate: float = 0.1
    exploration_rate: float = 0.2
    knowledge_retention: int = 90
    feedback_weight: float = 0.5

    # Security Hardening
    security_enabled: bool = True
    encryption_algorithm: str = "aes-256"
    session_timeout: int = 30
    max_login_attempts: int = 5
    audit_retention_days: int = 90

    # Time & Schedule Management
    scheduler_enabled: bool = True
    default_reminder_minutes: int = 15
    deadline_warning_hours: int = 24
    workday_start: str = "09:00"
    workday_end: str = "18:00"

    # Multi-Language & Localization
    localization_enabled: bool = True
    default_language: str = "en"
    supported_languages: str = "en,tr,de,fr,es,ar"
    auto_detect: bool = True
    translation_cache: bool = True

    # Notification & Alert System
    notification_enabled: bool = True
    default_channel: str = "log"
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    max_daily_notifications: int = 100

    # Data Pipeline & ETL
    pipeline_enabled: bool = True
    max_parallel_jobs: int = 5
    default_batch_size: int = 100
    retry_attempts: int = 3
    lineage_retention_days: int = 90

    # Workflow & Automation Engine
    workflow_enabled: bool = True
    max_concurrent_workflows: int = 10
    workflow_default_timeout: int = 3600
    max_loop_iterations: int = 1000
    execution_history_days: int = 30

    # Caching & Performance Optimization
    caching_enabled: bool = True
    default_ttl: int = 300
    max_cache_size: int = 10000
    compression_threshold: int = 1024
    profiling_enabled: bool = True

    # Version Control & Rollback
    versioning_enabled: bool = True
    max_snapshots: int = 100
    auto_snapshot_interval: int = 3600
    retention_days: int = 90
    compression_enabled: bool = True

    # API Management & Gateway
    api_gateway_enabled: bool = True
    default_rate_limit: int = 100
    request_timeout: int = 30
    enable_documentation: bool = True
    analytics_retention_days: int = 30

    # Logging & Audit Trail
    logging_enabled: bool = True
    log_level: str = "info"
    log_retention_days: int = 90
    audit_enabled: bool = True
    export_format: str = "json"

    # Testing & Quality Assurance
    qa_enabled: bool = True
    min_coverage: float = 80.0
    mutation_threshold: float = 0.8
    load_test_users: int = 100
    quality_gate_enabled: bool = True

    # Resilience / Offline
    resilience_enabled: bool = True
    offline_health_check_interval: int = 30
    offline_max_queue_size: int = 1000
    offline_sync_batch_size: int = 50
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    local_llm_provider: str = "rule_based"
    local_llm_ollama_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.2"
    state_persistence_db_path: str = "data/atlas_state.db"
    state_persistence_max_snapshots: int = 100

    # Event Sourcing & CQRS
    eventsourcing_enabled: bool = True
    snapshot_frequency: int = 100
    event_retention_days: int = 90
    projection_rebuild_batch: int = 100
    saga_timeout_minutes: int = 60

    # Distributed System Coordination
    distributed_enabled: bool = True
    cluster_size: int = 3
    replication_factor: int = 3
    consensus_timeout: int = 30
    heartbeat_interval: int = 5

    # Configuration Management
    config_mgmt_enabled: bool = True
    config_cache_ttl: int = 300
    secret_rotation_days: int = 90
    feature_flag_default: bool = False
    hot_reload_enabled: bool = True

    # Observability & Tracing
    observability_enabled: bool = True
    trace_sampling_rate: float = 1.0
    metrics_interval: int = 60
    alert_evaluation_interval: int = 30
    observability_retention_days: int = 30

    @property
    def is_production(self) -> bool:
        """Production ortaminda mi kontrol eder."""
        return self.app_env == "production"


# Tekil (singleton) settings nesnesi
settings = Settings()
