"""WorkingMemory testleri.

Calisma bellegi: ekleme, cikarma, erisim, odaklanma,
chunking, manipulasyon, durum, kapasite, yuk ve temizleme testleri.
"""

import time

import pytest

from app.core.memory_palace.working_memory import WorkingMemory


# === Yardimci fonksiyonlar ===


def _make_wm(**kwargs) -> WorkingMemory:
    """WorkingMemory olusturur."""
    return WorkingMemory(**kwargs)


# === Init Testleri ===


class TestInit:
    """WorkingMemory initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan parametrelerle olusturma."""
        wm = _make_wm()
        assert wm._capacity == 7
        assert wm._max_load == 1.0
        assert wm._items == {}
        assert wm._chunks == {}

    def test_custom_capacity(self) -> None:
        """Ozel kapasite ile olusturma."""
        wm = _make_wm(capacity=4)
        assert wm._capacity == 4

    def test_custom_max_load(self) -> None:
        """Ozel bilissel yuk limiti ile olusturma."""
        wm = _make_wm(max_cognitive_load=0.5)
        assert wm._max_load == 0.5


# === add Testleri ===


class TestAdd:
    """WorkingMemory.add testleri."""

    def test_basic_add(self) -> None:
        """Temel oge ekleme."""
        wm = _make_wm()
        item = wm.add("hello", priority=0.7, cognitive_load=0.1)
        assert item is not None
        assert item.content == "hello"
        assert item.priority == 0.7
        assert item.cognitive_load == 0.1
        assert item.id in wm._items

    def test_at_capacity_evicts_lowest_priority(self) -> None:
        """Kapasite doluyken en dusuk oncelikli ogenin cikarilmasi."""
        wm = _make_wm(capacity=2, max_cognitive_load=10.0)
        low = wm.add("low", priority=0.1, cognitive_load=0.1)
        high = wm.add("high", priority=0.9, cognitive_load=0.1)
        assert low is not None
        assert high is not None

        new = wm.add("new", priority=0.5, cognitive_load=0.1)
        assert new is not None
        # Dusuk oncelikli oge cikarilmis olmali
        assert low.id not in wm._items
        assert high.id in wm._items
        assert new.id in wm._items

    def test_returns_none_if_cognitive_load_exceeded(self) -> None:
        """Bilissel yuk asiminda None donmesi."""
        wm = _make_wm(max_cognitive_load=0.2)
        wm.add("first", cognitive_load=0.15)
        result = wm.add("second", cognitive_load=0.1)
        assert result is None


# === remove Testleri ===


class TestRemove:
    """WorkingMemory.remove testleri."""

    def test_removes_item(self) -> None:
        """Ogenin basariyla cikarilmasi."""
        wm = _make_wm()
        item = wm.add("data")
        assert item is not None
        assert wm.remove(item.id) is True
        assert item.id not in wm._items

    def test_returns_false_for_unknown(self) -> None:
        """Bilinmeyen oge icin False donmesi."""
        wm = _make_wm()
        assert wm.remove("nonexistent") is False

    def test_removes_from_chunk(self) -> None:
        """Chunk'a ait ogenin cikarildiginda chunk'tan da cikmasi."""
        wm = _make_wm()
        a = wm.add("a", cognitive_load=0.05)
        b = wm.add("b", cognitive_load=0.05)
        assert a is not None and b is not None
        chunk_id = wm.chunk([a.id, b.id])
        assert chunk_id is not None

        wm.remove(a.id)
        # a chunk'tan cikarilmis olmali
        assert a.id not in wm._chunks[chunk_id]
        assert b.id in wm._chunks[chunk_id]

    def test_removes_empty_chunk(self) -> None:
        """Tek elemanli chunk'tan oge cikarilinca chunk'un silinmesi."""
        wm = _make_wm()
        a = wm.add("a", cognitive_load=0.05)
        assert a is not None
        chunk_id = wm.chunk([a.id])
        assert chunk_id is not None

        wm.remove(a.id)
        assert chunk_id not in wm._chunks


# === get Testleri ===


class TestGet:
    """WorkingMemory.get testleri."""

    def test_existing(self) -> None:
        """Mevcut ogenin getirilmesi."""
        wm = _make_wm()
        item = wm.add("data")
        assert item is not None
        result = wm.get(item.id)
        assert result is not None
        assert result.content == "data"

    def test_none_for_unknown(self) -> None:
        """Bilinmeyen oge icin None donmesi."""
        wm = _make_wm()
        assert wm.get("nonexistent") is None

    def test_updates_accessed_at(self) -> None:
        """Erisim zamaninin guncellenmesi."""
        wm = _make_wm()
        item = wm.add("data")
        assert item is not None
        original_accessed = item.accessed_at
        time.sleep(0.01)
        wm.get(item.id)
        assert item.accessed_at >= original_accessed


