"""ATLAS Takip Linki Üretici.

Benzersiz link üretimi, UTM parametreleri,
kısa URL, QR kod ve derin link.
"""

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TrackingLinkGenerator:
    """Takip linki üretici.

    Referans takip linkleri üretir,
    UTM parametreleri ekler ve kısaltır.

    Attributes:
        _links: Link kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._links: dict[str, dict] = {}
        self._stats = {
            "links_generated": 0,
            "qr_codes_created": 0,
        }
        logger.info(
            "TrackingLinkGenerator "
            "baslatildi",
        )

    @property
    def link_count(self) -> int:
        """Üretilen link sayısı."""
        return self._stats[
            "links_generated"
        ]

    @property
    def qr_count(self) -> int:
        """Oluşturulan QR kod sayısı."""
        return self._stats[
            "qr_codes_created"
        ]

    def generate_link(
        self,
        referrer_id: str,
        campaign: str = "",
        base_url: str = "https://app.example.com",
    ) -> dict[str, Any]:
        """Benzersiz link üretir.

        Args:
            referrer_id: Referansçı kimliği.
            campaign: Kampanya adı.
            base_url: Temel URL.

        Returns:
            Link bilgisi.
        """
        code = hashlib.md5(
            f"{referrer_id}_{campaign}".encode(),
        ).hexdigest()[:8]

        url = f"{base_url}/ref/{code}"
        lid = f"lnk_{len(self._links)}"
        self._links[lid] = {
            "referrer_id": referrer_id,
            "code": code,
            "url": url,
            "clicks": 0,
        }
        self._stats[
            "links_generated"
        ] += 1

        logger.info(
            "Link uretildi: %s -> %s",
            referrer_id,
            code,
        )

        return {
            "link_id": lid,
            "referrer_id": referrer_id,
            "code": code,
            "url": url,
            "generated": True,
        }

    def add_utm_params(
        self,
        url: str,
        source: str = "referral",
        medium: str = "link",
        campaign: str = "",
    ) -> dict[str, Any]:
        """UTM parametreleri ekler.

        Args:
            url: Temel URL.
            source: Kaynak.
            medium: Ortam.
            campaign: Kampanya.

        Returns:
            UTM bilgisi.
        """
        params = (
            f"utm_source={source}"
            f"&utm_medium={medium}"
        )
        if campaign:
            params += (
                f"&utm_campaign={campaign}"
            )

        separator = (
            "&" if "?" in url else "?"
        )
        full_url = f"{url}{separator}{params}"

        return {
            "original_url": url,
            "full_url": full_url,
            "utm_source": source,
            "utm_medium": medium,
            "added": True,
        }

    def create_short_url(
        self,
        url: str,
        custom_slug: str = "",
    ) -> dict[str, Any]:
        """Kısa URL oluşturur.

        Args:
            url: Uzun URL.
            custom_slug: Özel kısa ad.

        Returns:
            Kısa URL bilgisi.
        """
        slug = custom_slug or hashlib.md5(
            url.encode(),
        ).hexdigest()[:6]

        short = f"https://ref.link/{slug}"

        return {
            "original_url": url,
            "short_url": short,
            "slug": slug,
            "created": True,
        }

    def generate_qr_code(
        self,
        url: str,
        size: int = 256,
    ) -> dict[str, Any]:
        """QR kod üretir.

        Args:
            url: URL.
            size: Boyut (piksel).

        Returns:
            QR bilgisi.
        """
        self._stats[
            "qr_codes_created"
        ] += 1

        return {
            "url": url,
            "size": size,
            "format": "png",
            "generated": True,
        }

    def create_deep_link(
        self,
        referrer_id: str,
        target_screen: str = "home",
        platform: str = "universal",
    ) -> dict[str, Any]:
        """Derin link oluşturur.

        Args:
            referrer_id: Referansçı kimliği.
            target_screen: Hedef ekran.
            platform: Platform.

        Returns:
            Derin link bilgisi.
        """
        code = hashlib.md5(
            referrer_id.encode(),
        ).hexdigest()[:8]

        if platform == "ios":
            link = (
                f"app://ref/{code}"
                f"?screen={target_screen}"
            )
        elif platform == "android":
            link = (
                f"intent://ref/{code}"
                f"?screen={target_screen}"
            )
        else:
            link = (
                f"https://app.link/ref/{code}"
                f"?screen={target_screen}"
            )

        return {
            "referrer_id": referrer_id,
            "deep_link": link,
            "platform": platform,
            "created": True,
        }
