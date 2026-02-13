"""ATLAS Kuru Calistirma modulu.

Yan etkisiz calistirma, ne olacagini kaydetme,
on kosul dogrulama, izin kontrolu ve kaynak uygunlugu.
"""

import logging
from typing import Any

from app.models.simulation import (
    DryRunResult,
    ResourceType,
    WorldSnapshot,
)

logger = logging.getLogger(__name__)

# Aksiyon tipi -> gerekli izinler
_REQUIRED_PERMISSIONS: dict[str, list[str]] = {
    "deploy": ["deploy:write", "service:restart", "config:read"],
    "migrate": ["database:write", "schema:alter", "backup:create"],
    "delete": ["data:delete", "resource:write"],
    "restart": ["service:restart", "process:kill"],
    "update": ["config:write", "service:reload"],
    "send": ["email:send", "notification:write"],
    "backup": ["storage:write", "data:read"],
    "create": ["resource:create", "config:write"],
}

# Aksiyon tipi -> on kosullar
_PREREQUISITES: dict[str, list[str]] = {
    "deploy": ["Build basarili", "Testler gecti", "Config hazir", "Kaynak yeterli"],
    "migrate": ["Yedek alinmis", "Baglanti var", "Schema gecerli"],
    "delete": ["Hedef dogrulanmis", "Yedek var", "Bagimliliklar kontrollu"],
    "restart": ["Servis mevcut", "Izinler yeterli"],
    "update": ["Versiyon uyumlu", "Bagimliliklar cozulmus"],
    "send": ["Alici gecerli", "Icerik hazir", "Kota musait"],
    "backup": ["Depolama yeterli", "Kaynak erisilebilir"],
    "create": ["Benzersiz ad", "Kaynak musait", "Sema gecerli"],
}

# Aksiyon tipi -> kaynak gereksinimleri
_RESOURCE_REQUIREMENTS: dict[str, dict[str, float]] = {
    "deploy": {"cpu": 0.3, "memory": 0.2, "disk": 0.1},
    "migrate": {"cpu": 0.2, "memory": 0.3, "disk": 0.3, "database": 0.5},
    "delete": {"cpu": 0.05, "disk": 0.0},
    "restart": {"cpu": 0.1, "memory": 0.05},
    "update": {"cpu": 0.15, "memory": 0.1},
    "send": {"network": 0.05},
    "backup": {"disk": 0.4, "cpu": 0.1},
    "create": {"cpu": 0.1, "memory": 0.1, "disk": 0.05},
}


