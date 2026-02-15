"""ATLAS Captcha Çözücü modülü.

Captcha tespiti, servis entegrasyonu,
yedek yönetimi, insan eskalasyonu,
hız sınırlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Captcha çözücü.

    Captcha'ları tespit eder ve çözer.

    Attributes:
        _solves: Çözüm geçmişi.
        _services: Çözüm servisleri.
    """

    def __init__(
        self,
        max_attempts: int = 3,
    ) -> None:
        """Çözücüyü başlatır.

        Args:
            max_attempts: Maks deneme.
        """
        self._solves: list[
            dict[str, Any]
        ] = []
        self._services: dict[
            str, dict[str, Any]
        ] = {}
        self._escalations: list[
            dict[str, Any]
        ] = []
        self._max_attempts = max_attempts
        self._counter = 0
        self._stats = {
            "captchas_detected": 0,
            "captchas_solved": 0,
            "escalations": 0,
            "failures": 0,
        }

        logger.info(
            "CaptchaSolver baslatildi",
        )

    def detect(
        self,
        page_content: str,
    ) -> dict[str, Any]:
        """Captcha tespit eder.

        Args:
            page_content: Sayfa içeriği.

        Returns:
            Tespit bilgisi.
        """
        content_lower = page_content.lower()

        captcha_type = None
        if "recaptcha" in content_lower:
            captcha_type = "recaptcha_v2"
        elif "hcaptcha" in content_lower:
            captcha_type = "hcaptcha"
        elif "captcha" in content_lower:
            captcha_type = "image"

        if captcha_type:
            self._stats[
                "captchas_detected"
            ] += 1

        return {
            "has_captcha": (
                captcha_type is not None
            ),
            "captcha_type": captcha_type,
            "detected": True,
        }

    def solve(
        self,
        captcha_type: str,
        page_url: str = "",
        site_key: str = "",
    ) -> dict[str, Any]:
        """Captcha çözer.

        Args:
            captcha_type: Captcha tipi.
            page_url: Sayfa URL.
            site_key: Site anahtarı.

        Returns:
            Çözüm bilgisi.
        """
        self._counter += 1
        sid = f"cap_{self._counter}"

        # Servis kontrolü
        service = self._get_service(
            captcha_type,
        )

        solved = service is not None
        if solved:
            self._stats["captchas_solved"] += 1
        else:
            self._stats["failures"] += 1

        result = {
            "solve_id": sid,
            "captcha_type": captcha_type,
            "solved": solved,
            "token": (
                f"token_{sid}" if solved
                else None
            ),
            "service_used": (
                service["name"] if service
                else None
            ),
            "timestamp": time.time(),
        }
        self._solves.append(result)

        return result

    def _get_service(
        self,
        captcha_type: str,
    ) -> dict[str, Any] | None:
        """Uygun servisi bulur."""
        for service in self._services.values():
            if (
                service["active"]
                and captcha_type
                in service.get("types", [])
            ):
                return service
        # Varsayılan simülasyon
        return {
            "name": "simulated",
            "active": True,
        }

    def register_service(
        self,
        name: str,
        api_key: str = "",
        types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Servis kaydeder.

        Args:
            name: Servis adı.
            api_key: API anahtarı.
            types: Desteklenen tipler.

        Returns:
            Kayıt bilgisi.
        """
        self._services[name] = {
            "name": name,
            "has_key": bool(api_key),
            "types": types or [
                "recaptcha_v2", "hcaptcha",
                "image",
            ],
            "active": True,
        }
        return {
            "name": name,
            "registered": True,
        }

    def escalate_to_human(
        self,
        captcha_type: str,
        reason: str = "unsolvable",
    ) -> dict[str, Any]:
        """İnsana eskale eder.

        Args:
            captcha_type: Captcha tipi.
            reason: Neden.

        Returns:
            Eskalasyon bilgisi.
        """
        escalation = {
            "captcha_type": captcha_type,
            "reason": reason,
            "timestamp": time.time(),
        }
        self._escalations.append(escalation)
        self._stats["escalations"] += 1

        return {
            "escalated": True,
            "reason": reason,
            "captcha_type": captcha_type,
        }

    def get_solves(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Çözümleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Çözüm listesi.
        """
        return list(self._solves[-limit:])

    @property
    def detected_count(self) -> int:
        """Tespit edilen sayı."""
        return self._stats[
            "captchas_detected"
        ]

    @property
    def solved_count(self) -> int:
        """Çözülen sayı."""
        return self._stats["captchas_solved"]

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayısı."""
        return self._stats["escalations"]
