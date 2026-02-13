"""ATLAS Knowledge Graph sistemi testleri.

EntityExtractor, RelationExtractor, GraphBuilder, GraphStore,
QueryEngine, InferenceEngine, KnowledgeFusion, OntologyManager,
KnowledgeGraphManager icin kapsamli testler.
"""

import json

import pytest

from app.core.knowledge.entity_extractor import EntityExtractor
from app.core.knowledge.graph_builder import GraphBuilder
from app.core.knowledge.graph_store import GraphStore
from app.core.knowledge.inference_engine import InferenceEngine
from app.core.knowledge.knowledge_fusion import KnowledgeFusion
from app.core.knowledge.knowledge_graph_manager import KnowledgeGraphManager
from app.core.knowledge.ontology_manager import OntologyManager
from app.core.knowledge.query_engine import QueryEngine
from app.core.knowledge.relation_extractor import RelationExtractor
from app.models.knowledge import (
    ConflictResolution,
    EntityType,
    FusionStrategy,
    GraphEdge,
    GraphNode,
    InferenceType,
    KGEntity,
    KGRelation,
    NodeStatus,
    OntologyClass,
    PropertyType,
    QualityLevel,
    QueryType,
    RelationType,
)


# === Yardimci Fonksiyonlar ===


def _make_entity(name: str, etype: EntityType = EntityType.CONCEPT, **kwargs) -> KGEntity:
    """Test varligi olusturur."""
    return KGEntity(name=name, entity_type=etype, **kwargs)


def _make_relation(
    src_id: str,
    tgt_id: str,
    rtype: RelationType = RelationType.RELATED_TO,
    **kwargs,
) -> KGRelation:
    """Test iliskisi olusturur."""
    return KGRelation(relation_type=rtype, source_id=src_id, target_id=tgt_id, **kwargs)


def _build_simple_graph():
    """Basit test grafi olusturur (3 dugum, 2 kenar)."""
    builder = GraphBuilder()
    e1 = _make_entity("Python", EntityType.TECHNOLOGY)
    e2 = _make_entity("Django", EntityType.TECHNOLOGY)
    e3 = _make_entity("Web", EntityType.CONCEPT)

    n1 = builder.add_node(e1)
    n2 = builder.add_node(e2)
    n3 = builder.add_node(e3)

    r1 = _make_relation(n1.id, n2.id, RelationType.HAS_A)
    r2 = _make_relation(n2.id, n3.id, RelationType.PRODUCES)

    builder.add_edge(r1, n1.id, n2.id)
    builder.add_edge(r2, n2.id, n3.id)

    return builder, [n1, n2, n3]


def _build_inference_graph():
    """Cikarim testi icin graf olusturur."""
    builder = GraphBuilder()
    # Animal -> Dog -> Labrador
    e1 = _make_entity("Animal", EntityType.CONCEPT, attributes={"legs": 4, "alive": True})
    e2 = _make_entity("Dog", EntityType.CONCEPT)
    e3 = _make_entity("Labrador", EntityType.CONCEPT)

    n1 = builder.add_node(e1)
    n2 = builder.add_node(e2)
    n3 = builder.add_node(e3)

    r1 = _make_relation(n2.id, n1.id, RelationType.IS_A)
    r2 = _make_relation(n3.id, n2.id, RelationType.IS_A)

    builder.add_edge(r1, n2.id, n1.id)
    builder.add_edge(r2, n3.id, n2.id)

    return builder, [n1, n2, n3]


# === Model Testleri ===


class TestKnowledgeModels:
    """Bilgi grafi modelleri testleri."""

    def test_kg_entity_defaults(self):
        e = KGEntity()
        assert e.name == ""
        assert e.entity_type == EntityType.CONCEPT
        assert e.confidence == 1.0
        assert e.aliases == []
        assert e.attributes == {}
        assert len(e.id) > 0

    def test_kg_entity_with_values(self):
        e = KGEntity(name="Python", entity_type=EntityType.TECHNOLOGY, confidence=0.9)
        assert e.name == "Python"
        assert e.entity_type == EntityType.TECHNOLOGY
        assert e.confidence == 0.9

    def test_kg_relation_defaults(self):
        r = KGRelation()
        assert r.relation_type == RelationType.RELATED_TO
        assert r.strength == 1.0
        assert r.bidirectional is False
        assert r.temporal is False

    def test_kg_relation_temporal(self):
        r = KGRelation(temporal=True, relation_type=RelationType.CAUSES)
        assert r.temporal is True
        assert r.relation_type == RelationType.CAUSES

    def test_graph_node_defaults(self):
        n = GraphNode()
        assert n.status == NodeStatus.ACTIVE
        assert n.in_edges == []
        assert n.out_edges == []

    def test_graph_edge_defaults(self):
        e = GraphEdge()
        assert e.source_node_id == ""
        assert e.target_node_id == ""

    def test_ontology_class_defaults(self):
        c = OntologyClass()
        assert c.name == ""
        assert c.parent_id is None
        assert c.properties == {}
        assert c.constraints == {}

    def test_entity_type_enum_values(self):
        assert EntityType.PERSON.value == "person"
        assert EntityType.ORGANIZATION.value == "organization"
        assert EntityType.TECHNOLOGY.value == "technology"

    def test_relation_type_enum_values(self):
        assert RelationType.IS_A.value == "is_a"
        assert RelationType.CAUSES.value == "causes"
        assert RelationType.PART_OF.value == "part_of"

    def test_property_type_enum_values(self):
        assert PropertyType.STRING.value == "string"
        assert PropertyType.INTEGER.value == "integer"
        assert PropertyType.FLOAT.value == "float"


# === EntityExtractor Testleri ===


