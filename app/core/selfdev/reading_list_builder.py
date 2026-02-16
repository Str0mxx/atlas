"""
Okuma listesi oluşturucu modülü.

Kitap önerileri, konu kümeleme, ilerleme
takibi, not entegrasyonu, yorum birleştirme.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ReadingListBuilder:
    """Okuma listesi oluşturucu.

    Attributes:
        _books: Kitap kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._books: list[dict] = []
        self._stats: dict[str, int] = {
            "books_added": 0,
        }
        logger.info(
            "ReadingListBuilder baslatildi"
        )

    @property
    def book_count(self) -> int:
        """Kitap sayısı."""
        return len(self._books)

    def recommend_books(
        self,
        topic: str = "",
        count: int = 3,
    ) -> dict[str, Any]:
        """Kitap önerir.

        Args:
            topic: Konu.
            count: Öneri sayısı.

        Returns:
            Kitap önerileri.
        """
        try:
            books = [
                {
                    "title": f"{topic} Essentials",
                    "author": "Expert Author",
                    "pages": 300,
                    "rating": 4.5,
                },
                {
                    "title": f"Mastering {topic}",
                    "author": "Pro Writer",
                    "pages": 450,
                    "rating": 4.7,
                },
                {
                    "title": f"{topic} in Practice",
                    "author": "Practitioner",
                    "pages": 250,
                    "rating": 4.3,
                },
                {
                    "title": f"Advanced {topic}",
                    "author": "Senior Dev",
                    "pages": 500,
                    "rating": 4.6,
                },
            ]

            results = books[:count]

            return {
                "topic": topic,
                "books": results,
                "count": len(results),
                "recommended": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recommended": False,
                "error": str(e),
            }

    def add_to_list(
        self,
        title: str = "",
        author: str = "",
        topic: str = "",
        pages: int = 0,
    ) -> dict[str, Any]:
        """Listeye kitap ekler.

        Args:
            title: Başlık.
            author: Yazar.
            topic: Konu.
            pages: Sayfa sayısı.

        Returns:
            Ekleme bilgisi.
        """
        try:
            bid = f"bk_{uuid4()!s:.8}"

            record = {
                "book_id": bid,
                "title": title,
                "author": author,
                "topic": topic,
                "pages": pages,
                "pages_read": 0,
                "status": "not_started",
                "notes": [],
            }
            self._books.append(record)
            self._stats["books_added"] += 1

            return {
                "book_id": bid,
                "title": title,
                "author": author,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def cluster_by_topic(
        self,
    ) -> dict[str, Any]:
        """Konuya göre kümeler.

        Returns:
            Kümeleme sonucu.
        """
        try:
            clusters: dict[str, list] = {}
            for book in self._books:
                topic = book.get(
                    "topic", "general"
                )
                if topic not in clusters:
                    clusters[topic] = []
                clusters[topic].append(
                    book["title"]
                )

            return {
                "clusters": clusters,
                "topic_count": len(clusters),
                "total_books": len(self._books),
                "clustered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "clustered": False,
                "error": str(e),
            }

    def track_progress(
        self,
        book_id: str = "",
        pages_read: int = 0,
    ) -> dict[str, Any]:
        """Okuma ilerlemesini takip eder.

        Args:
            book_id: Kitap ID.
            pages_read: Okunan sayfa.

        Returns:
            İlerleme bilgisi.
        """
        try:
            book = None
            for b in self._books:
                if b["book_id"] == book_id:
                    book = b
                    break

            if not book:
                return {
                    "tracked": False,
                    "error": "book_not_found",
                }

            book["pages_read"] = pages_read
            total = book["pages"]
            pct = round(
                pages_read / total * 100, 1
            ) if total > 0 else 0.0

            if pct >= 100:
                book["status"] = "completed"
            elif pct > 0:
                book["status"] = "in_progress"

            return {
                "book_id": book_id,
                "title": book["title"],
                "pages_read": pages_read,
                "total_pages": total,
                "progress_pct": min(pct, 100.0),
                "status": book["status"],
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def add_note(
        self,
        book_id: str = "",
        note: str = "",
        page: int = 0,
    ) -> dict[str, Any]:
        """Not ekler.

        Args:
            book_id: Kitap ID.
            note: Not.
            page: Sayfa.

        Returns:
            Not bilgisi.
        """
        try:
            book = None
            for b in self._books:
                if b["book_id"] == book_id:
                    book = b
                    break

            if not book:
                return {
                    "added": False,
                    "error": "book_not_found",
                }

            nid = f"nt_{uuid4()!s:.8}"
            book["notes"].append({
                "note_id": nid,
                "note": note,
                "page": page,
            })

            return {
                "note_id": nid,
                "book_id": book_id,
                "page": page,
                "total_notes": len(
                    book["notes"]
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def aggregate_reviews(
        self,
        reviews: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Yorumları birleştirir.

        Args:
            reviews: Yorum listesi.

        Returns:
            Yorum özeti.
        """
        try:
            items = reviews or []
            if not items:
                return {
                    "aggregated": True,
                    "avg_rating": 0.0,
                    "count": 0,
                }

            ratings = [
                r.get("rating", 0)
                for r in items
            ]
            avg = round(
                sum(ratings) / len(ratings), 1
            )

            return {
                "avg_rating": avg,
                "count": len(items),
                "highest": max(ratings),
                "lowest": min(ratings),
                "aggregated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "aggregated": False,
                "error": str(e),
            }
