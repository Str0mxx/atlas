"""CommunicationAgent unit testleri.

Gmail API ve Anthropic API mock'lanarak communication agent davranislari test edilir.
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.communication_agent import (
    CommunicationAgent,
    _ANALYZE_RESPONSE_PROMPT,
    _COMPOSE_PROMPT,
    _FOLLOW_UP_PROMPT,
    _SYSTEM_PROMPT,
    _risk_order,
)
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.communication import (
    BulkSendResult,
    CommunicationAnalysisResult,
    CommunicationConfig,
    EmailLanguage,
    EmailMessage,
    EmailRecipient,
    EmailTaskType,
    EmailTemplate,
    EmailTone,
    FollowUpEntry,
    FollowUpStatus,
    InboxMessage,
    ResponseAnalysis,
    ResponseSentiment,
)


# === Fixtures ===


@pytest.fixture
def config():
    """Varsayilan test yapilandirmasi."""
    return CommunicationConfig(
        sender_name="Test Sender",
        sender_email="test@example.com",
        follow_up_days=3,
        max_follow_ups=2,
    )


@pytest.fixture
def agent(config):
    """Test agent'i."""
    return CommunicationAgent(config=config)


@pytest.fixture
def sample_template():
    """Ornek e-posta sablonu."""
    return EmailTemplate(
        name="supplier_inquiry",
        subject="Urun Sorgusu - {product_name}",
        body="<p>Sayin {contact_name},</p><p>{product_name} hakkinda bilgi istiyoruz.</p>",
        language=EmailLanguage.TURKISH,
        tone=EmailTone.FORMAL,
        variables=["contact_name", "product_name"],
        description="Tedarikci urun sorgu sablonu",
    )


@pytest.fixture
def sample_inbox_message():
    """Ornek gelen kutusu mesaji."""
    return InboxMessage(
        message_id="msg_123",
        thread_id="thread_456",
        from_email="supplier@example.com",
        from_name="Ali Bey",
        subject="Re: Urun Sorgusu",
        snippet="Tesekkurler, fiyat listesi ektedir...",
        body_text="Tesekkurler, fiyat listesi ektedir. Lutfen inceleyin.",
    )