class TestEntityExtraction:
    """Varlik cikarma testleri."""

    def test_extract_named_entities(self):
        ext = EntityExtractor()
        entities = ext.extract("Python ve Django frameworkleri")
        names = [e.name for e in entities]
        assert "Python" in names
        assert "Django" in names

    def test_extract_quoted_entities(self):
        ext = EntityExtractor()
        entities = ext.extract('Bu "onemli kavram" ile ilgili')
        names = [e.name for e in entities]
        assert "onemli kavram" in names

    def test_extract_empty_text(self):
        ext = EntityExtractor()
        entities = ext.extract("")
        assert entities == []

    def test_classify_person(self):
        ext = EntityExtractor()
        entities = ext.extract("Bay Ahmet toplantiya katildi")
        person = [e for e in entities if e.entity_type == EntityType.PERSON]
        assert len(person) >= 1

    def test_classify_organization(self):
        ext = EntityExtractor()
        entities = ext.extract("ABC Ltd sirketinde calisiyor")
        org = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]
        assert len(org) >= 1

    def test_classify_technology(self):
        ext = EntityExtractor()
        entities = ext.extract("Redis bir database server olarak calistirildi")
        tech = [e for e in entities if e.entity_type == EntityType.TECHNOLOGY]
        assert len(tech) >= 1

    def test_entity_confidence(self):
        ext = EntityExtractor()
        entities = ext.extract("Python framework")
        for e in entities:
            assert 0.0 <= e.confidence <= 1.0

    def test_entity_count_property(self):
        ext = EntityExtractor()
        ext.extract("Python kullanilir. Django frameworktur. FastAPI hizlidir.")
        assert ext.entity_count >= 3

    def test_link_entity(self):
        ext = EntityExtractor()
        entities = ext.extract("Python programming and Py language")
        if len(entities) >= 2:
            result = ext.link_entity(entities[0].id, entities[1].id)
            assert result is True

    def test_link_entity_invalid_id(self):
        ext = EntityExtractor()
        result = ext.link_entity("invalid1", "invalid2")
        assert result is False

    def test_resolve_coreference(self):
        ext = EntityExtractor()
        entities = [_make_entity("Python")]
        resolutions = ext.resolve_coreference("Python iyi bir dil. O cok hizli.", entities)
        assert "o" in resolutions
        assert resolutions["o"] == "Python"

    def test_resolve_coreference_empty(self):
        ext = EntityExtractor()
        resolutions = ext.resolve_coreference("Bu bir test", [])
        assert resolutions == {}

    def test_extract_attributes_numeric(self):
        ext = EntityExtractor()
        attrs = ext.extract_attributes("Python 3.11 surumu", "Python")
        assert "numeric_value" in attrs
        assert attrs["numeric_value"] == 3.11

    def test_extract_attributes_not_found(self):
        ext = EntityExtractor()
        attrs = ext.extract_attributes("Django frameworku", "Flask")
        assert attrs == {}

    def test_find_by_name(self):
        ext = EntityExtractor()
        ext.extract("Python programlama dili")
        found = ext.find_by_name("Python")
        assert found is not None
        assert found.name == "Python"

    def test_find_by_name_not_found(self):
        ext = EntityExtractor()
        assert ext.find_by_name("NonExistent") is None

    def test_get_entity(self):
        ext = EntityExtractor()
        entities = ext.extract("Python dili")
        if entities:
            retrieved = ext.get_entity(entities[0].id)
            assert retrieved is not None
            assert retrieved.id == entities[0].id

    def test_entities_property(self):
        ext = EntityExtractor()
        ext.extract("Python kullanilir. Django frameworktur. FastAPI hizlidir.")
        assert len(ext.entities) >= 3


# === RelationExtractor Testleri ===


class TestRelationExtraction:
    """Iliski cikarma testleri."""

    def test_extract_is_a_relation(self):
        ext = RelationExtractor()
        e1 = _make_entity("Django")
        e2 = _make_entity("Framework")
        relations = ext.extract("Django bir Framework turudur", [e1, e2])
        assert len(relations) >= 1

    def test_extract_causes_relation(self):
        ext = RelationExtractor()
        e1 = _make_entity("Bug")
        e2 = _make_entity("Crash")
        relations = ext.extract("Bug causes Crash in system", [e1, e2])
        causes = [r for r in relations if r.relation_type == RelationType.CAUSES]
        assert len(causes) >= 1

    def test_extract_no_entities(self):
        ext = RelationExtractor()
        relations = ext.extract("Bos metin", [])
        assert relations == []

    def test_extract_single_entity(self):
        ext = RelationExtractor()
        relations = ext.extract("Python", [_make_entity("Python")])
        assert relations == []

    def test_relation_strength_scoring(self):
        ext = RelationExtractor()
        rel = _make_relation("a", "b", strength=0.5)
        score = ext.score_relation_strength(rel)
        assert 0.0 <= score <= 1.0

    def test_relation_strength_with_context(self):
        ext = RelationExtractor()
        rel = _make_relation("a", "b", strength=0.5)
        score = ext.score_relation_strength(rel, {"frequency": 5, "explicit": True, "verified": True})
        assert score > 0.5

    def test_create_temporal_relation(self):
        ext = RelationExtractor()
        rel = ext.create_temporal_relation("src", "tgt", RelationType.WORKS_FOR, "2024-01-01T00:00:00+00:00")
        assert rel.temporal is True
        assert rel.start_time is not None

    def test_create_causal_relation(self):
        ext = RelationExtractor()
        rel = ext.create_causal_relation("cause", "effect", 0.8)
        assert rel.relation_type == RelationType.CAUSES
        assert rel.strength == 0.8
        assert rel.attributes.get("causal") is True

    def test_create_bidirectional_relation(self):
        ext = RelationExtractor()
        rel = ext.create_bidirectional_relation("a", "b", strength=0.6)
        assert rel.bidirectional is True
        assert rel.strength == 0.6

    def test_relation_count_property(self):
        ext = RelationExtractor()
        ext.create_causal_relation("a", "b")
        ext.create_causal_relation("c", "d")
        assert ext.relation_count == 2

    def test_relations_property(self):
        ext = RelationExtractor()
        ext.create_causal_relation("a", "b")
        assert len(ext.relations) == 1

    def test_causal_strength_clamped(self):
        ext = RelationExtractor()
        rel = ext.create_causal_relation("a", "b", 1.5)
        assert rel.strength <= 1.0
        rel2 = ext.create_causal_relation("a", "b", -0.5)
        assert rel2.strength >= 0.0


# === GraphBuilder Testleri ===


