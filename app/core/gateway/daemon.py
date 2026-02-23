"""Gateway daemon yoneticisi.

Platform spesifik daemon islemleri,
TMPDIR yonlendirme ve Node.js tespiti.
"""

import logging
import os
import shutil
import sys
import tempfile

logger = logging.getLogger(__name__)


class GatewayDaemon:
    """Gateway daemon yoneticisi.

    Attributes:
        _pid_file: PID dosya yolu.
        _running: Calisma durumu.
    """

    def __init__(
        self,
        pid_file: str = "",
    ) -> None:
        """GatewayDaemon baslatir."""
        self._pid_file = pid_file or os.path.join(
            tempfile.gettempdir(),
            "atlas_gateway.pid",
        )
        self._running = False
        self._pid: int = 0

    def forward_tmpdir(self) -> str:
        """macOS LaunchAgent icin TMPDIR yonlendirir.

        macOS'ta SQLite icin gecici dizini
        ayarlar.

        Returns:
            Gecici dizin yolu.
        """
        if sys.platform == "darwin":
            tmpdir = os.environ.get(
                "TMPDIR",
                "/tmp",
            )
            if not os.path.isdir(tmpdir):
                tmpdir = "/tmp"
            os.environ["TMPDIR"] = tmpdir
            return tmpdir

        return tempfile.gettempdir()

    @staticmethod
    def prefer_active_node() -> str:
        """Aktif Node.js surum yoneticisini tercih eder.

        nvm, volta, fnm sirasiyla kontrol eder.

        Returns:
            Node.js calistirilabilir yolu veya bos.
        """
        managers = [
            ("volta", "VOLTA_HOME"),
            ("fnm", "FNM_DIR"),
            ("nvm", "NVM_DIR"),
        ]

        for name, env_var in managers:
            env_path = os.environ.get(env_var, "")
            if env_path and os.path.isdir(env_path):
                logger.debug(
                    "%s tespit edildi: %s",
                    name,
                    env_path,
                )
                return name

        node_path = shutil.which("node")
        if node_path:
            return node_path

        return ""

    def start(self) -> bool:
        """Daemon'u baslatir.

        Returns:
            Basarili ise True.
        """
        if self._running:
            return False

        self._running = True
        self._pid = os.getpid()

        try:
            with open(
                self._pid_file, "w",
            ) as f:
                f.write(str(self._pid))
        except OSError as e:
            logger.error(
                "PID dosyasi yazilamadi: %s", e,
            )

        logger.info("Gateway daemon baslatildi")
        return True

    def stop(self) -> bool:
        """Daemon'u durdurur.

        Returns:
            Basarili ise True.
        """
        if not self._running:
            return False

        self._running = False
        self._pid = 0

        try:
            if os.path.isfile(self._pid_file):
                os.remove(self._pid_file)
        except OSError:
            pass

        logger.info("Gateway daemon durduruldu")
        return True

    def status(self) -> dict:
        """Daemon durumunu dondurur.

        Returns:
            Durum bilgisi.
        """
        return {
            "running": self._running,
            "pid": self._pid,
            "pid_file": self._pid_file,
            "platform": sys.platform,
            "node": self.prefer_active_node(),
        }
