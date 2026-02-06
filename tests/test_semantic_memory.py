"""SemanticMemory (Qdrant) unit testleri.

Qdrant istemcisi ve embedding modeli mock'lanarak
semantik hafiza islemleri test edilir.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _MockPointStruct:
    """PointStruct mock - gercek nesne gibi davranir."""
    def __init__(self, id, vector, payload):
        self.id = id
        self.vector = vector
        self.payload = payload


class _MockFilter:
    """Filter mock - gercek nesne gibi davranir."""
    def __init__(self, must=None):
        self.must = must or []


class _MockFieldCondition:
    """FieldCondition mock."""
    def __init__(self, key, match):
        self.key = key
        self.match = match


class _MockMatchValue:
    """MatchValue mock."""
    def __init__(self, value):
        self.value = value


class _MockVectorParams:
    """VectorParams mock."""
    def __init__(self, size, distance):
        self.size = size
        self.distance = distance


class _MockDistance:
    """Distance enum mock."""
    COSINE = "Cosine"
    EUCLID = "Euclid"
    DOT = "Dot"


def _ensure_qdrant_mock():
    """qdrant_client modulu yoksa mock olarak ekler."""
    if "qdrant_client" not in sys.modules:
        mock_qdrant = MagicMock()
        mock_qdrant_models = MagicMock()
        mock_qdrant_models.Distance = _MockDistance
        mock_qdrant_models.PointStruct = _MockPointStruct
        mock_qdrant_models.Filter = _MockFilter
        mock_qdrant_models.FieldCondition = _MockFieldCondition
        mock_qdrant_models.MatchValue = _MockMatchValue
        mock_qdrant_models.VectorParams = _MockVectorParams
        sys.modules["qdrant_client"] = mock_qdrant
        sys.modules["qdrant_client.models"] = mock_qdrant_models

    if "fastembed" not in sys.modules:
        mock_fastembed = MagicMock()
        sys.modules["fastembed"] = mock_fastembed


_ensure_qdrant_mock()

from app.core.memory.semantic import (  # noqa: E402
    COLLECTIONS,
    SemanticEntry,
    SemanticMemory,
    SemanticSearchResult,
)


# === Fixtures ===

MOCK_EMBEDDING = [0.1] * 384  # 384 boyutlu sahte vektor


@pytest.fixture
def memory() -> SemanticMemory:
    """Yapilandirilmamis SemanticMemory (baglanti kurulmamis)."""
    return SemanticMemory(prefix="test")


@pytest.fixture
def connected_memory() -> SemanticMemory:
    """Qdrant mock ile bagli SemanticMemory."""
    mem = SemanticMemory(prefix="test")
    mock_client = AsyncMock()
    mock_client.get_collections = AsyncMock(
        return_value=MagicMock(collections=[])
    )
    mock_client.collection_exists = AsyncMock(return_value=True)
    mock_client.create_collection = AsyncMock()
    mock_client.delete_collection = AsyncMock(return_value=True)
    mock_client.upsert = AsyncMock()
    mock_client.search = AsyncMock(return_value=[])
    mock_client.delete = AsyncMock()
    mock_client.get_collection = AsyncMock(
        return_value=MagicMock(
            points_count=0,
            vectors_count=0,
            status=MagicMock(value="green"),
        )
    )
    mock_client.close = AsyncMock()
    mem.client = mock_client
    return mem


# === Pydantic model testleri ===


class TestModels:
    """SemanticEntry ve SemanticSearchResult model testleri."""

    def test_semantic_entry_defaults(self):
        """SemanticEntry varsayilan degerlerle olusturulur."""
        entry = SemanticEntry(text="test metin")
        assert entry.text == "test metin"
        assert entry.metadata == {}
        assert entry.source == ""

    def test_semantic_entry_full(self):
        """SemanticEntry tum alanlarla olusturulur."""
        entry = SemanticEntry(
            text="onemli veri",
            metadata={"agent": "security"},
            source="task",
        )
        assert entry.metadata["agent"] == "security"
        assert entry.source == "task"

    def test_search_result_defaults(self):
        """SemanticSearchResult varsayilan degerlerle olusturulur."""
        result = SemanticSearchResult(
            id="p1", text="sonuc", score=0.95,
        )
        assert result.id == "p1"
        assert result.score == 0.95
        assert result.metadata == {}

    def test_search_result_full(self):
        """SemanticSearchResult tum alanlarla olusturulur."""
        result = SemanticSearchResult(
            id="p2",
            text="detayli sonuc",
            score=0.87,
            metadata={"risk": "high"},
            source="decision",
        )
        assert result.metadata["risk"] == "high"
        assert result.source == "decision"


# === Baglanti testleri ===


class TestConnection:
    """Qdrant baglanti yonetimi testleri."""

    @pytest.mark.asyncio
    async def test_connect_creates_client(self, memory):
        """connect() AsyncQdrantClient olusturmali."""
        mock_client = AsyncMock()
        mock_client.get_collections = AsyncMock(
            return_value=MagicMock(collections=[])
        )
        mock_client.collection_exists = AsyncMock(return_value=True)

        with patch(
            "app.core.memory.semantic.AsyncQdrantClient",
            return_value=mock_client,
        ):
            await memory.connect()

        assert memory.client is not None
        mock_client.get_collections.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_creates_missing_collections(self, memory):
        """connect() eksik koleksiyonlari olusturmali."""
        mock_client = AsyncMock()
        mock_client.get_collections = AsyncMock(
            return_value=MagicMock(collections=[])
        )
        mock_client.collection_exists = AsyncMock(return_value=False)
        mock_client.create_collection = AsyncMock()

        with patch(
            "app.core.memory.semantic.AsyncQdrantClient",
            return_value=mock_client,
        ):
            await memory.connect()

        assert mock_client.create_collection.await_count == len(COLLECTIONS)

    @pytest.mark.asyncio
    async def test_connect_skips_existing_collections(self, memory):
        """connect() mevcut koleksiyonlari atlamali."""
        mock_client = AsyncMock()
        mock_client.get_collections = AsyncMock(
            return_value=MagicMock(collections=[])
        )
        mock_client.collection_exists = AsyncMock(return_value=True)
        mock_client.create_collection = AsyncMock()

        with patch(
            "app.core.memory.semantic.AsyncQdrantClient",
            return_value=mock_client,
        ):
            await memory.connect()

        mock_client.create_collection.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close(self, connected_memory):
        """close() Qdrant baglantisini kapatmali."""
        mock_client = connected_memory.client
        await connected_memory.close()

        mock_client.close.assert_awaited_once()
        assert connected_memory.client is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, memory):
        """Baglanti yokken close() hata vermemeli."""
        await memory.close()
        assert memory.client is None

    def test_ensure_connected_raises(self, memory):
        """Baglanti yokken _ensure_connected RuntimeError firlatmali."""
        with pytest.raises(RuntimeError, match="Qdrant baglantisi kurulmamis"):
            memory._ensure_connected()

    def test_ensure_connected_returns_client(self, connected_memory):
        """Baglanti varken _ensure_connected client dondurur."""
        result = connected_memory._ensure_connected()
        assert result is connected_memory.client


# === Koleksiyon adi testleri ===


class TestCollectionNaming:
    """Koleksiyon isimlendirme testleri."""

    def test_collection_name_with_prefix(self, memory):
        """Prefix ile koleksiyon adi olusturulur."""
        assert memory._collection_name("task_history") == "test_task_history"
        assert memory._collection_name("decisions") == "test_decisions"

    def test_collection_name_default_prefix(self):
        """Varsayilan prefix config'den gelir."""
        mem = SemanticMemory()
        name = mem._collection_name("agent_results")
        assert name.endswith("_agent_results")
        assert "_" in name

    def test_collections_defined(self):
        """4 koleksiyon tanimli olmali."""
        assert len(COLLECTIONS) == 4
        assert "task_history" in COLLECTIONS
        assert "decisions" in COLLECTIONS
        assert "agent_results" in COLLECTIONS
        assert "conversations" in COLLECTIONS


