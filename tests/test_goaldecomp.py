"""ATLAS Goal Decomposition & Self-Tasking testleri."""

import time

import pytest

from app.core.goaldecomp import (
    DecompositionEngine,
    GoalDecompOrchestrator,
    GoalParser,
    GoalValidator,
    PrerequisiteAnalyzer,
    ProgressSynthesizer,
    ReplanningEngine,
    SelfAssigner,
    TaskGenerator,
)
from app.models.goaldecomp_models import (
    AssignmentStrategy,
    DecompositionNode,
    DecompositionType,
    GoalDecompSnapshot,
    GoalRecord,
    GoalStatus,
    ReplanReason,
    TaskPriority,
    TaskSpec,
    ValidationResult,
)


# ── Model testleri ──


class TestGoalDecompModels:
    """Model testleri."""

    def test_goal_status_enum(self) -> None:
        assert GoalStatus.draft == "draft"
        assert GoalStatus.completed == "completed"
        assert GoalStatus.failed == "failed"

    def test_task_priority_enum(self) -> None:
        assert TaskPriority.critical == "critical"
        assert TaskPriority.low == "low"
        assert TaskPriority.optional == "optional"

    def test_decomposition_type_enum(self) -> None:
        assert DecompositionType.and_node == "and"
        assert DecompositionType.or_node == "or"
        assert DecompositionType.parallel == "parallel"

    def test_assignment_strategy_enum(self) -> None:
        assert (
            AssignmentStrategy.capability_match
            == "capability_match"
        )
        assert (
            AssignmentStrategy.load_balance
            == "load_balance"
        )

    def test_replan_reason_enum(self) -> None:
        assert ReplanReason.failure == "failure"
        assert ReplanReason.timeout == "timeout"
        assert (
            ReplanReason.opportunity
            == "opportunity"
        )

    def test_validation_result_enum(self) -> None:
        assert ValidationResult.valid == "valid"
        assert (
            ValidationResult.infeasible
            == "infeasible"
        )

    def test_goal_record(self) -> None:
        r = GoalRecord(
            description="Build feature",
            intent="create",
        )
        assert r.goal_id
        assert r.description == "Build feature"
        assert r.status == GoalStatus.draft

    def test_decomposition_node(self) -> None:
        n = DecompositionNode(
            goal_id="g1",
            description="Sub task",
        )
        assert n.node_id
        assert n.goal_id == "g1"
        assert n.node_type == DecompositionType.and_node

    def test_task_spec(self) -> None:
        t = TaskSpec(
            goal_id="g1",
            title="Do something",
            priority=TaskPriority.high,
        )
        assert t.task_id
        assert t.priority == TaskPriority.high

    def test_goaldecomp_snapshot(self) -> None:
        s = GoalDecompSnapshot(
            total_goals=5,
            total_tasks=20,
            completed_tasks=10,
            completion_pct=50.0,
        )
        assert s.total_goals == 5
        assert s.completion_pct == 50.0


# ── GoalParser testleri ──


