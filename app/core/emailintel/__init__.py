"""ATLAS Email Intelligence & Auto-Responder sistemi."""

from app.core.emailintel.action_extractor import (
    EmailActionExtractor,
)
from app.core.emailintel.email_classifier import (
    EmailClassifier,
)
from app.core.emailintel.email_digest import (
    EmailDigest,
)
from app.core.emailintel.emailintel_orchestrator import (
    EmailIntelOrchestrator,
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

__all__ = [
    "EmailActionExtractor",
    "EmailClassifier",
    "EmailDigest",
    "EmailFollowUpTracker",
    "EmailIntelOrchestrator",
    "EmailSmartResponder",
    "IntelligentSpamFilter",
    "PriorityInbox",
    "ThreadAnalyzer",
]
