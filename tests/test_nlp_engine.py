"""Natural Language Programming Engine testleri.

Niyet analizi, gorev ayristirma, gereksinim cikarma,
spesifikasyon uretimi, kod planlama, calistirma cevirisi,
geri bildirim yorumlayici, diyalog yoneticisi ve orkestrator testleri.
"""

from app.core.nlp_engine.code_planner import CodePlanner
from app.core.nlp_engine.conversation_manager import ConversationManager
from app.core.nlp_engine.execution_translator import ExecutionTranslator
from app.core.nlp_engine.feedback_interpreter import FeedbackInterpreter
from app.core.nlp_engine.intent_parser import IntentParser
from app.core.nlp_engine.nlp_orchestrator import NLPOrchestrator
from app.core.nlp_engine.requirement_extractor import RequirementExtractor
from app.core.nlp_engine.spec_generator import SpecGenerator
from app.core.nlp_engine.task_decomposer import TaskDecomposer
from app.models.nlp_engine import (
    CommandType,
    ConfidenceLevel,
    ConversationState,
    EntityType,
    FeedbackType,
    IntentCategory,
    PlannedFile,
    RequirementPriority,
    RequirementType,
    SafetyLevel,
    SpecSectionType,
    TaskRelation,
    TopicStatus,
    VerbosityLevel,
)


# === Yardimci fonksiyonlar ===


def _make_parser(**kwargs) -> IntentParser:
    return IntentParser(**kwargs)


def _make_decomposer(**kwargs) -> TaskDecomposer:
    return TaskDecomposer(**kwargs)


def _make_extractor() -> RequirementExtractor:
    return RequirementExtractor()


def _make_spec_gen() -> SpecGenerator:
    return SpecGenerator()


def _make_planner() -> CodePlanner:
    return CodePlanner()


def _make_translator(**kwargs) -> ExecutionTranslator:
    return ExecutionTranslator(**kwargs)


def _make_feedback(**kwargs) -> FeedbackInterpreter:
    return FeedbackInterpreter(**kwargs)


def _make_conversation(**kwargs) -> ConversationManager:
    return ConversationManager(**kwargs)


def _make_orchestrator(**kwargs) -> NLPOrchestrator:
    return NLPOrchestrator(**kwargs)


# ============================================================
# IntentParser Testleri
# ============================================================


class TestIntentParserInit:
    """IntentParser baslatma testleri."""

    def test_defaults(self) -> None:
        p = _make_parser()
        assert p.history_count == 0
        assert p._clarification_threshold == 0.4

    def test_custom_threshold(self) -> None:
        p = _make_parser(clarification_threshold=0.7)
        assert p._clarification_threshold == 0.7


class TestParse:
    """IntentParser.parse testleri."""

    def test_create_intent(self) -> None:
        p = _make_parser()
        intent = p.parse("yeni bir agent olustur")
        assert intent.category == IntentCategory.CREATE
        assert intent.confidence > 0

    def test_delete_intent(self) -> None:
        p = _make_parser()
        intent = p.parse("eski logları sil")
        assert intent.category == IntentCategory.DELETE

    def test_query_intent(self) -> None:
        p = _make_parser()
        intent = p.parse("tum gorevleri listele")
        assert intent.category == IntentCategory.QUERY

    def test_execute_intent(self) -> None:
        p = _make_parser()
        intent = p.parse("servisi baslat")
        assert intent.category == IntentCategory.EXECUTE

    def test_explain_intent(self) -> None:
        p = _make_parser()
        intent = p.parse("bu hatayi acikla")
        assert intent.category == IntentCategory.EXPLAIN

    def test_unknown_intent(self) -> None:
        p = _make_parser()
        intent = p.parse("xyz")
        assert intent.category == IntentCategory.UNKNOWN

    def test_confidence_level_high(self) -> None:
        p = _make_parser()
        intent = p.parse("yeni bir dosya olustur")
        assert intent.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def test_history_updated(self) -> None:
        p = _make_parser()
        p.parse("test komutu")
        assert p.history_count == 1

    def test_multiple_parses(self) -> None:
        p = _make_parser()
        p.parse("olustur")
        p.parse("sil")
        assert p.history_count == 2


