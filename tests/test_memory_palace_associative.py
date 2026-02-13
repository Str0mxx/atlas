"""AssociativeNetwork testleri.

Cagrisimsal ag: kavram ekleme, baglanti, yayilan aktivasyon,
priming, en kisa yol, yaratici baglanti, komsuluk ve azalma testleri.
"""

import pytest

from app.core.memory_palace.associative_network import AssociativeNetwork
from app.models.memory_palace import AssociationType


# === Yardimci fonksiyonlar ===


def _make_network(**kwargs) -> AssociativeNetwork:
    """AssociativeNetwork olusturur."""
    return AssociativeNetwork(**kwargs)


# === Init Testleri ===


class TestInit:
    """AssociativeNetwork initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan parametrelerle olusturma."""
        net = _make_network()
        assert net._decay_factor == 0.8
        assert net._activation_threshold == 0.1
        assert net._nodes == {}
        assert net._links == {}
        assert net._reverse_links == {}

    def test_custom_decay_factor(self) -> None:
        """Ozel azalma carpani ile olusturma."""
        net = _make_network(decay_factor=0.5)
        assert net._decay_factor == 0.5

    def test_custom_activation_threshold(self) -> None:
        """Ozel aktivasyon esigi ile olusturma."""
        net = _make_network(activation_threshold=0.05)
        assert net._activation_threshold == 0.05


# === add_concept Testleri ===


class TestAddConcept:
    """AssociativeNetwork.add_concept testleri."""

    def test_basic_add(self) -> None:
        """Temel kavram ekleme."""
        net = _make_network()
        node = net.add_concept("python")
        assert node.name == "python"
        assert node.id in net._nodes
        assert net._links[node.id] == []
        assert net._reverse_links[node.id] == []

    def test_with_category(self) -> None:
        """Kategorili kavram ekleme."""
        net = _make_network()
        node = net.add_concept("python", category="language")
        assert node.category == "language"

    def test_with_metadata(self) -> None:
        """Metadata ile kavram ekleme."""
        net = _make_network()
        meta = {"version": "3.11", "type": "interpreted"}
        node = net.add_concept("python", metadata=meta)
        assert node.metadata == meta


# === get_concept Testleri ===


class TestGetConcept:
    """AssociativeNetwork.get_concept / get_concept_by_name testleri."""

    def test_get_by_id(self) -> None:
        """ID ile kavram getirme."""
        net = _make_network()
        node = net.add_concept("fastapi")
        result = net.get_concept(node.id)
        assert result is not None
        assert result.name == "fastapi"

    def test_get_by_name(self) -> None:
        """Isim ile kavram getirme."""
        net = _make_network()
        net.add_concept("fastapi")
        result = net.get_concept_by_name("fastapi")
        assert result is not None
        assert result.name == "fastapi"

    def test_not_found_by_id(self) -> None:
        """Bulunamayan kavram ID icin None donmesi."""
        net = _make_network()
        assert net.get_concept("nonexistent") is None

    def test_not_found_by_name(self) -> None:
        """Bulunamayan kavram ismi icin None donmesi."""
        net = _make_network()
        assert net.get_concept_by_name("nonexistent") is None


# === link_concepts Testleri ===


class TestLinkConcepts:
    """AssociativeNetwork.link_concepts testleri."""

    def test_basic_link(self) -> None:
        """Temel baglanti olusturma."""
        net = _make_network()
        a = net.add_concept("python")
        b = net.add_concept("fastapi")
        link = net.link_concepts(a.id, b.id, weight=0.8)
        assert link is not None
        assert link.source_id == a.id
        assert link.target_id == b.id
        assert link.weight == 0.8

    def test_returns_none_if_source_missing(self) -> None:
        """Kaynak kavram bulunamazsa None donmesi."""
        net = _make_network()
        b = net.add_concept("fastapi")
        result = net.link_concepts("missing", b.id)
        assert result is None

    def test_returns_none_if_target_missing(self) -> None:
        """Hedef kavram bulunamazsa None donmesi."""
        net = _make_network()
        a = net.add_concept("python")
        result = net.link_concepts(a.id, "missing")
        assert result is None

    def test_stores_in_both_directions(self) -> None:
        """Baglantinin _links ve _reverse_links icinde saklanmasi."""
        net = _make_network()
        a = net.add_concept("python")
        b = net.add_concept("fastapi")
        net.link_concepts(a.id, b.id)
        assert len(net._links[a.id]) == 1
        assert len(net._reverse_links[b.id]) == 1
        assert net._links[a.id][0].target_id == b.id
        assert net._reverse_links[b.id][0].source_id == a.id


# === spread_activation Testleri ===


