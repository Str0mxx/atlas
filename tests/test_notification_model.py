"""Bildirim modeli unit testleri."""

from datetime import datetime, timezone

from app.models.notification import (
    NotificationChannel,
    NotificationCreate,
    NotificationEventType,
    NotificationPriority,
    NotificationRecord,
    NotificationResponse,
    NotificationStatus,
)


class TestNotificationEnums:
    """Enum tanimlari testleri."""

    def test_event_types(self) -> None:
        """Tum NotificationEventType degerlerini dogrular."""
        assert NotificationEventType.SECURITY_ALERT == "security_alert"
        assert NotificationEventType.SERVER_ALERT == "server_alert"
        assert NotificationEventType.ADS_ALERT == "ads_alert"
        assert NotificationEventType.OPPORTUNITY_ALERT == "opportunity_alert"
        assert NotificationEventType.TASK_COMPLETED == "task_completed"
        assert NotificationEventType.TASK_FAILED == "task_failed"
        assert NotificationEventType.SYSTEM_ERROR == "system_error"
        assert NotificationEventType.SCHEDULED_REPORT == "scheduled_report"

    def test_event_type_count(self) -> None:
        """Olay tipi enum'unda 8 deger bulundugunu dogrular."""
        assert len(NotificationEventType) == 8

    def test_priority_values(self) -> None:
        """Tum NotificationPriority degerlerini dogrular."""
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.MEDIUM == "medium"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.CRITICAL == "critical"

    def test_status_values(self) -> None:
        """Tum NotificationStatus degerlerini dogrular."""
        assert NotificationStatus.PENDING == "pending"
        assert NotificationStatus.SENT == "sent"
        assert NotificationStatus.FAILED == "failed"
        assert NotificationStatus.ACKNOWLEDGED == "acknowledged"

    def test_channel_values(self) -> None:
        """Tum NotificationChannel degerlerini dogrular."""
        assert NotificationChannel.TELEGRAM == "telegram"
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.WEBHOOK == "webhook"
        assert NotificationChannel.LOG == "log"


class TestNotificationRecord:
    """NotificationRecord SQLAlchemy modeli testleri."""

    def test_basic_instantiation(self) -> None:
        """Temel alan degerleriyle kayit olusturmayi dogrular."""
        record = NotificationRecord(
            id="test-id",
            event_type="server_alert",
            message="Test message",
        )
        assert record.id == "test-id"
        assert record.event_type == "server_alert"
        assert record.message == "Test message"

    def test_default_values(self) -> None:
        """Varsayilan deger atamalarini dogrular."""
        record = NotificationRecord(
            id="test-id-2",
            event_type="system_error",
            message="Hata mesaji",
        )
        # Nullable alanlar varsayilan olarak None olmali
        assert record.task_id is None
        assert record.details is None
        assert record.recipient is None
        assert record.sent_at is None
        assert record.acknowledged_at is None

    def test_all_fields(self) -> None:
        """Tum alanlar verildigi durumu dogrular."""
        now = datetime.now(timezone.utc)
        record = NotificationRecord(
            id="full-record-id",
            task_id="task-123",
            event_type="security_alert",
            priority="high",
            status="sent",
            message="Guvenlik uyarisi",
            details="Detayli bilgi",
            recipient="fatih",
            channel="telegram",
            sent_at=now,
            acknowledged_at=now,
            created_at=now,
        )
        assert record.task_id == "task-123"
        assert record.priority == "high"
        assert record.status == "sent"
        assert record.details == "Detayli bilgi"
        assert record.recipient == "fatih"
        assert record.channel == "telegram"
        assert record.sent_at == now
        assert record.acknowledged_at == now
        assert record.created_at == now

    def test_tablename(self) -> None:
        """Tablo adinin dogru tanimlandigini dogrular."""
        assert NotificationRecord.__tablename__ == "notifications"

    def test_to_dict_basic(self) -> None:
        """to_dict metodunun temel donusumu dogrular."""
        record = NotificationRecord(
            id="dict-test-id",
            event_type="task_completed",
            priority="low",
            status="pending",
            message="Gorev tamamlandi",
            channel="email",
        )
        result = record.to_dict()
        assert isinstance(result, dict)
        assert result["id"] == "dict-test-id"
        assert result["event_type"] == "task_completed"
        assert result["priority"] == "low"
        assert result["status"] == "pending"
        assert result["message"] == "Gorev tamamlandi"
        assert result["channel"] == "email"

    def test_to_dict_nullable_fields(self) -> None:
        """to_dict ile nullable alanlarin None donmesini dogrular."""
        record = NotificationRecord(
            id="nullable-test",
            event_type="ads_alert",
            message="Reklam uyarisi",
        )
        result = record.to_dict()
        assert result["task_id"] is None
        assert result["details"] is None
        assert result["recipient"] is None
        assert result["sent_at"] is None
        assert result["acknowledged_at"] is None

    def test_to_dict_datetime_formatting(self) -> None:
        """to_dict'in datetime alanlarini isoformat'a cevirmesini dogrular."""
        now = datetime.now(timezone.utc)
        record = NotificationRecord(
            id="dt-test",
            event_type="server_alert",
            message="Test",
            sent_at=now,
            acknowledged_at=now,
            created_at=now,
        )
        result = record.to_dict()
        assert result["sent_at"] == now.isoformat()
        assert result["acknowledged_at"] == now.isoformat()
        assert result["created_at"] == now.isoformat()


