"""HookManager testleri."""

from unittest.mock import AsyncMock

import pytest

from app.core.plugins.hooks import HookManager
from app.models.plugin import HookEvent


# === Yardimci Fonksiyonlar ===


def _make_handler(side_effect: Exception | None = None) -> AsyncMock:
    """Test icin async hook handler olusturur."""
    handler = AsyncMock()
    if side_effect:
        handler.side_effect = side_effect
    return handler


def _make_manager() -> HookManager:
    """Test icin temiz HookManager olusturur."""
    return HookManager()


# === Init Testleri ===


class TestHookManagerInit:
    """HookManager baslatma testleri."""

    def test_empty_init(self) -> None:
        """Bos handler listesi ile baslamali."""
        mgr = _make_manager()
        assert mgr.total_handlers == 0

    def test_no_handlers_for_event(self) -> None:
        """Kayitsiz olay icin bos liste donmeli."""
        mgr = _make_manager()
        assert mgr.get_handlers(HookEvent.TASK_CREATED) == []


# === Register Testleri ===


class TestHookRegister:
    """Hook kayit testleri."""

    def test_register_single(self) -> None:
        """Tek handler kaydedilmeli."""
        mgr = _make_manager()
        handler = _make_handler()
        mgr.register(HookEvent.TASK_CREATED, "plugin_a", handler)
        assert mgr.total_handlers == 1

    def test_register_multiple_same_event(self) -> None:
        """Ayni olaya birden fazla handler kaydedilmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_CREATED, "p2", _make_handler())
        assert len(mgr.get_handlers(HookEvent.TASK_CREATED)) == 2

    def test_register_multiple_events(self) -> None:
        """Farkli olaylara handler kaydedilmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_COMPLETED, "p1", _make_handler())
        assert mgr.total_handlers == 2

    def test_priority_ordering(self) -> None:
        """Handler'lar oncelik sirasinda siralanmali."""
        mgr = _make_manager()
        h1 = _make_handler()
        h2 = _make_handler()
        h3 = _make_handler()
        mgr.register(HookEvent.TASK_CREATED, "p3", h3, priority=300)
        mgr.register(HookEvent.TASK_CREATED, "p1", h1, priority=10)
        mgr.register(HookEvent.TASK_CREATED, "p2", h2, priority=50)

        handlers = mgr.get_handlers(HookEvent.TASK_CREATED)
        assert handlers[0][1] == "p1"
        assert handlers[1][1] == "p2"
        assert handlers[2][1] == "p3"

    def test_default_priority(self) -> None:
        """Varsayilan oncelik 100 olmali."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        handlers = mgr.get_handlers(HookEvent.TASK_CREATED)
        assert handlers[0][0] == 100

    def test_same_plugin_multiple_handlers(self) -> None:
        """Ayni plugin birden fazla handler kaydedebilmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_COMPLETED, "p1", _make_handler())
        hooks = mgr.get_plugin_hooks("p1")
        assert HookEvent.TASK_CREATED in hooks
        assert HookEvent.TASK_COMPLETED in hooks


# === Unregister Testleri ===


