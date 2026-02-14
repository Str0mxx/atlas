"""ATLAS Komut Zinciri modulu.

Yukaridan-asagi komut yayilimi, asagidan-yukari geri bildirim,
yayin komutlari, hedefli komutlar ve acil komutlar.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    CommandMessage,
    CommandType,
)

logger = logging.getLogger(__name__)


class CommandChain:
    """Komut zinciri sistemi.

    Hiyerarsi boyunca komut ve geri bildirim
    yayilimini yonetir.

    Attributes:
        _commands: Komut gecmisi.
        _pending: Bekleyen komutlar.
        _agent_inbox: Agent gelen kutusu.
    """

    def __init__(self) -> None:
        """Komut zincirini baslatir."""
        self._commands: list[CommandMessage] = []
        self._pending: dict[str, CommandMessage] = {}
        self._agent_inbox: dict[str, list[CommandMessage]] = {}

        logger.info("CommandChain baslatildi")

    def send_directive(
        self,
        from_agent: str,
        to_agents: list[str],
        content: str,
        priority: int = 5,
    ) -> CommandMessage:
        """Direktif komut gonderir (yukaridan asagi).

        Args:
            from_agent: Gonderen agent.
            to_agents: Hedef agent'lar.
            content: Komut icerigi.
            priority: Oncelik.

        Returns:
            CommandMessage nesnesi.
        """
        cmd = CommandMessage(
            command_type=CommandType.DIRECTIVE,
            from_agent=from_agent,
            to_agents=to_agents,
            content=content,
            priority=min(max(priority, 1), 10),
        )

        self._deliver(cmd)
        return cmd

    def send_broadcast(
        self,
        from_agent: str,
        content: str,
        all_agents: list[str] | None = None,
        priority: int = 5,
    ) -> CommandMessage:
        """Yayin komutu gonderir (tum agent'lara).

        Args:
            from_agent: Gonderen agent.
            content: Komut icerigi.
            all_agents: Tum agent ID listesi.
            priority: Oncelik.

        Returns:
            CommandMessage nesnesi.
        """
        targets = all_agents or []

        cmd = CommandMessage(
            command_type=CommandType.BROADCAST,
            from_agent=from_agent,
            to_agents=targets,
            content=content,
            priority=min(max(priority, 1), 10),
        )

        self._deliver(cmd)
        return cmd

    def send_targeted(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        priority: int = 5,
    ) -> CommandMessage:
        """Hedefli komut gonderir (tek agent).

        Args:
            from_agent: Gonderen agent.
            to_agent: Hedef agent.
            content: Komut icerigi.
            priority: Oncelik.

        Returns:
            CommandMessage nesnesi.
        """
        cmd = CommandMessage(
            command_type=CommandType.TARGETED,
            from_agent=from_agent,
            to_agents=[to_agent],
            content=content,
            priority=min(max(priority, 1), 10),
        )

        self._deliver(cmd)
        return cmd

    def send_emergency(
        self,
        from_agent: str,
        content: str,
        all_agents: list[str] | None = None,
    ) -> CommandMessage:
        """Acil komut gonderir (en yuksek oncelik).

        Args:
            from_agent: Gonderen agent.
            content: Acil icerik.
            all_agents: Tum agent ID listesi.

        Returns:
            CommandMessage nesnesi.
        """
        targets = all_agents or []

        cmd = CommandMessage(
            command_type=CommandType.EMERGENCY,
            from_agent=from_agent,
            to_agents=targets,
            content=content,
            priority=10,
        )

        self._deliver(cmd)
        logger.warning("ACIL KOMUT: %s -> %s", from_agent, content)
        return cmd

    def send_feedback(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
    ) -> CommandMessage:
        """Geri bildirim gonderir (asagidan yukari).

        Args:
            from_agent: Gonderen agent.
            to_agent: Hedef agent (ust).
            content: Geri bildirim.

        Returns:
            CommandMessage nesnesi.
        """
        cmd = CommandMessage(
            command_type=CommandType.FEEDBACK,
            from_agent=from_agent,
            to_agents=[to_agent],
            content=content,
            priority=3,
        )

        self._deliver(cmd)
        return cmd

    def acknowledge(
        self, command_id: str, agent_id: str,
    ) -> bool:
        """Komutu onaylar.

        Args:
            command_id: Komut ID.
            agent_id: Onaylayan agent.

        Returns:
            Basarili ise True.
        """
        cmd = self._pending.get(command_id)
        if not cmd:
            # Gecmiste ara
            for c in self._commands:
                if c.command_id == command_id:
                    cmd = c
                    break

        if not cmd:
            return False

        if agent_id not in cmd.acknowledged_by:
            cmd.acknowledged_by.append(agent_id)

        # Tum hedefler onaylediysa pending'den kaldir
        if set(cmd.to_agents).issubset(set(cmd.acknowledged_by)):
            self._pending.pop(command_id, None)

        return True

    def get_inbox(self, agent_id: str) -> list[CommandMessage]:
        """Agent gelen kutusunu getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            CommandMessage listesi (oncelik sirasinda).
        """
        messages = self._agent_inbox.get(agent_id, [])
        return sorted(messages, key=lambda m: m.priority, reverse=True)

    def get_pending(self) -> list[CommandMessage]:
        """Bekleyen komutlari getirir.

        Returns:
            CommandMessage listesi.
        """
        return list(self._pending.values())

    def get_command(self, command_id: str) -> CommandMessage | None:
        """Komut getirir.

        Args:
            command_id: Komut ID.

        Returns:
            CommandMessage veya None.
        """
        for c in self._commands:
            if c.command_id == command_id:
                return c
        return None

    def is_fully_acknowledged(self, command_id: str) -> bool:
        """Komut tam olarak onaylandi mi.

        Args:
            command_id: Komut ID.

        Returns:
            Tum hedefler onaylediysa True.
        """
        cmd = self.get_command(command_id)
        if not cmd:
            return False
        return set(cmd.to_agents).issubset(set(cmd.acknowledged_by))

    def _deliver(self, cmd: CommandMessage) -> None:
        """Komutu dagitir."""
        self._commands.append(cmd)
        self._pending[cmd.command_id] = cmd

        for agent_id in cmd.to_agents:
            if agent_id not in self._agent_inbox:
                self._agent_inbox[agent_id] = []
            self._agent_inbox[agent_id].append(cmd)

    @property
    def total_commands(self) -> int:
        """Toplam komut sayisi."""
        return len(self._commands)

    @property
    def pending_count(self) -> int:
        """Bekleyen komut sayisi."""
        return len(self._pending)

    @property
    def emergency_count(self) -> int:
        """Acil komut sayisi."""
        return sum(
            1 for c in self._commands
            if c.command_type == CommandType.EMERGENCY
        )
