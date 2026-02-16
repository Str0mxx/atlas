"""ATLAS Doküman Yönetimi Orkestratörü.

Tam doküman yönetimi pipeline,
Upload → Classify → Tag → Index → Track,
yaşam döngüsü yönetimi, analitik.
"""

import logging
import time
from typing import Any

from app.core.docmgr.access_controller import (
    DocAccessController,
)
from app.core.docmgr.auto_tagger import (
    AutoTagger,
)
from app.core.docmgr.doc_search_engine import (
    DocSearchEngine,
)
from app.core.docmgr.document_classifier import (
    DocumentClassifier,
)
from app.core.docmgr.expiry_tracker import (
    ExpiryTracker,
)
from app.core.docmgr.summary_generator import (
    DocSummaryGenerator,
)
from app.core.docmgr.template_manager import (
    DocTemplateManager,
)
from app.core.docmgr.version_tracker import (
    DocVersionTracker,
)

logger = logging.getLogger(__name__)


class DocMgrOrchestrator:
    """Doküman yönetimi orkestratörü.

    Tüm doküman yönetimi bileşenlerini
    koordine eder.

    Attributes:
        classifier: Sınıflandırıcı.
        tagger: Etiketleyici.
        versions: Sürüm takipçisi.
        search: Arama motoru.
        summaries: Özet üretici.
        templates: Şablon yöneticisi.
        expiry: Süre takipçisi.
        access: Erişim kontrolcüsü.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.classifier = (
            DocumentClassifier()
        )
        self.tagger = AutoTagger()
        self.versions = DocVersionTracker()
        self.search = DocSearchEngine()
        self.summaries = (
            DocSummaryGenerator()
        )
        self.templates = (
            DocTemplateManager()
        )
        self.expiry = ExpiryTracker()
        self.access = DocAccessController()
        self._stats = {
            "pipelines_run": 0,
            "documents_managed": 0,
        }

        logger.info(
            "DocMgrOrchestrator "
            "baslatildi",
        )

    def upload_classify_tag_index(
        self,
        doc_id: str,
        title: str = "",
        content: str = "",
        author: str = "",
    ) -> dict[str, Any]:
        """Upload → Classify → Tag → Index.

        Args:
            doc_id: Doküman kimliği.
            title: Başlık.
            content: İçerik.
            author: Yazar.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Classify
        classification = (
            self.classifier.auto_classify(
                title=title,
                content=content,
            )
        )

        # 2. Tag
        tags = self.tagger.extract_keywords(
            doc_id, content,
        )
        tag_list = [
            k["word"]
            for k in tags.get(
                "keywords", [],
            )
        ]

        # 3. Index
        self.search.index_document(
            doc_id=doc_id,
            title=title,
            content=content,
            tags=tag_list,
            category=classification.get(
                "category", "",
            ),
        )

        # 4. Version
        self.versions.create_version(
            doc_id=doc_id,
            content=content,
            author=author,
        )

        self._stats["pipelines_run"] += 1
        self._stats[
            "documents_managed"
        ] += 1

        return {
            "doc_id": doc_id,
            "doc_type": classification.get(
                "doc_type", "report",
            ),
            "category": classification.get(
                "category", "",
            ),
            "tags_count": len(tag_list),
            "indexed": True,
            "versioned": True,
            "pipeline_complete": True,
        }

    def manage_lifecycle(
        self,
        doc_id: str,
        title: str = "",
        content: str = "",
        expiry_days: int = 365,
        owner: str = "",
    ) -> dict[str, Any]:
        """Yaşam döngüsü yönetimi.

        Args:
            doc_id: Doküman kimliği.
            title: Başlık.
            content: İçerik.
            expiry_days: Süre sonu (gün).
            owner: Sahip.

        Returns:
            Yönetim bilgisi.
        """
        # Pipeline
        pipeline = (
            self.upload_classify_tag_index(
                doc_id=doc_id,
                title=title,
                content=content,
                author=owner,
            )
        )

        # Süre takibi
        expiry = self.expiry.set_expiration(
            doc_id=doc_id,
            days_until_expiry=expiry_days,
        )

        # Erişim kontrolü
        self.access.set_permission(
            doc_id=doc_id,
            user=owner,
            level="internal",
            can_read=True,
            can_write=True,
            can_share=True,
        )

        # Özet üret
        summary = (
            self.summaries.auto_summarize(
                doc_id=doc_id,
                content=content,
            )
        )

        return {
            "doc_id": doc_id,
            "pipeline": pipeline[
                "pipeline_complete"
            ],
            "expiry_status": expiry[
                "status"
            ],
            "owner": owner,
            "summary_length": summary.get(
                "summary_length", 0,
            ),
            "managed": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "documents_managed": self._stats[
                "documents_managed"
            ],
            "classifications": (
                self.classifier
                .classification_count
            ),
            "tags": (
                self.tagger.tag_count
            ),
            "versions": (
                self.versions.version_count
            ),
            "indexed": (
                self.search.index_count
            ),
            "summaries": (
                self.summaries.summary_count
            ),
            "templates": (
                self.templates.template_count
            ),
            "expiry_tracked": (
                self.expiry.tracked_count
            ),
            "permissions": (
                self.access.permission_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def document_count(self) -> int:
        """Yönetilen doküman sayısı."""
        return self._stats[
            "documents_managed"
        ]
