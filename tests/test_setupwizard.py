"""
Interactive Setup Wizard sistem testleri.

CLIWizard, APIKeyValidator, ChannelConfigurator,
WizardModelSelector, FirstRunTest, DependencyChecker,
EnvFileGenerator ve modeller icin kapsamli testler.
"""

import os
import tempfile
import pytest

from app.core.setupwizard.cli_wizard import CLIWizard
from app.core.setupwizard.api_key_validator import APIKeyValidator
from app.core.setupwizard.channel_configurator import ChannelConfigurator
from app.core.setupwizard.model_selector import WizardModelSelector
from app.core.setupwizard.first_run_test import FirstRunTest
from app.core.setupwizard.dependency_checker import DependencyChecker
from app.core.setupwizard.env_file_generator import EnvFileGenerator
from app.models.setupwizard_models import (
    WizardStep,
    ValidationRule,
    ChannelType,
    ModelProvider,
    TestStatus,
    DependencyStatus,
    StepInfo,
    WizardProgress,
    ValidationResult,
    APIKeyCheckResult,
    ChannelConfig,
    ModelInfo,
    ModelRecommendation,
    CostComparison,
    TestResult,
    AllTestsResult,
    DependencyCheckResult,
    AllDepsResult,
    EnvVariable,
    EnvFileResult,
    EnvValidationResult,
    WizardSummary,
    SetupWizardConfig,
)


# ── CLIWizard Testleri ────────────────────────────────────────────────────────


