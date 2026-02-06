"""E-posta iletisim agent modulu.

Gmail API ve Anthropic Claude API uzerinden e-posta yonetimi:
- Profesyonel e-posta yazma (Turkce, Ingilizce, Arapca)
- Gmail API ile gonderme ve okuma
- Toplu mail gonderme (kisisellestirilmis)
- Gelen cevaplari analiz etme (duygu/niyet)
- Cevap vermeyenlere otomatik hatirlatma takibi
- E-posta sablonlari yonetimi

Sonuclari risk/aciliyet olarak siniflandirir ve karar matrisine iletir.
"""

import base64
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import anthropic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
from app.models.communication import (
    BulkSendResult,
    CommunicationAnalysisResult,
    CommunicationConfig,
    EmailLanguage,
    EmailMessage,
    EmailRecipient,
    EmailTaskType,
    EmailTemplate,
    EmailTone,
    FollowUpEntry,
    FollowUpStatus,
    InboxMessage,
    ResponseAnalysis,
    ResponseSentiment,
)

logger = logging.getLogger("atlas.agent.communication")

# === LLM prompt sablonlari ===
_SYSTEM_PROMPT = (
    "Sen profesyonel bir is iletisimi uzmanisin. "
    "E-postalar yazarken alicinin kulturel baglamina ve is iliskisine uygun, "
    "net ve etkili bir dil kullanirsin. "
    "Yanit formatini her zaman JSON olarak dondur."
)

_COMPOSE_PROMPT = (
    "Asagidaki baglam bilgisine gore profesyonel bir is e-postasi yaz.\n\n"
    "Dil: {language}\n"
    "Ton: {tone}\n"
    "Alici: {recipient_name} ({recipient_email})\n"
    "Konu/Amac: {purpose}\n"
    "Ek Baglamsal Bilgi: {context}\n\n"
    "JSON formatinda yanit ver:\n"
    '{{"subject": "e-posta konu basligi", '
    '"body_html": "HTML formatinda e-posta govdesi", '
    '"body_text": "duz metin formatinda e-posta govdesi"}}\n'
)

_ANALYZE_RESPONSE_PROMPT = (
    "Asagidaki e-posta cevabini analiz et.\n\n"
    "Orijinal konu: {original_subject}\n"
    "Gonderici: {from_email}\n"
    "Cevap icerigi:\n{body}\n\n"
    "JSON formatinda yanit ver:\n"
    '{{"sentiment": "positive|negative|neutral|needs_action|out_of_office", '
    '"summary": "cevabin kisa ozeti", '
    '"action_required": true|false, '
    '"suggested_response": "onerilen cevap metni (bossa bos string)"}}\n'
)

_FOLLOW_UP_PROMPT = (
    "Asagidaki e-posta icin nazik bir hatirlatma (follow-up) mesaji yaz.\n\n"
    "Dil: {language}\n"
    "Ton: {tone}\n"
    "Orijinal konu: {original_subject}\n"
    "Alici: {recipient_name}\n"
    "Gonderim tarihi: {sent_date}\n"
    "Hatirlatma numarasi: {follow_up_number}\n\n"
    "JSON formatinda yanit ver:\n"
    '{{"subject": "hatirlatma konu basligi", '
    '"body_html": "HTML formatinda hatirlatma govdesi", '
    '"body_text": "duz metin formatinda hatirlatma govdesi"}}\n'
)


