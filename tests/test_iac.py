"""ATLAS Infrastructure as Code sistemi testleri."""

import pytest

from app.core.iac.resource_definer import (
    ResourceDefiner,
)
from app.core.iac.template_engine import (
    IaCTemplateEngine,
)
from app.core.iac.state_manager import (
    IaCStateManager,
)
from app.core.iac.plan_generator import (
    PlanGenerator,
)
from app.core.iac.resource_provisioner import (
    ResourceProvisioner,
)
from app.core.iac.drift_detector import (
    IaCDriftDetector,
)
from app.core.iac.module_manager import (
    ModuleManager,
)
from app.core.iac.compliance_checker import (
    IaCComplianceChecker,
)
from app.core.iac.iac_orchestrator import (
    IaCOrchestrator,
)
from app.models.iac_models import (
    ResourceStatus,
    ChangeAction,
    DriftSeverity,
    ComplianceLevel,
    StateBackend,
    ModuleStatus,
    ResourceRecord,
    PlanRecord,
    DriftRecord,
    IaCSnapshot,
)


# ==================== ResourceDefiner ====================


class TestResourceDefiner:
    """ResourceDefiner testleri."""

    def test_init(self):
        """Baslatma testi."""
        rd = ResourceDefiner()
        assert rd.resource_count == 0
        assert rd.output_count == 0
        assert rd.condition_count == 0
        assert rd.variable_count == 0

    def test_define_resource(self):
        """Kaynak tanimlama."""
        rd = ResourceDefiner()
        result = rd.define(
            "server", "web1",
            properties={"cpu": 2, "ram": 4},
        )
        assert result["key"] == "server.web1"
        assert result["type"] == "server"
        assert rd.resource_count == 1

    def test_define_with_dependencies(self):
        """Bagimlilikli tanim."""
        rd = ResourceDefiner()
        rd.define("network", "vpc1")
        rd.define(
            "server", "web1",
            depends_on=["network.vpc1"],
        )
        res = rd.get("server", "web1")
        assert "network.vpc1" in res["depends_on"]

    def test_define_with_condition(self):
        """Kosullu tanim."""
        rd = ResourceDefiner()
        rd.define(
            "server", "staging",
            condition="is_staging",
        )
        res = rd.get("server", "staging")
        assert res["condition"] == "is_staging"

    def test_define_with_provider(self):
        """Saglayicili tanim."""
        rd = ResourceDefiner()
        rd.define(
            "server", "web1",
            provider="aws",
        )
        res = rd.get("server", "web1")
        assert res["provider"] == "aws"

    def test_get_resource(self):
        """Kaynak getirme."""
        rd = ResourceDefiner()
        rd.define("db", "main", {"engine": "pg"})
        res = rd.get("db", "main")
        assert res is not None
        assert res["properties"]["engine"] == "pg"

    def test_get_nonexistent(self):
        """Olmayan kaynak getirme."""
        rd = ResourceDefiner()
        assert rd.get("x", "y") is None

    def test_remove_resource(self):
        """Kaynak kaldirma."""
        rd = ResourceDefiner()
        rd.define("server", "web1")
        assert rd.remove("server", "web1")
        assert rd.resource_count == 0

    def test_remove_nonexistent(self):
        """Olmayan kaynak kaldirma."""
        rd = ResourceDefiner()
        assert not rd.remove("x", "y")

    def test_set_property(self):
        """Ozellik ayarlama."""
        rd = ResourceDefiner()
        rd.define("server", "web1")
        assert rd.set_property(
            "server", "web1", "cpu", 4,
        )
        res = rd.get("server", "web1")
        assert res["properties"]["cpu"] == 4

    def test_set_property_nonexistent(self):
        """Olmayan kaynaga ozellik."""
        rd = ResourceDefiner()
        assert not rd.set_property(
            "x", "y", "cpu", 4,
        )

    def test_add_dependency(self):
        """Bagimlilik ekleme."""
        rd = ResourceDefiner()
        rd.define("server", "web1")
        assert rd.add_dependency(
            "server", "web1", "network.vpc1",
        )
        deps = rd.get_dependencies(
            "server", "web1",
        )
        assert "network.vpc1" in deps

    def test_add_dependency_nonexistent(self):
        """Olmayan kaynaga bagimlilik."""
        rd = ResourceDefiner()
        assert not rd.add_dependency(
            "x", "y", "z",
        )

    def test_add_duplicate_dependency(self):
        """Tekrar bagimlilik ekleme."""
        rd = ResourceDefiner()
        rd.define("server", "web1")
        rd.add_dependency(
            "server", "web1", "network.vpc1",
        )
        rd.add_dependency(
            "server", "web1", "network.vpc1",
        )
        deps = rd.get_dependencies(
            "server", "web1",
        )
        assert deps.count("network.vpc1") == 1

    def test_get_dependencies_nonexistent(self):
        """Olmayan kaynaktan bagimlilik."""
        rd = ResourceDefiner()
        assert rd.get_dependencies("x", "y") == []

    def test_define_output(self):
        """Cikti tanimlama."""
        rd = ResourceDefiner()
        result = rd.define_output(
            "ip", "10.0.0.1", "Server IP",
        )
        assert result["name"] == "ip"
        assert rd.output_count == 1

    def test_get_output(self):
        """Cikti getirme."""
        rd = ResourceDefiner()
        rd.define_output("port", 8080)
        assert rd.get_output("port") == 8080

    def test_get_output_nonexistent(self):
        """Olmayan cikti."""
        rd = ResourceDefiner()
        assert rd.get_output("x") is None

    def test_define_condition(self):
        """Kosul tanimlama."""
        rd = ResourceDefiner()
        result = rd.define_condition(
            "is_prod", "env",
            description="Production mi",
        )
        assert result["name"] == "is_prod"
        assert rd.condition_count == 1

    def test_evaluate_condition_true(self):
        """Kosul degerlendirme - dogru."""
        rd = ResourceDefiner()
        rd.define_condition("is_prod", "prod_flag")
        assert rd.evaluate_condition(
            "is_prod", {"prod_flag": True},
        )

    def test_evaluate_condition_false(self):
        """Kosul degerlendirme - yanlis."""
        rd = ResourceDefiner()
        rd.define_condition("is_prod", "prod_flag")
        assert not rd.evaluate_condition(
            "is_prod", {"prod_flag": False},
        )

    def test_evaluate_condition_literal_true(self):
        """Literal true kosul."""
        rd = ResourceDefiner()
        rd.define_condition("always", "true")
        assert rd.evaluate_condition("always")

    def test_evaluate_condition_literal_false(self):
        """Literal false kosul."""
        rd = ResourceDefiner()
        rd.define_condition("never", "false")
        assert not rd.evaluate_condition("never")

    def test_evaluate_nonexistent_condition(self):
        """Olmayan kosul - varsayilan True."""
        rd = ResourceDefiner()
        assert rd.evaluate_condition("x")

    def test_define_variable(self):
        """Degisken tanimlama."""
        rd = ResourceDefiner()
        result = rd.define_variable(
            "region", "string", "us-east-1",
        )
        assert result["name"] == "region"
        assert result["type"] == "string"
        assert rd.variable_count == 1

    def test_get_variable(self):
        """Degisken getirme."""
        rd = ResourceDefiner()
        rd.define_variable(
            "count", "number", 3,
        )
        v = rd.get_variable("count")
        assert v["default"] == 3

    def test_get_variable_nonexistent(self):
        """Olmayan degisken."""
        rd = ResourceDefiner()
        assert rd.get_variable("x") is None

    def test_list_resources(self):
        """Kaynak listeleme."""
        rd = ResourceDefiner()
        rd.define("server", "web1")
        rd.define("server", "web2")
        rd.define("db", "main")
        assert len(rd.list_resources()) == 3

    def test_list_resources_by_type(self):
        """Tipte filtreleme."""
        rd = ResourceDefiner()
        rd.define("server", "web1")
        rd.define("server", "web2")
        rd.define("db", "main")
        servers = rd.list_resources("server")
        assert len(servers) == 2

    def test_dependency_order(self):
        """Bagimlilik sirasi."""
        rd = ResourceDefiner()
        rd.define("network", "vpc1")
        rd.define(
            "server", "web1",
            depends_on=["network.vpc1"],
        )
        order = rd.get_dependency_order()
        assert order.index("network.vpc1") < (
            order.index("server.web1")
        )


