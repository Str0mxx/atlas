"""ATLAS Komut Örüntüsü Öğrenici modülü.

Örüntü çıkarma, frekans analizi,
sekans öğrenme, kısayol tespiti,
takma ad oluşturma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CommandPatternLearner:
    """Komut örüntüsü öğrenici.

    Kullanıcı komut kalıplarını öğrenir.

    Attributes:
        _patterns: Örüntü kayıtları.
        _commands: Komut geçmişi.
    """

    def __init__(
        self,
        min_frequency: int = 3,
    ) -> None:
        """Öğreniciyi başlatır.

        Args:
            min_frequency: Min frekans eşiği.
        """
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._commands: list[
            dict[str, Any]
        ] = []
        self._aliases: dict[str, str] = {}
        self._sequences: list[
            dict[str, Any]
        ] = []
        self._min_frequency = min_frequency
        self._counter = 0
        self._stats = {
            "patterns_detected": 0,
            "sequences_learned": 0,
            "aliases_created": 0,
        }

        logger.info(
            "CommandPatternLearner "
            "baslatildi",
        )

    def record_command(
        self,
        command: str,
        context: str = "",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Komutu kaydeder.

        Args:
            command: Komut.
            context: Bağlam.
            params: Parametreler.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        cid = f"cmd_{self._counter}"

        record = {
            "command_id": cid,
            "command": command,
            "context": context,
            "params": params or {},
            "timestamp": time.time(),
        }
        self._commands.append(record)

        return {
            "command_id": cid,
            "command": command,
            "recorded": True,
        }

    def extract_patterns(
        self,
    ) -> dict[str, Any]:
        """Örüntüleri çıkarır.

        Returns:
            Örüntü bilgisi.
        """
        # Frekans analizi
        freq: dict[str, int] = {}
        for cmd in self._commands:
            c = cmd["command"]
            freq[c] = freq.get(c, 0) + 1

        # Min frekans üzeri örüntüler
        new_patterns = 0
        for command, count in freq.items():
            if count >= self._min_frequency:
                pid = f"pat_{command[:20]}"
                if pid not in self._patterns:
                    self._patterns[pid] = {
                        "pattern_id": pid,
                        "command": command,
                        "frequency": count,
                        "type": "command",
                        "detected_at": (
                            time.time()
                        ),
                    }
                    new_patterns += 1
                    self._stats[
                        "patterns_detected"
                    ] += 1
                else:
                    self._patterns[pid][
                        "frequency"
                    ] = count

        return {
            "total_commands": len(
                self._commands,
            ),
            "patterns_found": len(
                self._patterns,
            ),
            "new_patterns": new_patterns,
        }

    def analyze_frequency(
        self,
    ) -> dict[str, Any]:
        """Frekans analizi yapar.

        Returns:
            Frekans bilgisi.
        """
        freq: dict[str, int] = {}
        for cmd in self._commands:
            c = cmd["command"]
            freq[c] = freq.get(c, 0) + 1

        sorted_freq = sorted(
            freq.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "unique_commands": len(freq),
            "total_commands": len(
                self._commands,
            ),
            "top_commands": dict(
                sorted_freq[:10],
            ),
            "most_used": (
                sorted_freq[0][0]
                if sorted_freq
                else None
            ),
        }

    def learn_sequences(
        self,
        window_size: int = 3,
    ) -> dict[str, Any]:
        """Sekans öğrenir.

        Args:
            window_size: Pencere boyutu.

        Returns:
            Sekans bilgisi.
        """
        if len(self._commands) < window_size:
            return {
                "sequences": [],
                "count": 0,
            }

        seq_freq: dict[str, int] = {}
        for i in range(
            len(self._commands)
            - window_size + 1
        ):
            window = self._commands[
                i: i + window_size
            ]
            seq_key = " -> ".join(
                c["command"] for c in window
            )
            seq_freq[seq_key] = (
                seq_freq.get(seq_key, 0) + 1
            )

        # Tekrarlayan sekanslar
        learned = []
        for seq, count in seq_freq.items():
            if count >= 2:
                learned.append({
                    "sequence": seq,
                    "frequency": count,
                })

        self._sequences = learned
        self._stats[
            "sequences_learned"
        ] = len(learned)

        return {
            "sequences": learned,
            "count": len(learned),
        }

    def detect_shortcuts(
        self,
    ) -> dict[str, Any]:
        """Kısayol tespit eder.

        Returns:
            Kısayol bilgisi.
        """
        shortcuts = []
        freq = self.analyze_frequency()
        top = freq.get("top_commands", {})

        for cmd, count in top.items():
            if count >= self._min_frequency:
                # Kısa versiyon öner
                words = cmd.split()
                if len(words) > 1:
                    shortcut = "".join(
                        w[0] for w in words
                    )
                    shortcuts.append({
                        "command": cmd,
                        "shortcut": shortcut,
                        "frequency": count,
                    })

        return {
            "shortcuts": shortcuts,
            "count": len(shortcuts),
        }

    def create_alias(
        self,
        alias: str,
        command: str,
    ) -> dict[str, Any]:
        """Takma ad oluşturur.

        Args:
            alias: Takma ad.
            command: Komut.

        Returns:
            Oluşturma bilgisi.
        """
        self._aliases[alias] = command
        self._stats["aliases_created"] += 1

        return {
            "alias": alias,
            "command": command,
            "created": True,
            "total_aliases": len(
                self._aliases,
            ),
        }

    def resolve_alias(
        self,
        alias: str,
    ) -> dict[str, Any]:
        """Takma adı çözer.

        Args:
            alias: Takma ad.

        Returns:
            Çözüm bilgisi.
        """
        command = self._aliases.get(alias)
        if not command:
            return {
                "error": "alias_not_found",
            }
        return {
            "alias": alias,
            "command": command,
            "resolved": True,
        }

    def get_patterns(
        self,
        pattern_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Örüntüleri getirir."""
        results = list(
            self._patterns.values(),
        )
        if pattern_type:
            results = [
                p for p in results
                if p["type"] == pattern_type
            ]
        return results

    @property
    def pattern_count(self) -> int:
        """Örüntü sayısı."""
        return len(self._patterns)

    @property
    def alias_count(self) -> int:
        """Takma ad sayısı."""
        return len(self._aliases)

    @property
    def command_count(self) -> int:
        """Komut sayısı."""
        return len(self._commands)
