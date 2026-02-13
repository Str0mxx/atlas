"""ATLAS Cikarim Motoru modulu.

Kural tabanli cikarim, gecisken kapanma, miras
muhakemesi, celiskiler tespiti ve yeni bilgi turetme.
"""

import logging
from typing import Any

from app.models.knowledge import (
    GraphEdge,
    GraphNode,
    InferenceType,
    InferredFact,
    RelationType,
)

logger = logging.getLogger(__name__)

# Gecisken iliski tipleri (A->B, B->C ise A->C)
_TRANSITIVE_RELATIONS = {RelationType.IS_A, RelationType.PART_OF, RelationType.LOCATED_IN}

# Ters iliski haritasi
_INVERSE_RELATIONS: dict[RelationType, RelationType] = {
    RelationType.IS_A: RelationType.HAS_A,
    RelationType.HAS_A: RelationType.IS_A,
    RelationType.PART_OF: RelationType.HAS_A,
    RelationType.CAUSES: RelationType.DEPENDS_ON,
    RelationType.PRODUCES: RelationType.USES,
}


class InferenceEngine:
    """Cikarim motoru.

    Mevcut bilgilerden yeni bilgiler turetir:
    gecisken kapanma, miras, ters iliski ve kural
    tabanli cikarimlar.

    Attributes:
        _nodes: Dugum referansi.
        _edges: Kenar referansi.
        _rules: Kural seti.
        _facts: Cikarilmis bilgiler.
        _max_depth: Maksimum cikarim derinligi.
    """

    def __init__(self, max_depth: int = 5) -> None:
        """Cikarim motorunu baslatir.

        Args:
            max_depth: Maksimum cikarim derinligi.
        """
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._rules: list[dict[str, Any]] = []
        self._facts: list[InferredFact] = []
        self._max_depth = max_depth

        logger.info("InferenceEngine baslatildi (max_depth=%d)", max_depth)

    def set_data(self, nodes: dict[str, GraphNode], edges: dict[str, GraphEdge]) -> None:
        """Graf verisini ayarlar."""
        self._nodes = nodes
        self._edges = edges

    def add_rule(self, name: str, condition: dict[str, Any], conclusion: dict[str, Any]) -> None:
        """Cikarim kurali ekler.

        Args:
            name: Kural adi.
            condition: Kosul (relation_type, source_type, vb).
            conclusion: Sonuc (new_relation, new_attribute, vb).
        """
        self._rules.append({"name": name, "condition": condition, "conclusion": conclusion})
        logger.info("Kural eklendi: %s", name)

    def infer_transitive(self) -> list[InferredFact]:
        """Gecisken kapanma cikarimi yapar.

        A->B ve B->C ise A->C cikarir (gecisken iliskiler icin).

        Returns:
            Cikarilmis bilgi listesi.
        """
        new_facts: list[InferredFact] = []

        # Tum gecisken kenarlari topla
        transitive_edges: dict[str, list[tuple[str, str]]] = {}
        for edge in self._edges.values():
            if edge.relation.relation_type in _TRANSITIVE_RELATIONS:
                rtype = edge.relation.relation_type.value
                if rtype not in transitive_edges:
                    transitive_edges[rtype] = []
                transitive_edges[rtype].append((edge.source_node_id, edge.target_node_id))

        for rtype, pairs in transitive_edges.items():
            # A->B haritasi
            forward: dict[str, list[str]] = {}
            for src, tgt in pairs:
                if src not in forward:
                    forward[src] = []
                forward[src].append(tgt)

            # Gecisken kapanma
            existing_pairs = set(pairs)
            for a, bs in forward.items():
                for b in bs:
                    for c in forward.get(b, []):
                        if (a, c) not in existing_pairs and a != c:
                            fact = InferredFact(
                                inference_type=InferenceType.TRANSITIVE,
                                subject=a,
                                predicate=rtype,
                                obj=c,
                                confidence=0.7,
                                evidence=[f"{a}->{b}", f"{b}->{c}"],
                            )
                            new_facts.append(fact)
                            self._facts.append(fact)

        logger.info("Gecisken cikarim: %d yeni bilgi", len(new_facts))
        return new_facts

    def infer_inheritance(self) -> list[InferredFact]:
        """Miras muhakemesi yapar.

        IS_A iliskisi uzerinden ozellik mirasi cikarir.

        Returns:
            Cikarilmis bilgi listesi.
        """
        new_facts: list[InferredFact] = []

        # IS_A iliskilerini bul
        is_a_map: dict[str, str] = {}
        for edge in self._edges.values():
            if edge.relation.relation_type == RelationType.IS_A:
                is_a_map[edge.source_node_id] = edge.target_node_id

        # Ust sinif ozelliklerini miras al
        for child_id, parent_id in is_a_map.items():
            child = self._nodes.get(child_id)
            parent = self._nodes.get(parent_id)
            if not child or not parent:
                continue

            for key, value in parent.entity.attributes.items():
                if key not in child.entity.attributes:
                    fact = InferredFact(
                        inference_type=InferenceType.INHERITANCE,
                        subject=child_id,
                        predicate=f"inherited_{key}",
                        obj=str(value),
                        confidence=0.6,
                        evidence=[f"{child_id} IS_A {parent_id}", f"{parent_id}.{key}={value}"],
                    )
                    new_facts.append(fact)
                    self._facts.append(fact)

        logger.info("Miras cikarimi: %d yeni bilgi", len(new_facts))
        return new_facts

    def infer_inverse(self) -> list[InferredFact]:
        """Ters iliski cikarimi yapar.

        A causes B ise B depends_on A cikarir.

        Returns:
            Cikarilmis bilgi listesi.
        """
        new_facts: list[InferredFact] = []

        for edge in self._edges.values():
            rel_type = edge.relation.relation_type
            if rel_type in _INVERSE_RELATIONS:
                inverse_type = _INVERSE_RELATIONS[rel_type]
                fact = InferredFact(
                    inference_type=InferenceType.INVERSE,
                    subject=edge.target_node_id,
                    predicate=inverse_type.value,
                    obj=edge.source_node_id,
                    confidence=0.8,
                    evidence=[f"{edge.source_node_id} {rel_type.value} {edge.target_node_id}"],
                )
                new_facts.append(fact)
                self._facts.append(fact)

        logger.info("Ters iliski cikarimi: %d yeni bilgi", len(new_facts))
        return new_facts

    def apply_rules(self) -> list[InferredFact]:
        """Kural tabanli cikarim yapar.

        Returns:
            Cikarilmis bilgi listesi.
        """
        new_facts: list[InferredFact] = []

        for rule in self._rules:
            cond = rule["condition"]
            concl = rule["conclusion"]

            # Kosulu saglayan kenarlari bul
            for edge in self._edges.values():
                match = True
                if "relation_type" in cond and edge.relation.relation_type.value != cond["relation_type"]:
                    match = False
                if "min_strength" in cond and edge.relation.strength < cond["min_strength"]:
                    match = False

                if match:
                    fact = InferredFact(
                        inference_type=InferenceType.RULE_BASED,
                        subject=edge.source_node_id,
                        predicate=concl.get("predicate", "derived"),
                        obj=edge.target_node_id,
                        confidence=concl.get("confidence", 0.5),
                        rule_name=rule["name"],
                        evidence=[f"rule:{rule['name']}"],
                    )
                    new_facts.append(fact)
                    self._facts.append(fact)

        logger.info("Kural cikarimi: %d yeni bilgi", len(new_facts))
        return new_facts

    def detect_contradictions(self) -> list[dict[str, Any]]:
        """Celiskileri tespit eder.

        Returns:
            Celiski listesi.
        """
        contradictions: list[dict[str, Any]] = []

        # Ayni varlik cifti icin celisken iliskiler
        pair_relations: dict[tuple[str, str], list[str]] = {}
        for edge in self._edges.values():
            key = (edge.source_node_id, edge.target_node_id)
            if key not in pair_relations:
                pair_relations[key] = []
            pair_relations[key].append(edge.relation.relation_type.value)

        contradictory_pairs = [
            ("is_a", "part_of"),
            ("causes", "depends_on"),
        ]

        for pair, rel_types in pair_relations.items():
            for c1, c2 in contradictory_pairs:
                if c1 in rel_types and c2 in rel_types:
                    contradictions.append({
                        "source": pair[0],
                        "target": pair[1],
                        "conflict": f"{c1} vs {c2}",
                        "relations": rel_types,
                    })

        logger.info("Celiski tespiti: %d celiski bulundu", len(contradictions))
        return contradictions

    def run_all(self) -> list[InferredFact]:
        """Tum cikarim yontemlerini calistirir.

        Returns:
            Tum cikarilmis bilgiler.
        """
        all_facts: list[InferredFact] = []
        all_facts.extend(self.infer_transitive())
        all_facts.extend(self.infer_inheritance())
        all_facts.extend(self.infer_inverse())
        all_facts.extend(self.apply_rules())
        return all_facts

    @property
    def facts(self) -> list[InferredFact]:
        """Cikarilmis bilgiler."""
        return list(self._facts)

    @property
    def fact_count(self) -> int:
        """Toplam cikarilmis bilgi sayisi."""
        return len(self._facts)

    @property
    def rule_count(self) -> int:
        """Toplam kural sayisi."""
        return len(self._rules)