# ==================== IaCTemplateEngine ====================


class TestIaCTemplateEngine:
    """IaCTemplateEngine testleri."""

    def test_init(self):
        """Baslatma testi."""
        te = IaCTemplateEngine()
        assert te.template_count == 0
        assert te.function_count >= 4
        assert te.partial_count == 0
        assert te.render_count == 0

    def test_render_variable(self):
        """Degisken ikamesi."""
        te = IaCTemplateEngine()
        result = te.render(
            "Hello {{ name }}!",
            {"name": "Atlas"},
        )
        assert result == "Hello Atlas!"

    def test_render_multiple_variables(self):
        """Birden fazla degisken."""
        te = IaCTemplateEngine()
        result = te.render(
            "{{ a }}-{{ b }}",
            {"a": "x", "b": "y"},
        )
        assert result == "x-y"

    def test_render_no_variables(self):
        """Degiskensiz render."""
        te = IaCTemplateEngine()
        result = te.render("plain text")
        assert result == "plain text"

    def test_render_missing_variable(self):
        """Eksik degisken - aynen kalir."""
        te = IaCTemplateEngine()
        result = te.render(
            "{{ missing }}", {},
        )
        assert "{{ missing }}" in result

    def test_render_if_true(self):
        """Kosul - dogru."""
        te = IaCTemplateEngine()
        result = te.render(
            "{% if enabled %}ON{% endif %}",
            {"enabled": True},
        )
        assert result == "ON"

    def test_render_if_false(self):
        """Kosul - yanlis."""
        te = IaCTemplateEngine()
        result = te.render(
            "{% if enabled %}ON{% endif %}",
            {"enabled": False},
        )
        assert "ON" not in result

    def test_render_for_loop(self):
        """Dongu render."""
        te = IaCTemplateEngine()
        result = te.render(
            "{% for item in items %}"
            "{{ item }}"
            "{% endfor %}",
            {"items": ["a", "b", "c"]},
        )
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_render_for_empty(self):
        """Bos dongu."""
        te = IaCTemplateEngine()
        result = te.render(
            "{% for x in items %}"
            "{{ x }}"
            "{% endfor %}",
            {"items": []},
        )
        assert result.strip() == ""

    def test_render_function_upper(self):
        """Upper fonksiyonu."""
        te = IaCTemplateEngine()
        result = te.render(
            "{{ upper(name) }}",
            {"name": "atlas"},
        )
        assert result == "ATLAS"

    def test_render_function_lower(self):
        """Lower fonksiyonu."""
        te = IaCTemplateEngine()
        result = te.render(
            "{{ lower(name) }}",
            {"name": "ATLAS"},
        )
        assert result == "atlas"

    def test_register_template(self):
        """Sablon kaydetme."""
        te = IaCTemplateEngine()
        result = te.register_template(
            "vpc", "VPC: {{ name }}",
        )
        assert result["name"] == "vpc"
        assert te.template_count == 1

    def test_get_template(self):
        """Sablon getirme."""
        te = IaCTemplateEngine()
        te.register_template(
            "vpc", "VPC: {{ name }}",
        )
        tmpl = te.get_template("vpc")
        assert tmpl is not None
        assert "VPC" in tmpl["content"]

    def test_get_template_nonexistent(self):
        """Olmayan sablon."""
        te = IaCTemplateEngine()
        assert te.get_template("x") is None

    def test_remove_template(self):
        """Sablon kaldirma."""
        te = IaCTemplateEngine()
        te.register_template("vpc", "content")
        assert te.remove_template("vpc")
        assert te.template_count == 0

    def test_remove_template_nonexistent(self):
        """Olmayan sablon kaldirma."""
        te = IaCTemplateEngine()
        assert not te.remove_template("x")

    def test_render_template(self):
        """Kayitli sablon render."""
        te = IaCTemplateEngine()
        te.register_template(
            "greet", "Hi {{ name }}!",
        )
        result = te.render_template(
            "greet", {"name": "Fatih"},
        )
        assert result == "Hi Fatih!"

    def test_render_template_nonexistent(self):
        """Olmayan sablon render."""
        te = IaCTemplateEngine()
        assert te.render_template("x") is None

    def test_register_function(self):
        """Fonksiyon kaydetme."""
        te = IaCTemplateEngine()
        te.register_function(
            "double", lambda x: str(x) * 2,
        )
        assert te.function_count >= 5

    def test_register_partial(self):
        """Partial kaydetme."""
        te = IaCTemplateEngine()
        te.register_partial(
            "header", "# Header",
        )
        assert te.partial_count == 1

    def test_render_include(self):
        """Include render."""
        te = IaCTemplateEngine()
        te.register_partial(
            "footer", "---END---",
        )
        result = te.render(
            'Content {% include "footer" %}',
        )
        assert "---END---" in result

    def test_render_count(self):
        """Render sayaci."""
        te = IaCTemplateEngine()
        te.render("a")
        te.render("b")
        assert te.render_count == 2

    def test_get_stats(self):
        """Istatistikler."""
        te = IaCTemplateEngine()
        te.render("a")
        stats = te.get_stats()
        assert stats["renders"] == 1


# ==================== IaCStateManager ====================


