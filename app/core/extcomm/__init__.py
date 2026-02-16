"""ATLAS External Communication Agent modülü.

Dış iletişim yönetimi: email, LinkedIn,
kampanya, takip, ton adaptasyonu.
"""

from app.core.extcomm.campaign_manager import (
    CampaignManager,
)
from app.core.extcomm.contact_database import (
    ContactDatabase,
)
from app.core.extcomm.email_composer import (
    EmailComposer,
)
from app.core.extcomm.email_sender import (
    EmailSender,
)
from app.core.extcomm.extcomm_orchestrator import (
    ExtCommOrchestrator,
)
from app.core.extcomm.followup_manager import (
    FollowUpManager,
)
from app.core.extcomm.linkedin_connector import (
    LinkedInConnector,
)
from app.core.extcomm.response_handler import (
    ResponseHandler,
)
from app.core.extcomm.tone_adapter import (
    ToneAdapter,
)

__all__ = [
    "CampaignManager",
    "ContactDatabase",
    "EmailComposer",
    "EmailSender",
    "ExtCommOrchestrator",
    "FollowUpManager",
    "LinkedInConnector",
    "ResponseHandler",
    "ToneAdapter",
]
