"""ATLAS Gorsel Aciklayici modulu.

Karar agaclari, faktor grafikleri,
zaman cizgisi gorunumleri, karsilastirma, etkilesim.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VisualExplainer:
    """Gorsel aciklayici.

    Karar sureclerini gorsel olarak aciklar.

    Attributes:
        _visuals: Gorsel kayitlari.
    """

    def __init__(self) -> None:
        """Gorsel aciklayiciyi baslatir."""
        self._visuals: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "generated": 0,
        }

        logger.info(
            "VisualExplainer baslatildi",
        )

    def generate_decision_tree(
        self,
        decision_id: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Karar agaci uretir.

        Args:
            decision_id: Karar ID.
            steps: Karar adimlari.

        Returns:
            Karar agaci verisi.
        """
        nodes = []
        edges = []

        for i, step in enumerate(steps):
            node_id = f"node_{i}"
            nodes.append({
                "id": node_id,
                "label": step.get(
                    "description", "",
                ),
                "type": step.get(
                    "step_type", "step",
                ),
                "confidence": step.get(
                    "confidence", 1.0,
                ),
            })

            if i > 0:
                edges.append({
                    "from": f"node_{i - 1}",
                    "to": node_id,
                    "label": step.get(
                        "output", "",
                    ),
                })

        visual = {
            "decision_id": decision_id,
            "type": "decision_tree",
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "generated_at": time.time(),
        }

        self._visuals.append(visual)
        self._stats["generated"] += 1

        return visual

    def generate_factor_chart(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Faktor grafigi uretir.

        Args:
            decision_id: Karar ID.
            factors: Faktorler.

        Returns:
            Grafik verisi.
        """
        bars = []
        for f in factors:
            bars.append({
                "label": f.get("name", ""),
                "value": f.get(
                    "contribution", 0.0,
                ),
                "weight": f.get("weight", 0.0),
                "color": (
                    "green"
                    if f.get(
                        "contribution", 0,
                    ) > 0
                    else "red"
                ),
            })

        bars.sort(
            key=lambda x: abs(x["value"]),
            reverse=True,
        )

        visual = {
            "decision_id": decision_id,
            "type": "factor_chart",
            "chart_type": "horizontal_bar",
            "bars": bars,
            "bar_count": len(bars),
            "generated_at": time.time(),
        }

        self._visuals.append(visual)
        self._stats["generated"] += 1

        return visual

    def generate_timeline(
        self,
        decision_id: str,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Zaman cizgisi gorunumu uretir.

        Args:
            decision_id: Karar ID.
            events: Olaylar.

        Returns:
            Zaman cizgisi verisi.
        """
        timeline = []
        for i, event in enumerate(events):
            timeline.append({
                "index": i,
                "label": event.get(
                    "description",
                    event.get("label", ""),
                ),
                "timestamp": event.get(
                    "timestamp", 0,
                ),
                "type": event.get("type", ""),
                "details": event.get(
                    "details", "",
                ),
            })

        duration = 0.0
        if len(timeline) >= 2:
            first_ts = timeline[0]["timestamp"]
            last_ts = timeline[-1]["timestamp"]
            duration = last_ts - first_ts

        visual = {
            "decision_id": decision_id,
            "type": "timeline",
            "events": timeline,
            "event_count": len(timeline),
            "duration_seconds": round(
                duration, 2,
            ),
            "generated_at": time.time(),
        }

        self._visuals.append(visual)
        self._stats["generated"] += 1

        return visual

    def generate_comparison(
        self,
        decision_id: str,
        alternatives: list[dict[str, Any]],
        criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        """Karsilastirma gorunumu uretir.

        Args:
            decision_id: Karar ID.
            alternatives: Alternatifler.
            criteria: Karsilastirma kriterleri.

        Returns:
            Karsilastirma verisi.
        """
        if criteria is None:
            criteria = []
            for alt in alternatives:
                for key in alt:
                    if (
                        key not in criteria
                        and key != "name"
                    ):
                        criteria.append(key)

        rows = []
        for alt in alternatives:
            row = {
                "name": alt.get("name", ""),
            }
            for c in criteria:
                row[c] = alt.get(c, "-")
            rows.append(row)

        visual = {
            "decision_id": decision_id,
            "type": "comparison",
            "criteria": criteria,
            "alternatives": rows,
            "count": len(rows),
            "generated_at": time.time(),
        }

        self._visuals.append(visual)
        self._stats["generated"] += 1

        return visual

    def generate_impact_map(
        self,
        decision_id: str,
        impacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Etki haritasi uretir.

        Args:
            decision_id: Karar ID.
            impacts: Etkiler.

        Returns:
            Etki haritasi verisi.
        """
        nodes = []
        for i, impact in enumerate(impacts):
            nodes.append({
                "id": f"impact_{i}",
                "area": impact.get("area", ""),
                "magnitude": impact.get(
                    "magnitude", 0.0,
                ),
                "direction": impact.get(
                    "direction", "neutral",
                ),
                "description": impact.get(
                    "description", "",
                ),
            })

        visual = {
            "decision_id": decision_id,
            "type": "impact_map",
            "nodes": nodes,
            "node_count": len(nodes),
            "generated_at": time.time(),
        }

        self._visuals.append(visual)
        self._stats["generated"] += 1

        return visual

    def get_visuals(
        self,
        decision_id: str | None = None,
        visual_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gorselleri getirir.

        Args:
            decision_id: Karar filtresi.
            visual_type: Tip filtresi.
            limit: Limit.

        Returns:
            Gorsel listesi.
        """
        visuals = self._visuals
        if decision_id:
            visuals = [
                v for v in visuals
                if v.get("decision_id")
                == decision_id
            ]
        if visual_type:
            visuals = [
                v for v in visuals
                if v.get("type") == visual_type
            ]
        return visuals[-limit:]

    @property
    def visual_count(self) -> int:
        """Gorsel sayisi."""
        return self._stats["generated"]