class TestIaCStateManager:
    """IaCStateManager testleri."""

    def test_init(self):
        """Baslatma testi."""
        sm = IaCStateManager()
        assert sm.resource_count == 0
        assert sm.version_count == 0
        assert sm.lock_count == 0
        assert sm.serial == 0
        assert sm.backend == "local"

    def test_init_custom_backend(self):
        """Ozel arka uc."""
        sm = IaCStateManager(backend="s3")
        assert sm.backend == "s3"

    def test_set_resource(self):
        """Kaynak durumu ayarlama."""
        sm = IaCStateManager()
        result = sm.set_resource(
            "server.web1", {"cpu": 2},
        )
        assert result["status"] == "updated"
        assert sm.resource_count == 1

    def test_get_resource(self):
        """Kaynak durumu getirme."""
        sm = IaCStateManager()
        sm.set_resource(
            "server.web1", {"cpu": 2},
        )
        state = sm.get_resource("server.web1")
        assert state["cpu"] == 2

    def test_get_resource_nonexistent(self):
        """Olmayan kaynak durumu."""
        sm = IaCStateManager()
        assert sm.get_resource("x") is None

    def test_remove_resource(self):
        """Kaynak durumu kaldirma."""
        sm = IaCStateManager()
        sm.set_resource("server.web1", {})
        assert sm.remove_resource("server.web1")
        assert sm.resource_count == 0

    def test_remove_resource_nonexistent(self):
        """Olmayan kaynak kaldirma."""
        sm = IaCStateManager()
        assert not sm.remove_resource("x")

    def test_save_version(self):
        """Surum kaydetme."""
        sm = IaCStateManager()
        sm.set_resource("s.w", {"cpu": 1})
        result = sm.save_version("initial")
        assert result["serial"] == 1
        assert result["resources"] == 1
        assert sm.version_count == 1

    def test_get_version(self):
        """Surum getirme."""
        sm = IaCStateManager()
        sm.save_version("v1")
        v = sm.get_version(1)
        assert v is not None
        assert v["message"] == "v1"

    def test_get_version_nonexistent(self):
        """Olmayan surum."""
        sm = IaCStateManager()
        assert sm.get_version(99) is None

    def test_restore_version(self):
        """Surum geri yukleme."""
        sm = IaCStateManager()
        sm.set_resource("s.w", {"cpu": 1})
        sm.save_version("v1")
        sm.set_resource("s.w", {"cpu": 4})
        sm.set_resource("s.w2", {"cpu": 2})
        result = sm.restore_version(1)
        assert result["resources"] == 1
        state = sm.get_resource("s.w")
        assert state["cpu"] == 1

    def test_restore_nonexistent_version(self):
        """Olmayan surum geri yukleme."""
        sm = IaCStateManager()
        result = sm.restore_version(99)
        assert "error" in result

    def test_lock(self):
        """Kilitleme."""
        sm = IaCStateManager()
        result = sm.lock("main", "user1")
        assert result["status"] == "locked"
        assert sm.lock_count == 1

    def test_lock_already_locked(self):
        """Zaten kilitli."""
        sm = IaCStateManager()
        sm.lock("main", "user1")
        result = sm.lock("main", "user2")
        assert "error" in result
        assert result["owner"] == "user1"

    def test_unlock(self):
        """Kilit acma."""
        sm = IaCStateManager()
        sm.lock("main", "user1")
        result = sm.unlock("main", "user1")
        assert result["status"] == "unlocked"
        assert sm.lock_count == 0

    def test_unlock_not_locked(self):
        """Kilitli olmayan acma."""
        sm = IaCStateManager()
        result = sm.unlock("main")
        assert "error" in result

    def test_unlock_wrong_owner(self):
        """Yanlis sahip acma."""
        sm = IaCStateManager()
        sm.lock("main", "user1")
        result = sm.unlock("main", "user2")
        assert "error" in result

    def test_is_locked(self):
        """Kilitli mi kontrolu."""
        sm = IaCStateManager()
        assert not sm.is_locked("main")
        sm.lock("main")
        assert sm.is_locked("main")

    def test_export_state(self):
        """Durum aktarma."""
        sm = IaCStateManager()
        sm.set_resource("s.w", {"cpu": 2})
        export = sm.export_state()
        assert export["backend"] == "local"
        assert "s.w" in export["resources"]

    def test_import_state(self):
        """Durum iceri aktarma."""
        sm = IaCStateManager()
        result = sm.import_state({
            "resources": {
                "s.w": {"cpu": 2},
                "s.w2": {"cpu": 4},
            },
        })
        assert result["imported"] == 2
        assert sm.resource_count == 2

    def test_list_resources(self):
        """Kaynak listeleme."""
        sm = IaCStateManager()
        sm.set_resource("a", {})
        sm.set_resource("b", {})
        keys = sm.list_resources()
        assert "a" in keys
        assert "b" in keys

    def test_get_versions(self):
        """Surumleri getirme."""
        sm = IaCStateManager()
        sm.save_version("v1")
        sm.save_version("v2")
        versions = sm.get_versions()
        assert len(versions) == 2

    def test_serial_increments(self):
        """Seri numarasi artisi."""
        sm = IaCStateManager()
        sm.save_version("v1")
        sm.save_version("v2")
        assert sm.serial == 2


# ==================== PlanGenerator ====================


class TestPlanGenerator:
    """PlanGenerator testleri."""

    def test_init(self):
        """Baslatma testi."""
        pg = PlanGenerator()
        assert pg.plan_count == 0
        assert pg.approved_count == 0
        assert pg.rejected_count == 0

    def test_generate_create(self):
        """Olusturma plani."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1",
            {"s.w": {"cpu": 2}},
        )
        assert plan["plan_id"] == "p1"
        assert plan["summary"]["creates"] == 1
        assert plan["summary"]["total"] == 1
        assert pg.plan_count == 1

    def test_generate_update(self):
        """Guncelleme plani."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1",
            {"s.w": {"cpu": 4}},
            {"s.w": {"cpu": 2}},
        )
        assert plan["summary"]["updates"] == 1

    def test_generate_delete(self):
        """Silme plani."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1",
            {},
            {"s.w": {"cpu": 2}},
        )
        assert plan["summary"]["deletes"] == 1

    def test_generate_mixed(self):
        """Karisik plan."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1",
            {"s.w": {"cpu": 4}, "s.w2": {}},
            {"s.w": {"cpu": 2}, "s.w3": {}},
        )
        assert plan["summary"]["creates"] == 1
        assert plan["summary"]["updates"] == 1
        assert plan["summary"]["deletes"] == 1

    def test_generate_no_changes(self):
        """Degisiklik yok."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1",
            {"s.w": {"cpu": 2}},
            {"s.w": {"cpu": 2}},
        )
        assert plan["summary"]["total"] == 0

    def test_cost_estimation(self):
        """Maliyet tahmini."""
        pg = PlanGenerator()
        pg.set_cost_rate("server", 100.0)
        plan = pg.generate(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        assert plan["estimated_cost"] == 100.0
        assert pg.cost_rate_count == 1

    def test_cost_update(self):
        """Guncelleme maliyeti."""
        pg = PlanGenerator()
        pg.set_cost_rate("server", 100.0)
        plan = pg.generate(
            "p1",
            {"server.web": {"cpu": 4}},
            {"server.web": {"cpu": 2}},
        )
        assert plan["estimated_cost"] == 10.0

    def test_risk_assessment(self):
        """Risk degerlendirmesi."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1", {},
            {"s.w": {}, "s.w2": {}, "s.w3": {}},
        )
        # 3 silme = 90 puan = critical
        assert plan["risk"]["level"] == "critical"

    def test_risk_low(self):
        """Dusuk risk."""
        pg = PlanGenerator()
        plan = pg.generate(
            "p1", {"s.w": {}},
        )
        assert plan["risk"]["level"] == "low"

    def test_risk_rules(self):
        """Risk kurallari."""
        pg = PlanGenerator()
        pg.add_risk_rule(
            "prod", "production",
            score=50, warning="Production!",
        )
        plan = pg.generate(
            "p1",
            {"production.db": {}},
        )
        assert plan["risk"]["score"] >= 50
        assert pg.risk_rule_count == 1

    def test_approve(self):
        """Plan onaylama."""
        pg = PlanGenerator()
        pg.generate("p1", {"s.w": {}})
        result = pg.approve("p1", "admin")
        assert result["status"] == "approved"
        assert pg.approved_count == 1

    def test_approve_nonexistent(self):
        """Olmayan plan onaylama."""
        pg = PlanGenerator()
        result = pg.approve("x")
        assert "error" in result

    def test_reject(self):
        """Plan reddi."""
        pg = PlanGenerator()
        pg.generate("p1", {"s.w": {}})
        result = pg.reject("p1", "too risky")
        assert result["status"] == "rejected"
        assert pg.rejected_count == 1

    def test_reject_nonexistent(self):
        """Olmayan plan reddi."""
        pg = PlanGenerator()
        result = pg.reject("x")
        assert "error" in result

    def test_get_plan(self):
        """Plan getirme."""
        pg = PlanGenerator()
        pg.generate("p1", {"s.w": {}})
        plan = pg.get_plan("p1")
        assert plan is not None
        assert plan["plan_id"] == "p1"

    def test_get_plan_nonexistent(self):
        """Olmayan plan getirme."""
        pg = PlanGenerator()
        assert pg.get_plan("x") is None

    def test_get_changes(self):
        """Degisiklikleri getirme."""
        pg = PlanGenerator()
        pg.generate("p1", {"s.w": {}})
        changes = pg.get_changes("p1")
        assert len(changes) == 1

    def test_get_changes_nonexistent(self):
        """Olmayan plan degisiklikleri."""
        pg = PlanGenerator()
        assert pg.get_changes("x") == []


