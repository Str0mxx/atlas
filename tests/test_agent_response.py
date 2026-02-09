"""AgentResponse model testleri."""

from datetime import datetime, timezone

from app.models.agent_response import (
    AgentAction,
    AgentResponse,
    ResponseStatus,
)


# === ResponseStatus Enum ===


class TestResponseStatus:
    """ResponseStatus enum testleri."""

    def test_values(self) -> None:
        """Tum durum degerlerini dogrular."""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.PARTIAL.value == "partial"
        assert ResponseStatus.FAILURE.value == "failure"
        assert ResponseStatus.TIMEOUT.value == "timeout"

    def test_count(self) -> None:
        """Enum uye sayisini dogrular."""
        assert len(ResponseStatus) == 4


# === AgentAction ===


class TestAgentAction:
    """AgentAction model testleri."""

    def test_required_fields(self) -> None:
        """Sadece action_type zorunlu."""
        action = AgentAction(action_type="email_sent")
        assert action.action_type == "email_sent"

    def test_defaults(self) -> None:
        """Varsayilan degerleri dogrular."""
        action = AgentAction(action_type="test")
        assert action.description == ""
        assert action.autonomous is False
        assert action.success is True

    def test_all_fields(self) -> None:
        """Tum alanlar dolu model."""
        action = AgentAction(
            action_type="ip_blocked",
            description="Basarisiz giris IP'si engellendi",
            autonomous=True,
            success=True,
        )
        assert action.action_type == "ip_blocked"
        assert action.description == "Basarisiz giris IP'si engellendi"
        assert action.autonomous is True
        assert action.success is True

    def test_failed_action(self) -> None:
        """Basarisiz aksiyon modeli."""
        action = AgentAction(
            action_type="ssl_renewal",
            success=False,
        )
        assert action.success is False


# === AgentResponse ===


class TestAgentResponse:
    """AgentResponse model testleri."""

    def test_required_fields(self) -> None:
        """Sadece agent_name zorunlu."""
        resp = AgentResponse(agent_name="security")
        assert resp.agent_name == "security"

    def test_defaults(self) -> None:
        """Varsayilan degerleri dogrular."""
        resp = AgentResponse(agent_name="test")
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.summary == ""
        assert resp.data == {}
        assert resp.actions_taken == []
        assert resp.recommendations == []
        assert resp.risk_level == "low"
        assert resp.confidence == 0.8
        assert resp.errors == []

    def test_timestamp_auto(self) -> None:
        """Zaman damgasi otomatik olusturulur."""
        resp = AgentResponse(agent_name="test")
        assert isinstance(resp.timestamp, datetime)
        assert resp.timestamp.tzinfo is not None

    def test_all_fields(self) -> None:
        """Tum alanlar dolu model."""
        now = datetime.now(timezone.utc)
        actions = [
            AgentAction(action_type="scan", autonomous=True),
            AgentAction(action_type="report"),
        ]
        resp = AgentResponse(
            agent_name="security",
            status=ResponseStatus.PARTIAL,
            summary="Tarama tamamlandi, 2 tehdit bulundu",
            data={"threats": 2, "scanned": 50},
            actions_taken=actions,
            recommendations=["Firewall guncelle"],
            risk_level="high",
            confidence=0.9,
            errors=["Port 8080 taranamiyor"],
            timestamp=now,
        )
        assert resp.agent_name == "security"
        assert resp.status == ResponseStatus.PARTIAL
        assert resp.summary == "Tarama tamamlandi, 2 tehdit bulundu"
        assert resp.data["threats"] == 2
        assert len(resp.actions_taken) == 2
        assert resp.recommendations == ["Firewall guncelle"]
        assert resp.risk_level == "high"
        assert resp.confidence == 0.9
        assert len(resp.errors) == 1
        assert resp.timestamp == now

    def test_is_success_true_for_success(self) -> None:
        """SUCCESS durumunda is_success True doner."""
        resp = AgentResponse(agent_name="test", status=ResponseStatus.SUCCESS)
        assert resp.is_success is True

    def test_is_success_true_for_partial(self) -> None:
        """PARTIAL durumunda is_success True doner."""
        resp = AgentResponse(agent_name="test", status=ResponseStatus.PARTIAL)
        assert resp.is_success is True

    def test_is_success_false_for_failure(self) -> None:
        """FAILURE durumunda is_success False doner."""
        resp = AgentResponse(agent_name="test", status=ResponseStatus.FAILURE)
        assert resp.is_success is False

    def test_is_success_false_for_timeout(self) -> None:
        """TIMEOUT durumunda is_success False doner."""
        resp = AgentResponse(agent_name="test", status=ResponseStatus.TIMEOUT)
        assert resp.is_success is False

    def test_autonomous_actions_filter(self) -> None:
        """Otonom aksiyonlari filtreler."""
        actions = [
            AgentAction(action_type="ip_block", autonomous=True),
            AgentAction(action_type="report", autonomous=False),
            AgentAction(action_type="ssl_renew", autonomous=True),
        ]
        resp = AgentResponse(agent_name="security", actions_taken=actions)
        auto = resp.autonomous_actions
        assert len(auto) == 2
        assert auto[0].action_type == "ip_block"
        assert auto[1].action_type == "ssl_renew"

    def test_autonomous_actions_empty(self) -> None:
        """Otonom aksiyon yoksa bos liste doner."""
        resp = AgentResponse(
            agent_name="test",
            actions_taken=[AgentAction(action_type="manual", autonomous=False)],
        )
        assert resp.autonomous_actions == []

    def test_confidence_bounds(self) -> None:
        """Guven skoru 0-1 arasinda olmali."""
        resp = AgentResponse(agent_name="test", confidence=0.0)
        assert resp.confidence == 0.0
        resp2 = AgentResponse(agent_name="test", confidence=1.0)
        assert resp2.confidence == 1.0

    def test_failure_with_errors(self) -> None:
        """Hatali yanit modeli."""
        resp = AgentResponse(
            agent_name="marketing",
            status=ResponseStatus.FAILURE,
            errors=["API key gecersiz", "Rate limit asildi"],
            confidence=0.0,
        )
        assert resp.is_success is False
        assert len(resp.errors) == 2
        assert resp.confidence == 0.0
