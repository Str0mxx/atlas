"""
Korunan sinif izleyici modulu.

Korunan ozellikler, farkli muamele,
sonuc izleme, esitsizlik uyarilari,
yasal uyumluluk.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProtectedClassMonitor:
    """Korunan sinif izleyici.

    Attributes:
        _classes: Korunan siniflar.
        _observations: Gozlemler.
        _alerts: Uyarilar.
        _stats: Istatistikler.
    """

    PROTECTED_CATEGORIES: list[str] = [
        "race",
        "gender",
        "age",
        "religion",
        "disability",
        "nationality",
        "sexual_orientation",
        "marital_status",
    ]

    TREATMENT_TYPES: list[str] = [
        "equal",
        "favorable",
        "unfavorable",
        "unknown",
    ]

    def __init__(
        self,
        disparity_threshold: float = 0.2,
    ) -> None:
        """Izleyiciyi baslatir.

        Args:
            disparity_threshold: Esitsizlik.
        """
        self._disparity_threshold = (
            disparity_threshold
        )
        self._classes: dict[
            str, dict
        ] = {}
        self._observations: list[
            dict
        ] = []
        self._alerts: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "observations_logged": 0,
            "disparities_found": 0,
            "alerts_raised": 0,
            "classes_monitored": 0,
        }
        logger.info(
            "ProtectedClassMonitor "
            "baslatildi"
        )

    @property
    def observation_count(self) -> int:
        """Gozlem sayisi."""
        return len(self._observations)

    def register_class(
        self,
        category: str = "",
        values: list[str] | None = None,
        legal_framework: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Korunan sinif kaydeder.

        Args:
            category: Kategori.
            values: Degerler.
            legal_framework: Yasal cerceve.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            cid = f"pcls_{uuid4()!s:.8}"
            self._classes[cid] = {
                "class_id": cid,
                "category": category,
                "values": values or [],
                "legal_framework": (
                    legal_framework
                ),
                "metadata": metadata or {},
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "classes_monitored"
            ] += 1
            return {
                "class_id": cid,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def log_observation(
        self,
        protected_attr: str = "",
        protected_value: str = "",
        outcome: Any = None,
        treatment: str = "unknown",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Gozlem kaydeder.

        Args:
            protected_attr: Korunan ozellik.
            protected_value: Deger.
            outcome: Sonuc.
            treatment: Muamele.
            context: Baglam.

        Returns:
            Kayit bilgisi.
        """
        try:
            oid = f"obs_{uuid4()!s:.8}"
            self._observations.append({
                "observation_id": oid,
                "protected_attr": (
                    protected_attr
                ),
                "protected_value": (
                    protected_value
                ),
                "outcome": outcome,
                "treatment": treatment,
                "context": context or {},
                "logged_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })
            self._stats[
                "observations_logged"
            ] += 1
            return {
                "observation_id": oid,
                "logged": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def check_disparity(
        self,
        protected_attr: str = "",
        last_n: int = 100,
    ) -> dict[str, Any]:
        """Esitsizlik kontrolu yapar.

        Args:
            protected_attr: Korunan ozellik.
            last_n: Son N gozlem.

        Returns:
            Kontrol bilgisi.
        """
        try:
            obs = [
                o
                for o in self._observations[
                    -last_n:
                ]
                if o["protected_attr"]
                == protected_attr
            ]

            if not obs:
                return {
                    "has_disparity": False,
                    "observation_count": 0,
                    "checked": True,
                }

            # Gruplara ayir
            groups: dict[
                str, list
            ] = {}
            for o in obs:
                g = o["protected_value"]
                groups.setdefault(g, [])
                groups[g].append(o)

            if len(groups) < 2:
                return {
                    "has_disparity": False,
                    "groups": len(groups),
                    "checked": True,
                }

            # Pozitif sonuc oranlari
            rates: dict[
                str, float
            ] = {}
            for g, recs in groups.items():
                pos = sum(
                    1
                    for r in recs
                    if r.get("outcome")
                )
                rates[g] = (
                    pos / len(recs)
                    if recs
                    else 0
                )

            max_r = max(rates.values())
            min_r = min(rates.values())
            gap = max_r - min_r

            has_disparity = (
                gap
                > self._disparity_threshold
            )

            # Muamele analizi
            treatment_dist: dict[
                str, dict
            ] = {}
            for g, recs in groups.items():
                td: dict[str, int] = {}
                for r in recs:
                    t = r.get(
                        "treatment",
                        "unknown",
                    )
                    td[t] = td.get(t, 0) + 1
                treatment_dist[g] = td

            if has_disparity:
                self._stats[
                    "disparities_found"
                ] += 1

                # Uyari olustur
                alert_id = (
                    self._create_alert(
                        protected_attr,
                        gap,
                        rates,
                    )
                )
            else:
                alert_id = None

            return {
                "has_disparity": (
                    has_disparity
                ),
                "attribute": protected_attr,
                "outcome_rates": {
                    k: round(v, 4)
                    for k, v in rates.items()
                },
                "gap": round(gap, 4),
                "treatment_dist": (
                    treatment_dist
                ),
                "alert_id": alert_id,
                "observation_count": len(
                    obs
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _create_alert(
        self,
        attr: str,
        gap: float,
        rates: dict,
    ) -> str:
        """Uyari olusturur."""
        aid = f"palr_{uuid4()!s:.8}"
        self._alerts[aid] = {
            "alert_id": aid,
            "attribute": attr,
            "gap": round(gap, 4),
            "rates": rates,
            "severity": (
                "critical"
                if gap > 0.5
                else "high"
            ),
            "status": "open",
            "created_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }
        self._stats[
            "alerts_raised"
        ] += 1
        return aid

    def check_differential_treatment(
        self,
        protected_attr: str = "",
    ) -> dict[str, Any]:
        """Farkli muamele kontrolu.

        Args:
            protected_attr: Korunan ozellik.

        Returns:
            Kontrol bilgisi.
        """
        try:
            obs = [
                o
                for o in self._observations
                if o["protected_attr"]
                == protected_attr
            ]

            groups: dict[
                str, dict
            ] = {}
            for o in obs:
                g = o["protected_value"]
                if g not in groups:
                    groups[g] = {
                        "favorable": 0,
                        "unfavorable": 0,
                        "equal": 0,
                        "unknown": 0,
                        "total": 0,
                    }
                t = o.get(
                    "treatment", "unknown"
                )
                if t in groups[g]:
                    groups[g][t] += 1
                groups[g]["total"] += 1

            # Farkli muamele tespiti
            has_differential = False
            for g, counts in (
                groups.items()
            ):
                if counts["total"] > 0:
                    unfav_rate = (
                        counts["unfavorable"]
                        / counts["total"]
                    )
                    if unfav_rate > 0.3:
                        has_differential = (
                            True
                        )

            return {
                "has_differential": (
                    has_differential
                ),
                "groups": groups,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_open_alerts(
        self,
    ) -> dict[str, Any]:
        """Acik uyarilari getirir."""
        try:
            open_alerts = [
                a
                for a in (
                    self._alerts.values()
                )
                if a["status"] == "open"
            ]
            return {
                "alerts": open_alerts,
                "count": len(open_alerts),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "classes_monitored": len(
                    self._classes
                ),
                "total_observations": len(
                    self._observations
                ),
                "total_alerts": len(
                    self._alerts
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