# ==================== ResourceProvisioner ====================


class TestResourceProvisioner:
    """ResourceProvisioner testleri."""

    def test_init(self):
        """Baslatma testi."""
        rp = ResourceProvisioner()
        assert rp.resource_count == 0
        assert rp.created_count == 0
        assert rp.rollback_stack_size == 0

    def test_create(self):
        """Kaynak olusturma."""
        rp = ResourceProvisioner()
        result = rp.create(
            "server.web1", "server",
            {"cpu": 2},
        )
        assert result["status"] == "created"
        assert rp.resource_count == 1
        assert rp.created_count == 1

    def test_update(self):
        """Kaynak guncelleme."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server", {"cpu": 2})
        result = rp.update("s.w", {"cpu": 4})
        assert result["status"] == "updated"

    def test_update_nonexistent(self):
        """Olmayan kaynak guncelleme."""
        rp = ResourceProvisioner()
        result = rp.update("x", {"cpu": 4})
        assert "error" in result

    def test_delete(self):
        """Kaynak silme."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server")
        result = rp.delete("s.w")
        assert result["status"] == "deleted"
        assert rp.resource_count == 0

    def test_delete_nonexistent(self):
        """Olmayan kaynak silme."""
        rp = ResourceProvisioner()
        result = rp.delete("x")
        assert "error" in result

    def test_apply_plan(self):
        """Plan uygulama."""
        rp = ResourceProvisioner()
        changes = [
            {
                "action": "create",
                "resource": "server.web",
                "properties": {"cpu": 2},
            },
        ]
        result = rp.apply_plan(changes)
        assert result["applied"] == 1
        assert result["errors"] == 0

    def test_apply_plan_mixed(self):
        """Karisik plan uygulama."""
        rp = ResourceProvisioner()
        rp.create("s.old", "server", {"cpu": 1})
        changes = [
            {
                "action": "create",
                "resource": "server.new",
                "properties": {"cpu": 2},
            },
            {
                "action": "update",
                "resource": "s.old",
                "new": {"cpu": 4},
            },
            {
                "action": "delete",
                "resource": "s.old",
            },
        ]
        result = rp.apply_plan(changes)
        assert result["total"] == 3

    def test_apply_plan_unknown_action(self):
        """Bilinmeyen eylem."""
        rp = ResourceProvisioner()
        changes = [
            {
                "action": "migrate",
                "resource": "s.w",
            },
        ]
        result = rp.apply_plan(changes)
        assert result["errors"] == 1

    def test_rollback_create(self):
        """Olusturmayi geri alma."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server")
        assert rp.resource_count == 1
        result = rp.rollback(1)
        assert result["rolled_back"] == 1
        assert rp.resource_count == 0

    def test_rollback_update(self):
        """Guncellemeyi geri alma."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server", {"cpu": 2})
        rp.update("s.w", {"cpu": 4})
        rp.rollback(1)
        res = rp.get_resource("s.w")
        assert res["properties"]["cpu"] == 2

    def test_rollback_delete(self):
        """Silmeyi geri alma."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server", {"cpu": 2})
        rp.delete("s.w")
        assert rp.resource_count == 0
        rp.rollback(1)
        assert rp.resource_count == 1

    def test_rollback_multiple(self):
        """Coklu geri alma."""
        rp = ResourceProvisioner()
        rp.create("s.w1", "server")
        rp.create("s.w2", "server")
        result = rp.rollback(2)
        assert result["rolled_back"] == 2
        assert rp.resource_count == 0

    def test_rollback_empty_stack(self):
        """Bos yigindan geri alma."""
        rp = ResourceProvisioner()
        result = rp.rollback(1)
        assert result["rolled_back"] == 0

    def test_get_resource(self):
        """Kaynak getirme."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server", {"cpu": 2})
        res = rp.get_resource("s.w")
        assert res is not None
        assert res["properties"]["cpu"] == 2

    def test_get_resource_nonexistent(self):
        """Olmayan kaynak getirme."""
        rp = ResourceProvisioner()
        assert rp.get_resource("x") is None

    def test_register_hook(self):
        """Hook kaydetme."""
        rp = ResourceProvisioner()
        called = []
        rp.register_hook(
            "create", lambda k: called.append(k),
        )
        rp.create("s.w", "server")
        assert "s.w" in called

    def test_list_resources(self):
        """Kaynak listeleme."""
        rp = ResourceProvisioner()
        rp.create("s.w1", "server")
        rp.create("db.m", "database")
        assert len(rp.list_resources()) == 2

    def test_list_resources_by_type(self):
        """Tipe gore listeleme."""
        rp = ResourceProvisioner()
        rp.create("s.w1", "server")
        rp.create("db.m", "database")
        servers = rp.list_resources("server")
        assert len(servers) == 1

    def test_get_stats(self):
        """Istatistikler."""
        rp = ResourceProvisioner()
        rp.create("s.w", "server")
        stats = rp.get_stats()
        assert stats["created"] == 1


# ==================== IaCDriftDetector ====================


