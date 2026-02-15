"""ATLAS Ic Gozlem modulu.

Sema ic gozlemi, tip bilgisi,
alan detaylari, kaldirilma bilgisi
ve dokumantasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class Introspection:
    """Ic gozlem motoru.

    GraphQL semasini ic gozlemler.

    Attributes:
        _schema_data: Sema verisi.
        _deprecations: Kaldirilma bilgileri.
    """

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._schema_data: dict[
            str, dict[str, Any]
        ] = {}
        self._deprecations: dict[
            str, dict[str, Any]
        ] = {}
        self._documentation: dict[
            str, str
        ] = {}

        logger.info(
            "Introspection baslatildi",
        )

    def register_type(
        self,
        name: str,
        kind: str,
        fields: dict[str, dict[str, Any]]
            | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Tipi kaydeder.

        Args:
            name: Tip adi.
            kind: Tip turu (OBJECT/SCALAR/ENUM/...).
            fields: Alan bilgileri.
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        self._schema_data[name] = {
            "name": name,
            "kind": kind,
            "fields": fields or {},
            "description": description,
            "registered_at": time.time(),
        }

        if description:
            self._documentation[name] = (
                description
            )

        return {"name": name, "kind": kind}

    def get_type(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Tip bilgisini getirir.

        Args:
            name: Tip adi.

        Returns:
            Tip bilgisi veya None.
        """
        return self._schema_data.get(name)

    def get_fields(
        self,
        type_name: str,
    ) -> dict[str, dict[str, Any]]:
        """Tip alanlarini getirir.

        Args:
            type_name: Tip adi.

        Returns:
            Alan bilgileri.
        """
        t = self._schema_data.get(type_name)
        if not t:
            return {}
        return dict(t.get("fields", {}))

    def get_field(
        self,
        type_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        """Alan bilgisini getirir.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.

        Returns:
            Alan bilgisi veya None.
        """
        t = self._schema_data.get(type_name)
        if not t:
            return None
        return t.get("fields", {}).get(field_name)

    def deprecate(
        self,
        type_name: str,
        field_name: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Kaldirildi olarak isaretler.

        Args:
            type_name: Tip adi.
            field_name: Alan adi (None=tip).
            reason: Sebep.

        Returns:
            Kaldirilma bilgisi.
        """
        key = (
            f"{type_name}.{field_name}"
            if field_name else type_name
        )

        self._deprecations[key] = {
            "type": type_name,
            "field": field_name,
            "reason": reason,
            "deprecated_at": time.time(),
        }

        return {
            "key": key,
            "reason": reason,
        }

    def is_deprecated(
        self,
        type_name: str,
        field_name: str | None = None,
    ) -> bool:
        """Kaldirilmis mi kontrol eder.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.

        Returns:
            Kaldirilmis mi.
        """
        key = (
            f"{type_name}.{field_name}"
            if field_name else type_name
        )
        return key in self._deprecations

    def get_deprecation(
        self,
        type_name: str,
        field_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Kaldirilma bilgisini getirir.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.

        Returns:
            Bilgi veya None.
        """
        key = (
            f"{type_name}.{field_name}"
            if field_name else type_name
        )
        return self._deprecations.get(key)

    def set_documentation(
        self,
        name: str,
        doc: str,
    ) -> None:
        """Dokumantasyon ayarlar.

        Args:
            name: Isim.
            doc: Dokumantasyon.
        """
        self._documentation[name] = doc

    def get_documentation(
        self,
        name: str,
    ) -> str | None:
        """Dokumantasyon getirir.

        Args:
            name: Isim.

        Returns:
            Dokumantasyon veya None.
        """
        return self._documentation.get(name)

    def introspect(self) -> dict[str, Any]:
        """Tam ic gozlem yapar.

        Returns:
            Sema bilgisi.
        """
        types_info: list[dict[str, Any]] = []
        for name, t in self._schema_data.items():
            info: dict[str, Any] = {
                "name": name,
                "kind": t["kind"],
                "description": t.get(
                    "description", "",
                ),
                "fields": [],
            }
            for fname, fdata in t.get(
                "fields", {},
            ).items():
                field_info = {
                    "name": fname,
                    **fdata,
                    "isDeprecated": self.is_deprecated(
                        name, fname,
                    ),
                }
                dep = self.get_deprecation(
                    name, fname,
                )
                if dep:
                    field_info[
                        "deprecationReason"
                    ] = dep["reason"]
                info["fields"].append(field_info)

            types_info.append(info)

        return {
            "__schema": {
                "types": types_info,
                "totalTypes": len(
                    self._schema_data,
                ),
                "deprecations": len(
                    self._deprecations,
                ),
            },
        }

    def list_types(
        self,
        kind: str | None = None,
    ) -> list[str]:
        """Tipleri listeler.

        Args:
            kind: Tur filtresi.

        Returns:
            Tip adlari.
        """
        if kind:
            return [
                n for n, t
                in self._schema_data.items()
                if t["kind"] == kind
            ]
        return list(self._schema_data.keys())

    @property
    def type_count(self) -> int:
        """Tip sayisi."""
        return len(self._schema_data)

    @property
    def deprecation_count(self) -> int:
        """Kaldirilma sayisi."""
        return len(self._deprecations)

    @property
    def doc_count(self) -> int:
        """Dokumantasyon sayisi."""
        return len(self._documentation)