class TestCLIWizard:
    """CLIWizard testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.wizard = CLIWizard(interactive=False)

    def test_init(self):
        """Baslatma testi."""
        assert self.wizard.step_count == 0
        assert self.wizard.current_step == 0
        assert not self.wizard.is_completed

    def test_init_with_title(self):
        """Baslikli baslatma."""
        w = CLIWizard(title="Test Wizard")
        assert w._title == "Test Wizard"

    def test_add_step(self):
        """Adim ekleme."""
        r = self.wizard.add_step(
            name="step1", title="Adim 1", description="Ilk adim"
        )
        assert r["added"] is True
        assert r["name"] == "step1"
        assert r["index"] == 0
        assert self.wizard.step_count == 1

    def test_add_multiple_steps(self):
        """Coklu adim ekleme."""
        for i in range(3):
            self.wizard.add_step(name=f"step{i}")
        assert self.wizard.step_count == 3

    def test_add_step_optional(self):
        """Opsiyonel adim ekleme."""
        r = self.wizard.add_step(name="opt", required=False)
        assert r["added"] is True

    def test_next_step(self):
        """Sonraki adim."""
        self.wizard.add_step(name="s1")
        self.wizard.add_step(name="s2")
        r = self.wizard.next_step()
        assert r["advanced"] is True
        assert r["index"] == 1

    def test_next_step_at_end(self):
        """Son adimda sonraki."""
        self.wizard.add_step(name="s1")
        r = self.wizard.next_step()
        assert r["advanced"] is False
        assert "error" in r

    def test_next_step_no_steps(self):
        """Adim yokken sonraki."""
        r = self.wizard.next_step()
        assert r["advanced"] is False

    def test_prev_step(self):
        """Onceki adim."""
        self.wizard.add_step(name="s1")
        self.wizard.add_step(name="s2")
        self.wizard.next_step()
        r = self.wizard.prev_step()
        assert r["back"] is True
        assert r["index"] == 0

    def test_prev_step_at_start(self):
        """Ilk adimda onceki."""
        self.wizard.add_step(name="s1")
        r = self.wizard.prev_step()
        assert r["back"] is False
        assert "error" in r

    def test_skip_step_optional(self):
        """Opsiyonel adim atlama."""
        self.wizard.add_step(name="opt", required=False)
        self.wizard.add_step(name="s2")
        r = self.wizard.skip_step()
        assert r["skipped"] is True

    def test_skip_step_required(self):
        """Zorunlu adim atlama."""
        self.wizard.add_step(name="req", required=True)
        r = self.wizard.skip_step()
        assert r["skipped"] is False
        assert "zorunlu" in r["error"]

    def test_skip_step_no_steps(self):
        """Adim yokken atlama."""
        r = self.wizard.skip_step()
        assert r["skipped"] is False

    def test_prompt(self):
        """Soru sorma."""
        r = self.wizard.prompt(
            question="Adi nedir?",
            default="Atlas",
            key="name",
        )
        assert r["prompted"] is True
        assert r["value"] == "Atlas"
        assert r["key"] == "name"

    def test_prompt_with_choices(self):
        """Secenekli soru."""
        r = self.wizard.prompt(
            question="Seciniz?",
            choices=["a", "b", "c"],
            key="choice",
        )
        assert r["prompted"] is True
        assert r["value"] in ["a", "b", "c"]

    def test_prompt_saves_answer(self):
        """Cevap kaydetme."""
        self.wizard.prompt(question="?", default="val", key="k")
        assert self.wizard.get_answer("k") == "val"

    def test_validate_input_not_empty(self):
        """Bos olmayan dogrulama."""
        r = self.wizard.validate_input(value="test", rule="not_empty")
        assert r["valid"] is True

    def test_validate_input_empty_fails(self):
        """Bos deger basarisiz."""
        r = self.wizard.validate_input(value="", rule="not_empty")
        assert r["valid"] is False

    def test_validate_input_positive_int(self):
        """Pozitif integer dogrulama."""
        r = self.wizard.validate_input(value=5, rule="positive_int")
        assert r["valid"] is True

    def test_validate_input_negative_int_fails(self):
        """Negatif integer basarisiz."""
        r = self.wizard.validate_input(value=-1, rule="positive_int")
        assert r["valid"] is False

    def test_validate_input_email(self):
        """Email dogrulama."""
        r = self.wizard.validate_input(
            value="test@example.com", rule="email"
        )
        assert r["valid"] is True

    def test_validate_input_invalid_email(self):
        """Gecersiz email."""
        r = self.wizard.validate_input(
            value="notanemail", rule="email"
        )
        assert r["valid"] is False

    def test_validate_input_custom_validator(self):
        """Ozel dogrulayici."""
        r = self.wizard.validate_input(
            value=10,
            validator=lambda x: x > 5,
            rule="gt_5",
        )
        assert r["valid"] is True

    def test_validate_none_value_default_rule(self):
        """Varsayilan kural None deger."""
        r = self.wizard.validate_input(value=None, rule="other")
        assert r["valid"] is False

    def test_display_progress(self):
        """Ilerleme gosterimi."""
        self.wizard.add_step(name="s1")
        self.wizard.add_step(name="s2")
        r = self.wizard.display_progress()
        assert r["displayed"] is True
        assert r["total"] == 2
        assert "percent" in r

    def test_display_summary(self):
        """Ozet gosterimi."""
        self.wizard.set_answer("k", "v")
        r = self.wizard.display_summary()
        assert r["displayed"] is True
        assert r["items"] == 1

    def test_display_summary_custom_data(self):
        """Ozel veri ile ozet."""
        r = self.wizard.display_summary(data={"a": 1, "b": 2})
        assert r["displayed"] is True
        assert r["items"] == 2

    def test_complete(self):
        """Sihirbazi tamamlama."""
        self.wizard.add_step(name="s1")
        r = self.wizard.complete()
        assert r["completed"] is True
        assert self.wizard.is_completed

    def test_complete_no_steps(self):
        """Adim yokken tamamlama."""
        r = self.wizard.complete()
        assert r["completed"] is True

    def test_reset(self):
        """Sifirlama."""
        self.wizard.add_step(name="s1")
        self.wizard.set_answer("k", "v")
        self.wizard.complete()
        r = self.wizard.reset()
        assert r["reset"] is True
        assert not self.wizard.is_completed
        assert self.wizard.get_answer("k") is None

    def test_set_answer(self):
        """Cevap ayarlama."""
        r = self.wizard.set_answer(key="x", value=42)
        assert r["set"] is True
        assert self.wizard.get_answer("x") == 42

    def test_get_answer_missing(self):
        """Olmayan cevap."""
        assert self.wizard.get_answer("nonexistent") is None

    def test_get_summary(self):
        """Ozet bilgi."""
        self.wizard.add_step(name="s1")
        r = self.wizard.get_summary()
        assert r["retrieved"] is True
        assert r["step_count"] == 1
        assert "stats" in r

    def test_stats_incremented(self):
        """Istatistik artimi."""
        self.wizard.add_step(name="s1")
        self.wizard.prompt(question="?", key="k")
        self.wizard.validate_input(value="x", rule="not_empty")
        assert self.wizard._stats["prompts_shown"] == 1
        assert self.wizard._stats["validations_run"] == 1


# ── APIKeyValidator Testleri ──────────────────────────────────────────────────


class TestAPIKeyValidator:
    """APIKeyValidator testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.validator = APIKeyValidator()

    def test_init(self):
        """Baslatma testi."""
        assert len(self.validator._results) == 0
        assert self.validator._stats["validations_run"] == 0

    def test_validate_format_anthropic_valid(self):
        """Anthropic format dogrulama."""
        key = "sk-ant-abcdefghijklmnopqrst12345"
        r = self.validator.validate_format(key, "anthropic")
        assert r["valid"] is True
        assert r["provider"] == "anthropic"

    def test_validate_format_empty(self):
        """Bos anahtar."""
        r = self.validator.validate_format("", "anthropic")
        assert r["valid"] is False
        assert r["format"] == "empty"

    def test_validate_format_generic_valid(self):
        """Generic format dogrulama."""
        r = self.validator.validate_format("validkey123", "generic")
        assert r["valid"] is True

    def test_validate_format_generic_short_fails(self):
        """Kisa generic anahtar basarisiz."""
        r = self.validator.validate_format("abc", "generic")
        assert r["valid"] is False

    def test_validate_format_unknown_provider_uses_generic(self):
        """Bilinmeyen saglayici generic kullanir."""
        r = self.validator.validate_format("validkey123", "unknown")
        assert "format" in r

    def test_validate_format_openai(self):
        """OpenAI format dogrulama."""
        key = "sk-" + "a" * 32
        r = self.validator.validate_format(key, "openai")
        assert r["valid"] is True

    def test_validate_format_slack(self):
        """Slack format dogrulama."""
        key = "xoxb-test-key"
        r = self.validator.validate_format(key, "slack")
        assert r["valid"] is True

    def test_validate_provider_supported(self):
        """Desteklenen saglayici."""
        key = "validkey123456"
        r = self.validator.validate_provider(key, "generic")
        assert "valid" in r
        assert r["supported"] is True

    def test_validate_provider_unsupported(self):
        """Desteklenmeyen saglayici."""
        r = self.validator.validate_provider("key", "xyz_unknown")
        assert r["valid"] is False
        assert "desteklenmeyen" in r.get("error", "")

    def test_validate_provider_empty_key(self):
        """Bos anahtar saglayici dogrulama."""
        r = self.validator.validate_provider("", "generic")
        assert r["valid"] is False

    def test_test_permission_with_key(self):
        """Izin testi."""
        key = "validkey123456"
        r = self.validator.test_permission(key, "generic", "read")
        assert "passed" in r
        assert r["permission"] == "read"

    def test_test_permission_empty_key(self):
        """Bos anahtar izin testi."""
        r = self.validator.test_permission("", "generic", "read")
        assert r["passed"] is False

    def test_check_quota(self):
        """Kota kontrolu."""
        r = self.validator.check_quota("validkey", "anthropic")
        assert r["checked"] is True
        assert r["quota_remaining"] == 100000

    def test_check_quota_openai(self):
        """OpenAI kota kontrolu."""
        r = self.validator.check_quota("validkey", "openai")
        assert r["quota_remaining"] == 90000

    def test_check_quota_empty_key(self):
        """Bos anahtar kota."""
        r = self.validator.check_quota("", "generic")
        assert r["checked"] is False

    def test_validate_all_valid_key(self):
        """Toplu dogrulama gecerli anahtar."""
        key = "validkey123456"
        r = self.validator.validate_all(key, "generic")
        assert "valid" in r
        assert "checks" in r
        assert r["total_checks"] == 4

    def test_validate_all_empty_key(self):
        """Toplu dogrulama bos anahtar."""
        r = self.validator.validate_all("", "generic")
        assert r["valid"] is False

    def test_validate_all_increments_stats(self):
        """Istatistik artimi."""
        self.validator.validate_all("key123", "generic")
        assert self.validator._stats["validations_run"] == 1

    def test_validate_all_saves_result(self):
        """Sonuc kaydedilir."""
        self.validator.validate_all("key123456", "generic")
        assert len(self.validator._results) == 1

    def test_get_supported_providers(self):
        """Desteklenen saglayicilar."""
        providers = self.validator.get_supported_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "generic" in providers

    def test_mask_key_normal(self):
        """Anahtar maskeleme."""
        masked = self.validator.mask_key("sk-ant-12345678")
        assert "****" in masked
        assert masked.startswith("sk-a")

    def test_mask_key_short(self):
        """Kisa anahtar maskeleme."""
        assert self.validator.mask_key("ab") == "***"

    def test_mask_key_empty(self):
        """Bos anahtar maskeleme."""
        assert self.validator.mask_key("") == "***"

    def test_get_summary(self):
        """Ozet bilgi."""
        r = self.validator.get_summary()
        assert r["retrieved"] is True
        assert r["supported_providers"] > 0