class TestIaCDriftDetector:
    """IaCDriftDetector testleri."""

    def test_init(self):
        """Baslatma testi."""
        dd = IaCDriftDetector()
        assert dd.baseline_count == 0
        assert dd.drift_count == 0
        assert dd.alert_count == 0
        assert dd.check_count == 0

    def test_set_baseline(self):
        """Temel durum ayarlama."""
        dd = IaCDriftDetector()
        result = dd.set_baseline(
            "s.w", {"cpu": 2, "ram": 4},
        )
        assert result["status"] == "baseline_set"
        assert dd.baseline_count == 1

    def test_check_no_drift(self):
        """Kayma yok."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        result = dd.check("s.w", {"cpu": 2})
        assert not result["drifted"]
        assert result["severity"] == "none"

    def test_check_with_drift(self):
        """Kayma tespiti."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        result = dd.check("s.w", {"cpu": 4})
        assert result["drifted"]
        assert result["drifted_count"] == 1
        assert dd.drift_count == 1

    def test_check_no_baseline(self):
        """Temel durum olmadan kontrol."""
        dd = IaCDriftDetector()
        result = dd.check("s.w", {"cpu": 2})
        assert not result["drifted"]
        assert result["reason"] == "no_baseline"

    def test_severity_low(self):
        """Dusuk ciddiyet (1 ozellik)."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        result = dd.check("s.w", {"cpu": 4})
        assert result["severity"] == "low"

    def test_severity_medium(self):
        """Orta ciddiyet (2 ozellik)."""
        dd = IaCDriftDetector()
        dd.set_baseline(
            "s.w", {"cpu": 2, "ram": 4},
        )
        result = dd.check(
            "s.w", {"cpu": 4, "ram": 8},
        )
        assert result["severity"] == "medium"

    def test_severity_high(self):
        """Yuksek ciddiyet (3 ozellik)."""
        dd = IaCDriftDetector()
        dd.set_baseline(
            "s.w", {"a": 1, "b": 2, "c": 3},
        )
        result = dd.check(
            "s.w", {"a": 9, "b": 9, "c": 9},
        )
        assert result["severity"] == "high"

    def test_severity_critical(self):
        """Kritik ciddiyet (5+ ozellik)."""
        dd = IaCDriftDetector()
        dd.set_baseline(
            "s.w",
            {"a": 1, "b": 2, "c": 3,
             "d": 4, "e": 5},
        )
        result = dd.check(
            "s.w",
            {"a": 9, "b": 9, "c": 9,
             "d": 9, "e": 9},
        )
        assert result["severity"] == "critical"

    def test_alerts_created(self):
        """Uyari olusturma."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        dd.check("s.w", {"cpu": 4})
        assert dd.alert_count == 1

    def test_check_all(self):
        """Toplu kontrol."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w1", {"cpu": 2})
        dd.set_baseline("s.w2", {"cpu": 4})
        result = dd.check_all({
            "s.w1": {"cpu": 2},
            "s.w2": {"cpu": 8},
        })
        assert result["checked"] == 2
        assert result["drifted"] == 1
        assert result["clean"] == 1

    def test_add_remediation_rule(self):
        """Duzeltme kurali ekleme."""
        dd = IaCDriftDetector()
        result = dd.add_remediation_rule(
            "test", "alert", False,
        )
        assert result["pattern"] == "test"

    def test_remediate(self):
        """Duzeltme."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        result = dd.remediate("s.w")
        assert result["status"] == "remediated"

    def test_remediate_no_baseline(self):
        """Temel durum olmadan duzeltme."""
        dd = IaCDriftDetector()
        result = dd.remediate("s.w")
        assert "error" in result

    def test_remediate_ignored(self):
        """Yoksayilan duzeltme."""
        dd = IaCDriftDetector()
        dd.set_baseline("test.w", {"cpu": 2})
        dd.add_remediation_rule(
            "test", "ignore",
        )
        result = dd.remediate("test.w")
        assert result["status"] == "ignored"

    def test_get_drifts(self):
        """Kaymalari getirme."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        dd.check("s.w", {"cpu": 4})
        drifts = dd.get_drifts()
        assert len(drifts) == 1

    def test_get_drifts_by_severity(self):
        """Ciddiyete gore kaymalar."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w1", {"cpu": 2})
        dd.set_baseline(
            "s.w2", {"a": 1, "b": 2, "c": 3},
        )
        dd.check("s.w1", {"cpu": 4})
        dd.check(
            "s.w2", {"a": 9, "b": 9, "c": 9},
        )
        low = dd.get_drifts(severity="low")
        assert len(low) == 1

    def test_get_alerts(self):
        """Uyarilari getirme."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        dd.check("s.w", {"cpu": 4})
        alerts = dd.get_alerts()
        assert len(alerts) == 1

    def test_get_report(self):
        """Rapor olusturma."""
        dd = IaCDriftDetector()
        dd.set_baseline("s.w", {"cpu": 2})
        dd.check("s.w", {"cpu": 4})
        report = dd.get_report()
        assert report["total_baselines"] == 1
        assert report["total_drifts"] == 1


# ==================== ModuleManager ====================


class TestModuleManager:
    """ModuleManager testleri."""

    def test_init(self):
        """Baslatma testi."""
        mm = ModuleManager()
        assert mm.module_count == 0
        assert mm.instance_count == 0

    def test_register(self):
        """Modul kaydetme."""
        mm = ModuleManager()
        result = mm.register(
            "vpc", "1.0.0",
            inputs={"cidr": {"type": "string"}},
            outputs={"vpc_id": {}},
            resources={"aws_vpc": {}},
        )
        assert result["name"] == "vpc"
        assert result["version"] == "1.0.0"
        assert mm.module_count == 1
        assert mm.registered_count == 1

    def test_register_with_metadata(self):
        """Metadatali kayit."""
        mm = ModuleManager()
        mm.register(
            "vpc", "1.0.0",
            description="VPC module",
            author="admin",
            dependencies=["network"],
        )
        mod = mm.get("vpc", "1.0.0")
        assert mod["description"] == "VPC module"
        assert mod["author"] == "admin"

    def test_get_specific_version(self):
        """Belirli surum getirme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.register("vpc", "2.0.0")
        mod = mm.get("vpc", "1.0.0")
        assert mod["version"] == "1.0.0"

    def test_get_latest(self):
        """Son surum getirme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.register("vpc", "2.0.0")
        mod = mm.get("vpc")
        assert mod["version"] == "2.0.0"

    def test_get_nonexistent(self):
        """Olmayan modul getirme."""
        mm = ModuleManager()
        assert mm.get("x") is None

    def test_unregister(self):
        """Modul kayit silme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        assert mm.unregister("vpc", "1.0.0")
        assert mm.module_count == 0

    def test_unregister_nonexistent(self):
        """Olmayan modul silme."""
        mm = ModuleManager()
        assert not mm.unregister("x", "1.0.0")

    def test_instantiate(self):
        """Modul ornekleme."""
        mm = ModuleManager()
        mm.register(
            "vpc", "1.0.0",
            inputs={
                "cidr": {"type": "string"},
            },
        )
        result = mm.instantiate(
            "vpc1", "vpc", "1.0.0",
            {"cidr": "10.0.0.0/16"},
        )
        assert result["instance_id"] == "vpc1"
        assert mm.instance_count == 1
        assert mm.instantiated_count == 1

    def test_instantiate_nonexistent(self):
        """Olmayan modul ornekleme."""
        mm = ModuleManager()
        result = mm.instantiate(
            "i1", "x", "1.0.0",
        )
        assert "error" in result

    def test_instantiate_with_defaults(self):
        """Varsayilan degerli ornekleme."""
        mm = ModuleManager()
        mm.register(
            "vpc", "1.0.0",
            inputs={
                "cidr": {
                    "default": "10.0.0.0/16",
                },
            },
        )
        result = mm.instantiate(
            "vpc1", "vpc", "1.0.0",
        )
        assert "error" not in result
        inst = mm.get_instance("vpc1")
        assert inst["inputs"]["cidr"] == (
            "10.0.0.0/16"
        )

    def test_get_instance(self):
        """Ornek getirme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.instantiate("i1", "vpc", "1.0.0")
        inst = mm.get_instance("i1")
        assert inst is not None

    def test_get_instance_nonexistent(self):
        """Olmayan ornek."""
        mm = ModuleManager()
        assert mm.get_instance("x") is None

    def test_remove_instance(self):
        """Ornek kaldirma."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.instantiate("i1", "vpc", "1.0.0")
        assert mm.remove_instance("i1")
        assert mm.instance_count == 0

    def test_remove_instance_nonexistent(self):
        """Olmayan ornek kaldirma."""
        mm = ModuleManager()
        assert not mm.remove_instance("x")

    def test_list_modules(self):
        """Modul listeleme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.register("subnet", "1.0.0")
        assert len(mm.list_modules()) == 2

    def test_list_modules_filter(self):
        """Filtreli listeleme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.register("subnet", "1.0.0")
        result = mm.list_modules("vpc")
        assert len(result) == 1

    def test_list_versions(self):
        """Surum listeleme."""
        mm = ModuleManager()
        mm.register("vpc", "1.0.0")
        mm.register("vpc", "2.0.0")
        versions = mm.list_versions("vpc")
        assert versions == ["1.0.0", "2.0.0"]

    def test_get_dependencies(self):
        """Bagimlilik getirme."""
        mm = ModuleManager()
        mm.register(
            "subnet", "1.0.0",
            dependencies=["vpc"],
        )
        deps = mm.get_dependencies(
            "subnet", "1.0.0",
        )
        assert "vpc" in deps

    def test_get_dependencies_nonexistent(self):
        """Olmayan modul bagimliliklari."""
        mm = ModuleManager()
        assert mm.get_dependencies(
            "x", "1.0.0",
        ) == []

    def test_validate_inputs_valid(self):
        """Gecerli giris dogrulama."""
        mm = ModuleManager()
        mm.register(
            "vpc", "1.0.0",
            inputs={"cidr": {"type": "string"}},
        )
        result = mm.validate_inputs(
            "vpc", "1.0.0",
            {"cidr": "10.0.0.0/16"},
        )
        assert result["valid"]

    def test_validate_inputs_missing(self):
        """Eksik giris dogrulama."""
        mm = ModuleManager()
        mm.register(
            "vpc", "1.0.0",
            inputs={"cidr": {"type": "string"}},
        )
        result = mm.validate_inputs(
            "vpc", "1.0.0", {},
        )
        assert not result["valid"]
        assert "cidr" in result["missing"]

    def test_validate_inputs_with_default(self):
        """Varsayilanli giris dogrulama."""
        mm = ModuleManager()
        mm.register(
            "vpc", "1.0.0",
            inputs={
                "cidr": {
                    "default": "10.0.0.0/16",
                },
            },
        )
        result = mm.validate_inputs(
            "vpc", "1.0.0", {},
        )
        assert result["valid"]

    def test_validate_inputs_nonexistent(self):
        """Olmayan modul dogrulama."""
        mm = ModuleManager()
        result = mm.validate_inputs(
            "x", "1.0.0", {},
        )
        assert not result["valid"]


