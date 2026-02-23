"""Gateway eslestirme yoneticisi.

Cihaz eslestirme, wildcard yetki
ve kapsam koruma islemleri.
"""

import logging
import time

from app.models.gateway_models import PairedDevice

logger = logging.getLogger(__name__)


class GatewayPairingManager:
    """Gateway cihaz eslestirme yoneticisi.

    Attributes:
        _paired_devices: Eslesmis cihazlar.
    """

    def __init__(self) -> None:
        """GatewayPairingManager baslatir."""
        self._paired_devices: dict[
            str, PairedDevice
        ] = {}

    @staticmethod
    def check_operator_scope(
        required: str,
        granted: str,
    ) -> bool:
        """Operator kapsamini kontrol eder.

        operator.admin, operator.* kapsamini karsilar.
        Wildcard eslestirme destekler.

        Args:
            required: Gereken kapsam.
            granted: Verilen kapsam.

        Returns:
            Kapsam yeterli ise True.
        """
        if granted == required:
            return True

        if granted.endswith(".*"):
            prefix = granted[:-2]
            if required.startswith(prefix):
                return True

        if required.endswith(".*"):
            prefix = required[:-2]
            if granted.startswith(prefix):
                parts = granted[len(prefix):]
                if parts.startswith("."):
                    return True

        return False

    def preserve_scopes_on_repair(
        self,
        device_id: str,
    ) -> list[str]:
        """Onarim sirasinda mevcut kapsamlari korur.

        Args:
            device_id: Cihaz tanimlayici.

        Returns:
            Korunan kapsam listesi.
        """
        device = self._paired_devices.get(
            device_id,
        )
        if device:
            return list(device.scopes)
        return []

    def pair_device(
        self,
        device_id: str,
        token: str,
        scopes: list[str] | None = None,
    ) -> bool:
        """Cihaz eslestirir.

        Args:
            device_id: Cihaz tanimlayici.
            token: Auth jetonu.
            scopes: Yetki kapsamlari.

        Returns:
            Basarili ise True.
        """
        if not device_id or not token:
            return False

        self._paired_devices[device_id] = (
            PairedDevice(
                device_id=device_id,
                token=token,
                scopes=scopes or ["operator.*"],
                paired_at=time.time(),
                last_seen=time.time(),
            )
        )
        logger.info(
            "Cihaz eslesti: %s", device_id,
        )
        return True

    def unpair_device(
        self,
        device_id: str,
    ) -> bool:
        """Cihaz eslestirmesini kaldirir.

        Args:
            device_id: Cihaz tanimlayici.

        Returns:
            Basarili ise True.
        """
        if device_id in self._paired_devices:
            del self._paired_devices[device_id]
            logger.info(
                "Cihaz eslestirmesi kaldirildi: %s",
                device_id,
            )
            return True
        return False

    def get_paired(
        self,
        device_id: str,
    ) -> PairedDevice | None:
        """Eslesmis cihaz bilgisi dondurur.

        Args:
            device_id: Cihaz tanimlayici.

        Returns:
            Cihaz bilgisi veya None.
        """
        return self._paired_devices.get(device_id)

    @property
    def paired_count(self) -> int:
        """Eslesmis cihaz sayisi."""
        return len(self._paired_devices)
