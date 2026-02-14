"""ATLAS Yerel Ayar Yoneticisi modulu.

Tarih/saat bicimlendirme, sayi
bicimlendirme, para birimi, birim
donusumu ve bolgesel tercihler.
"""

import logging
from typing import Any

from app.models.localization import LanguageCode

logger = logging.getLogger(__name__)

# Yerel ayar yapilari
_LOCALE_FORMATS: dict[str, dict[str, Any]] = {
    "tr": {
        "date": "DD.MM.YYYY",
        "time": "HH:mm",
        "decimal_sep": ",",
        "thousands_sep": ".",
        "currency": "TRY",
        "currency_symbol": "₺",
        "currency_position": "after",
    },
    "en": {
        "date": "MM/DD/YYYY",
        "time": "hh:mm A",
        "decimal_sep": ".",
        "thousands_sep": ",",
        "currency": "USD",
        "currency_symbol": "$",
        "currency_position": "before",
    },
    "de": {
        "date": "DD.MM.YYYY",
        "time": "HH:mm",
        "decimal_sep": ",",
        "thousands_sep": ".",
        "currency": "EUR",
        "currency_symbol": "€",
        "currency_position": "after",
    },
    "fr": {
        "date": "DD/MM/YYYY",
        "time": "HH:mm",
        "decimal_sep": ",",
        "thousands_sep": " ",
        "currency": "EUR",
        "currency_symbol": "€",
        "currency_position": "after",
    },
    "ar": {
        "date": "DD/MM/YYYY",
        "time": "hh:mm",
        "decimal_sep": "٫",
        "thousands_sep": "٬",
        "currency": "SAR",
        "currency_symbol": "ر.س",
        "currency_position": "after",
    },
}

# Birim donusum carpanlari (SI base)
_UNIT_CONVERSIONS: dict[str, dict[str, float]] = {
    "length": {
        "m": 1.0,
        "km": 1000.0,
        "cm": 0.01,
        "mm": 0.001,
        "in": 0.0254,
        "ft": 0.3048,
        "mi": 1609.344,
    },
    "weight": {
        "kg": 1.0,
        "g": 0.001,
        "lb": 0.453592,
        "oz": 0.0283495,
    },
    "temperature": {},  # Ozel islem
}


