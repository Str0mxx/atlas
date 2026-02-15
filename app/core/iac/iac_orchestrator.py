"""ATLAS IaC Orkestrator modulu.

Tam IaC pipeline, plan/apply is akisi,
durum yonetimi, izleme ve entegrasyon.
"""

import logging
import time
from typing import Any

from app.core.iac.compliance_checker import (
    IaCComplianceChecker,
)
from app.core.iac.drift_detector import (
    IaCDriftDetector,
)
from app.core.iac.module_manager import (
    ModuleManager,
)
from app.core.iac.plan_generator import (
    PlanGenerator,
)
from app.core.iac.resource_definer import (
    ResourceDefiner,
)
from app.core.iac.resource_provisioner import (
    ResourceProvisioner,
)
from app.core.iac.state_manager import (
    IaCStateManager,
)
from app.core.iac.template_engine import (
    IaCTemplateEngine,
)

logger = logging.getLogger(__name__)


class IaCOrchestrator:
    """IaC orkestrator.

    Tum IaC bilesenleri koordine eder.

    Attributes:
        definer: Kaynak tanimlayici.
        template_engine: Sablon motoru.
        state_manager: Durum yoneticisi.
        plan_generator: Plan uretici.
        provisioner: Kaynak saglayici.
        drift_detector: Kayma tespitcisi.
        module_manager: Modul yoneticisi.
        compliance_checker: Uyumluluk denetcisi.
    """

    def __init__(
        self,
        state_backend: str = "local",
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            state_backend: Durum arka ucu.
        """
        self.definer = ResourceDefiner()
        self.template_engine = (
            IaCTemplateEngine()
        )
        self.state_manager = IaCStateManager(
            backend=state_backend,
        )
        self.plan_generator = PlanGenerator()
        self.provisioner = ResourceProvisioner()
        self.drift_detector = IaCDriftDetector()
        self.module_manager = ModuleManager()
        self.compliance_checker = (
            IaCComplianceChecker()
        )

        self._pipelines: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "pipelines": 0,
            "applies": 0,
            "rollbacks": 0,
        }

        logger.info(
            "IaCOrchestrator baslatildi: %s",
            state_backend,
        )

    def define_and_plan(
        self,
        plan_id: str,
        resources: dict[
            str, dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Kaynak tanimla ve plan olustur.

        Args:
            plan_id: Plan ID.
            resources: Kaynaklar.

        Returns:
            Plan bilgisi.
        """
        # Kaynaklari tanimla
        for key, res_data in resources.items():
            parts = key.split(".")
            res_type = parts[0] if len(
                parts,
            ) > 1 else "resource"
            name = parts[-1]

            self.definer.define(
                resource_type=res_type,
                name=name,
                properties=res_data,
            )

        # Mevcut durumu al
        current: dict[str, dict[str, Any]] = {}
        for key in (
            self.state_manager.list_resources()
        ):
            state = (
                self.state_manager.get_resource(
                    key,
                )
            )
            if state:
                current[key] = state

        # Plan olustur
        plan = self.plan_generator.generate(
            plan_id=plan_id,
            desired=resources,
            current=current,
        )

        return plan

    def apply(
        self,
        plan_id: str,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        """Plani uygular.

        Args:
            plan_id: Plan ID.
            auto_approve: Otomatik onay.

        Returns:
            Uygulama sonucu.
        """
        plan = self.plan_generator.get_plan(
            plan_id,
        )
        if not plan:
            return {"error": "plan_not_found"}

        # Onay kontrolu
        if not auto_approve:
            if plan["status"] != "approved":
                return {
                    "error": "not_approved",
                    "status": plan["status"],
                }

        # Uyumluluk kontrolu
        compliance_issues: list[
            dict[str, Any]
        ] = []
        for change in plan["changes"]:
            if change["action"] == "create":
                result = (
                    self.compliance_checker.check(
                        change["resource"],
                        change.get(
                            "properties", {},
                        ),
                    )
                )
                if not result["compliant"]:
                    compliance_issues.extend(
                        result["violations"],
                    )

        if compliance_issues:
            return {
                "error": "compliance_failed",
                "issues": compliance_issues,
            }

        # Durumu kaydet (geri alma icin)
        self.state_manager.save_version(
            message=(
                f"Before apply: {plan_id}"
            ),
        )

        # Uygula
        result = (
            self.provisioner.apply_plan(
                plan["changes"],
            )
        )

        # Durumu guncelle
        for change in plan["changes"]:
            key = change["resource"]
            if change["action"] == "create":
                self.state_manager.set_resource(
                    key,
                    change.get(
                        "properties", {},
                    ),
                )
            elif change["action"] == "update":
                self.state_manager.set_resource(
                    key,
                    change.get("new", {}),
                )
            elif change["action"] == "delete":
                self.state_manager.remove_resource(
                    key,
                )

        # Baseline ayarla (drift icin)
        for change in plan["changes"]:
            if change["action"] in (
                "create",
                "update",
            ):
                key = change["resource"]
                props = change.get(
                    "properties",
                    change.get("new", {}),
                )
                self.drift_detector.set_baseline(
                    key, props,
                )

        self._stats["applies"] += 1

        return {
            "plan_id": plan_id,
            "applied": result["applied"],
            "errors": result["errors"],
            "total": result["total"],
        }

    def plan_and_apply(
        self,
        plan_id: str,
        resources: dict[
            str, dict[str, Any]
        ],
        auto_approve: bool = True,
    ) -> dict[str, Any]:
        """Plan olustur ve uygula.

        Args:
            plan_id: Plan ID.
            resources: Kaynaklar.
            auto_approve: Otomatik onay.

        Returns:
            Sonuc.
        """
        plan = self.define_and_plan(
            plan_id, resources,
        )

        if auto_approve:
            self.plan_generator.approve(
                plan_id, "auto",
            )

        return self.apply(
            plan_id, auto_approve,
        )

    def rollback(
        self,
        steps: int = 1,
    ) -> dict[str, Any]:
        """Geri alma yapar.

        Args:
            steps: Geri alinacak adim.

        Returns:
            Geri alma sonucu.
        """
        # Provisioner geri al
        prov_result = (
            self.provisioner.rollback(steps)
        )

        # Son durum surumune geri don
        if self.state_manager.version_count > 0:
            versions = (
                self.state_manager.get_versions()
            )
            if versions:
                last = versions[-1]
                self.state_manager.restore_version(
                    last["serial"],
                )

        self._stats["rollbacks"] += 1

        return {
            "rolled_back": (
                prov_result["rolled_back"]
            ),
            "state_restored": True,
        }

    def check_drift(
        self,
        actual_states: dict[
            str, dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Kayma kontrolu yapar.

        Args:
            actual_states: Gercek durumlar.

        Returns:
            Kayma raporu.
        """
        return self.drift_detector.check_all(
            actual_states,
        )

    def render_template(
        self,
        template: str,
        variables: dict[str, Any]
            | None = None,
    ) -> str:
        """Sablon render eder.

        Args:
            template: Sablon.
            variables: Degiskenler.

        Returns:
            Render sonucu.
        """
        return self.template_engine.render(
            template, variables,
        )

    def run_compliance(
        self,
        resources: dict[
            str, dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Uyumluluk denetimi yapar.

        Args:
            resources: Kaynaklar.

        Returns:
            Denetim sonucu.
        """
        return (
            self.compliance_checker.check_all(
                resources,
            )
        )

    def create_pipeline(
        self,
        pipeline_id: str,
        stages: list[str],
    ) -> dict[str, Any]:
        """Pipeline olusturur.

        Args:
            pipeline_id: Pipeline ID.
            stages: Asama listesi.

        Returns:
            Pipeline bilgisi.
        """
        self._pipelines[pipeline_id] = {
            "stages": stages,
            "status": "created",
            "current_stage": None,
            "results": {},
            "created_at": time.time(),
        }

        self._stats["pipelines"] += 1

        return {
            "pipeline_id": pipeline_id,
            "stages": len(stages),
        }

    def run_pipeline(
        self,
        pipeline_id: str,
        resources: dict[
            str, dict[str, Any]
        ],
        plan_id: str = "",
    ) -> dict[str, Any]:
        """Pipeline calistirir.

        Args:
            pipeline_id: Pipeline ID.
            resources: Kaynaklar.
            plan_id: Plan ID.

        Returns:
            Pipeline sonucu.
        """
        pipeline = self._pipelines.get(
            pipeline_id,
        )
        if not pipeline:
            return {
                "error": "pipeline_not_found",
            }

        pid = plan_id or pipeline_id
        results: dict[str, Any] = {}

        for stage in pipeline["stages"]:
            pipeline["current_stage"] = stage

            if stage == "validate":
                result = self.run_compliance(
                    resources,
                )
            elif stage == "plan":
                result = (
                    self.define_and_plan(
                        pid, resources,
                    )
                )
            elif stage == "approve":
                result = (
                    self.plan_generator.approve(
                        pid, "pipeline",
                    )
                )
            elif stage == "apply":
                result = self.apply(
                    pid, auto_approve=True,
                )
            elif stage == "verify":
                result = {"status": "verified"}
            else:
                result = {
                    "status": "skipped",
                    "stage": stage,
                }

            results[stage] = result

            # Hata varsa dur
            if isinstance(result, dict) and (
                "error" in result
            ):
                pipeline["status"] = "failed"
                pipeline["results"] = results
                return {
                    "pipeline_id": pipeline_id,
                    "status": "failed",
                    "failed_stage": stage,
                    "results": results,
                }

        pipeline["status"] = "completed"
        pipeline["results"] = results

        return {
            "pipeline_id": pipeline_id,
            "status": "completed",
            "results": results,
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "resources_defined": (
                self.definer.resource_count
            ),
            "state_resources": (
                self.state_manager.resource_count
            ),
            "state_versions": (
                self.state_manager.version_count
            ),
            "plans": (
                self.plan_generator.plan_count
            ),
            "provisioned": (
                self.provisioner.resource_count
            ),
            "drifts": (
                self.drift_detector.drift_count
            ),
            "modules": (
                self.module_manager.module_count
            ),
            "policies": (
                self.compliance_checker.policy_count
            ),
            "templates": (
                self.template_engine.template_count
            ),
            "pipelines": len(self._pipelines),
            "stats": dict(self._stats),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayisi."""
        return len(self._pipelines)

    @property
    def apply_count(self) -> int:
        """Uygulama sayisi."""
        return self._stats["applies"]

    @property
    def rollback_count(self) -> int:
        """Geri alma sayisi."""
        return self._stats["rollbacks"]
