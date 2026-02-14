"""ATLAS Ozet Olusturucu modulu.

Gunluk/haftalik ozetler, toplama
kurallari, ozet uretimi, kisiselleştirme
ve zamanlama.
"""

import logging
from typing import Any

from app.models.notification_system import (
    DigestFrequency,
    NotificationPriority,
)

logger = logging.getLogger(__name__)


class DigestBuilder:
    """Ozet olusturucu.

    Bildirimleri ozetler ve
    periyodik raporlar olusturur.

    Attributes:
        _items: Ozet ogoleri.
        _subscriptions: Abonelikler.
        _rules: Toplama kurallari.
    """

    def __init__(self) -> None:
        """Ozet olusturucuyu baslatir."""
        self._items: list[dict[str, Any]] = []
        self._subscriptions: dict[
            str, dict[str, Any]
        ] = {}
        self._rules: dict[str, dict[str, Any]] = {}
        self._generated: list[dict[str, Any]] = []

        logger.info("DigestBuilder baslatildi")

    def add_item(
        self,
        category: str,
        title: str,
        summary: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> dict[str, Any]:
        """Ozet ogesi ekler.

        Args:
            category: Kategori.
            title: Baslik.
            summary: Ozet.
            priority: Oncelik.

        Returns:
            Oge bilgisi.
        """
        item = {
            "category": category,
            "title": title,
            "summary": summary,
            "priority": priority.value,
        }
        self._items.append(item)
        return item

    def subscribe(
        self,
        user_id: str,
        frequency: DigestFrequency = DigestFrequency.DAILY,
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ozet aboneligi olusturur.

        Args:
            user_id: Kullanici ID.
            frequency: Siklik.
            categories: Kategori filtresi.

        Returns:
            Abonelik bilgisi.
        """
        sub = {
            "user_id": user_id,
            "frequency": frequency.value,
            "categories": categories or [],
            "enabled": True,
        }
        self._subscriptions[user_id] = sub
        return sub

    def unsubscribe(self, user_id: str) -> bool:
        """Aboneligi iptal eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Basarili ise True.
        """
        if user_id in self._subscriptions:
            del self._subscriptions[user_id]
            return True
        return False

    def build_digest(
        self,
        user_id: str | None = None,
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ozet olusturur.

        Args:
            user_id: Kullanici filtresi.
            categories: Kategori filtresi.

        Returns:
            Ozet.
        """
        # Kullanici filtresine bak
        cat_filter = categories
        if user_id and not cat_filter:
            sub = self._subscriptions.get(user_id)
            if sub and sub["categories"]:
                cat_filter = sub["categories"]

        # Filtreleme
        filtered = self._items
        if cat_filter:
            filtered = [
                i for i in filtered
                if i["category"] in cat_filter
            ]

        # Kategorilere ayir
        by_category: dict[str, list[dict[str, Any]]] = {}
        for item in filtered:
            cat = item["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        digest = {
            "user_id": user_id,
            "total_items": len(filtered),
            "categories": by_category,
            "category_count": len(by_category),
        }
        self._generated.append(digest)
        return digest

    def add_rule(
        self,
        name: str,
        min_priority: NotificationPriority = NotificationPriority.LOW,
        max_items: int = 50,
    ) -> dict[str, Any]:
        """Toplama kurali ekler.

        Args:
            name: Kural adi.
            min_priority: Minimum oncelik.
            max_items: Maks oge sayisi.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "min_priority": min_priority.value,
            "max_items": max_items,
        }
        self._rules[name] = rule
        return rule

    def clear_items(self) -> int:
        """Ogeleri temizler.

        Returns:
            Temizlenen oge sayisi.
        """
        count = len(self._items)
        self._items.clear()
        return count

    @property
    def item_count(self) -> int:
        """Oge sayisi."""
        return len(self._items)

    @property
    def subscription_count(self) -> int:
        """Abonelik sayisi."""
        return len(self._subscriptions)

    @property
    def digest_count(self) -> int:
        """Uretilen ozet sayisi."""
        return len(self._generated)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)
