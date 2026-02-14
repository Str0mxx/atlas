"""ATLAS Hedef Takip Motoru modulu.

Tam otonom hedef yasam dongusu, coklu hedef
yonetimi, oncelik dengeleme, insan eskalasyonu
ve 7/24 operasyon.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.goal_pursuit import (
    AlignmentLevel,
    GoalDefinition,
    GoalPriority,
    GoalPursuitSnapshot,
    GoalState,
    InitiativeState,
    OpportunityType,
)

from app.core.goal_pursuit.goal_generator import GoalGenerator
from app.core.goal_pursuit.goal_selector import GoalSelector
from app.core.goal_pursuit.initiative_launcher import InitiativeLauncher
from app.core.goal_pursuit.learning_extractor import LearningExtractor
from app.core.goal_pursuit.proactive_scanner import ProactiveScanner
from app.core.goal_pursuit.progress_evaluator import ProgressEvaluator
from app.core.goal_pursuit.user_aligner import UserAligner
from app.core.goal_pursuit.value_estimator import ValueEstimator

logger = logging.getLogger(__name__)


class GoalPursuitEngine:
    """Hedef takip motoru.

    Tum hedef takip alt sistemlerini koordine eder,
    otonom hedef yasam dongusunu yonetir.

    Attributes:
        _generator: Hedef uretici.
        _estimator: Deger tahmincisi.
        _selector: Hedef secici.
        _launcher: Girisim baslatici.
        _evaluator: Ilerleme degerlendirici.
        _learner: Ogrenme cikarici.
        _scanner: Proaktif tarayici.
        _aligner: Kullanici hizalayici.
    """

    def __init__(
        self,
        max_autonomous_goals: int = 5,
        require_approval: bool = True,
        value_threshold: float = 0.3,
    ) -> None:
        """Motoru baslatir.

        Args:
            max_autonomous_goals: Maks otonom hedef.
            require_approval: Onay gerekli mi.
            value_threshold: Deger esigi.
        """
        self._generator = GoalGenerator()
        self._estimator = ValueEstimator()
        self._selector = GoalSelector()
        self._launcher = InitiativeLauncher()
        self._evaluator = ProgressEvaluator()
        self._learner = LearningExtractor()
        self._scanner = ProactiveScanner()
        self._aligner = UserAligner()

        self._max_autonomous_goals = max_autonomous_goals
        self._require_approval = require_approval
        self._value_threshold = value_threshold
        self._active_goals: dict[str, GoalDefinition] = {}
        self._escalations: list[dict[str, Any]] = []

        logger.info(
            "GoalPursuitEngine baslatildi "
            "(max=%d, approval=%s, threshold=%.2f)",
            max_autonomous_goals, require_approval, value_threshold,
        )

    def discover_and_propose(
        self,
        opportunity_type: OpportunityType,
        title: str,
        description: str = "",
        estimated_value: float = 0.0,
        source: str = "",
    ) -> dict[str, Any]:
        """Firsat kesfeder ve hedef onerir.

        Args:
            opportunity_type: Firsat turu.
            title: Baslik.
            description: Aciklama.
            estimated_value: Tahmini deger.
            source: Kaynak.

        Returns:
            Kesif sonucu.
        """
        # 1. Firsat tespit
        candidate = self._generator.identify_opportunity(
            opportunity_type, title, description,
            estimated_value, source,
        )

        # 2. Fizibilite
        self._generator.check_feasibility(
            candidate.candidate_id, 0.7,
        )

        # 3. Hedef uret
        goal = self._generator.generate_goal(
            candidate.candidate_id,
        )
        if not goal:
            return {"success": False, "reason": "Hedef uretilemedi"}

        # 4. Deger tahmini
        self._estimator.estimate_benefit(
            goal.goal_id,
            revenue_impact=estimated_value * 0.5,
            strategic_value=estimated_value * 0.3,
            efficiency_gain=estimated_value * 0.2,
        )
        self._estimator.estimate_cost(
            goal.goal_id,
            direct_cost=estimated_value * 0.2,
            resource_cost=estimated_value * 0.1,
        )
        roi = self._estimator.calculate_roi(goal.goal_id)

        # 5. Selector'a ekle ve puanla
        self._selector.add_goal(goal)
        self._selector.score_goal(
            goal.goal_id,
            value_score=min(1.0, estimated_value / 10000),
            feasibility_score=candidate.feasibility,
            alignment_level=AlignmentLevel.NEUTRAL,
            strategic_fit=0.6,
        )

        # 6. Kullaniciya oner
        if self._require_approval:
            self._aligner.suggest_goal(
                goal.goal_id, title, description,
                rationale=f"ROI: {roi:.1%}",
                estimated_value=estimated_value,
            )

        return {
            "success": True,
            "goal_id": goal.goal_id,
            "candidate_id": candidate.candidate_id,
            "roi": roi,
            "needs_approval": self._require_approval,
        }

    def approve_and_launch(
        self,
        goal_id: str,
        resources: list[str] | None = None,
        milestones: list[str] | None = None,
        timeline_days: int = 30,
    ) -> dict[str, Any]:
        """Hedefi onaylar ve baslatir.

        Args:
            goal_id: Hedef ID.
            resources: Kaynaklar.
            milestones: Kilometre taslari.
            timeline_days: Zaman cizelgesi.

        Returns:
            Baslatma sonucu.
        """
        # Kapasite kontrolu
        if len(self._active_goals) >= self._max_autonomous_goals:
            return {
                "success": False,
                "reason": "Maks otonom hedef sayisina ulasildi",
            }

        # Hedefi bul
        goal = self._selector.get_goal(goal_id)
        if not goal:
            goal = self._generator.get_goal(goal_id)
        if not goal:
            return {"success": False, "reason": "Hedef bulunamadi"}

        # Onayla
        self._selector.add_goal(goal)
        self._selector.approve_goal(goal_id)
        self._aligner.approve_goal(goal_id)
        goal.state = GoalState.ACTIVE
        goal.started_at = datetime.now(timezone.utc)

        # Girisim olustur ve baslat
        initiative = self._launcher.create_initiative(
            goal,
            resources=resources,
            milestones=milestones,
            timeline_days=timeline_days,
        )
        launch_result = self._launcher.launch(initiative.initiative_id)

        # Ilerleme takibi baslat
        self._evaluator.track_progress(goal_id, 0.0)
        if milestones:
            step = 1.0 / len(milestones)
            for i, ms in enumerate(milestones):
                self._evaluator.add_milestone(
                    goal_id, ms, (i + 1) * step,
                )

        # Aktif hedeflere ekle
        self._active_goals[goal_id] = goal

        logger.info("Hedef onaylandi ve baslatildi: %s", goal.title)
        return {
            "success": True,
            "goal_id": goal_id,
            "initiative_id": initiative.initiative_id,
            "state": goal.state.value,
            "launch": launch_result,
        }

    def update_progress(
        self,
        goal_id: str,
        progress: float,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Hedef ilerlemesini gunceller.

        Args:
            goal_id: Hedef ID.
            progress: Ilerleme (0-1).
            details: Detaylar.

        Returns:
            Guncelleme sonucu.
        """
        result = self._evaluator.track_progress(
            goal_id, progress, details,
        )
        ms_result = self._evaluator.evaluate_milestones(goal_id)

        # Girisim ilerlemesini guncelle
        initiatives = self._launcher.get_by_goal(goal_id)
        for init in initiatives:
            self._launcher.update_progress(
                init.initiative_id, progress,
            )

        return {
            **result,
            "milestones": ms_result,
        }

    def evaluate_goal(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Hedefi degerlendirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Degerlendirme sonucu.
        """
        progress = self._evaluator.get_progress(goal_id)
        if not progress:
            return {"goal_id": goal_id, "status": "no_data"}

        current = progress.get("current", 0.0)
        abandon_check = self._evaluator.should_abandon(goal_id)
        ms_eval = self._evaluator.evaluate_milestones(goal_id)

        # Rota duzeltme gerekli mi
        needs_correction = current < 0.3 and ms_eval.get("reached", 0) == 0

        return {
            "goal_id": goal_id,
            "progress": current,
            "milestones": ms_eval,
            "abandon_recommended": abandon_check.get(
                "should_abandon", False,
            ),
            "needs_correction": needs_correction,
        }

    def complete_goal(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Hedefi tamamlar ve ogrenim cikarir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Tamamlama sonucu.
        """
        # Basari bildir
        success_result = self._evaluator.declare_success(goal_id)

        # Girisimleri tamamla
        initiatives = self._launcher.get_by_goal(goal_id)
        for init in initiatives:
            self._launcher.complete_initiative(init.initiative_id)

        # Ogrenme cikar
        goal = self._active_goals.get(goal_id)
        title = goal.title if goal else goal_id
        self._learner.extract_success_pattern(
            goal_id,
            title=f"Basari: {title}",
            description="Hedef basariyla tamamlandi",
            confidence=0.8,
        )

        # Aktif hedeflerden cikar
        if goal_id in self._active_goals:
            self._active_goals[goal_id].state = GoalState.COMPLETED
            self._active_goals[goal_id].completed_at = datetime.now(
                timezone.utc,
            )
            del self._active_goals[goal_id]

        logger.info("Hedef tamamlandi: %s", goal_id)
        return {
            "success": True,
            "goal_id": goal_id,
            **success_result,
        }

    def abandon_goal(
        self,
        goal_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Hedefi terk eder.

        Args:
            goal_id: Hedef ID.
            reason: Terk nedeni.

        Returns:
            Terk sonucu.
        """
        # Basarisizlik bildir
        self._evaluator.declare_failure(goal_id, reason)

        # Girisimleri iptal et
        initiatives = self._launcher.get_by_goal(goal_id)
        for init in initiatives:
            self._launcher.abort_initiative(
                init.initiative_id, reason,
            )

        # Basarisizlik analizi
        self._learner.analyze_failure(
            goal_id,
            title=f"Terk: {goal_id}",
            root_causes=[reason] if reason else ["Bilinmiyor"],
            lessons=["Gelecekte dikkat edilecek"],
        )

        # Aktif hedeflerden cikar
        if goal_id in self._active_goals:
            self._active_goals[goal_id].state = GoalState.ABANDONED
            del self._active_goals[goal_id]

        logger.info("Hedef terk edildi: %s (%s)", goal_id, reason)
        return {
            "success": True,
            "goal_id": goal_id,
            "reason": reason,
        }

    def escalate(
        self,
        goal_id: str,
        issue: str,
        severity: str = "high",
    ) -> dict[str, Any]:
        """Insana eskale eder.

        Args:
            goal_id: Hedef ID.
            issue: Sorun.
            severity: Ciddiyet.

        Returns:
            Eskalasyon sonucu.
        """
        escalation = {
            "goal_id": goal_id,
            "issue": issue,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        }
        self._escalations.append(escalation)

        # Rota duzeltme onerisi
        self._evaluator.suggest_correction(
            goal_id, issue,
            suggestion="Insan mudahalesi gerekli",
            severity=severity,
        )

        logger.info("Eskalasyon: %s - %s", goal_id, issue)
        return {
            "success": True,
            "escalation_index": len(self._escalations) - 1,
            **escalation,
        }

    def scan_and_discover(self) -> dict[str, Any]:
        """Proaktif tarama yapar ve firsatlari kesfeder.

        Returns:
            Tarama sonucu.
        """
        # Tarama yap
        scan_result = self._scanner.scan_environment("business")

        opportunities = []
        threats = []

        # Mevcut firsatlari topla
        for opp in self._scanner.get_opportunities():
            value = opp.get("value", 0)
            if value >= self._value_threshold:
                opportunities.append(opp)

        # Tehditleri topla
        for threat in self._scanner.get_threats(min_risk=0.3):
            threats.append(threat)

        return {
            "scan": scan_result,
            "opportunities": len(opportunities),
            "threats": len(threats),
            "high_value_opportunities": opportunities[:5],
        }

    def get_snapshot(self) -> GoalPursuitSnapshot:
        """Anlik goruntuyu getirir.

        Returns:
            GoalPursuitSnapshot nesnesi.
        """
        all_goals = {
            **{g.goal_id: g for g in self._selector.filter_by_state(
                GoalState.COMPLETED,
            )},
            **self._active_goals,
        }

        completed = sum(
            1 for g in all_goals.values()
            if g.state == GoalState.COMPLETED
        )
        abandoned = sum(
            1 for g in all_goals.values()
            if g.state == GoalState.ABANDONED
        )
        total = self._generator.total_goals
        success_rate = (
            completed / total if total > 0 else 0.0
        )

        # Ortalama ROI
        roi_values = []
        for gid in all_goals:
            est = self._estimator.get_estimate(gid)
            if est and est.roi_projection != 0:
                roi_values.append(est.roi_projection)
        avg_roi = (
            sum(roi_values) / len(roi_values) if roi_values else 0.0
        )

        return GoalPursuitSnapshot(
            total_goals=total,
            active_goals=len(self._active_goals),
            completed_goals=completed,
            abandoned_goals=abandoned,
            total_initiatives=self._launcher.total_initiatives,
            active_initiatives=self._launcher.active_count,
            total_learnings=self._learner.total_records,
            total_scans=self._scanner.total_scans,
            avg_roi=round(avg_roi, 4),
            success_rate=round(success_rate, 4),
        )

    # Alt sistem erisimi
    @property
    def generator(self) -> GoalGenerator:
        """Hedef uretici."""
        return self._generator

    @property
    def estimator(self) -> ValueEstimator:
        """Deger tahmincisi."""
        return self._estimator

    @property
    def selector(self) -> GoalSelector:
        """Hedef secici."""
        return self._selector

    @property
    def launcher(self) -> InitiativeLauncher:
        """Girisim baslatici."""
        return self._launcher

    @property
    def evaluator(self) -> ProgressEvaluator:
        """Ilerleme degerlendirici."""
        return self._evaluator

    @property
    def learner(self) -> LearningExtractor:
        """Ogrenme cikarici."""
        return self._learner

    @property
    def scanner(self) -> ProactiveScanner:
        """Proaktif tarayici."""
        return self._scanner

    @property
    def aligner(self) -> UserAligner:
        """Kullanici hizalayici."""
        return self._aligner

    @property
    def active_goal_count(self) -> int:
        """Aktif hedef sayisi."""
        return len(self._active_goals)

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayisi."""
        return len(self._escalations)