class TestGoalParser:
    """GoalParser testleri."""

    def setup_method(self) -> None:
        self.parser = GoalParser()

    def test_parse_goal(self) -> None:
        result = self.parser.parse_goal(
            "g1",
            "Create a web application for users",
        )
        assert result["goal_id"] == "g1"
        assert result["intent"] == "create"
        assert result["is_clear"] is True

    def test_parse_intent_improve(self) -> None:
        result = self.parser.parse_goal(
            "g2",
            "Improve the system performance",
        )
        assert result["intent"] == "improve"

    def test_parse_intent_fix(self) -> None:
        result = self.parser.parse_goal(
            "g3",
            "Fix the login bug quickly",
        )
        assert result["intent"] == "fix"

    def test_parse_intent_analyze(self) -> None:
        result = self.parser.parse_goal(
            "g4",
            "Analyze the market data",
        )
        assert result["intent"] == "analyze"

    def test_parse_intent_general(self) -> None:
        result = self.parser.parse_goal(
            "g5",
            "Handle the request properly",
        )
        assert result["intent"] == "general"

    def test_parse_criteria(self) -> None:
        result = self.parser.parse_goal(
            "g6",
            "Must achieve 99% uptime",
        )
        assert len(result["success_criteria"]) > 0

    def test_parse_constraints_time(self) -> None:
        result = self.parser.parse_goal(
            "g7",
            "Deploy before the deadline",
        )
        assert "time" in result["constraints"]

    def test_parse_constraints_budget(self) -> None:
        result = self.parser.parse_goal(
            "g8",
            "Keep the budget under control",
        )
        assert "budget" in result["constraints"]

    def test_parse_constraints_quality(self) -> None:
        result = self.parser.parse_goal(
            "g9",
            "Ensure reliable and secure system",
        )
        assert "quality" in result["constraints"]

    def test_parse_ambiguity_brief(self) -> None:
        result = self.parser.parse_goal(
            "g10", "Do it",
        )
        assert not result["is_clear"]
        assert any(
            "too_brief" in a
            for a in result["ambiguities"]
        )

    def test_parse_ambiguity_vague(self) -> None:
        result = self.parser.parse_goal(
            "g11",
            "Do something with stuff and whatever",
        )
        assert not result["is_clear"]

    def test_resolve_ambiguity(self) -> None:
        self.parser.parse_goal(
            "g12", "Do it",
        )
        result = self.parser.resolve_ambiguity(
            "g12",
            {"too_brief": "Build a REST API"},
        )
        assert result["resolved"] == 1
        assert result["is_clear"] is True

    def test_resolve_ambiguity_not_found(self) -> None:
        result = self.parser.resolve_ambiguity(
            "nope", {},
        )
        assert "error" in result

    def test_get_parsed(self) -> None:
        self.parser.parse_goal("g13", "Build app")
        result = self.parser.get_parsed("g13")
        assert result["goal_id"] == "g13"

    def test_get_parsed_not_found(self) -> None:
        result = self.parser.get_parsed("nope")
        assert "error" in result

    def test_parse_count(self) -> None:
        self.parser.parse_goal("a", "Create X")
        self.parser.parse_goal("b", "Fix Y")
        assert self.parser.parse_count == 2


# ── DecompositionEngine testleri ──


class TestDecompositionEngine:
    """DecompositionEngine testleri."""

    def setup_method(self) -> None:
        self.engine = DecompositionEngine(
            max_depth=3,
        )

    def test_decompose(self) -> None:
        result = self.engine.decompose(
            "g1", "Build system",
            [
                {"description": "Design DB"},
                {"description": "Write API"},
                {"description": "Build UI"},
            ],
        )
        assert result["goal_id"] == "g1"
        assert result["node_count"] == 4
        assert result["leaf_count"] == 3
        assert result["decomposed"] is True

    def test_decompose_empty(self) -> None:
        result = self.engine.decompose(
            "g2", "Simple task", [],
        )
        assert result["node_count"] == 1
        assert result["leaf_count"] == 0

    def test_add_subtask(self) -> None:
        self.engine.decompose(
            "g3", "Root",
            [{"description": "Child1"}],
        )
        result = self.engine.add_subtask(
            "node_g3_0", "Sub-child",
        )
        assert result["added"] is True
        assert result["depth"] == 2

    def test_add_subtask_not_found(self) -> None:
        result = self.engine.add_subtask(
            "nope", "Task",
        )
        assert "error" in result

    def test_add_subtask_max_depth(self) -> None:
        self.engine.decompose(
            "g4", "Root",
            [{"description": "L1"}],
        )
        self.engine.add_subtask(
            "node_g4_0", "L2",
        )
        r2 = self.engine.add_subtask(
            "node_g4_0_0", "L3",
        )
        assert r2["depth"] == 3
        r3 = self.engine.add_subtask(
            "node_g4_0_0_0", "L4",
        )
        assert "error" in r3

    def test_find_parallel_opportunities(self) -> None:
        self.engine.decompose(
            "g5", "Root",
            [
                {"description": "A"},
                {"description": "B"},
                {
                    "description": "C",
                    "dependencies": [
                        "node_g5_0",
                    ],
                },
            ],
        )
        result = (
            self.engine
            .find_parallel_opportunities("g5")
        )
        assert result["independent_count"] == 2
        assert result["dependent_count"] == 1
        assert result["parallelism_ratio"] > 0

    def test_find_parallel_not_found(self) -> None:
        result = (
            self.engine
            .find_parallel_opportunities("nope")
        )
        assert "error" in result

    def test_find_critical_path(self) -> None:
        self.engine.decompose(
            "g6", "Root",
            [
                {"description": "A"},
                {
                    "description": "B",
                    "dependencies": [
                        "node_g6_0",
                    ],
                },
            ],
        )
        result = (
            self.engine
            .find_critical_path("g6")
        )
        assert result["path_length"] >= 1

    def test_find_critical_path_not_found(self) -> None:
        result = (
            self.engine
            .find_critical_path("nope")
        )
        assert "error" in result

    def test_get_node(self) -> None:
        self.engine.decompose(
            "g7", "Root", [],
        )
        result = self.engine.get_node(
            "node_g7_root",
        )
        assert result["goal_id"] == "g7"

    def test_get_node_not_found(self) -> None:
        result = self.engine.get_node("nope")
        assert "error" in result

    def test_get_tree(self) -> None:
        self.engine.decompose(
            "g8", "Root",
            [{"description": "A"}],
        )
        result = self.engine.get_tree("g8")
        assert result["goal_id"] == "g8"
        assert result["total_nodes"] == 2

    def test_get_tree_not_found(self) -> None:
        result = self.engine.get_tree("nope")
        assert "error" in result

    def test_decomposition_count(self) -> None:
        self.engine.decompose("a", "X", [])
        self.engine.decompose("b", "Y", [])
        assert self.engine.decomposition_count == 2

    def test_node_count(self) -> None:
        self.engine.decompose(
            "c", "Z",
            [
                {"description": "A"},
                {"description": "B"},
            ],
        )
        assert self.engine.node_count >= 3


