"""
Ag analizcisi modulu.

Trafik analizi, protokol incelemesi,
anomali tespiti, baseline karsilastirma,
oruntu esleme.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """Ag analizcisi.

    Attributes:
        _traffic: Trafik kayitlari.
        _baselines: Baseline kayitlari.
        _anomalies: Anomali kayitlari.
        _patterns: Oruntu kayitlari.
        _stats: Istatistikler.
    """

    SUSPICIOUS_PATTERNS: list[dict] = [
        {
            "name": "port_scan",
            "pattern": (
                r"(?i)syn\s+(scan|flood)"
            ),
            "severity": "high",
        },
        {
            "name": "dns_tunnel",
            "pattern": (
                r"(?i)dns.*(tunnel|exfil)"
            ),
            "severity": "critical",
        },
        {
            "name": "large_transfer",
            "pattern": (
                r"(?i)transfer.*(gb|large)"
            ),
            "severity": "medium",
        },
        {
            "name": "unusual_protocol",
            "pattern": (
                r"(?i)(icmp|gre)\s*tunnel"
            ),
            "severity": "high",
        },
    ]

    def __init__(self) -> None:
        """Analizcisi baslatir."""
        self._traffic: list[dict] = []
        self._baselines: dict[str, dict] = {}
        self._anomalies: list[dict] = []
        self._patterns: list[dict] = list(
            self.SUSPICIOUS_PATTERNS
        )
        self._stats: dict[str, int] = {
            "packets_analyzed": 0,
            "anomalies_found": 0,
            "patterns_matched": 0,
        }
        logger.info(
            "NetworkAnalyzer baslatildi"
        )

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)

    def analyze_traffic(
        self,
        source_ip: str = "",
        dest_ip: str = "",
        protocol: str = "TCP",
        port: int = 0,
        payload_size: int = 0,
        description: str = "",
    ) -> dict[str, Any]:
        """Trafik analiz eder.

        Args:
            source_ip: Kaynak IP.
            dest_ip: Hedef IP.
            protocol: Protokol.
            port: Port.
            payload_size: Yuk boyutu.
            description: Aciklama.

        Returns:
            Analiz bilgisi.
        """
        try:
            tid = f"tr_{uuid4()!s:.8}"
            entry = {
                "traffic_id": tid,
                "source_ip": source_ip,
                "dest_ip": dest_ip,
                "protocol": protocol,
                "port": port,
                "payload_size": payload_size,
                "description": description,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._traffic.append(entry)
            self._stats[
                "packets_analyzed"
            ] += 1

            suspicious = False
            matched: list[str] = []
            for p in self._patterns:
                if re.search(
                    p["pattern"], description
                ):
                    suspicious = True
                    matched.append(p["name"])
                    self._stats[
                        "patterns_matched"
                    ] += 1

            return {
                "traffic_id": tid,
                "suspicious": suspicious,
                "matched_patterns": matched,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def inspect_protocol(
        self,
        protocol: str = "",
        data: str = "",
    ) -> dict[str, Any]:
        """Protokol inceler.

        Args:
            protocol: Protokol adi.
            data: Protokol verisi.

        Returns:
            Inceleme bilgisi.
        """
        try:
            allowed = [
                "TCP", "UDP", "HTTP",
                "HTTPS", "DNS", "SSH",
                "SMTP", "FTP",
            ]
            known = (
                protocol.upper() in allowed
            )
            anomalous = not known

            issues: list[str] = []
            if not known:
                issues.append(
                    f"Bilinmeyen protokol: "
                    f"{protocol}"
                )
            if data and len(data) > 10000:
                issues.append(
                    "Buyuk veri paketi"
                )

            return {
                "protocol": protocol,
                "known": known,
                "anomalous": anomalous,
                "issues": issues,
                "inspected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "inspected": False,
                "error": str(e),
            }

    def set_baseline(
        self,
        metric: str = "",
        avg_value: float = 0.0,
        std_dev: float = 0.0,
        max_value: float = 0.0,
    ) -> dict[str, Any]:
        """Baseline ayarlar.

        Args:
            metric: Metrik adi.
            avg_value: Ortalama deger.
            std_dev: Standart sapma.
            max_value: Maksimum deger.

        Returns:
            Ayar bilgisi.
        """
        try:
            self._baselines[metric] = {
                "avg": avg_value,
                "std_dev": std_dev,
                "max": max_value,
                "set_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            return {
                "metric": metric,
                "avg": avg_value,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def check_anomaly(
        self,
        metric: str = "",
        current_value: float = 0.0,
    ) -> dict[str, Any]:
        """Anomali kontrol eder.

        Args:
            metric: Metrik adi.
            current_value: Mevcut deger.

        Returns:
            Kontrol bilgisi.
        """
        try:
            baseline = self._baselines.get(
                metric
            )
            if not baseline:
                return {
                    "checked": True,
                    "anomaly": False,
                    "reason": (
                        "Baseline yok"
                    ),
                }

            threshold = (
                baseline["avg"]
                + 3 * baseline["std_dev"]
            )
            anomaly = (
                current_value > threshold
            )

            if anomaly:
                aid = f"an_{uuid4()!s:.8}"
                record = {
                    "anomaly_id": aid,
                    "metric": metric,
                    "value": current_value,
                    "threshold": threshold,
                    "deviation": round(
                        (
                            current_value
                            - baseline["avg"]
                        )
                        / max(
                            baseline["std_dev"],
                            0.001,
                        ),
                        2,
                    ),
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                self._anomalies.append(record)
                self._stats[
                    "anomalies_found"
                ] += 1

            return {
                "metric": metric,
                "current": current_value,
                "threshold": threshold,
                "anomaly": anomaly,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def add_pattern(
        self,
        name: str = "",
        pattern: str = "",
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Oruntu ekler.

        Args:
            name: Oruntu adi.
            pattern: Regex deseni.
            severity: Ciddiyet.

        Returns:
            Ekleme bilgisi.
        """
        try:
            re.compile(pattern)
            self._patterns.append({
                "name": name,
                "pattern": pattern,
                "severity": severity,
            })
            return {
                "name": name,
                "added": True,
            }

        except re.error as e:
            return {
                "added": False,
                "error": f"Gecersiz regex: {e}",
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            return {
                "total_traffic": len(
                    self._traffic
                ),
                "anomalies": len(
                    self._anomalies
                ),
                "baselines": len(
                    self._baselines
                ),
                "patterns": len(
                    self._patterns
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
