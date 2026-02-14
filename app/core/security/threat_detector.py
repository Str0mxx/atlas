"""ATLAS Tehdit Tespit modulu.

Sizma tespiti, anomali algilama, saldiri
deseni tanima, brute force ve injection
tespiti.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.security_hardening import (
    ThreatLevel,
    ThreatRecord,
    ThreatType,
)

logger = logging.getLogger(__name__)


class ThreatDetector:
    """Tehdit tespit sistemi.

    Cesitli tehdit turlerini tespit eder
    ve siniflandirir.

    Attributes:
        _threats: Tespit edilen tehditler.
        _patterns: Saldiri desenleri.
        _login_attempts: Giris denemeleri.
        _request_counts: Istek sayaclari.
        _max_login_attempts: Maks giris denemesi.
    """

    def __init__(
        self,
        max_login_attempts: int = 5,
    ) -> None:
        """Tehdit tespitini baslatir.

        Args:
            max_login_attempts: Maks giris denemesi.
        """
        self._threats: list[ThreatRecord] = []
        self._patterns: dict[str, dict[str, Any]] = {
            "sql_injection": {
                "keywords": [
                    "' OR ", "1=1", "DROP TABLE",
                    "UNION SELECT", "; DELETE",
                    "' --", "/*", "*/",
                ],
                "type": ThreatType.INJECTION,
            },
            "xss": {
                "keywords": [
                    "<script", "javascript:", "onerror=",
                    "onload=", "<iframe", "eval(",
                ],
                "type": ThreatType.XSS,
            },
            "command_injection": {
                "keywords": [
                    "; rm ", "| cat ", "&& wget",
                    "$(", "`", "| bash",
                ],
                "type": ThreatType.INJECTION,
            },
            "path_traversal": {
                "keywords": [
                    "../", "..\\", "%2e%2e",
                    "/etc/passwd", "/etc/shadow",
                ],
                "type": ThreatType.INTRUSION,
            },
        }
        self._login_attempts: dict[str, list[str]] = {}
        self._request_counts: dict[str, int] = {}
        self._baselines: dict[str, float] = {}
        self._max_login_attempts = max(1, max_login_attempts)

        logger.info(
            "ThreatDetector baslatildi (max_attempts=%d)",
            self._max_login_attempts,
        )

    def detect_intrusion(
        self,
        source_ip: str,
        request_path: str,
        payload: str = "",
    ) -> ThreatRecord | None:
        """Sizma tespiti yapar.

        Args:
            source_ip: Kaynak IP.
            request_path: Istek yolu.
            payload: Veri yuku.

        Returns:
            Tehdit kaydi veya None.
        """
        combined = f"{request_path} {payload}".upper()

        for pattern_name, pattern_data in self._patterns.items():
            for keyword in pattern_data["keywords"]:
                if keyword.upper() in combined:
                    threat = ThreatRecord(
                        threat_type=pattern_data["type"],
                        level=ThreatLevel.HIGH,
                        source=source_ip,
                        target=request_path,
                        description=(
                            f"{pattern_name} tespit edildi: "
                            f"{keyword}"
                        ),
                        blocked=True,
                    )
                    self._threats.append(threat)
                    logger.warning(
                        "Sizma tespiti: %s (%s)",
                        pattern_name, source_ip,
                    )
                    return threat

        return None

    def detect_anomaly(
        self,
        metric_name: str,
        value: float,
        threshold_factor: float = 2.0,
    ) -> ThreatRecord | None:
        """Anomali tespiti yapar.

        Args:
            metric_name: Metrik adi.
            value: Mevcut deger.
            threshold_factor: Esik carpani.

        Returns:
            Tehdit kaydi veya None.
        """
        baseline = self._baselines.get(metric_name)

        if baseline is None:
            self._baselines[metric_name] = value
            return None

        if baseline > 0 and value > baseline * threshold_factor:
            threat = ThreatRecord(
                threat_type=ThreatType.ANOMALY,
                level=ThreatLevel.MEDIUM,
                source=metric_name,
                description=(
                    f"Anomali: {value:.1f} "
                    f"(baseline: {baseline:.1f}, "
                    f"factor: {threshold_factor}x)"
                ),
            )
            self._threats.append(threat)
            return threat

        # Baseline guncelle (hareketli ort.)
        self._baselines[metric_name] = (
            baseline * 0.9 + value * 0.1
        )
        return None

    def detect_brute_force(
        self,
        identifier: str,
        success: bool = False,
    ) -> ThreatRecord | None:
        """Brute force tespiti yapar.

        Args:
            identifier: Kullanici/IP.
            success: Giris basarili mi.

        Returns:
            Tehdit kaydi veya None.
        """
        if identifier not in self._login_attempts:
            self._login_attempts[identifier] = []

        if success:
            self._login_attempts[identifier] = []
            return None

        self._login_attempts[identifier].append(
            datetime.now(timezone.utc).isoformat(),
        )

        attempts = len(self._login_attempts[identifier])

        if attempts >= self._max_login_attempts:
            level = ThreatLevel.HIGH
            if attempts >= self._max_login_attempts * 2:
                level = ThreatLevel.CRITICAL

            threat = ThreatRecord(
                threat_type=ThreatType.BRUTE_FORCE,
                level=level,
                source=identifier,
                description=(
                    f"Brute force: {attempts} basarisiz deneme"
                ),
                blocked=True,
            )
            self._threats.append(threat)
            logger.warning(
                "Brute force tespiti: %s (%d deneme)",
                identifier, attempts,
            )
            return threat

        return None

    def detect_ddos(
        self,
        source_ip: str,
        requests_per_second: int,
        threshold: int = 100,
    ) -> ThreatRecord | None:
        """DDoS tespiti yapar.

        Args:
            source_ip: Kaynak IP.
            requests_per_second: Saniyedeki istek.
            threshold: Esik degeri.

        Returns:
            Tehdit kaydi veya None.
        """
        if requests_per_second > threshold:
            level = ThreatLevel.HIGH
            if requests_per_second > threshold * 5:
                level = ThreatLevel.CRITICAL

            threat = ThreatRecord(
                threat_type=ThreatType.DDOS,
                level=level,
                source=source_ip,
                description=(
                    f"DDoS: {requests_per_second} req/s "
                    f"(esik: {threshold})"
                ),
                blocked=True,
            )
            self._threats.append(threat)
            return threat

        return None

    def add_pattern(
        self,
        name: str,
        keywords: list[str],
        threat_type: ThreatType,
    ) -> None:
        """Saldiri deseni ekler.

        Args:
            name: Desen adi.
            keywords: Anahtar kelimeler.
            threat_type: Tehdit turu.
        """
        self._patterns[name] = {
            "keywords": keywords,
            "type": threat_type,
        }

    def set_baseline(
        self,
        metric_name: str,
        value: float,
    ) -> None:
        """Baseline ayarlar.

        Args:
            metric_name: Metrik adi.
            value: Baseline degeri.
        """
        self._baselines[metric_name] = value

    def get_threats(
        self,
        threat_type: ThreatType | None = None,
        level: ThreatLevel | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Tehditleri getirir.

        Args:
            threat_type: Tur filtresi.
            level: Seviye filtresi.
            limit: Maks kayit.

        Returns:
            Tehdit listesi.
        """
        threats = self._threats
        if threat_type:
            threats = [
                t for t in threats
                if t.threat_type == threat_type
            ]
        if level:
            threats = [
                t for t in threats
                if t.level == level
            ]
        return [
            {
                "threat_id": t.threat_id,
                "type": t.threat_type.value,
                "level": t.level.value,
                "source": t.source,
                "description": t.description,
                "blocked": t.blocked,
            }
            for t in threats[-limit:]
        ]

    def get_login_attempts(
        self,
        identifier: str,
    ) -> int:
        """Giris denemesi sayisi getirir.

        Args:
            identifier: Kullanici/IP.

        Returns:
            Deneme sayisi.
        """
        return len(self._login_attempts.get(identifier, []))

    def reset_login_attempts(
        self,
        identifier: str,
    ) -> None:
        """Giris denemelerini sifirlar.

        Args:
            identifier: Kullanici/IP.
        """
        self._login_attempts[identifier] = []

    @property
    def threat_count(self) -> int:
        """Tehdit sayisi."""
        return len(self._threats)

    @property
    def blocked_count(self) -> int:
        """Engellenen tehdit sayisi."""
        return sum(1 for t in self._threats if t.blocked)

    @property
    def pattern_count(self) -> int:
        """Desen sayisi."""
        return len(self._patterns)