# ── ChannelConfigurator Testleri ──────────────────────────────────────────────


class TestChannelConfigurator:
    """ChannelConfigurator testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.conf = ChannelConfigurator()

    def test_init(self):
        """Baslatma testi."""
        assert self.conf.channel_count == 0
        assert len(self.conf.SUPPORTED_CHANNELS) == 5

    def test_setup_telegram(self):
        """Telegram kurulum."""
        r = self.conf.setup_telegram(
            token="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ12345"
        )
        assert r["configured"] is True
        assert r["channel"] == "telegram"

    def test_setup_telegram_no_token(self):
        """Telegram token olmadan basarisiz."""
        r = self.conf.setup_telegram(token="")
        assert r["configured"] is False
        assert "token" in r["error"]

    def test_setup_telegram_with_webhook(self):
        """Telegram webhook ile."""
        r = self.conf.setup_telegram(
            token="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ12345",
            webhook_url="https://example.com/webhook",
        )
        assert r["has_webhook"] is True

    def test_setup_whatsapp(self):
        """WhatsApp kurulum."""
        r = self.conf.setup_whatsapp(
            phone="+905551234567", api_key="validapikey"
        )
        assert r["configured"] is True

    def test_setup_whatsapp_missing_fields(self):
        """WhatsApp eksik alanlar."""
        r = self.conf.setup_whatsapp(phone="", api_key="")
        assert r["configured"] is False

    def test_setup_discord(self):
        """Discord kurulum."""
        r = self.conf.setup_discord(
            token="discordtoken123", guild_id="123456"
        )
        assert r["configured"] is True
        assert r["guild_id"] == "123456"

    def test_setup_discord_no_token(self):
        """Discord token olmadan basarisiz."""
        r = self.conf.setup_discord(token="")
        assert r["configured"] is False

    def test_setup_slack(self):
        """Slack kurulum."""
        r = self.conf.setup_slack(
            token="xoxb-test", workspace="myworkspace"
        )
        assert r["configured"] is True
        assert r["workspace"] == "myworkspace"

    def test_setup_slack_no_token(self):
        """Slack token olmadan basarisiz."""
        r = self.conf.setup_slack(token="")
        assert r["configured"] is False

    def test_setup_webchat(self):
        """WebChat kurulum."""
        r = self.conf.setup_webchat(host="0.0.0.0", port=8080)
        assert r["configured"] is True
        assert r["port"] == 8080

    def test_setup_webchat_invalid_port(self):
        """Gecersiz port basarisiz."""
        r = self.conf.setup_webchat(port=0)
        assert r["configured"] is False

    def test_setup_webchat_large_port_fails(self):
        """Cok buyuk port basarisiz."""
        r = self.conf.setup_webchat(port=70000)
        assert r["configured"] is False

    def test_get_channel(self):
        """Kanal getirme."""
        self.conf.setup_telegram(token="token123456789abc")
        r = self.conf.get_channel("telegram")
        assert r["found"] is True

    def test_get_channel_missing(self):
        """Olmayan kanal."""
        r = self.conf.get_channel("telegram")
        assert r["found"] is False

    def test_enable_channel(self):
        """Kanal etkinlestirme."""
        self.conf.setup_telegram(token="token123456789abc")
        self.conf.disable_channel("telegram")
        r = self.conf.enable_channel("telegram")
        assert r["enabled"] is True

    def test_enable_channel_missing(self):
        """Olmayan kanal etkinlestirme."""
        r = self.conf.enable_channel("nonexistent")
        assert r["enabled"] is False

    def test_disable_channel(self):
        """Kanal devre disi birakma."""
        self.conf.setup_telegram(token="token123456789abc")
        r = self.conf.disable_channel("telegram")
        assert r["disabled"] is True

    def test_disable_channel_missing(self):
        """Olmayan kanal devre disi."""
        r = self.conf.disable_channel("nonexistent")
        assert r["disabled"] is False

    def test_get_channels_all(self):
        """Tum kanallar."""
        self.conf.setup_telegram(token="tok1")
        self.conf.setup_webchat()
        channels = self.conf.get_channels()
        assert len(channels) == 2

    def test_get_channels_only_enabled(self):
        """Sadece aktif kanallar."""
        self.conf.setup_telegram(token="tok1")
        self.conf.setup_webchat()
        self.conf.disable_channel("webchat")
        channels = self.conf.get_channels(only_enabled=True)
        assert len(channels) == 1

    def test_validate_channel_telegram(self):
        """Telegram dogrulama."""
        self.conf.setup_telegram(token="mytoken123")
        r = self.conf.validate_channel("telegram")
        assert r["valid"] is True
        assert r["channel"] == "telegram"

    def test_validate_channel_missing(self):
        """Olmayan kanal dogrulama."""
        r = self.conf.validate_channel("telegram")
        assert r["valid"] is False

    def test_channel_count(self):
        """Kanal sayisi."""
        self.conf.setup_telegram(token="tok1")
        self.conf.setup_webchat()
        assert self.conf.channel_count == 2

    def test_get_summary(self):
        """Ozet bilgi."""
        self.conf.setup_telegram(token="tok1")
        r = self.conf.get_summary()
        assert r["retrieved"] is True
        assert r["channel_count"] == 1
        assert len(r["supported_channels"]) == 5


# ── WizardModelSelector Testleri ──────────────────────────────────────────────


class TestWizardModelSelector:
    """WizardModelSelector testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.selector = WizardModelSelector()

    def test_init(self):
        """Baslatma testi."""
        assert self.selector.model_count == 5
        assert self.selector._selected is None

    def test_list_models(self):
        """Model listeleme."""
        models = self.selector.list_models()
        assert len(models) == 5

    def test_list_models_by_provider(self):
        """Saglayiciya gore listeleme."""
        models = self.selector.list_models(provider="anthropic")
        assert len(models) == 3

    def test_list_models_openai_provider(self):
        """OpenAI saglayici."""
        models = self.selector.list_models(provider="openai")
        assert len(models) == 1
        assert models[0]["model_id"] == "gpt-4o"

    def test_list_models_unknown_provider(self):
        """Bilinmeyen saglayici."""
        models = self.selector.list_models(provider="xyz")
        assert len(models) == 0

    def test_get_capabilities_valid(self):
        """Gecerli model yetenekleri."""
        r = self.selector.get_capabilities("claude-opus-4-6")
        assert r["found"] is True
        assert len(r["capabilities"]) > 0
        assert r["context_window"] == 200000

    def test_get_capabilities_invalid(self):
        """Gecersiz model."""
        r = self.selector.get_capabilities("nonexistent-model")
        assert r["found"] is False

    def test_get_capabilities_empty(self):
        """Bos model id."""
        r = self.selector.get_capabilities("")
        assert r["found"] is False

    def test_compare_costs_all(self):
        """Tum model maliyet karsilastirma."""
        r = self.selector.compare_costs()
        assert r["compared"] is True
        assert r["count"] == 5
        assert r["cheapest"] is not None

    def test_compare_costs_specific(self):
        """Belirli model karsilastirma."""
        r = self.selector.compare_costs(
            ["claude-opus-4-6", "claude-sonnet-4-6"]
        )
        assert r["compared"] is True
        assert r["count"] == 2

    def test_compare_costs_sorted(self):
        """Maliyete gore sirali."""
        r = self.selector.compare_costs()
        models = r["models"]
        costs = [m["total_cost_1k"] for m in models]
        assert costs == sorted(costs)

    def test_compare_costs_cheapest_is_haiku(self):
        """En ucuz model Haiku."""
        r = self.selector.compare_costs()
        assert r["cheapest"] == "claude-haiku-4-5-20251001"

    def test_get_recommendation_complex(self):
        """Karmasik kullanim onerisi."""
        r = self.selector.get_recommendation("complex")
        assert r["recommended"] == "claude-opus-4-6"

    def test_get_recommendation_general(self):
        """Genel kullanim onerisi."""
        r = self.selector.get_recommendation("general")
        assert r["recommended"] == "claude-sonnet-4-6"

    def test_get_recommendation_simple(self):
        """Basit kullanim onerisi."""
        r = self.selector.get_recommendation("simple")
        assert r["recommended"] == "claude-haiku-4-5-20251001"

    def test_get_recommendation_long_context(self):
        """Uzun baglam onerisi."""
        r = self.selector.get_recommendation("long_context")
        assert r["recommended"] == "gemini-1.5-pro"

    def test_get_recommendation_unknown_use_case(self):
        """Bilinmeyen kullanim durumu varsayilan."""
        r = self.selector.get_recommendation("unknown_use_case")
        assert r["recommended"] == "claude-sonnet-4-6"

    def test_select_model_valid(self):
        """Gecerli model secimi."""
        r = self.selector.select_model("claude-opus-4-6")
        assert r["selected"] is True
        assert r["model_id"] == "claude-opus-4-6"
        assert r["provider"] == "anthropic"

    def test_select_model_invalid(self):
        """Gecersiz model secimi."""
        r = self.selector.select_model("nonexistent-model")
        assert r["selected"] is False
        assert "error" in r

    def test_get_selected_after_select(self):
        """Secili model sonrasi."""
        self.selector.select_model("claude-sonnet-4-6")
        r = self.selector.get_selected()
        assert r["found"] is True
        assert r["model_id"] == "claude-sonnet-4-6"

    def test_get_selected_before_select(self):
        """Secim oncesi secili model."""
        r = self.selector.get_selected()
        assert r["found"] is False

    def test_add_model(self):
        """Ozel model ekleme."""
        r = self.selector.add_model({
            "model_id": "custom-model",
            "name": "Custom",
            "provider": "custom",
        })
        assert r["added"] is True
        assert self.selector.model_count == 6

    def test_add_model_no_info(self):
        """Bilgisiz model ekleme basarisiz."""
        r = self.selector.add_model(None)
        assert r["added"] is False

    def test_add_model_no_id(self):
        """ID siz model ekleme basarisiz."""
        r = self.selector.add_model({"name": "test"})
        assert r["added"] is False

    def test_get_summary(self):
        """Ozet bilgi."""
        r = self.selector.get_summary()
        assert r["retrieved"] is True
        assert r["model_count"] == 5
        assert len(r["providers"]) > 0


