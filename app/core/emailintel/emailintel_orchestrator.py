"""ATLAS Email Zekası Orkestratörü.

Tam email zekası pipeline,
Receive → Classify → Prioritize → Extract → Respond,
inbox zero desteği, analitik.
"""

import logging
import time
from typing import Any

from app.core.emailintel.action_extractor import (
    EmailActionExtractor,
)
from app.core.emailintel.email_classifier import (
    EmailClassifier,
)
from app.core.emailintel.email_digest import (
    EmailDigest,
)
from app.core.emailintel.followup_tracker import (
    EmailFollowUpTracker,
)
from app.core.emailintel.priority_inbox import (
    PriorityInbox,
)
from app.core.emailintel.smart_responder import (
    EmailSmartResponder,
)
from app.core.emailintel.spam_filter import (
    IntelligentSpamFilter,
)
from app.core.emailintel.thread_analyzer import (
    ThreadAnalyzer,
)

logger = logging.getLogger(__name__)


class EmailIntelOrchestrator:
    """Email zekası orkestratörü.

    Tüm email zekası bileşenlerini
    koordine eder.

    Attributes:
        classifier: Sınıflandırıcı.
        inbox: Gelen kutusu.
        responder: Yanıtlayıcı.
        actions: Aksiyon çıkarıcı.
        followups: Takip takipçisi.
        spam: Spam filtresi.
        digest: Özet.
        threads: Analizci.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.classifier = EmailClassifier()
        self.inbox = PriorityInbox()
        self.responder = (
            EmailSmartResponder()
        )
        self.actions = (
            EmailActionExtractor()
        )
        self.followups = (
            EmailFollowUpTracker()
        )
        self.spam = IntelligentSpamFilter()
        self.digest = EmailDigest()
        self.threads = ThreadAnalyzer()
        self._stats = {
            "pipelines_run": 0,
            "emails_processed": 0,
        }

        logger.info(
            "EmailIntelOrchestrator "
            "baslatildi",
        )

    def process_email(
        self,
        email_id: str = "",
        sender: str = "",
        subject: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """Receive → Classify → Prioritize → Extract → Respond.

        Args:
            email_id: Email kimliği.
            sender: Gönderici.
            subject: Konu.
            body: Gövde.

        Returns:
            İşleme bilgisi.
        """
        # 1. Spam kontrol
        spam_result = self.spam.ml_filter(
            subject=subject,
            body=body,
            sender=sender,
        )

        if spam_result["verdict"] == "spam":
            self._stats[
                "emails_processed"
            ] += 1
            return {
                "email_id": email_id,
                "verdict": "spam",
                "blocked": True,
                "pipeline_complete": True,
            }

        # 2. Classify
        classification = (
            self.classifier.detect_category(
                subject=subject,
                body=body,
                sender=sender,
            )
        )

        # 3. Prioritize
        priority = (
            self.classifier.assign_priority(
                subject=subject,
                body=body,
                sender=sender,
            )
        )

        # 4. Add to inbox
        self.inbox.add_email(
            email_id=email_id,
            sender=sender,
            subject=subject,
            priority=priority["priority"],
        )

        # 5. Extract actions
        actions = (
            self.actions.extract_tasks(
                email_id=email_id,
                body=body,
            )
        )

        # 6. Check intent & respond
        intent = (
            self.classifier.detect_intent(
                subject=subject,
                body=body,
            )
        )

        response = None
        if intent["primary_intent"] in (
            "request", "question",
        ):
            response = (
                self.responder
                .generate_response(
                    subject=subject,
                    body=body,
                    sender=sender,
                    intent=intent[
                        "primary_intent"
                    ],
                )
            )

        # 7. Add to digest
        self.digest.add_email(
            email_id=email_id,
            sender=sender,
            subject=subject,
            priority=priority["priority"],
            has_action=actions["count"] > 0,
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "emails_processed"
        ] += 1

        return {
            "email_id": email_id,
            "category": classification[
                "category"
            ],
            "priority": priority[
                "priority"
            ],
            "actions_found": actions[
                "count"
            ],
            "response_generated": (
                response is not None
            ),
            "blocked": False,
            "pipeline_complete": True,
        }

    def inbox_zero_status(
        self,
    ) -> dict[str, Any]:
        """Inbox zero durumu döndürür.

        Returns:
            Durum bilgisi.
        """
        sorted_inbox = (
            self.inbox.sort_by_priority()
        )
        unread = sum(
            1 for e in sorted_inbox.get(
                "emails", [],
            )
            if not e.get("read", False)
        )

        return {
            "total_emails": sorted_inbox[
                "total"
            ],
            "unread": unread,
            "inbox_zero": unread == 0,
            "status": (
                "zero"
                if unread == 0
                else "manageable"
                if unread <= 10
                else "busy"
            ),
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "emails_processed": self._stats[
                "emails_processed"
            ],
            "classifications": (
                self.classifier
                .classification_count
            ),
            "spam_blocked": (
                self.spam.blocked_count
            ),
            "responses": (
                self.responder
                .response_count
            ),
            "actions_extracted": (
                self.actions.action_count
            ),
            "followups": (
                self.followups
                .followup_count
            ),
            "threads_analyzed": (
                self.threads.thread_count
            ),
            "digests": (
                self.digest.digest_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def processed_count(self) -> int:
        """İşlenen email sayısı."""
        return self._stats[
            "emails_processed"
        ]
