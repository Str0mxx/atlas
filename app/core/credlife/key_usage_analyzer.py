"""
Anahtar kullanim analizcisi modulu.

Kullanim kaliplari, anomali tespiti,
kullanilmayan anahtarlar, yuksek riskli
kullanim, oneriler.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class KeyUsageAnalyzer:
    """Anahtar kullanim analizcisi.

    Attributes:
        _usage_logs: Kullanim kayitlari.
        _patterns: Kalip kayitlari.
        _anomalies: Anomali kayitlari.
        _recommendations: Oneriler.
        _stats: Istatistikler.
    """

    RISK_LEVELS: list[str] = [
        "low",
        "medium",
        "high",
        "critical",
    ]

    def __init__(self) -> None:
        """Analizcisi baslatir."""
        self._usage_logs: dict[
            str, list
        ] = {}
        self._patterns: dict[
            str, dict
        ] = {}
        self._anomalies: list[dict] = []
        self._recommendations: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "logs_recorded": 0,
            "analyses_run": 0,
            "anomalies_detected": 0,
            "unused_found": 0,
            "recommendations_made": 0,
        }
        logger.info(
            "KeyUsageAnalyzer baslatildi"
        )

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)

    def record_usage(
        self,
        key_id: str = "",
        action: str = "",
        source_ip: str = "",
        user_agent: str = "",
        endpoint: str = "",
        response_code: int = 200,
    ) -> dict[str, Any]:
        """Kullanim kaydeder.

        Args:
            key_id: Anahtar ID.
            action: Eylem.
            source_ip: Kaynak IP.
            user_agent: Kullanici aracisi.
            endpoint: Endpoint.
            response_code: Yanit kodu.

        Returns:
            Kayit bilgisi.
        """
        try:
            if (
                key_id
                not in self._usage_logs
            ):
                self._usage_logs[
                    key_id
                ] = []

            log = {
                "action": action,
                "source_ip": source_ip,
                "user_agent": user_agent,
                "endpoint": endpoint,
                "response_code": (
                    response_code
                ),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._usage_logs[
                key_id
            ].append(log)
            self._stats[
                "logs_recorded"
            ] += 1

            return {
                "key_id": key_id,
                "total_logs": len(
                    self._usage_logs[key_id]
                ),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def analyze_patterns(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Kullanim kaliplarini analiz eder.

        Args:
            key_id: Anahtar ID.

        Returns:
            Analiz bilgisi.
        """
        try:
            self._stats[
                "analyses_run"
            ] += 1
            logs = self._usage_logs.get(
                key_id, []
            )
            if not logs:
                return {
                    "analyzed": True,
                    "key_id": key_id,
                    "total_usage": 0,
                    "patterns": {},
                }

            ips = set(
                l["source_ip"]
                for l in logs
                if l["source_ip"]
            )
            endpoints = {}
            for l in logs:
                ep = l["endpoint"]
                if ep:
                    endpoints[ep] = (
                        endpoints.get(
                            ep, 0
                        )
                        + 1
                    )
            errors = sum(
                1
                for l in logs
                if l["response_code"] >= 400
            )

            pattern = {
                "total_usage": len(logs),
                "unique_ips": len(ips),
                "endpoints": endpoints,
                "error_count": errors,
                "error_rate": round(
                    errors
                    / max(len(logs), 1),
                    2,
                ),
            }
            self._patterns[key_id] = pattern

            return {
                "key_id": key_id,
                "analyzed": True,
                **pattern,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def detect_anomalies(
        self,
        key_id: str = "",
        max_ips: int = 5,
        max_error_rate: float = 0.3,
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            key_id: Anahtar ID.
            max_ips: Max IP sayisi.
            max_error_rate: Max hata orani.

        Returns:
            Anomali bilgisi.
        """
        try:
            logs = self._usage_logs.get(
                key_id, []
            )
            if not logs:
                return {
                    "key_id": key_id,
                    "anomalies": [],
                    "detected": True,
                }

            anomalies: list[dict] = []
            ips = set(
                l["source_ip"]
                for l in logs
                if l["source_ip"]
            )
            if len(ips) > max_ips:
                anomalies.append({
                    "type": "too_many_ips",
                    "detail": (
                        f"{len(ips)} benzersiz IP"
                    ),
                    "severity": "high",
                })

            errors = sum(
                1
                for l in logs
                if l["response_code"] >= 400
            )
            erate = errors / max(
                len(logs), 1
            )
            if erate > max_error_rate:
                anomalies.append({
                    "type": (
                        "high_error_rate"
                    ),
                    "detail": (
                        f"Hata orani: "
                        f"{round(erate, 2)}"
                    ),
                    "severity": "medium",
                })

            recent = logs[-10:]
            recent_ips = set(
                l["source_ip"]
                for l in recent
                if l["source_ip"]
            )
            if len(recent_ips) > 3:
                anomalies.append({
                    "type": "rapid_ip_change",
                    "detail": (
                        "Son isteklerde "
                        "coklu IP"
                    ),
                    "severity": "critical",
                })

            for a in anomalies:
                aid = f"an_{uuid4()!s:.8}"
                a["anomaly_id"] = aid
                a["key_id"] = key_id
                a["detected_at"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )
                self._anomalies.append(a)

            self._stats[
                "anomalies_detected"
            ] += len(anomalies)

            return {
                "key_id": key_id,
                "anomalies": anomalies,
                "count": len(anomalies),
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def find_unused_keys(
        self,
        all_key_ids: list[str] | None = None,
        min_days_idle: int = 30,
    ) -> dict[str, Any]:
        """Kullanilmayan anahtarlari bulur.

        Args:
            all_key_ids: Tum anahtar IDleri.
            min_days_idle: Min bos gun.

        Returns:
            Kullanilmayan liste.
        """
        try:
            keys = all_key_ids or []
            unused: list[dict] = []
            for kid in keys:
                logs = self._usage_logs.get(
                    kid, []
                )
                if not logs:
                    unused.append({
                        "key_id": kid,
                        "reason": "never_used",
                        "risk": "high",
                    })
                elif len(logs) < 3:
                    unused.append({
                        "key_id": kid,
                        "reason": (
                            "rarely_used"
                        ),
                        "risk": "medium",
                    })

            self._stats[
                "unused_found"
            ] += len(unused)

            return {
                "unused_keys": unused,
                "count": len(unused),
                "total_checked": len(keys),
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_recommendations(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Oneriler getirir.

        Args:
            key_id: Anahtar ID.

        Returns:
            Oneri listesi.
        """
        try:
            recs: list[dict] = []
            logs = self._usage_logs.get(
                key_id, []
            )

            if not logs:
                recs.append({
                    "type": "remove_unused",
                    "detail": (
                        "Kullanilmayan "
                        "anahtar kaldirin"
                    ),
                    "priority": "high",
                })
            else:
                errors = sum(
                    1
                    for l in logs
                    if l[
                        "response_code"
                    ] >= 400
                )
                erate = errors / max(
                    len(logs), 1
                )
                if erate > 0.5:
                    recs.append({
                        "type": (
                            "investigate_errors"
                        ),
                        "detail": (
                            "Yuksek hata orani "
                            "inceleyin"
                        ),
                        "priority": "critical",
                    })

                ips = set(
                    l["source_ip"]
                    for l in logs
                    if l["source_ip"]
                )
                if len(ips) > 10:
                    recs.append({
                        "type": (
                            "restrict_ips"
                        ),
                        "detail": (
                            "IP sinirlamasi "
                            "ekleyin"
                        ),
                        "priority": "medium",
                    })

            for r in recs:
                r["key_id"] = key_id
                self._recommendations.append(
                    r
                )
            self._stats[
                "recommendations_made"
            ] += len(recs)

            return {
                "key_id": key_id,
                "recommendations": recs,
                "count": len(recs),
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
                "total_keys_tracked": len(
                    self._usage_logs
                ),
                "total_anomalies": len(
                    self._anomalies
                ),
                "total_recommendations": (
                    len(self._recommendations)
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