# === Koleksiyon yonetimi testleri ===


class TestCollectionManagement:
    """Koleksiyon olusturma/silme testleri."""

    @pytest.mark.asyncio
    async def test_ensure_collection_creates_when_missing(self, connected_memory):
        """Koleksiyon yoksa olusturulmali."""
        connected_memory.client.collection_exists = AsyncMock(return_value=False)

        result = await connected_memory.ensure_collection("task_history")

        assert result is True
        connected_memory.client.create_collection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_collection_skips_when_exists(self, connected_memory):
        """Koleksiyon varsa tekrar olusturulmamali."""
        connected_memory.client.collection_exists = AsyncMock(return_value=True)

        result = await connected_memory.ensure_collection("task_history")

        assert result is False
        connected_memory.client.create_collection.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_collection(self, connected_memory):
        """Koleksiyon silinebilmeli."""
        result = await connected_memory.delete_collection("task_history")

        assert result is True
        connected_memory.client.delete_collection.assert_awaited_once_with(
            "test_task_history"
        )

    @pytest.mark.asyncio
    async def test_ensure_collection_not_connected_raises(self, memory):
        """Baglanti yokken ensure_collection hata vermeli."""
        with pytest.raises(RuntimeError):
            await memory.ensure_collection("task_history")


# === Store testleri ===


