"""OpenClaw beceri donusturucusu.

Ham OpenClaw becerilerini dinamik
BaseSkill alt sinifina donusturur.
"""

import logging
import re
import time
from typing import Any

from app.core.skills.base_skill import (
    BaseSkill,
)
from app.models.openclaw_models import (
    ConversionResult,
    OpenClawSkillRaw,
    SecurityScanResult,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 5000
_MAX_HISTORY = 5000

# Kategori esleme tablosu
_CATEGORY_MAP: dict[str, str] = {
    "cursor": "developer",
    "code": "developer",
    "coding": "developer",
    "devops": "developer",
    "development": "developer",
    "programming": "developer",
    "debug": "developer",
    "testing": "developer",
    "git": "developer",
    "web": "web",
    "api": "web",
    "http": "web",
    "scraping": "web",
    "browser": "web",
    "data": "data_science",
    "data-science": "data_science",
    "analytics": "data_science",
    "ml": "data_science",
    "machine-learning": "data_science",
    "ai": "data_science",
    "finance": "finance",
    "accounting": "finance",
    "trading": "finance",
    "seo": "seo",
    "marketing": "seo",
    "content": "communication",
    "writing": "communication",
    "email": "communication",
    "communication": "communication",
    "chat": "communication",
    "media": "media",
    "image": "media",
    "video": "media",
    "audio": "media",
    "design": "media",
    "time": "datetime",
    "date": "datetime",
    "calendar": "datetime",
    "scheduler": "datetime",
    "document": "document",
    "pdf": "document",
    "docs": "document",
    "productivity": "productivity",
    "automation": "productivity",
    "workflow": "productivity",
    "task": "productivity",
}

# ID sayaci
_id_counter: int = 0


def _next_id() -> int:
    """Sonraki ID sayacini dondurur."""
    global _id_counter
    _id_counter += 1
    return _id_counter


def reset_id_counter() -> None:
    """ID sayacini sifirlar (test icin)."""
    global _id_counter
    _id_counter = 0


class OpenClawSkillConverter:
    """OpenClaw becerilerini BaseSkill'e donusturur.

    Dinamik sinif olusturarak disk uzerinde
    dosya yazmadan calisir.

    Attributes:
        _records: Donusum kayitlari.
    """

    def __init__(self) -> None:
        """OpenClawSkillConverter baslatir."""
        self._records: dict[
            str, ConversionResult
        ] = {}
        self._record_order: list[str] = []
        self._instances: dict[
            str, BaseSkill
        ] = {}
        self._total_ops: int = 0
        self._total_success: int = 0
        self._total_failed: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

    # ---- Donusum ----

    def create_skill_instance(
        self,
        raw: OpenClawSkillRaw,
        scan_result: SecurityScanResult | None = None,
    ) -> BaseSkill | None:
        """Ham beceriden BaseSkill ornegi olusturur.

        Args:
            raw: Ham beceri verisi.
            scan_result: Guvenlik tarama sonucu.

        Returns:
            BaseSkill ornegi veya None.
        """
        self._total_ops += 1

        try:
            fm = raw.frontmatter
            skill_name = fm.name or (
                self._name_from_path(
                    raw.file_path,
                )
            )
            skill_id = self._generate_skill_id()
            class_name = self._sanitize_class_name(
                skill_name,
            )
            category = self._map_category(
                fm.category,
                fm.tags,
            )
            risk_level = (
                scan_result.risk_level
                if scan_result
                else "medium"
            )

            prompt_text = raw.body
            source_repo = raw.source_repo
            required_env = fm.requires_env
            required_bins = fm.requires_bins
            params = dict(fm.extra)

            # Dinamik sinif olustur
            attrs: dict[str, Any] = {
                "SKILL_ID": skill_id,
                "NAME": skill_name,
                "CATEGORY": category,
                "RISK_LEVEL": risk_level,
                "DESCRIPTION": (
                    fm.description
                    or f"OpenClaw: {skill_name}"
                ),
                "PARAMETERS": {
                    "query": "Beceri sorgusu",
                },
                "VERSION": fm.version,
                "_prompt_text": prompt_text,
                "_source_repo": source_repo,
                "_required_env": required_env,
                "_required_bins": required_bins,
                "_oc_parameters": params,
            }

            def _execute_impl(
                self_inner: Any,
                **kw: Any,
            ) -> dict[str, Any]:
                return {
                    "skill_name": (
                        self_inner.NAME
                    ),
                    "prompt_text": (
                        self_inner._prompt_text
                    ),
                    "source_repo": (
                        self_inner._source_repo
                    ),
                    "required_env": (
                        self_inner._required_env
                    ),
                    "required_bins": (
                        self_inner._required_bins
                    ),
                    "parameters": kw,
                    "status": "prompt_ready",
                }

            attrs["_execute_impl"] = (
                _execute_impl
            )

            skill_cls = type(
                class_name,
                (BaseSkill,),
                attrs,
            )
            instance = skill_cls()

            # Kaydet
            result = ConversionResult(
                skill_id=skill_id,
                skill_name=skill_name,
                class_name=class_name,
                category=category,
                source_repo=source_repo,
                success=True,
                risk_level=risk_level,
            )
            self._records[skill_id] = result
            self._record_order.append(skill_id)
            self._instances[skill_id] = instance
            self._total_success += 1

            if len(self._records) > _MAX_RECORDS:
                self._rotate()

            self._record_history(
                "convert",
                skill_id,
                f"name={skill_name} "
                f"cat={category}",
            )
            return instance

        except Exception as e:
            self._total_failed += 1
            logger.warning(
                "Donusum hatasi %s: %s",
                raw.file_path, e,
            )
            return None

    # ---- ID Uretimi ----

    def _generate_skill_id(self) -> str:
        """Benzersiz OC_ onekli ID uretir.

        Returns:
            "OC_00001" formati ID.
        """
        num = _next_id()
        return f"OC_{num:05d}"

    # ---- Kategori Esleme ----

    def _map_category(
        self,
        category: str,
        tags: list[str],
    ) -> str:
        """Kategori adini ATLAS kategorisine esler.

        Args:
            category: OpenClaw kategori adi.
            tags: Etiket listesi.

        Returns:
            ATLAS kategori adi.
        """
        if category:
            cat_lower = category.lower().strip()
            if cat_lower in _CATEGORY_MAP:
                return _CATEGORY_MAP[cat_lower]

        # Etiketlerden esleme dene
        for tag in tags:
            tag_lower = tag.lower().strip()
            if tag_lower in _CATEGORY_MAP:
                return _CATEGORY_MAP[tag_lower]

        return "basic_tools"

    # ---- Sinif Adi ----

    def _sanitize_class_name(
        self,
        name: str,
    ) -> str:
        """Gecerli Python sinif adi uretir.

        Args:
            name: Ham beceri adi.

        Returns:
            Gecerli sinif adi.
        """
        # Alfanumerik olmayan karakterleri sil
        cleaned = re.sub(
            r"[^a-zA-Z0-9_]", "_", name,
        )
        # Bosluk ve tire yerine alt cizgi
        cleaned = re.sub(
            r"_+", "_", cleaned,
        ).strip("_")

        if not cleaned:
            cleaned = "UnnamedSkill"

        # Rakamla baslarsa onek ekle
        if cleaned[0].isdigit():
            cleaned = f"OC_{cleaned}"

        # PascalCase'e cevir
        parts = cleaned.split("_")
        pascal = "".join(
            p.capitalize() for p in parts
            if p
        )

        return f"OC{pascal}Skill"

    def _name_from_path(
        self,
        file_path: str,
    ) -> str:
        """Dosya yolundan beceri adi cikarir.

        Args:
            file_path: Dosya yolu.

        Returns:
            Beceri adi.
        """
        import os
        parent = os.path.dirname(file_path)
        name = os.path.basename(parent)
        if not name or name == ".":
            name = os.path.basename(file_path)
        return name.replace("-", " ").replace(
            "_", " ",
        ).title()

    # ---- Sorgulama ----

    def get_instance(
        self,
        skill_id: str,
    ) -> BaseSkill | None:
        """Olusturulan ornegi dondurur.

        Args:
            skill_id: Beceri ID.

        Returns:
            BaseSkill ornegi veya None.
        """
        return self._instances.get(skill_id)

    def get_result(
        self,
        skill_id: str,
    ) -> ConversionResult | None:
        """Donusum sonucunu dondurur.

        Args:
            skill_id: Beceri ID.

        Returns:
            Sonuc veya None.
        """
        return self._records.get(skill_id)

    def list_instances(
        self,
        limit: int = 100,
    ) -> list[BaseSkill]:
        """Olusturulan ornekleri listeler.

        Args:
            limit: Maks sayi.

        Returns:
            Ornek listesi.
        """
        keys = list(
            reversed(self._record_order),
        )[:limit]
        result: list[BaseSkill] = []
        for k in keys:
            inst = self._instances.get(k)
            if inst:
                result.append(inst)
        return result

    # ---- Dahili ----

    def _rotate(self) -> int:
        """Eski kayitlari temizler."""
        keep = _MAX_RECORDS // 2
        if len(self._record_order) <= keep:
            return 0
        to_remove = self._record_order[:-keep]
        for k in to_remove:
            self._records.pop(k, None)
            self._instances.pop(k, None)
        self._record_order = (
            self._record_order[-keep:]
        )
        return len(to_remove)

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-2500:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "total_converted": len(
                self._instances,
            ),
            "total_ops": self._total_ops,
            "total_success": self._total_success,
            "total_failed": self._total_failed,
        }
