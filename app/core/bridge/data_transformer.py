"""ATLAS Veri Donusturucu modulu.

Format donusturme, sema haritalama, veri zenginlestirme,
dogrulama ve normalizasyon.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DataTransformer:
    """Veri donusturucu.

    Sistemler arasi veri formatlarini donusturur,
    semalari haritalar ve veriyi zenginlestirir.

    Attributes:
        _converters: Format donusturuculeri.
        _schemas: Sema haritalari.
        _enrichers: Zenginlestiriciler.
        _validators: Dogrulayicilar.
        _normalizers: Normalizatorler.
    """

    def __init__(self) -> None:
        """Veri donusturucuyu baslatir."""
        self._converters: dict[str, Callable] = {}
        self._schemas: dict[str, dict[str, str]] = {}
        self._enrichers: dict[str, Callable] = {}
        self._validators: dict[str, Callable] = {}
        self._normalizers: dict[str, Callable] = {}

        logger.info("DataTransformer baslatildi")

    def register_converter(
        self,
        name: str,
        converter: Callable,
    ) -> None:
        """Format donusturucu kaydeder.

        Args:
            name: Donusturucu adi (orn: "json_to_xml").
            converter: Donusturme fonksiyonu.
        """
        self._converters[name] = converter

    def convert(
        self,
        name: str,
        data: Any,
    ) -> Any:
        """Veriyi donusturur.

        Args:
            name: Donusturucu adi.
            data: Giris verisi.

        Returns:
            Donusturulmus veri.
        """
        converter = self._converters.get(name)
        if not converter:
            return data
        return converter(data)

    def register_schema(
        self,
        name: str,
        mapping: dict[str, str],
    ) -> None:
        """Sema haritasi kaydeder.

        Args:
            name: Sema adi.
            mapping: Alan eslesmesi (kaynak -> hedef).
        """
        self._schemas[name] = mapping

    def map_schema(
        self,
        schema_name: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Sema haritasi uygular.

        Args:
            schema_name: Sema adi.
            data: Giris verisi.

        Returns:
            Haritalanmis veri.
        """
        mapping = self._schemas.get(schema_name)
        if not mapping:
            return dict(data)

        result: dict[str, Any] = {}
        for source_key, target_key in mapping.items():
            if source_key in data:
                result[target_key] = data[source_key]

        return result

    def register_enricher(
        self,
        name: str,
        enricher: Callable,
    ) -> None:
        """Zenginlestirici kaydeder.

        Args:
            name: Zenginlestirici adi.
            enricher: Zenginlestirme fonksiyonu.
        """
        self._enrichers[name] = enricher

    def enrich(
        self,
        name: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Veriyi zenginlestirir.

        Args:
            name: Zenginlestirici adi.
            data: Giris verisi.

        Returns:
            Zenginlestirilmis veri.
        """
        enricher = self._enrichers.get(name)
        if not enricher:
            return data
        return enricher(data)

    def register_validator(
        self,
        name: str,
        validator: Callable,
    ) -> None:
        """Dogrulayici kaydeder.

        Args:
            name: Dogrulayici adi.
            validator: Dogrulama fonksiyonu (data -> bool).
        """
        self._validators[name] = validator

    def validate(
        self,
        name: str,
        data: Any,
    ) -> bool:
        """Veriyi dogrular.

        Args:
            name: Dogrulayici adi.
            data: Dogrulanacak veri.

        Returns:
            Gecerli ise True.
        """
        validator = self._validators.get(name)
        if not validator:
            return True
        return validator(data)

    def register_normalizer(
        self,
        name: str,
        normalizer: Callable,
    ) -> None:
        """Normalizator kaydeder.

        Args:
            name: Normalizator adi.
            normalizer: Normalizasyon fonksiyonu.
        """
        self._normalizers[name] = normalizer

    def normalize(
        self,
        name: str,
        data: Any,
    ) -> Any:
        """Veriyi normalize eder.

        Args:
            name: Normalizator adi.
            data: Giris verisi.

        Returns:
            Normalize edilmis veri.
        """
        normalizer = self._normalizers.get(name)
        if not normalizer:
            return data
        return normalizer(data)

    def transform_pipeline(
        self,
        data: dict[str, Any],
        steps: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Donusturme pipeline'i uygular.

        Args:
            data: Giris verisi.
            steps: Adim listesi [{"type": "...", "name": "..."}].

        Returns:
            Donusturulmus veri.
        """
        result = dict(data)

        for step in steps:
            step_type = step.get("type", "")
            step_name = step.get("name", "")

            if step_type == "convert":
                result = self.convert(step_name, result)
            elif step_type == "schema":
                result = self.map_schema(step_name, result)
            elif step_type == "enrich":
                result = self.enrich(step_name, result)
            elif step_type == "normalize":
                result = self.normalize(step_name, result)

        return result

    @property
    def total_converters(self) -> int:
        """Toplam donusturucu sayisi."""
        return len(self._converters)

    @property
    def total_schemas(self) -> int:
        """Toplam sema sayisi."""
        return len(self._schemas)

    @property
    def total_validators(self) -> int:
        """Toplam dogrulayici sayisi."""
        return len(self._validators)
