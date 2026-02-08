"""Is analizi agent modulu.

Anthropic Claude API ile is analizi yapar:
- Fizibilite analizi (SWOT dahil)
- Finansal analiz (ROI, basabas, maliyet)
- Pazar analizi (buyukluk, trendler, engeller)
- Rakip analizi (guclu/zayif yanlar, pazar payi)
- Performans degerlendirmesi (metrik, hedef, trend)

Sonuclari risk/aciliyet olarak siniflandirir ve karar matrisine iletir.
"""

import json
import logging
import re
from typing import Any

import anthropic

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
from app.models.analysis import (
    AnalysisConfig,
    AnalysisReport,
    AnalysisType,
    CompetitorInfo,
    FeasibilityResult,
    FinancialResult,
    MarketResult,
    PerformanceResult,
)

logger = logging.getLogger("atlas.agent.analysis")

# === LLM prompt sablonlari ===
_SYSTEM_PROMPT = (
    "Sen bir uzman is analisti ve strateji danismanisin. Turkce yanit ver. "
    "Analizlerini JSON formatinda dondur. Sayisal degerleri gercekci tut."
)

_TASK_PROMPTS: dict[AnalysisType, str] = {
    AnalysisType.FEASIBILITY: (
        "Asagidaki is fikri/projesi icin detayli fizibilite analizi yap.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"score": 0-100, '
        '"strengths": ["guclu yon listesi"], '
        '"weaknesses": ["zayif yon listesi"], '
        '"opportunities": ["firsat listesi"], '
        '"threats": ["tehdit listesi"], '
        '"recommendation": "genel oneri metni", '
        '"estimated_timeline": "tahmini sure"}}\n\n'
        "Proje/Fikir:\n{description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    AnalysisType.FINANCIAL: (
        "Asagidaki is icin finansal analiz yap.\n"
        "Yatirim, gelir tahmini, maliyet kalemleri, ROI ve basabas suresini hesapla.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"investment": 0.0, '
        '"revenue_estimate": 0.0, '
        '"costs": {{"kalem_adi": tutar}}, '
        '"roi_estimate": 0.0, '
        '"break_even_months": 0, '
        '"risk_factors": ["risk faktor listesi"], '
        '"currency": "{currency}"}}\n\n'
        "Is detaylari:\n{description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    AnalysisType.MARKET: (
        "Asagidaki sektor/urun icin pazar analizi yap.\n"
        "Pazar buyuklugu, buyume orani, rakipler, hedef kitle, "
        "trendler ve giris engellerini belirle.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"market_size": "pazar buyuklugu aciklamasi", '
        '"growth_rate": 0.0, '
        '"competitors": [{{"name": "rakip", "strengths": ["guclu"], '
        '"weaknesses": ["zayif"], "market_share_estimate": 0.0}}], '
        '"target_audience": "hedef kitle tanimi", '
        '"trends": ["trend listesi"], '
        '"entry_barriers": ["engel listesi"]}}\n\n'
        "Sektor/Urun:\n{description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    AnalysisType.COMPETITOR: (
        "Asagidaki rakipleri detayli analiz et.\n"
        "Her rakibin guclu/zayif yonlerini, pazar payini ve "
        "stratejik konumunu degerlendir.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"competitors": [{{"name": "rakip adi", '
        '"strengths": ["guclu yon"], "weaknesses": ["zayif yon"], '
        '"market_share_estimate": 0.0}}], '
        '"market_size": "pazar buyuklugu", '
        '"trends": ["pazar trendleri"], '
        '"target_audience": "hedef kitle"}}\n\n'
        "Rakipler ve sektor:\n{description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    AnalysisType.PERFORMANCE: (
        "Asagidaki performans verisini analiz et.\n"
        "Mevcut durum, hedef, trend ve iyilestirme onerilerini belirle.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"metric_name": "metrik adi", '
        '"current_value": 0.0, '
        '"target_value": 0.0, '
        '"trend": "up|down|stable", '
        '"gap_percentage": 0.0, '
        '"recommendations": ["iyilestirme onerisi listesi"]}}\n\n'
        "Performans verisi:\n{description}\n\n"
        "Ek bilgi:\n{context}"
    ),
}