class TestGraphBuilder:
    """Graf olusturucu testleri."""

    def test_add_node(self):
        builder = GraphBuilder()
        entity = _make_entity("Python", EntityType.TECHNOLOGY)
        node = builder.add_node(entity)
        assert node is not None
        assert node.entity.name == "Python"
        assert builder.node_count == 1

    def test_add_duplicate_node(self):
        builder = GraphBuilder()
        e1 = _make_entity("Python")
        e2 = _make_entity("Python")
        n1 = builder.add_node(e1)
        n2 = builder.add_node(e2)
        assert n1.id == n2.id
        assert builder.node_count == 1

    def test_add_edge(self):
        builder = GraphBuilder()
        n1 = builder.add_node(_make_entity("A"))
        n2 = builder.add_node(_make_entity("B"))
        rel = _make_relation(n1.id, n2.id, RelationType.IS_A)
        edge = builder.add_edge(rel, n1.id, n2.id)
        assert edge is not None
        assert builder.edge_count == 1

    def test_add_edge_invalid_nodes(self):
        builder = GraphBuilder()
        rel = _make_relation("x", "y")
        edge = builder.add_edge(rel, "x", "y")
        assert edge is None

    def test_set_property(self):
        builder = GraphBuilder()
        node = builder.add_node(_make_entity("Python"))
        result = builder.set_property(node.id, "version", "3.11")
        assert result is True
        assert builder.get_node(node.id).entity.attributes["version"] == "3.11"

    def test_set_property_invalid_node(self):
        builder = GraphBuilder()
        assert builder.set_property("invalid", "key", "val") is False

    def test_merge_graphs(self):
        b1 = GraphBuilder()
        b1.add_node(_make_entity("Python"))
        b1.add_node(_make_entity("Django"))

        b2 = GraphBuilder()
        b2.add_node(_make_entity("Flask"))
        b2.add_node(_make_entity("Python"))  # Tekrar

        added = b1.merge_graphs(b2)
        assert added >= 1
        assert b1.node_count == 3  # Python tekrar eklenmemeli

    def test_detect_duplicates(self):
        builder = GraphBuilder()
        e1 = _make_entity("Python", attributes={"type": "lang"})
        e2 = _make_entity("Pythons", attributes={"type": "lang"})
        e2.aliases = ["Python"]  # Alias ile tekrar
        builder.add_node(e1)
        builder.add_node(e2)
        # detect_duplicates _are_similar ile kontrol eder
        duplicates = builder.detect_duplicates()
        assert len(duplicates) >= 1

    def test_merge_nodes(self):
        builder = GraphBuilder()
        n1 = builder.add_node(_make_entity("Python", attributes={"version": "3.11"}))
        n2 = builder.add_node(_make_entity("FastAPI", attributes={"type": "framework"}))
        result = builder.merge_nodes(n1.id, n2.id)
        assert result is True
        assert builder.node_count == 1
        assert "FastAPI" in builder.get_node(n1.id).entity.aliases

    def test_merge_nodes_invalid(self):
        builder = GraphBuilder()
        assert builder.merge_nodes("x", "y") is False

    def test_get_node_by_name(self):
        builder = GraphBuilder()
        builder.add_node(_make_entity("Python"))
        node = builder.get_node_by_name("python")
        assert node is not None
        assert node.entity.name == "Python"

    def test_get_node_by_name_not_found(self):
        builder = GraphBuilder()
        assert builder.get_node_by_name("nonexistent") is None

    def test_nodes_property(self):
        builder, nodes = _build_simple_graph()
        assert len(builder.nodes) == 3

    def test_edges_property(self):
        builder, _ = _build_simple_graph()
        assert len(builder.edges) == 2

    def test_get_edge(self):
        builder, nodes = _build_simple_graph()
        edges = builder.edges
        if edges:
            retrieved = builder.get_edge(edges[0].id)
            assert retrieved is not None


# === GraphStore Testleri ===


