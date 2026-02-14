"""ATLAS Pipeline Olusturucu modulu.

DAG olusturma, adim zincirleme,
dallanma, birlestirme ve kosullu
akislar.
"""

import logging
from typing import Any

from app.models.pipeline import (
    PipelineRecord,
    PipelineStatus,
    StepRecord,
    StepType,
)

logger = logging.getLogger(__name__)


class PipelineBuilder:
    """Pipeline olusturucu.

    DAG tabanli pipeline'lar olusturur
    ve yonetir.

    Attributes:
        _pipelines: Olusturulan pipeline'lar.
        _current: Mevcut pipeline.
    """

    def __init__(self) -> None:
        """Pipeline olusturucuyu baslatir."""
        self._pipelines: dict[
            str, PipelineRecord
        ] = {}
        self._steps: dict[
            str, list[StepRecord]
        ] = {}
        self._dependencies: dict[
            str, dict[str, list[str]]
        ] = {}
        self._conditions: dict[
            str, dict[str, Any]
        ] = {}

        logger.info("PipelineBuilder baslatildi")

    def create_pipeline(
        self,
        name: str,
    ) -> PipelineRecord:
        """Pipeline olusturur.

        Args:
            name: Pipeline adi.

        Returns:
            Pipeline kaydi.
        """
        pipeline = PipelineRecord(name=name)
        self._pipelines[pipeline.pipeline_id] = pipeline
        self._steps[pipeline.pipeline_id] = []
        self._dependencies[pipeline.pipeline_id] = {}

        logger.info(
            "Pipeline olusturuldu: %s", name,
        )
        return pipeline

    def add_step(
        self,
        pipeline_id: str,
        name: str,
        step_type: StepType,
        config: dict[str, Any] | None = None,
    ) -> StepRecord | None:
        """Adim ekler.

        Args:
            pipeline_id: Pipeline ID.
            name: Adim adi.
            step_type: Adim turu.
            config: Yapilandirma.

        Returns:
            Adim kaydi veya None.
        """
        if pipeline_id not in self._pipelines:
            return None

        step = StepRecord(
            name=name,
            step_type=step_type,
        )
        self._steps[pipeline_id].append(step)
        self._dependencies[pipeline_id][
            step.step_id
        ] = []

        return step

    def chain_steps(
        self,
        pipeline_id: str,
        step_ids: list[str],
    ) -> bool:
        """Adimlari zincirler.

        Args:
            pipeline_id: Pipeline ID.
            step_ids: Adim ID listesi.

        Returns:
            Basarili ise True.
        """
        deps = self._dependencies.get(pipeline_id)
        if not deps:
            return False

        for i in range(1, len(step_ids)):
            prev_id = step_ids[i - 1]
            curr_id = step_ids[i]
            if curr_id in deps:
                deps[curr_id].append(prev_id)

        return True

    def add_branch(
        self,
        pipeline_id: str,
        from_step: str,
        to_steps: list[str],
    ) -> bool:
        """Dallanma ekler.

        Args:
            pipeline_id: Pipeline ID.
            from_step: Kaynak adim.
            to_steps: Hedef adimlar.

        Returns:
            Basarili ise True.
        """
        deps = self._dependencies.get(pipeline_id)
        if not deps:
            return False

        for to_step in to_steps:
            if to_step in deps:
                deps[to_step].append(from_step)

        return True

    def add_merge(
        self,
        pipeline_id: str,
        from_steps: list[str],
        to_step: str,
    ) -> bool:
        """Birlestirme ekler.

        Args:
            pipeline_id: Pipeline ID.
            from_steps: Kaynak adimlar.
            to_step: Hedef adim.

        Returns:
            Basarili ise True.
        """
        deps = self._dependencies.get(pipeline_id)
        if not deps:
            return False

        if to_step in deps:
            deps[to_step].extend(from_steps)
            return True
        return False

    def add_condition(
        self,
        pipeline_id: str,
        step_id: str,
        condition: str,
        on_true: str = "",
        on_false: str = "",
    ) -> bool:
        """Kosullu akis ekler.

        Args:
            pipeline_id: Pipeline ID.
            step_id: Adim ID.
            condition: Kosul ifadesi.
            on_true: True durumunda adim.
            on_false: False durumunda adim.

        Returns:
            Basarili ise True.
        """
        if pipeline_id not in self._pipelines:
            return False

        key = f"{pipeline_id}:{step_id}"
        self._conditions[key] = {
            "condition": condition,
            "on_true": on_true,
            "on_false": on_false,
        }
        return True

    def get_pipeline(
        self,
        pipeline_id: str,
    ) -> PipelineRecord | None:
        """Pipeline getirir.

        Args:
            pipeline_id: Pipeline ID.

        Returns:
            Pipeline veya None.
        """
        return self._pipelines.get(pipeline_id)

    def get_steps(
        self,
        pipeline_id: str,
    ) -> list[StepRecord]:
        """Adimlari getirir.

        Args:
            pipeline_id: Pipeline ID.

        Returns:
            Adim listesi.
        """
        return self._steps.get(pipeline_id, [])

    def get_execution_order(
        self,
        pipeline_id: str,
    ) -> list[str]:
        """Calistirma sirasini belirler.

        Args:
            pipeline_id: Pipeline ID.

        Returns:
            Adim ID listesi (topolojik sira).
        """
        deps = self._dependencies.get(pipeline_id)
        if not deps:
            return []

        # Topolojik siralama
        visited: set[str] = set()
        order: list[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            for dep in deps.get(node, []):
                visit(dep)
            order.append(node)

        for node in deps:
            visit(node)

        return order

    def delete_pipeline(
        self,
        pipeline_id: str,
    ) -> bool:
        """Pipeline siler.

        Args:
            pipeline_id: Pipeline ID.

        Returns:
            Basarili ise True.
        """
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            self._steps.pop(pipeline_id, None)
            self._dependencies.pop(
                pipeline_id, None,
            )
            return True
        return False

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayisi."""
        return len(self._pipelines)

    @property
    def total_steps(self) -> int:
        """Toplam adim sayisi."""
        return sum(
            len(steps)
            for steps in self._steps.values()
        )
