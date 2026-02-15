"""ATLAS Unified Entity Memory testleri."""

import time

import pytest

from app.core.entitymem import (
    EntityContextProvider,
    EntityMemOrchestrator,
    EntityPreferenceLearner,
    EntityPrivacyManager,
    EntityRegistry,
    InteractionLogger,
    ProfileBuilder,
    RelationshipMapper,
    TimelineBuilder,
)
from app.models.entitymem_models import (
    ConsentStatus,
    EntityMemSnapshot,
    EntityRecord,
    EntityType,
    EventType,
    InteractionChannel,
    InteractionRecord,
    PrivacyLevel,
    RelationshipRecord,
    RelationshipType,
)


# ── Model Testleri ──────────────────────────


class TestEntityMemModels:
    """Model testleri."""

    def test_entity_type_enum(self) -> None:
        assert EntityType.PERSON == "person"
        assert EntityType.COMPANY == "company"
        assert EntityType.PROJECT == "project"
        assert EntityType.PRODUCT == "product"
        assert EntityType.SERVICE == "service"

    def test_relationship_type_enum(self) -> None:
        assert RelationshipType.WORKS_FOR == "works_for"
        assert RelationshipType.OWNS == "owns"
        assert RelationshipType.COLLABORATES == "collaborates"
        assert RelationshipType.MANAGES == "manages"
        assert RelationshipType.SUPPLIES == "supplies"

    def test_interaction_channel_enum(self) -> None:
        assert InteractionChannel.TELEGRAM == "telegram"
        assert InteractionChannel.EMAIL == "email"
        assert InteractionChannel.PHONE == "phone"
        assert InteractionChannel.MEETING == "meeting"
        assert InteractionChannel.API == "api"

    def test_privacy_level_enum(self) -> None:
        assert PrivacyLevel.PUBLIC == "public"
        assert PrivacyLevel.INTERNAL == "internal"
        assert PrivacyLevel.CONFIDENTIAL == "confidential"
        assert PrivacyLevel.RESTRICTED == "restricted"
        assert PrivacyLevel.PERSONAL == "personal"

    def test_consent_status_enum(self) -> None:
        assert ConsentStatus.GRANTED == "granted"
        assert ConsentStatus.DENIED == "denied"
        assert ConsentStatus.PENDING == "pending"
        assert ConsentStatus.WITHDRAWN == "withdrawn"
        assert ConsentStatus.EXPIRED == "expired"

    def test_event_type_enum(self) -> None:
        assert EventType.CREATED == "created"
        assert EventType.UPDATED == "updated"
        assert EventType.INTERACTION == "interaction"
        assert EventType.MILESTONE == "milestone"
        assert EventType.NOTE == "note"

    def test_entity_record(self) -> None:
        r = EntityRecord(name="Test")
        assert r.name == "Test"
        assert r.entity_type == EntityType.PERSON
        assert r.entity_id
        assert r.aliases == []

    def test_interaction_record(self) -> None:
        r = InteractionRecord(
            entity_id="e1",
            content="hello",
        )
        assert r.entity_id == "e1"
        assert r.content == "hello"
        assert r.sentiment == 0.0

    def test_relationship_record(self) -> None:
        r = RelationshipRecord(
            source_id="a",
            target_id="b",
        )
        assert r.source_id == "a"
        assert r.target_id == "b"
        assert r.strength == 0.5
        assert r.bidirectional is False

    def test_entitymem_snapshot(self) -> None:
        s = EntityMemSnapshot(
            total_entities=10,
            total_interactions=100,
        )
        assert s.total_entities == 10
        assert s.total_interactions == 100
        assert s.snapshot_id


# ── EntityRegistry Testleri ──────────────────