class TestNotificationCreate:
    """NotificationCreate Pydantic schema testleri."""

    def test_required_fields(self) -> None:
        """Zorunlu alanlarin saglanmasini dogrular."""
        notification = NotificationCreate(
            event_type="server_alert",
            message="Sunucu alarmi",
        )
        assert notification.event_type == "server_alert"
        assert notification.message == "Sunucu alarmi"

    def test_default_values(self) -> None:
        """Varsayilan degerlerin atanmasini dogrular."""
        notification = NotificationCreate(
            event_type="task_completed",
            message="Gorev tamamlandi",
        )
        assert notification.priority == "medium"
        assert notification.channel == "telegram"
        assert notification.task_id is None
        assert notification.details is None
        assert notification.recipient is None

    def test_optional_fields(self) -> None:
        """Opsiyonel alanlarin duzgun atanmasini dogrular."""
        notification = NotificationCreate(
            task_id="task-456",
            event_type="security_alert",
            priority="critical",
            message="Guvenlik alarmi",
            details="Ek detaylar buraya",
            recipient="admin@example.com",
            channel="email",
        )
        assert notification.task_id == "task-456"
        assert notification.priority == "critical"
        assert notification.details == "Ek detaylar buraya"
        assert notification.recipient == "admin@example.com"
        assert notification.channel == "email"


class TestNotificationResponse:
    """NotificationResponse Pydantic schema testleri."""

    def test_from_attributes_config(self) -> None:
        """model_config'de from_attributes: True ayarini dogrular."""
        assert NotificationResponse.model_config.get("from_attributes") is True

    def test_all_fields(self) -> None:
        """Tum alanlarla yanit olusturmayi dogrular."""
        now = datetime.now(timezone.utc)
        response = NotificationResponse(
            id="resp-id",
            task_id="task-789",
            event_type="ads_alert",
            priority="high",
            status="acknowledged",
            message="Reklam reddedildi",
            details="Google policy violation",
            recipient="fatih",
            channel="telegram",
            sent_at=now,
            acknowledged_at=now,
            created_at=now,
        )
        assert response.id == "resp-id"
        assert response.task_id == "task-789"
        assert response.event_type == "ads_alert"
        assert response.priority == "high"
        assert response.status == "acknowledged"
        assert response.message == "Reklam reddedildi"
        assert response.details == "Google policy violation"
        assert response.recipient == "fatih"
        assert response.channel == "telegram"
        assert response.sent_at == now
        assert response.acknowledged_at == now
        assert response.created_at == now

    def test_optional_datetime_none(self) -> None:
        """Opsiyonel datetime alanlarin None olabilecegini dogrular."""
        now = datetime.now(timezone.utc)
        response = NotificationResponse(
            id="resp-none-dt",
            event_type="system_error",
            priority="medium",
            status="pending",
            message="Hata bildirim",
            channel="log",
            created_at=now,
        )
        assert response.sent_at is None
        assert response.acknowledged_at is None
        assert response.task_id is None
        assert response.details is None
        assert response.recipient is None
