"""BeliefBase sinifi unit testleri.

Belief guncelleme, revizyon, decay, monitor entegrasyonu,
sorgulama ve yonetim islemlerini test eder.
"""

from datetime import datetime, timedelta, timezone

from app.core.autonomy.beliefs import BeliefBase
from app.models.autonomy import (
    Belief,
    BeliefCategory,
    BeliefSource,
    BeliefUpdate,
)


# === Baslangic Testleri ===


class TestBeliefBaseInit:
    """BeliefBase baslangic durumu testleri."""

    def test_init_empty(self) -> None:
        """Bos belief base olusturmayi dogrular."""
        bb = BeliefBase()
        assert bb.beliefs == {}
        assert bb.revision_history == []

    def test_init_types(self) -> None:
        """Baslangic veri tiplerinin dogru oldugunu dogrular."""
        bb = BeliefBase()
        assert isinstance(bb.beliefs, dict)
        assert isinstance(bb.revision_history, list)

    def test_init_independent_instances(self) -> None:
        """Farkli instance'larin birbirini etkilemedigini dogrular."""
        bb1 = BeliefBase()
        bb2 = BeliefBase()
        assert bb1.beliefs is not bb2.beliefs
        assert bb1.revision_history is not bb2.revision_history


# === Update Testleri ===


class TestBeliefUpdate:
    """BeliefBase.update metodu testleri."""

    async def test_update_new_belief(self) -> None:
        """Yeni belief eklemeyi dogrular."""
        bb = BeliefBase()
        update = BeliefUpdate(key="test", value=42)
        result = await bb.update(update)
        assert result.key == "test"
        assert result.value == 42
        assert "test" in bb.beliefs

    async def test_update_existing_same_value(self) -> None:
        """Ayni deger farkli guvenle guncellemeyi dogrular."""
        bb = BeliefBase()
        await bb.update(BeliefUpdate(key="cpu", value=80, confidence=0.7))
        result = await bb.update(BeliefUpdate(key="cpu", value=80, confidence=0.9))
        assert result.value == 80
        assert result.confidence == 0.9

    async def test_update_existing_different_value_higher_conf(self) -> None:
        """Daha yuksek guvenle farkli deger guncellemesini dogrular."""
        bb = BeliefBase()
        await bb.update(BeliefUpdate(key="status", value="ok", confidence=0.5))
        result = await bb.update(BeliefUpdate(key="status", value="critical", confidence=0.9))
        assert result.value == "critical"
        assert result.confidence == 0.9

    async def test_update_existing_different_value_lower_conf(self) -> None:
        """Dusuk guvenli farkli degerin reddedildigini dogrular."""
        bb = BeliefBase()
        await bb.update(BeliefUpdate(key="status", value="ok", confidence=0.9))
        result = await bb.update(BeliefUpdate(key="status", value="bad", confidence=0.3))
        # Dusuk guvenli deger reddedilir, eski deger korunur
        assert result.value == "ok"
        assert result.confidence == 0.9


# === Revise Testleri ===


class TestBeliefRevise:
    """BeliefBase.revise metodu testleri."""

    async def test_revise_higher_confidence_wins(self) -> None:
        """Yuksek guvenli yeni degerin kabul edildigini dogrular."""
        bb = BeliefBase()
        bb.beliefs["temp"] = Belief(key="temp", value=20, confidence=0.5)
        result = await bb.revise("temp", 30, 0.9)
        assert result is not None
        assert result.value == 30
        assert result.confidence == 0.9

    async def test_revise_lower_confidence_rejected(self) -> None:
        """Dusuk guvenli yeni degerin reddedildigini dogrular."""
        bb = BeliefBase()
        bb.beliefs["temp"] = Belief(key="temp", value=20, confidence=0.9)
        result = await bb.revise("temp", 30, 0.3)
        assert result is None
        assert bb.beliefs["temp"].value == 20

    async def test_revise_same_value_no_change(self) -> None:
        """Ayni deger ve guvenle degisiklik olmamasi dogrulanir."""
        bb = BeliefBase()
        bb.beliefs["temp"] = Belief(key="temp", value=20, confidence=0.8)
        result = await bb.revise("temp", 20, 0.8)
        assert result is None

    async def test_revise_records_history(self) -> None:
        """Celiskili deger geldiginde revizyon gecmisine kayit edildigini dogrular."""
        bb = BeliefBase()
        bb.beliefs["temp"] = Belief(key="temp", value=20, confidence=0.5)
        await bb.revise("temp", 30, 0.9)
        assert len(bb.revision_history) == 1
        assert bb.revision_history[0]["key"] == "temp"
        assert bb.revision_history[0]["old_value"] == 20
        assert bb.revision_history[0]["new_value"] == 30


