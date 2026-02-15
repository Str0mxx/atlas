"""ATLAS Self-Benchmarking Framework testleri.

KPIDefiner, BenchmarkMetricCollector, PerformanceScorer,
BenchmarkTrendAnalyzer, ABTester, ComparisonEngine,
BenchmarkReportGenerator, BenchmarkAlertManager,
BenchmarkOrchestrator testleri.
"""

import time
import unittest

from app.models.benchmark_models import (
    AlertRecord,
    AlertSeverity,
    BenchmarkResult,
    BenchmarkSnapshot,
    ExperimentPhase,
    KPICategory,
    KPIRecord,
    MetricType,
    ReportType,
    TrendDirection,
)


class TestBenchmarkModels(unittest.TestCase):
    """Benchmark model testleri."""

    def test_kpi_category_values(self):
        self.assertEqual(
            KPICategory.SYSTEM, "system",
        )
        self.assertEqual(
            KPICategory.AGENT, "agent",
        )
        self.assertEqual(
            KPICategory.BUSINESS, "business",
        )
        self.assertEqual(
            KPICategory.QUALITY, "quality",
        )
        self.assertEqual(
            KPICategory.CUSTOM, "custom",
        )

    def test_metric_type_values(self):
        self.assertEqual(
            MetricType.COUNTER, "counter",
        )
        self.assertEqual(
            MetricType.GAUGE, "gauge",
        )
        self.assertEqual(
            MetricType.HISTOGRAM, "histogram",
        )
        self.assertEqual(
            MetricType.RATE, "rate",
        )
        self.assertEqual(
            MetricType.PERCENTAGE, "percentage",
        )

    def test_trend_direction_values(self):
        self.assertEqual(
            TrendDirection.IMPROVING, "improving",
        )
        self.assertEqual(
            TrendDirection.STABLE, "stable",
        )
        self.assertEqual(
            TrendDirection.DEGRADING, "degrading",
        )
        self.assertEqual(
            TrendDirection.ANOMALY, "anomaly",
        )
        self.assertEqual(
            TrendDirection.INSUFFICIENT,
            "insufficient",
        )

    def test_alert_severity_values(self):
        self.assertEqual(
            AlertSeverity.CRITICAL, "critical",
        )
        self.assertEqual(
            AlertSeverity.WARNING, "warning",
        )
        self.assertEqual(
            AlertSeverity.INFO, "info",
        )
        self.assertEqual(
            AlertSeverity.IMPROVEMENT,
            "improvement",
        )
        self.assertEqual(
            AlertSeverity.DEGRADATION,
            "degradation",
        )

    def test_report_type_values(self):
        self.assertEqual(
            ReportType.PERFORMANCE, "performance",
        )
        self.assertEqual(
            ReportType.TREND, "trend",
        )
        self.assertEqual(
            ReportType.COMPARISON, "comparison",
        )
        self.assertEqual(
            ReportType.EXECUTIVE, "executive",
        )
        self.assertEqual(
            ReportType.DETAILED, "detailed",
        )

    def test_experiment_phase_values(self):
        self.assertEqual(
            ExperimentPhase.SETUP, "setup",
        )
        self.assertEqual(
            ExperimentPhase.RUNNING, "running",
        )
        self.assertEqual(
            ExperimentPhase.ANALYZING, "analyzing",
        )
        self.assertEqual(
            ExperimentPhase.COMPLETED, "completed",
        )
        self.assertEqual(
            ExperimentPhase.CANCELLED, "cancelled",
        )

    def test_kpi_record_defaults(self):
        r = KPIRecord()
        self.assertTrue(len(r.kpi_id) > 0)
        self.assertEqual(r.name, "")
        self.assertEqual(
            r.category, KPICategory.CUSTOM,
        )
        self.assertEqual(r.target, 0.0)
        self.assertEqual(r.threshold, 0.0)
        self.assertEqual(r.unit, "")
        self.assertIsInstance(r.metadata, dict)
        self.assertIsNotNone(r.created_at)

    def test_kpi_record_custom(self):
        r = KPIRecord(
            kpi_id="k1",
            name="Uptime",
            category=KPICategory.SYSTEM,
            target=99.9,
            threshold=95.0,
            unit="%",
        )
        self.assertEqual(r.kpi_id, "k1")
        self.assertEqual(r.name, "Uptime")
        self.assertEqual(
            r.category, KPICategory.SYSTEM,
        )
        self.assertEqual(r.target, 99.9)

    def test_benchmark_result_defaults(self):
        r = BenchmarkResult()
        self.assertTrue(len(r.result_id) > 0)
        self.assertEqual(r.kpi_id, "")
        self.assertEqual(r.score, 0.0)
        self.assertFalse(r.target_met)
        self.assertIsNotNone(r.measured_at)

    def test_benchmark_result_custom(self):
        r = BenchmarkResult(
            result_id="r1",
            kpi_id="k1",
            score=0.95,
            target_met=True,
            period="daily",
        )
        self.assertEqual(r.result_id, "r1")
        self.assertEqual(r.score, 0.95)
        self.assertTrue(r.target_met)

    def test_alert_record_defaults(self):
        r = AlertRecord()
        self.assertTrue(len(r.alert_id) > 0)
        self.assertEqual(
            r.severity, AlertSeverity.INFO,
        )
        self.assertFalse(r.acknowledged)
        self.assertIsNotNone(r.created_at)

    def test_alert_record_custom(self):
        r = AlertRecord(
            alert_id="a1",
            kpi_id="k1",
            severity=AlertSeverity.CRITICAL,
            message="CPU high",
            acknowledged=True,
        )
        self.assertEqual(r.alert_id, "a1")
        self.assertEqual(
            r.severity, AlertSeverity.CRITICAL,
        )
        self.assertTrue(r.acknowledged)

    def test_benchmark_snapshot_defaults(self):
        s = BenchmarkSnapshot()
        self.assertEqual(s.total_kpis, 0)
        self.assertEqual(s.targets_met, 0)
        self.assertEqual(s.active_experiments, 0)
        self.assertEqual(s.active_alerts, 0)
        self.assertEqual(s.avg_score, 0.0)
        self.assertIsNotNone(s.timestamp)

    def test_benchmark_snapshot_custom(self):
        s = BenchmarkSnapshot(
            total_kpis=10,
            targets_met=8,
            active_experiments=2,
            avg_score=0.85,
            trend="improving",
        )
        self.assertEqual(s.total_kpis, 10)
        self.assertEqual(s.targets_met, 8)
        self.assertEqual(s.avg_score, 0.85)


