"""ATLAS Log Analizcisi modulu.

Desen tespiti, anomali tespiti,
hata kumeleme, trend analizi
ve kok neden ipuclari.
"""

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Log analizcisi.

    Log verilerini analiz eder ve
    icerik cikarir.

    Attributes:
        _patterns: Tespit edilen desenler.
        _anomalies: Anomali kayitlari.
    """

    def __init__(
        self,
        anomaly_threshold: float = 2.0,
    ) -> None:
        """Log analizcisini baslatir.

        Args:
            anomaly_threshold: Anomali esigi.
        """
        self._anomaly_threshold = anomaly_threshold
        self._patterns: list[
            dict[str, Any]
        ] = []
        self._anomalies: list[
            dict[str, Any]
        ] = []
        self._analyses = 0

        logger.info(
            "LogAnalyzer baslatildi",
        )

    def detect_patterns(
        self,
        logs: list[dict[str, Any]],
        min_frequency: int = 3,
    ) -> list[dict[str, Any]]:
        """Desen tespit eder.

        Args:
            logs: Log kayitlari.
            min_frequency: Min frekans.

        Returns:
            Desen listesi.
        """
        self._analyses += 1
        messages = [
            log.get("message", "")
            for log in logs
        ]
        counts = Counter(messages)

        patterns = []
        for msg, count in counts.most_common():
            if count >= min_frequency:
                patterns.append({
                    "message": msg,
                    "count": count,
                    "frequency": round(
                        count / len(logs), 4,
                    ) if logs else 0.0,
                })

        self._patterns = patterns
        return patterns

    def detect_anomalies(
        self,
        logs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Anomali tespit eder.

        Args:
            logs: Log kayitlari.

        Returns:
            Anomali listesi.
        """
        self._analyses += 1
        if not logs:
            return []

        # Seviye bazli analiz
        level_counts: dict[str, int] = {}
        for log in logs:
            level = log.get("level", "info")
            level_counts[level] = (
                level_counts.get(level, 0) + 1
            )

        total = len(logs)
        avg = total / max(len(level_counts), 1)

        anomalies = []
        for level, count in level_counts.items():
            if count > avg * self._anomaly_threshold:
                anomalies.append({
                    "type": "high_frequency",
                    "level": level,
                    "count": count,
                    "average": round(avg, 2),
                    "ratio": round(
                        count / avg, 2,
                    ),
                })

        # Hata artisi anomalisi
        error_count = level_counts.get("error", 0)
        critical_count = level_counts.get(
            "critical", 0,
        )
        if error_count + critical_count > total * 0.3:
            anomalies.append({
                "type": "error_spike",
                "error_count": error_count,
                "critical_count": critical_count,
                "error_ratio": round(
                    (error_count + critical_count)
                    / total,
                    4,
                ),
            })

        self._anomalies = anomalies
        return anomalies

    def cluster_errors(
        self,
        logs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Hatalari kumeler.

        Args:
            logs: Log kayitlari.

        Returns:
            Kume listesi.
        """
        self._analyses += 1
        errors = [
            log for log in logs
            if log.get("level", "")
            in ("error", "critical")
        ]

        if not errors:
            return []

        # Mesaja gore kumele
        clusters: dict[
            str, list[dict[str, Any]]
        ] = {}
        for err in errors:
            msg = err.get("message", "unknown")
            # Basit kumeleme: ilk 50 karakter
            key = msg[:50]
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(err)

        result = []
        for key, items in clusters.items():
            result.append({
                "pattern": key,
                "count": len(items),
                "sources": list(set(
                    i.get("source", "")
                    for i in items
                )),
                "first_seen": min(
                    i.get("timestamp", 0)
                    for i in items
                ),
                "last_seen": max(
                    i.get("timestamp", 0)
                    for i in items
                ),
            })

        result.sort(
            key=lambda x: x["count"],
            reverse=True,
        )
        return result

    def analyze_trends(
        self,
        logs: list[dict[str, Any]],
        bucket_size: int = 60,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            logs: Log kayitlari.
            bucket_size: Kova boyutu (sn).

        Returns:
            Trend bilgisi.
        """
        self._analyses += 1
        if not logs:
            return {"trend": "stable", "buckets": []}

        # Zamana gore kovalara ayir
        timestamps = [
            log.get("timestamp", 0)
            for log in logs
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        buckets: list[int] = []
        current = min_ts
        while current <= max_ts:
            count = sum(
                1 for ts in timestamps
                if current <= ts < current + bucket_size
            )
            buckets.append(count)
            current += bucket_size

        if len(buckets) < 2:
            trend = "stable"
        elif buckets[-1] > buckets[0] * 1.5:
            trend = "increasing"
        elif buckets[-1] < buckets[0] * 0.5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "buckets": buckets,
            "total_logs": len(logs),
            "bucket_count": len(buckets),
        }

    def suggest_root_cause(
        self,
        error_logs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Kok neden ipuclari verir.

        Args:
            error_logs: Hata loglari.

        Returns:
            Ipucu listesi.
        """
        self._analyses += 1
        hints = []

        if not error_logs:
            return hints

        messages = [
            e.get("message", "").lower()
            for e in error_logs
        ]
        combined = " ".join(messages)

        keywords = {
            "timeout": "Network or service timeout - check connectivity and service health",
            "connection": "Connection issue - verify database/service availability",
            "memory": "Memory issue - check for leaks or increase allocation",
            "permission": "Permission denied - verify access rights",
            "disk": "Disk issue - check storage space",
            "authentication": "Auth failure - verify credentials",
            "rate limit": "Rate limiting - reduce request frequency",
        }

        for keyword, hint in keywords.items():
            if keyword in combined:
                count = combined.count(keyword)
                hints.append({
                    "keyword": keyword,
                    "hint": hint,
                    "occurrences": count,
                })

        # Kaynak bazli ipucu
        sources = Counter(
            e.get("source", "unknown")
            for e in error_logs
        )
        top_source = sources.most_common(1)
        if top_source:
            src, cnt = top_source[0]
            if cnt > len(error_logs) * 0.5:
                hints.append({
                    "keyword": "concentrated_source",
                    "hint": f"Most errors from '{src}' - investigate this component",
                    "occurrences": cnt,
                })

        return hints

    @property
    def pattern_count(self) -> int:
        """Desen sayisi."""
        return len(self._patterns)

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return self._analyses
