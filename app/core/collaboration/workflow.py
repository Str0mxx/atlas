"""ATLAS Multi-Agent workflow modulu.

Cok agentli is akisi orkestrasyon: seri, paralel,
kosullu dallanma ve birlesme.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

from app.models.collaboration import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowResult,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)

# Agent calistirici tipi: (agent_adi, gorev_params) -> sonuc
AgentExecutor = Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


class WorkflowEngine:
    """Multi-agent is akisi motoru.

    Seri (sequence), paralel, kosullu ve birlestirme
    dugumleriyle karmasik is akislarini orkestrasyona eder.

    Attributes:
        workflows: Kayitli is akislari (id -> WorkflowDefinition).
        _executor: Agent calistirici fonksiyonu.
        _context: Paylasimli calisma baglamı.
    """

    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self.workflows: dict[str, WorkflowDefinition] = {}
        self._executor = executor
        self._context: dict[str, Any] = {}

    def set_executor(self, executor: AgentExecutor) -> None:
        """Agent calistirici fonksiyonunu ayarlar.

        Args:
            executor: (agent_adi, params) -> sonuc coroutine.
        """
        self._executor = executor

    def create_workflow(
        self,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowDefinition:
        """Yeni is akisi olusturur.

        Args:
            name: Is akisi adi.
            description: Aciklama.
            metadata: Ek veriler.

        Returns:
            Olusturulan WorkflowDefinition.
        """
        workflow = WorkflowDefinition(
            name=name,
            description=description,
            metadata=metadata or {},
        )
        self.workflows[workflow.id] = workflow

        logger.info("Is akisi olusturuldu: %s", name)
        return workflow

    def add_node(
        self,
        workflow_id: str,
        name: str,
        node_type: WorkflowNodeType = WorkflowNodeType.TASK,
        agent_name: str | None = None,
        task_params: dict[str, Any] | None = None,
        condition: str | None = None,
    ) -> WorkflowNode | None:
        """Is akisina dugum ekler.

        Args:
            workflow_id: Is akisi ID.
            name: Dugum adi.
            node_type: Dugum tipi.
            agent_name: Atanan agent (TASK tipi icin).
            task_params: Gorev parametreleri.
            condition: Kosul ifadesi (CONDITIONAL tipi icin).

        Returns:
            Olusturulan dugum veya None.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return None

        node = WorkflowNode(
            name=name,
            node_type=node_type,
            agent_name=agent_name,
            task_params=task_params or {},
            condition=condition,
        )
        workflow.nodes[node.id] = node

        # Ilk dugum kok olur
        if workflow.root_id is None:
            workflow.root_id = node.id

        return node

    def connect_nodes(
        self,
        workflow_id: str,
        parent_id: str,
        child_id: str,
    ) -> bool:
        """Dugumleri baglar.

        Args:
            workflow_id: Is akisi ID.
            parent_id: Ust dugum ID.
            child_id: Alt dugum ID.

        Returns:
            Basarili mi.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return False

        parent = workflow.nodes.get(parent_id)
        child = workflow.nodes.get(child_id)
        if parent is None or child is None:
            return False

        if child_id not in parent.children:
            parent.children.append(child_id)
        return True

    async def execute(
        self,
        workflow_id: str,
        initial_context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Is akisini calistirir.

        Args:
            workflow_id: Is akisi ID.
            initial_context: Baslangic baglamı.

        Returns:
            WorkflowResult.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return WorkflowResult(
                workflow_id=workflow_id,
                success=False,
                failed_nodes=["workflow_not_found"],
            )

        if workflow.root_id is None:
            return WorkflowResult(
                workflow_id=workflow_id,
                success=False,
                failed_nodes=["no_root_node"],
            )

        self._context = dict(initial_context or {})
        workflow.status = WorkflowStatus.RUNNING
        start_time = time.monotonic()

        node_results: dict[str, Any] = {}
        failed_nodes: list[str] = []

        try:
            await self._execute_node(
                workflow, workflow.root_id, node_results, failed_nodes,
            )
        except Exception as exc:
            logger.exception("Is akisi hatasi: %s", exc)
            failed_nodes.append(f"exception:{exc}")

        elapsed = time.monotonic() - start_time
        success = len(failed_nodes) == 0

        workflow.status = (
            WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
        )

        logger.info(
            "Is akisi tamamlandi: %s (basarili=%s, sure=%.2fs)",
            workflow.name,
            success,
            elapsed,
        )

        return WorkflowResult(
            workflow_id=workflow_id,
            success=success,
            node_results=node_results,
            total_duration=elapsed,
            failed_nodes=failed_nodes,
        )

    async def _execute_node(
        self,
        workflow: WorkflowDefinition,
        node_id: str,
        node_results: dict[str, Any],
        failed_nodes: list[str],
    ) -> None:
        """Tek bir dugumu calistirir.

        Args:
            workflow: Is akisi.
            node_id: Calistirilacak dugum ID.
            node_results: Sonuc biriktiricisi.
            failed_nodes: Basarisiz dugum biriktiricisi.
        """
        node = workflow.nodes.get(node_id)
        if node is None:
            failed_nodes.append(node_id)
            return

        node.status = WorkflowStatus.RUNNING

        if node.node_type == WorkflowNodeType.TASK:
            await self._execute_task_node(node, node_results, failed_nodes)

        elif node.node_type == WorkflowNodeType.SEQUENCE:
            for child_id in node.children:
                await self._execute_node(
                    workflow, child_id, node_results, failed_nodes,
                )
                # Seri: basarisiz olursa dur
                if child_id in failed_nodes:
                    node.status = WorkflowStatus.FAILED
                    failed_nodes.append(node_id)
                    return

        elif node.node_type == WorkflowNodeType.PARALLEL:
            tasks = [
                self._execute_node(
                    workflow, child_id, node_results, failed_nodes,
                )
                for child_id in node.children
            ]
            await asyncio.gather(*tasks)
            # Herhangi bir alt dugum basarisiz ise
            if any(cid in failed_nodes for cid in node.children):
                node.status = WorkflowStatus.FAILED
                failed_nodes.append(node_id)
                return

        elif node.node_type == WorkflowNodeType.CONDITIONAL:
            branch_id = self._evaluate_condition(node, workflow)
            if branch_id:
                await self._execute_node(
                    workflow, branch_id, node_results, failed_nodes,
                )
            else:
                logger.debug("Kosul karsilanmadi, atlanıyor: %s", node.name)

        elif node.node_type == WorkflowNodeType.MERGE:
            # Merge: tum children sonuclarini birlestir
            for child_id in node.children:
                await self._execute_node(
                    workflow, child_id, node_results, failed_nodes,
                )

        if node_id not in failed_nodes:
            node.status = WorkflowStatus.COMPLETED

    async def _execute_task_node(
        self,
        node: WorkflowNode,
        node_results: dict[str, Any],
        failed_nodes: list[str],
    ) -> None:
        """TASK tipinde dugumu calistirir.

        Args:
            node: Calistirilacak dugum.
            node_results: Sonuc biriktiricisi.
            failed_nodes: Basarisiz dugum biriktiricisi.
        """
        if self._executor is None:
            logger.warning("Executor ayarlanmamis, dugum atlandi: %s", node.name)
            node.status = WorkflowStatus.FAILED
            failed_nodes.append(node.id)
            return

        if node.agent_name is None:
            logger.warning("Agent atanmamis: %s", node.name)
            node.status = WorkflowStatus.FAILED
            failed_nodes.append(node.id)
            return

        # Konteksti gorev parametrelerine ekle
        params = dict(node.task_params)
        params["_context"] = dict(self._context)

        try:
            result = await self._executor(node.agent_name, params)
            node.result = result
            node_results[node.id] = result
            node.status = WorkflowStatus.COMPLETED

            # Sonucu kontekste ekle
            self._context[node.id] = result

            logger.debug("Dugum tamamlandi: %s (agent=%s)", node.name, node.agent_name)
        except Exception as exc:
            logger.error("Dugum hatasi: %s -> %s", node.name, exc)
            node.status = WorkflowStatus.FAILED
            node_results[node.id] = {"error": str(exc)}
            failed_nodes.append(node.id)

    def _evaluate_condition(
        self,
        node: WorkflowNode,
        workflow: WorkflowDefinition,
    ) -> str | None:
        """Kosul ifadesini degerlendirir ve dallanma yapar.

        Kosul formati: "context_key == value" veya "context_key"
        (truthy kontrolu).

        Args:
            node: Conditional dugum.
            workflow: Is akisi.

        Returns:
            Secilen dal dugum ID veya None.
        """
        if not node.children:
            return None

        condition = node.condition or ""

        if "==" in condition:
            parts = condition.split("==", 1)
            key = parts[0].strip()
            expected = parts[1].strip()
            actual = str(self._context.get(key, ""))
            condition_met = actual == expected
        elif condition:
            condition_met = bool(self._context.get(condition))
        else:
            condition_met = True

        if condition_met and len(node.children) >= 1:
            return node.children[0]  # True dali
        elif not condition_met and len(node.children) >= 2:
            return node.children[1]  # False dali

        return None

    async def pause_workflow(self, workflow_id: str) -> bool:
        """Is akisini duraklatir.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Basarili mi.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None or workflow.status != WorkflowStatus.RUNNING:
            return False

        workflow.status = WorkflowStatus.PAUSED
        return True

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Is akisini iptal eder.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Basarili mi.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return False

        if workflow.status in (WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED):
            return False

        workflow.status = WorkflowStatus.CANCELLED
        return True

    def get_workflow_status(
        self, workflow_id: str
    ) -> dict[str, Any] | None:
        """Is akisi durumunu dondurur.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Durum bilgisi veya None.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return None

        node_statuses: dict[str, str] = {}
        for nid, node in workflow.nodes.items():
            node_statuses[nid] = node.status.value

        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "total_nodes": len(workflow.nodes),
            "node_statuses": node_statuses,
        }