class LocaleManager:
    """Yerel ayar yoneticisi.

    Tarih, sayi, para birimi bicimlendirme
    ve birim donusumu yapar.

    Attributes:
        _default_locale: Varsayilan yerel ayar.
        _custom_formats: Ozel birimler.
    """

    def __init__(
        self,
        default_locale: str = "en",
    ) -> None:
        """Yerel ayar yoneticisini baslatir.

        Args:
            default_locale: Varsayilan yerel ayar.
        """
        self._default_locale = default_locale
        self._custom_formats: dict[str, dict[str, Any]] = {}

        logger.info("LocaleManager baslatildi")

    def format_number(
        self,
        value: float,
        locale: str | None = None,
        decimals: int = 2,
    ) -> str:
        """Sayi bicimlendirir.

        Args:
            value: Sayi degeri.
            locale: Yerel ayar.
            decimals: Ondalik basamak.

        Returns:
            Bicimlenmis sayi.
        """
        loc = locale or self._default_locale
        fmt = _LOCALE_FORMATS.get(
            loc, _LOCALE_FORMATS["en"],
        )

        # Tam ve ondalik kismi ayir
        formatted = f"{abs(value):,.{decimals}f}"
        # Varsayilan ayiraclari degistir
        formatted = formatted.replace(
            ",", "TEMP",
        ).replace(
            ".", fmt["decimal_sep"],
        ).replace(
            "TEMP", fmt["thousands_sep"],
        )

        if value < 0:
            formatted = f"-{formatted}"
        return formatted

    def format_currency(
        self,
        value: float,
        locale: str | None = None,
        currency: str | None = None,
    ) -> str:
        """Para birimi bicimlendirir.

        Args:
            value: Miktar.
            locale: Yerel ayar.
            currency: Para birimi kodu.

        Returns:
            Bicimlenmis para.
        """
        loc = locale or self._default_locale
        fmt = _LOCALE_FORMATS.get(
            loc, _LOCALE_FORMATS["en"],
        )

        symbol = currency or fmt["currency_symbol"]
        num = self.format_number(value, locale=loc)

        if fmt["currency_position"] == "before":
            return f"{symbol}{num}"
        return f"{num} {symbol}"

    def format_date(
        self,
        year: int,
        month: int,
        day: int,
        locale: str | None = None,
    ) -> str:
        """Tarih bicimlendirir.

        Args:
            year: Yil.
            month: Ay.
            day: Gun.
            locale: Yerel ayar.

        Returns:
            Bicimlenmis tarih.
        """
        loc = locale or self._default_locale
        fmt = _LOCALE_FORMATS.get(
            loc, _LOCALE_FORMATS["en"],
        )

        pattern = fmt["date"]
        result = pattern.replace(
            "YYYY", str(year),
        ).replace(
            "MM", f"{month:02d}",
        ).replace(
            "DD", f"{day:02d}",
        )
        return result

    def convert_unit(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
        category: str = "length",
    ) -> float | None:
        """Birim donusturur.

        Args:
            value: Deger.
            from_unit: Kaynak birim.
            to_unit: Hedef birim.
            category: Kategori.

        Returns:
            Donusturulmus deger veya None.
        """
        if category == "temperature":
            return self._convert_temperature(
                value, from_unit, to_unit,
            )

        units = _UNIT_CONVERSIONS.get(category, {})
        from_factor = units.get(from_unit)
        to_factor = units.get(to_unit)

        if from_factor is None or to_factor is None:
            return None

        # SI tabanina donustur, sonra hedef birime
        base_value = value * from_factor
        return round(base_value / to_factor, 6)

    def get_locale_info(
        self,
        locale: str | None = None,
    ) -> dict[str, Any]:
        """Yerel ayar bilgisi getirir.

        Args:
            locale: Yerel ayar.

        Returns:
            Yerel ayar bilgisi.
        """
        loc = locale or self._default_locale
        fmt = _LOCALE_FORMATS.get(loc)
        if fmt:
            return {"locale": loc, **fmt}
        return {"locale": loc, "supported": False}

    def set_custom_format(
        self,
        locale: str,
        key: str,
        value: Any,
    ) -> None:
        """Ozel birim ayarlar.

        Args:
            locale: Yerel ayar.
            key: Anahtar.
            value: Deger.
        """
        if locale not in self._custom_formats:
            self._custom_formats[locale] = {}
        self._custom_formats[locale][key] = value

    def get_supported_locales(self) -> list[str]:
        """Desteklenen yerel ayarlari getirir.

        Returns:
            Yerel ayar listesi.
        """
        return list(_LOCALE_FORMATS.keys())

    def _convert_temperature(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> float | None:
        """Sicaklik donusturur.

        Args:
            value: Deger.
            from_unit: Kaynak birim.
            to_unit: Hedef birim.

        Returns:
            Donusturulmus deger.
        """
        # Celsius'a donustur
        if from_unit == "C":
            celsius = value
        elif from_unit == "F":
            celsius = (value - 32) * 5 / 9
        elif from_unit == "K":
            celsius = value - 273.15
        else:
            return None

        # Hedef birime donustur
        if to_unit == "C":
            return round(celsius, 2)
        if to_unit == "F":
            return round(celsius * 9 / 5 + 32, 2)
        if to_unit == "K":
            return round(celsius + 273.15, 2)
        return None

    @property
    def default_locale(self) -> str:
        """Varsayilan yerel ayar."""
        return self._default_locale

    @property
    def locale_count(self) -> int:
        """Desteklenen yerel ayar sayisi."""
        return len(_LOCALE_FORMATS)
