"""ATLAS Hukuki Son Tarih Çıkarıcı modülü.

Tarih çıkarma, son tarih hesaplama,
yenileme tarihleri, ihbar süreleri,
takvim entegrasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LegalDeadlineExtractor:
    """Hukuki son tarih çıkarıcı.

    Sözleşme son tarihlerini çıkarır.

    Attributes:
        _deadlines: Son tarih kayıtları.
        _calendar: Takvim kayıtları.
    """

    def __init__(self) -> None:
        """Çıkarıcıyı başlatır."""
        self._deadlines: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._calendar: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "deadlines_extracted": 0,
            "renewals_found": 0,
            "notices_tracked": 0,
        }

        logger.info(
            "LegalDeadlineExtractor "
            "baslatildi",
        )

    def extract_dates(
        self,
        contract_id: str,
        effective_date: str = "",
        expiry_date: str = "",
        renewal_date: str = "",
    ) -> dict[str, Any]:
        """Tarih çıkarır.

        Args:
            contract_id: Sözleşme ID.
            effective_date: Yürürlük.
            expiry_date: Bitiş.
            renewal_date: Yenileme.

        Returns:
            Tarih bilgisi.
        """
        dates = {
            "effective": effective_date,
            "expiry": expiry_date,
            "renewal": renewal_date,
        }

        extracted = {
            k: v for k, v in dates.items()
            if v
        }

        return {
            "contract_id": contract_id,
            "dates": extracted,
            "count": len(extracted),
            "extracted": True,
        }

    def calculate_deadline(
        self,
        contract_id: str,
        deadline_type: str,
        date: str,
        notice_days: int = 0,
        description: str = "",
    ) -> dict[str, Any]:
        """Son tarih hesaplar.

        Args:
            contract_id: Sözleşme ID.
            deadline_type: Son tarih tipi.
            date: Tarih.
            notice_days: İhbar günü.
            description: Açıklama.

        Returns:
            Son tarih bilgisi.
        """
        self._counter += 1
        did = f"dl_{self._counter}"

        deadline = {
            "deadline_id": did,
            "contract_id": contract_id,
            "type": deadline_type,
            "date": date,
            "notice_days": notice_days,
            "description": description,
            "status": "active",
            "timestamp": time.time(),
        }

        if (
            contract_id
            not in self._deadlines
        ):
            self._deadlines[
                contract_id
            ] = []
        self._deadlines[
            contract_id
        ].append(deadline)
        self._stats[
            "deadlines_extracted"
        ] += 1

        return {
            "deadline_id": did,
            "type": deadline_type,
            "date": date,
            "notice_days": notice_days,
            "calculated": True,
        }

    def track_renewal(
        self,
        contract_id: str,
        renewal_date: str,
        auto_renew: bool = False,
        notice_required_days: int = 30,
    ) -> dict[str, Any]:
        """Yenileme takip eder.

        Args:
            contract_id: Sözleşme ID.
            renewal_date: Yenileme tarihi.
            auto_renew: Otomatik yenileme.
            notice_required_days: İhbar günü.

        Returns:
            Yenileme bilgisi.
        """
        result = self.calculate_deadline(
            contract_id=contract_id,
            deadline_type="renewal",
            date=renewal_date,
            notice_days=(
                notice_required_days
            ),
            description=(
                "Auto-renewal"
                if auto_renew
                else "Manual renewal"
            ),
        )

        self._stats[
            "renewals_found"
        ] += 1

        result["auto_renew"] = auto_renew
        return result

    def track_notice_period(
        self,
        contract_id: str,
        notice_type: str = "termination",
        days: int = 30,
        start_date: str = "",
    ) -> dict[str, Any]:
        """İhbar süresi takip eder.

        Args:
            contract_id: Sözleşme ID.
            notice_type: İhbar tipi.
            days: Gün sayısı.
            start_date: Başlangıç tarihi.

        Returns:
            İhbar bilgisi.
        """
        self._stats[
            "notices_tracked"
        ] += 1

        return {
            "contract_id": contract_id,
            "notice_type": notice_type,
            "days": days,
            "start_date": start_date,
            "tracked": True,
        }

    def add_to_calendar(
        self,
        deadline_id: str,
        reminder_days: int = 7,
        assignee: str = "",
    ) -> dict[str, Any]:
        """Takvime ekler.

        Args:
            deadline_id: Son tarih ID.
            reminder_days: Hatırlatma günü.
            assignee: Atanan kişi.

        Returns:
            Takvim bilgisi.
        """
        entry = {
            "deadline_id": deadline_id,
            "reminder_days": reminder_days,
            "assignee": assignee,
            "status": "scheduled",
        }
        self._calendar.append(entry)

        return {
            "deadline_id": deadline_id,
            "reminder_days": reminder_days,
            "added_to_calendar": True,
        }

    def get_deadlines(
        self,
        contract_id: str,
        deadline_type: str = "",
    ) -> list[dict[str, Any]]:
        """Son tarihleri listeler."""
        deadlines = self._deadlines.get(
            contract_id, [],
        )
        if deadline_type:
            deadlines = [
                d for d in deadlines
                if d["type"] == deadline_type
            ]
        return deadlines

    def get_upcoming(
        self,
        days_ahead: int = 30,
    ) -> list[dict[str, Any]]:
        """Yaklaşan son tarihleri döndürür."""
        upcoming = []
        for dlist in (
            self._deadlines.values()
        ):
            for d in dlist:
                if d["status"] == "active":
                    upcoming.append({
                        "deadline_id": d[
                            "deadline_id"
                        ],
                        "contract_id": d[
                            "contract_id"
                        ],
                        "type": d["type"],
                        "date": d["date"],
                    })
        return upcoming

    @property
    def deadline_count(self) -> int:
        """Son tarih sayısı."""
        return self._stats[
            "deadlines_extracted"
        ]

    @property
    def renewal_count(self) -> int:
        """Yenileme sayısı."""
        return self._stats[
            "renewals_found"
        ]
