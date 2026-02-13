"""ATLAS Bilgi Grafi Yoneticisi modulu.

Tum bilgi grafi bilesenlerini orkestrasyonu: varlik cikarma,
iliski cikarma, graf olusturma, depolama, sorgulama, cikarim,
bilgi birlestirme, ontoloji yonetimi ve analitik.
"""

import logging
from typing import Any

from app.core.knowledge.entity_extractor import EntityExtractor
from app.core.knowledge.graph_builder import GraphBuilder
from app.core.knowledge.graph_store import GraphStore
from app.core.knowledge.inference_engine import InferenceEngine
from app.core.knowledge.knowledge_fusion import KnowledgeFusion
from app.core.knowledge.ontology_manager import OntologyManager
from app.core.knowledge.query_engine import QueryEngine
from app.core.knowledge.relation_extractor import RelationExtractor
from app.models.knowledge import (
    FusionResult,
    FusionStrategy,
    GraphStats,
    InferredFact,
    KGEntity,
    KGRelation,
    QueryResult,
)

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """Bilgi grafi orkestratoru.

    Tum bilgi grafi bilesenlerini koordine eder:
    metin isleme, graf olusturma, sorgulama, cikarim
    ve bilgi birlestirme.

    Attributes:
        _entity_extractor: Varlik cikarici.
        _relation_extractor: Iliski cikarici.
        _graph_builder: Graf olusturucu.
        _graph_store: Graf deposu.
        _query_engine: Sorgulama motoru.
        _inference_engine: Cikarim motoru.
        _fusion: Bilgi birlestirme.
        _ontology: Ontoloji yoneticisi.
    """

    def __init__(
        self,
        persistence_path: str = "",
        max_nodes: int = 10000,
        inference_depth: int = 5,
        fusion_strategy: FusionStrategy = FusionStrategy.TRUST_BASED,
    ) -> None:
        """Bilgi grafi yoneticisini baslatir.

        Args:
            persistence_path: Graf kalicilik dosya yolu.
            max_nodes: Maksimum dugum sayisi.
            inference_depth: Cikarim derinligi.
            fusion_strategy: Birlestirme stratejisi.
        """
        self._entity_extractor = EntityExtractor()
        self._relation_extractor = RelationExtractor()
        self._graph_builder = GraphBuilder()
        self._graph_store = GraphStore(persistence_path=persistence_path)
        self._query_engine = QueryEngine()
        self._inference_engine = InferenceEngine(max_depth=inference_depth)
        self._fusion = KnowledgeFusion(strategy=fusion_strategy)
        self._ontology = OntologyManager()
        self._max_nodes = max_nodes
        self._processing_count = 0

        logger.info(
            "KnowledgeGraphManager baslatildi (max_nodes=%d, depth=%d)",
            max_nodes, inference_depth,
        )

    def process_text(self, text: str, source: str = "text") -> dict[str, Any]:
        """Metni isle ve bilgi grafina ekle.

        Args:
            text: Giris metni.
            source: Kaynak tanimlayici.

        Returns:
            Isleme sonucu (entities, relations, nodes, edges).
        """
        # Varlik cikarma
        entities = self._entity_extractor.extract(text)

        # Iliski cikarma
        relations = self._relation_extractor.extract(text, entities)

        # Grafa ekle
        node_count = 0
        edge_count = 0
        node_ids: dict[str, str] = {}

        for entity in entities:
            entity.source = source
            node = self._graph_builder.add_node(entity)
            self._graph_store.store_node(node)
            node_ids[entity.id] = node.id
            node_count += 1

        for relation in relations:
            src_id = node_ids.get(relation.source_id)
            tgt_id = node_ids.get(relation.target_id)
            if src_id and tgt_id:
                edge = self._graph_builder.add_edge(relation, src_id, tgt_id)
                if edge:
                    self._graph_store.store_edge(edge)
                    edge_count += 1

        # Sorgu ve cikarim motorlarini guncelle
        self._sync_engines()
        self._processing_count += 1

        logger.info(
            "Metin islendi: %d varlik, %d iliski (source=%s)",
            node_count, edge_count, source,
        )
        return {
            "entities": len(entities),
            "relations": len(relations),
            "nodes_added": node_count,
            "edges_added": edge_count,
            "source": source,
        }

    def add_entity(self, entity: KGEntity) -> str:
        """Varlik ekler.

        Args:
            entity: Varlik nesnesi.

        Returns:
            Dugum ID.
        """
        node = self._graph_builder.add_node(entity)
        self._graph_store.store_node(node)
        self._sync_engines()
        return node.id

    def add_relation(self, relation: KGRelation, source_node_id: str, target_node_id: str) -> str | None:
        """Iliski ekler.

        Args:
            relation: Iliski nesnesi.
            source_node_id: Kaynak dugum ID.
            target_node_id: Hedef dugum ID.

        Returns:
            Kenar ID veya None.
        """
        edge = self._graph_builder.add_edge(relation, source_node_id, target_node_id)
        if edge:
            self._graph_store.store_edge(edge)
            self._sync_engines()
            return edge.id
        return None

    def query(self, query_text: str) -> QueryResult:
        """Dogal dil sorgusu yapar.

        Args:
            query_text: Sorgu metni.

        Returns:
            QueryResult nesnesi.
        """
        self._sync_engines()
        return self._query_engine.natural_language_query(query_text)

    def find_path(self, start_id: str, end_id: str, max_depth: int = 10) -> QueryResult:
        """Iki dugum arasi yol bulur.

        Args:
            start_id: Baslangic dugum ID.
            end_id: Hedef dugum ID.
            max_depth: Maksimum derinlik.

        Returns:
            QueryResult nesnesi.
        """
        self._sync_engines()
        return self._query_engine.find_path(start_id, end_id, max_depth)

    def extract_subgraph(self, center_id: str, depth: int = 2) -> QueryResult:
        """Alt graf cikarir.

        Args:
            center_id: Merkez dugum ID.
            depth: Cikarma derinligi.

        Returns:
            QueryResult nesnesi.
        """
        self._sync_engines()
        return self._query_engine.extract_subgraph(center_id, depth)

    def run_inference(self) -> list[InferredFact]:
        """Tum cikarim yontemlerini calistirir.

        Returns:
            Cikarilmis bilgi listesi.
        """
        self._sync_engines()
        return self._inference_engine.run_all()

    def fuse_sources(
        self,
        text_a: str,
        text_b: str,
        source_a: str = "source_a",
        source_b: str = "source_b",
    ) -> FusionResult:
        """Iki kaynagi birlestirir.

        Args:
            text_a: Birinci kaynak metni.
            text_b: Ikinci kaynak metni.
            source_a: Birinci kaynak adi.
            source_b: Ikinci kaynak adi.

        Returns:
            FusionResult nesnesi.
        """
        entities_a = self._entity_extractor.extract(text_a)
        relations_a = self._relation_extractor.extract(text_a, entities_a)
        entities_b = self._entity_extractor.extract(text_b)
        relations_b = self._relation_extractor.extract(text_b, entities_b)

        return self._fusion.fuse(
            entities_a, relations_a,
            entities_b, relations_b,
            source_a, source_b,
        )

    def get_stats(self) -> GraphStats:
        """Graf istatistiklerini getirir.

        Returns:
            GraphStats nesnesi.
        """
        return self._graph_store.get_stats()

    def get_analytics(self) -> dict[str, Any]:
        """Detayli analitik bilgi.

        Returns:
            Analitik sozlugu.
        """
        stats = self._graph_store.get_stats()
        return {
            "node_count": stats.node_count,
            "edge_count": stats.edge_count,
            "entity_types": stats.entity_type_counts,
            "relation_types": stats.relation_type_counts,
            "avg_degree": stats.avg_degree,
            "density": stats.density,
            "processing_count": self._processing_count,
            "inference_facts": self._inference_engine.fact_count,
            "fusion_count": self._fusion.fusion_count,
            "ontology_classes": self._ontology.class_count,
            "store_version": self._graph_store.version,
        }

    def export_json(self) -> str:
        """Grafi JSON olarak disari aktarir.

        Returns:
            JSON string.
        """
        return self._graph_store.export_json()

    def import_json(self, json_str: str) -> int:
        """JSON'dan graf icerir.

        Args:
            json_str: JSON string.

        Returns:
            Iceri alinan oge sayisi.
        """
        count = self._graph_store.import_json(json_str)
        self._sync_engines()
        return count

    def create_version(self, label: str = "") -> int:
        """Yeni versiyon olusturur.

        Args:
            label: Versiyon etiketi.

        Returns:
            Versiyon numarasi.
        """
        return self._graph_store.create_version(label)

    def _sync_engines(self) -> None:
        """Sorgu ve cikarim motorlarini graf verisiyle senkronize eder."""
        nodes = {n.id: n for n in self._graph_builder.nodes}
        edges = {e.id: e for e in self._graph_builder.edges}
        self._query_engine.set_data(nodes, edges)
        self._inference_engine.set_data(nodes, edges)

    @property
    def entity_extractor(self) -> EntityExtractor:
        """Varlik cikarici."""
        return self._entity_extractor

    @property
    def relation_extractor(self) -> RelationExtractor:
        """Iliski cikarici."""
        return self._relation_extractor

    @property
    def graph_builder(self) -> GraphBuilder:
        """Graf olusturucu."""
        return self._graph_builder

    @property
    def graph_store(self) -> GraphStore:
        """Graf deposu."""
        return self._graph_store

    @property
    def query_engine(self) -> QueryEngine:
        """Sorgulama motoru."""
        return self._query_engine

    @property
    def inference_engine(self) -> InferenceEngine:
        """Cikarim motoru."""
        return self._inference_engine

    @property
    def fusion(self) -> KnowledgeFusion:
        """Bilgi birlestirme."""
        return self._fusion

    @property
    def ontology(self) -> OntologyManager:
        """Ontoloji yoneticisi."""
        return self._ontology

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return self._graph_store.node_count

    @property
    def edge_count(self) -> int:
        """Kenar sayisi."""
        return self._graph_store.edge_count
