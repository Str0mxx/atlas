"""ATLAS Master Agent modulu.

Tum gelen gorevleri analiz eder, karar matrisini kullanarak
uygun agent'a yonlendirir. Akilli agent secimi, eskalasyon,
karar denetim izi ve onay is akisi yeteneklerini icerir.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.decision_matrix import (
    ActionType,
    Decision,
    DecisionMatrix,
    RiskLevel,
    UrgencyLevel,
)
from app.models.decision import (
    ApprovalRequest,
    ApprovalStatus,
    DecisionAuditEntry,
    DecisionCreate,
    EscalationLevel,
    EscalationRecord,
)

logger = logging.getLogger(__name__)


# === Agent Anahtar Kelime Eslestirme Tablosu ===

AGENT_KEYWORDS: dict[str, list[str]] = {
    "security": [
        "security", "firewall", "ssl", "hack", "auth", "fail2ban",
        "guvenlik", "saldiri", "izinsiz", "sertifika",
    ],
    "server_monitor": [
        "server", "cpu", "memory", "disk", "uptime", "restart",
        "sunucu", "bellek", "islemci", "servis",
    ],
    "marketing": [
        "ads", "campaign", "google ads", "seo", "keyword", "reklam",
        "kampanya", "anahtar kelime", "teklif", "maliyet",
    ],
    "research": [
        "research", "supplier", "tedarikci", "market", "trend",
        "arastirma", "pazar", "fiyat", "rekabet",
    ],
    "communication": [
        "email", "mail", "message", "iletisim", "mesaj", "posta",
        "yanit", "gonder",
    ],
    "coding": [
        "code", "bug", "deploy", "git", "error", "kod", "hata",
        "deployment", "test", "refactor",
    ],
    "analysis": [
        "analysis", "report", "analiz", "rapor", "fizibilite",
        "istatistik", "metric", "performans",
    ],
    "creative": [
        "design", "content", "icerik", "urun", "tasarim", "gorsel",
        "logo", "marka",
    ],
}


class MasterAgent(BaseAgent):
    """Ana koordinator agent.

    Gelen gorevleri analiz eder, karar matrisine gore
    uygun alt agent'a yonlendirir veya dogrudan islem yapar.

    Akilli agent secimi, eskalasyon mantigi, karar denetim izi
    ve onay is akisi yeteneklerini icerir.

    Attributes:
        decision_matrix: Karar matrisi.
        agents: Kayitli alt agent'lar.
        telegram_bot: Telegram bildirim botu.
        enable_escalation: Eskalasyon mantigi aktif mi.
        decision_history: Karar denetim izi gecmisi.
        pending_approvals: Bekleyen onay istekleri.
        escalation_history: Eskalasyon gecmisi.
    """

    def __init__(self, enable_escalation: bool = False) -> None:
        """Master Agent'i baslatir.

        Args:
            enable_escalation: Eskalasyon mantigi aktif mi.
                False ise basarisiz gorevler eskalasyon olmadan doner.
        """
        super().__init__(name="MasterAgent")
        self.decision_matrix = DecisionMatrix()
        self.agents: dict[str, BaseAgent] = {}
        self.telegram_bot: Any = None
        self.enable_escalation = enable_escalation

        # Karar denetim izi
        self.decision_history: list[DecisionAuditEntry] = []
        self._max_history: int = 1000

        # Onay is akisi
        self.pending_approvals: dict[str, ApprovalRequest] = {}

        # Eskalasyon gecmisi
        self.escalation_history: list[EscalationRecord] = []

        self.logger.info("Master Agent hazir. Kayitli agent sayisi: %d", len(self.agents))

    def register_agent(self, agent: BaseAgent) -> None:
        """Yeni bir alt agent kaydeder.

        Args:
            agent: Kaydedilecek agent.
        """
        self.agents[agent.name] = agent
        self.logger.info("Agent kaydedildi: %s", agent.name)

    # === Akilli Agent Secimi ===

    def select_agent(self, task: dict[str, Any]) -> str | None:
        """Gorev icin en uygun agent'i otomatik secer.

        Once target_agent kontrol edilir. Yoksa gorev aciklamasindaki
        anahtar kelimelere gore en uygun agent belirlenir.

        Args:
            task: Gorev detaylari.

        Returns:
            Secilen agent adi veya None (eslesme bulunamazsa).
        """
        # Acik belirtilmisse onu kullan
        target = task.get("target_agent")
        if target and target in self.agents:
            return target

        # Anahtar kelime eslestirme
        description = task.get("description", "").lower()
        best_agent: str | None = None
        best_score = 0

        for agent_type, keywords in AGENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in description)
            if score > best_score:
                # Agent type'in kayitli agent'lar arasinda karsiligi var mi?
                matching = [
                    name for name in self.agents
                    if agent_type.lower() in name.lower()
                ]
                if matching:
                    best_agent = matching[0]
                    best_score = score

        if best_agent:
            self.logger.info(
                "Otomatik agent secimi: %s (skor=%d)", best_agent, best_score,
            )
        return best_agent

    # === Temel Execute ===

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Gorevi analiz edip uygun agent'a yonlendirir.

        Karar matrisinden aksiyon belirler, akilli agent secimi yapar,
        denetim izi kaydeder. Eskalasyon aktifse basarisiz gorevleri
        yukselterek tekrar dener.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - description: Gorev aciklamasi
                - risk: Risk seviyesi (low/medium/high)
                - urgency: Aciliyet seviyesi (low/medium/high)
                - target_agent: (opsiyonel) Hedef agent adi

        Returns:
            Gorev sonucu.
        """
        description = task.get("description", "tanimsiz gorev")
        risk = RiskLevel(task.get("risk", "low"))
        urgency = UrgencyLevel(task.get("urgency", "low"))

        self.logger.info("Gorev alindi: %s", description)

        # Karar matrisinden aksiyon belirle
        decision = await self.decision_matrix.evaluate(
            risk=risk,
            urgency=urgency,
            context={"detail": description},
        )

        # Akilli agent secimi
        agent_name = self.select_agent(task)
        selection_method = "explicit" if task.get("target_agent") else (
            "keyword" if agent_name else "none"
        )
        # Secilen agent'i task'a ekle (route_action icin)
        if agent_name and not task.get("target_agent"):
            task["target_agent"] = agent_name

        # Karar denetim izi
        audit = self._record_decision(
            task, decision, agent_name, selection_method,
        )

        # Aksiyona gore yonlendir
        result = await self._route_action(task, decision.action)

        # Sonucu denetim izine kaydet
        audit.outcome_success = result.success

        # Basarisiz ise eskalasyon (aktifse)
        if (
            not result.success
            and self.enable_escalation
            and decision.action in (ActionType.AUTO_FIX, ActionType.IMMEDIATE)
        ):
            result = await self._escalate(
                task, decision.action,
                task.get("target_agent"),
                result.message,
            )

        return result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Gelen veriyi analiz eder.

        Args:
            data: Analiz edilecek veri.

        Returns:
            Analiz sonuclari (risk, urgency, suggested_action).
        """
        # TODO: LLM ile derin analiz yapilacak
        analysis = {
            "risk": data.get("risk", "low"),
            "urgency": data.get("urgency", "low"),
            "suggested_action": "log",
            "summary": f"Analiz tamamlandi: {data.get('description', '')}",
        }
        self.logger.info("Analiz sonucu: %s", analysis["summary"])
        return analysis

    async def report(self, result: TaskResult) -> str:
        """Gorev sonucunu formatli rapor olarak dondurur.

        Args:
            result: Raporlanacak sonuc.

        Returns:
            Formatlanmis rapor metni.
        """
        status_emoji = "OK" if result.success else "HATA"
        report_text = (
            f"[{status_emoji}] ATLAS Rapor\n"
            f"Durum: {'Basarili' if result.success else 'Basarisiz'}\n"
            f"Mesaj: {result.message}\n"
            f"Zaman: {result.timestamp.isoformat()}\n"
        )
        if result.errors:
            report_text += f"Hatalar: {', '.join(result.errors)}\n"
        return report_text

    # === Aksiyon Yonlendirme ===

    async def _route_action(self, task: dict[str, Any], action: ActionType) -> TaskResult:
        """Aksiyona gore gorevi yonlendirir.

        Args:
            task: Gorev detaylari.
            action: Belirlenen aksiyon tipi.

        Returns:
            Yonlendirme sonucu.
        """
        self.logger.info("Yonlendirme: aksiyon=%s", action.value)

        if action == ActionType.LOG:
            return await self._handle_log(task)
        elif action == ActionType.NOTIFY:
            return await self._handle_notify(task)
        elif action == ActionType.AUTO_FIX:
            return await self._handle_auto_fix(task)
        elif action == ActionType.IMMEDIATE:
            return await self._handle_immediate(task)

        return TaskResult(success=False, message=f"Bilinmeyen aksiyon: {action}")

    async def _handle_log(self, task: dict[str, Any]) -> TaskResult:
        """Sadece kaydet aksiyonu."""
        self.logger.info("Gorev kaydedildi: %s", task.get("description", ""))
        return TaskResult(success=True, message="Gorev kaydedildi")

    async def _handle_notify(self, task: dict[str, Any]) -> TaskResult:
        """Bildirim gonder aksiyonu."""
        description = task.get("description", "")
        self.logger.info("Bildirim gonderilecek: %s", description)

        if self.telegram_bot:
            try:
                await self.telegram_bot.send_message(
                    f"ATLAS Bildirim:\n{description}",
                )
            except Exception as exc:
                self.logger.error("Telegram bildirim hatasi: %s", exc)

        return TaskResult(success=True, message="Bildirim gonderildi")

    async def _handle_auto_fix(self, task: dict[str, Any]) -> TaskResult:
        """Otomatik duzeltme aksiyonu.

        Hedef agent belirtilmemisse akilli secim ile agent atar.
        """
        target = task.get("target_agent")
        if target and target in self.agents:
            agent = self.agents[target]
            return await agent.run(task)

        # Otomatik secim dene
        auto_target = self.select_agent(task)
        if auto_target:
            self.logger.info("Otomatik secimle agent atandi: %s", auto_target)
            return await self.agents[auto_target].run(task)

        self.logger.warning("Hedef agent bulunamadi: %s", target)
        return TaskResult(
            success=False,
            message=f"Otomatik duzeltme icin agent bulunamadi: {target}",
        )

    async def _handle_immediate(self, task: dict[str, Any]) -> TaskResult:
        """Acil mudahale aksiyonu."""
        description = task.get("description", "")
        self.logger.critical("ACIL MUDAHALE: %s", description)

        if self.telegram_bot:
            try:
                await self.telegram_bot.send_buttons(
                    text=f"ACIL MUDAHALE GEREKIYOR:\n{description}",
                    buttons=[
                        {"text": "Onayla", "callback_data": "approve_immediate"},
                        {"text": "Reddet", "callback_data": "reject_immediate"},
                    ],
                )
            except Exception as exc:
                self.logger.error("Telegram acil bildirim hatasi: %s", exc)

        # Hedef agent varsa otomatik calistir
        target = task.get("target_agent")
        if target and target in self.agents:
            agent = self.agents[target]
            return await agent.run(task)

        return TaskResult(success=True, message="Acil mudahale baslatildi")

    # === Karar Denetim Izi ===

    def _record_decision(
        self,
        task: dict[str, Any],
        decision: Decision,
        agent_name: str | None,
        selection_method: str,
        escalated_from: str | None = None,
    ) -> DecisionAuditEntry:
        """Karar denetim izi kaydi olusturur.

        Args:
            task: Gorev detaylari.
            decision: Karar matrisi sonucu.
            agent_name: Secilen agent.
            selection_method: Agent secim yontemi (explicit/keyword/none).
            escalated_from: Eskalasyon kaynagi aksiyon (opsiyonel).

        Returns:
            Olusturulan denetim kaydi.
        """
        entry = DecisionAuditEntry(
            task_description=task.get("description", ""),
            risk=decision.risk.value,
            urgency=decision.urgency.value,
            action=decision.action.value,
            confidence=decision.confidence,
            reason=decision.reason,
            agent_selected=agent_name,
            agent_selection_method=selection_method,
            escalated_from=escalated_from,
        )

        self.decision_history.append(entry)

        # Gecmis boyutunu sinirla
        if len(self.decision_history) > self._max_history:
            self.decision_history = self.decision_history[-self._max_history:]

        return entry

    def get_decision_history(
        self,
        limit: int = 50,
        action_filter: str | None = None,
    ) -> list[DecisionAuditEntry]:
        """Karar gecmisini dondurur.

        Args:
            limit: Maks kayit sayisi.
            action_filter: Aksiyon tipi filtresi (opsiyonel).

        Returns:
            Filtrelenmis karar gecmisi.
        """
        history = self.decision_history
        if action_filter:
            history = [e for e in history if e.action == action_filter]
        return history[-limit:]

    # === Eskalasyon ===

    async def _escalate(
        self,
        task: dict[str, Any],
        original_action: ActionType,
        original_agent: str | None,
        error_message: str,
    ) -> TaskResult:
        """Basarisiz gorevi yukselterek yeniden dener.

        AUTO_FIX basarisiz -> IMMEDIATE'a yukselir.
        Agent basarisiz -> farkli agent veya bildirim.

        Args:
            task: Gorev detaylari.
            original_action: Orijinal aksiyon tipi.
            original_agent: Orijinal agent adi.
            error_message: Hata mesaji.

        Returns:
            Eskalasyon sonucu.
        """
        record = EscalationRecord(
            original_action=original_action.value,
            original_agent=original_agent,
            reason=error_message,
        )

        # AUTO_FIX -> IMMEDIATE eskalasyonu
        if original_action == ActionType.AUTO_FIX:
            record.escalated_action = ActionType.IMMEDIATE.value
            record.level = EscalationLevel.NOTIFY_HUMAN
            self.escalation_history.append(record)
            self.logger.warning(
                "Eskalasyon: AUTO_FIX -> IMMEDIATE (%s)", error_message[:100],
            )
            return await self._handle_immediate(task)

        # Alternatif agent deneme
        alt_agent = self._find_alternate_agent(task, original_agent)
        if alt_agent:
            record.escalated_agent = alt_agent
            record.escalated_action = original_action.value
            record.level = EscalationLevel.ALTERNATE_AGENT
            self.escalation_history.append(record)
            self.logger.warning(
                "Eskalasyon: agent degistiriliyor %s -> %s",
                original_agent, alt_agent,
            )
            return await self.agents[alt_agent].run(task)

        # Son care: bildir
        record.escalated_action = ActionType.NOTIFY.value
        record.level = EscalationLevel.NOTIFY_HUMAN
        self.escalation_history.append(record)
        self.logger.warning("Eskalasyon: insan mudahalesi gerekli")
        return await self._handle_notify(task)

    def _find_alternate_agent(
        self,
        task: dict[str, Any],
        exclude_agent: str | None,
    ) -> str | None:
        """Basarisiz agent disinda alternatif agent bulur.

        Args:
            task: Gorev detaylari.
            exclude_agent: Haric tutulacak agent adi.

        Returns:
            Alternatif agent adi veya None.
        """
        description = task.get("description", "").lower()
        for agent_type, keywords in AGENT_KEYWORDS.items():
            if any(kw in description for kw in keywords):
                for name in self.agents:
                    if name != exclude_agent and agent_type.lower() in name.lower():
                        return name
        return None

    # === Onay Is Akisi ===

    async def request_approval(
        self,
        task: dict[str, Any],
        action: ActionType,
        decision: Decision,
        timeout_seconds: int = 300,
        auto_execute: bool = False,
    ) -> ApprovalRequest:
        """Onay istegi olusturur ve gonderir.

        Args:
            task: Gorev detaylari.
            action: Onerilen aksiyon.
            decision: Iliskili karar.
            timeout_seconds: Zaman asimi suresi (saniye).
            auto_execute: Zaman asiminda otomatik calistir.

        Returns:
            Olusturulan onay istegi.
        """
        approval = ApprovalRequest(
            task=task,
            action=action.value,
            decision=DecisionCreate(
                risk=decision.risk.value,
                urgency=decision.urgency.value,
                action=decision.action.value,
                confidence=decision.confidence,
                reason=decision.reason,
            ),
            timeout_seconds=timeout_seconds,
            auto_execute_on_timeout=auto_execute,
        )

        self.pending_approvals[approval.id] = approval
        self.logger.info("Onay istegi olusturuldu: %s", approval.id[:8])

        # Telegram ile bildirim
        if self.telegram_bot:
            try:
                await self.telegram_bot.send_buttons(
                    text=(
                        f"ONAY BEKLENIYOR:\n"
                        f"{task.get('description', '')}\n"
                        f"Aksiyon: {action.value}\n"
                        f"Guven: {decision.confidence:.0%}"
                    ),
                    buttons=[
                        {"text": "Onayla", "callback_data": f"approve_{approval.id}"},
                        {"text": "Reddet", "callback_data": f"reject_{approval.id}"},
                    ],
                )
            except Exception as exc:
                self.logger.error("Onay bildirimi hatasi: %s", exc)

        return approval

    async def handle_approval_response(
        self,
        approval_id: str,
        approved: bool,
    ) -> TaskResult:
        """Onay yaniti isler.

        Args:
            approval_id: Onay istegi ID'si.
            approved: Onaylandi mi.

        Returns:
            Islem sonucu.
        """
        approval = self.pending_approvals.pop(approval_id, None)
        if approval is None:
            return TaskResult(
                success=False,
                message=f"Onay istegi bulunamadi: {approval_id}",
            )

        approval.responded_at = datetime.now(timezone.utc)

        if approved:
            approval.status = ApprovalStatus.APPROVED
            self.logger.info("Onay verildi: %s", approval_id[:8])
            return await self._route_action(
                approval.task, ActionType(approval.action),
            )
        else:
            approval.status = ApprovalStatus.REJECTED
            self.logger.info("Onay reddedildi: %s", approval_id[:8])
            return TaskResult(
                success=True,
                message=f"Gorev reddedildi: {approval.task.get('description', '')}",
            )

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Bekleyen onay isteklerini dondurur.

        Returns:
            Bekleyen onay istekleri listesi.
        """
        return list(self.pending_approvals.values())

    def get_registered_agents(self) -> list[dict[str, Any]]:
        """Kayitli agent'larin listesini dondurur.

        Returns:
            Agent bilgileri listesi.
        """
        return [agent.get_info() for agent in self.agents.values()]