# ==================== IaCComplianceChecker ====================


class TestIaCComplianceChecker:
    """IaCComplianceChecker testleri."""

    def test_init(self):
        """Baslatma testi."""
        cc = IaCComplianceChecker()
        assert cc.policy_count == 0
        assert cc.custom_rule_count == 0
        assert cc.check_count == 0

    def test_add_policy(self):
        """Politika ekleme."""
        cc = IaCComplianceChecker()
        result = cc.add_policy(
            "encryption",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
            severity="high",
        )
        assert result["name"] == "encryption"
        assert cc.policy_count == 1

    def test_remove_policy(self):
        """Politika kaldirma."""
        cc = IaCComplianceChecker()
        cc.add_policy("p1", rules=[])
        assert cc.remove_policy("p1")
        assert cc.policy_count == 0

    def test_remove_policy_nonexistent(self):
        """Olmayan politika kaldirma."""
        cc = IaCComplianceChecker()
        assert not cc.remove_policy("x")

    def test_enable_disable_policy(self):
        """Politika etkin/devre disi."""
        cc = IaCComplianceChecker()
        cc.add_policy("p1", rules=[])
        assert cc.disable_policy("p1")
        assert cc.enable_policy("p1")

    def test_enable_nonexistent(self):
        """Olmayan politika etkinlestirme."""
        cc = IaCComplianceChecker()
        assert not cc.enable_policy("x")

    def test_disable_nonexistent(self):
        """Olmayan politika devre disi."""
        cc = IaCComplianceChecker()
        assert not cc.disable_policy("x")

    def test_check_compliant(self):
        """Uyumlu kaynak."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
        )
        result = cc.check(
            "s.w", {"encrypted": True},
        )
        assert result["compliant"]
        assert cc.check_count == 1

    def test_check_non_compliant(self):
        """Uyumsuz kaynak."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
            severity="high",
        )
        result = cc.check(
            "s.w", {"encrypted": False},
        )
        assert not result["compliant"]
        assert len(result["violations"]) == 1

    def test_check_exists_operator(self):
        """Exists operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "tag",
            rules=[{
                "field": "tags",
                "operator": "exists",
            }],
        )
        assert cc.check(
            "s.w", {"tags": ["a"]},
        )["compliant"]
        assert not cc.check(
            "s.w2", {},
        )["compliant"]

    def test_check_not_equals(self):
        """Not equals operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "no_public",
            rules=[{
                "field": "public",
                "operator": "not_equals",
                "value": True,
            }],
        )
        assert cc.check(
            "s.w", {"public": False},
        )["compliant"]

    def test_check_contains(self):
        """Contains operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "region",
            rules=[{
                "field": "name",
                "operator": "contains",
                "value": "prod",
            }],
        )
        assert cc.check(
            "s.w", {"name": "prod-web"},
        )["compliant"]

    def test_check_in_operator(self):
        """In operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "size",
            rules=[{
                "field": "size",
                "operator": "in",
                "value": ["small", "medium"],
            }],
        )
        assert cc.check(
            "s.w", {"size": "small"},
        )["compliant"]

    def test_check_not_in_operator(self):
        """Not in operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "no_large",
            rules=[{
                "field": "size",
                "operator": "not_in",
                "value": ["xlarge"],
            }],
        )
        assert cc.check(
            "s.w", {"size": "small"},
        )["compliant"]

    def test_check_min_operator(self):
        """Min operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "min_cpu",
            rules=[{
                "field": "cpu",
                "operator": "min",
                "value": 2,
            }],
        )
        assert cc.check(
            "s.w", {"cpu": 4},
        )["compliant"]
        assert not cc.check(
            "s.w2", {"cpu": 1},
        )["compliant"]

    def test_check_max_operator(self):
        """Max operatoru."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "max_cost",
            rules=[{
                "field": "cost",
                "operator": "max",
                "value": 100,
            }],
        )
        assert cc.check(
            "s.w", {"cost": 50},
        )["compliant"]
        assert not cc.check(
            "s.w2", {"cost": 200},
        )["compliant"]

    def test_check_disabled_policy(self):
        """Devre disi politika."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
        )
        cc.disable_policy("enc")
        result = cc.check(
            "s.w", {"encrypted": False},
        )
        assert result["compliant"]

    def test_check_with_exemption(self):
        """Muafiyetli kontrol."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
        )
        cc.add_exemption("s.w", "enc", "test")
        result = cc.check(
            "s.w", {"encrypted": False},
        )
        assert result["compliant"]
        assert cc.exemption_count == 1

    def test_add_custom_rule(self):
        """Ozel kural ekleme."""
        cc = IaCComplianceChecker()
        cc.add_custom_rule(
            "has_name",
            lambda d: "name" in d,
        )
        assert cc.custom_rule_count == 1

    def test_custom_rule_check(self):
        """Ozel kural kontrolu."""
        cc = IaCComplianceChecker()
        cc.add_custom_rule(
            "has_name",
            lambda d: "name" in d,
        )
        assert cc.check(
            "s.w", {"name": "web"},
        )["compliant"]
        assert not cc.check(
            "s.w2", {"cpu": 2},
        )["compliant"]

    def test_warnings_for_low_severity(self):
        """Dusuk ciddiyet uyarilari."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "tag",
            rules=[{
                "field": "tags",
                "operator": "exists",
            }],
            severity="low",
        )
        result = cc.check("s.w", {})
        assert result["compliant"]
        assert len(result["warnings"]) == 1

    def test_check_all(self):
        """Toplu kontrol."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
        )
        result = cc.check_all({
            "s.w1": {"encrypted": True},
            "s.w2": {"encrypted": False},
        })
        assert result["total"] == 2
        assert result["compliant"] == 1
        assert result["non_compliant"] == 1

    def test_get_report(self):
        """Rapor olusturma."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
            severity="high",
        )
        cc.check("s.w", {"encrypted": False})
        report = cc.get_report()
        assert report["total_checks"] == 1
        assert report["failed"] >= 1

    def test_get_results(self):
        """Sonuc getirme."""
        cc = IaCComplianceChecker()
        cc.check("s.w", {"cpu": 2})
        results = cc.get_results()
        assert len(results) == 1
        assert cc.result_count == 1

    def test_get_results_compliant_only(self):
        """Sadece uyumlu sonuclar."""
        cc = IaCComplianceChecker()
        cc.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
        )
        cc.check("s.w1", {"encrypted": True})
        cc.check("s.w2", {"encrypted": False})
        results = cc.get_results(
            compliant_only=True,
        )
        assert len(results) == 1


