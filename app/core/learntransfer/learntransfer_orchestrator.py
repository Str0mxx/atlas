"""ATLAS LearnTransfer Orkestrator modulu.

Tam transfer pipeline,
Extract > Match > Adapt > Validate > Inject.
"""

import logging
from typing import Any

from app.core.learntransfer.feedback_loop import (
    TransferFeedbackLoop,
)
from app.core.learntransfer.knowledge_adapter import (
    KnowledgeAdapter,
)
from app.core.learntransfer.knowledge_extractor import (
    KnowledgeExtractor,
)
from app.core.learntransfer.knowledge_injector import (
    KnowledgeInjector,
)
from app.core.learntransfer.knowledge_network import (
    KnowledgeNetwork,
)
from app.core.learntransfer.similarity_analyzer import (
    SimilarityAnalyzer,
)
from app.core.learntransfer.transfer_tracker import (
    TransferTracker,
)
from app.core.learntransfer.transfer_validator import (
    TransferValidator,
)

logger = logging.getLogger(__name__)


class LearnTransferOrchestrator:
    """LearnTransfer orkestrator.

    Tum ogrenme transferi bilesenleri koordine eder.

    Attributes:
        extractor: Bilgi cikarici.
        analyzer: Benzerlik analizcisi.
        adapter: Bilgi adaptoru.
        validator: Transfer dogrulayici.
        injector: Bilgi enjektoru.
        tracker: Transfer takipcisi.
        feedback: Geri bildirim dongusu.
        network: Bilgi agi.
    """

    def __init__(
        self,
        min_similarity: float = 0.3,
        auto_transfer: bool = False,
        require_validation: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            min_similarity: Min benzerlik.
            auto_transfer: Oto transfer.
            require_validation: Dogrulama zorunlu.
        """
        self.extractor = KnowledgeExtractor()
        self.analyzer = SimilarityAnalyzer(
            min_threshold=min_similarity,
        )
        self.adapter = KnowledgeAdapter()
        self.validator = TransferValidator()
        self.injector = KnowledgeInjector()
        self.tracker = TransferTracker()
        self.feedback = (
            TransferFeedbackLoop()
        )
        self.network = KnowledgeNetwork()

        self._auto_transfer = auto_transfer
        self._require_validation = (
            require_validation
        )
        self._stats = {
            "pipelines_run": 0,
        }

        logger.info(
            "LearnTransferOrchestrator "
            "baslatildi",
        )

    def transfer_knowledge(
        self,
        source_system: str,
        target_system: str,
        experience: dict[str, Any],
        target_context: dict[str, Any],
        adapt_method: str = "direct",
    ) -> dict[str, Any]:
        """Bilgi transfer eder (tam pipeline).

        Args:
            source_system: Kaynak sistem.
            target_system: Hedef sistem.
            experience: Deneyim verisi.
            target_context: Hedef baglam.
            adapt_method: Adaptasyon yontemi.

        Returns:
            Transfer sonucu.
        """
        # 1) Extract
        extraction = (
            self.extractor.extract_learning(
                source_system, experience,
            )
        )

        kid = extraction["knowledge_id"]
        knowledge = (
            self.extractor.get_knowledge(kid)
        )

        # 2) Adapt
        adaptation = (
            self.adapter.adapt_knowledge(
                knowledge, target_context,
                method=adapt_method,
            )
        )

        # 3) Validate
        validated = True
        validation = None
        if self._require_validation:
            validation = (
                self.validator
                .validate_transfer(
                    knowledge,
                    target_system,
                    target_context,
                )
            )
            validated = validation["approved"]

        if not validated:
            self._stats["pipelines_run"] += 1
            return {
                "source_system": source_system,
                "target_system": target_system,
                "knowledge_id": kid,
                "transferred": False,
                "reason": "validation_failed",
                "validation": validation,
            }

        # 4) Inject
        injection = (
            self.injector.inject_knowledge(
                target_system, knowledge,
            )
        )

        # 5) Track
        tracking = self.tracker.track_transfer(
            source_system,
            target_system,
            kid,
        )

        # 6) Network update
        for sys_id in (
            source_system, target_system,
        ):
            if not self.network.get_node(
                sys_id,
            ).get("error"):
                continue
            self.network.add_node(
                sys_id, "system",
            )

        self.network.add_edge(
            source_system,
            target_system,
            "knowledge_transfer",
        )

        self._stats["pipelines_run"] += 1

        return {
            "source_system": source_system,
            "target_system": target_system,
            "knowledge_id": kid,
            "transferred": True,
            "adaptation_id": adaptation[
                "adaptation_id"
            ],
            "injection_id": injection[
                "injection_id"
            ],
            "transfer_id": tracking[
                "transfer_id"
            ],
        }

    def find_transfer_opportunities(
        self,
        source_info: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Transfer firsatlarini bulur.

        Args:
            source_info: Kaynak bilgisi.
            candidates: Aday sistemler.

        Returns:
            Firsat listesi.
        """
        similar = (
            self.analyzer
            .find_similar_systems(
                source_info, candidates,
            )
        )

        return {
            "source": source_info.get(
                "system_id", "",
            ),
            "opportunities": similar,
            "opportunity_count": len(similar),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "knowledge_extracted": (
                self.extractor.knowledge_count
            ),
            "similarity_analyses": (
                self.analyzer.analysis_count
            ),
            "adaptations": (
                self.adapter.adaptation_count
            ),
            "validations": (
                self.validator
                .validation_count
            ),
            "approval_rate": (
                self.validator.approval_rate
            ),
            "injections": (
                self.injector.injection_count
            ),
            "transfers_tracked": (
                self.tracker.transfer_count
            ),
            "transfer_success_rate": (
                self.tracker.success_rate
            ),
            "feedback_collected": (
                self.feedback.feedback_count
            ),
            "network_nodes": (
                self.network.node_count
            ),
            "network_edges": (
                self.network.edge_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "total_knowledge": (
                self.extractor.knowledge_count
            ),
            "total_transfers": (
                self.tracker.transfer_count
            ),
            "total_injections": (
                self.injector.injection_count
            ),
            "network_size": (
                self.network.node_count
            ),
        }

    @property
    def pipelines_run(self) -> int:
        """Calisan pipeline sayisi."""
        return self._stats["pipelines_run"]
