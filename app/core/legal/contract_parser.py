"""ATLAS Sözleşme Ayrıştırıcı modülü.

Doküman ayrıştırma, bölüm tespiti,
yapı çıkarma, metadata çıkarma,
format yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContractParser:
    """Sözleşme ayrıştırıcı.

    Sözleşme dokümanlarını ayrıştırır.

    Attributes:
        _contracts: Sözleşme kayıtları.
        _sections: Bölüm kayıtları.
    """

    def __init__(self) -> None:
        """Ayrıştırıcıyı başlatır."""
        self._contracts: dict[
            str, dict[str, Any]
        ] = {}
        self._sections: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "contracts_parsed": 0,
            "sections_detected": 0,
            "metadata_extracted": 0,
        }

        logger.info(
            "ContractParser baslatildi",
        )

    def parse_document(
        self,
        title: str,
        content: str = "",
        contract_type: str = "other",
        format_type: str = "text",
    ) -> dict[str, Any]:
        """Doküman ayrıştırır.

        Args:
            title: Başlık.
            content: İçerik.
            contract_type: Sözleşme tipi.
            format_type: Format tipi.

        Returns:
            Ayrıştırma bilgisi.
        """
        self._counter += 1
        cid = f"contract_{self._counter}"

        # Basit bölüm tespiti
        sections = self._detect_sections(
            content,
        )

        contract = {
            "contract_id": cid,
            "title": title,
            "content": content,
            "contract_type": contract_type,
            "format": format_type,
            "sections": sections,
            "word_count": len(
                content.split(),
            ),
            "metadata": {},
            "parsed_at": time.time(),
        }
        self._contracts[cid] = contract
        self._sections[cid] = sections
        self._stats[
            "contracts_parsed"
        ] += 1

        return {
            "contract_id": cid,
            "title": title,
            "sections_found": len(
                sections,
            ),
            "word_count": contract[
                "word_count"
            ],
            "parsed": True,
        }

    def detect_sections(
        self,
        contract_id: str,
    ) -> dict[str, Any]:
        """Bölüm tespit eder.

        Args:
            contract_id: Sözleşme ID.

        Returns:
            Bölüm bilgisi.
        """
        if (
            contract_id
            not in self._contracts
        ):
            return {
                "contract_id": contract_id,
                "detected": False,
            }

        sections = self._sections.get(
            contract_id, [],
        )

        return {
            "contract_id": contract_id,
            "sections": sections,
            "count": len(sections),
            "detected": True,
        }

    def extract_structure(
        self,
        contract_id: str,
    ) -> dict[str, Any]:
        """Yapı çıkarır.

        Args:
            contract_id: Sözleşme ID.

        Returns:
            Yapı bilgisi.
        """
        if (
            contract_id
            not in self._contracts
        ):
            return {
                "contract_id": contract_id,
                "extracted": False,
            }

        contract = self._contracts[
            contract_id
        ]
        sections = self._sections.get(
            contract_id, [],
        )

        structure = {
            "title": contract["title"],
            "type": contract[
                "contract_type"
            ],
            "sections": [
                s["title"] for s in sections
            ],
            "depth": max(
                (
                    s.get("level", 1)
                    for s in sections
                ),
                default=0,
            ),
        }

        return {
            "contract_id": contract_id,
            "structure": structure,
            "section_count": len(sections),
            "extracted": True,
        }

    def extract_metadata(
        self,
        contract_id: str,
        parties: list[str]
        | None = None,
        effective_date: str = "",
        expiry_date: str = "",
    ) -> dict[str, Any]:
        """Metadata çıkarır.

        Args:
            contract_id: Sözleşme ID.
            parties: Taraflar.
            effective_date: Yürürlük tarihi.
            expiry_date: Bitiş tarihi.

        Returns:
            Metadata bilgisi.
        """
        if (
            contract_id
            not in self._contracts
        ):
            return {
                "contract_id": contract_id,
                "extracted": False,
            }

        metadata = {
            "parties": parties or [],
            "effective_date": (
                effective_date
            ),
            "expiry_date": expiry_date,
            "party_count": len(
                parties or [],
            ),
        }

        self._contracts[contract_id][
            "metadata"
        ] = metadata
        self._stats[
            "metadata_extracted"
        ] += 1

        return {
            "contract_id": contract_id,
            "metadata": metadata,
            "extracted": True,
        }

    def handle_format(
        self,
        content: str,
        source_format: str = "text",
    ) -> dict[str, Any]:
        """Format yönetir.

        Args:
            content: İçerik.
            source_format: Kaynak format.

        Returns:
            Format bilgisi.
        """
        supported = [
            "text", "pdf", "docx",
            "html", "markdown",
        ]
        is_supported = (
            source_format in supported
        )

        word_count = len(content.split())

        return {
            "source_format": source_format,
            "supported": is_supported,
            "word_count": word_count,
            "char_count": len(content),
        }

    def _detect_sections(
        self,
        content: str,
    ) -> list[dict[str, Any]]:
        """Bölümleri tespit eder."""
        sections = []
        lines = content.split("\n")
        section_num = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Basit bölüm tespiti
            is_section = (
                stripped[0].isdigit()
                and "." in stripped[:5]
            ) or stripped.isupper()

            if is_section:
                section_num += 1
                sections.append({
                    "number": section_num,
                    "title": stripped,
                    "level": 1,
                })
                self._stats[
                    "sections_detected"
                ] += 1

        return sections

    def get_contract(
        self,
        contract_id: str,
    ) -> dict[str, Any] | None:
        """Sözleşme döndürür."""
        return self._contracts.get(
            contract_id,
        )

    def list_contracts(
        self,
    ) -> list[dict[str, Any]]:
        """Sözleşmeleri listeler."""
        return [
            {
                "contract_id": c[
                    "contract_id"
                ],
                "title": c["title"],
                "type": c["contract_type"],
            }
            for c in
            self._contracts.values()
        ]

    @property
    def contract_count(self) -> int:
        """Sözleşme sayısı."""
        return self._stats[
            "contracts_parsed"
        ]

    @property
    def section_count(self) -> int:
        """Bölüm sayısı."""
        return self._stats[
            "sections_detected"
        ]
