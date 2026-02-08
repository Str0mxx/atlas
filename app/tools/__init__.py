"""ATLAS arac modulleri.

Lazy import ile dairesel bagimliligi onler.
Kullanim: from app.tools.email_client import EmailClient
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.tools.email_client import EmailClient
    from app.tools.file_handler import FileHandler
    from app.tools.google_ads import GoogleAdsManager
    from app.tools.image_generator import ImageGenerator
    from app.tools.web_scraper import WebScraper

__all__ = [
    "EmailClient",
    "FileHandler",
    "GoogleAdsManager",
    "ImageGenerator",
    "WebScraper",
]


def __getattr__(name: str) -> type:
    """Lazy import ile modulleri yukler.

    Args:
        name: Yuklenmek istenen sinif adi.

    Returns:
        Ilgili sinif.

    Raises:
        AttributeError: Bilinmeyen isim.
    """
    if name == "EmailClient":
        from app.tools.email_client import EmailClient
        return EmailClient
    if name == "FileHandler":
        from app.tools.file_handler import FileHandler
        return FileHandler
    if name == "GoogleAdsManager":
        from app.tools.google_ads import GoogleAdsManager
        return GoogleAdsManager
    if name == "ImageGenerator":
        from app.tools.image_generator import ImageGenerator
        return ImageGenerator
    if name == "WebScraper":
        from app.tools.web_scraper import WebScraper
        return WebScraper
    raise AttributeError(f"module 'app.tools' has no attribute {name!r}")