class TestGraphStore:
    """Graf deposu testleri."""

    def test_store_and_get_node(self):
        store = GraphStore()
        entity = _make_entity("Python", EntityType.TECHNOLOGY)
        node = GraphNode(entity=entity)
        store.store_node(node)
        retrieved = store.get_node(node.id)
        assert retrieved is not None
        assert retrieved.entity.name == "Python"

    def test_store_and_get_edge(self):
        store = GraphStore()
        rel = _make_relation("s", "t", RelationType.IS_A)
        edge = GraphEdge(relation=rel, source_node_id="s", target_node_id="t")
        store.store_edge(edge)
        retrieved = store.get_edge(edge.id)
        assert retrieved is not None

    def test_get_nodes_by_type(self):
        store = GraphStore()
        e1 = _make_entity("Python", EntityType.TECHNOLOGY)
        e2 = _make_entity("Django", EntityType.TECHNOLOGY)
        e3 = _make_entity("Istanbul", EntityType.LOCATION)
        store.store_node(GraphNode(entity=e1))
        store.store_node(GraphNode(entity=e2))
        store.store_node(GraphNode(entity=e3))
        tech_nodes = store.get_nodes_by_type("technology")
        assert len(tech_nodes) == 2

    def test_get_edges_by_type(self):
        store = GraphStore()
        r1 = _make_relation("a", "b", RelationType.IS_A)
        r2 = _make_relation("c", "d", RelationType.CAUSES)
        r3 = _make_relation("e", "f", RelationType.IS_A)
        store.store_edge(GraphEdge(relation=r1, source_node_id="a", target_node_id="b"))
        store.store_edge(GraphEdge(relation=r2, source_node_id="c", target_node_id="d"))
        store.store_edge(GraphEdge(relation=r3, source_node_id="e", target_node_id="f"))
        is_a_edges = store.get_edges_by_type("is_a")
        assert len(is_a_edges) == 2

    def test_get_neighbors(self):
        store = GraphStore()
        e1 = _make_entity("A")
        e2 = _make_entity("B")
        n1 = GraphNode(entity=e1)
        n2 = GraphNode(entity=e2)
        rel = _make_relation(n1.id, n2.id)
        edge = GraphEdge(relation=rel, source_node_id=n1.id, target_node_id=n2.id)
        n1.out_edges.append(edge.id)
        n2.in_edges.append(edge.id)
        store.store_node(n1)
        store.store_node(n2)
        store.store_edge(edge)
        neighbors = store.get_neighbors(n1.id)
        assert n2.id in neighbors

    def test_get_neighbors_not_found(self):
        store = GraphStore()
        assert store.get_neighbors("nonexistent") == []

    def test_remove_node(self):
        store = GraphStore()
        entity = _make_entity("Python", EntityType.TECHNOLOGY)
        node = GraphNode(entity=entity)
        store.store_node(node)
        assert store.remove_node(node.id) is True
        assert store.get_node(node.id) is None
        assert store.node_count == 0

    def test_remove_node_not_found(self):
        store = GraphStore()
        assert store.remove_node("nonexistent") is False

    def test_remove_edge(self):
        store = GraphStore()
        rel = _make_relation("s", "t")
        edge = GraphEdge(relation=rel, source_node_id="s", target_node_id="t")
        store.store_edge(edge)
        assert store.remove_edge(edge.id) is True
        assert store.get_edge(edge.id) is None

    def test_remove_edge_not_found(self):
        store = GraphStore()
        assert store.remove_edge("nonexistent") is False

    def test_create_version(self):
        store = GraphStore()
        store.store_node(GraphNode(entity=_make_entity("A")))
        v1 = store.create_version("initial")
        assert v1 == 1
        v2 = store.create_version("update")
        assert v2 == 2
        assert store.version == 2

    def test_versions_property(self):
        store = GraphStore()
        store.create_version("v1")
        store.create_version("v2")
        assert len(store.versions) == 2
        assert store.versions[0]["label"] == "v1"

    def test_export_json(self):
        store = GraphStore()
        entity = _make_entity("Python", EntityType.TECHNOLOGY)
        node = GraphNode(entity=entity)
        store.store_node(node)
        json_str = store.export_json()
        data = json.loads(json_str)
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "Python"

    def test_import_json(self):
        store = GraphStore()
        data = {
            "nodes": [{"id": "n1", "name": "Python", "type": "technology", "attributes": {}}],
            "edges": [],
        }
        count = store.import_json(json.dumps(data))
        assert count == 1
        assert store.node_count == 1

    def test_export_import_roundtrip(self):
        store1 = GraphStore()
        entity = _make_entity("Test", EntityType.CONCEPT)
        node = GraphNode(entity=entity)
        store1.store_node(node)
        json_str = store1.export_json()

        store2 = GraphStore()
        store2.import_json(json_str)
        assert store2.node_count == 1

    def test_get_stats(self):
        store = GraphStore()
        store.store_node(GraphNode(entity=_make_entity("A", EntityType.CONCEPT)))
        store.store_node(GraphNode(entity=_make_entity("B", EntityType.TECHNOLOGY)))
        stats = store.get_stats()
        assert stats.node_count == 2
        assert "concept" in stats.entity_type_counts
        assert "technology" in stats.entity_type_counts

    def test_node_edge_count_properties(self):
        store = GraphStore()
        assert store.node_count == 0
        assert store.edge_count == 0
        store.store_node(GraphNode(entity=_make_entity("A")))
        assert store.node_count == 1

    def test_stats_density(self):
        store = GraphStore()
        e1 = _make_entity("A")
        e2 = _make_entity("B")
        n1 = GraphNode(entity=e1)
        n2 = GraphNode(entity=e2)
        store.store_node(n1)
        store.store_node(n2)
        rel = _make_relation(n1.id, n2.id)
        edge = GraphEdge(relation=rel, source_node_id=n1.id, target_node_id=n2.id)
        store.store_edge(edge)
        stats = store.get_stats()
        assert stats.density > 0


# === QueryEngine Testleri ===


class TestQueryEngine:
    """Sorgulama motoru testleri."""

    def _setup_query_engine(self):
        builder, nodes = _build_simple_graph()
        node_map = {n.id: n for n in builder.nodes}
        edge_map = {e.id: e for e in builder.edges}
        qe = QueryEngine(nodes=node_map, edges=edge_map)
        return qe, nodes

    def test_find_path_direct(self):
        qe, nodes = self._setup_query_engine()
        result = qe.find_path(nodes[0].id, nodes[1].id)
        assert result.query_type == QueryType.PATH_FIND
        assert result.result_count == 1
        assert len(result.paths) == 1

    def test_find_path_two_hops(self):
        qe, nodes = self._setup_query_engine()
        result = qe.find_path(nodes[0].id, nodes[2].id)
        assert result.result_count == 1
        assert len(result.paths[0]) == 3

    def test_find_path_same_node(self):
        qe, nodes = self._setup_query_engine()
        result = qe.find_path(nodes[0].id, nodes[0].id)
        assert result.result_count == 1
        assert result.paths == [[nodes[0].id]]

    def test_find_path_not_found(self):
        qe = QueryEngine()
        result = qe.find_path("nonexistent_a", "nonexistent_b")
        assert result.result_count == 0

    def test_find_path_no_route(self):
        builder = GraphBuilder()
        n1 = builder.add_node(_make_entity("Isolated1"))
        n2 = builder.add_node(_make_entity("Isolated2"))
        node_map = {n.id: n for n in builder.nodes}
        qe = QueryEngine(nodes=node_map, edges={})
        result = qe.find_path(n1.id, n2.id)
        assert result.result_count == 0

    def test_extract_subgraph(self):
        qe, nodes = self._setup_query_engine()
        result = qe.extract_subgraph(nodes[0].id, depth=2)
        assert result.query_type == QueryType.SUBGRAPH
        assert result.result_count >= 1
        assert nodes[0].id in result.nodes

    def test_extract_subgraph_not_found(self):
        qe = QueryEngine()
        result = qe.extract_subgraph("nonexistent")
        assert result.result_count == 0

    def test_match_pattern_entity_type(self):
        qe, _ = self._setup_query_engine()
        result = qe.match_pattern(entity_type="technology")
        assert result.query_type == QueryType.PATTERN
        assert len(result.nodes) >= 2

    def test_match_pattern_relation_type(self):
        qe, _ = self._setup_query_engine()
        result = qe.match_pattern(relation_type="has_a")
        assert len(result.edges) >= 1

    def test_aggregate_entity_type(self):
        qe, _ = self._setup_query_engine()
        result = qe.aggregate(group_by="entity_type")
        assert result.query_type == QueryType.AGGREGATION
        assert "entity_type_counts" in result.aggregations
        assert result.aggregations["total_nodes"] == 3

    def test_aggregate_relation_type(self):
        qe, _ = self._setup_query_engine()
        result = qe.aggregate(group_by="relation_type")
        assert "relation_type_counts" in result.aggregations
        assert result.aggregations["total_edges"] == 2

    def test_natural_language_query(self):
        qe, _ = self._setup_query_engine()
        result = qe.natural_language_query("Python programlama")
        assert result.query_type == QueryType.NATURAL_LANGUAGE
        assert len(result.nodes) >= 1

    def test_results_property(self):
        qe, nodes = self._setup_query_engine()
        qe.find_path(nodes[0].id, nodes[1].id)
        qe.aggregate()
        assert qe.result_count == 2
        assert len(qe.results) == 2

    def test_execution_time_tracked(self):
        qe, nodes = self._setup_query_engine()
        result = qe.find_path(nodes[0].id, nodes[1].id)
        assert result.execution_time_ms >= 0

    def test_set_data(self):
        qe = QueryEngine()
        builder, nodes = _build_simple_graph()
        node_map = {n.id: n for n in builder.nodes}
        edge_map = {e.id: e for e in builder.edges}
        qe.set_data(node_map, edge_map)
        result = qe.aggregate()
        assert result.aggregations["total_nodes"] == 3