class CommunicationAgent(BaseAgent):
    """E-posta iletisim agent'i.

    Gmail API ve Anthropic Claude API ile e-posta yonetimi yapar.
    Profesyonel e-posta yazar, gonderir, okur, cevap analiz eder,
    takip yapar ve sablonlari yonetir.

    Attributes:
        config: Iletisim yapilandirmasi.
        templates: Kayitli e-posta sablonlari.
        follow_ups: Takip kayitlari.
    """

    def __init__(
        self,
        config: CommunicationConfig | None = None,
    ) -> None:
        """CommunicationAgent'i baslatir.

        Args:
            config: Iletisim yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="communication")
        self.config = config or CommunicationConfig()
        self._anthropic_client: anthropic.AsyncAnthropic | None = None
        self._gmail_service: Any | None = None
        self.templates: dict[str, EmailTemplate] = {}
        self.follow_ups: list[FollowUpEntry] = []

    # === Client yonetimi ===

    def _get_anthropic_client(self) -> anthropic.AsyncAnthropic:
        """Anthropic API istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis AsyncAnthropic.

        Raises:
            ValueError: API key eksikse.
        """
        if self._anthropic_client is not None:
            return self._anthropic_client

        api_key = settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError("Anthropic API key yapilandirilmamis.")

        self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._anthropic_client

    def _get_gmail_service(self) -> Any:
        """Gmail API servisini dondurur (lazy init).

        OAuth2 credentials ile Gmail API v1 servisi olusturur.

        Returns:
            Yapilandirilmis Gmail API servisi.

        Raises:
            ValueError: Gmail kimlik bilgileri eksikse.
        """
        if self._gmail_service is not None:
            return self._gmail_service

        client_id = settings.gmail_client_id
        client_secret = settings.gmail_client_secret.get_secret_value()
        refresh_token = settings.gmail_refresh_token.get_secret_value()

        if not refresh_token:
            raise ValueError("Gmail refresh token yapilandirilmamis.")

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
        )
        self._gmail_service = build("gmail", "v1", credentials=creds)
        return self._gmail_service

    # === BaseAgent abstract metodlari ===

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """E-posta gorevini calistirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - task_type: Gorev tipi (compose/send/read_inbox/
                  bulk_send/analyze_responses/follow_up_check).
                - config: Ozel yapilandirma (dict, opsiyonel).
                - templates: Sablon listesi (dict listesi, opsiyonel).
                - Gorev tipine ozel anahtarlar (handler dokumanlarina bkz).

        Returns:
            E-posta islem sonuclarini iceren TaskResult.
        """
        # Yapilandirma guncelle
        if task.get("config"):
            self.config = CommunicationConfig(**task["config"])

        # Gorev tipini belirle
        task_type_str = task.get("task_type", "compose")
        try:
            task_type = EmailTaskType(task_type_str)
        except ValueError:
            return TaskResult(
                success=False,
                message=f"Gecersiz gorev tipi: {task_type_str}",
                errors=[f"Gecerli tipler: {[t.value for t in EmailTaskType]}"],
            )

        # Sablonlari kaydet
        for tmpl_dict in task.get("templates", []):
            template = EmailTemplate(**tmpl_dict)
            self.templates[template.name] = template

        analysis_result = CommunicationAnalysisResult(task_type=task_type)
        errors: list[str] = []

        try:
            if task_type == EmailTaskType.COMPOSE:
                await self._handle_compose(task, analysis_result)

            elif task_type == EmailTaskType.SEND:
                await self._handle_send(task, analysis_result)

            elif task_type == EmailTaskType.READ_INBOX:
                await self._handle_read_inbox(task, analysis_result)

            elif task_type == EmailTaskType.BULK_SEND:
                await self._handle_bulk_send(task, analysis_result)

            elif task_type == EmailTaskType.ANALYZE_RESPONSES:
                await self._handle_analyze_responses(task, analysis_result)

            elif task_type == EmailTaskType.FOLLOW_UP_CHECK:
                await self._handle_follow_up_check(task, analysis_result)

            analysis_result.summary = self._build_summary(analysis_result)

        except HttpError as exc:
            self.logger.error("Gmail API hatasi: %s", exc)
            errors.append(f"Gmail API: {exc}")
        except Exception as exc:
            self.logger.error("Iletisim hatasi: %s", exc)
            errors.append(str(exc))

        # Karar matrisi icin analiz
        analysis = await self.analyze({"result": analysis_result.model_dump()})

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "analysis_result": analysis_result.model_dump(),
                "analysis": analysis,
            },
            message=analysis_result.summary or "Iletisim gorevi tamamlandi.",
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Iletisim Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analiz sonuclarini degerlendirir ve risk/aciliyet belirler.

        Args:
            data: {"result": CommunicationAnalysisResult dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary, issues, stats.
        """
        result_dict = data.get("result", {})
        result = (
            CommunicationAnalysisResult(**result_dict)
            if isinstance(result_dict, dict)
            else result_dict
        )

        issues: list[str] = []

        # Olumsuz cevaplar
        for ra in result.response_analyses:
            if ra.sentiment == ResponseSentiment.NEGATIVE:
                issues.append(
                    f"Olumsuz cevap: {ra.from_email} - {ra.summary}"
                )
            elif ra.sentiment == ResponseSentiment.NEEDS_ACTION:
                issues.append(
                    f"Aksiyon gerektiren cevap: {ra.from_email} - {ra.summary}"
                )

        # Cevapsiz takipler
        overdue = [
            f for f in result.follow_ups
            if f.status == FollowUpStatus.NO_RESPONSE
        ]
        if overdue:
            issues.append(f"{len(overdue)} e-posta cevapsiz kaldi")

        expired = [
            f for f in result.follow_ups
            if f.status == FollowUpStatus.EXPIRED
        ]
        if expired:
            issues.append(f"{len(expired)} e-posta takip suresi doldu")

        # Toplu gonderim hatalari
        if result.bulk_result and result.bulk_result.failed > 0:
            issues.append(
                f"Toplu gonderim: {result.bulk_result.failed}/"
                f"{result.bulk_result.total} basarisiz"
            )

        # Risk ve aciliyet eslestirmesi
        risk, urgency = self._map_to_risk_urgency(result)
        action = self._determine_action(risk, urgency)

        return {
            "task_type": result.task_type.value,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": result.summary,
            "issues": issues,
            "stats": {
                "composed_count": len(result.composed_emails),
                "sent_count": len(result.sent_emails),
                "inbox_count": len(result.inbox_messages),
                "analysis_count": len(result.response_analyses),
                "follow_up_count": len(result.follow_ups),
                "overdue_count": len(overdue),
                "expired_count": len(expired),
                "negative_response_count": sum(
                    1 for ra in result.response_analyses
                    if ra.sentiment == ResponseSentiment.NEGATIVE
                ),
                "bulk_sent": (
                    result.bulk_result.sent if result.bulk_result else 0
                ),
                "bulk_failed": (
                    result.bulk_result.failed if result.bulk_result else 0
                ),
            },
        }

    async def report(self, result: TaskResult) -> str:
        """E-posta sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Telegram ve log icin formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        stats = analysis.get("stats", {})
        issues = analysis.get("issues", [])

        lines = [
            "=== E-POSTA ILETISIM RAPORU ===",
            f"Gorev: {analysis.get('task_type', 'bilinmiyor').upper()}",
            f"Risk: {analysis.get('risk', '-')} | "
            f"Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
            "--- Istatistikler ---",
            f"  Olusturulan: {stats.get('composed_count', 0)}",
            f"  Gonderilen: {stats.get('sent_count', 0)}",
            f"  Okunan: {stats.get('inbox_count', 0)}",
            f"  Analiz edilen: {stats.get('analysis_count', 0)}",
            f"  Takip: {stats.get('follow_up_count', 0)}"
            f" (cevapsiz: {stats.get('overdue_count', 0)})",
            f"  Olumsuz cevap: {stats.get('negative_response_count', 0)}",
            "",
        ]

        bulk_sent = stats.get("bulk_sent", 0)
        bulk_failed = stats.get("bulk_failed", 0)
        if bulk_sent or bulk_failed:
            lines.append(
                f"--- Toplu Gonderim: {bulk_sent} basarili, "
                f"{bulk_failed} basarisiz ---"
            )
            lines.append("")

        if issues:
            lines.append("--- Bulgular ---")
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Gorev handler metodlari ===

    async def _handle_compose(
        self,
        task: dict[str, Any],
        result: CommunicationAnalysisResult,
    ) -> None:
        """LLM ile profesyonel e-posta yazar.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - to: Alici e-posta.
                - to_name: Alici adi.
                - purpose: E-posta amaci/konusu.
                - context: Ek baglamsal bilgi.
                - language: Dil (opsiyonel).
                - tone: Ton (opsiyonel).
                - template_name: Sablon adi (opsiyonel).
                - template_variables: Sablon degiskenleri (opsiyonel).
            result: Sonuclarin yazilacagi nesne.
        """
        template_name = task.get("template_name")

        if template_name and template_name in self.templates:
            # Sablon tabanli olusturma
            email = self._compose_from_template(
                template_name,
                task.get("to", ""),
                task.get("to_name", ""),
                task.get("template_variables", {}),
            )
            result.templates_used.append(template_name)
        else:
            # LLM tabanli olusturma
            language = EmailLanguage(
                task.get("language", self.config.default_language.value),
            )
            tone = EmailTone(
                task.get("tone", self.config.default_tone.value),
            )

            client = self._get_anthropic_client()
            user_message = _COMPOSE_PROMPT.format(
                language=language.value,
                tone=tone.value,
                recipient_name=task.get("to_name", ""),
                recipient_email=task.get("to", ""),
                purpose=task.get("purpose", ""),
                context=task.get("context", ""),
            )

            response = await client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            llm_data = self._parse_llm_response(response.content[0].text)

            email = EmailMessage(
                to=task.get("to", ""),
                to_name=task.get("to_name", ""),
                subject=llm_data.get("subject", ""),
                body_html=llm_data.get("body_html", ""),
                body_text=llm_data.get("body_text", ""),
                language=language,
                tone=tone,
            )

        result.composed_emails.append(email)

    async def _handle_send(
        self,
        task: dict[str, Any],
        result: CommunicationAnalysisResult,
    ) -> None:
        """E-postayi Gmail API ile gonderir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - to: Alici e-posta.
                - subject: Konu.
                - body_html: HTML govde.
                - body_text: Duz metin govde (opsiyonel).
                - thread_id: Thread ID (reply icin, opsiyonel).
                - purpose: Amac (govde yoksa LLM ile olusturmak icin).
                - track_follow_up: Takip baslatilsin mi (bool).
            result: Sonuclarin yazilacagi nesne.
        """
        to = task.get("to", "")
        subject = task.get("subject", "")
        body_html = task.get("body_html", "")
        body_text = task.get("body_text", "")

        if not to:
            raise ValueError("Alici (to) gerekli.")

        # Govde yoksa ve amac verilmisse LLM ile olustur
        if not body_html and task.get("purpose"):
            await self._handle_compose(task, result)
            if result.composed_emails:
                composed = result.composed_emails[-1]
                subject = subject or composed.subject
                body_html = composed.body_html
                body_text = composed.body_text

        if not subject:
            raise ValueError("Konu (subject) gerekli.")

        sent = self._send_email(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            thread_id=task.get("thread_id"),
        )
        result.sent_emails.append(sent)

        # Takip baslat
        if task.get("track_follow_up", False):
            entry = FollowUpEntry(
                original_message_id=sent.message_id,
                thread_id=sent.thread_id,
                to_email=to,
                to_name=task.get("to_name", ""),
                subject=subject,
            )
            self.follow_ups.append(entry)
            result.follow_ups.append(entry)

    async def _handle_read_inbox(
        self,
        task: dict[str, Any],
        result: CommunicationAnalysisResult,
    ) -> None:
        """Gmail gelen kutusunu okur.

        Args:
            task: Gorev detaylari. Opsiyonel anahtarlar:
                - query: Gmail arama sorgusu (orn: "is:unread").
                - max_results: Okunacak e-posta sayisi.
            result: Sonuclarin yazilacagi nesne.
        """
        service = self._get_gmail_service()
        query = task.get("query", "is:unread")
        max_results = task.get("max_results", self.config.max_inbox_results)

        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = response.get("messages", [])
        for msg_ref in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            inbox_msg = self._parse_gmail_message(msg_data)
            result.inbox_messages.append(inbox_msg)

    async def _handle_bulk_send(
        self,
        task: dict[str, Any],
        result: CommunicationAnalysisResult,
    ) -> None:
        """Toplu e-posta gonderir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - recipients: Alici listesi (EmailRecipient dict listesi).
                - template_name: Sablon adi (opsiyonel).
                - subject: Konu (sablon yoksa).
                - body_html: HTML govde (sablon yoksa).
                - track_follow_up: Takip baslatilsin mi (bool).
            result: Sonuclarin yazilacagi nesne.
        """
        recipients_data = task.get("recipients", [])
        if not recipients_data:
            raise ValueError("Alici listesi (recipients) bos.")

        recipients = [EmailRecipient(**r) for r in recipients_data]
        template_name = task.get("template_name")
        bulk_result = BulkSendResult(total=len(recipients))

        for recipient in recipients:
            try:
                if template_name and template_name in self.templates:
                    email = self._compose_from_template(
                        template_name,
                        recipient.email,
                        recipient.name,
                        recipient.variables,
                    )
                    if template_name not in result.templates_used:
                        result.templates_used.append(template_name)
                else:
                    email = EmailMessage(
                        to=recipient.email,
                        to_name=recipient.name,
                        subject=self._substitute_variables(
                            task.get("subject", ""),
                            recipient.variables,
                        ),
                        body_html=self._substitute_variables(
                            task.get("body_html", ""),
                            recipient.variables,
                        ),
                        body_text=self._substitute_variables(
                            task.get("body_text", ""),
                            recipient.variables,
                        ),
                    )

                sent = self._send_email(
                    to=email.to,
                    subject=email.subject,
                    body_html=email.body_html,
                    body_text=email.body_text,
                )
                result.sent_emails.append(sent)
                bulk_result.sent += 1

                # Takip
                if task.get("track_follow_up", False):
                    entry = FollowUpEntry(
                        original_message_id=sent.message_id,
                        thread_id=sent.thread_id,
                        to_email=recipient.email,
                        to_name=recipient.name,
                        subject=email.subject,
                    )
                    self.follow_ups.append(entry)

            except Exception as exc:
                bulk_result.failed += 1
                bulk_result.failed_recipients.append(
                    {"email": recipient.email, "error": str(exc)},
                )
                logger.error(
                    "Toplu gonderim hatasi [%s]: %s",
                    recipient.email,
                    exc,
                )

        result.bulk_result = bulk_result

    async def _handle_analyze_responses(
        self,
        task: dict[str, Any],
        result: CommunicationAnalysisResult,
    ) -> None:
        """Gelen cevaplari LLM ile analiz eder.

        Args:
            task: Gorev detaylari. Opsiyonel anahtarlar:
                - query: Gmail arama sorgusu.
                - max_results: Okunacak e-posta sayisi.
                - messages: Dogrudan analiz edilecek InboxMessage dict listesi.
            result: Sonuclarin yazilacagi nesne.
        """
        # Mesajlari hazirla
        if task.get("messages"):
            for msg_dict in task["messages"]:
                result.inbox_messages.append(InboxMessage(**msg_dict))
        elif not result.inbox_messages:
            await self._handle_read_inbox(task, result)

        client = self._get_anthropic_client()

        for msg in result.inbox_messages:
            user_message = _ANALYZE_RESPONSE_PROMPT.format(
                original_subject=msg.subject,
                from_email=msg.from_email,
                body=msg.body_text[:3000],
            )

            response = await client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            llm_data = self._parse_llm_response(response.content[0].text)

            try:
                sentiment = ResponseSentiment(
                    llm_data.get("sentiment", "neutral"),
                )
            except ValueError:
                sentiment = ResponseSentiment.NEUTRAL

            analysis = ResponseAnalysis(
                message_id=msg.message_id,
                from_email=msg.from_email,
                sentiment=sentiment,
                summary=llm_data.get("summary", ""),
                action_required=bool(llm_data.get("action_required", False)),
                suggested_response=llm_data.get("suggested_response", ""),
            )
            result.response_analyses.append(analysis)

            # Takip durumunu guncelle
            self._update_follow_up_from_response(msg)

    async def _handle_follow_up_check(
        self,
        task: dict[str, Any],
        result: CommunicationAnalysisResult,
    ) -> None:
        """Cevap vermeyenleri kontrol eder ve hatirlatma gonderir.

        Args:
            task: Gorev detaylari. Opsiyonel anahtarlar:
                - auto_send: Hatirlatmayi otomatik gonder (bool).
                - follow_up_days: Bekleme suresi (gun, opsiyonel).
                - language: Hatirlatma dili (opsiyonel).
                - tone: Hatirlatma tonu (opsiyonel).
            result: Sonuclarin yazilacagi nesne.
        """
        now = datetime.now(timezone.utc)
        auto_send = task.get("auto_send", False)
        follow_up_days = task.get(
            "follow_up_days",
            self.config.follow_up_days,
        )

        for entry in self.follow_ups:
            if entry.status not in (
                FollowUpStatus.PENDING,
                FollowUpStatus.FOLLOW_UP_SENT,
            ):
                continue

            days_elapsed = (now - entry.sent_at).days
            if days_elapsed < follow_up_days:
                continue

            # Maksimum hatirlatma asildi
            if entry.follow_up_count >= self.config.max_follow_ups:
                entry.status = FollowUpStatus.EXPIRED
                result.follow_ups.append(entry)
                continue

            entry.status = FollowUpStatus.NO_RESPONSE
            result.follow_ups.append(entry)

            if auto_send:
                language = task.get(
                    "language",
                    self.config.default_language.value,
                )
                tone = task.get("tone", self.config.default_tone.value)

                client = self._get_anthropic_client()
                user_message = _FOLLOW_UP_PROMPT.format(
                    language=language,
                    tone=tone,
                    original_subject=entry.subject,
                    recipient_name=entry.to_name or entry.to_email,
                    sent_date=entry.sent_at.strftime("%Y-%m-%d"),
                    follow_up_number=entry.follow_up_count + 1,
                )

                response = await client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}],
                )

                llm_data = self._parse_llm_response(
                    response.content[0].text,
                )

                sent = self._send_email(
                    to=entry.to_email,
                    subject=llm_data.get(
                        "subject",
                        f"Re: {entry.subject}",
                    ),
                    body_html=llm_data.get("body_html", ""),
                    body_text=llm_data.get("body_text", ""),
                    thread_id=entry.thread_id,
                )

                entry.follow_up_count += 1
                entry.last_follow_up_at = now
                entry.status = FollowUpStatus.FOLLOW_UP_SENT
                result.sent_emails.append(sent)

    # === Yardimci metodlar ===

    def _send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        thread_id: str | None = None,
    ) -> EmailMessage:
        """Gmail API ile tek e-posta gonderir.

        Args:
            to: Alici e-posta.
            subject: Konu.
            body_html: HTML govde.
            body_text: Duz metin govde.
            thread_id: Reply icin thread ID.

        Returns:
            Gonderilen EmailMessage.
        """
        service = self._get_gmail_service()

        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject
        if self.config.sender_email:
            msg["From"] = (
                f"{self.config.sender_name} <{self.config.sender_email}>"
            )

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html or " ", "html", "utf-8"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        send_body: dict[str, str] = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        sent_msg = (
            service.users()
            .messages()
            .send(userId="me", body=send_body)
            .execute()
        )

        return EmailMessage(
            message_id=sent_msg.get("id", ""),
            thread_id=sent_msg.get("threadId", ""),
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            sent_at=datetime.now(timezone.utc),
            is_sent=True,
        )

    def _compose_from_template(
        self,
        template_name: str,
        to: str,
        to_name: str,
        variables: dict[str, str],
    ) -> EmailMessage:
        """Sablondan e-posta olusturur.

        Args:
            template_name: Sablon adi.
            to: Alici e-posta.
            to_name: Alici adi.
            variables: Degisken degerleri.

        Returns:
            Olusturulan EmailMessage.
        """
        template = self.templates[template_name]
        subject = self._substitute_variables(template.subject, variables)
        body = self._substitute_variables(template.body, variables)

        return EmailMessage(
            to=to,
            to_name=to_name,
            subject=subject,
            body_html=body,
            body_text=body,
            language=template.language,
            tone=template.tone,
        )

    @staticmethod
    def _substitute_variables(
        text: str,
        variables: dict[str, str],
    ) -> str:
        """Metin icindeki {degisken} yer tutucularini degerlerle degistirir.

        Args:
            text: Sablon metni.
            variables: Degisken adi -> deger eslestirmesi.

        Returns:
            Degiskenler yerine konmus metin.
        """
        for key, value in variables.items():
            text = text.replace(f"{{{key}}}", value)
        return text

    @staticmethod
    def _parse_gmail_message(msg_data: dict[str, Any]) -> InboxMessage:
        """Gmail API mesaj verisini InboxMessage'a donusturur.

        Args:
            msg_data: Gmail API'den gelen mesaj verisi.

        Returns:
            Parse edilmis InboxMessage.
        """
        headers = {
            h["name"].lower(): h["value"]
            for h in msg_data.get("payload", {}).get("headers", [])
        }

        # Govde icerigini ayikla
        body_text = ""
        payload = msg_data.get("payload", {})
        if payload.get("body", {}).get("data"):
            body_text = base64.urlsafe_b64decode(
                payload["body"]["data"],
            ).decode("utf-8", errors="replace")
        elif payload.get("parts"):
            for part in payload["parts"]:
                if (
                    part.get("mimeType") == "text/plain"
                    and part.get("body", {}).get("data")
                ):
                    body_text = base64.urlsafe_b64decode(
                        part["body"]["data"],
                    ).decode("utf-8", errors="replace")
                    break

        # From header parse: "Name <email>" formatini ayristir
        from_header = headers.get("from", "")
        from_match = re.match(r"(.*?)\s*<(.+?)>", from_header)
        from_name = (
            from_match.group(1).strip("\" ") if from_match else ""
        )
        from_email = from_match.group(2) if from_match else from_header

        return InboxMessage(
            message_id=msg_data.get("id", ""),
            thread_id=msg_data.get("threadId", ""),
            from_email=from_email,
            from_name=from_name,
            subject=headers.get("subject", ""),
            snippet=msg_data.get("snippet", ""),
            body_text=body_text,
            labels=msg_data.get("labelIds", []),
        )

    @staticmethod
    def _parse_llm_response(text: str) -> dict[str, Any]:
        """LLM yanitini JSON olarak parse eder.

        Args:
            text: LLM ham yaniti.

        Returns:
            Parse edilmis dict. Parse basarisizsa bos dict icinde
            raw_text anahtar ile ham metin doner.
        """
        # JSON blogu bul (``` arasinda veya dogrudan)
        json_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```",
            text,
            re.DOTALL,
        )
        json_str = json_match.group(1) if json_match else text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Icinden { } blogu cikar
            brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"raw_text": text}

    def _update_follow_up_from_response(self, msg: InboxMessage) -> None:
        """Gelen mesajin takip listesindeki karsiligini gunceller.

        Thread ID eslestirmesi ile takip durumunu RESPONDED yapar.

        Args:
            msg: Gelen mesaj.
        """
        for entry in self.follow_ups:
            if entry.thread_id == msg.thread_id and entry.status in (
                FollowUpStatus.PENDING,
                FollowUpStatus.NO_RESPONSE,
                FollowUpStatus.FOLLOW_UP_SENT,
            ):
                entry.status = FollowUpStatus.RESPONDED
                entry.response_received_at = datetime.now(timezone.utc)
                break

    # === Karar matrisi entegrasyonu ===

    @staticmethod
    def _map_to_risk_urgency(
        result: CommunicationAnalysisResult,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Iletisim bulgularini RiskLevel ve UrgencyLevel'a esler.

        Karar matrisi entegrasyonu:
        - Basarili gonderim, pozitif cevap -> LOW/LOW (kaydet)
        - Cevapsiz e-posta -> LOW/MEDIUM (bildir)
        - Olumsuz cevap -> MEDIUM/MEDIUM (bildir)
        - 3+ olumsuz cevap -> MEDIUM/HIGH (otomatik duzelt)
        - Toplu gonderim %50+ basarisiz -> MEDIUM/HIGH (otomatik duzelt)
        - Takip suresi dolmus (expired) -> HIGH/HIGH (acil)

        Args:
            result: Iletisim analiz sonucu.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        risk = RiskLevel.LOW
        urgency = UrgencyLevel.LOW

        # Olumsuz cevaplar
        negative_count = sum(
            1 for ra in result.response_analyses
            if ra.sentiment == ResponseSentiment.NEGATIVE
        )
        if negative_count >= 3:
            risk = RiskLevel.MEDIUM
            urgency = UrgencyLevel.HIGH
        elif negative_count > 0:
            risk = RiskLevel.MEDIUM
            urgency = UrgencyLevel.MEDIUM

        # Cevapsiz takipler
        no_response = [
            f for f in result.follow_ups
            if f.status == FollowUpStatus.NO_RESPONSE
        ]
        expired = [
            f for f in result.follow_ups
            if f.status == FollowUpStatus.EXPIRED
        ]

        if expired:
            risk = RiskLevel.HIGH
            urgency = UrgencyLevel.HIGH
        elif no_response and urgency == UrgencyLevel.LOW:
            urgency = UrgencyLevel.MEDIUM

        # Toplu gonderim hatalari
        if result.bulk_result and result.bulk_result.total > 0:
            fail_ratio = (
                result.bulk_result.failed / result.bulk_result.total
            )
            if fail_ratio > 0.5:
                risk = max(risk, RiskLevel.MEDIUM, key=_risk_order)
                urgency = UrgencyLevel.HIGH
            elif fail_ratio > 0 and urgency == UrgencyLevel.LOW:
                urgency = UrgencyLevel.MEDIUM

        return risk, urgency

    @staticmethod
    def _determine_action(
        risk: RiskLevel,
        urgency: UrgencyLevel,
    ) -> ActionType:
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

    def _build_summary(
        self,
        result: CommunicationAnalysisResult,
    ) -> str:
        """Analiz ozeti olusturur.

        Args:
            result: Iletisim analiz sonucu.

        Returns:
            Ozet metni.
        """
        parts: list[str] = []

        if result.composed_emails:
            parts.append(
                f"{len(result.composed_emails)} e-posta olusturuldu",
            )

        if result.sent_emails:
            parts.append(f"{len(result.sent_emails)} e-posta gonderildi")

        if result.inbox_messages:
            parts.append(f"{len(result.inbox_messages)} mesaj okundu")

        if result.response_analyses:
            negative = sum(
                1 for ra in result.response_analyses
                if ra.sentiment == ResponseSentiment.NEGATIVE
            )
            text = f"{len(result.response_analyses)} cevap analiz edildi"
            if negative:
                text += f" ({negative} olumsuz)"
            parts.append(text)

        if result.follow_ups:
            overdue = sum(
                1 for f in result.follow_ups
                if f.status == FollowUpStatus.NO_RESPONSE
            )
            parts.append(
                f"{len(result.follow_ups)} takip ({overdue} cevapsiz)",
            )

        if result.bulk_result:
            parts.append(
                f"toplu gonderim: {result.bulk_result.sent}/"
                f"{result.bulk_result.total} basarili",
            )

        return " | ".join(parts) if parts else "Iletisim gorevi tamamlandi."


def _risk_order(level: RiskLevel) -> int:
    """RiskLevel siralama yardimcisi (max ile kullanmak icin)."""
    return {"low": 0, "medium": 1, "high": 2}.get(level.value, 0)
