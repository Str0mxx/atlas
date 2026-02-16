"""ATLAS Bilgi Tabanı Orkestratörü.

Tam bilgi yönetimi pipeline,
Create → Index → Link → Maintain,
kendi kendini güncelleyen wiki, analitik.
"""

import logging
import time
from typing import Any

from app.core.knowledgebase.auto_documenter import (
    AutoDocumenter,
)
from app.core.knowledgebase.faq_generator import (
    FAQGenerator,
)
from app.core.knowledgebase.gap_finder import (
    KnowledgeGapFinder,
)
from app.core.knowledgebase.kb_contributor import (
    KBContributor,
)
from app.core.knowledgebase.kb_search_indexer import (
    KBSearchIndexer,
)
from app.core.knowledgebase.knowledge_linker import (
    KnowledgeLinker,
)
from app.core.knowledgebase.versioned_content import (
    VersionedContent,
)
from app.core.knowledgebase.wiki_builder import (
    WikiBuilder,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseOrchestrator:
    """Bilgi tabanı orkestratörü.

    Tüm bilgi tabanı bileşenlerini
    koordine eder.

    Attributes:
        wiki: Wiki oluşturucu.
        documenter: Otomatik belgeleyici.
        faq: SSS üretici.
        indexer: Arama indeksleyici.
        linker: Bilgi bağlayıcı.
        gaps: Boşluk bulucu.
        versions: Versiyonlu içerik.
        contributors: Katkı yöneticisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.wiki = WikiBuilder()
        self.documenter = AutoDocumenter()
        self.faq = FAQGenerator()
        self.indexer = KBSearchIndexer()
        self.linker = KnowledgeLinker()
        self.gaps = KnowledgeGapFinder()
        self.versions = VersionedContent()
        self.contributors = (
            KBContributor()
        )
        self._stats = {
            "pipelines_run": 0,
            "pages_managed": 0,
        }

        logger.info(
            "KnowledgeBaseOrchestrator "
            "baslatildi",
        )

    def create_index_link(
        self,
        title: str,
        content: str = "",
        author: str = "",
        tags: list[str] | None = None,
        keywords: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Create → Index → Link pipeline.

        Args:
            title: Başlık.
            content: İçerik.
            author: Yazar.
            tags: Etiketler.
            keywords: Anahtar kelimeler.

        Returns:
            Pipeline bilgisi.
        """
        tags = tags or []
        keywords = keywords or []

        # 1. Create page
        page = self.wiki.create_page(
            title=title,
            content=content,
            author=author,
            tags=tags,
        )
        page_id = page["page_id"]

        # 2. Create version
        self.versions.create_version(
            page_id=page_id,
            content=content,
            author=author,
            message="Initial creation",
        )

        # 3. Index
        self.indexer.index_fulltext(
            page_id=page_id,
            title=title,
            content=content,
            tags=tags,
        )
        self.indexer.index_semantic(
            page_id=page_id,
            content=content,
            keywords=keywords,
        )

        # 4. Register for linking
        self.linker.register_page(
            page_id=page_id,
            title=title,
            keywords=keywords,
        )

        # 5. Auto-link
        link_result = (
            self.linker.auto_link(
                page_id=page_id,
                content=content,
            )
        )

        # 6. Track contribution
        self.contributors.track_contribution(
            contributor=author or "system",
            page_id=page_id,
            contribution_type="create",
            content_size=len(content),
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "pages_managed"
        ] += 1

        return {
            "page_id": page_id,
            "title": title,
            "indexed": True,
            "links_found": link_result[
                "links_found"
            ],
            "version": 1,
            "pipeline_complete": True,
        }

    def self_update(
        self,
        page_id: str,
        new_content: str = "",
        author: str = "",
    ) -> dict[str, Any]:
        """Kendi kendini günceller.

        Args:
            page_id: Sayfa kimliği.
            new_content: Yeni içerik.
            author: Yazar.

        Returns:
            Güncelleme bilgisi.
        """
        # 1. Create new version
        ver = self.versions.create_version(
            page_id=page_id,
            content=new_content,
            author=author or "system",
            message="Auto-update",
        )

        # 2. Update index
        self.indexer.update_realtime(
            page_id=page_id,
            new_content=new_content,
        )

        # 3. Re-link
        link_result = (
            self.linker.auto_link(
                page_id=page_id,
                content=new_content,
            )
        )

        # 4. Log change
        self.documenter.log_change(
            page_id=page_id,
            change_type="update",
            description="Auto-update",
            author=author or "system",
        )

        return {
            "page_id": page_id,
            "version": ver["version"],
            "links_found": link_result[
                "links_found"
            ],
            "updated": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": (
                self._stats[
                    "pipelines_run"
                ]
            ),
            "pages_managed": (
                self._stats[
                    "pages_managed"
                ]
            ),
            "pages_created": (
                self.wiki.page_count
            ),
            "versions": (
                self.versions.version_count
            ),
            "docs_generated": (
                self.documenter.doc_count
            ),
            "faqs_generated": (
                self.faq.faq_count
            ),
            "pages_indexed": (
                self.indexer.index_count
            ),
            "links_created": (
                self.linker.link_count
            ),
            "gaps_found": (
                self.gaps.gap_count
            ),
            "contributions": (
                self.contributors
                .contribution_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def page_count(self) -> int:
        """Yönetilen sayfa sayısı."""
        return self._stats[
            "pages_managed"
        ]
