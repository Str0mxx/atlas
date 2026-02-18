"""
Adli toplayici modulu.

Kanit toplama, log koruma,
bellek yakalama, gozetim zinciri,
butunluk dogrulama.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ForensicCollector:
    """Adli toplayici.

    Attributes:
        _evidence: Kanit kayitlari.
        _custody_chain: Gozetim zinciri.
        _snapshots: Anlık goruntu kayitlari.
        _stats: Istatistikler.
    """

    EVIDENCE_TYPES: list[str] = [
        "log_file",
        "memory_dump",
        "network_capture",
        "disk_image",
        "configuration",
        "process_list",
        "registry",
        "file_artifact",
    ]

    def __init__(self) -> None:
        """Toplayiciyi baslatir."""
        self._evidence: dict[
            str, dict
        ] = {}
        self._custody_chain: dict[
            str, list[dict]
        ] = {}
        self._snapshots: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "evidence_collected": 0,
            "custody_transfers": 0,
            "snapshots_taken": 0,
            "integrity_verified": 0,
        }
        logger.info(
            "ForensicCollector baslatildi"
        )

    @property
    def evidence_count(self) -> int:
        """Kanit sayisi."""
        return len(self._evidence)

    def collect_evidence(
        self,
        incident_id: str = "",
        evidence_type: str = "log_file",
        title: str = "",
        content: str = "",
        source_system: str = "",
        collector: str = "",
    ) -> dict[str, Any]:
        """Kanit toplar.

        Args:
            incident_id: Olay ID.
            evidence_type: Kanit tipi.
            title: Baslik.
            content: Icerik.
            source_system: Kaynak sistem.
            collector: Toplayici.

        Returns:
            Kanit bilgisi.
        """
        try:
            if (
                evidence_type
                not in self.EVIDENCE_TYPES
            ):
                return {
                    "collected": False,
                    "error": (
                        f"Gecersiz: "
                        f"{evidence_type}"
                    ),
                }

            eid = f"ev_{uuid4()!s:.8}"
            content_hash = hashlib.sha256(
                content.encode()
            ).hexdigest()[:16]

            self._evidence[eid] = {
                "evidence_id": eid,
                "incident_id": incident_id,
                "evidence_type": (
                    evidence_type
                ),
                "title": title,
                "content": content,
                "source_system": (
                    source_system
                ),
                "collector": collector,
                "hash": content_hash,
                "integrity": "verified",
                "status": "collected",
                "collected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            # Gozetim zinciri baslat
            self._custody_chain[eid] = [{
                "action": "collected",
                "handler": collector,
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }]

            self._stats[
                "evidence_collected"
            ] += 1

            return {
                "evidence_id": eid,
                "hash": content_hash,
                "collected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "collected": False,
                "error": str(e),
            }

    def transfer_custody(
        self,
        evidence_id: str = "",
        from_handler: str = "",
        to_handler: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Gozetim devreder.

        Args:
            evidence_id: Kanit ID.
            from_handler: Devreden.
            to_handler: Devralan.
            reason: Sebep.

        Returns:
            Devir bilgisi.
        """
        try:
            if (
                evidence_id
                not in self._evidence
            ):
                return {
                    "transferred": False,
                    "error": (
                        "Kanit bulunamadi"
                    ),
                }

            chain = (
                self._custody_chain.get(
                    evidence_id, []
                )
            )
            chain.append({
                "action": "transferred",
                "from_handler": (
                    from_handler
                ),
                "to_handler": to_handler,
                "reason": reason,
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })
            self._stats[
                "custody_transfers"
            ] += 1

            return {
                "evidence_id": evidence_id,
                "to_handler": to_handler,
                "chain_length": len(chain),
                "transferred": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "transferred": False,
                "error": str(e),
            }

    def verify_integrity(
        self,
        evidence_id: str = "",
    ) -> dict[str, Any]:
        """Butunluk dogrular.

        Args:
            evidence_id: Kanit ID.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            ev = self._evidence.get(
                evidence_id
            )
            if not ev:
                return {
                    "verified": False,
                    "error": (
                        "Kanit bulunamadi"
                    ),
                }

            current_hash = (
                hashlib.sha256(
                    ev["content"].encode()
                ).hexdigest()[:16]
            )
            is_intact = (
                current_hash == ev["hash"]
            )

            ev["integrity"] = (
                "verified"
                if is_intact
                else "tampered"
            )
            self._stats[
                "integrity_verified"
            ] += 1

            return {
                "evidence_id": evidence_id,
                "is_intact": is_intact,
                "original_hash": ev["hash"],
                "current_hash": current_hash,
                "verified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "verified": False,
                "error": str(e),
            }

    def take_snapshot(
        self,
        incident_id: str = "",
        system: str = "",
        snapshot_type: str = "full",
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Anlik goruntu alir.

        Args:
            incident_id: Olay ID.
            system: Sistem.
            snapshot_type: Goruntu tipi.
            data: Goruntu verisi.

        Returns:
            Goruntu bilgisi.
        """
        try:
            sid = f"ss_{uuid4()!s:.8}"
            snap_data = data or {}

            self._snapshots[sid] = {
                "snapshot_id": sid,
                "incident_id": incident_id,
                "system": system,
                "snapshot_type": (
                    snapshot_type
                ),
                "data": snap_data,
                "taken_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "snapshots_taken"
            ] += 1

            return {
                "snapshot_id": sid,
                "system": system,
                "taken": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "taken": False,
                "error": str(e),
            }

    def get_evidence(
        self,
        incident_id: str = "",
    ) -> dict[str, Any]:
        """Kanitleri getirir.

        Args:
            incident_id: Olay ID filtresi.

        Returns:
            Kanit listesi.
        """
        try:
            if incident_id:
                filtered = [
                    e
                    for e in (
                        self._evidence
                        .values()
                    )
                    if e["incident_id"]
                    == incident_id
                ]
            else:
                filtered = list(
                    self._evidence.values()
                )

            return {
                "evidence": filtered,
                "count": len(filtered),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_custody_chain(
        self,
        evidence_id: str = "",
    ) -> dict[str, Any]:
        """Gozetim zincirini getirir.

        Args:
            evidence_id: Kanit ID.

        Returns:
            Zincir bilgisi.
        """
        try:
            chain = (
                self._custody_chain.get(
                    evidence_id
                )
            )
            if chain is None:
                return {
                    "retrieved": False,
                    "error": (
                        "Kanit bulunamadi"
                    ),
                }

            return {
                "evidence_id": evidence_id,
                "chain": list(chain),
                "length": len(chain),
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
            by_type: dict[str, int] = {}
            for e in (
                self._evidence.values()
            ):
                t = e["evidence_type"]
                by_type[t] = (
                    by_type.get(t, 0) + 1
                )

            return {
                "total_evidence": len(
                    self._evidence
                ),
                "total_snapshots": len(
                    self._snapshots
                ),
                "by_type": by_type,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
