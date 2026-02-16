"""ATLAS Yatırımcı Bulucu.

Yatırımcı keşfi, tez eşleme,
portföy analizi ve iletişim takibi.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class InvestorFinder:
    """Yatırımcı bulucu.

    Yatırımcıları keşfeder, tez eşleme yapar
    ve iletişim takibi yönetir.

    Attributes:
        _investors: Yatırımcı kayıtları.
        _outreach: İletişim kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Bulucuyu başlatır."""
        self._investors: dict[str, dict] = {}
        self._outreach: dict[str, dict] = {}
        self._stats = {
            "investors_found": 0,
            "outreach_sent": 0,
        }
        logger.info(
            "InvestorFinder baslatildi",
        )

    @property
    def found_count(self) -> int:
        """Bulunan yatırımcı sayısı."""
        return self._stats[
            "investors_found"
        ]

    @property
    def outreach_count(self) -> int:
        """Gönderilen iletişim sayısı."""
        return self._stats["outreach_sent"]

    def discover_investors(
        self,
        industry: str = "",
        investor_type: str = "vc",
        stage: str = "seed",
    ) -> dict[str, Any]:
        """Yatırımcı keşfeder.

        Args:
            industry: Sektör filtresi.
            investor_type: Yatırımcı tipi.
            stage: Yatırım aşaması.

        Returns:
            Keşif bilgisi.
        """
        inv_id = (
            f"inv_{len(self._investors)}"
        )
        self._investors[inv_id] = {
            "industry": industry,
            "investor_type": investor_type,
            "stage": stage,
        }
        self._stats[
            "investors_found"
        ] += 1

        logger.info(
            "Yatirimci bulundu: %s (%s, %s)",
            inv_id,
            investor_type,
            industry or "all",
        )

        return {
            "investor_id": inv_id,
            "investor_type": investor_type,
            "stage": stage,
            "discovered": True,
        }

    def match_thesis(
        self,
        investor_id: str,
        thesis_keywords: list[str]
        | None = None,
        company_keywords: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Yatırım tezi eşlemesi yapar.

        Args:
            investor_id: Yatırımcı kimliği.
            thesis_keywords: Tez anahtar kelimeler.
            company_keywords: Şirket anahtar kelimeler.

        Returns:
            Eşleme bilgisi.
        """
        if thesis_keywords is None:
            thesis_keywords = []
        if company_keywords is None:
            company_keywords = []

        t_set = set(thesis_keywords)
        c_set = set(company_keywords)
        overlap = t_set & c_set
        match_score = (
            len(overlap) / len(t_set)
            if t_set
            else 0.0
        )

        return {
            "investor_id": investor_id,
            "overlap": list(overlap),
            "match_score": round(
                match_score, 2,
            ),
            "matched": True,
        }

    def analyze_portfolio(
        self,
        investor_id: str,
        portfolio_companies: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Portföy analizi yapar.

        Args:
            investor_id: Yatırımcı kimliği.
            portfolio_companies: Portföy şirketleri.

        Returns:
            Portföy bilgisi.
        """
        if portfolio_companies is None:
            portfolio_companies = []

        size = len(portfolio_companies)
        activity = (
            "very_active"
            if size > 20
            else "active"
            if size > 10
            else "moderate"
            if size > 5
            else "selective"
        )

        return {
            "investor_id": investor_id,
            "portfolio_size": size,
            "activity_level": activity,
            "analyzed": True,
        }

    def find_warm_paths(
        self,
        investor_id: str,
        network: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sıcak bağlantı yolları bulur.

        Args:
            investor_id: Yatırımcı kimliği.
            network: Mevcut ağ.

        Returns:
            Yol bilgisi.
        """
        if network is None:
            network = []

        paths = min(len(network), 3)

        return {
            "investor_id": investor_id,
            "paths_found": paths,
            "network_size": len(network),
            "searched": True,
        }

    def track_outreach(
        self,
        investor_id: str,
        status: str = "sent",
        channel: str = "email",
    ) -> dict[str, Any]:
        """İletişim takibi yapar.

        Args:
            investor_id: Yatırımcı kimliği.
            status: İletişim durumu.
            channel: İletişim kanalı.

        Returns:
            Takip bilgisi.
        """
        self._outreach[investor_id] = {
            "status": status,
            "channel": channel,
        }
        self._stats["outreach_sent"] += 1

        return {
            "investor_id": investor_id,
            "status": status,
            "channel": channel,
            "tracked": True,
        }