# ── FirstRunTest Testleri ─────────────────────────────────────────────────────


class TestFirstRunTest:
    """FirstRunTest testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.runner = FirstRunTest()

    def test_init(self):
        """Baslatma testi."""
        assert self.runner.test_count == 0
        assert self.runner.pass_rate == 0.0

    def test_test_connectivity(self):
        """Baglanti testi."""
        r = self.runner.test_connectivity()
        assert r["passed"] is True
        assert r["test"] == "connectivity"
        assert "latency_ms" in r

    def test_test_connectivity_custom_host(self):
        """Ozel host baglanti testi."""
        r = self.runner.test_connectivity(host="1.1.1.1")
        assert r["test"] == "connectivity"

    def test_test_llm_no_key(self):
        """LLM testi anahtar olmadan."""
        r = self.runner.test_llm(api_key="")
        assert r["passed"] is False
        assert r.get("skipped") is True

    def test_test_llm_with_key(self):
        """LLM testi anahtar ile."""
        r = self.runner.test_llm(
            api_key="sk-ant-test123456789", provider="anthropic"
        )
        assert "passed" in r
        assert r["test"] == "llm"

    def test_test_llm_short_key_fails(self):
        """Kisa anahtar LLM testi basarisiz."""
        r = self.runner.test_llm(api_key="abc")
        assert r["passed"] is False

    def test_test_channel_no_config(self):
        """Kanal testi konfig olmadan."""
        r = self.runner.test_channel("telegram")
        assert r.get("skipped") is True

    def test_test_channel_with_config(self):
        """Kanal testi konfig ile."""
        r = self.runner.test_channel(
            "telegram", config={"token": "testtoken"}
        )
        assert r["passed"] is True

    def test_test_database_no_url(self):
        """Veritabani testi URL olmadan."""
        r = self.runner.test_database(db_url="")
        assert r.get("skipped") is True

    def test_test_database_postgresql_url(self):
        """PostgreSQL URL testi."""
        r = self.runner.test_database(
            db_url="postgresql://user:pass@localhost/db"
        )
        assert r["passed"] is True

    def test_test_database_sqlite_url(self):
        """SQLite URL testi."""
        r = self.runner.test_database(
            db_url="sqlite:///test.db"
        )
        assert r["passed"] is True

    def test_test_database_invalid_url(self):
        """Gecersiz URL testi."""
        r = self.runner.test_database(db_url="invalid-url")
        assert r["passed"] is False

    def test_test_system(self):
        """Sistem testi."""
        r = self.runner.test_system()
        assert "python_version" in r
        assert "platform" in r

    def test_test_system_python_ok(self):
        """Python versiyonu kontrolu."""
        import sys
        r = self.runner.test_system()
        expected = sys.version_info >= (3, 11)
        assert r["python_ok"] == expected

    def test_run_all_minimal(self):
        """Minimal toplu test."""
        r = self.runner.run_all()
        assert r["completed"] is True
        assert r["total"] >= 2

    def test_run_all_with_db(self):
        """Veritabani ile toplu test."""
        r = self.runner.run_all(
            config={"db_url": "postgresql://u:p@h/db"}
        )
        assert r["completed"] is True

    def test_run_all_success_field(self):
        """Basari alani."""
        r = self.runner.run_all()
        assert "success" in r

    def test_get_result_existing(self):
        """Mevcut test sonucu."""
        self.runner.test_connectivity()
        r = self.runner.get_result("connectivity")
        assert r["found"] is True

    def test_get_result_missing(self):
        """Olmayan test sonucu."""
        r = self.runner.get_result("nonexistent")
        assert r["found"] is False

    def test_pass_rate_after_test(self):
        """Gecme orani hesaplama."""
        self.runner.test_connectivity()
        assert self.runner.pass_rate > 0

    def test_get_summary(self):
        """Ozet bilgi."""
        r = self.runner.get_summary()
        assert r["retrieved"] is True
        assert "categories" in r
        assert "pass_rate" in r


# ── DependencyChecker Testleri ────────────────────────────────────────────────


class TestDependencyChecker:
    """DependencyChecker testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.checker = DependencyChecker()

    def test_init(self):
        """Baslatma testi."""
        assert self.checker.check_count == 0
        assert len(self.checker.REQUIRED_PACKAGES) > 0

    def test_check_python_version_current(self):
        """Mevcut Python versiyonu."""
        r = self.checker.check_python_version((3, 11))
        assert "passed" in r
        assert "current" in r
        assert r["check"] == "python_version"

    def test_check_python_version_future_fails(self):
        """Gelecek versiyon basarisiz."""
        r = self.checker.check_python_version((99, 0))
        assert r["passed"] is False

    def test_check_package_stdlib(self):
        """Standart kutuphane paketi."""
        r = self.checker.check_package("os", required=True)
        assert r["installed"] is True
        assert r["passed"] is True

    def test_check_package_missing_optional(self):
        """Eksik opsiyonel paket."""
        r = self.checker.check_package(
            "nonexistent_package_xyz", required=False
        )
        assert r["passed"] is True  # Opsiyonel, eksik olsa da gecerli

    def test_check_package_missing_required(self):
        """Eksik zorunlu paket basarisiz."""
        r = self.checker.check_package(
            "nonexistent_package_xyz", required=True
        )
        assert r["passed"] is False

    def test_check_package_empty_name(self):
        """Bos paket adi."""
        r = self.checker.check_package("")
        assert r["passed"] is False

    def test_check_required_packages(self):
        """Zorunlu paketler kontrolu."""
        r = self.checker.check_required_packages()
        assert "passed" in r
        assert "missing" in r
        assert r["total"] == len(self.checker.REQUIRED_PACKAGES)

    def test_check_optional_packages(self):
        """Opsiyonel paketler kontrolu."""
        r = self.checker.check_optional_packages()
        assert r["passed"] is True  # Opsiyonel her zaman gecerli
        assert "installed_count" in r

    def test_check_system_dependency_python(self):
        """Sistem bagimlilik python."""
        r = self.checker.check_system_dependency("python3")
        assert "found" in r

    def test_check_system_dependency_empty(self):
        """Bos sistem bagimlilik."""
        r = self.checker.check_system_dependency("")
        assert r["passed"] is False

    def test_check_system_dependency_nonexistent(self):
        """Mevcut olmayan sistem bagimlilik."""
        r = self.checker.check_system_dependency(
            "nonexistent_tool_xyz_abc"
        )
        assert r["found"] is False

    def test_check_docker(self):
        """Docker kontrolu."""
        r = self.checker.check_docker()
        assert "passed" in r
        assert "docker_found" in r
        assert r["check"] == "docker"

    def test_check_env_file_missing(self):
        """Olmayan env dosyasi."""
        r = self.checker.check_env_file("/nonexistent/.env.xyz")
        assert r["exists"] is False
        assert r["passed"] is False

    def test_check_env_file_existing(self):
        """Mevcut env dosyasi."""
        with tempfile.NamedTemporaryFile(
            suffix=".env", delete=False
        ) as f:
            f.write(b"TEST=value\n")
            tmp_path = f.name
        try:
            r = self.checker.check_env_file(tmp_path)
            assert r["exists"] is True
            assert r["passed"] is True
        finally:
            os.unlink(tmp_path)

    def test_get_recommendations_empty(self):
        """Bos oneri listesi."""
        recs = self.checker.get_recommendations()
        assert isinstance(recs, list)

    def test_run_all(self):
        """Toplu kontrol."""
        r = self.checker.run_all()
        assert r["completed"] is True
        assert r["total"] > 0
        assert "recommendations" in r
        assert "ready" in r

    def test_check_count_after_checks(self):
        """Kontrol sayisi artimi."""
        self.checker.check_python_version()
        self.checker.check_docker()
        assert self.checker.check_count >= 2

    def test_get_summary(self):
        """Ozet bilgi."""
        r = self.checker.get_summary()
        assert r["retrieved"] is True
        assert "stats" in r