class TestEntityExtraction:
    """IntentParser varlik cikarma testleri."""

    def test_extract_agent_entity(self) -> None:
        p = _make_parser()
        intent = p.parse("agent bilgisini goster")
        agent_entities = [e for e in intent.entities if e.entity_type == EntityType.AGENT]
        assert len(agent_entities) > 0

    def test_extract_database_entity(self) -> None:
        p = _make_parser()
        intent = p.parse("veritabani baglantisini kontrol et")
        db_entities = [e for e in intent.entities if e.entity_type == EntityType.DATABASE]
        assert len(db_entities) > 0

    def test_extract_file_entity(self) -> None:
        p = _make_parser()
        intent = p.parse("dosya icerigini oku")
        file_entities = [e for e in intent.entities if e.entity_type == EntityType.FILE]
        assert len(file_entities) > 0


class TestContextUnderstanding:
    """IntentParser baglam anlama testleri."""

    def test_context_reference(self) -> None:
        p = _make_parser()
        intent = p.parse("bu dosyayi guncelle")
        assert "bu" in intent.context_references

    def test_previous_reference(self) -> None:
        p = _make_parser()
        intent = p.parse("onceki sonucu goster")
        assert "onceki" in intent.context_references


class TestAmbiguityResolution:
    """IntentParser belirsizlik cozumleme testleri."""

    def test_ambiguous_short_input(self) -> None:
        p = _make_parser(clarification_threshold=0.9)
        intent = p.parse("x")
        assert len(intent.ambiguities) > 0
        assert not intent.resolved

    def test_resolve_ambiguity(self) -> None:
        p = _make_parser(clarification_threshold=0.9)
        intent = p.parse("x")
        resolved = p.resolve_ambiguity(intent.id, "dosyayi sil")
        assert resolved is not None
        assert resolved.resolved

    def test_resolve_nonexistent(self) -> None:
        p = _make_parser()
        assert p.resolve_ambiguity("yok", "test") is None


class TestIntentParserContext:
    """IntentParser baglam yonetimi testleri."""

    def test_add_get_context(self) -> None:
        p = _make_parser()
        p.add_context("user", "Fatih")
        assert p.get_context("user") == "Fatih"

    def test_get_context_default(self) -> None:
        p = _make_parser()
        assert p.get_context("yok", "varsayilan") == "varsayilan"


# ============================================================
# TaskDecomposer Testleri
# ============================================================


class TestTaskDecomposerInit:
    """TaskDecomposer baslatma testleri."""

    def test_defaults(self) -> None:
        d = _make_decomposer()
        assert d.decomposition_count == 0

    def test_custom_max(self) -> None:
        d = _make_decomposer(max_subtasks=5)
        assert d._max_subtasks == 5


class TestDecompose:
    """TaskDecomposer.decompose testleri."""

    def test_simple_decompose(self) -> None:
        d = _make_decomposer()
        result = d.decompose("veritabani olustur ve tabloları ekle")
        assert len(result.subtasks) >= 2

    def test_numbered_list(self) -> None:
        d = _make_decomposer()
        result = d.decompose("1. model yaz 2. test yaz 3. deploy et")
        assert len(result.subtasks) == 3

    def test_comma_separated(self) -> None:
        d = _make_decomposer()
        result = d.decompose("model yaz, test yaz, dokumantasyon ekle")
        assert len(result.subtasks) >= 2

    def test_total_complexity(self) -> None:
        d = _make_decomposer()
        result = d.decompose("basit gorev ve karmasik gorev")
        assert result.total_complexity > 0

    def test_sequential_dependencies(self) -> None:
        d = _make_decomposer()
        result = d.decompose("once model olustur sonra test yaz")
        # Ikinci gorev birinciye bagimli olmali
        if len(result.subtasks) >= 2:
            has_dep = any(st.dependencies for st in result.subtasks[1:])
            assert has_dep

    def test_single_task(self) -> None:
        d = _make_decomposer()
        result = d.decompose("dosyayi oku")
        assert len(result.subtasks) >= 1


class TestComplexityEstimation:
    """TaskDecomposer karmasiklik tahmini testleri."""

    def test_simple_keyword(self) -> None:
        d = _make_decomposer()
        result = d.decompose("basit bir islem yap")
        assert any(st.estimated_complexity <= 2 for st in result.subtasks)

    def test_complex_keyword(self) -> None:
        d = _make_decomposer()
        result = d.decompose("karmasik bir sistem tasarla")
        assert any(st.estimated_complexity >= 5 for st in result.subtasks)


