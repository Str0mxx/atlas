"""GoogleAdsManager unit testleri.

Google Ads API arac sinifi davranislari mock'larla test edilir.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.marketing import (
    AdDisapproval,
    CampaignMetrics,
    KeywordMetrics,
    PerformanceLevel,
)
from app.tools.google_ads import GoogleAdsManager, _MICRO


# === Fixture'lar ===


@pytest.fixture
def mock_settings():
    """Test icin settings mock'u."""
    with patch("app.tools.google_ads.settings") as mock:
        mock.google_ads_developer_token = MagicMock()
        mock.google_ads_developer_token.get_secret_value.return_value = "test-dev-token"
        mock.google_ads_client_id = "test-client-id"
        mock.google_ads_client_secret = MagicMock()
        mock.google_ads_client_secret.get_secret_value.return_value = "test-secret"
        mock.google_ads_refresh_token = MagicMock()
        mock.google_ads_refresh_token.get_secret_value.return_value = "test-refresh"
        mock.google_ads_customer_id = "1234567890"
        yield mock


@pytest.fixture
def manager(mock_settings) -> GoogleAdsManager:
    """Yapilandirilmis GoogleAdsManager."""
    return GoogleAdsManager()


def _make_campaign_row(
    campaign_id: int = 1,
    name: str = "Test Kampanya",
    status_name: str = "ENABLED",
    impressions: int = 1000,
    clicks: int = 50,
    cost_micros: int = 100_000_000,
    conversions: float = 5.0,
    conv_value: float = 500.0,
    avg_cpc: int = 2_000_000,
    ctr: float = 0.05,
    budget_micros: int = 50_000_000,
) -> MagicMock:
    """Test icin kampanya satiri olusturur."""
    row = MagicMock()
    row.campaign.id = campaign_id
    row.campaign.name = name
    row.campaign.status.name = status_name
    row.metrics.impressions = impressions
    row.metrics.clicks = clicks
    row.metrics.cost_micros = cost_micros
    row.metrics.conversions = conversions
    row.metrics.conversions_value = conv_value
    row.metrics.average_cpc = avg_cpc
    row.metrics.ctr = ctr
    row.campaign_budget.amount_micros = budget_micros
    return row


def _make_keyword_row(
    criterion_id: int = 100,
    keyword_text: str = "test keyword",
    match_type_name: str = "EXACT",
    quality_score: int = 7,
    campaign_name: str = "Test Kampanya",
    ad_group_name: str = "Test Grup",
    impressions: int = 500,
    clicks: int = 25,
    cost_micros: int = 50_000_000,
    conversions: float = 2.0,
    avg_cpc: int = 2_000_000,
    ctr: float = 0.05,
) -> MagicMock:
    """Test icin anahtar kelime satiri olusturur."""
    row = MagicMock()
    row.ad_group_criterion.criterion_id = criterion_id
    row.ad_group_criterion.keyword.text = keyword_text
    row.ad_group_criterion.keyword.match_type.name = match_type_name
    row.ad_group_criterion.quality_info.quality_score = quality_score
    row.campaign.name = campaign_name
    row.ad_group.name = ad_group_name
    row.metrics.impressions = impressions
    row.metrics.clicks = clicks
    row.metrics.cost_micros = cost_micros
    row.metrics.conversions = conversions
    row.metrics.average_cpc = avg_cpc
    row.metrics.ctr = ctr
    return row


# === Init testleri ===


class TestGoogleAdsManagerInit:
    """GoogleAdsManager baslatma testleri."""

    def test_init_defaults(self, mock_settings) -> None:
        """Varsayilan yapilandirma."""
        manager = GoogleAdsManager()
        assert manager._client is None
        assert manager.default_customer_id == "1234567890"

    def test_lazy_client(self, mock_settings) -> None:
        """Client lazy baslatilir."""
        manager = GoogleAdsManager()
        assert manager._client is None


# === Client testleri ===