# ── TaskGenerator testleri ──


class TestTaskGenerator:
    """TaskGenerator testleri."""

    def setup_method(self) -> None:
        self.gen = TaskGenerator()

    def test_generate_task(self) -> None:
        result = self.gen.generate_task(
            "g1", "n1", "Build API",
        )
        assert result["generated"] is True
        assert result["goal_id"] == "g1"

    def test_generate_unique_ids(self) -> None:
        r1 = self.gen.generate_task(
            "g1", "n1", "Task 1",
        )
        r2 = self.gen.generate_task(
            "g1", "n2", "Task 2",
        )
        assert r1["task_id"] != r2["task_id"]

    def test_set_acceptance_criteria(self) -> None:
        r = self.gen.generate_task(
            "g1", "n1", "Task",
        )
        result = (
            self.gen.set_acceptance_criteria(
                r["task_id"],
                ["API responds 200", "Tests pass"],
            )
        )
        assert result["updated"] is True
        assert result["criteria_count"] == 2

    def test_set_acceptance_not_found(self) -> None:
        result = (
            self.gen.set_acceptance_criteria(
                "nope", [],
            )
        )
        assert "error" in result

    def test_set_resources(self) -> None:
        r = self.gen.generate_task(
            "g1", "n1", "Task",
        )
        result = self.gen.set_resources(
            r["task_id"],
            [{"type": "cpu", "amount": 2}],
        )
        assert result["updated"] is True
        assert result["resource_count"] == 1

    def test_set_resources_not_found(self) -> None:
        result = self.gen.set_resources(
            "nope", [],
        )
        assert "error" in result

    def test_estimate_time(self) -> None:
        r = self.gen.generate_task(
            "g1", "n1", "Task",
        )
        result = self.gen.estimate_time(
            r["task_id"], 8.0, 0.8,
        )
        assert result["estimated_hours"] == 8.0
        assert result["optimistic"] < 8.0
        assert result["pessimistic"] > 8.0

    def test_estimate_time_not_found(self) -> None:
        result = self.gen.estimate_time(
            "nope", 5.0,
        )
        assert "error" in result

    def test_generate_from_nodes(self) -> None:
        nodes = [
            {
                "node_id": "n1",
                "description": "Task A",
                "is_leaf": True,
            },
            {
                "node_id": "n2",
                "description": "Task B",
                "is_leaf": True,
            },
            {
                "node_id": "n3",
                "description": "Not leaf",
                "is_leaf": False,
            },
        ]
        result = self.gen.generate_from_nodes(
            "g1", nodes,
        )
        assert result["tasks_generated"] == 2
        assert len(result["task_ids"]) == 2

    def test_get_task(self) -> None:
        r = self.gen.generate_task(
            "g1", "n1", "Task",
        )
        result = self.gen.get_task(
            r["task_id"],
        )
        assert result["title"] == "Task"

    def test_get_task_not_found(self) -> None:
        result = self.gen.get_task("nope")
        assert "error" in result

    def test_get_tasks_by_goal(self) -> None:
        self.gen.generate_task(
            "g1", "n1", "A",
        )
        self.gen.generate_task(
            "g1", "n2", "B",
        )
        self.gen.generate_task(
            "g2", "n3", "C",
        )
        tasks = self.gen.get_tasks_by_goal("g1")
        assert len(tasks) == 2

    def test_update_status(self) -> None:
        r = self.gen.generate_task(
            "g1", "n1", "Task",
        )
        result = self.gen.update_status(
            r["task_id"], "completed",
        )
        assert result["updated"] is True
        task = self.gen.get_task(r["task_id"])
        assert task["status"] == "completed"

    def test_update_status_not_found(self) -> None:
        result = self.gen.update_status(
            "nope", "done",
        )
        assert "error" in result

    def test_task_count(self) -> None:
        self.gen.generate_task("g1", "n1", "A")
        self.gen.generate_task("g1", "n2", "B")
        assert self.gen.task_count == 2

    def test_pending_count(self) -> None:
        r = self.gen.generate_task(
            "g1", "n1", "A",
        )
        self.gen.generate_task("g1", "n2", "B")
        self.gen.update_status(
            r["task_id"], "completed",
        )
        assert self.gen.pending_count == 1


