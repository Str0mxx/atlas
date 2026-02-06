"""Google Ads marketing agent modulu.

Google Ads API uzerinden kampanya performansini izler:
- Kampanya performans analizi (CPC, CPA, ROAS, CTR)
- Anahtar kelime performans takibi
- Dusuk performansli kampanya/kelime tespiti
- Butce optimizasyon onerileri
- Reklam reddi tespiti ve bildirim
- Haftalik/gunluk rapor olusturma

Sonuclari risk/aciliyet olarak siniflandirir ve karar matrisine iletir.
"""

import logging
from typing import Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
from app.models.marketing import (
    AdCheckType,
    AdDisapproval,
    BudgetRecommendation,
    CampaignMetrics,
    KeywordMetrics,
    MarketingAnalysisResult,
    MarketingConfig,
    PerformanceLevel,
)

logger = logging.getLogger("atlas.agent.marketing")

# Mikro birim -> TRY donusumu (Google Ads API 1_000_000 mikro = 1 birim)
_MICRO = 1_000_000


class MarketingAgent(BaseAgent):
    """Google Ads marketing izleme agent'i.

    Google Ads API uzerinden kampanya performansini analiz eder,
    dusuk performansli kampanya/kelimeleri tespit eder,
    butce onerileri sunar ve karar matrisine entegre eder.

    Attributes:
        config: Marketing yapilandirmasi.
        ads_client: Google Ads API istemcisi.
    """

    def __init__(
        self,
        config: MarketingConfig | None = None,
    ) -> None:
        """MarketingAgent'i baslatir.

        Args:
            config: Marketing yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="marketing")
        self.config = config or MarketingConfig()
        self._ads_client: GoogleAdsClient | None = None

    def _get_ads_client(self) -> GoogleAdsClient:
        """Google Ads API istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis GoogleAdsClient.

        Raises:
            ValueError: API kimlik bilgileri eksikse.
        """
        if self._ads_client is not None:
            return self._ads_client

        developer_token = settings.google_ads_developer_token.get_secret_value()
        client_id = settings.google_ads_client_id
        client_secret = settings.google_ads_client_secret.get_secret_value()
        refresh_token = settings.google_ads_refresh_token.get_secret_value()

        if not developer_token:
            raise ValueError("Google Ads developer token yapilandirilmamis.")

        self._ads_client = GoogleAdsClient.load_from_dict({
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True,
        })
        return self._ads_client

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Marketing analizini calistirir.

        Args:
            task: Gorev detaylari. Opsiyonel anahtarlar:
                - customer_id: Google Ads musteri ID (tiresiz).
                - config: Ozel marketing yapilandirmasi (dict).
                - checks: Calistirilacak kontrol tipleri (str listesi).
                - date_range_days: Analiz suresi (gun).

        Returns:
            Kampanya performans sonuclarini iceren TaskResult.
        """
        # Task'tan yapilandirma al
        if task.get("config"):
            self.config = MarketingConfig(**task["config"])
        if task.get("checks"):
            self.config.checks = [AdCheckType(c) for c in task["checks"]]
        if task.get("date_range_days"):
            self.config.date_range_days = task["date_range_days"]

        customer_id = (
            task.get("customer_id")
            or self.config.customer_id
            or settings.google_ads_customer_id
        )
        if not customer_id:
            return TaskResult(
                success=False,
                message="Google Ads musteri ID yapilandirilmamis.",
                errors=["customer_id bos."],
            )
        # Tireleri temizle
        customer_id = customer_id.replace("-", "")

        self.logger.info(
            "Marketing analizi baslatiliyor (musteri=%s, gun=%d)...",
            customer_id,
            self.config.date_range_days,
        )

        analysis_result = MarketingAnalysisResult()
        errors: list[str] = []

        try:
            client = self._get_ads_client()
            ga_service = client.get_service("GoogleAdsService")

            # 1. Kampanya performansi
            if AdCheckType.CAMPAIGN_PERFORMANCE in self.config.checks:
                self.logger.info("Kampanya performans analizi...")
                await self._analyze_campaigns(
                    ga_service, customer_id, analysis_result,
                )

            # 2. Anahtar kelime performansi
            if AdCheckType.KEYWORD_PERFORMANCE in self.config.checks:
                self.logger.info("Anahtar kelime performans analizi...")
                await self._analyze_keywords(
                    ga_service, customer_id, analysis_result,
                )

            # 3. Reklam reddi kontrolu
            if AdCheckType.AD_DISAPPROVALS in self.config.checks:
                self.logger.info("Reklam reddi kontrolu...")
                await self._check_disapprovals(
                    ga_service, customer_id, analysis_result,
                )

            # 4. Butce analizi
            if AdCheckType.BUDGET_ANALYSIS in self.config.checks:
                self.logger.info("Butce analizi...")
                self._generate_budget_recommendations(analysis_result)

            # Genel performans seviyesini hesapla
            analysis_result.performance_level = self._calculate_overall_performance(
                analysis_result,
            )
            analysis_result.summary = self._build_summary(analysis_result)

        except GoogleAdsException as exc:
            self.logger.error("Google Ads API hatasi: %s", exc)
            errors.append(f"Google Ads API: {exc.failure.errors[0].message}")
        except Exception as exc:
            self.logger.error("Marketing analiz hatasi: %s", exc)
            errors.append(str(exc))

        # Karar matrisi icin analiz
        analysis = await self.analyze({"result": analysis_result.model_dump()})

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "analysis_result": analysis_result.model_dump(),
                "analysis": analysis,
            },
            message=analysis_result.summary or "Marketing analizi tamamlandi.",
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Marketing Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analiz sonuclarini degerlendirir ve risk/aciliyet belirler.

        Args:
            data: {"result": MarketingAnalysisResult dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, performance_level,
            summary, issues.
        """
        result_dict = data.get("result", {})
        result = (
            MarketingAnalysisResult(**result_dict)
            if isinstance(result_dict, dict)
            else result_dict
        )

        issues: list[str] = []

        # Reddedilen reklamlar -> acil bildirim
        if result.disapprovals:
            for d in result.disapprovals:
                issues.append(
                    f"Reklam REDDEDILDI: {d.headline} ({d.policy_topic})"
                )

        # Dusuk performansli kampanyalar
        for c in result.poor_campaigns:
            issues.append(
                f"Dusuk performans: {c.campaign_name} "
                f"(ROAS={c.roas:.2f}, CTR={c.ctr:.2f}%, CPA={c.cpa:.1f}TRY)"
            )

        # Dusuk performansli anahtar kelimeler
        for k in result.poor_keywords:
            issues.append(
                f"Dusuk kelime: '{k.keyword_text}' "
                f"(QS={k.quality_score}, CTR={k.ctr:.2f}%)"
            )

        # Butce onerileri
        for b in result.budget_recommendations:
            issues.append(
                f"Butce onerisi: {b.campaign_name} "
                f"({b.current_budget:.0f} -> {b.recommended_budget:.0f} TRY: {b.reason})"
            )

        # Risk ve aciliyet eslestirmesi
        risk, urgency = self._map_to_risk_urgency(result)
        action = self._determine_action(risk, urgency)

        return {
            "performance_level": result.performance_level.value,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": result.summary,
            "issues": issues,
            "stats": {
                "total_spend": result.total_spend,
                "total_conversions": result.total_conversions,
                "overall_roas": result.overall_roas,
                "overall_ctr": result.overall_ctr,
                "poor_campaign_count": len(result.poor_campaigns),
                "poor_keyword_count": len(result.poor_keywords),
                "disapproval_count": len(result.disapprovals),
                "recommendation_count": len(result.budget_recommendations),
            },
        }

    async def report(self, result: TaskResult) -> str:
        """Marketing sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        stats = analysis.get("stats", {})
        issues = analysis.get("issues", [])

        lines = [
            "=== GOOGLE ADS PERFORMANS RAPORU ===",
            f"Performans: {analysis.get('performance_level', 'bilinmiyor').upper()}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
            "--- Ozet Metrikler ---",
            f"  Toplam harcama: {stats.get('total_spend', 0):.2f} TRY",
            f"  Toplam donusum: {stats.get('total_conversions', 0):.1f}",
            f"  Genel ROAS: {stats.get('overall_roas', 0):.2f}",
            f"  Genel CTR: {stats.get('overall_ctr', 0):.2f}%",
            "",
            "--- Bulgular ---",
            f"  Dusuk performansli kampanya: {stats.get('poor_campaign_count', 0)}",
            f"  Dusuk performansli kelime: {stats.get('poor_keyword_count', 0)}",
            f"  Reddedilen reklam: {stats.get('disapproval_count', 0)}",
            f"  Butce onerisi: {stats.get('recommendation_count', 0)}",
            "",
        ]

        if issues:
            lines.append("--- Detaylar ---")
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Dahili metodlar ===

    async def _analyze_campaigns(
        self,
        ga_service: Any,
        customer_id: str,
        result: MarketingAnalysisResult,
    ) -> None:
        """Kampanya performans metriklerini ceker ve analiz eder.

        Args:
            ga_service: Google Ads query servisi.
            customer_id: Musteri ID (tiresiz).
            result: Sonuclarin yazilacagi MarketingAnalysisResult.
        """
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
            f"WHERE segments.date DURING LAST_{self.config.date_range_days}_DAYS "
            "  AND campaign.status != 'REMOVED' "
            "ORDER BY metrics.cost_micros DESC"
        )

        try:
            response = ga_service.search(
                customer_id=customer_id, query=query,
            )
        except GoogleAdsException:
            raise

        total_cost = 0
        total_conversions = 0.0
        total_conv_value = 0.0
        total_impressions = 0
        total_clicks = 0

        for row in response:
            campaign = row.campaign
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

            cm = CampaignMetrics(
                campaign_id=str(campaign.id),
                campaign_name=campaign.name,
                status=campaign.status.name,
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
            )
            result.campaigns.append(cm)

            if perf in (PerformanceLevel.POOR, PerformanceLevel.CRITICAL):
                result.poor_campaigns.append(cm)

            total_cost += cost_try
            total_conversions += conversions
            total_conv_value += conv_value
            total_impressions += metrics.impressions
            total_clicks += metrics.clicks

        result.total_spend = total_cost
        result.total_conversions = total_conversions
        result.total_conversion_value = total_conv_value
        result.overall_roas = (
            total_conv_value / total_cost if total_cost > 0 else 0.0
        )
        result.overall_ctr = (
            (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
        )

    async def _analyze_keywords(
        self,
        ga_service: Any,
        customer_id: str,
        result: MarketingAnalysisResult,
    ) -> None:
        """Anahtar kelime performansini ceker ve analiz eder.

        Args:
            ga_service: Google Ads query servisi.
            customer_id: Musteri ID (tiresiz).
            result: Sonuclarin yazilacagi MarketingAnalysisResult.
        """
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
            f"WHERE segments.date DURING LAST_{self.config.date_range_days}_DAYS "
            "  AND ad_group_criterion.status != 'REMOVED' "
            "ORDER BY metrics.cost_micros DESC "
            "LIMIT 200"
        )

        try:
            response = ga_service.search(
                customer_id=customer_id, query=query,
            )
        except GoogleAdsException:
            raise

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

            perf = self._evaluate_keyword_performance(
                quality_score=quality_score,
                ctr=ctr,
                cpc=cpc,
                conversions=metrics.conversions or 0.0,
                cost=cost_try,
            )

            km = KeywordMetrics(
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
                performance_level=perf,
            )

            if perf in (PerformanceLevel.POOR, PerformanceLevel.CRITICAL):
                result.poor_keywords.append(km)

    async def _check_disapprovals(
        self,
        ga_service: Any,
        customer_id: str,
        result: MarketingAnalysisResult,
    ) -> None:
        """Reddedilen veya kisitlanan reklamlari kontrol eder.

        Args:
            ga_service: Google Ads query servisi.
            customer_id: Musteri ID (tiresiz).
            result: Sonuclarin yazilacagi MarketingAnalysisResult.
        """
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

        try:
            response = ga_service.search(
                customer_id=customer_id, query=query,
            )
        except GoogleAdsException:
            raise

        for row in response:
            ad = row.ad_group_ad.ad
            policy = row.ad_group_ad.policy_summary

            # Basliklari birlestir
            headlines = []
            if hasattr(ad, "responsive_search_ad") and ad.responsive_search_ad:
                for h in ad.responsive_search_ad.headlines:
                    headlines.append(h.text)
            headline_text = " | ".join(headlines[:3]) if headlines else str(ad.id)

            # Politika konularini ayristir
            topics = []
            evidences = []
            for entry in policy.policy_topic_entries:
                topics.append(entry.topic)
                for ev in entry.evidences:
                    if hasattr(ev, "text_list") and ev.text_list:
                        for t in ev.text_list.texts:
                            evidences.append(t)

            result.disapprovals.append(
                AdDisapproval(
                    ad_id=str(ad.id),
                    ad_group_name=row.ad_group.name,
                    campaign_name=row.campaign.name,
                    headline=headline_text,
                    policy_topic=", ".join(topics) if topics else "bilinmiyor",
                    policy_type=policy.approval_status.name,
                    evidence=evidences,
                )
            )

    def _generate_budget_recommendations(
        self, result: MarketingAnalysisResult,
    ) -> None:
        """Kampanya verilerine dayanarak butce onerileri uretir.

        Args:
            result: Kampanya verileri iceren MarketingAnalysisResult.
        """
        for campaign in result.campaigns:
            if campaign.status != "ENABLED" or campaign.daily_budget == 0:
                continue

            daily_budget_try = campaign.daily_budget / _MICRO
            daily_spend = campaign.cost / _MICRO / max(self.config.date_range_days, 1)

            # Yuksek performansli kampanya butce kisitlamasi varsa -> artir
            if (
                campaign.performance_level in (PerformanceLevel.EXCELLENT, PerformanceLevel.GOOD)
                and campaign.roas >= self.config.roas_min_threshold
                and daily_spend >= daily_budget_try * 0.9
            ):
                result.budget_recommendations.append(
                    BudgetRecommendation(
                        campaign_name=campaign.campaign_name,
                        current_budget=daily_budget_try,
                        recommended_budget=daily_budget_try * 1.2,
                        reason="Yuksek ROAS, butce limiti yaklasiliyor",
                        estimated_impact=f"Tahmini %20 daha fazla donusum (ROAS={campaign.roas:.2f})",
                        priority=2,
                    )
                )

            # Dusuk performansli kampanya -> butceyi azalt
            if campaign.performance_level == PerformanceLevel.CRITICAL:
                result.budget_recommendations.append(
                    BudgetRecommendation(
                        campaign_name=campaign.campaign_name,
                        current_budget=daily_budget_try,
                        recommended_budget=daily_budget_try * 0.5,
                        reason="Kritik dusuk performans, butce israfi",
                        estimated_impact=f"Gunluk {daily_budget_try * 0.5:.0f} TRY tasarruf",
                        priority=1,
                    )
                )
            elif (
                campaign.performance_level == PerformanceLevel.POOR
                and campaign.roas < self.config.roas_min_threshold
            ):
                result.budget_recommendations.append(
                    BudgetRecommendation(
                        campaign_name=campaign.campaign_name,
                        current_budget=daily_budget_try,
                        recommended_budget=daily_budget_try * 0.7,
                        reason=f"Dusuk ROAS ({campaign.roas:.2f}), butce optimizasyonu gerekli",
                        estimated_impact=f"Gunluk {daily_budget_try * 0.3:.0f} TRY tasarruf",
                        priority=2,
                    )
                )

    def _evaluate_campaign_performance(
        self,
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
            Kampanya performans seviyesi.
        """
        score = 0

        # ROAS degerlendirmesi (en onemli)
        if roas >= self.config.roas_min_threshold * 2:
            score += 3
        elif roas >= self.config.roas_min_threshold:
            score += 2
        elif roas >= 1.0:
            score += 1

        # CTR degerlendirmesi
        if ctr >= self.config.ctr_min_threshold * 2:
            score += 2
        elif ctr >= self.config.ctr_min_threshold:
            score += 1

        # CPC degerlendirmesi (dusuk = iyi)
        if cpc <= self.config.cpc_threshold * 0.5:
            score += 1
        elif cpc > self.config.cpc_threshold:
            score -= 1

        # CPA degerlendirmesi (dusuk = iyi)
        if cpa > 0 and cpa <= self.config.cpa_threshold * 0.5:
            score += 1
        elif cpa > self.config.cpa_threshold:
            score -= 1

        if score >= 5:
            return PerformanceLevel.EXCELLENT
        if score >= 3:
            return PerformanceLevel.GOOD
        if score >= 1:
            return PerformanceLevel.AVERAGE
        if score >= -1:
            return PerformanceLevel.POOR
        return PerformanceLevel.CRITICAL

    def _evaluate_keyword_performance(
        self,
        quality_score: int,
        ctr: float,
        cpc: float,
        conversions: float,
        cost: float,
    ) -> PerformanceLevel:
        """Anahtar kelime performans seviyesini hesaplar.

        Args:
            quality_score: Google kalite puani (1-10).
            ctr: Tiklama orani (yuzde).
            cpc: Tiklama maliyeti (TRY).
            conversions: Donusum sayisi.
            cost: Toplam harcama (TRY).

        Returns:
            Kelime performans seviyesi.
        """
        # Dusuk kalite puani -> kotu performans
        if quality_score > 0 and quality_score <= self.config.low_quality_score_threshold:
            if ctr < self.config.ctr_min_threshold:
                return PerformanceLevel.CRITICAL
            return PerformanceLevel.POOR

        # Yuksek harcama, sifir donusum -> kotu
        if cost > self.config.cpa_threshold and conversions == 0:
            return PerformanceLevel.CRITICAL

        # Dusuk CTR -> kotu
        if ctr < self.config.ctr_min_threshold * 0.5:
            return PerformanceLevel.POOR

        if quality_score >= 7 and ctr >= self.config.ctr_min_threshold:
            return PerformanceLevel.GOOD

        return PerformanceLevel.AVERAGE

    def _calculate_overall_performance(
        self, result: MarketingAnalysisResult,
    ) -> PerformanceLevel:
        """Genel performans seviyesini hesaplar.

        Args:
            result: Marketing analiz sonucu.

        Returns:
            Genel performans seviyesi.
        """
        # Reddedilen reklam varsa otomatik olarak dusur
        if result.disapprovals:
            if len(result.disapprovals) >= 3:
                return PerformanceLevel.CRITICAL
            return PerformanceLevel.POOR

        # ROAS bazli
        if result.overall_roas >= self.config.roas_min_threshold * 2:
            base = PerformanceLevel.EXCELLENT
        elif result.overall_roas >= self.config.roas_min_threshold:
            base = PerformanceLevel.GOOD
        elif result.overall_roas >= 1.0:
            base = PerformanceLevel.AVERAGE
        elif result.overall_roas > 0:
            base = PerformanceLevel.POOR
        else:
            base = PerformanceLevel.CRITICAL

        # Dusuk performansli kampanya orani yuksekse dusur
        if result.campaigns:
            poor_ratio = len(result.poor_campaigns) / len(result.campaigns)
            if poor_ratio >= 0.5 and base.value in ("excellent", "good"):
                base = PerformanceLevel.AVERAGE

        return base

    def _build_summary(self, result: MarketingAnalysisResult) -> str:
        """Analiz ozeti olusturur.

        Args:
            result: Marketing analiz sonucu.

        Returns:
            Ozet metni.
        """
        total = len(result.campaigns)
        poor = len(result.poor_campaigns)
        disapprovals = len(result.disapprovals)

        parts = [
            f"{total} kampanya analiz edildi",
            f"ROAS={result.overall_roas:.2f}",
            f"CTR={result.overall_ctr:.2f}%",
            f"harcama={result.total_spend:.0f}TRY",
        ]

        if poor > 0:
            parts.append(f"{poor} dusuk performansli kampanya")
        if disapprovals > 0:
            parts.append(f"{disapprovals} reddedilen reklam!")
        if result.budget_recommendations:
            parts.append(f"{len(result.budget_recommendations)} butce onerisi")

        return " | ".join(parts)

    @staticmethod
    def _map_to_risk_urgency(
        result: MarketingAnalysisResult,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Performans bulgularini RiskLevel ve UrgencyLevel'a esler.

        Karar matrisi entegrasyonu:
        - EXCELLENT/GOOD -> LOW risk, LOW urgency (sadece kaydet)
        - AVERAGE -> LOW risk, MEDIUM urgency (bildir)
        - POOR -> MEDIUM risk, MEDIUM urgency (bildir + oneriler)
        - CRITICAL / reddedilen reklam -> HIGH risk, HIGH urgency (acil)

        Args:
            result: Marketing analiz sonucu.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        perf = result.performance_level

        # Reddedilen reklam -> en yuksek oncelik
        if result.disapprovals:
            if len(result.disapprovals) >= 3:
                return RiskLevel.HIGH, UrgencyLevel.HIGH
            return RiskLevel.HIGH, UrgencyLevel.MEDIUM

        if perf == PerformanceLevel.CRITICAL:
            return RiskLevel.HIGH, UrgencyLevel.HIGH

        if perf == PerformanceLevel.POOR:
            # Butce israfi yuksekse aciliyeti artir
            if result.total_spend > 0 and result.overall_roas < 1.0:
                return RiskLevel.MEDIUM, UrgencyLevel.HIGH
            return RiskLevel.MEDIUM, UrgencyLevel.MEDIUM

        if perf == PerformanceLevel.AVERAGE:
            return RiskLevel.LOW, UrgencyLevel.MEDIUM

        # GOOD veya EXCELLENT
        return RiskLevel.LOW, UrgencyLevel.LOW

    @staticmethod
    def _determine_action(risk: RiskLevel, urgency: UrgencyLevel) -> ActionType:
        """Risk ve aciliyetten aksiyon tipini belirler.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.

        Returns:
            Uygun aksiyon tipi.
        """
        action, _ = DECISION_RULES.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )
        return action