# === InferenceEngine Testleri ===


class TestInferenceEngine:
    """Cikarim motoru testleri."""

    def _setup_inference_engine(self):
        builder, nodes = _build_inference_graph()
        node_map = {n.id: n for n in builder.nodes}
        edge_map = {e.id: e for e in builder.edges}
        ie = InferenceEngine(max_depth=5)
        ie.set_data(node_map, edge_map)
        return ie, nodes

    def test_infer_transitive(self):
        ie, nodes = self._setup_inference_engine()
        facts = ie.infer_transitive()
        # Labrador IS_A Dog, Dog IS_A Animal -> Labrador IS_A Animal
        assert len(facts) >= 1
        assert any(f.inference_type == InferenceType.TRANSITIVE for f in facts)

    def test_infer_inheritance(self):
        ie, nodes = self._setup_inference_engine()
        facts = ie.infer_inheritance()
        # Dog IS_A Animal (Animal has legs=4) -> Dog should inherit legs
        inherited = [f for f in facts if f.inference_type == InferenceType.INHERITANCE]
        assert len(inherited) >= 1

    def test_infer_inverse(self):
        ie, nodes = self._setup_inference_engine()
        facts = ie.infer_inverse()
        # IS_A -> inverse HAS_A
        assert len(facts) >= 1
        assert any(f.inference_type == InferenceType.INVERSE for f in facts)

    def test_apply_rules(self):
        ie, nodes = self._setup_inference_engine()
        ie.add_rule(
            "strong_is_a",
            {"relation_type": "is_a"},
            {"predicate": "strongly_typed", "confidence": 0.7},
        )
        facts = ie.apply_rules()
        assert len(facts) >= 1
        assert any(f.rule_name == "strong_is_a" for f in facts)

    def test_apply_rules_with_min_strength(self):
        ie, nodes = self._setup_inference_engine()
        ie.add_rule(
            "high_strength",
            {"relation_type": "is_a", "min_strength": 0.9},
            {"predicate": "verified", "confidence": 0.9},
        )
        facts = ie.apply_rules()
        # Default strength is 1.0 so should match
        assert len(facts) >= 1

    def test_detect_contradictions_none(self):
        ie, _ = self._setup_inference_engine()
        contradictions = ie.detect_contradictions()
        assert len(contradictions) == 0

    def test_detect_contradictions_found(self):
        builder = GraphBuilder()
        n1 = builder.add_node(_make_entity("A"))
        n2 = builder.add_node(_make_entity("B"))
        r1 = _make_relation(n1.id, n2.id, RelationType.IS_A)
        r2 = _make_relation(n1.id, n2.id, RelationType.PART_OF)
        builder.add_edge(r1, n1.id, n2.id)
        builder.add_edge(r2, n1.id, n2.id)
        ie = InferenceEngine()
        ie.set_data(
            {n.id: n for n in builder.nodes},
            {e.id: e for e in builder.edges},
        )
        contradictions = ie.detect_contradictions()
        assert len(contradictions) >= 1

    def test_run_all(self):
        ie, _ = self._setup_inference_engine()
        ie.add_rule("test_rule", {"relation_type": "is_a"}, {"predicate": "derived"})
        all_facts = ie.run_all()
        assert len(all_facts) > 0

    def test_facts_property(self):
        ie, _ = self._setup_inference_engine()
        ie.infer_transitive()
        assert len(ie.facts) >= 1

    def test_fact_count_property(self):
        ie, _ = self._setup_inference_engine()
        ie.infer_inverse()
        assert ie.fact_count >= 1

    def test_rule_count_property(self):
        ie = InferenceEngine()
        ie.add_rule("r1", {}, {})
        ie.add_rule("r2", {}, {})
        assert ie.rule_count == 2

    def test_transitive_no_self_loop(self):
        ie, nodes = self._setup_inference_engine()
        facts = ie.infer_transitive()
        for f in facts:
            assert f.subject != f.obj


# === KnowledgeFusion Testleri ===


