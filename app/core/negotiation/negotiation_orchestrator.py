"""ATLAS Müzakere Orkestratörü modülü.

Tam müzakere pipeline'ı,
Plan → Offer → Analyze → Counter → Close,
çoklu taraf desteği, analitik.
"""

import logging
from typing import Any

from app.core.negotiation.communication_manager import (
    NegotiationCommunicationManager,
)
from app.core.negotiation.concession_tracker import (
    ConcessionTracker,
)
from app.core.negotiation.counter_offer_analyzer import (
    CounterOfferAnalyzer,
)
from app.core.negotiation.deal_scorer import (
    DealScorer,
)
from app.core.negotiation.negotiation_memory import (
    NegotiationMemory,
)
from app.core.negotiation.negotiation_strategy_planner import (
    NegotiationStrategyPlanner,
)
from app.core.negotiation.offer_generator import (
    OfferGenerator,
)
from app.core.negotiation.win_win_optimizer import (
    WinWinOptimizer,
)

logger = logging.getLogger(__name__)


class NegotiationOrchestrator:
    """Müzakere orkestratörü.

    Tüm müzakere bileşenlerini koordine eder.

    Attributes:
        strategy: Strateji planlayıcı.
        offers: Teklif üretici.
        counter: Karşı teklif analizcisi.
        concessions: Taviz takipçisi.
        optimizer: Kazan-kazan optimizasyonu.
        scorer: Anlaşma puanlayıcı.
        memory: Müzakere hafızası.
        comms: İletişim yöneticisi.
    """

    def __init__(
        self,
        currency: str = "TRY",
        min_acceptable_score: float = 60.0,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            currency: Para birimi.
            min_acceptable_score: Minimum puan.
        """
        self.strategy = (
            NegotiationStrategyPlanner()
        )
        self.offers = OfferGenerator(
            currency=currency,
        )
        self.counter = CounterOfferAnalyzer()
        self.concessions = (
            ConcessionTracker()
        )
        self.optimizer = WinWinOptimizer()
        self.scorer = DealScorer(
            min_acceptable=(
                min_acceptable_score
            ),
        )
        self.memory = NegotiationMemory()
        self.comms = (
            NegotiationCommunicationManager()
        )

        self._currency = currency
        self._active: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "negotiations_started": 0,
            "negotiations_completed": 0,
            "deals_closed": 0,
        }

        logger.info(
            "NegotiationOrchestrator "
            "baslatildi",
        )

    def start_negotiation(
        self,
        parties: list[str],
        target_value: float,
        minimum_value: float,
        context: str = "",
        relationship: str = "neutral",
    ) -> dict[str, Any]:
        """Müzakere başlatır.

        Args:
            parties: Taraflar.
            target_value: Hedef değer.
            minimum_value: Minimum değer.
            context: Bağlam.
            relationship: İlişki durumu.

        Returns:
            Müzakere bilgisi.
        """
        self._counter += 1
        nid = f"neg_{self._counter}"

        # Strateji seç
        strat = self.strategy.select_strategy(
            context=context,
            relationship=relationship,
        )

        # Hedef belirle
        goals = self.strategy.set_goals(
            negotiation_id=nid,
            target=target_value,
            minimum=minimum_value,
        )

        # İlk teklif üret
        offer = (
            self.offers.generate_initial_offer(
                target_value=target_value,
                strategy=strat["strategy"],
            )
        )

        # Aktif müzakereye ekle
        self._active[nid] = {
            "negotiation_id": nid,
            "parties": parties,
            "phase": "opening",
            "strategy": strat["strategy"],
            "target": target_value,
            "minimum": minimum_value,
            "current_offer": offer[
                "amount"
            ],
            "rounds": 0,
        }

        # Hafızaya kaydet
        self.memory.store_negotiation(
            negotiation_id=nid,
            parties=parties,
            strategy=strat["strategy"],
        )

        self._stats[
            "negotiations_started"
        ] += 1

        return {
            "negotiation_id": nid,
            "strategy": strat["strategy"],
            "initial_offer": offer["amount"],
            "target": target_value,
            "minimum": minimum_value,
            "phase": "opening",
            "started": True,
        }

    def process_counter_offer(
        self,
        negotiation_id: str,
        counter_amount: float,
        counter_party: str = "",
        terms: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Karşı teklif işler.

        Args:
            negotiation_id: Müzakere ID.
            counter_amount: Karşı tutar.
            counter_party: Karşı taraf.
            terms: Koşullar.

        Returns:
            İşleme bilgisi.
        """
        if (
            negotiation_id
            not in self._active
        ):
            return {
                "negotiation_id": (
                    negotiation_id
                ),
                "found": False,
            }

        neg = self._active[negotiation_id]
        neg["rounds"] += 1
        neg["phase"] = "bargaining"

        # Teklifi analiz et
        assessment = (
            self.counter.assess_value(
                offer_amount=counter_amount,
                our_target=neg["target"],
                our_minimum=neg["minimum"],
            )
        )

        # Fark analizi
        gap = self.counter.analyze_gap(
            our_position=neg[
                "current_offer"
            ],
            their_position=counter_amount,
        )

        # Taviz kaydet
        if counter_party:
            self.concessions.record_concession(
                party=counter_party,
                original=neg[
                    "current_offer"
                ],
                conceded=counter_amount,
            )

        # Yanıt öner
        response = (
            self.counter.recommend_response(
                offer_amount=counter_amount,
                our_target=neg["target"],
                our_minimum=neg["minimum"],
                gap_percent=gap[
                    "gap_percent"
                ],
            )
        )

        # Puanla
        score = self.scorer.evaluate_deal(
            deal_value=counter_amount,
            target_value=neg["target"],
        )

        return {
            "negotiation_id": (
                negotiation_id
            ),
            "counter_amount": counter_amount,
            "assessment": assessment[
                "quality"
            ],
            "acceptable": assessment[
                "acceptable"
            ],
            "gap_percent": gap[
                "gap_percent"
            ],
            "recommended_action": response[
                "action"
            ],
            "suggested_amount": response[
                "suggested_amount"
            ],
            "deal_score": score["overall"],
            "round": neg["rounds"],
        }

    def close_deal(
        self,
        negotiation_id: str,
        final_value: float,
        outcome: str = "won",
    ) -> dict[str, Any]:
        """Anlaşma kapatır.

        Args:
            negotiation_id: Müzakere ID.
            final_value: Son değer.
            outcome: Sonuç.

        Returns:
            Kapanış bilgisi.
        """
        if (
            negotiation_id
            not in self._active
        ):
            return {
                "negotiation_id": (
                    negotiation_id
                ),
                "found": False,
            }

        neg = self._active[negotiation_id]
        neg["phase"] = "settled"

        # Son puanlama
        score = self.scorer.evaluate_deal(
            deal_value=final_value,
            target_value=neg["target"],
        )

        # Öneri
        recommendation = (
            self.scorer.recommend(
                overall_score=score[
                    "overall"
                ],
            )
        )

        # Hafıza güncelle
        self.memory.store_negotiation(
            negotiation_id=negotiation_id,
            parties=neg["parties"],
            outcome=outcome,
            strategy=neg["strategy"],
            final_value=final_value,
            rounds=neg["rounds"],
        )

        self._stats[
            "negotiations_completed"
        ] += 1
        if outcome == "won":
            self._stats[
                "deals_closed"
            ] += 1

        # Aktiften kaldır
        del self._active[negotiation_id]

        return {
            "negotiation_id": (
                negotiation_id
            ),
            "final_value": final_value,
            "outcome": outcome,
            "score": score["overall"],
            "rounds": neg["rounds"],
            "recommendation": (
                recommendation[
                    "recommendation"
                ]
            ),
            "closed": True,
        }

    def get_negotiation_status(
        self,
        negotiation_id: str,
    ) -> dict[str, Any]:
        """Müzakere durumu döndürür.

        Args:
            negotiation_id: Müzakere ID.

        Returns:
            Durum bilgisi.
        """
        if (
            negotiation_id
            in self._active
        ):
            neg = self._active[
                negotiation_id
            ]
            remaining = (
                self.concessions
                .get_remaining_room(
                    current_position=neg[
                        "current_offer"
                    ],
                    minimum=neg["minimum"],
                )
            )
            return {
                "negotiation_id": (
                    negotiation_id
                ),
                "phase": neg["phase"],
                "rounds": neg["rounds"],
                "current_offer": neg[
                    "current_offer"
                ],
                "remaining_room": remaining[
                    "remaining_percent"
                ],
                "active": True,
            }

        stored = self.memory.get_negotiation(
            negotiation_id,
        )
        if stored:
            return {
                "negotiation_id": (
                    negotiation_id
                ),
                "outcome": stored.get(
                    "outcome",
                ),
                "active": False,
            }

        return {
            "negotiation_id": (
                negotiation_id
            ),
            "found": False,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Analitik bilgisi.
        """
        return {
            "negotiations_started": (
                self._stats[
                    "negotiations_started"
                ]
            ),
            "negotiations_completed": (
                self._stats[
                    "negotiations_completed"
                ]
            ),
            "deals_closed": self._stats[
                "deals_closed"
            ],
            "active_negotiations": len(
                self._active,
            ),
            "strategies_used": (
                self.strategy.strategy_count
            ),
            "offers_generated": (
                self.offers.offer_count
            ),
            "concessions_tracked": (
                self.concessions
                .concession_count
            ),
            "deals_scored": (
                self.scorer.score_count
            ),
            "messages_sent": (
                self.comms.message_count
            ),
            "parties_profiled": (
                self.memory.profile_count
            ),
        }

    @property
    def active_count(self) -> int:
        """Aktif müzakere sayısı."""
        return len(self._active)

    @property
    def completed_count(self) -> int:
        """Tamamlanan müzakere sayısı."""
        return self._stats[
            "negotiations_completed"
        ]
