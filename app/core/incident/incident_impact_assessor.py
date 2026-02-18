"""
Etki degerlendirici modulu.

Etki degerlendirme, veri ifsa,
sistem ele gecirme, is etkisi,
duzenleyici sonuclar.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class IncidentImpactAssessor:
    """Etki degerlendirici.

    Attributes:
        _assessments: Degerlendirmeler.
        _exposures: Veri ifsa kayitlari.
        _compromises: Ele gecirme kayit.
        _stats: Istatistikler.
    """

    IMPACT_LEVELS: list[str] = [
        "catastrophic",
        "severe",
        "major",
        "moderate",
        "minor",
        "negligible",
    ]

    IMPACT_CATEGORIES: list[str] = [
        "data_exposure",
        "system_compromise",
        "financial",
        "operational",
        "reputational",
        "regulatory",
        "legal",
        "safety",
    ]

    def __init__(self) -> None:
        """Degerlendiriciyi baslatir."""
        self._assessments: dict[
            str, dict
        ] = {}
        self._exposures: dict[
            str, dict
        ] = {}
        self._compromises: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "assessments_completed": 0,
            "data_exposures": 0,
            "systems_compromised": 0,
            "regulatory_impacts": 0,
        }
        logger.info(
            "IncidentImpactAssessor "
            "baslatildi"
        )

    @property
    def assessment_count(self) -> int:
        """Degerlendirme sayisi."""
        return len(self._assessments)

    def assess_impact(
        self,
        incident_id: str = "",
        title: str = "",
        impact_level: str = "moderate",
        categories: (
            list[str] | None
        ) = None,
        description: str = "",
        affected_users: int = 0,
        financial_impact: float = 0.0,
    ) -> dict[str, Any]:
        """Etki degerlendirmesi yapar.

        Args:
            incident_id: Olay ID.
            title: Baslik.
            impact_level: Etki seviyesi.
            categories: Etki kategorileri.
            description: Aciklama.
            affected_users: Etkilenenler.
            financial_impact: Mali etki.

        Returns:
            Degerlendirme bilgisi.
        """
        try:
            if (
                impact_level
                not in self.IMPACT_LEVELS
            ):
                return {
                    "assessed": False,
                    "error": (
                        f"Gecersiz: "
                        f"{impact_level}"
                    ),
                }

            aid = f"ia_{uuid4()!s:.8}"
            cat_list = categories or []
            score = self._calculate_score(
                impact_level,
                len(cat_list),
                affected_users,
                financial_impact,
            )

            self._assessments[aid] = {
                "assessment_id": aid,
                "incident_id": incident_id,
                "title": title,
                "impact_level": impact_level,
                "categories": cat_list,
                "description": description,
                "affected_users": (
                    affected_users
                ),
                "financial_impact": (
                    financial_impact
                ),
                "impact_score": score,
                "status": "assessed",
                "assessed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "assessments_completed"
            ] += 1

            return {
                "assessment_id": aid,
                "impact_level": impact_level,
                "impact_score": score,
                "assessed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def _calculate_score(
        self,
        level: str,
        cat_count: int,
        users: int,
        financial: float,
    ) -> float:
        """Etki puani hesaplar."""
        level_scores = {
            "catastrophic": 1.0,
            "severe": 0.85,
            "major": 0.7,
            "moderate": 0.5,
            "minor": 0.3,
            "negligible": 0.1,
        }
        base = level_scores.get(level, 0.5)

        # Kategori sayisi etkisi
        cat_factor = min(
            cat_count * 0.05, 0.2
        )

        # Kullanici sayisi etkisi
        user_factor = 0.0
        if users > 10000:
            user_factor = 0.15
        elif users > 1000:
            user_factor = 0.1
        elif users > 100:
            user_factor = 0.05

        # Mali etki
        fin_factor = 0.0
        if financial > 1000000:
            fin_factor = 0.15
        elif financial > 100000:
            fin_factor = 0.1
        elif financial > 10000:
            fin_factor = 0.05

        return min(
            1.0,
            round(
                base
                + cat_factor
                + user_factor
                + fin_factor,
                2,
            ),
        )

    def record_data_exposure(
        self,
        incident_id: str = "",
        data_type: str = "",
        record_count: int = 0,
        sensitivity: str = "medium",
        description: str = "",
    ) -> dict[str, Any]:
        """Veri ifsa kaydeder.

        Args:
            incident_id: Olay ID.
            data_type: Veri tipi.
            record_count: Kayit sayisi.
            sensitivity: Hassasiyet.
            description: Aciklama.

        Returns:
            Ifsa bilgisi.
        """
        try:
            eid = f"de_{uuid4()!s:.8}"
            self._exposures[eid] = {
                "exposure_id": eid,
                "incident_id": incident_id,
                "data_type": data_type,
                "record_count": record_count,
                "sensitivity": sensitivity,
                "description": description,
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "data_exposures"
            ] += 1

            return {
                "exposure_id": eid,
                "data_type": data_type,
                "record_count": record_count,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def record_system_compromise(
        self,
        incident_id: str = "",
        system: str = "",
        compromise_type: str = "",
        access_level: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Sistem ele gecirme kaydeder.

        Args:
            incident_id: Olay ID.
            system: Sistem.
            compromise_type: Tip.
            access_level: Erisim seviyesi.
            description: Aciklama.

        Returns:
            Ele gecirme bilgisi.
        """
        try:
            cid = f"sc_{uuid4()!s:.8}"
            self._compromises[cid] = {
                "compromise_id": cid,
                "incident_id": incident_id,
                "system": system,
                "compromise_type": (
                    compromise_type
                ),
                "access_level": access_level,
                "description": description,
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "systems_compromised"
            ] += 1

            return {
                "compromise_id": cid,
                "system": system,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def assess_regulatory_impact(
        self,
        incident_id: str = "",
        regulation: str = "",
        breach_type: str = "",
        notification_required: bool = False,
        deadline_hours: int = 72,
        potential_fine: float = 0.0,
    ) -> dict[str, Any]:
        """Duzenleyici etki degerlendirir.

        Args:
            incident_id: Olay ID.
            regulation: Duzenleme.
            breach_type: Ihlal tipi.
            notification_required: Bildirim.
            deadline_hours: Sure (saat).
            potential_fine: Potansiyel ceza.

        Returns:
            Duzenleyici bilgi.
        """
        try:
            rid = f"ri_{uuid4()!s:.8}"
            assessment = self._assessments

            # Olaya ait assessment bul
            for a in assessment.values():
                if (
                    a["incident_id"]
                    == incident_id
                ):
                    if "regulatory" not in (
                        a
                    ):
                        a["regulatory"] = []
                    a["regulatory"].append({
                        "reg_id": rid,
                        "regulation": (
                            regulation
                        ),
                        "breach_type": (
                            breach_type
                        ),
                        "notification": (
                            notification_required
                        ),
                        "deadline_hours": (
                            deadline_hours
                        ),
                        "potential_fine": (
                            potential_fine
                        ),
                    })
                    break

            self._stats[
                "regulatory_impacts"
            ] += 1

            return {
                "reg_id": rid,
                "regulation": regulation,
                "notification_required": (
                    notification_required
                ),
                "deadline_hours": (
                    deadline_hours
                ),
                "assessed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def get_business_impact(
        self,
        incident_id: str = "",
    ) -> dict[str, Any]:
        """Is etkisi getirir.

        Args:
            incident_id: Olay ID.

        Returns:
            Is etkisi bilgisi.
        """
        try:
            # Olaya ait bilgileri topla
            assessments = [
                a
                for a in (
                    self._assessments
                    .values()
                )
                if a["incident_id"]
                == incident_id
            ]
            exposures = [
                e
                for e in (
                    self._exposures.values()
                )
                if e["incident_id"]
                == incident_id
            ]
            compromises = [
                c
                for c in (
                    self._compromises
                    .values()
                )
                if c["incident_id"]
                == incident_id
            ]

            total_financial = sum(
                a["financial_impact"]
                for a in assessments
            )
            total_users = sum(
                a["affected_users"]
                for a in assessments
            )
            total_records = sum(
                e["record_count"]
                for e in exposures
            )

            return {
                "incident_id": incident_id,
                "assessments": len(
                    assessments
                ),
                "data_exposures": len(
                    exposures
                ),
                "systems_compromised": len(
                    compromises
                ),
                "total_financial": (
                    total_financial
                ),
                "total_users_affected": (
                    total_users
                ),
                "total_records_exposed": (
                    total_records
                ),
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
            by_level: dict[str, int] = {}
            for a in (
                self._assessments.values()
            ):
                lv = a["impact_level"]
                by_level[lv] = (
                    by_level.get(lv, 0) + 1
                )

            return {
                "total_assessments": len(
                    self._assessments
                ),
                "total_exposures": len(
                    self._exposures
                ),
                "total_compromises": len(
                    self._compromises
                ),
                "by_level": by_level,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