# ==================== IaCOrchestrator ====================


class TestIaCOrchestrator:
    """IaCOrchestrator testleri."""

    def test_init(self):
        """Baslatma testi."""
        orch = IaCOrchestrator()
        assert orch.pipeline_count == 0
        assert orch.apply_count == 0
        assert orch.rollback_count == 0

    def test_init_custom_backend(self):
        """Ozel arka uc."""
        orch = IaCOrchestrator(
            state_backend="s3",
        )
        assert orch.state_manager.backend == "s3"

    def test_components_initialized(self):
        """Bilesenlerin baslatilmasi."""
        orch = IaCOrchestrator()
        assert orch.definer is not None
        assert orch.template_engine is not None
        assert orch.state_manager is not None
        assert orch.plan_generator is not None
        assert orch.provisioner is not None
        assert orch.drift_detector is not None
        assert orch.module_manager is not None
        assert orch.compliance_checker is not None

    def test_define_and_plan(self):
        """Tanimla ve planla."""
        orch = IaCOrchestrator()
        plan = orch.define_and_plan(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        assert plan["plan_id"] == "p1"
        assert plan["summary"]["creates"] == 1

    def test_plan_and_apply(self):
        """Planla ve uygula."""
        orch = IaCOrchestrator()
        result = orch.plan_and_apply(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        assert result["applied"] == 1
        assert result["errors"] == 0
        assert orch.apply_count == 1

    def test_apply_not_approved(self):
        """Onaylanmamis uygulama."""
        orch = IaCOrchestrator()
        orch.define_and_plan(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        result = orch.apply("p1")
        assert result["error"] == "not_approved"

    def test_apply_approved(self):
        """Onaylanmis uygulama."""
        orch = IaCOrchestrator()
        orch.define_and_plan(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        orch.plan_generator.approve(
            "p1", "admin",
        )
        result = orch.apply("p1")
        assert result["applied"] == 1

    def test_apply_plan_not_found(self):
        """Olmayan plan uygulama."""
        orch = IaCOrchestrator()
        result = orch.apply("x")
        assert "error" in result

    def test_apply_with_compliance_fail(self):
        """Uyumluluk basarisiz uygulama."""
        orch = IaCOrchestrator()
        orch.compliance_checker.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
            severity="high",
        )
        orch.define_and_plan(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        orch.plan_generator.approve(
            "p1", "admin",
        )
        result = orch.apply("p1")
        assert result["error"] == (
            "compliance_failed"
        )

    def test_rollback(self):
        """Geri alma."""
        orch = IaCOrchestrator()
        orch.plan_and_apply(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        result = orch.rollback(1)
        assert result["rolled_back"] >= 1
        assert orch.rollback_count == 1

    def test_check_drift(self):
        """Kayma kontrolu."""
        orch = IaCOrchestrator()
        orch.plan_and_apply(
            "p1",
            {"server.web": {"cpu": 2}},
        )
        result = orch.check_drift({
            "server.web": {"cpu": 4},
        })
        assert result["drifted"] >= 1

    def test_render_template(self):
        """Sablon render."""
        orch = IaCOrchestrator()
        result = orch.render_template(
            "Hello {{ name }}!",
            {"name": "Atlas"},
        )
        assert result == "Hello Atlas!"

    def test_run_compliance(self):
        """Uyumluluk denetimi."""
        orch = IaCOrchestrator()
        orch.compliance_checker.add_policy(
            "enc",
            rules=[{
                "field": "encrypted",
                "operator": "equals",
                "value": True,
            }],
        )
        result = orch.run_compliance({
            "s.w": {"encrypted": True},
        })
        assert result["compliant"] == 1

    def test_create_pipeline(self):
        """Pipeline olusturma."""
        orch = IaCOrchestrator()
        result = orch.create_pipeline(
            "pipe1",
            ["validate", "plan", "approve",
             "apply"],
        )
        assert result["stages"] == 4
        assert orch.pipeline_count == 1

    def test_run_pipeline(self):
        """Pipeline calistirma."""
        orch = IaCOrchestrator()
        orch.create_pipeline(
            "pipe1",
            ["plan", "approve", "apply"],
        )
        result = orch.run_pipeline(
            "pipe1",
            {"server.web": {"cpu": 2}},
        )
        assert result["status"] == "completed"

    def test_run_pipeline_not_found(self):
        """Olmayan pipeline calistirma."""
        orch = IaCOrchestrator()
        result = orch.run_pipeline("x", {})
        assert "error" in result

    def test_run_pipeline_with_validate(self):
        """Dogrulama pipeline."""
        orch = IaCOrchestrator()
        orch.create_pipeline(
            "pipe1",
            ["validate", "plan", "approve",
             "apply"],
        )
        result = orch.run_pipeline(
            "pipe1",
            {"server.web": {"cpu": 2}},
        )
        assert result["status"] == "completed"

    def test_run_pipeline_verify_stage(self):
        """Dogrulama asamasi."""
        orch = IaCOrchestrator()
        orch.create_pipeline(
            "pipe1",
            ["plan", "approve", "apply",
             "verify"],
        )
        result = orch.run_pipeline(
            "pipe1",
            {"server.web": {"cpu": 2}},
        )
        assert result["status"] == "completed"
        assert result["results"]["verify"][
            "status"
        ] == "verified"

    def test_run_pipeline_unknown_stage(self):
        """Bilinmeyen asama."""
        orch = IaCOrchestrator()
        orch.create_pipeline(
            "pipe1", ["custom_stage"],
        )
        result = orch.run_pipeline(
            "pipe1", {"s.w": {}},
        )
        assert result["status"] == "completed"

    def test_get_status(self):
        """Durum bilgisi."""
        orch = IaCOrchestrator()
        orch.plan_and_apply(
            "p1", {"s.w": {"cpu": 2}},
        )
        status = orch.get_status()
        assert status["resources_defined"] >= 1
        assert status["plans"] >= 1
        assert status["provisioned"] >= 1

    def test_state_updated_after_apply(self):
        """Uygulama sonrasi durum."""
        orch = IaCOrchestrator()
        orch.plan_and_apply(
            "p1", {"server.web": {"cpu": 2}},
        )
        state = orch.state_manager.get_resource(
            "server.web",
        )
        assert state is not None
        assert state["cpu"] == 2

    def test_baseline_set_after_apply(self):
        """Uygulama sonrasi baseline."""
        orch = IaCOrchestrator()
        orch.plan_and_apply(
            "p1", {"server.web": {"cpu": 2}},
        )
        assert (
            orch.drift_detector.baseline_count
            >= 1
        )


# ==================== Models ====================


class TestIaCModels:
    """IaC model testleri."""

    def test_resource_status_values(self):
        """ResourceStatus degerleri."""
        assert ResourceStatus.PENDING == "pending"
        assert ResourceStatus.CREATED == "created"
        assert ResourceStatus.DELETED == "deleted"

    def test_change_action_values(self):
        """ChangeAction degerleri."""
        assert ChangeAction.CREATE == "create"
        assert ChangeAction.UPDATE == "update"
        assert ChangeAction.DELETE == "delete"
        assert ChangeAction.REPLACE == "replace"
        assert ChangeAction.NO_OP == "no_op"
        assert ChangeAction.READ == "read"

    def test_drift_severity_values(self):
        """DriftSeverity degerleri."""
        assert DriftSeverity.NONE == "none"
        assert DriftSeverity.LOW == "low"
        assert DriftSeverity.CRITICAL == (
            "critical"
        )

    def test_compliance_level_values(self):
        """ComplianceLevel degerleri."""
        assert ComplianceLevel.COMPLIANT == (
            "compliant"
        )
        assert ComplianceLevel.WARNING == (
            "warning"
        )

    def test_state_backend_values(self):
        """StateBackend degerleri."""
        assert StateBackend.LOCAL == "local"
        assert StateBackend.S3 == "s3"
        assert StateBackend.POSTGRESQL == (
            "postgresql"
        )

    def test_module_status_values(self):
        """ModuleStatus degerleri."""
        assert ModuleStatus.ACTIVE == "active"
        assert ModuleStatus.DEPRECATED == (
            "deprecated"
        )

    def test_resource_record(self):
        """ResourceRecord modeli."""
        r = ResourceRecord(
            resource_type="server",
            name="web1",
        )
        assert r.resource_type == "server"
        assert r.name == "web1"
        assert r.status == ResourceStatus.PENDING
        assert len(r.resource_id) == 8

    def test_plan_record(self):
        """PlanRecord modeli."""
        p = PlanRecord(
            creates=2, updates=1, deletes=0,
        )
        assert p.creates == 2
        assert not p.approved
        assert len(p.plan_id) == 8

    def test_drift_record(self):
        """DriftRecord modeli."""
        d = DriftRecord(
            resource_type="server",
            severity=DriftSeverity.HIGH,
            drifted_properties=3,
        )
        assert d.severity == DriftSeverity.HIGH
        assert d.drifted_properties == 3

    def test_iac_snapshot(self):
        """IaCSnapshot modeli."""
        s = IaCSnapshot(
            total_resources=10,
            drifted_resources=2,
            compliance_score=80.0,
        )
        assert s.total_resources == 10
        assert s.compliance_score == 80.0


# ==================== Config ====================


class TestIaCConfig:
    """IaC config testleri."""

    def test_iac_enabled(self):
        """iac_enabled ayari."""
        from app.config import settings
        assert hasattr(settings, "iac_enabled")

    def test_state_backend(self):
        """state_backend ayari."""
        from app.config import settings
        assert hasattr(settings, "state_backend")

    def test_auto_approve(self):
        """auto_approve ayari."""
        from app.config import settings
        assert hasattr(settings, "auto_approve")

    def test_parallel_operations(self):
        """parallel_operations ayari."""
        from app.config import settings
        assert hasattr(
            settings, "parallel_operations",
        )

    def test_iac_drift_check_interval(self):
        """iac_drift_check_interval ayari."""
        from app.config import settings
        assert hasattr(
            settings,
            "iac_drift_check_interval",
        )


# ==================== Imports ====================


class TestIaCImports:
    """IaC import testleri."""

    def test_import_all_from_package(self):
        """Paket uzerinden import."""
        from app.core.iac import (
            IaCComplianceChecker,
            IaCDriftDetector,
            IaCOrchestrator,
            IaCStateManager,
            IaCTemplateEngine,
            ModuleManager,
            PlanGenerator,
            ResourceDefiner,
            ResourceProvisioner,
        )
        assert IaCComplianceChecker is not None
        assert IaCDriftDetector is not None
        assert IaCOrchestrator is not None
        assert IaCStateManager is not None
        assert IaCTemplateEngine is not None
        assert ModuleManager is not None
        assert PlanGenerator is not None
        assert ResourceDefiner is not None
        assert ResourceProvisioner is not None

    def test_import_models(self):
        """Model import."""
        from app.models.iac_models import (
            ResourceStatus,
            ChangeAction,
            DriftSeverity,
            ComplianceLevel,
            StateBackend,
            ModuleStatus,
            ResourceRecord,
            PlanRecord,
            DriftRecord,
            IaCSnapshot,
        )
        assert ResourceStatus is not None
        assert IaCSnapshot is not None