# ── EnvFileGenerator Testleri ─────────────────────────────────────────────────


class TestEnvFileGenerator:
    """EnvFileGenerator testleri."""

    def setup_method(self):
        """Her test oncesi hazirlik."""
        self.gen = EnvFileGenerator()

    def test_init(self):
        """Baslatma testi."""
        assert self.gen.variable_count == 0
        assert len(self.gen.REQUIRED_VARS) > 0

    def test_set_variable(self):
        """Degisken ayarlama."""
        r = self.gen.set_variable("KEY", "value")
        assert r["set"] is True
        assert self.gen.variable_count == 1

    def test_set_variable_empty_key(self):
        """Bos anahtar basarisiz."""
        r = self.gen.set_variable("", "value")
        assert r["set"] is False

    def test_set_variables(self):
        """Toplu degisken ayarlama."""
        r = self.gen.set_variables({"A": "1", "B": "2"})
        assert r["set"] is True
        assert r["count"] == 2

    def test_set_variables_empty(self):
        """Bos degisken sozlugu."""
        r = self.gen.set_variables({})
        assert r["set"] is False

    def test_set_variables_none(self):
        """None degisken sozlugu."""
        r = self.gen.set_variables(None)
        assert r["set"] is False

    def test_generate_template(self):
        """Sablon uretimi."""
        r = self.gen.generate_template()
        assert r["generated"] is True
        assert len(r["content"]) > 0
        assert "ANTHROPIC_API_KEY" in r["content"]

    def test_generate_template_with_values(self):
        """Degerli sablon uretimi."""
        self.gen.set_variable("ANTHROPIC_API_KEY", "sk-ant-test")
        r = self.gen.generate_template()
        assert r["generated"] is True
        assert "sk-ant-test" in r["content"]

    def test_backup_existing_no_file(self):
        """Dosya yoksa yedek olusturmaz."""
        r = self.gen.backup_existing("/nonexistent/.env.xyz")
        assert r["backed_up"] is False
        assert r["reason"] == "dosya_bulunamadi"

    def test_backup_existing_with_file(self):
        """Dosya varsa yedekler."""
        with tempfile.NamedTemporaryFile(
            suffix=".env", delete=False
        ) as f:
            f.write(b"ORIGINAL=1\n")
            tmp_path = f.name
        try:
            r = self.gen.backup_existing(tmp_path)
            assert r["backed_up"] is True
            backup_path = r["backup"]
            assert os.path.isfile(backup_path)
            os.unlink(backup_path)
        finally:
            os.unlink(tmp_path)

    def test_write_file(self):
        """Dosya yazma."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            r = self.gen.write_file(env_path, backup=False)
            assert r["written"] is True
            assert os.path.isfile(env_path)

    def test_write_file_creates_content(self):
        """Dosya icerigi yazilir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            self.gen.set_variable("ANTHROPIC_API_KEY", "sk-ant-test")
            self.gen.write_file(env_path, backup=False)
            with open(env_path) as f:
                content = f.read()
            assert "sk-ant-test" in content

    def test_validate_missing_file(self):
        """Olmayan dosya dogrulama."""
        r = self.gen.validate("/nonexistent/.env.xyz")
        assert r["valid"] is False
        assert r["error"] == "dosya_bulunamadi"

    def test_validate_empty_env(self):
        """Bos env dosyasi dogrulama."""
        with tempfile.NamedTemporaryFile(
            suffix=".env", delete=False, mode="w"
        ) as f:
            f.write("# empty\n")
            tmp_path = f.name
        try:
            r = self.gen.validate(tmp_path)
            assert r["valid"] is False
            assert len(r["missing_vars"]) > 0
        finally:
            os.unlink(tmp_path)

    def test_validate_with_required_vars(self):
        """Zorunlu degiskenler ile dogrulama."""
        with tempfile.NamedTemporaryFile(
            suffix=".env", delete=False, mode="w"
        ) as f:
            for var in EnvFileGenerator.REQUIRED_VARS:
                f.write(f"{var}=testvalue\n")
            tmp_path = f.name
        try:
            r = self.gen.validate(tmp_path)
            assert r["valid"] is True
        finally:
            os.unlink(tmp_path)

    def test_load_from_file(self):
        """Dosyadan yukleme."""
        with tempfile.NamedTemporaryFile(
            suffix=".env", delete=False, mode="w"
        ) as f:
            f.write("MY_KEY=my_value\nOTHER=123\n")
            tmp_path = f.name
        try:
            r = self.gen.load_from_file(tmp_path)
            assert r["loaded"] is True
            assert r["variable_count"] == 2
            assert self.gen.get_variable("MY_KEY") == "my_value"
        finally:
            os.unlink(tmp_path)

    def test_load_from_nonexistent_file(self):
        """Olmayan dosyadan yukleme."""
        r = self.gen.load_from_file("/nonexistent/.env.xyz")
        assert r["loaded"] is False

    def test_get_variable_existing(self):
        """Mevcut degisken."""
        self.gen.set_variable("K", "V")
        assert self.gen.get_variable("K") == "V"

    def test_get_variable_missing(self):
        """Olmayan degisken."""
        assert self.gen.get_variable("NONEXISTENT") is None

    def test_get_summary(self):
        """Ozet bilgi."""
        r = self.gen.get_summary()
        assert r["retrieved"] is True
        assert "missing_required" in r
        assert "ready" in r

    def test_get_summary_ready_when_all_set(self):
        """Tum degiskenler ayarlandiginda hazir."""
        for var in EnvFileGenerator.REQUIRED_VARS:
            self.gen.set_variable(var, "testvalue")
        r = self.gen.get_summary()
        assert r["ready"] is True

    def test_stats_incremented(self):
        """Istatistik artimi."""
        self.gen.set_variable("K", "V")
        assert self.gen._stats["variables_set"] == 1

    def test_load_ignores_comments(self):
        """Yorumlar yuklenmez."""
        with tempfile.NamedTemporaryFile(
            suffix=".env", delete=False, mode="w"
        ) as f:
            f.write("# comment\nKEY=value\n")
            tmp_path = f.name
        try:
            r = self.gen.load_from_file(tmp_path)
            assert r["variable_count"] == 1
        finally:
            os.unlink(tmp_path)


