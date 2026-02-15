"""ATLAS Bilgi Enjektoru modulu.

Bilgi enjeksiyonu, mevcut ile birlestirme,
oncelik yonetimi, geri alma destegi, dogrulama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeInjector:
    """Bilgi enjektoru.

    Bilgiyi hedef sisteme enjekte eder.

    Attributes:
        _injections: Enjeksiyon kayitlari.
        _rollback_stack: Geri alma yigiti.
    """

    def __init__(self) -> None:
        """Bilgi enjektorunu baslatir."""
        self._injections: dict[
            str, dict[str, Any]
        ] = {}
        self._target_knowledge: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._rollback_stack: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "injected": 0,
            "rolled_back": 0,
        }

        logger.info(
            "KnowledgeInjector baslatildi",
        )

    def inject_knowledge(
        self,
        target_system: str,
        knowledge: dict[str, Any],
        priority: str = "normal",
        merge_strategy: str = "append",
    ) -> dict[str, Any]:
        """Bilgi enjekte eder.

        Args:
            target_system: Hedef sistem.
            knowledge: Bilgi verisi.
            priority: Oncelik.
            merge_strategy: Birlestirme stratejisi.

        Returns:
            Enjeksiyon bilgisi.
        """
        self._counter += 1
        inj_id = f"inj_{self._counter}"

        kid = knowledge.get(
            "knowledge_id", "",
        )

        # Mevcut bilgiyi kaydet (rollback icin)
        existing = self._target_knowledge.get(
            target_system, [],
        )
        self._rollback_stack[inj_id] = {
            "target_system": target_system,
            "previous_state": list(existing),
        }

        # Birlestirme
        if merge_strategy == "append":
            self._append_knowledge(
                target_system, knowledge,
            )
        elif merge_strategy == "replace":
            self._replace_knowledge(
                target_system, knowledge,
            )
        elif merge_strategy == "merge":
            self._merge_knowledge(
                target_system, knowledge,
            )
        else:
            self._append_knowledge(
                target_system, knowledge,
            )

        injection = {
            "injection_id": inj_id,
            "target_system": target_system,
            "knowledge_id": kid,
            "priority": priority,
            "merge_strategy": merge_strategy,
            "status": "completed",
            "injected_at": time.time(),
        }

        self._injections[inj_id] = injection
        self._stats["injected"] += 1

        return {
            "injection_id": inj_id,
            "knowledge_id": kid,
            "target_system": target_system,
            "injected": True,
        }

    def _append_knowledge(
        self,
        target_system: str,
        knowledge: dict[str, Any],
    ) -> None:
        """Bilgiyi ekler.

        Args:
            target_system: Hedef sistem.
            knowledge: Bilgi verisi.
        """
        if target_system not in (
            self._target_knowledge
        ):
            self._target_knowledge[
                target_system
            ] = []
        self._target_knowledge[
            target_system
        ].append(knowledge)

    def _replace_knowledge(
        self,
        target_system: str,
        knowledge: dict[str, Any],
    ) -> None:
        """Bilgiyi degistirir.

        Args:
            target_system: Hedef sistem.
            knowledge: Bilgi verisi.
        """
        kid = knowledge.get(
            "knowledge_id", "",
        )
        existing = self._target_knowledge.get(
            target_system, [],
        )
        self._target_knowledge[
            target_system
        ] = [
            k for k in existing
            if k.get("knowledge_id") != kid
        ]
        self._target_knowledge[
            target_system
        ].append(knowledge)

    def _merge_knowledge(
        self,
        target_system: str,
        knowledge: dict[str, Any],
    ) -> None:
        """Bilgiyi birlestirir.

        Args:
            target_system: Hedef sistem.
            knowledge: Bilgi verisi.
        """
        kid = knowledge.get(
            "knowledge_id", "",
        )
        existing = self._target_knowledge.get(
            target_system, [],
        )

        merged = False
        for i, k in enumerate(existing):
            if k.get("knowledge_id") == kid:
                # Mevcut bilgiyi guncelle
                existing[i] = {
                    **k, **knowledge,
                }
                merged = True
                break

        if not merged:
            self._append_knowledge(
                target_system, knowledge,
            )

    def rollback(
        self,
        injection_id: str,
    ) -> dict[str, Any]:
        """Enjeksiyonu geri alir.

        Args:
            injection_id: Enjeksiyon ID.

        Returns:
            Geri alma bilgisi.
        """
        rb = self._rollback_stack.get(
            injection_id,
        )
        if not rb:
            return {
                "error": (
                    "rollback_not_available"
                ),
            }

        target = rb["target_system"]
        self._target_knowledge[target] = (
            rb["previous_state"]
        )

        injection = self._injections.get(
            injection_id,
        )
        if injection:
            injection["status"] = "rolled_back"

        self._stats["rolled_back"] += 1

        return {
            "injection_id": injection_id,
            "target_system": target,
            "rolled_back": True,
        }

    def verify_injection(
        self,
        injection_id: str,
    ) -> dict[str, Any]:
        """Enjeksiyonu dogrular.

        Args:
            injection_id: Enjeksiyon ID.

        Returns:
            Dogrulama bilgisi.
        """
        injection = self._injections.get(
            injection_id,
        )
        if not injection:
            return {
                "error": (
                    "injection_not_found"
                ),
            }

        target = injection["target_system"]
        kid = injection["knowledge_id"]

        # Bilgi hedef sistemde var mi?
        current = self._target_knowledge.get(
            target, [],
        )
        found = any(
            k.get("knowledge_id") == kid
            for k in current
        )

        return {
            "injection_id": injection_id,
            "verified": found,
            "status": injection["status"],
        }

    def get_target_knowledge(
        self,
        target_system: str,
    ) -> list[dict[str, Any]]:
        """Hedef bilgilerini getirir.

        Args:
            target_system: Hedef sistem.

        Returns:
            Bilgi listesi.
        """
        return list(
            self._target_knowledge.get(
                target_system, [],
            ),
        )

    def get_injection(
        self,
        injection_id: str,
    ) -> dict[str, Any]:
        """Enjeksiyon getirir.

        Args:
            injection_id: Enjeksiyon ID.

        Returns:
            Enjeksiyon bilgisi.
        """
        inj = self._injections.get(
            injection_id,
        )
        if not inj:
            return {
                "error": (
                    "injection_not_found"
                ),
            }
        return dict(inj)

    @property
    def injection_count(self) -> int:
        """Enjeksiyon sayisi."""
        return self._stats["injected"]

    @property
    def rollback_count(self) -> int:
        """Geri alma sayisi."""
        return self._stats["rolled_back"]