class TestEntityRegistry:
    """EntityRegistry testleri."""

    def test_create_entity(self) -> None:
        reg = EntityRegistry()
        result = reg.create_entity("Fatih", "person")
        assert result["created"] is True
        assert result["name"] == "Fatih"
        assert result["entity_type"] == "person"
        assert reg.entity_count == 1

    def test_get_entity(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Test")
        e = reg.get_entity(c["entity_id"])
        assert e["name"] == "Test"
        assert e["status"] == "active"

    def test_get_entity_not_found(self) -> None:
        reg = EntityRegistry()
        r = reg.get_entity("nonexistent")
        assert r["error"] == "entity_not_found"

    def test_update_entity(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Old Name")
        r = reg.update_entity(
            c["entity_id"],
            {"name": "New Name"},
        )
        assert r["updated"] is True
        e = reg.get_entity(c["entity_id"])
        assert e["name"] == "New Name"

    def test_update_entity_properties(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Test", properties={"a": 1})
        reg.update_entity(
            c["entity_id"],
            {"properties": {"b": 2}},
        )
        e = reg.get_entity(c["entity_id"])
        assert e["properties"]["a"] == 1
        assert e["properties"]["b"] == 2

    def test_add_alias(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Fatih")
        r = reg.add_alias(c["entity_id"], "boss")
        assert r["added"] is True
        # Alias ile bul
        e = reg.get_entity("boss")
        assert e["name"] == "Fatih"

    def test_add_alias_duplicate(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("A")
        reg.add_alias(c["entity_id"], "x")
        r = reg.add_alias(c["entity_id"], "x")
        assert r["error"] == "alias_exists"

    def test_remove_alias(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("A")
        reg.add_alias(c["entity_id"], "myalias")
        r = reg.remove_alias("myalias")
        assert r["removed"] is True

    def test_archive_entity(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Test")
        r = reg.archive_entity(c["entity_id"])
        assert r["archived"] is True
        e = reg.get_entity(c["entity_id"])
        assert e["status"] == "archived"

    def test_search_entities(self) -> None:
        reg = EntityRegistry()
        reg.create_entity("Fatih", "person")
        reg.create_entity("Mapa Health", "company")
        reg.create_entity("FTRK", "company")
        results = reg.search_entities("fatih")
        assert len(results) == 1
        assert results[0]["name"] == "Fatih"

    def test_search_by_type(self) -> None:
        reg = EntityRegistry()
        reg.create_entity("A", "person")
        reg.create_entity("B", "company")
        reg.create_entity("C", "company")
        results = reg.search_entities(
            entity_type="company",
        )
        assert len(results) == 2

    def test_search_by_alias(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Long Name Corp")
        reg.add_alias(c["entity_id"], "LNC")
        results = reg.search_entities("lnc")
        assert len(results) == 1

    def test_list_by_type(self) -> None:
        reg = EntityRegistry()
        reg.create_entity("P1", "project")
        reg.create_entity("P2", "project")
        reg.create_entity("C1", "company")
        result = reg.list_by_type("project")
        assert len(result) == 2

    def test_active_count(self) -> None:
        reg = EntityRegistry()
        c1 = reg.create_entity("A")
        reg.create_entity("B")
        reg.archive_entity(c1["entity_id"])
        assert reg.active_count == 1

    def test_search_excludes_archived(self) -> None:
        reg = EntityRegistry()
        c = reg.create_entity("Archived")
        reg.archive_entity(c["entity_id"])
        results = reg.search_entities("archived")
        assert len(results) == 0


# ── ProfileBuilder Testleri ──────────────────


class TestProfileBuilder:
    """ProfileBuilder testleri."""

    def test_build_profile(self) -> None:
        pb = ProfileBuilder()
        r = pb.build_profile(
            "e1",
            {"name": "Fatih", "email": "f@test.com"},
        )
        assert r["is_new"] is True
        assert r["completeness"] > 0
        assert pb.profile_count == 1

    def test_build_profile_update(self) -> None:
        pb = ProfileBuilder()
        pb.build_profile("e1", {"name": "Fatih"})
        r = pb.build_profile("e1", {"phone": "555"})
        assert r["is_new"] is False
        p = pb.get_profile("e1")
        assert p["fields"]["name"] == "Fatih"
        assert p["fields"]["phone"] == "555"

    def test_merge_sources(self) -> None:
        pb = ProfileBuilder()
        sources = [
            {"source": "crm", "data": {"name": "Fatih", "email": "a@b.com"}},
            {"source": "linkedin", "data": {"company": "FTRK", "role": "CEO"}},
        ]
        r = pb.merge_sources("e1", sources)
        assert r["fields_merged"] == 4
        assert r["conflicts"] == 0

    def test_merge_with_conflict(self) -> None:
        pb = ProfileBuilder()
        sources = [
            {"source": "s1", "data": {"email": "a@b.com"}},
            {"source": "s2", "data": {"email": "x@y.com"}},
        ]
        r = pb.merge_sources("e1", sources, "latest")
        assert r["conflicts"] == 1

    def test_resolve_conflict(self) -> None:
        pb = ProfileBuilder()
        pb.build_profile("e1", {"name": "A"})
        r = pb.resolve_conflict("e1", "name", "B")
        assert r["resolved"] is True
        p = pb.get_profile("e1")
        assert p["fields"]["name"] == "B"

    def test_completeness_scoring(self) -> None:
        pb = ProfileBuilder()
        pb.build_profile("e1", {
            "name": "Fatih",
            "email": "f@t.com",
            "phone": "555",
            "company": "FTRK",
            "role": "CEO",
        })
        c = pb.get_completeness("e1")
        assert c["completeness"] == 1.0
        assert c["missing_fields"] == []

    def test_completeness_partial(self) -> None:
        pb = ProfileBuilder()
        pb.build_profile("e1", {"name": "Fatih"})
        c = pb.get_completeness("e1")
        assert c["completeness"] == 0.2
        assert "email" in c["missing_fields"]

    def test_update_history(self) -> None:
        pb = ProfileBuilder()
        pb.build_profile("e1", {"name": "A"}, "manual")
        pb.build_profile("e1", {"email": "b"}, "import")
        h = pb.get_update_history("e1")
        assert len(h) == 2
        assert h[0]["source"] == "manual"
        assert h[1]["source"] == "import"

    def test_get_profile_not_found(self) -> None:
        pb = ProfileBuilder()
        r = pb.get_profile("nonexistent")
        assert r["error"] == "profile_not_found"


# ── InteractionLogger Testleri ───────────────


class TestInteractionLogger:
    """InteractionLogger testleri."""

    def test_log_interaction(self) -> None:
        il = InteractionLogger()
        r = il.log_interaction(
            "e1", "telegram", "Merhaba",
        )
        assert r["logged"] is True
        assert r["channel"] == "telegram"
        assert il.interaction_count == 1

    def test_log_with_sentiment(self) -> None:
        il = InteractionLogger()
        il.log_interaction(
            "e1", "email", "Great!",
            sentiment=0.8,
        )
        ints = il.get_interactions("e1")
        assert ints[0]["sentiment"] == 0.8

    def test_log_with_context(self) -> None:
        il = InteractionLogger()
        il.log_interaction(
            "e1", "meeting", "Discussion",
            context={"topic": "budget"},
        )
        ints = il.get_interactions("e1")
        assert ints[0]["context"]["topic"] == "budget"

    def test_get_interactions_by_channel(self) -> None:
        il = InteractionLogger()
        il.log_interaction("e1", "telegram", "a")
        il.log_interaction("e1", "email", "b")
        il.log_interaction("e1", "telegram", "c")
        ints = il.get_interactions(
            "e1", channel="telegram",
        )
        assert len(ints) == 2

    def test_channel_stats(self) -> None:
        il = InteractionLogger()
        il.log_interaction("e1", "telegram", "a")
        il.log_interaction("e1", "telegram", "b")
        il.log_interaction("e2", "email", "c")
        stats = il.get_channel_stats()
        assert stats["channels"]["telegram"] == 2
        assert stats["channels"]["email"] == 1
        assert stats["total"] == 3

    def test_sentiment_summary(self) -> None:
        il = InteractionLogger()
        il.log_interaction("e1", "t", "a", sentiment=0.8)
        il.log_interaction("e1", "t", "b", sentiment=-0.5)
        il.log_interaction("e1", "t", "c", sentiment=0.1)
        s = il.get_sentiment_summary("e1")
        assert s["positive"] == 1
        assert s["negative"] == 1
        assert s["neutral"] == 1

    def test_sentiment_summary_empty(self) -> None:
        il = InteractionLogger()
        s = il.get_sentiment_summary("e1")
        assert s["avg_sentiment"] == 0.0
        assert s["interaction_count"] == 0

    def test_get_recent(self) -> None:
        il = InteractionLogger()
        for i in range(10):
            il.log_interaction("e1", "t", f"msg{i}")
        recent = il.get_recent("e1", count=3)
        assert len(recent) == 3
        assert recent[-1]["content"] == "msg9"

    def test_max_stored_limit(self) -> None:
        il = InteractionLogger(max_stored=5)
        for i in range(10):
            il.log_interaction("e1", "t", f"m{i}")
        ints = il.get_interactions("e1")
        assert len(ints) == 5

    def test_sentiment_clamping(self) -> None:
        il = InteractionLogger()
        il.log_interaction("e1", "t", "a", sentiment=5.0)
        il.log_interaction("e1", "t", "b", sentiment=-3.0)
        ints = il.get_interactions("e1")
        assert ints[0]["sentiment"] == 1.0
        assert ints[1]["sentiment"] == -1.0

    def test_entity_interaction_count(self) -> None:
        il = InteractionLogger()
        il.log_interaction("e1", "t", "a")
        il.log_interaction("e1", "t", "b")
        il.log_interaction("e2", "t", "c")
        assert il.entity_interaction_count("e1") == 2
        assert il.entity_interaction_count("e2") == 1
        assert il.entity_interaction_count("e3") == 0


# ── RelationshipMapper Testleri ──────────────


class TestRelationshipMapper:
    """RelationshipMapper testleri."""

    def test_add_relationship(self) -> None:
        rm = RelationshipMapper()
        r = rm.add_relationship(
            "e1", "e2", "works_for", 0.8,
        )
        assert r["added"] is True
        assert rm.relationship_count == 1

    def test_get_relationships(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("e1", "e2", "works_for")
        rm.add_relationship("e3", "e1", "manages")
        rels = rm.get_relationships("e1")
        assert len(rels["outgoing"]) == 1
        assert len(rels["incoming"]) == 1

    def test_get_relationships_outgoing(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("e1", "e2")
        rm.add_relationship("e1", "e3")
        rels = rm.get_relationships(
            "e1", direction="outgoing",
        )
        assert rels["count"] == 2

    def test_bidirectional(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship(
            "e1", "e2", "collaborates",
            bidirectional=True,
        )
        rels = rm.get_relationships("e2")
        assert len(rels["bidirectional"]) == 1

    def test_update_strength(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("e1", "e2", strength=0.5)
        r = rm.update_strength("e1", "e2", 0.3)
        assert r["updated"] is True
        assert r["new_strength"] == 0.8

    def test_update_strength_clamping(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("e1", "e2", strength=0.9)
        r = rm.update_strength("e1", "e2", 0.5)
        assert r["new_strength"] == 1.0

    def test_update_strength_not_found(self) -> None:
        rm = RelationshipMapper()
        r = rm.update_strength("x", "y", 0.1)
        assert r["error"] == "relationship_not_found"

    def test_find_connections(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("a", "b")
        rm.add_relationship("b", "c")
        rm.add_relationship("c", "d")
        conns = rm.find_connections("a", max_depth=3)
        ids = [c["entity_id"] for c in conns["connections"]]
        assert "b" in ids
        assert "c" in ids

    def test_find_connections_depth_limit(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("a", "b")
        rm.add_relationship("b", "c")
        rm.add_relationship("c", "d")
        conns = rm.find_connections("a", max_depth=1)
        ids = [c["entity_id"] for c in conns["connections"]]
        assert "b" in ids
        assert "c" not in ids

    def test_detect_hierarchy(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("boss", "m1", "manages")
        rm.add_relationship("boss", "m2", "manages")
        rm.add_relationship("m1", "w1", "manages")
        h = rm.detect_hierarchy("boss")
        assert h["total_members"] == 3

    def test_get_strongest(self) -> None:
        rm = RelationshipMapper()
        rm.add_relationship("e1", "e2", strength=0.3)
        rm.add_relationship("e1", "e3", strength=0.9)
        rm.add_relationship("e1", "e4", strength=0.6)
        strongest = rm.get_strongest("e1", limit=2)
        assert len(strongest) == 2
        assert strongest[0]["strength"] == 0.9


# ── TimelineBuilder Testleri ─────────────────


class TestTimelineBuilder:
    """TimelineBuilder testleri."""

    def test_add_event(self) -> None:
        tb = TimelineBuilder()
        r = tb.add_event("e1", "created", "Entity created")
        assert r["added"] is True
        assert tb.event_count == 1

    def test_add_event_with_timestamp(self) -> None:
        tb = TimelineBuilder()
        ts = time.time() - 86400
        tb.add_event("e1", "note", "Old event", timestamp=ts)
        tl = tb.get_timeline("e1")
        assert tl["events"][0]["timestamp"] == ts

    def test_chronological_order(self) -> None:
        tb = TimelineBuilder()
        now = time.time()
        tb.add_event("e1", "c", "Third", timestamp=now + 2)
        tb.add_event("e1", "a", "First", timestamp=now)
        tb.add_event("e1", "b", "Second", timestamp=now + 1)
        tl = tb.get_timeline("e1")
        descs = [e["description"] for e in tl["events"]]
        assert descs == ["First", "Second", "Third"]

    def test_mark_milestone(self) -> None:
        tb = TimelineBuilder()
        r = tb.mark_milestone("e1", "First Sale")
        assert r["marked"] is True
        assert tb.milestone_count == 1
        ms = tb.get_milestones("e1")
        assert len(ms) == 1
        assert ms[0]["title"] == "First Sale"

    def test_milestone_appears_in_timeline(self) -> None:
        tb = TimelineBuilder()
        tb.mark_milestone("e1", "Launch")
        tl = tb.get_timeline("e1")
        types = [e["event_type"] for e in tl["events"]]
        assert "milestone" in types

    def test_get_timeline_with_range(self) -> None:
        tb = TimelineBuilder()
        now = time.time()
        tb.add_event("e1", "a", "old", timestamp=now - 100)
        tb.add_event("e1", "b", "recent", timestamp=now)
        tb.add_event("e1", "c", "future", timestamp=now + 100)
        tl = tb.get_timeline("e1", start=now - 50, end=now + 50)
        assert tl["event_count"] == 1

    def test_analyze_period(self) -> None:
        tb = TimelineBuilder()
        now = time.time()
        tb.add_event("e1", "interaction", "a", timestamp=now)
        tb.add_event("e1", "interaction", "b", timestamp=now + 100)
        tb.add_event("e1", "note", "c", timestamp=now + 200)
        r = tb.analyze_period("e1", now - 1, now + 300)
        assert r["event_count"] == 3
        assert r["type_distribution"]["interaction"] == 2

    def test_detect_patterns_recurring(self) -> None:
        tb = TimelineBuilder()
        now = time.time()
        for i in range(5):
            tb.add_event("e1", "interaction", f"m{i}", timestamp=now + i)
        p = tb.detect_patterns("e1")
        assert p["pattern_count"] > 0
        types = [pt["pattern"] for pt in p["patterns"]]
        assert "recurring" in types

    def test_detect_patterns_few_events(self) -> None:
        tb = TimelineBuilder()
        tb.add_event("e1", "a", "single")
        p = tb.detect_patterns("e1")
        assert p["pattern_count"] == 0

    def test_project_future(self) -> None:
        tb = TimelineBuilder()
        now = time.time()
        for i in range(10):
            tb.add_event(
                "e1", "interaction", f"e{i}",
                timestamp=now + i * 3600,
            )
        r = tb.project_future("e1", days=30)
        assert r["projected_events"] > 0
        assert r["confidence"] > 0

    def test_project_future_insufficient_data(self) -> None:
        tb = TimelineBuilder()
        tb.add_event("e1", "a", "single")
        r = tb.project_future("e1")
        assert r["projected_events"] == 0
        assert r["confidence"] == 0.0


# ── EntityPreferenceLearner Testleri ─────────


class TestEntityPreferenceLearner:
    """EntityPreferenceLearner testleri."""

    def test_learn_preference(self) -> None:
        pl = EntityPreferenceLearner()
        r = pl.learn_preference(
            "e1", "communication", "channel", "telegram",
        )
        assert r["learned"] is True
        assert pl.preference_count == 1

    def test_reinforce_preference(self) -> None:
        pl = EntityPreferenceLearner()
        pl.learn_preference(
            "e1", "topics", "tech", "high", 0.5,
        )
        r = pl.reinforce_preference("e1", "topics", "tech")
        assert r["reinforced"] is True
        assert r["observations"] == 2
        assert r["confidence"] > 0.5

    def test_reinforce_not_found(self) -> None:
        pl = EntityPreferenceLearner()
        r = pl.reinforce_preference("e1", "x", "y")
        assert r["error"] == "preference_not_found"

    def test_communication_style(self) -> None:
        pl = EntityPreferenceLearner()
        pl.learn_preference(
            "e1", "communication", "formality", "informal",
        )
        pl.learn_preference(
            "e1", "communication", "channel", "telegram",
        )
        style = pl.get_communication_style("e1")
        assert style["formality"] == "informal"
        assert style["preferred_channel"] == "telegram"

    def test_communication_style_defaults(self) -> None:
        pl = EntityPreferenceLearner()
        style = pl.get_communication_style("e1")
        assert style["formality"] == "neutral"
        assert style["preferred_channel"] == "any"

    def test_timing_preferences(self) -> None:
        pl = EntityPreferenceLearner()
        pl.learn_preference(
            "e1", "timing", "hours", "evening",
        )
        t = pl.get_timing_preferences("e1")
        assert t["preferred_hours"] == "evening"

    def test_topic_interests(self) -> None:
        pl = EntityPreferenceLearner()
        pl.learn_preference(
            "e1", "topics", "ai", "high", 0.9,
        )
        pl.learn_preference(
            "e1", "topics", "finance", "medium", 0.5,
        )
        interests = pl.get_topic_interests("e1")
        assert interests["interest_count"] == 2
        # Sorted by confidence
        assert interests["interests"][0]["topic"] == "ai"

    def test_record_behavior(self) -> None:
        pl = EntityPreferenceLearner()
        r = pl.record_behavior(
            "e1", "quick_response",
            {"avg_time": 30},
        )
        assert r["recorded"] is True
        assert pl.behavior_count == 1

    def test_behavior_patterns(self) -> None:
        pl = EntityPreferenceLearner()
        for _ in range(5):
            pl.record_behavior("e1", "quick_response")
        for _ in range(2):
            pl.record_behavior("e1", "late_reply")
        p = pl.get_behavior_patterns("e1")
        assert p["behavior_count"] == 7
        assert p["patterns"][0]["is_habitual"] is True

    def test_behavior_patterns_empty(self) -> None:
        pl = EntityPreferenceLearner()
        p = pl.get_behavior_patterns("e1")
        assert p["behavior_count"] == 0

    def test_get_all_preferences(self) -> None:
        pl = EntityPreferenceLearner()
        pl.learn_preference("e1", "comm", "tone", "friendly")
        pl.learn_preference("e1", "timing", "days", "weekdays")
        prefs = pl.get_all_preferences("e1")
        assert "comm" in prefs["categories"]
        assert "timing" in prefs["categories"]


# ── EntityContextProvider Testleri ───────────


class TestEntityContextProvider:
    """EntityContextProvider testleri."""

    def test_get_context(self) -> None:
        cp = EntityContextProvider()
        ctx = cp.get_context("e1")
        assert ctx["entity_id"] == "e1"
        assert ctx["pending_count"] == 0
        assert cp.context_count == 1

    def test_get_context_with_data(self) -> None:
        cp = EntityContextProvider()
        interactions = [{"content": "hi"}, {"content": "hello"}]
        ctx = cp.get_context(
            "e1",
            interactions=interactions,
            profile={"fields": {"name": "Fatih"}},
        )
        assert len(ctx["recent_interactions"]) == 2
        assert ctx["profile_summary"]["name"] == "Fatih"

    def test_add_pending_item(self) -> None:
        cp = EntityContextProvider()
        r = cp.add_pending_item(
            "e1", "follow_up", "Call back",
        )
        assert r["added"] is True
        items = cp.get_pending_items("e1")
        assert len(items) == 1

    def test_resolve_pending(self) -> None:
        cp = EntityContextProvider()
        cp.add_pending_item("e1", "task", "Do X")
        r = cp.resolve_pending("e1", "task")
        assert r["resolved"] is True
        items = cp.get_pending_items("e1")
        assert len(items) == 0

    def test_resolve_pending_not_found(self) -> None:
        cp = EntityContextProvider()
        r = cp.resolve_pending("e1", "nonexistent")
        assert r["error"] == "item_not_found"

    def test_add_note(self) -> None:
        cp = EntityContextProvider()
        r = cp.add_note("e1", "Important note")
        assert r["note_added"] is True

    def test_get_quick_summary(self) -> None:
        cp = EntityContextProvider()
        cp.add_pending_item("e1", "task", "Do X")
        cp.add_note("e1", "Note 1")
        s = cp.get_quick_summary(
            "e1",
            profile={"fields": {"name": "Fatih"}},
            interaction_count=10,
            relationship_count=3,
        )
        assert s["name"] == "Fatih"
        assert s["interactions"] == 10
        assert s["pending_items"] == 1
        assert s["notes"] == 1

    def test_pending_in_context(self) -> None:
        cp = EntityContextProvider()
        cp.add_pending_item("e1", "review", "Review PR")
        ctx = cp.get_context("e1")
        assert ctx["pending_count"] == 1


# ── EntityPrivacyManager Testleri ────────────


class TestEntityPrivacyManager:
    """EntityPrivacyManager testleri."""

    def test_set_consent(self) -> None:
        pm = EntityPrivacyManager()
        r = pm.set_consent("e1", "marketing", "granted")
        assert r["set"] is True
        assert pm.consent_count == 1

    def test_check_consent_granted(self) -> None:
        pm = EntityPrivacyManager()
        pm.set_consent("e1", "analytics", "granted")
        r = pm.check_consent("e1", "analytics")
        assert r["has_consent"] is True

    def test_check_consent_denied(self) -> None:
        pm = EntityPrivacyManager()
        pm.set_consent("e1", "marketing", "denied")
        r = pm.check_consent("e1", "marketing")
        assert r["has_consent"] is False

    def test_check_consent_no_record(self) -> None:
        pm = EntityPrivacyManager()
        r = pm.check_consent("e1", "something")
        assert r["has_consent"] is False
        assert r["reason"] == "no_consent_record"

    def test_consent_expiry(self) -> None:
        pm = EntityPrivacyManager()
        pm.set_consent("e1", "data", "granted", expiry_days=0)
        # expiry is already passed since it's 0 days
        # need to manipulate
        pm._consent["e1"]["data"]["expiry"] = time.time() - 1
        r = pm.check_consent("e1", "data")
        assert r["has_consent"] is False
        assert r["reason"] == "expired"

    def test_check_access_allowed(self) -> None:
        pm = EntityPrivacyManager()
        r = pm.check_access("e1", "system", "analytics")
        assert r["allowed"] is True

    def test_check_access_anonymized(self) -> None:
        pm = EntityPrivacyManager()
        pm.anonymize_entity("e1")
        r = pm.check_access("e1", "system", "analytics")
        assert r["allowed"] is False
        assert r["reason"] == "anonymized"

    def test_strict_mode_access(self) -> None:
        pm = EntityPrivacyManager(privacy_mode="strict")
        r = pm.check_access("e1", "agent", "marketing")
        assert r["allowed"] is False
        assert r["reason"] == "no_consent_for_purpose"

    def test_strict_mode_with_consent(self) -> None:
        pm = EntityPrivacyManager(privacy_mode="strict")
        pm.set_consent("e1", "marketing", "granted")
        r = pm.check_access("e1", "agent", "marketing")
        assert r["allowed"] is True

    def test_anonymize_entity(self) -> None:
        pm = EntityPrivacyManager()
        r = pm.anonymize_entity("e1")
        assert r["anonymized"] is True
        assert pm.anonymization_count == 1

    def test_check_retention(self) -> None:
        pm = EntityPrivacyManager(retention_days=30)
        old = time.time() - 40 * 86400
        r = pm.check_retention("e1", old)
        assert r["expired"] is True
        assert r["action"] == "delete"

    def test_check_retention_active(self) -> None:
        pm = EntityPrivacyManager(retention_days=365)
        recent = time.time() - 10 * 86400
        r = pm.check_retention("e1", recent)
        assert r["expired"] is False
        assert r["action"] == "keep"

    def test_gdpr_report(self) -> None:
        pm = EntityPrivacyManager()
        pm.set_consent("e1", "analytics", "granted")
        pm.check_access("e1", "system", "read")
        r = pm.get_gdpr_report("e1")
        assert r["consent_count"] == 1
        assert r["access_log_count"] == 1
        assert r["is_anonymized"] is False

    def test_withdraw_consent(self) -> None:
        pm = EntityPrivacyManager()
        pm.set_consent("e1", "marketing", "granted")
        r = pm.withdraw_consent("e1", "marketing")
        assert r["withdrawn"] is True
        c = pm.check_consent("e1", "marketing")
        assert c["has_consent"] is False

    def test_withdraw_consent_not_found(self) -> None:
        pm = EntityPrivacyManager()
        r = pm.withdraw_consent("e1", "nonexistent")
        assert r["error"] == "consent_not_found"

    def test_get_access_log(self) -> None:
        pm = EntityPrivacyManager()
        pm.check_access("e1", "agent1", "read")
        pm.check_access("e1", "agent2", "write")
        pm.check_access("e2", "agent1", "read")
        log = pm.get_access_log("e1")
        assert len(log) == 2


# ── EntityMemOrchestrator Testleri ───────────


class TestEntityMemOrchestrator:
    """EntityMemOrchestrator testleri."""

    def test_create_entity(self) -> None:
        orch = EntityMemOrchestrator()
        r = orch.create_entity("Fatih", "person")
        assert r["created"] is True
        assert r["name"] == "Fatih"
        assert orch.operations == 1

    def test_create_entity_with_profile(self) -> None:
        orch = EntityMemOrchestrator()
        r = orch.create_entity(
            "Fatih", "person",
            profile_data={"email": "f@t.com", "role": "CEO"},
        )
        eid = r["entity_id"]
        p = orch.profiles.get_profile(eid)
        assert p["fields"]["email"] == "f@t.com"
        assert p["fields"]["name"] == "Fatih"

    def test_record_interaction(self) -> None:
        orch = EntityMemOrchestrator()
        c = orch.create_entity("Fatih")
        eid = c["entity_id"]
        r = orch.record_interaction(
            eid, "telegram", "Merhaba",
        )
        assert r["logged"] is True

    def test_record_interaction_entity_not_found(self) -> None:
        orch = EntityMemOrchestrator()
        r = orch.record_interaction(
            "nonexistent", "t", "hi",
        )
        assert r["error"] == "entity_not_found"

    def test_get_entity_context(self) -> None:
        orch = EntityMemOrchestrator()
        c = orch.create_entity("Fatih")
        eid = c["entity_id"]
        orch.record_interaction(eid, "t", "hi")
        ctx = orch.get_entity_context(eid)
        assert ctx["entity_id"] == eid
        assert len(ctx["recent_interactions"]) > 0

    def test_get_entity_context_not_found(self) -> None:
        orch = EntityMemOrchestrator()
        r = orch.get_entity_context("x")
        assert r["error"] == "entity_not_found"

    def test_query_entity(self) -> None:
        orch = EntityMemOrchestrator()
        c = orch.create_entity(
            "Fatih", "person",
            profile_data={"email": "f@t.com"},
        )
        eid = c["entity_id"]
        orch.record_interaction(eid, "t", "hi")
        q = orch.query_entity(eid)
        assert q["entity"]["name"] == "Fatih"
        assert q["interaction_count"] == 1

    def test_query_entity_not_found(self) -> None:
        orch = EntityMemOrchestrator()
        r = orch.query_entity("x")
        assert r["error"] == "entity_not_found"

    def test_export_entity(self) -> None:
        orch = EntityMemOrchestrator()
        c = orch.create_entity("Fatih")
        eid = c["entity_id"]
        orch.record_interaction(eid, "t", "hello")
        exp = orch.export_entity(eid)
        assert exp["exported"] is True
        assert exp["entity"]["name"] == "Fatih"
        assert len(exp["interactions"]) > 0

    def test_export_entity_not_found(self) -> None:
        orch = EntityMemOrchestrator()
        r = orch.export_entity("x")
        assert r["error"] == "entity_not_found"

    def test_import_entity(self) -> None:
        orch = EntityMemOrchestrator()
        data = {
            "entity": {
                "name": "Imported",
                "entity_type": "company",
            },
            "profile": {
                "fields": {"email": "a@b.com"},
            },
        }
        r = orch.import_entity(data)
        assert r["imported"] is True
        assert r["name"] == "Imported"

    def test_get_analytics(self) -> None:
        orch = EntityMemOrchestrator()
        orch.create_entity("A")
        orch.create_entity("B")
        a = orch.get_analytics()
        assert a["total_entities"] == 2
        assert a["total_profiles"] == 2
        assert a["operations"] == 2

    def test_get_status(self) -> None:
        orch = EntityMemOrchestrator()
        orch.create_entity("X")
        s = orch.get_status()
        assert s["total_entities"] == 1
        assert s["operations"] == 1

    def test_full_pipeline(self) -> None:
        """Tam pipeline testi."""
        orch = EntityMemOrchestrator()

        # Varlık oluştur
        fatih = orch.create_entity(
            "Fatih", "person",
            profile_data={
                "email": "fatih@test.com",
                "role": "CEO",
            },
        )
        fid = fatih["entity_id"]

        mapa = orch.create_entity(
            "Mapa Health", "company",
        )
        mid = mapa["entity_id"]

        # İlişki ekle
        orch.relationships.add_relationship(
            fid, mid, "owns", 1.0,
        )

        # Etkileşim kaydet
        orch.record_interaction(
            fid, "telegram", "Meeting tomorrow",
            sentiment=0.5,
        )

        # Bağlam al
        ctx = orch.get_entity_context(fid)
        assert ctx["entity_id"] == fid
        assert len(ctx["recent_interactions"]) == 1

        # Sorgu
        q = orch.query_entity(fid)
        assert q["entity"]["name"] == "Fatih"
        assert q["interaction_count"] == 1

        # Export
        exp = orch.export_entity(fid)
        assert exp["exported"] is True

        # Analytics
        a = orch.get_analytics()
        assert a["total_entities"] == 2
        assert a["total_relationships"] == 1


# ── Init ve Config Testleri ──────────────────


class TestEntityMemInit:
    """Init import testleri."""

    def test_all_imports(self) -> None:
        from app.core.entitymem import (
            EntityContextProvider,
            EntityMemOrchestrator,
            EntityPreferenceLearner,
            EntityPrivacyManager,
            EntityRegistry,
            InteractionLogger,
            ProfileBuilder,
            RelationshipMapper,
            TimelineBuilder,
        )
        assert EntityRegistry is not None
        assert ProfileBuilder is not None
        assert InteractionLogger is not None
        assert RelationshipMapper is not None
        assert TimelineBuilder is not None
        assert EntityPreferenceLearner is not None
        assert EntityContextProvider is not None
        assert EntityPrivacyManager is not None
        assert EntityMemOrchestrator is not None


class TestEntityMemConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings
        assert hasattr(settings, "entitymem_enabled")
        assert settings.entitymem_enabled is True
        assert settings.auto_merge_duplicates is False
        assert settings.retention_days == 365
        assert settings.privacy_mode == "standard"
        assert settings.max_interactions_stored == 10000