# ── PrerequisiteAnalyzer testleri ──


class TestPrerequisiteAnalyzer:
    """PrerequisiteAnalyzer testleri."""

    def setup_method(self) -> None:
        self.analyzer = PrerequisiteAnalyzer()

    def test_analyze_dependencies(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": [],
            },
            {
                "task_id": "t2",
                "dependencies": ["t1"],
            },
            {
                "task_id": "t3",
                "dependencies": ["t1"],
            },
        ]
        result = (
            self.analyzer.analyze_dependencies(
                "g1", tasks,
            )
        )
        assert result["task_count"] == 3
        assert result["has_cycle"] is False
        assert "t1" in result["enablers"]

    def test_analyze_ordering(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": [],
            },
            {
                "task_id": "t2",
                "dependencies": [],
            },
        ]
        result = (
            self.analyzer.analyze_dependencies(
                "g2", tasks,
            )
        )
        assert len(result["ordering"]) == 2

    def test_detect_cycle(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": ["t2"],
            },
            {
                "task_id": "t2",
                "dependencies": ["t1"],
            },
        ]
        result = (
            self.analyzer.analyze_dependencies(
                "g3", tasks,
            )
        )
        assert result["has_cycle"] is True

    def test_find_blockers(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": [],
            },
            {
                "task_id": "t2",
                "dependencies": ["t1"],
            },
            {
                "task_id": "t3",
                "dependencies": ["t1"],
            },
        ]
        result = (
            self.analyzer.analyze_dependencies(
                "g4", tasks,
            )
        )
        assert "t1" in result["blockers"]

    def test_get_blocking_tasks(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": [],
            },
            {
                "task_id": "t2",
                "dependencies": ["t1"],
            },
        ]
        self.analyzer.analyze_dependencies(
            "g5", tasks,
        )
        result = (
            self.analyzer.get_blocking_tasks(
                "g5", "t2",
            )
        )
        assert "t1" in result["blocked_by"]

    def test_get_blocking_not_found(self) -> None:
        result = (
            self.analyzer.get_blocking_tasks(
                "nope", "t1",
            )
        )
        assert "error" in result

    def test_get_risk_dependencies(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": [],
            },
            {
                "task_id": "t2",
                "dependencies": ["t1"],
            },
            {
                "task_id": "t3",
                "dependencies": ["t1"],
            },
        ]
        self.analyzer.analyze_dependencies(
            "g6", tasks,
        )
        result = (
            self.analyzer
            .get_risk_dependencies("g6")
        )
        assert result["risk_count"] >= 1

    def test_get_risk_not_found(self) -> None:
        result = (
            self.analyzer
            .get_risk_dependencies("nope")
        )
        assert "error" in result

    def test_get_analysis(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "dependencies": [],
            },
        ]
        self.analyzer.analyze_dependencies(
            "g7", tasks,
        )
        result = self.analyzer.get_analysis(
            "g7",
        )
        assert result["goal_id"] == "g7"

    def test_get_analysis_not_found(self) -> None:
        result = self.analyzer.get_analysis(
            "nope",
        )
        assert "error" in result

    def test_analysis_count(self) -> None:
        self.analyzer.analyze_dependencies(
            "a", [{"task_id": "t1", "dependencies": []}],
        )
        self.analyzer.analyze_dependencies(
            "b", [{"task_id": "t2", "dependencies": []}],
        )
        assert self.analyzer.analysis_count == 2


# ── SelfAssigner testleri ──


