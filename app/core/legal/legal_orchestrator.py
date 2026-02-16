"""ATLAS Hukuki Orkestratör modülü.

Tam hukuki analiz pipeline,
Parse → Extract → Analyze → Compare → Advise,
sözleşme yaşam döngüsü, analitik.
"""

import logging
import time
from typing import Any

from app.core.legal.clause_extractor import (
    ClauseExtractor,
)
from app.core.legal.compliance_checker import (
    LegalComplianceChecker,
)
from app.core.legal.contract_comparator import (
    ContractComparator,
)
from app.core.legal.contract_parser import (
    ContractParser,
)
from app.core.legal.deadline_extractor import (
    LegalDeadlineExtractor,
)
from app.core.legal.legal_summarizer import (
    LegalSummarizer,
)
from app.core.legal.negotiation_advisor import (
    LegalNegotiationAdvisor,
)
from app.core.legal.risk_highlighter import (
    RiskHighlighter,
)

logger = logging.getLogger(__name__)


class LegalOrchestrator:
    """Hukuki orkestratör.

    Tüm hukuki analiz bileşenlerini
    koordine eder.

    Attributes:
        parser: Sözleşme ayrıştırıcı.
        clauses: Madde çıkarıcı.
        risks: Risk işaretleyici.
        compliance: Uyumluluk kontrolcüsü.
        deadlines: Son tarih çıkarıcı.
        summarizer: Özetleyici.
        comparator: Karşılaştırıcı.
        advisor: Müzakere danışmanı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.parser = ContractParser()
        self.clauses = ClauseExtractor()
        self.risks = RiskHighlighter()
        self.compliance = (
            LegalComplianceChecker()
        )
        self.deadlines = (
            LegalDeadlineExtractor()
        )
        self.summarizer = LegalSummarizer()
        self.comparator = (
            ContractComparator()
        )
        self.advisor = (
            LegalNegotiationAdvisor()
        )
        self._stats = {
            "contracts_analyzed": 0,
            "full_pipelines": 0,
        }

        logger.info(
            "LegalOrchestrator baslatildi",
        )

    def analyze_contract(
        self,
        title: str,
        content: str = "",
        contract_type: str = "service",
        parties: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Tam sözleşme analizi yapar.

        Parse → Extract → Analyze pipeline.

        Args:
            title: Başlık.
            content: İçerik.
            contract_type: Sözleşme tipi.
            parties: Taraflar.

        Returns:
            Analiz bilgisi.
        """
        parties = parties or []

        # 1. Parse
        parsed = self.parser.parse_document(
            title=title,
            content=content,
            contract_type=contract_type,
        )
        cid = parsed["contract_id"]

        # 2. Metadata
        self.parser.extract_metadata(
            cid, parties=parties,
        )

        # 3. Summary
        self.summarizer.create_executive_summary(
            contract_id=cid,
            title=title,
            contract_type=contract_type,
            parties=parties,
        )

        # 4. Red flags
        red_flags = (
            self.risks.detect_red_flags(
                cid, text=content,
            )
        )

        self._stats[
            "contracts_analyzed"
        ] += 1

        return {
            "contract_id": cid,
            "title": title,
            "sections": parsed[
                "sections_found"
            ],
            "red_flags": red_flags[
                "count"
            ],
            "parties": len(parties),
            "analyzed": True,
        }

    def run_full_pipeline(
        self,
        title: str,
        content: str = "",
        contract_type: str = "service",
        parties: list[str]
        | None = None,
        regulation: str = "",
    ) -> dict[str, Any]:
        """Parse → Extract → Analyze → Advise.

        Args:
            title: Başlık.
            content: İçerik.
            contract_type: Sözleşme tipi.
            parties: Taraflar.
            regulation: Düzenleme.

        Returns:
            Pipeline bilgisi.
        """
        parties = parties or []

        # Analiz
        analysis = self.analyze_contract(
            title=title,
            content=content,
            contract_type=contract_type,
            parties=parties,
        )
        cid = analysis["contract_id"]

        # Compliance
        compliance_result = None
        if regulation:
            compliance_result = (
                self.compliance
                .check_regulatory(
                    cid, regulation,
                )
            )

        # Negotiation points
        neg_points = (
            self.advisor
            .identify_negotiation_points(
                contract_id=cid,
                risks=self.risks.get_risks(
                    cid,
                ),
            )
        )

        # Leverage
        leverage = (
            self.advisor.analyze_leverage(
                contract_id=cid,
            )
        )

        self._stats[
            "full_pipelines"
        ] += 1

        return {
            "contract_id": cid,
            "title": title,
            "red_flags": analysis[
                "red_flags"
            ],
            "compliance_status": (
                compliance_result[
                    "status"
                ] if compliance_result
                else "not_checked"
            ),
            "negotiation_points": (
                neg_points["count"]
            ),
            "leverage": leverage["level"],
            "pipeline_complete": True,
        }

    def get_contract_lifecycle(
        self,
        contract_id: str,
    ) -> dict[str, Any]:
        """Sözleşme yaşam döngüsü döndürür.

        Args:
            contract_id: Sözleşme ID.

        Returns:
            Yaşam döngüsü bilgisi.
        """
        contract = self.parser.get_contract(
            contract_id,
        )
        deadlines = (
            self.deadlines.get_deadlines(
                contract_id,
            )
        )
        versions = (
            self.comparator.get_versions(
                contract_id,
            )
        )
        risks = self.risks.get_risks(
            contract_id,
        )

        return {
            "contract_id": contract_id,
            "exists": contract is not None,
            "deadlines": len(deadlines),
            "versions": len(versions),
            "active_risks": len(risks),
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "contracts_analyzed": (
                self._stats[
                    "contracts_analyzed"
                ]
            ),
            "full_pipelines": (
                self._stats[
                    "full_pipelines"
                ]
            ),
            "total_contracts": (
                self.parser.contract_count
            ),
            "total_clauses": (
                self.clauses.clause_count
            ),
            "total_risks": (
                self.risks.risk_count
            ),
            "red_flags": (
                self.risks.red_flag_count
            ),
            "compliance_checks": (
                self.compliance.check_count
            ),
            "deadlines_tracked": (
                self.deadlines
                .deadline_count
            ),
            "summaries": (
                self.summarizer
                .summary_count
            ),
            "comparisons": (
                self.comparator
                .comparison_count
            ),
            "negotiation_points": (
                self.advisor.point_count
            ),
        }

    @property
    def contract_count(self) -> int:
        """Sözleşme sayısı."""
        return self.parser.contract_count

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "full_pipelines"
        ]