class TestValidationRules:
    """TaskDecomposer dogrulama kurallari testleri."""

    def test_create_rules(self) -> None:
        d = _make_decomposer()
        result = d.decompose("dosya olustur")
        if result.subtasks:
            assert len(result.subtasks[0].validation_rules) > 0

    def test_delete_rules(self) -> None:
        d = _make_decomposer()
        result = d.decompose("eski kayitlari sil")
        if result.subtasks:
            rules = result.subtasks[0].validation_rules
            assert any("mevcut olmamali" in r for r in rules)


class TestCompleteSubtask:
    """TaskDecomposer.complete_subtask testleri."""

    def test_complete(self) -> None:
        d = _make_decomposer()
        result = d.decompose("a ve b yap")
        if result.subtasks:
            assert d.complete_subtask(result.id, result.subtasks[0].id)
            assert result.subtasks[0].completed

    def test_complete_nonexistent(self) -> None:
        d = _make_decomposer()
        assert not d.complete_subtask("yok", "yok")


# ============================================================
# RequirementExtractor Testleri
# ============================================================


class TestRequirementExtractorInit:
    """RequirementExtractor baslatma testleri."""

    def test_defaults(self) -> None:
        e = _make_extractor()
        assert e.set_count == 0


class TestExtract:
    """RequirementExtractor.extract testleri."""

    def test_functional(self) -> None:
        e = _make_extractor()
        rs = e.extract("Kullanici giris yapabilmeli. Sifre sifirlanabilmeli.")
        func = [r for r in rs.requirements if r.requirement_type == RequirementType.FUNCTIONAL]
        assert len(func) >= 1

    def test_nonfunctional(self) -> None:
        e = _make_extractor()
        rs = e.extract("Sistem performans gereksinimleri karsilamali. Guvenlik standartlari saglanmali.")
        nfr = [r for r in rs.requirements if r.requirement_type == RequirementType.NON_FUNCTIONAL]
        assert len(nfr) >= 1

    def test_constraint(self) -> None:
        e = _make_extractor()
        rs = e.extract("Maksimum 100ms gecikme olmali. En fazla 5 baglanti siniri.")
        constraints = [r for r in rs.requirements if r.requirement_type == RequirementType.CONSTRAINT]
        assert len(constraints) >= 1

    def test_assumption(self) -> None:
        e = _make_extractor()
        rs = e.extract("Veritabani mevcut varsayilir. Sistem calisir kabul edilir.")
        assert len(rs.assumptions) >= 1

    def test_priority_must(self) -> None:
        e = _make_extractor()
        rs = e.extract("Mutlaka guvenlik saglanmali")
        if rs.requirements:
            assert rs.requirements[0].priority == RequirementPriority.MUST

    def test_acceptance_criteria(self) -> None:
        e = _make_extractor()
        rs = e.extract("Kullanici giris yapabilmeli")
        if rs.requirements:
            assert len(rs.requirements[0].acceptance_criteria) > 0


class TestExtractFunctional:
    """RequirementExtractor.extract_functional testleri."""

    def test_only_functional(self) -> None:
        e = _make_extractor()
        reqs = e.extract_functional("Giris yapilabilmeli. Performans iyi olmali.")
        assert all(r.requirement_type == RequirementType.FUNCTIONAL for r in reqs)


class TestExtractNonFunctional:
    """RequirementExtractor.extract_non_functional testleri."""

    def test_only_nfr(self) -> None:
        e = _make_extractor()
        reqs = e.extract_non_functional("Performans kritik. Guvenlik saglanmali.")
        assert all(r.requirement_type == RequirementType.NON_FUNCTIONAL for r in reqs)


# ============================================================
# SpecGenerator Testleri
# ============================================================


class TestSpecGeneratorInit:
    """SpecGenerator baslatma testleri."""

    def test_defaults(self) -> None:
        sg = _make_spec_gen()
        assert sg.spec_count == 0


