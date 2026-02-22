"""Is akisi deposu - is akislarini kalici saklama."""

import json
import logging
import os
import time
import uuid
from typing import Any, Optional

from app.models.lobster_models import Workflow, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowStore:
    """Is akisi kalici depo yoneticisi."""

    def __init__(self, store_dir: str = "") -> None:
        """WorkflowStore baslatici."""
        self.store_dir = store_dir
        self._store: dict[str, dict] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {"total_stored": len(self._store), "store_dir": self.store_dir, "history_count": len(self._history)}

    def save(self, workflow: Workflow) -> str:
        """Is akisini kaydeder."""
        workflow_id = workflow.workflow_id or str(uuid.uuid4())
        data = workflow.model_dump()
        data["status"] = workflow.status.value
        for i, step in enumerate(data.get("steps", [])):
            if hasattr(workflow.steps[i].status, "value"):
                step["status"] = workflow.steps[i].status.value
            if hasattr(workflow.steps[i].step_type, "value"):
                step["step_type"] = workflow.steps[i].step_type.value
        self._store[workflow_id] = data
        self._record_history("save", {"workflow_id": workflow_id})
        return workflow_id

    def load(self, workflow_id: str) -> Optional[Workflow]:
        """Is akisini yukler."""
        data = self._store.get(workflow_id)
        if not data:
            return None
        try:
            workflow = Workflow(**data)
            self._record_history("load", {"workflow_id": workflow_id})
            return workflow
        except Exception as e:
            logger.error(f"Is akisi yukleme hatasi: {e}")
            return None

    def delete(self, workflow_id: str) -> bool:
        """Is akisini siler."""
        if workflow_id in self._store:
            del self._store[workflow_id]
            self._record_history("delete", {"workflow_id": workflow_id})
            return True
        return False

    def list_all(self) -> list[dict]:
        """Tum kayitli is akislarini listeler."""
        result: list[dict] = []
        for wid, data in self._store.items():
            result.append({"workflow_id": wid, "name": data.get("name", ""), "status": data.get("status", ""), "step_count": len(data.get("steps", [])), "created_at": data.get("created_at", 0)})
        return result

    def export_workflow(self, workflow_id: str) -> dict:
        """Is akisini JSON olarak disa aktarir."""
        data = self._store.get(workflow_id)
        if not data:
            raise ValueError(f"Workflow not found: {workflow_id}")
        self._record_history("export_workflow", {"workflow_id": workflow_id})
        return dict(data)

    def import_workflow(self, data: dict) -> Workflow:
        """Dis kaynaklardan is akisi icerir."""
        workflow_id = data.get("workflow_id", str(uuid.uuid4()))
        data["workflow_id"] = workflow_id
        workflow = Workflow(**data)
        self.save(workflow)
        self._record_history("import_workflow", {"workflow_id": workflow_id})
        return workflow

    def search(self, query: str) -> list[Workflow]:
        """Is akislarinda arama yapar."""
        results: list[Workflow] = []
        query_lower = query.lower()
        for data in self._store.values():
            name = data.get("name", "").lower()
            description = data.get("description", "").lower()
            tags = [t.lower() for t in data.get("tags", [])]
            if query_lower in name or query_lower in description or any(query_lower in tag for tag in tags):
                try:
                    results.append(Workflow(**data))
                except Exception:
                    pass
        self._record_history("search", {"query": query, "results": len(results)})
        return results