def _make_llm_response(data: dict) -> MagicMock:
    """LLM yaniti olusturur."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(data))]
    return mock_response


def _make_gmail_send_response(
    msg_id: str = "sent_001",
    thread_id: str = "thread_001",
) -> dict:
    """Gmail send yaniti olusturur."""
    return {"id": msg_id, "threadId": thread_id}


# === Model Testleri ===


class TestModels:
    """Veri modeli testleri."""

    def test_communication_config_defaults(self):
        config = CommunicationConfig()
        assert config.default_language == EmailLanguage.TURKISH
        assert config.default_tone == EmailTone.FORMAL
        assert config.follow_up_days == 3
        assert config.max_follow_ups == 2
        assert config.max_bulk_batch_size == 50
        assert config.max_inbox_results == 20
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.max_tokens == 4096

    def test_email_message_defaults(self):
        msg = EmailMessage()
        assert msg.message_id == ""
        assert msg.to == ""
        assert msg.subject == ""
        assert msg.is_sent is False
        assert msg.sent_at is None
        assert msg.language == EmailLanguage.TURKISH
        assert msg.tone == EmailTone.FORMAL

    def test_email_template_creation(self, sample_template):
        assert sample_template.name == "supplier_inquiry"
        assert "{product_name}" in sample_template.subject
        assert "{contact_name}" in sample_template.body
        assert sample_template.variables == ["contact_name", "product_name"]

    def test_follow_up_entry_defaults(self):
        entry = FollowUpEntry()
        assert entry.status == FollowUpStatus.PENDING
        assert entry.follow_up_count == 0
        assert entry.last_follow_up_at is None
        assert entry.response_received_at is None
        assert isinstance(entry.sent_at, datetime)

    def test_bulk_send_result_defaults(self):
        result = BulkSendResult()
        assert result.total == 0
        assert result.sent == 0
        assert result.failed == 0
        assert result.failed_recipients == []

    def test_response_analysis_defaults(self):
        ra = ResponseAnalysis()
        assert ra.sentiment == ResponseSentiment.NEUTRAL
        assert ra.action_required is False
        assert ra.suggested_response == ""

    def test_communication_analysis_result_defaults(self):
        result = CommunicationAnalysisResult()
        assert result.task_type == EmailTaskType.COMPOSE
        assert result.composed_emails == []
        assert result.sent_emails == []
        assert result.inbox_messages == []
        assert result.response_analyses == []
        assert result.follow_ups == []
        assert result.bulk_result is None
        assert result.summary == ""

    def test_email_task_type_values(self):
        assert EmailTaskType.COMPOSE.value == "compose"
        assert EmailTaskType.SEND.value == "send"
        assert EmailTaskType.READ_INBOX.value == "read_inbox"
        assert EmailTaskType.BULK_SEND.value == "bulk_send"
        assert EmailTaskType.ANALYZE_RESPONSES.value == "analyze_responses"
        assert EmailTaskType.FOLLOW_UP_CHECK.value == "follow_up_check"

    def test_email_language_values(self):
        assert EmailLanguage.TURKISH.value == "turkish"
        assert EmailLanguage.ENGLISH.value == "english"
        assert EmailLanguage.ARABIC.value == "arabic"

    def test_email_tone_values(self):
        assert EmailTone.FORMAL.value == "formal"
        assert EmailTone.SEMI_FORMAL.value == "semi_formal"
        assert EmailTone.FRIENDLY.value == "friendly"
        assert EmailTone.URGENT.value == "urgent"

    def test_response_sentiment_values(self):
        assert ResponseSentiment.POSITIVE.value == "positive"
        assert ResponseSentiment.NEGATIVE.value == "negative"
        assert ResponseSentiment.NEUTRAL.value == "neutral"
        assert ResponseSentiment.NEEDS_ACTION.value == "needs_action"
        assert ResponseSentiment.OUT_OF_OFFICE.value == "out_of_office"

    def test_follow_up_status_values(self):
        assert FollowUpStatus.PENDING.value == "pending"
        assert FollowUpStatus.RESPONDED.value == "responded"
        assert FollowUpStatus.FOLLOW_UP_SENT.value == "follow_up_sent"
        assert FollowUpStatus.NO_RESPONSE.value == "no_response"
        assert FollowUpStatus.EXPIRED.value == "expired"

    def test_email_recipient(self):
        r = EmailRecipient(
            email="a@example.com",
            name="Ali",
            variables={"key": "val"},
        )
        assert r.email == "a@example.com"
        assert r.name == "Ali"
        assert r.variables == {"key": "val"}

    def test_email_recipient_defaults(self):
        r = EmailRecipient(email="a@example.com")
        assert r.name == ""
        assert r.variables == {}


# === Template Substitution Testleri ===


class TestTemplateSubstitution:
    """Sablon degisken degistirme testleri."""

    def test_simple_substitution(self, agent):
        result = agent._substitute_variables(
            "Merhaba {name}!",
            {"name": "Ali"},
        )
        assert result == "Merhaba Ali!"

    def test_multiple_variables(self, agent):
        result = agent._substitute_variables(
            "{greeting} {name}, {product} hakkinda",
            {"greeting": "Sayin", "name": "Veli Bey", "product": "Parfum"},
        )
        assert result == "Sayin Veli Bey, Parfum hakkinda"

    def test_missing_variable_left_as_is(self, agent):
        result = agent._substitute_variables(
            "Merhaba {name}, {missing}",
            {"name": "Ali"},
        )
        assert result == "Merhaba Ali, {missing}"

    def test_empty_variables(self, agent):
        result = agent._substitute_variables("Sabit metin", {})
        assert result == "Sabit metin"

    def test_compose_from_template(self, agent, sample_template):
        agent.templates["supplier_inquiry"] = sample_template
        email = agent._compose_from_template(
            "supplier_inquiry",
            "supplier@example.com",
            "Ali Bey",
            {"contact_name": "Ali Bey", "product_name": "Parfum"},
        )
        assert email.to == "supplier@example.com"
        assert email.to_name == "Ali Bey"
        assert email.subject == "Urun Sorgusu - Parfum"
        assert "Ali Bey" in email.body_html
        assert "Parfum" in email.body_html
        assert email.language == EmailLanguage.TURKISH
        assert email.tone == EmailTone.FORMAL


# === Parse LLM Response Testleri ===


class TestParseLlmResponse:
    """LLM yanit parse testleri."""

    def test_parse_json_block(self, agent):
        text = '```json\n{"subject": "Test", "body_html": "<p>Hi</p>"}\n```'
        result = agent._parse_llm_response(text)
        assert result["subject"] == "Test"
        assert result["body_html"] == "<p>Hi</p>"

    def test_parse_raw_json(self, agent):
        text = '{"sentiment": "positive", "summary": "Good"}'
        result = agent._parse_llm_response(text)
        assert result["sentiment"] == "positive"

    def test_parse_json_with_surrounding_text(self, agent):
        text = 'Here is the result:\n{"subject": "Hello"}\nDone.'
        result = agent._parse_llm_response(text)
        assert result["subject"] == "Hello"

    def test_parse_invalid_json_returns_raw(self, agent):
        text = "This is not JSON at all"
        result = agent._parse_llm_response(text)
        assert "raw_text" in result
        assert result["raw_text"] == text

    def test_parse_empty_code_block(self, agent):
        text = "```json\n{}\n```"
        result = agent._parse_llm_response(text)
        assert result == {}


# === Parse Gmail Message Testleri ===


class TestParseGmailMessage:
    """Gmail mesaj parse testleri."""

    def test_standard_message(self, agent):
        body_data = base64.urlsafe_b64encode(
            "Test body".encode("utf-8"),
        ).decode("utf-8")
        msg_data = {
            "id": "msg_001",
            "threadId": "thread_001",
            "snippet": "Test snippet",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Ali Bey <ali@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "body": {"data": body_data},
            },
        }
        inbox_msg = agent._parse_gmail_message(msg_data)
        assert inbox_msg.message_id == "msg_001"
        assert inbox_msg.thread_id == "thread_001"
        assert inbox_msg.from_email == "ali@example.com"
        assert inbox_msg.from_name == "Ali Bey"
        assert inbox_msg.subject == "Test Subject"
        assert inbox_msg.body_text == "Test body"
        assert inbox_msg.snippet == "Test snippet"
        assert "INBOX" in inbox_msg.labels

    def test_multipart_message(self, agent):
        text_data = base64.urlsafe_b64encode(
            "Plain text body".encode("utf-8"),
        ).decode("utf-8")
        msg_data = {
            "id": "msg_002",
            "threadId": "thread_002",
            "snippet": "Multi",
            "labelIds": [],
            "payload": {
                "headers": [
                    {"name": "From", "value": "veli@example.com"},
                    {"name": "Subject", "value": "Multipart"},
                ],
                "body": {},
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": text_data},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": "aHRtbA=="},
                    },
                ],
            },
        }
        inbox_msg = agent._parse_gmail_message(msg_data)
        assert inbox_msg.body_text == "Plain text body"
        assert inbox_msg.from_email == "veli@example.com"
        assert inbox_msg.from_name == ""

    def test_missing_fields(self, agent):
        msg_data = {
            "id": "msg_003",
            "payload": {"headers": []},
        }
        inbox_msg = agent._parse_gmail_message(msg_data)
        assert inbox_msg.message_id == "msg_003"
        assert inbox_msg.from_email == ""
        assert inbox_msg.subject == ""
        assert inbox_msg.body_text == ""

    def test_from_with_quotes(self, agent):
        msg_data = {
            "id": "msg_004",
            "threadId": "t_004",
            "payload": {
                "headers": [
                    {
                        "name": "From",
                        "value": '"Ali Yilmaz" <ali@example.com>',
                    },
                ],
                "body": {},
            },
        }
        inbox_msg = agent._parse_gmail_message(msg_data)
        assert inbox_msg.from_name == "Ali Yilmaz"
        assert inbox_msg.from_email == "ali@example.com"


# === Risk/Urgency Mapping Testleri ===


class TestRiskUrgencyMapping:
    """Risk/aciliyet eslestirme testleri."""

    def test_clean_result_low_low(self, agent):
        result = CommunicationAnalysisResult()
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_single_negative_response(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.NEGATIVE,
                    from_email="a@b.com",
                ),
            ],
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM

    def test_multiple_negative_responses(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.NEGATIVE,
                    from_email=f"user{i}@b.com",
                )
                for i in range(3)
            ],
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.HIGH

    def test_no_response_follow_up(self, agent):
        result = CommunicationAnalysisResult(
            follow_ups=[
                FollowUpEntry(
                    status=FollowUpStatus.NO_RESPONSE,
                    to_email="a@b.com",
                ),
            ],
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.MEDIUM

    def test_expired_follow_up_high_high(self, agent):
        result = CommunicationAnalysisResult(
            follow_ups=[
                FollowUpEntry(
                    status=FollowUpStatus.EXPIRED,
                    to_email="a@b.com",
                ),
            ],
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH

    def test_bulk_majority_failure(self, agent):
        result = CommunicationAnalysisResult(
            bulk_result=BulkSendResult(total=10, sent=3, failed=7),
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.HIGH

    def test_bulk_partial_failure(self, agent):
        result = CommunicationAnalysisResult(
            bulk_result=BulkSendResult(total=10, sent=8, failed=2),
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.MEDIUM

    def test_bulk_no_failure(self, agent):
        result = CommunicationAnalysisResult(
            bulk_result=BulkSendResult(total=10, sent=10, failed=0),
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_positive_response_low_low(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.POSITIVE,
                    from_email="a@b.com",
                ),
            ],
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_expired_overrides_negative(self, agent):
        """Expired follow-up HIGH/HIGH, olumsuz cevap MEDIUM/MEDIUM olsa bile."""
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.NEGATIVE,
                    from_email="a@b.com",
                ),
            ],
            follow_ups=[
                FollowUpEntry(
                    status=FollowUpStatus.EXPIRED,
                    to_email="c@d.com",
                ),
            ],
        )
        risk, urgency = agent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH


# === Action Determination Testleri ===


class TestActionDetermination:
    """Aksiyon belirleme testleri."""

    def test_low_low_logs(self, agent):
        action = agent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

    def test_medium_medium_notifies(self, agent):
        action = agent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM)
        assert action == ActionType.NOTIFY

    def test_high_high_immediate(self, agent):
        action = agent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert action == ActionType.IMMEDIATE

    def test_medium_high_auto_fix(self, agent):
        action = agent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.HIGH)
        assert action == ActionType.AUTO_FIX

    def test_high_medium_auto_fix(self, agent):
        action = agent._determine_action(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert action == ActionType.AUTO_FIX


# === Build Summary Testleri ===


class TestBuildSummary:
    """Ozet olusturma testleri."""

    def test_composed_emails_summary(self, agent):
        result = CommunicationAnalysisResult(
            composed_emails=[EmailMessage(subject="Test")],
        )
        summary = agent._build_summary(result)
        assert "1 e-posta olusturuldu" in summary

    def test_sent_emails_summary(self, agent):
        result = CommunicationAnalysisResult(
            sent_emails=[EmailMessage(is_sent=True)],
        )
        summary = agent._build_summary(result)
        assert "1 e-posta gonderildi" in summary

    def test_inbox_messages_summary(self, agent):
        result = CommunicationAnalysisResult(
            inbox_messages=[InboxMessage(message_id="m1")],
        )
        summary = agent._build_summary(result)
        assert "1 mesaj okundu" in summary

    def test_response_analyses_summary(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(sentiment=ResponseSentiment.NEGATIVE),
                ResponseAnalysis(sentiment=ResponseSentiment.POSITIVE),
            ],
        )
        summary = agent._build_summary(result)
        assert "2 cevap analiz edildi" in summary
        assert "1 olumsuz" in summary

    def test_follow_ups_summary(self, agent):
        result = CommunicationAnalysisResult(
            follow_ups=[
                FollowUpEntry(status=FollowUpStatus.NO_RESPONSE),
                FollowUpEntry(status=FollowUpStatus.RESPONDED),
            ],
        )
        summary = agent._build_summary(result)
        assert "2 takip" in summary
        assert "1 cevapsiz" in summary

    def test_bulk_result_summary(self, agent):
        result = CommunicationAnalysisResult(
            bulk_result=BulkSendResult(total=5, sent=4, failed=1),
        )
        summary = agent._build_summary(result)
        assert "toplu gonderim: 4/5 basarili" in summary

    def test_empty_result_default(self, agent):
        result = CommunicationAnalysisResult()
        summary = agent._build_summary(result)
        assert summary == "Iletisim gorevi tamamlandi."


# === Analyze Testleri ===


class TestAnalyze:
    """Analiz metodu testleri."""

    async def test_clean_analysis(self, agent):
        result = CommunicationAnalysisResult()
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["risk"] == "low"
        assert analysis["urgency"] == "low"
        assert analysis["action"] == "log"
        assert analysis["issues"] == []

    async def test_negative_response_analysis(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.NEGATIVE,
                    from_email="a@b.com",
                    summary="Olumsuz cevap geldi",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["risk"] == "medium"
        assert analysis["urgency"] == "medium"
        assert len(analysis["issues"]) == 1
        assert "Olumsuz cevap" in analysis["issues"][0]
        assert analysis["stats"]["negative_response_count"] == 1

    async def test_needs_action_analysis(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.NEEDS_ACTION,
                    from_email="x@y.com",
                    summary="Fiyat bilgisi istendi",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert len(analysis["issues"]) == 1
        assert "Aksiyon gerektiren" in analysis["issues"][0]

    async def test_follow_up_overdue_analysis(self, agent):
        result = CommunicationAnalysisResult(
            follow_ups=[
                FollowUpEntry(
                    status=FollowUpStatus.NO_RESPONSE,
                    to_email="a@b.com",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["stats"]["overdue_count"] == 1
        assert "cevapsiz" in analysis["issues"][0]

    async def test_follow_up_expired_analysis(self, agent):
        result = CommunicationAnalysisResult(
            follow_ups=[
                FollowUpEntry(
                    status=FollowUpStatus.EXPIRED,
                    to_email="a@b.com",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["risk"] == "high"
        assert analysis["urgency"] == "high"
        assert analysis["stats"]["expired_count"] == 1

    async def test_bulk_failure_analysis(self, agent):
        result = CommunicationAnalysisResult(
            bulk_result=BulkSendResult(
                total=10,
                sent=3,
                failed=7,
                failed_recipients=[
                    {"email": "a@b.com", "error": "timeout"},
                ],
            ),
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["stats"]["bulk_failed"] == 7
        assert "basarisiz" in analysis["issues"][0]

    async def test_analysis_stats_complete(self, agent):
        result = CommunicationAnalysisResult(
            composed_emails=[EmailMessage()],
            sent_emails=[EmailMessage(), EmailMessage()],
            inbox_messages=[InboxMessage()],
            response_analyses=[ResponseAnalysis()],
            follow_ups=[FollowUpEntry()],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        stats = analysis["stats"]
        assert stats["composed_count"] == 1
        assert stats["sent_count"] == 2
        assert stats["inbox_count"] == 1
        assert stats["analysis_count"] == 1
        assert stats["follow_up_count"] == 1


# === Report Testleri ===


class TestReport:
    """Rapor formatlama testleri."""

    async def test_report_contains_header(self, agent):
        result = CommunicationAnalysisResult(task_type=EmailTaskType.SEND)
        analysis = await agent.analyze({"result": result.model_dump()})
        task_result = TaskResult(
            success=True,
            data={"analysis": analysis},
        )
        report = await agent.report(task_result)
        assert "=== E-POSTA ILETISIM RAPORU ===" in report
        assert "SEND" in report

    async def test_report_contains_stats(self, agent):
        result = CommunicationAnalysisResult(
            sent_emails=[EmailMessage()],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        task_result = TaskResult(
            success=True,
            data={"analysis": analysis},
        )
        report = await agent.report(task_result)
        assert "Gonderilen: 1" in report

    async def test_report_contains_issues(self, agent):
        result = CommunicationAnalysisResult(
            response_analyses=[
                ResponseAnalysis(
                    sentiment=ResponseSentiment.NEGATIVE,
                    from_email="a@b.com",
                    summary="Kotu",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        task_result = TaskResult(
            success=True,
            data={"analysis": analysis},
        )
        report = await agent.report(task_result)
        assert "Bulgular" in report
        assert "Olumsuz cevap" in report

    async def test_report_contains_errors(self, agent):
        analysis = await agent.analyze(
            {"result": CommunicationAnalysisResult().model_dump()},
        )
        task_result = TaskResult(
            success=False,
            data={"analysis": analysis},
            errors=["Gmail API timeout"],
        )
        report = await agent.report(task_result)
        assert "HATALAR:" in report
        assert "Gmail API timeout" in report

    async def test_report_bulk_send_stats(self, agent):
        result = CommunicationAnalysisResult(
            bulk_result=BulkSendResult(total=10, sent=8, failed=2),
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        task_result = TaskResult(
            success=True,
            data={"analysis": analysis},
        )
        report = await agent.report(task_result)
        assert "8 basarili" in report
        assert "2 basarisiz" in report


# === Follow-Up Tracking Testleri ===


class TestFollowUpTracking:
    """Takip mekanizmasi testleri."""

    def test_update_follow_up_from_response(self, agent):
        entry = FollowUpEntry(
            thread_id="thread_100",
            to_email="a@b.com",
            status=FollowUpStatus.PENDING,
        )
        agent.follow_ups.append(entry)

        msg = InboxMessage(
            thread_id="thread_100",
            from_email="a@b.com",
        )
        agent._update_follow_up_from_response(msg)

        assert entry.status == FollowUpStatus.RESPONDED
        assert entry.response_received_at is not None

    def test_update_follow_up_no_match(self, agent):
        entry = FollowUpEntry(
            thread_id="thread_100",
            to_email="a@b.com",
            status=FollowUpStatus.PENDING,
        )
        agent.follow_ups.append(entry)

        msg = InboxMessage(
            thread_id="thread_999",
            from_email="x@y.com",
        )
        agent._update_follow_up_from_response(msg)

        assert entry.status == FollowUpStatus.PENDING

    def test_update_follow_up_already_responded(self, agent):
        entry = FollowUpEntry(
            thread_id="thread_100",
            to_email="a@b.com",
            status=FollowUpStatus.RESPONDED,
        )
        agent.follow_ups.append(entry)

        msg = InboxMessage(
            thread_id="thread_100",
            from_email="a@b.com",
        )
        agent._update_follow_up_from_response(msg)

        # Zaten responded, degismemeli
        assert entry.status == FollowUpStatus.RESPONDED

    def test_update_follow_up_from_no_response(self, agent):
        entry = FollowUpEntry(
            thread_id="thread_100",
            to_email="a@b.com",
            status=FollowUpStatus.NO_RESPONSE,
        )
        agent.follow_ups.append(entry)

        msg = InboxMessage(
            thread_id="thread_100",
            from_email="a@b.com",
        )
        agent._update_follow_up_from_response(msg)

        assert entry.status == FollowUpStatus.RESPONDED


# === Execute Testleri ===


class TestExecute:
    """Execute metodu testleri."""

    async def test_invalid_task_type(self, agent):
        result = await agent.execute({"task_type": "invalid_type"})
        assert result.success is False
        assert "Gecersiz gorev tipi" in result.message

    async def test_compose_with_mock_llm(self, agent):
        llm_data = {
            "subject": "Is Teklifi",
            "body_html": "<p>Sayin Alici</p>",
            "body_text": "Sayin Alici",
        }

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(llm_data),
        )
        agent._anthropic_client = mock_client

        result = await agent.execute({
            "task_type": "compose",
            "to": "alici@example.com",
            "to_name": "Ali Bey",
            "purpose": "Is teklifi gondermek",
            "context": "Medikal turizm",
            "language": "turkish",
            "tone": "formal",
        })

        assert result.success is True
        analysis_result = result.data["analysis_result"]
        assert len(analysis_result["composed_emails"]) == 1
        assert analysis_result["composed_emails"][0]["subject"] == "Is Teklifi"

    async def test_compose_with_template(self, agent):
        template = EmailTemplate(
            name="test_tmpl",
            subject="Merhaba {name}",
            body="<p>Sayin {name}, {topic} hakkinda.</p>",
        )

        result = await agent.execute({
            "task_type": "compose",
            "templates": [template.model_dump()],
            "template_name": "test_tmpl",
            "to": "x@y.com",
            "to_name": "Veli",
            "template_variables": {"name": "Veli Bey", "topic": "urunler"},
        })

        assert result.success is True
        composed = result.data["analysis_result"]["composed_emails"]
        assert len(composed) == 1
        assert composed[0]["subject"] == "Merhaba Veli Bey"
        assert "urunler" in composed[0]["body_html"]

    async def test_send_with_mock_gmail(self, agent):
        mock_service = MagicMock()
        mock_service.users().messages().send().execute.return_value = (
            _make_gmail_send_response()
        )
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "send",
            "to": "alici@example.com",
            "subject": "Test",
            "body_html": "<p>Hello</p>",
        })

        assert result.success is True
        assert len(result.data["analysis_result"]["sent_emails"]) == 1

    async def test_send_missing_to_fails(self, agent):
        result = await agent.execute({
            "task_type": "send",
            "subject": "Test",
            "body_html": "<p>Hello</p>",
        })

        assert result.success is False
        assert "Alici" in result.errors[0] or "to" in result.errors[0]

    async def test_send_with_compose(self, agent):
        """Send gorevi body yoksa ama purpose varsa LLM ile olusturur."""
        llm_data = {
            "subject": "Auto Subject",
            "body_html": "<p>Auto Body</p>",
            "body_text": "Auto Body",
        }

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(llm_data),
        )
        agent._anthropic_client = mock_client

        mock_service = MagicMock()
        mock_service.users().messages().send().execute.return_value = (
            _make_gmail_send_response()
        )
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "send",
            "to": "x@y.com",
            "purpose": "Teklif gondermek",
        })

        assert result.success is True
        sent = result.data["analysis_result"]["sent_emails"]
        assert len(sent) == 1

    async def test_send_with_follow_up_tracking(self, agent):
        mock_service = MagicMock()
        mock_service.users().messages().send().execute.return_value = (
            _make_gmail_send_response("msg_tracked", "thread_tracked")
        )
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "send",
            "to": "alici@example.com",
            "to_name": "Ali",
            "subject": "Test",
            "body_html": "<p>Hi</p>",
            "track_follow_up": True,
        })

        assert result.success is True
        assert len(agent.follow_ups) == 1
        assert agent.follow_ups[0].original_message_id == "msg_tracked"
        assert agent.follow_ups[0].thread_id == "thread_tracked"
        assert agent.follow_ups[0].to_email == "alici@example.com"

    async def test_read_inbox_with_mock_gmail(self, agent):
        body_data = base64.urlsafe_b64encode(b"Test body").decode("utf-8")
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_inbox_1"}],
        }
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_inbox_1",
            "threadId": "t_inbox_1",
            "snippet": "Snippet",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "ali@example.com"},
                    {"name": "Subject", "value": "Inbox Test"},
                ],
                "body": {"data": body_data},
            },
        }
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "read_inbox",
            "query": "is:unread",
            "max_results": 5,
        })

        assert result.success is True
        inbox = result.data["analysis_result"]["inbox_messages"]
        assert len(inbox) == 1
        assert inbox[0]["subject"] == "Inbox Test"

    async def test_bulk_send_with_template(self, agent):
        template = EmailTemplate(
            name="bulk_tmpl",
            subject="Merhaba {name}",
            body="<p>{name} icin mesaj</p>",
        )

        mock_service = MagicMock()
        call_count = 0

        def fake_send(**kwargs):
            nonlocal call_count
            call_count += 1
            mock_exec = MagicMock()
            mock_exec.execute.return_value = _make_gmail_send_response(
                f"msg_{call_count}",
                f"thread_{call_count}",
            )
            return mock_exec

        mock_service.users().messages().send = fake_send
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "bulk_send",
            "templates": [template.model_dump()],
            "template_name": "bulk_tmpl",
            "recipients": [
                {"email": "a@b.com", "name": "Ali", "variables": {"name": "Ali Bey"}},
                {"email": "c@d.com", "name": "Veli", "variables": {"name": "Veli Bey"}},
            ],
        })

        assert result.success is True
        bulk = result.data["analysis_result"]["bulk_result"]
        assert bulk["total"] == 2
        assert bulk["sent"] == 2
        assert bulk["failed"] == 0

    async def test_bulk_send_empty_recipients(self, agent):
        result = await agent.execute({
            "task_type": "bulk_send",
            "recipients": [],
        })
        assert result.success is False

    async def test_bulk_send_partial_failure(self, agent):
        call_count = 0

        def fake_send_exec():
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("SMTP error")
            return _make_gmail_send_response(f"msg_{call_count}")

        mock_service = MagicMock()
        mock_send = MagicMock()
        mock_send.execute = fake_send_exec
        mock_service.users().messages().send.return_value = mock_send
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "bulk_send",
            "subject": "Test",
            "body_html": "<p>Hi</p>",
            "recipients": [
                {"email": "a@b.com"},
                {"email": "fail@b.com"},
                {"email": "c@d.com"},
            ],
        })

        assert result.success is True
        bulk = result.data["analysis_result"]["bulk_result"]
        assert bulk["total"] == 3
        assert bulk["sent"] == 2
        assert bulk["failed"] == 1
        assert len(bulk["failed_recipients"]) == 1
        assert bulk["failed_recipients"][0]["email"] == "fail@b.com"

    async def test_analyze_responses_with_mock_llm(self, agent):
        llm_data = {
            "sentiment": "positive",
            "summary": "Olumlu cevap",
            "action_required": False,
            "suggested_response": "",
        }

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(llm_data),
        )
        agent._anthropic_client = mock_client

        result = await agent.execute({
            "task_type": "analyze_responses",
            "messages": [
                {
                    "message_id": "msg_r1",
                    "thread_id": "t_r1",
                    "from_email": "ali@example.com",
                    "subject": "Re: Teklif",
                    "body_text": "Tesekkurler, kabul ediyoruz.",
                },
            ],
        })

        assert result.success is True
        analyses = result.data["analysis_result"]["response_analyses"]
        assert len(analyses) == 1
        assert analyses[0]["sentiment"] == "positive"

    async def test_analyze_responses_negative(self, agent):
        llm_data = {
            "sentiment": "negative",
            "summary": "Teklif reddedildi",
            "action_required": True,
            "suggested_response": "Yeni fiyat onerebiliriz",
        }

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(llm_data),
        )
        agent._anthropic_client = mock_client

        result = await agent.execute({
            "task_type": "analyze_responses",
            "messages": [
                {
                    "message_id": "msg_neg",
                    "thread_id": "t_neg",
                    "from_email": "supplier@example.com",
                    "subject": "Re: Siparis",
                    "body_text": "Maalesef bu fiyatla calismamiz mumkun degil.",
                },
            ],
        })

        assert result.success is True
        analyses = result.data["analysis_result"]["response_analyses"]
        assert analyses[0]["sentiment"] == "negative"
        assert analyses[0]["action_required"] is True

    async def test_follow_up_check_no_overdue(self, agent):
        # Henuz suresi dolmamis entry
        entry = FollowUpEntry(
            to_email="a@b.com",
            subject="Test",
            sent_at=datetime.now(timezone.utc),
            status=FollowUpStatus.PENDING,
        )
        agent.follow_ups.append(entry)

        result = await agent.execute({"task_type": "follow_up_check"})

        assert result.success is True
        # Hicbir entry overdue degil
        assert len(result.data["analysis_result"]["follow_ups"]) == 0

    async def test_follow_up_check_overdue(self, agent):
        # 5 gun once gonderilmis, 3 gun limit -> overdue
        entry = FollowUpEntry(
            to_email="a@b.com",
            subject="Test",
            sent_at=datetime.now(timezone.utc) - timedelta(days=5),
            status=FollowUpStatus.PENDING,
        )
        agent.follow_ups.append(entry)

        result = await agent.execute({"task_type": "follow_up_check"})

        assert result.success is True
        follow_ups = result.data["analysis_result"]["follow_ups"]
        assert len(follow_ups) == 1
        assert follow_ups[0]["status"] == "no_response"

    async def test_follow_up_check_expired(self, agent):
        # Max follow-up (2) asilmis
        entry = FollowUpEntry(
            to_email="a@b.com",
            subject="Test",
            sent_at=datetime.now(timezone.utc) - timedelta(days=10),
            status=FollowUpStatus.PENDING,
            follow_up_count=2,
        )
        agent.follow_ups.append(entry)

        result = await agent.execute({"task_type": "follow_up_check"})

        assert result.success is True
        follow_ups = result.data["analysis_result"]["follow_ups"]
        assert len(follow_ups) == 1
        assert follow_ups[0]["status"] == "expired"

    async def test_follow_up_check_auto_send(self, agent):
        entry = FollowUpEntry(
            to_email="a@b.com",
            to_name="Ali",
            subject="Urun Teklifi",
            sent_at=datetime.now(timezone.utc) - timedelta(days=5),
            thread_id="thread_fu",
            status=FollowUpStatus.PENDING,
            follow_up_count=0,
        )
        agent.follow_ups.append(entry)

        llm_data = {
            "subject": "Re: Urun Teklifi - Hatirlatma",
            "body_html": "<p>Nazik hatirlatma</p>",
            "body_text": "Nazik hatirlatma",
        }
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_llm_response(llm_data),
        )
        agent._anthropic_client = mock_client

        mock_service = MagicMock()
        mock_service.users().messages().send().execute.return_value = (
            _make_gmail_send_response("msg_fu", "thread_fu")
        )
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "follow_up_check",
            "auto_send": True,
        })

        assert result.success is True
        # Hatirlatma gonderildi
        sent = result.data["analysis_result"]["sent_emails"]
        assert len(sent) == 1
        # Entry durumu guncellendi
        assert entry.status == FollowUpStatus.FOLLOW_UP_SENT
        assert entry.follow_up_count == 1

    async def test_config_override(self, agent):
        result = await agent.execute({
            "task_type": "compose",
            "config": {
                "default_language": "english",
                "default_tone": "friendly",
                "follow_up_days": 7,
            },
            "template_name": "nonexistent",
            "to": "x@y.com",
            "purpose": "Test",
        })

        # Config degisti, LLM cagrilacak ama mock yok -> hata
        assert result.success is False
        assert agent.config.default_language == EmailLanguage.ENGLISH
        assert agent.config.default_tone == EmailTone.FRIENDLY
        assert agent.config.follow_up_days == 7

    async def test_gmail_api_error_handled(self, agent):
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        error = HttpError(resp=mock_resp, content=b"Permission denied")

        mock_service = MagicMock()
        mock_service.users().messages().send().execute.side_effect = error
        agent._gmail_service = mock_service

        result = await agent.execute({
            "task_type": "send",
            "to": "x@y.com",
            "subject": "Test",
            "body_html": "<p>Hi</p>",
        })

        assert result.success is False
        assert any("Gmail API" in e for e in result.errors)


# === LLM Prompt Testleri ===


class TestPromptTemplates:
    """Prompt sablonu testleri."""

    def test_system_prompt_exists(self):
        assert "profesyonel" in _SYSTEM_PROMPT
        assert "JSON" in _SYSTEM_PROMPT

    def test_compose_prompt_has_placeholders(self):
        assert "{language}" in _COMPOSE_PROMPT
        assert "{tone}" in _COMPOSE_PROMPT
        assert "{recipient_name}" in _COMPOSE_PROMPT
        assert "{purpose}" in _COMPOSE_PROMPT

    def test_analyze_prompt_has_placeholders(self):
        assert "{original_subject}" in _ANALYZE_RESPONSE_PROMPT
        assert "{from_email}" in _ANALYZE_RESPONSE_PROMPT
        assert "{body}" in _ANALYZE_RESPONSE_PROMPT

    def test_follow_up_prompt_has_placeholders(self):
        assert "{language}" in _FOLLOW_UP_PROMPT
        assert "{original_subject}" in _FOLLOW_UP_PROMPT
        assert "{recipient_name}" in _FOLLOW_UP_PROMPT
        assert "{follow_up_number}" in _FOLLOW_UP_PROMPT


# === BaseAgent Integration Testleri ===


class TestBaseAgentIntegration:
    """BaseAgent entegrasyon testleri."""

    def test_agent_name(self, agent):
        assert agent.name == "communication"

    def test_agent_info(self, agent):
        info = agent.get_info()
        assert info["name"] == "communication"
        assert info["status"] == "idle"
        assert "created_at" in info

    async def test_run_wraps_execute(self, agent):
        """run() metodu execute()'u hata yakalamayla sarar."""
        # Gecersiz task_type ile cagir - run() hata firlatmamali
        result = await agent.run({"task_type": "invalid"})
        assert result.success is False

    async def test_run_with_exception(self, agent):
        """run() beklenmeyen hata ile cagrildiginda."""
        with patch.object(
            agent,
            "execute",
            side_effect=RuntimeError("Unexpected"),
        ):
            result = await agent.run({"task_type": "compose"})
            assert result.success is False
            assert any("Unexpected" in e for e in result.errors)


# === Risk Order Helper Testleri ===


class TestRiskOrder:
    """_risk_order yardimci fonksiyonu testleri."""

    def test_low_order(self):
        assert _risk_order(RiskLevel.LOW) == 0

    def test_medium_order(self):
        assert _risk_order(RiskLevel.MEDIUM) == 1

    def test_high_order(self):
        assert _risk_order(RiskLevel.HIGH) == 2

    def test_max_comparison(self):
        result = max(RiskLevel.LOW, RiskLevel.MEDIUM, key=_risk_order)
        assert result == RiskLevel.MEDIUM


# Gerekli importlar (test dosyasinda kullaniliyor)
from app.agents.base_agent import TaskResult
from googleapiclient.errors import HttpError
