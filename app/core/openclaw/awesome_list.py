"""Awesome list analizcisi.

README.md dosyalarindan kurate edilmis
beceri listelerini ayristirir ve
guvenlik sonuclariyla capraz referanslar.
"""

import logging
import re
import time
from typing import Any

from app.models.openclaw_models import (
    AwesomeListEntry,
    SecurityScanResult,
)

logger = logging.getLogger(__name__)

_MAX_HISTORY = 5000

# Markdown link kaliplari
_LINK_RE = re.compile(
    r"-\s+\[([^\]]+)\]\(([^)]+)\)"
    r"\s*[-–]?\s*(.*)",
)
_HEADER_RE = re.compile(
    r"^#{1,3}\s+(.+)$",
    re.MULTILINE,
)


class AwesomeListAnalyzer:
    """Awesome list analizcisi.

    README.md dosyalarindan kurate edilmis
    becerileri ayristirir ve premium
    olarak isaretler.

    Attributes:
        _entries: Ayristirilan girdiler.
    """

    def __init__(self) -> None:
        """AwesomeListAnalyzer baslatir."""
        self._entries: list[
            AwesomeListEntry
        ] = []
        self._by_name: dict[
            str, AwesomeListEntry
        ] = {}
        self._by_category: dict[
            str, list[AwesomeListEntry]
        ] = {}
        self._premium: list[
            AwesomeListEntry
        ] = []
        self._total_ops: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

    # ---- Ayristirma ----

    def parse_readme(
        self,
        content: str,
    ) -> list[AwesomeListEntry]:
        """README.md icerigini ayristirir.

        ## Category basliklari ve
        - [name](url) - description satirlari.

        Args:
            content: README.md icerigi.

        Returns:
            Girdi listesi.
        """
        self._total_ops += 1
        entries: list[AwesomeListEntry] = []
        current_category = ""

        for line in content.split("\n"):
            line = line.strip()

            # Baslik kontrolu
            header_match = _HEADER_RE.match(line)
            if header_match:
                current_category = (
                    header_match.group(1).strip()
                )
                continue

            # Link kontrolu
            link_match = _LINK_RE.match(line)
            if link_match:
                name = link_match.group(
                    1,
                ).strip()
                url = link_match.group(
                    2,
                ).strip()
                desc = link_match.group(
                    3,
                ).strip()

                entry = AwesomeListEntry(
                    name=name,
                    url=url,
                    description=desc,
                    category=current_category,
                    is_curated=True,
                )
                entries.append(entry)
                self._by_name[
                    name.lower()
                ] = entry

                if current_category:
                    cat_list = (
                        self._by_category
                        .setdefault(
                            current_category, [],
                        )
                    )
                    cat_list.append(entry)

        self._entries.extend(entries)

        self._record_history(
            "parse_readme",
            "readme",
            f"entries={len(entries)}",
        )
        return entries

    def parse_file(
        self,
        file_path: str,
    ) -> list[AwesomeListEntry]:
        """README.md dosyasini ayristirir.

        Args:
            file_path: Dosya yolu.

        Returns:
            Girdi listesi.
        """
        try:
            with open(
                file_path, "r",
                encoding="utf-8",
                errors="replace",
            ) as f:
                content = f.read()
            return self.parse_readme(content)
        except Exception as e:
            logger.warning(
                "README okunamadi: %s: %s",
                file_path, e,
            )
            return []

    # ---- Capraz Referans ----

    def cross_reference(
        self,
        scan_results: list[SecurityScanResult],
        min_score: int = 70,
    ) -> list[AwesomeListEntry]:
        """Guvenlik sonuclariyla capraz referanslar.

        Args:
            scan_results: Tarama sonuclari.
            min_score: Minimum puan.

        Returns:
            Guncellenmis girdi listesi.
        """
        self._total_ops += 1

        # Sonuclari isme gore indeksle
        scan_by_name: dict[
            str, SecurityScanResult
        ] = {}
        for sr in scan_results:
            name_lower = sr.skill_name.lower()
            scan_by_name[name_lower] = sr

        updated: list[AwesomeListEntry] = []

        for entry in self._entries:
            name_lower = entry.name.lower()
            sr = scan_by_name.get(name_lower)
            if sr:
                entry.security_score = sr.score
                # Kurate edilmis + guvenli = premium
                if (
                    entry.is_curated
                    and sr.score >= min_score
                ):
                    entry.is_premium = True
                    if entry not in self._premium:
                        self._premium.append(
                            entry,
                        )
                updated.append(entry)

        self._record_history(
            "cross_reference",
            "batch",
            f"updated={len(updated)} "
            f"premium={len(self._premium)}",
        )
        return updated

    # ---- Premium ----

    def get_premium_skills(
        self,
    ) -> list[AwesomeListEntry]:
        """Premium becerileri dondurur.

        Returns:
            Premium girdi listesi.
        """
        return list(self._premium)

    # ---- Sorgulama ----

    def get_entry(
        self,
        name: str,
    ) -> AwesomeListEntry | None:
        """Isimle girdi dondurur.

        Args:
            name: Beceri adi.

        Returns:
            Girdi veya None.
        """
        return self._by_name.get(name.lower())

    def list_entries(
        self,
        category: str = "",
        limit: int = 100,
    ) -> list[AwesomeListEntry]:
        """Girdileri listeler.

        Args:
            category: Kategori filtresi.
            limit: Maks sayi.

        Returns:
            Girdi listesi.
        """
        if category:
            entries = self._by_category.get(
                category, [],
            )
        else:
            entries = self._entries

        return entries[:limit]

    def list_categories(
        self,
    ) -> list[dict[str, Any]]:
        """Kategorileri listeler.

        Returns:
            Kategori bilgileri.
        """
        return [
            {
                "category": cat,
                "count": len(entries),
            }
            for cat, entries
            in self._by_category.items()
        ]

    def search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[AwesomeListEntry]:
        """Girdileri arar.

        Args:
            query: Arama sorgusu.
            limit: Maks sayi.

        Returns:
            Eslesen girdiler.
        """
        q = query.lower()
        result: list[AwesomeListEntry] = []
        for entry in self._entries:
            if (
                q in entry.name.lower()
                or q in entry.description.lower()
                or q in entry.category.lower()
            ):
                result.append(entry)
                if len(result) >= limit:
                    break
        return result

    # ---- Dahili ----

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-2500:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "total_entries": len(self._entries),
            "total_categories": len(
                self._by_category,
            ),
            "total_premium": len(self._premium),
            "total_ops": self._total_ops,
        }
