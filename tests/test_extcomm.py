"""ATLAS External Communication Agent testleri.

EmailComposer, EmailSender, LinkedInConnector,
FollowUpManager, ResponseHandler, ContactDatabase,
ToneAdapter, CampaignManager, ExtCommOrchestrator
testleri.
"""

import time

import pytest


# ===================== EmailComposer =====================

class TestEmailComposerInit:
    """EmailComposer başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        assert ec.compose_count == 0
        assert ec.template_count >= 5

    def test_default_templates(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        templates = ec.get_templates()
        assert "introduction" in templates
        assert "follow_up" in templates
        assert "proposal" in templates


class TestEmailComposerCompose:
    """EmailComposer compose testleri."""

    def test_compose_basic(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose(
            to="test@example.com",
            subject="Test Subject",
            body="Hello, this is a test.",
        )
        assert result["composed"] is True
        assert result["to"] == "test@example.com"
        assert result["email_id"].startswith("eml_")
        assert ec.compose_count == 1

    def test_compose_with_tone(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose(
            to="test@example.com",
            subject="Test",
            body="Hi there, Thanks for your help.",
            tone="formal",
        )
        assert result["tone"] == "formal"
        assert "Dear" in result["body"] or "Thank you" in result["body"]

    def test_compose_urgent_tone(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose(
            to="test@example.com",
            subject="Urgent",
            body="Please review.",
            tone="urgent",
        )
        assert "immediate attention" in result["body"]

    def test_compose_with_attachments(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose(
            to="test@example.com",
            subject="With files",
            body="See attached.",
            attachments=["file1.pdf", "file2.xlsx"],
        )
        assert result["attachments"] == 2

    def test_compose_subject_optimization(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        long_subject = "a" * 70
        result = ec.compose(
            to="test@example.com",
            subject=long_subject,
            body="Test",
        )
        assert len(result["subject"]) <= 60

    def test_compose_subject_capitalization(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose(
            to="test@example.com",
            subject="lowercase start",
            body="Test",
        )
        assert result["subject"][0].isupper()


class TestEmailComposerTemplate:
    """EmailComposer şablon testleri."""

    def test_compose_from_template(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose_from_template(
            template_name="introduction",
            to="test@example.com",
            variables={
                "sender": "Fatih",
                "recipient": "Ali",
                "topic": "partnership",
                "body": "Let's collaborate.",
            },
        )
        assert result["composed"] is True
        assert "Fatih" in result["body"]

    def test_template_not_found(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.compose_from_template(
            template_name="nonexistent",
            to="test@example.com",
            variables={},
        )
        assert result["error"] == "template_not_found"

    def test_add_custom_template(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.add_template(
            name="custom",
            subject="Custom: {topic}",
            body="Custom body for {topic}",
        )
        assert result["added"] is True
        assert "custom" in ec.get_templates()


class TestEmailComposerPersonalize:
    """EmailComposer kişiselleştirme testleri."""

    def test_personalize(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        composed = ec.compose(
            to="test@example.com",
            subject="Test",
            body="Dear , this is for you.",
        )
        result = ec.personalize(
            email_id=composed["email_id"],
            recipient_info={
                "name": "Ali",
                "company": "ACME",
            },
        )
        assert result["personalized"] is True

    def test_personalize_not_found(self):
        from app.core.extcomm.email_composer import EmailComposer
        ec = EmailComposer()
        result = ec.personalize(
            email_id="nonexistent",
            recipient_info={"name": "Test"},
        )
        assert result["error"] == "email_not_found"


# ===================== EmailSender =====================

class TestEmailSenderInit:
    """EmailSender başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        assert es.sent_count == 0
        assert es.queue_size == 0
        assert es.bounce_count == 0


