"""Envanter plugin hook handler'lari."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def on_task_completed(**kwargs: Any) -> None:
    """Gorev tamamlandiginda envanter etkisini kontrol eder.

    Args:
        **kwargs: Olay verileri (task, result vb.).
    """
    task = kwargs.get("task")
    if task and "stok" in str(task).lower():
        logger.info(
            "Envanter etkilenen gorev tamamlandi: %s",
            task if isinstance(task, str) else task.get("id", "?"),
        )
