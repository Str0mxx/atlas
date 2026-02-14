"""ATLAS Agent Sablon Yoneticisi modulu.

Agent sablonlari, onceden tanimli tipler,
yetenek sablonlari, konfigürasyon ve kaynak profilleri.
"""

import logging
from typing import Any

from app.models.spawner import (
    AgentTemplate,
    TemplateCategory,
)

logger = logging.getLogger(__name__)

# Onceden tanimli agent sablonlari
_PREDEFINED_TEMPLATES: dict[str, dict[str, Any]] = {
    "worker": {
        "name": "Worker Agent",
        "category": TemplateCategory.WORKER,
        "capabilities": ["execute", "report"],
        "resource_profile": {"memory": 256, "cpu": 0.5},
        "behavior_preset": "obedient",
        "description": "Genel amacli is yapan agent.",
    },
    "researcher": {
        "name": "Research Agent",
        "category": TemplateCategory.SPECIALIST,
        "capabilities": ["search", "analyze", "summarize"],
        "resource_profile": {"memory": 512, "cpu": 1.0},
        "behavior_preset": "thorough",
        "description": "Arastirma ve analiz uzmani.",
    },
    "monitor": {
        "name": "Monitor Agent",
        "category": TemplateCategory.MONITOR,
        "capabilities": ["observe", "alert", "log"],
        "resource_profile": {"memory": 128, "cpu": 0.25},
        "behavior_preset": "vigilant",
        "description": "Sistem izleme agent'i.",
    },
    "coordinator": {
        "name": "Coordinator Agent",
        "category": TemplateCategory.COORDINATOR,
        "capabilities": ["delegate", "coordinate", "plan"],
        "resource_profile": {"memory": 512, "cpu": 1.0},
        "behavior_preset": "strategic",
        "description": "Koordinasyon ve yonetim agent'i.",
    },
    "security": {
        "name": "Security Agent",
        "category": TemplateCategory.SPECIALIST,
        "capabilities": ["scan", "detect", "block", "report"],
        "resource_profile": {"memory": 256, "cpu": 0.75},
        "behavior_preset": "cautious",
        "description": "Guvenlik uzmani agent.",
    },
    "coder": {
        "name": "Coding Agent",
        "category": TemplateCategory.SPECIALIST,
        "capabilities": ["code_analyze", "code_generate", "test", "debug"],
        "resource_profile": {"memory": 1024, "cpu": 2.0},
        "behavior_preset": "precise",
        "description": "Kod gelistirme uzmani.",
    },
}

# Davranis on-ayarlari
_BEHAVIOR_PRESETS: dict[str, dict[str, Any]] = {
    "default": {"autonomy": "medium", "reporting": "normal", "risk_tolerance": 0.5},
    "obedient": {"autonomy": "low", "reporting": "frequent", "risk_tolerance": 0.2},
    "thorough": {"autonomy": "medium", "reporting": "detailed", "risk_tolerance": 0.3},
    "vigilant": {"autonomy": "high", "reporting": "on_alert", "risk_tolerance": 0.1},
    "strategic": {"autonomy": "high", "reporting": "summary", "risk_tolerance": 0.6},
    "cautious": {"autonomy": "low", "reporting": "frequent", "risk_tolerance": 0.1},
    "precise": {"autonomy": "medium", "reporting": "normal", "risk_tolerance": 0.3},
    "autonomous": {"autonomy": "full", "reporting": "minimal", "risk_tolerance": 0.7},
}


