"""ATLAS Email Intelligence & Auto-Responder testleri.

EmailClassifier, PriorityInbox,
EmailSmartResponder, EmailActionExtractor,
EmailFollowUpTracker, IntelligentSpamFilter,
EmailDigest, ThreadAnalyzer,
EmailIntelOrchestrator testleri.
"""

import pytest

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
from app.models.emailintel_models import (
    ActionRecord,
    ActionType,
    DigestRecord,
    EmailCategory,
    EmailPriority,
    EmailRecord,
    ResponseTone,
    SpamVerdict,
    ThreadRecord,
    ThreadStatus,
)


# ── EmailClassifier ───────────────────────


class TestDetectCategory:
    """detect_category testleri."""

    def test_business(self):
        c = EmailClassifier()
        r = c.detect_category(
            subject="Project Meeting",
            body="deadline for the report",
        )
        assert r["detected"] is True
        assert r["category"] == "business"

    def test_marketing(self):
        c = EmailClassifier()
        r = c.detect_category(
            subject="Special Offer",
            body="discount sale promo",
        )
        assert r["category"] == "marketing"

    def test_transactional(self):
        c = EmailClassifier()
        r = c.detect_category(
            subject="Order Confirmation",
            body="receipt payment shipping",
        )
        assert r["category"] == (
            "transactional"
        )

    def test_counter(self):
        c = EmailClassifier()
        c.detect_category(subject="A")
        c.detect_category(subject="B")
        assert c.classification_count == 2


class TestAssignPriority:
    """assign_priority testleri."""

    def test_critical(self):
        c = EmailClassifier()
        r = c.assign_priority(
            subject="URGENT ASAP",
            body="critical immediately",
        )
        assert r["priority"] == "critical"

    def test_high(self):
        c = EmailClassifier()
        r = c.assign_priority(
            subject="Important deadline",
        )
        assert r["priority"] == "high"

    def test_vip(self):
        c = EmailClassifier()
        r = c.assign_priority(
            subject="Hello",
            is_vip=True,
        )
        assert r["priority"] == "critical"

    def test_medium(self):
        c = EmailClassifier()
        r = c.assign_priority(
            subject="Regular update",
        )
        assert r["priority"] == "medium"


class TestFilterSpam:
    """filter_spam testleri."""

    def test_clean(self):
        c = EmailClassifier()
        r = c.filter_spam(
            subject="Meeting tomorrow",
        )
        assert r["verdict"] == "clean"

    def test_spam(self):
        c = EmailClassifier()
        r = c.filter_spam(
            subject="Winner lottery free",
            body="click here act now",
        )
        assert r["verdict"] == "spam"

    def test_suspicious(self):
        c = EmailClassifier()
        r = c.filter_spam(
            body="free offer",
        )
        assert r["verdict"] == "suspicious"


class TestDetectIntent:
    """detect_intent testleri."""

    def test_request(self):
        c = EmailClassifier()
        r = c.detect_intent(
            body="Could you please send it?",
        )
        assert r["detected"] is True
        assert r["primary_intent"] in (
            "request", "question",
        )

    def test_question(self):
        c = EmailClassifier()
        r = c.detect_intent(
            body="How do we proceed?",
        )
        assert r["primary_intent"] in (
            "question", "request",
        )

    def test_information(self):
        c = EmailClassifier()
        r = c.detect_intent(
            body="FYI sharing the report",
        )
        assert r["primary_intent"] == (
            "information"
        )


class TestProfileSender:
    """profile_sender testleri."""

    def test_basic(self):
        c = EmailClassifier()
        r = c.profile_sender(
            sender="fatih@test.com",
            history_count=15,
        )
        assert r["profiled"] is True
        assert r["reputation"] == "trusted"
        assert r["domain"] == "test.com"

    def test_new(self):
        c = EmailClassifier()
        r = c.profile_sender(
            sender="new@test.com",
            history_count=1,
        )
        assert r["reputation"] == "new"


# ── PriorityInbox ─────────────────────────


class TestAddEmail:
    """add_email testleri."""

    def test_basic(self):
        p = PriorityInbox()
        r = p.add_email(
            sender="a@test.com",
            subject="Hello",
        )
        assert r["added"] is True
        assert p.email_count == 1

    def test_vip_upgrade(self):
        p = PriorityInbox()
        p.add_vip("vip@test.com")
        r = p.add_email(
            sender="vip@test.com",
            priority="low",
        )
        assert r["priority"] == "critical"


