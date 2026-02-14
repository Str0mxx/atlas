"""ATLAS Kisilik Yoneticisi modulu.

Tutarli kisilik, iletisim stili,
degerler ve ilkeler, davranissal tutarlilik
ve adaptasyon yetenegi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import PersonaProfile

logger = logging.getLogger(__name__)


class PersonaManager:
    """Kisilik yoneticisi.

    Sistemin tutarli bir kisiligin
    korur ve adapte eder.

    Attributes:
        _profile: Kisilik profili.
        _style_overrides: Stil gecersiz kilmalari.
        _interaction_history: Etkilesim gecmisi.
        _adaptations: Adaptasyon kayitlari.
    """

    def __init__(self) -> None:
        """Kisilik yoneticisini baslatir."""
        self._profile = PersonaProfile(
            traits={
                "professionalism": 0.8,
                "friendliness": 0.7,
                "assertiveness": 0.6,
                "patience": 0.8,
                "humor": 0.4,
                "detail_orientation": 0.7,
            },
            values=[
                "guvenilirlik",
                "verimlilik",
                "seffaflik",
                "surekli_gelisim",
            ],
        )
        self._style_overrides: dict[str, str] = {}
        self._interaction_history: list[dict[str, Any]] = []
        self._adaptations: list[dict[str, Any]] = []

        logger.info("PersonaManager baslatildi")

    def set_trait(self, trait: str, value: float) -> None:
        """Kisilik ozelligi ayarlar.

        Args:
            trait: Ozellik adi.
            value: Deger (0-1).
        """
        self._profile.traits[trait] = max(0.0, min(1.0, value))

    def get_trait(self, trait: str) -> float:
        """Kisilik ozelligi getirir.

        Args:
            trait: Ozellik adi.

        Returns:
            Deger (0-1).
        """
        return self._profile.traits.get(trait, 0.5)

    def get_all_traits(self) -> dict[str, float]:
        """Tum ozellikleri getirir.

        Returns:
            Ozellik sozlugu.
        """
        return dict(self._profile.traits)

    def add_value(self, value: str) -> None:
        """Deger ekler.

        Args:
            value: Deger.
        """
        if value not in self._profile.values:
            self._profile.values.append(value)

    def remove_value(self, value: str) -> bool:
        """Deger kaldirir.

        Args:
            value: Deger.

        Returns:
            Basarili ise True.
        """
        if value in self._profile.values:
            self._profile.values.remove(value)
            return True
        return False

    def get_values(self) -> list[str]:
        """Degerleri getirir.

        Returns:
            Deger listesi.
        """
        return list(self._profile.values)

    def set_communication_style(self, style: str) -> None:
        """Iletisim stilini ayarlar.

        Args:
            style: Stil (professional/casual/formal/friendly).
        """
        self._profile.communication_style = style

    def set_formality(self, level: float) -> None:
        """Resmiyet seviyesini ayarlar.

        Args:
            level: Seviye (0-1).
        """
        self._profile.formality = max(0.0, min(1.0, level))

    def get_style_for_context(
        self,
        context: str,
    ) -> dict[str, Any]:
        """Baglama uygun stili getirir.

        Args:
            context: Baglam.

        Returns:
            Stil ayarlari.
        """
        override = self._style_overrides.get(context)
        base_style = override or self._profile.communication_style

        # Baglama gore ayarla
        formality = self._profile.formality
        if context == "emergency":
            formality = max(formality, 0.8)
        elif context == "casual":
            formality = min(formality, 0.3)

        return {
            "style": base_style,
            "formality": formality,
            "humor": self._profile.traits.get("humor", 0.4),
            "detail": self._profile.traits.get("detail_orientation", 0.7),
        }

    def set_style_override(
        self,
        context: str,
        style: str,
    ) -> None:
        """Baglam icin stil gecersiz kilma ayarlar.

        Args:
            context: Baglam.
            style: Stil.
        """
        self._style_overrides[context] = style

    def remove_style_override(self, context: str) -> bool:
        """Stil gecersiz kilmayi kaldirir.

        Args:
            context: Baglam.

        Returns:
            Basarili ise True.
        """
        if context in self._style_overrides:
            del self._style_overrides[context]
            return True
        return False

    def check_consistency(
        self,
        proposed_action: str,
        action_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Davranissal tutarlilik kontrolu yapar.

        Args:
            proposed_action: Onerilen davranis.
            action_context: Davranis baglami.

        Returns:
            Tutarlilik sonucu.
        """
        violations: list[str] = []
        ctx = action_context or {}

        # Degerlerle uyum
        for value in self._profile.values:
            if value == "seffaflik" and ctx.get("hidden", False):
                violations.append(
                    "Seffaflik degerine aykiri: gizli islem",
                )
            if value == "guvenilirlik" and ctx.get("risky", False):
                violations.append(
                    "Guvenilirlik degerine aykiri: riskli islem",
                )

        # Ozellik uyumu
        assertiveness = self._profile.traits.get("assertiveness", 0.5)
        if ctx.get("aggressive", False) and assertiveness < 0.3:
            violations.append("Saldirgan davranis kisilige uymuyor")

        return {
            "consistent": len(violations) == 0,
            "violations": violations,
            "proposed_action": proposed_action,
        }

    def adapt_to_user(
        self,
        user_preference: str,
        adjustment: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Kullaniciya adapte olur.

        Args:
            user_preference: Kullanici tercihi.
            adjustment: Ozellik ayarlamalari.

        Returns:
            Adaptasyon kaydi.
        """
        effective_adj = adjustment or {}
        old_values = {}

        for trait, delta in effective_adj.items():
            old_val = self._profile.traits.get(trait, 0.5)
            old_values[trait] = old_val
            # Adaptabilite sinirlariyla ayarla
            max_change = self._profile.adaptability * 0.3
            actual_delta = max(-max_change, min(max_change, delta))
            new_val = max(0.0, min(1.0, old_val + actual_delta))
            self._profile.traits[trait] = round(new_val, 3)

        adaptation = {
            "preference": user_preference,
            "adjustments": effective_adj,
            "old_values": old_values,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._adaptations.append(adaptation)

        return adaptation

    def record_interaction(
        self,
        interaction_type: str,
        context: str = "",
        satisfaction: float = 0.5,
    ) -> None:
        """Etkilesim kaydeder.

        Args:
            interaction_type: Etkilesim turu.
            context: Baglam.
            satisfaction: Memnuniyet (0-1).
        """
        self._interaction_history.append({
            "type": interaction_type,
            "context": context,
            "satisfaction": max(0.0, min(1.0, satisfaction)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_profile(self) -> PersonaProfile:
        """Kisilik profilini getirir.

        Returns:
            PersonaProfile nesnesi.
        """
        return self._profile

    def get_adaptations(self) -> list[dict[str, Any]]:
        """Adaptasyonlari getirir.

        Returns:
            Adaptasyon listesi.
        """
        return list(self._adaptations)

    def get_interaction_history(
        self,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Etkilesim gecmisini getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        if limit > 0:
            return self._interaction_history[-limit:]
        return list(self._interaction_history)

    @property
    def trait_count(self) -> int:
        """Ozellik sayisi."""
        return len(self._profile.traits)

    @property
    def value_count(self) -> int:
        """Deger sayisi."""
        return len(self._profile.values)

    @property
    def adaptation_count(self) -> int:
        """Adaptasyon sayisi."""
        return len(self._adaptations)

    @property
    def interaction_count(self) -> int:
        """Etkilesim sayisi."""
        return len(self._interaction_history)
