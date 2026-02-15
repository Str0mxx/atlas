"""ATLAS Ilerleme Takipcisi modulu.

Edinme durumu, kilometre tasi takibi,
engel tespiti, ETA hesaplama, raporlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AcquisitionProgressTracker:
    """Ilerleme takipcisi.

    Yetenek edinme ilerlemesini izler.

    Attributes:
        _acquisitions: Edinme kayitlari.
        _milestones: Kilometre taslari.
    """

    def __init__(self) -> None:
        """Ilerleme takipcisini baslatir."""
        self._acquisitions: dict[
            str, dict[str, Any]
        ] = {}
        self._milestones: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._blockers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "tracked": 0,
            "completed": 0,
        }

        logger.info(
            "AcquisitionProgressTracker "
            "baslatildi",
        )

    def start_tracking(
        self,
        acquisition_id: str,
        capability: str,
        total_steps: int = 5,
        estimated_hours: float = 0.0,
    ) -> dict[str, Any]:
        """Ilerleme takibi baslatir.

        Args:
            acquisition_id: Edinme ID.
            capability: Yetenek adi.
            total_steps: Toplam adim.
            estimated_hours: Tahmini saat.

        Returns:
            Baslatma bilgisi.
        """
        self._acquisitions[
            acquisition_id
        ] = {
            "acquisition_id": acquisition_id,
            "capability": capability,
            "total_steps": total_steps,
            "completed_steps": 0,
            "estimated_hours": estimated_hours,
            "status": "in_progress",
            "phase": "detection",
            "started_at": time.time(),
            "completed_at": None,
        }
        self._milestones[
            acquisition_id
        ] = []
        self._blockers[
            acquisition_id
        ] = []
        self._stats["tracked"] += 1

        return {
            "acquisition_id": acquisition_id,
            "tracking_started": True,
        }

    def update_progress(
        self,
        acquisition_id: str,
        step: int,
        phase: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Ilerleme gunceller.

        Args:
            acquisition_id: Edinme ID.
            step: Tamamlanan adim.
            phase: Asama.
            description: Aciklama.

        Returns:
            Guncelleme bilgisi.
        """
        acq = self._acquisitions.get(
            acquisition_id,
        )
        if not acq:
            return {
                "error": (
                    "acquisition_not_found"
                ),
            }

        acq["completed_steps"] = step
        if phase:
            acq["phase"] = phase

        progress_pct = (
            step / max(
                acq["total_steps"], 1,
            ) * 100
        )

        # Kilometre tasi ekle
        self._milestones[
            acquisition_id
        ].append({
            "step": step,
            "phase": phase,
            "description": description,
            "reached_at": time.time(),
        })

        return {
            "acquisition_id": acquisition_id,
            "step": step,
            "progress_pct": round(
                progress_pct, 1,
            ),
            "updated": True,
        }

    def complete_acquisition(
        self,
        acquisition_id: str,
    ) -> dict[str, Any]:
        """Edinmeyi tamamlar.

        Args:
            acquisition_id: Edinme ID.

        Returns:
            Tamamlama bilgisi.
        """
        acq = self._acquisitions.get(
            acquisition_id,
        )
        if not acq:
            return {
                "error": (
                    "acquisition_not_found"
                ),
            }

        acq["status"] = "completed"
        acq["completed_at"] = time.time()
        acq["completed_steps"] = acq[
            "total_steps"
        ]
        acq["phase"] = "deployment"

        duration = (
            acq["completed_at"]
            - acq["started_at"]
        )

        self._stats["completed"] += 1

        return {
            "acquisition_id": acquisition_id,
            "completed": True,
            "duration_seconds": round(
                duration, 2,
            ),
        }

    def add_blocker(
        self,
        acquisition_id: str,
        blocker: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Engel ekler.

        Args:
            acquisition_id: Edinme ID.
            blocker: Engel aciklamasi.
            severity: Siddet.

        Returns:
            Ekleme bilgisi.
        """
        if (
            acquisition_id
            not in self._blockers
        ):
            return {
                "error": (
                    "acquisition_not_found"
                ),
            }

        self._blockers[
            acquisition_id
        ].append({
            "blocker": blocker,
            "severity": severity,
            "resolved": False,
            "added_at": time.time(),
        })

        return {
            "acquisition_id": acquisition_id,
            "blocker_added": True,
            "severity": severity,
        }

    def resolve_blocker(
        self,
        acquisition_id: str,
        blocker_index: int,
    ) -> dict[str, Any]:
        """Engeli cozer.

        Args:
            acquisition_id: Edinme ID.
            blocker_index: Engel indeksi.

        Returns:
            Cozum bilgisi.
        """
        blockers = self._blockers.get(
            acquisition_id,
        )
        if not blockers:
            return {
                "error": (
                    "acquisition_not_found"
                ),
            }

        if blocker_index >= len(blockers):
            return {
                "error": "blocker_not_found",
            }

        blockers[blocker_index][
            "resolved"
        ] = True
        blockers[blocker_index][
            "resolved_at"
        ] = time.time()

        return {
            "acquisition_id": acquisition_id,
            "blocker_resolved": True,
        }

    def calculate_eta(
        self,
        acquisition_id: str,
    ) -> dict[str, Any]:
        """ETA hesaplar.

        Args:
            acquisition_id: Edinme ID.

        Returns:
            ETA bilgisi.
        """
        acq = self._acquisitions.get(
            acquisition_id,
        )
        if not acq:
            return {
                "error": (
                    "acquisition_not_found"
                ),
            }

        if acq["status"] == "completed":
            return {
                "acquisition_id": (
                    acquisition_id
                ),
                "eta_hours": 0.0,
                "completed": True,
            }

        completed = acq["completed_steps"]
        total = acq["total_steps"]
        remaining = total - completed

        elapsed = (
            time.time() - acq["started_at"]
        )
        elapsed_hours = elapsed / 3600

        if completed > 0:
            rate = elapsed_hours / completed
            eta_hours = rate * remaining
        else:
            eta_hours = acq.get(
                "estimated_hours", 1.0,
            )

        # Engeller ETA'yi etkiler
        active_blockers = sum(
            1 for b in self._blockers.get(
                acquisition_id, [],
            )
            if not b["resolved"]
        )
        if active_blockers > 0:
            eta_hours *= (
                1 + active_blockers * 0.5
            )

        return {
            "acquisition_id": acquisition_id,
            "eta_hours": round(eta_hours, 2),
            "remaining_steps": remaining,
            "active_blockers": active_blockers,
            "completed": False,
        }

    def get_report(
        self,
        acquisition_id: str,
    ) -> dict[str, Any]:
        """Rapor getirir.

        Args:
            acquisition_id: Edinme ID.

        Returns:
            Rapor bilgisi.
        """
        acq = self._acquisitions.get(
            acquisition_id,
        )
        if not acq:
            return {
                "error": (
                    "acquisition_not_found"
                ),
            }

        milestones = self._milestones.get(
            acquisition_id, [],
        )
        blockers = self._blockers.get(
            acquisition_id, [],
        )
        active_blockers = [
            b for b in blockers
            if not b["resolved"]
        ]

        progress_pct = (
            acq["completed_steps"]
            / max(acq["total_steps"], 1)
            * 100
        )

        return {
            "acquisition_id": acquisition_id,
            "capability": acq["capability"],
            "status": acq["status"],
            "phase": acq["phase"],
            "progress_pct": round(
                progress_pct, 1,
            ),
            "milestones": len(milestones),
            "total_blockers": len(blockers),
            "active_blockers": len(
                active_blockers,
            ),
        }

    def get_all_status(
        self,
    ) -> list[dict[str, Any]]:
        """Tum edinme durumlari.

        Returns:
            Durum listesi.
        """
        statuses = []
        for acq_id, acq in (
            self._acquisitions.items()
        ):
            progress = (
                acq["completed_steps"]
                / max(acq["total_steps"], 1)
                * 100
            )
            statuses.append({
                "acquisition_id": acq_id,
                "capability": acq["capability"],
                "status": acq["status"],
                "progress_pct": round(
                    progress, 1,
                ),
            })
        return statuses

    @property
    def tracking_count(self) -> int:
        """Takip sayisi."""
        return self._stats["tracked"]

    @property
    def completed_count(self) -> int:
        """Tamamlanan sayisi."""
        return self._stats["completed"]

    @property
    def in_progress_count(self) -> int:
        """Devam eden sayisi."""
        return sum(
            1 for a in (
                self._acquisitions.values()
            )
            if a["status"] == "in_progress"
        )
