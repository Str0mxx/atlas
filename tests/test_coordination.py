"""Coordination testleri.

Blackboard, SyncBarrier ve MutexLock testleri.
"""

import asyncio

from app.core.collaboration.coordination import (
    Blackboard,
    MutexLock,
    SyncBarrier,
)


# === Blackboard Testleri ===


class TestBlackboardInit:
    def test_default(self) -> None:
        bb = Blackboard()
        assert bb.read("ns", "key") is None


class TestBlackboardWriteRead:
    async def test_write_and_read(self) -> None:
        bb = Blackboard()
        version = await bb.write("server", "cpu", 85.0, author="monitor")
        assert version == 1
        assert bb.read("server", "cpu") == 85.0

    async def test_overwrite(self) -> None:
        bb = Blackboard()
        await bb.write("server", "cpu", 85.0)
        v = await bb.write("server", "cpu", 90.0)
        assert v == 2
        assert bb.read("server", "cpu") == 90.0

    async def test_different_namespaces(self) -> None:
        bb = Blackboard()
        await bb.write("server", "status", "ok")
        await bb.write("security", "status", "alert")
        assert bb.read("server", "status") == "ok"
        assert bb.read("security", "status") == "alert"

    def test_read_nonexistent(self) -> None:
        bb = Blackboard()
        assert bb.read("ns", "missing") is None


class TestBlackboardNamespace:
    async def test_read_namespace(self) -> None:
        bb = Blackboard()
        await bb.write("server", "cpu", 85.0)
        await bb.write("server", "mem", 70.0)
        await bb.write("other", "x", 1)
        ns = bb.read_namespace("server")
        assert ns == {"cpu": 85.0, "mem": 70.0}

    async def test_read_empty_namespace(self) -> None:
        bb = Blackboard()
        assert bb.read_namespace("empty") == {}

    async def test_clear_namespace(self) -> None:
        bb = Blackboard()
        await bb.write("server", "a", 1)
        await bb.write("server", "b", 2)
        await bb.write("other", "c", 3)
        cleared = bb.clear_namespace("server")
        assert cleared == 2
        assert bb.read("server", "a") is None
        assert bb.read("other", "c") == 3


class TestBlackboardVersion:
    async def test_version(self) -> None:
        bb = Blackboard()
        assert bb.get_version("ns", "key") == 0
        await bb.write("ns", "key", "v1")
        assert bb.get_version("ns", "key") == 1
        await bb.write("ns", "key", "v2")
        assert bb.get_version("ns", "key") == 2


class TestBlackboardDelete:
    async def test_delete(self) -> None:
        bb = Blackboard()
        await bb.write("ns", "key", "val")
        assert bb.delete("ns", "key") is True
        assert bb.read("ns", "key") is None

    def test_delete_nonexistent(self) -> None:
        bb = Blackboard()
        assert bb.delete("ns", "key") is False


class TestBlackboardWatch:
    async def test_watch_triggered(self) -> None:
        bb = Blackboard()

        async def writer() -> None:
            await asyncio.sleep(0.01)
            await bb.write("ns", "key", "updated")

        task = asyncio.create_task(writer())
        result = await bb.watch("ns", "key", timeout=2.0)
        await task
        assert result is True

    async def test_watch_timeout(self) -> None:
        bb = Blackboard()
        result = await bb.watch("ns", "key", timeout=0.01)
        assert result is False


class TestBlackboardHistory:
    async def test_history(self) -> None:
        bb = Blackboard()
        await bb.write("ns", "a", 1, author="x")
        await bb.write("ns", "b", 2, author="y")
        history = bb.get_history()
        assert len(history) == 2
        assert history[0]["author"] == "x"

    async def test_history_limit(self) -> None:
        bb = Blackboard()
        for i in range(10):
            await bb.write("ns", str(i), i)
        history = bb.get_history(limit=3)
        assert len(history) == 3


# === SyncBarrier Testleri ===


class TestSyncBarrierInit:
    def test_default(self) -> None:
        barrier = SyncBarrier("sync_point", 3)
        assert barrier.name == "sync_point"
        assert barrier.expected == 3
        assert barrier.arrived_count == 0
        assert barrier.is_complete is False


class TestSyncBarrierArrive:
    async def test_arrive(self) -> None:
        barrier = SyncBarrier("sync", 2)
        result = await barrier.arrive("agent_a")
        assert result is False
        assert barrier.arrived_count == 1

    async def test_arrive_complete(self) -> None:
        barrier = SyncBarrier("sync", 2)
        await barrier.arrive("agent_a")
        result = await barrier.arrive("agent_b")
        assert result is True
        assert barrier.is_complete is True

    async def test_duplicate_arrive(self) -> None:
        barrier = SyncBarrier("sync", 2)
        await barrier.arrive("agent_a")
        await barrier.arrive("agent_a")
        # Set kullanildigindan tekrar eklenmez
        assert barrier.arrived_count == 1


class TestSyncBarrierWait:
    async def test_wait_complete(self) -> None:
        barrier = SyncBarrier("sync", 2)

        async def arrivals() -> None:
            await asyncio.sleep(0.01)
            await barrier.arrive("a")
            await barrier.arrive("b")

        task = asyncio.create_task(arrivals())
        result = await barrier.wait(timeout=2.0)
        await task
        assert result is True

    async def test_wait_timeout(self) -> None:
        barrier = SyncBarrier("sync", 5)
        await barrier.arrive("a")
        result = await barrier.wait(timeout=0.01)
        assert result is False

    async def test_reset(self) -> None:
        barrier = SyncBarrier("sync", 2)
        await barrier.arrive("a")
        barrier.reset()
        assert barrier.arrived_count == 0
        assert barrier.is_complete is False


# === MutexLock Testleri ===


class TestMutexLockInit:
    def test_default(self) -> None:
        lock = MutexLock("database")
        assert lock.resource_name == "database"
        assert lock.holder is None
        assert lock.is_locked is False


class TestMutexLockAcquireRelease:
    async def test_acquire(self) -> None:
        lock = MutexLock("db")
        result = await lock.acquire("agent_a")
        assert result is True
        assert lock.holder == "agent_a"
        assert lock.is_locked is True

    async def test_release(self) -> None:
        lock = MutexLock("db")
        await lock.acquire("agent_a")
        result = lock.release("agent_a")
        assert result is True
        assert lock.holder is None
        assert lock.is_locked is False

    async def test_release_wrong_agent(self) -> None:
        lock = MutexLock("db")
        await lock.acquire("agent_a")
        result = lock.release("agent_b")
        assert result is False
        assert lock.holder == "agent_a"

    async def test_release_not_held(self) -> None:
        lock = MutexLock("db")
        result = lock.release("agent_a")
        assert result is False

    async def test_acquire_timeout(self) -> None:
        lock = MutexLock("db")
        await lock.acquire("agent_a")
        result = await lock.acquire("agent_b", timeout=0.01)
        assert result is False
        assert lock.holder == "agent_a"

    async def test_sequential_acquire(self) -> None:
        lock = MutexLock("db")
        await lock.acquire("agent_a")
        lock.release("agent_a")
        result = await lock.acquire("agent_b")
        assert result is True
        assert lock.holder == "agent_b"
