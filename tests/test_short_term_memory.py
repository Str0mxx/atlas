"""ShortTermMemory (Redis) unit testleri.

Redis mock'lanarak kisa sureli hafiza islemleri test edilir.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.memory.short_term import ShortTermMemory


# === Fixtures ===


@pytest.fixture
def memory() -> ShortTermMemory:
    """Yapilandirilmis ShortTermMemory (baglanti kurulmamis)."""
    return ShortTermMemory(prefix="test")


@pytest.fixture
def connected_memory() -> ShortTermMemory:
    """Redis mock ile bagli ShortTermMemory."""
    mem = ShortTermMemory(prefix="test")
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.close = AsyncMock()
    mem.redis = mock_redis
    return mem


# === Baglanti testleri ===


class TestConnection:
    """Redis baglanti yonetimi testleri."""

    @pytest.mark.asyncio
    async def test_connect_calls_redis(self, memory: ShortTermMemory) -> None:
        """connect() Redis.from_url cagirmali ve ping atmali."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        with patch(
            "app.core.memory.short_term.Redis.from_url",
            return_value=mock_redis,
        ):
            await memory.connect()

        assert memory.redis is not None
        mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close(self, connected_memory: ShortTermMemory) -> None:
        """close() Redis baglantisini kapatmali."""
        mock_redis = connected_memory.redis
        await connected_memory.close()

        mock_redis.close.assert_awaited_once()
        assert connected_memory.redis is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, memory: ShortTermMemory) -> None:
        """Baglanti yokken close() hata vermemeli."""
        await memory.close()
        assert memory.redis is None

    def test_ensure_connected_raises_when_not_connected(
        self, memory: ShortTermMemory,
    ) -> None:
        """Baglanti yokken _ensure_connected RuntimeError firlatmali."""
        with pytest.raises(RuntimeError, match="Redis baglantisi kurulmamis"):
            memory._ensure_connected()

    def test_ensure_connected_returns_redis(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Baglanti varken _ensure_connected Redis dondurur."""
        result = connected_memory._ensure_connected()
        assert result is connected_memory.redis


# === Key olusturma testleri ===


class TestKeyGeneration:
    """Redis anahtar olusturma testleri."""

    def test_key_single_part(self, memory: ShortTermMemory) -> None:
        assert memory._key("task") == "test:task"

    def test_key_multiple_parts(self, memory: ShortTermMemory) -> None:
        assert memory._key("task", "abc123") == "test:task:abc123"

    def test_key_with_default_prefix(self) -> None:
        mem = ShortTermMemory()
        assert mem._key("session", "xyz") == "atlas:session:xyz"


# === Gorev durum testleri ===


class TestTaskStatus:
    """Aktif gorev durum CRUD testleri."""

    @pytest.mark.asyncio
    async def test_store_task_status(self, connected_memory: ShortTermMemory) -> None:
        """store_task_status JSON serialize edip set cagirmali."""
        status_data = {"id": "t1", "status": "running", "agent": "test_agent"}

        await connected_memory.store_task_status("t1", status_data, ttl=3600)

        connected_memory.redis.set.assert_awaited_once_with(
            "test:task:t1",
            json.dumps(status_data, default=str),
            ex=3600,
        )

    @pytest.mark.asyncio
    async def test_get_task_status_found(self, connected_memory: ShortTermMemory) -> None:
        """Mevcut gorev durumu dondurulmeli."""
        expected = {"id": "t1", "status": "running"}
        connected_memory.redis.get = AsyncMock(return_value=json.dumps(expected))

        result = await connected_memory.get_task_status("t1")

        assert result == expected
        connected_memory.redis.get.assert_awaited_once_with("test:task:t1")

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Bulunamayan gorev icin None donmeli."""
        connected_memory.redis.get = AsyncMock(return_value=None)

        result = await connected_memory.get_task_status("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_task_status_exists(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Mevcut gorev silindiginde True donmeli."""
        connected_memory.redis.delete = AsyncMock(return_value=1)

        result = await connected_memory.delete_task_status("t1")

        assert result is True
        connected_memory.redis.delete.assert_awaited_once_with("test:task:t1")

    @pytest.mark.asyncio
    async def test_delete_task_status_not_exists(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Olmayan gorev silindiginde False donmeli."""
        connected_memory.redis.delete = AsyncMock(return_value=0)

        result = await connected_memory.delete_task_status("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, connected_memory: ShortTermMemory) -> None:
        """Tum aktif gorevler listelenmeli."""
        task1 = {"id": "t1", "status": "running"}
        task2 = {"id": "t2", "status": "pending"}

        # scan_iter mock - async generator
        async def mock_scan_iter(match: str):
            yield "test:task:t1"
            yield "test:task:t2"

        connected_memory.redis.scan_iter = mock_scan_iter
        connected_memory.redis.get = AsyncMock(
            side_effect=[json.dumps(task1), json.dumps(task2)]
        )

        result = await connected_memory.get_active_tasks()

        assert len(result) == 2
        assert result[0] == task1
        assert result[1] == task2


# === Oturum cache testleri ===


class TestSession:
    """Oturum cache CRUD testleri."""

    @pytest.mark.asyncio
    async def test_store_session(self, connected_memory: ShortTermMemory) -> None:
        """store_session TTL ile kaydetmeli."""
        data = {"user": "fatih", "role": "admin"}

        await connected_memory.store_session("s1", data, ttl=1800)

        connected_memory.redis.set.assert_awaited_once_with(
            "test:session:s1",
            json.dumps(data, default=str),
            ex=1800,
        )

    @pytest.mark.asyncio
    async def test_get_session_found(self, connected_memory: ShortTermMemory) -> None:
        """Mevcut oturum dondurulmeli."""
        expected = {"user": "fatih"}
        connected_memory.redis.get = AsyncMock(return_value=json.dumps(expected))

        result = await connected_memory.get_session("s1")

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Bulunamayan oturum icin None donmeli."""
        connected_memory.redis.get = AsyncMock(return_value=None)

        result = await connected_memory.get_session("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self, connected_memory: ShortTermMemory) -> None:
        """Oturum silinebilmeli."""
        connected_memory.redis.delete = AsyncMock(return_value=1)

        result = await connected_memory.delete_session("s1")

        assert result is True


# === Genel cache testleri ===


class TestCache:
    """Genel amacli cache testleri."""

    @pytest.mark.asyncio
    async def test_cache_set(self, connected_memory: ShortTermMemory) -> None:
        """cache_set deger kaydetmeli."""
        await connected_memory.cache_set("my_key", {"data": 42}, ttl=600)

        connected_memory.redis.set.assert_awaited_once_with(
            "test:cache:my_key",
            json.dumps({"data": 42}, default=str),
            ex=600,
        )

    @pytest.mark.asyncio
    async def test_cache_get_found(self, connected_memory: ShortTermMemory) -> None:
        """Mevcut cache degeri dondurulmeli."""
        connected_memory.redis.get = AsyncMock(return_value=json.dumps({"data": 42}))

        result = await connected_memory.cache_get("my_key")

        assert result == {"data": 42}

    @pytest.mark.asyncio
    async def test_cache_get_not_found(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Bulunamayan cache icin None donmeli."""
        connected_memory.redis.get = AsyncMock(return_value=None)

        result = await connected_memory.cache_get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, connected_memory: ShortTermMemory) -> None:
        """Cache silinebilmeli."""
        connected_memory.redis.delete = AsyncMock(return_value=1)

        result = await connected_memory.cache_delete("my_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_cache_delete_not_found(
        self, connected_memory: ShortTermMemory,
    ) -> None:
        """Olmayan cache silindiginde False donmeli."""
        connected_memory.redis.delete = AsyncMock(return_value=0)

        result = await connected_memory.cache_delete("nonexistent")

        assert result is False
