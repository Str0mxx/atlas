"""ATLAS Degisken Yoneticisi modulu.

Is akisi degiskenleri, global
degiskenler, gizli referanslar,
dinamik degerler ve kapsam yonetimi.
"""

import logging
from typing import Any

from app.models.workflow_engine import VariableScope

logger = logging.getLogger(__name__)


class VariableManager:
    """Degisken yoneticisi.

    Is akisi degiskenlerini yonetir
    ve kapsam izler.

    Attributes:
        _scopes: Kapsam degiskenleri.
        _secrets: Gizli referanslar.
    """

    def __init__(self) -> None:
        """Degisken yoneticisini baslatir."""
        self._scopes: dict[
            str, dict[str, Any]
        ] = {
            VariableScope.GLOBAL.value: {},
        }
        self._secrets: dict[str, str] = {}
        self._history: list[dict[str, Any]] = []

        logger.info("VariableManager baslatildi")

    def set_variable(
        self,
        name: str,
        value: Any,
        scope: VariableScope = VariableScope.WORKFLOW,
        workflow_id: str = "",
    ) -> None:
        """Degisken ayarlar.

        Args:
            name: Degisken adi.
            value: Deger.
            scope: Kapsam.
            workflow_id: Is akisi ID.
        """
        scope_key = self._scope_key(
            scope, workflow_id,
        )
        if scope_key not in self._scopes:
            self._scopes[scope_key] = {}
        self._scopes[scope_key][name] = value

        self._history.append({
            "action": "set",
            "name": name,
            "scope": scope.value,
            "workflow_id": workflow_id,
        })

    def get_variable(
        self,
        name: str,
        scope: VariableScope = VariableScope.WORKFLOW,
        workflow_id: str = "",
        default: Any = None,
    ) -> Any:
        """Degisken getirir.

        Args:
            name: Degisken adi.
            scope: Kapsam.
            workflow_id: Is akisi ID.
            default: Varsayilan deger.

        Returns:
            Degisken degeri.
        """
        scope_key = self._scope_key(
            scope, workflow_id,
        )
        scope_vars = self._scopes.get(
            scope_key, {},
        )
        if name in scope_vars:
            return scope_vars[name]

        # Ust kapsam arama
        if scope == VariableScope.LOCAL:
            return self.get_variable(
                name, VariableScope.WORKFLOW,
                workflow_id, default,
            )
        if scope == VariableScope.WORKFLOW:
            return self.get_variable(
                name, VariableScope.GLOBAL,
                "", default,
            )

        return default

    def delete_variable(
        self,
        name: str,
        scope: VariableScope = VariableScope.WORKFLOW,
        workflow_id: str = "",
    ) -> bool:
        """Degisken siler.

        Args:
            name: Degisken adi.
            scope: Kapsam.
            workflow_id: Is akisi ID.

        Returns:
            Basarili ise True.
        """
        scope_key = self._scope_key(
            scope, workflow_id,
        )
        scope_vars = self._scopes.get(scope_key)
        if scope_vars and name in scope_vars:
            del scope_vars[name]
            return True
        return False

    def set_secret(
        self,
        name: str,
        reference: str,
    ) -> None:
        """Gizli referans ayarlar.

        Args:
            name: Gizli adi.
            reference: Referans.
        """
        self._secrets[name] = reference

    def get_secret(
        self,
        name: str,
    ) -> str | None:
        """Gizli referans getirir.

        Args:
            name: Gizli adi.

        Returns:
            Referans veya None.
        """
        return self._secrets.get(name)

    def resolve(
        self,
        template: str,
        scope: VariableScope = VariableScope.WORKFLOW,
        workflow_id: str = "",
    ) -> str:
        """Sablon cozer.

        Args:
            template: Sablon ({var} formati).
            scope: Kapsam.
            workflow_id: Is akisi ID.

        Returns:
            Cozulmus metin.
        """
        result = template
        scope_key = self._scope_key(
            scope, workflow_id,
        )
        all_vars = dict(
            self._scopes.get(
                VariableScope.GLOBAL.value, {},
            ),
        )
        all_vars.update(
            self._scopes.get(scope_key, {}),
        )

        for key, val in all_vars.items():
            result = result.replace(
                f"{{{key}}}", str(val),
            )
        return result

    def get_scope_variables(
        self,
        scope: VariableScope = VariableScope.WORKFLOW,
        workflow_id: str = "",
    ) -> dict[str, Any]:
        """Kapsam degiskenlerini getirir.

        Args:
            scope: Kapsam.
            workflow_id: Is akisi ID.

        Returns:
            Degiskenler.
        """
        scope_key = self._scope_key(
            scope, workflow_id,
        )
        return dict(
            self._scopes.get(scope_key, {}),
        )

    def clear_scope(
        self,
        scope: VariableScope = VariableScope.WORKFLOW,
        workflow_id: str = "",
    ) -> int:
        """Kapsami temizler.

        Args:
            scope: Kapsam.
            workflow_id: Is akisi ID.

        Returns:
            Temizlenen degisken sayisi.
        """
        scope_key = self._scope_key(
            scope, workflow_id,
        )
        scope_vars = self._scopes.get(scope_key)
        if scope_vars:
            count = len(scope_vars)
            scope_vars.clear()
            return count
        return 0

    def _scope_key(
        self,
        scope: VariableScope,
        workflow_id: str,
    ) -> str:
        """Kapsam anahtari olusturur.

        Args:
            scope: Kapsam.
            workflow_id: Is akisi ID.

        Returns:
            Kapsam anahtari.
        """
        if scope == VariableScope.GLOBAL:
            return VariableScope.GLOBAL.value
        if scope == VariableScope.SECRET:
            return VariableScope.SECRET.value
        return f"{scope.value}:{workflow_id}"

    @property
    def total_variables(self) -> int:
        """Toplam degisken sayisi."""
        return sum(
            len(v) for v in self._scopes.values()
        )

    @property
    def secret_count(self) -> int:
        """Gizli sayisi."""
        return len(self._secrets)

    @property
    def scope_count(self) -> int:
        """Kapsam sayisi."""
        return len(self._scopes)