class TestStore:
    """Veri kaydetme testleri."""

    @pytest.mark.asyncio
    async def test_store_single_entry(self, connected_memory):
        """Tek metin kaydedilebilmeli."""
        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            point_id = await connected_memory.store(
                collection="task_history",
                text="Sunucu CPU kullanimi yuksek",
                metadata={"agent": "server_monitor", "severity": "high"},
                source="task",
            )

        assert point_id is not None
        connected_memory.client.upsert.assert_awaited_once()

        call_args = connected_memory.client.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points) == 1
        assert points[0].payload["text"] == "Sunucu CPU kullanimi yuksek"
        assert points[0].payload["source"] == "task"
        assert points[0].payload["metadata"]["agent"] == "server_monitor"
        assert "created_at" in points[0].payload

    @pytest.mark.asyncio
    async def test_store_with_custom_id(self, connected_memory):
        """Ozel ID ile kayit yapilabilmeli."""
        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            point_id = await connected_memory.store(
                collection="decisions",
                text="Test karari",
                point_id="custom-id-123",
            )

        assert point_id == "custom-id-123"

    @pytest.mark.asyncio
    async def test_store_without_metadata(self, connected_memory):
        """Metadata olmadan kayit yapilabilmeli."""
        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            point_id = await connected_memory.store(
                collection="task_history",
                text="Basit kayit",
            )

        assert point_id is not None
        call_args = connected_memory.client.upsert.call_args
        payload = call_args.kwargs["points"][0].payload
        assert "metadata" not in payload
        assert payload["source"] == ""

    @pytest.mark.asyncio
    async def test_store_uses_correct_collection(self, connected_memory):
        """Dogru koleksiyon ismi kullanilmali."""
        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            await connected_memory.store(
                collection="decisions",
                text="Karar",
            )

        call_args = connected_memory.client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "test_decisions"

    @pytest.mark.asyncio
    async def test_store_batch(self, connected_memory):
        """Toplu kayit yapilabilmeli."""
        entries = [
            SemanticEntry(text="Birinci giris", metadata={"index": 1}, source="test"),
            SemanticEntry(text="Ikinci giris", metadata={"index": 2}, source="test"),
            SemanticEntry(text="Ucuncu giris", source="test"),
        ]

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            ids = await connected_memory.store_batch(
                collection="task_history",
                entries=entries,
            )

        assert len(ids) == 3
        connected_memory.client.upsert.assert_awaited_once()
        call_args = connected_memory.client.upsert.call_args
        assert len(call_args.kwargs["points"]) == 3

    @pytest.mark.asyncio
    async def test_store_batch_empty(self, connected_memory):
        """Bos liste ile toplu kayit calismali."""
        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            ids = await connected_memory.store_batch(
                collection="task_history",
                entries=[],
            )

        assert ids == []


