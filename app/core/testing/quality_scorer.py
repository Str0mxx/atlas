"""ATLAS Kalite Puanlayici modulu.

Kod kalitesi metrikleri, test kalitesi,
bakim indeksi, teknik borc
ve kalite kapilari.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class QualityScorer:
    """Kalite puanlayici.

    Kod ve test kalitesini puanlar.

    Attributes:
        _metrics: Metrik kayitlari.
        _gates: Kalite kapilari.
    """

    def __init__(self) -> None:
        """Kalite puanlayiciyi baslatir."""
        self._metrics: dict[
            str, dict[str, Any]
        ] = {}
        self._gates: dict[
            str, dict[str, Any]
        ] = {}
        self._debt_items: list[
            dict[str, Any]
        ] = []

        logger.info(
            "QualityScorer baslatildi",
        )

    def score_code_quality(
        self,
        module: str,
        complexity: float = 0.0,
        duplication: float = 0.0,
        doc_coverage: float = 0.0,
        lint_issues: int = 0,
        lines_of_code: int = 0,
    ) -> dict[str, Any]:
        """Kod kalitesini puanlar.

        Args:
            module: Modul adi.
            complexity: Karmasiklik (1-100).
            duplication: Tekrar yuzdesi.
            doc_coverage: Dokumantasyon kapsami.
            lint_issues: Lint sorunu sayisi.
            lines_of_code: Satir sayisi.

        Returns:
            Kalite puani.
        """
        # Puanlama (0-100)
        complexity_score = max(
            0, 100 - complexity,
        )
        duplication_score = max(
            0, 100 - duplication * 2,
        )
        doc_score = doc_coverage
        lint_score = max(
            0, 100 - lint_issues * 5,
        )

        overall = (
            complexity_score * 0.3
            + duplication_score * 0.2
            + doc_score * 0.2
            + lint_score * 0.3
        )

        result = {
            "module": module,
            "complexity_score": round(
                complexity_score, 2,
            ),
            "duplication_score": round(
                duplication_score, 2,
            ),
            "doc_score": round(doc_score, 2),
            "lint_score": round(lint_score, 2),
            "overall": round(overall, 2),
            "lines_of_code": lines_of_code,
        }
        self._metrics[module] = result
        return result

    def score_test_quality(
        self,
        module: str,
        coverage: float = 0.0,
        mutation_score: float = 0.0,
        assertion_density: float = 0.0,
        test_count: int = 0,
    ) -> dict[str, Any]:
        """Test kalitesini puanlar.

        Args:
            module: Modul adi.
            coverage: Kapsam yuzdesi.
            mutation_score: Mutasyon puani.
            assertion_density: Assertion yogunlugu.
            test_count: Test sayisi.

        Returns:
            Kalite puani.
        """
        coverage_score = coverage
        mutation_s = mutation_score * 100
        assertion_s = min(100, assertion_density * 20)

        overall = (
            coverage_score * 0.4
            + mutation_s * 0.3
            + assertion_s * 0.3
        )

        key = f"{module}:test"
        result = {
            "module": module,
            "coverage_score": round(
                coverage_score, 2,
            ),
            "mutation_score": round(
                mutation_s, 2,
            ),
            "assertion_score": round(
                assertion_s, 2,
            ),
            "overall": round(overall, 2),
            "test_count": test_count,
        }
        self._metrics[key] = result
        return result

    def calculate_maintainability(
        self,
        module: str,
        complexity: float = 0.0,
        lines_of_code: int = 0,
        comment_ratio: float = 0.0,
    ) -> dict[str, Any]:
        """Bakim indeksini hesaplar.

        Args:
            module: Modul adi.
            complexity: Siklomatik karmasiklik.
            lines_of_code: Satir sayisi.
            comment_ratio: Yorum orani.

        Returns:
            Bakim indeksi.
        """
        # Basitlestirilmis MI formulu
        import math
        vol = max(1, lines_of_code)
        mi = max(0, min(100,
            171
            - 5.2 * math.log(vol)
            - 0.23 * complexity
            + 16.2 * math.log(
                max(1, comment_ratio * 100)
            )
        ))

        if mi >= 80:
            grade = "A"
        elif mi >= 60:
            grade = "B"
        elif mi >= 40:
            grade = "C"
        else:
            grade = "D"

        return {
            "module": module,
            "maintainability_index": round(mi, 2),
            "grade": grade,
            "complexity": complexity,
            "lines_of_code": lines_of_code,
        }

    def add_technical_debt(
        self,
        module: str,
        description: str,
        severity: str = "medium",
        estimated_hours: float = 1.0,
    ) -> dict[str, Any]:
        """Teknik borc ekler.

        Args:
            module: Modul adi.
            description: Aciklama.
            severity: Ciddiyet.
            estimated_hours: Tahmini saat.

        Returns:
            Borc bilgisi.
        """
        item = {
            "module": module,
            "description": description,
            "severity": severity,
            "estimated_hours": estimated_hours,
        }
        self._debt_items.append(item)
        return item

    def get_technical_debt(
        self,
    ) -> dict[str, Any]:
        """Teknik borc ozetini getirir.

        Returns:
            Borc ozeti.
        """
        total_hours = sum(
            d["estimated_hours"]
            for d in self._debt_items
        )
        by_severity: dict[str, int] = {}
        for d in self._debt_items:
            sev = d["severity"]
            by_severity[sev] = (
                by_severity.get(sev, 0) + 1
            )

        return {
            "total_items": len(self._debt_items),
            "total_hours": round(total_hours, 1),
            "by_severity": by_severity,
            "items": list(self._debt_items),
        }

    def add_quality_gate(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str = ">=",
    ) -> dict[str, Any]:
        """Kalite kapisi ekler.

        Args:
            name: Kapi adi.
            metric: Metrik adi.
            threshold: Esik degeri.
            operator: Karsilastirma operatoru.

        Returns:
            Kapi bilgisi.
        """
        gate = {
            "name": name,
            "metric": metric,
            "threshold": threshold,
            "operator": operator,
        }
        self._gates[name] = gate
        return gate

    def check_quality_gates(
        self,
        values: dict[str, float],
    ) -> dict[str, Any]:
        """Kalite kapilarini kontrol eder.

        Args:
            values: Metrik degerleri.

        Returns:
            Kontrol sonucu.
        """
        results = []
        all_passed = True

        for name, gate in self._gates.items():
            metric = gate["metric"]
            threshold = gate["threshold"]
            op = gate["operator"]
            actual = values.get(metric, 0.0)

            if op == ">=":
                passed = actual >= threshold
            elif op == ">":
                passed = actual > threshold
            elif op == "<=":
                passed = actual <= threshold
            elif op == "<":
                passed = actual < threshold
            elif op == "==":
                passed = actual == threshold
            else:
                passed = actual >= threshold

            if not passed:
                all_passed = False

            results.append({
                "gate": name,
                "metric": metric,
                "threshold": threshold,
                "actual": actual,
                "passed": passed,
            })

        return {
            "all_passed": all_passed,
            "results": results,
            "total_gates": len(self._gates),
            "passed_count": sum(
                1 for r in results if r["passed"]
            ),
        }

    def get_overall_score(
        self,
    ) -> dict[str, Any]:
        """Genel puan getirir.

        Returns:
            Genel puan.
        """
        if not self._metrics:
            return {"score": 0.0, "modules": 0}

        scores = [
            m.get("overall", 0.0)
            for m in self._metrics.values()
        ]
        avg = sum(scores) / len(scores)

        return {
            "score": round(avg, 2),
            "modules": len(self._metrics),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
        }

    @property
    def metric_count(self) -> int:
        """Metrik sayisi."""
        return len(self._metrics)

    @property
    def gate_count(self) -> int:
        """Kapi sayisi."""
        return len(self._gates)

    @property
    def debt_count(self) -> int:
        """Borc sayisi."""
        return len(self._debt_items)
