"""ATLAS Wiki Oluşturucu modülü.

Sayfa oluşturma, hiyerarşi yönetimi,
bağlantı sistemi, şablon desteği,
biçimlendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WikiBuilder:
    """Wiki oluşturucu.

    Wiki sayfalarını oluşturur ve yönetir.

    Attributes:
        _pages: Sayfa kayıtları.
        _hierarchy: Hiyerarşi yapısı.
        _templates: Şablon kayıtları.
    """

    def __init__(self) -> None:
        """Wiki oluşturucuyu başlatır."""
        self._pages: dict[
            str, dict[str, Any]
        ] = {}
        self._hierarchy: dict[
            str, list[str]
        ] = {}
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "pages_created": 0,
            "templates_used": 0,
        }

        logger.info(
            "WikiBuilder baslatildi",
        )

    def create_page(
        self,
        title: str,
        content: str = "",
        author: str = "",
        parent_id: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sayfa oluşturur.

        Args:
            title: Başlık.
            content: İçerik.
            author: Yazar.
            parent_id: Üst sayfa kimliği.
            tags: Etiketler.

        Returns:
            Oluşturma bilgisi.
        """
        tags = tags or []
        self._counter += 1
        pid = f"pg_{self._counter}"

        self._pages[pid] = {
            "page_id": pid,
            "title": title,
            "content": content,
            "author": author,
            "parent_id": parent_id,
            "tags": tags,
            "status": "draft",
            "links": [],
            "timestamp": time.time(),
        }

        if parent_id:
            children = self._hierarchy.get(
                parent_id, [],
            )
            children.append(pid)
            self._hierarchy[
                parent_id
            ] = children

        self._stats["pages_created"] += 1

        return {
            "page_id": pid,
            "title": title,
            "status": "draft",
            "created": True,
        }

    def manage_hierarchy(
        self,
        page_id: str,
        action: str = "get_children",
        target_id: str = "",
    ) -> dict[str, Any]:
        """Hiyerarşi yönetir.

        Args:
            page_id: Sayfa kimliği.
            action: Eylem.
            target_id: Hedef sayfa kimliği.

        Returns:
            Hiyerarşi bilgisi.
        """
        if action == "get_children":
            children = self._hierarchy.get(
                page_id, [],
            )
            return {
                "page_id": page_id,
                "children": children,
                "count": len(children),
                "retrieved": True,
            }

        if action == "move":
            page = self._pages.get(page_id)
            if page:
                old_parent = page.get(
                    "parent_id", "",
                )
                if old_parent:
                    old_children = (
                        self._hierarchy.get(
                            old_parent, [],
                        )
                    )
                    if page_id in old_children:
                        old_children.remove(
                            page_id,
                        )

                page["parent_id"] = target_id
                if target_id:
                    new_children = (
                        self._hierarchy.get(
                            target_id, [],
                        )
                    )
                    new_children.append(
                        page_id,
                    )
                    self._hierarchy[
                        target_id
                    ] = new_children

            return {
                "page_id": page_id,
                "new_parent": target_id,
                "moved": True,
            }

        return {
            "page_id": page_id,
            "action": action,
            "managed": True,
        }

    def add_link(
        self,
        from_page: str,
        to_page: str,
        link_type: str = "related",
    ) -> dict[str, Any]:
        """Bağlantı ekler.

        Args:
            from_page: Kaynak sayfa.
            to_page: Hedef sayfa.
            link_type: Bağlantı tipi.

        Returns:
            Bağlantı bilgisi.
        """
        page = self._pages.get(from_page)
        if page:
            page["links"].append({
                "to": to_page,
                "type": link_type,
            })

        return {
            "from": from_page,
            "to": to_page,
            "link_type": link_type,
            "linked": True,
        }

    def use_template(
        self,
        template_name: str,
        variables: dict[str, str]
        | None = None,
    ) -> dict[str, Any]:
        """Şablon kullanır.

        Args:
            template_name: Şablon adı.
            variables: Değişkenler.

        Returns:
            Şablon bilgisi.
        """
        variables = variables or {}

        template = self._templates.get(
            template_name,
        )
        if not template:
            default_templates = {
                "article": (
                    "# {{title}}\n\n"
                    "{{content}}"
                ),
                "guide": (
                    "# {{title}}\n\n"
                    "## Steps\n\n"
                    "{{content}}"
                ),
                "reference": (
                    "# {{title}}\n\n"
                    "## Overview\n\n"
                    "{{content}}"
                ),
            }
            body = default_templates.get(
                template_name,
                "# {{title}}\n\n{{content}}",
            )
        else:
            body = template.get("body", "")

        rendered = body
        for k, v in variables.items():
            rendered = rendered.replace(
                f"{{{{{k}}}}}", v,
            )

        self._stats["templates_used"] += 1

        return {
            "template": template_name,
            "rendered": rendered,
            "variables_used": len(variables),
            "applied": True,
        }

    def format_content(
        self,
        page_id: str,
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """İçerik biçimlendirir.

        Args:
            page_id: Sayfa kimliği.
            output_format: Çıktı biçimi.

        Returns:
            Biçimlendirme bilgisi.
        """
        page = self._pages.get(page_id)
        if not page:
            return {
                "page_id": page_id,
                "found": False,
            }

        content = page.get("content", "")
        title = page.get("title", "")

        if output_format == "markdown":
            formatted = (
                f"# {title}\n\n{content}"
            )
        elif output_format == "html":
            formatted = (
                f"<h1>{title}</h1>"
                f"<p>{content}</p>"
            )
        else:
            formatted = (
                f"{title}\n\n{content}"
            )

        return {
            "page_id": page_id,
            "format": output_format,
            "formatted": formatted,
            "formatted_ok": True,
        }

    @property
    def page_count(self) -> int:
        """Sayfa sayısı."""
        return self._stats[
            "pages_created"
        ]

    @property
    def template_usage(self) -> int:
        """Şablon kullanım sayısı."""
        return self._stats[
            "templates_used"
        ]
