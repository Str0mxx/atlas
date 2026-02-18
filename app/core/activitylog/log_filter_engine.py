"""
Log filtre motoru modulu.

Coklu alan filtreleme, tarih araligi,
aktor/sistem filtreleme, kayitli filtreler,
filtre birlestirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class LogFilterEngine:
    """Log filtre motoru.

    Attributes:
        _filters: Kayitli filtreler.
        _logs: Log kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Filtre motorunu baslatir."""
        self._filters: list[dict] = []
        self._logs: list[dict] = []
        self._stats: dict[str, int] = {
            "filters_created": 0,
            "filters_applied": 0,
        }
        logger.info(
            "LogFilterEngine baslatildi"
        )

    @property
    def filter_count(self) -> int:
        """Filtre sayisi."""
        return len(self._filters)

    @property
    def log_count(self) -> int:
        """Log sayisi."""
        return len(self._logs)

    def add_log(
        self,
        source: str = "",
        action: str = "",
        actor: str = "",
        level: str = "info",
        category: str = "system",
        details: str = "",
    ) -> dict[str, Any]:
        """Log ekler.

        Args:
            source: Kaynak.
            action: Aksiyon.
            actor: Aktor.
            level: Seviye.
            category: Kategori.
            details: Detaylar.

        Returns:
            Ekleme bilgisi.
        """
        try:
            lid = f"lg_{uuid4()!s:.8}"
            log = {
                "log_id": lid,
                "source": source,
                "action": action,
                "actor": actor,
                "level": level,
                "category": category,
                "details": details,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._logs.append(log)

            return {
                "log_id": lid,
                "source": source,
                "action": action,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def create_filter(
        self,
        name: str = "",
        conditions: dict | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Filtre olusturur.

        Args:
            name: Filtre adi.
            conditions: Kosullar.
            description: Aciklama.

        Returns:
            Olusturma bilgisi.
        """
        try:
            fid = f"ft_{uuid4()!s:.8}"
            filt = {
                "filter_id": fid,
                "name": name,
                "conditions": conditions or {},
                "description": description,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "use_count": 0,
            }
            self._filters.append(filt)
            self._stats[
                "filters_created"
            ] += 1

            return {
                "filter_id": fid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def apply_filter(
        self,
        filter_id: str = "",
    ) -> dict[str, Any]:
        """Kayitli filtreyi uygular.

        Args:
            filter_id: Filtre ID.

        Returns:
            Filtreleme sonucu.
        """
        try:
            target = None
            for f in self._filters:
                if f["filter_id"] == filter_id:
                    target = f
                    break

            if not target:
                return {
                    "filter_id": filter_id,
                    "applied": False,
                    "reason": "not_found",
                }

            conds = target.get(
                "conditions", {}
            )
            results = self._apply_conditions(
                conds
            )

            target["use_count"] += 1
            self._stats[
                "filters_applied"
            ] += 1

            return {
                "filter_id": filter_id,
                "filter_name": target["name"],
                "results": results,
                "result_count": len(results),
                "applied": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "applied": False,
                "error": str(e),
            }

    def filter_logs(
        self,
        actor: str = "",
        level: str = "",
        category: str = "",
        source: str = "",
        action: str = "",
    ) -> dict[str, Any]:
        """Loglari filtreler.

        Args:
            actor: Aktor.
            level: Seviye.
            category: Kategori.
            source: Kaynak.
            action: Aksiyon.

        Returns:
            Filtreleme sonucu.
        """
        try:
            conditions: dict[str, str] = {}
            if actor:
                conditions["actor"] = actor
            if level:
                conditions["level"] = level
            if category:
                conditions[
                    "category"
                ] = category
            if source:
                conditions["source"] = source
            if action:
                conditions["action"] = action

            results = self._apply_conditions(
                conditions
            )
            self._stats[
                "filters_applied"
            ] += 1

            return {
                "conditions": conditions,
                "results": results,
                "result_count": len(results),
                "filtered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "filtered": False,
                "error": str(e),
            }

    def filter_by_date_range(
        self,
        start_date: str = "",
        end_date: str = "",
    ) -> dict[str, Any]:
        """Tarih araligina gore filtreler.

        Args:
            start_date: Baslangic tarihi.
            end_date: Bitis tarihi.

        Returns:
            Filtreleme sonucu.
        """
        try:
            results = []
            for log in self._logs:
                ts = log.get("timestamp", "")
                if not ts:
                    continue

                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue

                results.append(log)

            return {
                "start_date": start_date,
                "end_date": end_date,
                "results": results,
                "result_count": len(results),
                "filtered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "filtered": False,
                "error": str(e),
            }

    def get_saved_filters(
        self,
    ) -> dict[str, Any]:
        """Kayitli filtreleri getirir.

        Returns:
            Filtre listesi.
        """
        try:
            return {
                "filters": list(
                    self._filters
                ),
                "filter_count": len(
                    self._filters
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def delete_filter(
        self,
        filter_id: str = "",
    ) -> dict[str, Any]:
        """Filtre siler.

        Args:
            filter_id: Filtre ID.

        Returns:
            Silme bilgisi.
        """
        try:
            original = len(self._filters)
            self._filters = [
                f
                for f in self._filters
                if f["filter_id"] != filter_id
            ]

            deleted = (
                original - len(self._filters)
                > 0
            )

            return {
                "filter_id": filter_id,
                "deleted": deleted,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "deleted": False,
                "error": str(e),
            }

    def _apply_conditions(
        self,
        conditions: dict,
    ) -> list[dict]:
        """Kosullari uygular.

        Args:
            conditions: Filtre kosullari.

        Returns:
            Filtrelenmis loglar.
        """
        results = []
        for log in self._logs:
            match = True
            for key, value in conditions.items():
                if log.get(key) != value:
                    match = False
                    break
            if match:
                results.append(log)
        return results