class TestSelfAssigner:
    """SelfAssigner testleri."""

    def setup_method(self) -> None:
        self.assigner = SelfAssigner()
        self.assigner.register_agent(
            "agent1",
            ["python", "api", "testing"],
            max_concurrent=3,
        )
        self.assigner.register_agent(
            "agent2",
            ["javascript", "ui", "testing"],
            max_concurrent=2,
        )

    def test_register_agent(self) -> None:
        result = self.assigner.register_agent(
            "agent3", ["go"],
        )
        assert result["registered"] is True

    def test_assign_capability_match(self) -> None:
        result = self.assigner.assign_task(
            "t1",
            required_capabilities=["python", "api"],
            strategy="capability_match",
        )
        assert result["assigned"] is True
        assert result["agent_id"] == "agent1"

    def test_assign_load_balance(self) -> None:
        result = self.assigner.assign_task(
            "t2",
            strategy="load_balance",
        )
        assert result["assigned"] is True

    def test_assign_priority_first(self) -> None:
        result = self.assigner.assign_task(
            "t3",
            priority="critical",
            strategy="priority_first",
        )
        assert result["assigned"] is True

    def test_assign_no_agents(self) -> None:
        empty = SelfAssigner()
        result = empty.assign_task("t4")
        assert result["assigned"] is False
        assert result["reason"] == "no_agents"

    def test_assign_max_concurrent(self) -> None:
        # agent2 max_concurrent=2
        self.assigner.assign_task(
            "x1",
            required_capabilities=["javascript"],
            strategy="capability_match",
        )
        self.assigner.assign_task(
            "x2",
            required_capabilities=["javascript"],
            strategy="capability_match",
        )
        # agent2 is full, should go to agent1
        result = self.assigner.assign_task(
            "x3",
            required_capabilities=["javascript"],
            strategy="capability_match",
        )
        assert result["assigned"] is True

    def test_delegate_task(self) -> None:
        self.assigner.assign_task("t5")
        result = self.assigner.delegate_task(
            "t5", "agent1", "agent2",
            reason="overloaded",
        )
        assert result["delegated"] is True

    def test_delegate_not_found(self) -> None:
        result = self.assigner.delegate_task(
            "t6", "agent1", "nope",
        )
        assert "error" in result

    def test_complete_task(self) -> None:
        self.assigner.assign_task("t7")
        result = self.assigner.complete_task(
            "t7",
        )
        assert result["completed"] is True

    def test_complete_not_found(self) -> None:
        result = self.assigner.complete_task(
            "nope",
        )
        assert "error" in result

    def test_get_assignment(self) -> None:
        self.assigner.assign_task("t8")
        result = self.assigner.get_assignment(
            "t8",
        )
        assert result["task_id"] == "t8"

    def test_get_assignment_not_found(self) -> None:
        result = self.assigner.get_assignment(
            "nope",
        )
        assert "error" in result

    def test_get_agent_workload(self) -> None:
        self.assigner.assign_task("t9")
        result = (
            self.assigner.get_agent_workload(
                "agent1",
            )
        )
        assert result["current_tasks"] >= 0
        assert "utilization" in result

    def test_get_workload_not_found(self) -> None:
        result = (
            self.assigner.get_agent_workload(
                "nope",
            )
        )
        assert "error" in result

    def test_assignment_count(self) -> None:
        self.assigner.assign_task("a1")
        self.assigner.assign_task("a2")
        assert self.assigner.assignment_count == 2

    def test_delegation_count(self) -> None:
        self.assigner.assign_task("d1")
        self.assigner.delegate_task(
            "d1", "agent1", "agent2",
        )
        assert self.assigner.delegation_count == 1


# ── ProgressSynthesizer testleri ──


