"""Yaratici icerik ve urun gelistirme agent modulu.

Anthropic Claude API ile yaratici icerik uretir:
- Urun fikri onerisi (Mapa Health, FTRK Store icin)
- Icerik uretimi (blog, sosyal medya, e-posta, video script)
- Reklam metni yazimi (Google Ads, sosyal medya)
- Marka isim onerisi (tagline, domain dahil)
- Ambalaj tasarimi onerisi (konsept, malzeme, renk)

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
from app.models.creative import (
    AdCopy,
    BrandSuggestion,
    ContentPiece,
    CreativeConfig,
    CreativeResult,
    CreativeType,
    PackagingIdea,
    ProductIdea,
)

logger = logging.getLogger("atlas.agent.creative")

# === LLM prompt sablonlari ===
_SYSTEM_PROMPT_TEMPLATE = (
    "Sen yaratici bir icerik stratejisti ve marka danismanisin. "
    "Turkce yanit ver. Yaratici ve ozgun fikirler uret. "
    "Marka sesi: {brand_voice}. "
    "Yanitlarini JSON formatinda dondur."
)

_TASK_PROMPTS: dict[CreativeType, str] = {
    CreativeType.PRODUCT_IDEA: (
        "Asagidaki bilgilere gore yenilikci urun fikirleri oner.\n"
        "Her urun fikri icin isim, aciklama, hedef kitle, benzersiz deger, "
        "tahmini maliyet ve pazar potansiyeli belirle.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"items": [{{"name": "urun adi", "description": "urun aciklamasi", '
        '"target_audience": "hedef kitle", "unique_value": "benzersiz deger", '
        '"estimated_cost": "tahmini maliyet", '
        '"market_potential": "pazar potansiyeli"}}], '
        '"summary": "genel degerlendirme", '
        '"recommendations": ["oneri listesi"]}}\n\n'
        "Sektor/Alan: {description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    CreativeType.CONTENT: (
        "Asagidaki bilgilere gore icerik uret.\n"
        "Baslik, govde metni, icerik turu, hedef platform, "
        "hashtag'ler ve CTA belirle.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"items": [{{"title": "baslik", "body": "icerik metni", '
        '"content_type": "blog|social|email|video_script", '
        '"target_platform": "platform", '
        '"hashtags": ["hashtag1", "hashtag2"], '
        '"cta": "harekete gecirici mesaj"}}], '
        '"summary": "genel degerlendirme", '
        '"recommendations": ["oneri listesi"]}}\n\n'
        "Konu: {description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    CreativeType.AD_COPY: (
        "Asagidaki bilgilere gore reklam metni yaz.\n"
        "Ana baslik, aciklama, CTA, hedef kitle, platform "
        "ve alternatif varyasyonlar olustur.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"items": [{{"headline": "ana baslik", "description": "aciklama", '
        '"cta": "harekete gecirici mesaj", "target_audience": "hedef kitle", '
        '"platform": "reklam platformu", '
        '"variations": [{{"headline": "alt baslik", "description": "alt aciklama"}}]}}], '
        '"summary": "genel degerlendirme", '
        '"recommendations": ["oneri listesi"]}}\n\n'
        "Urun/Hizmet: {description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    CreativeType.BRAND_NAME: (
        "Asagidaki bilgilere gore marka isim onerileri uret.\n"
        "Her oneri icin isim, slogan, secim gerekceleri "
        "ve domain onerileri belirle.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"items": [{{"name": "marka adi", "tagline": "slogan", '
        '"reasoning": "secim gerekcesi", '
        '"domain_suggestions": ["domain1.com", "domain2.com"]}}], '
        '"summary": "genel degerlendirme", '
        '"recommendations": ["oneri listesi"]}}\n\n'
        "Sektor ve ozellikler: {description}\n\n"
        "Ek bilgi:\n{context}"
    ),
    CreativeType.PACKAGING: (
        "Asagidaki bilgilere gore ambalaj tasarimi onerisi uret.\n"
        "Tasarim konsepti, malzeme, renk paleti, stil "
        "ve surdurulebilirlik notu belirle.\n\n"
        "JSON formatinda yanit ver:\n"
        '{{"items": [{{"concept": "tasarim konsepti", '
        '"materials": ["malzeme1", "malzeme2"], '
        '"colors": ["renk1", "renk2"], '
        '"style": "tasarim stili", '
        '"sustainability": "surdurulebilirlik notu"}}], '
        '"summary": "genel degerlendirme", '
        '"recommendations": ["oneri listesi"]}}\n\n'
        "Urun bilgileri: {description}\n\n"
        "Ek bilgi:\n{context}"
    ),
}

# CreativeType -> model sinifi eslestirmesi (parse icin)
_ITEM_MODELS: dict[CreativeType, type] = {
    CreativeType.PRODUCT_IDEA: ProductIdea,
    CreativeType.CONTENT: ContentPiece,
    CreativeType.AD_COPY: AdCopy,
    CreativeType.BRAND_NAME: BrandSuggestion,
    CreativeType.PACKAGING: PackagingIdea,
}


class CreativeAgent(BaseAgent):
    """Yaratici icerik ve urun gelistirme agent'i.

    Anthropic Claude API ile urun fikirleri, icerik,
    reklam metni, marka ismi ve ambalaj tasarimi uretir.
    Fatih'in isleri (Mapa Health, FTRK Store, e-ticaret)
    icin optimize edilmistir.

    Attributes:
        config: Yaratici agent yapilandirmasi.
    """

    def __init__(
        self,
        config: CreativeConfig | None = None,
    ) -> None:
        """CreativeAgent'i baslatir.

        Args:
            config: Yaratici agent yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="creative")
        self.config = config or CreativeConfig()
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
        """Yaratici gorev calistirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - task_type: Icerik tipi (product_idea/content/ad_copy/
                  brand_name/packaging).
                - description: Konu/urun aciklamasi.
                - context: Ek baglamsal bilgi (opsiyonel).
                - brand_voice: Marka ses tonu (opsiyonel, config'i override).
                - config: Ozel yapilandirma (dict, opsiyonel).

        Returns:
            Yaratici icerik sonuclarini iceren TaskResult.
        """
        if task.get("config"):
            self.config = CreativeConfig(**task["config"])

        if task.get("brand_voice"):
            self.config.brand_voice = task["brand_voice"]

        # Gorev tipini belirle
        task_type_str = task.get("task_type", "content")
        try:
            creative_type = CreativeType(task_type_str)
        except ValueError:
            return TaskResult(
                success=False,
                message=f"Gecersiz icerik tipi: {task_type_str}",
                errors=[f"Gecerli tipler: {[t.value for t in CreativeType]}"],
            )

        description = task.get("description", "")
        if not description:
            return TaskResult(
                success=False,
                message="Icerik uretimi icin aciklama belirtilmemis.",
                errors=["'description' alani gerekli."],
            )

        context = task.get("context", "")

        self.logger.info(
            "Yaratici icerik baslatiliyor: tip=%s, aciklama=%s",
            creative_type.value,
            description[:100],
        )

        errors: list[str] = []

        # LLM ile uret
        try:
            llm_result = await self._generate(
                creative_type, description, context,
            )
        except Exception as exc:
            self.logger.error("LLM uretim hatasi: %s", exc)
            return TaskResult(
                success=False,
                message=f"Icerik uretimi sirasinda hata: {exc}",
                errors=[str(exc)],
            )

        # Sonucu modele donustur
        creative_result = self._build_result(creative_type, llm_result)

        # Karar matrisi icin analiz
        analysis = await self.analyze({
            "creative_type": creative_type.value,
            "result": creative_result.model_dump(),
        })

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "creative_result": creative_result.model_dump(),
                "analysis": analysis,
            },
            message=creative_result.summary or "Icerik uretimi tamamlandi.",
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Yaratici Rapor:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Yaratici sonuclari degerlendirir ve risk/aciliyet belirler.

        Yaratici icerik genelde dusuk risklidir (icerik uretimi
        geri alinabilir bir islemdir).

        Args:
            data: {"creative_type": str, "result": CreativeResult dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary.
        """
        result_dict = data.get("result", {})
        result = (
            CreativeResult(**result_dict)
            if isinstance(result_dict, dict)
            else result_dict
        )

        creative_type = data.get("creative_type", "content")

        risk, urgency = self._map_to_risk_urgency(creative_type, result)
        action = self._determine_action(risk, urgency)

        return {
            "creative_type": creative_type,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": result.summary,
            "item_count": len(result.items),
            "recommendations": result.recommendations,
        }

    async def report(self, result: TaskResult) -> str:
        """Yaratici icerik sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        creative = result.data.get("creative_result", {})
        creative_type = analysis.get("creative_type", "-")

        lines = [
            "=== YARATICI ICERIK RAPORU ===",
            f"Tip: {creative_type.upper()}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            f"Uretilen oge: {analysis.get('item_count', 0)}",
            "",
            creative.get("summary", ""),
            "",
        ]

        # Icerik turune gore detay
        items = creative.get("items", [])
        for i, item in enumerate(items[:5], 1):
            lines.append(f"--- Oneri #{i} ---")

            if creative_type == "product_idea":
                lines.append(f"  Urun: {item.get('name', '-')}")
                lines.append(f"  Aciklama: {item.get('description', '-')[:100]}")
                lines.append(f"  Hedef: {item.get('target_audience', '-')}")
                lines.append(f"  Maliyet: {item.get('estimated_cost', '-')}")

            elif creative_type == "content":
                lines.append(f"  Baslik: {item.get('title', '-')}")
                lines.append(f"  Tur: {item.get('content_type', '-')}")
                lines.append(f"  Platform: {item.get('target_platform', '-')}")
                body = item.get("body", "")
                if body:
                    lines.append(f"  Icerik: {body[:150]}...")
                hashtags = item.get("hashtags", [])
                if hashtags:
                    lines.append(f"  Hashtag'ler: {' '.join(hashtags[:5])}")

            elif creative_type == "ad_copy":
                lines.append(f"  Baslik: {item.get('headline', '-')}")
                lines.append(f"  Aciklama: {item.get('description', '-')[:100]}")
                lines.append(f"  CTA: {item.get('cta', '-')}")
                lines.append(f"  Platform: {item.get('platform', '-')}")
                variations = item.get("variations", [])
                if variations:
                    lines.append(f"  Varyasyon sayisi: {len(variations)}")

            elif creative_type == "brand_name":
                lines.append(f"  Marka: {item.get('name', '-')}")
                lines.append(f"  Slogan: {item.get('tagline', '-')}")
                lines.append(f"  Gerekce: {item.get('reasoning', '-')[:100]}")
                domains = item.get("domain_suggestions", [])
                if domains:
                    lines.append(f"  Domain: {', '.join(domains[:3])}")

            elif creative_type == "packaging":
                lines.append(f"  Konsept: {item.get('concept', '-')}")
                lines.append(f"  Stil: {item.get('style', '-')}")
                materials = item.get("materials", [])
                if materials:
                    lines.append(f"  Malzeme: {', '.join(materials)}")
                colors = item.get("colors", [])
                if colors:
                    lines.append(f"  Renkler: {', '.join(colors)}")

            lines.append("")

        # Oneriler
        recommendations = creative.get("recommendations", [])
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

    async def _generate(
        self,
        creative_type: CreativeType,
        description: str,
        context: str,
    ) -> dict[str, Any]:
        """Anthropic Claude API ile yaratici icerik uretir.

        Args:
            creative_type: Icerik tipi.
            description: Konu/urun aciklamasi.
            context: Ek baglamsal bilgi.

        Returns:
            LLM uretim sonucu (dict).
        """
        client = self._get_client()

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            brand_voice=self.config.brand_voice,
        )

        template = _TASK_PROMPTS[creative_type]
        user_message = template.format(
            description=description,
            context=context or "Ek bilgi yok.",
        )

        response = await client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.creativity_level,
            system=system_prompt,
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

    @staticmethod
    def _build_result(
        creative_type: CreativeType,
        llm_data: dict[str, Any],
    ) -> CreativeResult:
        """LLM sonucunu CreativeResult modeline donusturur.

        Args:
            creative_type: Icerik tipi.
            llm_data: LLM'den gelen dict.

        Returns:
            Yapilandirilmis CreativeResult.
        """
        result = CreativeResult(creative_type=creative_type.value)

        # Items listesini parse et ve dogrula
        raw_items = llm_data.get("items", [])
        model_cls = _ITEM_MODELS.get(creative_type)

        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue

            if model_cls:
                try:
                    validated = model_cls(**raw_item)
                    result.items.append(validated.model_dump())
                except (ValueError, TypeError):
                    # Dogrulama basarisizsa ham dict'i kullan
                    result.items.append(raw_item)
            else:
                result.items.append(raw_item)

        result.summary = llm_data.get("summary", "")
        result.recommendations = llm_data.get("recommendations", [])

        return result

    @staticmethod
    def _map_to_risk_urgency(
        creative_type: str,
        result: CreativeResult,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Yaratici sonucu RiskLevel ve UrgencyLevel'a esler.

        Yaratici icerik genelde dusuk risk tasir (geri alinabilir).
        Reklam metni ve marka ismi biraz daha yuksek risk tasir
        (dis dunyaya yansir).

        Args:
            creative_type: Icerik tipi.
            result: Yaratici sonuc.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        # Reklam ve marka: dis dunyaya yansidigi icin biraz daha dikkatli
        if creative_type in ("ad_copy", "brand_name"):
            risk = RiskLevel.MEDIUM
            urgency = UrgencyLevel.LOW
        else:
            risk = RiskLevel.LOW
            urgency = UrgencyLevel.LOW

        # Bos sonuc -> orta urgency (yeniden denenmeli)
        if not result.items:
            urgency = UrgencyLevel.MEDIUM

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
