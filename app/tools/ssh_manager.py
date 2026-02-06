"""SSH baglanti yonetici modulu.

Paramiko uzerinden async SSH baglantisi saglar.
asyncio.to_thread() ile non-blocking calisir.
"""

import asyncio
import logging
from pathlib import Path
from types import TracebackType

import paramiko

logger = logging.getLogger("atlas.tools.ssh_manager")


class SSHManager:
    """Async SSH baglanti yoneticisi.

    Paramiko'yu asyncio.to_thread() ile sarimlayarak
    non-blocking SSH islemleri saglar.

    Kullanim:
        async with SSHManager(host, user, key_path) as ssh:
            stdout, stderr, code = await ssh.execute_command("uptime")
    """

    def __init__(
        self,
        host: str,
        user: str = "root",
        key_path: str = "~/.ssh/id_rsa",
        port: int = 22,
        timeout: int = 10,
    ) -> None:
        """SSH yoneticisini baslatir.

        Args:
            host: Sunucu adresi.
            user: SSH kullanici adi.
            key_path: SSH ozel anahtar dosya yolu.
            port: SSH port numarasi.
            timeout: Baglanti zaman asimi (saniye).
        """
        self.host = host
        self.user = user
        self.key_path = str(Path(key_path).expanduser())
        self.port = port
        self.timeout = timeout
        self._client: paramiko.SSHClient | None = None

    async def connect(self) -> None:
        """SSH baglantisini kurar (async)."""
        await asyncio.to_thread(self._connect_sync)
        logger.info("SSH baglantisi kuruldu: %s@%s:%d", self.user, self.host, self.port)

    def _connect_sync(self) -> None:
        """SSH baglantisini kurar (sync - thread icinde calisir)."""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            key_filename=self.key_path,
            timeout=self.timeout,
        )

    async def execute_command(self, command: str) -> tuple[str, str, int]:
        """Uzak sunucuda komut calistirir.

        Args:
            command: Calistirilacak shell komutu.

        Returns:
            (stdout, stderr, exit_code) tuple.

        Raises:
            RuntimeError: SSH baglantisi kurulmamissa.
        """
        if self._client is None:
            raise RuntimeError("SSH baglantisi kurulmamis. Once connect() cagiriniz.")

        return await asyncio.to_thread(self._execute_sync, command)

    def _execute_sync(self, command: str) -> tuple[str, str, int]:
        """Komutu sync olarak calistirir (thread icinde)."""
        assert self._client is not None
        _, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)
        exit_code = stdout.channel.recv_exit_status()
        return (
            stdout.read().decode("utf-8", errors="replace").strip(),
            stderr.read().decode("utf-8", errors="replace").strip(),
            exit_code,
        )

    async def close(self) -> None:
        """SSH baglantisini kapatir."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("SSH baglantisi kapatildi: %s", self.host)

    async def __aenter__(self) -> "SSHManager":
        """Context manager giris - baglanti kurar."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager cikis - baglanti kapatir."""
        await self.close()