# === focus Testleri ===


class TestFocus:
    """WorkingMemory.focus testleri."""

    def test_updates_priority(self) -> None:
        """Oncelik guncelleme (odaklanma)."""
        wm = _make_wm()
        item = wm.add("task", priority=0.3)
        assert item is not None
        result = wm.focus(item.id, new_priority=0.9)
        assert result is not None
        assert result.priority == 0.9

    def test_focus_unknown_returns_none(self) -> None:
        """Bilinmeyen oge icin None donmesi."""
        wm = _make_wm()
        assert wm.focus("nonexistent") is None


# === chunk Testleri ===


class TestChunk:
    """WorkingMemory.chunk testleri."""

    def test_groups_items(self) -> None:
        """Ogelerin gruplandirmasi."""
        wm = _make_wm()
        a = wm.add("a", cognitive_load=0.05)
        b = wm.add("b", cognitive_load=0.05)
        assert a is not None and b is not None
        chunk_id = wm.chunk([a.id, b.id], chunk_label="pair")
        assert chunk_id is not None
        assert a.chunk_id == chunk_id
        assert b.chunk_id == chunk_id
        assert wm._chunks[chunk_id] == [a.id, b.id]

    def test_counts_as_one_slot(self) -> None:
        """Chunk'in kapasitede tek slot olarak sayilmasi."""
        wm = _make_wm(capacity=3, max_cognitive_load=10.0)
        items = [wm.add(f"item{i}", cognitive_load=0.05) for i in range(3)]
        assert all(it is not None for it in items)

        # 3 oge kapasite dolu; chunk yap -> 1 slot + 0 standalone = 1
        chunk_id = wm.chunk([items[0].id, items[1].id, items[2].id])
        assert chunk_id is not None
        assert wm.available_capacity() == 2  # 3 - 1 chunk = 2

    def test_returns_none_if_item_not_found(self) -> None:
        """Oge bulunamazsa None donmesi."""
        wm = _make_wm()
        a = wm.add("a", cognitive_load=0.05)
        assert a is not None
        result = wm.chunk([a.id, "nonexistent"])
        assert result is None


# === unchunk Testleri ===


class TestUnchunk:
    """WorkingMemory.unchunk testleri."""

    def test_separates_items(self) -> None:
        """Grubu cozup ogeleri bagimsiz hale getirme."""
        wm = _make_wm()
        a = wm.add("a", cognitive_load=0.05)
        b = wm.add("b", cognitive_load=0.05)
        assert a is not None and b is not None
        chunk_id = wm.chunk([a.id, b.id])
        assert chunk_id is not None

        unchunked = wm.unchunk(chunk_id)
        assert len(unchunked) == 2
        assert a.chunk_id is None
        assert b.chunk_id is None
        assert chunk_id not in wm._chunks

    def test_each_counts_individually(self) -> None:
        """Unchunk sonrasi her ogenin ayri slot olarak sayilmasi."""
        wm = _make_wm(capacity=5, max_cognitive_load=10.0)
        a = wm.add("a", cognitive_load=0.05)
        b = wm.add("b", cognitive_load=0.05)
        c = wm.add("c", cognitive_load=0.05)
        assert a is not None and b is not None and c is not None
        chunk_id = wm.chunk([a.id, b.id])
        assert chunk_id is not None
        # 1 chunk + 1 standalone = 2 effective -> 3 available
        assert wm.available_capacity() == 3

        wm.unchunk(chunk_id)
        # 3 standalone -> 2 available
        assert wm.available_capacity() == 2


# === manipulate Testleri ===


class TestManipulate:
    """WorkingMemory.manipulate testleri."""

    def test_transforms_content(self) -> None:
        """Icerige donusum uygulanmasi."""
        wm = _make_wm()
        item = wm.add("hello")
        assert item is not None
        result = wm.manipulate(item.id, lambda x: x.upper())
        assert result is not None
        assert result.content == "HELLO"

    def test_updates_accessed_at(self) -> None:
        """Manipulasyon sonrasi erisim zamani guncellenmesi."""
        wm = _make_wm()
        item = wm.add("data")
        assert item is not None
        original = item.accessed_at
        time.sleep(0.01)
        wm.manipulate(item.id, lambda x: x)
        assert item.accessed_at >= original

    def test_returns_none_for_unknown(self) -> None:
        """Bilinmeyen oge icin None donmesi."""
        wm = _make_wm()
        assert wm.manipulate("nonexistent", lambda x: x) is None


# === get_state Testleri ===


