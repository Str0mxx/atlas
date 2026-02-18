"""
Prompt sablon kutuphanesi modulu.

Sablon depolama, kategori,
degisken yonetimi, kalitim,
arama yetenegi.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PromptTemplateLibrary:
    """Prompt sablon kutuphanesi.

    Attributes:
        _templates: Sablon kayitlari.
        _categories: Kategoriler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Kutuphaneyi baslatir."""
        self._templates: dict[
            str, dict
        ] = {}
        self._categories: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "templates_created": 0,
            "templates_rendered": 0,
            "categories_created": 0,
            "searches_performed": 0,
        }
        logger.info(
            "PromptTemplateLibrary "
            "baslatildi"
        )

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)

    def create_category(
        self,
        name: str = "",
        description: str = "",
        parent: str = "",
    ) -> dict[str, Any]:
        """Kategori olusturur.

        Args:
            name: Kategori adi.
            description: Aciklama.
            parent: Ust kategori.

        Returns:
            Kategori bilgisi.
        """
        try:
            self._categories[name] = {
                "name": name,
                "description": description,
                "parent": parent,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "categories_created"
            ] += 1

            return {
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def create_template(
        self,
        name: str = "",
        content: str = "",
        category: str = "",
        variables: (
            list[str] | None
        ) = None,
        parent_template: str = "",
        tags: (
            list[str] | None
        ) = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Sablon olusturur.

        Args:
            name: Sablon adi.
            content: Icerik.
            category: Kategori.
            variables: Degiskenler.
            parent_template: Ust sablon.
            tags: Etiketler.
            description: Aciklama.

        Returns:
            Sablon bilgisi.
        """
        try:
            tid = f"pt_{uuid4()!s:.8}"

            # Degiskenleri cikar
            detected = self._extract_vars(
                content
            )
            vars_list = variables or detected

            # Kalitim
            if parent_template:
                parent = self._templates.get(
                    parent_template
                )
                if parent:
                    merged = (
                        parent["content"]
                        + "\n\n"
                        + content
                    )
                    content = merged
                    vars_list = list(
                        set(vars_list)
                        | set(
                            parent[
                                "variables"
                            ]
                        )
                    )

            self._templates[tid] = {
                "template_id": tid,
                "name": name,
                "content": content,
                "category": category,
                "variables": vars_list,
                "parent_template": (
                    parent_template
                ),
                "tags": tags or [],
                "description": description,
                "usage_count": 0,
                "version": 1,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "templates_created"
            ] += 1

            return {
                "template_id": tid,
                "name": name,
                "variables": vars_list,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def _extract_vars(
        self,
        content: str,
    ) -> list[str]:
        """Degiskenleri cikarir."""
        pattern = r"\{\{(\w+)\}\}"
        return list(
            set(re.findall(pattern, content))
        )

    def render_template(
        self,
        template_id: str = "",
        variables: (
            dict[str, str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Sablonu render eder.

        Args:
            template_id: Sablon ID.
            variables: Degisken degerleri.

        Returns:
            Render sonucu.
        """
        try:
            tpl = self._templates.get(
                template_id
            )
            if not tpl:
                return {
                    "rendered": False,
                    "error": (
                        "Sablon bulunamadi"
                    ),
                }

            content = tpl["content"]
            vals = variables or {}

            for var in tpl["variables"]:
                placeholder = (
                    "{{" + var + "}}"
                )
                value = vals.get(var, "")
                content = content.replace(
                    placeholder, value
                )

            tpl["usage_count"] += 1
            self._stats[
                "templates_rendered"
            ] += 1

            return {
                "template_id": (
                    template_id
                ),
                "content": content,
                "rendered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rendered": False,
                "error": str(e),
            }

    def get_template(
        self,
        template_id: str = "",
    ) -> dict[str, Any]:
        """Sablonu getirir.

        Args:
            template_id: Sablon ID.

        Returns:
            Sablon bilgisi.
        """
        try:
            tpl = self._templates.get(
                template_id
            )
            if not tpl:
                return {
                    "retrieved": False,
                    "error": (
                        "Sablon bulunamadi"
                    ),
                }

            return {
                **tpl,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def update_template(
        self,
        template_id: str = "",
        content: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Sablonu gunceller.

        Args:
            template_id: Sablon ID.
            content: Yeni icerik.
            description: Yeni aciklama.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            tpl = self._templates.get(
                template_id
            )
            if not tpl:
                return {
                    "updated": False,
                    "error": (
                        "Sablon bulunamadi"
                    ),
                }

            if content:
                tpl["content"] = content
                tpl["variables"] = (
                    self._extract_vars(
                        content
                    )
                )
            if description:
                tpl["description"] = (
                    description
                )
            tpl["version"] += 1

            return {
                "template_id": (
                    template_id
                ),
                "version": tpl["version"],
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def search_templates(
        self,
        query: str = "",
        category: str = "",
        tags: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Sablonlari arar.

        Args:
            query: Arama sorgusu.
            category: Kategori filtresi.
            tags: Etiket filtresi.

        Returns:
            Arama sonucu.
        """
        try:
            results = []
            search_tags = tags or []

            for tpl in (
                self._templates.values()
            ):
                # Kategori filtresi
                if (
                    category
                    and tpl["category"]
                    != category
                ):
                    continue

                # Etiket filtresi
                if search_tags:
                    if not set(
                        search_tags
                    ).intersection(
                        set(tpl["tags"])
                    ):
                        continue

                # Metin arama
                if query:
                    q = query.lower()
                    name = tpl[
                        "name"
                    ].lower()
                    desc = tpl[
                        "description"
                    ].lower()
                    cont = tpl[
                        "content"
                    ].lower()
                    if (
                        q not in name
                        and q not in desc
                        and q not in cont
                    ):
                        continue

                results.append({
                    "template_id": tpl[
                        "template_id"
                    ],
                    "name": tpl["name"],
                    "category": tpl[
                        "category"
                    ],
                    "usage_count": tpl[
                        "usage_count"
                    ],
                })

            self._stats[
                "searches_performed"
            ] += 1

            return {
                "results": results,
                "count": len(results),
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def list_by_category(
        self,
        category: str = "",
    ) -> dict[str, Any]:
        """Kategoriye gore listeler."""
        try:
            results = [
                {
                    "template_id": t[
                        "template_id"
                    ],
                    "name": t["name"],
                }
                for t in (
                    self._templates.values()
                )
                if t["category"] == category
            ]
            return {
                "templates": results,
                "count": len(results),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_cat: dict[str, int] = {}
            for t in (
                self._templates.values()
            ):
                c = t["category"] or "uncategorized"
                by_cat[c] = (
                    by_cat.get(c, 0) + 1
                )

            return {
                "total_templates": len(
                    self._templates
                ),
                "total_categories": len(
                    self._categories
                ),
                "by_category": by_cat,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