class TestGetClient:
    """Google Ads istemci baslatma testleri."""

    @patch("app.tools.google_ads._GOOGLE_ADS_AVAILABLE", True)
    @patch("app.tools.google_ads.GoogleAdsClient")
    def test_client_created(
        self, mock_client_cls, manager,
    ) -> None:
        """GoogleAdsClient olusturulur."""
        mock_client = MagicMock()
        mock_client_cls.load_from_dict.return_value = mock_client

        result = manager._get_client()

        assert result is mock_client
        mock_client_cls.load_from_dict.assert_called_once()
        call_args = mock_client_cls.load_from_dict.call_args[0][0]
        assert call_args["developer_token"] == "test-dev-token"
        assert call_args["use_proto_plus"] is True

    @patch("app.tools.google_ads._GOOGLE_ADS_AVAILABLE", True)
    @patch("app.tools.google_ads.GoogleAdsClient")
    def test_client_cached(
        self, mock_client_cls, manager,
    ) -> None:
        """Client ikinci cagirimda cache'ten gelir."""
        mock_client_cls.load_from_dict.return_value = MagicMock()

        manager._get_client()
        manager._get_client()

        assert mock_client_cls.load_from_dict.call_count == 1

    @patch("app.tools.google_ads._GOOGLE_ADS_AVAILABLE", False)
    def test_client_not_available(self, manager) -> None:
        """google-ads kurulu degilse RuntimeError."""
        with pytest.raises(RuntimeError, match="google-ads"):
            manager._get_client()

    def test_missing_developer_token(self, mock_settings) -> None:
        """Developer token yoksa ValueError."""
        mock_settings.google_ads_developer_token.get_secret_value.return_value = ""
        manager = GoogleAdsManager()

        with patch("app.tools.google_ads._GOOGLE_ADS_AVAILABLE", True):
            with pytest.raises(ValueError, match="developer token"):
                manager._get_client()


# === Search testleri ===


class TestSearch:
    """GAQL sorgu testleri."""

    def test_search_basic(self, manager) -> None:
        """Temel GAQL sorgusu."""
        mock_service = MagicMock()
        mock_row = MagicMock()
        mock_row.campaign.id = 1
        mock_row.campaign.name = "Test"
        mock_service.search.return_value = [mock_row]

        manager._get_service = MagicMock(return_value=mock_service)

        results = manager.search("SELECT campaign.id FROM campaign")

        assert len(results) == 1
        mock_service.search.assert_called_once_with(
            customer_id="1234567890",
            query="SELECT campaign.id FROM campaign",
        )

    def test_search_custom_customer_id(self, manager) -> None:
        """Ozel musteri ID ile sorgu."""
        mock_service = MagicMock()
        mock_service.search.return_value = []

        manager._get_service = MagicMock(return_value=mock_service)

        manager.search("SELECT campaign.id FROM campaign", customer_id="999-888-7777")

        mock_service.search.assert_called_once_with(
            customer_id="9998887777",
            query="SELECT campaign.id FROM campaign",
        )

    def test_search_empty_results(self, manager) -> None:
        """Sonucsuz sorgu."""
        mock_service = MagicMock()
        mock_service.search.return_value = []

        manager._get_service = MagicMock(return_value=mock_service)

        results = manager.search("SELECT campaign.id FROM campaign")
        assert results == []


# === GetCampaigns testleri ===