class AgentTemplateManager:
    """Agent sablon yoneticisi.

    Onceden tanimli ve ozel agent sablonlari
    olusturur, yonetir ve uygular.

    Attributes:
        _templates: Kayitli sablonlar.
        _presets: Davranis on-ayarlari.
    """

    def __init__(self) -> None:
        """Sablon yoneticisini baslatir."""
        self._templates: dict[str, AgentTemplate] = {}
        self._presets: dict[str, dict[str, Any]] = dict(_BEHAVIOR_PRESETS)

        # Onceden tanimli sablonlari yukle
        for key, data in _PREDEFINED_TEMPLATES.items():
            tmpl = AgentTemplate(**data)
            tmpl.template_id = key
            self._templates[key] = tmpl

        logger.info(
            "AgentTemplateManager baslatildi (%d sablon)",
            len(self._templates),
        )

    def create_template(
        self,
        name: str,
        category: TemplateCategory = TemplateCategory.CUSTOM,
        capabilities: list[str] | None = None,
        config: dict[str, Any] | None = None,
        resource_profile: dict[str, float] | None = None,
        behavior_preset: str = "default",
        description: str = "",
    ) -> AgentTemplate:
        """Yeni sablon olusturur.

        Args:
            name: Sablon adi.
            category: Kategori.
            capabilities: Yetenekler.
            config: Konfigürasyon.
            resource_profile: Kaynak profili.
            behavior_preset: Davranis on-ayari.
            description: Aciklama.

        Returns:
            AgentTemplate nesnesi.
        """
        tmpl = AgentTemplate(
            name=name,
            category=category,
            capabilities=capabilities or [],
            config=config or {},
            resource_profile=resource_profile or {},
            behavior_preset=behavior_preset,
            description=description,
        )

        self._templates[tmpl.template_id] = tmpl
        logger.info("Sablon olusturuldu: %s (%s)", name, tmpl.template_id)
        return tmpl

    def get_template(self, template_id: str) -> AgentTemplate | None:
        """Sablonu getirir.

        Args:
            template_id: Sablon ID.

        Returns:
            AgentTemplate veya None.
        """
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: TemplateCategory | None = None,
    ) -> list[AgentTemplate]:
        """Sablonlari listeler.

        Args:
            category: Kategori filtresi.

        Returns:
            AgentTemplate listesi.
        """
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    def delete_template(self, template_id: str) -> bool:
        """Sablonu siler.

        Args:
            template_id: Sablon ID.

        Returns:
            Basarili ise True.
        """
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def merge_templates(
        self,
        template_ids: list[str],
        name: str = "",
    ) -> AgentTemplate | None:
        """Sablonlari birlestirir (hybrid).

        Args:
            template_ids: Birlestirilecek sablon ID'leri.
            name: Yeni sablon adi.

        Returns:
            Birlesmis AgentTemplate veya None.
        """
        templates = [
            self._templates[tid]
            for tid in template_ids
            if tid in self._templates
        ]
        if not templates:
            return None

        # Yetenekleri birlestir
        all_caps: list[str] = []
        for t in templates:
            for c in t.capabilities:
                if c not in all_caps:
                    all_caps.append(c)

        # Kaynak profillerini birlestir (maks deger)
        merged_resources: dict[str, float] = {}
        for t in templates:
            for k, v in t.resource_profile.items():
                if k not in merged_resources or v > merged_resources[k]:
                    merged_resources[k] = v

        # Config birlestir
        merged_config: dict[str, Any] = {}
        for t in templates:
            merged_config.update(t.config)

        return self.create_template(
            name=name or f"Hybrid-{'-'.join(template_ids[:3])}",
            category=TemplateCategory.CUSTOM,
            capabilities=all_caps,
            config=merged_config,
            resource_profile=merged_resources,
            description=f"Birlesmis: {', '.join(t.name for t in templates)}",
        )

    def get_behavior_preset(self, preset_name: str) -> dict[str, Any]:
        """Davranis on-ayarini getirir.

        Args:
            preset_name: On-ayar adi.

        Returns:
            On-ayar sozlugu.
        """
        return dict(self._presets.get(preset_name, self._presets["default"]))

    def register_preset(
        self, name: str, preset: dict[str, Any],
    ) -> None:
        """Yeni davranis on-ayari kaydeder.

        Args:
            name: On-ayar adi.
            preset: On-ayar verisi.
        """
        self._presets[name] = preset

    def get_resource_profile(self, template_id: str) -> dict[str, float]:
        """Kaynak profilini getirir.

        Args:
            template_id: Sablon ID.

        Returns:
            Kaynak profili sozlugu.
        """
        tmpl = self._templates.get(template_id)
        if tmpl:
            return dict(tmpl.resource_profile)
        return {}

    @property
    def template_count(self) -> int:
        """Toplam sablon sayisi."""
        return len(self._templates)

    @property
    def preset_count(self) -> int:
        """Toplam on-ayar sayisi."""
        return len(self._presets)
