"""ATLAS Sema Olusturucu modulu.

Tip tanimlari, query/mutation/subscription
tipleri ve input tipleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SchemaBuilder:
    """Sema olusturucu.

    GraphQL semasi olusturur ve yonetir.

    Attributes:
        _types: Tip tanimlari.
        _queries: Sorgu tanimlari.
    """

    def __init__(self) -> None:
        """Olusturucuyu baslatir."""
        self._types: dict[
            str, dict[str, Any]
        ] = {}
        self._queries: dict[
            str, dict[str, Any]
        ] = {}
        self._mutations: dict[
            str, dict[str, Any]
        ] = {}
        self._subscriptions: dict[
            str, dict[str, Any]
        ] = {}
        self._inputs: dict[
            str, dict[str, Any]
        ] = {}
        self._enums: dict[
            str, dict[str, Any]
        ] = {}
        self._interfaces: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "SchemaBuilder baslatildi",
        )

    def add_type(
        self,
        name: str,
        fields: dict[str, str],
        description: str = "",
        interfaces: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tip ekler.

        Args:
            name: Tip adi.
            fields: Alan tanimlari.
            description: Aciklama.
            interfaces: Uyguladigi arayuzler.

        Returns:
            Tip bilgisi.
        """
        self._types[name] = {
            "name": name,
            "fields": fields,
            "description": description,
            "interfaces": interfaces or [],
            "created_at": time.time(),
        }

        return {
            "name": name,
            "fields": len(fields),
        }

    def add_query(
        self,
        name: str,
        return_type: str,
        args: dict[str, str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Sorgu ekler.

        Args:
            name: Sorgu adi.
            return_type: Donus tipi.
            args: Argumanlar.
            description: Aciklama.

        Returns:
            Sorgu bilgisi.
        """
        self._queries[name] = {
            "name": name,
            "return_type": return_type,
            "args": args or {},
            "description": description,
        }

        return {
            "name": name,
            "return_type": return_type,
        }

    def add_mutation(
        self,
        name: str,
        return_type: str,
        args: dict[str, str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Mutasyon ekler.

        Args:
            name: Mutasyon adi.
            return_type: Donus tipi.
            args: Argumanlar.
            description: Aciklama.

        Returns:
            Mutasyon bilgisi.
        """
        self._mutations[name] = {
            "name": name,
            "return_type": return_type,
            "args": args or {},
            "description": description,
        }

        return {
            "name": name,
            "return_type": return_type,
        }

    def add_subscription(
        self,
        name: str,
        return_type: str,
        args: dict[str, str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Abonelik ekler.

        Args:
            name: Abonelik adi.
            return_type: Donus tipi.
            args: Argumanlar.
            description: Aciklama.

        Returns:
            Abonelik bilgisi.
        """
        self._subscriptions[name] = {
            "name": name,
            "return_type": return_type,
            "args": args or {},
            "description": description,
        }

        return {
            "name": name,
            "return_type": return_type,
        }

    def add_input(
        self,
        name: str,
        fields: dict[str, str],
        description: str = "",
    ) -> dict[str, Any]:
        """Input tipi ekler.

        Args:
            name: Input adi.
            fields: Alanlar.
            description: Aciklama.

        Returns:
            Input bilgisi.
        """
        self._inputs[name] = {
            "name": name,
            "fields": fields,
            "description": description,
        }

        return {"name": name, "fields": len(fields)}

    def add_enum(
        self,
        name: str,
        values: list[str],
        description: str = "",
    ) -> dict[str, Any]:
        """Enum tipi ekler.

        Args:
            name: Enum adi.
            values: Degerler.
            description: Aciklama.

        Returns:
            Enum bilgisi.
        """
        self._enums[name] = {
            "name": name,
            "values": values,
            "description": description,
        }

        return {"name": name, "values": len(values)}

    def add_interface(
        self,
        name: str,
        fields: dict[str, str],
        description: str = "",
    ) -> dict[str, Any]:
        """Arayuz ekler.

        Args:
            name: Arayuz adi.
            fields: Alanlar.
            description: Aciklama.

        Returns:
            Arayuz bilgisi.
        """
        self._interfaces[name] = {
            "name": name,
            "fields": fields,
            "description": description,
        }

        return {"name": name, "fields": len(fields)}

    def get_type(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Tip getirir.

        Args:
            name: Tip adi.

        Returns:
            Tip bilgisi veya None.
        """
        return self._types.get(name)

    def get_query(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Sorgu getirir.

        Args:
            name: Sorgu adi.

        Returns:
            Sorgu bilgisi veya None.
        """
        return self._queries.get(name)

    def remove_type(
        self,
        name: str,
    ) -> bool:
        """Tip kaldirir.

        Args:
            name: Tip adi.

        Returns:
            Basarili mi.
        """
        if name in self._types:
            del self._types[name]
            return True
        return False

    def build_sdl(self) -> str:
        """SDL formatinda sema olusturur.

        Returns:
            SDL string.
        """
        parts: list[str] = []

        for name, enum in self._enums.items():
            vals = " ".join(enum["values"])
            parts.append(
                f"enum {name} {{ {vals} }}",
            )

        for name, iface in self._interfaces.items():
            fields_str = " ".join(
                f"{f}: {t}"
                for f, t in iface["fields"].items()
            )
            parts.append(
                f"interface {name} {{ {fields_str} }}",
            )

        for name, inp in self._inputs.items():
            fields_str = " ".join(
                f"{f}: {t}"
                for f, t in inp["fields"].items()
            )
            parts.append(
                f"input {name} {{ {fields_str} }}",
            )

        for name, t in self._types.items():
            impl = ""
            if t["interfaces"]:
                impl = (
                    " implements "
                    + " & ".join(t["interfaces"])
                )
            fields_str = " ".join(
                f"{f}: {ft}"
                for f, ft in t["fields"].items()
            )
            parts.append(
                f"type {name}{impl} {{ {fields_str} }}",
            )

        if self._queries:
            q_fields = " ".join(
                f"{n}: {q['return_type']}"
                for n, q in self._queries.items()
            )
            parts.append(
                f"type Query {{ {q_fields} }}",
            )

        if self._mutations:
            m_fields = " ".join(
                f"{n}: {m['return_type']}"
                for n, m in self._mutations.items()
            )
            parts.append(
                f"type Mutation {{ {m_fields} }}",
            )

        return "\n".join(parts)

    @property
    def type_count(self) -> int:
        """Tip sayisi."""
        return len(self._types)

    @property
    def query_count(self) -> int:
        """Sorgu sayisi."""
        return len(self._queries)

    @property
    def mutation_count(self) -> int:
        """Mutasyon sayisi."""
        return len(self._mutations)

    @property
    def subscription_count(self) -> int:
        """Abonelik sayisi."""
        return len(self._subscriptions)

    @property
    def input_count(self) -> int:
        """Input sayisi."""
        return len(self._inputs)

    @property
    def total_definitions(self) -> int:
        """Toplam tanim sayisi."""
        return (
            len(self._types)
            + len(self._queries)
            + len(self._mutations)
            + len(self._subscriptions)
            + len(self._inputs)
            + len(self._enums)
            + len(self._interfaces)
        )
