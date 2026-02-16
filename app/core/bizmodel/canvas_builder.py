"""
Is Modeli Canvas olusturucu modulu.

Business Model Canvas yapilarini olusturur,
bolum yonetimi, sablon ve versiyon destegi
saglar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CanvasBuilder:
    """
    Business Model Canvas olusturucu.

    9 bolumlu BMC yapilari olusturur,
    sablon destegi ve versiyon yonetimi
    saglar.

    Attributes:
        _canvases: Olusturulan canvas listesi.
        _templates: Sablon haritasi.
        _stats: Istatistik sayaclari.
    """

    def __init__(self) -> None:
        """Canvas olusturucuyu baslatir."""
        self._canvases: list[dict] = []
        self._templates: dict[
            str, list[str]
        ] = {}
        self._stats: dict = {
            "canvases_created": 0
        }

    @property

    def canvas_count(self) -> int:
        """Toplam canvas sayisini dondurur."""
        return len(self._canvases)

    def create_canvas(
        self,
        name: str = "New Canvas",
        maturity: str = "ideation",
    ) -> dict[str, Any]:
        """
        Yeni Business Model Canvas olusturur.

        Args:
            name: Canvas adi.
            maturity: Olgunluk seviyesi.

        Returns:
            Olusturulan canvas bilgileri.
        """
        try:
            cid = f"cvs_{str(uuid4())[:8]}"
            sections = {
                "key_partners": [],
                "key_activities": [],
                "key_resources": [],
                "value_propositions": [],
                "customer_relationships": [],
                "channels": [],
                "customer_segments": [],
                "cost_structure": [],
                "revenue_streams": [],
            }
            canvas = {
                "canvas_id": cid,
                "name": name,
                "maturity": maturity,
                "version": 1,
                "sections": sections,
                "collaborators": [],
            }
            self._canvases.append(canvas)
            self._stats[
                "canvases_created"
            ] += 1
            logger.info(
                "Canvas olusturuldu: "
                "%s (olgunluk: %s)",
                name,
                maturity,
            )
            return canvas
        except Exception as e:
            logger.error(
                "Canvas olusturma hatasi:"
                " %s",
                e,
            )
            return {
                "created": False,
                "error": str(e),
            }

    def manage_section(
        self,
        canvas_id: str,
        section: str,
        items: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Canvas bolumunu yonetir.

        Args:
            canvas_id: Canvas kimligi.
            section: Bolum adi.
            items: Bolum ogeleri.

        Returns:
            Bolum yonetim sonucu.
        """
        try:
            canvas = None
            for c in self._canvases:
                if (
                    c["canvas_id"]
                    == canvas_id
                ):
                    canvas = c
                    break
            if canvas is None:
                return {
                    "managed": False,
                    "error": (
                        "canvas_not_found"
                    ),
                }
            if items is None:
                items = []
            canvas["sections"][
                section
            ] = items
            return {
                "canvas_id": canvas_id,
                "section": section,
                "item_count": len(items),
                "managed": True,
            }
        except Exception as e:
            logger.error(
                "Bolum yonetim hatasi:"
                " %s",
                e,
            )
            return {
                "managed": False,
                "error": str(e),
            }

    def get_template(
        self,
        template_type: str = "saas",
    ) -> dict[str, Any]:
        """
        BMC sablonu dondurur.

        Args:
            template_type: Sablon turu.

        Returns:
            Sablon bilgileri ve bilesenleri.
        """
        try:
            templates = {
                "saas": [
                    "cloud_infrastructure",
                    "subscription_billing",
                    "customer_success",
                    "product_dev",
                ],
                "marketplace": [
                    "buyer_acquisition",
                    "seller_acquisition",
                    "trust_safety",
                    "payments",
                ],
                "ecommerce": [
                    "inventory",
                    "logistics",
                    "marketing",
                    "customer_service",
                ],
                "consulting": [
                    "expertise",
                    "client_relationships",
                    "delivery",
                    "thought_leadership",
                ],
            }
            components = templates.get(
                template_type,
                ["general_template"],
            )
            return {
                "template_type": (
                    template_type
                ),
                "components": components,
                "component_count": len(
                    components
                ),
                "available": True,
            }
        except Exception as e:
            logger.error(
                "Sablon alma hatasi: %s",
                e,
            )
            return {
                "available": False,
                "error": str(e),
            }

    def version_canvas(
        self,
        canvas_id: str,
    ) -> dict[str, Any]:
        """
        Canvas versiyonunu artirir.

        Args:
            canvas_id: Canvas kimligi.

        Returns:
            Versiyon guncelleme sonucu.
        """
        try:
            canvas = None
            for c in self._canvases:
                if (
                    c["canvas_id"]
                    == canvas_id
                ):
                    canvas = c
                    break
            if canvas is None:
                return {
                    "versioned": False,
                    "error": (
                        "canvas_not_found"
                    ),
                }
            canvas["version"] += 1
            return {
                "canvas_id": canvas_id,
                "new_version": (
                    canvas["version"]
                ),
                "versioned": True,
            }
        except Exception as e:
            logger.error(
                "Versiyon hatasi: %s",
                e,
            )
            return {
                "versioned": False,
                "error": str(e),
            }

    def add_collaborator(
        self,
        canvas_id: str,
        collaborator: str = "team_member",
    ) -> dict[str, Any]:
        """
        Canvas isbirlikci ekler.

        Args:
            canvas_id: Canvas kimligi.
            collaborator: Isbirlikci adi.

        Returns:
            Isbirlikci ekleme sonucu.
        """
        try:
            canvas = None
            for c in self._canvases:
                if (
                    c["canvas_id"]
                    == canvas_id
                ):
                    canvas = c
                    break
            if canvas is None:
                return {
                    "added": False,
                    "error": (
                        "canvas_not_found"
                    ),
                }
            canvas[
                "collaborators"
            ].append(collaborator)
            return {
                "canvas_id": canvas_id,
                "collaborator": (
                    collaborator
                ),
                "total_collaborators": len(
                    canvas["collaborators"]
                ),
                "added": True,
            }
        except Exception as e:
            logger.error(
                "Isbirlikci ekleme"
                " hatasi: %s",
                e,
            )
            return {
                "added": False,
                "error": str(e),
            }
