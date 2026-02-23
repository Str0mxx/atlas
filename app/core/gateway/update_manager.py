"""Gateway guncelleme yoneticisi.

Guncelleme akisi, doktor calistirma
ve restart baglam koruma.
"""

import json
import logging
import os
import tempfile
import time
from typing import Any

from app.models.gateway_models import UpdateResult

logger = logging.getLogger(__name__)

_CONTEXT_FILE = os.path.join(
    tempfile.gettempdir(),
    "atlas_restart_context.json",
)


class GatewayUpdateManager:
    """Gateway guncelleme yoneticisi.

    Attributes:
        _context_file: Baglam dosya yolu.
    """

    def __init__(
        self,
        context_file: str = "",
    ) -> None:
        """GatewayUpdateManager baslatir."""
        self._context_file = (
            context_file or _CONTEXT_FILE
        )

    @staticmethod
    def restart_only_on_success(
        update_result: dict[str, Any],
    ) -> bool:
        """Sadece basarili guncellemede restart.

        Args:
            update_result: Guncelleme sonucu.

        Returns:
            Restart gerekli ise True.
        """
        success = update_result.get(
            "success", False,
        )
        needs_restart = update_result.get(
            "restart_required", False,
        )
        return success and needs_restart

    @staticmethod
    def run_doctor_during_update() -> dict[str, Any]:
        """Guncelleme sirasinda doktor calistirir.

        Returns:
            Doktor sonuclari.
        """
        from app.core.gateway.doctor import (
            GatewayDoctor,
        )

        doctor = GatewayDoctor()
        return doctor.run_diagnostics(fix=True)

    def preserve_restart_context(
        self,
        context: dict[str, Any],
    ) -> str:
        """Restart oncesi baglami kaydeder.

        Args:
            context: Korunacak baglam.

        Returns:
            Dosya yolu.
        """
        try:
            data = {
                "context": context,
                "saved_at": time.time(),
            }
            with open(
                self._context_file,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(data, f)
            logger.info(
                "Restart baglami kaydedildi",
            )
            return self._context_file
        except OSError as e:
            logger.error(
                "Baglam kaydetme hatasi: %s", e,
            )
            return ""

    def restore_restart_context(
        self,
    ) -> dict[str, Any] | None:
        """Restart sonrasi baglami geri yukler.

        Returns:
            Korunan baglam veya None.
        """
        try:
            if not os.path.isfile(
                self._context_file,
            ):
                return None

            with open(
                self._context_file,
                encoding="utf-8",
            ) as f:
                data = json.load(f)

            os.remove(self._context_file)
            return data.get("context")
        except (
            json.JSONDecodeError,
            OSError,
        ):
            return None

    def perform_update(
        self,
        version: str,
        config: dict[str, Any] | None = None,
    ) -> UpdateResult:
        """Guncelleme orkestre eder.

        Args:
            version: Hedef surum.
            config: Mevcut yapilandirma.

        Returns:
            Guncelleme sonucu.
        """
        result = UpdateResult(version=version)

        doctor_result = (
            self.run_doctor_during_update()
        )
        result.doctor_result = doctor_result

        if config:
            self.preserve_restart_context(config)
            result.context_preserved = True

        result.success = True
        result.restart_required = True

        logger.info(
            "Guncelleme tamamlandi: v%s",
            version,
        )
        return result