# === Search testleri ===


class TestSearch:
    """Semantik arama testleri."""

    def _make_hit(self, id_val="point-001", score=0.95, text="Test sonuc",
                  source="task", metadata=None):
        """Mock arama sonucu olusturur."""
        hit = MagicMock()
        hit.id = id_val
        hit.score = score
        hit.payload = {
            "text": text,
            "source": source,
            "metadata": metadata or {},
        }
        return hit

    @pytest.mark.asyncio
    async def test_search_returns_results(self, connected_memory):
        """Arama sonuclari dondurulmeli."""
        hit = self._make_hit(
            text="Sunucu durumu kontrol edildi",
            metadata={"agent": "server_monitor"},
        )
        connected_memory.client.search = AsyncMock(return_value=[hit])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search(
                collection="task_history",
                query="sunucu kontrol",
                limit=5,
            )

        assert len(results) == 1
        assert results[0].id == "point-001"
        assert results[0].score == 0.95
        assert results[0].text == "Sunucu durumu kontrol edildi"
        assert results[0].source == "task"
        assert results[0].metadata["agent"] == "server_monitor"

    @pytest.mark.asyncio
    async def test_search_multiple_results(self, connected_memory):
        """Birden fazla sonuc dondurulmeli."""
        hits = [
            self._make_hit(id_val="p1", score=0.95, text="Birinci"),
            self._make_hit(id_val="p2", score=0.80, text="Ikinci"),
            self._make_hit(id_val="p3", score=0.70, text="Ucuncu"),
        ]
        connected_memory.client.search = AsyncMock(return_value=hits)

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search(
                collection="task_history",
                query="test",
            )

        assert len(results) == 3
        assert results[0].score > results[1].score > results[2].score

    @pytest.mark.asyncio
    async def test_search_empty_results(self, connected_memory):
        """Sonuc yoksa bos liste donmeli."""
        connected_memory.client.search = AsyncMock(return_value=[])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search(
                collection="task_history",
                query="olmayan sey",
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_source_filter(self, connected_memory):
        """Kaynak filtresi ile arama calismali."""
        connected_memory.client.search = AsyncMock(return_value=[])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            await connected_memory.search(
                collection="task_history",
                query="test",
                source_filter="task",
            )

        call_args = connected_memory.client.search.call_args
        assert call_args.kwargs["query_filter"] is not None

    @pytest.mark.asyncio
    async def test_search_with_score_threshold(self, connected_memory):
        """Skor esigi parametresi gecilmeli."""
        connected_memory.client.search = AsyncMock(return_value=[])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            await connected_memory.search(
                collection="task_history",
                query="test",
                score_threshold=0.5,
            )

        call_args = connected_memory.client.search.call_args
        assert call_args.kwargs["score_threshold"] == 0.5

    @pytest.mark.asyncio
    async def test_search_uses_correct_collection(self, connected_memory):
        """Dogru koleksiyon ismi kullanilmali."""
        connected_memory.client.search = AsyncMock(return_value=[])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            await connected_memory.search(
                collection="decisions",
                query="test",
            )

        call_args = connected_memory.client.search.call_args
        assert call_args.kwargs["collection_name"] == "test_decisions"

    @pytest.mark.asyncio
    async def test_search_with_none_payload(self, connected_memory):
        """Payload None olan sonuclar icin varsayilan degerler kullanilmali."""
        hit = MagicMock()
        hit.id = "p1"
        hit.score = 0.5
        hit.payload = None
        connected_memory.client.search = AsyncMock(return_value=[hit])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search(
                collection="task_history",
                query="test",
            )

        assert len(results) == 1
        assert results[0].text == ""
        assert results[0].metadata == {}
        assert results[0].source == ""

    @pytest.mark.asyncio
    async def test_search_across_collections(self, connected_memory):
        """Capraz koleksiyon aramasi calismali."""
        hit = self._make_hit(id_val="p1", score=0.8, text="Test")
        connected_memory.client.search = AsyncMock(return_value=[hit])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search_across_collections(
                query="test sorgusu",
                collections=["task_history", "decisions"],
            )

        assert "task_history" in results
        assert "decisions" in results
        assert len(results["task_history"]) == 1
        assert len(results["decisions"]) == 1

    @pytest.mark.asyncio
    async def test_search_across_all_collections(self, connected_memory):
        """Koleksiyon belirtilmezse tumu aranmali."""
        connected_memory.client.search = AsyncMock(return_value=[])

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search_across_collections(
                query="test",
            )

        assert len(results) == len(COLLECTIONS)

    @pytest.mark.asyncio
    async def test_search_across_handles_errors(self, connected_memory):
        """Koleksiyon hatasi diger aramalari etkilememeli."""
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Koleksiyon hatasi")
            return []

        connected_memory.client.search = AsyncMock(side_effect=side_effect)

        with patch.object(
            connected_memory,
            "_generate_embedding",
            return_value=MOCK_EMBEDDING,
        ):
            results = await connected_memory.search_across_collections(
                query="test",
                collections=["task_history", "decisions"],
            )

        assert "task_history" in results
        assert "decisions" in results
        assert results["task_history"] == []  # Hata olan bos donmeli


# === Delete testleri ===


class TestDelete:
    """Silme islemleri testleri."""

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, connected_memory):
        """ID'ler ile silme calismali."""
        result = await connected_memory.delete(
            collection="task_history",
            point_ids=["id-1", "id-2"],
        )

        assert result is True
        connected_memory.client.delete.assert_awaited_once()
        call_args = connected_memory.client.delete.call_args
        assert call_args.kwargs["collection_name"] == "test_task_history"
        assert call_args.kwargs["points_selector"] == ["id-1", "id-2"]

    @pytest.mark.asyncio
    async def test_delete_single_id(self, connected_memory):
        """Tek ID ile silme calismali."""
        result = await connected_memory.delete(
            collection="decisions",
            point_ids=["single-id"],
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_by_source(self, connected_memory):
        """Kaynak etiketi ile silme calismali."""
        result = await connected_memory.delete_by_source(
            collection="task_history",
            source="task",
        )

        assert result is True
        connected_memory.client.delete.assert_awaited_once()
        call_args = connected_memory.client.delete.call_args
        assert call_args.kwargs["collection_name"] == "test_task_history"

    @pytest.mark.asyncio
    async def test_delete_not_connected_raises(self, memory):
        """Baglanti yokken delete hata vermeli."""
        with pytest.raises(RuntimeError):
            await memory.delete(collection="task_history", point_ids=["id"])


# === Info/Count testleri ===


class TestInfo:
    """Bilgi sorgulama testleri."""

    @pytest.mark.asyncio
    async def test_get_collection_info(self, connected_memory):
        """Koleksiyon bilgisi dondurulmeli."""
        info = await connected_memory.get_collection_info("task_history")

        assert info["name"] == "test_task_history"
        assert "points_count" in info
        assert "vectors_count" in info
        assert info["status"] == "green"

    @pytest.mark.asyncio
    async def test_get_collection_info_none_status(self, connected_memory):
        """Status None ise 'unknown' donmeli."""
        connected_memory.client.get_collection = AsyncMock(
            return_value=MagicMock(
                points_count=10,
                vectors_count=10,
                status=None,
            )
        )

        info = await connected_memory.get_collection_info("task_history")
        assert info["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_count(self, connected_memory):
        """Nokta sayisi dondurulmeli."""
        connected_memory.client.get_collection = AsyncMock(
            return_value=MagicMock(points_count=42)
        )

        count = await connected_memory.count("task_history")
        assert count == 42

    @pytest.mark.asyncio
    async def test_count_zero(self, connected_memory):
        """Bos koleksiyonda 0 donmeli."""
        connected_memory.client.get_collection = AsyncMock(
            return_value=MagicMock(points_count=0)
        )

        count = await connected_memory.count("task_history")
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_none_returns_zero(self, connected_memory):
        """points_count None ise 0 donmeli."""
        connected_memory.client.get_collection = AsyncMock(
            return_value=MagicMock(points_count=None)
        )

        count = await connected_memory.count("task_history")
        assert count == 0


# === Filtre olusturma testleri ===


class TestFilterBuilder:
    """Filtre olusturma yardimci metod testleri."""

    def test_no_filter_returns_none(self, memory):
        """Filtre yoksa None donmeli."""
        result = memory._build_filter()
        assert result is None

    def test_source_filter(self, memory):
        """Kaynak filtresi olusturulmali."""
        result = memory._build_filter(source_filter="task")
        assert result is not None
        assert len(result.must) == 1

    def test_metadata_filter_single(self, memory):
        """Tek metadata filtresi olusturulmali."""
        result = memory._build_filter(
            metadata_filter={"agent": "server_monitor"}
        )
        assert result is not None
        assert len(result.must) == 1

    def test_metadata_filter_multiple(self, memory):
        """Birden fazla metadata filtresi olusturulmali."""
        result = memory._build_filter(
            metadata_filter={"agent": "security", "risk": "high"}
        )
        assert result is not None
        assert len(result.must) == 2

    def test_combined_filter(self, memory):
        """Source + metadata kombine filtre olusturulmali."""
        result = memory._build_filter(
            source_filter="task",
            metadata_filter={"agent": "server_monitor", "risk": "high"},
        )
        assert result is not None
        assert len(result.must) == 3  # 1 source + 2 metadata

    def test_empty_metadata_filter(self, memory):
        """Bos metadata dict filtre olusturmamali."""
        result = memory._build_filter(metadata_filter={})
        assert result is None


# === Embedding testleri ===


class TestEmbedding:
    """Embedding uretimi testleri."""

    def test_get_embedder_lazy_loads(self, memory):
        """_get_embedder ilk cagirida modeli yukler."""
        assert memory._embedder is None

        with patch("app.core.memory.semantic.SemanticMemory._get_embedder") as mock:
            mock.return_value = MagicMock()
            embedder = memory._get_embedder()
            assert embedder is not None

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_list(self, connected_memory):
        """_generate_embedding float listesi dondurmeli."""
        mock_embedder = MagicMock()
        import numpy as np
        mock_embedder.embed.return_value = [np.array(MOCK_EMBEDDING)]
        connected_memory._embedder = mock_embedder

        result = await connected_memory._generate_embedding("test metin")

        assert isinstance(result, list)
        assert len(result) == 384
        mock_embedder.embed.assert_called_once_with(["test metin"])


# === Init testleri ===


class TestInit:
    """SemanticMemory baslatma testleri."""

    def test_init_defaults(self, memory):
        """Varsayilan degerlerle olusturulur."""
        assert memory.prefix == "test"
        assert memory.client is None
        assert memory._embedder is None

    def test_init_custom_prefix(self):
        """Ozel prefix ile olusturulabilir."""
        mem = SemanticMemory(prefix="custom")
        assert mem.prefix == "custom"

    def test_init_none_prefix_uses_config(self):
        """None prefix config'den alinir."""
        mem = SemanticMemory(prefix=None)
        assert mem.prefix is not None
        assert len(mem.prefix) > 0
