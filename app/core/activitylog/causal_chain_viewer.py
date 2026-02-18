"""
Nedensel zincir goruntuleyici modulu.

Neden-sonuc zincirleri, gorsel graf,
kok neden izleme, etki yollari,
zaman cizelgesi entegrasyonu.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CausalChainViewer:
    """Nedensel zincir goruntuleyici.

    Attributes:
        _events: Olay kayitlari.
        _chains: Nedensel zincirler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Goruntuleyiciyi baslatir."""
        self._events: list[dict] = []
        self._chains: list[dict] = []
        self._stats: dict[str, int] = {
            "events_added": 0,
            "chains_created": 0,
        }
        logger.info(
            "CausalChainViewer baslatildi"
        )

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)

    @property
    def chain_count(self) -> int:
        """Zincir sayisi."""
        return len(self._chains)

    def add_event(
        self,
        name: str = "",
        event_type: str = "action",
        cause_id: str = "",
        actor: str = "",
        details: str = "",
    ) -> dict[str, Any]:
        """Olay ekler.

        Args:
            name: Olay adi.
            event_type: Olay turu.
            cause_id: Neden olay ID.
            actor: Aktor.
            details: Detaylar.

        Returns:
            Ekleme bilgisi.
        """
        try:
            eid = f"ce_{uuid4()!s:.8}"
            event = {
                "event_id": eid,
                "name": name,
                "event_type": event_type,
                "cause_id": cause_id,
                "actor": actor,
                "details": details,
                "effects": [],
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._events.append(event)
            self._stats["events_added"] += 1

            if cause_id:
                for e in self._events:
                    if (
                        e["event_id"]
                        == cause_id
                    ):
                        e["effects"].append(eid)
                        break

            return {
                "event_id": eid,
                "name": name,
                "cause_id": cause_id,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def build_chain(
        self,
        root_event_id: str = "",
    ) -> dict[str, Any]:
        """Nedensel zincir olusturur.

        Args:
            root_event_id: Kok olay ID.

        Returns:
            Zincir bilgisi.
        """
        try:
            root = None
            for e in self._events:
                if (
                    e["event_id"]
                    == root_event_id
                ):
                    root = e
                    break

            if not root:
                return {
                    "event_id": root_event_id,
                    "built": False,
                    "reason": "not_found",
                }

            chain = self._traverse_effects(
                root_event_id
            )
            cid = f"ch_{uuid4()!s:.8}"

            chain_record = {
                "chain_id": cid,
                "root_event_id": (
                    root_event_id
                ),
                "root_name": root["name"],
                "chain": chain,
                "depth": self._chain_depth(
                    chain
                ),
                "total_events": (
                    self._count_chain_events(
                        chain
                    )
                ),
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._chains.append(chain_record)
            self._stats[
                "chains_created"
            ] += 1

            return {
                "chain_id": cid,
                "root_event_id": (
                    root_event_id
                ),
                "chain": chain,
                "depth": chain_record["depth"],
                "total_events": chain_record[
                    "total_events"
                ],
                "built": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "built": False,
                "error": str(e),
            }

    def trace_root_cause(
        self,
        event_id: str = "",
    ) -> dict[str, Any]:
        """Kok nedeni izler.

        Args:
            event_id: Olay ID.

        Returns:
            Kok neden bilgisi.
        """
        try:
            path = []
            current_id = event_id

            visited: set[str] = set()
            while current_id:
                if current_id in visited:
                    break
                visited.add(current_id)

                event = None
                for e in self._events:
                    if (
                        e["event_id"]
                        == current_id
                    ):
                        event = e
                        break

                if not event:
                    break

                path.append({
                    "event_id": event[
                        "event_id"
                    ],
                    "name": event["name"],
                    "event_type": event[
                        "event_type"
                    ],
                    "actor": event["actor"],
                })

                current_id = event.get(
                    "cause_id", ""
                )

            path.reverse()

            root_cause = (
                path[0] if path else None
            )

            return {
                "event_id": event_id,
                "root_cause": root_cause,
                "path": path,
                "path_length": len(path),
                "traced": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "traced": False,
                "error": str(e),
            }

    def get_impact_path(
        self,
        event_id: str = "",
    ) -> dict[str, Any]:
        """Etki yolunu getirir.

        Args:
            event_id: Olay ID.

        Returns:
            Etki yolu bilgisi.
        """
        try:
            effects = (
                self._collect_all_effects(
                    event_id
                )
            )

            return {
                "event_id": event_id,
                "effects": effects,
                "impact_count": len(effects),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_timeline_view(
        self,
        chain_id: str = "",
    ) -> dict[str, Any]:
        """Zaman cizelgesi gorunumu getirir.

        Args:
            chain_id: Zincir ID.

        Returns:
            Zaman cizelgesi.
        """
        try:
            chain_record = None
            for c in self._chains:
                if c["chain_id"] == chain_id:
                    chain_record = c
                    break

            if not chain_record:
                return {
                    "chain_id": chain_id,
                    "retrieved": False,
                    "reason": "not_found",
                }

            event_ids = (
                self._extract_event_ids(
                    chain_record["chain"]
                )
            )

            timeline = []
            for eid in event_ids:
                for e in self._events:
                    if e["event_id"] == eid:
                        timeline.append({
                            "event_id": e[
                                "event_id"
                            ],
                            "name": e["name"],
                            "timestamp": e[
                                "timestamp"
                            ],
                            "actor": e[
                                "actor"
                            ],
                        })
                        break

            timeline.sort(
                key=lambda x: x.get(
                    "timestamp", ""
                )
            )

            return {
                "chain_id": chain_id,
                "timeline": timeline,
                "event_count": len(timeline),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def _traverse_effects(
        self,
        event_id: str,
    ) -> dict:
        """Etkileri dolasar."""
        event = None
        for e in self._events:
            if e["event_id"] == event_id:
                event = e
                break

        if not event:
            return {}

        node = {
            "event_id": event["event_id"],
            "name": event["name"],
            "event_type": event["event_type"],
            "children": [],
        }

        for eff_id in event.get(
            "effects", []
        ):
            child = self._traverse_effects(
                eff_id
            )
            if child:
                node["children"].append(child)

        return node

    def _chain_depth(
        self, chain: dict
    ) -> int:
        """Zincir derinligi."""
        if not chain:
            return 0
        children = chain.get("children", [])
        if not children:
            return 1
        return 1 + max(
            self._chain_depth(c)
            for c in children
        )

    def _count_chain_events(
        self, chain: dict
    ) -> int:
        """Zincirdeki olay sayisi."""
        if not chain:
            return 0
        count = 1
        for c in chain.get("children", []):
            count += self._count_chain_events(
                c
            )
        return count

    def _collect_all_effects(
        self,
        event_id: str,
    ) -> list[dict]:
        """Tum etkileri toplar."""
        effects = []
        event = None
        for e in self._events:
            if e["event_id"] == event_id:
                event = e
                break

        if not event:
            return effects

        for eff_id in event.get(
            "effects", []
        ):
            for e in self._events:
                if e["event_id"] == eff_id:
                    effects.append({
                        "event_id": e[
                            "event_id"
                        ],
                        "name": e["name"],
                    })
                    effects.extend(
                        self._collect_all_effects(
                            eff_id
                        )
                    )
                    break

        return effects

    def _extract_event_ids(
        self, chain: dict
    ) -> list[str]:
        """Zincirden olay ID cikartir."""
        if not chain:
            return []
        ids = [chain.get("event_id", "")]
        for c in chain.get("children", []):
            ids.extend(
                self._extract_event_ids(c)
            )
        return ids