class TestGetCampaigns:
    """Kampanya metrikleri testleri."""

    def test_get_campaigns_success(self, manager) -> None:
        """Basarili kampanya metrikleri getirme."""
        rows = [
            _make_campaign_row(
                campaign_id=1, name="Kampanya A",
                cost_micros=100 * _MICRO, conversions=10.0,
                conv_value=1000.0, ctr=0.03,
            ),
            _make_campaign_row(
                campaign_id=2, name="Kampanya B",
                cost_micros=50 * _MICRO, conversions=2.0,
                conv_value=100.0, ctr=0.005,
            ),
        ]

        mock_service = MagicMock()
        mock_service.search.return_value = rows
        manager._get_service = MagicMock(return_value=mock_service)

        campaigns = manager.get_campaigns(date_range_days=14)

        assert len(campaigns) == 2
        assert isinstance(campaigns[0], CampaignMetrics)
        assert campaigns[0].campaign_name == "Kampanya A"
        assert campaigns[0].cost == 100 * _MICRO
        # ROAS = 1000 / 100 = 10.0
        assert campaigns[0].roas == pytest.approx(10.0)
        # CTR = 0.03 * 100 = 3.0%
        assert campaigns[0].ctr == pytest.approx(3.0)

    def test_get_campaigns_empty(self, manager) -> None:
        """Bos kampanya listesi."""
        mock_service = MagicMock()
        mock_service.search.return_value = []
        manager._get_service = MagicMock(return_value=mock_service)

        campaigns = manager.get_campaigns()
        assert campaigns == []

    def test_get_campaigns_micro_conversion(self, manager) -> None:
        """Mikro birim donusumu dogru yapilir."""
        row = _make_campaign_row(
            cost_micros=5_500_000,  # 5.5 TRY
            avg_cpc=1_100_000,  # 1.1 TRY
        )

        mock_service = MagicMock()
        mock_service.search.return_value = [row]
        manager._get_service = MagicMock(return_value=mock_service)

        campaigns = manager.get_campaigns()

        assert campaigns[0].cpc == pytest.approx(1.1)

    def test_get_campaigns_zero_conversions(self, manager) -> None:
        """Sifir donusumde CPA ve ROAS sifir."""
        row = _make_campaign_row(
            conversions=0.0, conv_value=0.0,
        )

        mock_service = MagicMock()
        mock_service.search.return_value = [row]
        manager._get_service = MagicMock(return_value=mock_service)

        campaigns = manager.get_campaigns()

        assert campaigns[0].cpa == 0.0
        assert campaigns[0].roas == 0.0


# === GetKeywords testleri ===


class TestGetKeywords:
    """Anahtar kelime metrikleri testleri."""

    def test_get_keywords_success(self, manager) -> None:
        """Basarili anahtar kelime getirme."""
        rows = [
            _make_keyword_row(
                criterion_id=101, keyword_text="sac ekimi",
                quality_score=8, ctr=0.04,
            ),
        ]

        mock_service = MagicMock()
        mock_service.search.return_value = rows
        manager._get_service = MagicMock(return_value=mock_service)

        keywords = manager.get_keywords(date_range_days=7, limit=100)

        assert len(keywords) == 1
        assert isinstance(keywords[0], KeywordMetrics)
        assert keywords[0].keyword_text == "sac ekimi"
        assert keywords[0].quality_score == 8
        assert keywords[0].ctr == pytest.approx(4.0)

    def test_get_keywords_empty(self, manager) -> None:
        """Bos anahtar kelime listesi."""
        mock_service = MagicMock()
        mock_service.search.return_value = []
        manager._get_service = MagicMock(return_value=mock_service)

        keywords = manager.get_keywords()
        assert keywords == []

    def test_get_keywords_zero_quality_score(self, manager) -> None:
        """Kalite skoru 0 olan kelime."""
        row = _make_keyword_row(quality_score=0)
        row.ad_group_criterion.quality_info.quality_score = 0

        mock_service = MagicMock()
        mock_service.search.return_value = [row]
        manager._get_service = MagicMock(return_value=mock_service)

        keywords = manager.get_keywords()
        assert keywords[0].quality_score == 0


# === GetDisapprovals testleri ===


class TestGetDisapprovals:
    """Reddedilen reklam testleri."""

    def test_get_disapprovals_success(self, manager) -> None:
        """Basarili reddedilen reklam getirme."""
        row = MagicMock()
        row.ad_group_ad.ad.id = 999
        headline_mock = MagicMock()
        headline_mock.text = "Test Headline"
        row.ad_group_ad.ad.responsive_search_ad.headlines = [headline_mock]
        row.ad_group_ad.policy_summary.approval_status.name = "DISAPPROVED"

        topic_entry = MagicMock()
        topic_entry.topic = "healthcare"
        topic_entry.evidences = []
        row.ad_group_ad.policy_summary.policy_topic_entries = [topic_entry]

        row.ad_group.name = "Test Grup"
        row.campaign.name = "Test Kampanya"

        mock_service = MagicMock()
        mock_service.search.return_value = [row]
        manager._get_service = MagicMock(return_value=mock_service)

        disapprovals = manager.get_disapprovals()

        assert len(disapprovals) == 1
        assert isinstance(disapprovals[0], AdDisapproval)
        assert disapprovals[0].ad_id == "999"
        assert disapprovals[0].headline == "Test Headline"
        assert disapprovals[0].policy_topic == "healthcare"
        assert disapprovals[0].policy_type == "DISAPPROVED"

    def test_get_disapprovals_empty(self, manager) -> None:
        """Reddedilen reklam yok."""
        mock_service = MagicMock()
        mock_service.search.return_value = []
        manager._get_service = MagicMock(return_value=mock_service)

        disapprovals = manager.get_disapprovals()
        assert disapprovals == []