# === Decay Testleri ===


class TestBeliefDecay:
    """BeliefBase.decay metodu testleri."""

    async def test_decay_reduces_confidence(self) -> None:
        """Zaman gecince guven skorunun dusuruldugunu dogrular."""
        bb = BeliefBase()
        belief = Belief(key="test", value="v", confidence=1.0, decay_rate=0.1)
        # Timestamp'i 2 saat oncesine ayarla
        belief.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        bb.beliefs["test"] = belief

        removed = await bb.decay()
        assert "test" not in removed
        # 1.0 - (0.1 * 2) = 0.8 civari
        assert bb.beliefs["test"].confidence < 1.0
        assert abs(bb.beliefs["test"].confidence - 0.8) < 0.05

    async def test_decay_removes_below_threshold(self) -> None:
        """Esik altina dusen belief'in silindigini dogrular."""
        bb = BeliefBase()
        belief = Belief(key="old", value="stale", confidence=0.5, decay_rate=0.1)
        # Cok eski timestamp (10 saat once)
        belief.timestamp = datetime.now(timezone.utc) - timedelta(hours=10)
        bb.beliefs["old"] = belief

        removed = await bb.decay()
        assert "old" in removed
        assert "old" not in bb.beliefs

    async def test_decay_zero_rate_unchanged(self) -> None:
        """Sifir decay_rate ile guven skorunun degismedigini dogrular."""
        bb = BeliefBase()
        belief = Belief(key="stable", value="v", confidence=0.9, decay_rate=0.0)
        belief.timestamp = datetime.now(timezone.utc) - timedelta(hours=5)
        bb.beliefs["stable"] = belief

        removed = await bb.decay()
        assert removed == []
        assert bb.beliefs["stable"].confidence == 0.9


# === Monitor Testleri ===


class TestBeliefFromMonitor:
    """BeliefBase.update_from_monitor metodu testleri."""

    async def test_from_server_monitor(self) -> None:
        """Server monitor sonucundan belief olusturmayi dogrular."""
        bb = BeliefBase()
        beliefs = await bb.update_from_monitor(
            monitor_name="server",
            risk="high",
            urgency="high",
            details=[],
        )
        # Risk ve urgency olmak uzere 2 belief olusturulur
        assert len(beliefs) == 2
        risk_belief = bb.get("server:risk")
        assert risk_belief is not None
        # Anahtar "server:" ile baslar (kategori eslesmesinden)
        assert risk_belief.key.startswith("server:")
        assert risk_belief.confidence == 0.95

    async def test_from_security_monitor(self) -> None:
        """Security monitor sonucundan detay belief'leri olusturmayi dogrular."""
        bb = BeliefBase()
        beliefs = await bb.update_from_monitor(
            monitor_name="security",
            risk="medium",
            urgency="medium",
            details=[{"threat_type": "brute_force", "ip": "1.2.3.4"}],
        )
        # 2 (risk+urgency) + 2 (detail fields) = 4 belief
        assert len(beliefs) == 4
        threat_belief = bb.get("security:threat_type")
        assert threat_belief is not None
        assert threat_belief.value == "brute_force"
        ip_belief = bb.get("security:ip")
        assert ip_belief is not None
        assert ip_belief.value == "1.2.3.4"

    async def test_unknown_monitor_uses_system(self) -> None:
        """Bilinmeyen monitor adinin SYSTEM kategorisine eslendigini dogrular."""
        bb = BeliefBase()
        beliefs = await bb.update_from_monitor(
            monitor_name="unknown",
            risk="low",
            urgency="low",
            details=[],
        )
        assert len(beliefs) == 2
        risk_belief = bb.get("system:risk")
        assert risk_belief is not None
        assert risk_belief.category == BeliefCategory.SYSTEM