class TestState:
    """WorkingMemory.get_state testleri."""

    def test_reflects_current_items(self) -> None:
        """Durumun mevcut ogeleri ve chunk'lari yansitmasi."""
        wm = _make_wm()
        a = wm.add("a", cognitive_load=0.1)
        b = wm.add("b", cognitive_load=0.2)
        assert a is not None and b is not None
        chunk_id = wm.chunk([a.id, b.id])
        assert chunk_id is not None

        state = wm.get_state()
        assert state.capacity == 7
        assert state.current_load == pytest.approx(0.3)
        assert len(state.items) == 2
        assert chunk_id in state.chunks
        assert len(state.chunks[chunk_id]) == 2


# === available_capacity Testleri ===


class TestCapacity:
    """WorkingMemory.available_capacity testleri."""

    def test_accounts_for_chunks(self) -> None:
        """Kapasite hesabinda chunk'larin tek slot sayilmasi."""
        wm = _make_wm(capacity=5, max_cognitive_load=10.0)
        a = wm.add("a", cognitive_load=0.05)
        b = wm.add("b", cognitive_load=0.05)
        c = wm.add("c", cognitive_load=0.05)
        assert a is not None and b is not None and c is not None

        # 3 standalone -> 2 available
        assert wm.available_capacity() == 2

        # Chunk 2 -> 1 chunk + 1 standalone = 2 effective -> 3 available
        wm.chunk([a.id, b.id])
        assert wm.available_capacity() == 3

    def test_empty(self) -> None:
        """Bos bellekte tam kapasite."""
        wm = _make_wm(capacity=7)
        assert wm.available_capacity() == 7


# === current_load Testleri ===


class TestLoad:
    """WorkingMemory.current_load testleri."""

    def test_sum_of_cognitive_loads(self) -> None:
        """Toplam bilissel yuk hesaplanmasi."""
        wm = _make_wm()
        wm.add("a", cognitive_load=0.1)
        wm.add("b", cognitive_load=0.2)
        assert wm.current_load() == pytest.approx(0.3)

    def test_empty_load(self) -> None:
        """Bos bellekte sifir yuk."""
        wm = _make_wm()
        assert wm.current_load() == 0.0


# === clear Testleri ===


class TestClear:
    """WorkingMemory.clear testleri."""

    def test_removes_all(self) -> None:
        """Tum ogelerin temizlenmesi."""
        wm = _make_wm()
        wm.add("a", cognitive_load=0.05)
        wm.add("b", cognitive_load=0.05)
        count = wm.clear()
        assert count == 2
        assert wm._items == {}
        assert wm._chunks == {}

    def test_returns_count(self) -> None:
        """Temizlenen oge sayisinin donmesi."""
        wm = _make_wm()
        for i in range(5):
            wm.add(f"item{i}", cognitive_load=0.05)
        assert wm.clear() == 5


# === Eviction Testleri ===


class TestEviction:
    """WorkingMemory eviction (cikarma) testleri."""

    def test_fifo_tiebreak_for_equal_priority(self) -> None:
        """Esit onceliklerde en eski (FIFO) ogenin cikarilmasi."""
        wm = _make_wm(capacity=2, max_cognitive_load=10.0)
        first = wm.add("first", priority=0.5, cognitive_load=0.1)
        time.sleep(0.01)  # added_at farki icin
        second = wm.add("second", priority=0.5, cognitive_load=0.1)
        assert first is not None and second is not None

        new = wm.add("new", priority=0.5, cognitive_load=0.1)
        assert new is not None
        # Ilk eklenen (en eski) cikarilmis olmali
        assert first.id not in wm._items
        assert second.id in wm._items
        assert new.id in wm._items

    def test_chunked_items_not_evicted(self) -> None:
        """Chunk'a ait ogelerin cikarma adayi olmamalari."""
        wm = _make_wm(capacity=2, max_cognitive_load=10.0)
        a = wm.add("chunked_low", priority=0.1, cognitive_load=0.1)
        b = wm.add("chunked_low2", priority=0.1, cognitive_load=0.1)
        assert a is not None and b is not None
        chunk_id = wm.chunk([a.id, b.id])
        assert chunk_id is not None
        # Efektif: 1 chunk = 1 slot, kapasite = 2 -> 1 bos slot
        standalone = wm.add("standalone", priority=0.9, cognitive_load=0.1)
        assert standalone is not None
        # Efektif: 1 chunk + 1 standalone = 2 slot (dolu)
        # Yeni oge eklendiginde standalone cikarilmali (chunk'taki ogeler korunmali)
        newest = wm.add("newest", priority=0.5, cognitive_load=0.1)
        assert newest is not None
        assert a.id in wm._items
        assert b.id in wm._items