# === GetAccountSummary testleri ===


class TestGetAccountSummary:
    """Hesap ozet metrikleri testleri."""

    def test_account_summary(self, manager) -> None:
        """Basarili hesap ozeti."""
        rows = [
            _make_campaign_row(
                cost_micros=100 * _MICRO,
                conversions=10.0,
                conv_value=1000.0,
                impressions=2000,
                clicks=100,
            ),
            _make_campaign_row(
                cost_micros=50 * _MICRO,
                conversions=5.0,
                conv_value=500.0,
                impressions=1000,
                clicks=50,
            ),
        ]

        mock_service = MagicMock()
        mock_service.search.return_value = rows
        manager._get_service = MagicMock(return_value=mock_service)

        summary = manager.get_account_summary()

        assert summary["total_spend"] == pytest.approx(150.0)
        assert summary["total_conversions"] == pytest.approx(15.0)
        assert summary["total_conversion_value"] == pytest.approx(1500.0)
        assert summary["overall_roas"] == pytest.approx(10.0)
        # CTR = (100+50) / (2000+1000) * 100 = 5.0%
        assert summary["overall_ctr"] == pytest.approx(5.0)
        assert summary["campaign_count"] == 2

    def test_account_summary_empty(self, manager) -> None:
        """Bos hesap ozeti."""
        mock_service = MagicMock()
        mock_service.search.return_value = []
        manager._get_service = MagicMock(return_value=mock_service)

        summary = manager.get_account_summary()

        assert summary["total_spend"] == 0.0
        assert summary["campaign_count"] == 0
        assert summary["overall_roas"] == 0.0


# === PerformanceLevel testleri ===


class TestEvaluatePerformance:
    """Performans seviyesi hesaplama testleri."""

    def test_excellent_performance(self) -> None:
        """Mukemmel performans."""
        result = GoogleAdsManager._evaluate_campaign_performance(
            cpc=1.0, cpa=50.0, roas=5.0, ctr=4.0,
        )
        assert result == PerformanceLevel.EXCELLENT

    def test_poor_performance(self) -> None:
        """Dusuk performans."""
        result = GoogleAdsManager._evaluate_campaign_performance(
            cpc=20.0, cpa=500.0, roas=0.5, ctr=0.5,
        )
        assert result in (PerformanceLevel.POOR, PerformanceLevel.CRITICAL)

    def test_average_performance(self) -> None:
        """Ortalama performans."""
        result = GoogleAdsManager._evaluate_campaign_performance(
            cpc=5.0, cpa=150.0, roas=2.5, ctr=1.5,
        )
        assert result in (PerformanceLevel.AVERAGE, PerformanceLevel.GOOD)


# === ResolveCustomerId testleri ===


class TestResolveCustomerId:
    """Musteri ID cozumleme testleri."""

    def test_provided_id(self, manager) -> None:
        """Verilen ID kullanilir."""
        result = manager._resolve_customer_id("999-888-7777")
        assert result == "9998887777"

    def test_default_id(self, manager) -> None:
        """Varsayilan ID kullanilir."""
        result = manager._resolve_customer_id(None)
        assert result == "1234567890"

    def test_no_id_raises(self, mock_settings) -> None:
        """ID yoksa ValueError."""
        mock_settings.google_ads_customer_id = ""
        manager = GoogleAdsManager()

        with pytest.raises(ValueError, match="musteri ID"):
            manager._resolve_customer_id(None)
