"""ATLAS API Kesfi modulu.

Resmi API'leri arama, dokumantasyon bulma, endpoint cikarma,
kimlik dogrulama yontemlerini tespit etme ve rate limit algilama.
"""

import logging
from typing import Any

from app.models.jit import APIEndpoint, AuthMethod, OutputFormat

logger = logging.getLogger(__name__)

# Bilinen API katalog
_KNOWN_APIS: dict[str, dict[str, Any]] = {
    "google_ads": {
        "base_url": "https://googleads.googleapis.com",
        "auth": AuthMethod.OAUTH2,
        "doc_url": "https://developers.google.com/google-ads/api",
        "rate_limit": 1000,
        "endpoints": ["campaigns", "ad_groups", "keywords", "reports"],
    },
    "gmail": {
        "base_url": "https://gmail.googleapis.com",
        "auth": AuthMethod.OAUTH2,
        "doc_url": "https://developers.google.com/gmail/api",
        "rate_limit": 250,
        "endpoints": ["messages", "labels", "drafts", "threads"],
    },
    "telegram": {
        "base_url": "https://api.telegram.org",
        "auth": AuthMethod.BEARER_TOKEN,
        "doc_url": "https://core.telegram.org/bots/api",
        "rate_limit": 30,
        "endpoints": ["sendMessage", "getUpdates", "sendPhoto", "sendDocument"],
    },
    "weather": {
        "base_url": "https://api.openweathermap.org",
        "auth": AuthMethod.API_KEY,
        "doc_url": "https://openweathermap.org/api",
        "rate_limit": 60,
        "endpoints": ["weather", "forecast", "onecall"],
    },
    "stripe": {
        "base_url": "https://api.stripe.com/v1",
        "auth": AuthMethod.BEARER_TOKEN,
        "doc_url": "https://stripe.com/docs/api",
        "rate_limit": 100,
        "endpoints": ["charges", "customers", "invoices", "subscriptions"],
    },
    "github": {
        "base_url": "https://api.github.com",
        "auth": AuthMethod.BEARER_TOKEN,
        "doc_url": "https://docs.github.com/en/rest",
        "rate_limit": 5000,
        "endpoints": ["repos", "issues", "pulls", "users"],
    },
    "maps": {
        "base_url": "https://maps.googleapis.com/maps/api",
        "auth": AuthMethod.API_KEY,
        "doc_url": "https://developers.google.com/maps",
        "rate_limit": 50000,
        "endpoints": ["geocode", "directions", "places", "distancematrix"],
    },
    "twilio": {
        "base_url": "https://api.twilio.com/2010-04-01",
        "auth": AuthMethod.BASIC,
        "doc_url": "https://www.twilio.com/docs/usage/api",
        "rate_limit": 100,
        "endpoints": ["Messages", "Calls", "Accounts"],
    },
}