class AnalysisAgent(BaseAgent):
    """Is analizi agent'i.

    Anthropic Claude API ile fizibilite, finansal, pazar, rakip
    ve performans analizleri yaparak sonuclari karar matrisine
    entegre eder.

    Attributes:
        config: Analiz yapilandirmasi.
    """

    def __init__(
        self,
        config: AnalysisConfig | None = None,
    ) -> None:
        """AnalysisAgent'i baslatir.

        Args:
            config: Analiz yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="analysis")
        self.config = config or AnalysisConfig()
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        """Anthropic API istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis AsyncAnthropic.

        Raises:
            ValueError: API key eksikse.
        """
        if self._client is not None:
            return self._client

        api_key = settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError("Anthropic API key yapilandirilmamis.")

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Analiz gorevini calistirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - task_type: Analiz tipi (feasibility/financial/market/
                  competitor/performance).
                - description: Analiz edilecek konu aciklamasi.
                - context: Ek baglamsal bilgi (opsiyonel).
                - config: Ozel yapilandirma (dict, opsiyonel).

        Returns:
            Analiz sonuclarini iceren TaskResult.
        """
        if task.get("config"):
            self.config = AnalysisConfig(**task["config"])

        # Gorev tipini belirle
        task_type_str = task.get("task_type", "feasibility")
        try:
            analysis_type = AnalysisType(task_type_str)
        except ValueError:
            return TaskResult(
                success=False,
                message=f"Gecersiz analiz tipi: {task_type_str}",
                errors=[f"Gecerli tipler: {[t.value for t in AnalysisType]}"],
            )

        description = task.get("description", "")
        if not description:
            return TaskResult(
                success=False,
                message="Analiz icin aciklama belirtilmemis.",
                errors=["'description' alani gerekli."],
            )

        context = task.get("context", "")

        self.logger.info(
            "Analiz baslatiliyor: tip=%s, aciklama=%s",
            analysis_type.value,
            description[:100],
        )

        errors: list[str] = []

        # LLM analizi
        try:
            llm_result = await self._run_analysis(
                analysis_type, description, context,
            )
        except Exception as exc:
            self.logger.error("LLM analiz hatasi: %s", exc)
            return TaskResult(
                success=False,
                message=f"Analiz sirasinda hata: {exc}",
                errors=[str(exc)],
            )

        # Sonucu uygun modele donustur
        report_data = self._build_report(analysis_type, llm_result)

        # Karar matrisi icin analiz
        analysis = await self.analyze({
            "analysis_type": analysis_type.value,
            "report": report_data.model_dump(),
        })

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "report": report_data.model_dump(),
                "analysis": analysis,
            },
            message=report_data.summary or "Analiz tamamlandi.",
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Analiz Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analiz sonuclarini degerlendirir ve risk/aciliyet belirler.

        Args:
            data: {"analysis_type": str, "report": AnalysisReport dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary.
        """
        report_dict = data.get("report", {})
        report = (
            AnalysisReport(**report_dict)
            if isinstance(report_dict, dict)
            else report_dict
        )

        risk, urgency = self._map_to_risk_urgency(report)
        action = self._determine_action(risk, urgency)

        return {
            "analysis_type": report.analysis_type,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": report.summary,
            "risk_level": report.risk_level,
            "confidence": report.confidence,
            "recommendations": report.recommendations,
        }

    async def report(self, result: TaskResult) -> str:
        """Analiz sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        report_data = result.data.get("report", {})

        lines = [
            "=== IS ANALIZ RAPORU ===",
            f"Tip: {analysis.get('analysis_type', '-').upper()}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            f"Guven: {analysis.get('confidence', 0):.0%}",
            "",
            f"Baslik: {report_data.get('title', '-')}",
            "",
            report_data.get("summary", ""),
            "",
        ]

        # Tur bazli detaylar
        report_inner = report_data.get("data", {})

        if report_data.get("analysis_type") == "feasibility":
            score = report_inner.get("score", 0)
            lines.append(f"--- Fizibilite Skoru: {score}/100 ---")
            for label, key in [
                ("Guclu", "strengths"), ("Zayif", "weaknesses"),
                ("Firsatlar", "opportunities"), ("Tehditler", "threats"),
            ]:
                items = report_inner.get(key, [])
                if items:
                    lines.append(f"  {label}:")
                    for item in items:
                        lines.append(f"    - {item}")

            if report_inner.get("recommendation"):
                lines.append(f"\n  Oneri: {report_inner['recommendation']}")
            if report_inner.get("estimated_timeline"):
                lines.append(f"  Tahmini sure: {report_inner['estimated_timeline']}")

        elif report_data.get("analysis_type") == "financial":
            currency = report_inner.get("currency", "TRY")
            lines.append("--- Finansal Ozet ---")
            lines.append(f"  Yatirim: {report_inner.get('investment', 0):,.0f} {currency}")
            lines.append(f"  Tahmini gelir: {report_inner.get('revenue_estimate', 0):,.0f} {currency}/ay")
            lines.append(f"  ROI: %{report_inner.get('roi_estimate', 0):.1f}")
            lines.append(f"  Basabas: {report_inner.get('break_even_months', 0)} ay")

            costs = report_inner.get("costs", {})
            if costs:
                lines.append("  Maliyet kalemleri:")
                for item, amount in costs.items():
                    lines.append(f"    - {item}: {amount:,.0f} {currency}")

        elif report_data.get("analysis_type") in ("market", "competitor"):
            lines.append("--- Pazar Bilgisi ---")
            if report_inner.get("market_size"):
                lines.append(f"  Pazar buyuklugu: {report_inner['market_size']}")
            if report_inner.get("growth_rate"):
                lines.append(f"  Buyume orani: %{report_inner['growth_rate']:.1f}")
            competitors = report_inner.get("competitors", [])
            if competitors:
                lines.append(f"  Rakip sayisi: {len(competitors)}")
                for comp in competitors[:5]:
                    name = comp.get("name", "?")
                    share = comp.get("market_share_estimate", 0)
                    lines.append(f"    - {name} (pazar payi: ~%{share:.0f})")

        elif report_data.get("analysis_type") == "performance":
            lines.append("--- Performans ---")
            lines.append(f"  Metrik: {report_inner.get('metric_name', '-')}")
            lines.append(f"  Mevcut: {report_inner.get('current_value', 0)}")
            lines.append(f"  Hedef: {report_inner.get('target_value', 0)}")
            lines.append(f"  Trend: {report_inner.get('trend', '-')}")
            gap = report_inner.get("gap_percentage", 0)
            lines.append(f"  Hedef farki: %{gap:.1f}")

        lines.append("")

        # Oneriler
        recommendations = report_data.get("recommendations", [])
        if recommendations:
            lines.append("--- Oneriler ---")
            for rec in recommendations:
                lines.append(f"  - {rec}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Dahili metodlar ===

    async def _run_analysis(
        self,
        analysis_type: AnalysisType,
        description: str,
        context: str,
    ) -> dict[str, Any]:
        """Anthropic Claude API ile analiz yapar.

        Args:
            analysis_type: Analiz tipi.
            description: Analiz konusu aciklamasi.
            context: Ek baglamsal bilgi.

        Returns:
            LLM analiz sonucu (dict).
        """
        client = self._get_client()

        template = _TASK_PROMPTS[analysis_type]
        user_message = template.format(
            description=description,
            context=context or "Ek bilgi yok.",
            currency=self.config.currency,
        )

        response = await client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text
        return self._parse_llm_response(raw_text)

    @staticmethod
    def _parse_llm_response(text: str) -> dict[str, Any]:
        """LLM yanitini JSON olarak parse eder.

        Args:
            text: LLM ham yaniti.

        Returns:
            Parse edilmis dict. Parse basarisizsa raw_text ile doner.
        """
        # JSON blogu bul (``` arasinda veya dogrudan)
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        json_str = json_match.group(1) if json_match else text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"raw_text": text}

    def _build_report(
        self,
        analysis_type: AnalysisType,
        llm_data: dict[str, Any],
    ) -> AnalysisReport:
        """LLM sonucunu AnalysisReport modeline donusturur.

        Args:
            analysis_type: Analiz tipi.
            llm_data: LLM'den gelen dict.

        Returns:
            Yapilandirilmis AnalysisReport.
        """
        report = AnalysisReport(analysis_type=analysis_type.value)

        if analysis_type == AnalysisType.FEASIBILITY:
            try:
                feasibility = FeasibilityResult(
                    score=float(llm_data.get("score", 50)),
                    strengths=llm_data.get("strengths", []),
                    weaknesses=llm_data.get("weaknesses", []),
                    opportunities=llm_data.get("opportunities", []),
                    threats=llm_data.get("threats", []),
                    recommendation=llm_data.get("recommendation", ""),
                    estimated_timeline=llm_data.get("estimated_timeline", ""),
                )
            except (ValueError, TypeError):
                feasibility = FeasibilityResult(score=50)

            report.data = feasibility.model_dump()
            report.title = "Fizibilite Analizi"

            score = feasibility.score
            if score >= 70:
                report.risk_level = "low"
                report.summary = f"Proje fizibil gorunuyor (skor: {score}/100)."
            elif score >= 40:
                report.risk_level = "medium"
                report.summary = f"Proje orta riskli (skor: {score}/100). Dikkatli ilerlenmeli."
            else:
                report.risk_level = "high"
                report.summary = f"Proje yuksek riskli (skor: {score}/100). Yeniden degerlendirilmeli."

            report.recommendations = [feasibility.recommendation] if feasibility.recommendation else []

        elif analysis_type == AnalysisType.FINANCIAL:
            try:
                financial = FinancialResult(
                    investment=float(llm_data.get("investment", 0)),
                    revenue_estimate=float(llm_data.get("revenue_estimate", 0)),
                    costs=llm_data.get("costs", {}),
                    roi_estimate=float(llm_data.get("roi_estimate", 0)),
                    break_even_months=int(llm_data.get("break_even_months", 0)),
                    risk_factors=llm_data.get("risk_factors", []),
                    currency=llm_data.get("currency", self.config.currency),
                )
            except (ValueError, TypeError):
                financial = FinancialResult()

            report.data = financial.model_dump()
            report.title = "Finansal Analiz"
            report.recommendations = financial.risk_factors

            roi = financial.roi_estimate
            if roi >= 50:
                report.risk_level = "low"
                report.summary = f"Finansal gorunum olumlu (ROI: %{roi:.1f})."
            elif roi >= 10:
                report.risk_level = "medium"
                report.summary = f"Finansal gorunum orta (ROI: %{roi:.1f})."
            else:
                report.risk_level = "high"
                report.summary = f"Finansal gorunum riskli (ROI: %{roi:.1f})."

        elif analysis_type in (AnalysisType.MARKET, AnalysisType.COMPETITOR):
            competitors_data = llm_data.get("competitors", [])
            competitors: list[CompetitorInfo] = []
            for comp in competitors_data:
                try:
                    competitors.append(CompetitorInfo(
                        name=comp.get("name", ""),
                        url=comp.get("url"),
                        strengths=comp.get("strengths", []),
                        weaknesses=comp.get("weaknesses", []),
                        market_share_estimate=comp.get("market_share_estimate"),
                    ))
                except (ValueError, TypeError):
                    continue

            try:
                market = MarketResult(
                    market_size=llm_data.get("market_size", ""),
                    growth_rate=float(llm_data.get("growth_rate", 0)),
                    competitors=competitors,
                    target_audience=llm_data.get("target_audience", ""),
                    trends=llm_data.get("trends", []),
                    entry_barriers=llm_data.get("entry_barriers", []),
                )
            except (ValueError, TypeError):
                market = MarketResult()

            report.data = market.model_dump()
            report.title = (
                "Pazar Analizi" if analysis_type == AnalysisType.MARKET
                else "Rakip Analizi"
            )
            report.recommendations = llm_data.get("recommendations", [])

            barriers = len(market.entry_barriers)
            if barriers >= 3:
                report.risk_level = "high"
                report.summary = f"Pazara giris engelleri yuksek ({barriers} engel tespit edildi)."
            elif barriers >= 1:
                report.risk_level = "medium"
                report.summary = f"Pazara giris orta zorlukta ({barriers} engel). {len(competitors)} rakip mevcut."
            else:
                report.risk_level = "low"
                report.summary = f"Pazar giris icin uygun. {len(competitors)} rakip tespit edildi."

        elif analysis_type == AnalysisType.PERFORMANCE:
            try:
                performance = PerformanceResult(
                    metric_name=llm_data.get("metric_name", ""),
                    current_value=float(llm_data.get("current_value", 0)),
                    target_value=float(llm_data.get("target_value", 0)),
                    trend=llm_data.get("trend", "stable"),
                    gap_percentage=float(llm_data.get("gap_percentage", 0)),
                    recommendations=llm_data.get("recommendations", []),
                )
            except (ValueError, TypeError):
                performance = PerformanceResult()

            report.data = performance.model_dump()
            report.title = "Performans Degerlendirmesi"
            report.recommendations = performance.recommendations

            gap = abs(performance.gap_percentage)
            if gap > 30:
                report.risk_level = "high"
                report.summary = f"Performans hedefin %{gap:.1f} gerisinde. Acil iyilestirme gerekli."
            elif gap > 10:
                report.risk_level = "medium"
                report.summary = f"Performans hedefin %{gap:.1f} gerisinde."
            else:
                report.risk_level = "low"
                report.summary = f"Performans hedefe yakin (%{gap:.1f} fark)."

        # Guven skoru: risk_level bazli
        confidence_map = {"low": 0.8, "medium": 0.6, "high": 0.5}
        report.confidence = confidence_map.get(report.risk_level, 0.7)

        return report

    @staticmethod
    def _map_to_risk_urgency(
        report: AnalysisReport,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Analiz raporunu RiskLevel ve UrgencyLevel'a esler.

        Eslestirme:
        - risk_level "high" -> HIGH risk, MEDIUM urgency
        - risk_level "medium" -> MEDIUM risk, LOW urgency
        - risk_level "low" -> LOW risk, LOW urgency
        - Oneriler 3'ten fazlaysa urgency bir kademe artar

        Args:
            report: Analiz raporu.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        risk_map = {
            "high": RiskLevel.HIGH,
            "medium": RiskLevel.MEDIUM,
            "low": RiskLevel.LOW,
        }
        risk = risk_map.get(report.risk_level, RiskLevel.LOW)

        # Varsayilan urgency: risk bazli
        urgency_defaults = {
            RiskLevel.HIGH: UrgencyLevel.MEDIUM,
            RiskLevel.MEDIUM: UrgencyLevel.LOW,
            RiskLevel.LOW: UrgencyLevel.LOW,
        }
        urgency = urgency_defaults[risk]

        # Cok oneri varsa urgency artar
        if len(report.recommendations) > 3:
            if urgency == UrgencyLevel.LOW:
                urgency = UrgencyLevel.MEDIUM
            elif urgency == UrgencyLevel.MEDIUM:
                urgency = UrgencyLevel.HIGH

        return risk, urgency

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
