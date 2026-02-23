"""Gateway doktor (tani) sistemi.

Yapilandirma dogrulama, otomatik onarim
ve jeton sapma tespiti.
"""

import logging
from typing import Any

from app.models.gateway_models import (
    DiagnosticResult,
)

logger = logging.getLogger(__name__)


class GatewayDoctor:
    """Gateway tanilama ve onarim sistemi.

    Attributes:
        _issues: Tespit edilen sorunlar.
        _fixed: Duzeltilen sorunlar.
    """

    def __init__(self) -> None:
        """GatewayDoctor baslatir."""
        self._issues: list[DiagnosticResult] = []
        self._fixed: list[str] = []

    @staticmethod
    def avoid_rewriting_invalid(
        config: dict[str, Any],
    ) -> bool:
        """Gecersiz config'leri yeniden yazmaz.

        Gecersiz config tespit edilirse False doner
        ve yazma islemi engellenir.

        Args:
            config: Yapilandirma.

        Returns:
            Config gecerli ise True.
        """
        if not config:
            return False
        if not isinstance(config, dict):
            return False

        required = {"version"}
        for key in required:
            if key not in config:
                return False

        return True

    @staticmethod
    def skip_embedding_warnings(
        backend: str,
    ) -> bool:
        """qmd backend icin embedding uyarilarini atlar.

        Args:
            backend: Backend adi.

        Returns:
            Atlanacaksa True.
        """
        skip_backends = {"qmd", "quantized"}
        return backend.lower() in skip_backends

    @staticmethod
    def auto_repair_dm_policy(
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """dmPolicy='open' config'lerini onarir.

        'open' degerini 'invite' ile degistirir.

        Args:
            config: Yapilandirma.

        Returns:
            Onarilmis yapilandirma.
        """
        result = dict(config)
        if result.get("dmPolicy") == "open":
            result["dmPolicy"] = "invite"
            logger.info(
                "dmPolicy 'open' -> 'invite' onarildi",
            )
        return result

    @staticmethod
    def detect_token_drift(
        config: dict[str, Any],
    ) -> list[str]:
        """Gateway servis jeton sapmasini tespit eder.

        Config'teki jetonlarin tutarli olup
        olmadigini kontrol eder.

        Args:
            config: Yapilandirma.

        Returns:
            Saptanan sorunlar listesi.
        """
        issues: list[str] = []

        tokens = config.get("tokens", {})
        service_token = config.get(
            "service_token", "",
        )

        if service_token and isinstance(
            tokens, dict,
        ):
            for name, tok in tokens.items():
                if isinstance(tok, dict):
                    tok_val = tok.get("token", "")
                    if (
                        tok_val
                        and tok_val == service_token
                    ):
                        issues.append(
                            f"Jeton sapmasi: "
                            f"'{name}' servis jetonu "
                            f"ile ayni",
                        )

        if not service_token and tokens:
            issues.append(
                "Servis jetonu tanimlanmamis "
                "ama cihaz jetonlari var",
            )

        return issues

    def run_diagnostics(
        self,
        config: dict[str, Any] | None = None,
        fix: bool = False,
        non_interactive: bool = False,
    ) -> dict[str, Any]:
        """Tam tanilama calistirir.

        Args:
            config: Yapilandirma.
            fix: Otomatik duzeltme.
            non_interactive: Etkilesimli degil.

        Returns:
            Tanilama sonuclari.
        """
        self._issues.clear()
        self._fixed.clear()

        cfg = config or {}

        if not self.avoid_rewriting_invalid(cfg):
            self._issues.append(
                DiagnosticResult(
                    category="config",
                    issue="Gecersiz yapilandirma",
                    severity="error",
                    auto_fixable=False,
                ),
            )

        dm_policy = cfg.get("dmPolicy", "")
        if dm_policy == "open":
            result = DiagnosticResult(
                category="security",
                issue="dmPolicy 'open' olarak ayarli",
                severity="warning",
                auto_fixable=True,
            )
            if fix:
                cfg = self.auto_repair_dm_policy(cfg)
                result.fixed = True
                self._fixed.append(
                    "dmPolicy onarildi",
                )
            self._issues.append(result)

        drift = self.detect_token_drift(cfg)
        for d in drift:
            self._issues.append(
                DiagnosticResult(
                    category="auth",
                    issue=d,
                    severity="warning",
                    auto_fixable=False,
                ),
            )

        return {
            "total_issues": len(self._issues),
            "fixed": len(self._fixed),
            "issues": [
                i.model_dump()
                for i in self._issues
            ],
            "config": cfg,
        }
