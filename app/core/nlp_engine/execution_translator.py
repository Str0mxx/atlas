"""ATLAS Calistirma Cevirici modulu.

Dogal dilden agent komutlarina, API cagrilarina,
veritabani sorgularina ve shell komutlarina ceviri.
Guvenlik dogrulamasi dahil.
"""

import logging
import re
from typing import Any

from app.models.nlp_engine import (
    CommandType,
    Intent,
    IntentCategory,
    SafetyLevel,
    TranslatedCommand,
)

logger = logging.getLogger(__name__)

# Tehlikeli komut kaliplari
_DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdrop\s+database\b",
    r"\bdrop\s+table\b",
    r"\bdelete\s+from\s+\w+\s*$",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\s+-9\b",
    r"\btruncate\b",
]

# Dikkat gerektiren kaliplar
_CAUTION_PATTERNS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\bstop\b",
    r"\brestart\b",
    r"\bupdate\b.*\bwhere\b",
    r"\balter\b",
    r"\bdeploy\b",
    r"\bpush\b",
]

# Agent tip esleme
_AGENT_TYPE_MAP: dict[str, str] = {
    "sunucu": "server_monitor",
    "server": "server_monitor",
    "guvenlik": "security",
    "security": "security",
    "arastirma": "research",
    "research": "research",
    "analiz": "analysis",
    "analysis": "analysis",
    "email": "communication",
    "eposta": "communication",
    "kod": "coding",
    "code": "coding",
    "reklam": "marketing",
    "marketing": "marketing",
    "ads": "marketing",
    "icerik": "creative",
    "creative": "creative",
    "ses": "voice",
    "voice": "voice",
}