class TestKnowledgeFusion:
    """Bilgi birlestirme testleri."""

    def test_merge_entities_no_conflict(self):
        fusion = KnowledgeFusion()
        e1 = [_make_entity("Python")]
        e2 = [_make_entity("Django")]
        merged, conflicts = fusion.merge_entities(e1, e2)
        assert len(merged) == 2
        assert conflicts == 0

    def test_merge_entities_with_conflict(self):
        fusion = KnowledgeFusion()
        e1 = [_make_entity("Python", confidence=0.8)]
        e2 = [_make_entity("Python", confidence=0.9)]
        merged, conflicts = fusion.merge_entities(e1, e2)
        assert len(merged) == 1
        assert conflicts == 1

    def test_conflict_keep_first(self):
        fusion = KnowledgeFusion(conflict_resolution=ConflictResolution.KEEP_FIRST)
        e1 = [_make_entity("Python", attributes={"v": "3.10"})]
        e2 = [_make_entity("Python", attributes={"v": "3.11"})]
        merged, _ = fusion.merge_entities(e1, e2)
        assert merged[0].attributes.get("v") == "3.10"

    def test_conflict_keep_latest(self):
        fusion = KnowledgeFusion(conflict_resolution=ConflictResolution.KEEP_LATEST)
        e1 = [_make_entity("Python", attributes={"v": "3.10"})]
        e2 = [_make_entity("Python", attributes={"v": "3.11"})]
        merged, _ = fusion.merge_entities(e1, e2)
        assert merged[0].attributes.get("v") == "3.11"

    def test_conflict_keep_trusted(self):
        fusion = KnowledgeFusion(conflict_resolution=ConflictResolution.KEEP_TRUSTED)
        fusion.set_source_trust("official", 0.9)
        fusion.set_source_trust("blog", 0.3)
        e1 = [_make_entity("Python", attributes={"v": "3.10"})]
        e2 = [_make_entity("Python", attributes={"v": "3.11"})]
        merged, _ = fusion.merge_entities(e1, e2, "official", "blog")
        assert merged[0].attributes.get("v") == "3.10"

    def test_conflict_merge(self):
        fusion = KnowledgeFusion(conflict_resolution=ConflictResolution.MERGE)
        e1 = [_make_entity("Python", attributes={"a": 1})]
        e2 = [_make_entity("Python", attributes={"b": 2})]
        merged, _ = fusion.merge_entities(e1, e2)
        assert "a" in merged[0].attributes
        assert "b" in merged[0].attributes

    def test_conflict_flag(self):
        fusion = KnowledgeFusion(conflict_resolution=ConflictResolution.FLAG)
        e1 = [_make_entity("Python")]
        e2 = [_make_entity("Python")]
        merged, _ = fusion.merge_entities(e1, e2, "s1", "s2")
        assert merged[0].attributes.get("_conflict") is True

    def test_merge_relations(self):
        fusion = KnowledgeFusion()
        r1 = [_make_relation("a", "b", RelationType.IS_A, strength=0.6)]
        r2 = [_make_relation("c", "d", RelationType.CAUSES, strength=0.8)]
        merged, conflicts = fusion.merge_relations(r1, r2)
        assert len(merged) == 2
        assert conflicts == 0

    def test_merge_relations_conflict(self):
        fusion = KnowledgeFusion()
        r1 = [_make_relation("a", "b", RelationType.IS_A, strength=0.6)]
        r2 = [_make_relation("a", "b", RelationType.IS_A, strength=0.8)]
        merged, conflicts = fusion.merge_relations(r1, r2)
        assert len(merged) == 1
        assert conflicts == 1
        assert merged[0].strength == pytest.approx(0.7, abs=0.01)

    def test_calculate_trust_score_default(self):
        fusion = KnowledgeFusion()
        score = fusion.calculate_trust_score("unknown")
        assert score == 0.5

    def test_calculate_trust_score_with_history(self):
        fusion = KnowledgeFusion()
        fusion.set_source_trust("source", 0.8)
        history = [{"correct": True}, {"correct": True}, {"correct": False}]
        score = fusion.calculate_trust_score("source", history)
        assert 0.0 <= score <= 1.0

    def test_set_source_trust_clamped(self):
        fusion = KnowledgeFusion()
        fusion.set_source_trust("a", 1.5)
        assert fusion.calculate_trust_score("a") == 1.0
        fusion.set_source_trust("b", -0.5)
        assert fusion.calculate_trust_score("b") == 0.0

    def test_assess_quality_empty(self):
        fusion = KnowledgeFusion()
        quality = fusion.assess_quality([], [])
        assert quality == QualityLevel.UNVERIFIED

    def test_assess_quality_high(self):
        fusion = KnowledgeFusion()
        entities = [
            _make_entity("A", confidence=0.9, source="s1"),
            _make_entity("B", confidence=0.85, source="s2"),
            _make_entity("C", confidence=0.88, source="s3"),
        ]
        quality = fusion.assess_quality(entities, [_make_relation("a", "b")])
        assert quality in (QualityLevel.VERIFIED, QualityLevel.HIGH)

    def test_assess_quality_low(self):
        fusion = KnowledgeFusion()
        entities = [_make_entity("A", confidence=0.2)]
        quality = fusion.assess_quality(entities, [])
        assert quality in (QualityLevel.LOW, QualityLevel.UNVERIFIED)

    def test_fuse_full(self):
        fusion = KnowledgeFusion()
        e1 = [_make_entity("Python")]
        r1 = [_make_relation("a", "b")]
        e2 = [_make_entity("Django")]
        r2 = [_make_relation("c", "d")]
        result = fusion.fuse(e1, r1, e2, r2)
        assert result.entities_merged == 2
        assert result.relations_merged == 2

    def test_fusion_history(self):
        fusion = KnowledgeFusion()
        fusion.fuse([_make_entity("A")], [], [_make_entity("B")], [])
        fusion.fuse([_make_entity("C")], [], [_make_entity("D")], [])
        assert fusion.fusion_count == 2
        assert len(fusion.fusion_history) == 2

    def test_fuse_with_conflicts(self):
        fusion = KnowledgeFusion()
        e1 = [_make_entity("Python")]
        e2 = [_make_entity("Python")]
        result = fusion.fuse(e1, [], e2, [])
        assert result.conflicts_found >= 1


# === OntologyManager Testleri ===


