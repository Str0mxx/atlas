"""ATLAS Ihtiyac Analizi modulu.

Kullanici isteklerini parse etme, gerekli API'leri cikarma,
veri kaynaklarini belirleme, cikti formatini tespit etme
ve guvenlik gereksinimlerini analiz etme.
"""

import logging
import re
from typing import Any

from app.models.jit import (
    AuthMethod,
    OutputFormat,
    RequirementSpec,
    SecurityLevel,
)

logger = logging.getLogger(__name__)

# API anahtar kelimeleri
_API_KEYWORDS: dict[str, list[str]] = {
    "google_ads": ["google ads", "adwords", "kampanya", "reklam", "campaign"],
    "gmail": ["email", "e-posta", "mail", "gmail", "inbox"],
    "telegram": ["telegram", "mesaj", "bot", "notification"],
    "weather": ["hava durumu", "weather", "sicaklik", "temperature"],
    "maps": ["harita", "map", "konum", "location", "geocode"],
    "payment": ["odeme", "payment", "stripe", "iyzico", "fatura"],
    "social_media": ["instagram", "twitter", "facebook", "sosyal medya", "linkedin"],
    "analytics": ["analytics", "analitik", "istatistik", "metrik"],
    "storage": ["dosya", "file", "upload", "s3", "storage", "depolama"],
    "sms": ["sms", "kisa mesaj", "text message", "twilio"],
}

# Veri kaynaklari
_DATA_SOURCE_KEYWORDS: dict[str, list[str]] = {
    "database": ["veritabani", "database", "sql", "postgresql", "mysql"],
    "api": ["api", "rest", "endpoint", "servis", "service"],
    "web": ["web", "site", "sayfa", "url", "scrape"],
    "file": ["dosya", "file", "csv", "excel", "json", "pdf"],
    "cache": ["cache", "redis", "onbellek"],
    "queue": ["kuyruk", "queue", "celery", "task"],
}


