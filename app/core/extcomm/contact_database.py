"""ATLAS İletişim Veritabanı modülü.

Kişi yönetimi, etkileşim geçmişi,
tercih takibi, ilişki puanlama,
segmentasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContactDatabase:
    """İletişim veritabanı.

    Kişileri ve etkileşimlerini yönetir.

    Attributes:
        _contacts: Kişi kayıtları.
        _interactions: Etkileşim geçmişi.
    """

    def __init__(self) -> None:
        """Veritabanını başlatır."""
        self._contacts: dict[
            str, dict[str, Any]
        ] = {}
        self._interactions: list[
            dict[str, Any]
        ] = []
        self._segments: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "contacts_added": 0,
            "interactions_logged": 0,
            "segments_created": 0,
        }

        logger.info(
            "ContactDatabase baslatildi",
        )

    def add_contact(
        self,
        name: str,
        email: str,
        company: str = "",
        role: str = "",
        channel: str = "email",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kişi ekler.

        Args:
            name: İsim.
            email: Email.
            company: Şirket.
            role: Rol.
            channel: Kanal.
            tags: Etiketler.

        Returns:
            Kişi bilgisi.
        """
        self._counter += 1
        cid = f"ct_{self._counter}"

        contact = {
            "contact_id": cid,
            "name": name,
            "email": email,
            "company": company,
            "role": role,
            "channel": channel,
            "tags": tags or [],
            "relationship_score": 0.0,
            "preferences": {},
            "interaction_count": 0,
            "last_interaction": None,
            "created_at": time.time(),
        }
        self._contacts[cid] = contact
        self._stats["contacts_added"] += 1

        return {
            "contact_id": cid,
            "name": name,
            "email": email,
            "added": True,
        }

    def get_contact(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """Kişi getirir.

        Args:
            contact_id: Kişi ID.

        Returns:
            Kişi bilgisi.
        """
        contact = self._contacts.get(
            contact_id,
        )
        if not contact:
            return {
                "error": "contact_not_found",
            }
        return dict(contact)

    def update_contact(
        self,
        contact_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Kişi günceller.

        Args:
            contact_id: Kişi ID.
            **kwargs: Güncellenecek alanlar.

        Returns:
            Güncelleme bilgisi.
        """
        contact = self._contacts.get(
            contact_id,
        )
        if not contact:
            return {
                "error": "contact_not_found",
            }

        updated_fields = []
        for key, val in kwargs.items():
            if key in contact:
                contact[key] = val
                updated_fields.append(key)

        return {
            "contact_id": contact_id,
            "updated_fields": updated_fields,
            "updated": True,
        }

    def log_interaction(
        self,
        contact_id: str,
        interaction_type: str,
        description: str = "",
        outcome: str = "",
    ) -> dict[str, Any]:
        """Etkileşim kaydeder.

        Args:
            contact_id: Kişi ID.
            interaction_type: Etkileşim tipi.
            description: Açıklama.
            outcome: Sonuç.

        Returns:
            Kayıt bilgisi.
        """
        contact = self._contacts.get(
            contact_id,
        )
        if not contact:
            return {
                "error": "contact_not_found",
            }

        self._counter += 1
        iid = f"int_{self._counter}"

        interaction = {
            "interaction_id": iid,
            "contact_id": contact_id,
            "type": interaction_type,
            "description": description,
            "outcome": outcome,
            "timestamp": time.time(),
        }
        self._interactions.append(
            interaction,
        )

        contact["interaction_count"] += 1
        contact["last_interaction"] = (
            time.time()
        )
        self._stats[
            "interactions_logged"
        ] += 1

        return {
            "interaction_id": iid,
            "contact_id": contact_id,
            "type": interaction_type,
            "logged": True,
        }

    def update_relationship_score(
        self,
        contact_id: str,
        delta: float,
    ) -> dict[str, Any]:
        """İlişki puanı günceller.

        Args:
            contact_id: Kişi ID.
            delta: Puan değişimi.

        Returns:
            Güncelleme bilgisi.
        """
        contact = self._contacts.get(
            contact_id,
        )
        if not contact:
            return {
                "error": "contact_not_found",
            }

        old_score = contact[
            "relationship_score"
        ]
        new_score = max(
            0.0,
            min(100.0, old_score + delta),
        )
        contact["relationship_score"] = (
            new_score
        )

        return {
            "contact_id": contact_id,
            "old_score": old_score,
            "new_score": new_score,
            "updated": True,
        }

    def set_preference(
        self,
        contact_id: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        """Tercih ayarlar.

        Args:
            contact_id: Kişi ID.
            key: Anahtar.
            value: Değer.

        Returns:
            Ayar bilgisi.
        """
        contact = self._contacts.get(
            contact_id,
        )
        if not contact:
            return {
                "error": "contact_not_found",
            }

        contact["preferences"][key] = value

        return {
            "contact_id": contact_id,
            "key": key,
            "set": True,
        }

    def create_segment(
        self,
        name: str,
        criteria: dict[str, Any],
    ) -> dict[str, Any]:
        """Segment oluşturur.

        Args:
            name: Segment adı.
            criteria: Filtreleme kriterleri.

        Returns:
            Segment bilgisi.
        """
        matching = []
        for cid, contact in (
            self._contacts.items()
        ):
            match = True
            for key, val in criteria.items():
                if key == "min_score":
                    if (
                        contact[
                            "relationship_score"
                        ]
                        < val
                    ):
                        match = False
                elif key == "company":
                    if contact["company"] != val:
                        match = False
                elif key == "channel":
                    if contact["channel"] != val:
                        match = False
                elif key == "tag":
                    if val not in contact.get(
                        "tags", [],
                    ):
                        match = False
            if match:
                matching.append(cid)

        self._segments[name] = matching
        self._stats["segments_created"] += 1

        return {
            "segment": name,
            "count": len(matching),
            "contact_ids": matching,
            "created": True,
        }

    def get_segment(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Segmenti getirir.

        Args:
            name: Segment adı.

        Returns:
            Segment bilgisi.
        """
        contacts = self._segments.get(name)
        if contacts is None:
            return {
                "error": "segment_not_found",
            }
        return {
            "segment": name,
            "count": len(contacts),
            "contact_ids": contacts,
        }

    def search_contacts(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Kişi arar.

        Args:
            query: Arama sorgusu.
            limit: Maks kayıt.

        Returns:
            Kişi listesi.
        """
        query_lower = query.lower()
        results = []

        for contact in (
            self._contacts.values()
        ):
            if (
                query_lower
                in contact["name"].lower()
                or query_lower
                in contact["email"].lower()
                or query_lower
                in contact[
                    "company"
                ].lower()
            ):
                results.append(
                    dict(contact),
                )

        return results[:limit]

    def get_interaction_history(
        self,
        contact_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Etkileşim geçmişi getirir.

        Args:
            contact_id: Kişi ID.
            limit: Maks kayıt.

        Returns:
            Etkileşim listesi.
        """
        results = [
            i for i in self._interactions
            if i["contact_id"] == contact_id
        ]
        return list(results[-limit:])

    @property
    def contact_count(self) -> int:
        """Kişi sayısı."""
        return len(self._contacts)

    @property
    def interaction_count(self) -> int:
        """Etkileşim sayısı."""
        return self._stats[
            "interactions_logged"
        ]
