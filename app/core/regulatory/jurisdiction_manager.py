"""ATLAS Yetki Alanı Yöneticisi modulu.

Coğrafi kurallar, sektör kuralları,
platform kuralları, zamanlı kurallar, çakışma yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class JurisdictionManager:
    """Yetki alanı yöneticisi.

    Kuralların yetki alanlarını yönetir.

    Attributes:
        _jurisdictions: Yetki alanı kayıtları.
        _mappings: Kural-yetki eşlemeleri.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._jurisdictions: dict[
            str, dict[str, Any]
        ] = {}
        self._mappings: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "jurisdictions": 0,
            "mappings": 0,
        }

        logger.info(
            "JurisdictionManager baslatildi",
        )

    def add_jurisdiction(
        self,
        name: str,
        scope: str = "global",
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yetki alanı ekler.

        Args:
            name: Alan adı.
            scope: Kapsam.
            properties: Özellikler.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        jid = f"jur_{self._counter}"

        self._jurisdictions[jid] = {
            "jurisdiction_id": jid,
            "name": name,
            "scope": scope,
            "properties": properties or {},
            "active": True,
            "created_at": time.time(),
        }
        self._mappings[jid] = []
        self._stats["jurisdictions"] += 1

        return {
            "jurisdiction_id": jid,
            "name": name,
            "scope": scope,
            "added": True,
        }

    def map_rule(
        self,
        jurisdiction_id: str,
        rule_id: str,
    ) -> dict[str, Any]:
        """Kural eşler.

        Args:
            jurisdiction_id: Yetki alanı ID.
            rule_id: Kural ID.

        Returns:
            Eşleme bilgisi.
        """
        if (
            jurisdiction_id
            not in self._jurisdictions
        ):
            return {
                "error": (
                    "jurisdiction_not_found"
                ),
            }

        if (
            rule_id
            not in self._mappings[
                jurisdiction_id
            ]
        ):
            self._mappings[
                jurisdiction_id
            ].append(rule_id)
            self._stats["mappings"] += 1

        return {
            "jurisdiction_id": jurisdiction_id,
            "rule_id": rule_id,
            "mapped": True,
        }

    def get_applicable_rules(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Uygulanabilir kuralları bulur.

        Args:
            context: İşlem bağlamı.

        Returns:
            Kural listesi.
        """
        geo = context.get("geography", "")
        industry = context.get("industry", "")
        platform = context.get("platform", "")

        applicable_jids = []

        for jid, j in (
            self._jurisdictions.items()
        ):
            if not j["active"]:
                continue

            scope = j["scope"]
            props = j["properties"]

            if scope == "global":
                applicable_jids.append(jid)
            elif scope == "regional":
                regions = props.get(
                    "regions", [],
                )
                if geo in regions:
                    applicable_jids.append(jid)
            elif scope == "national":
                countries = props.get(
                    "countries", [],
                )
                if geo in countries:
                    applicable_jids.append(jid)
            elif scope == "industry":
                industries = props.get(
                    "industries", [],
                )
                if industry in industries:
                    applicable_jids.append(jid)
            elif scope == "platform":
                platforms = props.get(
                    "platforms", [],
                )
                if platform in platforms:
                    applicable_jids.append(jid)

        # Eşlenmiş kuralları topla
        rule_ids: list[str] = []
        for jid in applicable_jids:
            rule_ids.extend(
                self._mappings.get(jid, []),
            )

        # Tekrarları kaldır, sırayı koru
        seen: set[str] = set()
        unique: list[str] = []
        for rid in rule_ids:
            if rid not in seen:
                seen.add(rid)
                unique.append(rid)

        return {
            "applicable_jurisdictions": (
                applicable_jids
            ),
            "rule_ids": unique,
            "rule_count": len(unique),
        }

    def check_overlaps(
        self,
        rule_id: str,
    ) -> dict[str, Any]:
        """Çakışma kontrolü yapar.

        Args:
            rule_id: Kural ID.

        Returns:
            Çakışma bilgisi.
        """
        jids_with_rule = [
            jid
            for jid, rules in (
                self._mappings.items()
            )
            if rule_id in rules
        ]

        overlaps = []
        for i, jid1 in enumerate(
            jids_with_rule,
        ):
            for jid2 in jids_with_rule[i + 1:]:
                overlaps.append({
                    "jurisdiction_1": jid1,
                    "jurisdiction_2": jid2,
                })

        return {
            "rule_id": rule_id,
            "jurisdictions": jids_with_rule,
            "overlaps": overlaps,
            "overlap_count": len(overlaps),
        }

    def get_jurisdiction(
        self,
        jurisdiction_id: str,
    ) -> dict[str, Any]:
        """Yetki alanı getirir.

        Args:
            jurisdiction_id: Yetki alanı ID.

        Returns:
            Yetki alanı bilgisi.
        """
        j = self._jurisdictions.get(
            jurisdiction_id,
        )
        if not j:
            return {
                "error": (
                    "jurisdiction_not_found"
                ),
            }
        return dict(j)

    def get_rules_for_jurisdiction(
        self,
        jurisdiction_id: str,
    ) -> list[str]:
        """Yetki alanı kurallarını getirir.

        Args:
            jurisdiction_id: Yetki alanı ID.

        Returns:
            Kural ID listesi.
        """
        return list(
            self._mappings.get(
                jurisdiction_id, [],
            ),
        )

    @property
    def jurisdiction_count(self) -> int:
        """Yetki alanı sayısı."""
        return self._stats["jurisdictions"]

    @property
    def mapping_count(self) -> int:
        """Eşleme sayısı."""
        return self._stats["mappings"]
