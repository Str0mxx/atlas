"""ATLAS Yetenek Fabrikası Orkestratörü modülü.

Tam yetenek oluşturma pipeline'ı,
Analyze → Design → Build → Test → Deploy,
analitik ve raporlama.
"""

import logging
from typing import Any

from app.core.capfactory.auto_tester import (
    CapabilityAutoTester,
)
from app.core.capfactory.capability_registry import (
    RuntimeCapabilityRegistry,
)
from app.core.capfactory.need_analyzer import (
    NeedAnalyzer,
)
from app.core.capfactory.rapid_prototyper import (
    RapidPrototyper,
)
from app.core.capfactory.rollback_on_failure import (
    RollbackOnFailure,
)
from app.core.capfactory.safe_deployer import (
    SafeDeployer,
)
from app.core.capfactory.sandbox_environment import (
    SandboxEnvironment,
)
from app.core.capfactory.solution_architect import (
    SolutionArchitect,
)

logger = logging.getLogger(__name__)


class CapFactoryOrchestrator:
    """Yetenek fabrikası orkestratörü.

    Tüm yetenek oluşturma bileşenlerini koordine eder.

    Attributes:
        analyzer: İhtiyaç analizcisi.
        architect: Çözüm mimarı.
        prototyper: Hızlı prototipleyici.
        sandbox: Sandbox ortamı.
        tester: Otomatik testçi.
        deployer: Güvenli dağıtıcı.
        registry: Yetenek kayıt defteri.
        rollback: Geri alma yöneticisi.
    """

    def __init__(
        self,
        sandbox_timeout: int = 60,
        min_coverage: float = 80.0,
        auto_deploy: bool = False,
        rollback_on_failure: bool = True,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            sandbox_timeout: Sandbox zaman aşımı.
            min_coverage: Minimum test kapsamı.
            auto_deploy: Otomatik dağıtım.
            rollback_on_failure: Hatada geri al.
        """
        self.analyzer = NeedAnalyzer()
        self.architect = SolutionArchitect()
        self.prototyper = RapidPrototyper()
        self.sandbox = SandboxEnvironment(
            timeout_seconds=sandbox_timeout,
        )
        self.tester = CapabilityAutoTester(
            min_coverage=min_coverage,
        )
        self.deployer = SafeDeployer()
        self.registry = RuntimeCapabilityRegistry()
        self.rollback = RollbackOnFailure(
            auto_rollback=rollback_on_failure,
        )

        self._auto_deploy = auto_deploy
        self._stats = {
            "capabilities_created": 0,
            "pipeline_runs": 0,
            "successful_deployments": 0,
        }

        logger.info(
            "CapFactoryOrchestrator baslatildi",
        )

    def create_capability(
        self,
        request: str,
        name: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tam yetenek oluşturma pipeline'ı.

        Args:
            request: İstek metni.
            name: Yetenek adı.
            context: Bağlam.

        Returns:
            Pipeline sonucu.
        """
        self._stats["pipeline_runs"] += 1

        # 1) Analyze
        analysis = self.analyzer.analyze_request(
            request, context,
        )
        if not analysis.get("feasible"):
            return {
                "success": False,
                "stage": "analyze",
                "reason": "not_feasible",
                "analysis": analysis,
            }

        # 2) Design
        design = self.architect.design_architecture(
            analysis,
        )

        # 3) Build (Prototype)
        prototype = self.prototyper.create_prototype(
            design, name=name,
        )

        # 4) Sandbox Test
        sb = self.sandbox.create_sandbox(
            name=f"sb_{prototype['prototype_id']}",
        )
        for part in prototype.get(
            "code_parts", [],
        ):
            self.sandbox.execute(
                sb["sandbox_id"],
                part.get("code", ""),
            )

        # 5) Auto Test
        test_suite = self.tester.generate_tests(
            prototype,
        )
        test_result = self.tester.run_tests(
            test_suite["suite_id"],
        )

        # 6) Register
        cap_name = name or f"cap_{request[:20]}"
        reg = self.registry.register(
            name=cap_name,
            description=request,
            tags=analysis.get("keywords", [])[:5],
        )
        capability_id = reg["capability_id"]

        # 7) Deploy (if auto or tests pass)
        deployment = None
        if (
            self._auto_deploy
            and test_result.get("failed", 0) == 0
        ):
            # Checkpoint before deploy
            self.rollback.create_checkpoint(
                capability_id,
                {"stage": "pre_deploy"},
            )
            deployment = self.deployer.deploy(
                capability_id, stage="canary",
            )
            self._stats[
                "successful_deployments"
            ] += 1

        # Cleanup sandbox
        self.sandbox.cleanup(sb["sandbox_id"])

        self._stats["capabilities_created"] += 1

        return {
            "success": True,
            "capability_id": capability_id,
            "analysis": analysis,
            "design": design,
            "prototype": prototype,
            "test_result": test_result,
            "registration": reg,
            "deployment": deployment,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "capabilities_created": self._stats[
                "capabilities_created"
            ],
            "pipeline_runs": self._stats[
                "pipeline_runs"
            ],
            "successful_deployments": self._stats[
                "successful_deployments"
            ],
            "total_analyses": (
                self.analyzer.analysis_count
            ),
            "total_designs": (
                self.architect.design_count
            ),
            "total_prototypes": (
                self.prototyper.prototype_count
            ),
            "total_tests_run": (
                self.tester.total_tests_run
            ),
            "test_pass_rate": (
                self.tester.pass_rate
            ),
            "active_deployments": (
                self.deployer.active_deployment_count
            ),
            "registered_capabilities": (
                self.registry.registered_count
            ),
            "total_rollbacks": (
                self.rollback.rollback_count
            ),
            "active_sandboxes": (
                self.sandbox.active_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "capabilities_created": self._stats[
                "capabilities_created"
            ],
            "pipeline_runs": self._stats[
                "pipeline_runs"
            ],
            "active_deployments": (
                self.deployer.active_deployment_count
            ),
            "registered_capabilities": (
                self.registry.registered_count
            ),
        }

    @property
    def capabilities_created(self) -> int:
        """Oluşturulan yetenek sayısı."""
        return self._stats[
            "capabilities_created"
        ]
