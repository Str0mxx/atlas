"""ATLAS Kapsam Analizcisi modulu.

Satir kapsamı, dal kapsami,
fonksiyon kapsami, yol kapsami
ve bosluk tespiti.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CoverageAnalyzer:
    """Kapsam analizcisi.

    Kod kapsam verilerini analiz eder.

    Attributes:
        _modules: Modul kapsam verileri.
        _thresholds: Esik degerleri.
    """

    def __init__(
        self,
        min_coverage: float = 80.0,
    ) -> None:
        """Kapsam analizcisini baslatir.

        Args:
            min_coverage: Minimum kapsam yuzdesi.
        """
        self._min_coverage = min_coverage
        self._modules: dict[
            str, dict[str, Any]
        ] = {}
        self._thresholds: dict[str, float] = {
            "line": min_coverage,
            "branch": min_coverage - 10,
            "function": min_coverage,
            "path": min_coverage - 20,
        }

        logger.info(
            "CoverageAnalyzer baslatildi",
        )

    def add_module_coverage(
        self,
        module: str,
        total_lines: int,
        covered_lines: int,
        total_branches: int = 0,
        covered_branches: int = 0,
        total_functions: int = 0,
        covered_functions: int = 0,
    ) -> dict[str, Any]:
        """Modul kapsam verisi ekler.

        Args:
            module: Modul adi.
            total_lines: Toplam satir.
            covered_lines: Kapsanan satir.
            total_branches: Toplam dal.
            covered_branches: Kapsanan dal.
            total_functions: Toplam fonksiyon.
            covered_functions: Kapsanan fonksiyon.

        Returns:
            Kapsam bilgisi.
        """
        line_pct = (
            (covered_lines / total_lines * 100)
            if total_lines > 0
            else 0.0
        )
        branch_pct = (
            (covered_branches / total_branches * 100)
            if total_branches > 0
            else 0.0
        )
        func_pct = (
            (covered_functions / total_functions * 100)
            if total_functions > 0
            else 0.0
        )

        data = {
            "module": module,
            "line": {
                "total": total_lines,
                "covered": covered_lines,
                "percentage": round(line_pct, 2),
            },
            "branch": {
                "total": total_branches,
                "covered": covered_branches,
                "percentage": round(branch_pct, 2),
            },
            "function": {
                "total": total_functions,
                "covered": covered_functions,
                "percentage": round(func_pct, 2),
            },
        }
        self._modules[module] = data
        return data

    def get_line_coverage(
        self,
        module: str | None = None,
    ) -> dict[str, Any]:
        """Satir kapsamini getirir.

        Args:
            module: Modul adi (None=toplam).

        Returns:
            Kapsam bilgisi.
        """
        if module:
            data = self._modules.get(module)
            if not data:
                return {"percentage": 0.0}
            return data["line"]

        total = sum(
            m["line"]["total"]
            for m in self._modules.values()
        )
        covered = sum(
            m["line"]["covered"]
            for m in self._modules.values()
        )
        pct = (
            covered / total * 100
            if total > 0
            else 0.0
        )
        return {
            "total": total,
            "covered": covered,
            "percentage": round(pct, 2),
        }

    def get_branch_coverage(
        self,
        module: str | None = None,
    ) -> dict[str, Any]:
        """Dal kapsamini getirir.

        Args:
            module: Modul adi (None=toplam).

        Returns:
            Kapsam bilgisi.
        """
        if module:
            data = self._modules.get(module)
            if not data:
                return {"percentage": 0.0}
            return data["branch"]

        total = sum(
            m["branch"]["total"]
            for m in self._modules.values()
        )
        covered = sum(
            m["branch"]["covered"]
            for m in self._modules.values()
        )
        pct = (
            covered / total * 100
            if total > 0
            else 0.0
        )
        return {
            "total": total,
            "covered": covered,
            "percentage": round(pct, 2),
        }

    def get_function_coverage(
        self,
        module: str | None = None,
    ) -> dict[str, Any]:
        """Fonksiyon kapsamini getirir.

        Args:
            module: Modul adi (None=toplam).

        Returns:
            Kapsam bilgisi.
        """
        if module:
            data = self._modules.get(module)
            if not data:
                return {"percentage": 0.0}
            return data["function"]

        total = sum(
            m["function"]["total"]
            for m in self._modules.values()
        )
        covered = sum(
            m["function"]["covered"]
            for m in self._modules.values()
        )
        pct = (
            covered / total * 100
            if total > 0
            else 0.0
        )
        return {
            "total": total,
            "covered": covered,
            "percentage": round(pct, 2),
        }

    def identify_gaps(
        self,
    ) -> list[dict[str, Any]]:
        """Kapsam bosluklarini tespit eder.

        Returns:
            Bosluk listesi.
        """
        gaps = []
        for name, data in self._modules.items():
            line_pct = data["line"]["percentage"]
            if line_pct < self._thresholds["line"]:
                gaps.append({
                    "module": name,
                    "type": "line",
                    "current": line_pct,
                    "required": self._thresholds[
                        "line"
                    ],
                    "gap": round(
                        self._thresholds["line"]
                        - line_pct,
                        2,
                    ),
                })

            branch_pct = data["branch"]["percentage"]
            if (
                data["branch"]["total"] > 0
                and branch_pct
                < self._thresholds["branch"]
            ):
                gaps.append({
                    "module": name,
                    "type": "branch",
                    "current": branch_pct,
                    "required": self._thresholds[
                        "branch"
                    ],
                    "gap": round(
                        self._thresholds["branch"]
                        - branch_pct,
                        2,
                    ),
                })

        return gaps

    def set_threshold(
        self,
        level: str,
        threshold: float,
    ) -> None:
        """Esik degeri ayarlar.

        Args:
            level: Kapsam seviyesi.
            threshold: Esik degeri.
        """
        self._thresholds[level] = threshold

    def meets_threshold(
        self,
        module: str | None = None,
    ) -> bool:
        """Esik degerini karsilar mi.

        Args:
            module: Modul adi (None=toplam).

        Returns:
            Karsiliyorsa True.
        """
        line_cov = self.get_line_coverage(module)
        return (
            line_cov["percentage"]
            >= self._thresholds["line"]
        )

    def get_summary(self) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        line = self.get_line_coverage()
        branch = self.get_branch_coverage()
        func = self.get_function_coverage()
        gaps = self.identify_gaps()

        return {
            "modules": len(self._modules),
            "line_coverage": line["percentage"],
            "branch_coverage": branch["percentage"],
            "function_coverage": func["percentage"],
            "gaps": len(gaps),
            "meets_threshold": (
                line["percentage"]
                >= self._thresholds["line"]
            ),
        }

    @property
    def module_count(self) -> int:
        """Modul sayisi."""
        return len(self._modules)

    @property
    def overall_coverage(self) -> float:
        """Toplam kapsam yuzdesi."""
        line = self.get_line_coverage()
        return line["percentage"]