# ── Model Testleri ────────────────────────────────────────────────────────────


class TestSetupWizardModels:
    """Pydantic model testleri."""

    def test_wizard_step_enum(self):
        """WizardStep enum."""
        assert WizardStep.PENDING == "pending"
        assert WizardStep.COMPLETED == "completed"
        assert WizardStep.SKIPPED == "skipped"

    def test_validation_rule_enum(self):
        """ValidationRule enum."""
        assert ValidationRule.NOT_EMPTY == "not_empty"
        assert ValidationRule.EMAIL == "email"

    def test_channel_type_enum(self):
        """ChannelType enum."""
        assert ChannelType.TELEGRAM == "telegram"
        assert ChannelType.DISCORD == "discord"

    def test_model_provider_enum(self):
        """ModelProvider enum."""
        assert ModelProvider.ANTHROPIC == "anthropic"
        assert ModelProvider.OPENAI == "openai"

    def test_test_status_enum(self):
        """TestStatus enum."""
        assert TestStatus.PASSED == "passed"
        assert TestStatus.FAILED == "failed"

    def test_dependency_status_enum(self):
        """DependencyStatus enum."""
        assert DependencyStatus.INSTALLED == "installed"
        assert DependencyStatus.MISSING == "missing"

    def test_step_info(self):
        """StepInfo modeli."""
        step = StepInfo(index=0, name="step1", title="Adim 1")
        assert step.status == WizardStep.PENDING
        assert step.required is True

    def test_wizard_progress(self):
        """WizardProgress modeli."""
        p = WizardProgress(current=1, total=5, completed=0, percent=0)
        assert p.current == 1
        assert p.percent == 0

    def test_validation_result(self):
        """ValidationResult modeli."""
        r = ValidationResult(valid=True, value="test", rule="not_empty")
        assert r.valid is True

    def test_api_key_check_result(self):
        """APIKeyCheckResult modeli."""
        r = APIKeyCheckResult(
            valid=True,
            provider="anthropic",
            checks={"format": True, "provider": True},
            passed_count=2,
            total_checks=4,
        )
        assert r.valid is True
        assert r.passed_count == 2

    def test_channel_config(self):
        """ChannelConfig modeli."""
        c = ChannelConfig(channel="telegram")
        assert c.enabled is True
        assert c.status == "configured"

    def test_model_info(self):
        """ModelInfo modeli."""
        m = ModelInfo(
            model_id="claude-opus-4-6",
            name="Claude Opus",
            provider="anthropic",
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            context_window=200000,
        )
        assert m.cost_per_1k_input == 0.015

    def test_model_recommendation(self):
        """ModelRecommendation modeli."""
        r = ModelRecommendation(
            recommended="claude-sonnet-4-6",
            reason="balanced",
            use_case="general",
        )
        assert r.recommended == "claude-sonnet-4-6"

    def test_cost_comparison(self):
        """CostComparison modeli."""
        c = CostComparison(
            compared=True, models=[], cheapest="haiku", count=3
        )
        assert c.compared is True

    def test_test_result(self):
        """TestResult modeli."""
        r = TestResult(passed=True, test="connectivity")
        assert r.passed is True
        assert not r.skipped

    def test_all_tests_result(self):
        """AllTestsResult modeli."""
        r = AllTestsResult(
            completed=True, total=5, passed=4, failed=1, success=False
        )
        assert r.total == 5

    def test_dependency_check_result(self):
        """DependencyCheckResult modeli."""
        r = DependencyCheckResult(
            passed=True, check="package", package="pytest",
            installed=True
        )
        assert r.installed is True

    def test_all_deps_result(self):
        """AllDepsResult modeli."""
        r = AllDepsResult(
            completed=True, total=10, passed=9, failed=1,
            ready=False
        )
        assert r.ready is False

    def test_env_variable(self):
        """EnvVariable modeli."""
        v = EnvVariable(key="MY_KEY", value="secret", required=True)
        assert v.key == "MY_KEY"
        assert not v.masked

    def test_env_file_result(self):
        """EnvFileResult modeli."""
        r = EnvFileResult(
            written=True, path=".env", variable_count=15
        )
        assert r.written is True

    def test_env_validation_result(self):
        """EnvValidationResult modeli."""
        r = EnvValidationResult(
            valid=False, missing_vars=["KEY1"], required_count=5
        )
        assert len(r.missing_vars) == 1

    def test_wizard_summary(self):
        """WizardSummary modeli."""
        s = WizardSummary(
            title="ATLAS Setup",
            step_count=7,
            current_step=3,
            completed_steps=2,
            is_completed=False,
            answers_count=5,
        )
        assert s.step_count == 7

    def test_setup_wizard_config(self):
        """SetupWizardConfig modeli."""
        c = SetupWizardConfig()
        assert c.enabled is True
        assert c.interactive is True
        assert c.auto_test is True
        assert c.backup_existing is True


# ── Config Testleri ───────────────────────────────────────────────────────────


class TestSetupWizardConfig:
    """Config ayar testleri."""

    def test_config_has_setupwizard_settings(self):
        """Config setupwizard ayarlari."""
        from app.config import settings
        assert hasattr(settings, "setupwizard_enabled")
        assert settings.setupwizard_enabled is True

    def test_config_interactive_mode(self):
        """Config interaktif mod."""
        from app.config import settings
        assert hasattr(settings, "interactive_mode")

    def test_config_auto_test(self):
        """Config otomatik test."""
        from app.config import settings
        assert hasattr(settings, "auto_test")

    def test_config_backup_existing(self):
        """Config yedekleme."""
        from app.config import settings
        assert hasattr(settings, "backup_existing")