# === Sorgulama Testleri ===


class TestBeliefQuery:
    """BeliefBase sorgulama metotlari testleri."""

    def test_get_by_key(self) -> None:
        """Anahtara gore belief getirmeyi dogrular."""
        bb = BeliefBase()
        belief = Belief(key="server:cpu", value=75, category=BeliefCategory.SERVER)
        bb.beliefs["server:cpu"] = belief
        result = bb.get("server:cpu")
        assert result is not None
        assert result.value == 75
        assert bb.get("nonexistent") is None

    def test_get_by_category(self) -> None:
        """Kategoriye gore filtrelemeyi dogrular."""
        bb = BeliefBase()
        bb.beliefs["s1"] = Belief(key="s1", value="a", category=BeliefCategory.SERVER)
        bb.beliefs["s2"] = Belief(key="s2", value="b", category=BeliefCategory.SERVER)
        bb.beliefs["x1"] = Belief(key="x1", value="c", category=BeliefCategory.SECURITY)

        server_beliefs = bb.get_by_category(BeliefCategory.SERVER)
        assert len(server_beliefs) == 2
        security_beliefs = bb.get_by_category(BeliefCategory.SECURITY)
        assert len(security_beliefs) == 1
        marketing_beliefs = bb.get_by_category(BeliefCategory.MARKETING)
        assert len(marketing_beliefs) == 0

    def test_get_confident(self) -> None:
        """Minimum guven skoruyla filtrelemeyi dogrular."""
        bb = BeliefBase()
        bb.beliefs["high"] = Belief(key="high", value="a", confidence=0.9)
        bb.beliefs["mid"] = Belief(key="mid", value="b", confidence=0.5)
        bb.beliefs["low"] = Belief(key="low", value="c", confidence=0.2)

        confident = bb.get_confident(min_confidence=0.5)
        assert len(confident) == 2
        keys = {b.key for b in confident}
        assert "high" in keys
        assert "mid" in keys
        assert "low" not in keys


# === Yonetim Testleri ===


class TestBeliefManagement:
    """Belief silme ve temizleme testleri."""

    def test_remove_and_clear(self) -> None:
        """Belief silme ve tum belief'leri temizlemeyi dogrular."""
        bb = BeliefBase()
        bb.beliefs["a"] = Belief(key="a", value=1)
        bb.beliefs["b"] = Belief(key="b", value=2)

        # Var olan belief silinmeli
        assert bb.remove("a") is True
        assert "a" not in bb.beliefs
        # Olmayan belief silinememeli
        assert bb.remove("nonexistent") is False

        # Clear tum belief'leri temizlemeli
        bb.clear()
        assert len(bb.beliefs) == 0

    def test_snapshot(self) -> None:
        """Anlik goruntuyu (snapshot) dogrular."""
        bb = BeliefBase()
        bb.beliefs["k1"] = Belief(
            key="k1",
            value="v1",
            confidence=0.8,
            category=BeliefCategory.SERVER,
            source=BeliefSource.MONITOR,
        )
        bb.revision_history.append({"key": "k1", "old_value": "v0", "new_value": "v1"})

        snap = bb.snapshot()
        assert snap["count"] == 1
        assert "k1" in snap["beliefs"]
        assert snap["beliefs"]["k1"]["value"] == "v1"
        assert snap["beliefs"]["k1"]["confidence"] == 0.8
        assert snap["beliefs"]["k1"]["category"] == "server"
        assert snap["beliefs"]["k1"]["source"] == "monitor"
        assert snap["revision_count"] == 1