class ExecutionTranslator:
    """Calistirma cevirici.

    Dogal dil komutlarini agent komutlarina, API cagrilarina,
    veritabani sorgularina ve shell komutlarina cevirir.
    Her ceviri icin guvenlik dogrulamasi yapar.

    Attributes:
        _translations: Ceviri gecmisi (id -> TranslatedCommand).
        _execution_confirmation: Onay gerektiriyor mu.
    """

    def __init__(self, execution_confirmation: bool = True) -> None:
        """Calistirma ceviriciyi baslatir.

        Args:
            execution_confirmation: Tehlikeli komutlar icin onay iste.
        """
        self._translations: dict[str, TranslatedCommand] = {}
        self._execution_confirmation = execution_confirmation

        logger.info("ExecutionTranslator baslatildi (confirmation=%s)", execution_confirmation)

    def translate(self, text: str, intent: Intent | None = None) -> TranslatedCommand:
        """Dogal dil komutunu calitirilabilir komuta cevirir.

        Args:
            text: Dogal dil komutu.
            intent: Onceden analiz edilmis niyet.

        Returns:
            TranslatedCommand nesnesi.
        """
        command_type = self._detect_command_type(text, intent)
        command, parameters = self._build_command(text, command_type, intent)
        safety_level, safety_reason = self._validate_safety(command, command_type)

        requires_confirmation = (
            self._execution_confirmation and safety_level in (SafetyLevel.CAUTION, SafetyLevel.DANGEROUS)
        )

        translated = TranslatedCommand(
            original_text=text,
            command_type=command_type,
            command=command,
            parameters=parameters,
            safety_level=safety_level,
            safety_reason=safety_reason,
            requires_confirmation=requires_confirmation,
        )
        self._translations[translated.id] = translated

        logger.info(
            "Komut cevrildi: tip=%s, guvenlik=%s, onay=%s",
            command_type.value, safety_level.value, requires_confirmation,
        )
        return translated

    def translate_to_agent(self, text: str, intent: Intent | None = None) -> TranslatedCommand:
        """Agent komutuna cevirir.

        Args:
            text: Dogal dil komutu.
            intent: Onceden analiz edilmis niyet.

        Returns:
            Agent komutu.
        """
        agent_type = self._detect_agent_type(text)
        action = self._extract_action(text, intent)

        command = f"agent:{agent_type}:{action}" if agent_type else f"agent:master:{action}"
        translated = TranslatedCommand(
            original_text=text,
            command_type=CommandType.AGENT_COMMAND,
            command=command,
            parameters={"agent_type": agent_type, "action": action},
            safety_level=SafetyLevel.SAFE,
        )
        self._translations[translated.id] = translated
        return translated

    def translate_to_api(self, text: str, intent: Intent | None = None) -> TranslatedCommand:
        """API cagrisina cevirir.

        Args:
            text: Dogal dil komutu.
            intent: Onceden analiz edilmis niyet.

        Returns:
            API komutu.
        """
        method, path = self._infer_api_call(text, intent)
        safety_level = SafetyLevel.SAFE
        if method in ("DELETE", "PUT", "PATCH"):
            safety_level = SafetyLevel.CAUTION

        translated = TranslatedCommand(
            original_text=text,
            command_type=CommandType.API_CALL,
            command=f"{method} {path}",
            parameters={"method": method, "path": path},
            safety_level=safety_level,
            requires_confirmation=method == "DELETE" and self._execution_confirmation,
        )
        self._translations[translated.id] = translated
        return translated

    def translate_to_query(self, text: str) -> TranslatedCommand:
        """Veritabani sorgusuna cevirir.

        Args:
            text: Dogal dil komutu.

        Returns:
            Veritabani komutu.
        """
        query = self._build_query(text)
        safety_level, safety_reason = self._validate_safety(query, CommandType.DB_QUERY)

        translated = TranslatedCommand(
            original_text=text,
            command_type=CommandType.DB_QUERY,
            command=query,
            parameters={"query": query},
            safety_level=safety_level,
            safety_reason=safety_reason,
            requires_confirmation=safety_level != SafetyLevel.SAFE,
        )
        self._translations[translated.id] = translated
        return translated

    def translate_to_shell(self, text: str) -> TranslatedCommand:
        """Shell komutuna cevirir.

        Args:
            text: Dogal dil komutu.

        Returns:
            Shell komutu.
        """
        command = self._build_shell_command(text)
        safety_level, safety_reason = self._validate_safety(command, CommandType.SHELL_COMMAND)

        translated = TranslatedCommand(
            original_text=text,
            command_type=CommandType.SHELL_COMMAND,
            command=command,
            parameters={"shell": command},
            safety_level=safety_level,
            safety_reason=safety_reason,
            requires_confirmation=safety_level != SafetyLevel.SAFE,
        )
        self._translations[translated.id] = translated
        return translated

    def _detect_command_type(self, text: str, intent: Intent | None) -> CommandType:
        """Komut tipini tespit eder.

        Args:
            text: Metin.
            intent: Niyet.

        Returns:
            Komut tipi.
        """
        lower = text.lower()

        # Agent komutlari
        agent_words = ["agent", "ajan", "monitor", "izle"]
        if any(w in lower for w in agent_words):
            return CommandType.AGENT_COMMAND

        # DB komutlari
        db_words = ["veritabani", "database", "sorgu", "query", "tablo", "table", "kayit", "record"]
        if any(w in lower for w in db_words):
            return CommandType.DB_QUERY

        # Shell komutlari
        shell_words = ["terminal", "shell", "komut", "calistir", "run", "deploy", "restart"]
        if any(w in lower for w in shell_words):
            return CommandType.SHELL_COMMAND

        # API komutlari
        api_words = ["api", "endpoint", "istek", "request", "gonder", "send"]
        if any(w in lower for w in api_words):
            return CommandType.API_CALL

        # Niyet bazli
        if intent:
            if intent.category in (IntentCategory.EXECUTE, IntentCategory.CONFIGURE):
                return CommandType.SYSTEM_ACTION
            if intent.category == IntentCategory.QUERY:
                return CommandType.DB_QUERY

        return CommandType.SYSTEM_ACTION

    def _build_command(self, text: str, cmd_type: CommandType, intent: Intent | None) -> tuple[str, dict[str, Any]]:
        """Komut ve parametreleri olusturur.

        Args:
            text: Metin.
            cmd_type: Komut tipi.
            intent: Niyet.

        Returns:
            (komut, parametreler) ciftci.
        """
        action = self._extract_action(text, intent)

        if cmd_type == CommandType.AGENT_COMMAND:
            agent = self._detect_agent_type(text)
            return f"agent:{agent or 'master'}:{action}", {"agent": agent, "action": action}
        elif cmd_type == CommandType.DB_QUERY:
            query = self._build_query(text)
            return query, {"query": query}
        elif cmd_type == CommandType.SHELL_COMMAND:
            shell = self._build_shell_command(text)
            return shell, {"shell": shell}
        elif cmd_type == CommandType.API_CALL:
            method, path = self._infer_api_call(text, intent)
            return f"{method} {path}", {"method": method, "path": path}
        else:
            return f"system:{action}", {"action": action}

    def _detect_agent_type(self, text: str) -> str:
        """Agent tipini tespit eder.

        Args:
            text: Metin.

        Returns:
            Agent tipi veya bos string.
        """
        lower = text.lower()
        for keyword, agent_type in _AGENT_TYPE_MAP.items():
            if keyword in lower:
                return agent_type
        return ""

    def _extract_action(self, text: str, intent: Intent | None) -> str:
        """Eylemi cikarir.

        Args:
            text: Metin.
            intent: Niyet.

        Returns:
            Eylem metni.
        """
        if intent and intent.action:
            return intent.action
        # Ilk fiili kullan
        words = text.lower().split()
        return words[0] if words else "execute"

    def _infer_api_call(self, text: str, intent: Intent | None) -> tuple[str, str]:
        """API cagrisini cikarir.

        Args:
            text: Metin.
            intent: Niyet.

        Returns:
            (HTTP metodu, yol) cifti.
        """
        lower = text.lower()

        if intent:
            method_map = {
                IntentCategory.CREATE: "POST",
                IntentCategory.QUERY: "GET",
                IntentCategory.MODIFY: "PUT",
                IntentCategory.DELETE: "DELETE",
            }
            method = method_map.get(intent.category, "GET")
        else:
            method = "GET"

        # Kaynak adini bul
        resource = "resource"
        for word in text.split():
            if len(word) > 3 and word.lower() not in ("olustur", "goster", "sil", "guncelle", "api", "endpoint"):
                resource = word.lower()
                break

        return method, f"/api/{resource}"

    def _build_query(self, text: str) -> str:
        """Veritabani sorgusu olusturur.

        Args:
            text: Metin.

        Returns:
            SQL-benzeri sorgu.
        """
        lower = text.lower()

        if any(w in lower for w in ["goster", "listele", "getir", "show", "list", "get"]):
            return f"SELECT * FROM data WHERE context='{text[:30]}'"
        elif any(w in lower for w in ["ekle", "olustur", "create", "add", "insert"]):
            return f"INSERT INTO data (description) VALUES ('{text[:30]}')"
        elif any(w in lower for w in ["sil", "kaldir", "delete", "remove"]):
            return f"DELETE FROM data WHERE description LIKE '%{text[:20]}%'"
        elif any(w in lower for w in ["guncelle", "degistir", "update", "modify"]):
            return f"UPDATE data SET description='{text[:30]}'"
        else:
            return f"SELECT * FROM data WHERE description LIKE '%{text[:20]}%'"

    def _build_shell_command(self, text: str) -> str:
        """Shell komutu olusturur.

        Args:
            text: Metin.

        Returns:
            Shell komutu.
        """
        lower = text.lower()

        if any(w in lower for w in ["restart", "yeniden baslat"]):
            return "systemctl restart atlas"
        elif any(w in lower for w in ["durum", "status"]):
            return "systemctl status atlas"
        elif any(w in lower for w in ["log", "gunluk"]):
            return "journalctl -u atlas --no-pager -n 50"
        elif any(w in lower for w in ["deploy", "yayinla"]):
            return "docker-compose up -d --build"
        else:
            return f"echo 'NL komut: {text[:40]}'"

    def _validate_safety(self, command: str, cmd_type: CommandType) -> tuple[SafetyLevel, str]:
        """Komut guvenligini dogrular.

        Args:
            command: Komut metni.
            cmd_type: Komut tipi.

        Returns:
            (guvenlik seviyesi, gerekce) cifti.
        """
        lower = command.lower()

        # Tehlikeli kaliplar
        for pattern in _DANGEROUS_PATTERNS:
            if re.search(pattern, lower):
                return SafetyLevel.DANGEROUS, f"Tehlikeli komut tespit edildi: {pattern}"

        # Dikkat gerektiren kaliplar
        for pattern in _CAUTION_PATTERNS:
            if re.search(pattern, lower):
                return SafetyLevel.CAUTION, f"Dikkat gerektiren komut: {pattern}"

        return SafetyLevel.SAFE, ""

    def get_translation(self, translation_id: str) -> TranslatedCommand | None:
        """Ceviri kaydini getirir.

        Args:
            translation_id: Ceviri ID.

        Returns:
            TranslatedCommand nesnesi veya None.
        """
        return self._translations.get(translation_id)

    @property
    def translation_count(self) -> int:
        """Toplam ceviri sayisi."""
        return len(self._translations)
