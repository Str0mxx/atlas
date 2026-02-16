"""ATLAS Kişi Profilleyici modülü.

Profil oluşturma, veri toplama,
zenginleştirme, etiketleme,
kategorilendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContactProfiler:
    """Kişi profilleyici.

    Kişi profillerini oluşturur ve yönetir.

    Attributes:
        _contacts: Kişi kayıtları.
        _tags: Etiket indeksi.
    """

    def __init__(self) -> None:
        """Profilleyiciyi başlatır."""
        self._contacts: dict[
            str, dict[str, Any]
        ] = {}
        self._tags: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "contacts_created": 0,
            "enrichments": 0,
            "tags_applied": 0,
        }

        logger.info(
            "ContactProfiler baslatildi",
        )

    def create_profile(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        category: str = "other",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Profil oluşturur.

        Args:
            name: Kişi adı.
            email: E-posta.
            phone: Telefon.
            company: Şirket.
            category: Kategori.
            tags: Etiketler.

        Returns:
            Profil bilgisi.
        """
        self._counter += 1
        cid = f"contact_{self._counter}"

        contact = {
            "contact_id": cid,
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "category": category,
            "tags": tags or [],
            "metadata": {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._contacts[cid] = contact
        self._stats[
            "contacts_created"
        ] += 1

        if tags:
            for tag in tags:
                self._index_tag(tag, cid)

        return {
            "contact_id": cid,
            "name": name,
            "category": category,
            "created": True,
        }

    def aggregate_data(
        self,
        contact_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Veri toplar.

        Args:
            contact_id: Kişi ID.
            data: Ek veriler.

        Returns:
            Toplama bilgisi.
        """
        if (
            contact_id
            not in self._contacts
        ):
            return {
                "contact_id": contact_id,
                "aggregated": False,
            }

        contact = self._contacts[
            contact_id
        ]
        contact["metadata"].update(data)
        contact["updated_at"] = time.time()

        return {
            "contact_id": contact_id,
            "fields_added": len(data),
            "aggregated": True,
        }

    def enrich_profile(
        self,
        contact_id: str,
        source: str = "",
        data: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Profili zenginleştirir.

        Args:
            contact_id: Kişi ID.
            source: Kaynak.
            data: Zenginleştirme verisi.

        Returns:
            Zenginleştirme bilgisi.
        """
        if (
            contact_id
            not in self._contacts
        ):
            return {
                "contact_id": contact_id,
                "enriched": False,
            }

        data = data or {}
        contact = self._contacts[
            contact_id
        ]

        for key, value in data.items():
            if key not in contact:
                contact[key] = value
            elif key == "metadata":
                contact["metadata"].update(
                    value,
                )

        contact["updated_at"] = time.time()
        self._stats["enrichments"] += 1

        return {
            "contact_id": contact_id,
            "source": source,
            "fields_enriched": len(data),
            "enriched": True,
        }

    def add_tags(
        self,
        contact_id: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """Etiket ekler.

        Args:
            contact_id: Kişi ID.
            tags: Etiketler.

        Returns:
            Etiketleme bilgisi.
        """
        if (
            contact_id
            not in self._contacts
        ):
            return {
                "contact_id": contact_id,
                "tagged": False,
            }

        contact = self._contacts[
            contact_id
        ]
        added = 0
        for tag in tags:
            if tag not in contact["tags"]:
                contact["tags"].append(tag)
                self._index_tag(
                    tag, contact_id,
                )
                added += 1

        self._stats[
            "tags_applied"
        ] += added

        return {
            "contact_id": contact_id,
            "tags_added": added,
            "total_tags": len(
                contact["tags"],
            ),
            "tagged": True,
        }

    def categorize(
        self,
        contact_id: str,
        category: str,
    ) -> dict[str, Any]:
        """Kategorize eder.

        Args:
            contact_id: Kişi ID.
            category: Yeni kategori.

        Returns:
            Kategori bilgisi.
        """
        if (
            contact_id
            not in self._contacts
        ):
            return {
                "contact_id": contact_id,
                "categorized": False,
            }

        contact = self._contacts[
            contact_id
        ]
        old = contact["category"]
        contact["category"] = category

        return {
            "contact_id": contact_id,
            "old_category": old,
            "new_category": category,
            "categorized": True,
        }

    def get_contact(
        self,
        contact_id: str,
    ) -> dict[str, Any] | None:
        """Kişi döndürür."""
        return self._contacts.get(
            contact_id,
        )

    def search_contacts(
        self,
        category: str = "",
        tag: str = "",
    ) -> list[dict[str, Any]]:
        """Kişi arar."""
        results = list(
            self._contacts.values(),
        )
        if category:
            results = [
                c for c in results
                if c["category"] == category
            ]
        if tag:
            results = [
                c for c in results
                if tag in c["tags"]
            ]
        return results

    def _index_tag(
        self, tag: str, contact_id: str,
    ) -> None:
        """Etiket indeksler."""
        if tag not in self._tags:
            self._tags[tag] = []
        if (
            contact_id
            not in self._tags[tag]
        ):
            self._tags[tag].append(
                contact_id,
            )

    @property
    def contact_count(self) -> int:
        """Kişi sayısı."""
        return self._stats[
            "contacts_created"
        ]

    @property
    def tag_count(self) -> int:
        """Etiket sayısı."""
        return len(self._tags)
