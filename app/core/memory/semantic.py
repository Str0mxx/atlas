"""ATLAS semantik hafiza modulu (Qdrant vektor veritabani).

Gorev gecmisi, kararlar, agent sonuclari ve konusmalarin
vektor tabanli semantik arama ile yonetimi.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger(__name__)


# === Pydantic Modelleri ===


class SemanticEntry(BaseModel):
    """Semantik hafizaya kaydedilecek veri modeli.

    Attributes:
        text: Embedding olusturulacak metin.
        metadata: Ek metadata bilgileri (agent, task_id, vb.).
        source: Kaynagi belirten etiket (ornek: 'task', 'decision').
    """

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = ""


class SemanticSearchResult(BaseModel):
    """Semantik arama sonuc modeli.

    Attributes:
        id: Nokta kimlik numarasi.
        text: Saklanan metin.
        score: Benzerlik skoru (0.0 - 1.0).
        metadata: Ek metadata bilgileri.
        source: Kaynak etiketi.
    """

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = ""


# === Koleksiyon tanimlari ===

COLLECTIONS: dict[str, str] = {
    "task_history": "Gorev gecmisi vektorleri",
    "decisions": "Karar kayitlari vektorleri",
    "agent_results": "Agent sonuc vektorleri",
    "conversations": "Konusma parca vektorleri",
}


class SemanticMemory:
    """Qdrant tabanli semantik hafiza sinifi.

    Vektor embedding'leri kullanarak semantik benzerlik aramasi yapar.
    fastembed entegrasyonu ile yerel embedding modeli kullanir.

    Attributes:
        prefix: Koleksiyon ad on eki (namespace).
        client: Async Qdrant istemcisi.
    """

    def __init__(self, prefix: str | None = None) -> None:
        """SemanticMemory'yi baslatir.

        Args:
            prefix: Koleksiyon ad on eki. None ise config'den alinir.
        """
        self.prefix = prefix or settings.qdrant_collection_prefix
        self.client: AsyncQdrantClient | None = None
        self._embedding_model = settings.qdrant_embedding_model
        self._embedding_dimension = settings.qdrant_embedding_dimension
        self._embedder: Any = None

    async def connect(self) -> None:
        """Qdrant baglantisini kurar ve koleksiyonlari hazirlar."""
        api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )

        self.client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            api_key=api_key,
        )

        # Baglanti testi
        collections = await self.client.get_collections()
        logger.info(
            "Qdrant baglantisi kuruldu: %s:%s (mevcut koleksiyon: %d)",
            settings.qdrant_host,
            settings.qdrant_port,
            len(collections.collections),
        )

        # Koleksiyonlari olustur (yoksa)
        for collection_name in COLLECTIONS:
            await self.ensure_collection(collection_name)

    async def close(self) -> None:
        """Qdrant baglantisini kapatir."""
        if self.client is not None:
            await self.client.close()
            self.client = None
            logger.info("Qdrant baglantisi kapatildi")

    def _ensure_connected(self) -> AsyncQdrantClient:
        """Baglantinin aktif oldugunu dogrular.

        Returns:
            Aktif AsyncQdrantClient istemcisi.

        Raises:
            RuntimeError: Baglanti kurulmamissa.
        """
        if self.client is None:
            raise RuntimeError(
                "Qdrant baglantisi kurulmamis. Once connect() cagiriniz."
            )
        return self.client

    def _collection_name(self, name: str) -> str:
        """Prefixed koleksiyon adi olusturur.

        Args:
            name: Koleksiyon kisa adi.

        Returns:
            Tam koleksiyon adi (ornek: 'atlas_task_history').
        """
        return f"{self.prefix}_{name}"

    # === Koleksiyon yonetimi ===

    async def ensure_collection(self, name: str) -> bool:
        """Koleksiyonu olusturur (yoksa).

        Args:
            name: Koleksiyon kisa adi (ornek: 'task_history').

        Returns:
            True: Olusturuldu, False: Zaten mevcut.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(name)

        exists = await client.collection_exists(full_name)
        if exists:
            logger.debug("Koleksiyon zaten mevcut: %s", full_name)
            return False

        await client.create_collection(
            collection_name=full_name,
            vectors_config=VectorParams(
                size=self._embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Koleksiyon olusturuldu: %s", full_name)
        return True

    async def delete_collection(self, name: str) -> bool:
        """Koleksiyonu siler.

        Args:
            name: Koleksiyon kisa adi.

        Returns:
            True: Silindi.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(name)

        result = await client.delete_collection(full_name)
        logger.info("Koleksiyon silindi: %s", full_name)
        return result

    # === Embedding uretimi ===

    def _get_embedder(self) -> Any:
        """Embedding modelini lazy-load eder.

        Returns:
            TextEmbedding model nesnesi.

        Raises:
            ImportError: fastembed kurulu degilse.
        """
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise ImportError(
                    "fastembed kurulu degil. "
                    "'pip install qdrant-client[fastembed]' ile kurunuz."
                ) from exc

            self._embedder = TextEmbedding(model_name=self._embedding_model)
            logger.info("Embedding modeli yuklendi: %s", self._embedding_model)
        return self._embedder

    async def _generate_embedding(self, text: str) -> list[float]:
        """Metin icin embedding vektoru uretir.

        Args:
            text: Embedding olusturulacak metin.

        Returns:
            Embedding vektoru (float listesi).
        """
        embedder = self._get_embedder()
        embeddings = list(embedder.embed([text]))
        return embeddings[0].tolist()

    # === CRUD islemleri ===

    async def store(
        self,
        collection: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        source: str = "",
        point_id: str | None = None,
    ) -> str:
        """Metni embedding ile birlikte koleksiyona kaydeder.

        Args:
            collection: Koleksiyon kisa adi.
            text: Kaydedilecek metin.
            metadata: Ek metadata bilgileri (opsiyonel).
            source: Kaynak etiketi (opsiyonel).
            point_id: Nokta ID'si (opsiyonel, otomatik olusturulur).

        Returns:
            Kaydedilen noktanin ID'si.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(collection)

        embedding = await self._generate_embedding(text)

        pid = point_id or str(uuid.uuid4())

        payload: dict[str, Any] = {
            "text": text,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            payload["metadata"] = metadata

        await client.upsert(
            collection_name=full_name,
            points=[
                PointStruct(
                    id=pid,
                    vector=embedding,
                    payload=payload,
                ),
            ],
        )

        logger.debug(
            "Semantik kayit eklendi: koleksiyon=%s, id=%s, metin=%s...",
            collection,
            pid,
            text[:50],
        )
        return pid

    async def store_batch(
        self,
        collection: str,
        entries: list[SemanticEntry],
    ) -> list[str]:
        """Birden fazla metni toplu olarak kaydeder.

        Args:
            collection: Koleksiyon kisa adi.
            entries: Kaydedilecek girisler listesi.

        Returns:
            Kaydedilen nokta ID'leri listesi.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(collection)

        points: list[PointStruct] = []
        ids: list[str] = []

        for entry in entries:
            embedding = await self._generate_embedding(entry.text)
            pid = str(uuid.uuid4())
            ids.append(pid)

            payload: dict[str, Any] = {
                "text": entry.text,
                "source": entry.source,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if entry.metadata:
                payload["metadata"] = entry.metadata

            points.append(
                PointStruct(id=pid, vector=embedding, payload=payload)
            )

        await client.upsert(
            collection_name=full_name,
            points=points,
        )

        logger.info(
            "Toplu semantik kayit: koleksiyon=%s, adet=%d",
            collection,
            len(points),
        )
        return ids

    async def search(
        self,
        collection: str,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.0,
        source_filter: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SemanticSearchResult]:
        """Semantik benzerlik aramasi yapar.

        Args:
            collection: Koleksiyon kisa adi.
            query: Arama sorgu metni.
            limit: Maksimum sonuc sayisi.
            score_threshold: Minimum benzerlik skoru (0.0-1.0).
            source_filter: Kaynak etiketi filtresi (opsiyonel).
            metadata_filter: Metadata filtresi (opsiyonel).

        Returns:
            Benzerlik sirasina gore siralanmis sonuc listesi.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(collection)

        query_embedding = await self._generate_embedding(query)

        query_filter = self._build_filter(source_filter, metadata_filter)

        results = await client.search(
            collection_name=full_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        search_results: list[SemanticSearchResult] = []
        for hit in results:
            payload = hit.payload or {}
            search_results.append(
                SemanticSearchResult(
                    id=str(hit.id),
                    text=payload.get("text", ""),
                    score=hit.score,
                    metadata=payload.get("metadata", {}),
                    source=payload.get("source", ""),
                )
            )

        logger.debug(
            "Semantik arama: koleksiyon=%s, sorgu=%s..., sonuc=%d",
            collection,
            query[:50],
            len(search_results),
        )
        return search_results

    async def search_across_collections(
        self,
        query: str,
        collections: list[str] | None = None,
        limit_per_collection: int = 3,
        score_threshold: float = 0.3,
    ) -> dict[str, list[SemanticSearchResult]]:
        """Birden fazla koleksiyonda arama yapar.

        Args:
            query: Arama sorgu metni.
            collections: Aranacak koleksiyonlar (None ise tumu).
            limit_per_collection: Koleksiyon basina maks sonuc.
            score_threshold: Minimum benzerlik skoru.

        Returns:
            Koleksiyon adi -> sonuc listesi eslesmesi.
        """
        target_collections = collections or list(COLLECTIONS.keys())
        all_results: dict[str, list[SemanticSearchResult]] = {}

        for col_name in target_collections:
            try:
                results = await self.search(
                    collection=col_name,
                    query=query,
                    limit=limit_per_collection,
                    score_threshold=score_threshold,
                )
                all_results[col_name] = results
            except Exception as exc:
                logger.warning(
                    "Koleksiyon aramasinda hata: %s - %s", col_name, exc
                )
                all_results[col_name] = []

        total = sum(len(v) for v in all_results.values())
        logger.info(
            "Capraz koleksiyon arama: sorgu=%s..., toplam sonuc=%d",
            query[:50],
            total,
        )
        return all_results

    async def delete(
        self,
        collection: str,
        point_ids: list[str],
    ) -> bool:
        """Belirtilen noktalari koleksiyondan siler.

        Args:
            collection: Koleksiyon kisa adi.
            point_ids: Silinecek nokta ID'leri.

        Returns:
            True: Silme basarili.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(collection)

        await client.delete(
            collection_name=full_name,
            points_selector=point_ids,
        )

        logger.debug(
            "Semantik kayitlar silindi: koleksiyon=%s, adet=%d",
            collection,
            len(point_ids),
        )
        return True

    async def delete_by_source(
        self,
        collection: str,
        source: str,
    ) -> bool:
        """Belirli bir kaynaga ait tum noktalari siler.

        Args:
            collection: Koleksiyon kisa adi.
            source: Kaynak etiketi.

        Returns:
            True: Silme basarili.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(collection)

        await client.delete(
            collection_name=full_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source),
                    ),
                ],
            ),
        )

        logger.info(
            "Kaynaga gore silme: koleksiyon=%s, kaynak=%s",
            collection,
            source,
        )
        return True

    async def get_collection_info(self, name: str) -> dict[str, Any]:
        """Koleksiyon hakkinda bilgi dondurur.

        Args:
            name: Koleksiyon kisa adi.

        Returns:
            Koleksiyon bilgileri (nokta sayisi, boyut, vb.).
        """
        client = self._ensure_connected()
        full_name = self._collection_name(name)

        info = await client.get_collection(full_name)
        return {
            "name": full_name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value if info.status else "unknown",
        }

    async def count(self, collection: str) -> int:
        """Koleksiyondaki toplam nokta sayisini dondurur.

        Args:
            collection: Koleksiyon kisa adi.

        Returns:
            Nokta sayisi.
        """
        client = self._ensure_connected()
        full_name = self._collection_name(collection)

        info = await client.get_collection(full_name)
        return info.points_count or 0

    # === Yardimci metodlar ===

    def _build_filter(
        self,
        source_filter: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> Filter | None:
        """Qdrant filtre nesnesi olusturur.

        Args:
            source_filter: Kaynak etiketi filtresi.
            metadata_filter: Metadata alan filtreleri.

        Returns:
            Filter nesnesi veya None (filtre yoksa).
        """
        conditions: list[FieldCondition] = []

        if source_filter:
            conditions.append(
                FieldCondition(
                    key="source",
                    match=MatchValue(value=source_filter),
                )
            )

        if metadata_filter:
            for key, value in metadata_filter.items():
                conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value),
                    )
                )

        if not conditions:
            return None

        return Filter(must=conditions)