class TestOntologyManager:
    """Ontoloji yoneticisi testleri."""

    def test_define_class(self):
        om = OntologyManager()
        cls = om.define_class("Entity")
        assert cls.name == "Entity"
        assert om.class_count == 1

    def test_define_class_with_parent(self):
        om = OntologyManager()
        om.define_class("Thing")
        child = om.define_class("Person", parent_name="Thing")
        assert child.parent_id is not None

    def test_define_class_with_properties(self):
        om = OntologyManager()
        cls = om.define_class("Person", properties={"name": PropertyType.STRING, "age": PropertyType.INTEGER})
        assert "name" in cls.properties
        assert cls.properties["name"] == PropertyType.STRING

    def test_get_class(self):
        om = OntologyManager()
        om.define_class("Entity")
        cls = om.get_class("entity")
        assert cls is not None
        assert cls.name == "Entity"

    def test_get_class_not_found(self):
        om = OntologyManager()
        assert om.get_class("nonexistent") is None

    def test_get_class_by_id(self):
        om = OntologyManager()
        cls = om.define_class("Entity")
        retrieved = om.get_class_by_id(cls.id)
        assert retrieved is not None
        assert retrieved.name == "Entity"

    def test_get_hierarchy(self):
        om = OntologyManager()
        om.define_class("Thing")
        om.define_class("LivingThing", parent_name="Thing")
        om.define_class("Animal", parent_name="LivingThing")
        hierarchy = om.get_hierarchy("Animal")
        assert hierarchy == ["Thing", "LivingThing", "Animal"]

    def test_get_hierarchy_root(self):
        om = OntologyManager()
        om.define_class("Root")
        hierarchy = om.get_hierarchy("Root")
        assert hierarchy == ["Root"]

    def test_get_children(self):
        om = OntologyManager()
        om.define_class("Parent")
        om.define_class("Child1", parent_name="Parent")
        om.define_class("Child2", parent_name="Parent")
        children = om.get_children("Parent")
        assert len(children) == 2
        names = [c.name for c in children]
        assert "Child1" in names
        assert "Child2" in names

    def test_get_children_no_parent(self):
        om = OntologyManager()
        assert om.get_children("nonexistent") == []

    def test_add_property(self):
        om = OntologyManager()
        om.define_class("Entity")
        result = om.add_property("Entity", "color", PropertyType.STRING)
        assert result is True
        cls = om.get_class("Entity")
        assert "color" in cls.properties

    def test_add_property_invalid_class(self):
        om = OntologyManager()
        assert om.add_property("nonexistent", "key", PropertyType.STRING) is False

    def test_add_constraint(self):
        om = OntologyManager()
        om.define_class("Product")
        result = om.add_constraint("Product", "min_price", 0)
        assert result is True

    def test_add_constraint_invalid_class(self):
        om = OntologyManager()
        assert om.add_constraint("nonexistent", "key", "val") is False

    def test_get_all_properties_with_inheritance(self):
        om = OntologyManager()
        om.define_class("Thing", properties={"id": PropertyType.STRING})
        om.define_class("Person", parent_name="Thing", properties={"name": PropertyType.STRING, "age": PropertyType.INTEGER})
        all_props = om.get_all_properties("Person")
        assert "id" in all_props
        assert "name" in all_props
        assert "age" in all_props

    def test_validate_entity_no_rules(self):
        om = OntologyManager()
        errors = om.validate_entity("person", {"name": "Test"})
        assert errors == []

    def test_validate_entity_required_missing(self):
        om = OntologyManager()
        om.add_validation_rule({
            "entity_type": "person",
            "required_properties": ["name", "age"],
        })
        errors = om.validate_entity("person", {"name": "Test"})
        assert len(errors) == 1
        assert "age" in errors[0]

    def test_validate_entity_type_check(self):
        om = OntologyManager()
        om.add_validation_rule({
            "entity_type": "product",
            "type_checks": {"price": "float"},
        })
        errors = om.validate_entity("product", {"price": "not_a_number"})
        assert len(errors) >= 1

    def test_validate_entity_range_check(self):
        om = OntologyManager()
        om.add_validation_rule({
            "entity_type": "metric",
            "ranges": {"score": (0, 100)},
        })
        errors = om.validate_entity("metric", {"score": 150})
        assert len(errors) >= 1

    def test_validate_entity_wrong_type_skips(self):
        om = OntologyManager()
        om.add_validation_rule({
            "entity_type": "person",
            "required_properties": ["name"],
        })
        errors = om.validate_entity("product", {})
        assert errors == []

    def test_map_entity_type(self):
        om = OntologyManager()
        om.define_class("PersonClass")
        result = om.map_entity_type(EntityType.PERSON, "PersonClass")
        assert result is True

    def test_map_entity_type_invalid(self):
        om = OntologyManager()
        result = om.map_entity_type(EntityType.PERSON, "nonexistent")
        assert result is False

    def test_evolve_schema_add_class(self):
        om = OntologyManager()
        applied = om.evolve_schema([{"action": "add_class", "target": "NewClass", "description": "New"}])
        assert applied == 1
        assert om.class_count == 1

    def test_evolve_schema_add_property(self):
        om = OntologyManager()
        om.define_class("Entity")
        applied = om.evolve_schema([{
            "action": "add_property",
            "target": "Entity",
            "property": "color",
            "type": "string",
        }])
        assert applied == 1
        cls = om.get_class("Entity")
        assert "color" in cls.properties

    def test_evolve_schema_remove_property(self):
        om = OntologyManager()
        om.define_class("Entity", properties={"color": PropertyType.STRING})
        applied = om.evolve_schema([{
            "action": "remove_property",
            "target": "Entity",
            "property": "color",
        }])
        assert applied == 1
        cls = om.get_class("Entity")
        assert "color" not in cls.properties

    def test_evolve_schema_rename_class(self):
        om = OntologyManager()
        om.define_class("OldName")
        applied = om.evolve_schema([{
            "action": "rename_class",
            "target": "OldName",
            "new_name": "NewName",
        }])
        assert applied == 1
        assert om.get_class("NewName") is not None
        assert om.get_class("OldName") is None

    def test_evolve_schema_version_incremented(self):
        om = OntologyManager()
        assert om.version == 0
        om.evolve_schema([{"action": "add_class", "target": "A"}])
        assert om.version == 1

    def test_export_schema(self):
        om = OntologyManager()
        om.define_class("Entity", properties={"name": PropertyType.STRING})
        schema = om.export_schema()
        assert "classes" in schema
        assert len(schema["classes"]) == 1
        assert schema["classes"][0]["name"] == "Entity"

    def test_classes_property(self):
        om = OntologyManager()
        om.define_class("A")
        om.define_class("B")
        assert len(om.classes) == 2


# === KnowledgeGraphManager Testleri ===


