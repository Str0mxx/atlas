"""ATLAS Kriz İletişim Şablonu modülü.

Mesaj şablonları, hedef kitle,
ton adaptasyonu, çoklu kanal,
versiyon kontrolü.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CrisisCommunicationTemplate:
    """Kriz iletişim şablonu.

    Kriz iletişimlerini şablonlar.

    Attributes:
        _templates: Şablon kayıtları.
        _versions: Versiyon geçmişi.
    """

    def __init__(self) -> None:
        """Şablonu başlatır."""
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._versions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "templates_created": 0,
            "messages_generated": 0,
        }

        logger.info(
            "CrisisCommunicationTemplate "
            "baslatildi",
        )

    def create_template(
        self,
        name: str,
        body: str = "",
        audience: str = "internal",
        tone: str = "formal",
        channels: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Şablon oluşturur.

        Args:
            name: Şablon adı.
            body: Gövde.
            audience: Hedef kitle.
            tone: Ton.
            channels: Kanallar.

        Returns:
            Oluşturma bilgisi.
        """
        channels = channels or [
            "telegram",
        ]
        self._counter += 1
        tid = f"tpl_{self._counter}"

        self._templates[name] = {
            "template_id": tid,
            "name": name,
            "body": body,
            "audience": audience,
            "tone": tone,
            "channels": channels,
            "version": 1,
            "timestamp": time.time(),
        }

        self._versions[name] = [{
            "version": 1,
            "body": body,
            "timestamp": time.time(),
        }]

        self._stats[
            "templates_created"
        ] += 1

        return {
            "template_id": tid,
            "name": name,
            "version": 1,
            "created": True,
        }

    def target_audience(
        self,
        template_name: str,
        audience: str = "internal",
    ) -> dict[str, Any]:
        """Hedef kitle ayarlar.

        Args:
            template_name: Şablon adı.
            audience: Hedef kitle.

        Returns:
            Ayarlama bilgisi.
        """
        tpl = self._templates.get(
            template_name,
        )
        if not tpl:
            return {
                "template": template_name,
                "found": False,
            }

        tpl["audience"] = audience

        return {
            "template": template_name,
            "audience": audience,
            "targeted": True,
        }

    def adapt_tone(
        self,
        template_name: str,
        tone: str = "formal",
        crisis_level: str = "moderate",
    ) -> dict[str, Any]:
        """Ton adaptasyonu yapar.

        Args:
            template_name: Şablon adı.
            tone: Ton.
            crisis_level: Kriz seviyesi.

        Returns:
            Adaptasyon bilgisi.
        """
        tpl = self._templates.get(
            template_name,
        )
        if not tpl:
            return {
                "template": template_name,
                "found": False,
            }

        if crisis_level in (
            "critical", "high",
        ):
            tone = "urgent"

        tpl["tone"] = tone

        return {
            "template": template_name,
            "tone": tone,
            "adapted": True,
        }

    def generate_message(
        self,
        template_name: str,
        variables: dict[str, str]
        | None = None,
    ) -> dict[str, Any]:
        """Mesaj üretir.

        Args:
            template_name: Şablon adı.
            variables: Değişkenler.

        Returns:
            Üretim bilgisi.
        """
        variables = variables or {}
        tpl = self._templates.get(
            template_name,
        )
        if not tpl:
            return {
                "template": template_name,
                "found": False,
            }

        body = tpl.get("body", "")
        for k, v in variables.items():
            body = body.replace(
                f"{{{{{k}}}}}", v,
            )

        self._stats[
            "messages_generated"
        ] += 1

        return {
            "template": template_name,
            "message": body,
            "tone": tpl["tone"],
            "channels": tpl["channels"],
            "generated": True,
        }

    def update_version(
        self,
        template_name: str,
        new_body: str = "",
    ) -> dict[str, Any]:
        """Versiyon günceller.

        Args:
            template_name: Şablon adı.
            new_body: Yeni gövde.

        Returns:
            Güncelleme bilgisi.
        """
        tpl = self._templates.get(
            template_name,
        )
        if not tpl:
            return {
                "template": template_name,
                "found": False,
            }

        new_ver = tpl["version"] + 1
        tpl["body"] = new_body
        tpl["version"] = new_ver

        versions = self._versions.get(
            template_name, [],
        )
        versions.append({
            "version": new_ver,
            "body": new_body,
            "timestamp": time.time(),
        })

        return {
            "template": template_name,
            "version": new_ver,
            "updated": True,
        }

    @property
    def template_count(self) -> int:
        """Şablon sayısı."""
        return self._stats[
            "templates_created"
        ]

    @property
    def message_count(self) -> int:
        """Mesaj sayısı."""
        return self._stats[
            "messages_generated"
        ]
