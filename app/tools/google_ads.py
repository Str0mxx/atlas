"""ATLAS Google Ads API yonetim modulu.

Google Ads API ile kampanya, anahtar kelime ve reklam
verilerine erisim saglayan yeniden kullanilabilir arac sinifi.

MarketingAgent bu sinifi kullanarak Google Ads islemlerini
gerceklestirebilir. Bagimsiz olarak da kullanilabilir.
"""

import logging
from typing import Any

from app.config import settings
from app.models.marketing import (
    AdDisapproval,
    CampaignMetrics,
    KeywordMetrics,
    PerformanceLevel,
)

logger = logging.getLogger("atlas.tools.google_ads")

# Mikro birim donusumu (1 TRY = 1_000_000 mikro)
_MICRO = 1_000_000

# Google Ads opsiyonel import
_GOOGLE_ADS_AVAILABLE = False
try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    _GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GoogleAdsClient = None  # type: ignore[assignment, misc]
    GoogleAdsException = Exception  # type: ignore[assignment, misc]
    logger.info("google-ads kurulu degil, GoogleAdsManager kullanilamaz")


class GoogleAdsManager:
    """Google Ads API yonetici sinifi.

    Google Ads API ile kampanya, anahtar kelime ve reklam
    verilerine erisim saglar. Lazy initialization ile
    GoogleAdsClient baslatir.

    Kullanim:
        manager = GoogleAdsManager()
        campaigns = manager.get_campaigns("1234567890", date_range_days=7)

    Attributes:
        default_customer_id: Varsayilan musteri ID (settings'ten).
    """

    def __init__(self) -> None:
        """GoogleAdsManager'i baslatir. Client lazy yuklenir."""
        self._client: Any | None = None
        self.default_customer_id: str = settings.google_ads_customer_id

    def _get_client(self) -> Any:
        """Google Ads API istemcisini dondurur (lazy init).

        OAuth2 credentials ile GoogleAdsClient olusturur.

        Returns:
            Yapilandirilmis GoogleAdsClient.

        Raises:
            RuntimeError: google-ads kutuphanesi kurulu degilse.
            ValueError: Developer token yapilandirilmamissa.
        """
        if self._client is not None:
            return self._client

        if not _GOOGLE_ADS_AVAILABLE:
            raise RuntimeError(
                "google-ads kutuphanesi kurulu degil. "
                "Kurmak icin: pip install google-ads"
            )

        developer_token = settings.google_ads_developer_token.get_secret_value()
        if not developer_token:
            raise ValueError("Google Ads developer token yapilandirilmamis.")

        client_id = settings.google_ads_client_id
        client_secret = settings.google_ads_client_secret.get_secret_value()
        refresh_token = settings.google_ads_refresh_token.get_secret_value()

        self._client = GoogleAdsClient.load_from_dict({
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True,
        })
        logger.info("Google Ads istemcisi baslatildi")
        return self._client

    def _get_service(self) -> Any:
        """GoogleAdsService nesnesini dondurur.

        Returns:
            GoogleAdsService nesnesi.
        """
        client = self._get_client()
        return client.get_service("GoogleAdsService")

    def _resolve_customer_id(self, customer_id: str | None) -> str:
        """Musteri ID'sini cozumler.

        Args:
            customer_id: Verilen musteri ID veya None.

        Returns:
            Tiresiz musteri ID.

        Raises:
            ValueError: Musteri ID bulunamazsa.
        """
        cid = customer_id or self.default_customer_id
        if not cid:
            raise ValueError("Google Ads musteri ID yapilandirilmamis.")
        return cid.replace("-", "")

    def search(
        self,
        query: str,
        customer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """GAQL sorgusu calistirir.

        Args:
            query: Google Ads Query Language sorgusu.
            customer_id: Musteri ID (None ise varsayilan).

        Returns:
            Sorgu sonuclari dict listesi.
        """
        cid = self._resolve_customer_id(customer_id)
        service = self._get_service()

        response = service.search(customer_id=cid, query=query)

        results: list[dict[str, Any]] = []
        for row in response:
            results.append(self._row_to_dict(row))

        logger.info(
            "GAQL sorgusu tamamlandi: customer=%s, sonuc=%d",
            cid, len(results),
        )
        return results

    def get_campaigns(
        self,
        customer_id: str | None = None,
        date_range_days: int = 7,
    ) -> list[CampaignMetrics]:
        """Kampanya performans metriklerini getirir.

        Args:
            customer_id: Musteri ID (None ise varsayilan).
            date_range_days: Analiz icin geri bakilacak gun sayisi.

        Returns:
            Kampanya metrikleri listesi.
        """
        cid = self._resolve_customer_id(customer_id)
        service = self._get_service()

        query = (
            "SELECT "
            "  campaign.id, "
            "  campaign.name, "
            "  campaign.status, "
            "  campaign_budget.amount_micros, "
            "  metrics.impressions, "
            "  metrics.clicks, "
            "  metrics.cost_micros, "
            "  metrics.conversions, "
            "  metrics.conversions_value, "
            "  metrics.average_cpc, "
            "  metrics.ctr "
            "FROM campaign "
            f"WHERE segments.date DURING LAST_{date_range_days}_DAYS "
            "  AND campaign.status != 'REMOVED' "
            "ORDER BY metrics.cost_micros DESC"
        )

        response = service.search(customer_id=cid, query=query)

        campaigns: list[CampaignMetrics] = []
        for row in response:
            metrics = row.metrics
            budget = row.campaign_budget

            cost_try = metrics.cost_micros / _MICRO
            cpc = metrics.average_cpc / _MICRO if metrics.average_cpc else 0.0
            ctr = metrics.ctr * 100 if metrics.ctr else 0.0
            conversions = metrics.conversions or 0.0
            conv_value = metrics.conversions_value or 0.0
            cpa = cost_try / conversions if conversions > 0 else 0.0
            roas = conv_value / cost_try if cost_try > 0 else 0.0

            perf = self._evaluate_campaign_performance(
                cpc=cpc, cpa=cpa, roas=roas, ctr=ctr,
            )

            campaigns.append(CampaignMetrics(
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                status=row.campaign.status.name,
                impressions=metrics.impressions,
                clicks=metrics.clicks,
                cost=metrics.cost_micros,
                conversions=conversions,
                conversion_value=conv_value,
                cpc=cpc,
                cpa=cpa,
                ctr=ctr,
                roas=roas,
                daily_budget=budget.amount_micros if budget.amount_micros else 0,
                performance_level=perf,
            ))

        logger.info(
            "Kampanya metrikleri getirildi: customer=%s, kampanya=%d",
            cid, len(campaigns),
        )
        return campaigns

    def get_keywords(
        self,
        customer_id: str | None = None,
        date_range_days: int = 7,
        limit: int = 200,
    ) -> list[KeywordMetrics]:
        """Anahtar kelime performans metriklerini getirir.

        Args:
            customer_id: Musteri ID (None ise varsayilan).
            date_range_days: Analiz icin geri bakilacak gun sayisi.
            limit: Maksimum sonuc sayisi.

        Returns:
            Anahtar kelime metrikleri listesi.
        """
        cid = self._resolve_customer_id(customer_id)
        service = self._get_service()

        query = (
            "SELECT "
            "  ad_group_criterion.criterion_id, "
            "  ad_group_criterion.keyword.text, "
            "  ad_group_criterion.keyword.match_type, "
            "  ad_group_criterion.quality_info.quality_score, "
            "  campaign.name, "
            "  ad_group.name, "
            "  metrics.impressions, "
            "  metrics.clicks, "
            "  metrics.cost_micros, "
            "  metrics.conversions, "
            "  metrics.average_cpc, "
            "  metrics.ctr "
            "FROM keyword_view "
            f"WHERE segments.date DURING LAST_{date_range_days}_DAYS "
            "  AND ad_group_criterion.status != 'REMOVED' "
            "ORDER BY metrics.cost_micros DESC "
            f"LIMIT {limit}"
        )

        response = service.search(customer_id=cid, query=query)

        keywords: list[KeywordMetrics] = []
        for row in response:
            criterion = row.ad_group_criterion
            metrics = row.metrics
            quality_score = (
                criterion.quality_info.quality_score
                if criterion.quality_info.quality_score
                else 0
            )

            cost_try = metrics.cost_micros / _MICRO
            cpc = metrics.average_cpc / _MICRO if metrics.average_cpc else 0.0
            ctr = metrics.ctr * 100 if metrics.ctr else 0.0

            keywords.append(KeywordMetrics(
                keyword_id=str(criterion.criterion_id),
                keyword_text=criterion.keyword.text,
                match_type=criterion.keyword.match_type.name,
                campaign_name=row.campaign.name,
                ad_group_name=row.ad_group.name,
                impressions=metrics.impressions,
                clicks=metrics.clicks,
                cost=metrics.cost_micros,
                conversions=metrics.conversions or 0.0,
                cpc=cpc,
                ctr=ctr,
                quality_score=quality_score,
            ))

        logger.info(
            "Anahtar kelime metrikleri getirildi: customer=%s, kelime=%d",
            cid, len(keywords),
        )
        return keywords

    def get_disapprovals(
        self,
        customer_id: str | None = None,
    ) -> list[AdDisapproval]:
        """Reddedilen veya kisitlanan reklamlari getirir.

        Args:
            customer_id: Musteri ID (None ise varsayilan).

        Returns:
            Reddedilen reklam bilgileri listesi.
        """
        cid = self._resolve_customer_id(customer_id)
        service = self._get_service()

        query = (
            "SELECT "
            "  ad_group_ad.ad.id, "
            "  ad_group_ad.ad.responsive_search_ad.headlines, "
            "  ad_group_ad.policy_summary.approval_status, "
            "  ad_group_ad.policy_summary.policy_topic_entries, "
            "  ad_group.name, "
            "  campaign.name "
            "FROM ad_group_ad "
            "WHERE ad_group_ad.policy_summary.approval_status IN "
            "  ('DISAPPROVED', 'AREA_OF_INTEREST_ONLY', 'APPROVED_LIMITED') "
            "  AND ad_group_ad.status != 'REMOVED'"
        )

        response = service.search(customer_id=cid, query=query)

        disapprovals: list[AdDisapproval] = []
        for row in response:
            ad = row.ad_group_ad.ad
            policy = row.ad_group_ad.policy_summary

            # Baslik cikar
            headline = ""
            if hasattr(ad, "responsive_search_ad") and ad.responsive_search_ad:
                headlines = ad.responsive_search_ad.headlines
                if headlines:
                    headline = headlines[0].text if hasattr(headlines[0], "text") else str(headlines[0])

            # Politika konulari
            topics: list[str] = []
            evidence: list[str] = []
            for entry in policy.policy_topic_entries or []:
                if hasattr(entry, "topic"):
                    topics.append(entry.topic)
                if hasattr(entry, "evidences"):
                    for ev in entry.evidences or []:
                        evidence.append(str(ev))

            disapprovals.append(AdDisapproval(
                ad_id=str(ad.id),
                ad_group_name=row.ad_group.name,
                campaign_name=row.campaign.name,
                headline=headline,
                policy_topic=", ".join(topics) if topics else "bilinmiyor",
                policy_type=policy.approval_status.name if hasattr(policy.approval_status, "name") else str(policy.approval_status),
                evidence=evidence,
            ))

        logger.info(
            "Reddedilen reklamlar getirildi: customer=%s, red=%d",
            cid, len(disapprovals),
        )
        return disapprovals

    def get_account_summary(
        self,
        customer_id: str | None = None,
        date_range_days: int = 7,
    ) -> dict[str, Any]:
        """Hesap genel ozet metriklerini getirir.

        Args:
            customer_id: Musteri ID (None ise varsayilan).
            date_range_days: Analiz icin geri bakilacak gun sayisi.

        Returns:
            Ozet metrikler sozlugu: total_spend, total_conversions,
            total_conversion_value, overall_roas, overall_ctr,
            campaign_count.
        """
        campaigns = self.get_campaigns(customer_id, date_range_days)

        total_cost = 0.0
        total_conversions = 0.0
        total_conv_value = 0.0
        total_impressions = 0
        total_clicks = 0

        for c in campaigns:
            total_cost += c.cost / _MICRO
            total_conversions += c.conversions
            total_conv_value += c.conversion_value
            total_impressions += c.impressions
            total_clicks += c.clicks

        overall_roas = total_conv_value / total_cost if total_cost > 0 else 0.0
        overall_ctr = (
            (total_clicks / total_impressions * 100)
            if total_impressions > 0
            else 0.0
        )

        return {
            "total_spend": total_cost,
            "total_conversions": total_conversions,
            "total_conversion_value": total_conv_value,
            "overall_roas": overall_roas,
            "overall_ctr": overall_ctr,
            "campaign_count": len(campaigns),
        }

    # === Yardimci metodlar ===

    @staticmethod
    def _evaluate_campaign_performance(
        cpc: float,
        cpa: float,
        roas: float,
        ctr: float,
    ) -> PerformanceLevel:
        """Kampanya performans seviyesini hesaplar.

        Args:
            cpc: Ortalama tiklama maliyeti (TRY).
            cpa: Donusum basina maliyet (TRY).
            roas: Reklam harcamasi getirisi.
            ctr: Tiklama orani (yuzde).

        Returns:
            Hesaplanan performans seviyesi.
        """
        score = 0

        if roas >= 4.0:
            score += 2
        elif roas >= 2.0:
            score += 1
        elif roas < 1.0:
            score -= 2

        if ctr >= 3.0:
            score += 1
        elif ctr < 1.0:
            score -= 1

        if cpa <= 100.0:
            score += 1
        elif cpa >= 300.0:
            score -= 1

        if score >= 3:
            return PerformanceLevel.EXCELLENT
        if score >= 1:
            return PerformanceLevel.GOOD
        if score >= 0:
            return PerformanceLevel.AVERAGE
        if score >= -2:
            return PerformanceLevel.POOR
        return PerformanceLevel.CRITICAL

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        """Google Ads API satirini sozluge donusturur.

        Args:
            row: Google Ads SearchGoogleAdsResponse satiri.

        Returns:
            Satir verisi sozluk olarak.
        """
        result: dict[str, Any] = {}

        for field_name in ("campaign", "ad_group", "ad_group_ad",
                           "ad_group_criterion", "metrics",
                           "campaign_budget", "segments"):
            obj = getattr(row, field_name, None)
            if obj is not None:
                try:
                    # proto-plus nesneleri icin
                    if hasattr(obj, "__iter__") and not isinstance(obj, str):
                        result[field_name] = str(obj)
                    else:
                        result[field_name] = str(obj)
                except Exception:
                    result[field_name] = repr(obj)

        return result