class TestKnowledgeGraphManager:
    """Bilgi grafi orkestratoru testleri."""

    def test_init_defaults(self):
        kgm = KnowledgeGraphManager()
        assert kgm.node_count == 0
        assert kgm.edge_count == 0

    def test_process_text(self):
        kgm = KnowledgeGraphManager()
        result = kgm.process_text("Python ve Django frameworkleri", source="test")
        assert result["entities"] >= 2
        assert result["source"] == "test"

    def test_process_text_multiple(self):
        kgm = KnowledgeGraphManager()
        kgm.process_text("Python programlama dili")
        kgm.process_text("Django web framework")
        assert kgm.node_count >= 2

    def test_add_entity(self):
        kgm = KnowledgeGraphManager()
        entity = _make_entity("TestEntity", EntityType.CONCEPT)
        node_id = kgm.add_entity(entity)
        assert node_id is not None
        assert kgm.node_count == 1

    def test_add_relation(self):
        kgm = KnowledgeGraphManager()
        e1 = _make_entity("A")
        e2 = _make_entity("B")
        n1_id = kgm.add_entity(e1)
        n2_id = kgm.add_entity(e2)
        rel = _make_relation(n1_id, n2_id, RelationType.IS_A)
        edge_id = kgm.add_relation(rel, n1_id, n2_id)
        assert edge_id is not None
        assert kgm.edge_count == 1

    def test_add_relation_invalid_nodes(self):
        kgm = KnowledgeGraphManager()
        rel = _make_relation("x", "y")
        edge_id = kgm.add_relation(rel, "x", "y")
        assert edge_id is None

    def test_query(self):
        kgm = KnowledgeGraphManager()
        kgm.process_text("Python framework Django")
        result = kgm.query("Python")
        assert result.query_type == QueryType.NATURAL_LANGUAGE

    def test_find_path(self):
        kgm = KnowledgeGraphManager()
        e1 = _make_entity("Start")
        e2 = _make_entity("End")
        n1_id = kgm.add_entity(e1)
        n2_id = kgm.add_entity(e2)
        rel = _make_relation(n1_id, n2_id)
        kgm.add_relation(rel, n1_id, n2_id)
        result = kgm.find_path(n1_id, n2_id)
        assert result.result_count == 1

    def test_extract_subgraph(self):
        kgm = KnowledgeGraphManager()
        e1 = _make_entity("Center")
        n1_id = kgm.add_entity(e1)
        result = kgm.extract_subgraph(n1_id)
        assert result.result_count >= 1

    def test_run_inference(self):
        kgm = KnowledgeGraphManager()
        e1 = _make_entity("Animal", attributes={"legs": 4})
        e2 = _make_entity("Dog")
        n1 = kgm.add_entity(e1)
        n2 = kgm.add_entity(e2)
        rel = _make_relation(n2, n1, RelationType.IS_A)
        kgm.add_relation(rel, n2, n1)
        facts = kgm.run_inference()
        assert len(facts) >= 1

    def test_fuse_sources(self):
        kgm = KnowledgeGraphManager()
        result = kgm.fuse_sources(
            "Python programming language",
            "Django web framework",
            "wiki", "docs",
        )
        assert result.entities_merged >= 2

    def test_get_stats(self):
        kgm = KnowledgeGraphManager()
        kgm.add_entity(_make_entity("A", EntityType.CONCEPT))
        kgm.add_entity(_make_entity("B", EntityType.TECHNOLOGY))
        stats = kgm.get_stats()
        assert stats.node_count == 2

    def test_get_analytics(self):
        kgm = KnowledgeGraphManager()
        kgm.process_text("Python Django FastAPI")
        analytics = kgm.get_analytics()
        assert "node_count" in analytics
        assert "processing_count" in analytics
        assert analytics["processing_count"] == 1

    def test_export_import_json(self):
        kgm = KnowledgeGraphManager()
        kgm.add_entity(_make_entity("Python", EntityType.TECHNOLOGY))
        json_str = kgm.export_json()

        kgm2 = KnowledgeGraphManager()
        count = kgm2.import_json(json_str)
        assert count >= 1

    def test_create_version(self):
        kgm = KnowledgeGraphManager()
        kgm.add_entity(_make_entity("A"))
        v = kgm.create_version("v1")
        assert v == 1

    def test_component_accessors(self):
        kgm = KnowledgeGraphManager()
        assert kgm.entity_extractor is not None
        assert kgm.relation_extractor is not None
        assert kgm.graph_builder is not None
        assert kgm.graph_store is not None
        assert kgm.query_engine is not None
        assert kgm.inference_engine is not None
        assert kgm.fusion is not None
        assert kgm.ontology is not None

    def test_custom_parameters(self):
        kgm = KnowledgeGraphManager(
            max_nodes=5000,
            inference_depth=3,
            fusion_strategy=FusionStrategy.MAJORITY_VOTE,
        )
        assert kgm._max_nodes == 5000


# === Entegrasyon Testleri ===


class TestKnowledgeIntegration:
    """End-to-end entegrasyon testleri."""

    def test_full_pipeline(self):
        """Metin -> varlik -> graf -> sorgu -> cikarim."""
        kgm = KnowledgeGraphManager()
        kgm.process_text("Python is a programming language. Django uses Python.")
        stats = kgm.get_stats()
        assert stats.node_count >= 2

    def test_multi_source_fusion(self):
        """Coklu kaynak birlestirme."""
        kgm = KnowledgeGraphManager()
        kgm.fusion.set_source_trust("wiki", 0.9)
        kgm.fusion.set_source_trust("blog", 0.5)
        result = kgm.fuse_sources(
            "Python programming",
            "Python scripting",
            "wiki", "blog",
        )
        assert result.provenance == ["wiki", "blog"]

    def test_ontology_driven_validation(self):
        """Ontoloji tabanli dogrulama."""
        kgm = KnowledgeGraphManager()
        kgm.ontology.define_class("Product", properties={"price": PropertyType.FLOAT})
        kgm.ontology.add_validation_rule({
            "entity_type": "product",
            "required_properties": ["price"],
        })
        errors = kgm.ontology.validate_entity("product", {"name": "Test"})
        assert len(errors) >= 1

    def test_graph_versioning(self):
        """Graf versiyonlama."""
        kgm = KnowledgeGraphManager()
        kgm.add_entity(_make_entity("V1Entity"))
        v1 = kgm.create_version("v1")
        kgm.add_entity(_make_entity("V2Entity"))
        v2 = kgm.create_version("v2")
        assert v2 > v1
        assert kgm.graph_store.version == 2

    def test_inference_after_processing(self):
        """Isleme sonrasi cikarim."""
        kgm = KnowledgeGraphManager()
        # Manuel graf olustur (cikarim icin)
        e1 = _make_entity("Animal", attributes={"alive": True})
        e2 = _make_entity("Cat")
        n1 = kgm.add_entity(e1)
        n2 = kgm.add_entity(e2)
        rel = _make_relation(n2, n1, RelationType.IS_A)
        kgm.add_relation(rel, n2, n1)
        facts = kgm.run_inference()
        # En az miras ve ters iliski cikarimi olmali
        assert len(facts) >= 1
