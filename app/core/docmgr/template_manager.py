"""ATLAS Doküman Şablon Yöneticisi modülü.

Şablon kütüphanesi, değişken yerleştirme,
sürüm kontrolü, paylaşım,
analitik.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocTemplateManager:
    """Doküman şablon yöneticisi.

    Doküman şablonlarını yönetir.

    Attributes:
        _templates: Şablon kayıtları.
        _usage: Kullanım kayıtları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._usage: dict[
            str, int
        ] = {}
        self._shared: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "templates_created": 0,
            "templates_used": 0,
        }

        logger.info(
            "DocTemplateManager "
            "baslatildi",
        )

    def create_template(
        self,
        name: str,
        content: str = "",
        variables: list[str] | None = None,
        category: str = "",
    ) -> dict[str, Any]:
        """Şablon oluşturur.

        Args:
            name: Şablon adı.
            content: İçerik.
            variables: Değişkenler.
            category: Kategori.

        Returns:
            Oluşturma bilgisi.
        """
        self._counter += 1
        tid = f"tpl_{self._counter}"
        variables = variables or []

        self._templates[name] = {
            "template_id": tid,
            "name": name,
            "content": content,
            "variables": variables,
            "category": category,
            "version": 1,
            "timestamp": time.time(),
        }
        self._usage[name] = 0
        self._stats[
            "templates_created"
        ] += 1

        return {
            "template_id": tid,
            "name": name,
            "variables": variables,
            "created": True,
        }

    def substitute_variables(
        self,
        name: str,
        values: dict[str, str]
        | None = None,
    ) -> dict[str, Any]:
        """Değişken yerleştirme yapar.

        Args:
            name: Şablon adı.
            values: Değerler.

        Returns:
            Yerleştirme bilgisi.
        """
        values = values or {}
        tpl = self._templates.get(name)
        if not tpl:
            return {
                "name": name,
                "substituted": False,
            }

        content = tpl["content"]
        for var, val in values.items():
            placeholder = "{{" + var + "}}"
            content = content.replace(
                placeholder, val,
            )

        self._usage[name] = (
            self._usage.get(name, 0) + 1
        )
        self._stats[
            "templates_used"
        ] += 1

        return {
            "name": name,
            "content": content,
            "variables_replaced": len(
                values,
            ),
            "substituted": True,
        }

    def update_template(
        self,
        name: str,
        content: str = "",
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Şablon günceller (sürüm kontrolü).

        Args:
            name: Şablon adı.
            content: Yeni içerik.
            variables: Yeni değişkenler.

        Returns:
            Güncelleme bilgisi.
        """
        tpl = self._templates.get(name)
        if not tpl:
            return {
                "name": name,
                "updated": False,
            }

        if content:
            tpl["content"] = content
        if variables is not None:
            tpl["variables"] = variables

        tpl["version"] += 1
        tpl["timestamp"] = time.time()

        return {
            "name": name,
            "version": tpl["version"],
            "updated": True,
        }

    def share_template(
        self,
        name: str,
        users: list[str] | None = None,
    ) -> dict[str, Any]:
        """Şablon paylaşır.

        Args:
            name: Şablon adı.
            users: Kullanıcılar.

        Returns:
            Paylaşım bilgisi.
        """
        users = users or []
        if name not in self._templates:
            return {
                "name": name,
                "shared": False,
            }

        if name not in self._shared:
            self._shared[name] = []

        self._shared[name].extend(users)

        return {
            "name": name,
            "shared_with": users,
            "total_shared": len(
                self._shared[name],
            ),
            "shared": True,
        }

    def get_analytics(
        self,
        name: str = "",
    ) -> dict[str, Any]:
        """Şablon analitik döndürür.

        Args:
            name: Şablon adı (boşsa tümü).

        Returns:
            Analitik bilgisi.
        """
        if name:
            tpl = self._templates.get(name)
            if not tpl:
                return {
                    "name": name,
                    "found": False,
                }

            return {
                "name": name,
                "usage_count": self._usage.get(
                    name, 0,
                ),
                "version": tpl["version"],
                "shared_count": len(
                    self._shared.get(
                        name, [],
                    ),
                ),
                "found": True,
            }

        # Genel analitik
        most_used = sorted(
            self._usage.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        return {
            "total_templates": len(
                self._templates,
            ),
            "total_usage": sum(
                self._usage.values(),
            ),
            "most_used": [
                {"name": n, "count": c}
                for n, c in most_used
            ],
            "found": True,
        }

    @property
    def template_count(self) -> int:
        """Şablon sayısı."""
        return self._stats[
            "templates_created"
        ]

    @property
    def usage_count(self) -> int:
        """Kullanım sayısı."""
        return self._stats[
            "templates_used"
        ]
