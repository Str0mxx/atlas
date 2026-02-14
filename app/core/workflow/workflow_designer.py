"""ATLAS Is Akisi Tasarimcisi modulu.

Gorsel is akisi olusturma, dugum
yonetimi, baglanti islemleri,
sablon kutuphanesi ve dogrulama.
"""

import logging
from typing import Any

from app.models.workflow_engine import (
    NodeType,
    WorkflowRecord,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class WorkflowDesigner:
    """Is akisi tasarimcisi.

    Is akislarini tasarlar, dugum
    ve baglantilari yonetir.

    Attributes:
        _workflows: Is akislari.
        _templates: Sablon kutuphanesi.
    """

    def __init__(self) -> None:
        """Tasarimciyi baslatir."""
        self._workflows: dict[
            str, WorkflowRecord
        ] = {}
        self._templates: dict[
            str, dict[str, Any]
        ] = {}

        logger.info("WorkflowDesigner baslatildi")

    def create_workflow(
        self,
        name: str,
    ) -> WorkflowRecord:
        """Is akisi olusturur.

        Args:
            name: Is akisi adi.

        Returns:
            Is akisi kaydi.
        """
        wf = WorkflowRecord(name=name)
        self._workflows[wf.workflow_id] = wf
        logger.info(
            "Is akisi olusturuldu: %s", name,
        )
        return wf

    def add_node(
        self,
        workflow_id: str,
        name: str,
        node_type: NodeType,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Dugum ekler.

        Args:
            workflow_id: Is akisi ID.
            name: Dugum adi.
            node_type: Dugum turu.
            config: Yapilandirma.

        Returns:
            Dugum bilgisi veya None.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None

        node_id = f"n_{len(wf.nodes) + 1}"
        node = {
            "id": node_id,
            "name": name,
            "type": node_type.value,
            "config": config or {},
        }
        wf.nodes.append(node)
        return node

    def remove_node(
        self,
        workflow_id: str,
        node_id: str,
    ) -> bool:
        """Dugum kaldirir.

        Args:
            workflow_id: Is akisi ID.
            node_id: Dugum ID.

        Returns:
            Basarili ise True.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False

        original = len(wf.nodes)
        wf.nodes = [
            n for n in wf.nodes
            if n["id"] != node_id
        ]
        # Baglantilari da temizle
        wf.connections = [
            c for c in wf.connections
            if c["from"] != node_id
            and c["to"] != node_id
        ]
        return len(wf.nodes) < original

    def add_connection(
        self,
        workflow_id: str,
        from_node: str,
        to_node: str,
        label: str = "",
    ) -> dict[str, Any] | None:
        """Baglanti ekler.

        Args:
            workflow_id: Is akisi ID.
            from_node: Kaynak dugum.
            to_node: Hedef dugum.
            label: Etiket.

        Returns:
            Baglanti bilgisi veya None.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None

        node_ids = {n["id"] for n in wf.nodes}
        if (
            from_node not in node_ids
            or to_node not in node_ids
        ):
            return None

        conn = {
            "from": from_node,
            "to": to_node,
            "label": label,
        }
        wf.connections.append(conn)
        return conn

    def remove_connection(
        self,
        workflow_id: str,
        from_node: str,
        to_node: str,
    ) -> bool:
        """Baglanti kaldirir.

        Args:
            workflow_id: Is akisi ID.
            from_node: Kaynak dugum.
            to_node: Hedef dugum.

        Returns:
            Basarili ise True.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False

        original = len(wf.connections)
        wf.connections = [
            c for c in wf.connections
            if not (
                c["from"] == from_node
                and c["to"] == to_node
            )
        ]
        return len(wf.connections) < original

    def validate(
        self,
        workflow_id: str,
    ) -> dict[str, Any]:
        """Is akisini dogrular.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Dogrulama sonucu.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {
                "valid": False,
                "errors": ["workflow_not_found"],
            }

        errors: list[str] = []

        if not wf.nodes:
            errors.append("no_nodes")

        # Baglanti dogrulamasi
        node_ids = {n["id"] for n in wf.nodes}
        for conn in wf.connections:
            if conn["from"] not in node_ids:
                errors.append(
                    f"invalid_from:{conn['from']}",
                )
            if conn["to"] not in node_ids:
                errors.append(
                    f"invalid_to:{conn['to']}",
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "node_count": len(wf.nodes),
            "connection_count": len(wf.connections),
        }

    def save_template(
        self,
        name: str,
        workflow_id: str,
    ) -> dict[str, Any] | None:
        """Sablon kaydeder.

        Args:
            name: Sablon adi.
            workflow_id: Is akisi ID.

        Returns:
            Sablon bilgisi veya None.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None

        template = {
            "name": name,
            "nodes": list(wf.nodes),
            "connections": list(wf.connections),
        }
        self._templates[name] = template
        return template

    def create_from_template(
        self,
        template_name: str,
        workflow_name: str,
    ) -> WorkflowRecord | None:
        """Sablondan olusturur.

        Args:
            template_name: Sablon adi.
            workflow_name: Yeni is akisi adi.

        Returns:
            Is akisi veya None.
        """
        template = self._templates.get(
            template_name,
        )
        if not template:
            return None

        wf = self.create_workflow(workflow_name)
        wf.nodes = list(template["nodes"])
        wf.connections = list(
            template["connections"],
        )
        return wf

    def activate(
        self,
        workflow_id: str,
    ) -> bool:
        """Is akisini aktif eder.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Basarili ise True.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False
        validation = self.validate(workflow_id)
        if not validation["valid"]:
            return False
        wf.status = WorkflowStatus.ACTIVE
        return True

    def get_workflow(
        self,
        workflow_id: str,
    ) -> WorkflowRecord | None:
        """Is akisi getirir.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Is akisi veya None.
        """
        return self._workflows.get(workflow_id)

    def delete_workflow(
        self,
        workflow_id: str,
    ) -> bool:
        """Is akisi siler.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Basarili ise True.
        """
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    @property
    def workflow_count(self) -> int:
        """Is akisi sayisi."""
        return len(self._workflows)

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)