class TestKPIDefiner(unittest.TestCase):
    """KPIDefiner testleri."""

    def setUp(self):
        from app.core.benchmark.kpi_definer import (
            KPIDefiner,
        )
        self.definer = KPIDefiner()

    def test_define_kpi(self):
        r = self.definer.define_kpi(
            "k1", "Uptime",
            category="system", unit="%",
        )
        self.assertTrue(r["defined"])
        self.assertEqual(r["kpi_id"], "k1")
        self.assertEqual(r["name"], "Uptime")

    def test_kpi_count(self):
        self.assertEqual(self.definer.kpi_count, 0)
        self.definer.define_kpi("k1", "A")
        self.assertEqual(self.definer.kpi_count, 1)
        self.definer.define_kpi("k2", "B")
        self.assertEqual(self.definer.kpi_count, 2)

    def test_get_kpi(self):
        self.definer.define_kpi(
            "k1", "Uptime",
            category="system",
        )
        kpi = self.definer.get_kpi("k1")
        self.assertIsNotNone(kpi)
        self.assertEqual(kpi["name"], "Uptime")

    def test_get_kpi_not_found(self):
        r = self.definer.get_kpi("nonexistent")
        self.assertIsNone(r)

    def test_set_target(self):
        self.definer.define_kpi("k1", "Uptime")
        r = self.definer.set_target("k1", 99.9)
        self.assertTrue(r["set"])
        self.assertEqual(r["target"], 99.9)
        # Threshold otomatik %80
        self.assertAlmostEqual(
            r["threshold"], 99.9 * 0.8, places=2,
        )

    def test_set_target_custom_threshold(self):
        self.definer.define_kpi("k1", "Uptime")
        r = self.definer.set_target(
            "k1", 100.0, threshold=95.0,
        )
        self.assertEqual(r["threshold"], 95.0)

    def test_set_target_not_found(self):
        r = self.definer.set_target("no", 50.0)
        self.assertIn("error", r)

    def test_define_system_kpis(self):
        results = self.definer.define_system_kpis()
        self.assertEqual(len(results), 5)
        self.assertEqual(self.definer.kpi_count, 5)

    def test_define_agent_kpis(self):
        results = self.definer.define_agent_kpis()
        self.assertEqual(len(results), 4)
        self.assertEqual(self.definer.kpi_count, 4)

    def test_get_by_category(self):
        self.definer.define_kpi(
            "k1", "A", category="system",
        )
        self.definer.define_kpi(
            "k2", "B", category="system",
        )
        self.definer.define_kpi(
            "k3", "C", category="agent",
        )
        system = self.definer.get_by_category("system")
        self.assertEqual(len(system), 2)
        agent = self.definer.get_by_category("agent")
        self.assertEqual(len(agent), 1)

    def test_list_kpis(self):
        self.definer.define_kpi("k1", "A")
        self.definer.define_kpi("k2", "B")
        all_kpis = self.definer.list_kpis()
        self.assertEqual(len(all_kpis), 2)

    def test_remove_kpi(self):
        self.definer.define_kpi(
            "k1", "A", category="system",
        )
        r = self.definer.remove_kpi("k1")
        self.assertTrue(r["removed"])
        self.assertEqual(self.definer.kpi_count, 0)

    def test_remove_kpi_not_found(self):
        r = self.definer.remove_kpi("no")
        self.assertIn("error", r)

    def test_category_count(self):
        self.definer.define_kpi(
            "k1", "A", category="system",
        )
        self.definer.define_kpi(
            "k2", "B", category="agent",
        )
        self.assertEqual(
            self.definer.category_count, 2,
        )

    def test_define_both_kpi_sets(self):
        self.definer.define_system_kpis()
        self.definer.define_agent_kpis()
        self.assertEqual(self.definer.kpi_count, 9)


class TestBenchmarkMetricCollector(unittest.TestCase):
    """BenchmarkMetricCollector testleri."""

    def setUp(self):
        from app.core.benchmark.metric_collector import (
            BenchmarkMetricCollector,
        )
        self.collector = BenchmarkMetricCollector()

    def test_collect(self):
        r = self.collector.collect("k1", 95.5)
        self.assertTrue(r["collected"])
        self.assertEqual(r["kpi_id"], "k1")
        self.assertEqual(r["value"], 95.5)

    def test_collect_with_tags(self):
        r = self.collector.collect(
            "k1", 50.0,
            tags={"env": "prod"},
        )
        self.assertTrue(r["collected"])

    def test_metric_count(self):
        self.assertEqual(
            self.collector.metric_count, 0,
        )
        self.collector.collect("k1", 10.0)
        self.assertEqual(
            self.collector.metric_count, 1,
        )
        self.collector.collect("k2", 20.0)
        self.assertEqual(
            self.collector.metric_count, 2,
        )

    def test_get_latest(self):
        self.collector.collect("k1", 10.0)
        self.collector.collect("k1", 20.0)
        latest = self.collector.get_latest("k1")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["value"], 20.0)

    def test_get_latest_none(self):
        r = self.collector.get_latest("no")
        self.assertIsNone(r)

    def test_get_history(self):
        for i in range(5):
            self.collector.collect("k1", float(i))
        history = self.collector.get_history("k1")
        self.assertEqual(len(history), 5)

    def test_get_history_limit(self):
        for i in range(10):
            self.collector.collect("k1", float(i))
        history = self.collector.get_history(
            "k1", limit=3,
        )
        self.assertEqual(len(history), 3)

    def test_get_history_empty(self):
        history = self.collector.get_history("no")
        self.assertEqual(len(history), 0)

    def test_aggregate(self):
        for i in range(5):
            self.collector.collect("k1", float(i + 1))
        agg = self.collector.aggregate(
            "k1", period_seconds=9999,
        )
        self.assertEqual(agg["count"], 5)
        self.assertEqual(agg["avg"], 3.0)
        self.assertEqual(agg["min"], 1.0)
        self.assertEqual(agg["max"], 5.0)
        self.assertEqual(agg["sum"], 15.0)

    def test_aggregate_empty(self):
        agg = self.collector.aggregate("no")
        self.assertEqual(agg["count"], 0)

    def test_sample(self):
        for i in range(10):
            self.collector.collect("k1", float(i))
        samples = self.collector.sample("k1", count=3)
        self.assertEqual(len(samples), 3)

    def test_sample_empty(self):
        samples = self.collector.sample("no")
        self.assertEqual(len(samples), 0)

    def test_total_samples(self):
        self.collector.collect("k1", 10.0)
        self.collector.collect("k1", 20.0)
        self.collector.collect("k2", 30.0)
        self.assertEqual(
            self.collector.total_samples, 3,
        )

    def test_get_all_latest(self):
        self.collector.collect("k1", 10.0)
        self.collector.collect("k2", 20.0)
        latest = self.collector.get_all_latest()
        self.assertEqual(len(latest), 2)
        self.assertEqual(latest["k1"]["value"], 10.0)
        self.assertEqual(latest["k2"]["value"], 20.0)

    def test_max_samples_limit(self):
        from app.core.benchmark.metric_collector import (
            BenchmarkMetricCollector,
        )
        collector = BenchmarkMetricCollector(
            max_samples=5,
        )
        for i in range(10):
            collector.collect("k1", float(i))
        history = collector.get_history("k1")
        self.assertEqual(len(history), 5)