class RequirementAnalyzer:
    """Ihtiyac analizi sistemi.

    Kullanici isteklerini analiz ederek yapisal
    gereksinim spesifikasyonlari olusturur.

    Attributes:
        _specs: Uretilen spesifikasyonlar.
    """

    def __init__(self) -> None:
        """Ihtiyac analizi sistemini baslatir."""
        self._specs: list[RequirementSpec] = []

        logger.info("RequirementAnalyzer baslatildi")

    def analyze(self, request: str) -> RequirementSpec:
        """Kullanici istegini analiz eder.

        Args:
            request: Ham kullanici istegi.

        Returns:
            RequirementSpec nesnesi.
        """
        intent = self._parse_intent(request)
        apis = self._extract_apis(request)
        sources = self._identify_data_sources(request)
        output = self._determine_output_format(request)
        security = self._analyze_security(request, apis)
        constraints = self._extract_constraints(request)

        spec = RequirementSpec(
            raw_request=request,
            parsed_intent=intent,
            required_apis=apis,
            data_sources=sources,
            output_format=output,
            security_level=security,
            constraints=constraints,
        )
        self._specs.append(spec)

        logger.info(
            "Ihtiyac analizi: intent=%s, apis=%d, sources=%d",
            intent, len(apis), len(sources),
        )
        return spec

    def _parse_intent(self, request: str) -> str:
        """Istekten niyeti cikarir.

        Args:
            request: Kullanici istegi.

        Returns:
            Niyet ozeti.
        """
        req_lower = request.lower()

        # Eylem tespiti
        action_patterns: dict[str, list[str]] = {
            "fetch": ["getir", "cek", "al", "fetch", "get", "retrieve"],
            "send": ["gonder", "yolla", "ilet", "send", "post", "push"],
            "analyze": ["analiz", "incele", "degerlendir", "analyze", "evaluate"],
            "monitor": ["izle", "takip", "monitor", "track", "watch"],
            "create": ["olustur", "yarat", "yap", "create", "generate", "build"],
            "update": ["guncelle", "degistir", "update", "modify", "change"],
            "delete": ["sil", "kaldir", "temizle", "delete", "remove", "clean"],
            "report": ["raporla", "ozetle", "report", "summarize", "export"],
            "integrate": ["entegre", "bagla", "connect", "integrate", "link"],
            "automate": ["otomatik", "zamanla", "schedule", "automate", "cron"],
        }

        detected_action = "process"
        for action, keywords in action_patterns.items():
            for kw in keywords:
                if kw in req_lower:
                    detected_action = action
                    break
            if detected_action != "process":
                break

        # Konu tespiti
        subject_words = [w for w in req_lower.split() if len(w) > 3]
        subject = " ".join(subject_words[:3]) if subject_words else "unknown"

        return f"{detected_action}:{subject}"

    def _extract_apis(self, request: str) -> list[str]:
        """Gerekli API'leri cikarir.

        Args:
            request: Kullanici istegi.

        Returns:
            API listesi.
        """
        apis: list[str] = []
        req_lower = request.lower()

        for api_name, keywords in _API_KEYWORDS.items():
            for kw in keywords:
                if kw in req_lower:
                    if api_name not in apis:
                        apis.append(api_name)
                    break

        return apis

    def _identify_data_sources(self, request: str) -> list[str]:
        """Veri kaynaklarini belirler.

        Args:
            request: Kullanici istegi.

        Returns:
            Veri kaynagi listesi.
        """
        sources: list[str] = []
        req_lower = request.lower()

        for source, keywords in _DATA_SOURCE_KEYWORDS.items():
            for kw in keywords:
                if kw in req_lower:
                    if source not in sources:
                        sources.append(source)
                    break

        return sources

    def _determine_output_format(self, request: str) -> OutputFormat:
        """Cikti formatini belirler.

        Args:
            request: Kullanici istegi.

        Returns:
            OutputFormat enum degeri.
        """
        req_lower = request.lower()

        format_map: dict[str, OutputFormat] = {
            "json": OutputFormat.JSON,
            "csv": OutputFormat.CSV,
            "excel": OutputFormat.CSV,
            "html": OutputFormat.HTML,
            "pdf": OutputFormat.BINARY,
            "dosya": OutputFormat.BINARY,
            "text": OutputFormat.TEXT,
            "metin": OutputFormat.TEXT,
            "stream": OutputFormat.STREAM,
            "canli": OutputFormat.STREAM,
        }

        for keyword, fmt in format_map.items():
            if keyword in req_lower:
                return fmt

        return OutputFormat.JSON

    def _analyze_security(self, request: str, apis: list[str]) -> SecurityLevel:
        """Guvenlik gereksinimlerini analiz eder.

        Args:
            request: Kullanici istegi.
            apis: Tespit edilen API'ler.

        Returns:
            SecurityLevel enum degeri.
        """
        req_lower = request.lower()

        if "oauth" in req_lower or "yetkilendirme" in req_lower:
            return SecurityLevel.OAUTH

        # API gerektiren servisler genellikle API key ister
        oauth_apis = {"social_media", "gmail"}
        if any(api in oauth_apis for api in apis):
            return SecurityLevel.OAUTH

        if apis:
            return SecurityLevel.API_KEY

        if "public" in req_lower or "acik" in req_lower:
            return SecurityLevel.PUBLIC

        return SecurityLevel.API_KEY

    def _extract_constraints(self, request: str) -> dict[str, Any]:
        """Kisitlamalari cikarir.

        Args:
            request: Kullanici istegi.

        Returns:
            Kisitlama sozlugu.
        """
        constraints: dict[str, Any] = {}
        req_lower = request.lower()

        # Sayi limitleri
        numbers = re.findall(r"(\d+)\s*(saniye|dakika|saat|gun|adet|kayit|limit)", req_lower)
        for num, unit in numbers:
            constraints[unit] = int(num)

        # Hiz gereksinimleri
        if "hizli" in req_lower or "fast" in req_lower:
            constraints["performance"] = "fast"
        if "gercek zamanli" in req_lower or "real-time" in req_lower:
            constraints["realtime"] = True

        # Periyodiklik
        if "her gun" in req_lower or "daily" in req_lower:
            constraints["schedule"] = "daily"
        elif "her saat" in req_lower or "hourly" in req_lower:
            constraints["schedule"] = "hourly"

        return constraints

    @property
    def spec_count(self) -> int:
        """Toplam spesifikasyon sayisi."""
        return len(self._specs)

    @property
    def specs(self) -> list[RequirementSpec]:
        """Tum spesifikasyonlar."""
        return list(self._specs)
