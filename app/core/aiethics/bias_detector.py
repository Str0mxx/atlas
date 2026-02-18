"""
Onyargi tespitcisi modulu.

Onyargi tespiti, kalip analizi,
istatistiksel test, demografik parite,
farkli etki.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class BiasDetector:
    """Onyargi tespitcisi.

    Attributes:
        _detections: Tespitler.
        _datasets: Veri setleri.
        _stats: Istatistikler.
    """

    BIAS_TYPES: list[str] = [
        "demographic",
        "representation",
        "measurement",
        "aggregation",
        "evaluation",
        "selection",
        "historical",
        "label",
    ]

    SEVERITY_LEVELS: list[str] = [
        "none",
        "low",
        "medium",
        "high",
        "critical",
    ]

    def __init__(
        self,
        parity_threshold: float = 0.8,
        impact_threshold: float = 0.8,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            parity_threshold: Parite esigi.
            impact_threshold: Etki esigi.
        """
        self._parity_threshold = (
            parity_threshold
        )
        self._impact_threshold = (
            impact_threshold
        )
        self._detections: dict[
            str, dict
        ] = {}
        self._datasets: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "scans_done": 0,
            "biases_found": 0,
            "high_severity": 0,
            "datasets_analyzed": 0,
        }
        logger.info(
            "BiasDetector baslatildi"
        )

    @property
    def detection_count(self) -> int:
        """Tespit sayisi."""
        return len(self._detections)

    def add_dataset(
        self,
        name: str = "",
        records: list[dict] | None = None,
        protected_attrs: (
            list[str] | None
        ) = None,
        outcome_attr: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Veri seti ekler.

        Args:
            name: Ad.
            records: Kayitlar.
            protected_attrs: Korunan ozellikler.
            outcome_attr: Sonuc ozelligi.
            metadata: Ek veri.

        Returns:
            Ekleme bilgisi.
        """
        try:
            did = f"bds_{uuid4()!s:.8}"
            self._datasets[did] = {
                "dataset_id": did,
                "name": name,
                "records": records or [],
                "protected_attrs": (
                    protected_attrs or []
                ),
                "outcome_attr": outcome_attr,
                "metadata": metadata or {},
                "added_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            return {
                "dataset_id": did,
                "record_count": len(
                    records or []
                ),
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def scan_for_bias(
        self,
        dataset_id: str = "",
    ) -> dict[str, Any]:
        """Onyargi taramas yapar.

        Args:
            dataset_id: Veri seti ID.

        Returns:
            Tarama bilgisi.
        """
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "scanned": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }

            bid = f"bdet_{uuid4()!s:.8}"
            findings: list[dict] = []
            records = ds["records"]
            pattrs = ds["protected_attrs"]
            outcome = ds["outcome_attr"]

            if not records or not pattrs:
                self._detections[bid] = {
                    "detection_id": bid,
                    "dataset_id": dataset_id,
                    "findings": [],
                    "bias_score": 0.0,
                    "severity": "none",
                    "scanned_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                }
                self._stats[
                    "scans_done"
                ] += 1
                return {
                    "detection_id": bid,
                    "findings": [],
                    "bias_score": 0.0,
                    "severity": "none",
                    "scanned": True,
                }

            # Her korunan ozellik icin
            for attr in pattrs:
                # Demografik parite
                dp = (
                    self._check_demographic_parity(
                        records,
                        attr,
                        outcome,
                    )
                )
                if dp["has_bias"]:
                    findings.append(dp)

                # Farkli etki
                di = (
                    self._check_disparate_impact(
                        records,
                        attr,
                        outcome,
                    )
                )
                if di["has_bias"]:
                    findings.append(di)

                # Temsil
                rep = (
                    self._check_representation(
                        records, attr
                    )
                )
                if rep["has_bias"]:
                    findings.append(rep)

            # Genel puan
            if findings:
                bias_score = sum(
                    f.get("score", 0)
                    for f in findings
                ) / len(findings)
            else:
                bias_score = 0.0

            severity = (
                self._get_severity(
                    bias_score
                )
            )

            self._detections[bid] = {
                "detection_id": bid,
                "dataset_id": dataset_id,
                "findings": findings,
                "bias_score": round(
                    bias_score, 4
                ),
                "severity": severity,
                "scanned_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "scans_done"
            ] += 1
            self._stats[
                "datasets_analyzed"
            ] += 1
            self._stats[
                "biases_found"
            ] += len(findings)
            if severity in (
                "high",
                "critical",
            ):
                self._stats[
                    "high_severity"
                ] += 1

            return {
                "detection_id": bid,
                "findings": findings,
                "finding_count": len(
                    findings
                ),
                "bias_score": round(
                    bias_score, 4
                ),
                "severity": severity,
                "scanned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def _check_demographic_parity(
        self,
        records: list[dict],
        attr: str,
        outcome: str,
    ) -> dict[str, Any]:
        """Demografik parite kontrolu."""
        groups: dict[str, list] = {}
        for r in records:
            g = str(r.get(attr, "unknown"))
            groups.setdefault(g, [])
            groups[g].append(r)

        if len(groups) < 2:
            return {
                "has_bias": False,
                "type": "demographic",
            }

        rates: dict[str, float] = {}
        for g, recs in groups.items():
            pos = sum(
                1
                for r in recs
                if r.get(outcome)
            )
            rates[g] = (
                pos / len(recs)
                if recs
                else 0
            )

        if not rates:
            return {
                "has_bias": False,
                "type": "demographic",
            }

        max_rate = max(rates.values())
        min_rate = min(rates.values())
        gap = max_rate - min_rate

        has_bias = (
            gap > 1.0 - self._parity_threshold
        )

        return {
            "has_bias": has_bias,
            "type": "demographic",
            "attribute": attr,
            "rates": {
                k: round(v, 4)
                for k, v in rates.items()
            },
            "gap": round(gap, 4),
            "score": round(
                min(1.0, gap * 2), 4
            ),
        }

    def _check_disparate_impact(
        self,
        records: list[dict],
        attr: str,
        outcome: str,
    ) -> dict[str, Any]:
        """Farkli etki kontrolu."""
        groups: dict[str, list] = {}
        for r in records:
            g = str(r.get(attr, "unknown"))
            groups.setdefault(g, [])
            groups[g].append(r)

        if len(groups) < 2:
            return {
                "has_bias": False,
                "type": "disparate_impact",
            }

        rates: dict[str, float] = {}
        for g, recs in groups.items():
            pos = sum(
                1
                for r in recs
                if r.get(outcome)
            )
            rates[g] = (
                pos / len(recs)
                if recs
                else 0
            )

        max_rate = max(rates.values())
        if max_rate == 0:
            return {
                "has_bias": False,
                "type": "disparate_impact",
            }

        min_rate = min(rates.values())
        ratio = min_rate / max_rate

        has_bias = (
            ratio < self._impact_threshold
        )

        return {
            "has_bias": has_bias,
            "type": "disparate_impact",
            "attribute": attr,
            "ratio": round(ratio, 4),
            "threshold": (
                self._impact_threshold
            ),
            "score": round(
                max(0, 1.0 - ratio), 4
            ),
        }

    def _check_representation(
        self,
        records: list[dict],
        attr: str,
    ) -> dict[str, Any]:
        """Temsil kontrolu."""
        groups: dict[str, int] = {}
        for r in records:
            g = str(r.get(attr, "unknown"))
            groups[g] = (
                groups.get(g, 0) + 1
            )

        total = len(records)
        if total == 0 or not groups:
            return {
                "has_bias": False,
                "type": "representation",
            }

        expected = total / len(groups)
        max_dev = 0.0
        for count in groups.values():
            dev = abs(
                count - expected
            ) / max(1, expected)
            max_dev = max(max_dev, dev)

        has_bias = max_dev > 0.5

        return {
            "has_bias": has_bias,
            "type": "representation",
            "attribute": attr,
            "group_counts": groups,
            "max_deviation": round(
                max_dev, 4
            ),
            "score": round(
                min(1.0, max_dev), 4
            ),
        }

    def _get_severity(
        self, score: float
    ) -> str:
        """Ciddiyet seviyesi."""
        if score < 0.1:
            return "none"
        if score < 0.3:
            return "low"
        if score < 0.5:
            return "medium"
        if score < 0.7:
            return "high"
        return "critical"

    def analyze_patterns(
        self,
        dataset_id: str = "",
    ) -> dict[str, Any]:
        """Kalip analizi yapar.

        Args:
            dataset_id: Veri seti ID.

        Returns:
            Analiz bilgisi.
        """
        try:
            ds = self._datasets.get(
                dataset_id
            )
            if not ds:
                return {
                    "analyzed": False,
                    "error": (
                        "Veri seti bulunamadi"
                    ),
                }

            records = ds["records"]
            patterns: list[dict] = []

            # Ozellik dagilimi analizi
            for attr in ds[
                "protected_attrs"
            ]:
                vals: dict[str, int] = {}
                for r in records:
                    v = str(
                        r.get(
                            attr, "unknown"
                        )
                    )
                    vals[v] = (
                        vals.get(v, 0) + 1
                    )

                total = len(records)
                if total > 0:
                    dist = {
                        k: round(
                            c / total, 4
                        )
                        for k, c in vals.items()
                    }
                    entropy = -sum(
                        p * math.log2(p)
                        for p in dist.values()
                        if p > 0
                    )
                    patterns.append({
                        "attribute": attr,
                        "distribution": dist,
                        "entropy": round(
                            entropy, 4
                        ),
                        "unique_values": len(
                            vals
                        ),
                    })

            return {
                "dataset_id": dataset_id,
                "patterns": patterns,
                "pattern_count": len(
                    patterns
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_detection_info(
        self, detection_id: str = ""
    ) -> dict[str, Any]:
        """Tespit bilgisi getirir."""
        try:
            det = self._detections.get(
                detection_id
            )
            if not det:
                return {
                    "retrieved": False,
                    "error": (
                        "Tespit bulunamadi"
                    ),
                }
            return {
                **det,
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
                "total_detections": len(
                    self._detections
                ),
                "total_datasets": len(
                    self._datasets
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
