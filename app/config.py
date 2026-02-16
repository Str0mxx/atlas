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

    # Service Mesh & Microservices
    servicemesh_enabled: bool = True
    default_timeout_ms: int = 30000
    circuit_failure_threshold: int = 5
    retry_max_attempts: int = 3
    load_balancer_algorithm: str = "round_robin"

    # Machine Learning Pipeline
    mlpipeline_enabled: bool = True
    model_cache_size: int = 1000
    experiment_retention_days: int = 90
    drift_check_interval: int = 3600
    auto_retrain: bool = False

    # Stream Processing & Real-Time Analytics
    streaming_enabled: bool = True
    default_window_size: int = 60
    checkpoint_interval: int = 300
    max_lateness: int = 10
    parallelism: int = 4

    # GraphQL & API Federation
    graphql_enabled: bool = True
    max_query_depth: int = 10
    max_complexity: int = 1000
    introspection_enabled: bool = True
    playground_enabled: bool = True

    # Container & Orchestration Management
    container_enabled: bool = True
    default_cpu_limit: str = "1.0"
    default_memory_limit: str = "512Mi"
    registry_url: str = "localhost:5000"
    auto_cleanup: bool = True

    # Infrastructure as Code
    iac_enabled: bool = True
    state_backend: str = "local"
    auto_approve: bool = False
    parallel_operations: int = 4
    iac_drift_check_interval: int = 3600

    # Backup & Disaster Recovery
    backup_enabled: bool = True
    default_retention_days: int = 30
    backup_compression_enabled: bool = True
    backup_encryption_enabled: bool = False
    rpo_hours: int = 1

    # Identity & Access Management
    iam_enabled: bool = True
    iam_session_timeout_minutes: int = 30
    iam_max_failed_attempts: int = 5
    iam_mfa_required: bool = False
    iam_password_min_length: int = 8

    # Rate Limiting & Throttling
    ratelimit_enabled: bool = True
    default_requests_per_minute: int = 60
    ratelimit_burst_multiplier: float = 1.5
    ratelimit_quota_reset_hour: int = 0
    ratelimit_violation_penalty_minutes: int = 15

    # Closed-Loop Execution Tracking
    closedloop_enabled: bool = True
    outcome_detection_timeout: int = 300
    min_confidence_for_learning: float = 0.5
    experiment_duration_hours: int = 24
    auto_apply_learnings: bool = False

    # Confidence-Based Autonomy
    confidence_enabled: bool = True
    auto_execute_threshold: float = 0.8
    ask_human_threshold: float = 0.3
    trust_decay_rate: float = 0.01
    calibration_interval_hours: int = 24

    # Self-Benchmarking Framework
    benchmark_enabled: bool = True
    evaluation_interval_hours: int = 6
    ab_test_min_samples: int = 30
    alert_on_degradation: bool = True
    report_frequency: str = "daily"

    # Cost-Per-Decision Engine
    costengine_enabled: bool = True
    default_budget_daily: float = 100.0
    pause_on_budget_exceed: bool = True
    cost_alert_threshold: float = 0.8
    require_approval_above: float = 50.0

    # Decision Explainability Layer
    explainability_enabled: bool = True
    default_explanation_depth: str = "standard"
    cache_explanations: bool = True
    include_counterfactuals: bool = True
    explanation_language: str = "en"

    # Capability Gap Detection & Auto-Acquisition
    capgap_enabled: bool = True
    auto_acquire: bool = False
    max_acquisition_time_hours: int = 24
    require_validation: bool = True
    notify_on_acquisition: bool = True

    # Goal Decomposition & Self-Tasking
    goaldecomp_enabled: bool = True
    max_decomposition_depth: int = 5
    auto_assign_tasks: bool = False
    replan_on_failure: bool = True
    validate_before_execute: bool = True

    # Cross-System Learning Transfer
    learntransfer_enabled: bool = True
    min_similarity_threshold: float = 0.3
    auto_transfer: bool = False
    require_transfer_validation: bool = True
    max_transfer_age_days: int = 90

    # Entity Memory
    entitymem_enabled: bool = True
    auto_merge_duplicates: bool = False
    retention_days: int = 365
    privacy_mode: str = "standard"
    max_interactions_stored: int = 10000

    # Regulatory
    regulatory_enabled: bool = True
    strict_mode: bool = False
    auto_update_rules: bool = False
    violation_alert: bool = True
    exception_approval_required: bool = True

    # Proactive Brain
    proactive_enabled: bool = True
    scan_interval_minutes: int = 5
    proactive_quiet_hours_start: int = 23
    proactive_quiet_hours_end: int = 7
    auto_action_threshold: float = 0.8

    # Voice Call Interface
    voicecall_enabled: bool = True
    default_voice: str = "atlas_default"
    max_call_duration: int = 1800
    recording_enabled: bool = True
    emergency_override: bool = True

    # Multi-Channel Command Center
    multichannel_enabled: bool = True
    multichannel_default_channel: str = "telegram"
    context_timeout_minutes: int = 30
    multichannel_auto_escalate: bool = True
    unified_inbox_enabled: bool = True

    # Runtime Capability Factory
    capfactory_enabled: bool = True
    sandbox_timeout_seconds: int = 60
    capfactory_auto_deploy: bool = False
    min_test_coverage: float = 80.0
    capfactory_rollback_on_failure: bool = True

    # --- Contextual Availability & Priority ---
    availability_learning: bool = True
    default_quiet_start: str = "22:00"
    default_quiet_end: str = "08:00"
    emergency_override: bool = True
    digest_enabled: bool = True

    # --- Deep Research Engine ---
    research_enabled: bool = True
    max_sources: int = 10
    min_credibility_score: float = 0.3
    continuous_tracking: bool = True
    report_format: str = "markdown"

    # --- Intelligent Web Navigator ---
    webnav_enabled: bool = True
    headless_mode: bool = True
    page_timeout: int = 30
    screenshot_on_error: bool = True
    webnav_max_retries: int = 3

    # --- Report & Insight Generator ---
    reportgen_enabled: bool = True
    default_format: str = "markdown"
    include_visuals: bool = True
    telegram_friendly: bool = True
    auto_export: bool = False

    # --- External Communication Agent ---
    extcomm_enabled: bool = True
    default_tone: str = "professional"
    auto_followup: bool = True
    followup_days: int = 3
    daily_send_limit: int = 100

    # --- Market & Trend Intelligence ---
    marketintel_enabled: bool = True
    scan_frequency_hours: int = 24
    competitor_tracking: bool = True
    patent_alerts: bool = True
    regulation_monitoring: bool = True

    # --- Task Memory & Command Learning ---
    taskmem_enabled: bool = True
    learning_rate: float = 0.1
    template_auto_create: bool = True
    prediction_enabled: bool = True
    personalization_level: str = "moderate"

    # --- Financial Intelligence & Tracker ---
    financial_enabled: bool = True
    currency: str = "TRY"
    tax_rate: float = 0.20
    alert_threshold: float = 1000.0
    auto_categorize: bool = True

    # --- Autonomous Negotiation Engine ---
    negotiation_enabled: bool = True
    auto_respond: bool = False
    min_acceptable_score: float = 60.0
    max_rounds: int = 10
    require_approval: bool = True

    # --- Project & Deadline Manager ---
    projectmgr_enabled: bool = True
    auto_escalate: bool = True
    deadline_warning_days: int = 7
    progress_report_frequency: str = "weekly"
    blocker_alert: bool = True

    # --- People & Relationship Manager ---
    peoplemgr_enabled: bool = True
    auto_log_interactions: bool = True
    relationship_decay_days: int = 90
    birthday_reminder_days: int = 7
    sentiment_tracking: bool = True

    # --- Legal & Contract Analyzer ---
    legal_enabled: bool = True
    risk_threshold: str = "medium"
    auto_extract_deadlines: bool = True
    compliance_check: bool = True
    comparison_highlight: bool = True

    # --- Content & Copy Generator ---
    contentgen_enabled: bool = True
    default_language: str = "en"
    seo_optimization: bool = True
    brand_voice_check: bool = True
    ab_test_auto: bool = True

    # --- Autonomous Purchasing Agent ---
    purchasing_enabled: bool = True
    auto_purchase_limit: float = 100.0
    reorder_auto: bool = True
    quality_check: bool = True
    multi_supplier: bool = True

    # --- Health & Uptime Guardian ---
    guardian_enabled: bool = True
    health_check_interval: int = 60
    auto_remediate: bool = True
    sla_target: float = 99.9
    incident_auto_escalate: bool = True

    # --- Feedback Loop Optimizer ---
    feedbackopt_enabled: bool = True
    auto_tune: bool = True
    experiment_auto_start: bool = True
    improvement_threshold: float = 0.1
    learning_integration: bool = True

    @property
    def is_production(self) -> bool:
        """Production ortaminda mi kontrol eder."""
        return self.app_env == "production"


# Tekil (singleton) settings nesnesi
settings = Settings()