class TestPerformanceScorer(unittest.TestCase):
    """PerformanceScorer testleri."""

    def setUp(self):
        from app.core.benchmark.performance_scorer import (
            PerformanceScorer,
        )
        self.scorer = PerformanceScorer()

    def test_score_basic(self):
        r = self.scorer.score("k1", 80.0, 100.0)
        self.assertEqual(r["score"], 0.8)
        self.assertFalse(r["meets_target"])

    def test_score_meets_target(self):
        r = self.scorer.score("k1", 100.0, 100.0)
        self.assertEqual(r["score"], 1.0)
        self.assertTrue(r["meets_target"])

    def test_score_exceeds_target(self):
        r = self.scorer.score("k1", 120.0, 100.0)
        self.assertEqual(r["score"], 1.0)
        self.assertTrue(r["meets_target"])

    def test_score_zero_target(self):
        r = self.scorer.score("k1", 0.0, 0.0)
        self.assertEqual(r["score"], 1.0)

    def test_score_zero_target_nonzero_value(self):
        r = self.scorer.score("k1", 50.0, 0.0)
        self.assertEqual(r["score"], 0.0)

    def test_score_meets_threshold(self):
        r = self.scorer.score(
            "k1", 85.0, 100.0, threshold=80.0,
        )
        self.assertTrue(r["meets_threshold"])
        self.assertFalse(r["meets_target"])

    def test_score_below_threshold(self):
        r = self.scorer.score(
            "k1", 75.0, 100.0, threshold=80.0,
        )
        self.assertFalse(r["meets_threshold"])

    def test_total_scores(self):
        self.assertEqual(self.scorer.total_scores, 0)
        self.scorer.score("k1", 80.0, 100.0)
        self.assertEqual(self.scorer.total_scores, 1)

    def test_weighted_score(self):
        scores = {"k1": 0.8, "k2": 0.6}
        weights = {"k1": 2.0, "k2": 1.0}
        r = self.scorer.weighted_score(
            scores, weights,
        )
        # (0.8*2 + 0.6*1) / 3 = 2.2/3 = 0.7333
        self.assertAlmostEqual(
            r["overall_score"], 0.7333, places=3,
        )

    def test_weighted_score_default_weights(self):
        scores = {"k1": 0.8, "k2": 0.6}
        r = self.scorer.weighted_score(scores)
        # default weight=1.0, (0.8+0.6)/2 = 0.7
        self.assertAlmostEqual(
            r["overall_score"], 0.7, places=3,
        )

    def test_normalize(self):
        values = {"k1": 10.0, "k2": 50.0, "k3": 30.0}
        r = self.scorer.normalize(values)
        self.assertEqual(r["k1"], 0.0)
        self.assertEqual(r["k2"], 1.0)
        self.assertEqual(r["k3"], 0.5)

    def test_normalize_empty(self):
        r = self.scorer.normalize({})
        self.assertEqual(r, {})

    def test_normalize_all_same(self):
        values = {"k1": 5.0, "k2": 5.0}
        r = self.scorer.normalize(values)
        self.assertEqual(r["k1"], 1.0)
        self.assertEqual(r["k2"], 1.0)

    def test_compare(self):
        r = self.scorer.compare(
            "k1", 100.0, 80.0,
        )
        self.assertEqual(r["winner"], "a")
        self.assertAlmostEqual(
            r["pct_diff"], 25.0, places=1,
        )

    def test_compare_b_wins(self):
        r = self.scorer.compare(
            "k1", 50.0, 80.0,
        )
        self.assertEqual(r["winner"], "b")

    def test_compare_tie(self):
        r = self.scorer.compare(
            "k1", 50.0, 50.0,
        )
        self.assertEqual(r["winner"], "tie")

    def test_rank(self):
        scores = {"A": 0.9, "B": 0.7, "C": 0.95}
        ranking = self.scorer.rank(scores)
        self.assertEqual(ranking[0]["name"], "C")
        self.assertEqual(ranking[0]["rank"], 1)
        self.assertEqual(ranking[1]["name"], "A")
        self.assertEqual(ranking[2]["name"], "B")

    def test_set_weight_and_use(self):
        self.scorer.set_weight("k1", 3.0)
        self.scorer.set_weight("k2", 1.0)
        scores = {"k1": 0.9, "k2": 0.5}
        r = self.scorer.weighted_score(scores)
        # (0.9*3 + 0.5*1) / 4 = 3.2/4 = 0.8
        self.assertAlmostEqual(
            r["overall_score"], 0.8, places=3,
        )

    def test_get_scores(self):
        self.scorer.score("k1", 80.0, 100.0)
        self.scorer.score("k1", 90.0, 100.0)
        history = self.scorer.get_scores("k1")
        self.assertEqual(len(history), 2)

    def test_get_scores_empty(self):
        r = self.scorer.get_scores("no")
        self.assertEqual(len(r), 0)

    def test_scored_kpi_count(self):
        self.scorer.score("k1", 80.0, 100.0)
        self.scorer.score("k2", 70.0, 100.0)
        self.assertEqual(
            self.scorer.scored_kpi_count, 2,
        )