class TestProgressSynthesizer:
    """ProgressSynthesizer testleri."""

    def setup_method(self) -> None:
        self.synth = ProgressSynthesizer()

    def test_synthesize_progress(self) -> None:
        tasks = [
            {"status": "completed"},
            {"status": "in_progress"},
            {"status": "pending"},
        ]
        result = self.synth.synthesize_progress(
            "g1", tasks,
        )
        assert result["total_tasks"] == 3
        assert result["completed"] == 1
        assert result["in_progress"] == 1
        assert result["pending"] == 1
        assert abs(
            result["completion_pct"] - 33.3
        ) < 1

    def test_synthesize_empty(self) -> None:
        result = self.synth.synthesize_progress(
            "g2", [],
        )
        assert result["total_tasks"] == 0
        assert result["completion_pct"] == 0.0

    def test_synthesize_all_complete(self) -> None:
        tasks = [
            {"status": "completed"},
            {"status": "completed"},
        ]
        result = self.synth.synthesize_progress(
            "g3", tasks,
        )
        assert result["completion_pct"] == 100.0

    def test_identify_blockers_failed(self) -> None:
        tasks = [
            {
                "task_id": "t1",
                "title": "Bad task",
                "status": "failed",
            },
        ]
        result = self.synth.identify_blockers(
            "g4", tasks,
        )
        assert result["is_blocked"] is True
        assert result["blocker_count"] == 1

    def test_identify_blockers_none(self) -> None:
        tasks = [
            {"status": "completed"},
            {"status": "pending"},
        ]
        result = self.synth.identify_blockers(
            "g5", tasks,
        )
        assert result["is_blocked"] is False

    def test_calculate_eta(self) -> None:
        tasks = [
            {
                "status": "completed",
                "estimated_hours": 4.0,
            },
            {
                "status": "pending",
                "estimated_hours": 8.0,
            },
        ]
        result = self.synth.calculate_eta(
            "g6", tasks,
        )
        assert result["eta_hours"] == 8.0
        assert result["remaining_tasks"] == 1

    def test_calculate_eta_complete(self) -> None:
        tasks = [
            {"status": "completed"},
        ]
        result = self.synth.calculate_eta(
            "g7", tasks,
        )
        assert result["completed"] is True
        assert result["eta_hours"] == 0.0

    def test_calculate_eta_empty(self) -> None:
        result = self.synth.calculate_eta(
            "g8", [],
        )
        assert result["completed"] is True

    def test_generate_report(self) -> None:
        tasks = [
            {
                "status": "completed",
                "priority": "high",
                "estimated_hours": 2.0,
            },
            {
                "status": "pending",
                "priority": "medium",
                "estimated_hours": 4.0,
            },
        ]
        result = self.synth.generate_report(
            "g9", tasks,
        )
        assert result["goal_id"] == "g9"
        assert "progress" in result
        assert "blockers" in result
        assert "eta" in result
        assert result["health"] == "healthy"

    def test_get_progress(self) -> None:
        self.synth.synthesize_progress(
            "g10",
            [{"status": "completed"}],
        )
        result = self.synth.get_progress("g10")
        assert result["goal_id"] == "g10"

    def test_get_progress_not_found(self) -> None:
        result = self.synth.get_progress("nope")
        assert "error" in result

    def test_synthesis_count(self) -> None:
        self.synth.synthesize_progress(
            "a", [{"status": "pending"}],
        )
        self.synth.synthesize_progress(
            "b", [{"status": "pending"}],
        )
        assert self.synth.synthesis_count == 2


# ── ReplanningEngine testleri ──


class TestReplanningEngine:
    """ReplanningEngine testleri."""

    def setup_method(self) -> None:
        self.engine = ReplanningEngine()

    def test_replan_failure(self) -> None:
        result = self.engine.replan(
            "g1", "failure",
            failed_tasks=["t1", "t2"],
        )
        assert result["replanned"] is True
        assert result["action_count"] == 2
        assert result["actions"][0]["type"] == "retry"

    def test_replan_failure_empty(self) -> None:
        result = self.engine.replan(
            "g2", "failure",
        )
        assert result["actions"][0]["type"] == "investigate"

    def test_replan_scope_change_add(self) -> None:
        result = self.engine.replan(
            "g3", "scope_change",
            new_constraints={
                "added_tasks": ["t5", "t6"],
            },
        )
        assert result["actions"][0]["type"] == "add_tasks"

    def test_replan_scope_change_remove(self) -> None:
        result = self.engine.replan(
            "g4", "scope_change",
            new_constraints={
                "removed_tasks": ["t7"],
            },
        )
        assert result["actions"][0]["type"] == "remove_tasks"

    def test_replan_scope_change_generic(self) -> None:
        result = self.engine.replan(
            "g5", "scope_change",
        )
        assert result["actions"][0]["type"] == "reassess"

    def test_replan_resource_budget(self) -> None:
        result = self.engine.replan(
            "g6", "resource_change",
            new_constraints={
                "reduced_budget": True,
            },
        )
        assert result["actions"][0]["type"] == "reprioritize"

    def test_replan_resource_time(self) -> None:
        result = self.engine.replan(
            "g7", "resource_change",
            new_constraints={
                "reduced_time": True,
            },
        )
        assert result["actions"][0]["type"] == "parallelize"

    def test_replan_resource_generic(self) -> None:
        result = self.engine.replan(
            "g8", "resource_change",
        )
        assert result["actions"][0]["type"] == "reallocate"

    def test_replan_opportunity(self) -> None:
        result = self.engine.replan(
            "g9", "opportunity",
        )
        assert result["actions"][0]["type"] == "evaluate"

    def test_replan_opportunity_shortcut(self) -> None:
        result = self.engine.replan(
            "g10", "opportunity",
            new_constraints={"shortcut": True},
        )
        assert any(
            a["type"] == "shortcut"
            for a in result["actions"]
        )

    def test_replan_timeout(self) -> None:
        result = self.engine.replan(
            "g11", "timeout",
            failed_tasks=["t10"],
        )
        assert result["actions"][0]["type"] == "simplify"

    def test_replan_timeout_empty(self) -> None:
        result = self.engine.replan(
            "g12", "timeout",
        )
        assert result["actions"][0]["type"] == "extend_deadline"

    def test_replan_unknown_reason(self) -> None:
        result = self.engine.replan(
            "g13", "unknown_reason",
        )
        assert result["actions"][0]["type"] == "review"

    def test_get_replan_history(self) -> None:
        self.engine.replan(
            "g14", "failure",
            failed_tasks=["t1"],
        )
        self.engine.replan(
            "g14", "scope_change",
        )
        result = self.engine.get_replan_history(
            "g14",
        )
        assert result["replan_count"] == 2

    def test_get_history_empty(self) -> None:
        result = self.engine.get_replan_history(
            "nope",
        )
        assert result["replan_count"] == 0

    def test_get_latest_replan(self) -> None:
        self.engine.replan(
            "g15", "failure",
        )
        self.engine.replan(
            "g15", "timeout",
        )
        result = self.engine.get_latest_replan(
            "g15",
        )
        assert result["reason"] == "timeout"

    def test_get_latest_not_found(self) -> None:
        result = self.engine.get_latest_replan(
            "nope",
        )
        assert "error" in result

    def test_replan_count(self) -> None:
        self.engine.replan("a", "failure")
        self.engine.replan("b", "timeout")
        assert self.engine.replan_count == 2


