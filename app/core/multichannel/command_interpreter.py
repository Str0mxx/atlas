"""ATLAS Komut Yorumlayıcı modülü.

Çoklu format ayrıştırma, niyet çıkarma,
parametre yönetimi, belirsizlik çözümleme,
kısayol genişletme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CommandInterpreter:
    """Komut yorumlayıcı.

    Çeşitli formatlardaki komutları yorumlar.

    Attributes:
        _commands: Komut kayıtları.
        _shortcuts: Kısayol tanımları.
    """

    def __init__(self) -> None:
        """Yorumlayıcıyı başlatır."""
        self._commands: list[
            dict[str, Any]
        ] = []
        self._shortcuts: dict[str, str] = {
            "st": "status",
            "rpt": "report",
            "hlp": "help",
            "cfg": "config",
            "tsk": "task",
        }
        self._intents: dict[
            str, list[str]
        ] = {
            "query": [
                "what", "how", "when", "show",
                "get", "list", "find",
            ],
            "action": [
                "do", "run", "execute", "start",
                "stop", "create", "delete",
            ],
            "report": [
                "report", "summary", "stats",
                "analytics", "metrics",
            ],
            "config": [
                "set", "config", "configure",
                "setting", "change",
            ],
            "help": [
                "help", "?", "assist",
                "guide", "how to",
            ],
        }
        self._counter = 0
        self._stats = {
            "commands_parsed": 0,
            "shortcuts_used": 0,
            "ambiguities": 0,
        }

        logger.info(
            "CommandInterpreter baslatildi",
        )

    def parse(
        self,
        raw_input: str,
        channel: str = "telegram",
    ) -> dict[str, Any]:
        """Komut ayrıştırır.

        Args:
            raw_input: Ham girdi.
            channel: Kaynak kanal.

        Returns:
            Ayrıştırma bilgisi.
        """
        self._counter += 1
        cid = f"cmd_{self._counter}"

        # Kısayol genişletme
        expanded = self._expand_shortcuts(
            raw_input,
        )

        # Niyet çıkarma
        intent = self._extract_intent(expanded)

        # Parametre çıkarma
        params = self._extract_params(expanded)

        command = {
            "command_id": cid,
            "raw_input": raw_input,
            "expanded": expanded,
            "intent": intent,
            "params": params,
            "channel": channel,
            "timestamp": time.time(),
        }
        self._commands.append(command)
        self._stats["commands_parsed"] += 1

        return command

    def extract_intent(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Niyet çıkarır.

        Args:
            text: Metin.

        Returns:
            Niyet bilgisi.
        """
        intent = self._extract_intent(text)
        confidence = 0.9 if intent != "unknown" else 0.3

        # Birden fazla eşleşme = belirsizlik
        matches = []
        text_lower = text.lower()
        for intent_name, keywords in self._intents.items():
            for kw in keywords:
                if kw in text_lower:
                    if intent_name not in matches:
                        matches.append(
                            intent_name,
                        )
                    break

        ambiguous = len(matches) > 1
        if ambiguous:
            self._stats["ambiguities"] += 1
            confidence = 0.5

        return {
            "intent": intent,
            "confidence": confidence,
            "ambiguous": ambiguous,
            "alternatives": matches,
        }

    def _extract_intent(
        self,
        text: str,
    ) -> str:
        """İç niyet çıkarma.

        Args:
            text: Metin.

        Returns:
            Niyet adı.
        """
        text_lower = text.lower().strip()

        for intent_name, keywords in self._intents.items():
            for kw in keywords:
                if kw in text_lower:
                    return intent_name

        return "unknown"

    def _extract_params(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Parametre çıkarır.

        Args:
            text: Metin.

        Returns:
            Parametreler.
        """
        params: dict[str, Any] = {}
        parts = text.split()

        for i, part in enumerate(parts):
            if part.startswith("--"):
                key = part[2:]
                value: Any = True
                if (
                    i + 1 < len(parts)
                    and not parts[i + 1].startswith("--")
                ):
                    value = parts[i + 1]
                params[key] = value
            elif "=" in part:
                k, _, v = part.partition("=")
                params[k] = v

        return params

    def _expand_shortcuts(
        self,
        text: str,
    ) -> str:
        """Kısayolları genişletir.

        Args:
            text: Metin.

        Returns:
            Genişletilmiş metin.
        """
        words = text.split()
        expanded = []
        used = False

        for word in words:
            lower = word.lower()
            if lower in self._shortcuts:
                expanded.append(
                    self._shortcuts[lower],
                )
                used = True
            else:
                expanded.append(word)

        if used:
            self._stats["shortcuts_used"] += 1

        return " ".join(expanded)

    def add_shortcut(
        self,
        shortcut: str,
        expansion: str,
    ) -> dict[str, Any]:
        """Kısayol ekler.

        Args:
            shortcut: Kısayol.
            expansion: Genişletme.

        Returns:
            Ekleme bilgisi.
        """
        self._shortcuts[shortcut.lower()] = (
            expansion
        )
        return {
            "shortcut": shortcut,
            "expansion": expansion,
            "added": True,
        }

    def resolve_ambiguity(
        self,
        command_id: str,
        chosen_intent: str,
    ) -> dict[str, Any]:
        """Belirsizlik çözümler.

        Args:
            command_id: Komut ID.
            chosen_intent: Seçilen niyet.

        Returns:
            Çözüm bilgisi.
        """
        for cmd in self._commands:
            if cmd["command_id"] == command_id:
                cmd["intent"] = chosen_intent
                cmd["resolved"] = True
                return {
                    "command_id": command_id,
                    "intent": chosen_intent,
                    "resolved": True,
                }
        return {"error": "command_not_found"}

    def get_commands(
        self,
        intent: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Komutları getirir.

        Args:
            intent: Niyet filtresi.
            limit: Maks kayıt.

        Returns:
            Komut listesi.
        """
        results = self._commands
        if intent:
            results = [
                c for c in results
                if c.get("intent") == intent
            ]
        return list(results[-limit:])

    @property
    def command_count(self) -> int:
        """Komut sayısı."""
        return self._stats["commands_parsed"]

    @property
    def shortcut_count(self) -> int:
        """Kısayol sayısı."""
        return len(self._shortcuts)