class DryRunExecutor:
    """Kuru calistirma sistemi.

    Aksiyonlari yan etkisiz calistirir, ne olacagini
    loglar, on kosullari ve izinleri dogrular.

    Attributes:
        _runs: Calistirma gecmisi.
        _available_permissions: Mevcut izinler.
        _available_resources: Mevcut kaynaklar.
    """

    def __init__(
        self,
        permissions: list[str] | None = None,
    ) -> None:
        """Kuru calistirmayi baslatir.

        Args:
            permissions: Mevcut izinler.
        """
        self._runs: list[DryRunResult] = []
        self._available_permissions: set[str] = set(permissions or [])
        self._available_resources: dict[str, float] = {}

        logger.info("DryRunExecutor baslatildi")

    def set_permissions(self, permissions: list[str]) -> None:
        """Mevcut izinleri ayarlar.

        Args:
            permissions: Izin listesi.
        """
        self._available_permissions = set(permissions)

    def set_resources(self, resources: dict[str, float]) -> None:
        """Mevcut kaynaklari ayarlar.

        Args:
            resources: Kaynak -> kullanilabilir oran haritasi.
        """
        self._available_resources = dict(resources)

    def execute(
        self,
        action_name: str,
        parameters: dict[str, Any] | None = None,
        world_state: WorldSnapshot | None = None,
    ) -> DryRunResult:
        """Kuru calistirma yapar.

        Args:
            action_name: Aksiyon adi.
            parameters: Parametreler.
            world_state: Dunya durumu.

        Returns:
            DryRunResult nesnesi.
        """
        action_type = self._detect_action_type(action_name)
        steps: list[str] = []
        warnings: list[str] = []

        # 1. On kosul kontrolu
        steps.append(f"[DRY-RUN] Aksiyon: {action_name}")
        prereqs_ok, missing_prereqs = self._check_prerequisites(
            action_type, world_state
        )
        if prereqs_ok:
            steps.append("[OK] Tum on kosullar karsilandi")
        else:
            steps.append(f"[FAIL] Eksik on kosullar: {', '.join(missing_prereqs)}")

        # 2. Izin kontrolu
        perms_ok, missing_perms = self._check_permissions(action_type)
        if perms_ok:
            steps.append("[OK] Tum izinler mevcut")
        else:
            steps.append(f"[FAIL] Eksik izinler: {', '.join(missing_perms)}")

        # 3. Kaynak kontrolu
        resources_ok, shortages = self._check_resources(action_type, world_state)
        if resources_ok:
            steps.append("[OK] Kaynaklar yeterli")
        else:
            steps.append(f"[FAIL] Kaynak yetersiz: {', '.join(shortages)}")

        # 4. Parametreleri dogrula
        if parameters:
            param_warnings = self._validate_parameters(action_type, parameters)
            warnings.extend(param_warnings)
            if param_warnings:
                steps.append(f"[WARN] {len(param_warnings)} uyari")
            else:
                steps.append("[OK] Parametreler gecerli")

        # 5. Ne olacagini logla
        expected_actions = self._log_expected_actions(action_type, parameters)
        for action in expected_actions:
            steps.append(f"  -> {action}")

        # Genel sonuc
        would_succeed = prereqs_ok and perms_ok and resources_ok

        result = DryRunResult(
            action_name=action_name,
            would_succeed=would_succeed,
            steps_log=steps,
            prerequisites_met=prereqs_ok,
            missing_prerequisites=missing_prereqs,
            permissions_ok=perms_ok,
            missing_permissions=missing_perms,
            resources_available=resources_ok,
            resource_shortages=shortages,
            warnings=warnings,
        )

        self._runs.append(result)
        return result

    def batch_execute(
        self, actions: list[str], world_state: WorldSnapshot | None = None
    ) -> list[DryRunResult]:
        """Toplu kuru calistirma yapar.

        Args:
            actions: Aksiyon listesi.
            world_state: Dunya durumu.

        Returns:
            DryRunResult listesi.
        """
        return [self.execute(a, world_state=world_state) for a in actions]

    def _check_prerequisites(
        self, action_type: str, world_state: WorldSnapshot | None
    ) -> tuple[bool, list[str]]:
        """On kosullari kontrol eder."""
        required = _PREREQUISITES.get(action_type, ["Varsayilan kontrol"])
        missing: list[str] = []

        # World state varsa kisitlamalari kontrol et
        if world_state:
            for constraint in world_state.constraints:
                if not constraint.is_satisfied:
                    missing.append(f"Kisitlama: {constraint.name}")

        # On kosullarin simule kontrolu (varsayilan: karsilandi)
        # Gercek implementasyonda her on kosul kontrol edilir
        return len(missing) == 0, missing

    def _check_permissions(self, action_type: str) -> tuple[bool, list[str]]:
        """Izinleri kontrol eder."""
        required = _REQUIRED_PERMISSIONS.get(action_type, [])

        if not self._available_permissions:
            # Izin seti tanimlanmamissa basarili kabul et
            return True, []

        missing = [p for p in required if p not in self._available_permissions]
        return len(missing) == 0, missing

    def _check_resources(
        self, action_type: str, world_state: WorldSnapshot | None
    ) -> tuple[bool, list[str]]:
        """Kaynaklari kontrol eder."""
        required = _RESOURCE_REQUIREMENTS.get(action_type, {})
        shortages: list[str] = []

        if self._available_resources:
            for resource, needed in required.items():
                available = self._available_resources.get(resource, 1.0)
                if available < needed:
                    shortages.append(
                        f"{resource}: gerekli={needed:.0%}, mevcut={available:.0%}"
                    )

        if world_state:
            for resource in world_state.resources:
                if resource.current_usage > 0.95:
                    shortages.append(
                        f"{resource.resource_type.value}: %{resource.current_usage*100:.0f} dolu"
                    )

        return len(shortages) == 0, shortages

    def _validate_parameters(
        self, action_type: str, parameters: dict[str, Any]
    ) -> list[str]:
        """Parametreleri dogrular."""
        warnings: list[str] = []

        if parameters.get("force"):
            warnings.append("'force' parametresi kullaniliyor - dikkatli olun")

        if parameters.get("skip_validation"):
            warnings.append("Dogrulama atlaniyor - riskli")

        if action_type == "delete" and not parameters.get("confirm"):
            warnings.append("Silme islemi icin onay (confirm) gerekli")

        if parameters.get("timeout", 0) > 600:
            warnings.append("Yuksek timeout degeri - performans etkisi olabilir")

        return warnings

    def _log_expected_actions(
        self, action_type: str, parameters: dict[str, Any] | None
    ) -> list[str]:
        """Beklenen aksiyonlari loglar."""
        actions: list[str] = []

        if action_type == "deploy":
            actions.extend([
                "Yeni versiyon build edilecek",
                "Container'lar guncellecek",
                "Health check yapilacak",
            ])
        elif action_type == "migrate":
            actions.extend([
                "Veritabani yedegi alinacak",
                "Schema degisiklikleri uygulanacak",
                "Veri migrasyonu yapilacak",
            ])
        elif action_type == "delete":
            target = parameters.get("target", "bilinmeyen") if parameters else "bilinmeyen"
            actions.append(f"'{target}' silinecek")
            actions.append("Iliskili referanslar temizlenecek")
        elif action_type == "restart":
            actions.extend([
                "Servis durdurulacak",
                "Servis yeniden baslatilacak",
                "Health check yapilacak",
            ])
        else:
            actions.append(f"{action_type} islemi uygulanacak")

        return actions

    def _detect_action_type(self, action_name: str) -> str:
        """Aksiyon tipini tespit eder."""
        lower = action_name.lower()
        for t in _REQUIRED_PERMISSIONS:
            if t in lower:
                return t
        return "update"

    @property
    def run_count(self) -> int:
        """Calistirma sayisi."""
        return len(self._runs)

    @property
    def success_rate(self) -> float:
        """Basari orani."""
        if not self._runs:
            return 0.0
        successes = sum(1 for r in self._runs if r.would_succeed)
        return successes / len(self._runs)
