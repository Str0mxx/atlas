"""ATLAS API Analitik Toplayici modulu.

Istek loglama, yanit sureleri,
hata oranlari, kullanim kaliplari
ve istemci takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class APIAnalyticsCollector:
    """API analitik toplayici.

    API kullanim verilerini toplar
    ve analiz eder.

    Attributes:
        _requests: Istek kayitlari.
        _errors: Hata kayitlari.
    """

    def __init__(
        self,
        retention_hours: int = 24,
    ) -> None:
        """Analitik toplayiciyi baslatir.

        Args:
            retention_hours: Saklama suresi.
        """
        self._retention_hours = retention_hours
        self._requests: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []
        self._clients: dict[
            str, dict[str, Any]
        ] = {}
        self._endpoint_stats: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "APIAnalyticsCollector baslatildi",
        )

    def record_request(
        self,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200,
        response_time: float = 0.0,
        client_id: str = "",
    ) -> dict[str, Any]:
        """Istek kaydeder.

        Args:
            endpoint: Endpoint yolu.
            method: HTTP metodu.
            status_code: Yanit kodu.
            response_time: Yanit suresi (ms).
            client_id: Istemci ID.

        Returns:
            Kayit bilgisi.
        """
        record = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time": response_time,
            "client_id": client_id,
            "timestamp": time.time(),
        }
        self._requests.append(record)

        # Endpoint istatistikleri guncelle
        key = f"{method}:{endpoint}"
        if key not in self._endpoint_stats:
            self._endpoint_stats[key] = {
                "total": 0,
                "errors": 0,
                "total_time": 0.0,
            }
        stats = self._endpoint_stats[key]
        stats["total"] += 1
        stats["total_time"] += response_time
        if status_code >= 400:
            stats["errors"] += 1

        # Istemci takibi
        if client_id:
            if client_id not in self._clients:
                self._clients[client_id] = {
                    "request_count": 0,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                }
            self._clients[client_id][
                "request_count"
            ] += 1
            self._clients[client_id][
                "last_seen"
            ] = time.time()

        # Hata kaydi
        if status_code >= 400:
            self._errors.append(record)

        return record

    def get_endpoint_stats(
        self,
        endpoint: str,
        method: str = "GET",
    ) -> dict[str, Any]:
        """Endpoint istatistikleri getirir.

        Args:
            endpoint: Endpoint yolu.
            method: HTTP metodu.

        Returns:
            Istatistik bilgisi.
        """
        key = f"{method}:{endpoint}"
        stats = self._endpoint_stats.get(key)
        if not stats:
            return {
                "total": 0,
                "avg_time": 0.0,
                "error_rate": 0.0,
            }

        total = stats["total"]
        avg_time = (
            stats["total_time"] / total
            if total > 0
            else 0.0
        )
        error_rate = (
            stats["errors"] / total
            if total > 0
            else 0.0
        )

        return {
            "total": total,
            "errors": stats["errors"],
            "avg_time": round(avg_time, 2),
            "error_rate": round(error_rate, 4),
        }

    def get_top_endpoints(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """En cok kullanilan endpointleri getirir.

        Args:
            limit: Sonuc limiti.

        Returns:
            Endpoint listesi.
        """
        sorted_eps = sorted(
            self._endpoint_stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True,
        )
        results = []
        for key, stats in sorted_eps[:limit]:
            parts = key.split(":", 1)
            method = parts[0] if parts else ""
            endpoint = parts[1] if len(parts) > 1 else key
            total = stats["total"]
            results.append({
                "endpoint": endpoint,
                "method": method,
                "total": total,
                "avg_time": round(
                    stats["total_time"] / total
                    if total > 0
                    else 0.0,
                    2,
                ),
            })
        return results

    def get_error_summary(
        self,
    ) -> dict[str, Any]:
        """Hata ozeti getirir.

        Returns:
            Hata ozeti.
        """
        total_requests = len(self._requests)
        total_errors = len(self._errors)
        error_rate = (
            total_errors / total_requests
            if total_requests > 0
            else 0.0
        )

        # Hata kodlarina gore grupla
        by_code: dict[int, int] = {}
        for err in self._errors:
            code = err["status_code"]
            by_code[code] = by_code.get(code, 0) + 1

        return {
            "total_errors": total_errors,
            "error_rate": round(error_rate, 4),
            "by_status_code": by_code,
        }

    def get_client_stats(
        self,
        client_id: str,
    ) -> dict[str, Any] | None:
        """Istemci istatistikleri getirir.

        Args:
            client_id: Istemci ID.

        Returns:
            Istemci bilgisi veya None.
        """
        return self._clients.get(client_id)

    def get_response_time_stats(
        self,
    ) -> dict[str, Any]:
        """Yanit suresi istatistikleri.

        Returns:
            Sure istatistikleri.
        """
        if not self._requests:
            return {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "count": 0,
            }

        times = [
            r["response_time"]
            for r in self._requests
        ]
        return {
            "avg": round(
                sum(times) / len(times), 2,
            ),
            "min": round(min(times), 2),
            "max": round(max(times), 2),
            "count": len(times),
        }

    def get_usage_patterns(
        self,
    ) -> dict[str, Any]:
        """Kullanim kaliplarini analiz eder.

        Returns:
            Kalip analizi.
        """
        # Metot dagilimi
        method_dist: dict[str, int] = {}
        for r in self._requests:
            m = r["method"]
            method_dist[m] = (
                method_dist.get(m, 0) + 1
            )

        # Durum kodu dagilimi
        status_dist: dict[str, int] = {}
        for r in self._requests:
            code = str(r["status_code"])
            group = code[0] + "xx"
            status_dist[group] = (
                status_dist.get(group, 0) + 1
            )

        return {
            "total_requests": len(self._requests),
            "unique_clients": len(self._clients),
            "method_distribution": method_dist,
            "status_distribution": status_dist,
        }

    def cleanup(
        self,
        max_age_hours: int | None = None,
    ) -> int:
        """Eski kayitlari temizler.

        Args:
            max_age_hours: Maksimum yas (saat).

        Returns:
            Temizlenen kayit sayisi.
        """
        hours = max_age_hours or self._retention_hours
        cutoff = time.time() - (hours * 3600)

        before = len(self._requests)
        self._requests = [
            r for r in self._requests
            if r["timestamp"] > cutoff
        ]
        self._errors = [
            e for e in self._errors
            if e["timestamp"] > cutoff
        ]
        return before - len(self._requests)

    @property
    def request_count(self) -> int:
        """Istek sayisi."""
        return len(self._requests)

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return len(self._errors)

    @property
    def client_count(self) -> int:
        """Istemci sayisi."""
        return len(self._clients)

    @property
    def endpoint_stat_count(self) -> int:
        """Endpoint istatistik sayisi."""
        return len(self._endpoint_stats)