class TestSpreadActivation:
    """AssociativeNetwork.spread_activation testleri."""

    def test_single_depth(self) -> None:
        """Tek derinlikte aktivasyon yayilimi."""
        net = _make_network(decay_factor=0.8, activation_threshold=0.01)
        a = net.add_concept("A")
        b = net.add_concept("B")
        net.link_concepts(a.id, b.id, weight=1.0)
        results = net.spread_activation(a.id, initial_activation=1.0, max_depth=1)
        ids = [r.node_id for r in results]
        assert a.id in ids
        assert b.id in ids

    def test_multi_depth(self) -> None:
        """Cok derinlikte aktivasyon yayilimi."""
        net = _make_network(decay_factor=0.9, activation_threshold=0.01)
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        net.link_concepts(a.id, b.id, weight=1.0)
        net.link_concepts(b.id, c.id, weight=1.0)
        results = net.spread_activation(a.id, initial_activation=1.0, max_depth=3)
        ids = [r.node_id for r in results]
        assert c.id in ids

    def test_decay_applied(self) -> None:
        """Azalma carpaninin aktivasyona uygulanmasi."""
        net = _make_network(decay_factor=0.5, activation_threshold=0.01)
        a = net.add_concept("A")
        b = net.add_concept("B")
        net.link_concepts(a.id, b.id, weight=1.0)
        results = net.spread_activation(a.id, initial_activation=1.0, max_depth=2)
        b_result = next(r for r in results if r.node_id == b.id)
        # activation = 1.0 * 1.0 * 0.5^1 = 0.5
        assert b_result.activation_level == pytest.approx(0.5)

    def test_cycle_handling(self) -> None:
        """Dongusel baglantilarda ziyaret takibi (sonsuz dongu olmamasi)."""
        net = _make_network(decay_factor=0.9, activation_threshold=0.01)
        a = net.add_concept("A")
        b = net.add_concept("B")
        net.link_concepts(a.id, b.id, weight=1.0)
        net.link_concepts(b.id, a.id, weight=1.0)
        results = net.spread_activation(a.id, max_depth=5)
        # Her dugum en fazla bir kez sonuclarda olmali
        node_ids = [r.node_id for r in results]
        assert len(node_ids) == len(set(node_ids))

    def test_threshold_filtering(self) -> None:
        """Esik altindaki aktivasyonlarin filtrelenmesi."""
        net = _make_network(decay_factor=0.1, activation_threshold=0.5)
        a = net.add_concept("A")
        b = net.add_concept("B")
        net.link_concepts(a.id, b.id, weight=0.3)
        results = net.spread_activation(a.id, initial_activation=1.0, max_depth=2)
        # B'nin aktivasyonu: 1.0 * 0.3 * 0.1^1 = 0.03 < 0.5 -> filtrelenmeli
        ids = [r.node_id for r in results]
        assert b.id not in ids

    def test_sorted_by_activation(self) -> None:
        """Sonuclarin aktivasyon seviyesine gore azalan sirali donmesi."""
        net = _make_network(decay_factor=0.9, activation_threshold=0.01)
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        net.link_concepts(a.id, b.id, weight=0.9)
        net.link_concepts(a.id, c.id, weight=0.3)
        results = net.spread_activation(a.id, initial_activation=1.0, max_depth=2)
        activations = [r.activation_level for r in results]
        assert activations == sorted(activations, reverse=True)

    def test_nonexistent_start(self) -> None:
        """Var olmayan baslangic dugumu icin bos liste."""
        net = _make_network()
        assert net.spread_activation("ghost") == []


# === prime Testleri ===


class TestPrime:
    """AssociativeNetwork.prime testleri."""

    def test_boosts_activation(self) -> None:
        """Aktivasyon artisi (priming)."""
        net = _make_network()
        a = net.add_concept("A")
        assert a.activation == 0.0
        net.prime([a.id], boost=0.3)
        assert a.activation == pytest.approx(0.3)

    def test_capped_at_one(self) -> None:
        """Aktivasyonun 1.0'i gecmemesi."""
        net = _make_network()
        a = net.add_concept("A")
        a.activation = 0.9
        net.prime([a.id], boost=0.5)
        assert a.activation == pytest.approx(1.0)

    def test_returns_count(self) -> None:
        """Prime edilen kavram sayisinin donmesi."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        count = net.prime([a.id, b.id, "nonexistent"])
        assert count == 2


# === find_path Testleri ===


class TestFindPath:
    """AssociativeNetwork.find_path testleri."""

    def test_direct_link(self) -> None:
        """Dogrudan baglanti ile yol bulma."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        net.link_concepts(a.id, b.id)
        path = net.find_path(a.id, b.id)
        assert path == [a.id, b.id]

    def test_multi_hop(self) -> None:
        """Cok adimli yol bulma."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        net.link_concepts(a.id, b.id)
        net.link_concepts(b.id, c.id)
        path = net.find_path(a.id, c.id)
        assert path == [a.id, b.id, c.id]

    def test_no_path_returns_empty(self) -> None:
        """Yol bulunamazsa bos liste donmesi."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        path = net.find_path(a.id, b.id)
        assert path == []

    def test_same_node(self) -> None:
        """Ayni dugume yol tek elemanli liste."""
        net = _make_network()
        a = net.add_concept("A")
        path = net.find_path(a.id, a.id)
        assert path == [a.id]