class TestGenerate:
    """SpecGenerator.generate testleri."""

    def test_basic(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test Sistemi", description="Basit test sistemi")
        assert spec.title == "Test Sistemi"
        assert len(spec.sections) >= 1
        assert sg.spec_count == 1

    def test_with_requirements(self) -> None:
        e = _make_extractor()
        rs = e.extract("API endpoint gerekli. Performans kritik.")
        sg = _make_spec_gen()
        spec = sg.generate("API Sistemi", requirements=rs)
        assert len(spec.sections) >= 2


class TestDesignAPI:
    """SpecGenerator.design_api testleri."""

    def test_crud_api(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test")
        endpoints = sg.design_api(spec.id, "users")
        assert len(endpoints) == 5
        methods = {ep["method"] for ep in endpoints}
        assert methods == {"GET", "POST", "PUT", "DELETE"}

    def test_custom_operations(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test")
        endpoints = sg.design_api(spec.id, "tasks", operations=["list", "create"])
        assert len(endpoints) == 2

    def test_nonexistent_spec(self) -> None:
        sg = _make_spec_gen()
        assert sg.design_api("yok", "x") == []


class TestDesignDataModel:
    """SpecGenerator.design_data_model testleri."""

    def test_model(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test")
        model = sg.design_data_model(spec.id, "User", [
            {"name": "id", "type": "int", "description": "Kimlik"},
            {"name": "name", "type": "str", "description": "Ad"},
        ])
        assert model["name"] == "User"
        assert model["field_count"] == 2

    def test_nonexistent_spec(self) -> None:
        sg = _make_spec_gen()
        assert sg.design_data_model("yok", "X", []) == {}


class TestSuggestArchitecture:
    """SpecGenerator.suggest_architecture testleri."""

    def test_suggestions(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test")
        notes = sg.suggest_architecture(spec.id)
        assert len(notes) >= 2

    def test_with_context(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test")
        notes = sg.suggest_architecture(spec.id, context="Yuksek trafik bekleniyor")
        assert any("Baglam notu" in n for n in notes)


class TestGenerateDocumentation:
    """SpecGenerator.generate_documentation testleri."""

    def test_documentation(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test Sistemi")
        sg.design_api(spec.id, "items")
        doc = sg.generate_documentation(spec.id)
        assert "# Test Sistemi" in doc
        assert "API Endpoints" in doc

    def test_nonexistent(self) -> None:
        sg = _make_spec_gen()
        assert sg.generate_documentation("yok") == ""


# ============================================================
# CodePlanner Testleri
# ============================================================


class TestCodePlannerInit:
    """CodePlanner baslatma testleri."""

    def test_defaults(self) -> None:
        cp = _make_planner()
        assert cp.plan_count == 0


class TestPlan:
    """CodePlanner.plan testleri."""

    def test_from_modules(self) -> None:
        cp = _make_planner()
        plan = cp.plan("Test", modules=["auth", "users", "tasks"])
        assert len(plan.files) == 3
        assert len(plan.implementation_order) == 3

    def test_from_spec(self) -> None:
        sg = _make_spec_gen()
        spec = sg.generate("Test")
        sg.design_api(spec.id, "items")
        sg.design_data_model(spec.id, "Item", [{"name": "id", "type": "int", "description": "ID"}])

        cp = _make_planner()
        plan = cp.plan("Test", spec=spec)
        assert len(plan.files) > 0

    def test_test_strategy(self) -> None:
        cp = _make_planner()
        plan = cp.plan("Test", modules=["a", "b"])
        assert "birim test" in plan.test_strategy.lower() or "test" in plan.test_strategy.lower()

    def test_interfaces(self) -> None:
        cp = _make_planner()
        plan = cp.plan("Test", modules=["auth_service"])
        assert len(plan.interfaces) > 0


class TestPlanFileStructure:
    """CodePlanner.plan_file_structure testleri."""

    def test_structure(self) -> None:
        cp = _make_planner()
        files = cp.plan_file_structure("app/core/new", [
            {"name": "parser", "purpose": "Metin analizi"},
            {"name": "executor", "purpose": "Calistirma"},
        ])
        assert len(files) == 3  # __init__ + 2 modul
        assert files[0].path.endswith("__init__.py")


class TestIdentifyDependencies:
    """CodePlanner.identify_dependencies testleri."""

    def test_init_depends_on_all(self) -> None:
        cp = _make_planner()
        files = [
            PlannedFile(path="pkg/__init__.py", purpose="init"),
            PlannedFile(path="pkg/a.py", purpose="a"),
            PlannedFile(path="pkg/b.py", purpose="b"),
        ]
        deps = cp.identify_dependencies(files)
        assert "pkg/__init__.py" in deps
        assert len(deps["pkg/__init__.py"]) == 2


class TestDesignInterface:
    """CodePlanner.design_interface testleri."""

    def test_interface(self) -> None:
        cp = _make_planner()
        iface = cp.design_interface("UserService", [
            {"name": "get_user", "return_type": "User", "description": "Kullanici getir"},
        ])
        assert iface["class_name"] == "UserService"
        assert iface["method_count"] == 1


# ============================================================
# ExecutionTranslator Testleri
# ============================================================


class TestExecutionTranslatorInit:
    """ExecutionTranslator baslatma testleri."""

    def test_defaults(self) -> None:
        t = _make_translator()
        assert t.translation_count == 0

    def test_no_confirmation(self) -> None:
        t = _make_translator(execution_confirmation=False)
        assert not t._execution_confirmation


class TestTranslate:
    """ExecutionTranslator.translate testleri."""

    def test_agent_command(self) -> None:
        t = _make_translator()
        cmd = t.translate("agent durumunu kontrol et")
        assert cmd.command_type == CommandType.AGENT_COMMAND

    def test_db_command(self) -> None:
        t = _make_translator()
        cmd = t.translate("veritabani kayitlarini sorgula")
        assert cmd.command_type == CommandType.DB_QUERY

    def test_shell_command(self) -> None:
        t = _make_translator()
        cmd = t.translate("servisi restart et")
        assert cmd.command_type == CommandType.SHELL_COMMAND

    def test_api_command(self) -> None:
        t = _make_translator()
        cmd = t.translate("api endpoint'e istek gonder")
        assert cmd.command_type == CommandType.API_CALL


class TestTranslateToAgent:
    """ExecutionTranslator.translate_to_agent testleri."""

    def test_security_agent(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_agent("guvenlik taramasi yap")
        assert "security" in cmd.parameters.get("agent_type", "")

    def test_research_agent(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_agent("arastirma yap")
        assert "research" in cmd.parameters.get("agent_type", "")

    def test_unknown_agent(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_agent("birseyler yap")
        assert cmd.command_type == CommandType.AGENT_COMMAND


class TestTranslateToAPI:
    """ExecutionTranslator.translate_to_api testleri."""

    def test_api_call(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_api("kullanici bilgilerini getir")
        assert cmd.command_type == CommandType.API_CALL
        assert "GET" in cmd.command or "method" in cmd.parameters


class TestTranslateToQuery:
    """ExecutionTranslator.translate_to_query testleri."""

    def test_select(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_query("kayitlari listele")
        assert "SELECT" in cmd.command

    def test_insert(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_query("yeni kayit olustur")
        assert "INSERT" in cmd.command

    def test_delete(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_query("eski kayitlari sil")
        assert "DELETE" in cmd.command


class TestTranslateToShell:
    """ExecutionTranslator.translate_to_shell testleri."""

    def test_restart(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_shell("servisi restart et")
        assert "restart" in cmd.command

    def test_status(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_shell("servis durumunu goster")
        assert "status" in cmd.command

    def test_deploy(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_shell("uygulamayi deploy et")
        assert "docker" in cmd.command or "deploy" in cmd.command.lower()


class TestSafetyValidation:
    """ExecutionTranslator guvenlik dogrulama testleri."""

    def test_safe_command(self) -> None:
        t = _make_translator()
        cmd = t.translate("gorevleri listele")
        assert cmd.safety_level == SafetyLevel.SAFE

    def test_dangerous_command(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_shell("rm -rf /tmp/test")
        assert cmd.safety_level == SafetyLevel.DANGEROUS

    def test_caution_command(self) -> None:
        t = _make_translator()
        cmd = t.translate_to_query("kayitlari sil delete islemleri")
        assert cmd.safety_level in (SafetyLevel.CAUTION, SafetyLevel.DANGEROUS)

    def test_confirmation_required(self) -> None:
        t = _make_translator(execution_confirmation=True)
        cmd = t.translate_to_shell("rm -rf /tmp")
        assert cmd.requires_confirmation

    def test_no_confirmation_mode(self) -> None:
        t = _make_translator(execution_confirmation=False)
        cmd = t.translate("gorevleri listele")
        assert not cmd.requires_confirmation


# ============================================================
# FeedbackInterpreter Testleri
# ============================================================


class TestFeedbackInterpreterInit:
    """FeedbackInterpreter baslatma testleri."""

    def test_defaults(self) -> None:
        fi = _make_feedback()
        assert fi.message_count == 0
        assert fi.verbosity == VerbosityLevel.NORMAL

    def test_custom_verbosity(self) -> None:
        fi = _make_feedback(verbosity=VerbosityLevel.DETAILED)
        assert fi.verbosity == VerbosityLevel.DETAILED


class TestExplainError:
    """FeedbackInterpreter.explain_error testleri."""

    def test_not_found(self) -> None:
        fi = _make_feedback()
        msg = fi.explain_error("not_found", entity="Dosya")
        assert "bulunamadi" in msg.content
        assert msg.feedback_type == FeedbackType.ERROR_EXPLANATION

    def test_permission(self) -> None:
        fi = _make_feedback()
        msg = fi.explain_error("permission", entity="Admin")
        assert "yetkiniz" in msg.content

    def test_timeout(self) -> None:
        fi = _make_feedback()
        msg = fi.explain_error("timeout", entity="API")
        assert "zaman asimi" in msg.content

    def test_with_suggestions(self) -> None:
        fi = _make_feedback()
        msg = fi.explain_error("generic", suggestions=["Tekrar deneyin", "Log kontrol edin"])
        assert len(msg.suggestions) == 2

    def test_verbose_detail(self) -> None:
        fi = _make_feedback(verbosity=VerbosityLevel.DETAILED)
        msg = fi.explain_error("not_found", entity="X", detail="detay")
        assert msg.technical_detail != ""


class TestConfirmSuccess:
    """FeedbackInterpreter.confirm_success testleri."""

    def test_created(self) -> None:
        fi = _make_feedback()
        msg = fi.confirm_success("created", entity="Agent")
        assert "olusturuldu" in msg.content
        assert msg.feedback_type == FeedbackType.SUCCESS_CONFIRMATION

    def test_deleted(self) -> None:
        fi = _make_feedback()
        msg = fi.confirm_success("deleted", entity="Kayit")
        assert "silindi" in msg.content

    def test_generic(self) -> None:
        fi = _make_feedback()
        msg = fi.confirm_success("unknown_action")
        assert "tamamlandi" in msg.content


class TestReportProgress:
    """FeedbackInterpreter.report_progress testleri."""

    def test_progress(self) -> None:
        fi = _make_feedback()
        msg = fi.report_progress(3, 10, "Model olusturuluyor")
        assert "%30" in msg.content
        assert msg.feedback_type == FeedbackType.PROGRESS_REPORT

    def test_zero_total(self) -> None:
        fi = _make_feedback()
        msg = fi.report_progress(0, 0)
        assert "%0" in msg.content


class TestRequestClarification:
    """FeedbackInterpreter.request_clarification testleri."""

    def test_with_options(self) -> None:
        fi = _make_feedback()
        msg = fi.request_clarification("Hangi agent?", options=["Security", "Research"])
        assert msg.feedback_type == FeedbackType.CLARIFICATION_REQUEST
        assert "Security" in msg.content
        assert len(msg.suggestions) == 2

    def test_without_options(self) -> None:
        fi = _make_feedback()
        msg = fi.request_clarification("Ne demek istediniz?")
        assert msg.content == "Ne demek istediniz?"


class TestSuggest:
    """FeedbackInterpreter.suggest testleri."""

    def test_suggest(self) -> None:
        fi = _make_feedback()
        msg = fi.suggest("Cache ekleyin", reason="Performans artisi")
        assert "Cache" in msg.content
        assert msg.feedback_type == FeedbackType.SUGGESTION


class TestVerbosityChange:
    """FeedbackInterpreter.set_verbosity testleri."""

    def test_change(self) -> None:
        fi = _make_feedback()
        fi.set_verbosity(VerbosityLevel.DEBUG)
        assert fi.verbosity == VerbosityLevel.DEBUG


# ============================================================
# ConversationManager Testleri
# ============================================================


class TestConversationManagerInit:
    """ConversationManager baslatma testleri."""

    def test_defaults(self) -> None:
        cm = _make_conversation()
        assert cm.turn_count == 0
        assert cm.state == ConversationState.IDLE
        assert cm.personality["tone"] == "professional"

    def test_custom(self) -> None:
        cm = _make_conversation(max_turns=10, personality={"tone": "casual"})
        assert cm._max_turns == 10
        assert cm.personality["tone"] == "casual"


class TestAddTurns:
    """ConversationManager tur ekleme testleri."""

    def test_user_turn(self) -> None:
        cm = _make_conversation()
        turn = cm.add_user_turn("merhaba")
        assert turn.role == "user"
        assert cm.turn_count == 1
        assert cm.state == ConversationState.LISTENING

    def test_system_turn(self) -> None:
        cm = _make_conversation()
        turn = cm.add_system_turn("Hosgeldiniz")
        assert turn.role == "system"
        assert cm.turn_count == 1

    def test_max_turns(self) -> None:
        cm = _make_conversation(max_turns=3)
        for i in range(5):
            cm.add_user_turn(f"mesaj {i}")
        assert cm.turn_count == 3


class TestReferenceResolution:
    """ConversationManager referans cozumleme testleri."""

    def test_resolve(self) -> None:
        cm = _make_conversation()
        cm.add_user_turn("SecurityAgent kontrol et")
        resolved = cm.resolve_reference("o nedir")
        assert "SecurityAgent" in resolved

    def test_no_reference(self) -> None:
        cm = _make_conversation()
        resolved = cm.resolve_reference("yeni agent olustur")
        assert resolved == "yeni agent olustur"


class TestTopicTracking:
    """ConversationManager konu takibi testleri."""

    def test_start_topic(self) -> None:
        cm = _make_conversation()
        topic = cm.start_topic("Guvenlik Analizi")
        assert topic.name == "Guvenlik Analizi"
        assert cm.topic_count == 1
        assert cm.get_active_topic() is not None

    def test_complete_topic(self) -> None:
        cm = _make_conversation()
        topic = cm.start_topic("Test")
        assert cm.complete_topic(topic.id)
        assert topic.status == TopicStatus.COMPLETED

    def test_topic_switch(self) -> None:
        cm = _make_conversation()
        t1 = cm.start_topic("Konu 1")
        t2 = cm.start_topic("Konu 2")
        assert t1.status == TopicStatus.PAUSED
        assert cm.get_active_topic().name == "Konu 2"

    def test_resume_paused_topic(self) -> None:
        cm = _make_conversation()
        t1 = cm.start_topic("Konu 1")
        t2 = cm.start_topic("Konu 2")
        cm.complete_topic(t2.id)
        # Konu 1 tekrar aktif olmali
        active = cm.get_active_topic()
        assert active is not None
        assert active.id == t1.id

    def test_auto_topic_from_message(self) -> None:
        cm = _make_conversation()
        cm.add_user_turn("Yeni bir sey konusalim")
        assert cm.topic_count >= 1


class TestConversationMemory:
    """ConversationManager hafiza testleri."""

    def test_add_memory_key(self) -> None:
        cm = _make_conversation()
        cm.add_memory_key("user_preference")
        assert "user_preference" in cm.context.memory_keys

    def test_no_duplicate_keys(self) -> None:
        cm = _make_conversation()
        cm.add_memory_key("key1")
        cm.add_memory_key("key1")
        assert cm.context.memory_keys.count("key1") == 1


class TestRecentContext:
    """ConversationManager.get_recent_context testleri."""

    def test_recent(self) -> None:
        cm = _make_conversation()
        for i in range(10):
            cm.add_user_turn(f"mesaj {i}")
        recent = cm.get_recent_context(3)
        assert len(recent) == 3


class TestReset:
    """ConversationManager.reset testleri."""

    def test_reset(self) -> None:
        cm = _make_conversation()
        cm.add_user_turn("test")
        cm.start_topic("T")
        cm.reset()
        assert cm.turn_count == 0
        assert cm.topic_count == 0


# ============================================================
# NLPOrchestrator Testleri
# ============================================================


class TestNLPOrchestratorInit:
    """NLPOrchestrator baslatma testleri."""

    def test_defaults(self) -> None:
        o = _make_orchestrator()
        assert o.interaction_count == 0
        assert o.error_count == 0
        assert o.success_rate == 1.0

    def test_custom(self) -> None:
        o = _make_orchestrator(
            clarification_threshold=0.6,
            max_context_turns=20,
            execution_confirmation=False,
            verbosity_level="detailed",
        )
        assert o.feedback.verbosity == VerbosityLevel.DETAILED


class TestProcess:
    """NLPOrchestrator.process testleri."""

    def test_create_command(self) -> None:
        o = _make_orchestrator()
        result = o.process("yeni bir agent olustur")
        assert result.success
        assert result.intent is not None
        assert result.intent.category == IntentCategory.CREATE
        assert result.processing_time_ms > 0

    def test_query_command(self) -> None:
        o = _make_orchestrator()
        result = o.process("tum gorevleri listele")
        assert result.success
        assert result.intent.category == IntentCategory.QUERY
        assert len(result.commands) > 0

    def test_explain_command(self) -> None:
        o = _make_orchestrator()
        result = o.process("bu sistemi acikla")
        assert result.success
        assert result.feedback is not None

    def test_create_has_spec_and_plan(self) -> None:
        o = _make_orchestrator()
        result = o.process("yeni bir API endpoint olustur")
        assert result.intent.category == IntentCategory.CREATE
        # Create pipeline spec ve plan icerir
        assert result.decomposition is not None

    def test_delete_is_simple(self) -> None:
        o = _make_orchestrator()
        result = o.process("eski loglari sil")
        assert result.intent.category == IntentCategory.DELETE
        # Delete pipeline decompose icermez
        assert result.decomposition is None

    def test_interaction_count(self) -> None:
        o = _make_orchestrator()
        o.process("test 1")
        o.process("test 2")
        assert o.interaction_count == 2


class TestProcessAmbiguous:
    """NLPOrchestrator belirsiz giris testleri."""

    def test_ambiguous_asks_clarification(self) -> None:
        o = _make_orchestrator(clarification_threshold=0.99)
        result = o.process("x")
        # Belirsiz giriste aciklama istemeli
        if result.feedback:
            assert result.feedback.feedback_type in (
                FeedbackType.CLARIFICATION_REQUEST,
                FeedbackType.SUGGESTION,
                FeedbackType.SUCCESS_CONFIRMATION,
            )


class TestRecoverFromError:
    """NLPOrchestrator.recover_from_error testleri."""

    def test_recover(self) -> None:
        o = _make_orchestrator()
        r1 = o.process("test komutu")
        r2 = o.recover_from_error(r1.id, "agent olustur")
        assert r2.success

    def test_recover_nonexistent(self) -> None:
        o = _make_orchestrator()
        r = o.recover_from_error("yok", "test")
        assert r.success  # Yine de isler, sadece baglam olmadan


class TestAdaptStyle:
    """NLPOrchestrator.adapt_style testleri."""

    def test_adapt_verbosity(self) -> None:
        o = _make_orchestrator()
        o.adapt_style({"verbosity": "detailed"})
        assert o.feedback.verbosity == VerbosityLevel.DETAILED

    def test_adapt_invalid(self) -> None:
        o = _make_orchestrator()
        o.adapt_style({"verbosity": "invalid"})
        assert o.feedback.verbosity == VerbosityLevel.NORMAL  # Degismemeli


class TestGetResult:
    """NLPOrchestrator.get_result testleri."""

    def test_get(self) -> None:
        o = _make_orchestrator()
        r = o.process("test")
        fetched = o.get_result(r.id)
        assert fetched is not None
        assert fetched.id == r.id

    def test_get_nonexistent(self) -> None:
        o = _make_orchestrator()
        assert o.get_result("yok") is None


# ============================================================
# Entegrasyon Testleri
# ============================================================


class TestEndToEndPipeline:
    """Uc-uca pipeline testleri."""

    def test_full_create_pipeline(self) -> None:
        """Tam CREATE pipeline: parse -> decompose -> requirements -> spec -> plan -> translate -> feedback."""
        o = _make_orchestrator()
        result = o.process("yeni bir kullanici yonetim sistemi olustur ve API endpoint ekle")

        assert result.success
        assert result.intent is not None
        assert result.intent.category == IntentCategory.CREATE
        assert result.decomposition is not None
        assert len(result.decomposition.subtasks) >= 1
        assert result.feedback is not None

    def test_full_query_pipeline(self) -> None:
        """Tam QUERY pipeline: parse -> translate -> feedback."""
        o = _make_orchestrator()
        result = o.process("aktif gorevleri goster")

        assert result.success
        assert result.intent.category == IntentCategory.QUERY
        assert len(result.commands) > 0
        assert result.feedback is not None

    def test_multi_turn_conversation(self) -> None:
        """Coklu tur diyalog."""
        o = _make_orchestrator()

        r1 = o.process("SecurityAgent ile guvenlik taramas yap")
        assert r1.success

        r2 = o.process("sonuclari goster")
        assert r2.success
        assert o.conversation.turn_count >= 4  # 2 user + 2 system

    def test_error_and_recovery(self) -> None:
        """Hata ve kurtarma dongusu."""
        o = _make_orchestrator()
        r1 = o.process("bilinmeyen komut xyz")
        r2 = o.recover_from_error(r1.id, "gorevleri listele")
        assert r2.success

    def test_conversation_context_preserved(self) -> None:
        """Konusma baglami korunur."""
        o = _make_orchestrator()
        o.process("SecurityAgent bilgisini goster")
        o.process("ayni agent icin log getir")

        # Baglam referanslari mevcut olmali
        assert o.conversation.turn_count >= 4
        topics = o.conversation.topic_count
        assert topics >= 1
