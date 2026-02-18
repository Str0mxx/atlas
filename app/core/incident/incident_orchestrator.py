"""
Olay mudahale orkestratoru modulu.

Tam olay mudahale yasam dongusu:
Tespit -> Cevreleme -> Arastirma ->
Kurtarma -> Ders cikarma.
7/24 mudahale, analitik.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from .auto_containment import (
    AutoContainment,
)
from .forensic_collector import (
    ForensicCollector,
)
from .incident_detector import (
    IncidentDetector,
)
from .incident_impact_assessor import (
    IncidentImpactAssessor,
)
from .incident_lesson_learner import (
    IncidentLessonLearner,
)
from .incident_root_cause_analyzer import (
    IncidentRootCauseAnalyzer,
)
from .playbook_generator import (
    PlaybookGenerator,
)
from .recovery_executor import (
    RecoveryExecutor,
)

logger = logging.getLogger(__name__)


class IncidentOrchestrator:
    """Olay mudahale orkestratoru.

    Attributes:
        detector: Olay tespitcisi.
        containment: Otomatik cevreleme.
        forensic: Adli toplayici.
        root_cause: Kok neden analizcisi.
        impact: Etki degerlendirici.
        recovery: Kurtarma yurutucusu.
        lessons: Ders cikarma.
        playbook: Playbook uretici.
    """

    def __init__(
        self,
        auto_contain: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            auto_contain: Oto cevreleme.
        """
        self.detector = IncidentDetector()
        self.containment = (
            AutoContainment(
                auto_contain=auto_contain
            )
        )
        self.forensic = ForensicCollector()
        self.root_cause = (
            IncidentRootCauseAnalyzer()
        )
        self.impact = (
            IncidentImpactAssessor()
        )
        self.recovery = RecoveryExecutor()
        self.lessons = (
            IncidentLessonLearner()
        )
        self.playbook = PlaybookGenerator()
        logger.info(
            "IncidentOrchestrator "
            "baslatildi"
        )

    def respond_to_incident(
        self,
        title: str = "",
        incident_type: str = "malware",
        severity: str = "high",
        source: str = "",
        description: str = "",
        indicators: (
            list[str] | None
        ) = None,
        affected_systems: (
            list[str] | None
        ) = None,
        auto_contain_actions: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Olaya tam mudahale eder.

        Detect -> Contain -> Investigate
        pipeline.

        Args:
            title: Olay basligi.
            incident_type: Olay tipi.
            severity: Ciddiyet.
            source: Kaynak.
            description: Aciklama.
            indicators: Gostergeler.
            affected_systems: Etkilenenler.
            auto_contain_actions: Oto eylem.

        Returns:
            Mudahale bilgisi.
        """
        try:
            # 1. Tespit
            detect_r = (
                self.detector.detect_incident(
                    title=title,
                    incident_type=(
                        incident_type
                    ),
                    severity=severity,
                    source=source,
                    description=description,
                    indicators=indicators,
                    affected_systems=(
                        affected_systems
                    ),
                )
            )
            if not detect_r.get("detected"):
                return {
                    "responded": False,
                    "error": detect_r.get(
                        "error",
                        "Tespit basarisiz",
                    ),
                }

            iid = detect_r["incident_id"]
            results = {
                "incident_id": iid,
                "detection": detect_r,
            }

            # 2. Otomatik cevreleme
            if auto_contain_actions:
                contain_r = (
                    self.containment
                    .contain_incident(
                        incident_id=iid,
                        actions=(
                            auto_contain_actions
                        ),
                        targets=(
                            affected_systems
                            or []
                        ),
                        reason=(
                            f"Auto: {title}"
                        ),
                    )
                )
                results["containment"] = (
                    contain_r
                )

                # Durum guncelle
                self.detector.update_status(
                    incident_id=iid,
                    status="contained",
                )

            # 3. Etki degerlendirmesi
            impact_r = (
                self.impact.assess_impact(
                    incident_id=iid,
                    title=title,
                    impact_level=(
                        self._severity_to_impact(
                            severity
                        )
                    ),
                    description=description,
                )
            )
            results["impact"] = impact_r

            # 4. Kok neden analizi baslat
            rca_r = (
                self.root_cause
                .start_analysis(
                    incident_id=iid,
                    title=(
                        f"RCA: {title}"
                    ),
                    description=description,
                )
            )
            results["root_cause"] = rca_r

            # Durum guncelle
            self.detector.update_status(
                incident_id=iid,
                status="investigating",
            )

            results["responded"] = True
            return results

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "responded": False,
                "error": str(e),
            }

    def _severity_to_impact(
        self,
        severity: str,
    ) -> str:
        """Ciddiyet -> Etki donusumu."""
        mapping = {
            "critical": "catastrophic",
            "high": "severe",
            "medium": "moderate",
            "low": "minor",
            "info": "negligible",
        }
        return mapping.get(
            severity, "moderate"
        )

    def recover_incident(
        self,
        incident_id: str = "",
        title: str = "",
        recovery_steps: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Olayi kurtarir.

        Args:
            incident_id: Olay ID.
            title: Baslik.
            recovery_steps: Adimlar.

        Returns:
            Kurtarma bilgisi.
        """
        try:
            # Kurtarma plani olustur
            plan_r = (
                self.recovery.create_plan(
                    incident_id=incident_id,
                    title=title,
                    steps=recovery_steps,
                )
            )
            if not plan_r.get("created"):
                return {
                    "recovered": False,
                    "error": plan_r.get(
                        "error"
                    ),
                }

            pid = plan_r["plan_id"]

            # Her adimi yurutulur
            actions = []
            for step in (
                recovery_steps or []
            ):
                r = (
                    self.recovery
                    .execute_recovery(
                        plan_id=pid,
                        recovery_type=(
                            step.get(
                                "type",
                                "service_restore",
                            )
                        ),
                        target=step.get(
                            "target", ""
                        ),
                        parameters=step.get(
                            "params"
                        ),
                    )
                )
                actions.append(r)

            # Plani tamamla
            self.recovery.complete_plan(
                plan_id=pid
            )

            # Durum guncelle
            self.detector.update_status(
                incident_id=incident_id,
                status="recovering",
            )

            return {
                "incident_id": incident_id,
                "plan_id": pid,
                "actions": len(actions),
                "recovered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recovered": False,
                "error": str(e),
            }

    def close_incident(
        self,
        incident_id: str = "",
        lesson_title: str = "",
        lesson_category: str = "process",
        what_went_well: str = "",
        what_went_wrong: str = "",
        recommendations: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Olayi kapatir ve ders cikarir.

        Args:
            incident_id: Olay ID.
            lesson_title: Ders basligi.
            lesson_category: Kategori.
            what_went_well: Iyi giden.
            what_went_wrong: Kotu giden.
            recommendations: Oneriler.

        Returns:
            Kapatma bilgisi.
        """
        try:
            # Ders kaydet
            lesson_r = (
                self.lessons.record_lesson(
                    incident_id=incident_id,
                    title=lesson_title,
                    category=(
                        lesson_category
                    ),
                    what_went_well=(
                        what_went_well
                    ),
                    what_went_wrong=(
                        what_went_wrong
                    ),
                    recommendations=(
                        recommendations
                    ),
                )
            )

            # Olayi kapat
            self.detector.update_status(
                incident_id=incident_id,
                status="closed",
            )

            return {
                "incident_id": incident_id,
                "lesson": lesson_r,
                "closed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "closed": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir."""
        try:
            det_s = (
                self.detector.get_summary()
            )
            cont_s = (
                self.containment
                .get_summary()
            )
            for_s = (
                self.forensic.get_summary()
            )
            rca_s = (
                self.root_cause.get_summary()
            )
            imp_s = (
                self.impact.get_summary()
            )
            rec_s = (
                self.recovery.get_summary()
            )
            les_s = (
                self.lessons.get_summary()
            )
            pb_s = (
                self.playbook.get_summary()
            )

            return {
                "detection": det_s,
                "containment": cont_s,
                "forensics": for_s,
                "root_cause": rca_s,
                "impact": imp_s,
                "recovery": rec_s,
                "lessons": les_s,
                "playbook": pb_s,
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
            det_s = (
                self.detector.get_summary()
            )
            return {
                "total_incidents": (
                    det_s.get(
                        "total_incidents", 0
                    )
                ),
                "active_incidents": (
                    det_s.get(
                        "active_incidents",
                        0,
                    )
                ),
                "active_quarantines": (
                    self.containment
                    .active_quarantines
                ),
                "evidence_count": (
                    self.forensic
                    .evidence_count
                ),
                "analyses": (
                    self.root_cause
                    .analysis_count
                ),
                "active_plans": (
                    self.recovery
                    .active_plans
                ),
                "lessons_learned": (
                    self.lessons
                    .lesson_count
                ),
                "playbooks": (
                    self.playbook
                    .playbook_count
                ),
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