class APIDiscoverer:
    """API kesif sistemi.

    Resmi API'leri arar, dokumantasyon bulur, endpoint bilgisi
    cikarir ve kimlik dogrulama yontemlerini tespit eder.

    Attributes:
        _discovered: Kesfedilen API'ler.
        _custom_apis: Ozel eklenen API'ler.
    """

    def __init__(self) -> None:
        """API kesif sistemini baslatir."""
        self._discovered: dict[str, list[APIEndpoint]] = {}
        self._custom_apis: dict[str, dict[str, Any]] = {}

        logger.info("APIDiscoverer baslatildi")

    def search(self, api_name: str) -> list[APIEndpoint]:
        """API arar ve endpoint bilgilerini getirir.

        Args:
            api_name: API adi.

        Returns:
            APIEndpoint listesi.
        """
        name_lower = api_name.lower()

        # Onceden kesfedilmis mi?
        if name_lower in self._discovered:
            return self._discovered[name_lower]

        # Bilinen katalogda ara
        api_info = _KNOWN_APIS.get(name_lower) or self._custom_apis.get(name_lower)
        if not api_info:
            # Yakin eslesme dene
            api_info = self._fuzzy_search(name_lower)

        if not api_info:
            logger.warning("API bulunamadi: %s", api_name)
            return []

        endpoints = self._extract_endpoints(name_lower, api_info)
        self._discovered[name_lower] = endpoints

        logger.info("API kesfedildi: %s (%d endpoint)", api_name, len(endpoints))
        return endpoints

    def _fuzzy_search(self, query: str) -> dict[str, Any] | None:
        """Yakin eslesen API arar.

        Args:
            query: Arama sorgusu.

        Returns:
            API bilgisi veya None.
        """
        all_apis = {**_KNOWN_APIS, **self._custom_apis}
        for name, info in all_apis.items():
            if query in name or name in query:
                return info
        return None

    def _extract_endpoints(self, api_name: str, api_info: dict[str, Any]) -> list[APIEndpoint]:
        """API bilgisinden endpoint listesi cikarir.

        Args:
            api_name: API adi.
            api_info: API bilgisi.

        Returns:
            APIEndpoint listesi.
        """
        endpoints: list[APIEndpoint] = []
        base_url = api_info.get("base_url", "")
        auth = api_info.get("auth", AuthMethod.NONE)
        if isinstance(auth, str):
            auth = AuthMethod(auth)
        doc_url = api_info.get("doc_url", "")
        rate_limit = api_info.get("rate_limit", 0)

        for ep_name in api_info.get("endpoints", []):
            endpoint = APIEndpoint(
                name=f"{api_name}_{ep_name}",
                base_url=base_url,
                path=f"/{ep_name}",
                auth_method=auth,
                rate_limit=rate_limit,
                doc_url=doc_url,
            )
            endpoints.append(endpoint)

        return endpoints

    def find_documentation(self, api_name: str) -> str:
        """API dokumantasyon URL'ini bulur.

        Args:
            api_name: API adi.

        Returns:
            Dokumantasyon URL'i.
        """
        name_lower = api_name.lower()
        all_apis = {**_KNOWN_APIS, **self._custom_apis}

        if name_lower in all_apis:
            return all_apis[name_lower].get("doc_url", "")

        # Yakin eslesme
        for name, info in all_apis.items():
            if name_lower in name or name in name_lower:
                return info.get("doc_url", "")

        return ""

    def get_auth_method(self, api_name: str) -> AuthMethod:
        """API kimlik dogrulama yontemini getirir.

        Args:
            api_name: API adi.

        Returns:
            AuthMethod enum degeri.
        """
        name_lower = api_name.lower()
        all_apis = {**_KNOWN_APIS, **self._custom_apis}

        if name_lower in all_apis:
            auth = all_apis[name_lower].get("auth", AuthMethod.NONE)
            return AuthMethod(auth) if isinstance(auth, str) else auth

        return AuthMethod.NONE

    def get_rate_limit(self, api_name: str) -> int:
        """API rate limitini getirir.

        Args:
            api_name: API adi.

        Returns:
            Dakika basina istek limiti (0 = bilinmiyor).
        """
        name_lower = api_name.lower()
        all_apis = {**_KNOWN_APIS, **self._custom_apis}

        if name_lower in all_apis:
            return all_apis[name_lower].get("rate_limit", 0)

        return 0

    def register_api(self, name: str, info: dict[str, Any]) -> None:
        """Ozel API kaydeder.

        Args:
            name: API adi.
            info: API bilgisi (base_url, auth, endpoints, vb).
        """
        self._custom_apis[name.lower()] = info
        logger.info("Ozel API kaydedildi: %s", name)

    @property
    def discovered_count(self) -> int:
        """Kesfedilen API sayisi."""
        return len(self._discovered)

    @property
    def known_apis(self) -> list[str]:
        """Bilinen API listesi."""
        return list(_KNOWN_APIS.keys()) + list(self._custom_apis.keys())
