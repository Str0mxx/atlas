"""ATLAS Kişi Yönetim Orkestratörü modülü.

Tam ilişki yönetimi,
Profile → Track → Score → Advise → Act,
ağ zekası, analitik.
"""

import logging
import time
from typing import Any

from app.core.peoplemgr.birthday_reminder import (
    BirthdayReminder,
)
from app.core.peoplemgr.contact_profiler import (
    ContactProfiler,
)
from app.core.peoplemgr.followup_scheduler import (
    PeopleFollowUpScheduler,
)
from app.core.peoplemgr.interaction_logger import (
    PeopleInteractionLogger,
)
from app.core.peoplemgr.network_mapper import (
    NetworkMapper,
)
from app.core.peoplemgr.relationship_advisor import (
    RelationshipAdvisor,
)
from app.core.peoplemgr.relationship_scorer import (
    RelationshipScorer,
)
from app.core.peoplemgr.sentiment_tracker import (
    PeopleSentimentTracker,
)

logger = logging.getLogger(__name__)


class PeopleMgrOrchestrator:
    """Kişi yönetim orkestratörü.

    Tüm kişi yönetim bileşenlerini
    koordine eder.

    Attributes:
        profiler: Kişi profilleyici.
        interactions: Etkileşim kaydedici.
        scorer: İlişki puanlayıcı.
        followups: Takip zamanlayıcı.
        sentiment: Duygu takipçisi.
        network: Ağ haritacısı.
        birthdays: Doğum günü hatırlatıcı.
        advisor: İlişki danışmanı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.profiler = ContactProfiler()
        self.interactions = (
            PeopleInteractionLogger()
        )
        self.scorer = RelationshipScorer()
        self.followups = (
            PeopleFollowUpScheduler()
        )
        self.sentiment = (
            PeopleSentimentTracker()
        )
        self.network = NetworkMapper()
        self.birthdays = BirthdayReminder()
        self.advisor = (
            RelationshipAdvisor()
        )
        self._stats = {
            "contacts_managed": 0,
            "full_cycles": 0,
        }

        logger.info(
            "PeopleMgrOrchestrator "
            "baslatildi",
        )

    def onboard_contact(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        category: str = "other",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kişi ekler (tam onboard).

        Args:
            name: İsim.
            email: E-posta.
            phone: Telefon.
            company: Şirket.
            category: Kategori.
            tags: Etiketler.

        Returns:
            Onboard bilgisi.
        """
        # Profil oluştur
        result = self.profiler.create_profile(
            name=name,
            email=email,
            phone=phone,
            company=company,
            category=category,
            tags=tags,
        )
        cid = result["contact_id"]

        # Ağa ekle
        self.network.add_node(
            cid, name=name,
        )

        # İlk etkileşim kaydet
        self.interactions.log_interaction(
            contact_id=cid,
            channel="onboarding",
            content=f"Contact added: {name}",
        )

        self._stats[
            "contacts_managed"
        ] += 1

        return {
            "contact_id": cid,
            "name": name,
            "category": category,
            "onboarded": True,
        }

    def run_relationship_cycle(
        self,
        contact_id: str,
        interaction_count: int = 0,
        last_contact_days: float = 30.0,
        sentiment_score: float = 0.5,
    ) -> dict[str, Any]:
        """Profile → Track → Score → Advise → Act.

        Args:
            contact_id: Kişi ID.
            interaction_count: Etkileşim.
            last_contact_days: Son temas.
            sentiment_score: Duygu puanı.

        Returns:
            Döngü sonucu.
        """
        # 1. Score
        score_result = (
            self.scorer.calculate_strength(
                contact_id=contact_id,
                interaction_count=(
                    interaction_count
                ),
                recency_days=(
                    last_contact_days
                ),
                sentiment_avg=(
                    sentiment_score
                ),
            )
        )

        # 2. Sentiment
        self.sentiment.analyze_sentiment(
            contact_id=contact_id,
            score=sentiment_score,
        )

        # 3. Health assessment
        health = (
            self.advisor.assess_health(
                contact_id=contact_id,
                score=score_result[
                    "score"
                ],
                last_contact_days=(
                    last_contact_days
                ),
                sentiment_avg=(
                    sentiment_score
                ),
                interaction_count=(
                    interaction_count
                ),
            )
        )

        # 4. Advise
        actions = (
            self.advisor.suggest_actions(
                contact_id=contact_id,
                health_status=health[
                    "status"
                ],
            )
        )

        # 5. Auto-schedule if needed
        followup = None
        if health["status"] != "healthy":
            followup = (
                self.followups
                .auto_schedule(
                    contact_id=contact_id,
                    relationship_score=(
                        score_result["score"]
                    ),
                    last_contact_days=(
                        last_contact_days
                    ),
                )
            )

        self._stats["full_cycles"] += 1

        return {
            "contact_id": contact_id,
            "score": score_result["score"],
            "strength": score_result[
                "strength"
            ],
            "health": health["status"],
            "actions_count": actions[
                "count"
            ],
            "followup_scheduled": (
                followup is not None
            ),
            "cycle_complete": True,
        }

    def get_network_intelligence(
        self,
    ) -> dict[str, Any]:
        """Ağ zekası döndürür.

        Returns:
            Ağ bilgisi.
        """
        viz = (
            self.network
            .get_visualization_data()
        )
        communities = (
            self.network
            .detect_communities()
        )

        return {
            "total_contacts": (
                self.profiler.contact_count
            ),
            "network_nodes": viz[
                "node_count"
            ],
            "network_edges": viz[
                "edge_count"
            ],
            "communities": communities[
                "count"
            ],
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "contacts_managed": (
                self._stats[
                    "contacts_managed"
                ]
            ),
            "full_cycles": (
                self._stats["full_cycles"]
            ),
            "total_contacts": (
                self.profiler.contact_count
            ),
            "total_interactions": (
                self.interactions
                .interaction_count
            ),
            "scores_calculated": (
                self.scorer.scored_count
            ),
            "pending_followups": (
                self.followups.pending_count
            ),
            "sentiments_analyzed": (
                self.sentiment
                .analyzed_count
            ),
            "birthdays_tracked": (
                self.birthdays.tracked_count
            ),
            "health_checks": (
                self.advisor
                .health_check_count
            ),
            "network_nodes": (
                self.network.node_count
            ),
        }

    @property
    def contact_count(self) -> int:
        """Kişi sayısı."""
        return self.profiler.contact_count

    @property
    def cycle_count(self) -> int:
        """Döngü sayısı."""
        return self._stats[
            "full_cycles"
        ]