class TestBenchmarkTrendAnalyzer(unittest.TestCase):
    """BenchmarkTrendAnalyzer testleri."""

    def setUp(self):
        from app.core.benchmark.trend_analyzer import (
            BenchmarkTrendAnalyzer,
        )
        self.analyzer = BenchmarkTrendAnalyzer()

    def test_add_data_point(self):
        r = self.analyzer.add_data_point("k1", 10.0)
        self.assertTrue(r["added"])
        self.assertEqual(r["count"], 1)

    def test_add_multiple_data_points(self):
        self.analyzer.add_data_point("k1", 10.0)
        r = self.analyzer.add_data_point("k1", 20.0)
        self.assertEqual(r["count"], 2)

    def test_analyze_trend_insufficient(self):
        self.analyzer.add_data_point("k1", 10.0)
        r = self.analyzer.analyze_trend("k1")
        self.assertEqual(
            r["direction"], "insufficient",
        )

    def test_analyze_trend_improving(self):
        # Ilk yari dusuk, ikinci yari yuksek
        for v in [10, 12, 14, 16, 50, 55, 60, 65]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        r = self.analyzer.analyze_trend("k1")
        self.assertEqual(r["direction"], "improving")
        self.assertGreater(r["change_pct"], 10)

    def test_analyze_trend_degrading(self):
        for v in [90, 85, 80, 75, 40, 35, 30, 25]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        r = self.analyzer.analyze_trend("k1")
        self.assertEqual(r["direction"], "degrading")
        self.assertLess(r["change_pct"], -10)

    def test_analyze_trend_stable(self):
        for v in [50, 51, 49, 50, 50, 51, 49, 50]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        r = self.analyzer.analyze_trend("k1")
        self.assertEqual(r["direction"], "stable")

    def test_detect_degradation(self):
        for v in [90, 88, 92, 89, 91,
                   50, 48, 52, 47, 51]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        r = self.analyzer.detect_degradation("k1")
        self.assertTrue(r["degrading"])

    def test_detect_degradation_insufficient(self):
        self.analyzer.add_data_point("k1", 10.0)
        r = self.analyzer.detect_degradation("k1")
        self.assertFalse(r["degrading"])

    def test_detect_degradation_no_degradation(self):
        for v in [50, 51, 52, 53, 54,
                   55, 56, 57, 58, 59]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        r = self.analyzer.detect_degradation("k1")
        self.assertFalse(r["degrading"])

    def test_detect_anomaly(self):
        # Normal degerler
        for v in [50, 51, 49, 50, 50]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        # Anomali deger
        r = self.analyzer.detect_anomaly("k1", 200.0)
        self.assertTrue(r["is_anomaly"])

    def test_detect_anomaly_insufficient(self):
        self.analyzer.add_data_point("k1", 10.0)
        r = self.analyzer.detect_anomaly("k1", 20.0)
        self.assertFalse(r["is_anomaly"])

    def test_detect_anomaly_normal(self):
        for v in [50, 51, 49, 50, 50]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        r = self.analyzer.detect_anomaly("k1", 50.5)
        self.assertFalse(r["is_anomaly"])

    def test_forecast(self):
        for i in range(10):
            self.analyzer.add_data_point(
                "k1", float(i * 10),
            )
        r = self.analyzer.forecast("k1", steps=3)
        self.assertTrue(r["forecasted"])
        self.assertEqual(len(r["predictions"]), 3)
        # Yukselen trend - tahminler artmali
        self.assertGreater(
            r["predictions"][-1],
            r["predictions"][0],
        )

    def test_forecast_insufficient(self):
        self.analyzer.add_data_point("k1", 10.0)
        r = self.analyzer.forecast("k1")
        self.assertFalse(r["forecasted"])

    def test_get_anomalies(self):
        for v in [50, 51, 49, 50, 50]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        self.analyzer.detect_anomaly("k1", 200.0)
        anomalies = self.analyzer.get_anomalies()
        self.assertEqual(len(anomalies), 1)

    def test_get_anomalies_filtered(self):
        for v in [50, 51, 49, 50, 50]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        for v in [10, 11, 9, 10, 10]:
            self.analyzer.add_data_point(
                "k2", float(v),
            )
        self.analyzer.detect_anomaly("k1", 200.0)
        self.analyzer.detect_anomaly("k2", 200.0)
        anomalies = self.analyzer.get_anomalies(
            kpi_id="k1",
        )
        self.assertEqual(len(anomalies), 1)

    def test_tracked_kpi_count(self):
        self.analyzer.add_data_point("k1", 10.0)
        self.analyzer.add_data_point("k2", 20.0)
        self.assertEqual(
            self.analyzer.tracked_kpi_count, 2,
        )

    def test_anomaly_count(self):
        for v in [50, 51, 49, 50, 50]:
            self.analyzer.add_data_point(
                "k1", float(v),
            )
        self.analyzer.detect_anomaly("k1", 200.0)
        self.assertEqual(
            self.analyzer.anomaly_count, 1,
        )

    def test_add_data_point_custom_timestamp(self):
        r = self.analyzer.add_data_point(
            "k1", 10.0, timestamp=1000.0,
        )
        self.assertTrue(r["added"])