class TestSortByPriority:
    """sort_by_priority testleri."""

    def test_basic(self):
        p = PriorityInbox()
        p.add_email(
            email_id="e1",
            priority="low",
        )
        p.add_email(
            email_id="e2",
            priority="critical",
        )
        r = p.sort_by_priority()
        assert r["sorted"] is True
        assert r["emails"][0][
            "priority"
        ] == "critical"


class TestGetImportantFirst:
    """get_important_first testleri."""

    def test_basic(self):
        p = PriorityInbox()
        p.add_email(
            email_id="e1",
            priority="low",
        )
        p.add_email(
            email_id="e2",
            priority="high",
        )
        p.add_email(
            email_id="e3",
            priority="critical",
        )
        r = p.get_important_first()
        assert r["retrieved"] is True
        assert r["count"] == 2


class TestAddVip:
    """add_vip testleri."""

    def test_basic(self):
        p = PriorityInbox()
        r = p.add_vip("boss@test.com")
        assert r["added"] is True
        assert p.vip_count == 1


class TestGetTimeSensitive:
    """get_time_sensitive testleri."""

    def test_basic(self):
        p = PriorityInbox()
        p.add_email(
            email_id="e1",
            subject="Recent",
        )
        r = p.get_time_sensitive(
            max_age_hours=24,
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1


class TestAddRule:
    """add_rule testleri."""

    def test_basic(self):
        p = PriorityInbox()
        r = p.add_rule(
            "boss_rule",
            condition_field="sender",
            condition_value="boss@co.com",
            set_priority="critical",
        )
        assert r["added"] is True
        assert r["total_rules"] == 1


# ── EmailSmartResponder ───────────────────


class TestGenerateResponse:
    """generate_response testleri."""

    def test_basic(self):
        r = EmailSmartResponder()
        res = r.generate_response(
            subject="Question",
            body="How do I proceed?",
            intent="question",
        )
        assert res["generated"] is True
        assert res["body"] != ""
        assert r.response_count == 1

    def test_request(self):
        r = EmailSmartResponder()
        res = r.generate_response(
            intent="request",
        )
        assert res["generated"] is True


class TestContextAwareResponse:
    """context_aware_response testleri."""

    def test_basic(self):
        r = EmailSmartResponder()
        res = r.context_aware_response(
            subject="Meeting",
            body="Can we schedule a meeting?",
            history=["prev1", "prev2"],
        )
        assert res["generated"] is True
        assert res["history_count"] == 2

    def test_no_history(self):
        r = EmailSmartResponder()
        res = r.context_aware_response(
            body="Question?",
        )
        assert res["generated"] is True


class TestMatchTone:
    """match_tone testleri."""

    def test_casual(self):
        r = EmailSmartResponder()
        res = r.match_tone(
            body="Hi there, cheers",
        )
        assert res["matched"] is True
        assert res["tone"] == "casual"

    def test_formal(self):
        r = EmailSmartResponder()
        res = r.match_tone(
            body="Dear Sir, regards",
        )
        assert res["tone"] == "formal"

    def test_override(self):
        r = EmailSmartResponder()
        res = r.match_tone(
            sender_tone="friendly",
        )
        assert res["tone"] == "friendly"


class TestSelectTemplate:
    """select_template testleri."""

    def test_basic(self):
        r = EmailSmartResponder()
        res = r.select_template(
            intent="request",
        )
        assert res["selected"] is True


class TestPersonalize:
    """personalize testleri."""

    def test_basic(self):
        r = EmailSmartResponder()
        res = r.personalize(
            body="Thank you.",
            recipient_name="Fatih",
            sender_name="ATLAS",
        )
        assert res["personalized"] is True
        assert "Fatih" in res["body"]
        assert "ATLAS" in res["body"]


# ── EmailActionExtractor ──────────────────


class TestExtractTasks:
    """extract_tasks testleri."""

    def test_basic(self):
        a = EmailActionExtractor()
        r = a.extract_tasks(
            "e1",
            body=(
                "Please review the doc. "
                "Could you send the report."
            ),
        )
        assert r["extracted"] is True
        assert r["count"] >= 2

    def test_no_tasks(self):
        a = EmailActionExtractor()
        r = a.extract_tasks(
            "e1", body="Hello there.",
        )
        assert r["count"] == 0


class TestDetectDeadlines:
    """detect_deadlines testleri."""

    def test_basic(self):
        a = EmailActionExtractor()
        r = a.detect_deadlines(
            "e1",
            body="Need this by tomorrow asap",
        )
        assert r["detected"] is True
        assert r["count"] >= 1

    def test_no_deadlines(self):
        a = EmailActionExtractor()
        r = a.detect_deadlines(
            "e1", body="General update.",
        )
        assert r["detected"] is False


class TestIdentifyRequests:
    """identify_requests testleri."""

    def test_basic(self):
        a = EmailActionExtractor()
        r = a.identify_requests(
            "e1",
            body=(
                "Could you please provide "
                "the data."
            ),
        )
        assert r["identified"] is True
        assert r["count"] >= 1


class TestTrackCommitments:
    """track_commitments testleri."""

    def test_basic(self):
        a = EmailActionExtractor()
        r = a.track_commitments(
            "e1",
            body="I will send it tomorrow.",
        )
        assert r["tracked"] is True
        assert r["count"] >= 1

    def test_no_commitments(self):
        a = EmailActionExtractor()
        r = a.track_commitments(
            "e1", body="Thanks.",
        )
        assert r["tracked"] is False


class TestCheckFollowupNeeds:
    """check_followup_needs testleri."""

    def test_needs(self):
        a = EmailActionExtractor()
        r = a.check_followup_needs(
            "e1",
            body="Let me know, waiting for reply",
        )
        assert r["needs_followup"] is True

    def test_no_needs(self):
        a = EmailActionExtractor()
        r = a.check_followup_needs(
            "e1", body="All done.",
        )
        assert r["needs_followup"] is False

    def test_urgent(self):
        a = EmailActionExtractor()
        r = a.check_followup_needs(
            "e1",
            body="Follow up urgent asap",
        )
        assert r["urgency"] == "high"


# ── EmailFollowUpTracker ──────────────────


class TestTrackPending:
    """track_pending testleri."""

    def test_new(self):
        f = EmailFollowUpTracker()
        r = f.track_pending(
            "e1",
            sender="a@test.com",
            days_waiting=0,
        )
        assert r["tracked"] is True
        assert r["status"] == "new"

    def test_overdue(self):
        f = EmailFollowUpTracker()
        r = f.track_pending(
            "e1", days_waiting=10,
        )
        assert r["status"] == "overdue"

    def test_counter(self):
        f = EmailFollowUpTracker()
        f.track_pending("e1")
        f.track_pending("e2")
        assert f.followup_count == 2


class TestScheduleReminder:
    """schedule_reminder testleri."""

    def test_basic(self):
        f = EmailFollowUpTracker()
        r = f.schedule_reminder(
            "e1", remind_in_days=3,
        )
        assert r["scheduled"] is True
        assert r["remind_in_days"] == 3


class TestEscalate:
    """escalate testleri."""

    def test_basic(self):
        f = EmailFollowUpTracker()
        f.track_pending("e1")
        r = f.escalate(
            "e1",
            reason="No response",
            escalate_to="manager",
        )
        assert r["escalated"] is True
        assert f.escalation_count == 1


class TestGetThreadStatus:
    """get_thread_status testleri."""

    def test_found(self):
        f = EmailFollowUpTracker()
        f.track_pending(
            "e1",
            sender="a@test.com",
            days_waiting=5,
        )
        r = f.get_thread_status("e1")
        assert r["found"] is True
        assert r["status"] == "pending"

    def test_not_found(self):
        f = EmailFollowUpTracker()
        r = f.get_thread_status("none")
        assert r["found"] is False


class TestResolve:
    """resolve testleri."""

    def test_basic(self):
        f = EmailFollowUpTracker()
        f.track_pending("e1")
        r = f.resolve(
            "e1",
            resolution="Replied",
        )
        assert r["resolved"] is True

    def test_not_found(self):
        f = EmailFollowUpTracker()
        r = f.resolve("none")
        assert r["resolved"] is False


# ── IntelligentSpamFilter ─────────────────


class TestMlFilter:
    """ml_filter testleri."""

    def test_clean(self):
        s = IntelligentSpamFilter()
        r = s.ml_filter(
            subject="Meeting update",
        )
        assert r["filtered"] is True
        assert r["verdict"] == "clean"

    def test_spam(self):
        s = IntelligentSpamFilter()
        r = s.ml_filter(
            subject="Winner lottery",
            body=(
                "free prize casino "
                "click here congratulations"
            ),
        )
        assert r["verdict"] == "spam"

    def test_blacklisted(self):
        s = IntelligentSpamFilter()
        s.add_to_blacklist("bad@spam.com")
        r = s.ml_filter(
            sender="bad@spam.com",
        )
        assert r["verdict"] == "spam"
        assert r["reason"] == "blacklisted"

    def test_whitelisted(self):
        s = IntelligentSpamFilter()
        s.add_to_whitelist("good@co.com")
        r = s.ml_filter(
            sender="good@co.com",
        )
        assert r["verdict"] == "clean"
        assert r["reason"] == "whitelisted"


class TestDetectPhishing:
    """detect_phishing testleri."""

    def test_phishing(self):
        s = IntelligentSpamFilter()
        r = s.detect_phishing(
            subject="Security Alert",
            body=(
                "verify your account "
                "unusual activity "
                "update your password"
            ),
        )
        assert r["detected"] is True
        assert r["is_phishing"] is True

    def test_clean(self):
        s = IntelligentSpamFilter()
        r = s.detect_phishing(
            body="Regular email.",
        )
        assert r["is_phishing"] is False


class TestCheckReputation:
    """check_reputation testleri."""

    def test_trusted(self):
        s = IntelligentSpamFilter()
        s.add_to_whitelist("good@co.com")
        r = s.check_reputation(
            "good@co.com",
        )
        assert r["status"] == "trusted"

    def test_blocked(self):
        s = IntelligentSpamFilter()
        s.add_to_blacklist("bad@co.com")
        r = s.check_reputation(
            "bad@co.com",
        )
        assert r["status"] == "blocked"

    def test_neutral(self):
        s = IntelligentSpamFilter()
        r = s.check_reputation(
            "unknown@co.com",
        )
        assert r["status"] == "neutral"


class TestAnalyzeContent:
    """analyze_content testleri."""

    def test_high_risk(self):
        s = IntelligentSpamFilter()
        r = s.analyze_content(
            body=(
                "winner lottery free "
                "click here casino"
            ),
        )
        assert r["analyzed"] is True
        assert r["risk_level"] == "high"

    def test_low_risk(self):
        s = IntelligentSpamFilter()
        r = s.analyze_content(
            body="Meeting tomorrow at 3pm.",
        )
        assert r["risk_level"] == "low"


class TestWhiteBlacklist:
    """whitelist/blacklist testleri."""

    def test_whitelist(self):
        s = IntelligentSpamFilter()
        r = s.add_to_whitelist("a@co.com")
        assert r["added"] is True
        assert r["list"] == "whitelist"

    def test_blacklist(self):
        s = IntelligentSpamFilter()
        r = s.add_to_blacklist("b@co.com")
        assert r["added"] is True
        assert r["list"] == "blacklist"

    def test_override(self):
        s = IntelligentSpamFilter()
        s.add_to_whitelist("x@co.com")
        s.add_to_blacklist("x@co.com")
        r = s.check_reputation("x@co.com")
        assert r["status"] == "blocked"


# ── EmailDigest ───────────────────────────


class TestDigestAddEmail:
    """add_email testleri."""

    def test_basic(self):
        d = EmailDigest()
        r = d.add_email(
            sender="a@test.com",
            subject="Hello",
        )
        assert r["added"] is True
        assert d.email_count == 1


class TestGenerateDailyDigest:
    """generate_daily_digest testleri."""

    def test_basic(self):
        d = EmailDigest()
        d.add_email(
            priority="high",
            has_action=True,
        )
        d.add_email(
            priority="low",
            read=True,
        )
        r = d.generate_daily_digest()
        assert r["generated"] is True
        assert r["total_emails"] == 2
        assert r["unread"] == 1
        assert r["high_priority"] == 1
        assert r["action_items"] == 1

    def test_counter(self):
        d = EmailDigest()
        d.generate_daily_digest()
        assert d.digest_count == 1


class TestGenerateDigestSummary:
    """generate_summary testleri."""

    def test_basic(self):
        d = EmailDigest()
        d.add_email(
            sender="a", subject="X",
            priority="critical",
        )
        d.add_email(
            sender="b", subject="Y",
            priority="low",
        )
        r = d.generate_summary()
        assert r["generated"] is True
        assert r["items"][0][
            "priority"
        ] == "critical"


class TestGetHighlights:
    """get_highlights testleri."""

    def test_basic(self):
        d = EmailDigest()
        d.add_email(
            priority="high",
        )
        d.add_email(
            priority="low",
            has_action=True,
        )
        d.add_email(
            priority="low",
        )
        r = d.get_highlights()
        assert r["retrieved"] is True
        assert r["count"] == 2


class TestGetActionItems:
    """get_action_items testleri."""

    def test_basic(self):
        d = EmailDigest()
        d.add_email(has_action=True)
        d.add_email(has_action=False)
        r = d.get_action_items()
        assert r["count"] == 1


class TestGetUnreadSummary:
    """get_unread_summary testleri."""

    def test_basic(self):
        d = EmailDigest()
        d.add_email(
            subject="A",
            priority="high",
        )
        d.add_email(
            subject="B",
            read=True,
        )
        r = d.get_unread_summary()
        assert r["summarized"] is True
        assert r["total_unread"] == 1

    def test_all_read(self):
        d = EmailDigest()
        d.add_email(read=True)
        r = d.get_unread_summary()
        assert r["total_unread"] == 0


# ── ThreadAnalyzer ────────────────────────


class TestReconstructThread:
    """reconstruct_thread testleri."""

    def test_basic(self):
        t = ThreadAnalyzer()
        msgs = [
            {
                "sender": "a@co.com",
                "body": "Hello",
                "timestamp": 1,
            },
            {
                "sender": "b@co.com",
                "body": "Hi",
                "timestamp": 2,
            },
        ]
        r = t.reconstruct_thread(
            "t1", messages=msgs,
        )
        assert r["reconstructed"] is True
        assert r["message_count"] == 2
        assert len(r["participants"]) == 2

    def test_counter(self):
        t = ThreadAnalyzer()
        t.reconstruct_thread("t1", [])
        assert t.thread_count == 1


class TestTrackParticipants:
    """track_participants testleri."""

    def test_basic(self):
        t = ThreadAnalyzer()
        t.reconstruct_thread(
            "t1",
            messages=[
                {"sender": "a", "timestamp": 1},
                {"sender": "a", "timestamp": 2},
                {"sender": "b", "timestamp": 3},
            ],
        )
        r = t.track_participants("t1")
        assert r["tracked"] is True
        assert r["most_active"] == "a"
        assert r["total_participants"] == 2

    def test_not_found(self):
        t = ThreadAnalyzer()
        r = t.track_participants("none")
        assert r["tracked"] is False


class TestAnalyzeTopicEvolution:
    """analyze_topic_evolution testleri."""

    def test_basic(self):
        t = ThreadAnalyzer()
        t.reconstruct_thread(
            "t1",
            messages=[
                {
                    "subject": "Budget",
                    "body": "Review the budget",
                    "sender": "a",
                    "timestamp": 1,
                },
            ],
        )
        r = t.analyze_topic_evolution("t1")
        assert r["analyzed"] is True

    def test_not_found(self):
        t = ThreadAnalyzer()
        r = t.analyze_topic_evolution("x")
        assert r["analyzed"] is False


class TestDetectResolution:
    """detect_resolution testleri."""

    def test_resolved(self):
        t = ThreadAnalyzer()
        t.reconstruct_thread(
            "t1",
            messages=[
                {
                    "body": "Need help",
                    "sender": "a",
                    "timestamp": 1,
                },
                {
                    "body": "Done, resolved",
                    "sender": "b",
                    "timestamp": 2,
                },
            ],
        )
        r = t.detect_resolution("t1")
        assert r["detected"] is True
        assert r["is_resolved"] is True

    def test_unresolved(self):
        t = ThreadAnalyzer()
        t.reconstruct_thread(
            "t1",
            messages=[
                {
                    "body": "Still working",
                    "sender": "a",
                    "timestamp": 1,
                },
            ],
        )
        r = t.detect_resolution("t1")
        assert r["is_resolved"] is False


class TestThreadExtractKeyPoints:
    """extract_key_points testleri."""

    def test_basic(self):
        t = ThreadAnalyzer()
        t.reconstruct_thread(
            "t1",
            messages=[
                {
                    "body": (
                        "We need to review "
                        "the budget for Q2."
                    ),
                    "sender": "a",
                    "timestamp": 1,
                },
            ],
        )
        r = t.extract_key_points("t1")
        assert r["extracted"] is True
        assert r["count"] >= 1

    def test_not_found(self):
        t = ThreadAnalyzer()
        r = t.extract_key_points("none")
        assert r["extracted"] is False


# ── EmailIntelOrchestrator ────────────────


class TestProcessEmail:
    """process_email testleri."""

    def test_normal(self):
        o = EmailIntelOrchestrator()
        r = o.process_email(
            email_id="e1",
            sender="a@co.com",
            subject="Project Report",
            body=(
                "Please review the report. "
                "Deadline is Friday."
            ),
        )
        assert r["pipeline_complete"] is True
        assert r["blocked"] is False
        assert r["category"] == "business"

    def test_spam_blocked(self):
        o = EmailIntelOrchestrator()
        o.spam.add_to_blacklist(
            "bad@spam.com",
        )
        r = o.process_email(
            email_id="e2",
            sender="bad@spam.com",
            subject="Free prize",
        )
        assert r["blocked"] is True
        assert r["verdict"] == "spam"

    def test_counter(self):
        o = EmailIntelOrchestrator()
        o.process_email(
            email_id="e1",
            sender="a@co.com",
        )
        o.process_email(
            email_id="e2",
            sender="b@co.com",
        )
        assert o.pipeline_count == 2
        assert o.processed_count == 2


class TestInboxZeroStatus:
    """inbox_zero_status testleri."""

    def test_zero(self):
        o = EmailIntelOrchestrator()
        r = o.inbox_zero_status()
        assert r["inbox_zero"] is True
        assert r["status"] == "zero"

    def test_busy(self):
        o = EmailIntelOrchestrator()
        for i in range(15):
            o.inbox.add_email(
                email_id=f"e{i}",
            )
        r = o.inbox_zero_status()
        assert r["inbox_zero"] is False
        assert r["status"] == "busy"


class TestOrchestratorAnalytics:
    """get_analytics testleri."""

    def test_basic(self):
        o = EmailIntelOrchestrator()
        o.process_email(
            email_id="e1",
            sender="a@co.com",
            subject="Hello",
            body="Please review.",
        )
        r = o.get_analytics()
        assert r["pipelines_run"] >= 1
        assert r["classifications"] >= 1


# ── Models ────────────────────────────────


class TestEmailintelModels:
    """Model testleri."""

    def test_email_category(self):
        assert (
            EmailCategory.BUSINESS
            == "business"
        )
        assert (
            EmailCategory.MARKETING
            == "marketing"
        )

    def test_email_priority(self):
        assert (
            EmailPriority.CRITICAL
            == "critical"
        )
        assert (
            EmailPriority.LOW == "low"
        )

    def test_spam_verdict(self):
        assert (
            SpamVerdict.CLEAN == "clean"
        )
        assert (
            SpamVerdict.PHISHING
            == "phishing"
        )

    def test_action_type(self):
        assert (
            ActionType.TASK == "task"
        )
        assert (
            ActionType.DEADLINE
            == "deadline"
        )

    def test_thread_status(self):
        assert (
            ThreadStatus.ACTIVE == "active"
        )
        assert (
            ThreadStatus.RESOLVED
            == "resolved"
        )

    def test_response_tone(self):
        assert (
            ResponseTone.FORMAL == "formal"
        )
        assert (
            ResponseTone.CASUAL == "casual"
        )

    def test_email_record(self):
        r = EmailRecord(
            sender="a@test.com",
        )
        assert r.sender == "a@test.com"
        assert r.email_id

    def test_action_record(self):
        r = ActionRecord(
            description="Review doc",
        )
        assert r.description == "Review doc"

    def test_thread_record(self):
        r = ThreadRecord(
            subject="Budget",
        )
        assert r.subject == "Budget"

    def test_digest_record(self):
        r = DigestRecord(
            email_count=10,
        )
        assert r.email_count == 10