# ── GoalValidator testleri ──


class TestGoalValidator:
    """GoalValidator testleri."""

    def setup_method(self) -> None:
        self.validator = GoalValidator()

    def test_validate_valid(self) -> None:
        result = self.validator.validate_goal(
            "g1",
            "Build a REST API for user management",
        )
        assert result["result"] == "valid"

    def test_validate_infeasible(self) -> None:
        result = self.validator.validate_goal(
            "g2",
            "Solve all problems in the world with infinite resources",
        )
        assert result["result"] == "invalid"

    def test_validate_too_brief(self) -> None:
        result = self.validator.validate_goal(
            "g3", "Do",
        )
        assert result["result"] == "invalid"

    def test_validate_empty(self) -> None:
        result = self.validator.validate_goal(
            "g4", "",
        )
        assert result["result"] == "invalid"

    def test_validate_with_resources(self) -> None:
        result = self.validator.validate_goal(
            "g5",
            "Build a microservice architecture",
            available_resources={
                "budget": 1000,
                "agents": 3,
            },
        )
        assert result["result"] == "valid"

    def test_validate_insufficient_resources(self) -> None:
        result = self.validator.validate_goal(
            "g6",
            "Build a system quickly",
            available_resources={
                "budget": 0,
                "agents": 0,
            },
        )
        assert result["result"] == "invalid"

    def test_validate_with_timeline(self) -> None:
        result = self.validator.validate_goal(
            "g7",
            "Complete the migration project",
            deadline_hours=48.0,
        )
        assert result["result"] == "valid"

    def test_validate_invalid_timeline(self) -> None:
        result = self.validator.validate_goal(
            "g8",
            "Build a great product",
            deadline_hours=-1.0,
        )
        assert result["result"] == "invalid"

    def test_validate_consistency(self) -> None:
        result = self.validator.validate_goal(
            "g9",
            "Build it properly",
            constraints=["fast", "cheap"],
        )
        assert result["result"] == "invalid"

    def test_get_validation(self) -> None:
        self.validator.validate_goal(
            "g10", "Build API endpoint",
        )
        result = self.validator.get_validation(
            "g10",
        )
        assert result["goal_id"] == "g10"

    def test_get_validation_not_found(self) -> None:
        result = self.validator.get_validation(
            "nope",
        )
        assert "error" in result

    def test_validation_count(self) -> None:
        self.validator.validate_goal(
            "a", "Create something useful",
        )
        self.validator.validate_goal(
            "b", "Fix the bug in the system",
        )
        assert self.validator.validation_count == 2

    def test_pass_rate(self) -> None:
        self.validator.validate_goal(
            "x", "Build a web app for users",
        )
        self.validator.validate_goal(
            "y", "",
        )
        assert self.validator.pass_rate == 50.0

    def test_pass_rate_empty(self) -> None:
        assert self.validator.pass_rate == 0.0


# ── GoalDecompOrchestrator testleri ──