class TestABTester(unittest.TestCase):
    """ABTester testleri."""

    def setUp(self):
        from app.core.benchmark.ab_tester import (
            ABTester,
        )
        self.tester = ABTester(min_samples=5)

    def test_create_experiment(self):
        r = self.tester.create_experiment(
            "exp1", "Test",
            variants=["A", "B"],
        )
        self.assertEqual(r["status"], "running")
        self.assertEqual(len(r["variants"]), 2)

    def test_create_experiment_custom_split(self):
        r = self.tester.create_experiment(
            "exp1", "Test",
            variants=["A", "B"],
            traffic_split={"A": 0.7, "B": 0.3},
        )
        self.assertEqual(r["status"], "running")

    def test_experiment_count(self):
        self.assertEqual(
            self.tester.experiment_count, 0,
        )
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        self.assertEqual(
            self.tester.experiment_count, 1,
        )

    def test_active_count(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        self.assertEqual(self.tester.active_count, 1)

    def test_record_observation(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        r = self.tester.record_observation(
            "exp1", "A", 1.0,
        )
        self.assertTrue(r["recorded"])

    def test_record_observation_not_found(self):
        r = self.tester.record_observation(
            "no", "A", 1.0,
        )
        self.assertIn("error", r)

    def test_record_observation_completed(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        # Deneyi tamamla
        for _ in range(10):
            self.tester.record_observation(
                "exp1", "A", 1.0, success=True,
            )
            self.tester.record_observation(
                "exp1", "B", 0.5, success=False,
            )
        self.tester.determine_winner("exp1")
        r = self.tester.record_observation(
            "exp1", "A", 1.0,
        )
        self.assertIn("error", r)

    def test_analyze(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        for _ in range(10):
            self.tester.record_observation(
                "exp1", "A", 1.0, success=True,
            )
            self.tester.record_observation(
                "exp1", "B", 0.5, success=False,
            )
        r = self.tester.analyze("exp1")
        self.assertEqual(
            r["total_observations"], 20,
        )
        self.assertIn("variant_stats", r)
        self.assertIn("A", r["variant_stats"])
        self.assertIn("B", r["variant_stats"])

    def test_analyze_not_found(self):
        r = self.tester.analyze("no")
        self.assertIn("error", r)

    def test_analyze_sufficient_data(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        for _ in range(5):
            self.tester.record_observation(
                "exp1", "A", 1.0, success=True,
            )
            self.tester.record_observation(
                "exp1", "B", 0.5, success=False,
            )
        r = self.tester.analyze("exp1")
        self.assertTrue(r["sufficient_data"])

    def test_analyze_insufficient_data(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        self.tester.record_observation(
            "exp1", "A", 1.0,
        )
        r = self.tester.analyze("exp1")
        self.assertFalse(r["sufficient_data"])

    def test_determine_winner(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        for _ in range(10):
            self.tester.record_observation(
                "exp1", "A", 1.0, success=True,
            )
            self.tester.record_observation(
                "exp1", "B", 0.5, success=False,
            )
        r = self.tester.determine_winner("exp1")
        self.assertEqual(r["winner"], "A")

    def test_determine_winner_not_found(self):
        r = self.tester.determine_winner("no")
        self.assertIn("error", r)

    def test_get_experiment(self):
        self.tester.create_experiment(
            "exp1", "Test",
            variants=["A", "B"],
        )
        exp = self.tester.get_experiment("exp1")
        self.assertIsNotNone(exp)
        self.assertEqual(exp["name"], "Test")

    def test_get_experiment_not_found(self):
        r = self.tester.get_experiment("no")
        self.assertIsNone(r)

    def test_get_rollout_recommendation_winner(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        for _ in range(10):
            self.tester.record_observation(
                "exp1", "A", 1.0, success=True,
            )
            self.tester.record_observation(
                "exp1", "B", 0.5, success=False,
            )
        self.tester.determine_winner("exp1")
        r = self.tester.get_rollout_recommendation(
            "exp1",
        )
        self.assertEqual(
            r["recommendation"], "rollout",
        )
        self.assertEqual(r["variant"], "A")

    def test_get_rollout_recommendation_continue(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        self.tester.record_observation(
            "exp1", "A", 1.0,
        )
        r = self.tester.get_rollout_recommendation(
            "exp1",
        )
        self.assertEqual(
            r["recommendation"], "continue",
        )

    def test_get_rollout_not_found(self):
        r = self.tester.get_rollout_recommendation(
            "no",
        )
        self.assertIn("error", r)

    def test_significance_check(self):
        self.tester.create_experiment(
            "exp1", "T", variants=["A", "B"],
        )
        # A cok basarili, B basarisiz
        for _ in range(20):
            self.tester.record_observation(
                "exp1", "A", 1.0, success=True,
            )
            self.tester.record_observation(
                "exp1", "B", 0.1, success=False,
            )
        r = self.tester.analyze("exp1")
        self.assertTrue(r["significant"])

    def test_three_variants(self):
        self.tester.create_experiment(
            "exp1", "T",
            variants=["A", "B", "C"],
        )
        self.assertEqual(
            self.tester.experiment_count, 1,
        )
        exp = self.tester.get_experiment("exp1")
        self.assertEqual(len(exp["variants"]), 3)


class TestComparisonEngine(unittest.TestCase):
    """ComparisonEngine testleri."""

    def setUp(self):
        from app.core.benchmark.comparison_engine import (
            ComparisonEngine,
        )
        self.engine = ComparisonEngine()

    def test_set_baseline(self):
        r = self.engine.set_baseline("k1", 100.0)
        self.assertTrue(r["set"])
        self.assertEqual(r["baseline"], 100.0)

    def test_baseline_count(self):
        self.assertEqual(
            self.engine.baseline_count, 0,
        )
        self.engine.set_baseline("k1", 100.0)
        self.assertEqual(
            self.engine.baseline_count, 1,
        )

    def test_compare_to_baseline(self):
        self.engine.set_baseline("k1", 100.0)
        r = self.engine.compare_to_baseline(
            "k1", 120.0,
        )
        self.assertEqual(r["change_pct"], 20.0)
        self.assertTrue(r["improved"])

    def test_compare_to_baseline_degraded(self):
        self.engine.set_baseline("k1", 100.0)
        r = self.engine.compare_to_baseline(
            "k1", 80.0,
        )
        self.assertEqual(r["change_pct"], -20.0)
        self.assertFalse(r["improved"])

    def test_compare_to_baseline_no_baseline(self):
        r = self.engine.compare_to_baseline(
            "k1", 50.0,
        )
        self.assertIn("error", r)

    def test_compare_to_baseline_zero(self):
        self.engine.set_baseline("k1", 0.0)
        r = self.engine.compare_to_baseline(
            "k1", 50.0,
        )
        self.assertEqual(r["change_pct"], 100.0)

    def test_set_standard(self):
        r = self.engine.set_standard(
            "k1", 95.0, source="industry",
        )
        self.assertEqual(r["standard"], 95.0)
        self.assertEqual(r["source"], "industry")

    def test_standard_count(self):
        self.engine.set_standard("k1", 95.0)
        self.assertEqual(
            self.engine.standard_count, 1,
        )

    def test_compare_to_standard(self):
        self.engine.set_standard("k1", 90.0)
        r = self.engine.compare_to_standard(
            "k1", 95.0,
        )
        self.assertTrue(r["meets_standard"])
        self.assertAlmostEqual(r["gap"], 5.0)

    def test_compare_to_standard_below(self):
        self.engine.set_standard("k1", 90.0)
        r = self.engine.compare_to_standard(
            "k1", 80.0,
        )
        self.assertFalse(r["meets_standard"])

    def test_compare_to_standard_no_standard(self):
        r = self.engine.compare_to_standard(
            "k1", 50.0,
        )
        self.assertIn("error", r)

    def test_compare_periods(self):
        r = self.engine.compare_periods(
            "k1",
            [10.0, 20.0, 30.0],
            [40.0, 50.0, 60.0],
        )
        self.assertTrue(r["improved"])
        self.assertEqual(r["period_a_avg"], 20.0)
        self.assertEqual(r["period_b_avg"], 50.0)

    def test_compare_periods_degraded(self):
        r = self.engine.compare_periods(
            "k1",
            [40.0, 50.0, 60.0],
            [10.0, 20.0, 30.0],
        )
        self.assertFalse(r["improved"])

    def test_compare_periods_empty(self):
        r = self.engine.compare_periods(
            "k1", [], [10.0],
        )
        self.assertEqual(r["period_a_avg"], 0.0)

    def test_gap_analysis(self):
        current = {"k1": 80.0, "k2": 95.0}
        target = {"k1": 100.0, "k2": 90.0}
        r = self.engine.gap_analysis(
            current, target,
        )
        self.assertEqual(r["total_kpis"], 2)
        self.assertEqual(r["met_count"], 1)
        # k2 hedefe ulasti
        self.assertTrue(r["gaps"]["k2"]["met"])
        self.assertFalse(r["gaps"]["k1"]["met"])

    def test_gap_analysis_all_met(self):
        current = {"k1": 100.0, "k2": 100.0}
        target = {"k1": 90.0, "k2": 90.0}
        r = self.engine.gap_analysis(
            current, target,
        )
        self.assertEqual(r["met_count"], 2)

    def test_comparison_count(self):
        self.engine.set_baseline("k1", 100.0)
        self.engine.compare_to_baseline("k1", 120.0)
        self.assertEqual(
            self.engine.comparison_count, 1,
        )

    def test_set_baseline_with_period(self):
        r = self.engine.set_baseline(
            "k1", 100.0, period="Q1",
        )
        self.assertTrue(r["set"])


class TestBenchmarkReportGenerator(unittest.TestCase):
    """BenchmarkReportGenerator testleri."""

    def setUp(self):
        from app.core.benchmark.report_generator import (
            BenchmarkReportGenerator,
        )
        self.gen = BenchmarkReportGenerator()

    def test_generate_performance_report(self):
        scores = {
            "k1": {"score": 0.9, "meets_target": True},
            "k2": {"score": 0.7, "meets_target": False},
        }
        r = self.gen.generate_performance_report(
            scores,
        )
        self.assertEqual(r["type"], "performance")
        self.assertEqual(r["total_kpis"], 2)
        self.assertEqual(r["targets_met"], 1)
        self.assertEqual(r["met_rate"], 0.5)

    def test_performance_report_avg_score(self):
        scores = {
            "k1": {"score": 0.8, "meets_target": True},
            "k2": {"score": 0.6, "meets_target": False},
        }
        r = self.gen.generate_performance_report(
            scores,
        )
        self.assertAlmostEqual(
            r["avg_score"], 0.7, places=3,
        )

    def test_generate_trend_report(self):
        trends = {
            "k1": {"direction": "improving"},
            "k2": {"direction": "stable"},
            "k3": {"direction": "degrading"},
        }
        r = self.gen.generate_trend_report(trends)
        self.assertEqual(r["type"], "trend")
        self.assertEqual(r["improving"], 1)
        self.assertEqual(r["stable"], 1)
        self.assertEqual(r["degrading"], 1)

    def test_generate_executive_summary_good(self):
        perf = {"met_rate": 0.95, "avg_score": 0.9}
        r = self.gen.generate_executive_summary(perf)
        self.assertEqual(r["type"], "executive")
        self.assertEqual(r["health"], "good")

    def test_executive_summary_critical(self):
        perf = {"met_rate": 0.95, "avg_score": 0.9}
        alerts = [
            {"severity": "critical", "id": "a1"},
        ]
        r = self.gen.generate_executive_summary(
            perf, alerts=alerts,
        )
        self.assertEqual(r["health"], "critical")

    def test_executive_summary_needs_attention(self):
        perf = {"met_rate": 0.3, "avg_score": 0.4}
        r = self.gen.generate_executive_summary(perf)
        self.assertEqual(
            r["health"], "needs_attention",
        )

    def test_executive_summary_insights(self):
        perf = {"met_rate": 0.95}
        r = self.gen.generate_executive_summary(perf)
        self.assertTrue(len(r["key_insights"]) > 0)

    def test_executive_insights_good(self):
        perf = {"met_rate": 0.95}
        r = self.gen.generate_executive_summary(perf)
        self.assertIn(
            "Excellent", r["key_insights"][0],
        )

    def test_executive_insights_moderate(self):
        perf = {"met_rate": 0.75}
        r = self.gen.generate_executive_summary(perf)
        self.assertIn("Good", r["key_insights"][0])

    def test_executive_insights_low(self):
        perf = {"met_rate": 0.5}
        r = self.gen.generate_executive_summary(perf)
        self.assertIn(
            "improvement", r["key_insights"][0],
        )

    def test_generate_detailed_breakdown(self):
        history = [
            {"score": 0.8},
            {"score": 0.9},
            {"score": 0.7},
        ]
        r = self.gen.generate_detailed_breakdown(
            "k1", history,
        )
        self.assertEqual(r["type"], "detailed")
        self.assertEqual(r["kpi_id"], "k1")
        self.assertEqual(r["data_points"], 3)
        self.assertAlmostEqual(
            r["avg_score"], 0.8, places=3,
        )
        self.assertEqual(r["best_score"], 0.9)
        self.assertEqual(r["worst_score"], 0.7)

    def test_detailed_breakdown_empty(self):
        r = self.gen.generate_detailed_breakdown(
            "k1", [],
        )
        self.assertEqual(r["data_points"], 0)
        self.assertEqual(r["avg_score"], 0.0)

    def test_report_count(self):
        self.assertEqual(self.gen.report_count, 0)
        self.gen.generate_performance_report({})
        self.assertEqual(self.gen.report_count, 1)

    def test_get_reports(self):
        self.gen.generate_performance_report({})
        self.gen.generate_trend_report({})
        reports = self.gen.get_reports()
        self.assertEqual(len(reports), 2)

    def test_get_reports_filtered(self):
        self.gen.generate_performance_report({})
        self.gen.generate_trend_report({})
        reports = self.gen.get_reports(
            report_type="performance",
        )
        self.assertEqual(len(reports), 1)

    def test_get_reports_limit(self):
        for _ in range(10):
            self.gen.generate_performance_report({})
        reports = self.gen.get_reports(limit=3)
        self.assertEqual(len(reports), 3)

    def test_performance_report_with_period(self):
        r = self.gen.generate_performance_report(
            {}, period="Q1-2026",
        )
        self.assertEqual(r["period"], "Q1-2026")

    def test_detailed_with_trend(self):
        r = self.gen.generate_detailed_breakdown(
            "k1", [{"score": 0.8}],
            trend={"direction": "improving"},
        )
        self.assertEqual(
            r["trend"]["direction"], "improving",
        )

    def test_executive_with_trends(self):
        perf = {"met_rate": 0.8}
        trends = {"degrading": 2}
        r = self.gen.generate_executive_summary(
            perf, trends=trends,
        )
        insights = r["key_insights"]
        degrading_found = any(
            "degrading" in i for i in insights
        )
        self.assertTrue(degrading_found)


class TestBenchmarkAlertManager(unittest.TestCase):
    """BenchmarkAlertManager testleri."""

    def setUp(self):
        from app.core.benchmark.alert_manager import (
            BenchmarkAlertManager,
        )
        self.mgr = BenchmarkAlertManager()

    def test_add_rule(self):
        r = self.mgr.add_rule(
            "r1", "k1", "below", 50.0,
        )
        self.assertTrue(r["added"])
        self.assertEqual(self.mgr.rule_count, 1)

    def test_add_rule_with_severity(self):
        r = self.mgr.add_rule(
            "r1", "k1", "above", 90.0,
            severity="critical",
        )
        self.assertTrue(r["added"])

    def test_check_value_triggered(self):
        self.mgr.add_rule(
            "r1", "k1", "below", 50.0,
        )
        alerts = self.mgr.check_value("k1", 30.0)
        self.assertEqual(len(alerts), 1)

    def test_check_value_not_triggered(self):
        self.mgr.add_rule(
            "r1", "k1", "below", 50.0,
        )
        alerts = self.mgr.check_value("k1", 70.0)
        self.assertEqual(len(alerts), 0)

    def test_check_value_above(self):
        self.mgr.add_rule(
            "r1", "k1", "above", 90.0,
        )
        alerts = self.mgr.check_value("k1", 95.0)
        self.assertEqual(len(alerts), 1)

    def test_check_value_equals(self):
        self.mgr.add_rule(
            "r1", "k1", "equals", 50.0,
        )
        alerts = self.mgr.check_value("k1", 50.0)
        self.assertEqual(len(alerts), 1)

    def test_check_value_different_kpi(self):
        self.mgr.add_rule(
            "r1", "k1", "below", 50.0,
        )
        alerts = self.mgr.check_value("k2", 30.0)
        self.assertEqual(len(alerts), 0)

    def test_alert_threshold(self):
        r = self.mgr.alert_threshold(
            "k1", 70.0, 100.0,
        )
        # 70 < 100 * 0.8 = 80 -> uyari
        self.assertIsNotNone(r)
        self.assertEqual(r["kpi_id"], "k1")

    def test_alert_threshold_ok(self):
        r = self.mgr.alert_threshold(
            "k1", 90.0, 100.0,
        )
        # 90 >= 80 -> OK
        self.assertIsNone(r)

    def test_alert_degradation(self):
        r = self.mgr.alert_degradation("k1", -15.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["severity"], "warning")

    def test_alert_degradation_critical(self):
        r = self.mgr.alert_degradation("k1", -30.0)
        self.assertIsNotNone(r)
        self.assertEqual(r["severity"], "critical")

    def test_alert_degradation_ok(self):
        r = self.mgr.alert_degradation("k1", -5.0)
        self.assertIsNone(r)

    def test_alert_improvement(self):
        r = self.mgr.alert_improvement("k1", 25.0)
        self.assertIsNotNone(r)
        self.assertEqual(
            r["severity"], "improvement",
        )

    def test_alert_improvement_not_enough(self):
        r = self.mgr.alert_improvement("k1", 10.0)
        self.assertIsNone(r)

    def test_alert_anomaly(self):
        r = self.mgr.alert_anomaly(
            "k1", 200.0, 50.0, 10.0,
        )
        self.assertIsNotNone(r)
        self.assertEqual(r["mean"], 50.0)
        self.assertEqual(r["std"], 10.0)

    def test_acknowledge(self):
        self.mgr.alert_degradation("k1", -20.0)
        alerts = self.mgr.get_active_alerts()
        alert_id = alerts[0]["alert_id"]
        r = self.mgr.acknowledge(alert_id)
        self.assertTrue(r["acknowledged"])

    def test_acknowledge_not_found(self):
        r = self.mgr.acknowledge("no")
        self.assertIn("error", r)

    def test_resolve(self):
        self.mgr.alert_degradation("k1", -20.0)
        alerts = self.mgr.get_active_alerts()
        alert_id = alerts[0]["alert_id"]
        r = self.mgr.resolve(alert_id)
        self.assertTrue(r["resolved"])
        self.assertEqual(self.mgr.active_count, 0)

    def test_resolve_not_found(self):
        r = self.mgr.resolve("no")
        self.assertIn("error", r)

    def test_get_active_alerts(self):
        self.mgr.alert_degradation("k1", -20.0)
        self.mgr.alert_degradation("k2", -30.0)
        alerts = self.mgr.get_active_alerts()
        self.assertEqual(len(alerts), 2)

    def test_get_active_alerts_severity(self):
        self.mgr.alert_degradation("k1", -15.0)
        self.mgr.alert_degradation("k2", -30.0)
        warnings = self.mgr.get_active_alerts(
            severity="warning",
        )
        criticals = self.mgr.get_active_alerts(
            severity="critical",
        )
        self.assertEqual(len(warnings), 1)
        self.assertEqual(len(criticals), 1)

    def test_alert_count(self):
        self.assertEqual(self.mgr.alert_count, 0)
        self.mgr.alert_degradation("k1", -20.0)
        self.assertEqual(self.mgr.alert_count, 1)

    def test_active_count(self):
        self.mgr.alert_degradation("k1", -20.0)
        self.assertEqual(self.mgr.active_count, 1)

    def test_rule_count(self):
        self.mgr.add_rule(
            "r1", "k1", "below", 50.0,
        )
        self.mgr.add_rule(
            "r2", "k2", "above", 90.0,
        )
        self.assertEqual(self.mgr.rule_count, 2)


class TestBenchmarkOrchestrator(unittest.TestCase):
    """BenchmarkOrchestrator testleri."""

    def setUp(self):
        from app.core.benchmark.benchmark_orchestrator import (
            BenchmarkOrchestrator,
        )
        self.orch = BenchmarkOrchestrator(
            ab_min_samples=5,
        )

    def test_init(self):
        self.assertIsNotNone(self.orch.kpis)
        self.assertIsNotNone(self.orch.metrics)
        self.assertIsNotNone(self.orch.scorer)
        self.assertIsNotNone(self.orch.trends)
        self.assertIsNotNone(self.orch.ab_tester)
        self.assertIsNotNone(self.orch.comparison)
        self.assertIsNotNone(self.orch.reports)
        self.assertIsNotNone(self.orch.alerts)

    def test_evaluate_kpi_without_target(self):
        r = self.orch.evaluate_kpi("k1", 50.0)
        self.assertEqual(r["kpi_id"], "k1")
        self.assertEqual(r["value"], 50.0)
        self.assertIsNone(r["score"])
        self.assertIsNone(r["meets_target"])

    def test_evaluate_kpi_with_target(self):
        self.orch.kpis.define_kpi("k1", "Uptime")
        self.orch.kpis.set_target("k1", 100.0)
        r = self.orch.evaluate_kpi("k1", 90.0)
        self.assertEqual(r["score"], 0.9)
        self.assertFalse(r["meets_target"])

    def test_evaluate_kpi_meets_target(self):
        self.orch.kpis.define_kpi("k1", "Uptime")
        self.orch.kpis.set_target("k1", 100.0)
        r = self.orch.evaluate_kpi("k1", 100.0)
        self.assertTrue(r["meets_target"])
        self.assertEqual(r["score"], 1.0)

    def test_evaluate_kpi_anomaly(self):
        self.orch.kpis.define_kpi("k1", "Uptime")
        # Normal veri ekle
        for v in [50.0, 51.0, 49.0, 50.0, 50.0]:
            self.orch.evaluate_kpi("k1", v)
        # Anomali
        r = self.orch.evaluate_kpi("k1", 200.0)
        self.assertTrue(r["is_anomaly"])

    def test_evaluation_count(self):
        self.assertEqual(
            self.orch.evaluation_count, 0,
        )
        self.orch.evaluate_kpi("k1", 50.0)
        self.assertEqual(
            self.orch.evaluation_count, 1,
        )

    def test_run_evaluation(self):
        self.orch.kpis.define_kpi("k1", "A")
        self.orch.kpis.set_target("k1", 100.0)
        self.orch.metrics.collect("k1", 90.0)
        r = self.orch.run_evaluation()
        self.assertEqual(r["kpis_evaluated"], 1)
        self.assertIn("k1", r["results"])

    def test_run_evaluation_empty(self):
        r = self.orch.run_evaluation()
        self.assertEqual(r["kpis_evaluated"], 0)

    def test_run_evaluation_generates_report(self):
        self.orch.kpis.define_kpi("k1", "A")
        self.orch.kpis.set_target("k1", 100.0)
        self.orch.metrics.collect("k1", 90.0)
        r = self.orch.run_evaluation()
        self.assertIsNotNone(r["report"])
        self.assertEqual(
            r["report"]["type"], "performance",
        )

    def test_get_status(self):
        s = self.orch.get_status()
        self.assertEqual(s["total_kpis"], 0)
        self.assertEqual(s["metrics_tracked"], 0)
        self.assertEqual(s["total_scores"], 0)
        self.assertEqual(s["active_experiments"], 0)
        self.assertEqual(s["active_alerts"], 0)
        self.assertEqual(s["reports_generated"], 0)
        self.assertEqual(s["evaluations"], 0)

    def test_get_status_after_work(self):
        self.orch.kpis.define_kpi("k1", "A")
        self.orch.kpis.set_target("k1", 100.0)
        self.orch.evaluate_kpi("k1", 90.0)
        s = self.orch.get_status()
        self.assertEqual(s["total_kpis"], 1)
        self.assertGreaterEqual(
            s["metrics_tracked"], 1,
        )
        self.assertEqual(s["evaluations"], 1)

    def test_get_analytics(self):
        r = self.orch.get_analytics()
        self.assertIn("kpi_count", r)
        self.assertIn("trends", r)
        self.assertIn("anomalies", r)
        self.assertIn("active_alerts", r)
        self.assertIn("experiments", r)

    def test_get_analytics_with_data(self):
        self.orch.kpis.define_kpi("k1", "A")
        for v in [50, 51, 49, 50, 52]:
            self.orch.evaluate_kpi("k1", float(v))
        r = self.orch.get_analytics()
        self.assertEqual(r["kpi_count"], 1)

    def test_evaluate_kpi_degradation(self):
        self.orch.kpis.define_kpi("k1", "A")
        # Degrading trend: yuksek baslayip dusuyor
        for v in [90, 85, 80, 75, 40, 35, 30, 25]:
            self.orch.evaluate_kpi("k1", float(v))
        r = self.orch.evaluate_kpi("k1", 20.0)
        # Degradation alert olabilir
        self.assertIn("degradation_alert", r)

    def test_no_alert_on_degradation_disabled(self):
        from app.core.benchmark.benchmark_orchestrator import (
            BenchmarkOrchestrator,
        )
        orch = BenchmarkOrchestrator(
            alert_on_degradation=False,
        )
        orch.kpis.define_kpi("k1", "A")
        for v in [90, 85, 80, 75, 40, 35, 30, 25]:
            orch.evaluate_kpi("k1", float(v))
        r = orch.evaluate_kpi("k1", 20.0)
        self.assertFalse(r["degradation_alert"])

    def test_full_pipeline(self):
        # KPI tanimla
        self.orch.kpis.define_kpi("k1", "Uptime")
        self.orch.kpis.set_target("k1", 100.0)
        # Metrik topla ve degerlendir
        for v in [90, 92, 94, 96, 98]:
            self.orch.evaluate_kpi("k1", float(v))
        # Run evaluation
        self.orch.metrics.collect("k1", 95.0)
        r = self.orch.run_evaluation()
        self.assertGreater(r["kpis_evaluated"], 0)
        # Status
        s = self.orch.get_status()
        self.assertGreater(s["evaluations"], 0)

    def test_multiple_kpis(self):
        self.orch.kpis.define_kpi("k1", "A")
        self.orch.kpis.define_kpi("k2", "B")
        self.orch.kpis.set_target("k1", 100.0)
        self.orch.kpis.set_target("k2", 50.0)
        self.orch.metrics.collect("k1", 90.0)
        self.orch.metrics.collect("k2", 45.0)
        r = self.orch.run_evaluation()
        self.assertEqual(r["kpis_evaluated"], 2)


class TestBenchmarkInit(unittest.TestCase):
    """Benchmark __init__ testleri."""

    def test_imports(self):
        from app.core.benchmark import (
            ABTester,
            BenchmarkAlertManager,
            BenchmarkMetricCollector,
            BenchmarkOrchestrator,
            BenchmarkReportGenerator,
            BenchmarkTrendAnalyzer,
            ComparisonEngine,
            KPIDefiner,
            PerformanceScorer,
        )
        self.assertIsNotNone(ABTester)
        self.assertIsNotNone(BenchmarkAlertManager)
        self.assertIsNotNone(BenchmarkMetricCollector)
        self.assertIsNotNone(BenchmarkOrchestrator)
        self.assertIsNotNone(BenchmarkReportGenerator)
        self.assertIsNotNone(BenchmarkTrendAnalyzer)
        self.assertIsNotNone(ComparisonEngine)
        self.assertIsNotNone(KPIDefiner)
        self.assertIsNotNone(PerformanceScorer)

    def test_instantiate_all(self):
        from app.core.benchmark import (
            ABTester,
            BenchmarkAlertManager,
            BenchmarkMetricCollector,
            BenchmarkOrchestrator,
            BenchmarkReportGenerator,
            BenchmarkTrendAnalyzer,
            ComparisonEngine,
            KPIDefiner,
            PerformanceScorer,
        )
        self.assertIsNotNone(KPIDefiner())
        self.assertIsNotNone(
            BenchmarkMetricCollector(),
        )
        self.assertIsNotNone(PerformanceScorer())
        self.assertIsNotNone(
            BenchmarkTrendAnalyzer(),
        )
        self.assertIsNotNone(ABTester())
        self.assertIsNotNone(ComparisonEngine())
        self.assertIsNotNone(
            BenchmarkReportGenerator(),
        )
        self.assertIsNotNone(
            BenchmarkAlertManager(),
        )
        self.assertIsNotNone(
            BenchmarkOrchestrator(),
        )


class TestBenchmarkConfig(unittest.TestCase):
    """Benchmark config testleri."""

    def test_config_defaults(self):
        from app.config import settings
        self.assertTrue(settings.benchmark_enabled)
        self.assertEqual(
            settings.evaluation_interval_hours, 6,
        )
        self.assertEqual(
            settings.ab_test_min_samples, 30,
        )
        self.assertTrue(
            settings.alert_on_degradation,
        )
        self.assertEqual(
            settings.report_frequency, "daily",
        )


if __name__ == "__main__":
    unittest.main()
