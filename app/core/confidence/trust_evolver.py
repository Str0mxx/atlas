"""ATLAS Guven Evrimcisi modulu.

Zamanla guven kazanma, basarisizlikta guven kaybetme,
alana ozel guven, guven azalmasi, guven kurtarma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TrustEvolver:
    """Guven evrimcisi.

    Zamanla guven seviyelerini evrimlestirir.

    Attributes:
        _trust: Guven kayitlari.
        _history: Guven gecmisi.
    """

    def __init__(
        self,
        decay_rate: float = 0.01,
        recovery_rate: float = 0.05,
        initial_trust: float = 0.5,
    ) -> None:
        """Guven evrimcisini baslatir.

        Args:
            decay_rate: Azalma orani.
            recovery_rate: Kurtarma orani.
            initial_trust: Baslangic guveni.
        """
        self._trust: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._decay_rate = decay_rate
        self._recovery_rate = recovery_rate
        self._initial_trust = initial_trust
        self._stats = {
            "successes": 0,
            "failures": 0,
            "decays": 0,
        }

        logger.info(
            "TrustEvolver baslatildi",
        )

    def get_trust(
        self,
        domain: str,
    ) -> dict[str, Any]:
        """Guven bilgisini getirir.

        Args:
            domain: Alan.

        Returns:
            Guven bilgisi.
        """
        if domain not in self._trust:
            self._trust[domain] = {
                "domain": domain,
                "score": self._initial_trust,
                "level": self._score_to_level(
                    self._initial_trust,
                ),
                "successes": 0,
                "failures": 0,
                "last_updated": time.time(),
            }
        return dict(self._trust[domain])

    def record_success(
        self,
        domain: str,
        magnitude: float = 0.1,
    ) -> dict[str, Any]:
        """Basari kaydeder (guven artar).

        Args:
            domain: Alan.
            magnitude: Artis buyuklugu.

        Returns:
            Guncelleme bilgisi.
        """
        trust = self.get_trust(domain)
        old = trust["score"]

        new_score = min(
            1.0, old + magnitude,
        )

        self._trust[domain]["score"] = new_score
        self._trust[domain]["level"] = (
            self._score_to_level(new_score)
        )
        self._trust[domain]["successes"] += 1
        self._trust[domain]["last_updated"] = (
            time.time()
        )

        self._stats["successes"] += 1
        self._history.append({
            "domain": domain,
            "event": "success",
            "old_score": old,
            "new_score": new_score,
            "timestamp": time.time(),
        })

        return {
            "domain": domain,
            "old_score": round(old, 4),
            "new_score": round(new_score, 4),
            "level": self._trust[domain]["level"],
        }

    def record_failure(
        self,
        domain: str,
        magnitude: float = 0.2,
    ) -> dict[str, Any]:
        """Basarisizlik kaydeder (guven azalir).

        Args:
            domain: Alan.
            magnitude: Azalma buyuklugu.

        Returns:
            Guncelleme bilgisi.
        """
        trust = self.get_trust(domain)
        old = trust["score"]

        new_score = max(
            0.0, old - magnitude,
        )

        self._trust[domain]["score"] = new_score
        self._trust[domain]["level"] = (
            self._score_to_level(new_score)
        )
        self._trust[domain]["failures"] += 1
        self._trust[domain]["last_updated"] = (
            time.time()
        )

        self._stats["failures"] += 1
        self._history.append({
            "domain": domain,
            "event": "failure",
            "old_score": old,
            "new_score": new_score,
            "timestamp": time.time(),
        })

        return {
            "domain": domain,
            "old_score": round(old, 4),
            "new_score": round(new_score, 4),
            "level": self._trust[domain]["level"],
        }

    def apply_decay(
        self,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Guven azalmasi uygular.

        Args:
            domain: Alan (None = tumu).

        Returns:
            Azalma sonuclari.
        """
        results = []
        domains = (
            [domain] if domain
            else list(self._trust.keys())
        )

        for d in domains:
            if d not in self._trust:
                continue
            trust = self._trust[d]
            old = trust["score"]
            new_score = max(
                0.0,
                old - self._decay_rate,
            )

            if new_score != old:
                trust["score"] = new_score
                trust["level"] = (
                    self._score_to_level(new_score)
                )
                trust["last_updated"] = time.time()
                self._stats["decays"] += 1

                results.append({
                    "domain": d,
                    "old_score": round(old, 4),
                    "new_score": round(
                        new_score, 4,
                    ),
                })

        return results

    def recover_trust(
        self,
        domain: str,
        amount: float | None = None,
    ) -> dict[str, Any]:
        """Guven kurtarir.

        Args:
            domain: Alan.
            amount: Kurtarma miktari.

        Returns:
            Kurtarma bilgisi.
        """
        trust = self.get_trust(domain)
        old = trust["score"]
        recovery = amount or self._recovery_rate

        new_score = min(1.0, old + recovery)
        self._trust[domain]["score"] = new_score
        self._trust[domain]["level"] = (
            self._score_to_level(new_score)
        )
        self._trust[domain]["last_updated"] = (
            time.time()
        )

        return {
            "domain": domain,
            "old_score": round(old, 4),
            "new_score": round(new_score, 4),
            "recovered": round(
                new_score - old, 4,
            ),
        }

    def get_all_trust(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Tum guven bilgilerini getirir.

        Returns:
            Guven haritasi.
        """
        return {
            d: dict(t)
            for d, t in self._trust.items()
        }

    def get_history(
        self,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Guven gecmisini getirir.

        Args:
            domain: Alan filtresi.
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        history = self._history
        if domain:
            history = [
                h for h in history
                if h["domain"] == domain
            ]
        return list(history[-limit:])

    def _score_to_level(
        self,
        score: float,
    ) -> str:
        """Puani seviyeye cevirir.

        Args:
            score: Puan.

        Returns:
            Seviye.
        """
        if score >= 0.9:
            return "full"
        if score >= 0.7:
            return "high"
        if score >= 0.4:
            return "moderate"
        if score >= 0.2:
            return "limited"
        return "none"

    @property
    def domain_count(self) -> int:
        """Alan sayisi."""
        return len(self._trust)

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)