class TestGoalDecompOrchestrator:
    """GoalDecompOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = GoalDecompOrchestrator(
            max_depth=5,
            auto_assign=False,
            validate_first=True,
        )

    def test_init(self) -> None:
        assert self.orch.parser is not None
        assert self.orch.decomposer is not None
        assert self.orch.generator is not None

    def test_process_goal(self) -> None:
        result = self.orch.process_goal(
            "g1",
            "Build a REST API for users",
            [
                {"description": "Design schema"},
                {"description": "Implement endpoints"},
                {"description": "Write tests"},
            ],
        )
        assert result["pipeline_completed"] is True
        assert result["status"] == "processed"
        assert result["tasks_generated"] == 3

    def test_process_goal_invalid(self) -> None:
        result = self.orch.process_goal(
            "g2", "",
            [],
        )
        assert result["pipeline_completed"] is False
        assert result["status"] == "invalid"

    def test_process_no_validate(self) -> None:
        orch = GoalDecompOrchestrator(
            validate_first=False,
        )
        result = orch.process_goal(
            "g3", "X",
            [{"description": "A"}],
        )
        assert result["pipeline_completed"] is True

    def test_process_auto_assign(self) -> None:
        orch = GoalDecompOrchestrator(
            auto_assign=True,
            validate_first=False,
        )
        orch.assigner.register_agent(
            "a1", ["general"],
        )
        result = orch.process_goal(
            "g4", "Build feature",
            [{"description": "Task A"}],
        )
        assert result["tasks_assigned"] >= 1

    def test_get_goal_status(self) -> None:
        self.orch.process_goal(
            "g5", "Build API system",
            [
                {"description": "Design"},
                {"description": "Build"},
            ],
        )
        result = self.orch.get_goal_status("g5")
        assert result["task_count"] == 2
        assert "progress" in result

    def test_handle_failure(self) -> None:
        result = self.orch.handle_failure(
            "g6", ["t1"],
        )
        assert result["handled"] is True
        assert "replan" in result

    def test_get_analytics(self) -> None:
        self.orch.process_goal(
            "g7", "Build something great",
            [{"description": "Task"}],
        )
        result = self.orch.get_analytics()
        assert result["pipelines_run"] >= 1
        assert result["goals_parsed"] >= 1

    def test_get_status(self) -> None:
        result = self.orch.get_status()
        assert "pipelines_run" in result
        assert "total_nodes" in result
        assert "total_tasks" in result

    def test_pipelines_run(self) -> None:
        self.orch.process_goal(
            "g8", "Create a web service",
            [{"description": "A"}],
        )
        assert self.orch.pipelines_run >= 1

    def test_full_integration(self) -> None:
        orch = GoalDecompOrchestrator(
            auto_assign=True,
            validate_first=True,
        )
        orch.assigner.register_agent(
            "bot", ["python", "api"],
        )

        result = orch.process_goal(
            "int1",
            "Deploy the monitoring system",
            [
                {"description": "Setup infra"},
                {"description": "Configure alerts"},
                {"description": "Run tests"},
            ],
        )

        assert result["pipeline_completed"] is True
        assert result["tasks_generated"] == 3
        assert result["tasks_assigned"] == 3

        status = orch.get_goal_status("int1")
        assert status["task_count"] == 3

        analytics = orch.get_analytics()
        assert analytics["pipelines_run"] >= 1


# ── Init & Config testleri ──


class TestGoalDecompInit:
    """Init import testleri."""

    def test_imports(self) -> None:
        from app.core.goaldecomp import (
            DecompositionEngine,
            GoalDecompOrchestrator,
            GoalParser,
            GoalValidator,
            PrerequisiteAnalyzer,
            ProgressSynthesizer,
            ReplanningEngine,
            SelfAssigner,
            TaskGenerator,
        )
        assert GoalParser is not None
        assert DecompositionEngine is not None
        assert TaskGenerator is not None
        assert PrerequisiteAnalyzer is not None
        assert SelfAssigner is not None
        assert ProgressSynthesizer is not None
        assert ReplanningEngine is not None
        assert GoalValidator is not None
        assert GoalDecompOrchestrator is not None

    def test_instantiate_all(self) -> None:
        assert GoalParser()
        assert DecompositionEngine()
        assert TaskGenerator()
        assert PrerequisiteAnalyzer()
        assert SelfAssigner()
        assert ProgressSynthesizer()
        assert ReplanningEngine()
        assert GoalValidator()
        assert GoalDecompOrchestrator()


class TestGoalDecompConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings

        assert settings.goaldecomp_enabled is True
        assert settings.max_decomposition_depth == 5
        assert settings.auto_assign_tasks is False
        assert settings.replan_on_failure is True
        assert settings.validate_before_execute is True