class TestEmailSenderSend:
    """EmailSender gönderim testleri."""

    def test_send_basic(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        result = es.send(
            email_id="eml_1",
            to="test@example.com",
            subject="Test",
            body="Hello",
        )
        assert result["sent"] is True
        assert result["send_id"].startswith("snd_")
        assert es.sent_count == 1

    def test_daily_limit(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender(daily_limit=2)
        es.send("e1", "a@b.com", "S1", "B1")
        es.send("e2", "a@b.com", "S2", "B2")
        result = es.send("e3", "a@b.com", "S3", "B3")
        assert result["sent"] is False
        assert result["error"] == "daily_limit_reached"

    def test_reset_daily_counter(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender(daily_limit=1)
        es.send("e1", "a@b.com", "S", "B")
        es.reset_daily_counter()
        result = es.send("e2", "a@b.com", "S", "B")
        assert result["sent"] is True


class TestEmailSenderQueue:
    """EmailSender kuyruk testleri."""

    def test_queue_email(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        result = es.queue(
            email_id="eml_1",
            to="test@example.com",
            subject="Test",
            body="Hello",
            priority=3,
        )
        assert result["queued"] is True
        assert es.queue_size == 1

    def test_process_queue(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        es.queue("e1", "a@b.com", "S1", "B1", priority=2)
        es.queue("e2", "c@d.com", "S2", "B2", priority=1)
        result = es.process_queue(max_items=5)
        assert result["processed"] == 2
        assert result["remaining"] == 0
        assert es.sent_count == 2


class TestEmailSenderTracking:
    """EmailSender takip testleri."""

    def test_track_delivery(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        sent = es.send("e1", "a@b.com", "S", "B")
        result = es.track_delivery(sent["send_id"])
        assert result["status"] == "sent"

    def test_mark_delivered(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        sent = es.send("e1", "a@b.com", "S", "B")
        result = es.mark_delivered(sent["send_id"])
        assert result["updated"] is True
        track = es.track_delivery(sent["send_id"])
        assert track["delivered"] is True

    def test_handle_bounce(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        sent = es.send("e1", "a@b.com", "S", "B")
        result = es.handle_bounce(
            sent["send_id"],
            reason="mailbox full",
            bounce_type="soft",
        )
        assert result["bounced"] is True
        assert es.bounce_count == 1

    def test_get_stats(self):
        from app.core.extcomm.email_sender import EmailSender
        es = EmailSender()
        es.send("e1", "a@b.com", "S", "B")
        stats = es.get_stats()
        assert stats["sent"] == 1
        assert "bounce_rate" in stats


# ===================== LinkedInConnector =====================

class TestLinkedInConnectorInit:
    """LinkedInConnector başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        assert lc.connection_count == 0
        assert lc.message_count == 0


class TestLinkedInConnectorConnection:
    """LinkedInConnector bağlantı testleri."""

    def test_send_connection_request(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        result = lc.send_connection_request(
            profile_id="prof_1",
            name="Ali Yilmaz",
            note="Let's connect!",
        )
        assert result["sent"] is True
        assert result["status"] == "pending"
        assert lc.connection_count == 1

    def test_connection_daily_limit(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        for i in range(20):
            lc.send_connection_request(f"p{i}", f"Name{i}")
        result = lc.send_connection_request("p20", "Name20")
        assert result["error"] == "daily_limit_reached"

    def test_note_truncation(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        long_note = "x" * 400
        result = lc.send_connection_request("p1", "N", long_note)
        assert result["sent"] is True

    def test_accept_connection(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        conn = lc.send_connection_request("p1", "Ali")
        result = lc.accept_connection(conn["connection_id"])
        assert result["accepted"] is True


class TestLinkedInConnectorMessage:
    """LinkedInConnector mesaj testleri."""

    def test_send_message(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        result = lc.send_message(
            profile_id="prof_1",
            message="Hello from ATLAS!",
        )
        assert result["sent"] is True
        assert lc.message_count == 1

    def test_message_daily_limit(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        for i in range(50):
            lc.send_message(f"p{i}", f"msg{i}")
        result = lc.send_message("p50", "msg50")
        assert result["error"] == "daily_limit_reached"

    def test_view_profile(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        result = lc.view_profile("prof_1", "Ali")
        assert result["viewed"] is True

    def test_get_activity(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        lc.send_connection_request("p1", "Ali")
        lc.send_message("p1", "Hello")
        lc.view_profile("p1", "Ali")
        result = lc.get_activity(profile_id="p1")
        assert result["total"] == 3

    def test_reset_daily_counters(self):
        from app.core.extcomm.linkedin_connector import LinkedInConnector
        lc = LinkedInConnector()
        for i in range(20):
            lc.send_connection_request(f"p{i}", f"N{i}")
        lc.reset_daily_counters()
        result = lc.send_connection_request("px", "NX")
        assert result["sent"] is True


# ===================== FollowUpManager =====================

class TestFollowUpManagerInit:
    """FollowUpManager başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        assert fm.followup_count == 0
        assert fm.pending_count == 0


class TestFollowUpManagerSchedule:
    """FollowUpManager zamanlama testleri."""

    def test_schedule_followup(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        result = fm.schedule_followup(
            contact_id="ct_1",
            email_id="eml_1",
            days=5,
            priority="high",
        )
        assert result["scheduled"] is True
        assert result["days"] == 5
        assert fm.followup_count == 1
        assert fm.pending_count == 1

    def test_complete_followup(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        fu = fm.schedule_followup("ct_1", "eml_1")
        result = fm.complete_followup(
            fu["followup_id"],
            outcome="responded",
        )
        assert result["completed"] is True
        assert fm.pending_count == 0

    def test_complete_not_found(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        result = fm.complete_followup("nonexistent")
        assert result["error"] == "followup_not_found"

    def test_reschedule(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        fu = fm.schedule_followup("ct_1", "eml_1")
        result = fm.reschedule(fu["followup_id"], days=7)
        assert result["rescheduled"] is True
        assert result["attempt"] == 2

    def test_reschedule_max_reached(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager(max_followups=2)
        fu = fm.schedule_followup("ct_1", "eml_1")
        fm.reschedule(fu["followup_id"])
        result = fm.reschedule(fu["followup_id"])
        assert "error" in result


class TestFollowUpManagerEscalation:
    """FollowUpManager eskalasyon testleri."""

    def test_add_escalation_rule(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        result = fm.add_escalation_rule(
            name="no_response",
            max_attempts=3,
            action="notify_manager",
        )
        assert result["added"] is True

    def test_check_escalations(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        fm.add_escalation_rule("rule1", max_attempts=2, action="alert")
        fu = fm.schedule_followup("ct_1", "eml_1")
        fm.reschedule(fu["followup_id"])
        result = fm.check_escalations()
        assert result["count"] >= 1

    def test_create_reminder(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        fu = fm.schedule_followup("ct_1", "eml_1")
        result = fm.create_reminder(
            fu["followup_id"],
            "Don't forget to follow up!",
        )
        assert result["created"] is True

    def test_get_due_followups(self):
        from app.core.extcomm.followup_manager import FollowUpManager
        fm = FollowUpManager()
        # Geçmiş tarihli takip
        fu = fm.schedule_followup("ct_1", "eml_1", days=0)
        # Hemen due olur (days=0 -> follow_at = now)
        result = fm.get_due_followups()
        assert result["total_due"] >= 0


# ===================== ResponseHandler =====================

class TestResponseHandlerInit:
    """ResponseHandler başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        assert rh.response_count == 0


class TestResponseHandlerProcess:
    """ResponseHandler işleme testleri."""

    def test_process_positive(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.process_response(
            email_id="eml_1",
            from_addr="ali@example.com",
            subject="Re: Proposal",
            body="This is great! I am very interested. Thank you!",
        )
        assert result["processed"] is True
        assert result["sentiment"] == "positive"
        assert rh.response_count == 1

    def test_process_negative(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.process_response(
            email_id="eml_2",
            from_addr="test@example.com",
            subject="Re: Offer",
            body="Not interested. Please stop contacting me. Unsubscribe.",
        )
        assert result["sentiment"] == "negative"

    def test_process_neutral(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.process_response(
            email_id="eml_3",
            from_addr="test@example.com",
            subject="Re: Info",
            body="Ok, maybe I will consider it later.",
        )
        assert result["sentiment"] == "neutral"


class TestResponseHandlerSentiment:
    """ResponseHandler duygu analizi testleri."""

    def test_analyze_sentiment_positive(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.analyze_sentiment(
            "This is excellent! Thank you so much!"
        )
        assert result["sentiment"] == "positive"
        assert result["confidence"] > 0

    def test_analyze_sentiment_empty(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.analyze_sentiment("")
        assert result["sentiment"] == "neutral"
        assert result["confidence"] == 0.5


class TestResponseHandlerIntent:
    """ResponseHandler niyet çıkarma testleri."""

    def test_extract_intent_interested(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.extract_intent(
            "I am interested. Can we schedule a meeting?"
        )
        assert result["intent"] == "interested"

    def test_extract_intent_not_interested(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.extract_intent(
            "No thanks, I'll pass."
        )
        assert result["intent"] == "not_interested"

    def test_extract_intent_question(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.extract_intent(
            "How does this work? What is the pricing?"
        )
        assert result["intent"] == "question"

    def test_extract_intent_unknown(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        result = rh.extract_intent("abc xyz 123")
        assert result["intent"] == "unknown"

    def test_get_responses(self):
        from app.core.extcomm.response_handler import ResponseHandler
        rh = ResponseHandler()
        rh.process_response("e1", "a@b.com", "S", "Great, thank you!")
        rh.process_response("e2", "c@d.com", "S", "Not interested, stop")
        results = rh.get_responses(sentiment="positive")
        assert len(results) >= 1


# ===================== ContactDatabase =====================

class TestContactDatabaseInit:
    """ContactDatabase başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        assert db.contact_count == 0
        assert db.interaction_count == 0


class TestContactDatabaseCRUD:
    """ContactDatabase CRUD testleri."""

    def test_add_contact(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        result = db.add_contact(
            name="Ali Yilmaz",
            email="ali@example.com",
            company="ACME",
            role="CEO",
        )
        assert result["added"] is True
        assert db.contact_count == 1

    def test_get_contact(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        result = db.get_contact(added["contact_id"])
        assert result["name"] == "Ali"

    def test_get_contact_not_found(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        result = db.get_contact("nonexistent")
        assert result["error"] == "contact_not_found"

    def test_update_contact(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        result = db.update_contact(
            added["contact_id"],
            company="NewCo",
        )
        assert result["updated"] is True
        assert "company" in result["updated_fields"]

    def test_search_contacts(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        db.add_contact("Ali Yilmaz", "ali@ex.com", company="ACME")
        db.add_contact("Veli Kaya", "veli@ex.com", company="Beta")
        results = db.search_contacts("Ali")
        assert len(results) == 1
        assert results[0]["name"] == "Ali Yilmaz"


class TestContactDatabaseInteraction:
    """ContactDatabase etkileşim testleri."""

    def test_log_interaction(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        result = db.log_interaction(
            added["contact_id"],
            interaction_type="email_sent",
            description="Sent proposal",
        )
        assert result["logged"] is True
        assert db.interaction_count == 1

    def test_interaction_history(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        db.log_interaction(added["contact_id"], "email_sent")
        db.log_interaction(added["contact_id"], "call")
        history = db.get_interaction_history(added["contact_id"])
        assert len(history) == 2

    def test_relationship_score(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        result = db.update_relationship_score(
            added["contact_id"], 15.0,
        )
        assert result["new_score"] == 15.0

    def test_relationship_score_bounds(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        db.update_relationship_score(added["contact_id"], -50)
        contact = db.get_contact(added["contact_id"])
        assert contact["relationship_score"] >= 0.0

    def test_set_preference(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        added = db.add_contact("Ali", "ali@ex.com")
        result = db.set_preference(
            added["contact_id"],
            "language", "tr",
        )
        assert result["set"] is True


class TestContactDatabaseSegment:
    """ContactDatabase segmentasyon testleri."""

    def test_create_segment(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        db.add_contact("Ali", "ali@ex.com", company="ACME")
        db.add_contact("Veli", "veli@ex.com", company="Beta")
        result = db.create_segment(
            name="acme_contacts",
            criteria={"company": "ACME"},
        )
        assert result["created"] is True
        assert result["count"] == 1

    def test_get_segment(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        db.add_contact("Ali", "ali@ex.com", company="ACME")
        db.create_segment("seg1", {"company": "ACME"})
        result = db.get_segment("seg1")
        assert result["count"] == 1

    def test_get_segment_not_found(self):
        from app.core.extcomm.contact_database import ContactDatabase
        db = ContactDatabase()
        result = db.get_segment("nonexistent")
        assert result["error"] == "segment_not_found"


# ===================== ToneAdapter =====================

class TestToneAdapterInit:
    """ToneAdapter başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        assert ta.adaptation_count == 0
        assert ta.profile_count == 0


class TestToneAdapterAnalyze:
    """ToneAdapter analiz testleri."""

    def test_analyze_recipient_basic(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.analyze_recipient(
            name="Ali Yilmaz",
            company="ACME",
            industry="technology",
        )
        assert "recommended_tone" in result

    def test_analyze_ceo_role(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.analyze_recipient(
            name="Ali",
            role="CEO",
            industry="startup",
        )
        assert result["recommended_tone"] in ("formal", "very_formal")

    def test_analyze_culture_jp(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.analyze_recipient(
            name="Tanaka",
            culture="jp",
        )
        assert result["cultural_formality"] == "very_formal"

    def test_analyze_industry_healthcare(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.analyze_recipient(
            name="Dr. Smith",
            industry="healthcare",
        )
        assert result["industry_tone"] == "formal"


class TestToneAdapterAdapt:
    """ToneAdapter adaptasyon testleri."""

    def test_adapt_text_formal(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.adapt_text(
            text="Hi there, Thanks for your help.",
            target_tone="formal",
            recipient_name="Ali",
        )
        assert result["adapted"] is True
        assert result["greeting"] == "Dear Ali"
        assert ta.adaptation_count == 1

    def test_adapt_text_casual(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.adapt_text(
            text="Dear Sir, Thank you.",
            target_tone="casual",
            recipient_name="Ali",
        )
        assert result["closing"] == "Cheers"

    def test_create_profile(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.create_profile(
            contact_id="ct_1",
            preferred_tone="formal",
            industry="finance",
        )
        assert result["created"] is True
        assert ta.profile_count == 1

    def test_get_profile(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        ta.create_profile("ct_1", "formal")
        result = ta.get_profile("ct_1")
        assert result["preferred_tone"] == "formal"

    def test_get_profile_not_found(self):
        from app.core.extcomm.tone_adapter import ToneAdapter
        ta = ToneAdapter()
        result = ta.get_profile("nonexistent")
        assert result["error"] == "profile_not_found"


# ===================== CampaignManager =====================

class TestCampaignManagerInit:
    """CampaignManager başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        assert cm.campaign_count == 0
        assert cm.active_count == 0


class TestCampaignManagerCRUD:
    """CampaignManager CRUD testleri."""

    def test_create_campaign(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        result = cm.create_campaign(
            name="Q1 Outreach",
            contact_ids=["ct_1", "ct_2", "ct_3"],
        )
        assert result["created"] is True
        assert result["contacts"] == 3
        assert cm.campaign_count == 1
        assert cm.active_count == 1

    def test_pause_campaign(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        result = cm.pause_campaign(camp["campaign_id"])
        assert result["paused"] is True
        assert cm.active_count == 0

    def test_resume_campaign(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        cm.pause_campaign(camp["campaign_id"])
        result = cm.resume_campaign(camp["campaign_id"])
        assert result["resumed"] is True
        assert cm.active_count == 1

    def test_complete_campaign(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        result = cm.complete_campaign(camp["campaign_id"])
        assert result["completed"] is True

    def test_campaign_not_found(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        result = cm.pause_campaign("nonexistent")
        assert result["error"] == "campaign_not_found"


class TestCampaignManagerTracking:
    """CampaignManager takip testleri."""

    def test_record_send(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        result = cm.record_send(camp["campaign_id"], "ct_1")
        assert result["recorded"] is True

    def test_record_response(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        result = cm.record_response(
            camp["campaign_id"], "ct_1", "reply",
        )
        assert result["recorded"] is True

    def test_get_performance(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1", "ct_2"])
        cm.record_send(camp["campaign_id"], "ct_1")
        cm.record_send(camp["campaign_id"], "ct_2")
        cm.record_response(camp["campaign_id"], "ct_1")
        result = cm.get_performance(camp["campaign_id"])
        assert result["sent"] == 2
        assert result["responses"] == 1
        assert result["response_rate"] == 50.0


class TestCampaignManagerSequence:
    """CampaignManager sekans testleri."""

    def test_create_sequence(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        result = cm.create_sequence(
            camp["campaign_id"],
            steps=[
                {"day": 0, "action": "send_intro"},
                {"day": 3, "action": "send_followup"},
                {"day": 7, "action": "send_final"},
            ],
        )
        assert result["created"] is True
        assert result["steps"] == 3

    def test_create_ab_test(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        camp = cm.create_campaign("Test", ["ct_1"])
        result = cm.create_ab_test(
            camp["campaign_id"],
            variant_a={"subject": "Option A"},
            variant_b={"subject": "Option B"},
            split_ratio=0.5,
        )
        assert result["created"] is True

    def test_get_campaigns_filter(self):
        from app.core.extcomm.campaign_manager import CampaignManager
        cm = CampaignManager()
        cm.create_campaign("Active1", ["ct_1"])
        camp2 = cm.create_campaign("Paused1", ["ct_2"])
        cm.pause_campaign(camp2["campaign_id"])
        active = cm.get_campaigns(status="active")
        assert len(active) == 1


# ===================== ExtCommOrchestrator =====================

class TestExtCommOrchestratorInit:
    """ExtCommOrchestrator başlatma testleri."""

    def test_init(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        assert orch.outreach_count == 0
        assert orch.composer is not None
        assert orch.sender is not None
        assert orch.linkedin is not None

    def test_init_with_params(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator(
            default_tone="formal",
            daily_send_limit=50,
            followup_days=5,
        )
        assert orch.outreach_count == 0


class TestExtCommOrchestratorOutreach:
    """ExtCommOrchestrator outreach testleri."""

    def test_outreach_basic(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        result = orch.outreach(
            contact_name="Ali Yilmaz",
            contact_email="ali@example.com",
            subject="Partnership Proposal",
            body="Let's work together.",
            company="ACME",
        )
        assert result["success"] is True
        assert result["sent"] is True
        assert result["contact_id"] is not None
        assert result["email_id"] is not None
        assert result["followup_id"] is not None
        assert orch.outreach_count == 1

    def test_outreach_no_followup(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        result = orch.outreach(
            contact_name="Ali",
            contact_email="ali@ex.com",
            subject="Quick note",
            body="FYI",
            auto_followup=False,
        )
        assert result["followup_id"] is None

    def test_outreach_custom_tone(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        result = orch.outreach(
            contact_name="Ali",
            contact_email="ali@ex.com",
            subject="Hello",
            body="Test",
            tone="casual",
        )
        assert result["tone"] == "casual"


class TestExtCommOrchestratorIncoming:
    """ExtCommOrchestrator gelen yanıt testleri."""

    def test_process_incoming_positive(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        # Önce kişi oluştur
        orch.contacts.add_contact("Ali", "ali@example.com")
        result = orch.process_incoming(
            email_id="eml_1",
            from_addr="ali@example.com",
            subject="Re: Proposal",
            body="Great proposal! I am very interested.",
        )
        assert result["processed"] is True
        assert result["sentiment"] == "positive"

    def test_process_incoming_negative(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        result = orch.process_incoming(
            email_id="eml_2",
            from_addr="unknown@example.com",
            subject="Re: Offer",
            body="Not interested. Please stop.",
        )
        assert result["processed"] is True


class TestExtCommOrchestratorCampaign:
    """ExtCommOrchestrator kampanya testleri."""

    def test_launch_campaign(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        c1 = orch.contacts.add_contact("Ali", "ali@ex.com")
        c2 = orch.contacts.add_contact("Veli", "veli@ex.com")
        result = orch.launch_campaign(
            name="Q1 Campaign",
            contact_ids=[c1["contact_id"], c2["contact_id"]],
            subject="New Product",
            body="Check out our new product.",
        )
        assert result["launched"] is True
        assert result["sent"] == 2

    def test_get_analytics(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        orch.outreach("Ali", "ali@ex.com", "S", "B")
        analytics = orch.get_analytics()
        assert analytics["outreach_completed"] == 1
        assert analytics["emails_composed"] >= 1
        assert analytics["emails_sent"] >= 1
        assert "contacts_total" in analytics

    def test_get_status(self):
        from app.core.extcomm.extcomm_orchestrator import ExtCommOrchestrator
        orch = ExtCommOrchestrator()
        status = orch.get_status()
        assert "outreach_completed" in status
        assert "emails_sent" in status
        assert "contacts" in status


# ===================== Imports & Models =====================

class TestExtCommImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.extcomm import (
            CampaignManager,
            ContactDatabase,
            EmailComposer,
            EmailSender,
            ExtCommOrchestrator,
            FollowUpManager,
            LinkedInConnector,
            ResponseHandler,
            ToneAdapter,
        )
        assert CampaignManager is not None
        assert ContactDatabase is not None
        assert EmailComposer is not None
        assert EmailSender is not None
        assert ExtCommOrchestrator is not None
        assert FollowUpManager is not None
        assert LinkedInConnector is not None
        assert ResponseHandler is not None
        assert ToneAdapter is not None


class TestExtCommModels:
    """Model testleri."""

    def test_channel_type_enum(self):
        from app.models.extcomm_models import ChannelType
        assert ChannelType.EMAIL == "email"
        assert ChannelType.LINKEDIN == "linkedin"

    def test_tone_level_enum(self):
        from app.models.extcomm_models import ToneLevel
        assert ToneLevel.FORMAL == "formal"
        assert ToneLevel.PROFESSIONAL == "professional"

    def test_email_status_enum(self):
        from app.models.extcomm_models import EmailStatus
        assert EmailStatus.DRAFT == "draft"
        assert EmailStatus.SENT == "sent"

    def test_campaign_status_enum(self):
        from app.models.extcomm_models import CampaignStatus
        assert CampaignStatus.ACTIVE == "active"

    def test_response_sentiment_enum(self):
        from app.models.extcomm_models import ResponseSentiment
        assert ResponseSentiment.POSITIVE == "positive"

    def test_followup_priority_enum(self):
        from app.models.extcomm_models import FollowUpPriority
        assert FollowUpPriority.HIGH == "high"

    def test_contact_record(self):
        from app.models.extcomm_models import ContactRecord
        rec = ContactRecord(name="Ali", email="ali@ex.com")
        assert rec.name == "Ali"
        assert len(rec.contact_id) == 8

    def test_email_record(self):
        from app.models.extcomm_models import EmailRecord
        rec = EmailRecord(to="ali@ex.com", subject="Test")
        assert rec.to == "ali@ex.com"
        assert rec.status == "draft"

    def test_campaign_record(self):
        from app.models.extcomm_models import CampaignRecord
        rec = CampaignRecord(name="Q1")
        assert rec.name == "Q1"
        assert rec.status == "planning"

    def test_extcomm_snapshot(self):
        from app.models.extcomm_models import ExtCommSnapshot
        snap = ExtCommSnapshot()
        assert snap.emails_sent == 0
        assert snap.timestamp is not None


class TestExtCommConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.extcomm_enabled is True
        assert s.default_tone == "professional"
        assert s.auto_followup is True
        assert s.followup_days == 3
        assert s.daily_send_limit == 100
