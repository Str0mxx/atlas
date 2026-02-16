"""ATLAS Bilgi Bağlayıcı modülü.

Otomatik bağlantı, ilgili içerik,
çapraz referans, geri bağlantılar,
bağlantı doğrulama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeLinker:
    """Bilgi bağlayıcı.

    Bilgi sayfalarını birbirine bağlar.

    Attributes:
        _links: Bağlantı kayıtları.
        _backlinks: Geri bağlantılar.
    """

    def __init__(self) -> None:
        """Bağlayıcıyı başlatır."""
        self._links: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._backlinks: dict[
            str, list[str]
        ] = {}
        self._pages: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "links_created": 0,
            "auto_links": 0,
        }

        logger.info(
            "KnowledgeLinker baslatildi",
        )

    def register_page(
        self,
        page_id: str,
        title: str = "",
        keywords: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Sayfa kaydeder.

        Args:
            page_id: Sayfa kimliği.
            title: Başlık.
            keywords: Anahtar kelimeler.

        Returns:
            Kayıt bilgisi.
        """
        keywords = keywords or []

        self._pages[page_id] = {
            "page_id": page_id,
            "title": title,
            "keywords": keywords,
        }

        return {
            "page_id": page_id,
            "registered": True,
        }

    def auto_link(
        self,
        page_id: str,
        content: str = "",
    ) -> dict[str, Any]:
        """Otomatik bağlantı yapar.

        Args:
            page_id: Sayfa kimliği.
            content: İçerik.

        Returns:
            Bağlantı bilgisi.
        """
        found_links: list[
            dict[str, Any]
        ] = []
        content_lower = content.lower()

        for pid, page in (
            self._pages.items()
        ):
            if pid == page_id:
                continue

            title = page.get(
                "title", "",
            ).lower()
            keywords = [
                k.lower()
                for k in page.get(
                    "keywords", [],
                )
            ]

            matched = False
            if (
                title
                and title in content_lower
            ):
                matched = True
            else:
                for kw in keywords:
                    if kw in content_lower:
                        matched = True
                        break

            if matched:
                found_links.append({
                    "to": pid,
                    "type": "auto",
                })
                bk = self._backlinks.get(
                    pid, [],
                )
                if page_id not in bk:
                    bk.append(page_id)
                self._backlinks[pid] = bk

        existing = self._links.get(
            page_id, [],
        )
        existing.extend(found_links)
        self._links[page_id] = existing

        self._stats[
            "auto_links"
        ] += len(found_links)

        return {
            "page_id": page_id,
            "links_found": len(
                found_links,
            ),
            "links": found_links,
            "linked": True,
        }

    def find_related(
        self,
        page_id: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """İlgili içerik bulur.

        Args:
            page_id: Sayfa kimliği.
            max_results: Maks sonuç.

        Returns:
            İlgili içerik bilgisi.
        """
        page = self._pages.get(page_id)
        if not page:
            return {
                "page_id": page_id,
                "found": False,
            }

        keywords = set(
            k.lower()
            for k in page.get(
                "keywords", [],
            )
        )

        related: list[
            dict[str, Any]
        ] = []

        for pid, p in (
            self._pages.items()
        ):
            if pid == page_id:
                continue
            p_keywords = set(
                k.lower()
                for k in p.get(
                    "keywords", [],
                )
            )
            overlap = len(
                keywords & p_keywords,
            )
            if overlap > 0:
                related.append({
                    "page_id": pid,
                    "title": p.get(
                        "title", "",
                    ),
                    "relevance": overlap,
                })

        related.sort(
            key=lambda r: r["relevance"],
            reverse=True,
        )

        return {
            "page_id": page_id,
            "related": related[
                :max_results
            ],
            "count": min(
                len(related), max_results,
            ),
            "found_ok": True,
        }

    def add_cross_reference(
        self,
        from_page: str,
        to_page: str,
        ref_type: str = "reference",
    ) -> dict[str, Any]:
        """Çapraz referans ekler.

        Args:
            from_page: Kaynak sayfa.
            to_page: Hedef sayfa.
            ref_type: Referans tipi.

        Returns:
            Referans bilgisi.
        """
        existing = self._links.get(
            from_page, [],
        )
        existing.append({
            "to": to_page,
            "type": ref_type,
        })
        self._links[from_page] = existing

        bk = self._backlinks.get(
            to_page, [],
        )
        if from_page not in bk:
            bk.append(from_page)
        self._backlinks[to_page] = bk

        self._stats["links_created"] += 1

        return {
            "from": from_page,
            "to": to_page,
            "ref_type": ref_type,
            "added": True,
        }

    def get_backlinks(
        self,
        page_id: str,
    ) -> dict[str, Any]:
        """Geri bağlantıları getirir.

        Args:
            page_id: Sayfa kimliği.

        Returns:
            Geri bağlantı bilgisi.
        """
        backlinks = self._backlinks.get(
            page_id, [],
        )

        return {
            "page_id": page_id,
            "backlinks": backlinks,
            "count": len(backlinks),
            "retrieved": True,
        }

    def validate_links(
        self,
        page_id: str = "",
    ) -> dict[str, Any]:
        """Bağlantı doğrulama yapar.

        Args:
            page_id: Sayfa kimliği (boşsa tümü).

        Returns:
            Doğrulama bilgisi.
        """
        broken: list[
            dict[str, Any]
        ] = []
        valid_count = 0

        pages_to_check = (
            {page_id: self._links.get(
                page_id, [],
            )}
            if page_id
            else self._links
        )

        for pid, links in (
            pages_to_check.items()
        ):
            for link in links:
                target = link.get("to", "")
                if target not in (
                    self._pages
                ):
                    broken.append({
                        "from": pid,
                        "to": target,
                        "type": link.get(
                            "type", "",
                        ),
                    })
                else:
                    valid_count += 1

        return {
            "broken_links": broken,
            "broken_count": len(broken),
            "valid_count": valid_count,
            "validated": True,
        }

    @property
    def link_count(self) -> int:
        """Bağlantı sayısı."""
        return self._stats[
            "links_created"
        ]

    @property
    def auto_link_count(self) -> int:
        """Otomatik bağlantı sayısı."""
        return self._stats[
            "auto_links"
        ]
