"""ATLAS otonom fallback modulu.

Tam bagimsiz mod: onceden programlanmis yanitlar,
sezgisel kararlar ve acil durum protokolleri.
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.core.resilience.local_inference import LocalLLM

logger = logging.getLogger(__name__)


class EmergencyLevel(str, Enum):
    """Acil durum seviyesi tanimlari."""

    NORMAL = "normal"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    CRITICAL = "critical"


class FallbackResponse(BaseModel):
    """Fallback yanit modeli.

    Attributes:
        action: Aksiyon tipi (log/notify/escalate/block).
        message: Yanit mesaji.
        confidence: Guven skoru (0-1).
        source: Yanit kaynagi (rule/heuristic/emergency/programmed).
    """

    action: str
    message: str
    confidence: float
    source: str


# Onceden programlanmis yanitlar
PROGRAMMED_RESPONSES: dict[str, FallbackResponse] = {
    "server_down": FallbackResponse(
        action="notify",
        message="Sunucu erisimez. Yonetici bilgilendirildi. "
                "Otomatik yeniden baslama deneniyor.",
        confidence=0.9,
        source="programmed",
    ),
    "database_failure": FallbackResponse(
        action="notify",
        message="Veritabani erisimez. Yerel cache kullaniliyor. "
                "Islemler kuyruga eklendi.",
        confidence=0.85,
        source="programmed",
    ),
    "api_unavailable": FallbackResponse(
        action="log",
        message="Dis API erisimez. Yerel kural motoru aktif. "
                "Baglanti gelince islemler tekrarlanacak.",
        confidence=0.8,
        source="programmed",
    ),
    "security_threat": FallbackResponse(
        action="notify",
        message="Guvenlik tehdidi tespit edildi. "
                "Muhafazakar mod aktif: yeni baglantilar engelleniyor.",
        confidence=0.95,
        source="programmed",
    ),
    "high_load": FallbackResponse(
        action="log",
        message="Yuksek yuk tespit edildi. Oncelik disi islemler ertelendi.",
        confidence=0.85,
        source="programmed",
    ),
}

# Sezgisel karar kurallari (risk, urgency) -> (action, confidence)
_HEURISTIC_RULES: dict[tuple[str, str], tuple[str, float]] = {
    ("low", "low"): ("log", 0.9),
    ("low", "medium"): ("log", 0.85),
    ("low", "high"): ("notify", 0.8),
    ("medium", "low"): ("log", 0.8),
    ("medium", "medium"): ("notify", 0.75),
    ("medium", "high"): ("notify", 0.7),
    ("high", "low"): ("notify", 0.75),
    ("high", "medium"): ("notify", 0.7),
    ("high", "high"): ("notify", 0.9),
    # CRITICAL: auto_fix/immediate yerine her zaman notify
}

# Acil durum protokolleri — seviyeye gore kisitlamalar
_EMERGENCY_PROTOCOLS: dict[EmergencyLevel, dict[str, Any]] = {
    EmergencyLevel.NORMAL: {
        "allowed_actions": ["log", "notify", "auto_fix", "immediate"],
        "description": "Normal mod — tum aksiyonlar izinli",
    },
    EmergencyLevel.DEGRADED: {
        "allowed_actions": ["log", "notify", "auto_fix"],
        "description": "Azaltilmis mod — immediate engellendi",
    },
    EmergencyLevel.EMERGENCY: {
        "allowed_actions": ["log", "notify"],
        "description": "Acil durum — sadece log ve notify izinli",
    },
    EmergencyLevel.CRITICAL: {
        "allowed_actions": ["log"],
        "description": "Kritik — sadece loglama izinli, tum aksiyonlar durduruldu",
    },
}


class AutonomousFallback:
    """Otonom fallback sinifi.

    Tam bagimsiz modda onceden programlanmis yanitlar,
    sezgisel kararlar ve acil durum protokolleri ile
    sistem calismasini surdurur.

    Attributes:
        local_llm: Yerel LLM (opsiyonel).
        state_persistence: Durum kaliciligi (opsiyonel).
    """

    def __init__(
        self,
        local_llm: LocalLLM | None = None,
        state_persistence: Any | None = None,
    ) -> None:
        """AutonomousFallback'i baslatir.

        Args:
            local_llm: Yerel LLM nesnesi.
            state_persistence: Durum kaliciligi nesnesi.
        """
        self.local_llm = local_llm
        self.state_persistence = state_persistence
        self._emergency_level = EmergencyLevel.NORMAL
        self._custom_protocols: dict[str, FallbackResponse] = {}

        logger.info("AutonomousFallback olusturuldu")

    @property
    def emergency_level(self) -> EmergencyLevel:
        """Guncel acil durum seviyesi.

        Returns:
            Acil durum seviyesi.
        """
        return self._emergency_level

    def get_programmed_response(
        self, event_type: str,
    ) -> FallbackResponse | None:
        """Onceden programlanmis yaniti dondurur.

        Oncelikle ozel protokollere, sonra varsayilan
        programlanmis yanitlara bakar.

        Args:
            event_type: Olay tipi.

        Returns:
            Programlanmis yanit veya None.
        """
        # Ozel protokoller oncelikli
        if event_type in self._custom_protocols:
            return self._custom_protocols[event_type]
        return PROGRAMMED_RESPONSES.get(event_type)

    def make_heuristic_decision(
        self,
        risk: str,
        urgency: str,
        context: dict[str, Any] | None = None,
    ) -> FallbackResponse:
        """Sezgisel karar verir.

        Risk ve aciliyet seviyesine gore onceden tanimli
        kurallara bakarak karar uretir.

        Args:
            risk: Risk seviyesi (low/medium/high).
            urgency: Aciliyet seviyesi (low/medium/high).
            context: Ek baglam bilgisi.

        Returns:
            Sezgisel karar yaniti.
        """
        action, confidence = _HEURISTIC_RULES.get(
            (risk, urgency), ("notify", 0.5),
        )

        # Acil durum seviyesine gore aksiyonu kisitla
        allowed = _EMERGENCY_PROTOCOLS[self._emergency_level]["allowed_actions"]
        if action not in allowed:
            # En yuksek izinli aksiyona dusur
            action = allowed[-1] if allowed else "log"
            confidence *= 0.8

        detail = ""
        if context and context.get("detail"):
            detail = f" Detay: {context['detail']}"

        return FallbackResponse(
            action=action,
            message=f"Sezgisel karar: risk={risk}, urgency={urgency}. "
                    f"Aksiyon: {action}.{detail}",
            confidence=confidence,
            source="heuristic",
        )

    async def activate_emergency_protocol(
        self, level: EmergencyLevel,
    ) -> None:
        """Acil durum protokolunu aktiflestirir.

        Args:
            level: Hedef acil durum seviyesi.
        """
        old_level = self._emergency_level
        self._emergency_level = level

        protocol_info = _EMERGENCY_PROTOCOLS[level]
        logger.warning(
            "Acil durum protokolu aktif: %s -> %s (%s)",
            old_level.value, level.value,
            protocol_info["description"],
        )

        # Durum kaliciligi varsa kaydet
        if self.state_persistence:
            try:
                await self.state_persistence.save_snapshot(
                    "emergency",
                    {
                        "level": level.value,
                        "old_level": old_level.value,
                        "allowed_actions": protocol_info["allowed_actions"],
                    },
                )
            except Exception as exc:
                logger.error("Acil durum snapshot kaydedilemedi: %s", exc)

    async def deactivate_emergency(self) -> None:
        """Acil durum protokolunu deaktiflestirir."""
        old_level = self._emergency_level
        self._emergency_level = EmergencyLevel.NORMAL
        logger.info(
            "Acil durum protokolu deaktif: %s -> NORMAL",
            old_level.value,
        )

    async def decide(
        self,
        event_type: str,
        risk: str,
        urgency: str,
        context: dict[str, Any] | None = None,
    ) -> FallbackResponse:
        """Tam bagimsiz karar verir.

        Oncelik sirasi:
        1. Onceden programlanmis yanitlar
        2. Yerel LLM (varsa)
        3. Sezgisel kararlar

        Args:
            event_type: Olay tipi.
            risk: Risk seviyesi (low/medium/high).
            urgency: Aciliyet seviyesi (low/medium/high).
            context: Ek baglam bilgisi.

        Returns:
            Fallback karar yaniti.
        """
        # 1. Programlanmis yanit
        programmed = self.get_programmed_response(event_type)
        if programmed is not None:
            # Acil durum kisitlamasi uygula
            allowed = _EMERGENCY_PROTOCOLS[self._emergency_level][
                "allowed_actions"
            ]
            if programmed.action in allowed:
                return programmed
            return FallbackResponse(
                action=allowed[-1] if allowed else "log",
                message=programmed.message,
                confidence=programmed.confidence * 0.8,
                source="programmed",
            )

        # 2. Yerel LLM
        if self.local_llm:
            try:
                llm_action = self.local_llm.get_fallback_action(
                    risk, urgency,
                )
                return FallbackResponse(
                    action=llm_action,
                    message=f"Yerel LLM karari: {event_type} "
                            f"(risk={risk}, urgency={urgency})",
                    confidence=0.6,
                    source="rule",
                )
            except Exception as exc:
                logger.warning("Yerel LLM basarisiz: %s", exc)

        # 3. Sezgisel karar
        return self.make_heuristic_decision(risk, urgency, context)

    def register_protocol(
        self,
        event_type: str,
        response: FallbackResponse,
    ) -> None:
        """Ozel protokol kaydeder.

        Args:
            event_type: Olay tipi.
            response: Programlanmis yanit.
        """
        self._custom_protocols[event_type] = response
        logger.info("Ozel protokol kaydedildi: %s", event_type)

    def get_registered_protocols(self) -> dict[str, FallbackResponse]:
        """Kayitli ozel protokolleri dondurur.

        Returns:
            Olay tipi -> yanit eslesmesi.
        """
        return dict(self._custom_protocols)