# === find_creative_connections Testleri ===


class TestCreativeConnections:
    """AssociativeNetwork.find_creative_connections testleri."""

    def test_filters_by_min_distance(self) -> None:
        """Minimum mesafe filtrelemesi."""
        net = _make_network(decay_factor=0.9, activation_threshold=0.001)
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        net.link_concepts(a.id, b.id, weight=1.0)
        net.link_concepts(b.id, c.id, weight=1.0)
        # min_distance=2 ile depth=1 olan B filtrelenmeli
        creative = net.find_creative_connections(a.id, min_distance=2, max_distance=3)
        ids = [r.node_id for r in creative]
        assert b.id not in ids
        assert c.id in ids

    def test_filters_by_max_distance(self) -> None:
        """Maksimum mesafe filtrelemesi."""
        net = _make_network(decay_factor=0.95, activation_threshold=0.001)
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        d = net.add_concept("D")
        net.link_concepts(a.id, b.id, weight=1.0)
        net.link_concepts(b.id, c.id, weight=1.0)
        net.link_concepts(c.id, d.id, weight=1.0)
        # max_distance=2 ile depth=3 olan D filtrelenmeli
        creative = net.find_creative_connections(a.id, min_distance=2, max_distance=2)
        ids = [r.node_id for r in creative]
        assert d.id not in ids
        assert c.id in ids


# === get_neighbors Testleri ===


class TestNeighbors:
    """AssociativeNetwork.get_neighbors testleri."""

    def test_returns_direct_connections(self) -> None:
        """Dogrudan bagli komsu kavramlarin donmesi."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        net.link_concepts(a.id, b.id)
        net.link_concepts(a.id, c.id)
        neighbors = net.get_neighbors(a.id)
        neighbor_ids = [n.id for n in neighbors]
        assert b.id in neighbor_ids
        assert c.id in neighbor_ids
        assert len(neighbors) == 2

    def test_no_neighbors(self) -> None:
        """Komsusu olmayan dugum icin bos liste."""
        net = _make_network()
        a = net.add_concept("A")
        assert net.get_neighbors(a.id) == []


# === decay_activations Testleri ===


class TestDecayActivations:
    """AssociativeNetwork.decay_activations testleri."""

    def test_reduces_all(self) -> None:
        """Tum aktivasyonlarin azaltilmasi."""
        net = _make_network(decay_factor=0.5, activation_threshold=0.01)
        a = net.add_concept("A")
        b = net.add_concept("B")
        a.activation = 0.8
        b.activation = 0.6
        net.decay_activations()
        assert a.activation == pytest.approx(0.4)
        assert b.activation == pytest.approx(0.3)

    def test_below_threshold_set_to_zero(self) -> None:
        """Esik altina dusen aktivasyonlarin sifirlanmasi."""
        net = _make_network(decay_factor=0.5, activation_threshold=0.2)
        a = net.add_concept("A")
        a.activation = 0.3
        net.decay_activations()
        # 0.3 * 0.5 = 0.15 < 0.2 -> 0.0
        assert a.activation == 0.0

    def test_custom_factor(self) -> None:
        """Ozel azalma carpani ile azaltma."""
        net = _make_network(decay_factor=0.8, activation_threshold=0.01)
        a = net.add_concept("A")
        a.activation = 1.0
        net.decay_activations(factor=0.3)
        assert a.activation == pytest.approx(0.3)


# === get_strongest_links Testleri ===


class TestStrongestLinks:
    """AssociativeNetwork.get_strongest_links testleri."""

    def test_sorted_by_weight(self) -> None:
        """Baglantilarin agirliga gore azalan sirali donmesi."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        c = net.add_concept("C")
        net.link_concepts(a.id, b.id, weight=0.3)
        net.link_concepts(a.id, c.id, weight=0.9)
        links = net.get_strongest_links(a.id)
        assert links[0].weight == 0.9
        assert links[1].weight == 0.3

    def test_limited(self) -> None:
        """Sonuc sayisi limiti."""
        net = _make_network()
        a = net.add_concept("A")
        for i in range(10):
            n = net.add_concept(f"N{i}")
            net.link_concepts(a.id, n.id, weight=i * 0.1)
        links = net.get_strongest_links(a.id, limit=3)
        assert len(links) == 3


# === count Testleri ===


class TestCounts:
    """AssociativeNetwork.count_nodes / count_links testleri."""

    def test_count_nodes(self) -> None:
        """Dugum sayisinin dogru donmesi."""
        net = _make_network()
        assert net.count_nodes() == 0
        net.add_concept("A")
        net.add_concept("B")
        assert net.count_nodes() == 2

    def test_count_links(self) -> None:
        """Baglanti sayisinin dogru donmesi."""
        net = _make_network()
        a = net.add_concept("A")
        b = net.add_concept("B")
        assert net.count_links() == 0
        net.link_concepts(a.id, b.id)
        assert net.count_links() == 1
