"""
Prompt engineering orkestrator modulu.

Tam prompt muhendisligi,
Create -> Optimize -> Test -> Deploy,
surekli iyilestirme, analitik.
"""

import logging
from typing import Any

from app.core.prompteng.ab_prompt_tester import (
    ABPromptTester,
)
from app.core.prompteng.chain_of_thought_builder import (
    ChainOfThoughtBuilder,
)
from app.core.prompteng.context_window_manager import (
    ContextWindowManager,
)
from app.core.prompteng.few_shot_selector import (
    FewShotSelector,
)
from app.core.prompteng.prompt_optimizer import (
    PromptOptimizer,
)
from app.core.prompteng.prompt_performance_tracker import (
    PromptPerformanceTracker,
)
from app.core.prompteng.prompt_template_library import (
    PromptTemplateLibrary,
)
from app.core.prompteng.prompt_version_control import (
    PromptVersionControl,
)

logger = logging.getLogger(__name__)


class PromptEngOrchestrator:
    """Prompt engineering orkestratoru.

    Attributes:
        template_library: Sablon kutuphanesi.
        optimizer: Optimizasyon.
        version_control: Versiyon kontrol.
        ab_tester: A/B test.
        context_manager: Context yonetimi.
        cot_builder: CoT builder.
        few_shot: Few-shot secici.
        perf_tracker: Performans takibi.
    """

    def __init__(
        self,
        auto_optimize: bool = True,
        ab_testing: bool = True,
        cot_enabled: bool = True,
        version_control: bool = True,
        max_tokens: int = 4096,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            auto_optimize: Oto-optimize.
            ab_testing: A/B test aktif.
            cot_enabled: CoT aktif.
            version_control: Versiyon aktif.
            max_tokens: Maks token.
        """
        self.template_library = (
            PromptTemplateLibrary()
        )
        self.optimizer = (
            PromptOptimizer()
        )
        self.version_control = (
            PromptVersionControl()
        )
        self.ab_tester = ABPromptTester()
        self.context_manager = (
            ContextWindowManager(
                default_max_tokens=(
                    max_tokens
                )
            )
        )
        self.cot_builder = (
            ChainOfThoughtBuilder()
        )
        self.few_shot = FewShotSelector()
        self.perf_tracker = (
            PromptPerformanceTracker()
        )

        self._auto_optimize = auto_optimize
        self._ab_testing = ab_testing
        self._cot_enabled = cot_enabled
        self._version_control = (
            version_control
        )

        logger.info(
            "PromptEngOrchestrator "
            "baslatildi"
        )

    def create_prompt(
        self,
        name: str = "",
        content: str = "",
        category: str = "",
        domain: str = "",
        variables: (
            list[str] | None
        ) = None,
        tags: (
            list[str] | None
        ) = None,
        description: str = "",
        auto_optimize: bool | None = None,
    ) -> dict[str, Any]:
        """Prompt olusturur ve optimize eder.

        Args:
            name: Prompt adi.
            content: Icerik.
            category: Kategori.
            domain: Alan.
            variables: Degiskenler.
            tags: Etiketler.
            description: Aciklama.
            auto_optimize: Oto optimize.

        Returns:
            Olusturma bilgisi.
        """
        try:
            # 1. Sablon olustur
            tpl_result = (
                self.template_library
                .create_template(
                    name=name,
                    content=content,
                    category=category,
                    variables=variables,
                    tags=tags,
                    description=description,
                )
            )

            if not tpl_result.get(
                "created"
            ):
                return tpl_result

            template_id = tpl_result[
                "template_id"
            ]

            # 2. Optimize et
            should_optimize = (
                auto_optimize
                if auto_optimize is not None
                else self._auto_optimize
            )

            optimized_content = content
            optimization = None
            if should_optimize:
                optimization = (
                    self.optimizer.optimize(
                        prompt=content
                    )
                )
                if optimization.get(
                    "optimized"
                ):
                    optimized_content = (
                        optimization[
                            "optimized_prompt"
                        ]
                    )
                    # Template guncelle
                    self.template_library\
                        .update_template(
                            template_id=(
                                template_id
                            ),
                            content=(
                                optimized_content
                            ),
                        )

            # 3. Versiyon kontrol
            version_info = None
            if self._version_control:
                version_info = (
                    self.version_control
                    .track_prompt(
                        name=name,
                        content=(
                            optimized_content
                        ),
                        author="system",
                        description=(
                            description
                        ),
                    )
                )

            # 4. Performans takibi
            perf_result = (
                self.perf_tracker
                .register_prompt(
                    name=name,
                    prompt_text=(
                        optimized_content
                    ),
                    domain=domain,
                )
            )

            return {
                "template_id": template_id,
                "name": name,
                "optimized": (
                    optimization is not None
                    and optimization.get(
                        "optimized"
                    )
                ),
                "tokens_saved": (
                    optimization.get(
                        "tokens_saved", 0
                    )
                    if optimization
                    else 0
                ),
                "version_id": (
                    version_info.get(
                        "prompt_id"
                    )
                    if version_info
                    else None
                ),
                "perf_id": (
                    perf_result.get(
                        "prompt_id"
                    )
                ),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def enhance_prompt(
        self,
        prompt: str = "",
        cot_type: str = "",
        few_shot_domain: str = "",
        few_shot_k: int = 0,
        max_tokens: int = 0,
    ) -> dict[str, Any]:
        """Promptu zenginlestirir.

        Args:
            prompt: Prompt.
            cot_type: CoT tipi.
            few_shot_domain: Few-shot alani.
            few_shot_k: Ornek sayisi.
            max_tokens: Maks token.

        Returns:
            Zenginlestirme bilgisi.
        """
        try:
            enhanced = prompt
            applied = []

            # 1. Few-shot ornekler
            if few_shot_domain:
                sel = (
                    self.few_shot
                    .select_examples(
                        query=prompt,
                        k=few_shot_k or 3,
                        domain=(
                            few_shot_domain
                        ),
                    )
                )
                if sel.get("selected"):
                    fmt = (
                        self.few_shot
                        .format_few_shot(
                            examples=sel[
                                "examples"
                            ],
                            task=prompt,
                        )
                    )
                    if fmt.get("formatted"):
                        enhanced = fmt[
                            "prompt"
                        ]
                        applied.append(
                            "few_shot"
                        )

            # 2. CoT
            if (
                cot_type
                and self._cot_enabled
            ):
                cot = (
                    self.cot_builder
                    .build_cot(
                        task=enhanced,
                        cot_type=cot_type,
                    )
                )
                if cot.get("built"):
                    enhanced = cot["prompt"]
                    applied.append("cot")

            # 3. Context window kontrolu
            if max_tokens > 0:
                overflow = (
                    self.context_manager
                    .handle_overflow(
                        text=enhanced,
                        max_tokens=(
                            max_tokens
                        ),
                    )
                )
                if overflow.get("handled"):
                    enhanced = overflow[
                        "text"
                    ]
                    if overflow.get(
                        "overflow"
                    ):
                        applied.append(
                            "truncated"
                        )

            return {
                "enhanced_prompt": enhanced,
                "applied": applied,
                "original_length": len(
                    prompt.split()
                ),
                "enhanced_length": len(
                    enhanced.split()
                ),
                "enhanced": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "enhanced": False,
                "error": str(e),
            }

    def test_prompt(
        self,
        name: str = "",
        prompt_a: str = "",
        prompt_b: str = "",
        metric: str = "quality",
        sample_size: int = 50,
    ) -> dict[str, Any]:
        """Prompt A/B testi baslatir.

        Args:
            name: Test adi.
            prompt_a: A varyanti.
            prompt_b: B varyanti.
            metric: Olcum metrigi.
            sample_size: Orneklem.

        Returns:
            Test bilgisi.
        """
        try:
            if not self._ab_testing:
                return {
                    "started": False,
                    "error": (
                        "A/B test devre disi"
                    ),
                }

            result = (
                self.ab_tester.create_test(
                    name=name,
                    prompt_a=prompt_a,
                    prompt_b=prompt_b,
                    metric=metric,
                    sample_size=sample_size,
                )
            )

            return {
                "test_id": result.get(
                    "test_id"
                ),
                "name": name,
                "started": result.get(
                    "created", False
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "started": False,
                "error": str(e),
            }

    def deploy_prompt(
        self,
        template_id: str = "",
        version_id: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        """Promptu deploy eder.

        Args:
            template_id: Sablon ID.
            version_id: Versiyon ID.
            message: Deploy mesaji.

        Returns:
            Deploy bilgisi.
        """
        try:
            tpl = (
                self.template_library
                .get_template(
                    template_id=template_id
                )
            )
            if not tpl.get("retrieved"):
                return {
                    "deployed": False,
                    "error": (
                        "Sablon bulunamadi"
                    ),
                }

            # Versiyon commit
            if (
                self._version_control
                and version_id
            ):
                self.version_control.commit(
                    prompt_id=version_id,
                    content=tpl["content"],
                    message=(
                        message
                        or "Deploy commit"
                    ),
                    author="system",
                )

            return {
                "template_id": template_id,
                "version": tpl.get(
                    "version", 1
                ),
                "deployed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "deployed": False,
                "error": str(e),
            }

    def record_usage(
        self,
        perf_id: str = "",
        success: bool = True,
        quality_score: float = 0.0,
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """Kullanim kaydeder.

        Args:
            perf_id: Performans ID.
            success: Basarili mi.
            quality_score: Kalite puani.
            latency_ms: Gecikme ms.
            input_tokens: Giris tokenlari.
            output_tokens: Cikis tokenlari.
            cost: Maliyet.

        Returns:
            Kayit bilgisi.
        """
        try:
            result = (
                self.perf_tracker
                .record_execution(
                    prompt_id=perf_id,
                    success=success,
                    quality_score=(
                        quality_score
                    ),
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=(
                        output_tokens
                    ),
                    cost=cost,
                )
            )

            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik verileri getirir."""
        try:
            return {
                "templates": (
                    self.template_library
                    .get_summary()
                ),
                "optimizer": (
                    self.optimizer
                    .get_summary()
                ),
                "versions": (
                    self.version_control
                    .get_summary()
                ),
                "ab_tests": (
                    self.ab_tester
                    .get_summary()
                ),
                "context": (
                    self.context_manager
                    .get_summary()
                ),
                "cot": (
                    self.cot_builder
                    .get_summary()
                ),
                "few_shot": (
                    self.few_shot
                    .get_summary()
                ),
                "performance": (
                    self.perf_tracker
                    .get_summary()
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
            return {
                "templates": (
                    self.template_library
                    .template_count
                ),
                "optimizations": (
                    self.optimizer
                    .optimization_count
                ),
                "versions": (
                    self.version_control
                    .prompt_count
                ),
                "ab_tests": (
                    self.ab_tester
                    .test_count
                ),
                "chains": (
                    self.cot_builder
                    .chain_count
                ),
                "examples": (
                    self.few_shot
                    .example_count
                ),
                "perf_records": (
                    self.perf_tracker
                    .record_count
                ),
                "config": {
                    "auto_optimize": (
                        self._auto_optimize
                    ),
                    "ab_testing": (
                        self._ab_testing
                    ),
                    "cot_enabled": (
                        self._cot_enabled
                    ),
                    "version_control": (
                        self._version_control
                    ),
                },
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