class TestHookUnregister:
    """Hook kayit silme testleri."""

    def test_unregister_plugin(self) -> None:
        """Plugin'in tum handler'lari kaldirilmali."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_COMPLETED, "p1", _make_handler())
        removed = mgr.unregister_plugin("p1")
        assert removed == 2
        assert mgr.total_handlers == 0

    def test_unregister_preserves_others(self) -> None:
        """Diger plugin handler'lari korunmali."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_CREATED, "p2", _make_handler())
        mgr.unregister_plugin("p1")
        assert mgr.total_handlers == 1
        handlers = mgr.get_handlers(HookEvent.TASK_CREATED)
        assert handlers[0][1] == "p2"

    def test_unregister_nonexistent(self) -> None:
        """Olmayan plugin icin 0 donmeli."""
        mgr = _make_manager()
        removed = mgr.unregister_plugin("nonexistent")
        assert removed == 0

    def test_unregister_cleans_empty_events(self) -> None:
        """Bos kalan olay listesi temizlenmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.unregister_plugin("p1")
        assert mgr.get_handlers(HookEvent.TASK_CREATED) == []


# === Emit Testleri ===


class TestHookEmit:
    """Hook olay tetikleme testleri."""

    async def test_emit_calls_handler(self) -> None:
        """Emit handler'i cagirmali."""
        mgr = _make_manager()
        handler = _make_handler()
        mgr.register(HookEvent.TASK_CREATED, "p1", handler)
        await mgr.emit(HookEvent.TASK_CREATED, task_id="123")
        handler.assert_called_once_with(task_id="123")

    async def test_emit_calls_all_handlers(self) -> None:
        """Emit tum handler'lari cagirmali."""
        mgr = _make_manager()
        h1 = _make_handler()
        h2 = _make_handler()
        mgr.register(HookEvent.TASK_CREATED, "p1", h1)
        mgr.register(HookEvent.TASK_CREATED, "p2", h2)
        await mgr.emit(HookEvent.TASK_CREATED)
        h1.assert_called_once()
        h2.assert_called_once()

    async def test_emit_priority_order(self) -> None:
        """Emit handler'lari oncelik sirasinda cagirmali."""
        mgr = _make_manager()
        call_order: list[str] = []

        async def h1(**kwargs):
            call_order.append("first")

        async def h2(**kwargs):
            call_order.append("second")

        mgr.register(HookEvent.TASK_CREATED, "p2", h2, priority=200)
        mgr.register(HookEvent.TASK_CREATED, "p1", h1, priority=10)
        await mgr.emit(HookEvent.TASK_CREATED)
        assert call_order == ["first", "second"]

    async def test_emit_no_handlers(self) -> None:
        """Handler olmayan olay icin hata vermemeli."""
        mgr = _make_manager()
        errors = await mgr.emit(HookEvent.TASK_CREATED)
        assert errors == []

    async def test_emit_error_isolation(self) -> None:
        """Hata veren handler digerlerini engellemezken hata listesinde yer almali."""
        mgr = _make_manager()
        h1 = _make_handler(side_effect=ValueError("boom"))
        h2 = _make_handler()
        mgr.register(HookEvent.TASK_CREATED, "bad_plugin", h1, priority=10)
        mgr.register(HookEvent.TASK_CREATED, "good_plugin", h2, priority=20)
        errors = await mgr.emit(HookEvent.TASK_CREATED)
        assert "bad_plugin" in errors
        h2.assert_called_once()

    async def test_emit_multiple_errors(self) -> None:
        """Birden fazla hata veren handler raporlanmali."""
        mgr = _make_manager()
        h1 = _make_handler(side_effect=RuntimeError("err1"))
        h2 = _make_handler(side_effect=RuntimeError("err2"))
        mgr.register(HookEvent.TASK_CREATED, "p1", h1)
        mgr.register(HookEvent.TASK_CREATED, "p2", h2)
        errors = await mgr.emit(HookEvent.TASK_CREATED)
        assert len(errors) == 2

    async def test_emit_passes_kwargs(self) -> None:
        """Emit kwargs'lari handler'a iletmeli."""
        mgr = _make_manager()
        handler = _make_handler()
        mgr.register(HookEvent.TASK_COMPLETED, "p1", handler)
        await mgr.emit(HookEvent.TASK_COMPLETED, task_id="t1", result="ok")
        handler.assert_called_once_with(task_id="t1", result="ok")

    async def test_emit_returns_empty_on_success(self) -> None:
        """Hatasiz emit bos liste donmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        errors = await mgr.emit(HookEvent.TASK_CREATED)
        assert errors == []


# === Plugin Hooks Sorgulama Testleri ===


class TestGetPluginHooks:
    """Plugin hook sorgulama testleri."""

    def test_get_plugin_hooks(self) -> None:
        """Plugin'in kayitli hook'lari donmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_COMPLETED, "p1", _make_handler())
        hooks = mgr.get_plugin_hooks("p1")
        assert hooks[HookEvent.TASK_CREATED] == 1
        assert hooks[HookEvent.TASK_COMPLETED] == 1

    def test_get_plugin_hooks_empty(self) -> None:
        """Kayitsiz plugin icin bos dict donmeli."""
        mgr = _make_manager()
        assert mgr.get_plugin_hooks("nonexistent") == {}

    def test_multiple_handlers_same_event(self) -> None:
        """Ayni olaya birden fazla handler kayitliysa sayi dogru olmali."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        hooks = mgr.get_plugin_hooks("p1")
        assert hooks[HookEvent.TASK_CREATED] == 2


# === Clear Testleri ===


class TestHookClear:
    """Hook temizleme testleri."""

    def test_clear(self) -> None:
        """Clear tum handler'lari silmeli."""
        mgr = _make_manager()
        mgr.register(HookEvent.TASK_CREATED, "p1", _make_handler())
        mgr.register(HookEvent.TASK_COMPLETED, "p2", _make_handler())
        mgr.clear()
        assert mgr.total_handlers == 0

    def test_clear_empty(self) -> None:
        """Bos manager'da clear hata vermemeli."""
        mgr = _make_manager()
        mgr.clear()
        assert mgr.total_handlers == 0
